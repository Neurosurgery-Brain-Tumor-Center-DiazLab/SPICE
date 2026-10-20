"""Fail-closed public provenance and Galaxy acceptance gates (no network/server)."""
import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from check_public_distribution import CHANNEL, validate_record, verify_public_install
from check_galaxy import validate_test_report
from check_distribution import sha256


class PublicProvenance(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)
        self.prefix = self.work / "prefix"
        self.meta = self.prefix / "conda-meta"
        self.meta.mkdir(parents=True)
        payload = self.prefix / "lib/python3.11/site-packages/spice_lineage/VERSION"
        payload.parent.mkdir(parents=True)
        payload.write_text("0.2.0")
        self.payload = payload
        filename = "spice-lineage-0.2.0-pyhdfd78af_0.conda"
        self.artifact = {"filename": filename, "build": "pyhdfd78af_0", "url": CHANNEL + filename,
                         "sha256": "a" * 64, "source_sha256": {"spice_lineage/VERSION": sha256(payload)}}
        self.record = {"name": "spice-lineage", "version": "0.2.0", "build": "pyhdfd78af_0",
                       "build_number": 0, "subdir": "noarch", "url": CHANNEL + filename,
                       "sha256": "a" * 64}
        self.write_record(self.record)
        for name, version in (("iqtree", "2.4.0"), ("r-base", "4.3.3")):
            self.write_record({"name": name, "version": version,
                               "url": "https://conda.anaconda.org/conda-forge/linux-64/" + name + ".conda"})

    def write_record(self, record):
        (self.meta / (record["name"] + ".json")).write_text(json.dumps(record))

    def verify(self):
        return verify_public_install(self.prefix, self.artifact, self.work / "evidence")

    def test_public_identity_and_installed_payload_pass(self):
        result = self.verify()
        self.assertTrue(result["payload_matches_release"])
        self.assertEqual(result["package_count"], 3)
        self.assertEqual(json.loads((self.work / "evidence/spice-conda-meta.json").read_text()), self.record)

    def test_wrong_artifact_identity_is_rejected(self):
        for field, value in (("name", "spice"), ("version", "0.2.1"), ("build", "other_0"),
                             ("build_number", 1), ("subdir", "linux-64"), ("sha256", "b" * 64),
                             ("url", "file:///tmp/local/spice.conda"),
                             ("url", self.record["url"].replace("bioconda/", "bioconda/label/test/"))):
            with self.subTest(field=field, value=value), self.assertRaises(RuntimeError):
                validate_record({**self.record, field: value}, self.artifact)

    def test_installed_payload_drift_is_rejected(self):
        self.payload.write_text("modified")
        with self.assertRaisesRegex(RuntimeError, "payload differs"):
            self.verify()

    def test_dependency_channels_are_enforced(self):
        self.write_record({"name": "unexpected", "url": "file:///tmp/cache/dependency.conda"})
        with self.assertRaisesRegex(RuntimeError, "Non-public dependency"):
            self.verify()

    def test_scientific_executable_versions_are_enforced(self):
        for name, version in (("iqtree", "3.0.0"), ("r-base", "4.4.0")):
            with self.subTest(name=name):
                path = self.meta / (name + ".json")
                original = json.loads(path.read_text())
                self.write_record({**original, "version": version})
                with self.assertRaisesRegex(RuntimeError, "contract changed"):
                    self.verify()
                self.write_record(original)

    def test_missing_spice_record_is_rejected(self):
        (self.meta / "spice-lineage.json").unlink()
        with self.assertRaisesRegex(RuntimeError, "missing or ambiguous"):
            self.verify()


class GalaxyAcceptance(unittest.TestCase):
    def test_all_required_cases_must_succeed(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "report.json"
            success = [{"id": str(i), "data": {"status": "success"}} for i in range(6)]
            path.write_text(json.dumps({"tests": success}))
            self.assertEqual(validate_test_report(path, 6)["skipped"], 0)
            for state in ("skip", "skipped", "failure", "error", None):
                cases = copy.deepcopy(success)
                cases[0]["data"]["status"] = state
                path.write_text(json.dumps({"tests": cases}))
                with self.subTest(state=state), self.assertRaises(RuntimeError):
                    validate_test_report(path, 6)
            path.write_text(json.dumps({"tests": success[:5]}))
            with self.assertRaises(RuntimeError):
                validate_test_report(path, 6)


if __name__ == "__main__":
    unittest.main()
