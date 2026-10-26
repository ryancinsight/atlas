"""Collect the source-extractor contracts in the existing hosted test suite.

The test classes retain one implementation beside their extraction fixtures;
pytest scripts/tests and unittest discovery both collect these imported cases.
"""

from parity.reference.test_extract_torch_tensorflow import ReferenceExtractionTests
from parity.reference.test_numpy_jax import DocumentationDeclarationTests

__all__ = ["DocumentationDeclarationTests", "ReferenceExtractionTests"]
