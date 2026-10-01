"""Independent static policy rejects executable syntax and changed supplied data."""

import json
import warnings
from pathlib import Path

import pytest
from autocad_mcp.advanced.codegen.models import decode_recipe
from autocad_mcp.advanced.codegen.render import render_recipe
from autocad_mcp.advanced.codegen.validate import validate_source

from .test_models import request

FIXTURES = Path(__file__).resolve().parents[3] / "fixtures" / "codegen"
PAIRS = json.loads((FIXTURES / "catalogue.json").read_text())["pairs"]
GOLDENS = json.loads((FIXTURES / "goldens.json").read_text())["goldens"]


@pytest.mark.parametrize("pair", PAIRS, ids=lambda p: f'{p["target"]}-{p["template_id"]}')
def test_every_frozen_golden_passes_without_using_renderer_as_oracle(pair: dict) -> None:
    golden = next(
        g
        for g in GOLDENS
        if (g["target"], g["template_id"]) == (pair["target"], pair["template_id"])
    )
    source = (FIXTURES / golden["file"]).read_text()
    assert validate_source(decode_recipe(pair["example"]), source) == ()


FORBIDDEN = {
    "python": [
        "\nimport os\n",
        "\ncodegen_iterate_handles()\n",
        "\ndef extra():\n    pass\n",
        "\nclass Extra:\n    pass\n",
        '\nexec("synthetic")\n',
        '\neval("synthetic")\n',
        '\n__import__("socket")\n',
        '\nopen("synthetic", "w")\n',
    ],
    "autolisp": [
        '\n(command "synthetic")\n',
        "\n(eval (list 1.0))\n",
        '\n(load "synthetic")\n',
        "\n(vl-load-com)\n",
        '\n(vlax-invoke object \'SendCommand "synthetic")\n',
        "\n(defun c:Injected () (princ))\n",
        "\n(codegen_iterate_handles)\n",
    ],
    "vba": [
        '\nShell "synthetic"\n',
        '\nCreateObject("synthetic")\n',
        '\nThisDrawing.SendCommand "synthetic"\n',
        '\nApplication.Run "synthetic"\n',
        '\nOpen "synthetic" For Output As #1\n',
        "\nPublic Sub Auto_Open()\nEnd Sub\n",
        "\nCall CodegenIterateHandles\n",
    ],
}


@pytest.mark.parametrize(
    "target,attack", [(t, a) for t, values in FORBIDDEN.items() for a in values]
)
def test_extra_invocations_definitions_and_forbidden_sinks_fail(target: str, attack: str) -> None:
    recipe = decode_recipe(request(literals={"handles": ["ABC"]}, target=target))
    findings = validate_source(recipe, render_recipe(recipe) + attack)
    assert findings and all(f.severity == "error" for f in findings)
    assert all("synthetic" not in f.message and "Injected" not in f.message for f in findings)


@pytest.mark.parametrize("target", ["python", "autolisp", "vba"])
@pytest.mark.parametrize(
    "template", ["literal_geometry", "serialize_entity_facts", "iterate_handles"]
)
def test_changed_literal_data_never_passes_structure_alone(target: str, template: str) -> None:
    pair = next(p for p in PAIRS if (p["target"], p["template_id"]) == (target, template))
    recipe = decode_recipe(pair["example"])
    source = render_recipe(recipe)
    replacement = {
        "literal_geometry": ("1.0", "2.0"),
        "serialize_entity_facts": ("Entity", "Changed"),
        "iterate_handles": ('"ABC"', '"DEF"'),
    }[template]
    changed = source.replace(*replacement)
    assert changed != source and validate_source(recipe, changed)


@pytest.mark.parametrize(
    "change",
    [
        ("def codegen_iterate_handles():", 'def codegen_iterate_handles(x=open("synthetic")):'),
        ("def codegen_iterate_handles():", "@unknown\ndef codegen_iterate_handles():"),
        ("def codegen_iterate_handles():", "def codegen_iterate_handles(*args, **kwargs):"),
        ("for handle in handles:", 'for handle in getattr(handles, "synthetic"):'),
        ("last_handle = handle", "last_handle = handle.lower()"),
        ("return last_handle", "return eval(last_handle)"),
        ("return last_handle", "return last_handle.__class__"),
    ],
)
def test_python_receivers_arguments_annotations_and_loop_shapes_are_closed(change: tuple) -> None:
    recipe = decode_recipe(request(literals={"handles": ["ABC"]}))
    assert validate_source(recipe, render_recipe(recipe).replace(*change))


