"""Platform-aware contracts for the real-AutoCAD controller lease."""

from __future__ import annotations

import dataclasses
import hashlib
import importlib
import inspect
import json
import os
import subprocess
import sys
import textwrap
import time
from pathlib import Path
from types import TracebackType
from typing import get_type_hints

import pytest


def _lease_module():
    return importlib.import_module("autocad_lease")


def _test_key(name: str) -> str:
    material = f"pytest-autocad-lease:{name}:{os.getpid()}:{time.time_ns()}"
    return hashlib.sha256(material.encode()).hexdigest()


def _start_owner(key: str, *, release: bool) -> subprocess.Popen[str]:
    module_directory = Path(__file__).parent
    script = textwrap.dedent(
        """
        import json
        import sys
        from autocad_lease import AutoCADLease

        lease = AutoCADLease.acquire(sys.argv[1])
        print(json.dumps({"owner": lease.evidence.owner.__dict__}), flush=True)
        if sys.argv[2] == "release":
            sys.stdin.readline()
            lease.release()
        else:
            sys.stdin.readline()
        """
    )
    return subprocess.Popen(  # noqa: S603 - fixed current interpreter and test-local script
        [sys.executable, "-c", script, key, "release" if release else "die"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=module_directory,
    )


def _await_owner(process: subprocess.Popen[str]) -> dict[str, object]:
    assert process.stdout is not None
    line = process.stdout.readline().strip()
    if not line:
        assert process.stderr is not None
        raise AssertionError(process.stderr.read())
    return json.loads(line)


def _stop_owner(process: subprocess.Popen[str], *, normal_release: bool) -> None:
    assert process.stdin is not None
    process.stdin.write("release\n")
    process.stdin.flush()
    process.wait(timeout=15)
    assert process.returncode == 0
    if normal_release:
        assert process.stderr is not None
        assert process.stderr.read() == ""


def test_import_does_not_eagerly_load_windows_modules() -> None:
    for name in ("autocad_lease", "msvcrt", "win32api", "win32security", "win32con"):
        sys.modules.pop(name, None)

    module = _lease_module()

    assert module.AutoCADLease is not None
    assert not {"msvcrt", "win32api", "win32security", "win32con"} & sys.modules.keys()


@pytest.mark.skipif(sys.platform == "win32", reason="non-Windows fail-closed contract")
def test_non_windows_lease_operations_fail_closed_without_raw_import_errors(tmp_path: Path) -> None:
    module = _lease_module()

    with pytest.raises(module.AutoCADLeaseUnavailableError, match="Windows"):
        module.build_autocad_lease_key(installation_path=tmp_path / "acad.exe")
    with pytest.raises(module.AutoCADLeaseUnavailableError, match="Windows"):
        module.AutoCADLease.acquire("trusted-key")
    with pytest.raises(module.AutoCADLeaseUnavailableError, match="Windows"):
        module.assert_current_user_system_only_acl(tmp_path)


def test_key_uses_only_injected_trusted_facts_without_public_override(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    module = _lease_module()
    monkeypatch.setattr(module, "_require_windows", lambda: None)
    facts = module._TrustedLeaseFacts(
        machine_identity="machine-guid",
        user_sid="S-1-5-21-100",
        windows_session_id=12,
        normalized_installation_path="C:\\Program Files\\Autodesk\\AutoCAD\\acad.exe",
        file_identity="volume=1;file=2;size=3",
        version_build="24.3.1.0",
    )
    monkeypatch.setattr(module, "_trusted_key_facts", lambda installation_path: facts)

    first = module.build_autocad_lease_key(installation_path=tmp_path / "ignored.exe")
    second = module.build_autocad_lease_key(installation_path=tmp_path / "different.exe")

    assert first == second
    assert len(first) == 64
    assert set(first) <= set("0123456789abcdef")
    for field, changed in (
        ("machine_identity", "other-machine-guid"),
        ("user_sid", "S-1-5-21-200"),
        ("windows_session_id", 13),
        ("normalized_installation_path", "C:\\Other\\acad.exe"),
        ("file_identity", "volume=4;file=5;size=6"),
        ("version_build", "24.3.2.0"),
    ):
        altered = dataclasses.replace(facts, **{field: changed})
        monkeypatch.setattr(
            module, "_trusted_key_facts", lambda installation_path, result=altered: result
        )
        assert module.build_autocad_lease_key(installation_path=tmp_path / "ignored.exe") != first
    assert list(inspect.signature(module.build_autocad_lease_key).parameters) == [
        "installation_path"
    ]
    assert dataclasses.is_dataclass(module.LeaseOwner)
    assert dataclasses.is_dataclass(module.LeaseEvidence)
    assert module.LeaseOwner.__dataclass_params__.frozen is True
    assert module.LeaseEvidence.__dataclass_params__.frozen is True


def test_public_owner_command_and_context_exit_contracts_are_frozen() -> None:
    module = _lease_module()

    assert get_type_hints(module.LeaseOwner)["command"] == tuple[str, ...]
    exit_hints = get_type_hints(module.AutoCADLease.__exit__)
    assert exit_hints["exc_type"] == type[BaseException] | None
    assert exit_hints["exc_value"] == BaseException | None
    assert exit_hints["traceback"] == TracebackType | None


def test_metadata_parser_normalizes_command_and_rejects_untrusted_shapes(tmp_path: Path) -> None:
    module = _lease_module()
    key = _test_key("metadata")
    metadata_path = tmp_path / key / "owner.json"
    metadata_path.parent.mkdir()
    owner = {
        "lease_key": key,
        "pid": 123,
        "process_created_at_100ns": 456,
        "user_sid": "S-1-5-21-100",
        "computer_name": "controller",
        "windows_session_id": 1,
        "acquired_at_utc": "2026-08-29T12:00:00.000000Z",
        "command": ["pytest", "tests/windows/test_autocad_lease.py"],
    }
    metadata_path.write_text(
        json.dumps({"owner": owner, "released_at_utc": None}), encoding="utf-8"
    )

    parsed, released_at = module._read_metadata(metadata_path, expected_lease_key=key)

    assert parsed.command == tuple(owner["command"])
    assert released_at is None
    for field, invalid in (
        ("pid", True),
        ("process_created_at_100ns", 0),
        ("user_sid", "not-a-sid"),
        ("computer_name", ""),
        ("windows_session_id", True),
        ("acquired_at_utc", "not-utc"),
        ("command", ["pytest", 1]),
    ):
        malformed = dict(owner)
        malformed[field] = invalid
        metadata_path.write_text(
            json.dumps({"owner": malformed, "released_at_utc": None}), encoding="utf-8"
        )
        with pytest.raises(module.AutoCADLeaseError, match="metadata is corrupt"):
            module._read_metadata(metadata_path, expected_lease_key=key)

    metadata_path.write_text(
        json.dumps({"owner": owner, "released_at_utc": "not-utc"}), encoding="utf-8"
    )
    with pytest.raises(module.AutoCADLeaseError, match="metadata is corrupt"):
        module._read_metadata(metadata_path, expected_lease_key=key)


def test_prior_owner_recovery_rejects_missing_live_and_indeterminate_states(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    module = _lease_module()
    key = _test_key("prior-owner")
    metadata_path = tmp_path / key / "owner.json"
    metadata_path.parent.mkdir()

    with pytest.raises(module.AutoCADLeaseError, match="unexpectedly missing"):
        module._recoverable_prior_owner(
            metadata_path, "S-1-5-21-100", expected_lease_key=key, missing_metadata_allowed=False
        )

    owner = module.LeaseOwner(
        lease_key=key,
        pid=123,
        process_created_at_100ns=456,
        user_sid="S-1-5-21-100",
        computer_name="controller",
        windows_session_id=1,
        acquired_at_utc="2026-08-29T12:00:00.000000Z",
        command=("pytest",),
    )
    metadata_path.write_text(
        json.dumps({"owner": dataclasses.asdict(owner), "released_at_utc": None}), encoding="utf-8"
    )
    monkeypatch.setattr(module, "_verify_acl", lambda path, sid: None)
    monkeypatch.setattr(module, "_owner_liveness", lambda prior: "live")
    with pytest.raises(module.AutoCADLeaseContendedError, match="cannot be stolen"):
        module._recoverable_prior_owner(
            metadata_path, "S-1-5-21-100", expected_lease_key=key, missing_metadata_allowed=False
        )
    monkeypatch.setattr(module, "_owner_liveness", lambda prior: "indeterminate")
    with pytest.raises(module.AutoCADLeaseError, match="indeterminate"):
        module._recoverable_prior_owner(
            metadata_path, "S-1-5-21-100", expected_lease_key=key, missing_metadata_allowed=False
        )
    monkeypatch.setattr(module, "_owner_liveness", lambda prior: "dead")
    assert (
        module._recoverable_prior_owner(
            metadata_path, "S-1-5-21-100", expected_lease_key=key, missing_metadata_allowed=False
        )
        == owner
    )


def test_acl_helpers_use_delayed_ntsecuritycon_and_do_not_repair_existing_paths() -> None:
    module = _lease_module()

    assert "ntsecuritycon" in inspect.getsource(module._set_private_acl)
    assert "DACL_SECURITY_INFORMATION" in inspect.getsource(module._verify_acl)
    assert "PROTECTED_DACL_SECURITY_INFORMATION" not in inspect.getsource(module._verify_acl)
    assert "exist_ok" not in inspect.getsource(module._create_private_directory)
    assert "O_EXCL" in inspect.getsource(module._create_private_file)


@pytest.mark.skipif(sys.platform != "win32", reason="requires Windows ACL APIs")
def test_new_private_temporary_directory_has_current_user_system_only_acl() -> None:
    module = _lease_module()
    directory = module.create_current_user_system_private_directory()
    try:
        module.assert_current_user_system_only_acl(directory)
    finally:
        directory.rmdir()


@pytest.mark.skipif(
    sys.platform != "win32", reason="requires Windows OS lock, ACL, and process APIs"
)
def test_same_key_is_exclusive_across_processes() -> None:
    module = _lease_module()
    key = _test_key("exclusive")
    owner = _start_owner(key, release=True)
    expected = _await_owner(owner)
    try:
        with pytest.raises(module.AutoCADLeaseContendedError) as raised:
            module.AutoCADLease.acquire(key)
        assert raised.value.owner is not None
        assert raised.value.owner.pid == expected["owner"]["pid"]
    finally:
        _stop_owner(owner, normal_release=True)


@pytest.mark.skipif(
    sys.platform != "win32", reason="requires Windows OS lock, ACL, and process APIs"
)
def test_release_records_evidence_and_allows_reacquire() -> None:
    module = _lease_module()
    key = _test_key("release")
    lease = module.AutoCADLease.acquire(key)
    released = lease.release()

    assert released.owner.lease_key == key
    assert released.released_at_utc is not None
    assert Path(released.metadata_path).is_file()
    reacquired = module.AutoCADLease.acquire(key)
    assert reacquired.evidence.stale_owner_recovered is None
    reacquired.release()


@pytest.mark.skipif(sys.platform != "win32", reason="requires Windows process creation-time API")
def test_live_owner_is_never_stolen() -> None:
    module = _lease_module()
    key = _test_key("live-owner")
    owner = _start_owner(key, release=True)
    expected = _await_owner(owner)
    try:
        with pytest.raises(module.AutoCADLeaseContendedError) as raised:
            module.AutoCADLease.acquire(key)
        assert raised.value.owner is not None
        assert (
            raised.value.owner.process_created_at_100ns
            == expected["owner"]["process_created_at_100ns"]
        )
    finally:
        _stop_owner(owner, normal_release=True)


@pytest.mark.skipif(sys.platform != "win32", reason="requires Windows process creation-time API")
def test_stale_owner_recovers_only_after_process_death() -> None:
    module = _lease_module()
    key = _test_key("stale")
    owner = _start_owner(key, release=False)
    expected = _await_owner(owner)
    _stop_owner(owner, normal_release=False)

    recovered = module.AutoCADLease.acquire(key)
    try:
        assert recovered.evidence.stale_owner_recovered is not None
        assert recovered.evidence.stale_owner_recovered.pid == expected["owner"]["pid"]
    finally:
        recovered.release()


@pytest.mark.skipif(sys.platform != "win32", reason="requires Windows ACL APIs")
def test_corrupt_or_unprotected_metadata_fails_closed() -> None:
    module = _lease_module()
    key = _test_key("corrupt")
    released = module.AutoCADLease.acquire(key).release()
    metadata_path = Path(released.metadata_path)
    metadata_path.write_text("not JSON", encoding="utf-8")
    with pytest.raises(module.AutoCADLeaseError, match="metadata is corrupt"):
        module.AutoCADLease.acquire(key)

    clean_key = _test_key("unprotected")
    clean = module.AutoCADLease.acquire(clean_key).release()
    win32security = importlib.import_module("win32security")
    descriptor = win32security.SECURITY_DESCRIPTOR()
    descriptor.SetSecurityDescriptorDacl(True, win32security.ACL(), False)
    win32security.SetFileSecurity(
        clean.metadata_path,
        win32security.DACL_SECURITY_INFORMATION | win32security.PROTECTED_DACL_SECURITY_INFORMATION,
        descriptor,
    )
    with pytest.raises(module.AutoCADLeaseError, match="ACL"):
        module.AutoCADLease.acquire(clean_key)


@pytest.mark.skipif(sys.platform != "win32", reason="requires Windows ACL APIs")
def test_lease_path_is_current_user_protected() -> None:
    module = _lease_module()
    lease = module.AutoCADLease.acquire(_test_key("acl"))
    try:
        module.assert_current_user_system_only_acl(Path(lease.evidence.metadata_path).parent)
        module.assert_current_user_system_only_acl(Path(lease.evidence.metadata_path))
    finally:
        lease.release()


@pytest.mark.skipif(sys.platform != "win32", reason="requires distinct real Windows sessions")
def test_distinct_real_windows_sessions_derive_distinct_keys() -> None:
    pytest.skip("requires this test command to run in two distinct interactive Windows sessions")
