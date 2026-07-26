# Structural Rollout Audit

Use this reference for Windows or WSL rollout audits and skill-invocation classification.

Exact rollout record names and nesting are version-sensitive; record the active CLI/runtime version and verify the observed schema before classifying evidence.

## Contents

- [Select Sessions](#select-sessions)
- [Parse Structurally](#parse-structurally)
- [Deduplicate History](#deduplicate-history)
- [Classify Skill Invocation](#classify-skill-invocation)
- [Classify Direct V2 Calls](#classify-direct-v2-calls)
- [Control Confounds](#control-confounds)
- [Report Evidence](#report-evidence)

## Select Sessions

1. Record the current audit root session ID, descendant task paths, and rollout paths.
2. Exclude the entire current task family so its prompt, descendants, and loaded skill text cannot self-confirm the result.
3. Select candidate sessions by timestamp, task ID, cwd, or explicit rollout path.
4. Include archived and resumed locations only when they belong to the requested scope.
5. Record CLI version, host, and session metadata separately from behavioral evidence.

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

## Parse Structurally

Parse one JSON object per line. Inspect `session_meta`, `turn_context`, `event_msg`, and `response_item` records by their parsed fields. For `response_item`, classify the nested payload type before reading names, namespaces, arguments, or outputs.

Use PowerShell for a bounded structural inventory:

```powershell
$rollout = 'C:\path\to\rollout.jsonl'
$records = Get-Content -LiteralPath $rollout | ForEach-Object {
  try { $_ | ConvertFrom-Json -Depth 100 } catch {
    [pscustomobject]@{ parse_error = $_.Exception.Message; raw = $_ }
  }
}

$records | ForEach-Object {
  $outer = $_
  $payload = $outer.payload
  $item = if ($payload.PSObject.Properties.Name -contains 'item') {
    $payload.item
  } else {
    $payload
  }
  [pscustomobject]@{
    timestamp = $outer.timestamp
    record_type = $outer.type
    payload_type = $payload.type
    item_type = $item.type
    item_id = $item.id
    call_id = $item.call_id
    name = $item.name
    namespace = $item.namespace
    role = $item.role
  }
} | Format-Table -AutoSize
```

Use a streaming parser in WSL:

```bash
python3 - "$ROLLOUT" <<'PY'
import json, sys
path = sys.argv[1]
with open(path, encoding="utf-8") as fh:
    for line_no, line in enumerate(fh, 1):
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            print(line_no, "parse_error", exc)
            continue
        payload = row.get("payload") or {}
        item = payload.get("item") if isinstance(payload, dict) else {}
        if not isinstance(item, dict):
            item = payload if isinstance(payload, dict) else {}
        print(line_no, row.get("type"), payload.get("type"),
              item.get("type"), item.get("id"), item.get("call_id"),
              item.get("name"), item.get("namespace"), item.get("role"))
PY
```

Use `rg` only to locate candidate files or line numbers. Confirm every claim from parsed record fields. Prompt text, skill bodies, shell commands, and audit instructions can contain tool names without proving invocation.

## Deduplicate History

Treat resume and compaction as history transport, not new behavior.

1. Group files by `session_meta.payload.id`.
2. Deduplicate response items by stable `item.id` or `call_id`.
3. When stable IDs are absent, hash a canonical tuple of record type, timestamp, role, parsed payload type, and normalized content.
4. Count a copied summary or replayed context once, not once per resumed file.
5. Keep the earliest source location and record every duplicate location as provenance.
6. Keep genuinely new post-resume calls even when their prompt restates earlier work.
7. Treat a coordinator and its descendants as one workflow family for usage counts; child rollouts are supporting evidence, not independent invocations.

## Classify Skill Invocation

Keep these levels separate:

- **Loaded:** Skill metadata or body was injected into the model context by the runtime.
- **Read:** A structural tool call or runtime record shows the skill file or skill resource was opened.
- **Announced:** An assistant message explicitly says the skill is being used.
- **Applied:** The observable workflow follows distinctive instructions from the skill and produces task-relevant evidence.

Do not infer one level from another. A skill can be loaded but unread, read but unannounced, announced but not applied, or applied without an announcement in older evidence. Require a structural record for loaded/read and behavioral evidence for applied.

## Classify Direct V2 Calls

Count a collaboration call only from a parsed function-call record. Record the exact `name`, `namespace`, arguments, call ID, output, and status transition.

Historical negative classification may record that a parsed call did **not** use the legacy `multi_agent_v1` namespace or `close_agent`. Never turn those terms into operational guidance.

## Control Confounds

Record the worker model, reasoning effort, role, tool surface, prompt, permissions, and artifact state for every compared run. Never attribute an improvement to skill text when the Sol model or effort differs. Mark the result confounded and rerun under the same Sol worker condition.

## Report Evidence

Return:

- included and excluded session IDs and paths;
- current-audit exclusion;
- deduplication keys and duplicate counts;
- loaded/read/announced/applied classifications with separate evidence;
- exact direct-tool call records and lifecycle outputs;
- worker-condition equality or confounds;
- parse errors, missing fields, and an inconclusive label where evidence is insufficient.
