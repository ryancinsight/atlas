"""Routing storage must not erase APIs or manufacture qualified ownership."""

import copy
import hashlib
import unittest

from atlas_parity_schema import ParityError
from atlas_parity_scope import restore_audit, validate_bindings
from atlas_parity_tables import canonical, pack
from atlas_parity_scope_sources import audit_identity, classify, family_rows

REV = "a" * 40


class ScopeTests(unittest.TestCase):
    def setUp(self):
        self.refs = {"numpy-id": {"framework": "numpy"}}
        self.caps = {"ARRAY": {"owner": "leto", "prerequisites": []}}
        self.repos = {"leto": {"candidate_revision": REV}, "atlas": {"candidate_revision": REV}}
        self.contract = {"framework": "numpy", "source_artifact": "source.json",
                         "source_entry": ["contracts", 0], "capabilities": ["ARRAY"],
                         "prerequisites": [], "route_state": "canonical_family_proposal",
                         "semantic_definition_complete": False, "planned_owner": "leto",
                         "owner_revision": REV, "implementation_owner_verified": False}
        self.row = {"reference_id": "numpy-id", "visibility": "documented_public",
                    "identity_role": "declared", "contract": "array", "retained_obligation": True,
                    "signature_status": "source signature, coverage open",
                    "source_artifact": "record.json", "source_row": 0}

    def validate(self, rows=None):
        return validate_bindings(rows or [self.row], self.refs, {"array": self.contract},
                                 self.caps, self.repos)

    def test_source_route_does_not_claim_semantic_or_runtime_qualification(self):
        self.assertEqual(len(self.validate()), 1)
        self.assertFalse(self.contract["semantic_definition_complete"])

    def test_missing_extra_and_duplicate_reference_rejected(self):
        for rows in [[], [{**self.row, "reference_id": "other"}], [self.row, self.row]]:
            with self.subTest(rows=rows), self.assertRaises(ParityError):
                validate_bindings(rows, self.refs, {"array": self.contract}, self.caps, self.repos)

    def test_private_unsupported_and_hardware_absence_cannot_remove_obligation(self):
        self.row["retained_obligation"] = False
        with self.assertRaisesRegex(ParityError, "remove an obligation"):
            self.validate()

    def test_triage_owner_is_not_resolved_implementation_ownership(self):
        self.contract.update(route_state="ownership_unresolved", planned_owner="atlas")
        with self.assertRaisesRegex(ParityError, "triage owner"):
            self.validate()
        self.contract["planned_owner"] = None
        self.validate()

    def test_atlas_cannot_be_canonical_provider_route(self):
        self.contract["planned_owner"] = "atlas"
        self.caps["ARRAY"]["owner"] = "atlas"
        with self.assertRaisesRegex(ParityError, "planned provider"):
            self.validate()

    def test_wrong_owner_revision_or_capability_rejected(self):
        for update in [{"planned_owner": "atlas"}, {"owner_revision": "b" * 40},
                       {"capabilities": ["unknown"]}, {"prerequisites": ["unknown"]}]:
            with self.subTest(update=update):
                original = copy.deepcopy(self.contract)
                self.contract.update(update)
                with self.assertRaises(ParityError):
                    self.validate()
                self.contract = original

    def test_framework_semantics_and_signature_views_cannot_be_collapsed(self):
        self.contract["framework"] = "jax"
        with self.assertRaisesRegex(ParityError, "another framework"):
            self.validate()

    def test_family_membership_cannot_claim_complete_semantics(self):
        self.contract["semantic_definition_complete"] = True
        with self.assertRaisesRegex(ParityError, "routing does not establish"):
            self.validate()

    def test_owner_verified_field_cannot_be_promoted(self):
        self.contract["implementation_owner_verified"] = True
        with self.assertRaisesRegex(ParityError, "routing does not establish"):
            self.validate()

    def test_unreviewed_owner_state_cannot_be_promoted(self):
        self.contract["route_state"] = "implemented_and_qualified"
        with self.assertRaisesRegex(ParityError, "unreviewed routing"):
            self.validate()

    def test_canonical_prerequisite_cannot_be_silently_removed(self):
        self.caps["NUMERIC"] = {"owner": "leto", "prerequisites": []}
        self.caps["ARRAY"]["prerequisites"] = ["NUMERIC"]
        with self.assertRaisesRegex(ParityError, "prerequisites lost"):
            self.validate()
        self.contract["prerequisites"] = ["NUMERIC"]
        self.validate()

    def audit_fixture(self):
        source = {"records": [{"original_record": self.refs["numpy-id"], "signature": "shape(a)"}]}
        metadata = {"restore_original_record": True, "duplicate_original_record": "bound by identity/hash",
                    "capture_receipt": {"semantic_sha256": hashlib.sha256(canonical(source).encode()).hexdigest()}}
        table = pack([{"reference_id": "numpy-id", "reference_sha256": "c" * 64,
                       "signature": "shape(a)"}], metadata)
        return source, table

    def test_complete_rich_audit_roundtrip(self):
        source, table = self.audit_fixture()
        self.assertEqual(restore_audit(table, self.refs), source)

    def test_wrong_signature_or_lost_row_rejected_even_with_valid_table(self):
        _, table = self.audit_fixture()
        for rows in [[{"reference_id": "numpy-id", "reference_sha256": "c" * 64,
                       "signature": "ndim(a)"}], []]:
            with self.subTest(rows=rows), self.assertRaisesRegex(ParityError, "roundtrip differs"):
                restore_audit(pack(rows, table["metadata"]), self.refs)

    def test_unknown_source_identity_rejected(self):
        _, table = self.audit_fixture()
        wrong = pack([{"reference_id": "different", "reference_sha256": "c" * 64}], table["metadata"])
        with self.assertRaisesRegex(ParityError, "unknown reference"):
            restore_audit(wrong, self.refs)

    def test_torch_wrong_audit_and_row_baseline_rejected(self):
        expected = {"version": "2.14.1", "revision": REV, "inventory_sha256": "c" * 64}
        document = {"summary": {"framework": "pytorch", "version": "2.14.1", "revision": REV},
                    "records": [{"framework": "pytorch", "version": "2.14.1", "revision": REV}]}
        audit_identity("pytorch", document, expected)
        for target, key, value in [("summary", "version", "99.0.0"), ("summary", "revision", "b" * 40),
                                   ("record", "version", "99.0.0"), ("record", "revision", "b" * 40)]:
            changed = copy.deepcopy(document)
            (changed["summary"] if target == "summary" else changed["records"][0])[key] = value
            with self.subTest(target=target, key=key), self.assertRaises(ParityError):
                audit_identity("pytorch", changed, expected)

    def test_tf_input_digest_and_optional_version_cannot_drift(self):
        expected = {"version": "2.21.0", "revision": REV, "inventory_sha256": "c" * 64}
        audit_identity("tensorflow", {"input": {"sha256": "c" * 64}}, expected)
        for changed in [{"input": {"sha256": "d" * 64}},
                        {"input": {"sha256": "c" * 64}, "version": "99.0.0"}]:
            with self.assertRaises(ParityError):
                audit_identity("tensorflow", changed, expected)

    def test_binding_and_owner_are_derived_from_pinned_source(self):
        source = {"family_proposal": "ARR", "scope_classification": "documented_public_contract",
                  "signature": {"status": "partial"}}
        self.assertEqual(classify("pytorch", source)[2], "ARR")
        raw = {"id": "ARR", "canonical_capability": "ARRAY", "accountable_owner_proposal": "leto"}
        derived = family_rows("pytorch", {"families": [raw]}, "families", "source.json", self.caps, self.repos)[0]
        self.assertEqual(derived["planned_owner"], "leto")
        self.assertEqual(derived["capabilities"], ["ARRAY"])

    def test_unknown_source_class_and_silent_exclusion_rejected(self):
        row = {"family_proposal": "ARR", "scope_classification": "unknown-status",
               "signature": {"status": "partial"}}
        with self.assertRaisesRegex(ParityError, "unknown source publicness"):
            classify("pytorch", row)
        row.update(scope_classification="documented_public_contract", excluded=True)
        with self.assertRaisesRegex(ParityError, "cannot exclude"):
            classify("pytorch", row)


if __name__ == "__main__":
    unittest.main()
