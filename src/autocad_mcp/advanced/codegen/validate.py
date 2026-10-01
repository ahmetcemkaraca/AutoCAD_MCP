"""Independent bounded AST/structure validation; generated text is never evaluated."""

import ast
import io
import json
import math
import re
import tokenize
from typing import Any, cast

from .models import MAX_ARTIFACT_BYTES, CodeRecipe, CodeTarget, StaticFinding, recipe_payload

type Token = tuple[str, str]


def _require(condition: bool) -> None:
    if not condition:
        raise ValueError("Unreviewed source")


def _name(node: ast.AST | None, name: str) -> bool:
    return isinstance(node, ast.Name) and node.id == name


def _assignment(node: ast.stmt, name: str) -> ast.expr:
    if not isinstance(node, ast.Assign) or len(node.targets) != 1:
        raise ValueError("Unreviewed assignment")
    _require(_name(node.targets[0], name) and node.type_comment is None)
    return node.value


def _python_literal(node: ast.AST, *, collection: bool = False) -> Any:
    if collection:
        _require(isinstance(node, ast.List))
        return [_python_literal(item) for item in cast(ast.List, node).elts]
    if isinstance(node, ast.Constant) and type(node.value) in (str, float):
        if type(node.value) is float:
            _require(math.isfinite(node.value))
        return node.value
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        _require(isinstance(node.operand, ast.Constant) and type(node.operand.value) is float)
        return -_python_literal(node.operand)
    if isinstance(node, ast.Tuple):
        return [_python_literal(item) for item in node.elts]
    raise ValueError("Unreviewed literal")


def _python(recipe: CodeRecipe, source: str) -> Any:
    # Reject non-reviewed string escapes before AST parsing can emit native diagnostics.
    allowed = {
        tokenize.NAME,
        tokenize.NUMBER,
        tokenize.STRING,
        tokenize.OP,
        tokenize.NEWLINE,
        tokenize.NL,
        tokenize.INDENT,
        tokenize.DEDENT,
        tokenize.COMMENT,
        tokenize.ENDMARKER,
    }
    for token in tokenize.generate_tokens(io.StringIO(source).readline):
        _require(token.type in allowed)
        if token.type == tokenize.STRING:
            _require(re.fullmatch(r'"(?:\\["\\]|[^"\\\r\n])*"', token.string) is not None)
    module = ast.parse(source, type_comments=True)
    _require(len(module.body) == 1 and not module.type_ignores)
    function = module.body[0]
    if not isinstance(function, ast.FunctionDef):
        raise ValueError("Unreviewed function")
    names = {
        "literal_geometry": "codegen_geometry",
        "serialize_entity_facts": "codegen_facts",
        "iterate_handles": "codegen_iterate_handles",
    }
    args = function.args
    _require(
        function.name == names[recipe.template_id]
        and not function.decorator_list
        and function.returns is None
        and function.type_comment is None
        and not function.type_params
        and not args.posonlyargs
        and not args.args
        and args.vararg is None
        and not args.kwonlyargs
        and not args.kw_defaults
        and args.kwarg is None
        and not args.defaults
    )
    body = function.body
    _require(bool(body) and isinstance(body[-1], ast.Return))
    last = cast(ast.Return, body[-1])
    if recipe.template_id == "literal_geometry":
        _require(
            len(body) == 3
            and isinstance(last.value, ast.Tuple)
            and len(last.value.elts) == 2
            and _name(last.value.elts[0], "lines")
            and _name(last.value.elts[1], "circles")
        )
        return {
            name: _python_literal(_assignment(node, name), collection=True)
            for name, node in zip(("lines", "circles"), body[:2], strict=True)
        }
    if recipe.template_id == "iterate_handles":
        _require(len(body) == 4 and _name(last.value, "last_handle"))
        handles = _python_literal(_assignment(body[0], "handles"), collection=True)
        _require(_python_literal(_assignment(body[1], "last_handle")) == "")
        loop = body[2]
        if not isinstance(loop, ast.For):
            raise ValueError("Unreviewed loop")
        _require(
            _name(loop.target, "handle")
            and _name(loop.iter, "handles")
            and not loop.orelse
            and loop.type_comment is None
            and len(loop.body) == 1
        )
        _require(_name(_assignment(loop.body[0], "last_handle"), "handle"))
        return handles
    _require(
        len(body) >= 3
        and _name(last.value, "facts_json")
        and _python_literal(_assignment(body[0], "facts_json")) == ""
    )
    chunks = []
    for node in body[1:-1]:
        value = _assignment(node, "facts_json")
        if not isinstance(value, ast.BinOp):
            raise ValueError("Unreviewed concatenation")
        _require(isinstance(value.op, ast.Add) and _name(value.left, "facts_json"))
        chunk = _python_literal(value.right)
        _require(type(chunk) is str and 1 <= len(chunk) <= 256)
        chunks.append(chunk)
    return "".join(chunks)


