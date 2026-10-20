#!/usr/bin/env python3
"""Run Planemo shed_test with Test Tool Shed registration and complete reporting.

Planemo 0.75.47 derives configured sheds from workflow runnables only. shed_test
has tool runnables, so its generated registry otherwise contains only Main.
Its remote test expansion also yields six cases from five placeholders, while
BaseEngine pairs results with the five placeholders and drops the last result.
This adapter retains the actual expanded cases when pairing results. It does
not replace tools, tests, assertions, outcomes, installation, dependency
resolution, Galaxy source or installed Planemo files.
"""
import sys
import xml.etree.ElementTree as ET

HOST = "https://testtoolshed.g2.bx.psu.edu"


def register_test_shed(contents):
    root = ET.fromstring(contents)
    urls = {node.attrib["url"].rstrip("/") for node in root.findall("tool_shed")}
    if HOST not in urls:
        ET.SubElement(root, "tool_shed", {"name": "Test Tool Shed", "url": HOST})
    return ET.tostring(root, encoding="unicode")


def pair_expanded_results(cases, responses):
    if len(cases) != len(responses) or not cases:
        raise RuntimeError("Missing results for expanded published test cases")
    paired = []
    for case, response in zip(cases, responses):
        if response["id"] != f"{case.tool_id}-{case.test_index}":
            raise RuntimeError("Published test result identity mismatch")
        paired.append((case, response))
    return paired


def main():
    from planemo import __version__
    from planemo.cli import planemo
    from planemo.galaxy import config
    from planemo.engine import galaxy as engine
    from planemo.runnable import ExternalGalaxyToolTestCase

    if __version__ != "0.75.47" or len(sys.argv) < 2 or sys.argv[1] != "shed_test":
        raise RuntimeError("This configuration adapter supports only Planemo 0.75.47 shed_test")
    original = config.get_tool_sheds_conf_for_runnables

    def configured_sheds(runnables):
        return register_test_shed(original(runnables) or "<tool_sheds/>")

    config.get_tool_sheds_conf_for_runnables = configured_sheds
    original_expand = engine.expand_test_cases

    def collect_all_remote_results(self, test_cases, test_timeout):
        if not all(isinstance(case, ExternalGalaxyToolTestCase) for case in test_cases):
            raise RuntimeError("Expected only remote Tool Shed test cases")
        expanded = []

        def record_expansion(galaxy_config, cases):
            actual = original_expand(galaxy_config, cases)
            expanded.extend(actual)
            return actual

        engine.expand_test_cases = record_expansion
        try:
            responses = self._run_test_cases(test_cases, test_timeout)
        finally:
            engine.expand_test_cases = original_expand
        # Every response and assertion outcome is returned unmodified.
        return pair_expanded_results(expanded, responses)

    engine.GalaxyEngine._collect_test_results = collect_all_remote_results
    planemo()


if __name__ == "__main__":
    main()
