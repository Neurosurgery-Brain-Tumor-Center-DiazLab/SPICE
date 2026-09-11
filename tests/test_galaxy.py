"""Fast Galaxy interface contracts; no Galaxy server or external inference."""
import argparse
import copy
import csv
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET

from spice_lineage.cli import build_parser

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "galaxy/tools"
NAMES = ("filter", "clones", "ancestry", "plasticity", "summarize")


def expanded_inputs(root, macros):
    node = copy.deepcopy(root.find("inputs"))
    def expand(parent):
        for child in list(parent):
            if child.tag == "expand":
                position = list(parent).index(child)
                parent.remove(child)
                definition = macros.find("xml[@name='" + child.attrib["macro"] + "']")
                for offset, entry in enumerate(definition):
                    entry = copy.deepcopy(entry)
                    parent.insert(position + offset, entry)
                    expand(entry)
            else:
                expand(child)
    expand(node)
    return node


class GalaxyContracts(unittest.TestCase):
    def test_versions_requirements_and_functional_tests(self):
        macros = ET.parse(TOOLS / "macros.xml").getroot()
        tokens = {x.attrib["name"]: x.text for x in macros.findall("token")}
        self.assertEqual(tokens["@TOOL_VERSION@"], (ROOT / "VERSION").read_text().strip())
        self.assertEqual(tokens["@VERSION_SUFFIX@"], "0")
        self.assertEqual(tokens["@PROFILE@"], "25.0")
        requirement = macros.find("xml[@name='requirements']/requirements/requirement")
        self.assertEqual(requirement.text, "spice-lineage")
        self.assertEqual(requirement.attrib, {"type": "package", "version": "@TOOL_VERSION@"})
        for name in NAMES:
            tool = ET.parse(TOOLS / ("spice_" + name + ".xml")).getroot()
            self.assertEqual(tool.attrib["version"], "@TOOL_VERSION@+galaxy@VERSION_SUFFIX@")
            self.assertEqual(tool.attrib["profile"], "@PROFILE@")
            self.assertIsNotNone(tool.find("expand[@macro='requirements']"))
            self.assertTrue(tool.findall("tests/test"), name)
            self.assertIsNotNone(tool.find("expand[@macro='command']"))
        command = macros.find("xml[@name='command']/command")
        self.assertEqual(command.attrib["detect_errors"], "aggressive")
        self.assertIn("unset PYTHONPATH PYTHONHOME", command.text)

    def test_all_production_option_defaults_match_cli(self):
        parser = build_parser()
        subcommands = next(a.choices for a in parser._actions
                           if isinstance(a, argparse._SubParsersAction))
        macros = ET.parse(TOOLS / "macros.xml").getroot()
        for name in NAMES:
            tool = ET.parse(TOOLS / ("spice_" + name + ".xml")).getroot()
            params = expanded_inputs(tool, macros).findall(".//param")
            options = {a.dest: a for a in subcommands[name]._actions if a.option_strings}
            represented = set()
            for param in params:
                argument = param.get("argument")
                if not argument:
                    continue
                key = argument.removeprefix("--")
                represented.add(key)
                if key == "outgroup":
                    self.assertEqual(param.get("value"), "")
                    self.assertIsNone(options[key].default)
                    continue
                if param.get("type") == "select":
                    selected = param.find("option[@selected='true']")
                    value = selected.get("value") if selected is not None else param.find("option").get("value")
                else:
                    value = param.get("value")
                    if value is not None and options[key].type is not None:
                        value = options[key].type(value)
                self.assertEqual(value, options[key].default, (name, key))
            expected = {key for key, action in options.items() if not action.required}
            expected -= {"help", "bayestraits_bin", "input_format"}
            self.assertEqual(represented, expected, name)
            self.assertNotIn("--bayestraits_bin", (TOOLS / ("spice_" + name + ".xml")).read_text())

    def test_standard_staging_and_existing_cli_only(self):
        text = (TOOLS / "spice_filter.xml").read_text()
        for name in ("matrix.tsv", "variants.tsv", "cells.tsv"):
            self.assertIn("standard/" + name, text)
        self.assertIn("'--input_format', 'standard'", text)
        for name in NAMES:
            xml = (TOOLS / ("spice_" + name + ".xml")).read_text()
            self.assertIn("'" + name + "'", xml)
            self.assertIn("json.dumps", xml)
        helper = (TOOLS / "run_spice.py").read_text()
        self.assertIn('os.execve(str(executable), [str(executable), *argv], env)', helper)
        self.assertIn('prefix / "bin/spice"', helper)
        self.assertFalse(list(TOOLS.glob("*.R")))
        self.assertFalse((TOOLS / "spice_phylogeny.xml").exists())

    def test_pinned_iqtree_and_collection_connections(self):
        workflow = json.loads((ROOT / "galaxy/workflows/spice_lineage_analysis.ga").read_text())
        steps = {step.get("label"): step for step in workflow["steps"].values()}
        iq = steps["iqtree"]
        self.assertEqual(iq["tool_id"], "toolshed.g2.bx.psu.edu/repos/iuc/iqtree/iqtree/2.4.0+galaxy2")
        self.assertEqual(iq["tool_shed_repository"], {"tool_shed": "toolshed.g2.bx.psu.edu", "name": "iqtree", "owner": "iuc", "changeset_revision": "e727e82945af"})
        state = json.loads(iq["tool_state"])
        self.assertEqual(state["tree_parameters"]["single_branch"]["alrt"], 1000)
        self.assertEqual(state["bootstrap_parameters"]["ultrafast_bootstrap"]["ufboot"], 1000)
        self.assertEqual(state["general_options"]["seqtype"], "DNA")
        # IUC defaults to AIC; SPICE relies on IQ-TREE 2.4.0's BIC default.
        self.assertEqual(state["modelling_parameters"]["automatic_model"]["merit"], "BIC")
        for target, input_name, source, output in [
            ("clones", "tree", "iqtree", "treefile"),
            ("ancestry", "tree", "clones", "clone_trees"),
            ("plasticity", "tree", "clones", "clone_trees"),
            ("plasticity", "ancestral_states", "ancestry", "ancestral_states"),
            ("summarize", "plasticity_tests", "plasticity", "plasticity_test"),
        ]:
            connection = steps[target]["input_connections"][input_name]
            self.assertEqual(len(connection), 1)
            self.assertEqual(connection[0]["id"], steps[source]["id"])
            self.assertEqual(connection[0]["output_name"], output)
        clones = ET.parse(TOOLS / "spice_clones.xml").getroot()
        collection = clones.find("outputs/collection[@name='clone_trees']")
        self.assertEqual(collection.get("type"), "list")
        self.assertIn("designation", collection.find("discover_datasets").get("pattern"))
        summary = ET.parse(TOOLS / "spice_summarize.xml").getroot()
        self.assertEqual(summary.find("inputs/param[@name='plasticity_tests']").get("collection_type"), "list")
        self.assertIn("element.element_identifier", (TOOLS / "spice_summarize.xml").read_text())

    def test_no_bundled_external_binaries(self):
        for path in (ROOT / "galaxy").rglob("*"):
            if path.is_file() and "__pycache__" not in path.parts:
                with path.open("rb") as handle:
                    self.assertNotIn(handle.read(4), (b"\x7fELF", b"PK\x03\x04", b"\x1f\x8b\x08\x00"), str(path))
                self.assertNotIn(path.suffix, (".exe", ".conda", ".gz", ".zip"))