def _tokens(source: str, *, vba: bool) -> list[Token]:
    string = r'"(?:[^"\r\n]|"")*"' if vba else r'"(?:\\["\\]|[^"\\\r\n])*"'
    real = r"-?\d+\.\d+(?:E[+-]?\d+)?#" if vba else r"-?\d+\.\d+(?:E[+-]?\d+)?"
    pattern = (
        f"(?P<string>{string})|(?P<real>{real})|(?P<integer>\\d+)"
        r"|(?P<symbol>[A-Za-z_][A-Za-z_0-9]*)|(?P<punct>[(),=/&])"
    )
    if not vba:
        # Parentheses/whitespace/quotes delimit Lisp atoms; slash and signs do not.
        pattern = f'(?P<string>{string})|(?P<punct>[()])|(?P<atom>[^() \\n"]+)'
    tokens: list[Token] = []
    cursor = 0
    for token in re.finditer(pattern, source):
        _require(not source[cursor : token.start()].strip(" \n"))
        if token.lastgroup is None:
            raise ValueError("Unreviewed token")
        kind, text = token.lastgroup, token.group()
        if kind == "atom":
            if re.fullmatch(real, text):
                kind = "real"
            elif re.fullmatch(r"\d+", text):
                kind = "integer"
            elif re.fullmatch(r"[A-Za-z_][A-Za-z_0-9]*", text):
                kind = "symbol"
            elif text == "/":
                kind = "punct"
            else:
                raise ValueError("Unreviewed atom")
        tokens.append((kind, text))
        cursor = token.end()
    _require(not source[cursor:].strip(" \n"))
    return tokens


def _primitive(token: Token, *, vba: bool) -> Any:
    kind, text = token
    if kind == "string":
        return text[1:-1].replace('""', '"') if vba else json.loads(text)
    _require(kind == "real")
    number = float(text[:-1] if vba else text)
    _require(math.isfinite(number))
    return number


def _lisp_form(tokens: list[Token], index: int = 0, depth: int = 0) -> tuple[Any, int]:
    _require(depth <= 12 and index < len(tokens))
    if tokens[index] != ("punct", "("):
        _require(tokens[index] != ("punct", ")"))
        return tokens[index], index + 1
    items = []
    index += 1
    while index < len(tokens) and tokens[index] != ("punct", ")"):
        item, index = _lisp_form(tokens, index, depth + 1)
        items.append(item)
    _require(index < len(tokens))
    return items, index + 1


def _lisp_data(value: Any) -> Any:
    if type(value) is list:
        _require(bool(value) and value[0] == ("symbol", "list"))
        return [_lisp_data(item) for item in value[1:]]
    return _primitive(value, vba=False)


