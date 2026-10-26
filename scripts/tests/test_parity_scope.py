"""Routing storage must not erase APIs or manufacture qualified ownership."""

import copy
import hashlib
import unittest

from atlas_parity_schema import ParityError
from atlas_parity_scope import restore_audit, validate_bindings
from atlas_parity_tables import canonical, pack

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
                         "owner_revision": REV}
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


if __name__ == "__main__":
    unittest.main()
