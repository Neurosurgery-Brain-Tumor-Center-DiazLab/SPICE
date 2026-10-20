"""Offline fail-closed checks for published Tool Shed validation."""
import copy
import json
import sqlite3
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import check_published_galaxy as published
import planemo_published


class PublishedValidation(unittest.TestCase):

    def test_shed_registry_adapter_preserves_main_and_adds_test_once(self):
        original = '<tool_sheds><tool_shed name="Main" url="https://toolshed.g2.bx.psu.edu" /></tool_sheds>'
        configured = planemo_published.register_test_shed(original)
        self.assertEqual(configured, planemo_published.register_test_shed(configured))
        self.assertEqual({n.attrib['url'] for n in ET.fromstring(configured)},
                         {'https://toolshed.g2.bx.psu.edu', published.SHED})


    def test_expanded_case_reporting_preserves_all_outcomes(self):
        cases = [SimpleNamespace(tool_id='published', test_index=i) for i in range(6)]
        responses = [{'id': f'published-{i}', 'data': {'status': 'success' if i < 5 else 'failure'}}
                     for i in range(6)]
        paired = planemo_published.pair_expanded_results(cases, responses)
        self.assertEqual(len(paired), 6)
        self.assertIs(paired[-1][1], responses[-1])
        self.assertEqual(paired[-1][1]['data']['status'], 'failure')
        with self.assertRaises(RuntimeError):
            planemo_published.pair_expanded_results(cases, responses[:-1])
        with self.assertRaises(RuntimeError):
            planemo_published.pair_expanded_results(cases, list(reversed(responses)))

    def metadata(self):
        repository = {"id": published.REPOSITORY_ID, "owner": "diazlab", "name": "spice_lineage"}
        tools = [{"id": name, "guid": f"{published.HOST}/repos/diazlab/spice_lineage/{name}/{published.VERSION}",
                  "version": published.VERSION, "profile": 25.0,
                  "requirements": [{"name": "spice-lineage", "type": "package", "version": "0.2.0"}],
                  "tests": [{}] * (2 if name == "spice_plasticity" else 1)} for name in sorted(published.TOOL_IDS)]
        metadata = {"0:revision": {"repository_id": published.REPOSITORY_ID,
                    "changeset_revision": published.REVISION, "downloadable": True, "tools": tools}}
        return repository, metadata

    def test_exact_published_metadata_and_revision_required(self):
        repository, metadata = self.metadata()
        result = published.validate_metadata(repository, metadata, [published.REVISION])
        self.assertEqual(set(result), published.TOOL_IDS)
        for name, change in [("profile", 24.0), ("version", "0.2.1"), ("guid", "spice_filter"),
                             ("requirements", []), ("tests", [])]:
            broken = copy.deepcopy(metadata)
            broken["0:revision"]["tools"][0][name] = change
            with self.subTest(name=name), self.assertRaises(RuntimeError):
                published.validate_metadata(repository, broken, [published.REVISION])
        with self.assertRaises(RuntimeError):
            published.validate_metadata(repository, metadata, [published.REVISION, "newer"])

    def test_published_xml_profile_tokens_and_citations(self):
        self.assertEqual(set(published.verify_citations(ROOT / "galaxy/tools")), published.TOOL_IDS)

    def test_payload_matches_reviewed_archive_and_rejects_drift(self):
        manifest = json.loads(published.MANIFEST.read_text())
        self.assertTrue(published.compare_payload(ROOT / "galaxy/tools", manifest, strict=False)["all_hashes_match"])
        broken = copy.deepcopy(manifest)
        broken["files"]["run_spice.py"]["sha256"] = "0" * 64
        with self.assertRaises(RuntimeError):
            published.compare_payload(ROOT / "galaxy/tools", broken, strict=False)

    def test_workflow_changes_only_published_identity(self):
        repository, metadata = self.metadata()
        tools = published.validate_metadata(repository, metadata, [published.REVISION])
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            path = published.stage_workflow(root, tools)
            modified = json.loads(path.read_text())
            original = json.loads((ROOT / "galaxy/workflows/spice_lineage_analysis.ga").read_text())
            for key, step in modified["steps"].items():
                before = original["steps"][key]
                if before.get("tool_id") in tools:
                    self.assertEqual(step["tool_id"], tools[before["tool_id"]])
                    self.assertEqual(step.pop("tool_shed_repository")["changeset_revision"], published.REVISION)
                    step["tool_id"] = before["tool_id"]
                self.assertEqual(step, before)
            self.assertFalse(list((root / "tools").glob("*.xml")))
            self.assertEqual((root / "workflows/spice_lineage_analysis-job.yml").read_bytes(),
                             (ROOT / "galaxy/workflows/spice_lineage_analysis-job.yml").read_bytes())

    def test_local_tool_or_wrong_runtime_cannot_pass_job_audit(self):
        tools = {name: f"{published.HOST}/repos/diazlab/spice_lineage/{name}/{published.VERSION}"
                 for name in published.TOOL_IDS}
        prefix = Path('/isolated/public-conda/envs/__spice-lineage@0.2.0')
        marker = {"prefix": str(prefix), "spice_executable": str(prefix / 'bin/spice'),
                  "spice_import": str(prefix / 'lib/python3.11/site-packages/spice_lineage/__init__.py'), "version": "0.2.0"}
        job = {"id": "1", "tool_id": tools["spice_filter"], "state": "ok", "exit_code": 0,
               "stdout": "SPICE_GALAXY_EXECUTION " + json.dumps(marker)}
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "tools.json"
            data = {"tests": [{"data": {"job": copy.deepcopy(job)}} for _ in range(6)]}
            path.write_text(json.dumps(data))
            self.assertEqual(len(published.audit_jobs(path, tools, prefix, 6)), 6)
            data["tests"][0]["data"]["job"]["tool_id"] = 'spice_filter'
            path.write_text(json.dumps(data))
            with self.assertRaises(RuntimeError):
                published.audit_jobs(path, tools, prefix, 6)


    def test_actual_bayestraits_inference_banner_is_required(self):
        binary = Path('/external/BayesTraitsV4')
        runtime = {"success": True, "spice_version": "0.2.0", "command": "ancestry",
                   "parameters": {}, "executables": {"BayesTraits": {
                       "path": str(binary), "sha256": published.BT_BINARY_SHA256,
                       "recorded_banner": "BayesTraits V4.1.3"}}}
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            datasets = root / 'datasets'
            datasets.mkdir()
            source = datasets / 'dataset_1.dat'
            source.write_text(json.dumps(runtime))
            self.assertEqual(len(published.audit_runtime_outputs(datasets, binary, 1, root / 'pass')), 1)
            del runtime['executables']['BayesTraits']['recorded_banner']
            source.write_text(json.dumps(runtime))
            with self.assertRaises(RuntimeError):
                published.audit_runtime_outputs(datasets, binary, 1, root / 'fail')


    def test_retained_results_follow_recorded_dataset_uuids(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            datasets = root / 'datasets'
            datasets.mkdir()
            database = root / 'workflow.sqlite'
            steps = {}
            number = 0
            with sqlite3.connect(database) as connection:
                connection.execute('CREATE TABLE dataset (id INTEGER, uuid TEXT, external_filename TEXT)')
                for label, names, count in [('clones', ['assignments'], 1),
                        ('ancestry', ['qc_status', 'ancestral_states'], 3),
                        ('plasticity', ['plasticity_test'], 3), ('summarize', ['summary'], 1)]:
                    jobs = []
                    for j in range(count):
                        outputs = {}
                        for name in names:
                            number += 1
                            uuid = f'00000000-0000-0000-0000-{number:012d}'
                            outputs[name] = {'id': str(number), 'uuid': uuid}
                            connection.execute('INSERT INTO dataset VALUES (?, ?, NULL)', (number, uuid.replace('-', '')))
                            text = 'synthetic\toutput\n'
                            if name == 'summary':
                                text = 'clone_id\ttest_status\talternative\tn_tests_planned\tq_value\n'
                                text += ''.join(f'Clone_{i}\tpass\tgreater\t3\t1.0\n' for i in range(1, 4))
                            (datasets / f'dataset_{number}.dat').write_text(text)
                        jobs.append({'id': f'{label}-{j}', 'outputs': outputs})
                    steps[label] = {'workflow_step_label': label, 'jobs': jobs}
            report = root / 'workflow.json'
            report.write_text(json.dumps({'tests': [{'data': {'invocation_details': {'steps': steps}}}]}))
            result = published.retain_workflow_results(report, datasets, database, root / 'results')
            self.assertEqual(len(result['files']), 11)
            self.assertEqual(len(result['summary_rows']), 3)
            with sqlite3.connect(database) as connection:
                connection.execute("UPDATE dataset SET external_filename='/outside/data' WHERE id=1")
            with self.assertRaises(RuntimeError):
                published.retain_workflow_results(report, datasets, database, root / 'rejected')


if __name__ == '__main__':
    unittest.main()
