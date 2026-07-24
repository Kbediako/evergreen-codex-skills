from __future__ import annotations

import codecs
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from datetime import datetime
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "build_context_bundle.py"


def load_helper():
    spec = importlib.util.spec_from_file_location("build_context_bundle_under_test", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not import {SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


HELPER = load_helper()


def create_file_symlink(link: Path, target: Path) -> None:
    try:
        link.symlink_to(target)
    except OSError as error:
        raise unittest.SkipTest(f"Could not create file symlink: {error}") from error


def create_directory_redirect(link: Path, target: Path) -> None:
    if os.name == "nt":
        result = subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(link), str(target)],
            text=True,
            capture_output=True,
            check=False,
        )
        if result.returncode != 0:
            raise unittest.SkipTest(result.stderr or result.stdout)
    else:
        try:
            link.symlink_to(target, target_is_directory=True)
        except OSError as error:
            raise unittest.SkipTest(f"Could not create directory symlink: {error}") from error


def remove_directory_redirect(link: Path) -> None:
    if not os.path.lexists(link):
        return
    os.rmdir(link) if os.name == "nt" else link.unlink()


class BundleCliTests(unittest.TestCase):
    def run_cli(
        self,
        root: Path,
        *args: str,
        add_default_prompt: bool = True,
        env: dict[str, str] | None = None,
    ) -> tuple[subprocess.CompletedProcess[str], dict]:
        command = [sys.executable, str(SCRIPT), "--root", str(root)]
        if add_default_prompt and not {"--question", "--prompt-file", "--question-file"}.intersection(args):
            command.extend(["--question", "Test question."])
        command.extend(args)
        result = subprocess.run(
            command,
            cwd=root,
            text=True,
            capture_output=True,
            check=False,
            encoding="utf-8",
            env=env,
        )
        try:
            payload = json.loads(result.stdout)
        except json.JSONDecodeError as error:
            self.fail(f"stdout was not one JSON object:\n{result.stdout}\nstderr:\n{result.stderr}\n{error}")
        return result, payload

    def manifest(self, payload: dict) -> dict:
        return json.loads(Path(payload["manifest"]).read_text(encoding="utf-8"))

    def init_git_repo(self, root: Path) -> None:
        if shutil.which("git") is None:
            self.skipTest("git is unavailable")
        for command in (
            ["git", "init", "--quiet"],
            ["git", "add", "good.txt"],
            [
                "git",
                "-c",
                "user.name=Bundle Tests",
                "-c",
                "user.email=bundle-tests@example.invalid",
                "commit",
                "--quiet",
                "-m",
                "baseline",
            ],
        ):
            result = subprocess.run(command, cwd=root, text=True, capture_output=True, check=False)
            self.assertEqual(result.returncode, 0, result.stderr)

    def git_porcelain(self, root: Path) -> str:
        result = subprocess.run(
            ["git", "status", "--porcelain", "--untracked-files=all"],
            cwd=root,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout

    def test_happy_path_preserves_bytes_zip_and_provenance(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "src" / "sample.txt"
            source.parent.mkdir()
            original = b"alpha\r\nomega"
            source.write_bytes(original)

            result, payload = self.run_cli(
                root,
                "--out",
                ".codex-consults/custom",
                "--title",
                "Happy path",
                "--include",
                "src/sample.txt",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(payload["status"], "complete")
            manifest = self.manifest(payload)
            self.assertEqual(manifest["schema_version"], 4)
            self.assertEqual(manifest["filesystem_security"]["model"], "best-effort")
            self.assertFalse(manifest["filesystem_security"]["owner_only_modes_enforced"])
            self.assertFalse(manifest["discovery"]["traversal_stopped"])
            entry = manifest["included"][0]
            self.assertEqual(entry["path"], "src/sample.txt")
            self.assertEqual(entry["canonical_path"], "src/sample.txt")
            self.assertEqual(entry["requested_include"], "src/sample.txt")
            self.assertEqual(entry["sha256"], hashlib.sha256(original).hexdigest())
            self.assertEqual((Path(payload["bundle_dir"]) / entry["bundle_path"]).read_bytes(), original)
            with zipfile.ZipFile(payload["zip"]) as archive:
                self.assertEqual(archive.read(entry["bundle_path"]), original)
                self.assertIn("CONSULT_PACKET.md", archive.namelist())
                self.assertIn("manifest.json", archive.namelist())
            packet = Path(payload["packet"]).read_bytes()
            self.assertIn(b"alpha\r\nomega\n```", packet)
            self.assertNotIn(b"alpha\r\nomega\n\n```", packet)

    def test_prompt_validation_is_nonoverridable_and_has_honest_provenance(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "good.txt").write_text("good", encoding="utf-8")
            (root / "blank.md").write_text(" \n", encoding="utf-8")
            (root / "binary.bin").write_bytes(b"\x00\x01")
            (root / "large.md").write_text("too large", encoding="utf-8")
            cases = (
                (("--title", "No prompt", "--include", "good.txt"), "missing-prompt"),
                (
                    ("--title", "Blank inline", "--question", " ", "--include", "good.txt"),
                    "blank-prompt",
                ),
                (
                    (
                        "--title",
                        "Missing file",
                        "--prompt-file",
                        "missing.md",
                        "--include",
                        "good.txt",
                        "--allow-partial",
                    ),
                    "invalid-prompt",
                ),
                (
                    (
                        "--title",
                        "Blank file",
                        "--prompt-file",
                        "blank.md",
                        "--include",
                        "good.txt",
                        "--allow-partial",
                    ),
                    "invalid-prompt",
                ),
                (
                    (
                        "--title",
                        "Binary file",
                        "--prompt-file",
                        "binary.bin",
                        "--include",
                        "good.txt",
                        "--allow-partial",
                    ),
                    "invalid-prompt",
                ),
                (
                    (
                        "--title",
                        "Large file",
                        "--prompt-file",
                        "large.md",
                        "--include",
                        "good.txt",
                        "--max-file-bytes",
                        "3",
                        "--allow-partial",
                    ),
                    "invalid-prompt",
                ),
            )
            for args, expected in cases:
                with self.subTest(expected=expected):
                    result, payload = self.run_cli(root, *args, add_default_prompt=False)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertEqual(payload["error"], expected)
                    self.assertFalse((root / ".codex-consults").exists())
            result, payload = self.run_cli(
                root,
                "--title",
                "Missing provenance",
                "--prompt-file",
                "missing.md",
                "--include",
                "good.txt",
                add_default_prompt=False,
            )
            self.assertEqual(result.returncode, 1)
            self.assertEqual(payload["prompt"]["requested_path"], "missing.md")
            self.assertNotIn("canonical_path", payload["prompt"])

    def test_prompt_only_packets_are_complete_but_requested_evidence_cannot_fall_back(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            prompt_text = "Compare these two architecture options."
            prompt_file = root / "prompt.md"
            prompt_file.write_text(prompt_text, encoding="utf-8")

            inline, inline_payload = self.run_cli(
                root,
                "--title",
                "Inline prompt only",
                "--question",
                prompt_text,
            )
            self.assertEqual(inline.returncode, 0, inline.stderr)
            inline_manifest = self.manifest(inline_payload)
            self.assertEqual(inline_payload["status"], "complete")
            self.assertEqual(inline_manifest["included_count"], 0)
            self.assertEqual(inline_manifest["total_context_file_count"], 1)
            self.assertEqual(inline_manifest["total_context_bytes"], len(prompt_text.encode("utf-8")))
            self.assertEqual(inline_manifest["prompt"]["source"], "inline")
            self.assertEqual(inline_manifest["prompt"]["sha256"], hashlib.sha256(prompt_text.encode("utf-8")).hexdigest())
            self.assertEqual(inline_manifest["omission_counts"]["total"], 0)

            from_file, file_payload = self.run_cli(
                root,
                "--title",
                "File prompt only",
                "--prompt-file",
                "prompt.md",
                add_default_prompt=False,
            )
            self.assertEqual(from_file.returncode, 0, from_file.stderr)
            file_manifest = self.manifest(file_payload)
            self.assertEqual(file_manifest["included_count"], 0)
            self.assertEqual(file_manifest["total_context_file_count"], 1)
            self.assertEqual(file_manifest["prompt"]["requested_path"], "prompt.md")
            self.assertEqual(file_manifest["prompt"]["canonical_path"], "prompt.md")
            self.assertEqual(file_manifest["prompt"]["bytes"], len(prompt_text.encode("utf-8")))
            self.assertEqual(file_manifest["question_files"], [file_manifest["prompt"]])

            outputs_before_failure = {
                path.relative_to(root).as_posix()
                for path in root.rglob("*")
            }
            missing, missing_payload = self.run_cli(
                root,
                "--title",
                "Missing requested evidence",
                "--question",
                prompt_text,
                "--include",
                "missing.md",
                "--allow-partial",
            )
            self.assertEqual(missing.returncode, 1)
            self.assertEqual(missing_payload["error"], "zero-usable-context")
            self.assertEqual(
                {
                    path.relative_to(root).as_posix()
                    for path in root.rglob("*")
                },
                outputs_before_failure,
            )

            oversized, oversized_payload = self.run_cli(
                root,
                "--title",
                "Oversized prompt only",
                "--question",
                prompt_text,
                "--max-file-bytes",
                "8",
            )
            self.assertEqual(oversized.returncode, 1)
            self.assertEqual(oversized_payload["error"], "invalid-prompt")

    def test_prompt_symlink_is_authoritative_deduplicated_and_provenanced(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            prompt = root / "prompt.md"
            prompt.write_text("Review the evidence.", encoding="utf-8")
            prompt_alias = root / "prompt-alias.md"
            evidence_alias = root / "evidence-alias.md"
            create_file_symlink(prompt_alias, prompt)
            create_file_symlink(evidence_alias, prompt)
            (root / "good.txt").write_text("good", encoding="utf-8")

            result, payload = self.run_cli(
                root,
                "--title",
                "Prompt alias",
                "--prompt-file",
                "prompt-alias.md",
                "--include",
                "evidence-alias.md",
                "--include",
                "good.txt",
                add_default_prompt=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            manifest = self.manifest(payload)
            self.assertEqual(manifest["prompt"]["path"], "prompt-alias.md")
            self.assertEqual(manifest["prompt"]["requested_path"], "prompt-alias.md")
            self.assertEqual(manifest["prompt"]["canonical_path"], "prompt.md")
            self.assertEqual([item["path"] for item in manifest["included"]], ["good.txt"])
            self.assertEqual(
                manifest["omission_counts"]["by_reason"]["prompt-source-deduplicated"],
                1,
            )
            deduplicated = next(
                item
                for item in manifest["omitted"]
                if item["reason"] == "prompt-source-deduplicated"
            )
            self.assertEqual(deduplicated["path"], "evidence-alias.md")
            self.assertEqual(deduplicated["detail"]["prompt_requested_path"], "prompt-alias.md")
            self.assertEqual(deduplicated["detail"]["canonical_path"], "prompt.md")

    def test_exact_file_symlink_records_requested_and_canonical_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            target = root / "evidence.txt"
            target.write_bytes(b"canonical evidence")
            first_alias = root / "alias-a.txt"
            second_alias = root / "alias-b.txt"
            create_file_symlink(first_alias, target)
            create_file_symlink(second_alias, target)

            result, payload = self.run_cli(
                root,
                "--title",
                "Evidence alias",
                "--include",
                "alias-a.txt",
                "--include",
                "alias-b.txt",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            manifest = self.manifest(payload)
            entry = manifest["included"][0]
            self.assertEqual(entry["path"], "alias-a.txt")
            self.assertEqual(entry["requested_include"], "alias-a.txt")
            self.assertEqual(entry["canonical_path"], "evidence.txt")
            self.assertEqual(
                (Path(payload["bundle_dir"]) / entry["bundle_path"]).read_bytes(),
                target.read_bytes(),
            )
            deduplicated = next(
                item
                for item in manifest["omitted"]
                if item["reason"] == "canonical-target-deduplicated"
            )
            self.assertEqual(deduplicated["path"], "alias-b.txt")
            self.assertEqual(deduplicated["detail"]["kept_path"], "alias-a.txt")
            self.assertEqual(deduplicated["detail"]["canonical_path"], "evidence.txt")

    def test_outside_file_symlink_requires_explicit_allowance(self) -> None:
        with tempfile.TemporaryDirectory() as temp, tempfile.TemporaryDirectory() as outside_temp:
            root = Path(temp)
            outside = Path(outside_temp) / "outside.txt"
            outside.write_text("outside", encoding="utf-8")
            first_alias = root / "outside-alias-a.txt"
            second_alias = root / "outside-alias-b.txt"
            create_file_symlink(first_alias, outside)
            create_file_symlink(second_alias, outside)
            (root / "good.txt").write_text("good", encoding="utf-8")

            denied, denied_payload = self.run_cli(
                root,
                "--title",
                "Denied outside",
                "--include",
                "outside-alias-a.txt",
                "--include",
                "outside-alias-b.txt",
                "--include",
                "good.txt",
            )
            self.assertEqual(denied.returncode, 1)
            self.assertEqual(denied_payload["error"], "critical-omissions")
            outside_omissions = [
                item
                for item in denied_payload["critical_omissions"]
                if item["reason"] == "outside-root"
            ]
            self.assertEqual(
                {item["path"] for item in outside_omissions},
                {"outside-alias-a.txt", "outside-alias-b.txt"},
            )
            self.assertTrue(
                all(item["detail"]["canonical_path"] == outside.as_posix() for item in outside_omissions)
            )

            allowed, allowed_payload = self.run_cli(
                root,
                "--title",
                "Allowed outside",
                "--include",
                "outside-alias-a.txt",
                "--allow-outside-root",
            )
            self.assertEqual(allowed.returncode, 0, allowed.stderr)
            entry = self.manifest(allowed_payload)["included"][0]
            self.assertEqual(entry["path"], "outside-alias-a.txt")
            self.assertEqual(entry["canonical_path"], outside.as_posix())

    def test_directory_redirect_is_pruned_as_a_critical_explicit_omission(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            target = root / "real-dir"
            target.mkdir()
            (target / "secret.txt").write_text("secret", encoding="utf-8")
            redirect = root / "redirect"
            create_directory_redirect(redirect, target)
            (root / "good.txt").write_text("good", encoding="utf-8")
            try:
                result, payload = self.run_cli(
                    root,
                    "--title",
                    "Directory redirect",
                    "--include",
                    "redirect",
                    "--include",
                    "good.txt",
                    "--allow-partial",
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(payload["status"], "partial")
                manifest = self.manifest(payload)
                self.assertEqual([item["path"] for item in manifest["included"]], ["good.txt"])
                self.assertIn(
                    "direct-directory-redirect",
                    manifest["omission_counts"]["by_reason"],
                )
            finally:
                remove_directory_redirect(redirect)

    def test_explicit_directory_preserves_noise_and_generated_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            chosen = root / "chosen"
            for relative in ("build/a.txt", "vendor/b.txt", "target/c.txt", "keep.txt", "skip.txt"):
                path = chosen / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(relative, encoding="utf-8")
            archive = chosen / "generated.zip"
            archive.write_bytes(b"PK\x03\x04generated")
            vcs = chosen / ".git"
            vcs.mkdir()
            (vcs / "config").write_text("private", encoding="utf-8")

            explicit, explicit_payload = self.run_cli(
                root,
                "--title",
                "Explicit directory",
                "--include",
                "chosen",
                "--exclude",
                "skip",
                "--include-binary",
                "--allow-partial",
            )
            self.assertEqual(explicit.returncode, 0, explicit.stderr)
            self.assertEqual(explicit_payload["status"], "partial")
            manifest = self.manifest(explicit_payload)
            paths = {item["path"] for item in manifest["included"]}
            self.assertEqual(
                paths,
                {
                    "chosen/build/a.txt",
                    "chosen/vendor/b.txt",
                    "chosen/target/c.txt",
                    "chosen/keep.txt",
                    "chosen/generated.zip",
                },
            )
            self.assertTrue(
                all(item["source"] == "explicit-dir" for item in manifest["included"])
            )
            self.assertTrue(
                all(item["requested_include"] == "chosen" for item in manifest["included"])
            )
            self.assertIn("vcs-metadata-excluded", manifest["omission_counts"]["by_reason"])

            broad, broad_payload = self.run_cli(
                root,
                "--title",
                "Whole repo",
                "--whole-repo",
                "--exclude",
                "skip",
            )
            self.assertEqual(broad.returncode, 0, broad.stderr)
            broad_manifest = self.manifest(broad_payload)
            broad_paths = {item["path"] for item in broad_manifest["included"]}
            self.assertEqual(broad_paths, {"chosen/keep.txt"})
            self.assertIn("default-noise-excluded", broad_manifest["omission_counts"]["by_reason"])
            self.assertIn("generated-file-excluded", broad_manifest["omission_counts"]["by_reason"])

    def test_include_exclude_conflict_fails_before_output(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "secret.txt").write_text("secret", encoding="utf-8")
            result, payload = self.run_cli(
                root,
                "--title",
                "Conflict",
                "--include",
                "secret.txt",
                "--exclude",
                "secret",
            )
            self.assertEqual(result.returncode, 2)
            self.assertEqual(payload["error"], "include-exclude-conflict")
            self.assertFalse((root / ".codex-consults").exists())

    def test_large_snapshot_is_bounded_deterministic_and_aggregated(self) -> None:
        with tempfile.TemporaryDirectory() as temp, tempfile.TemporaryDirectory() as strict_temp:
            root = Path(temp)
            (root / "anchor.txt").write_text("deterministic anchor", encoding="utf-8")
            snapshots = []
            for name, indexes in (
                ("snapshot-forward", range(200)),
                ("snapshot-reverse", reversed(range(200))),
            ):
                snapshot = root / name
                snapshot.mkdir()
                for index in indexes:
                    (snapshot / f"{index:04}.txt").write_text(str(index), encoding="utf-8")
                snapshots.append(snapshot)

            manifests = []
            for snapshot in snapshots:
                result, payload = self.run_cli(
                    root,
                    "--title",
                    f"Bounded {snapshot.name}",
                    "--include",
                    "anchor.txt",
                    "--include",
                    snapshot.name,
                    "--max-files",
                    "5",
                    "--max-omitted",
                    "0",
                    "--allow-partial",
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertLess(len(result.stdout.encode("utf-8")), 20_000)
                manifest = self.manifest(payload)
                self.assertLess(Path(payload["manifest"]).stat().st_size, 30_000)
                manifests.append(manifest)
                discovery = manifest["discovery"]
                self.assertEqual(discovery["entry_limit"], 64)
                self.assertEqual(discovery["entries_examined"], 64)
                self.assertEqual(discovery["candidates_retained"], 1)
                self.assertEqual(discovery["discarded_entries_lower_bound"], 65)
                self.assertTrue(discovery["traversal_stopped"])
                self.assertEqual(discovery["stopped_sources"], ["explicit-dir"])
                self.assertLessEqual(len(discovery["stop_samples"]), 5)
                self.assertEqual(
                    [item["path"] for item in manifest["included"]],
                    ["anchor.txt"],
                )
                self.assertEqual(
                    manifest["omission_counts"]["represented_paths_count_kind"],
                    "lower-bound",
                )
                traversal = next(
                    item
                    for item in manifest["critical_omissions"]
                    if item["reason"] == "discovery-entry-limit"
                )
                self.assertEqual(traversal["detail"]["count_lower_bound"], 65)

            self.assertEqual(
                [item["path"] for item in manifests[0]["included"]],
                [item["path"] for item in manifests[1]["included"]],
            )
            strict_out = Path(strict_temp) / "strict-output"
            strict, strict_payload = self.run_cli(
                root,
                "--out",
                str(strict_out),
                "--title",
                "Bounded strict",
                "--include",
                "anchor.txt",
                "--include",
                "snapshot-forward",
                "--max-files",
                "5",
            )
            self.assertEqual(strict.returncode, 1)
            self.assertEqual(strict_payload["error"], "critical-omissions")
            self.assertTrue(strict_payload["discovery"]["traversal_stopped"])
            self.assertFalse(strict_out.exists())

    def test_repetitive_broad_failures_are_aggregated(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            snapshot = root / "snapshot"
            snapshot.mkdir()
            (snapshot / "good.txt").write_text("usable", encoding="utf-8")
            for index in range(300):
                (snapshot / f"{index:04}.bin").write_bytes(b"\x00")

            result, payload = self.run_cli(
                root,
                "--title",
                "Aggregate broad failures",
                "--include",
                "snapshot",
                "--include",
                "snapshot",
                "--max-files",
                "500",
                "--max-omitted",
                "0",
                "--allow-partial",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertLess(len(result.stdout.encode("utf-8")), 20_000)
            manifest = self.manifest(payload)
            self.assertLess(Path(payload["manifest"]).stat().st_size, 30_000)
            self.assertEqual(manifest["discovery"]["entries_examined"], 301)
            self.assertEqual(manifest["discovery"]["candidates_retained"], 301)
            self.assertFalse(manifest["discovery"]["traversal_stopped"])
            aggregates = [
                item
                for item in manifest["critical_omissions"]
                if item["reason"] == "binary-not-included"
            ]
            self.assertEqual(len(aggregates), 1)
            detail = aggregates[0]["detail"]
            self.assertTrue(detail["aggregated"])
            self.assertEqual(detail["count_kind"], "exact")
            self.assertEqual(detail["count"], 300)
            self.assertLessEqual(len(detail["samples"]), 5)
            self.assertEqual(
                len({sample["path"] for sample in detail["samples"]}),
                len(detail["samples"]),
            )

    def test_exact_failures_remain_complete_after_broad_traversal_stops(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            snapshot = root / "snapshot"
            snapshot.mkdir()
            (root / "anchor.txt").write_text("usable", encoding="utf-8")
            for index in range(200):
                (snapshot / f"{index:04}.txt").write_text("x", encoding="utf-8")
            missing = [f"missing-{index:02}.txt" for index in range(20)]
            args = [
                "--title",
                "Complete exact failures",
                "--include",
                "anchor.txt",
                "--include",
                "snapshot",
                "--max-files",
                "3",
                "--max-omitted",
                "0",
                "--allow-partial",
            ]
            for path in missing:
                args.extend(["--include", path])

            result, payload = self.run_cli(root, *args)

            self.assertEqual(result.returncode, 0, result.stderr)
            manifest = self.manifest(payload)
            reported = {
                item["path"]
                for item in manifest["critical_omissions"]
                if item["reason"] == "missing"
            }
            self.assertEqual(reported, set(missing))
            self.assertTrue(manifest["discovery"]["traversal_stopped"])

    def test_limits_are_strict_partial_or_zero_context_as_requested(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "good.txt").write_text("good", encoding="utf-8")
            (root / "large.txt").write_text("x" * 100, encoding="utf-8")

            strict, strict_payload = self.run_cli(
                root,
                "--title",
                "Strict limits",
                "--include",
                "good.txt",
                "--include",
                "large.txt",
                "--max-file-bytes",
                "20",
            )
            self.assertEqual(strict.returncode, 1)
            self.assertEqual(strict_payload["error"], "critical-omissions")
            self.assertFalse((root / ".codex-consults").exists())

            partial, partial_payload = self.run_cli(
                root,
                "--title",
                "Partial limits",
                "--include",
                "good.txt",
                "--include",
                "large.txt",
                "--max-file-bytes",
                "20",
                "--allow-partial",
            )
            self.assertEqual(partial.returncode, 0, partial.stderr)
            self.assertEqual(partial_payload["status"], "partial")
            self.assertEqual(
                [item["path"] for item in self.manifest(partial_payload)["included"]],
                ["good.txt"],
            )

        with tempfile.TemporaryDirectory() as zero_temp:
            root = Path(zero_temp)
            (root / "large.txt").write_text("x" * 100, encoding="utf-8")
            zero, zero_payload = self.run_cli(
                root,
                "--title",
                "Zero context",
                "--include",
                "large.txt",
                "--max-file-bytes",
                "20",
                "--allow-partial",
            )
            self.assertEqual(zero.returncode, 1)
            self.assertEqual(zero_payload["error"], "zero-usable-context")
            self.assertFalse((root / ".codex-consults").exists())

    def test_binary_requires_opt_in_and_is_copied_exactly(self) -> None:
        data = b"\x89PNG\r\n\x1a\n\x00binary"
        with tempfile.TemporaryDirectory() as denied_temp:
            root = Path(denied_temp)
            (root / "image.png").write_bytes(data)
            denied, payload = self.run_cli(
                root,
                "--title",
                "Binary denied",
                "--include",
                "image.png",
            )
            self.assertEqual(denied.returncode, 1)
            self.assertEqual(payload["error"], "zero-usable-context")

        with tempfile.TemporaryDirectory() as allowed_temp:
            root = Path(allowed_temp)
            (root / "image.png").write_bytes(data)
            allowed, payload = self.run_cli(
                root,
                "--title",
                "Binary allowed",
                "--include",
                "image.png",
                "--include-binary",
            )
            self.assertEqual(allowed.returncode, 0, allowed.stderr)
            entry = self.manifest(payload)["included"][0]
            self.assertEqual(entry["kind"], "binary")
            self.assertEqual((Path(payload["bundle_dir"]) / entry["bundle_path"]).read_bytes(), data)

    def test_default_git_output_marker_is_simple_semantic_and_clean(self) -> None:
        for marker_data in (None, b"# generated consultations\n*\n"):
            with self.subTest(marker_data=marker_data), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                (root / "good.txt").write_text("good", encoding="utf-8")
                self.init_git_repo(root)
                marker = root / ".codex-consults" / ".gitignore"
                if marker_data is not None:
                    marker.parent.mkdir()
                    marker.write_bytes(marker_data)

                result, payload = self.run_cli(
                    root,
                    "--title",
                    "Git default output",
                    "--include",
                    "good.txt",
                )

                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertTrue(Path(payload["bundle_dir"]).is_dir())
                self.assertTrue(marker.is_file())
                if marker_data is not None:
                    self.assertEqual(marker.read_bytes(), marker_data)
                self.assertEqual(self.git_porcelain(root), "")

    def test_ineffective_marker_fails_and_rolls_back(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "good.txt").write_text("good", encoding="utf-8")
            self.init_git_repo(root)
            output = root / ".codex-consults"
            output.mkdir()
            marker = output / ".gitignore"
            marker.write_text("# comments only\n", encoding="utf-8")

            result, payload = self.run_cli(
                root,
                "--title",
                "Ineffective marker",
                "--include",
                "good.txt",
            )

            self.assertEqual(result.returncode, 1)
            self.assertEqual(payload["error"], "unsafe-output-ignore")
            self.assertEqual(payload["marker_state"], "not-ignored")
            self.assertEqual([item.name for item in output.iterdir()], [".gitignore"])
            self.assertEqual(marker.read_text(encoding="utf-8"), "# comments only\n")

    def test_explicit_in_repo_output_must_already_be_git_ignored(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "good.txt").write_text("good", encoding="utf-8")
            self.init_git_repo(root)
            output = root / "generated" / "consults"

            denied, denied_payload = self.run_cli(
                root,
                "--out",
                "generated/consults",
                "--title",
                "Unignored explicit output",
                "--include",
                "good.txt",
            )
            self.assertEqual(denied.returncode, 1)
            self.assertEqual(denied_payload["error"], "unsafe-output-ignore")
            self.assertFalse((root / "generated").exists())

            (root / ".gitignore").write_text("/generated/\n", encoding="utf-8")
            allowed, allowed_payload = self.run_cli(
                root,
                "--out",
                "generated/consults",
                "--title",
                "Ignored explicit output",
                "--include",
                "good.txt",
            )
            self.assertEqual(allowed.returncode, 0, allowed.stderr)
            self.assertTrue(Path(allowed_payload["bundle_dir"]).is_dir())
            self.assertFalse((output / ".gitignore").exists())

    def test_custom_output_uses_its_own_worktree_ignore_rules(self) -> None:
        with tempfile.TemporaryDirectory() as source_temp, tempfile.TemporaryDirectory() as output_temp:
            root = Path(source_temp)
            output_repo = Path(output_temp)
            (root / "good.txt").write_text("good", encoding="utf-8")
            (output_repo / "good.txt").write_text("baseline", encoding="utf-8")
            self.init_git_repo(output_repo)
            output = output_repo / "generated" / "consults"

            denied, denied_payload = self.run_cli(
                root,
                "--out",
                str(output),
                "--title",
                "Different worktree denied",
                "--include",
                "good.txt",
            )
            self.assertEqual(denied.returncode, 1)
            self.assertEqual(denied_payload["error"], "unsafe-output-ignore")
            self.assertFalse((output_repo / "generated").exists())
            self.assertEqual(self.git_porcelain(output_repo), "")

            (output_repo / ".gitignore").write_text("/generated/\n", encoding="utf-8")
            for command in (
                ["git", "add", ".gitignore"],
                [
                    "git",
                    "-c",
                    "user.name=Bundle Tests",
                    "-c",
                    "user.email=bundle-tests@example.invalid",
                    "commit",
                    "--quiet",
                    "-m",
                    "ignore generated output",
                ],
            ):
                commit = subprocess.run(
                    command,
                    cwd=output_repo,
                    text=True,
                    capture_output=True,
                    check=False,
                )
                self.assertEqual(commit.returncode, 0, commit.stderr)

            allowed, allowed_payload = self.run_cli(
                root,
                "--out",
                str(output),
                "--title",
                "Different worktree allowed",
                "--include",
                "good.txt",
            )
            self.assertEqual(allowed.returncode, 0, allowed.stderr)
            self.assertTrue(Path(allowed_payload["bundle_dir"]).is_dir())
            self.assertEqual(self.git_porcelain(output_repo), "")

    def test_git_unavailable_distinguishes_custom_worktree_from_plain_output(self) -> None:
        no_git_env = os.environ.copy()
        no_git_env["PATH"] = ""
        with tempfile.TemporaryDirectory() as repo_temp:
            root = Path(repo_temp)
            (root / "good.txt").write_text("good", encoding="utf-8")
            self.init_git_repo(root)

            denied, denied_payload = self.run_cli(
                root,
                "--out",
                "generated/consults",
                "--title",
                "Unavailable Git in worktree",
                "--include",
                "good.txt",
                env=no_git_env,
            )
            self.assertEqual(denied.returncode, 1)
            self.assertEqual(denied_payload["error"], "unsafe-output-ignore")
            self.assertEqual(denied_payload["marker_state"], "git-unavailable")
            self.assertFalse((root / "generated").exists())
            self.assertEqual(self.git_porcelain(root), "")

            defaulted, defaulted_payload = self.run_cli(
                root,
                "--title",
                "Unavailable Git with helper marker",
                "--include",
                "good.txt",
                env=no_git_env,
            )
            self.assertEqual(defaulted.returncode, 0, defaulted.stderr)
            self.assertEqual((root / ".codex-consults" / ".gitignore").read_bytes(), HELPER.OUTPUT_GITIGNORE)
            self.assertTrue(Path(defaulted_payload["bundle_dir"]).is_dir())
            self.assertEqual(self.git_porcelain(root), "")

        with tempfile.TemporaryDirectory() as marker_temp:
            root = Path(marker_temp)
            (root / "good.txt").write_text("good", encoding="utf-8")
            marker = root / ".codex-consults" / ".gitignore"
            marker.parent.mkdir()
            marker.write_text("# comments only\n", encoding="utf-8")
            self.init_git_repo(root)
            for command in (
                ["git", "add", "-f", ".codex-consults/.gitignore"],
                [
                    "git",
                    "-c",
                    "user.name=Bundle Tests",
                    "-c",
                    "user.email=bundle-tests@example.invalid",
                    "commit",
                    "--quiet",
                    "-m",
                    "track custom marker",
                ],
            ):
                commit = subprocess.run(
                    command,
                    cwd=root,
                    text=True,
                    capture_output=True,
                    check=False,
                )
                self.assertEqual(commit.returncode, 0, commit.stderr)

            denied, denied_payload = self.run_cli(
                root,
                "--title",
                "Unavailable Git with ineffective marker",
                "--include",
                "good.txt",
                env=no_git_env,
            )
            self.assertEqual(denied.returncode, 1)
            self.assertEqual(denied_payload["error"], "unsafe-output-ignore")
            self.assertEqual(denied_payload["marker_state"], "git-unavailable")
            self.assertEqual([path.name for path in marker.parent.iterdir()], [".gitignore"])
            self.assertEqual(marker.read_text(encoding="utf-8"), "# comments only\n")
            self.assertEqual(self.git_porcelain(root), "")

        with tempfile.TemporaryDirectory() as source_temp, tempfile.TemporaryDirectory() as output_temp:
            root = Path(source_temp)
            output = Path(output_temp) / "consult-output"
            (root / "good.txt").write_text("good", encoding="utf-8")

            allowed, allowed_payload = self.run_cli(
                root,
                "--out",
                str(output),
                "--title",
                "Unavailable Git outside worktree",
                "--include",
                "good.txt",
                env=no_git_env,
            )
            self.assertEqual(allowed.returncode, 0, allowed.stderr)
            self.assertTrue(Path(allowed_payload["bundle_dir"]).is_dir())

    def test_output_root_redirect_and_repo_root_are_rejected_preflight(self) -> None:
        with tempfile.TemporaryDirectory() as temp, tempfile.TemporaryDirectory() as outside_temp:
            root = Path(temp)
            outside = Path(outside_temp)
            (root / "good.txt").write_text("good", encoding="utf-8")
            redirect = root / ".codex-consults"
            create_directory_redirect(redirect, outside)
            try:
                redirected, payload = self.run_cli(
                    root,
                    "--title",
                    "Redirected output",
                    "--include",
                    "good.txt",
                )
                self.assertEqual(redirected.returncode, 2)
                self.assertEqual(payload["error"], "output-redirect")
                self.assertEqual(list(outside.iterdir()), [])
            finally:
                remove_directory_redirect(redirect)

            root_result, root_payload = self.run_cli(
                root,
                "--out",
                str(root),
                "--title",
                "Root output",
                "--include",
                "good.txt",
            )
            self.assertEqual(root_result.returncode, 2)
            self.assertEqual(root_payload["error"], "invalid-output")

    def test_explicit_absolute_outside_output_succeeds(self) -> None:
        with tempfile.TemporaryDirectory() as temp, tempfile.TemporaryDirectory() as output_temp:
            root = Path(temp)
            output = Path(output_temp) / "consult-output"
            (root / "good.txt").write_text("good", encoding="utf-8")
            result, payload = self.run_cli(
                root,
                "--out",
                str(output),
                "--title",
                "Outside output",
                "--include",
                "good.txt",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(Path(payload["bundle_dir"]).is_relative_to(output))
            self.assertFalse((root / ".codex-consults").exists())


class BundleUnitTests(unittest.TestCase):
    def test_mode_contract_and_schema_invariants(self) -> None:
        expected_markers = {
            "plan": "ordered implementation plan",
            "debug": "plausible root causes",
            "review": "material correctness",
            "consensus": "competing views",
        }
        closure = (
            "End with exactly one terminal closure verdict line: "
            "MATERIAL FEEDBACK REMAINS or NO MATERIAL FEEDBACK."
        )
        self.assertEqual(set(HELPER.MODE_RESPONSE_CONTRACTS), set(expected_markers))
        for mode, marker in expected_markers.items():
            contract = HELPER.MODE_RESPONSE_CONTRACTS[mode]
            self.assertTrue(any(marker in item for item in contract))
            self.assertEqual(contract[-1], closure)
        self.assertEqual(HELPER.MANIFEST_SCHEMA_VERSION, 4)
        self.assertEqual(HELPER.RESULT_SCHEMA_VERSION, 1)

    def make_config(self, root: Path, out: Path | None = None) -> object:
        output = out or root / ".codex-consults"
        return HELPER.Config(
            root=root,
            out_logical=output,
            out_explicit=out is not None,
            mode="plan",
            title="Unit",
            question="Question",
            prompt_file=None,
            includes=["good.txt"],
            excludes=[],
            whole_repo=False,
            include_binary=False,
            allow_outside_root=False,
            allow_partial=False,
            max_files=10,
            max_file_bytes=10_000,
            max_total_bytes=10_000,
            max_omitted=10,
        )

    def make_entry(self, root: Path) -> object:
        data = b"good"
        return HELPER.CapturedFile(
            display_path="good.txt",
            canonical_path="good.txt",
            requested_include="good.txt",
            bundle_path="files/good.txt",
            source="explicit-file",
            kind="text",
            data=data,
            sha256=hashlib.sha256(data).hexdigest(),
            text="good",
            encoding="utf-8",
            language="text",
        )

    def test_scandir_error_is_a_complete_critical_omission(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve()
            omissions: list[dict] = []
            discovery = HELPER.DiscoveryState(entry_limit=64)
            with mock.patch.object(
                HELPER.os,
                "scandir",
                side_effect=PermissionError(13, "denied", str(root)),
            ):
                files = list(
                    HELPER.iter_dir_files(
                        root,
                        root,
                        "whole-repo",
                        [],
                        omissions,
                        [],
                        discovery=discovery,
                    )
                )
            self.assertEqual(files, [])
            self.assertEqual(len(omissions), 1)
            self.assertTrue(omissions[0]["critical"])
            self.assertEqual(omissions[0]["reason"], "traversal-error")
            self.assertEqual(omissions[0]["detail"]["error_type"], "PermissionError")

    def test_decoding_and_binary_classification_are_conservative(self) -> None:
        cases = (
            (codecs.BOM_UTF8 + "utf8".encode("utf-8"), "utf-8-bom"),
            (codecs.BOM_UTF16_LE + "little".encode("utf-16-le"), "utf-16-le-bom"),
            (codecs.BOM_UTF32_BE + "wide".encode("utf-32-be"), "utf-32-be-bom"),
        )
        for data, encoding in cases:
            with self.subTest(encoding=encoding):
                self.assertEqual(HELPER.read_text(data, Path("known.txt"))[1], encoding)
        self.assertEqual(HELPER.read_text(b"caf\xe9", Path("known.txt"))[1], "cp1252")
        self.assertIsNone(HELPER.read_text(b"caf\xe9", Path("unknown.bin")))
        self.assertIsNone(HELPER.classify_text(b"\x89PNG\x00<not-svg>", Path("fake.svg")))

    def test_read_failure_becomes_a_critical_exact_file_omission(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve()
            source = root / "good.txt"
            source.write_text("good", encoding="utf-8")
            config = self.make_config(root)
            omissions: list[dict] = []
            prompt = HELPER.capture_prompt(config, omissions)
            candidate = HELPER.Candidate(source, "explicit-file", "good.txt", "good.txt")
            with mock.patch.object(
                Path,
                "read_bytes",
                side_effect=PermissionError(13, "denied", str(source)),
            ):
                entries, _ = HELPER.capture_candidates(
                    config,
                    [candidate],
                    prompt,
                    omissions,
                    HELPER.DiscoveryState(entry_limit=64),
                )
            self.assertEqual(entries, [])
            self.assertEqual(omissions[-1]["reason"], "file-read-error")
            self.assertTrue(omissions[-1]["critical"])

    def test_staging_failure_cleans_temp_marker_and_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve()
            config = self.make_config(root)
            with mock.patch.object(HELPER, "write_zip", side_effect=OSError("zip failed")):
                with self.assertRaises(OSError):
                    HELPER.stage_and_publish(config, [self.make_entry(root)], "packet", {})
            self.assertFalse(config.out_logical.exists())
            self.assertFalse(any(path.name.startswith(HELPER.STAGING_DIR_PREFIX) for path in root.rglob("*")))

    def test_marker_creation_failures_clean_up_and_allow_a_clean_retry(self) -> None:
        if shutil.which("git") is None:
            self.skipTest("git is unavailable")

        def git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
            return subprocess.run(
                ["git", *args],
                cwd=root,
                text=True,
                capture_output=True,
                check=False,
            )

        def initialize_repo(root: Path) -> None:
            (root / "good.txt").write_text("good", encoding="utf-8")
            for args in (
                ("init", "--quiet"),
                ("add", "good.txt"),
                (
                    "-c",
                    "user.name=Bundle Tests",
                    "-c",
                    "user.email=bundle-tests@example.invalid",
                    "commit",
                    "--quiet",
                    "-m",
                    "baseline",
                ),
            ):
                result = git(root, *args)
                self.assertEqual(result.returncode, 0, result.stderr)

        real_open = Path.open
        real_lstat = Path.lstat

        for fault in ("write", "close", "post-write-lstat"):
            with self.subTest(fault=fault), tempfile.TemporaryDirectory() as temp:
                root = Path(temp).resolve()
                initialize_repo(root)
                config = self.make_config(root)
                marker = config.out_logical / ".gitignore"
                entry = self.make_entry(root)

                class FaultyMarker:
                    def __init__(self, stream) -> None:
                        self.stream = stream

                    def __enter__(self):
                        return self

                    def write(self, data: bytes) -> int:
                        if fault == "write":
                            raise OSError("marker write failed")
                        return self.stream.write(data)

                    def __exit__(self, exc_type, exc, traceback) -> bool:
                        self.stream.close()
                        if fault == "close" and exc_type is None:
                            raise OSError("marker close failed")
                        return False

                def open_with_fault(path: Path, mode: str = "r", *args, **kwargs):
                    stream = real_open(path, mode, *args, **kwargs)
                    if path == marker and mode == "xb":
                        return FaultyMarker(stream)
                    return stream

                marker_lstat_calls = 0

                def lstat_with_fault(path: Path):
                    nonlocal marker_lstat_calls
                    if path == marker:
                        marker_lstat_calls += 1
                        if fault == "post-write-lstat" and marker_lstat_calls == 2:
                            raise OSError("post-write marker inspection failed")
                    return real_lstat(path)

                with (
                    mock.patch.object(Path, "open", new=open_with_fault),
                    mock.patch.object(Path, "lstat", new=lstat_with_fault),
                ):
                    with self.assertRaises(OSError):
                        HELPER.stage_and_publish(config, [entry], "packet", {})

                self.assertFalse(config.out_logical.exists())
                self.assertFalse(any(path.name.startswith(HELPER.STAGING_DIR_PREFIX) for path in root.rglob("*")))
                status = git(root, "status", "--porcelain", "--untracked-files=all")
                self.assertEqual(status.returncode, 0, status.stderr)
                self.assertEqual(status.stdout, "")

                bundle_dir, zip_path, _, _ = HELPER.stage_and_publish(config, [entry], "packet", {})
                self.assertTrue(bundle_dir.is_dir())
                self.assertTrue(zip_path.is_file())
                status = git(root, "status", "--porcelain", "--untracked-files=all")
                self.assertEqual(status.returncode, 0, status.stderr)
                self.assertEqual(status.stdout, "")

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve()
            initialize_repo(root)
            config = self.make_config(root)
            config.out_logical.mkdir()
            marker = config.out_logical / ".gitignore"
            marker.write_bytes(HELPER.OUTPUT_GITIGNORE)
            original = marker.read_bytes()

            def reject_creation(path: Path, mode: str = "r", *args, **kwargs):
                if path == marker and mode == "xb":
                    raise OSError("exclusive marker creation should not run")
                return real_open(path, mode, *args, **kwargs)

            with mock.patch.object(Path, "open", new=reject_creation):
                HELPER.stage_and_publish(config, [self.make_entry(root)], "packet", {})

            self.assertEqual(marker.read_bytes(), original)
            status = git(root, "status", "--porcelain", "--untracked-files=all")
            self.assertEqual(status.returncode, 0, status.stderr)
            self.assertEqual(status.stdout, "")

    def test_mkdtemp_failure_cleans_new_nested_output_directories(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve()
            output = root / ".codex-consults" / "nested"
            config = self.make_config(root, output)
            with mock.patch.object(HELPER.tempfile, "mkdtemp", side_effect=OSError("failed")):
                with self.assertRaises(OSError):
                    HELPER.stage_and_publish(config, [self.make_entry(root)], "packet", {})
            self.assertFalse((root / ".codex-consults").exists())

    def test_second_publish_failure_rolls_back_first_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve()
            config = self.make_config(root)
            real_replace = HELPER.os.replace
            replace_count = 0

            def fail_second(source, destination):
                nonlocal replace_count
                replace_count += 1
                if replace_count == 2:
                    raise OSError("second publish failed")
                return real_replace(source, destination)

            with mock.patch.object(HELPER.os, "replace", side_effect=fail_second):
                with self.assertRaises(OSError):
                    HELPER.stage_and_publish(config, [self.make_entry(root)], "packet", {})
            self.assertEqual(replace_count, 2)
            self.assertFalse(config.out_logical.exists())

    def test_output_collision_preserves_preexisting_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve()
            config = self.make_config(root)
            output = config.out_logical
            output.mkdir()
            stamp = "20260102-030405-006000"
            final_bundle = output / f"{stamp}-unit"
            final_zip = output / f"{stamp}-unit.zip"
            final_bundle.mkdir()
            (final_bundle / "sentinel").write_text("keep", encoding="utf-8")
            final_zip.write_bytes(b"keep-zip")
            fake_datetime = mock.Mock()
            fake_datetime.now.return_value = datetime(2026, 1, 2, 3, 4, 5, 6000)

            with mock.patch.object(HELPER, "datetime", fake_datetime):
                with self.assertRaises(HELPER.BundleError) as caught:
                    HELPER.stage_and_publish(config, [self.make_entry(root)], "packet", {})

            self.assertEqual(caught.exception.error, "output-collision")
            self.assertEqual((final_bundle / "sentinel").read_text(encoding="utf-8"), "keep")
            self.assertEqual(final_zip.read_bytes(), b"keep-zip")
            self.assertEqual(
                sorted(path.name for path in output.iterdir()),
                [f"{stamp}-unit", f"{stamp}-unit.zip"],
            )


if __name__ == "__main__":
    unittest.main()
