"""Single-writer local case persistence; workflow and authorization stay in engines."""

from __future__ import annotations

from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime, timezone
import errno
import hashlib
import json
import logging
import msvcrt
import os
from pathlib import Path
import stat
import tempfile
from typing import Any, Iterator

from jsonschema import Draft202012Validator
from tools.contracts.validate import SCHEMA, assert_run_context_unchanged, validate_contract

LOGGER = logging.getLogger(__name__)


class StoreError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def canonical_bytes(value: dict[str, Any]) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n"
    ).encode("utf-8")


def seal(value: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(value)
    result.pop("stateChecksum", None)
    result["stateChecksum"] = "sha256:" + hashlib.sha256(canonical_bytes(result)).hexdigest()
    return result


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise StoreError("invalid-artifact", f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise StoreError("invalid-artifact", f"Non-finite JSON value: {value}")


def _reject_reparse(path: Path) -> None:
    if path.exists() or path.is_symlink():
        info = path.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            raise StoreError("workspace-conflict", "Reparse points are not supported")


def _identifier(value: str, definition: str) -> None:
    Draft202012Validator(SCHEMA["definitions"][definition]).validate(value)


def _read(path: Path, contract: str | None = None) -> dict[str, Any]:
    _reject_reparse(path)
    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
    except (json.JSONDecodeError, UnicodeError) as error:
        raise StoreError("invalid-artifact", "Stored JSON is malformed") from error
    if not isinstance(value, dict):
        raise StoreError("invalid-artifact", "Stored artifact must be an object")
    if contract:
        validate_contract(value, contract)
    if value.get("stateChecksum") != seal(value)["stateChecksum"]:
        raise StoreError("invalid-artifact", "Stored artifact checksum does not match")
    return value


class CaseStore:
    """Accepts trusted server-configured roots, never browser-selected destinations."""

    def __init__(self, root: Path) -> None:
        root = root.absolute()
        for parent in (*reversed(root.parents), root):
            _reject_reparse(parent)
        root.mkdir(parents=True, exist_ok=True)
        self.root = root.resolve(strict=True)

    def _path(self, run_id: str, *parts: str) -> Path:
        _identifier(run_id, "RunId")
        path = self.root / run_id
        _reject_reparse(path)
        for part in parts:
            path = path / part
            _reject_reparse(path)
        return path

    @contextmanager
    def _lock(self, directory: Path) -> Iterator[None]:
        lock_path = directory / "writer.lock"
        _reject_reparse(lock_path)
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
                raise StoreError("workspace-conflict", "Another writer is active") from error
            try:
                yield
            finally:
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)

    def _replace(self, destination: Path, payload: bytes) -> None:
        _reject_reparse(destination)
        descriptor, name = tempfile.mkstemp(
            prefix=f"{destination.stem}-", suffix=".tmp", dir=destination.parent
        )
        temporary = Path(name)
        try:
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, destination)
        finally:
            temporary.unlink(missing_ok=True)

    def create_run(self, manifest: dict[str, Any]) -> dict[str, Any]:
        stored = seal(manifest)
        validate_contract(stored, "D22")
        directory = self._path(stored["runId"])
        try:
            directory.mkdir()
        except FileExistsError as error:
            raise StoreError("workspace-conflict", "Run already exists; mode cannot be changed") from error
        self._replace(directory / "run-manifest.json", canonical_bytes(stored))
        return deepcopy(stored)

    def read_run(self, run_id: str) -> dict[str, Any]:
        manifest = _read(self._path(run_id, "run-manifest.json"), "D22")
        if manifest["runId"] != run_id:
            raise StoreError("invalid-artifact", "Run identity does not match its directory")
        return manifest

    def check_run_context(self, run_id: str, proposed: dict[str, Any]) -> None:
        try:
            assert_run_context_unchanged(self.read_run(run_id), proposed)
        except ValueError as error:
            raise StoreError("not-authorized", str(error)) from error

    def _case_directory(self, manifest: dict[str, Any]) -> Path:
        _identifier(manifest["caseId"], "CaseId")
        return self._path(manifest["runId"], "cases", manifest["caseId"])

    @staticmethod
    def _bound(case: dict[str, Any], manifest: dict[str, Any]) -> None:
        for field in ("runId", "caseId", "scope"):
            if case[field] != manifest[field]:
                raise StoreError("invalid-artifact", f"Case {field} does not match run context")
        if case["derivedFrom"].get("runManifest") != manifest["stateChecksum"]:
            raise StoreError("invalid-artifact", "Case is not bound to this immutable run")

    def create_case(self, run_id: str) -> dict[str, Any]:
        manifest = self.read_run(run_id)
        directory = self._case_directory(manifest)
        directory.mkdir(parents=True, exist_ok=True)
        now = datetime.now(timezone.utc).isoformat()
        case = seal({
            "schemaVersion": "1.0.0",
            "artifactType": "case-state",
            "artifactId": "ART-CASE-STATE",
            "runId": run_id,
            "caseId": manifest["caseId"],
            "scope": deepcopy(manifest["scope"]),
            "logicalRevision": 0,
            "caseRevisionAtWrite": 0,
            "createdAt": now,
            "updatedAt": now,
            "derivedFrom": {"runManifest": manifest["stateChecksum"]},
            "lifecycleState": "Draft",
            "sections": {},
            "work": [],
            "events": [],
            "idempotencyRecords": [],
        })
        validate_contract(case, "D01")
        with self._lock(directory):
            destination = directory / "case.json"
            if destination.exists():
                raise StoreError("workspace-conflict", "Case already exists")
            self._replace(destination, canonical_bytes(case))
        return deepcopy(case)

    def read_case(self, run_id: str) -> dict[str, Any]:
        manifest = self.read_run(run_id)
        case = _read(self._case_directory(manifest) / "case.json", "D01")
        self._bound(case, manifest)
        return case

    def commit(
        self,
        run_id: str,
        expected_revision: int,
        proposed_case: dict[str, Any],
    ) -> dict[str, Any]:
        if type(expected_revision) is not int or expected_revision < 0:
            raise StoreError("stale-revision", "Expected revision must be a nonnegative integer")
        manifest = self.read_run(run_id)
        directory = self._case_directory(manifest)
        with self._lock(directory):
            current = self.read_case(run_id)
            if current["logicalRevision"] != expected_revision:
                raise StoreError("stale-revision", "Reload the current case before committing")
            candidate = deepcopy(proposed_case)
            validate_contract(candidate, "D01")
            self._bound(candidate, manifest)
            if candidate["artifactId"] != current["artifactId"]:
                raise StoreError("invalid-artifact", "Case artifact identity cannot change")
            candidate["logicalRevision"] = expected_revision + 1
            candidate["caseRevisionAtWrite"] = expected_revision + 1
            candidate["createdAt"] = current["createdAt"]
            candidate["updatedAt"] = datetime.now(timezone.utc).isoformat()
            candidate = seal(candidate)
            validate_contract(candidate, "D01")
            for reference in candidate["sections"].values():
                self.read_artifact(run_id, reference)
            self._replace(directory / "case.json", canonical_bytes(candidate))
            self._project_events(directory, candidate)
            return deepcopy(candidate)

    def _project_events(self, directory: Path, case: dict[str, Any]) -> None:
        payload = b"".join(canonical_bytes(event) for event in case["events"])
        try:
            self._replace(directory / "events.ndjson", payload)
        except (OSError, StoreError) as error:
            LOGGER.warning(
                "event-projection-unavailable: canonical revision %s committed; "
                "rebuild projection: %s",
                case["logicalRevision"],
                error,
            )

    def rebuild_event_projection(self, run_id: str) -> None:
        manifest = self.read_run(run_id)
        directory = self._case_directory(manifest)
        with self._lock(directory):
            self._project_events(directory, self.read_case(run_id))

    def put_artifact(self, run_id: str, artifact: dict[str, Any]) -> dict[str, str]:
        manifest = self.read_run(run_id)
        _identifier(artifact.get("artifactId"), "Identifier")
        stored = seal(artifact)
        for field in ("runId", "caseId", "scope"):
            if stored.get(field) != manifest[field]:
                raise StoreError("invalid-artifact", f"Artifact {field} does not match run context")
        digest = stored["stateChecksum"].split(":", 1)[1]
        directory = self._path(run_id, "artifacts")
        directory.mkdir(exist_ok=True)
        destination = self._path(run_id, "artifacts", digest + ".json")
        payload = canonical_bytes(stored)
        try:
            with destination.open("xb") as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
        except FileExistsError:
            if destination.read_bytes() != payload:
                raise StoreError("invalid-artifact", "Existing immutable artifact bytes differ")
        return {"artifactId": stored["artifactId"], "checksum": stored["stateChecksum"]}

    def read_artifact(self, run_id: str, reference: dict[str, str]) -> dict[str, Any]:
        _identifier(reference["artifactId"], "Identifier")
        _identifier(reference["checksum"], "Checksum")
        digest = reference["checksum"].split(":", 1)[1]
        artifact = _read(self._path(run_id, "artifacts", digest + ".json"))
        if (
            artifact.get("artifactId") != reference["artifactId"]
            or artifact["stateChecksum"] != reference["checksum"]
        ):
            raise StoreError("invalid-artifact", "Artifact reference does not match persisted content")
        manifest = self.read_run(run_id)
        for field in ("runId", "caseId", "scope"):
            if artifact.get(field) != manifest[field]:
                raise StoreError("invalid-artifact", "Artifact belongs to a different run context")
        return artifact
