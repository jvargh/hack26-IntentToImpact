"""Bounded jobs, ownership, immutable inputs/results and durable local receipts."""

import asyncio
import copy
import json
import os
import secrets
import io
import zipfile
from pathlib import Path

from .model_client import FoundryModelClient, now
from .generation_schema import response_format
from .design_changes import prepare_change
from .validation import (
    StudioFailure, digest, no_secrets, safe_token, source_ids, strict_json, validate,
    validate_analysis, validate_request, validate_review, ground_external_dependencies,
)

MAX_JOBS = 64
MAX_BYTES = 200 * 1024 * 1024
JOB_TIMEOUT = 300


def write_json(path, value, immutable=False):
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(value, ensure_ascii=True, indent=2, allow_nan=False)
    if immutable:
        with path.open("x", encoding="utf-8") as file:
            file.write(text)
            file.flush()
            os.fsync(file.fileno())
    else:
        pending = path.with_suffix(".pending")
        with pending.open("w", encoding="utf-8") as file:
            file.write(text)
            file.flush()
            os.fsync(file.fileno())
        pending.replace(path)


def read_json(path):
    return strict_json(path.read_bytes())


class StudioService:
    def __init__(self, root, model=None, bundle_builder=None, history_scope="session"):
        if history_scope not in {"session", "workspace"}:
            raise StudioFailure("invalid_history_scope", "History scope must be session or workspace.", 500)
        self.history_scope = history_scope
        self.root = Path(root).absolute()
        if self.root.resolve() != self.root or self.root.is_symlink():
            raise StudioFailure("unsafe_storage", "Studio storage must not be a symbolic link.", 500)
        self.root.mkdir(parents=True, exist_ok=True)
        self.model = model or FoundryModelClient()
        self.bundle_builder = bundle_builder
        self.jobs = {}
        self.result_jobs = {}
        self.idempotency = {}
        self.builds = {}
        self.tasks = set()
        self.lock = asyncio.Lock()
        self.build_lock = asyncio.Lock()
        self._recover()

    def _path(self, *parts):
        path = self.root.joinpath(*parts)
        if (
            not path.resolve().is_relative_to(self.root)
            or path.is_symlink()
            or any(parent.is_symlink() for parent in path.parents if parent.is_relative_to(self.root))
        ):
            raise StudioFailure("unsafe_storage", "Unsafe local storage path.", 500)
        return path

    def _recover(self):
        for folder in self._path("jobs").glob("*"):
            if folder.is_symlink() or not folder.is_dir():
                raise StudioFailure("recovery_corrupt", "Unexpected entry in local job storage. Preserve it and inspect the run directory before restarting.", 500)
            try:
                safe_token(folder.name)
                record = read_json(self._path("jobs", folder.name, "state.json"))
                validate("StudioJob", record["job"])
                if record["job"]["jobId"] != folder.name:
                    raise StudioFailure("recovery_corrupt", "Stored job identity does not match its directory.", 500)
                self.jobs[folder.name] = record
                result = record["job"]["result"]
                if result is not None:
                    saved = read_json(self._path("jobs", folder.name, "result.json"))
                    if saved != result or digest(saved) != record["resultHash"]:
                        raise ValueError("Result integrity failure")
                    self.result_jobs[saved["resultId"]] = folder.name
                self.idempotency[(record["owner"], record["key"])] = folder.name
            except (OSError, ValueError, KeyError, TypeError, StudioFailure) as exc:
                raise StudioFailure("recovery_corrupt", "Stored job data failed recovery validation. No records were discarded or retried; preserve local runs for inspection.", 500) from exc
        for record in self.jobs.values():
            try:
                self._verify_change_approval(record)
            except (OSError, ValueError, KeyError, TypeError, StudioFailure) as exc:
                raise StudioFailure("recovery_corrupt", "Stored design-change authorization failed recovery validation. Preserve the original run records; nothing was retried.", 500) from exc
        for record in self.jobs.values():
            if record["job"]["status"] in ("queued", "running"):
                self._fail(record, StudioFailure(
                    "recovery_needed", "Server stopped during this job. Remote completion is unknown; submit a new request explicitly.", 503, True
                ))
        for path in self._path("build-records").glob("*.json"):
            if path.is_symlink():
                raise StudioFailure("recovery_corrupt", "A build record cannot be a symbolic link.", 500)
            try:
                record = read_json(path)
                if record.get("result"):
                    validate("BuildResult", record["result"])
                elif not record.get("error"):
                    record["error"] = StudioFailure(
                        "recovery_needed", "Server stopped during package generation; completion is unknown.", 503
                    ).public()
                    write_json(path, record)
                self.builds[(record["owner"], record["key"])] = record
            except (OSError, ValueError, KeyError, TypeError, StudioFailure) as exc:
                raise StudioFailure("recovery_corrupt", "Stored build data failed recovery validation. No records were discarded or retried; preserve local runs for inspection.", 500) from exc

    def _capacity(self, reserve=0):
        total = 0
        for file in self.root.rglob("*"):
            if file.is_symlink():
                raise StudioFailure("unsafe_storage", "Symlinks are not allowed in studio storage.", 500)
            if file.is_file():
                total += file.stat().st_size
                if total + reserve >= MAX_BYTES:
                    raise StudioFailure("storage_limit", "Local studio storage is full. Archive local runs before creating more.", 429)

    def _persist(self, record):
        write_json(self._path("jobs", record["job"]["jobId"], "state.json"), record)

    def _event(self, record, stage, message):
        events = record["job"]["events"]
        if len(events) >= 60 and stage not in ("complete", "error"):
            return
        events.append({"sequence": len(events) + 1, "stage": stage, "message": message, "at": now()})
        self._persist(record)

    def _fail(self, record, failure):
        record["job"].update(status="failed", result=None, error=failure.public())
        self._event(record, "error", failure.message)

    def get_job(self, owner, job_id):
        safe_token(job_id)
        record = self.jobs.get(job_id)
        if not record or not self._visible(owner, record):
            raise StudioFailure("not_found", "Job not found.", 404)
        return copy.deepcopy(record["job"])

    def _visible(self, owner, record):
        return self.history_scope == "workspace" or record["owner"] == owner

    def _saved_inputs(self, record):
        job_id = record["job"]["jobId"]
        stored = read_json(self._path("jobs", job_id, "input.json"))
        request = stored["effective"]
        validate_request(request)
        if digest(request) != record["inputHash"] or digest(stored["request"]) != record["requestHash"]:
            raise StudioFailure("history_integrity", "Saved run inputs failed their recorded hash checks.", 500)
        self._verify_change_approval(record, stored)
        return {key: copy.deepcopy(request[key]) for key in ("title", "prompt", "documents", "refinement", "previousResultId")}

    def _change_parent(self, owner, result_id, *, enforce_visibility=True):
        if not enforce_visibility:
            prior_id = self.result_jobs.get(result_id)
            if not prior_id:
                raise StudioFailure("change_integrity", "The immutable authorization parent is missing.", 500)
            owner = self.jobs[prior_id]["owner"]
        previous = self.get_result(owner, result_id)
        prior = self.jobs[self.result_jobs[result_id]]
        saved = read_json(self._path("jobs", prior["job"]["jobId"], "result.json"))
        if saved != previous or digest(saved) != prior["resultHash"]:
            raise StudioFailure("history_integrity", "The selected parent result failed its immutable hash check.", 500)
        stored = read_json(self._path("jobs", prior["job"]["jobId"], "input.json"))
        validate_request(stored["effective"])
        validate_request(stored["request"])
        if digest(stored["effective"]) != prior["inputHash"] or digest(stored["request"]) != prior["requestHash"]:
            raise StudioFailure("history_integrity", "The selected parent sources failed their immutable hash checks.", 500)
        return previous, stored["effective"]

    def _verify_change_approval(self, record, stored=None):
        folder = ("jobs", record["job"]["jobId"])
        stored = stored if stored is not None else read_json(self._path(*folder, "input.json"))
        approval = record["job"].get("changeApproval")
        approval_path = self._path(*folder, "change-approval.json")
        targeted = "designChange" in stored["request"]
        if not targeted and approval is None and "changeApprovalHash" not in record and not approval_path.exists():
            return
        if not targeted or approval is None:
            raise StudioFailure("change_integrity", "Design-change request and authorization are inconsistent.", 500)
        validate("ChangeApproval", approval)
        if read_json(approval_path) != approval or digest(approval) != record["changeApprovalHash"]:
            raise StudioFailure("change_integrity", "Stored design-change authorization failed its immutable hash check.", 500)
        previous, original = self._change_parent(record["owner"], approval["baseResultId"], enforce_visibility=False)
        effective, expected = prepare_change(stored["request"], previous, approval["approvedAt"])
        if (
            expected != approval or effective != stored["effective"] or stored["previous"] != previous
            or digest(stored["request"]) != record["requestHash"] or digest(effective) != record["inputHash"]
            or effective["prompt"] != original["prompt"] or effective["documents"] != original["documents"]
        ):
            raise StudioFailure("change_integrity", "Design-change authorization is not bound to the saved request, sources and parent.", 500)

    def _run_builds(self, owner, result_id):
        if result_id is None:
            return []
        return [entry["result"] for entry in self.builds.values()
                if self._visible(owner, entry) and entry.get("result")
                and entry["result"]["resultId"] == result_id]

    def _run_summary(self, owner, record, inputs):
        job = record["job"]
        result = job["result"]
        result_id = result["resultId"] if result else None
        events = job["events"]
        return {
            "jobId": job["jobId"],
            "title": inputs["title"].strip() or (result["analysis"]["title"] if result else "Untitled run"),
            "status": job["status"],
            "createdAt": events[0]["at"] if events else "",
            "updatedAt": events[-1]["at"] if events else "",
            "documentCount": len(inputs["documents"]), "resultId": result_id,
            "previousResultId": inputs["previousResultId"],
            "compiledPackageCount": sum(build["status"] == "compiled" for build in self._run_builds(owner, result_id)),
            "error": copy.deepcopy(job["error"]),
        }

    def history(self, owner):
        rows = [self._run_summary(owner, record, self._saved_inputs(record))
                for record in self.jobs.values() if self._visible(owner, record)]
        rows.sort(key=lambda row: (row["createdAt"], row["jobId"]), reverse=True)
        value = {"scope": self.history_scope, "runs": rows}
        validate("RunHistory", value)
        return value

    def saved_run(self, owner, job_id):
        job = self.get_job(owner, job_id)
        record = self.jobs[job_id]
        inputs = self._saved_inputs(record)
        result_id = job["result"]["resultId"] if job["result"] else None
        value = {
            "scope": self.history_scope, "summary": self._run_summary(owner, record, inputs),
            "inputs": inputs, "job": job,
            "builds": [{key: build[key] for key in ("buildId", "resultId", "optionId", "status", "compilerVersion", "exitCode")}
                       for build in self._run_builds(owner, result_id)],
        }
        validate("SavedRun", value)
        return value

    def saved_build(self, owner, job_id, build_id):
        safe_token(build_id)
        run = self.saved_run(owner, job_id)
        if run["job"]["result"]:
            for build in self._run_builds(owner, run["job"]["result"]["resultId"]):
                if build["buildId"] == build_id:
                    return copy.deepcopy(build)
        raise StudioFailure("not_found", "Saved package was not found for this run.", 404)

    def export_run(self, owner, job_id):
        run = self.saved_run(owner, job_id)
        files = {
            "run.json": json.dumps({"summary": run["summary"], "job": run["job"]}, ensure_ascii=False, indent=2),
            "inputs.json": json.dumps(run["inputs"], ensure_ascii=False, indent=2),
            "packages.json": json.dumps(run["builds"], ensure_ascii=False, indent=2),
            "README.txt": (
                "Saved studio run, not a new inference or deployment.\n"
                "This archive includes original prompt and document text. Handle it as customer data.\n"
                "Authentication cookies, CSRF tokens and internal owner/idempotency records are excluded.\n"
                "Download compiled infrastructure packages separately from Run history.\n"
            ),
        }
        for index, document in enumerate(run["inputs"]["documents"], 1):
            files[f"documents/{index:02d}.txt"] = document["text"]
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for name, content in files.items():
                archive.writestr(name, content.encode("utf-8"))
        if stream.tell() > 20 * 1024 * 1024:
            raise StudioFailure("export_too_large", "The run archive exceeds the download limit.", 413)
        return stream.getvalue()

    def get_result(self, owner, result_id):
        safe_token(result_id)
        job_id = self.result_jobs.get(result_id)
        if not job_id:
            raise StudioFailure("not_found", "Result not found.", 404)
        job = self.get_job(owner, job_id)
        if job["status"] != "succeeded" or job["result"] is None:
            raise StudioFailure("not_found", "Completed result not found.", 404)
        return job["result"]

    async def submit(self, owner, request):
        validate_request(request)
        request = copy.deepcopy(request)
        fingerprint = digest(request)
        async with self.lock:
            lookup = (owner, request["idempotencyKey"])
            if lookup in self.idempotency:
                record = self.jobs[self.idempotency[lookup]]
                if record["requestHash"] != fingerprint:
                    raise StudioFailure("idempotency_conflict", "This idempotency key was already used with different input.", 409)
                self._verify_change_approval(record)
                return copy.deepcopy(record["job"])
            previous = None
            approval = None
            effective = copy.deepcopy(request)
            if request["previousResultId"]:
                if "designChange" in request:
                    previous, original = self._change_parent(owner, request["previousResultId"])
                else:
                    previous = self.get_result(owner, request["previousResultId"])
                    prior = self.jobs[self.result_jobs[previous["resultId"]]]
                    original = read_json(self._path("jobs", prior["job"]["jobId"], "input.json"))["effective"]
                if request["prompt"] != original["prompt"] or request["documents"] != original["documents"]:
                    raise StudioFailure("revision_source_conflict", "Refinements must retain the original prompt and documents; start a new analysis to replace sources.", 409)
                effective["prompt"], effective["documents"] = original["prompt"], original["documents"]
                if "designChange" in request:
                    effective, approval = prepare_change(request, previous, now())
            if any(record["job"]["status"] in ("queued", "running") for record in self.jobs.values()):
                raise StudioFailure("busy", "One live analysis is already running. Wait for completion before submitting another.", 429, True)
            if len(self.jobs) >= MAX_JOBS:
                raise StudioFailure("job_limit", "The local studio job limit has been reached. Archive runs before creating more.", 429)
            self._capacity(reserve=4 * 1024 * 1024)
            job_id = "job_" + secrets.token_hex(16)
            job = {"jobId": job_id, "status": "queued", "events": [], "result": None, "error": None}
            record = {
                "job": job, "owner": owner, "key": request["idempotencyKey"],
                "requestHash": fingerprint, "inputHash": digest(effective), "resultHash": None,
            }
            if approval is not None:
                job["changeApproval"] = approval
                record["changeApprovalHash"] = digest(approval)
                write_json(self._path("jobs", job_id, "change-approval.json"), approval, immutable=True)
            write_json(self._path("jobs", job_id, "input.json"),
                       {"request": request, "effective": effective, "previous": previous}, immutable=True)
            self.jobs[job_id] = record
            self.idempotency[lookup] = job_id
            self._event(record, "intake", "Input validated; consent recorded. Prompt, documents and results persist locally.")
            task = asyncio.create_task(self._execute(record, effective, previous))
            self.tasks.add(task)
            task.add_done_callback(self.tasks.discard)
            return copy.deepcopy(job)

    async def _execute(self, record, request, previous):
        receipts = []
        try:
            async with asyncio.timeout(JOB_TIMEOUT):
                record["job"]["status"] = "running"
                write_json(self._path("jobs", record["job"]["jobId"], "synthesis-response-format.json"),
                           response_format("ArchitectureAnalysis", request), immutable=True)
                self._event(record, "synthesis", "Calling the existing Foundry model for source-grounded architecture synthesis.")
                analysis, receipt = await self.model.generate(
                    "synthesis", request, previous=previous,
                    progress=lambda message: self._event(record, "synthesis", message),
                )
                validate("ModelReceipt", receipt)
                if receipt["role"] != "synthesis":
                    raise StudioFailure("invalid_receipt", "Synthesis receipt has the wrong role.", 502)
                receipts.append(receipt)
                write_json(self._path("jobs", record["job"]["jobId"], "synthesis-receipt.json"), receipt, immutable=True)
                no_secrets(analysis)
                write_json(self._path("jobs", record["job"]["jobId"], "synthesis-proposal.json"), analysis, immutable=True)
                analysis = ground_external_dependencies(analysis, request)
                validate_analysis(analysis, request)
                self._event(record, "assurance", "Synthesis validated. Starting a separate live, no-tools assurance call.")
                write_json(self._path("jobs", record["job"]["jobId"], "assurance-response-format.json"),
                           response_format("AssuranceReview", request), immutable=True)
                assurance, receipt = await self.model.generate(
                    "assurance", request, analysis=analysis, previous=previous,
                    progress=lambda message: self._event(record, "assurance", message),
                )
                validate("ModelReceipt", receipt)
                if receipt["role"] != "assurance" or receipt["responseId"] == receipts[0]["responseId"]:
                    raise StudioFailure("invalid_receipt", "Independent assurance requires its own response ID.", 502)
                receipts.append(receipt)
                write_json(self._path("jobs", record["job"]["jobId"], "assurance-receipt.json"), receipt, immutable=True)
                validate("AssuranceReview", assurance)
                no_secrets(assurance)
                validate_review(assurance["review"], source_ids(request))
                analysis = {**analysis, "review": assurance["review"]}
                validate_analysis(analysis, request)
                result = {
                    "resultId": "result_" + secrets.token_hex(16), "inputHash": record["inputHash"],
                    "createdAt": now(), "origin": "live-model", "analysis": analysis,
                    "modelReceipts": receipts,
                    "sources": [{"id": "prompt", "name": "Business prompt"}]
                    + [{"id": doc["id"], "name": doc["name"]} for doc in request["documents"]]
                    + ([{"id": "refinement", "name": "Refinement instruction"}] if request["refinement"].strip() else []),
                }
                validate("StudioResult", result)
                self._capacity()
                write_json(self._path("jobs", record["job"]["jobId"], "result.json"), result, immutable=True)
                record["resultHash"] = digest(result)
                record["job"].update(status="succeeded", result=result)
                self.result_jobs[result["resultId"]] = record["job"]["jobId"]
                self._event(record, "complete", "Two live model calls completed and validated. Proposal only; nothing deployed.")
        except asyncio.CancelledError:
            self._fail(record, StudioFailure("cancelled", "Server stopped; request was cancelled locally. Remote completion is unknown.", 503, True))
            raise
        except TimeoutError:
            self._fail(record, StudioFailure("job_timeout", "Job exceeded its 300-second deadline. No automatic retry.", 504, True))
        except StudioFailure as exc:
            receipt = getattr(exc, "receipt", None)
            if receipt:
                validate("ModelReceipt", receipt)
                write_json(self._path("jobs", record["job"]["jobId"], receipt["role"] + "-rejected-receipt.json"),
                           receipt, immutable=True)
            self._fail(record, exc)
        except Exception:
            self._fail(record, StudioFailure("internal_error", "The analysis failed safely; no generated result is available.", 500))

    async def shutdown(self):
        tasks = list(self.tasks)
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        for record in self.jobs.values():
            if record["job"]["status"] in ("queued", "running"):
                self._fail(record, StudioFailure(
                    "cancelled", "Server stopped before this job completed. Remote completion is unknown.", 503, True
                ))

    async def build(self, owner, request):
        validate("BuildRequest", request)
        safe_token(request["resultId"])
        fingerprint = digest(request)
        if self.build_lock.locked():
            raise StudioFailure("build_busy", "One infrastructure package is already being generated.", 429, True)
        async with self.build_lock:
            lookup = (owner, request["idempotencyKey"])
            if lookup in self.builds:
                record = self.builds[lookup]
                if fingerprint != record["requestHash"]:
                    raise StudioFailure("idempotency_conflict", "Build idempotency key was used with different input.", 409)
                if record.get("error"):
                    err = record["error"]
                    raise StudioFailure(err["code"], err["message"], 503, err["retryable"])
                return copy.deepcopy(record["result"])
            result = self.get_result(owner, request["resultId"])
            if request["optionId"] not in {item["id"] for item in result["analysis"]["options"]}:
                raise StudioFailure("invalid_option", "Selected option does not belong to this result.", 422)
            if len(self.builds) >= MAX_JOBS:
                raise StudioFailure("build_limit", "The local package limit has been reached.", 429)
            self._capacity(reserve=24 * 1024 * 1024)
            record = {"owner": owner, "key": request["idempotencyKey"], "requestHash": fingerprint,
                      "result": None, "error": None}
            record_path = self._path("build-records", digest([owner, request["idempotencyKey"]]) + ".json")
            self.builds[lookup] = record
            write_json(record_path, record, immutable=True)
            try:
                builder = self.bundle_builder
                if builder is None:
                    try:
                        from .bundle import build_bundle
                    except ImportError:
                        raise StudioFailure("build_unavailable", "The infrastructure package generator is not installed yet.", 503, True) from None
                    builder = build_bundle
                try:
                    async with asyncio.timeout(120):
                        bundle = await asyncio.to_thread(builder, result, request["optionId"], self._path("builds"))
                except TimeoutError:
                    raise StudioFailure("build_timeout", "Package generation exceeded 120 seconds; local compiler completion is unknown. No automatic retry.", 504) from None
                validate("BuildResult", bundle)
                no_secrets(bundle)
                safe_token(bundle["buildId"])
                if bundle["resultId"] != result["resultId"] or bundle["optionId"] != request["optionId"]:
                    raise StudioFailure("invalid_build", "Generator returned a mismatched result or option.", 502)
                expected = f"/api/studio/builds/{bundle['buildId']}/download"
                if bundle["downloadUrl"] not in (None, expected):
                    raise StudioFailure("invalid_build", "Generator returned an unsafe download path.", 502)
                if bundle["status"] == "compiled":
                    if (bundle["exitCode"] != 0 or not bundle["compilerVersion"]
                            or bundle["downloadUrl"] != expected
                            or not any(file["path"] == "main.bicep" for file in bundle["files"])):
                        raise StudioFailure("invalid_build", "Compiled status requires successful compiler evidence and a Bicep package.", 502)
                elif bundle["downloadUrl"] is not None:
                    raise StudioFailure("invalid_build", "Failed or blocked builds cannot be downloaded as completed packages.", 502)
                if bundle["downloadUrl"]:
                    package = self._path("builds", bundle["buildId"], "package.zip")
                    if not package.is_file() or package.stat().st_size > 20 * 1024 * 1024:
                        raise StudioFailure("invalid_build", "The generated package is missing or exceeds the download limit.", 502)
                self._capacity()
                record["result"] = bundle
                write_json(record_path, record)
                return copy.deepcopy(bundle)
            except asyncio.CancelledError:
                record["error"] = StudioFailure(
                    "build_cancelled", "Package request was cancelled locally; compiler completion is unknown.", 503
                ).public()
                write_json(record_path, record)
                raise
            except StudioFailure as exc:
                record["error"] = exc.public()
                write_json(record_path, record)
                raise
            except Exception:
                failure = StudioFailure("build_failed", "Package generation failed; no deployment was attempted.", 502)
                record["error"] = failure.public()
                write_json(record_path, record)
                raise failure from None

    def download(self, owner, build_id):
        safe_token(build_id)
        for record in self.builds.values():
            result = record.get("result")
            if (self._visible(owner, record) and result and result["buildId"] == build_id
                    and result["status"] == "compiled" and result["downloadUrl"]):
                path = self._path("builds", build_id, "package.zip")
                if path.is_file():
                    return path
        raise StudioFailure("not_found", "Package not found.", 404)
