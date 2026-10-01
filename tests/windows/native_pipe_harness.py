"""Bounded lifecycle helpers for the owned native fake-host test process only."""

import json
import queue
import subprocess
import threading
from typing import Any


def read_ready(process: subprocess.Popen[str], *, timeout: float = 5.0) -> dict[str, Any]:
    output: queue.Queue[str] = queue.Queue(maxsize=1)
    if process.stdout is None:
        raise ValueError("fake-host stdout unavailable")
    stream = process.stdout
    threading.Thread(target=lambda: output.put(stream.readline(4096)), daemon=True).start()
    try:
        line = output.get(timeout=timeout)
    except queue.Empty:
        raise TimeoutError("fake-host readiness deadline exceeded") from None
    value = json.loads(line)
    if type(value) is not dict or set(value) != {"hwnd", "pipe"}:
        raise ValueError("invalid fake-host readiness metadata")
    return value


def stop_owned_process(process: subprocess.Popen[str], *, timeout: float = 10.0) -> tuple[str, str]:
    """Request shutdown, escalate on bounded waits, and always reap this owned child."""
    try:
        if process.stdin is not None:
            try:
                process.stdin.write("stop\n")
                process.stdin.flush()
            except (OSError, ValueError):
                pass
        try:
            return process.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            process.terminate()
            try:
                return process.communicate(timeout=timeout)
            except subprocess.TimeoutExpired:
                process.kill()
                return process.communicate(timeout=timeout)
    finally:
        if process.poll() is None:
            process.kill()
        process.wait()
        for stream in (process.stdin, process.stdout, process.stderr):
            if stream is not None:
                stream.close()
