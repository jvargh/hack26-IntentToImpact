"""Fixed-command, local-only Bicep compile experiment; not a product adapter."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone


SOURCE = Path(__file__).resolve().parent
WORKSPACE = SOURCE.parents[2]
REPOSITORY_ROOT = WORKSPACE.parent if WORKSPACE.name == "intent-to-impact-studio" else WORKSPACE
OWNED_ROOT = REPOSITORY_ROOT / ".intent-to-impact" / "spikes" / "SPK-04-01"
RESTORE_VERSION = "v0.34.44"
LIMITATIONS = [
    "Compilation is live-local; the sample, component tag and promise association are fixture assumptions.",
    "No deployment, target validation, what-if, authentication, provider registration or Azure resource operations were performed.",
    "CP-01 runtime status is unknown: publicNetworkAccess Disabled alone cannot verify CP-01.",
    "Private Endpoint, DNS resolution, private-path connectivity and data-plane operations are not tested.",
    "RBAC, managed identity, encryption configuration, policy, quotas, region support, name availability and target permissions are not verified.",
    "Standard_LRS is a synthetic compile choice, not a production resilience recommendation.",
    "subscriptionId only parameterizes the intended resource-ID output; it does not select a deployment subscription.",
    "Repeatability is demonstrated for recorded source bytes and compiler version, not across arbitrary compiler versions.",
    "No canonical product state, UX gate approval or complete architecture verification is produced.",
]


def now():
    return datetime.now(timezone.utc).isoformat()


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def redact(text):
    for path, label in [(str(WORKSPACE), "[workspace]"), (str(Path.home()), "[user-home]")]:
        text = re.sub(re.escape(path), lambda _: label, text, flags=re.IGNORECASE)
    text = re.sub(r"(?i)(Bearer\s+)\S+", r"\1[redacted]", text)
    return re.sub(
        r"(?i)((?:access_token|refresh_token|client_secret|password|AccountKey|SharedAccessSignature)\s*[=:]\s*)[^\s,;]+",
        r"\1[redacted]", text,
    )


def expected_result(exit_code, stdout, stderr, *, negative=False, timed_out=False, capture_error=None):
    if timed_out or capture_error or exit_code is None:
        return False
    if negative:
        return exit_code != 0 and re.search(r"\bError BCP\d{3}\b", stdout + stderr) is not None
    return exit_code == 0


def validate_mapping(template, sidecar):
    """Assert this exact bounded fixture, not a generic ARM/promise verifier."""
    assert sidecar["schemaVersion"] == "1.0.0"
    assert sidecar["canonicalProductState"] is False
    assert sidecar["evidenceOrigin"] == "fixture"
    assert sidecar["externalModules"] == []
    assert sidecar["source"] == "main.bicep"
    assert sidecar["scenarioId"] == "DEMO-CASE-CLAIMS-V1"
    assert len(sidecar["resources"]) == 1
    spec = sidecar["resources"][0]
    assert spec["sourceSymbol"] == "claimsStore"
    assert spec["compiledResourcePointer"] == "/resources/0"
    assert spec["componentId"] == "CMP-CLAIMS-STORE"
    assert spec["componentTag"] == "architecture-component-id"
    assert spec["promiseIds"] == ["CP-01"]
    assert spec["coverage"] == "partial-desired-state-example-only"
    assert spec["resourceType"] == "Microsoft.Storage/storageAccounts"
    assert spec["apiVersion"] == "2023-05-01"
    assert len(template["resources"]) == 1
    resource = template["resources"][0]
    assert resource["type"] == spec["resourceType"]
    assert resource["apiVersion"] == spec["apiVersion"]
    assert resource["tags"][spec["componentTag"]] == spec["componentId"]
    assert resource["tags"]["evidence-origin"] == "fixture"
    assert resource["kind"] == "StorageV2"
    assert resource["sku"]["name"] == "Standard_LRS"
    assert resource["name"] == "[parameters('storageAccountName')]"
    assert resource["location"] == "[parameters('location')]"
    assert set(template["parameters"]) == {"subscriptionId", "location", "storageAccountName"}
    for parameter in template["parameters"].values():
        assert parameter["type"] == "string"
        assert "defaultValue" not in parameter
    assert "parameters('subscriptionId')" in template["outputs"]["intendedStorageResourceId"]["value"]
    properties = resource["properties"]
    assert properties["publicNetworkAccess"] == "Disabled"
    assert properties["allowBlobPublicAccess"] is False
    assert properties["supportsHttpsTrafficOnly"] is True
    assert properties["minimumTlsVersion"] == "TLS1_2"
    assert properties["networkAcls"] == {"defaultAction": "Deny", "bypass": "None"}
    assert properties == spec["assertedProperties"]
    return {
        "componentId": spec["componentId"],
        "promiseIds": spec["promiseIds"],
        "source": sidecar["source"],
        "sourceSymbol": spec["sourceSymbol"],
        "compiledResourcePointer": spec["compiledResourcePointer"],
        "resourceType": resource["type"],
        "apiVersion": resource["apiVersion"],
        "nameExpression": resource["name"],
        "associationOrigin": "fixture",
        "compiledStructureOrigin": "live-local",
        "coverage": spec["coverage"],
        "runtimePromiseStatus": "unknown",
    }


class Spike:
    def __init__(self, run_directory):
        self.root = run_directory
        self.environment = os.environ.copy()
        self.environment.update({
            "AZURE_CONFIG_DIR": str(self.root / "azure-config"),
            "AZURE_EXTENSION_DIR": str(self.root / "azure-extensions"),
            "AZURE_CORE_COLLECT_TELEMETRY": "false",
            "AZURE_CORE_CHECK_VERSION": "false",
            "AZURE_BICEP_CHECK_VERSION": "false",
            "AZURE_BICEP_USE_BINARY_FROM_PATH": "false",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONNOUSERSITE": "1",
            "TEMP": str(self.root / "tmp"),
            "TMP": str(self.root / "tmp"),
            "TMPDIR": str(self.root / "tmp"),
            "SPK_BICEP_RUN_DIRECTORY": str(self.root),
        })
        self.receipt = {
            "schemaVersion": "1.0.0",
            "purpose": "spike-only-local-bicep-compile",
            "taskId": "SPK-04-01",
            "parentPlanId": "SPK-04",
            "canonicalProductState": False,
            "startedAt": now(),
            "status": "running",
            "evidenceOrigin": "live-local",
            "inputOrigin": "fixture",
            "scenarioId": "DEMO-CASE-CLAIMS-V1",
            "cloudOperationsPerformed": False,
            "targetPreflight": {"status": "not-run", "reason": "Not authorized; compile-only task."},
            "runtimePromiseStatus": "unknown",
            "externalModules": [],
            "environment": {
                "pythonVersion": sys.version,
                "powershellVersion": os.environ.get("SPK_BICEP_POWERSHELL_VERSION", "not-invoked-via-wrapper"),
                "azureConfigDirectory": "azure-config",
                "temporaryDirectory": "tmp",
                "telemetryDisabled": True,
                "bicepVersionChecksDisabled": True,
            },
            "toolRestore": {"attempted": False},
            "commands": [],
            "files": [],
            "sourceMapping": [],
            "limitations": LIMITATIONS,
        }
        for folder in ["azure-config", "azure-extensions", "tmp"]:
            (self.root / folder).mkdir()

    def save(self):
        write_json(self.root / "receipt.json", self.receipt)

    def record_file(self, path, role):
        self.receipt["files"].append({
            "path": str(path.relative_to(WORKSPACE)),
            "role": role,
            "sha256": digest(path),
            "bytes": path.stat().st_size,
        })

    def command(self, name, argv, *, negative=False, timeout=120):
        record = {
            "id": name,
            "argv": [redact(str(arg)) for arg in argv],
            "cwd": "[workspace]",
            "startedAt": now(),
            "timeoutSeconds": timeout,
            "expectedOutcome": "compiler-rejection" if negative else "success",
            "exitCode": None,
            "timedOut": False,
            "captureError": None,
        }
        stdout, stderr = "", ""
        try:
            result = subprocess.run(
                [str(arg) for arg in argv], cwd=WORKSPACE, env=self.environment,
                capture_output=True, timeout=timeout, check=False,
            )
            record["exitCode"] = result.returncode
            stdout = result.stdout.decode("utf-8", errors="replace")
            stderr = result.stderr.decode("utf-8", errors="replace")
        except subprocess.TimeoutExpired as error:
            record["timedOut"] = True
            stdout = (error.stdout or b"").decode("utf-8", errors="replace")
            stderr = (error.stderr or b"").decode("utf-8", errors="replace")
        except OSError as error:
            record["captureError"] = redact(str(error))
        record["finishedAt"] = now()
        record["expectationMet"] = expected_result(
            record["exitCode"], stdout, stderr, negative=negative,
            timed_out=record["timedOut"], capture_error=record["captureError"],
        )
        record["outcome"] = (
            "expected-negative-failure" if negative and record["expectationMet"]
            else "succeeded" if record["expectationMet"] else "unexpected-failure"
        )
        for stream, text in [("stdout", stdout), ("stderr", stderr)]:
            path = self.root / f"{name}.{stream}.txt"
            path.write_text(redact(text), encoding="utf-8")
            record[stream] = {"path": path.name, "sha256": digest(path), "redacted": True}
        self.receipt["commands"].append(record)
        self.save()
        return record

    def require(self, record):
        if not record["expectationMet"]:
            raise RuntimeError(f"{record['id']}: {record['outcome']}, exit={record['exitCode']}")

    def execute(self):
        if sys.flags.optimize:
            raise RuntimeError("Assertions must be enabled; do not run Python with -O.")
        az = shutil.which("az")
        # A missing executable is still invoked and captured as a real process error.
        az = az or "az"
        before = {path: digest(path) for path in SOURCE.iterdir() if path.is_file()}
        for path in before:
            self.record_file(path, "source")
        cli = self.command("azure-cli-version", [az, "version", "--output", "json"])
        self.require(cli)
        self.receipt["environment"]["azureCliVersion"] = json.loads(
            (self.root / "azure-cli-version.stdout.txt").read_text(encoding="utf-8")
        )["azure-cli"]
        version = self.command("bicep-version", [az, "bicep", "version"])
        if not version["expectationMet"]:
            error_text = (self.root / "bicep-version.stderr.txt").read_text(encoding="utf-8")
            if not re.search(r"Bicep CLI not found|Bicep.*not installed", error_text, re.IGNORECASE):
                raise RuntimeError("Bicep version failed without a recognized missing-compiler diagnostic.")
            version["outcome"] = "missing-dependency"
            self.receipt["toolRestore"] = {
                "attempted": True,
                "reason": "Actual bicep-version missing-compiler failure",
                "version": RESTORE_VERSION,
                "destination": "azure-config\\bin",
                "networkEffect": "Compiler download only; not Azure authentication or resource access.",
                "status": "running",
            }
            restore = self.command("bicep-install", [az, "bicep", "install", "--version", RESTORE_VERSION], timeout=240)
            self.require(restore)
            self.receipt["toolRestore"]["status"] = "restored"
            version = self.command("bicep-version-after-restore", [az, "bicep", "version"])
        self.require(version)
        self.receipt["environment"]["bicepVersion"] = (
            self.root / version["stdout"]["path"]
        ).read_text(encoding="utf-8").strip()
        for binary in (self.root / "azure-config" / "bin").glob("bicep*"):
            if binary.is_file():
                self.record_file(binary, "restored-compiler")
        template_paths = [self.root / "main.arm.json", self.root / "main.repeat.arm.json"]
        for index, output in enumerate(template_paths, 1):
            result = self.command(f"build-valid-{index}", [
                az, "bicep", "build", "--file", SOURCE / "main.bicep",
                "--outfile", output, "--no-restore",
            ])
            self.require(result)
            if not output.is_file():
                raise RuntimeError("Compiler returned success without producing the ARM output.")
            self.record_file(output, "compiled-output")
        if digest(template_paths[0]) != digest(template_paths[1]):
            raise RuntimeError("Repeated compilation did not produce identical output bytes.")
        self.receipt["repeatability"] = {
            "status": "matched",
            "sourceSha256": before[SOURCE / "main.bicep"],
            "firstOutputSha256": digest(template_paths[0]),
            "secondOutputSha256": digest(template_paths[1]),
        }
        sidecar = json.loads((SOURCE / "promise-mapping.json").read_text(encoding="utf-8"))
        template = json.loads(template_paths[0].read_text(encoding="utf-8-sig"))
        self.receipt["sourceMapping"] = [validate_mapping(template, sidecar)]
        write_json(self.root / "resource-mapping.json", {
            "schemaVersion": "1.0.0", "canonicalProductState": False,
            "templateSha256": digest(template_paths[0]),
            "sidecarSha256": before[SOURCE / "promise-mapping.json"],
            "resources": self.receipt["sourceMapping"],
        })
        self.record_file(self.root / "resource-mapping.json", "compiled-resource-mapping")
        invalid = self.root / "tmp" / "invalid.bicep"
        invalid.write_text("param intentionallyBroken string =\n", encoding="utf-8")
        self.record_file(invalid, "generated-invalid-source")
        invalid_output = self.root / "tmp" / "invalid.arm.json"
        negative = self.command("build-invalid", [
            az, "bicep", "build", "--file", invalid, "--outfile", invalid_output, "--no-restore",
        ], negative=True)
        self.require(negative)
        if invalid_output.exists():
            raise RuntimeError("Invalid input unexpectedly produced an ARM artifact.")
        for path, source_hash in before.items():
            if digest(path) != source_hash:
                raise RuntimeError(f"Source changed during run: {path.name}")
        self.receipt["sourceUnchanged"] = True
        self.save()
        tests = self.command("unittest", [
            sys.executable, "-B", "-m", "unittest", "discover",
            "-s", SOURCE, "-p", "test_spike.py", "-v",
        ])
        self.require(tests)
        self.receipt["status"] = "passed"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-directory", required=True, type=Path)
    args = parser.parse_args()
    run_directory = args.run_directory
    if not run_directory.is_absolute() or run_directory.resolve().parent != OWNED_ROOT.resolve():
        parser.error("Run directory must be an immediate child of the owned SPK-04-01 root.")
    for path in [REPOSITORY_ROOT / ".intent-to-impact", OWNED_ROOT.parent, OWNED_ROOT, run_directory]:
        if path.is_symlink() or getattr(path, "is_junction", lambda: False)():
            parser.error("Reparse evidence paths are not supported.")
    if not run_directory.is_dir() or any(run_directory.iterdir()):
        parser.error("Run directory must exist and be empty; never overwrite earlier evidence.")
    spike = Spike(run_directory)
    try:
        spike.execute()
    except Exception as error:
        spike.receipt["status"] = "failed"
        spike.receipt["failure"] = redact(f"{type(error).__name__}: {error}")
        if not spike.receipt["sourceMapping"]:
            spike.receipt["safeNextAction"] = "Inspect recorded failures; never synthesize ARM as a fallback."
    finally:
        spike.receipt["finishedAt"] = now()
        spike.save()
    print(json.dumps({
        "taskId": "SPK-04-01", "status": spike.receipt["status"],
        "receipt": str((run_directory / "receipt.json").relative_to(REPOSITORY_ROOT)),
        "commandOutcomes": [
            {"id": item["id"], "exitCode": item["exitCode"], "outcome": item["outcome"]}
            for item in spike.receipt["commands"]
        ],
    }, indent=2))
    return 0 if spike.receipt["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
