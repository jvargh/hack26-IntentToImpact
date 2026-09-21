"""Bounded Windows file-safety experiment; not the production state store."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
import errno
import json
import msvcrt
import os
from pathlib import Path
import sys
import tempfile
from typing import Iterator


class WriterBusyError(RuntimeError):
    pass


class RevisionConflictError(RuntimeError):
    pass


def initialize(root: Path) -> None:
    if not root.is_dir():
        raise ValueError("Use an existing, explicitly owned spike directory")
    marker = root / "spike-root.json"
    with marker.open("x", encoding="utf-8") as stream:
        json.dump({"taskId": "SPK-02-01", "productionStore": False}, stream)


def require_spike_root(root: Path) -> Path:
    resolved = root.resolve(strict=True)
    marker = resolved / "spike-root.json"
    data = json.loads(marker.read_text(encoding="utf-8"))
    if data != {"taskId": "SPK-02-01", "productionStore": False}:
        raise ValueError("Directory is not an initialized SPK-02-01 test root")
    return resolved


@contextmanager
def writer_lock(root: Path) -> Iterator[None]:
    root = require_spike_root(root)
    lock_path = root / "writer.lock"
    with lock_path.open("a+b") as handle:
        handle.seek(0, os.SEEK_END)
        if handle.tell() == 0:
            handle.write(b"\0")
            handle.flush()
        handle.seek(0)
        try:
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError as error:
            if error.errno not in (errno.EACCES, errno.EAGAIN, errno.EDEADLK):
                raise
            raise WriterBusyError("Another writer owns this spike root") from error
        try:
            yield
        finally:
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)


def read_case(root: Path) -> dict[str, object]:
    root = require_spike_root(root)
    data = json.loads((root / "case.json").read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Case must be a JSON object")
    return data


def replace_case(
    root: Path,
    expected_revision: int | None,
    next_state: dict[str, object],
    *,
    interrupt_before_replace: bool = False,
) -> None:
    root = require_spike_root(root)
    if expected_revision is not None and (
        type(expected_revision) is not int or expected_revision < 1
    ):
        raise ValueError("Expected revision must be a positive integer or None")
    with writer_lock(root):
        destination = root / "case.json"
        if destination.exists():
            actual = read_case(root).get("logicalRevision")
            if actual != expected_revision:
                raise RevisionConflictError(
                    f"Expected revision {expected_revision}, found {actual}"
                )
        elif expected_revision is not None:
            raise RevisionConflictError("Case does not exist")
        next_revision = next_state.get("logicalRevision")
        required_revision = 1 if expected_revision is None else expected_revision + 1
        if type(next_revision) is not int or next_revision != required_revision:
            raise ValueError(f"Next logical revision must be {required_revision}")
        payload = (
            json.dumps(next_state, sort_keys=True, separators=(",", ":"), allow_nan=False)
            + "\n"
        ).encode("utf-8")
        descriptor, temporary_name = tempfile.mkstemp(
            prefix="case-", suffix=".tmp", dir=root
        )
        temporary_path = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            if interrupt_before_replace:
                # Deliberate process exit leaves a staged orphan, as a crash would.
                os._exit(23)
            os.replace(temporary_path, destination)
        finally:
            temporary_path.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("read", "interrupt-before-replace", "lock"))
    parser.add_argument("root", type=Path)
    arguments = parser.parse_args()
    try:
        if arguments.operation == "read":
            print(json.dumps(read_case(arguments.root), sort_keys=True))
        elif arguments.operation == "lock":
            with writer_lock(arguments.root):
                print("LOCKED", flush=True)
        else:
            current = read_case(arguments.root)
            revision = current.get("logicalRevision")
            if type(revision) is not int:
                raise ValueError("Current logical revision is invalid")
            replace_case(
                arguments.root,
                revision,
                {"logicalRevision": revision + 1, "status": "interrupted"},
                interrupt_before_replace=True,
            )
    except WriterBusyError as error:
        print(f"writer-busy: {error}", file=sys.stderr)
        return 7
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
