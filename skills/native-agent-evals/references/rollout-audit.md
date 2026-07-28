# Structural rollout audit

Use this reference for Windows, macOS, or WSL rollout audits and skill-invocation classification. Record the active CLI/runtime version because record names and nesting may change.

## Select sessions

1. Record the current audit root session ID, descendants, and rollout paths.
2. Exclude that whole task family so its prompts and loaded skills cannot self-confirm the result.
3. Select candidates by timestamp, task ID, cwd, or explicit path.
4. Include archived or resumed locations only when they belong to the requested scope.
5. Keep host and runtime metadata separate from behavioral evidence.

Find candidates on Windows:

```powershell
$roots = @(
  "$env:USERPROFILE\.codex\sessions",
  "$env:USERPROFILE\.codex\archived_sessions"
)
Get-ChildItem -LiteralPath $roots -Recurse -Filter 'rollout-*.jsonl' -ErrorAction SilentlyContinue |
  Sort-Object LastWriteTime -Descending |
  Select-Object FullName, LastWriteTime, Length
```

Find candidates in WSL:

```bash
find ~/.codex/sessions ~/.codex/archived_sessions \
  -type f -name 'rollout-*.jsonl' -printf '%T@ %p\n' 2>/dev/null |
  sort -nr
```

Find candidates on macOS:

```bash
find ~/.codex/sessions ~/.codex/archived_sessions \
  -type f -name 'rollout-*.jsonl' -exec stat -f '%m %N' {} + 2>/dev/null |
  sort -nr
```

## Parse structurally

Parse one JSON object per line. Inspect `session_meta`, `turn_context`, `event_msg`, and `response_item` by their typed fields. Use `rg` only to locate candidates; prompt text, skill bodies, commands, and audit instructions can mention a tool without proving invocation.

PowerShell inventory:

```powershell
$rollout = 'C:\path\to\rollout.jsonl'
Get-Content -LiteralPath $rollout | ForEach-Object {
  try { $_ | ConvertFrom-Json -Depth 100 } catch {
    [pscustomobject]@{ parse_error = $_.Exception.Message }
  }
} | ForEach-Object {
  $outer = $_
  $item = $outer.payload
  [pscustomobject]@{
    timestamp = $outer.timestamp
    record_type = $outer.type
    payload_type = $item.type
    item_id = $item.id
    call_id = $item.call_id
    name = $item.name
    namespace = $item.namespace
    role = $item.role
  }
} | Format-Table -AutoSize
```

Python inventory on macOS or WSL:

```bash
python3 - "$ROLLOUT" <<'PY'
import json, sys
with open(sys.argv[1], encoding="utf-8") as stream:
    for line_no, line in enumerate(stream, 1):
        row = json.loads(line)
        item = row.get("payload") or {}
        print(line_no, row.get("type"), item.get("type"), item.get("id"),
              item.get("call_id"), item.get("name"), item.get("namespace"),
              item.get("role"))
PY
```

## Deduplicate history

Treat resume and compaction as history transport:

1. Group files by `session_meta.payload.id`.
2. Register every nonempty stable `item.id` across the complete scoped call
   graph. One ID must retain one outer/payload kind, call ID, and content
   identity; only exact replays may share it.
3. Without stable IDs, hash a canonical tuple of record type, timestamp, role, parsed payload type, and normalized content.
4. Compare replayed turn segments and their governing session envelopes with
   hashes of the literal JSONL record-content bytes, including timestamps and
   excluding only the physical LF framing delimiter; only exact byte replays
   deduplicate.
5. Keep the earliest source and every duplicate locator as provenance.
6. Keep genuinely new post-resume calls.
7. Treat a coordinator and descendants as one workflow family for usage counts.

The exporter keeps two identities. Physical identity is the resolved source path plus selected turn-segment and governing-session locators and hashes. Logical identity is the bound session plus turn. Reusing either evidence identity across compared runs is rejected.

## Classify invocation and direct calls

Keep skill levels separate:

- **Loaded:** runtime structure injected the skill metadata or body.
- **Read:** a structural call opened the skill file or resource.
- **Announced:** an assistant message said the skill was being used.
- **Applied:** behavior followed distinctive instructions and produced relevant evidence.