def _lisp(recipe: CodeRecipe, source: str) -> Any:
    tokens = _tokens(source, vba=False)
    form, end = _lisp_form(tokens)
    _require(end == len(tokens) and type(form) is list and len(form) >= 4)

    def sym(name: str) -> Token:
        return "symbol", name

    names = {
        "literal_geometry": "codegen_geometry",
        "serialize_entity_facts": "codegen_facts",
        "iterate_handles": "codegen_iterate_handles",
    }
    locals_ = {
        "literal_geometry": ["lines", "circles"],
        "serialize_entity_facts": ["facts_json"],
        "iterate_handles": ["handles", "handle", "last_handle"],
    }
    _require(
        form[:2] == [sym("defun"), sym(names[recipe.template_id])]
        and form[2] == [("punct", "/"), *(sym(n) for n in locals_[recipe.template_id])]
    )
    body = form[3:]
    if recipe.template_id == "literal_geometry":
        _require(len(body) == 3 and body[-1] == [sym("list"), sym("lines"), sym("circles")])
        result = {}
        for name, assignment in zip(("lines", "circles"), body[:2], strict=True):
            _require(
                type(assignment) is list
                and len(assignment) == 3
                and assignment[:2] == [sym("setq"), sym(name)]
            )
            result[name] = _lisp_data(assignment[2])
        return result
    if recipe.template_id == "iterate_handles":
        _require(
            len(body) == 4
            and body[-1] == sym("last_handle")
            and body[1] == [sym("setq"), sym("last_handle"), ("string", '""')]
            and body[2]
            == [
                sym("foreach"),
                sym("handle"),
                sym("handles"),
                [sym("setq"), sym("last_handle"), sym("handle")],
            ]
        )
        _require(
            type(body[0]) is list
            and len(body[0]) == 3
            and body[0][:2] == [sym("setq"), sym("handles")]
        )
        return _lisp_data(body[0][2])
    _require(
        len(body) >= 3
        and body[0] == [sym("setq"), sym("facts_json"), ("string", '""')]
        and body[-1] == sym("facts_json")
    )
    chunks = []
    for assignment in body[1:-1]:
        _require(
            type(assignment) is list
            and len(assignment) == 3
            and assignment[:2] == [sym("setq"), sym("facts_json")]
        )
        concat = assignment[2]
        _require(
            type(concat) is list
            and len(concat) == 3
            and concat[:2] == [sym("strcat"), sym("facts_json")]
        )
        chunk = _primitive(concat[2], vba=False)
        _require(type(chunk) is str and 1 <= len(chunk) <= 256)
        chunks.append(chunk)
    return "".join(chunks)


def _vba_data(tokens: list[Token], index: int = 0, depth: int = 0) -> tuple[Any, int]:
    _require(depth <= 8 and index < len(tokens))
    if tokens[index] != ("symbol", "Array"):
        return _primitive(tokens[index], vba=True), index + 1
    _require(tokens[index : index + 2] == [("symbol", "Array"), ("punct", "(")])
    index += 2
    result = []
    _require(index < len(tokens))
    if tokens[index] != ("punct", ")"):
        while True:
            item, index = _vba_data(tokens, index, depth + 1)
            result.append(item)
            _require(index < len(tokens))
            if tokens[index] == ("punct", ")"):
                break
            _require(tokens[index] == ("punct", ","))
            index += 1
    return result, index + 1


def _vba_records(lines: list[str], index: int, name: str, maximum: int) -> tuple[list[Any], int]:
    _require(index < len(lines))
    if lines[index] == f"{name} = Array()":
        return [], index + 1
    dimension = re.fullmatch(r"ReDim ([a-z_]+)\(0 To (\d+)\)", lines[index])
    if dimension is None or dimension[1] != name:
        raise ValueError("Unreviewed dimension")
    count = int(dimension[2]) + 1
    _require(1 <= count <= maximum and index + count < len(lines))
    result = []
    for position in range(count):
        prefix = f"{name}({position}) = "
        line = lines[index + position + 1]
        _require(line.startswith(prefix))
        tokens = _tokens(line[len(prefix) :], vba=True)
        value, end = _vba_data(tokens)
        _require(end == len(tokens))
        result.append(value)
    return result, index + count + 1


