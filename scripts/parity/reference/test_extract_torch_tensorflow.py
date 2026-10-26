"""Behavior tests for source inventory extraction, with no framework runtime."""

import hashlib
import importlib.util
import unittest
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    "extract_torch_tensorflow", Path(__file__).with_name("extract_torch_tensorflow.py")
)
EXTRACT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(EXTRACT)


class ReferenceExtractionTests(unittest.TestCase):
    def test_legacy_class_preserves_signature_and_public_symbol(self):
        # TensorFlow 2.21.0 Session.run's golden argument contract.
        source = b'''path: "tensorflow.Session"
tf_class {
  member_method {
    name: "run"
    argspec: "args=['self', 'fetches', 'feed_dict', 'options', 'run_metadata']"
  }
}
'''
        rows = EXTRACT.golden_records("golden/v1/tensorflow.-session.pbtxt", source, "source")
        self.assertEqual([r["symbol"] for r in rows], ["tf.compat.v1.Session", "tf.compat.v1.Session.run"])
        self.assertEqual(rows[1]["kind"], "method")
        self.assertIn("feed_dict", rows[1]["signature"])
        self.assertEqual(rows[1]["stability"], "legacy_compatibility_namespace")

    def test_protocol_fields_keep_serialization_schema(self):
        source = b'''path: "tensorflow.GraphDef"
tf_proto {
  descriptor {
    name: "GraphDef"
    field { name: "node" number: 1 label: LABEL_REPEATED type: TYPE_MESSAGE }
  }
}
'''
        rows = EXTRACT.golden_records("golden/v1/tensorflow.-graph-def.pbtxt", source, "source")
        self.assertEqual(rows[0]["kind"], "protocol_message")
        self.assertEqual(rows[1]["symbol"], "tf.compat.v1.GraphDef.node")
        self.assertEqual(rows[1]["descriptor"]["label"], ["LABEL_REPEATED"])
        self.assertEqual(rows[1]["descriptor"]["number"], ["1"])

    def test_unknown_syntax_does_not_silently_reduce_scope(self):
        with self.assertRaises(ValueError):
            EXTRACT.proto_nodes('path: "tensorflow" @ tf_module {}')

    def test_git_blob_identity_rejects_modified_source(self):
        value = b"public API declaration\n"
        expected = hashlib.sha1(b"blob 23\0" + value).hexdigest()
        self.assertEqual(len(value), 23)
        EXTRACT.verify_git_blob(value, expected)
        with self.assertRaises(ValueError):
            EXTRACT.verify_git_blob(value + b"modified", expected)


if __name__ == "__main__":
    unittest.main()