Count a collaboration call only from a parsed call record. Record exact name,
namespace, arguments, payload kind, stable record ID, call ID, output payload
kind, output stable ID, output, and status transition. Fail closed on unsupported
call-like records. Require a nonempty string call name and type-check optional
namespace and status fields. Bind each output to an existing call ID and its
exact kind; reject orphaned outputs, cross-kind pairings, conflicting duplicate
call identities, or a supported call ID without an exact-kind output. Build
this graph before selector projection for every physical turn intersecting the
declared line scope, so unselected calls in that scope cannot satisfy or hide
another turn's records. Every output must occur after its matching call, and
emitted status transitions retain total physical source-line order. Validate
duplicate output identity and value for every supported scoped call.

## Classify waits

Record two independent fields:

- **Observation:** native mailbox, app-task event, process/session wait, source event/watch/stream, or pull endpoint.
- **Continuation:** active turn, scheduled continuation, or `needs-scheduled-handoff`.

Apply the current callable contract:

- `wait_agent` is a native-mailbox wait; timeout ends one wait window, not the task.
- `list_agents` is a lifecycle snapshot; justify repeated snapshots after waits.
- `wait_threads` is an app-task event wait and preserves its cursor when exposed.
- yielded command cells and exact PTY/session resumes are process/session waits.
- configured provider cursors, watches, or streams are source events only when currently callable and authorized.
- repeated endpoint requests are pulls.
- scheduling is a continuation choice, not an observation type.

For scheduled continuation, preserve task identity, reacquisition method, required host/tool/authorization, expiry, and compatibility evidence. Otherwise report `needs-scheduled-handoff`.

## Control confounds

Record model, effort, role, fork mode, tool surface, prompt, permissions, cwd, and artifact state for every run. For revision comparisons, preserve exact prompt/policy hashes, a direct policy diff, neutral run IDs, assignment/order, isolated artifact manifests, complete answers, and blind classifications.

Do not attribute an effect to skill text when a worker or environment condition changed.

## Export bounded evidence

Never send a source rollout. Use `scripts/export_structural_rollout.py` with a schema-v3 JSON spec. The spec declares:

- claim, rubric, classification source/checks, and pass aggregation;
- study-wide worker expectations, actual cross-run worker invariance, and
  promotion status;
- source path and exact SHA-256;
- neutral run ID and condition;
- nonempty unique `selected_call_ids`;
- inclusive line scope and selectors for session metadata, turn context, final answer, and completion.

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
python3 "<skill-root>/scripts/export_structural_rollout.py" --spec "<spec.json>" --out "<extract.json>"
python3 "<skill-root>/scripts/export_structural_rollout.py" --spec "<spec.json>" --verify "<extract.json>"
```

The output parent must already exist as a real non-reparse directory and the output path must be absent. Export publishes once with no-clobber creation; a second export requires a new filename and never updates the first artifact. Verification is read-only.

The exporter pins and freshly rechecks every source after all runs are assembled and around publication or final verification, emits canonical finite JSON, refuses output aliases to the spec or a source rollout, and retains selected task evidence exactly. On success, the final checked destination bytes match the reported SHA-256.

The output parent and temporary namespace are a trusted, cooperative local filesystem boundary. No same-account process may deliberately replace helper staging entries or the destination during an invocation. Identity checks, no-clobber creation, and cleanup are practical collision and drift controls, not a linearizable multi-path transaction or atomic compare-and-unlink guarantee. Deliberately timed namespace replacement and post-return mutation are outside this evidence workflow's contract.

Keep the spec and extract, not the source rollout, in any review packet.

Before sharing an extract, inspect it for credentials, secrets, private browser state, unnecessary personal data, and unrelated records. If safe redaction would break its exact-evidence contract, do not transmit it.

## Report evidence

Return:

- included and excluded session IDs and paths;
- current-audit exclusion;
- source and extract hashes;
- selectors, deduplication identities, and duplicate counts;
- loaded/read/announced/applied classifications;
- exact selected calls, outputs, complete answer, and completion;
- worker-condition matches or confounds;
- pass, fail, or inconclusive result and promotion status;
- parse errors, missing fields, and remaining uncertainty.