def _vba(recipe: CodeRecipe, source: str) -> Any:
    _require(all(len(line) <= 1023 for line in source.splitlines()))
    lines = [line.strip() for line in source.splitlines() if line.strip()]
    names = {
        "literal_geometry": "CodegenGeometry",
        "serialize_entity_facts": "CodegenFacts",
        "iterate_handles": "CodegenIterateHandles",
    }
    name = names[recipe.template_id]
    return_type = "Variant" if recipe.template_id == "literal_geometry" else "String"
    _require(
        lines[:3]
        == ["Option Explicit", "Option Base 0", f"Public Function {name}() As {return_type}"]
        and lines[-1:] == ["End Function"]
    )
    if recipe.template_id == "literal_geometry":
        _require(lines[3:5] == ["Dim lines As Variant", "Dim circles As Variant"])
        first, index = _vba_records(lines, 5, "lines", 64)
        second, index = _vba_records(lines, index, "circles", 64)
        _require(lines[index:-1] == ["CodegenGeometry = Array(lines, circles)"])
        return {"lines": first, "circles": second}
    if recipe.template_id == "iterate_handles":
        _require(
            lines[3:6]
            == ["Dim handles As Variant", "Dim handle As Variant", "Dim last_handle As String"]
        )
        handles, index = _vba_records(lines, 6, "handles", 256)
        _require(
            lines[index:-1]
            == [
                'last_handle = ""',
                "For Each handle In handles",
                "last_handle = handle",
                "Next handle",
                "CodegenIterateHandles = last_handle",
            ]
        )
        return handles
    _require(
        lines[3:5] == ["Dim facts_json As String", 'facts_json = ""']
        and lines[-2:-1] == ["CodegenFacts = facts_json"]
        and len(lines) >= 8
    )
    chunks = []
    for line in lines[5:-2]:
        prefix = "facts_json = facts_json & "
        _require(line.startswith(prefix))
        tokens = _tokens(line[len(prefix) :], vba=True)
        _require(len(tokens) == 1 and tokens[0][0] == "string")
        chunk = _primitive(tokens[0], vba=True)
        _require(1 <= len(chunk) <= 256)
        chunks.append(chunk)
    return "".join(chunks)


def _compare(recipe: CodeRecipe, actual: Any) -> None:
    literals = cast(dict[str, Any], recipe_payload(recipe)["literals"])
    expected: Any
    if recipe.template_id == "serialize_entity_facts":
        _require(type(actual) is str)
        expected = json.dumps(
            literals["facts"],
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        # Canonical JSON comparison preserves scalar types and rejects duplicate keys/trailing data.
        _require(actual == expected)
        return
    if recipe.template_id == "iterate_handles":
        expected = literals["handles"]
    else:
        expected = {
            "lines": [[line["start"], line["end"]] for line in literals["lines"]],
            "circles": [[circle["center"], circle["radius"]] for circle in literals["circles"]],
        }
    _require(json.dumps(actual, allow_nan=False) == json.dumps(expected, allow_nan=False))


def validate_source(recipe: CodeRecipe, source: str) -> tuple[StaticFinding, ...]:
    """Admit only the reviewed local structure and exact supplied literal values."""
    try:
        _require(
            type(recipe) is CodeRecipe
            and type(source) is str
            and 0 < len(source) <= MAX_ARTIFACT_BYTES
        )
        _require(all(character == "\n" or 32 <= ord(character) <= 126 for character in source))
        reader = {CodeTarget.PYTHON: _python, CodeTarget.AUTOLISP: _lisp, CodeTarget.VBA: _vba}[
            recipe.target
        ]
        _compare(recipe, reader(recipe, source))
        return ()
    except (
        ValueError,
        TypeError,
        SyntaxError,
        IndexError,
        KeyError,
        AttributeError,
        RecursionError,
        tokenize.TokenError,
    ):
        return (
            StaticFinding(
                "SOURCE_POLICY",
                "error",
                "1:1",
                "Source is outside the reviewed literal-only structure",
            ),
        )
