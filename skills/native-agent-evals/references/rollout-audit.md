# Structural rollout audit

Use this reference for Windows or WSL rollout audits and skill-invocation classification. Record the active CLI/runtime version because record names and nesting may change.

## Select sessions

1. Record the current audit root session ID, descendants, and rollout paths.
2. For retrospective discovery or natural-usage inventories, exclude that whole audit family so its prompts and loaded skills cannot self-confirm usage. For a predeclared probe or controlled study, explicitly selected fresh trial descendants are experimental evidence. Keep coordinator/evaluator activity out of the measured behavior and retain the study's isolation and contamination controls.
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

## Parse structurally

Parse one JSON object per line. Inspect `session_meta`, `turn_context`, `event_msg`, and `response_item` by their typed fields. Use `rg` only to locate candidates; prompt text, skill bodies, commands, and audit instructions can mention a tool without proving invocation.

PowerShell inventory:

```powershell
$rollout = 'C:\path\to\rollout.jsonl'
$sourceLine = 0
Get-Content -LiteralPath $rollout | ForEach-Object {
  $sourceLine += 1
  try {
    $outer = $_ | ConvertFrom-Json -Depth 100 -ErrorAction Stop
  } catch {
    [pscustomobject]@{
      source_path = $rollout
      source_line = $sourceLine
      parse_error = $_.Exception.Message
    }
    return
  }
  $item = $outer.payload
  [pscustomobject]@{
    source_path = $rollout
    source_line = $sourceLine
    parse_error = $null
    timestamp = $outer.timestamp
    record_type = $outer.type
    payload_type = $item.type
    item_id = $item.id
    call_id = $item.call_id
    name = $item.name
    namespace = $item.namespace
    role = $item.role
  }
}
```

WSL inventory:

```bash
python3 - "$ROLLOUT" <<'PY'
import json, sys
with open(sys.argv[1], encoding="utf-8") as stream:
    for line_no, line in enumerate(stream, 1):
        try:
            row = json.loads(line)
        except json.JSONDecodeError as error:
            print(json.dumps({"source_path": sys.argv[1],
                              "source_line": line_no,
                              "parse_error": str(error)}))
            continue
        item = row.get("payload") or {}
        print(json.dumps({"source_path": sys.argv[1], "source_line": line_no,
                          "parse_error": None, "record_type": row.get("type"),
                          "payload_type": item.get("type"), "item_id": item.get("id"),
                          "call_id": item.get("call_id"), "name": item.get("name"),
                          "namespace": item.get("namespace"), "role": item.get("role")}))
PY
```

These examples inventory source rows, including parse failures. They do not validate malformed evidence or relax the strict export and promotion checks.

## Deduplicate history

Treat resume and compaction as history transport:

1. Group files by `session_meta.payload.id`.
2. Register every nonempty stable `item.id` across the complete scoped call
   graph. One ID must retain one outer/payload kind, call ID, and content
   identity; only exact replays may share it.
3. Without stable IDs, normalized hashes may group candidate replays. They are lookup aids only and cannot establish replay equivalence or justify deduplication.
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

Apply treatment/control requirements to comparative claims. A retrospective inventory or single runtime probe does not require invented comparison conditions; state the narrower claim and mark inapplicable comparison fields accordingly.

Record model, effort, role, fork mode, tool surface, prompt, permissions, cwd, and artifact state for every run. For revision comparisons, preserve exact prompt/policy hashes, a direct policy diff, neutral run IDs, assignment/order, isolated artifact manifests, complete answers, and blind classifications.

Do not attribute an effect to skill text when a worker or environment condition changed.

## Export bounded evidence

Read [structural evidence export](structural-export.md) before preparing a schema-v3 spec, running the exporter, verifying an extract, or sending rollout-derived evidence. It owns selector, source-identity, replay, classification, worker-invariance, and publication requirements. Preserve this distinction: source hashes bind the source bytes; normalized matching does not prove exact replay.

Never transmit a source rollout. Include the verified bounded spec and extract in review packets.

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
