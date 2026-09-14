"""Local assertions for the revised public-only proposal; no Azure operations."""

import copy
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import sys
import unittest
from urllib.parse import urlparse

from collect_public_evidence import DOCUMENTS, FILTERS


SOURCE = Path(__file__).resolve().parent
WORKSPACE = SOURCE.parents[2]
EVIDENCE = WORKSPACE / ".intent-to-impact" / "spikes" / "SPK-03-01"


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate(proposal):
    assert proposal["schemaVersion"] == "1.0.0"
    assert proposal["status"] == "approval-required"
    assert proposal["runtimeProof"] == "blocked"
    assert proposal["runtimePromiseStatus"] == "unknown"
    assert proposal["canonicalProductState"] is False
    assert proposal["deploymentId"] is None
    assert proposal["azureMutationsPerformed"] == []
    assert proposal["evidenceOrigins"]["fixtureUsedAsProof"] is False
    change = proposal["scenarioChange"]
    assert change["publicEndpointDesignDirected"] is True
    assert change["originalCp01PrivateNetworkResult"] == "not-evaluated-not-passed"
    assert change["privateConnectivityRequired"] is False
    assert change["allAttackScenariosVerified"] is False
    assert change["currentCanonicalPromiseId"] is None
    assert change["historicalBicepFixture"] and change["canonicalScenarioUpdate"]
    target = proposal["target"]
    assert target["subscriptionId"] == "463a82d4-1896-4332-aeeb-618ee5a5aa93"
    assert target["resourceGroupName"] == "rg-intent-to-impact-demo"
    assert target["resourceGroupId"] is None and target["storageAccountId"] is None
    assert target["resourceGroupExists"] is False
    assert target["regionStatus"] == "proposed-not-confirmed"
    resources = proposal["resources"]
    assert len(resources) == 2
    assert {r["armType"] for r in resources} == {
        "Microsoft.Resources/resourceGroups", "Microsoft.Storage/storageAccounts"
    }
    assert {r["proposedRef"] for r in resources} == {"sandbox-rg", "claims-store"}
    assert all(r["quantity"] == 1 and r["resourceId"] is None for r in resources)
    design = proposal["design"]
    assert design["publicEndpoint"] is True
    for key in ["standalonePublicIpResources", "vnetResources", "privateEndpointResources",
                "privateDnsResources", "vpnResources", "verifierVmResources", "roleAssignmentsToCreate"]:
        assert design[key] == 0
    assert design["localPrivateConnectivityAssumed"] is False
    controls = proposal["storageControls"]
    assert controls["publicNetworkAccess"] == "Enabled"
    assert controls["supportsHttpsTrafficOnly"] is True
    assert controls["minimumTlsVersion"] == "TLS1_2"
    for key in ["allowBlobPublicAccess", "allowSharedKeyAccess", "realDataAllowed", "blobWritesAllowed", "isHnsEnabled"]:
        assert controls[key] is False
    assert controls["containersToCreate"] == 0
    assert controls["networkAcls"] == {"defaultAction": "Allow", "bypass": "None", "ipRules": [], "virtualNetworkRules": []}
    assert {item["check"] for item in proposal["requiredProofAfterApproval"]} == {
        "actual-empty-deployment-baseline", "https-only-configuration", "anonymous-blob-configuration",
        "public-endpoint-and-tls-configuration", "fresh-post-rollback"
    }
    assert all(item["requiredEvidence"] for item in proposal["requiredProofAfterApproval"])
    verifier = proposal["verifier"]
    assert verifier["kind"] == "operator-scoped-management-plane-property-read"
    assert verifier["infrastructureRequired"] == []
    assert verifier["executionStatus"] == "not-run"
    assert verifier["privateNetworkPathProofRequired"] is False
    assert verifier["dataPlaneOperationsRequired"] is False
    assert proposal["permissions"]["operatorOnlyMutations"] is True
    assert proposal["permissions"]["newRoleAssignmentsRequired"] is False
    assert proposal["permissions"]["status"] == "not-verified-not-granted"
    for section in ["seedAndRollback", "cleanup"]:
        assert proposal[section]["approvalRequired"] is True
        assert proposal[section]["approved"] is False
        assert proposal[section]["operatorOnly"] is True
    seed = proposal["seedAndRollback"]
    assert seed["scopeRef"] == "claims-store"
    assert seed["change"] == {"property": "supportsHttpsTrafficOnly", "from": True, "to": False}
    assert seed["rollbackProperty"] == "supportsHttpsTrafficOnly"
    assert seed["rollbackValue"] is True
    assert seed["anonymousAccessMayBeEnabled"] is False
    assert "allowBlobPublicAccess=false" in seed["unchangedGuards"]
    assert seed["preconditions"] and seed["rollback"] and seed["rollbackOnFailure"] and seed["postRollback"]
    assert 0 < seed["maximumRequestedDurationSeconds"] <= 120
    cleanup = proposal["cleanup"]
    assert cleanup["scopeRule"] == "actual-owned-manifest-only"
    assert cleanup["unrelatedResourceDeletionAllowed"] is False
    assert cleanup["automaticCleanupClaimed"] is False
    assert cleanup["plan"]
    assert proposal["pricing"]["budgetApproved"] is False
    assert proposal["pricing"]["selectedMeters"] and proposal["pricing"]["exclusions"]
    assert proposal["unknownsAndBlockers"]
    assert proposal["approval"]["approved"] is False
    assert all(proposal["approval"][key] for key in ["requestedNow", "beforeProvisioning", "beforeSeed", "safeNextAction"])


class ProposalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.proposal = load(SOURCE / "proposed-sandbox.json")

    def test_public_only_proposal(self):
        validate(self.proposal)

    def test_runtime_or_private_promise_success_rejected(self):
        for section, key, value in [
            (None, "runtimeProof", "verified"), (None, "runtimePromiseStatus", "verified"),
            (None, "status", "approved"), ("scenarioChange", "originalCp01PrivateNetworkResult", "passed"),
            ("scenarioChange", "allAttackScenariosVerified", True),
        ]:
            with self.subTest(field=key):
                changed = copy.deepcopy(self.proposal)
                (changed if section is None else changed[section])[key] = value
                with self.assertRaises(AssertionError):
                    validate(changed)

    def test_no_fabricated_resource_or_deployment_ids(self):
        for key in ["deploymentId", "resourceId"]:
            changed = copy.deepcopy(self.proposal)
            if key == "resourceId":
                changed["resources"][1][key] = "/subscriptions/fake/storageAccounts/fake"
            else:
                changed[key] = "/subscriptions/fake/deployments/fake"
            with self.assertRaises(AssertionError):
                validate(changed)

    def test_private_or_extra_infrastructure_rejected(self):
        for arm_type in ["Microsoft.Network/privateEndpoints", "Microsoft.Network/privateDnsZones",
                         "Microsoft.Network/publicIPAddresses", "Microsoft.Compute/virtualMachines"]:
            with self.subTest(resource=arm_type):
                changed = copy.deepcopy(self.proposal)
                changed["resources"].append({"proposedRef": "not-allowed", "armType": arm_type,
                                             "quantity": 1, "resourceId": None})
                with self.assertRaises(AssertionError):
                    validate(changed)
        changed = copy.deepcopy(self.proposal)
        changed["design"]["privateEndpointResources"] = 1
        with self.assertRaises(AssertionError):
            validate(changed)

    def test_required_public_https_and_anonymous_settings(self):
        for key, value in [("publicNetworkAccess", "Disabled"), ("supportsHttpsTrafficOnly", False),
                           ("allowBlobPublicAccess", True), ("minimumTlsVersion", "TLS1_0")]:
            with self.subTest(property=key):
                changed = copy.deepcopy(self.proposal)
                changed["storageControls"][key] = value
                with self.assertRaises(AssertionError):
                    validate(changed)

    def test_missing_configuration_proof_rejected(self):
        for check in ["https-only-configuration", "anonymous-blob-configuration", "fresh-post-rollback"]:
            changed = copy.deepcopy(self.proposal)
            changed["requiredProofAfterApproval"] = [
                item for item in changed["requiredProofAfterApproval"] if item["check"] != check
            ]
            with self.assertRaises(AssertionError):
                validate(changed)

    def test_wrong_or_unapproved_seed_and_rollback_rejected(self):
        for key, value in [
            ("change", {"property": "allowBlobPublicAccess", "from": False, "to": True}),
            ("change", {"property": "publicNetworkAccess", "from": "Disabled", "to": "Enabled"}),
            ("anonymousAccessMayBeEnabled", True), ("approvalRequired", False),
            ("approved", True), ("operatorOnly", False), ("rollbackValue", False),
            ("scopeRef", "all-subscription-storage"), ("rollback", ""),
        ]:
            with self.subTest(field=key):
                changed = copy.deepcopy(self.proposal)
                changed["seedAndRollback"][key] = value
                with self.assertRaises(AssertionError):
                    validate(changed)

    def test_scoped_cleanup_and_approval_required(self):
        for section, key, value in [
            ("cleanup", "scopeRule", "whole-subscription"),
            ("cleanup", "unrelatedResourceDeletionAllowed", True),
            ("approval", "approved", True), ("approval", "beforeProvisioning", ""),
            ("approval", "beforeSeed", ""),
        ]:
            changed = copy.deepcopy(self.proposal)
            changed[section][key] = value
            with self.assertRaises(AssertionError):
                validate(changed)

    def test_superseded_findings_retained_not_current(self):
        old = load(SOURCE / "superseded-private-proposed-sandbox.json")
        self.assertEqual(old["status"], "superseded")
        self.assertEqual(old["supersededBy"], "proposed-sandbox.json")
        self.assertTrue(any(r["armType"] == "Microsoft.Network/privateEndpoints" for r in old["resources"]))
        self.assertIn("HISTORICAL ONLY", (SOURCE / "superseded-private-approval-request.md").read_text(encoding="utf-8"))
        self.assertEqual(set(FILTERS), {"blob"})
        self.assertEqual(set(DOCUMENTS), set(self.proposal["evidence"]["requiredDocumentIds"]))

    def test_public_evidence_retrieval_and_hashes(self):
        found = set()
        for reference in self.proposal["evidence"]["publicManifests"]:
            path = EVIDENCE / reference
            manifest = load(path)
            self.assertEqual(manifest["evidenceOrigin"], "live-external")
            self.assertTrue(manifest["readOnly"])
            self.assertEqual(manifest["azureOperations"], [])
            for item in manifest["sources"]:
                self.assertEqual(item["method"], "GET")
                self.assertEqual(item["status"], "retrieved")
                self.assertEqual(item["httpStatus"], 200)
                self.assertIn(urlparse(item["url"]).hostname, {
                    "learn.microsoft.com", "azure.microsoft.com", "prices.azure.com"
                })
                datetime.fromisoformat(item["retrievedAt"])
                self.assertEqual(sha(path.parent / item["file"]), item["sha256"])
                found.add(item["id"])
        self.assertTrue(set(self.proposal["evidence"]["requiredDocumentIds"]) <= found)

    def test_selected_prices_match_primary_live_meters(self):
        for selected in self.proposal["pricing"]["selectedMeters"]:
            body = load(EVIDENCE / selected["evidenceFile"])
            self.assertFalse(body["NextPageLink"])
            matches = [
                item for item in body["Items"]
                if item["meterId"] == selected["meterId"] and item["productName"] == selected["productName"]
                and item["armRegionName"] == selected["armRegionName"] and item["isPrimaryMeterRegion"]
                and item["tierMinimumUnits"] == 0 and item["type"] == "Consumption"
            ]
            self.assertEqual(len(matches), 1)
            self.assertEqual(matches[0]["retailPrice"], selected["unitPrice"])
            self.assertEqual(matches[0]["unitOfMeasure"], selected["unit"])
            self.assertEqual(matches[0]["currencyCode"], "USD")

    def test_zero_usage_is_conditional_not_a_guaranteed_bill(self):
        prices = self.proposal["pricing"]
        estimate = (prices["assumedStoredGb"] * 0.0184
                    + prices["assumedDataPlaneReadOperations"] / 10000 * 0.004
                    + prices["assumedDataPlaneListOperations"] / 10000 * 0.05)
        self.assertEqual(estimate, 0)
        self.assertEqual(prices["listedUsageEstimateUsd"], estimate)
        self.assertGreater(len(prices["exclusions"]), 3)
        self.assertFalse(prices["budgetApproved"])


