"""Portable checks for bounded readiness and cleanup of the owned fake-host child."""

import importlib
import subprocess
import sys
import time

import pytest


def harness():
    try:
        return importlib.import_module("tests.windows.native_pipe_harness")
    except ModuleNotFoundError:
        pytest.fail("Bounded fake-host lifecycle helper is not implemented")


def child(script):
    return subprocess.Popen(  # noqa: S603 - fixed test-only Python fixture scripts
        [sys.executable, "-u", "-c", script],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def test_ready_metadata_is_read_without_waiting_for_process_exit():
    api = harness()
    process = child('print(\'{"hwnd":1,"pipe":"synthetic"}\', flush=True); input()')
    try:
        assert api.read_ready(process, timeout=1) == {"hwnd": 1, "pipe": "synthetic"}
        assert process.poll() is None
    finally:
        api.stop_owned_process(process, timeout=1)
    assert process.poll() == 0


def test_readiness_timeout_is_bounded_and_unresponsive_child_is_reaped():
    api = harness()
    process = child("import time; time.sleep(60)")
    began = time.monotonic()
    try:
        with pytest.raises(TimeoutError):
            api.read_ready(process, timeout=0.1)
        assert time.monotonic() - began < 1
    finally:
        api.stop_owned_process(process, timeout=0.1)
    assert process.poll() is not None
    assert process.wait(timeout=0.1) == process.returncode


def test_malformed_readiness_still_allows_cleanup():
    api = harness()
    process = child('print("not-json", flush=True); input()')
    try:
        with pytest.raises(ValueError):
            api.read_ready(process, timeout=1)
    finally:
        api.stop_owned_process(process, timeout=1)
    assert process.poll() is not None


def test_cleanup_escalates_from_terminate_to_kill_and_reaps():
    api = harness()

    class Stubborn:
        stdin = None
        stdout = None
        stderr = None
        returncode = None
        actions = []

        def communicate(self, timeout):
            self.actions.append(("communicate", timeout))
            if "kill" not in self.actions:
                raise subprocess.TimeoutExpired("fixed child", timeout)
            self.returncode = -9
            return "", ""

        def poll(self):
            return self.returncode

        def terminate(self):
            self.actions.append("terminate")

        def kill(self):
            self.actions.append("kill")

        def wait(self, timeout=None):
            self.actions.append("wait")
            self.returncode = -9
            return -9

    process = Stubborn()
    api.stop_owned_process(process, timeout=0.1)
    assert (
        "terminate" in process.actions and "kill" in process.actions and "wait" in process.actions
    )
