"""Acceptance tests for false parity qualification and lost scope.

Small protocol fixtures exercise failure invariants. One acceptance test also
checks all real recorded declarations; no framework runtime or GPU is mocked.
"""

from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

import atlas_parity as parity
from atlas_parity_evidence import validate_evidence, validate_mappings
from atlas_parity_schema import ParityError, api_identity, read_json
from atlas_parity_repository import ATLAS_GATES, validate_repository_evidence
from atlas_parity_decisions import validate_decisions

REV = "a" * 40
OTHER = "b" * 40
HASH = "c" * 64


def mapping_fixture():
    refs = {"reference-op": {"framework": "numpy", "version": "2.5.4"}}
    caps = {"ARRAY": {"owner": "leto"}}
    repos = {"leto": {"candidate_revision": REV}}
    row = {
        "id": "numpy-add", "capability": "ARRAY", "owner": "leto", "revision": REV,
        "canonical_operation": "leto::add", "reference_ids": ["reference-op"],
        "variants": [{"reference_id": "reference-op", "semantics": "Elementwise represented addition",
                      "coverage_proof": "f32 CPU dense class for this fixture's declared scalar domain",
                      "error_cases": ["unequal nonbroadcast shapes"], "analytical_tests": ["1+2=3"],
                      "differential_tests": ["numpy.add"], "benchmarks": ["vector bandwidth"],
                      "hardware": ["CPU"]}],
        "coverage_classes": [{"id": "add-cpu", "reference_id": "reference-op", "dtype": "f32",
                              "device": "cpu", "layout": "dense", "gradient": "reverse",
                              "execution": "eager", "domain": "finite represented values"}],
        "status": {"mapping": "specified", "implementation": "unknown", "tested": "unrun",
                   "external": "unrun", "performance": "unrun", "release": "unreleased"},
        "stage_evidence": {},
    }
    evidence = {
        "id": "E1", "stage": "tested", "owner": "leto", "revision": REV, "capability": "ARRAY",
        "mapping_ids": [row["id"]], "command": "run analytical-add", "result": "success",
        "skipped": 0, "executed": 4, "artifact": "https://example.org/run/1", "sha256": HASH,
        "environment": {"cpu": "actual machine recorded by caller"}, "coverage": ["add-cpu"],
        "execution_device_by_class": {"add-cpu": "cpu"},
        "review": {"state": "approved", "revision": REV, "artifact": "https://example.org/review/1",
                   "independent": True},
    }
    return refs, caps, repos, row, evidence


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.refs, self.caps, self.repos, self.mapping, self.evidence = mapping_fixture()

    def validate(self, evidence=None):
        mappings, assigned = validate_mappings([self.mapping], self.caps, self.refs, self.repos)
        records = validate_evidence([evidence or self.evidence], mappings, self.caps, self.refs)
        return mappings, assigned, records

    def test_materialized_mapping_and_executed_coverage_accepted(self):
        self.mapping["status"]["tested"] = "passed"
        self.mapping["stage_evidence"]["tested"] = ["E1"]
        mappings, assigned, records = self.validate()
        self.assertEqual(assigned, {"reference-op": "numpy-add"})
        self.assertEqual(set(records), {"E1"})
        self.assertEqual(mappings["numpy-add"]["status"]["external"], "unrun")

    def test_skipped_test_does_not_verify(self):
        self.evidence["skipped"] = 1
        with self.assertRaisesRegex(ParityError, "skipped"):
            self.validate()

    def test_zero_execution_does_not_verify(self):
        self.evidence["executed"] = 0
        with self.assertRaisesRegex(ParityError, "unexecuted"):
            self.validate()

    def test_failed_or_unavailable_result_does_not_verify(self):
        for result in ("failed", "unavailable"):
            with self.subTest(result=result):
                self.evidence["result"] = result
                with self.assertRaises(ParityError):
                    self.validate()

    def test_boolean_execution_count_rejected(self):
        self.evidence["executed"] = True
        with self.assertRaisesRegex(ParityError, "expected int"):
            self.validate()

    def test_cpu_fallback_for_promised_device_rejected(self):
        self.mapping["coverage_classes"][0]["device"] = "cuda:0"
        with self.assertRaisesRegex(ParityError, "fallback"):
            self.validate()

    def test_stale_execution_revision_rejected(self):
        self.evidence["revision"] = OTHER
        self.evidence["review"]["revision"] = OTHER
        with self.assertRaisesRegex(ParityError, "stale execution"):
            self.validate()

    def test_off_cohort_mapping_revision_rejected(self):
        self.mapping["revision"] = OTHER
        with self.assertRaisesRegex(ParityError, "selected exact revision"):
            self.validate()

    def test_stale_review_rejected(self):
        self.evidence["review"]["revision"] = OTHER
        with self.assertRaisesRegex(ParityError, "stale review"):
            self.validate()

    def test_nonindependent_review_rejected(self):
        self.evidence["review"]["independent"] = False
        with self.assertRaisesRegex(ParityError, "independent review absent"):
            self.validate()

    def test_promoted_state_requires_stage_evidence(self):
        self.mapping["status"]["external"] = "passed"
        with self.assertRaisesRegex(ParityError, "without evidence"):
            self.validate()

    def test_wrong_stage_cannot_promote(self):
        self.mapping["status"]["external"] = "passed"
        self.mapping["stage_evidence"]["external"] = ["E1"]
        with self.assertRaisesRegex(ParityError, "wrong evidence stage"):
            self.validate()

    def test_partial_classes_cannot_promote(self):
        additional = {**self.mapping["coverage_classes"][0], "id": "add-strided", "layout": "strided"}
        self.mapping["coverage_classes"].append(additional)
        self.mapping["status"]["tested"] = "passed"
        self.mapping["stage_evidence"]["tested"] = ["E1"]
        with self.assertRaisesRegex(ParityError, "every coverage class"):
            self.validate()

    def external(self):
        self.evidence.update(stage="external", oracle_releases={"numpy": "2.5.4"},
                             input_sha256=HASH, numerical_bound="Exact represented addition in this fixture")

    def test_pinned_external_release_accepted(self):
        self.external()
        self.assertEqual(self.validate()[2]["E1"]["oracle_releases"], {"numpy": "2.5.4"})

    def test_wrong_or_unrelated_external_release_rejected(self):
        self.external()
        for oracle in ({"numpy": "1.0"}, {"pytorch": "2.14.1"}):
            with self.subTest(oracle=oracle):
                self.evidence["oracle_releases"] = oracle
                with self.assertRaisesRegex(ParityError, "oracle release differs"):
                    self.validate()

    def test_companion_oracle_release_is_required(self):
        self.external()
        self.refs["reference-op"]["companion_version"] = "keras==3.15.1"
        with self.assertRaisesRegex(ParityError, "companion oracle"):
            self.validate()
        self.evidence["oracle_releases"]["keras"] = "3.15.1"
        self.assertIn("E1", self.validate()[2])

    def test_unqualified_performance_rejected(self):
        self.evidence["stage"] = "performance"
        with self.assertRaisesRegex(ParityError, "baseline_revision"):
            self.validate()

    def test_release_without_fresh_consumer_rejected(self):
        self.evidence.update(stage="release", registry_artifact="https://example.org/registry/1")
        with self.assertRaisesRegex(ParityError, "fresh_consumer_artifact"):
            self.validate()

    def test_duplicate_owner_mapping_rejected(self):
        duplicate = {**copy.deepcopy(self.mapping), "id": "second-owner"}
        with self.assertRaisesRegex(ParityError, "multiple canonical owners"):
            validate_mappings([self.mapping, duplicate], self.caps, self.refs, self.repos)

    def test_name_only_mapping_without_axes_rejected(self):
        self.mapping["coverage_classes"][0]["dtype"] = "reference_valid_combinations"
        with self.assertRaisesRegex(ParityError, "unresolved coverage"):
            self.validate()

    def test_missing_reference_variant_rejected(self):
        self.mapping["variants"] = []
        with self.assertRaisesRegex(ParityError, "semantic variant"):
            self.validate()


class ProgramTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.real = parity.load()

    def test_real_inventory_is_valid_and_does_not_qualify(self):
        result = parity.report(self.real)
        self.assertGreater(result["reference_declarations"], 38000)
        self.assertEqual(result["mapped_declarations"], 0)
        self.assertEqual(result["reference_declarations"], result["unmapped_declarations"])
        self.assertEqual(result["repositories"], 29)
        self.assertTrue(parity.qualification(self.real, "definition", REV))
        self.assertTrue(parity.qualification(self.real, "release", REV))

    def test_capability_dependency_cycle_rejected(self):
        caps = copy.deepcopy(self.real["capabilities"])
        caps["NUM-REP"]["prerequisites"] = ["NUM-PROMOTE"]
        with self.assertRaisesRegex(ParityError, "cycle"):
            parity.program_structure(self.real["program"], caps, self.real["repositories"], self.real["packages"])

    def test_missing_package_prerequisite_rejected(self):
        packages = copy.deepcopy(self.real["packages"])
        packages["WP-011"]["dependencies"].remove("WP-010")
        with self.assertRaisesRegex(ParityError, "ARR-REDUCE scheduled later"):
            parity.program_structure(self.real["program"], self.real["capabilities"], self.real["repositories"], packages)

    def test_unknown_owner_rejected(self):
        caps = copy.deepcopy(self.real["capabilities"])
        caps["NUM-REP"]["owner"] = "unassigned"
        with self.assertRaisesRegex(ParityError, "unknown owner"):
            parity.program_structure(self.real["program"], caps, self.real["repositories"], self.real["packages"])

    def test_scope_policies_cannot_disappear(self):
        rows = list(self.real["decisions"].values())[1:]
        with self.assertRaisesRegex(ParityError, "decision disappeared"):
            validate_decisions(self.real["program"], rows, self.real["repositories"])

    def test_policy_cannot_reduce_scope_or_fabricate_approval(self):
        for flag in ("scope_reduction", "implementation_approval_granted"):
            rows = copy.deepcopy(list(self.real["decisions"].values()))
            rows[0][flag] = True
            with self.subTest(flag=flag), self.assertRaisesRegex(ParityError, "reduce scope or fabricate"):
                validate_decisions(self.real["program"], rows, self.real["repositories"])

    def test_policy_summary_must_match_actual_resolutions(self):
        for key, value in (("open_decisions", ["DEC-001"]), ("resolved_policy_decisions", [])):
            program = {**self.real["program"], key: value}
            with self.subTest(key=key), self.assertRaisesRegex(ParityError, "differs from decision register"):
                validate_decisions(program, list(self.real["decisions"].values()), self.real["repositories"])

    def test_family_labels_cannot_claim_implementation(self):
        caps = copy.deepcopy(self.real["capabilities"])
        caps["ARR-CREATE"]["status"]["implementation"] = "implemented"
        with self.assertRaisesRegex(ParityError, "family labels"):
            parity.program_structure(self.real["program"], caps, self.real["repositories"], self.real["packages"])

    def test_source_hash_and_count_drift_rejected(self):
        snapshot = copy.deepcopy(self.real["program"]["reference_snapshots"])
        snapshot[0]["sha256"] = HASH
        with self.assertRaisesRegex(ParityError, "content hash drift"):
            parity.references(parity.DEFAULT, snapshot)
        snapshot = copy.deepcopy(self.real["program"]["reference_snapshots"])
        snapshot[0]["records"] += 1
        with self.assertRaisesRegex(ParityError, "record count drift"):
            parity.references(parity.DEFAULT, snapshot)

    def test_source_completeness_cannot_be_overridden(self):
        snapshot = copy.deepcopy(self.real["program"]["reference_snapshots"])
        snapshot[0]["public_surface_complete"] = True
        with self.assertRaisesRegex(ParityError, "completeness claim"):
            parity.references(parity.DEFAULT, snapshot)

    def test_all_four_sources_required(self):
        with self.assertRaisesRegex(ParityError, "all four"):
            parity.references(parity.DEFAULT, self.real["program"]["reference_snapshots"][:3])

    def test_distinct_source_declarations_preserved(self):
        row = {"symbol": "tf.add", "kind": "function", "source": "https://example.org/v1"}
        other = {**row, "source": "https://example.org/v2"}
        self.assertNotEqual(api_identity("tensorflow", "2.21.0", row),
                            api_identity("tensorflow", "2.21.0", other))

    def test_duplicate_json_keys_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            file = Path(directory) / "record.json"
            file.write_text('{"state":"unrun","state":"passed"}')
            with self.assertRaisesRegex(ParityError, "duplicate JSON key"):
                read_json(file)

    def test_false_release_status_still_requires_definition(self):
        bundle = {**self.real, "program": copy.deepcopy(self.real["program"])}
        bundle["program"]["definition_complete"] = True
        blockers = parity.qualification(bundle, "release", REV)
        self.assertIn(f"{len(self.real['references'])} API declarations unmapped", blockers)
        self.assertIn("independent exact-final-revision release review pending", blockers)

    def test_repository_status_string_is_not_exit_evidence(self):
        bundle = {**self.real, "repositories": copy.deepcopy(self.real["repositories"])}
        for row in bundle["repositories"].values():
            row["status"] = "qualified"
        blockers = parity.qualification(bundle, "release", REV)
        self.assertIn("leto: repository exit criteria unqualified", blockers)

    def test_source_manifest_loss_and_aggregate_drift_rejected(self):
        snapshot = copy.deepcopy(self.real["program"]["reference_snapshots"])
        # Keep complete actual source rows; removing a provenance row must be
        # detected even after a caller intentionally refreshes the file hash.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for item in snapshot:
                target = root / item["path"]
                target.parent.mkdir(exist_ok=True)
                target.write_bytes((parity.DEFAULT / item["path"]).read_bytes())
            target = root / snapshot[0]["path"]
            data = json.loads(target.read_text())
            data["sources"].pop()
            target.write_text(json.dumps(data))
            snapshot[0]["sha256"] = hashlib.sha256(target.read_bytes()).hexdigest()
            with self.assertRaisesRegex(ParityError, "source count drift"):
                parity.references(root, snapshot)

    def test_committed_binding_catches_ignored_alternate_input(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            (root / ".gitignore").write_text("ignored/\n")
            (root / "tracked.json").write_text('{"value":1}')
            subprocess.run(["git", "-C", str(root), "add", "."], check=True)
            subprocess.run(["git", "-C", str(root), "-c", "user.name=Parity test",
                            "-c", "user.email=parity@example.org", "commit", "-qm", "fixture"], check=True)
            candidate = subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()
            ignored = root / "ignored" / "program.json"
            ignored.parent.mkdir()
            ignored.write_text('{"value":2}')
            status = subprocess.check_output(["git", "-C", str(root), "status", "--porcelain"], text=True)
            self.assertEqual(status, "")
            self.assertEqual(parity.committed_inputs([root / "tracked.json"], root, candidate), [])
            self.assertTrue(parity.committed_inputs([ignored], root, candidate))
            (root / "tracked.json").write_text('{"value":3}')
            self.assertTrue(parity.committed_inputs([root / "tracked.json"], root, candidate))

    def test_clean_crlf_checkout_matches_committed_git_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            subprocess.run(["git", "-C", str(root), "config", "core.autocrlf", "true"], check=True)
            (root / ".gitattributes").write_text("* text=auto\n")
            target = root / "program.json"
            original = b'{\n  "value": 1\n}\n'
            target.write_bytes(original)
            subprocess.run(["git", "-C", str(root), "add", "."], check=True, capture_output=True)
            subprocess.run(["git", "-C", str(root), "-c", "user.name=Parity test",
                            "-c", "user.email=parity@example.org", "commit", "-qm", "fixture"], check=True)
            candidate = subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()
            target.unlink()
            subprocess.run(["git", "-C", str(root), "checkout", "--", "program.json"], check=True)
            self.assertIn(b'\r\n', target.read_bytes())
            self.assertEqual(subprocess.check_output(
                ["git", "-C", str(root), "status", "--porcelain"], text=True), "")
            self.assertEqual(parity.committed_inputs([target], root, candidate), [])


class RepositoryEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.repos = {"atlas": {"candidate_revision": REV, "required_gates": sorted(ATLAS_GATES)}}
        self.record = {"id": "atlas-exit", "repository": "atlas", "revision": REV,
                       "review": {"state": "approved", "revision": REV, "independent": True,
                                  "artifact": "https://example.org/review/1"},
                       "gates": [{"name": name, "command": f"run {name}", "executed": 1,
                                  "skipped": 0, "result": "success", "artifact": "https://example.org/run/1",
                                  "sha256": HASH, "environment": {"machine": "recorded"}}
                                 for name in sorted(ATLAS_GATES)]}

    def test_complete_exact_revision_repository_evidence_accepted(self):
        records, qualified = validate_repository_evidence([self.record], self.repos)
        self.assertEqual(qualified, {"atlas"})
        self.assertEqual(set(records), {"atlas-exit"})

    def test_missing_actual_repository_gate_rejected(self):
        self.record["gates"].pop()
        with self.assertRaisesRegex(ParityError, "missing repository exit gates"):
            validate_repository_evidence([self.record], self.repos)

    def test_stale_repository_revision_rejected(self):
        with self.assertRaisesRegex(ParityError, "stale repository"):
            validate_repository_evidence([self.record], self.repos, OTHER)

    def test_repository_gate_skip_rejected(self):
        self.record["gates"][0]["skipped"] = 1
        with self.assertRaisesRegex(ParityError, "skipped"):
            validate_repository_evidence([self.record], self.repos)

    def test_release_retains_implementation_hold_after_definition_closes(self):
        approved = {"state": "approved", "revision": REV, "independent": True,
                    "artifact": "https://example.org/review/1"}
        bundle = {"program": {"definition_complete": True, "open_decisions": [],
                              "definition_gaps": [], "implementation_blockers": ["Apollo service hold"]},
                  "snapshots": [], "references": {}, "assigned": {}, "mappings": {},
                  "repositories": self.repos, "qualified_repositories": set()}
        external = {"candidate_revision": REV, "definition_review": approved,
                    "release_review": approved, "repository_evidence": [self.record]}
        self.assertEqual(parity.qualification(bundle, "definition", REV, external), [])
        self.assertEqual(parity.qualification(bundle, "release", REV, external),
                         ["implementation: Apollo service hold"])


if __name__ == "__main__":
    unittest.main()
