"""Validate the shared Python wheel workflow's free-threaded contract."""

from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

import yaml


WORKFLOW = Path(__file__).resolve().parents[2] / ".github" / "workflows" / "python-wheels.yml"
VALIDATOR = WORKFLOW.parents[2] / "scripts" / "validate-python-wheels.py"


def legacy_platform_accepts(filename: str) -> bool:
    """Model the former first-match parser to prove these regressions matter."""
    platform_tag = filename.removesuffix(".whl").split("-")[-1]
    patterns = ("manylinux", "musllinux", "win_amd64", "macosx_")
    return any(token in platform_tag for token in patterns)


def legacy_validate(names: list[str]) -> bool:
    """Model the former count plus first-match presence checks."""
    return len(names) == 4 and all(legacy_platform_accepts(name) for name in names)


class PythonWheelsWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = WORKFLOW.read_text(encoding="utf-8")
        cls.workflow = yaml.safe_load(cls.source)

    def test_free_threaded_inputs_are_explicit_and_disabled_by_default(self) -> None:
        inputs = self.workflow[True]["workflow_call"]["inputs"]
        self.assertFalse(inputs["free-threaded"]["default"])
        self.assertEqual(inputs["free-threaded-versions"]["default"], '["3.14t", "3.15t"]')
        self.assertFalse(inputs["abi3t"]["default"])
        self.assertEqual(inputs["abi3t-python"]["default"], "3.15t")
        self.assertEqual(inputs["abi3t-features"]["default"], "")

    def test_free_threaded_jobs_use_the_shared_build_and_test_contract(self) -> None:
        jobs = self.workflow["jobs"]
        for job in ("build-free-threaded", "build-abi3t"):
            self.assertIn(job, jobs)
            text = "\n".join(step.get("run", "") for step in jobs[job]["steps"])
            self.assertIn("sys._is_gil_enabled() is False", text)
            self.assertIn("pytest", text)
            self.assertIn("PyO3/maturin-action@", self.source)
            self.assertIn("maturin-version: v1.14.1", self.source)
        self.assertIn('PYTHON_GIL: "0"', self.source)
        for job in ("build-free-threaded", "build-abi3t"):
            setup = next(
                step for step in self.workflow["jobs"][job]["steps"]
                if step.get("uses", "").startswith("actions/setup-python@")
            )
            self.assertTrue(setup["with"]["allow-prereleases"])

    def test_release_validation_distinguishes_free_threaded_abi_tags(self) -> None:
        validation = next(
            step for step in self.workflow["jobs"]["release-assets"]["steps"]
            if step.get("name") == "Validate release identity and wheel set"
        )
        run = validation["run"]
        self.assertIn("atlas-tools/scripts/validate-python-wheels.py", run)
        self.assertIn("--free", run)
        self.assertIn("--abi3t", run)
        self.assertIn("ABI3T_PYTHON", validation["env"])
        self.assertIn("--abi3-python", run)
        self.assertNotIn('PYTHON_GIL: "0"', run)

    def test_actual_release_validator_handles_compressed_tags_and_wrong_floor(self) -> None:
        valid = [
            "pkg-1-cp315-abi3.abi3t-macosx_11_0_universal2.macosx_10_9_universal2.whl",
            "pkg-1-cp315-abi3t-manylinux_2_17_x86_64.manylinux2014_x86_64.whl",
            "pkg-1-cp315-abi3t-manylinux_2_17_aarch64.whl",
            "pkg-1-cp315-abi3t-win_amd64.whl",
        ]
        command = [sys.executable, str(VALIDATOR), "--abi3t", "--abi3t-python", "3.15t"]
        for wheel in valid:
            command.extend(("--wheel", wheel))
        self.assertEqual(subprocess.run(command, check=False).returncode, 0)
        wrong = command.copy()
        wrong[wrong.index("pkg-1-cp315-abi3.abi3t-macosx_11_0_universal2.macosx_10_9_universal2.whl")] = "pkg-1-cp314-abi3.abi3t-macosx_11_0_universal2.whl"
        self.assertNotEqual(subprocess.run(wrong, check=False).returncode, 0)
        for malformed, index in (
            ("pkg-1-cp315-abi3t-manylinux_2_17_x86_64.win_amd64.whl", 1),
            ("pkg-1-cp315-abi3t-manylinux_2_17_x86_64.not_a_platform.whl", 1),
            ("pkg-1-cp315-abi3t-macosx___universal2.whl", 0),
        ):
            invalid_set = valid.copy()
            invalid_set[index] = malformed
            self.assertTrue(legacy_validate(invalid_set))
            invalid = [sys.executable, str(VALIDATOR), "--abi3t", "--abi3t-python", "3.15t"]
            for wheel in invalid_set:
                invalid.extend(("--wheel", wheel))
            self.assertNotEqual(subprocess.run(invalid, check=False).returncode, 0)

    def test_actual_release_validator_checks_cpython_and_abi3_floor(self) -> None:
        base = [
            "pkg-1-cp39-cp39-manylinux2014_x86_64.whl",
            "pkg-1-cp39-cp39-macosx_11_0_universal2.whl",
            "pkg-1-cp39-cp39-win_amd64.whl",
            "pkg-1-cp39-cp39-musllinux_1_2_x86_64.whl",
            "pkg-1-cp39-cp39-manylinux_2_17_aarch64.whl",
            "pkg-1-cp39-cp39-musllinux_1_2_aarch64.whl",
        ]
        command = [sys.executable, str(VALIDATOR), "--cpython", "3.9"]
        for wheel in base:
            command.extend(("--wheel", wheel))
        self.assertEqual(subprocess.run(command, check=False).returncode, 0)
        abi3 = [name.replace("cp39-cp39", "cp39-abi3") for name in base]
        command = [sys.executable, str(VALIDATOR), "--abi3", "--abi3-python", "3.9"]
        for wheel in abi3:
            command.extend(("--wheel", wheel))
        self.assertEqual(subprocess.run(command, check=False).returncode, 0)
        wrong_floor = [name.replace("cp39-abi3", "cp314-abi3") for name in abi3]
        command = [sys.executable, str(VALIDATOR), "--abi3", "--abi3-python", "3.9"]
        for wheel in wrong_floor:
            command.extend(("--wheel", wheel))
        self.assertNotEqual(subprocess.run(command, check=False).returncode, 0)

    def test_free_threaded_matrix_excludes_unexercisable_musl_rows(self) -> None:
        matrix = self.workflow["jobs"]["build-free-threaded"]["strategy"]["matrix"]
        self.assertEqual(matrix["platform"], ["glibc-x86", "glibc-arm", "windows", "macos"])
        platforms = {(row["target"], row["manylinux"]) for row in matrix["include"]}
        self.assertEqual(
            platforms,
            {
                ("x86_64", "2_17"),
                ("aarch64", "2_17"),
                ("x86_64", "off"),
                ("universal2-apple-darwin", "off"),
            },
        )
        self.assertNotIn("musllinux_1_2", {row["manylinux"] for row in matrix["include"]})

    def test_cpython_matrix_is_an_explicit_platform_cross_product(self) -> None:
        matrix = self.workflow["jobs"]["build-cpython"]["strategy"]["matrix"]
        self.assertEqual(
            matrix["platform"],
            ["glibc-x86", "glibc-arm", "musl-x86", "musl-arm", "windows", "macos"],
        )
        self.assertEqual(
            [row["platform"] for row in matrix["include"]],
            matrix["platform"],
        )
        self.assertIn("fromJSON(inputs.python-versions)", matrix["python-version"])

    def test_abi3t_matrix_is_an_explicit_platform_set(self) -> None:
        matrix = self.workflow["jobs"]["build-abi3t"]["strategy"]["matrix"]
        self.assertEqual(matrix["platform"], ["glibc-x86", "glibc-arm", "windows", "macos"])
        self.assertEqual([row["platform"] for row in matrix["include"]], matrix["platform"])

    def test_release_aggregation_waits_for_both_free_threaded_jobs(self) -> None:
        needs = self.workflow["jobs"]["release-assets"]["needs"]
        self.assertIn("build-free-threaded", needs)
        self.assertIn("build-abi3t", needs)
        validation = next(
            step for step in self.workflow["jobs"]["release-assets"]["steps"]
            if step.get("name") == "Validate release identity and wheel set"
        )
        environment = validation["env"]
        self.assertEqual(environment["FREE_THREADED"], "${{ inputs.free-threaded }}")
        self.assertEqual(environment["ABI3T"], "${{ inputs.abi3t }}")
        self.assertIn("abi3t", validation["run"])
        self.assertIn("validate-python-wheels.py", validation["run"])

    def test_workflow_has_no_registry_secret_path(self) -> None:
        for forbidden in ("PYPI_TOKEN", "TWINE_PASSWORD", "SSH_PRIVATE_KEY", "private_key"):
            self.assertNotIn(forbidden, self.source)
        self.assertEqual(self.source.count("Checkout Atlas wheel validator"), 1)


if __name__ == "__main__":
    unittest.main()