class CollectionManifest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location("spice_galaxy_adapter", TOOLS / "run_spice.py")
        cls.adapter = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.adapter)

    def test_identifiers_and_paths_round_trip_without_shell_interpretation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "test result; literal 'quote'.tsv"
            source.write_text("result")
            identifier = "Clone_2; $(touch forbidden) 'quoted'"
            manifest = root / "manifest.tsv"
            self.adapter.write_manifest([(identifier, str(source))], manifest)
            with manifest.open() as handle:
                rows = list(csv.DictReader(handle, delimiter="\t"))
            self.assertEqual(rows, [{"clone_id": identifier, "plasticity_test": str(source)}])
            self.assertFalse((root / "forbidden").exists())

    def test_unrepresentable_identifiers_fail_explicitly(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "input.tsv"
            source.write_text("result")
            for identifier in ("", " clone", "clone ", "clone\t1", "clone\n1", "clone\r1"):
                with self.subTest(identifier=identifier), self.assertRaises(ValueError):
                    self.adapter.write_manifest([(identifier, str(source))], root / "manifest.tsv")
            with self.assertRaises(ValueError):
                self.adapter.write_manifest([("Clone_1", str(source))] * 2, root / "manifest.tsv")
            with self.assertRaises(ValueError):
                self.adapter.write_manifest([], root / "manifest.tsv")


if __name__ == "__main__":
    unittest.main()
