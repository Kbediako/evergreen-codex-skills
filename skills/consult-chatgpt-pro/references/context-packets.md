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

Exact file symlinks may resolve to regular files and record both requested and canonical provenance. For exact evidence and `--prompt-file`, the requested endpoint identity, link target when applicable, and canonical target are bound at selection and revalidated before and after reading. Both paths must remain inside the root unless the exact file is authorized with `--allow-outside-root`. Parent-directory components are rejected before normalization, and directory redirects are never traversed.

Explicit directories and whole-repo selections bind the lexical root, every discovered selected regular-file endpoint, and every traversed directory's endpoint identity and exact entry inventory. Files eligible for capture also receive a content fingerprint bounded by the packet byte limit; an unfingerprinted broad candidate is explicitly omitted and can never enter the ZIP. Captured bytes are compared with that fingerprint, re-read after capture and ZIP staging, and checked again after the publication temporary file is durable but before commit. Prompt files are re-read first at the same boundary so overlapping prompt drift keeps the prompt-specific diagnostic. Every final source read is followed by endpoint revalidation. The sequential success boundary verifies the destination, validates the final source snapshot, performs identity-checked staging cleanup, re-verifies the final destination bytes, and derives the reported SHA-256 from those bytes. Observed file changes, additions, removals, renames, type changes, nested mutations, root retargeting, directory replacement, and artifact mutation fail the invocation. `--allow-partial` permits bounded truncation only; it never permits observed source drift.

This is an observation contract, not a filesystem-level atomic snapshot. Path and directory state bind during traversal; capturable content binds at its first bounded stable fingerprint read, and every later capture or publication check must match it. The helper makes no claim about unobserved bytes before that first read.

The output parent and temporary namespace are a trusted, cooperative local filesystem boundary. No same-account process may deliberately rename, replace, link, or delete helper staging entries or the destination while an invocation is running. The helper detects ordinary drift and collisions, publishes only to an absent destination, and attempts cleanup only after an immediate identity check. These checks are not a linearizable multi-path transaction or an atomic compare-and-unlink primitive. Deliberately timed namespace replacement can race adjacent path operations; foreign-entry preservation, complete cleanup, a simultaneous source/artifact snapshot, and immutability after the final check are not guaranteed under that unsupported interference.

The helper fails if exact evidence is missing, unreadable, changes during capture, exceeds an exact-file limit, requires binary opt-in, or has a path that cannot be represented as UTF-8; path-encoding failures use an ASCII-safe domain diagnostic. Authoritative prompt drift reports `prompt-changed`; evidence drift reports `evidence-changed`; discovery overflow reports `discovery-limit` and publishes nothing. Within the discovery budget, broad-selection omissions use total, exact-path-tiebroken ordering and remain explicit. Untrusted displayed values use ASCII-injective escapes: literal backslashes and every non-ASCII or control code point remain distinguishable inside safe Markdown code spans. Generated member components percent-encode Windows reserved device stems such as `CON`, `NUL`, `COM1`, `LPT1`, `COM¹`, and `LPT¹`; raw canonical validation rejects their unencoded aliases on every platform. Requested evidence never silently becomes a prompt-only packet.

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
