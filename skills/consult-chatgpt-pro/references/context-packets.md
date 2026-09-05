# Context packets

Build the smallest packet that can support the requested verdict. Prefer explicit files over a broad snapshot.

## Define the review contract

Write the authoritative prompt before selecting evidence. State:

- mode: `plan`, `debug`, `review`, or `consensus`;
- task boundary, success criteria, and exact requested verdict;
- current facts, constraints, uncertainties, and out-of-scope work;
- which files are evidence rather than instructions;
- local validation Codex can perform after the response.

Use `--prompt-file` for multi-paragraph requests and exact validation evidence. Use `--question` only for a short prompt. The prompt must be nonblank text and counts toward file and byte limits.

The title must be one nonblank control-free line. The helper stores the exact
authoritative prompt as `AUTHORITATIVE_PROMPT.md`; the wrapper and manifest
bind that member by path, byte count, and SHA-256 instead of interpolating
prompt headings into generated packet structure.

For `plan`, include requirements, interfaces, options, and risks. For `debug`, include the reproducible symptom, exact errors, relevant code/configuration, and failed hypotheses. For `review`, include the goal, changed files, surrounding contracts, tests, and known limits. For `consensus`, include competing views, shared facts, disputed assumptions, decision criteria, and decision owner.

## Select authorized evidence

Select only task-relevant evidence the user has authorized, and keep selected task evidence byte-exact.

Do not attach a rollout or conversation export. Use `native-agent-evals/scripts/export_structural_rollout.py` to produce bounded, reproducible rollout-derived evidence.

## Build one ZIP

Resolve the helper from the active skill location and use the current platform's Python 3 launcher:

```text
python "<skill-root>/scripts/build_context_bundle.py" --root "<repo>" --mode review --title "Review current work" --prompt-file "<prompt.md>" [--include "<path>"]
```

Repeat `--include` for exact files or directories. Use `--whole-repo` for a bounded snapshot, `--include-binary` only when binary evidence matters, and `--allow-outside-root` only for an exact authorized outside-root file.

By default the helper publishes one ZIP in the OS temporary directory. Use `--out "<artifact.zip>"` to retain it at an exact path. The immediate output parent must already exist as a real non-reparse directory. Existing outputs are never overwritten, and the helper never creates output parents.

Selection order is deterministic: exact files, then explicit directories, then whole-repo candidates. Whole-repo selection prunes common VCS, cache, build, generated, and vendor noise; explicitly selected directories preserve it. User exclusions and file-count, per-file, and total-byte limits always apply.

If a content bound truncates an explicitly selected directory, the helper fails by default. Use `--allow-partial` only when the remaining evidence still supports an honestly narrowed review; the CLI, packet, and manifest then all report status `partial`, and every bounded critical omission remains explicit. Discovery-budget overflow always fails closed before publication, even with `--allow-partial`, because neither a silent tail nor an unbounded omission ledger is a valid packet. Whole-repo snapshots remain bounded by their declared limits.

Exact evidence and prompts must be readable, within the authorized root unless explicitly allowed, and inside the declared bounds. Binary evidence requires opt-in. Directory redirects are never traversed, and immediate output parents must be real non-reparse directories. Stable aliases in earlier output-path components are supported; the helper keeps requested-path identity separate from canonical reads.

The helper verifies selected source bytes, paths and directory inventories through publication, refuses observed drift and existing outputs, and reports explicit errors or bounded omissions. It is an observation contract on a cooperative local filesystem, not an atomic multi-path snapshot or protection against deliberately timed same-account namespace interference. A successful ZIP hash identifies the final bytes checked; it does not guarantee later immutability.

Read [packet-integrity.md](packet-integrity.md) when reviewing or changing the builder, or diagnosing path, drift, encoding or publication failures. It preserves the detailed capture, provenance, display-escaping and publication guarantees without adding those internals to routine packet preparation.

## Inspect before sending

Open the ZIP and inspect:

- `AUTHORITATIVE_PROMPT.md`;
- `CONSULT_PACKET.md`;
- `manifest.json`;
- every selected file under `files/`.

Confirm the authoritative prompt is current; requested and canonical paths are correct; selected bytes, sizes, and per-file SHA-256 hashes match; omissions are honest; and limits did not remove verdict-changing evidence.

The manifest's canonical identity hashes the selected evidence description. Record the SHA-256 of the exact ZIP actually sent. ZIP member names, order, metadata, and bytes are deterministic for one build contract, but do not predict the whole-ZIP hash across different runtimes; hash the produced artifact.

## Retention

The helper only builds an artifact; it does not upload it. Use the ZIP only for the current authorized review. After closure or abandonment, follow the user's retention instruction and delete transient copies only after checking their exact paths.