@pytest.mark.parametrize(
    "target,original,changed",
    [
        ("autolisp", "(setq last_handle handle)", "(setq last_handle (eval handle))"),
        ("autolisp", '(list\n    "ABC"', '(list\n    (load "ABC")'),
        ("vba", "last_handle = handle", "last_handle = Shell(handle)"),
        ("vba", 'handles(0) = "ABC"', 'handles(0) = Array("ABC", Shell("synthetic"))'),
        ("vba", "ReDim handles(0 To 0)", "ReDim handles(1 To 1)"),
        ("vba", "Dim handle As Variant", "Dim handle As Object"),
    ],
)
def test_nonpython_executable_tokens_are_checked_inside_the_function(
    target: str, original: str, changed: str
) -> None:
    recipe = decode_recipe(request(literals={"handles": ["ABC"]}, target=target))
    source = render_recipe(recipe)
    assert original in source and validate_source(recipe, source.replace(original, changed))


@pytest.mark.parametrize(
    "source",
    [None, 12, "(", "(" * 65536, "x" * 65537, "\ud800", "\0"],
    ids=["none", "number", "unclosed", "deep", "oversize", "surrogate", "nul"],
)
def test_malformed_or_excessive_source_is_fixed_redacted_error(source: object) -> None:
    findings = validate_source(decode_recipe(request()), source)  # type: ignore[arg-type]
    assert len(findings) == 1 and findings[0].severity == "error"


def test_python_boolean_cannot_replace_equal_numeric_geometry() -> None:
    pair = next(
        p for p in PAIRS if (p["target"], p["template_id"]) == ("python", "literal_geometry")
    )
    recipe = decode_recipe(pair["example"])
    assert validate_source(recipe, render_recipe(recipe).replace("1.0", "True"))


def test_python_assignment_collection_shape_cannot_drift_to_tuple() -> None:
    recipe = decode_recipe(request())
    source = render_recipe(recipe).replace("handles = [", "handles = (").replace("    ]", "    )")
    assert validate_source(recipe, source)


def test_python_nested_point_shape_cannot_drift_to_list() -> None:
    pair = next(
        p for p in PAIRS if (p["target"], p["template_id"]) == ("python", "literal_geometry")
    )
    recipe = decode_recipe(pair["example"])
    source = render_recipe(recipe).replace("(0.0, 0.0, 0.0)", "[0.0, 0.0, 0.0]")
    assert validate_source(recipe, source)


def test_python_unreviewed_escape_is_redacted_without_native_warning() -> None:
    recipe = decode_recipe(request(literals={"handles": ["ABC"]}))
    source = render_recipe(recipe).replace('"ABC"', '"private\\q"')
    with warnings.catch_warnings(record=True) as observed:
        warnings.simplefilter("always")
        findings = validate_source(recipe, source)
    assert findings and not observed
    assert all("private" not in finding.message for finding in findings)


def test_python_type_comments_are_not_silently_discarded() -> None:
    recipe = decode_recipe(request())
    source = render_recipe(recipe).replace(
        "last_handle = handle", "last_handle = handle # type: str"
    )
    assert validate_source(recipe, source)


@pytest.mark.parametrize(
    "old,new",
    [
        ("1.0 -2.0", "1.0-2.0"),
        ("-2.0 3.0", "-2.03.0"),
        ("(/ lines circles)", "(/lines circles)"),
        ("lines circles", "linescircles"),
    ],
)
def test_autolisp_joined_atoms_cannot_be_split_into_reviewed_tokens(old: str, new: str) -> None:
    recipe = decode_recipe(
        request(
            "literal_geometry",
            {
                "lines": [{"start": [1, -2, 3], "end": [4, 5, 6]}],
                "circles": [],
            },
            target="autolisp",
        )
    )
    source = render_recipe(recipe)
    changed = source.replace(old, new)
    assert changed != source
    findings = validate_source(recipe, changed)
    assert findings and findings[0].severity == "error"
