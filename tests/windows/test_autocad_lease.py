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
from types import SimpleNamespace, TracebackType
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
    assert list(inspect.signature(module.AutoCADLease.__exit__).parameters) == [
        "self",
        "exc_type",
        "exc",
        "traceback",
    ]
    assert exit_hints["exc_type"] == type[BaseException] | None
    assert exit_hints["exc"] == BaseException | None
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

    bindings = module._OwnerBindings("S-1-5-21-100", "controller", 1)
    parsed, released_at = module._read_metadata(
        metadata_path, expected_lease_key=key, expected_bindings=bindings
    )

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
            module._read_metadata(
                metadata_path, expected_lease_key=key, expected_bindings=bindings
            )

    metadata_path.write_text(
        json.dumps({"owner": owner, "released_at_utc": "not-utc"}), encoding="utf-8"
    )
    with pytest.raises(module.AutoCADLeaseError, match="metadata is corrupt"):
        module._read_metadata(metadata_path, expected_lease_key=key, expected_bindings=bindings)

    for field, invalid in (
        ("lease_key", _test_key("wrong-key")),
        ("user_sid", "S-1-5-21-999"),
        ("computer_name", "other-controller"),
        ("windows_session_id", 2),
    ):
        mismatched = dict(owner)
        mismatched[field] = invalid
        metadata_path.write_text(
            json.dumps({"owner": mismatched, "released_at_utc": None}), encoding="utf-8"
        )
        with pytest.raises(module.AutoCADLeaseError, match="metadata is corrupt"):
            module._read_metadata(
                metadata_path, expected_lease_key=key, expected_bindings=bindings
            )


