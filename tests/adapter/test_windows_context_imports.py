"""Import the extension without loading or attaching any COM dependency."""

import subprocess
import sys


def test_windows_context_import_does_not_load_com_or_native_transport():
    script = """
import sys
import autocad_mcp.adapter.windows_context
assert not {'pythoncom','win32com','win32com.client','pyautocad',
            'autocad_mcp.adapter.native_revision_windows'} & set(sys.modules)
"""
    result = subprocess.run(  # noqa: S603 - fixed interpreter and literal test probe
        [sys.executable, "-c", script], capture_output=True, text=True, check=False
    )  # noqa: S603 - fixed literal import probe
    assert result.returncode == 0, result.stderr
