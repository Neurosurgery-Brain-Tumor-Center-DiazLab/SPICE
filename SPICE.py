#!/usr/bin/env python3
"""Compatibility entry point for source-checkout users."""
from spice_lineage.cli import build_parser, main

if __name__ == "__main__":
    raise SystemExit(main())
