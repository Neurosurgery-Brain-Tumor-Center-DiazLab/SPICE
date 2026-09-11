"""Real CLI/R check of the checked-in synthetic example, never silently skipped."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from standard_example import assert_standard_example

ROOT = Path(__file__).resolve().parents[1]


class StandardExampleTests(unittest.TestCase):
    def test_checked_in_example_through_real_filter(self):
        with tempfile.TemporaryDirectory(prefix="SPICE example ") as tmp:
            out = Path(tmp) / "output with spaces"
            subprocess.run(
                [sys.executable, str(ROOT / "SPICE.py"), "filter",
                 str(ROOT / "examples/standard"), str(out), "example",
                 "--input_format", "standard", "--min_alt_cells_per_snv", "2",
                 "--min_snvs_per_cell", "1", "--threads", "1"],
                cwd=ROOT, check=True, timeout=120,
            )
            assert_standard_example(self, out, (ROOT / "VERSION").read_text().strip())


if __name__ == "__main__":
    unittest.main()