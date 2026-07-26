# Read-only boundaries

## Hard boundary

A user, policy, or procedure that forbids mutation creates a hard boundary.

- Use a role or sandbox that prevents every in-scope filesystem and external side effect.
- Verify the child's effective permissions after parent live overrides; a configured sandbox default is not proof.
- A filesystem-read-only scout is sufficient only when external tools and credentials cannot mutate consequential state.
- Otherwise use a disposable isolated snapshot with consequential credentials and external mutation routes removed.
- If neither is available, do not delegate the hard read-only scope to a write-capable child.

Post-work checks prove final state, not that no transient write occurred. They never replace enforcement.

## Advisory boundary

Use a write-capable child only when the parent is authorized to accept best-effort read-only execution plus detection.

Before launch, bind the scope to its target revision or baseline identity and record a bounded recursive manifest:

- lexical relative path and existence; inventory a link-valued scope root itself;
- lstat-style entry type plus precise link/reparse kind;
- SHA-256 for regular-file contents;
- stored link/reparse-target identity without dereferencing it.

Include tracked, staged, untracked, and ignored entries. Never recurse through a link/reparse point. Exclude `.git` and exact out-of-scope cache/build trees only when the brief forbids access to them.

For Git, also hash the bounded output of `git ls-files --stage -z -- <scope>`. Use `git status --porcelain=v2 -z --untracked-files=all --ignored=matching -- <scope>` plus staged/unstaged diffs for diagnosis only when they cannot cross a link/reparse boundary; otherwise skip them and record the reason explicitly. They do not replace content identity.

Compare the same surface after the run. An unexplained created, deleted, replaced, retyped, re-linked, rehashed, or index-only change fails the invariant. Do not use the child's result until the mismatch is explained and user-owned state is recovered safely.

If the bounded surface is too large to inventory, narrow the scope or use isolation. Do not substitute a Git-only check.
