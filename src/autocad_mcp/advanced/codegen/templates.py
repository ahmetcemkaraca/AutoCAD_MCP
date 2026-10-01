"""Nine fixed version-one function definitions; no invocation or command entry."""

from types import MappingProxyType
from typing import Final

from .models import CodeTarget

TEMPLATES: Final = MappingProxyType(
    {
        (CodeTarget.PYTHON, "literal_geometry"): (
            "def codegen_geometry():\n{lines}{circles}    return lines, circles\n"
        ),
        (CodeTarget.PYTHON, "serialize_entity_facts"): (
            'def codegen_facts():\n    facts_json = ""\n{facts}    return facts_json\n'
        ),
        (CodeTarget.PYTHON, "iterate_handles"): (
            'def codegen_iterate_handles():\n{handles}    last_handle = ""\n'
            "    for handle in handles:\n        last_handle = handle\n    return last_handle\n"
        ),
        (CodeTarget.AUTOLISP, "literal_geometry"): (
            "(defun codegen_geometry (/ lines circles)\n{lines}{circles}  (list lines circles)\n)\n"
        ),
        (CodeTarget.AUTOLISP, "serialize_entity_facts"): (
            '(defun codegen_facts (/ facts_json)\n  (setq facts_json "")\n{facts}  facts_json\n)\n'
        ),
        (CodeTarget.AUTOLISP, "iterate_handles"): (
            "(defun codegen_iterate_handles (/ handles handle last_handle)\n{handles}"
            '  (setq last_handle "")\n  (foreach handle handles\n'
            "    (setq last_handle handle)\n  )\n  last_handle\n)\n"
        ),
        (CodeTarget.VBA, "literal_geometry"): (
            "Option Explicit\nOption Base 0\n\nPublic Function CodegenGeometry() As Variant\n"
            "    Dim lines As Variant\n    Dim circles As Variant\n{lines}{circles}"
            "    CodegenGeometry = Array(lines, circles)\nEnd Function\n"
        ),
        (CodeTarget.VBA, "serialize_entity_facts"): (
            "Option Explicit\nOption Base 0\n\nPublic Function CodegenFacts() As String\n"
            '    Dim facts_json As String\n    facts_json = ""\n{facts}'
            "    CodegenFacts = facts_json\nEnd Function\n"
        ),
        (CodeTarget.VBA, "iterate_handles"): (
            "Option Explicit\nOption Base 0\n\nPublic Function CodegenIterateHandles() As String\n"
            "    Dim handles As Variant\n    Dim handle As Variant\n    Dim last_handle As String\n"
            '{handles}    last_handle = ""\n    For Each handle In handles\n'
            "        last_handle = handle\n    Next handle\n"
            "    CodegenIterateHandles = last_handle\nEnd Function\n"
        ),
    }
)
