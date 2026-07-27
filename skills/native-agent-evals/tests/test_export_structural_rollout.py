from __future__ import annotations

import copy
import hashlib
import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import contextmanager, redirect_stdout
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "export_structural_rollout.py"


def load_exporter():
    spec = importlib.util.spec_from_file_location(
        "export_structural_rollout_under_test",
        SCRIPT,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not import {SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


EXPORTER = load_exporter()


def jsonl_bytes(records: list[dict]) -> bytes:
    return "".join(
        json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n"
        for record in records
    ).encode("utf-8")


class StructuralExportTests(unittest.TestCase):
    def session(self, *, session_id: str = "session-root") -> dict:
        return {
            "type": "session_meta",
            "payload": {
                "session_id": session_id,
                "id": "session-record",
                "cwd": "C:/fixture",
                "cli_version": "0.145.0",
                "agent_role": "reviewer",
                "agent_path": "/root/run",
                "model_provider": "openai",
                "base_instructions": "NOT-PROJECTED-BASE-INSTRUCTIONS",
                "multi_agent_version": "v2",
                "context_window": 1000,
            },
        }

    def turn(
        self,
        turn_id: str = "turn-1",
        *,
        call_ids: tuple[str, ...] = ("call-1",),
        answer_blocks: tuple[str, ...] = ("Synthetic evidence includes REQUIRED.",),
        outputs: tuple[object, ...] | None = None,
    ) -> list[dict]:
        selected_outputs = outputs or tuple(f"output-{call_id}" for call_id in call_ids)
        records = [
            {
                "type": "turn_context",
                "payload": {
                    "turn_id": turn_id,
                    "cwd": "C:/fixture",
                    "approval_policy": "never",
                    "sandbox_policy": {"type": "fixture-sandbox"},
                    "permission_profile": {"type": "fixture-permissions"},
                    "model": "fixture-worker",
                    "effort": "high",
                    "summary": "NOT-PROJECTED-TURN-SUMMARY",
                },
            }
        ]
        for index, (call_id, output) in enumerate(zip(call_ids, selected_outputs, strict=True), 1):
            records.extend(
                [
                    {
                        "type": "response_item",
                        "payload": {
                            "type": "custom_tool_call",
                            "id": f"tool-{turn_id}-{index}",
                            "status": "completed",
                            "call_id": call_id,
                            "name": "fixture_read",
                            "namespace": "fixture",
                            "input": {
                                "path": f"C:/fixture/{index}.txt",
                                "ordinal": index,
                            },
                        },
                    },
                    {
                        "type": "response_item",
                        "payload": {
                            "type": "custom_tool_call_output",
                            "id": f"output-{turn_id}-{index}",
                            "call_id": call_id,
                            "output": output,
                        },
                    },
                ]
            )
        answer = "".join(answer_blocks)
        records.extend(
            [
                {
                    "type": "response_item",
                    "payload": {
                        "type": "reasoning",
                        "id": f"reasoning-{turn_id}",
                        "summary": ["NOT-PROJECTED-REASONING"],
                        "encrypted_content": "NOT-PROJECTED-ENCRYPTED",
                    },
                },
                {
                    "type": "response_item",
                    "payload": {
                        "type": "message",
                        "id": f"answer-{turn_id}",
                        "role": "assistant",
                        "phase": "final_answer",
                        "content": [
                            {"type": "output_text", "text": block}
                            for block in answer_blocks
                        ],
                    },
                },
                {
                    "type": "event_msg",
                    "payload": {
                        "type": "task_complete",
                        "turn_id": turn_id,
                        "last_agent_message": answer,
                        "started_at": 1,
                        "completed_at": 2,
                        "duration_ms": 1,
                        "time_to_first_token_ms": 1,
                    },
                },
            ]
        )
        return records

    def records(
        self,
        *,
        call_ids: tuple[str, ...] = ("call-1",),
        answer_blocks: tuple[str, ...] = ("Synthetic evidence includes REQUIRED.",),
        outputs: tuple[object, ...] | None = None,
    ) -> list[dict]:
        return [
            self.session(),
            {
                "type": "response_item",
                "payload": {
                    "type": "message",
                    "id": "developer-1",
                    "role": "developer",
                    "content": [{"type": "input_text", "text": "NOT-PROJECTED-DEVELOPER"}],
                },
            },
            *self.turn(
                call_ids=call_ids,
                answer_blocks=answer_blocks,
                outputs=outputs,
            ),
        ]

    def spec(
        self,
        source: Path,
        data: bytes,
        *,
        turn_id: str = "turn-1",
        call_ids: list[str] | None = None,
        start_line: int = 3,
        end_line: int | None = None,
        run_id: str = "run-01",
    ) -> dict:
        selected_ids = call_ids or ["call-1"]
        return {
            "schema_version": 3,
            "study": {
                "claim": "The selected answer contains the required synthetic evidence.",
                "rubric": "Pass when REQUIRED is present and FORBIDDEN is absent.",
                "classification": {
                    "source": "complete_final_answer",
                    "pass_when": "all",
                    "checks": [
                        {"id": "required", "operator": "contains", "value": "REQUIRED"},
                        {"id": "forbidden", "operator": "not_contains", "value": "FORBIDDEN"},
                    ],
                },
                "worker_expectations": {
                    "model": "fixture-worker",
                    "effort": "high",
                    "role": "reviewer",
                    "sandbox_type": "fixture-sandbox",
                },
                "reporting": {
                    "promotion_candidate": False,
                    "evidence_grade": "synthetic-test-evidence",
                    "known_limits": ["Synthetic records only."],
                },
            },
            "runs": [
                {
                    "run_id": run_id,
                    "condition": "treatment",
                    "source": source.as_posix(),
                    "expected_source_sha256": hashlib.sha256(data).hexdigest(),
                    "selected_call_ids": selected_ids,
                    "record_selection": {
                        "scope": {
                            "start_line": start_line,
                            "end_line": end_line or len(data.splitlines()),
                        },
                        "session_meta": {"occurrence": 1},
                        "turn_context": {"turn_id": turn_id},
                        "final_answer": {"stable_id": f"answer-{turn_id}"},
                        "task_completion": {"turn_id": turn_id},
                    },
                }
            ],
        }

    def write_source(self, root: Path, records: list[dict], name: str = "rollout.jsonl") -> tuple[Path, bytes]:
        data = jsonl_bytes(records)
        source = root / name
        source.write_bytes(data)
        return source, data

    def write_spec(self, root: Path, value: dict, name: str = "spec.json") -> Path:
        path = root / name
        path.write_text(json.dumps(value), encoding="utf-8")
        return path

    def run_cli(
        self,
        cwd: Path,
        *arguments: str,
    ) -> tuple[subprocess.CompletedProcess[str], dict]:
        result = subprocess.run(
            [sys.executable, str(SCRIPT), *arguments],
            cwd=cwd,
            text=True,
            encoding="utf-8",
            capture_output=True,
            check=False,
        )
        return result, json.loads(result.stdout)

    def run_main_in_process(self, *arguments: str) -> tuple[int, dict]:
        stdout = io.StringIO()
        with (
            mock.patch.object(
                sys,
                "argv",
                [str(SCRIPT), *arguments],
            ),
            redirect_stdout(stdout),
        ):
            return_code = EXPORTER.main()
        return return_code, json.loads(stdout.getvalue())

    @contextmanager
    def raises_code(self, code: str):
        with self.assertRaises(EXPORTER.ExportError) as captured:
            yield
        self.assertEqual(captured.exception.code, code)

    # Evidence-core tests (23)

    def test_export_is_canonical_verifiable_complete_and_bounded(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source, data = self.write_source(root, self.records())
            spec_path = self.write_spec(root, self.spec(source, data))
            out = root / "extract.json"
            exported, payload = self.run_cli(root, "--spec", str(spec_path), "--out", str(out))
            self.assertEqual(exported.returncode, 0, exported.stderr)
            first = out.read_bytes()
            verified, verified_payload = self.run_cli(
                root,
                "--spec",
                str(spec_path),
                "--verify",
                str(out),
            )
            self.assertEqual(verified.returncode, 0, verified.stderr)
            self.assertEqual(payload["extract_sha256"], verified_payload["extract_sha256"])
            extract = json.loads(first)
            run = extract["runs"][0]
            self.assertEqual(run["source_identity"]["sha256"], hashlib.sha256(data).hexdigest())
            self.assertEqual(run["selected_task_calls"][0]["exact_output"], "output-call-1")
            self.assertEqual(run["classification"]["result"], "pass")
            self.assertTrue(run["call_coverage"]["covers_every_call_record"])
            self.assertEqual(run["runtime"]["source_schema"]["task_completion_payload_schema_version"], 1)
            self.assertEqual(run["complete_task_completion"]["source_field_schema_version"], 1)
            self.assertEqual(run["complete_task_completion"]["payload_kind"], "task_complete")
            self.assertEqual(extract["export_policy"]["task_completion_source_schema_version"], 1)
            self.assertFalse(extract["summary"]["declared_promotion_candidate"])
            self.assertFalse(extract["summary"]["verified_promotion_eligible"])
            self.assertEqual(extract["summary"]["promotion_gate"]["status"], "not-requested")
            self.assertNotIn(b"NOT-PROJECTED", first)

    def test_relative_source_resolves_from_process_cwd(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source, data = self.write_source(root, self.records())
            value = self.spec(source, data)
            value["runs"][0]["source"] = source.name
            spec_path = self.write_spec(root, value)
            result, payload = self.run_cli(
                root,
                "--spec",
                spec_path.name,
                "--out",
                "extract.json",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(payload["status"], "exported")

    def test_source_hash_pin_and_fresh_byte_check(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source, data = self.write_source(root, self.records())
            value = self.spec(source, data)
            value["runs"][0]["expected_source_sha256"] = "0" * 64
            with self.raises_code("source-hash-mismatch"):
                EXPORTER.build_extract(value)

            value = self.spec(source, data)
            original = EXPORTER.parse_rollout

            def drift(path):
                parsed = original(path)
                path.write_bytes(data + b"\n")
                return parsed

            with mock.patch.object(EXPORTER, "parse_rollout", side_effect=drift):
                with self.raises_code("source-drift"):
                    EXPORTER.build_extract(value)

    def test_artifact_freshness_rejects_earlier_source_mutated_while_later_run_builds(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            first, first_data = self.write_source(
                root,
                [self.session(session_id="session-first"), *self.turn("turn-first", call_ids=("call-first",))],
                "first.jsonl",
            )
            second, second_data = self.write_source(
                root,
                [self.session(session_id="session-second"), *self.turn("turn-second", call_ids=("call-second",))],
                "second.jsonl",
            )
            value = self.spec(
                first,
                first_data,
                turn_id="turn-first",
                call_ids=["call-first"],
                start_line=2,
                run_id="run-first",
            )
            value["runs"].append(
                self.spec(
                    second,
                    second_data,
                    turn_id="turn-second",
                    call_ids=["call-second"],
                    start_line=2,
                    run_id="run-second",
                )["runs"][0]
            )
            original = EXPORTER.build_run

            def mutate_first_before_second(run_spec, study_spec):
                if run_spec["run_id"] == "run-second":
                    first.write_bytes(first_data + b"\n")
                return original(run_spec, study_spec)

            with mock.patch.object(
                EXPORTER,
                "build_run",
                side_effect=mutate_first_before_second,
            ):
                with self.assertRaises(EXPORTER.ExportError) as captured:
                    EXPORTER.build_extract(value)
            self.assertEqual(captured.exception.code, "source-drift")
            self.assertEqual(captured.exception.details["path"], first.resolve().as_posix())
            self.assertEqual(captured.exception.details["run_ids"], ["run-first"])
            self.assertEqual(
                captured.exception.details["expected_sha256s"],
                [hashlib.sha256(first_data).hexdigest()],
            )

    def test_artifact_freshness_rejects_conflicting_identities_for_one_source(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            first_turn = self.turn("turn-first", call_ids=("call-first",))
            second_turn = self.turn("turn-second", call_ids=("call-second",))
            source, first_data = self.write_source(
                root,
                [self.session(), *first_turn],
            )
            second_data = jsonl_bytes(
                [self.session(), *first_turn, *second_turn]
            )
            value = self.spec(
                source,
                first_data,
                turn_id="turn-first",
                call_ids=["call-first"],
                start_line=2,
                run_id="run-first",
            )
            value["runs"].append(
                self.spec(
                    source,
                    second_data,
                    turn_id="turn-second",
                    call_ids=["call-second"],
                    start_line=2 + len(first_turn),
                    run_id="run-second",
                )["runs"][0]
            )
            original = EXPORTER.build_run

            def install_second_version(run_spec, study_spec):
                if run_spec["run_id"] == "run-second":
                    source.write_bytes(second_data)
                return original(run_spec, study_spec)

            with mock.patch.object(
                EXPORTER,
                "build_run",
                side_effect=install_second_version,
            ):
                with self.assertRaises(EXPORTER.ExportError) as captured:
                    EXPORTER.build_extract(value)
            self.assertEqual(captured.exception.code, "source-drift")
            self.assertEqual(captured.exception.details["path"], source.resolve().as_posix())
            self.assertEqual(
                captured.exception.details["run_ids"],
                ["run-first", "run-second"],
            )
            self.assertEqual(
                captured.exception.details["expected_sha256s"],
                sorted(
                    (
                        hashlib.sha256(first_data).hexdigest(),
                        hashlib.sha256(second_data).hexdigest(),
                    )
                ),
            )

    def test_output_cannot_alias_spec_or_rollout_source(self) -> None:
        for target_name in ("spec", "source"):
            with self.subTest(target=target_name), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                source, data = self.write_source(root, self.records())
                spec_path = self.write_spec(root, self.spec(source, data))
                target = spec_path if target_name == "spec" else source
                original = target.read_bytes()
                result, payload = self.run_cli(
                    root,
                    "--spec",
                    str(spec_path),
                    "--out",
                    str(target.relative_to(root)),
                )
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertEqual(payload["error"], "output-input-conflict")
                self.assertEqual(target.read_bytes(), original)

    def test_publish_binds_owned_bytes_at_link_and_after_publish(self) -> None:
        for mutation_point in ("during-publish", "after-publish"):
            with self.subTest(mutation_point=mutation_point), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                out = root / "extract.json"
                intended = b"INTENDED"
                real_link = EXPORTER.os.link
                linked = False

                def mutate_during_link(source, destination):
                    nonlocal linked
                    if (
                        mutation_point == "during-publish"
                        and Path(destination) == out
                        and not linked
                    ):
                        Path(source).write_bytes(b"FOREIGN")
                        linked = True
                    return real_link(source, destination)

                def mutate_after_publish():
                    if mutation_point == "after-publish":
                        out.write_bytes(b"FOREIGN")

                with mock.patch.object(
                    EXPORTER.os,
                    "link",
                    side_effect=mutate_during_link,
                ):
                    with self.raises_code("artifact-write-integrity"):
                        EXPORTER.write_atomic(
                            out,
                            intended,
                            after_publish=mutate_after_publish,
                        )
                self.assertFalse(out.exists())
                self.assertEqual(
                    list(root.glob(f".{out.name}.*.tmp")),
                    [],
                )

    def test_cli_publish_once_first_success_second_failure_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source, data = self.write_source(root, self.records())
            spec_path = self.write_spec(root, self.spec(source, data))
            out = root / "extract.json"
            first, first_payload = self.run_cli(
                root,
                "--spec",
                str(spec_path),
                "--out",
                str(out),
            )
            self.assertEqual(first.returncode, 0, first.stderr)
            published = out.read_bytes()
            published_sha256 = hashlib.sha256(published).hexdigest()
            self.assertEqual(first_payload["status"], "exported")
            self.assertEqual(first_payload["extract_sha256"], published_sha256)

            second, second_payload = self.run_cli(
                root,
                "--spec",
                str(spec_path),
                "--out",
                str(out),
            )
            self.assertEqual(second.returncode, 1, second.stderr)
            self.assertEqual(second_payload["error"], "output-exists")
            self.assertEqual(out.read_bytes(), published)
            self.assertEqual(
                hashlib.sha256(out.read_bytes()).hexdigest(),
                published_sha256,
            )
            self.assertEqual(list(root.glob(f".{out.name}.*.tmp")), [])

    def test_output_parent_must_already_be_a_real_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            missing_parent = root / "missing"
            with self.raises_code("output-parent-missing"):
                EXPORTER.write_atomic(
                    missing_parent / "extract.json",
                    b"INTENDED",
                )
            self.assertFalse(missing_parent.exists())

            parent_file = root / "not-a-directory"
            parent_file.write_bytes(b"OWNER")
            with self.raises_code("output-parent-invalid"):
                EXPORTER.write_atomic(
                    parent_file / "extract.json",
                    b"INTENDED",
                )
            self.assertEqual(parent_file.read_bytes(), b"OWNER")

            output = root / "existing-parent.json"
            EXPORTER.write_atomic(output, b"INTENDED")
            self.assertEqual(output.read_bytes(), b"INTENDED")

    def test_cli_rejects_lexical_output_and_verify_symlink_endpoints(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source, data = self.write_source(root, self.records())
            value = self.spec(source, data)
            spec_path = self.write_spec(root, value)
            dangling_target = root / "dangling-target.json"
            output_link = root / "output-link.json"
            try:
                output_link.symlink_to(dangling_target)
            except OSError as error:
                self.skipTest(f"symlink creation is unavailable: {error}")

            result, payload = self.run_cli(
                root,
                "--spec",
                str(spec_path),
                "--out",
                str(output_link),
            )
            self.assertEqual(result.returncode, 1, result.stderr)
            self.assertEqual(payload["error"], "output-exists")
            self.assertTrue(output_link.is_symlink())
            self.assertFalse(dangling_target.exists())

            candidate = root / "candidate.json"
            candidate.write_bytes(
                EXPORTER.canonical_bytes(EXPORTER.build_extract(value))
            )
            verify_link = root / "verify-link.json"
            verify_link.symlink_to(candidate)
            result, payload = self.run_cli(
                root,
                "--spec",
                str(spec_path),
                "--verify",
                str(verify_link),
            )
            self.assertEqual(result.returncode, 1, result.stderr)
            self.assertEqual(payload["error"], "artifact-write-integrity")
            self.assertTrue(verify_link.is_symlink())
            self.assertEqual(
                candidate.read_bytes(),
                EXPORTER.canonical_bytes(EXPORTER.build_extract(value)),
            )

    def test_commit_never_clobbers_concurrently_created_output(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            out = root / "extract.json"
            foreign = b"CONCURRENT"
            real_commit = EXPORTER.os.link
            injected = False

            def create_during_commit(source, destination):
                nonlocal injected
                if Path(destination) == out and not injected:
                    out.write_bytes(foreign)
                    injected = True
                return real_commit(source, destination)

            with mock.patch.object(
                EXPORTER.os,
                "link",
                side_effect=create_during_commit,
            ):
                with self.raises_code("artifact-write-conflict"):
                    EXPORTER.write_atomic(out, b"INTENDED")
            self.assertEqual(out.read_bytes(), foreign)

    @unittest.skipIf(os.name == "nt", "POSIX directory fsync semantics")
    def test_posix_commit_and_rollback_fsync_parent_directory_entries(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            out = root / "extract.json"
            calls = []
            original = EXPORTER.fsync_parent_directory

            def record(path):
                calls.append(Path(path))
                original(path)

            with mock.patch.object(
                EXPORTER,
                "fsync_parent_directory",
                side_effect=record,
            ):
                EXPORTER.write_atomic(out, b"INTENDED")
            self.assertGreaterEqual(len(calls), 2)
            self.assertTrue(all(call == out for call in calls))

    def test_main_rechecks_sources_across_the_atomic_replace_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source, data = self.write_source(root, self.records())
            spec_path = self.write_spec(root, self.spec(source, data))
            out = root / "extract.json"
            real_link = EXPORTER.os.link
            mutated = False

            def drift_during_link(staged, destination):
                nonlocal mutated
                if Path(destination) == out and not mutated:
                    source.write_bytes(data + b"\n")
                    mutated = True
                return real_link(staged, destination)

            stdout = io.StringIO()
            with (
                mock.patch.object(
                    EXPORTER.os,
                    "link",
                    side_effect=drift_during_link,
                ),
                mock.patch.object(
                    sys,
                    "argv",
                    [
                        str(SCRIPT),
                        "--spec",
                        str(spec_path),
                        "--out",
                        str(out),
                    ],
                ),
                redirect_stdout(stdout),
            ):
                return_code = EXPORTER.main()
            payload = json.loads(stdout.getvalue())
            self.assertEqual(return_code, 1)
            self.assertEqual(payload["error"], "source-drift")
            self.assertFalse(out.exists())

    def test_verify_rechecks_sources_at_the_final_success_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source, data = self.write_source(root, self.records())
            value = self.spec(source, data)
            spec_path = self.write_spec(root, value)
            candidate = root / "extract.json"
            candidate.write_bytes(
                EXPORTER.canonical_bytes(EXPORTER.build_extract(value))
            )
            original_freshness = EXPORTER.validate_artifact_source_freshness
            freshness_calls = 0

            def drift_after_intermediate_check(runs):
                nonlocal freshness_calls
                freshness_calls += 1
                original_freshness(runs)
                if freshness_calls == 2:
                    source.write_bytes(data + b"\n")

            stdout = io.StringIO()
            with (
                mock.patch.object(
                    EXPORTER,
                    "validate_artifact_source_freshness",
                    side_effect=drift_after_intermediate_check,
                ),
                mock.patch.object(
                    sys,
                    "argv",
                    [
                        str(SCRIPT),
                        "--spec",
                        str(spec_path),
                        "--verify",
                        str(candidate),
                    ],
                ),
                redirect_stdout(stdout),
            ):
                return_code = EXPORTER.main()
            payload = json.loads(stdout.getvalue())
            self.assertEqual(return_code, 1)
            self.assertEqual(payload["error"], "source-drift")
            self.assertEqual(freshness_calls, 3)

    def test_verify_rechecks_candidate_identity_after_every_source_boundary(self) -> None:
        for mutation_boundary in (1, 2, 3):
            with (
                self.subTest(mutation_boundary=mutation_boundary),
                tempfile.TemporaryDirectory() as temp,
            ):
                root = Path(temp)
                source, data = self.write_source(root, self.records())
                value = self.spec(source, data)
                spec_path = self.write_spec(root, value)
                candidate = root / "extract.json"
                candidate.write_bytes(
                    EXPORTER.canonical_bytes(EXPORTER.build_extract(value))
                )
                original_freshness = (
                    EXPORTER.validate_artifact_source_freshness
                )
                freshness_calls = 0

                def mutate_candidate_after_boundary(runs):
                    nonlocal freshness_calls
                    freshness_calls += 1
                    original_freshness(runs)
                    if freshness_calls == mutation_boundary:
                        candidate.write_bytes(b"{}")

                stdout = io.StringIO()
                with (
                    mock.patch.object(
                        EXPORTER,
                        "validate_artifact_source_freshness",
                        side_effect=mutate_candidate_after_boundary,
                    ),
                    mock.patch.object(
                        sys,
                        "argv",
                        [
                            str(SCRIPT),
                            "--spec",
                            str(spec_path),
                            "--verify",
                            str(candidate),
                        ],
                    ),
                    redirect_stdout(stdout),
                ):
                    return_code = EXPORTER.main()
                payload = json.loads(stdout.getvalue())
                self.assertEqual(return_code, 1)
                self.assertEqual(payload["error"], "extract-mismatch")

    def test_specification_snapshot_mutation_boundary_matrix(self) -> None:
        for field in ("selected_call_ids", "study_claim"):
            for mutation_mode in (
                "same-size-bytes",
                "editor-endpoint-replacement",
            ):
                for operation in ("export", "verify"):
                    for mutation_boundary in (1, 2, 3):
                        with (
                            self.subTest(
                                field=field,
                                mutation_mode=mutation_mode,
                                operation=operation,
                                mutation_boundary=mutation_boundary,
                            ),
                            tempfile.TemporaryDirectory() as temp,
                        ):
                            root = Path(temp)
                            source, data = self.write_source(
                                root,
                                self.records(
                                    call_ids=("call-1", "call-2")
                                ),
                            )
                            value = self.spec(
                                source,
                                data,
                                call_ids=["call-1"],
                            )
                            initial_bytes = json.dumps(value).encode("utf-8")
                            spec_path = root / "spec.json"
                            spec_path.write_bytes(initial_bytes)
                            initial_identity = EXPORTER.file_identity(
                                spec_path.lstat()
                            )
                            mutated = copy.deepcopy(value)
                            if field == "selected_call_ids":
                                mutated["runs"][0]["selected_call_ids"] = [
                                    "call-2"
                                ]
                            else:
                                mutated["study"]["claim"] = "X" * len(
                                    value["study"]["claim"]
                                )
                            mutated_bytes = json.dumps(mutated).encode(
                                "utf-8"
                            )
                            self.assertEqual(
                                len(mutated_bytes),
                                len(initial_bytes),
                            )
                            candidate = root / "candidate.json"
                            if operation == "verify":
                                candidate.write_bytes(
                                    EXPORTER.canonical_bytes(
                                        EXPORTER.build_extract(value)
                                    )
                                )
                                candidate_bytes = candidate.read_bytes()
                            output = root / "extract.json"
                            freshness_calls = 0
                            original_freshness = (
                                EXPORTER.validate_specification_freshness
                            )

                            def mutate_before_boundary(snapshot):
                                nonlocal freshness_calls
                                freshness_calls += 1
                                if freshness_calls == mutation_boundary:
                                    if mutation_mode == "same-size-bytes":
                                        spec_path.write_bytes(mutated_bytes)
                                    else:
                                        replacement = (
                                            root / "replacement-spec.json"
                                        )
                                        replacement.write_bytes(mutated_bytes)
                                        os.replace(replacement, spec_path)
                                return original_freshness(snapshot)

                            arguments = (
                                (
                                    "--spec",
                                    str(spec_path),
                                    "--out",
                                    str(output),
                                )
                                if operation == "export"
                                else (
                                    "--spec",
                                    str(spec_path),
                                    "--verify",
                                    str(candidate),
                                )
                            )
                            with mock.patch.object(
                                EXPORTER,
                                "validate_specification_freshness",
                                side_effect=mutate_before_boundary,
                            ):
                                return_code, payload = (
                                    self.run_main_in_process(*arguments)
                                )
                            self.assertEqual(return_code, 1)
                            self.assertEqual(
                                payload["error"],
                                "specification-changed",
                            )
                            self.assertEqual(
                                freshness_calls,
                                mutation_boundary,
                            )
                            self.assertEqual(
                                payload["expected_sha256"],
                                hashlib.sha256(initial_bytes).hexdigest(),
                            )
                            self.assertEqual(
                                payload["actual_sha256"],
                                hashlib.sha256(mutated_bytes).hexdigest(),
                            )
                            current_identity = EXPORTER.file_identity(
                                spec_path.lstat()
                            )
                            if mutation_mode == "same-size-bytes":
                                self.assertEqual(
                                    current_identity,
                                    initial_identity,
                                )
                            else:
                                self.assertNotEqual(
                                    current_identity,
                                    initial_identity,
                                )
                            if operation == "export":
                                self.assertFalse(output.exists())
                            else:
                                self.assertEqual(
                                    candidate.read_bytes(),
                                    candidate_bytes,
                                )

    def test_unchanged_specification_snapshot_passes_every_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source, data = self.write_source(root, self.records())
            value = self.spec(source, data)
            spec_path = self.write_spec(root, value)
            captured_bytes = spec_path.read_bytes()
            snapshot, captured_value = EXPORTER.capture_specification(
                spec_path
            )
            self.assertEqual(snapshot.data, captured_bytes)
            self.assertEqual(
                snapshot.sha256,
                hashlib.sha256(captured_bytes).hexdigest(),
            )
            self.assertEqual(captured_value, value)

            output = root / "extract.json"
            original_freshness = (
                EXPORTER.validate_specification_freshness
            )
            with mock.patch.object(
                EXPORTER,
                "validate_specification_freshness",
                wraps=original_freshness,
            ) as export_freshness:
                return_code, payload = self.run_main_in_process(
                    "--spec",
                    str(spec_path),
                    "--out",
                    str(output),
                )
            self.assertEqual(return_code, 0)
            self.assertEqual(payload["status"], "exported")
            self.assertEqual(export_freshness.call_count, 3)

            with mock.patch.object(
                EXPORTER,
                "validate_specification_freshness",
                wraps=original_freshness,
            ) as verify_freshness:
                return_code, payload = self.run_main_in_process(
                    "--spec",
                    str(spec_path),
                    "--verify",
                    str(output),
                )
            self.assertEqual(return_code, 0)
            self.assertEqual(payload["status"], "verified")
            self.assertEqual(verify_freshness.call_count, 3)

    def test_specification_endpoint_must_be_regular_and_nonreparse(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source, data = self.write_source(root, self.records())
            valid_spec = self.write_spec(root, self.spec(source, data))
            directory_spec = root / "directory-spec"
            directory_spec.mkdir()
            endpoints = [("directory", directory_spec)]
            symlink_spec = root / "symlink-spec.json"
            try:
                symlink_spec.symlink_to(valid_spec)
            except OSError:
                pass
            else:
                endpoints.append(("symlink", symlink_spec))

            for label, endpoint in endpoints:
                with self.subTest(endpoint=label):
                    output = root / f"{label}-extract.json"
                    return_code, payload = self.run_main_in_process(
                        "--spec",
                        str(endpoint),
                        "--out",
                        str(output),
                    )
                    self.assertEqual(return_code, 1)
                    self.assertEqual(
                        payload["error"],
                        "invalid-spec-endpoint",
                    )
                    self.assertFalse(output.exists())
            self.assertEqual(
                json.loads(valid_spec.read_text(encoding="utf-8")),
                self.spec(source, data),
            )

    def test_same_bytes_specification_endpoint_replacement_is_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source, data = self.write_source(root, self.records())
            spec_path = self.write_spec(root, self.spec(source, data))
            snapshot, _ = EXPORTER.capture_specification(spec_path)
            replacement = root / "replacement.json"
            replacement.write_bytes(snapshot.data)
            os.replace(replacement, spec_path)
            with self.assertRaises(EXPORTER.ExportError) as captured:
                EXPORTER.validate_specification_freshness(snapshot)
            self.assertEqual(
                captured.exception.code,
                "specification-changed",
            )
            self.assertEqual(
                captured.exception.details["expected_sha256"],
                captured.exception.details["actual_sha256"],
            )
            self.assertNotEqual(
                tuple(
                    captured.exception.details[
                        "expected_endpoint_identity"
                    ]
                ),
                tuple(
                    captured.exception.details[
                        "actual_endpoint_identity"
                    ]
                ),
            )

    def test_specification_drift_rollback_preserves_foreign_destination(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source, data = self.write_source(
                root,
                self.records(call_ids=("call-1", "call-2")),
            )
            value = self.spec(source, data, call_ids=["call-1"])
            spec_path = self.write_spec(root, value)
            mutated = copy.deepcopy(value)
            mutated["runs"][0]["selected_call_ids"] = ["call-2"]
            mutated_bytes = json.dumps(mutated).encode("utf-8")
            output = root / "extract.json"
            foreign = b"FOREIGN-DESTINATION"
            freshness_calls = 0
            original_freshness = (
                EXPORTER.validate_specification_freshness
            )

            def replace_destination_and_drift(snapshot):
                nonlocal freshness_calls
                freshness_calls += 1
                if freshness_calls == 2:
                    replacement = root / "foreign.json"
                    replacement.write_bytes(foreign)
                    os.replace(replacement, output)
                    spec_path.write_bytes(mutated_bytes)
                return original_freshness(snapshot)

            with mock.patch.object(
                EXPORTER,
                "validate_specification_freshness",
                side_effect=replace_destination_and_drift,
            ):
                return_code, payload = self.run_main_in_process(
                    "--spec",
                    str(spec_path),
                    "--out",
                    str(output),
                )
            self.assertEqual(return_code, 1)
            self.assertEqual(
                payload["error"],
                "specification-changed",
            )
            self.assertEqual(output.read_bytes(), foreign)
            self.assertEqual(
                list(root.glob(f".{output.name}.*.tmp")),
                [],
            )

    def test_session_selector_is_whole_rollout_while_other_selectors_are_scoped(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source, data = self.write_source(root, self.records())
            value = self.spec(source, data, start_line=3)
            extract = EXPORTER.build_extract(value)
            run = extract["runs"][0]
            self.assertEqual(
                run["worker_condition"]["record_locators"]["session_meta"]["selected"]["source_line"],
                1,
            )
            value["runs"][0]["record_selection"]["final_answer"] = {"source_line": 2}
            with self.raises_code("selected-record-missing"):
                EXPORTER.build_extract(value)

    def test_selectors_support_line_stable_turn_and_occurrence(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source, data = self.write_source(root, self.records())
            value = self.spec(source, data)
            selection = value["runs"][0]["record_selection"]
            selection["session_meta"] = {"source_line": 1}
            selection["turn_context"] = {"source_line": 3}
            selection["final_answer"] = {"stable_id": "answer-turn-1"}
            selection["task_completion"] = {"turn_id": "turn-1", "occurrence": 1}
            run = EXPORTER.build_extract(value)["runs"][0]
            self.assertEqual(run["complete_final_answer"]["record_locator"]["stable_id"], "answer-turn-1")

    def test_two_turn_answer_selection_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            records = [self.session(), *self.turn("turn-1"), *self.turn("turn-2", call_ids=("call-2",))]
            source, data = self.write_source(root, records)
            value = self.spec(source, data, start_line=2, call_ids=["call-1"])
            selection = value["runs"][0]["record_selection"]
            selection["final_answer"] = {"stable_id": "answer-turn-2"}
            selection["task_completion"] = {"turn_id": "turn-2"}
            with self.raises_code("cross-turn-selection"):
                EXPORTER.build_extract(value)

    def test_two_turn_call_selection_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            records = [self.session(), *self.turn("turn-1"), *self.turn("turn-2", call_ids=("call-2",))]
            source, data = self.write_source(root, records)
            value = self.spec(
                source,
                data,
                turn_id="turn-2",
                call_ids=["call-1"],
                start_line=2,
            )
            with self.raises_code("cross-turn-selection"):
                EXPORTER.build_extract(value)

    def test_nonidentical_intervening_turn_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            replay = self.turn("turn-1")
            replay[1]["payload"]["input"]["path"] = "C:/fixture/different.txt"
            records = [self.session(), *self.turn("turn-1"), *replay]
            source, data = self.write_source(root, records)
            value = self.spec(source, data, start_line=2)
            with self.assertRaises(EXPORTER.ExportError):
                EXPORTER.build_extract(value)

    def test_unselected_nonidentical_segment_between_selected_replays_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            selected = self.turn("turn-1")
            intervening = self.turn("turn-1", call_ids=("call-middle",))
            intervening[1]["payload"]["id"] = "tool-middle"
            intervening[2]["payload"]["id"] = "output-middle"
            records = [
                self.session(),
                *selected,
                *intervening,
                *copy.deepcopy(selected),
            ]
            source, data = self.write_source(root, records)
            value = self.spec(source, data, start_line=2)
            final_replay_start = 2 + len(selected) + len(intervening)
            selection = value["runs"][0]["record_selection"]
            selection["turn_context"] = {"source_line": 2}
            selection["final_answer"] = {
                "source_line": final_replay_start + len(selected) - 2
            }
            selection["task_completion"] = {
                "source_line": final_replay_start + len(selected) - 1
            }
            with self.raises_code("cross-turn-selection"):
                EXPORTER.build_extract(value)

    def test_exact_turn_replays_deduplicate_with_provenance(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            original_turn = self.turn("turn-1")
            records = [self.session(), *original_turn, *copy.deepcopy(original_turn)]
            source, data = self.write_source(root, records)
            run = EXPORTER.build_extract(self.spec(source, data, start_line=2))["runs"][0]
            selected = run["selected_task_calls"][0]
            self.assertEqual(len(selected["duplicate_call_record_locators"]), 1)
            self.assertEqual(len(selected["duplicate_output_record_locators"]), 1)
            self.assertTrue(run["derived_assertions"]["intervening_turn_records_are_exact_replays"])

    def test_scoped_turn_context_replay_requires_exact_outer_bytes_matrix(self) -> None:
        cases = (
            ("literal-replay", "literal", True),
            ("timestamp-different", "timestamp", False),
            ("outer-key-order-different", "key-order", False),
            ("outer-whitespace-different", "whitespace", False),
            ("line-ending-different", "line-ending", False),
        )
        for case, mutation, accepted in cases:
            with self.subTest(case=case), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                turn = self.turn("turn-1")
                first_context = copy.deepcopy(turn[0])
                replayed_context = copy.deepcopy(first_context)
                if mutation == "timestamp":
                    first_context["timestamp"] = "2026-07-27T00:00:01Z"
                    replayed_context["timestamp"] = "2026-07-27T00:00:02Z"
                records = [
                    self.session(),
                    first_context,
                    replayed_context,
                    *turn[1:],
                ]
                lines = [
                    json.dumps(record, ensure_ascii=False, sort_keys=True)
                    for record in records
                ]
                if mutation == "key-order":
                    lines[2] = json.dumps(
                        replayed_context,
                        ensure_ascii=False,
                        sort_keys=False,
                    )
                elif mutation == "whitespace":
                    lines[2] = json.dumps(
                        replayed_context,
                        ensure_ascii=False,
                        sort_keys=True,
                        separators=(",", ":"),
                    )
                separators = ["\n"] * len(lines)
                if mutation == "line-ending":
                    separators[2] = "\r\n"
                data = "".join(
                    line + separator
                    for line, separator in zip(
                        lines,
                        separators,
                        strict=True,
                    )
                ).encode("utf-8")
                source = root / f"{case}.jsonl"
                source.write_bytes(data)
                value = self.spec(source, data, start_line=2)
                if accepted:
                    run = EXPORTER.build_extract(value)["runs"][0]
                    segments = run["evidence_identity"][
                        "physical_selection"
                    ]["turn_segments"]
                    self.assertEqual(
                        segments[0]["turn_context_source_lines"],
                        [2, 3],
                    )
                    continue
                with self.assertRaises(EXPORTER.ExportError) as captured:
                    EXPORTER.build_extract(value)
                self.assertEqual(
                    captured.exception.code,
                    "turn-completeness-error",
                )
                self.assertEqual(
                    captured.exception.details["reason"],
                    "non-identical-turn-context-replay",
                )
                self.assertEqual(
                    captured.exception.details[
                        "turn_context_source_lines"
                    ],
                    [2, 3],
                )
                self.assertEqual(
                    len(
                        captured.exception.details[
                            "turn_context_outer_record_sha256s"
                        ]
                    ),
                    2,
                )

    def test_byte_different_json_values_are_not_exact_physical_replays(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            session = self.session()
            turn = self.turn("turn-1")
            first_lines = [
                json.dumps(record, ensure_ascii=False, sort_keys=True)
                for record in [session, *turn]
            ]
            replay_lines = [
                json.dumps(
                    record,
                    ensure_ascii=False,
                    sort_keys=False,
                    separators=(",", ":"),
                )
                for record in copy.deepcopy(turn)
            ]
            data = ("\n".join([*first_lines, *replay_lines]) + "\n").encode(
                "utf-8"
            )
            source = root / "format-different-replay.jsonl"
            source.write_bytes(data)
            value = self.spec(source, data, start_line=2)
            with self.assertRaises(EXPORTER.ExportError) as captured:
                EXPORTER.build_extract(value)
            self.assertEqual(captured.exception.code, "cross-turn-selection")
            self.assertEqual(
                captured.exception.details["reason"],
                "non-identical-turn-replay",
            )

    def test_governing_session_replays_require_exact_outer_records(self) -> None:
        for timestamps_match in (True, False):
            with self.subTest(timestamps_match=timestamps_match), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                first_session = self.session()
                first_session["timestamp"] = "2026-07-27T00:00:01Z"
                replayed_session = copy.deepcopy(first_session)
                if not timestamps_match:
                    replayed_session["timestamp"] = "2026-07-27T00:00:02Z"
                original_turn = self.turn("turn-1")
                records = [
                    first_session,
                    *original_turn,
                    replayed_session,
                    *copy.deepcopy(original_turn),
                ]
                source, data = self.write_source(root, records)
                value = self.spec(source, data, start_line=2)
                value["runs"][0]["record_selection"]["session_meta"] = {
                    "stable_id": "session-record"
                }
                if not timestamps_match:
                    with self.assertRaises(EXPORTER.ExportError) as captured:
                        EXPORTER.build_extract(value)
                    self.assertEqual(captured.exception.code, "session-turn-binding-error")
                    self.assertEqual(
                        captured.exception.details["reason"],
                        "mixed-governing-session-metadata",
                    )
                    continue

                run = EXPORTER.build_extract(value)["runs"][0]
                segments = run["evidence_identity"]["physical_selection"]["turn_segments"]
                governing_sessions = [
                    segment["governing_session_meta"]
                    for segment in segments
                ]
                self.assertEqual(
                    [
                        session["record_locator"]["source_line"]
                        for session in governing_sessions
                    ],
                    [1, len(original_turn) + 2],
                )
                self.assertEqual(
                    len(
                        {
                            session["outer_record_sha256"]
                            for session in governing_sessions
                        }
                    ),
                    1,
                )
                self.assertEqual(
                    governing_sessions[0]["outer_record_sha256"],
                    hashlib.sha256(
                        json.dumps(
                            first_session,
                            ensure_ascii=False,
                            sort_keys=True,
                        ).encode("utf-8")
                    ).hexdigest(),
                )
                self.assertTrue(
                    run["derived_assertions"]["intervening_turn_records_are_exact_replays"]
                )

    def test_unpairable_no_id_replays_fail_before_promotion_coherence(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            value = None
            runs = []
            for index in range(4):
                turn_id = f"turn-{index}"
                original = self.turn(turn_id)
                replay = copy.deepcopy(original)
                no_id_call = {
                    "type": "response_item",
                    "timestamp": "2026-07-27T00:00:01Z",
                    "payload": {
                        "type": "function_call",
                        "name": "wait_agent",
                        "arguments": {"timeout_ms": 30000},
                    },
                }
                replayed_no_id_call = copy.deepcopy(no_id_call)
                replayed_no_id_call["timestamp"] = "2026-07-27T00:00:02Z"
                original.insert(1, no_id_call)
                replay.insert(1, replayed_no_id_call)
                records = [
                    self.session(session_id=f"session-{index}"),
                    *original,
                    *replay,
                ]
                source, data = self.write_source(
                    root,
                    records,
                    name=f"timestamp-replay-{index}.jsonl",
                )
                run_spec = self.spec(
                    source,
                    data,
                    turn_id=turn_id,
                    start_line=2,
                    run_id=f"run-{index}",
                )
                if value is None:
                    value = run_spec
                run = run_spec["runs"][0]
                run["condition"] = "control" if index < 2 else "treatment"
                runs.append(run)

            assert value is not None
            value["runs"] = runs
            value["study"]["reporting"]["promotion_candidate"] = True
            with self.assertRaises(EXPORTER.ExportError) as captured:
                EXPORTER.build_extract(value)
            self.assertEqual(
                captured.exception.code,
                "call-output-binding-error",
            )
            self.assertEqual(
                captured.exception.details["reason"],
                "missing-call-identity",
            )

    def test_final_blocks_concatenate_without_separator_and_equal_completion(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            records = self.records(answer_blocks=("Synthetic ", "evidence includes REQUIRED."))
            source, data = self.write_source(root, records)
            run = EXPORTER.build_extract(self.spec(source, data))["runs"][0]
            self.assertEqual(
                [block["text"] for block in run["complete_final_answer"]["content_blocks"]],
                ["Synthetic ", "evidence includes REQUIRED."],
            )
            records[-1]["payload"]["last_agent_message"] += " "
            source, data = self.write_source(root, records)
            with self.raises_code("final-completion-mismatch"):
                EXPORTER.build_extract(self.spec(source, data))

    def test_scope_intersecting_turn_completeness_rejection_matrix(self) -> None:
        cases = (
            (
                "final-no-completion",
                "turn-completeness-error",
                "physical-turn-missing-task-completion",
            ),
            (
                "calls-outputs-no-terminals",
                "turn-completeness-error",
                "physical-turn-missing-final-answer",
            ),
            (
                "complete-no-call-turn-without-session",
                "session-turn-binding-error",
                "scope-intersecting-turn-unbound",
            ),
            (
                "two-distinct-finals-same-text",
                "turn-completeness-error",
                "multiple-distinct-final-answer-records",
            ),
            (
                "equal-completions-different-outer-timestamps",
                "turn-completeness-error",
                "non-identical-task-completion-replay",
            ),
        )
        for case, error_code, reason in cases:
            with (
                self.subTest(case=case),
                tempfile.TemporaryDirectory() as temp,
            ):
                root = Path(temp)
                malformed_turn = self.turn("turn-malformed")
                selected_turn = self.turn("turn-1")
                if case == "final-no-completion":
                    malformed_turn.pop()
                    records = [
                        self.session(),
                        *malformed_turn,
                        *selected_turn,
                    ]
                    start_line = 2
                elif case == "calls-outputs-no-terminals":
                    malformed_turn = malformed_turn[:-2]
                    records = [
                        self.session(),
                        *malformed_turn,
                        *selected_turn,
                    ]
                    start_line = 2
                elif case == "complete-no-call-turn-without-session":
                    malformed_turn = self.turn(
                        "turn-malformed",
                        call_ids=(),
                    )
                    records = [
                        *malformed_turn,
                        self.session(),
                        *selected_turn,
                    ]
                    start_line = 1
                elif case == "two-distinct-finals-same-text":
                    final = next(
                        row
                        for row in malformed_turn
                        if row.get("payload", {}).get("phase")
                        == "final_answer"
                    )
                    second_final = copy.deepcopy(final)
                    second_final["payload"]["id"] = (
                        "answer-turn-malformed-second"
                    )
                    malformed_turn.insert(
                        malformed_turn.index(final) + 1,
                        second_final,
                    )
                    records = [
                        self.session(),
                        *malformed_turn,
                        *selected_turn,
                    ]
                    start_line = 2
                else:
                    completion = malformed_turn[-1]
                    completion["timestamp"] = (
                        "2026-07-27T00:00:01Z"
                    )
                    second_completion = copy.deepcopy(completion)
                    second_completion["timestamp"] = (
                        "2026-07-27T00:00:02Z"
                    )
                    malformed_turn.append(second_completion)
                    records = [
                        self.session(),
                        *malformed_turn,
                        *selected_turn,
                    ]
                    start_line = 2
                source, data = self.write_source(root, records)
                with self.assertRaises(EXPORTER.ExportError) as captured:
                    EXPORTER.build_extract(
                        self.spec(
                            source,
                            data,
                            start_line=start_line,
                        )
                    )
                self.assertEqual(captured.exception.code, error_code)
                self.assertEqual(
                    captured.exception.details["reason"],
                    reason,
                )

    def test_byte_identical_final_and_completion_replays_are_one_logical_terminal(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            turn = self.turn("turn-1")
            final = next(
                row
                for row in turn
                if row.get("payload", {}).get("phase")
                == "final_answer"
            )
            turn.insert(
                turn.index(final) + 1,
                copy.deepcopy(final),
            )
            turn.append(copy.deepcopy(turn[-1]))
            source, data = self.write_source(
                root,
                [self.session(), *turn],
            )
            run = EXPORTER.build_extract(
                self.spec(source, data, start_line=2)
            )["runs"][0]
            for assertion in (
                "scope_intersecting_turn_singleton_terminals_complete",
                "scope_intersecting_turn_final_completion_texts_match",
                "scope_intersecting_turn_completion_terminal",
            ):
                self.assertTrue(run["derived_assertions"][assertion])

    def test_wholly_out_of_scope_final_completion_mismatch_is_hash_pinned_only(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            unselected_turn = self.turn(
                "turn-unselected",
                answer_blocks=("REQUIRED",),
            )
            unselected_turn[-1]["payload"][
                "last_agent_message"
            ] = "CONFLICTING"
            selected_turn = self.turn("turn-1")
            records = [
                self.session(),
                *unselected_turn,
                *selected_turn,
            ]
            selected_start = records.index(selected_turn[0]) + 1
            source, data = self.write_source(root, records)
            run = EXPORTER.build_extract(
                self.spec(
                    source,
                    data,
                    start_line=selected_start,
                )
            )["runs"][0]
            self.assertEqual(
                run["complete_task_completion"]["turn_id"],
                "turn-1",
            )
            self.assertTrue(
                run["derived_assertions"][
                    "scope_intersecting_turn_singleton_terminals_complete"
                ]
            )

    def test_matching_unselected_final_completion_replays_are_accepted(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            unselected_turn = self.turn(
                "turn-unselected",
                answer_blocks=("MATCH", "ING"),
            )
            selected_turn = self.turn("turn-1")
            records = [
                self.session(),
                *unselected_turn,
                *copy.deepcopy(unselected_turn),
                *selected_turn,
            ]
            selected_start = records.index(selected_turn[0]) + 1
            source, data = self.write_source(root, records)
            run = EXPORTER.build_extract(
                self.spec(
                    source,
                    data,
                    start_line=selected_start,
                )
            )["runs"][0]
            self.assertEqual(
                run["complete_task_completion"]["turn_id"],
                "turn-1",
            )

    def test_multi_call_order_arguments_outputs_and_status_are_exact(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            exact_outputs = ({"value": [1, 2]}, "second output")
            source, data = self.write_source(
                root,
                self.records(call_ids=("call-a", "call-b"), outputs=exact_outputs),
            )
            value = self.spec(source, data, call_ids=["call-b", "call-a"])
            run = EXPORTER.build_extract(value)["runs"][0]
            self.assertEqual(
                [call["call_id"] for call in run["selected_task_calls"]],
                ["call-b", "call-a"],
            )
            self.assertEqual(run["selected_task_calls"][0]["exact_output"], "second output")
            self.assertEqual(run["selected_task_calls"][1]["exact_output"], {"value": [1, 2]})
            self.assertEqual(run["selected_task_calls"][0]["arguments"]["ordinal"], 2)
            self.assertEqual(
                [step["status"] for step in run["selected_task_calls"][0]["status_transitions"]],
                ["completed", "output-recorded"],
            )

    def test_governed_turn_chronology_rejects_malformed_source_order(self) -> None:
        cases = (
            (
                "output-before-call",
                "output-before-matching-call",
                {
                    "call_source_lines": [4],
                    "output_source_line": 3,
                },
            ),
            (
                "final-before-call-output",
                "final-answer-before-call-output",
                {
                    "final_answer_source_line": 3,
                    "governed_call_output_source_lines": [4, 5],
                    "offending_call_output_source_lines": [4, 5],
                },
            ),
            (
                "completion-before-governed-records",
                "governed-record-after-task-completion",
                {
                    "task_completion_source_line": 3,
                    "offending_source_line": 4,
                    "offending_payload_kind": "custom_tool_call",
                },
            ),
        )
        for case, reason, expected_details in cases:
            with self.subTest(case=case), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                malformed_turn = self.turn("turn-malformed")
                records = [
                    self.session(),
                    *malformed_turn,
                    *self.turn("turn-1"),
                ]
                call_index = next(
                    index
                    for index, row in enumerate(records)
                    if row.get("payload", {}).get("type")
                    == "custom_tool_call"
                )
                output_index = next(
                    index
                    for index, row in enumerate(records)
                    if row.get("payload", {}).get("type")
                    == "custom_tool_call_output"
                )
                final_index = next(
                    index
                    for index, row in enumerate(records)
                    if row.get("payload", {}).get("phase")
                    == "final_answer"
                )
                completion_index = next(
                    index
                    for index, row in enumerate(records)
                    if row.get("payload", {}).get("type")
                    == "task_complete"
                )
                if case == "output-before-call":
                    records[call_index], records[output_index] = (
                        records[output_index],
                        records[call_index],
                    )
                elif case == "final-before-call-output":
                    final = records.pop(final_index)
                    records.insert(call_index, final)
                else:
                    completion = records.pop(completion_index)
                    records.insert(call_index, completion)
                source, data = self.write_source(root, records)
                value = self.spec(
                    source,
                    data,
                    start_line=2,
                )
                value["study"]["reporting"]["promotion_candidate"] = True
                with self.assertRaises(EXPORTER.ExportError) as captured:
                    EXPORTER.build_extract(value)
                self.assertEqual(
                    captured.exception.code,
                    "turn-chronology-error",
                )
                self.assertEqual(
                    captured.exception.details["reason"],
                    reason,
                )
                self.assertEqual(
                    captured.exception.details["physical_segment_index"],
                    0,
                )
                self.assertEqual(
                    captured.exception.details["turn_identity"],
                    "turn-malformed",
                )
                for field, expected in expected_details.items():
                    self.assertEqual(
                        captured.exception.details[field],
                        expected,
                    )

    def test_task_completion_rejects_later_governed_records_in_scoped_turn(self) -> None:
        cases = (
            (
                "reasoning",
                {
                    "type": "response_item",
                    "payload": {
                        "type": "reasoning",
                        "id": "late-reasoning",
                        "summary": ["late"],
                        "encrypted_content": "opaque",
                    },
                },
                "governed-record-after-task-completion",
                "response_item",
                "reasoning",
            ),
            (
                "agent-message",
                {
                    "type": "response_item",
                    "payload": {
                        "type": "agent_message",
                        "id": "late-agent-message",
                        "author": "/root/child",
                        "recipient": "/root",
                        "content": [
                            {
                                "type": "output_text",
                                "text": "late",
                            }
                        ],
                    },
                },
                "governed-record-after-task-completion",
                "response_item",
                "agent_message",
            ),
            (
                "assistant-commentary",
                {
                    "type": "response_item",
                    "payload": {
                        "type": "message",
                        "id": "late-commentary",
                        "role": "assistant",
                        "phase": "commentary",
                        "content": [
                            {
                                "type": "output_text",
                                "text": "late",
                            }
                        ],
                    },
                },
                "governed-record-after-task-completion",
                "response_item",
                "message",
            ),
            (
                "nonidentical-completion",
                None,
                "unsupported-task-completion-replay",
                "event_msg",
                "task_complete",
            ),
        )
        for case, late_record, reason, outer_kind, payload_kind in cases:
            with self.subTest(case=case), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                unselected_turn = self.turn("turn-unselected")
                selected_turn = self.turn("turn-1")
                if late_record is None:
                    late_record = copy.deepcopy(unselected_turn[-1])
                    late_record["payload"]["completed_at"] = 3
                    late_record["payload"]["duration_ms"] = 2
                records = [
                    self.session(),
                    *unselected_turn,
                    late_record,
                    *selected_turn,
                ]
                selected_start = records.index(selected_turn[0]) + 1
                source, data = self.write_source(root, records)
                with self.assertRaises(EXPORTER.ExportError) as captured:
                    EXPORTER.build_extract(
                        self.spec(
                            source,
                            data,
                            start_line=2,
                        )
                    )
                self.assertEqual(
                    captured.exception.code,
                    "turn-chronology-error",
                )
                self.assertEqual(
                    captured.exception.details["reason"],
                    reason,
                )
                self.assertEqual(
                    captured.exception.details["physical_segment_index"],
                    0,
                )
                self.assertEqual(
                    captured.exception.details["turn_identity"],
                    "turn-unselected",
                )
                self.assertEqual(
                    captured.exception.details["task_completion_source_line"],
                    7,
                )
                self.assertEqual(
                    captured.exception.details["task_completion_source_lines"],
                    [7],
                )
                self.assertEqual(
                    captured.exception.details["offending_source_line"],
                    8,
                )
                self.assertEqual(
                    captured.exception.details["offending_outer_record_kind"],
                    outer_kind,
                )
                self.assertEqual(
                    captured.exception.details["offending_payload_kind"],
                    payload_kind,
                )

    def test_exact_completion_replay_and_opaque_records_allow_next_turn(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            unselected_turn = self.turn(
                "turn-unselected",
                call_ids=("call-unselected",),
            )
            selected_turn = self.turn("turn-1")
            completion_replay = copy.deepcopy(unselected_turn[-1])
            opaque_event = {
                "type": "event_msg",
                "payload": {
                    "type": "opaque-event",
                    "marker": "NOT-PROJECTED-OPAQUE-EVENT",
                },
            }
            opaque_world = {
                "type": "world_state",
                "payload": {
                    "marker": "NOT-PROJECTED-OPAQUE-WORLD",
                    "state": {},
                },
            }
            records = [
                self.session(),
                *unselected_turn,
                completion_replay,
                opaque_event,
                opaque_world,
                *selected_turn,
            ]
            selected_start = records.index(selected_turn[0]) + 1
            source, data = self.write_source(root, records)
            extract = EXPORTER.build_extract(
                self.spec(
                    source,
                    data,
                    start_line=2,
                )
            )
            run = extract["runs"][0]
            self.assertEqual(
                run["complete_task_completion"]["turn_id"],
                "turn-1",
            )
            exported = EXPORTER.canonical_bytes(extract)
            self.assertNotIn(b"NOT-PROJECTED-OPAQUE-EVENT", exported)
            self.assertNotIn(b"NOT-PROJECTED-OPAQUE-WORLD", exported)

            delayed_replay_records = [
                self.session(),
                *unselected_turn,
                opaque_event,
                copy.deepcopy(completion_replay),
                opaque_world,
                *selected_turn,
            ]
            delayed_selected_start = (
                delayed_replay_records.index(selected_turn[0]) + 1
            )
            delayed_source, delayed_data = self.write_source(
                root,
                delayed_replay_records,
                name="delayed-replay.jsonl",
            )
            with self.assertRaises(EXPORTER.ExportError) as captured:
                EXPORTER.build_extract(
                    self.spec(
                        delayed_source,
                        delayed_data,
                        start_line=2,
                    )
                )
            self.assertEqual(
                captured.exception.code,
                "turn-chronology-error",
            )
            self.assertEqual(
                captured.exception.details["reason"],
                "unsupported-task-completion-replay",
            )

    def test_task_completion_requires_an_active_matching_turn_segment(self) -> None:
        cases = (
            "orphan-then-reasoning",
            "two-nonidentical-orphans",
            "mismatched-bound-completion",
        )
        for case in cases:
            with self.subTest(case=case), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                if case == "mismatched-bound-completion":
                    records = self.records()
                    completion = next(
                        row
                        for row in records
                        if row.get("payload", {}).get("type")
                        == "task_complete"
                    )
                    completion["payload"]["turn_id"] = "turn-other"
                    expected_line = 8
                    active_turn_id = "turn-1"
                    completion_turn_id = "turn-other"
                    selected_start = 3
                else:
                    orphan_turn = self.turn("turn-orphan")
                    orphan_completion = copy.deepcopy(orphan_turn[-1])
                    if case == "orphan-then-reasoning":
                        following = copy.deepcopy(orphan_turn[-3])
                        following["payload"]["id"] = "orphan-late-reasoning"
                    else:
                        following = copy.deepcopy(orphan_completion)
                        following["payload"]["completed_at"] = 3
                        following["payload"]["duration_ms"] = 2
                    selected_turn = self.turn("turn-1")
                    records = [
                        self.session(),
                        orphan_completion,
                        following,
                        *selected_turn,
                    ]
                    expected_line = 2
                    active_turn_id = None
                    completion_turn_id = "turn-orphan"
                    selected_start = 2
                source, data = self.write_source(root, records)
                with self.assertRaises(EXPORTER.ExportError) as captured:
                    EXPORTER.build_extract(
                        self.spec(
                            source,
                            data,
                            start_line=selected_start,
                        )
                    )
                self.assertEqual(
                    captured.exception.code,
                    "session-turn-binding-error",
                )
                self.assertEqual(
                    captured.exception.details["reason"],
                    "task-completion-outside-turn-segment",
                )
                self.assertEqual(
                    captured.exception.details["source_line"],
                    expected_line,
                )
                self.assertEqual(
                    captured.exception.details["active_turn_id"],
                    active_turn_id,
                )
                self.assertEqual(
                    captured.exception.details["task_completion_turn_id"],
                    completion_turn_id,
                )

    def test_bound_completion_and_pre_turn_message_are_accepted(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            records = self.records()
            self.assertEqual(
                records[1]["payload"]["role"],
                "developer",
            )
            source, data = self.write_source(root, records)
            run = EXPORTER.build_extract(
                self.spec(source, data)
            )["runs"][0]
            self.assertEqual(
                run["complete_task_completion"]["record_locator"][
                    "source_line"
                ],
                8,
            )
            self.assertEqual(
                run["complete_task_completion"]["turn_id"],
                "turn-1",
            )

    def test_interleaved_call_outputs_preserve_physical_transition_order(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            records = self.records(
                call_ids=("call-a", "call-b"),
                outputs=("output-a", "output-b"),
            )
            call_a = next(
                row
                for row in records
                if row.get("payload", {}).get("call_id") == "call-a"
                and row["payload"].get("type") == "custom_tool_call"
            )
            output_a = next(
                row
                for row in records
                if row.get("payload", {}).get("call_id") == "call-a"
                and row["payload"].get("type") == "custom_tool_call_output"
            )
            call_b = next(
                row
                for row in records
                if row.get("payload", {}).get("call_id") == "call-b"
                and row["payload"].get("type") == "custom_tool_call"
            )
            output_b = next(
                row
                for row in records
                if row.get("payload", {}).get("call_id") == "call-b"
                and row["payload"].get("type") == "custom_tool_call_output"
            )
            call_a["payload"]["status"] = "in_progress"
            call_a_completed = copy.deepcopy(call_a)
            call_a_completed["payload"]["status"] = "completed"
            first_call_index = records.index(call_a)
            records[first_call_index:first_call_index + 4] = [
                call_a,
                call_b,
                output_b,
                output_a,
                call_a_completed,
            ]
            source, data = self.write_source(root, records)
            run = EXPORTER.build_extract(
                self.spec(
                    source,
                    data,
                    call_ids=["call-a", "call-b"],
                )
            )["runs"][0]
            selected = {
                call["call_id"]: call
                for call in run["selected_task_calls"]
            }
            self.assertEqual(
                [
                    (
                        step["record_locator"]["source_line"],
                        step["status"],
                    )
                    for step in selected["call-a"]["status_transitions"]
                ],
                [
                    (4, "in_progress"),
                    (7, "output-recorded"),
                    (8, "completed"),
                ],
            )
            self.assertEqual(
                [
                    (
                        step["record_locator"]["source_line"],
                        step["status"],
                    )
                    for step in selected["call-b"]["status_transitions"]
                ],
                [
                    (5, "completed"),
                    (6, "output-recorded"),
                ],
            )
            self.assertEqual(selected["call-a"]["exact_output"], "output-a")
            self.assertEqual(selected["call-b"]["exact_output"], "output-b")

    def test_raw_unicode_line_separators_remain_inside_physical_jsonl_records(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            exact_answer = "Synthetic evidence includes REQUIRED.\u2028answer\u2029tail"
            exact_output = "tool\u2029output\u2028tail"
            records = self.records(
                outputs=(exact_output,),
                answer_blocks=(exact_answer,),
            )
            records[3]["payload"]["input"]["unicode_text"] = "argument\u2028middle\u2029tail"
            source, data = self.write_source(root, records)
            self.assertEqual(data.count(b"\n"), len(records))
            self.assertTrue(
                all(json.loads(line.decode("utf-8")) for line in data.split(b"\n")[:-1])
            )

            run = EXPORTER.build_extract(self.spec(source, data))["runs"][0]
            selected = run["selected_task_calls"][0]
            self.assertEqual(selected["arguments"]["unicode_text"], "argument\u2028middle\u2029tail")
            self.assertEqual(selected["exact_output"], exact_output)
            self.assertEqual(run["complete_final_answer"]["content_blocks"][0]["text"], exact_answer)
            self.assertEqual(run["complete_task_completion"]["last_agent_message"], exact_answer)

    def test_unpairable_no_id_calls_do_not_use_replay_or_physical_fallbacks(self) -> None:
        for case, timestamps in (
            ("different-timestamps", ("2026-07-27T00:00:01Z", "2026-07-27T00:00:02Z")),
            ("missing-timestamps", (None, None)),
        ):
            with self.subTest(case=case), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                records = self.records()
                no_id_calls = []
                for timestamp in timestamps:
                    row = {
                        "type": "response_item",
                        "payload": {
                            "type": "function_call",
                            "name": "wait_agent",
                            "arguments": {"timeout_ms": 30000},
                        },
                    }
                    if timestamp is not None:
                        row["timestamp"] = timestamp
                    no_id_calls.append(row)
                records[4:4] = no_id_calls
                source, data = self.write_source(root, records)

                with self.assertRaises(EXPORTER.ExportError) as captured:
                    EXPORTER.build_extract(self.spec(source, data))
                self.assertEqual(
                    captured.exception.code,
                    "call-output-binding-error",
                )
                self.assertEqual(
                    captured.exception.details["reason"],
                    "missing-call-identity",
                )

    def test_conflicting_duplicate_call_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            records = self.records()
            duplicate = copy.deepcopy(records[3])
            duplicate["payload"]["id"] = "different-duplicate-id"
            duplicate["payload"]["input"]["path"] = "different"
            records.insert(4, duplicate)
            source, data = self.write_source(root, records)
            with self.raises_code("duplicate-call-conflict"):
                EXPORTER.build_extract(self.spec(source, data))

    def test_missing_and_conflicting_outputs_are_rejected(self) -> None:
        for case in ("missing", "conflicting"):
            with self.subTest(case=case), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                records = self.records()
                if case == "missing":
                    del records[4]
                else:
                    duplicate = copy.deepcopy(records[4])
                    duplicate["payload"]["output"] = "different"
                    records.insert(5, duplicate)
                source, data = self.write_source(root, records)
                with self.assertRaises(EXPORTER.ExportError):
                    EXPORTER.build_extract(self.spec(source, data))

    def test_duplicate_physical_run_selection_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source, data = self.write_source(root, self.records())
            value = self.spec(source, data)
            duplicate = copy.deepcopy(value["runs"][0])
            duplicate["run_id"] = "run-02"
            value["runs"].append(duplicate)
            with self.raises_code("duplicate-physical-run-selection"):
                EXPORTER.build_extract(value)

    def test_logical_replay_copied_to_another_file_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            records = self.records()
            first, first_data = self.write_source(root, records, "first.jsonl")
            second, second_data = self.write_source(root, records, "second.jsonl")
            value = self.spec(first, first_data)
            second_run = self.spec(second, second_data, run_id="run-02")["runs"][0]
            value["runs"].append(second_run)
            with self.raises_code("duplicate-logical-run-selection"):
                EXPORTER.build_extract(value)

    def test_distinct_turns_from_one_session_are_accepted(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            first_turn = self.turn("turn-1")
            second_turn = self.turn("turn-2", call_ids=("call-2",))
            records = [self.session(), *first_turn, *second_turn]
            source, data = self.write_source(root, records)
            first_start = 2
            first_end = 1 + len(first_turn)
            second_start = first_end + 1
            value = self.spec(
                source,
                data,
                start_line=first_start,
                end_line=first_end,
            )
            second_run = self.spec(
                source,
                data,
                turn_id="turn-2",
                call_ids=["call-2"],
                start_line=second_start,
                end_line=len(records),
                run_id="run-02",
            )["runs"][0]
            value["runs"].append(second_run)
            extract = EXPORTER.build_extract(value)
            self.assertEqual(len(extract["runs"]), 2)
            self.assertNotEqual(
                extract["runs"][0]["evidence_identity"]["physical_selection"]["sha256"],
                extract["runs"][1]["evidence_identity"]["physical_selection"]["sha256"],
            )

    def test_worker_expectations_are_study_wide_and_run_overrides_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source, data = self.write_source(root, self.records())
            value = self.spec(source, data)
            value["study"]["worker_expectations"]["model"] = "shared-wrong"
            run = EXPORTER.build_extract(value)["runs"][0]
            self.assertFalse(run["worker_expectation_evaluation"]["all_match"])

            value["runs"][0]["worker_expectations"] = {"model": "fixture-worker"}
            with self.raises_code("invalid-spec"):
                EXPORTER.build_extract(value)

    def test_worker_type_contract_matrix_and_optional_absence(self) -> None:
        invalid_actuals = (
            ("role-bool", {"agent_role": False}, {}),
            ("model-null", {}, {"model": None}),
            ("effort-empty", {}, {"effort": ""}),
            ("cwd-wrong-type", {}, {"cwd": []}),
            ("approval-bool", {}, {"approval_policy": False}),
            ("sandbox-wrong-type", {}, {"sandbox_policy": False}),
            ("sandbox-empty", {}, {"sandbox_policy": {}}),
            ("sandbox-type-bool", {}, {"sandbox_policy": {"type": False}}),
            ("permission-null", {}, {"permission_profile": None}),
        )
        for case, session, turn in invalid_actuals:
            with self.subTest(actual=case), self.raises_code("unprojectable-record"):
                EXPORTER.worker_actuals(session, turn)

        for field in EXPORTER.WORKER_FIELDS:
            with self.subTest(expectation=field), self.raises_code("invalid-spec"):
                EXPORTER.evaluate_worker_expectations({}, {field: False})

        actuals = EXPORTER.worker_actuals({}, {})
        evaluation = EXPORTER.evaluate_worker_expectations(
            actuals,
            {"model": None, "sandbox_policy": None},
        )
        self.assertTrue(evaluation["all_match"])
        self.assertIsNone(actuals["model"])
        self.assertIsNone(actuals["sandbox_policy"])

    def test_promotion_candidate_requires_design_and_never_self_certifies(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source, data = self.write_source(root, self.records())
            value = self.spec(source, data)
            value["study"]["reporting"]["promotion_candidate"] = True
            with self.raises_code("promotion-evidence-insufficient"):
                EXPORTER.build_extract(value)

            runs = []
            for index in range(4):
                turn_id = f"turn-{index}"
                records = [
                    self.session(session_id=f"session-{index}"),
                    *self.turn(turn_id=turn_id),
                ]
                run_source, run_data = self.write_source(
                    root,
                    records,
                    name=f"rollout-{index}.jsonl",
                )
                run = self.spec(
                    run_source,
                    run_data,
                    turn_id=turn_id,
                    start_line=2,
                    run_id=f"run-{index}",
                )["runs"][0]
                run["condition"] = "control" if index < 2 else "treatment"
                runs.append(run)
            value["runs"] = runs
            summary = EXPORTER.build_extract(value)["summary"]
            self.assertTrue(summary["declared_promotion_candidate"])
            self.assertFalse(summary["verified_promotion_eligible"])
            self.assertEqual(
                summary["promotion_gate"]["status"],
                "unverified-non-machine-evidence",
            )
            self.assertTrue(all(summary["promotion_gate"]["machine_checks"].values()))
            self.assertTrue(
                summary["promotion_gate"]["machine_checks"][
                    "scoped_turn_semantic_completeness_verified_all_runs"
                ]
            )
            self.assertTrue(
                summary[
                    "scoped_turn_semantic_completeness_verified_all_runs"
                ]
            )
            self.assertTrue(summary["promotion_gate"]["unverified_requirements"])

            value["study"]["worker_expectations"] = {"effort": "high"}
            for index, run in enumerate(value["runs"]):
                source = Path(run["source"])
                records = [json.loads(line) for line in source.read_text(encoding="utf-8").splitlines()]
                turn = next(record for record in records if record["type"] == "turn_context")
                turn["payload"]["model"] = "worker-control" if index < 2 else "worker-treatment"
                data = jsonl_bytes(records)
                source.write_bytes(data)
                run["expected_source_sha256"] = hashlib.sha256(data).hexdigest()
            with self.raises_code("promotion-evidence-insufficient"):
                EXPORTER.build_extract(value)

            value["study"]["reporting"]["promotion_candidate"] = False
            value["study"]["worker_expectations"]["model"] = "different-worker"
            summary = EXPORTER.build_extract(value)["summary"]
            self.assertFalse(summary["declared_promotion_candidate"])
            self.assertFalse(summary["verified_promotion_eligible"])
            self.assertFalse(summary["worker_expectations_match_all_runs"])

    def test_classification_sources_operators_and_explicit_call_target(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            output = '{"marker":"ALLOW","role":"system"}'
            source, data = self.write_source(root, self.records(outputs=(output,)))
            sources = (
                "complete_final_answer",
                "complete_task_completion.last_agent_message",
                "selected_task_calls.arguments",
                "selected_task_calls.output",
            )
            for classification_source in sources:
                with self.subTest(source=classification_source):
                    value = self.spec(source, data)
                    classification = {
                        "source": classification_source,
                        "pass_when": "all",
                        "checks": [],
                    }
                    if classification_source.startswith("selected_task_calls."):
                        classification["selected_call_id"] = "call-1"
                    if classification_source.endswith("arguments"):
                        classification["checks"] = [
                            {"id": "path", "operator": "regex", "value": "fixture.1", "flags": "i"},
                        ]
                    elif classification_source.endswith("output"):
                        classification["checks"] = [
                            {"id": "allow", "operator": "equals", "value": output},
                        ]
                    else:
                        classification["checks"] = [
                            {"id": "required", "operator": "contains", "value": "REQUIRED"},
                            {"id": "absent", "operator": "not_regex", "value": "FORBIDDEN"},
                        ]
                    value["study"]["classification"] = classification
                    self.assertEqual(
                        EXPORTER.build_extract(value)["runs"][0]["classification"]["result"],
                        "pass",
                    )

            invalid = self.spec(source, data)
            invalid["study"]["classification"] = {
                "source": "selected_task_calls.output",
                "pass_when": "all",
                "checks": [{"id": "allow", "operator": "contains", "value": "ALLOW"}],
            }
            with self.raises_code("invalid-spec"):
                EXPORTER.build_extract(invalid)

    def test_schema_v3_strict_fields_and_selected_call_ids(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source, data = self.write_source(root, self.records())
            cases = []
            schema_two = self.spec(source, data)
            schema_two["schema_version"] = 2
            cases.append(schema_two)
            singular = self.spec(source, data)
            singular["runs"][0]["selected_call_id"] = singular["runs"][0].pop("selected_call_ids")[0]
            cases.append(singular)
            unknown_study = self.spec(source, data)
            unknown_study["study"]["extra"] = True
            cases.append(unknown_study)
            unknown_top = self.spec(source, data)
            unknown_top["extra"] = True
            cases.append(unknown_top)
            misspelled_pass_when = self.spec(source, data)
            classification = misspelled_pass_when["study"]["classification"]
            classification["pass_whne"] = classification.pop("pass_when")
            cases.append(misspelled_pass_when)
            unknown_classification = self.spec(source, data)
            unknown_classification["study"]["classification"]["extra"] = True
            cases.append(unknown_classification)
            unknown_check = self.spec(source, data)
            unknown_check["study"]["classification"]["checks"][0]["extra"] = True
            cases.append(unknown_check)
            flags_on_contains = self.spec(source, data)
            flags_on_contains["study"]["classification"]["checks"][0]["flags"] = "i"
            cases.append(flags_on_contains)
            duplicate_calls = self.spec(source, data)
            duplicate_calls["runs"][0]["selected_call_ids"] = ["call-1", "call-1"]
            cases.append(duplicate_calls)
            for index, value in enumerate(cases):
                with self.subTest(index=index), self.raises_code("invalid-spec"):
                    EXPORTER.build_extract(value)

    def test_duplicate_object_keys_fail_closed_in_spec_and_rollout_json(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            duplicate_spec = root / "duplicate-spec.json"
            duplicate_spec.write_text(
                '{"schema_version":3,"schema_version":3}',
                encoding="utf-8",
            )
            with self.assertRaises(EXPORTER.ExportError) as captured:
                EXPORTER.load_json(duplicate_spec)
            self.assertEqual(captured.exception.code, "invalid-json")
            self.assertEqual(
                captured.exception.details["duplicate_key"],
                "schema_version",
            )

            records = self.records()
            data = jsonl_bytes(records)
            call_line = next(
                index
                for index, row in enumerate(records)
                if row.get("payload", {}).get("type") == "custom_tool_call"
            )
            lines = data.splitlines(keepends=True)
            lines[call_line] = lines[call_line].replace(
                b'"name": "fixture_read"',
                b'"name": "alternate_semantics", "name": "fixture_read"',
            )
            source = root / "duplicate-rollout.jsonl"
            source.write_bytes(b"".join(lines))
            with self.assertRaises(EXPORTER.ExportError) as captured:
                EXPORTER.parse_rollout(source)
            self.assertEqual(captured.exception.code, "rollout-parse-error")
            self.assertEqual(captured.exception.details["duplicate_key"], "name")
            self.assertEqual(captured.exception.details["line"], call_line + 1)

    def test_governed_record_fields_are_closed_world_for_every_call_family(self) -> None:
        kind_pairs = tuple(EXPORTER.CALL_OUTPUT_KIND.items())
        for call_kind, output_kind in kind_pairs:
            for target in ("call", "output"):
                with (
                    self.subTest(call_kind=call_kind, target=target),
                    tempfile.TemporaryDirectory() as temp,
                ):
                    root = Path(temp)
                    records = self.records()
                    call = next(
                        row["payload"]
                        for row in records
                        if row.get("payload", {}).get("type") == "custom_tool_call"
                    )
                    output = next(
                        row["payload"]
                        for row in records
                        if row.get("payload", {}).get("type")
                        == "custom_tool_call_output"
                    )
                    call["type"] = call_kind
                    output["type"] = output_kind
                    if call_kind != "custom_tool_call":
                        call["arguments"] = call.pop("input")
                    (call if target == "call" else output)[
                        "semantic_extension"
                    ] = {"changes_interpretation": True}
                    source, data = self.write_source(root, records)
                    with self.raises_code("unprojectable-record"):
                        EXPORTER.build_extract(self.spec(source, data))

        carrier_cases = (
            ("unselected-call", "payload"),
            ("unselected-output", "payload"),
            ("call-outer-envelope", "outer"),
            ("output-outer-envelope", "outer"),
            ("final-answer", "payload"),
            ("final-output-text", "block"),
        )
        for case, carrier in carrier_cases:
            with self.subTest(case=case), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                records = self.records(call_ids=("call-1", "call-2"))
                calls = [
                    row
                    for row in records
                    if row.get("payload", {}).get("type") == "custom_tool_call"
                ]
                outputs = [
                    row
                    for row in records
                    if row.get("payload", {}).get("type")
                    == "custom_tool_call_output"
                ]
                final = next(
                    row
                    for row in records
                    if row.get("payload", {}).get("phase") == "final_answer"
                )
                if case == "unselected-call":
                    target = calls[1]["payload"]
                elif case == "unselected-output":
                    target = outputs[1]["payload"]
                elif case == "call-outer-envelope":
                    target = calls[0]
                elif case == "output-outer-envelope":
                    target = outputs[0]
                elif case == "final-answer":
                    target = final["payload"]
                else:
                    target = final["payload"]["content"][0]
                target["semantic_extension"] = True
                source, data = self.write_source(root, records)
                with self.raises_code("unprojectable-record"):
                    EXPORTER.build_extract(
                        self.spec(source, data, call_ids=["call-1"])
                    )

    def test_response_item_turn_metadata_real_shape_and_coherence(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            records = self.records()
            reasoning_index = next(
                index
                for index, row in enumerate(records)
                if row.get("payload", {}).get("type") == "reasoning"
            )
            records.insert(
                reasoning_index,
                {
                    "type": "response_item",
                    "payload": {
                        "type": "agent_message",
                        "id": "agent-message-turn-1",
                        "content": [
                            {"type": "input_text", "text": "intermediate"}
                        ],
                        "internal_chat_message_metadata_passthrough": {
                            "turn_id": "turn-1"
                        },
                    },
                },
            )
            governed_kinds = {
                "message",
                "agent_message",
                "reasoning",
                "custom_tool_call",
                "custom_tool_call_output",
            }
            for row in records:
                item = row.get("payload", {})
                if (
                    row.get("type") == "response_item"
                    and item.get("type") in governed_kinds
                    and item.get("role") != "developer"
                ):
                    item["internal_chat_message_metadata_passthrough"] = {
                        "turn_id": "turn-1"
                    }
            source, data = self.write_source(root, records)
            run = EXPORTER.build_extract(self.spec(source, data))["runs"][0]
            self.assertEqual(run["complete_final_answer"]["record_locator"]["stable_id"], "answer-turn-1")
            self.assertTrue(run["derived_assertions"]["selected_evidence_within_one_logical_turn"])

        invalid_metadata = (
            ({}, "unprojectable-record"),
            ({"turn_id": ""}, "unprojectable-record"),
            ({"turn_id": "turn-1", "extra": True}, "unprojectable-record"),
            ({"turn_id": "turn-other"}, "cross-turn-selection"),
        )
        for metadata, error_code in invalid_metadata:
            with (
                self.subTest(metadata=metadata),
                tempfile.TemporaryDirectory() as temp,
            ):
                root = Path(temp)
                records = self.records()
                call = next(
                    row["payload"]
                    for row in records
                    if row.get("payload", {}).get("type") == "custom_tool_call"
                )
                call["internal_chat_message_metadata_passthrough"] = metadata
                source, data = self.write_source(root, records)
                with self.assertRaises(EXPORTER.ExportError) as captured:
                    EXPORTER.build_extract(self.spec(source, data))
                self.assertEqual(captured.exception.code, error_code)
                if error_code == "cross-turn-selection":
                    self.assertEqual(
                        captured.exception.details["reason"],
                        "response-item-turn-metadata-mismatch",
                    )

    def test_governed_source_schema_closes_selected_unselected_nested_and_outer_records(self) -> None:
        cases = (
            "selected-session",
            "selected-turn",
            "nested-sandbox-policy",
            "selected-reasoning",
            "nested-content-block",
            "unselected-call",
            "unselected-metadata",
            "world-state-outer",
        )
        for case in cases:
            with self.subTest(case=case), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                selected_turn = self.turn("turn-1")
                records = [self.session(), *selected_turn]
                start_line = 2
                if case in {"unselected-call", "unselected-metadata"}:
                    unselected_turn = self.turn(
                        "turn-unselected",
                        call_ids=("call-unselected",),
                    )
                    records = [
                        self.session(),
                        *unselected_turn,
                        *selected_turn,
                    ]
                    start_line = 2
                    unselected_call = next(
                        row["payload"]
                        for row in unselected_turn
                        if row.get("payload", {}).get("type")
                        == "custom_tool_call"
                    )
                    if case == "unselected-call":
                        unselected_call["semantic_extension"] = True
                    else:
                        unselected_call[
                            "internal_chat_message_metadata_passthrough"
                        ] = {
                            "turn_id": "wrong-turn",
                            "extra": True,
                        }
                elif case == "selected-session":
                    records[0]["payload"]["semantic_extension"] = True
                elif case == "selected-turn":
                    records[1]["payload"]["semantic_extension"] = True
                elif case == "nested-sandbox-policy":
                    records[1]["payload"]["sandbox_policy"]["extra"] = True
                elif case == "selected-reasoning":
                    reasoning = next(
                        row["payload"]
                        for row in records
                        if row.get("payload", {}).get("type") == "reasoning"
                    )
                    reasoning["semantic_extension"] = True
                elif case == "nested-content-block":
                    answer = next(
                        row["payload"]
                        for row in records
                        if row.get("payload", {}).get("phase")
                        == "final_answer"
                    )
                    answer["content"][0]["semantic_extension"] = True
                else:
                    records.insert(
                        1,
                        {
                            "type": "world_state",
                            "semantic_extension": True,
                            "payload": {"full": True, "state": {}},
                        },
                    )
                source, data = self.write_source(root, records)
                with self.raises_code("unprojectable-record"):
                    EXPORTER.build_extract(
                        self.spec(
                            source,
                            data,
                            start_line=start_line,
                        )
                    )

    def test_governed_source_call_contracts_follow_declared_semantic_scope(self) -> None:
        cases = (
            ("call-id", "call", "id", 7, "unprojectable-record"),
            ("call-call-id", "call", "call_id", 7, "unprojectable-record"),
            ("output-id", "output", "id", 7, "unprojectable-record"),
            (
                "output-call-id",
                "output",
                "call_id",
                7,
                "unprojectable-record",
            ),
            (
                "unsupported-call",
                "call",
                "type",
                "web_search_call",
                "unsupported-call-kind",
            ),
        )
        for selected in (True, False):
            for case, target, field, value, error_code in cases:
                with (
                    self.subTest(selected=selected, case=case),
                    tempfile.TemporaryDirectory() as temp,
                ):
                    root = Path(temp)
                    selected_turn = self.turn("turn-1")
                    if selected:
                        records = [self.session(), *selected_turn]
                        mutation_turn = selected_turn
                        start_line = 2
                    else:
                        unselected_turn = self.turn(
                            "turn-unselected",
                            call_ids=("call-unselected",),
                        )
                        records = [
                            self.session(),
                            *unselected_turn,
                            *selected_turn,
                        ]
                        mutation_turn = unselected_turn
                        start_line = len(unselected_turn) + 2
                    payload_kind = (
                        "custom_tool_call"
                        if target == "call"
                        else "custom_tool_call_output"
                    )
                    item = next(
                        row["payload"]
                        for row in mutation_turn
                        if row.get("payload", {}).get("type")
                        == payload_kind
                    )
                    item[field] = value
                    source, data = self.write_source(root, records)
                    value = self.spec(
                        source,
                        data,
                        start_line=start_line,
                    )
                    if selected:
                        with self.raises_code(error_code):
                            EXPORTER.build_extract(value)
                    else:
                        run = EXPORTER.build_extract(value)["runs"][0]
                        self.assertEqual(
                            [
                                call["call_id"]
                                for call in run["selected_task_calls"]
                            ],
                            ["call-1"],
                        )

    def test_scoped_call_discriminator_equivalence_matrix_fails_closed(self) -> None:
        cases = (
            (
                "custom-call-outer-delete",
                "custom_tool_call",
                "custom_tool_call_output",
                "call",
                "outer-delete",
            ),
            (
                "function-call-outer-rename",
                "function_call",
                "function_call_output",
                "call",
                "outer-rename",
            ),
            (
                "mcp-output-outer-value",
                "mcp_tool_call",
                "mcp_tool_call_output",
                "output",
                "outer-value",
            ),
            (
                "tool-output-outer-nonstring",
                "tool_call",
                "tool_call_output",
                "output",
                "outer-nonstring",
            ),
            (
                "custom-call-payload-delete",
                "custom_tool_call",
                "custom_tool_call_output",
                "call",
                "payload-delete",
            ),
            (
                "function-call-payload-rename",
                "function_call",
                "function_call_output",
                "call",
                "payload-rename",
            ),
            (
                "mcp-output-payload-value",
                "mcp_tool_call",
                "mcp_tool_call_output",
                "output",
                "payload-value",
            ),
            (
                "tool-output-payload-nonstring",
                "tool_call",
                "tool_call_output",
                "output",
                "payload-nonstring",
            ),
            (
                "tool-call-both-delete",
                "tool_call",
                "tool_call_output",
                "call",
                "both-delete",
            ),
            (
                "function-output-both-rename",
                "function_call",
                "function_call_output",
                "output",
                "both-rename",
            ),
        )
        for case, call_kind, output_kind, target, mutation in cases:
            with self.subTest(case=case), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                records = self.records()
                call_row = next(
                    row
                    for row in records
                    if row.get("payload", {}).get("type")
                    == "custom_tool_call"
                )
                output_row = next(
                    row
                    for row in records
                    if row.get("payload", {}).get("type")
                    == "custom_tool_call_output"
                )
                call_row["payload"]["type"] = call_kind
                output_row["payload"]["type"] = output_kind
                target_row = call_row if target == "call" else output_row
                if mutation == "outer-delete":
                    target_row.pop("type")
                elif mutation == "outer-rename":
                    target_row["record_type"] = target_row.pop("type")
                elif mutation == "outer-value":
                    target_row["type"] = "response-record"
                elif mutation == "outer-nonstring":
                    target_row["type"] = None
                elif mutation == "payload-delete":
                    target_row["payload"].pop("type")
                elif mutation == "payload-rename":
                    target_row["payload"]["kind"] = target_row[
                        "payload"
                    ].pop("type")
                elif mutation == "payload-value":
                    target_row["payload"]["type"] = "tool-result"
                elif mutation == "payload-nonstring":
                    target_row["payload"]["type"] = None
                elif mutation == "both-delete":
                    target_row.pop("type")
                    target_row["payload"].pop("type")
                else:
                    target_row["record_type"] = target_row.pop("type")
                    target_row["payload"]["kind"] = target_row[
                        "payload"
                    ].pop("type")
                source, data = self.write_source(
                    root,
                    records,
                    name=f"{case}.jsonl",
                )
                with self.assertRaises(EXPORTER.ExportError) as captured:
                    EXPORTER.build_extract(self.spec(source, data))
                self.assertEqual(
                    captured.exception.code,
                    "unprojectable-record",
                )
                self.assertEqual(
                    captured.exception.details["reason"],
                    "malformed-call-record-discriminator",
                )
                self.assertEqual(
                    captured.exception.details["detected_shape"],
                    target,
                )

    def test_scoped_call_discriminator_detection_ignores_unrelated_opaque_records(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            outside_turn = self.turn(
                "turn-outside",
                call_ids=("call-outside",),
            )
            outside_call = next(
                row
                for row in outside_turn
                if row.get("payload", {}).get("type")
                == "custom_tool_call"
            )
            outside_call["record_type"] = outside_call.pop("type")
            outside_call["payload"]["kind"] = outside_call[
                "payload"
            ].pop("type")
            selected_turn = self.turn("turn-1")
            opaque_records = [
                {
                    "type": "world_state",
                    "payload": {
                        "cwd": "C:/shadow",
                        "state": {"marker": "NOT-PROJECTED-OPAQUE"},
                    },
                },
                {
                    "type": "world_state",
                    "payload": {
                        "type": "opaque_payload",
                        "name": "not-a-call-without-arguments",
                    },
                },
                {
                    "type": "inter_agent_communication_metadata",
                    "payload": {
                        "type": "opaque_payload",
                        "input": {"marker": "NOT-PROJECTED-OPAQUE"},
                    },
                },
                {
                    "type": "event_msg",
                    "payload": {
                        "type": "opaque_event",
                        "call_id": "not-an-output-without-output",
                    },
                },
            ]
            selected_turn[3:3] = opaque_records
            records = [
                self.session(),
                *outside_turn,
                *selected_turn,
            ]
            selected_start = records.index(selected_turn[0]) + 1
            source, data = self.write_source(root, records)
            run = EXPORTER.build_extract(
                self.spec(
                    source,
                    data,
                    start_line=selected_start,
                )
            )["runs"][0]
            self.assertEqual(
                [
                    call["call_id"]
                    for call in run["selected_task_calls"]
                ],
                ["call-1"],
            )
            self.assertNotIn(
                b"NOT-PROJECTED-OPAQUE",
                EXPORTER.canonical_bytes(run),
            )

    def test_scoped_lifecycle_discriminator_equivalence_matrix_fails_closed(self) -> None:
        cases = (
            ("session-outer-delete", "session_meta", "rich", "outer-delete"),
            (
                "session-outer-known-wrong-rich",
                "session_meta",
                "rich",
                "outer-known-wrong",
            ),
            (
                "session-outer-known-wrong-sparse-id",
                "session_meta",
                "sparse-id",
                "outer-known-wrong",
            ),
            (
                "session-outer-known-wrong-sparse-session-id",
                "session_meta",
                "sparse-session-id",
                "outer-known-wrong",
            ),
            ("turn-outer-delete", "turn_context", "rich", "outer-delete"),
            ("turn-outer-rename", "turn_context", "rich", "outer-rename"),
            ("turn-outer-value", "turn_context", "rich", "outer-value"),
            ("turn-outer-nonstring", "turn_context", "rich", "outer-nonstring"),
            (
                "turn-outer-known-wrong-rich",
                "turn_context",
                "rich",
                "outer-known-wrong",
            ),
            (
                "turn-outer-known-wrong-sparse",
                "turn_context",
                "sparse",
                "outer-known-wrong",
            ),
            (
                "final-outer-known-wrong",
                "final_answer",
                "rich",
                "outer-known-wrong",
            ),
            ("final-payload-delete", "final_answer", "rich", "payload-delete"),
            ("final-payload-rename", "final_answer", "rich", "payload-rename"),
            ("final-payload-value", "final_answer", "rich", "payload-value"),
            (
                "final-payload-nonstring",
                "final_answer",
                "rich",
                "payload-nonstring",
            ),
            (
                "completion-outer-known-wrong",
                "task_completion",
                "rich",
                "outer-known-wrong",
            ),
            (
                "completion-payload-delete",
                "task_completion",
                "rich",
                "payload-delete",
            ),
            (
                "completion-payload-rename",
                "task_completion",
                "rich",
                "payload-rename",
            ),
            (
                "completion-payload-value",
                "task_completion",
                "rich",
                "payload-value",
            ),
            (
                "completion-payload-nonstring",
                "task_completion",
                "rich",
                "payload-nonstring",
            ),
        )
        for case, family, shape, mutation in cases:
            with self.subTest(case=case), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                records = self.records()
                if family == "session_meta":
                    target = copy.deepcopy(records[0])
                    insert_at = 3
                elif family == "turn_context":
                    target = copy.deepcopy(
                        next(row for row in records if row.get("type") == "turn_context")
                    )
                    insert_at = 3
                elif family == "final_answer":
                    insert_at = next(
                        index
                        for index, row in enumerate(records)
                        if row.get("payload", {}).get("phase") == "final_answer"
                    )
                    target = copy.deepcopy(records[insert_at])
                else:
                    insert_at = next(
                        index
                        for index, row in enumerate(records)
                        if row.get("payload", {}).get("type") == "task_complete"
                    )
                    target = copy.deepcopy(records[insert_at])
                if shape == "sparse-id":
                    target["payload"] = {"id": "session-record"}
                elif shape == "sparse-session-id":
                    target["payload"] = {"session_id": "session-root"}
                elif shape == "sparse":
                    target["payload"] = {"turn_id": "turn-1"}
                if mutation == "outer-delete":
                    target.pop("type")
                elif mutation == "outer-rename":
                    target["record_type"] = target.pop("type")
                elif mutation == "outer-value":
                    target["type"] = "renamed_record"
                elif mutation == "outer-nonstring":
                    target["type"] = None
                elif mutation == "outer-known-wrong":
                    target["type"] = "world_state"
                elif mutation == "payload-delete":
                    target["payload"].pop("type")
                elif mutation == "payload-rename":
                    target["payload"]["kind"] = target["payload"].pop("type")
                elif mutation == "payload-value":
                    target["payload"]["type"] = "renamed_payload"
                else:
                    target["payload"]["type"] = None
                records.insert(insert_at, target)
                source, data = self.write_source(root, records, name=f"{case}.jsonl")
                with self.assertRaises(EXPORTER.ExportError) as captured:
                    EXPORTER.build_extract(self.spec(source, data))
                self.assertEqual(captured.exception.code, "unprojectable-record")
                self.assertIn(
                    captured.exception.details["reason"],
                    {
                        "malformed-lifecycle-record-discriminator",
                        "malformed-outer-record-discriminator",
                    },
                )

    def test_lifecycle_discriminator_signatures_match_sparse_validators(self) -> None:
        cases = (
            (
                "session-id",
                {"id": "session-record"},
                EXPORTER.validate_session_meta_payload,
                ("session_meta", None, "session_meta"),
            ),
            (
                "session-session-id",
                {"session_id": "session-root"},
                EXPORTER.validate_session_meta_payload,
                ("session_meta", None, "session_meta"),
            ),
            (
                "turn-id",
                {"turn_id": "turn-1"},
                EXPORTER.validate_turn_context_payload,
                ("turn_context", None, "turn_context"),
            ),
        )
        for case, payload, validator, expected in cases:
            with self.subTest(case=case):
                validator(payload, label=case)
                self.assertEqual(
                    EXPORTER.lifecycle_discriminator_expectation(payload),
                    expected,
                )

    def test_session_meta_payload_requires_identity_matrix(self) -> None:
        cases = (
            ("empty", {}),
            ("cwd-only", {"cwd": "C:/shadow"}),
            ("role-only", {"agent_role": "reviewer"}),
        )
        for case, payload in cases:
            with self.subTest(case=case), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                records = self.records()
                records.insert(
                    3,
                    {
                        "type": "session_meta",
                        "payload": payload,
                    },
                )
                source, data = self.write_source(root, records, name=f"{case}.jsonl")
                with self.assertRaises(EXPORTER.ExportError) as captured:
                    EXPORTER.build_extract(self.spec(source, data))
                self.assertEqual(captured.exception.code, "unprojectable-record")
                self.assertEqual(
                    captured.exception.details["required_any"],
                    ["id", "session_id"],
                )

    def test_four_run_promotion_rejects_sparse_and_rich_discriminator_evasion(self) -> None:
        evasion_shapes = (
            ("session_meta", "sparse-id"),
            ("session_meta", "sparse-session-id"),
            ("turn_context", "sparse"),
            ("turn_context", "rich"),
        )
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            runs = []
            for index, (family, shape) in enumerate(evasion_shapes):
                turn_id = f"turn-{index}"
                turn = self.turn(turn_id)
                session = self.session(session_id=f"session-{index}")
                if family == "session_meta":
                    duplicate = copy.deepcopy(session)
                    if shape == "sparse-id":
                        duplicate["payload"] = {"id": "session-record"}
                    else:
                        duplicate["payload"] = {
                            "session_id": f"session-{index}"
                        }
                else:
                    duplicate = copy.deepcopy(turn[0])
                    if shape == "sparse":
                        duplicate["payload"] = {"turn_id": turn_id}
                duplicate["type"] = "world_state"
                records = [
                    session,
                    turn[0],
                    duplicate,
                    *turn[1:],
                ]
                source, data = self.write_source(
                    root,
                    records,
                    name=f"promotion-{index}.jsonl",
                )
                run = self.spec(
                    source,
                    data,
                    turn_id=turn_id,
                    start_line=2,
                    run_id=f"run-{index}",
                )["runs"][0]
                run["condition"] = "control" if index < 2 else "treatment"
                runs.append(run)
            value = self.spec(
                Path(runs[0]["source"]),
                Path(runs[0]["source"]).read_bytes(),
                start_line=2,
            )
            value["study"]["reporting"]["promotion_candidate"] = True
            value["runs"] = runs
            with self.assertRaises(EXPORTER.ExportError) as captured:
                EXPORTER.build_extract(value)
            self.assertEqual(captured.exception.code, "unprojectable-record")
            self.assertEqual(
                captured.exception.details["reason"],
                "malformed-lifecycle-record-discriminator",
            )

    def test_governed_call_graph_is_complete_for_every_scope_intersecting_turn(self) -> None:
        cases = (
            (
                "missing-output",
                "call-output-binding-error",
                "missing-call-output",
            ),
            (
                "orphan-output",
                "call-output-binding-error",
                "orphaned-call-output",
            ),
            (
                "cross-kind-output",
                "call-output-binding-error",
                "cross-kind-call-output",
            ),
            ("duplicate-call-conflict", "duplicate-call-conflict", None),
            ("stable-id-reuse", "stable-record-conflict", None),
        )
        for case, error_code, reason in cases:
            with self.subTest(case=case), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                unselected_turn = self.turn(
                    "turn-unselected",
                    call_ids=("call-unselected",),
                )
                selected_turn = self.turn("turn-1")
                unselected_call = next(
                    row
                    for row in unselected_turn
                    if row.get("payload", {}).get("type")
                    == "custom_tool_call"
                )
                unselected_output = next(
                    row
                    for row in unselected_turn
                    if row.get("payload", {}).get("type")
                    == "custom_tool_call_output"
                )
                if case == "missing-output":
                    unselected_turn.remove(unselected_output)
                elif case == "orphan-output":
                    orphan = copy.deepcopy(unselected_output)
                    orphan["payload"]["id"] = "orphan-output"
                    orphan["payload"]["call_id"] = "orphan-call"
                    unselected_turn.insert(
                        unselected_turn.index(unselected_output) + 1,
                        orphan,
                    )
                elif case == "cross-kind-output":
                    unselected_output["payload"]["type"] = (
                        "function_call_output"
                    )
                elif case == "duplicate-call-conflict":
                    duplicate = copy.deepcopy(unselected_call)
                    duplicate["payload"]["id"] = "duplicate-call-record"
                    duplicate["payload"]["input"]["ordinal"] = 99
                    unselected_turn.insert(
                        unselected_turn.index(unselected_call) + 1,
                        duplicate,
                    )
                else:
                    reused = copy.deepcopy(unselected_call)
                    reused["payload"]["call_id"] = "reused-id-call"
                    reused["payload"]["input"]["ordinal"] = 99
                    unselected_turn.insert(
                        unselected_turn.index(unselected_call) + 1,
                        reused,
                    )
                records = [
                    self.session(),
                    *unselected_turn,
                    *selected_turn,
                ]
                source, data = self.write_source(root, records)
                with self.assertRaises(EXPORTER.ExportError) as captured:
                    EXPORTER.build_extract(
                        self.spec(
                            source,
                            data,
                            start_line=2,
                        )
                    )
                self.assertEqual(captured.exception.code, error_code)
                if reason is not None:
                    self.assertEqual(
                        captured.exception.details["reason"],
                        reason,
                    )

    def test_call_identity_graph_completeness_fails_closed_matrix(self) -> None:
        for call_kind, output_kind in EXPORTER.CALL_OUTPUT_KIND.items():
            for selected in (True, False):
                for call_id_state in (
                    "absent-no-fallback",
                    "absent-stable-fallback",
                    "empty",
                    "wrong-type",
                ):
                    for output_present in (False, True):
                        with (
                            self.subTest(
                                call_kind=call_kind,
                                selected=selected,
                                call_id_state=call_id_state,
                                output_present=output_present,
                            ),
                            tempfile.TemporaryDirectory() as temp,
                        ):
                            root = Path(temp)
                            call_ids = (
                                ("call-1",)
                                if selected
                                else ("call-1", "call-unselected")
                            )
                            records = self.records(call_ids=call_ids)
                            calls = [
                                row
                                for row in records
                                if row.get("payload", {}).get("type")
                                == "custom_tool_call"
                            ]
                            outputs = [
                                row
                                for row in records
                                if row.get("payload", {}).get("type")
                                == "custom_tool_call_output"
                            ]
                            target_index = 0 if selected else 1
                            call_row = calls[target_index]
                            output_row = outputs[target_index]
                            call = call_row["payload"]
                            output = output_row["payload"]
                            call["type"] = call_kind
                            output["type"] = output_kind
                            if call_kind != "custom_tool_call":
                                call["arguments"] = call.pop("input")
                            if call_id_state.startswith("absent-"):
                                call.pop("call_id")
                                if call_id_state == "absent-no-fallback":
                                    call.pop("id")
                            elif call_id_state == "empty":
                                call["call_id"] = ""
                            else:
                                call["call_id"] = {"wrong": "type"}
                            if not output_present:
                                records.remove(output_row)
                            source, data = self.write_source(root, records)
                            value = self.spec(
                                source,
                                data,
                                call_ids=["call-1"],
                            )
                            value["study"]["reporting"][
                                "promotion_candidate"
                            ] = True
                            with self.assertRaises(
                                EXPORTER.ExportError
                            ) as captured:
                                EXPORTER.build_extract(value)
                            if call_id_state == "absent-no-fallback":
                                self.assertEqual(
                                    captured.exception.code,
                                    "call-output-binding-error",
                                )
                                self.assertEqual(
                                    captured.exception.details["reason"],
                                    "missing-call-identity",
                                )
                            elif call_id_state == "absent-stable-fallback":
                                self.assertEqual(
                                    captured.exception.code,
                                    "call-output-binding-error",
                                )
                                self.assertEqual(
                                    captured.exception.details["reason"],
                                    (
                                        "orphaned-call-output"
                                        if output_present
                                        else "missing-call-output"
                                    ),
                                )
                            else:
                                self.assertEqual(
                                    captured.exception.code,
                                    "unprojectable-record",
                                )

    def test_supported_call_identity_positive_controls(self) -> None:
        for call_kind, output_kind in EXPORTER.CALL_OUTPUT_KIND.items():
            with (
                self.subTest(call_kind=call_kind, identity="call-id"),
                tempfile.TemporaryDirectory() as temp,
            ):
                root = Path(temp)
                records = self.records()
                call = next(
                    row["payload"]
                    for row in records
                    if row.get("payload", {}).get("type")
                    == "custom_tool_call"
                )
                output = next(
                    row["payload"]
                    for row in records
                    if row.get("payload", {}).get("type")
                    == "custom_tool_call_output"
                )
                call["type"] = call_kind
                output["type"] = output_kind
                if call_kind != "custom_tool_call":
                    call["arguments"] = call.pop("input")
                source, data = self.write_source(root, records)
                run = EXPORTER.build_extract(
                    self.spec(source, data)
                )["runs"][0]
                self.assertTrue(
                    run["derived_assertions"][
                        "scope_intersecting_turn_call_output_graphs_complete"
                    ]
                )
                self.assertEqual(
                    run["selected_task_calls"][0]["output_payload_kind"],
                    output_kind,
                )

            with (
                self.subTest(
                    call_kind=call_kind,
                    identity="stable-id-fallback",
                ),
                tempfile.TemporaryDirectory() as temp,
            ):
                root = Path(temp)
                records = self.records(
                    call_ids=("call-1", "call-unselected")
                )
                calls = [
                    row["payload"]
                    for row in records
                    if row.get("payload", {}).get("type")
                    == "custom_tool_call"
                ]
                outputs = [
                    row["payload"]
                    for row in records
                    if row.get("payload", {}).get("type")
                    == "custom_tool_call_output"
                ]
                call = calls[1]
                output = outputs[1]
                call["type"] = call_kind
                output["type"] = output_kind
                if call_kind != "custom_tool_call":
                    call["arguments"] = call.pop("input")
                call.pop("call_id")
                output["call_id"] = call["id"]
                source, data = self.write_source(root, records)
                run = EXPORTER.build_extract(
                    self.spec(source, data, call_ids=["call-1"])
                )["runs"][0]
                fallback_entry = next(
                    entry
                    for entry in run["function_call_inventory"]
                    if entry["stable_id"] == call["id"]
                )
                self.assertIsNone(fallback_entry["call_id"])
                self.assertTrue(
                    run["derived_assertions"][
                        "scope_intersecting_turn_call_output_graphs_complete"
                    ]
                )

    def test_no_call_id_stable_fallback_distinct_and_replay_cases(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            records = self.records(
                call_ids=("call-1", "fallback-a", "fallback-b")
            )
            calls = [
                row
                for row in records
                if row.get("payload", {}).get("type")
                == "custom_tool_call"
            ]
            outputs = [
                row
                for row in records
                if row.get("payload", {}).get("type")
                == "custom_tool_call_output"
            ]
            for call_row, output_row in zip(
                calls[1:],
                outputs[1:],
                strict=True,
            ):
                call = call_row["payload"]
                output = output_row["payload"]
                call["type"] = "function_call"
                call["arguments"] = call.pop("input")
                call.pop("call_id")
                output["type"] = "function_call_output"
                output["call_id"] = call["id"]
            source, data = self.write_source(
                root,
                records,
                name="distinct-stable-fallbacks.jsonl",
            )
            run = EXPORTER.build_extract(
                self.spec(source, data, call_ids=["call-1"])
            )["runs"][0]
            self.assertEqual(run["call_coverage"]["unique_call_count"], 3)
            self.assertEqual(
                [
                    entry["stable_id"]
                    for entry in run["function_call_inventory"]
                    if entry["call_id"] is None
                ],
                [calls[1]["payload"]["id"], calls[2]["payload"]["id"]],
            )

            replay_records = self.records(
                call_ids=("call-1", "fallback-replay")
            )
            replay_call = next(
                row
                for row in replay_records
                if row.get("payload", {}).get("call_id")
                == "fallback-replay"
                and row["payload"].get("type") == "custom_tool_call"
            )
            replay_output = next(
                row
                for row in replay_records
                if row.get("payload", {}).get("call_id")
                == "fallback-replay"
                and row["payload"].get("type")
                == "custom_tool_call_output"
            )
            replay_call["payload"]["type"] = "function_call"
            replay_call["payload"]["arguments"] = replay_call[
                "payload"
            ].pop("input")
            replay_call["payload"].pop("call_id")
            replay_call["timestamp"] = "2026-07-27T00:00:01Z"
            replay_output["payload"]["type"] = "function_call_output"
            replay_output["payload"]["call_id"] = replay_call["payload"]["id"]
            replay = copy.deepcopy(replay_call)
            replay["timestamp"] = "2026-07-27T00:00:02Z"
            replay_records.insert(
                replay_records.index(replay_call) + 1,
                replay,
            )
            replay_source, replay_data = self.write_source(
                root,
                replay_records,
                name="replayed-stable-fallback.jsonl",
            )
            replay_run = EXPORTER.build_extract(
                self.spec(
                    replay_source,
                    replay_data,
                    call_ids=["call-1"],
                )
            )["runs"][0]
            self.assertEqual(
                replay_run["call_coverage"]["source_call_record_count"],
                3,
            )
            self.assertEqual(
                replay_run["call_coverage"]["unique_call_count"],
                2,
            )
            self.assertEqual(
                replay_run["call_coverage"]["duplicate_call_record_count"],
                1,
            )
            replay_entry = next(
                entry
                for entry in replay_run["function_call_inventory"]
                if entry["stable_id"] == replay_call["payload"]["id"]
            )
            self.assertEqual(
                len(replay_entry["duplicate_record_locators"]),
                1,
            )
            self.assertTrue(
                replay_run["derived_assertions"][
                    "scope_intersecting_turn_call_output_graphs_complete"
                ]
            )

    def test_call_outputs_cannot_bridge_physical_turn_or_session_boundaries(self) -> None:
        for boundary in ("turn", "session"):
            with self.subTest(boundary=boundary), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                call_turn = self.turn(
                    "turn-call",
                    call_ids=("bridge-call",),
                )
                output_turn = self.turn(
                    "turn-output",
                    call_ids=("bridge-call",),
                )
                call_turn.remove(
                    next(
                        row
                        for row in call_turn
                        if row.get("payload", {}).get("type")
                        == "custom_tool_call_output"
                    )
                )
                output_turn.remove(
                    next(
                        row
                        for row in output_turn
                        if row.get("payload", {}).get("type")
                        == "custom_tool_call"
                    )
                )
                selected_turn = self.turn("turn-1")
                records = [self.session(), *call_turn]
                if boundary == "session":
                    records.append(
                        self.session(session_id="session-second")
                    )
                records.extend([*output_turn, *selected_turn])
                selected_start = (
                    next(
                        index
                        for index, row in enumerate(records)
                        if row.get("type") == "turn_context"
                        and row.get("payload", {}).get("turn_id")
                        == "turn-1"
                    )
                    + 1
                )
                source, data = self.write_source(root, records)
                value = self.spec(
                    source,
                    data,
                    start_line=2,
                )
                if boundary == "session":
                    value["runs"][0]["record_selection"][
                        "session_meta"
                    ] = {"stable_id": "session-record"}
                with self.assertRaises(EXPORTER.ExportError) as captured:
                    EXPORTER.build_extract(value)
                self.assertEqual(
                    captured.exception.code,
                    "call-output-binding-error",
                )
                self.assertEqual(
                    captured.exception.details["reason"],
                    "missing-call-output",
                )
                self.assertEqual(
                    captured.exception.details["turn_identity"],
                    "turn-call",
                )

    def test_session_transition_inside_unselected_turn_fails_before_graph_binding(self) -> None:
        for position in ("before-call", "before-output", "before-completion"):
            with self.subTest(position=position), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                malformed_turn = self.turn(
                    "turn-malformed",
                    call_ids=("bridge-call",),
                )
                payload_kind = {
                    "before-call": "custom_tool_call",
                    "before-output": "custom_tool_call_output",
                    "before-completion": "task_complete",
                }[position]
                insertion_index = next(
                    index
                    for index, row in enumerate(malformed_turn)
                    if row.get("payload", {}).get("type")
                    == payload_kind
                )
                malformed_turn.insert(
                    insertion_index,
                    self.session(session_id="session-second"),
                )
                selected_turn = self.turn("turn-1")
                records = [
                    self.session(session_id="session-first"),
                    *malformed_turn,
                    *selected_turn,
                ]
                selected_start = (
                    next(
                        index
                        for index, row in enumerate(records)
                        if row.get("type") == "turn_context"
                        and row.get("payload", {}).get("turn_id")
                        == "turn-1"
                    )
                    + 1
                )
                source, data = self.write_source(root, records)
                value = self.spec(
                    source,
                    data,
                    start_line=2,
                )
                value["runs"][0]["record_selection"]["session_meta"] = {
                    "occurrence": 2
                }
                with self.assertRaises(EXPORTER.ExportError) as captured:
                    EXPORTER.build_extract(value)
                self.assertEqual(
                    captured.exception.code,
                    "session-turn-binding-error",
                )
                self.assertEqual(
                    captured.exception.details["reason"],
                    "session-metadata-inside-turn-segment",
                )
                self.assertEqual(
                    captured.exception.details["turn_id"],
                    "turn-malformed",
                )
                transition_line = (
                    records.index(
                        next(
                            row
                            for row in malformed_turn
                            if row.get("type") == "session_meta"
                        )
                    )
                    + 1
                )
                self.assertEqual(
                    captured.exception.details["source_lines"],
                    [transition_line],
                )

    def test_recognized_outer_timestamp_is_a_nonempty_string(self) -> None:
        invalid_values = (None, True, 7, {}, [], "")
        for value in invalid_values:
            with self.subTest(value=value), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                records = [
                    self.session(),
                    {
                        "timestamp": value,
                        "type": "world_state",
                        "payload": {"full": True, "state": {}},
                    },
                    *self.turn("turn-1"),
                ]
                source, data = self.write_source(root, records)
                with self.raises_code("unprojectable-record"):
                    EXPORTER.build_extract(
                        self.spec(source, data, start_line=2)
                    )

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            records = self.records()
            records[0]["timestamp"] = "2026-07-27T00:00:00Z"
            source, data = self.write_source(root, records)
            EXPORTER.build_extract(self.spec(source, data))

    def test_nonfinite_json_is_rejected_at_parse_and_serialize_boundaries(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            spec_cases = (
                ('{"schema_version":NaN}', "nonfinite_constant"),
                ('{"nested":{"positive":1e400}}', "json_path"),
                ('{"nested":{"negative":-1e400}}', "json_path"),
            )
            for index, (raw_spec, detail_field) in enumerate(spec_cases):
                with self.subTest(spec_case=index):
                    spec_path = root / f"nonfinite-spec-{index}.json"
                    spec_path.write_text(raw_spec, encoding="utf-8")
                    with self.assertRaises(EXPORTER.ExportError) as captured:
                        EXPORTER.load_json(spec_path)
                    self.assertEqual(captured.exception.code, "invalid-json")
                    self.assertIn(detail_field, captured.exception.details)

            for selected in (True, False):
                for exponent in ("1e400", "-1e400"):
                    with self.subTest(selected=selected, exponent=exponent):
                        records = self.records(
                            call_ids=("call-1", "call-2"),
                        )
                        calls = [
                            row["payload"]
                            for row in records
                            if row.get("payload", {}).get("type")
                            == "custom_tool_call"
                        ]
                        calls[0 if selected else 1]["input"][
                            "nested_nonfinite"
                        ] = {"value": "EXPONENT_OVERFLOW"}
                        data = jsonl_bytes(records).replace(
                            b'"EXPONENT_OVERFLOW"',
                            exponent.encode("ascii"),
                        )
                        source = root / (
                            f"overflow-{selected}-{exponent[0]}.jsonl"
                        )
                        source.write_bytes(data)
                        with self.raises_code("rollout-parse-error"):
                            EXPORTER.build_extract(
                                self.spec(
                                    source,
                                    data,
                                    call_ids=["call-1"],
                                )
                            )

            finite = EXPORTER.strict_json_loads(
                '{"positive":1e308,"negative":-1e308}'
            )
            self.assertEqual(finite["positive"], 1e308)
            self.assertEqual(finite["negative"], -1e308)
            finite_records = self.records()
            finite_call = next(
                row["payload"]
                for row in finite_records
                if row.get("payload", {}).get("type") == "custom_tool_call"
            )
            finite_call["input"]["extremes"] = finite
            finite_source, finite_data = self.write_source(
                root,
                finite_records,
                name="finite-extremes.jsonl",
            )
            projected = EXPORTER.build_extract(
                self.spec(finite_source, finite_data)
            )["runs"][0]["selected_task_calls"][0]["arguments"]["extremes"]
            self.assertEqual(projected, finite)

            candidate = root / "nonfinite-candidate.json"
            candidate_data = b'{"nested":{"positive":1e400}}'
            with self.assertRaises(EXPORTER.ExportError) as captured:
                EXPORTER.validate_artifact_json_bytes(
                    candidate,
                    candidate_data,
                )
            self.assertEqual(captured.exception.code, "invalid-json")
            self.assertEqual(
                captured.exception.details["json_path"],
                "$.nested.positive",
            )

            with self.assertRaises(ValueError):
                EXPORTER.canonical_bytes({"nonfinite": float("nan")})
            with self.raises_code("unprojectable-record"):
                EXPORTER.json_value_hash({"nonfinite": float("-inf")})

    def test_projected_source_field_contract_matrix(self) -> None:
        cases = (
            ("session-present-null", "session", "session_id", None, "set"),
            ("session-identities-missing", "session", None, None, "drop-identities"),
            ("turn-id-missing", "turn", "turn_id", None, "drop"),
            ("turn-id-null", "turn", "turn_id", None, "set"),
            ("turn-id-bool", "turn", "turn_id", True, "set"),
            ("turn-id-empty", "turn", "turn_id", "", "set"),
            ("turn-id-wrong-type", "turn", "turn_id", {}, "set"),
            ("completion-field-missing", "completion", "duration_ms", None, "drop"),
            ("completion-field-unknown", "completion", "status_detail", {}, "set"),
            ("completion-null", "completion", "time_to_first_token_ms", None, "set"),
            ("completion-bool", "completion", "duration_ms", False, "set"),
            ("completion-empty", "completion", "completed_at", [], "set"),
            ("completion-wrong-type", "completion", "started_at", {}, "set"),
        )
        for case, target, field, replacement, operation in cases:
            with self.subTest(case=case), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                records = self.records()
                targets = {
                    "session": records[0]["payload"],
                    "turn": next(
                        row["payload"]
                        for row in records
                        if row.get("type") == "turn_context"
                    ),
                    "completion": next(
                        row["payload"]
                        for row in records
                        if row.get("type") == "event_msg"
                        and row.get("payload", {}).get("type") == "task_complete"
                    ),
                }
                item = targets[target]
                if operation == "drop-identities":
                    item.pop("session_id")
                    item.pop("id")
                elif operation == "drop":
                    item.pop(field)
                else:
                    item[field] = replacement
                source, data = self.write_source(root, records)
                value = self.spec(source, data)
                if target == "turn":
                    value["runs"][0]["record_selection"]["turn_context"] = {
                        "source_line": 3,
                    }
                if target == "completion" and field == "turn_id":
                    value["runs"][0]["record_selection"]["task_completion"] = {
                        "source_line": len(records),
                    }
                with self.raises_code("unprojectable-record"):
                    EXPORTER.build_extract(value)

    def test_selected_call_fields_are_present_unambiguous_and_exact(self) -> None:
        cases = ("missing-arguments", "missing-output", "both-same", "both-conflicting")
        for case in cases:
            with self.subTest(case=case), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                records = self.records()
                call = next(
                    row["payload"]
                    for row in records
                    if row["payload"].get("type") == "custom_tool_call"
                )
                output = next(
                    row["payload"]
                    for row in records
                    if row["payload"].get("type") == "custom_tool_call_output"
                )
                if case == "missing-arguments":
                    call.pop("input")
                elif case == "missing-output":
                    output.pop("output")
                else:
                    call["arguments"] = (
                        call["input"]
                        if case == "both-same"
                        else {"path": "C:/conflicting.txt"}
                    )
                source, data = self.write_source(root, records)
                with self.raises_code("unprojectable-record"):
                    EXPORTER.build_extract(self.spec(source, data))

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            records = self.records()
            call = next(
                row["payload"]
                for row in records
                if row["payload"].get("type") == "custom_tool_call"
            )
            output = next(
                row["payload"]
                for row in records
                if row["payload"].get("type") == "custom_tool_call_output"
            )
            call["input"] = None
            output["output"] = None
            source, data = self.write_source(root, records)
            run = EXPORTER.build_extract(self.spec(source, data))["runs"][0]
            self.assertIsNone(run["selected_task_calls"][0]["arguments"])
            self.assertIsNone(run["selected_task_calls"][0]["exact_output"])

    def test_call_graph_rejects_unsupported_cross_kind_orphan_and_identity_conflicts(self) -> None:
        cases = (
            ("unsupported-web", "unsupported-call-kind", None),
            ("unsupported-computer", "unsupported-call-kind", None),
            ("unsupported-shell", "unsupported-call-kind", None),
            ("cross-kind-output", "call-output-binding-error", "cross-kind-call-output"),
            ("orphan-output", "call-output-binding-error", "orphaned-call-output"),
            ("different-call-kind", "duplicate-call-conflict", None),
            ("different-stable-id", "duplicate-call-conflict", None),
        )
        for case, code, reason in cases:
            with self.subTest(case=case), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                records = self.records()
                call = next(row for row in records if row["payload"].get("type") == "custom_tool_call")
                output = next(
                    row
                    for row in records
                    if row["payload"].get("type") == "custom_tool_call_output"
                )
                if case.startswith("unsupported-"):
                    kind = {
                        "unsupported-web": "web_search_call",
                        "unsupported-computer": "computer_call",
                        "unsupported-shell": "local_shell_call",
                    }[case]
                    extra_call = copy.deepcopy(call)
                    extra_call["payload"]["type"] = kind
                    extra_call["payload"]["id"] = f"{kind}-id"
                    extra_call["payload"]["call_id"] = f"{kind}-call-id"
                    extra_output = copy.deepcopy(output)
                    extra_output["payload"]["type"] = f"{kind}_output"
                    extra_output["payload"]["id"] = f"{kind}-output-id"
                    extra_output["payload"]["call_id"] = f"{kind}-call-id"
                    records[5:5] = [extra_call, extra_output]
                elif case == "cross-kind-output":
                    output["payload"]["type"] = "function_call_output"
                elif case == "orphan-output":
                    orphan = copy.deepcopy(output)
                    orphan["payload"]["id"] = "orphan-output"
                    orphan["payload"]["call_id"] = "orphan-call"
                    records.insert(5, orphan)
                else:
                    duplicate = copy.deepcopy(call)
                    duplicate["payload"]["id"] = "different-stable-id"
                    if case == "different-call-kind":
                        duplicate["payload"]["type"] = "function_call"
                    records.insert(4, duplicate)
                source, data = self.write_source(root, records)
                with self.assertRaises(EXPORTER.ExportError) as captured:
                    EXPORTER.build_extract(self.spec(source, data))
                self.assertEqual(captured.exception.code, code)
                if reason is not None:
                    self.assertEqual(captured.exception.details["reason"], reason)

    def test_call_field_contract_and_scope_graph_totality_matrix(self) -> None:
        invalid_fields = (
            ("name-missing", "name", None, "drop"),
            ("name-null", "name", None, "set"),
            ("name-bool", "name", False, "set"),
            ("name-empty", "name", "", "set"),
            ("name-whitespace", "name", "   ", "set"),
            ("name-wrong-type", "name", {}, "set"),
            ("namespace-null", "namespace", None, "set"),
            ("namespace-bool", "namespace", False, "set"),
            ("namespace-empty", "namespace", "", "set"),
            ("namespace-wrong-type", "namespace", {}, "set"),
            ("status-null", "status", None, "set"),
            ("status-bool", "status", False, "set"),
            ("status-empty", "status", "", "set"),
            ("status-wrong-type", "status", {}, "set"),
        )
        for case, field, replacement, operation in invalid_fields:
            with self.subTest(field=case), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                records = self.records()
                call = next(
                    row["payload"]
                    for row in records
                    if row.get("payload", {}).get("type") == "custom_tool_call"
                )
                if operation == "drop":
                    call.pop(field)
                else:
                    call[field] = replacement
                source, data = self.write_source(root, records)
                with self.raises_code("unprojectable-record"):
                    EXPORTER.build_extract(self.spec(source, data))

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            records = self.records(call_ids=("call-1", "call-2"))
            records = [
                row
                for row in records
                if not (
                    row.get("payload", {}).get("type") == "custom_tool_call_output"
                    and row["payload"].get("call_id") == "call-2"
                )
            ]
            source, data = self.write_source(root, records)
            with self.assertRaises(EXPORTER.ExportError) as captured:
                EXPORTER.build_extract(
                    self.spec(source, data, call_ids=["call-1"])
                )
            self.assertEqual(captured.exception.code, "call-output-binding-error")
            self.assertEqual(captured.exception.details["reason"], "missing-call-output")
            self.assertEqual(captured.exception.details["call_id"], "call-2")

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            records = self.records()
            call = next(
                row["payload"]
                for row in records
                if row.get("payload", {}).get("type") == "custom_tool_call"
            )
            call.pop("namespace")
            call.pop("status")
            source, data = self.write_source(root, records)
            selected = EXPORTER.build_extract(
                self.spec(source, data)
            )["runs"][0]["selected_task_calls"][0]
            self.assertIsNone(selected["namespace"])
            self.assertIsNone(selected["status_transitions"][0]["status"])

    def test_scoped_graph_rejects_stable_id_and_unselected_output_conflicts(self) -> None:
        cases = (
            ("call-stable-id-reuse", "stable-record-conflict"),
            ("output-stable-id-reuse", "stable-record-conflict"),
            ("cross-kind-stable-id-reuse", "stable-record-conflict"),
            ("cross-record-stable-id-reuse", "stable-record-conflict"),
            ("unselected-output-value-conflict", "stable-record-conflict"),
            ("unselected-output-id-conflict", "duplicate-output-conflict"),
        )
        for case, code in cases:
            with self.subTest(case=case), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                records = self.records(call_ids=("call-1", "call-2"))
                calls = [
                    row for row in records
                    if row["payload"].get("type") == "custom_tool_call"
                ]
                outputs = [
                    row for row in records
                    if row["payload"].get("type") == "custom_tool_call_output"
                ]
                if case == "call-stable-id-reuse":
                    calls[1]["payload"]["id"] = calls[0]["payload"]["id"]
                elif case == "output-stable-id-reuse":
                    outputs[1]["payload"]["id"] = outputs[0]["payload"]["id"]
                elif case == "cross-kind-stable-id-reuse":
                    outputs[0]["payload"]["id"] = calls[0]["payload"]["id"]
                elif case == "cross-record-stable-id-reuse":
                    answer = next(
                        row for row in records
                        if row["payload"].get("phase") == "final_answer"
                    )
                    answer["payload"]["id"] = calls[0]["payload"]["id"]
                else:
                    duplicate = copy.deepcopy(outputs[1])
                    if case == "unselected-output-value-conflict":
                        duplicate["payload"]["output"] = "different"
                    else:
                        duplicate["payload"]["id"] = "different-output-id"
                    records.insert(records.index(outputs[1]) + 1, duplicate)
                source, data = self.write_source(root, records)
                with self.raises_code(code):
                    EXPORTER.build_extract(
                        self.spec(source, data, call_ids=["call-1"])
                    )

    def test_record_selector_values_are_type_strict(self) -> None:
        cases = (
            {"source_line": True},
            {"source_line": 1.0},
            {"source_line": None},
            {"stable_id": ""},
            {"stable_id": 1},
            {"call_id": None},
            {"turn_id": 1},
            {"occurrence": True},
            {"occurrence": 1.0},
        )
        for selector in cases:
            with self.subTest(selector=selector), self.raises_code("invalid-spec"):
                EXPORTER.select_rows(
                    [],
                    selector,
                    label="fixture.selector",
                    predicate=lambda _row: True,
                )

    def test_selected_json_and_source_like_content_is_retained_exactly(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            exact_output = (
                'prefix {"type":"session_meta","payload":{"encrypted_content":"example"}}\n'
                '```json\n{"role":"system","content":"schema example"}\n```\n'
                "C:/users/example/.codex/sessions/rollout-example.jsonl"
            )
            exact_answer = (
                "Synthetic evidence includes REQUIRED.\n"
                '{"role":"assistant","content":"ordinary source example"}\n'
                "C:/fixtures/rollout-example.jsonl"
            )
            records = self.records(
                outputs=(exact_output,),
                answer_blocks=(exact_answer,),
            )
            records[3]["payload"]["input"]["schema_example"] = {
                "role": "developer",
                "reasoning": {"encrypted_content": "ordinary task data"},
            }
            source, data = self.write_source(root, records)
            run = EXPORTER.build_extract(self.spec(source, data))["runs"][0]
            selected = run["selected_task_calls"][0]
            self.assertEqual(selected["exact_output"], exact_output)
            self.assertEqual(
                run["complete_final_answer"]["content_blocks"][0]["text"],
                exact_answer,
            )
            self.assertEqual(
                run["complete_task_completion"]["last_agent_message"],
                exact_answer,
            )
            self.assertEqual(
                selected["arguments"]["schema_example"],
                {
                    "role": "developer",
                    "reasoning": {"encrypted_content": "ordinary task data"},
                },
            )

if __name__ == "__main__":
    unittest.main()