def test_prior_owner_recovery_rejects_missing_live_and_indeterminate_states(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    module = _lease_module()
    key = _test_key("prior-owner")
    metadata_path = tmp_path / key / "owner.json"
    metadata_path.parent.mkdir()
    bindings = module._OwnerBindings("S-1-5-21-100", "controller", 1)

    with pytest.raises(module.AutoCADLeaseError, match="unexpectedly missing"):
        module._recoverable_prior_owner(
            metadata_path, bindings, expected_lease_key=key, missing_metadata_allowed=False
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
    monkeypatch.setattr(module, "_verify_lease_acl", lambda path, sid: None)
    monkeypatch.setattr(module, "_owner_liveness", lambda prior: "live")
    with pytest.raises(module.AutoCADLeaseContendedError, match="cannot be stolen"):
        module._recoverable_prior_owner(
            metadata_path, bindings, expected_lease_key=key, missing_metadata_allowed=False
        )
    monkeypatch.setattr(module, "_owner_liveness", lambda prior: "indeterminate")
    with pytest.raises(module.AutoCADLeaseError, match="indeterminate"):
        module._recoverable_prior_owner(
            metadata_path, bindings, expected_lease_key=key, missing_metadata_allowed=False
        )
    monkeypatch.setattr(module, "_owner_liveness", lambda prior: "dead")
    assert (
        module._recoverable_prior_owner(
            metadata_path, bindings, expected_lease_key=key, missing_metadata_allowed=False
        )
        == owner
    )


def test_acl_helpers_use_delayed_ntsecuritycon_and_do_not_repair_existing_paths() -> None:
    module = _lease_module()

    assert "ntsecuritycon" in inspect.getsource(module._set_private_acl)
    assert "OWNER_SECURITY_INFORMATION" in inspect.getsource(module._verify_lease_acl)
    assert "DACL_SECURITY_INFORMATION" in inspect.getsource(module._verify_lease_acl)
    assert "PROTECTED_DACL_SECURITY_INFORMATION" not in inspect.getsource(module._verify_lease_acl)
    assert "exist_ok" not in inspect.getsource(module._create_private_directory)
    assert "O_EXCL" in inspect.getsource(module._create_private_file)
    assert inspect.getsource(module._set_private_acl).count("ace_flags,") == 2


def test_guard_acl_flag_rules_accept_effective_inherited_and_reject_inherit_only() -> None:
    module = _lease_module()

    assert module._guard_ace_is_effective(0, inherit_only_flag=8) is True
    assert module._guard_ace_is_effective(1 | 2 | 0x10, inherit_only_flag=8) is True
    assert module._guard_ace_is_effective(8, inherit_only_flag=8) is False


def test_new_path_acl_sets_current_user_owner_and_protected_dacl(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    module = _lease_module()
    calls: list[tuple[object, ...]] = []
    descriptor = SimpleNamespace(
        SetSecurityDescriptorOwner=lambda *args: calls.append(("owner", *args)),
        SetSecurityDescriptorDacl=lambda *args: None,
    )
    security = SimpleNamespace(
        ACL=lambda: SimpleNamespace(AddAccessAllowedAceEx=lambda *args: None),
        ACL_REVISION=2,
        ConvertStringSidToSid=lambda sid: sid,
        SECURITY_DESCRIPTOR=lambda: descriptor,
        OWNER_SECURITY_INFORMATION=1,
        DACL_SECURITY_INFORMATION=4,
        PROTECTED_DACL_SECURITY_INFORMATION=0x80000000,
        SetFileSecurity=lambda *args: calls.append(("set", *args)),
    )
    bindings = {
        "ntsecuritycon": SimpleNamespace(FILE_ALL_ACCESS=0x1F01FF),
        "win32security": security,
    }
    monkeypatch.setattr(module.importlib, "import_module", bindings.__getitem__)

    module._set_private_acl(tmp_path / "new", "S-1-5-21-100")

    assert calls == [
        ("owner", "S-1-5-21-100", False),
        ("set", str(tmp_path / "new"), 0x80000005, descriptor),
    ]


def test_existing_foreign_paths_are_rejected_without_repair(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    module = _lease_module()
    directory = tmp_path / "foreign-directory"
    directory.mkdir()
    file_path = tmp_path / "foreign-file"
    file_path.write_bytes(b"foreign evidence")
    repairs: list[object] = []
    monkeypatch.setattr(module, "_require_windows", lambda: None)
    monkeypatch.setattr(module, "_current_user_sid", lambda: "S-1-5-21-100")
    monkeypatch.setattr(module, "_set_private_acl", lambda *args, **kwargs: repairs.append(args))

    def reject_foreign_owner(path: Path, sid: str) -> None:
        raise module.AutoCADLeaseError("Windows lease path owner is not the current user")

    monkeypatch.setattr(module, "_verify_lease_acl", reject_foreign_owner)
    with pytest.raises(module.AutoCADLeaseError, match="owner"):
        module._create_private_directory(directory, "S-1-5-21-100")
    with pytest.raises(module.AutoCADLeaseError, match="owner"):
        module._create_private_file(file_path, "S-1-5-21-100")
    with pytest.raises(module.AutoCADLeaseError, match="already exists"):
        module.create_guard_run_directory(directory)
    assert repairs == []
    assert file_path.read_bytes() == b"foreign evidence"


def test_enter_unlocks_if_ownership_assertion_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _lease_module()
    lease = object.__new__(module.AutoCADLease)
    lease._owned = True
    lease._lock_file = object()
    monkeypatch.setattr(
        module.AutoCADLease,
        "assert_owned",
        lambda self: (_ for _ in ()).throw(module.AutoCADLeaseError("lost ownership")),
    )
    unlocked: list[object] = []
    monkeypatch.setattr(module, "_unlock_and_close", unlocked.append)

    with pytest.raises(module.AutoCADLeaseError, match="lost ownership"):
        lease.__enter__()

    assert lease._owned is False
    assert unlocked == [lease._lock_file]


def test_acquire_passes_current_bindings_to_prior_owner_recovery(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    module = _lease_module()
    key = _test_key("acquire-bindings")
    bindings = module._OwnerBindings("S-1-5-21-100", "controller", 1)
    owner = module.LeaseOwner(
        lease_key=key,
        pid=123,
        process_created_at_100ns=456,
        user_sid=bindings.user_sid,
        computer_name=bindings.computer_name,
        windows_session_id=bindings.windows_session_id,
        acquired_at_utc="2026-08-29T12:00:00.000000Z",
        command=("pytest",),
    )
    calls: list[tuple[object, ...]] = []

    def make_directory(path: Path, sid: str) -> bool:
        was_new = not path.exists()
        path.mkdir(exist_ok=True)
        return was_new

    monkeypatch.setattr(module, "_require_windows", lambda: None)
    monkeypatch.setattr(module, "_current_user_sid", lambda: bindings.user_sid)
    monkeypatch.setattr(module, "_computer_name", lambda: bindings.computer_name)
    monkeypatch.setattr(module, "_current_windows_session_id", lambda: bindings.windows_session_id)
    monkeypatch.setattr(module, "_lease_root", lambda: tmp_path / "verification-leases")
    monkeypatch.setattr(module, "_create_private_directory", make_directory)
    monkeypatch.setattr(
        module, "_create_private_file", lambda path, sid: (path.touch(exist_ok=True), False)[1]
    )
    monkeypatch.setattr(module, "_lock_nonblocking", lambda lock_file: None)
    monkeypatch.setattr(
        module,
        "_recoverable_prior_owner",
        lambda path, received_bindings, **kwargs: calls.append(
            (
                path,
                received_bindings,
                kwargs["expected_lease_key"],
                kwargs["missing_metadata_allowed"],
            )
        )
        or None,
    )
    monkeypatch.setattr(module, "_current_owner", lambda lease_key, received_bindings: owner)
    monkeypatch.setattr(module, "_write_metadata", lambda *args: None)

    lease = module.AutoCADLease.acquire(key)
    lease._lock_file.close()

    assert calls == [
        (
            tmp_path / "verification-leases" / key / "owner.json",
            bindings,
            key,
            True,
        )
    ]


def test_lease_root_uses_the_known_folder_api_not_an_environment_override() -> None:
    module = _lease_module()

    assert "LOCALAPPDATA" not in inspect.getsource(module._lease_root)
    assert "SHGetKnownFolderPath" in inspect.getsource(module._known_local_app_data)


@pytest.mark.skipif(
    sys.platform != "win32", reason="requires Windows temporary-directory and ACL APIs"
)
def test_guard_temp_root_and_task15_style_child_are_current_user_system_only() -> None:
    module = _lease_module()
    from drawing_copy_guard import DrawingCopyGuard

    directory = module.create_guard_run_temp_root()
    source = directory / "source.dwg"
    source.write_bytes(b"disposable fixture")
    guard = None
    try:
        module.assert_guard_run_current_user_system_acl(directory)
        guard = DrawingCopyGuard.prepare(
            source,
            temp_root=directory,
            create_run_directory=module.create_guard_run_directory,
        )
        module.assert_guard_run_current_user_system_acl(guard.copy_path.parent)
    finally:
        if guard is not None:
            guard.finalize(preserve=False, reason="ACL test completed")
        source.unlink()
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
