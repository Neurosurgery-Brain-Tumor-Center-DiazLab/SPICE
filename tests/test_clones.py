"""Fast routing/default/provenance regressions; external computation is mocked."""
import argparse
from contextlib import redirect_stderr, redirect_stdout
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import SPICE
from spice_lineage import cli, runtime_info

# Reviewed Phase 3 defaults: every shared option must retain these values.
CLONE_DEFAULTS = {
    "uf_support_threshold": 90, "sh_support_threshold": 75,
    "branch_cut_min": 0, "branch_cut_max": 0.5, "branch_cut_step": 0.01,
    "clone_cut_mode": "auto", "clone_cut_threshold": None,
    "min_trusted_ratio": 0.95, "min_partition_stability": 0.95,
    "stability_window": 3, "min_tips": 50,
    "root_method": "midpoint", "outgroup": None,
}
ROOT = Path(__file__).resolve().parents[1]


class ClonesTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="SPICE clones ")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.tree = self.root / "external supported tree.nwk"
        self.tree.write_text("(Ref:1,(A:0.1,B:0.1)99/100:0.2,C:1);\n")
        self.fasta = self.root / "upstream alignment.fa"
        self.fasta.write_text(">A\nACGT\n>B\nACGA\n")
        self.output = self.root / "clone output with spaces"
        self.parser = cli.build_parser()
        # Suppress routine command chatter, leaving unittest's result stream alone.
        self.quiet = redirect_stdout(io.StringIO())
        self.quiet.__enter__()
        self.addCleanup(self.quiet.__exit__, None, None, None)

    def argv(self, *extra):
        return ["clones", "--tree", str(self.tree), "--output_directory",
                str(self.output), "--prefix", "sample", *extra]

    def args(self, command="clones", *extra):
        if command == "clones":
            return self.parser.parse_args(self.argv(*extra))
        return self.parser.parse_args(["phylogeny", str(self.fasta),
                                       str(self.output), "sample", *extra])

    def test_registration_and_legacy_help(self):
        choices = next(a.choices for a in self.parser._actions
                       if isinstance(a, argparse._SubParsersAction))
        self.assertIn("clones", choices)
        self.assertIs(self.args().func, cli.run_clones)
        self.assertIs(SPICE.main, cli.main)
        result = subprocess.run([sys.executable, str(ROOT / "SPICE.py"), "clones", "--help"],
                                text=True, capture_output=True, check=True)
        for text in ("Does not infer a tree", "IQ-TREE-style", "SH-aLRT/UFBoot",
                     "rooting", "support filtering", "branch-cut analysis",
                     "threshold selection", "clone assignment", "clone tree export"):
            self.assertIn(text, " ".join(result.stdout.split()))

    def test_required_arguments(self):
        argv = self.argv()
        for option in ("--tree", "--output_directory", "--prefix"):
            index = argv.index(option)
            with self.subTest(option=option), redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
                self.parser.parse_args(argv[:index] + argv[index+2:])
            self.assertEqual(error.exception.code, 2)

    def test_no_inference_options(self):
        for option in ("--model", "--threads", "--uf_bootstrap_replicates", "--sh_alrt_replicates"):
            with self.subTest(option=option), redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                self.parser.parse_args(self.argv(option, "1"))

    def test_all_shared_defaults_match_phase3_and_each_other(self):
        phy, clones = self.args("phylogeny"), self.args()
        for name, expected in CLONE_DEFAULTS.items():
            with self.subTest(option=name):
                self.assertEqual(getattr(phy, name), expected)
                self.assertEqual(getattr(clones, name), expected)
        extra = set(vars(clones)) - {"command", "tree", "output_directory", "prefix", "func"}
        self.assertEqual(extra, set(CLONE_DEFAULTS))

    def test_missing_tree_and_directory_fail_before_runner(self):
        for tree in (self.root / "missing.treefile", self.root):
            args = self.args()
            args.tree = str(tree)
            with self.subTest(tree=tree), patch.object(cli, "run_clone_classification") as runner:
                error = io.StringIO()
                with redirect_stderr(error), self.assertRaises(SystemExit):
                    cli.run_clones(args)
                self.assertIn("IQ-TREE tree not found", error.getvalue())
                runner.assert_not_called()

    def test_unreadable_tree_fails_before_runner(self):
        with (
            patch.object(Path, "open", side_effect=PermissionError("permission denied")),
            patch.object(cli, "run_clone_classification") as runner,
        ):
            with self.assertRaisesRegex(ValueError, "Cannot read IQ-TREE tree"):
                cli.run_clones(self.args())
            runner.assert_not_called()

    def test_prefix_safety_uses_existing_main_validation(self):
        for prefix in ("", ".", "..", "../escape", "a/b", "bad\nname", "bad\tname"):
            with self.subTest(prefix=prefix), patch.object(cli, "capture_runtime") as capture:
                with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
                    cli.main(self.argv("--prefix", prefix))
                self.assertEqual(error.exception.code, 2)
                capture.assert_not_called()

    def test_invalid_selection_and_root_settings_match_both_routes(self):
        cases = [(["--clone_cut_mode", "manual"], "requires --clone_cut_threshold"),
                 (["--clone_cut_threshold", "-1"], "must be >= 0"),
                 (["--min_trusted_ratio", "-0.1"], "between 0 and 1"),
                 (["--min_trusted_ratio", "1.1"], "between 0 and 1"),
                 (["--min_trusted_ratio", "nan"], "between 0 and 1"),
                 (["--min_partition_stability", "-0.1"], "between 0 and 1"),
                 (["--min_partition_stability", "1.1"], "between 0 and 1"),
                 (["--min_partition_stability", "nan"], "between 0 and 1"),
                 (["--stability_window", "1"], "must be >= 2"),
                 (["--root_method", "outgroup"], "requires --outgroup")]
        for options, message in cases:
            errors = []
            for command in ("phylogeny", "clones"):
                with self.subTest(command=command, options=options), patch.object(cli.subprocess, "run") as run:
                    error = io.StringIO()
                    with redirect_stderr(error), self.assertRaises(SystemExit):
                        cli.run_clone_classification(self.args(command, *options), self.tree)
                    self.assertIn(message, error.getvalue())
                    errors.append(error.getvalue())
                    run.assert_not_called()
            self.assertEqual(*errors)
        for command in ("phylogeny", "clones"):
            with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                self.args(command, "--root_method", "invalid")

    def test_outgroup_precedence_without_changing_recorded_options(self):
        for command in ("phylogeny", "clones"):
            for method in ("midpoint", "none", "outgroup"):
                args = self.args(command, "--root_method", method, "--outgroup", "Ref", "Other")
                with self.subTest(command=command, method=method), patch.object(cli.subprocess, "run") as run:
                    cli.run_clone_classification(args, self.tree)
                    self.assertEqual(run.call_args.args[0][10:12], ["outgroup", "Ref,Other"])
                    self.assertEqual(args.root_method, method)

    def test_shared_r_command_explicit_path_spaces_and_no_iqtree(self):
        args = self.args("clones", "--clone_cut_mode", "manual", "--clone_cut_threshold", "0.12",
                         "--uf_support_threshold", "91", "--sh_support_threshold", "76",
                         "--branch_cut_min", "0.02", "--branch_cut_max", "0.42",
                         "--branch_cut_step", "0.02", "--min_tips", "4",
                         "--min_trusted_ratio", "0.8", "--min_partition_stability", "0.9",
                         "--stability_window", "5", "--outgroup", "Ref")
        with (
            patch.object(cli, "iqtree2_command", side_effect=AssertionError("IQ-TREE reached")),
            patch.object(cli, "generate_script", side_effect=AssertionError("IQ-TREE script reached")),
            patch.object(cli, "run_filter", side_effect=AssertionError("Filtering reached")),
            patch.object(cli, "run_clone_classification", wraps=cli.run_clone_classification) as shared,
            patch.object(cli.subprocess, "run") as run,
        ):
            cli.run_clones(args)
            shared.assert_called_once_with(args, self.tree.resolve())
            run.assert_called_once_with([
                "Rscript", str(cli.SCRIPTS_DIR / "BranchSupportCut.R"),
                str(self.output.resolve()) + os.sep, "sample", "91", "76",
                "0.02", "0.42", "0.02", "4", "outgroup", "Ref", "manual", "0.12",
                "0.8", "0.9", "5", str(self.tree.resolve())], check=True)
        self.assertFalse(list(self.output.glob("*_iqtree2.sh")))

    def test_phylogeny_infers_then_delegates_actual_alignment_tree(self):
        args = self.args("phylogeny")
        iq = ["/fixture/iqtree", "-s", str(self.fasta)]
        events = []
        with (
            patch.object(cli, "iqtree2_command", return_value=iq) as build,
            patch.object(cli.subprocess, "run", side_effect=lambda *a, **k: events.append("iqtree")) as run,
            patch.object(cli, "run_clone_classification", side_effect=lambda *a: events.append("clones")) as shared,
        ):
            cli.run_phylogeny(args)
            self.assertEqual(events, ["iqtree", "clones"])
            run.assert_called_once_with(iq, check=True)
            shared.assert_called_once_with(args, Path(str(self.fasta) + ".treefile"))
            self.assertEqual(build.call_args.kwargs["model"], "TEST")
            self.assertEqual(build.call_args.kwargs["uf_bootstrap"], 1000)
            self.assertEqual(build.call_args.kwargs["sh_alrt"], 1000)
            self.assertEqual(build.call_args.kwargs["threads"], 1)
        self.assertTrue((self.output / "sample_iqtree2.sh").is_file())

    def test_shared_runner_preserves_phylogeny_output_path_resolution(self):
        args = self.args("phylogeny")
        # A quoted tilde is a literal component in the existing phylogeny route.
        # Mock mkdir so this path regression never creates a real directory.
        args.output_directory = "~/literal output"
        expected = str(Path(args.output_directory).resolve()) + os.sep
        with patch.object(Path, "mkdir"), patch.object(cli.subprocess, "run") as run:
            cli.run_clone_classification(args, self.tree)
        self.assertEqual(run.call_args.args[0][2], expected)

    def test_iqtree_failure_never_reaches_clones(self):
        iq = ["/fixture/iqtree"]
        with (
            patch.object(cli, "iqtree2_command", return_value=iq),
            patch.object(cli.subprocess, "run", side_effect=subprocess.CalledProcessError(7, iq)),
            patch.object(cli, "run_clone_classification") as shared,
        ):
            with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
                cli.run_phylogeny(self.args("phylogeny"))
            self.assertEqual(error.exception.code, 7)
            shared.assert_not_called()

    def test_main_provenance_success_failure_never_executes_discovered_iqtree(self):
        def which(name):
            return {"Rscript": "/fixture/Rscript", "iqtree2": sys.executable}.get(name)
        for success in (True, False):
            dispatched = []
            def dispatch(cmd, **kwargs):
                dispatched.append(cmd)
                self.assertIn(cmd[0], ("git", "uname", "Rscript", "/fixture/Rscript"))
                if cmd[0] == "Rscript" and not success:
                    raise subprocess.CalledProcessError(7, cmd)
                return subprocess.CompletedProcess(cmd, 1 if cmd[0] == "git" else 0,
                                                   stdout="R provenance", stderr="")
            with (
                self.subTest(success=success),
                patch.object(runtime_info.shutil, "which", side_effect=which),
                patch.object(cli.subprocess, "run", side_effect=dispatch),
                patch.object(cli, "iqtree2_command", side_effect=AssertionError("IQ-TREE reached")),
            ):
                if success:
                    self.assertEqual(cli.main(self.argv()), 0)
                else:
                    with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
                        cli.main(self.argv())
                    self.assertEqual(error.exception.code, 7)
            records = [json.loads(p.read_text()) for p in self.output.glob("sample.runtime*.json")]
            record = next(r for r in records if r["success"] is success)
            self.assertEqual(record["command"], "clones")
            self.assertEqual(record["parameters"]["tree"], str(self.tree))
            for key, value in CLONE_DEFAULTS.items():
                self.assertEqual(record["parameters"][key], value)
            self.assertIn("spice_lineage/resources/r/BranchSupportCut.R", record["source_sha256"])
            self.assertEqual(record["R"]["returncode"], 0)
            iq = record["executables"]["IQ-TREE"]
            self.assertEqual(iq["path"], str(Path(sys.executable).resolve()))
            self.assertIn("sha256", iq)
            self.assertNotIn("version_probe", iq)
            self.assertEqual(sum(cmd[0] == "Rscript" for cmd in dispatched), 1)


if __name__ == "__main__":
    unittest.main()