def main():
    if sys.flags.optimize:
        raise SystemExit("Do not run assertion checks with Python optimization enabled.")
    started = datetime.now(timezone.utc)
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(ProposalTests)
    )
    text = stream.getvalue()
    print(text, end="")
    for parent in [WORKSPACE / ".intent-to-impact", EVIDENCE.parent, EVIDENCE]:
        if parent.is_symlink() or getattr(parent, "is_junction", lambda: False)():
            raise SystemExit("Refusing reparse evidence paths.")
    run = EVIDENCE / ("validation-" + started.strftime("%Y%m%dT%H%M%S%fZ"))
    run.mkdir(parents=True, exist_ok=False)
    log = run / "unittest.txt"
    log.write_text(text, encoding="utf-8")
    receipt = {
        "schemaVersion": "1.0.0", "purpose": "public-only-proposal-validation",
        "taskId": "SPK-03-01", "evidenceOrigin": "live-local",
        "startedAt": started.isoformat(), "finishedAt": datetime.now(timezone.utc).isoformat(),
        "command": ["python", "-B", "tests\\spikes\\azure\\test_proposal.py"],
        "pythonVersion": sys.version,
        "validationStatus": "passed" if result.wasSuccessful() else "failed",
        "testCount": result.testsRun, "failures": len(result.failures), "errors": len(result.errors),
        "exitCode": 0 if result.wasSuccessful() else 1,
        "proposalStatus": "approval-required", "runtimeProof": "blocked",
        "originalCp01PrivateNetworkResult": "not-evaluated-not-passed",
        "azureMutationsPerformed": [],
        "sourceHashes": {path.name: sha(path) for path in SOURCE.iterdir() if path.is_file()},
        "log": {"file": log.name, "sha256": sha(log)},
        "limitations": ["Local tests are not deployment or runtime proof. Private proposal is superseded."],
    }
    (run / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print("RECEIPT", str((run / "receipt.json").relative_to(WORKSPACE)))
    return receipt["exitCode"]


if __name__ == "__main__":
    raise SystemExit(main())
