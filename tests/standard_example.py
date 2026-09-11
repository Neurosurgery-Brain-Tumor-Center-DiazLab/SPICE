"""Scientific output assertions shared by source and installed-wheel checks."""
import csv
import json


def assert_standard_example(test, out, version):
    with (out / "example.SNV_mat.filter.csv").open(newline="") as handle:
        rows = list(csv.reader(handle))
    test.assertEqual(rows, [
        ["Variant_ID", "Ref", "cell-2", "cell_3"],
        ["chr1:10:A:G", "0/3", "1/2", "3/0"],
        ["chr1:20:A:G", "0/3", "1/2", "3/0"],
        ["chr2:30:C:T", "2/0", "0/3", "0/4"],
    ])
    fasta = (out / "example.SNV_mat.filter.fasta").read_text()
    test.assertEqual([line for line in fasta.splitlines() if line],
                     [">Ref", "GGC", ">cell-2", "RRT", ">cell_3", "AAT"])
    for suffix in (".cellID.filter.csv", ".selected_cells.tsv",
                   ".SNV_mat.input.tsv", ".SNVs.filter.csv", ".SNV_mat.RDS"):
        test.assertGreater((out / ("example" + suffix)).stat().st_size, 0)
    test.assertTrue((out / "CellMutationDist.pdf").read_bytes().startswith(b"%PDF"))
    runtime = json.loads((out / "example.runtime.json").read_text())
    test.assertIs(runtime["success"], True)
    test.assertEqual(runtime["command"], "filter")
    test.assertEqual(runtime["spice_version"], version)
    test.assertEqual(runtime["R"]["returncode"], 0)
