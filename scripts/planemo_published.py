#!/usr/bin/env python3
"""Run Planemo shed_test with Test Tool Shed registered in disposable Galaxy.

Planemo 0.75.47 derives configured sheds from workflow runnables only. shed_test
has tool runnables, so its generated registry otherwise contains only Main.
This adapter changes configuration generation only; it does not replace tools,
tests, installation, dependency resolution, Galaxy source or Planemo files.
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


def main():
    from planemo import __version__
    from planemo.cli import planemo
    from planemo.galaxy import config

    if __version__ != "0.75.47" or len(sys.argv) < 2 or sys.argv[1] != "shed_test":
        raise RuntimeError("This configuration adapter supports only Planemo 0.75.47 shed_test")
    original = config.get_tool_sheds_conf_for_runnables

    def configured_sheds(runnables):
        return register_test_shed(original(runnables) or "<tool_sheds/>")

    config.get_tool_sheds_conf_for_runnables = configured_sheds
    planemo()


if __name__ == "__main__":
    main()
