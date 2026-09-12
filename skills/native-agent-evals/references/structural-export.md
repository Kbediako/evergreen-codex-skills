# Structural evidence export

Never send a source rollout. Use `scripts/export_structural_rollout.py` with a schema-v3 JSON spec. The spec declares:

- claim, rubric, classification source/checks, and pass aggregation;
- study-wide worker expectations, actual cross-run worker invariance, and
  promotion status;
- source path and exact SHA-256;
- neutral run ID and condition;
- nonempty unique `selected_call_ids`;
- inclusive line scope and selectors for session metadata, turn context, final answer, and completion.

## Trials without tool calls

A natural-trigger negative case may correctly finish without any tool call. The current exporter requires nonempty `selected_call_ids`, so it cannot export that trial. Preserve the complete answer and available local provenance, report the export limitation, and keep it out of exporter-backed promotion. Do not invent a call, select a coordinator call from another turn, force a child call that changes the trial condition, or transmit a raw rollout. An observation without an export is limited local evidence, not a validated structural extract.

Minimal shape:

```json
{
  "schema_version": 3,
  "study": {
    "claim": "The selected answer contains the required evidence.",
    "rubric": "Pass when REQUIRED is present.",
    "classification": {
      "source": "complete_final_answer",
      "pass_when": "all",
      "checks": [{"id": "required", "operator": "contains", "value": "REQUIRED"}]
    },
    "worker_expectations": {
      "model": "expected-model",
      "effort": "expected-effort",
      "role": "expected-role",
      "sandbox_policy": {"type": "expected-sandbox"},
      "approval_policy": "expected-approval",
      "permission_profile": {"type": "expected-permissions"}
    },
    "reporting": {
      "promotion_candidate": false,
      "evidence_grade": "declared-grade",
      "known_limits": ["Declare study-specific limits."]
    }
  },
  "runs": [{
    "run_id": "neutral-run-01",
    "condition": "condition-a",
    "source": "C:/path/to/rollout.jsonl",
    "expected_source_sha256": "<64 lowercase hex characters>",
    "selected_call_ids": ["call-id"],
    "record_selection": {
      "scope": {"start_line": 10, "end_line": 40},
      "session_meta": {"source_line": 1},
      "turn_context": {"turn_id": "turn-id"},
      "final_answer": {"stable_id": "answer-id"},
      "task_completion": {"turn_id": "turn-id"}
    }
  }]
}
```

Run specifications cannot override worker expectations. Promotion candidates
also compare the actual model, effort, role, sandbox policy, approval policy,
and permission profile across every run; missing or different values fail the
machine gate.

Classification sources are `complete_final_answer`, `complete_task_completion.last_agent_message`, `selected_task_calls.arguments`, and `selected_task_calls.output`. Selected-call sources require `classification.selected_call_id`. Checks support `contains`, `not_contains`, `equals`, `regex`, and `not_regex`; regex flags are `i`, `m`, and `s`.

Worker expectations may name `model`, `effort`, `role`, `sandbox_policy`, `sandbox_type`, `approval_policy`, `permission_profile`, `permission_profile_type`, and `cwd`. Promotion requires every declared expectation to match.

The declared line scope and selected governing-session envelope are closed and validated before projection. They reject duplicate keys, non-finite JSON values, unsupported call-like records, unknown fields on recognized records, malformed nested policies or turn metadata, in-turn session transitions, and incomplete or cross-turn call/output graphs. Every physical turn intersecting the line scope requires one governing session and turn, one complete ordered call/output graph, exactly one logical final, and exactly one bound logical completion. Multiplicity is allowed only for byte-identical complete outer-record replays. Final evidence follows governed call/output records, completion follows and exactly matches the final text, and no governed record follows completion. Unrelated turns wholly outside the declared scope remain pinned by the complete source SHA-256 but are not semantically claimed.

The session selector is evaluated over the full parsed source so it can bind metadata preceding the selected scope. All other selectors are scoped. Session and turn identities are nonempty strings; completion timing fields are exact integers; present worker strings and policy objects follow their declared types. Selected calls, outputs, answer, and completion must belong to one coherent logical turn; exact literal record-content replays deduplicate with provenance.

Run:

```text
python "<skill-root>/scripts/export_structural_rollout.py" --spec "<spec.json>" --out "<extract.json>"
python "<skill-root>/scripts/export_structural_rollout.py" --spec "<spec.json>" --verify "<extract.json>"
```

The output parent must already exist as a real non-reparse directory and the output path must be absent. Export publishes once with no-clobber creation; a second export requires a new filename and never updates the first artifact. Verification is read-only.

The exporter pins and freshly rechecks every source after all runs are assembled and around publication or final verification, emits canonical finite JSON, refuses output aliases to the spec or a source rollout, and retains selected task evidence exactly. On success, the final checked destination bytes match the reported SHA-256.

The output parent and temporary namespace are a trusted, cooperative local filesystem boundary. No same-account process may deliberately replace helper staging entries or the destination during an invocation. Identity checks, no-clobber creation, and cleanup are practical collision and drift controls, not a linearizable multi-path transaction or atomic compare-and-unlink guarantee. Deliberately timed namespace replacement and post-return mutation are outside this evidence workflow's contract.

Keep the spec and extract, not the source rollout, in any review packet.
