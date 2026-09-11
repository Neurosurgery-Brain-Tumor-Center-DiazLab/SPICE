"""Real CLI/R check of the checked-in synthetic example, never silently skipped."""
import csv
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

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
            with (out / "example.SNV_mat.filter.csv").open(newline="") as handle:
                rows = list(csv.reader(handle))
            self.assertEqual(rows, [
                ["Variant_ID", "Ref", "cell-2", "cell_3"],
                ["chr1:10:A:G", "0/3", "1/2", "3/0"],
                ["chr1:20:A:G", "0/3", "1/2", "3/0"],
                ["chr2:30:C:T", "2/0", "0/3", "0/4"],
            ])
            fasta = (out / "example.SNV_mat.filter.fasta").read_text()
            self.assertEqual([line for line in fasta.splitlines() if line],
                             [">Ref", "GGC", ">cell-2", "RRT", ">cell_3", "AAT"])
            for suffix in (".cellID.filter.csv", ".selected_cells.tsv",
                           ".SNV_mat.input.tsv", ".SNVs.filter.csv", ".SNV_mat.RDS"):
                self.assertGreater((out / ("example" + suffix)).stat().st_size, 0)
            self.assertTrue((out / "CellMutationDist.pdf").read_bytes().startswith(b"%PDF"))
            runtime = json.loads((out / "example.runtime.json").read_text())
            self.assertIs(runtime["success"], True)
            self.assertEqual(runtime["command"], "filter")
            self.assertEqual(runtime["spice_version"], (ROOT / "VERSION").read_text().strip())
            self.assertEqual(runtime["R"]["returncode"], 0)


if __name__ == "__main__":
    unittest.main()