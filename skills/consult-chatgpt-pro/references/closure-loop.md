# Reconciliation and closure loop

Convert Pro's advice into evidence-backed dispositions, not automatic edits. Keep the loop focused on the user's task and the exact material findings still capable of changing its outcome.

## Identify material findings

Treat a finding as material when it could change:

- Correctness, safety, security, data integrity, or user-visible behavior.
- The chosen architecture, implementation plan, or root-cause diagnosis.
- Required tests, acceptance evidence, rollback, or operational readiness.
- Context fidelity, authorization compliance, or the validity of the consultation.
- A stated task requirement or success criterion.

Treat taste, optional polish, already-satisfied suggestions, and explicitly out-of-scope work as nonmaterial only when they cannot change those outcomes. Record the rationale instead of dropping them silently.

## Assign one disposition per finding

Give each finding a stable identifier and one current disposition:

- `accepted-actioned`: Implement or adopt it, then attach local validation evidence.
- `accepted-no-change`: Accept the conclusion when it requires a decision or explanation rather than a file change; record the deciding evidence.
- `rejected-evidence`: Reject it only with current local facts, commands, tests, contracts, or user policy that address the claim.
- `superseded`: Replace it with a later design or fact; show why the replacement resolves the same risk.
- `out-of-scope`: Use only when the current user/developer task boundary excludes it or the user explicitly authorizes its exclusion; record that authority and residual risk.
- `blocked`: Name the missing context, authorization, execution evidence, user decision, or consultant outcome.

Do not use `noted`, `deferred`, `duplicate`, or `repeated` as closure dispositions for an in-scope material finding. Map a duplicate or repeat to the earlier evidence-backed disposition.

Keep `blocked` findings unresolved. Do not turn them into out-of-scope items merely to end the loop.

## Validate locally

Test each factual recommendation against the strongest available local evidence. Match validation to the claim:

- Run focused and broader tests for code behavior and regression risk.
- Inspect current files, diffs, schemas, configuration, and dependency contracts for implementation claims.
- Reproduce errors and falsify competing hypotheses for debugging claims.
- Observe the live UI for visual or interaction claims.
- Compare plans against requirements, constraints, ownership, rollback, and acceptance gates.
- For evaluation or analytical claims, test construct validity, treatment/baseline comparability, omitted controls, and whether the evidence can distinguish the claimed effect.
- Ask the user when policy, priority, or scope cannot be decided technically.

Record exact commands or checks, outcomes, affected files, and unresolved uncertainty. Never state that Pro executed local validation.

## Apply advice within authority

Make only changes already authorized by the task. If a recommendation materially expands scope, changes external state, or needs a user decision, pause that item and request direction.

After changes, run proportionate validation and update every affected finding. Inspect the resulting diff or decision record before asking for re-review.

## Prepare the re-review handoff

Use the same conversation when the round depends on its prior findings. Send a compact handoff containing:

- Original task, current boundary, success criteria, and requested verdict.
- Prior bundle identity and the new bundle identity when context changed.
- Each material finding, its disposition, and the evidence supporting it.
- Exact changed files or decisions and a concise diff summary.
- Validation commands or checks with exact results.
- Remaining disagreement, missing evidence, and residual risk.
- Any deliberately omitted or newly added context.

Ask Pro to identify only unresolved in-scope material findings and to end with an explicit closure verdict. Do not drip-feed unrelated material or ask it to repeat findings that are already resolved.

Start a fresh conversation with this same handoff when the prior context is stale, conflicted, inaccessible, or unsuitable for an independent review. Record both URLs.

## Evaluate the latest review

Treat a response as substantive only when it evaluates the supplied work rather than merely acknowledging it or reporting progress.

If it identifies a new in-scope material finding, add it to the ledger and return to local reconciliation.

If it repeats a prior finding, attach the earlier disposition and evidence in the next handoff. Close that item only after the latest review has the evidence needed to recognize it as resolved; repetition alone proves nothing.

If it suggests out-of-scope work, restate the boundary and ask whether any unresolved material issue remains inside it. Preserve the suggestion and residual risk in the ledger.

If the verdict is absent or ambiguous after a complete response, ask for the verdict without reopening the whole review. Until it arrives, use `BLOCKED`.

If Pro is unavailable, interrupted, or the conversation cannot be observed, preserve the latest evidence and use `BLOCKED`. Do not manufacture a terminal verdict.

## Apply the closure gate

Set `CLOSED` only when all three conditions hold:

1. The latest substantive Pro review explicitly reports no unresolved in-scope material finding.
2. Every in-scope material finding has a resolved disposition: `accepted-actioned`, `accepted-no-change`, `rejected-evidence`, `superseded`, or properly authorized `out-of-scope`.
3. No finding remains `blocked` or otherwise unresolved; any blocked finding forces `BLOCKED` even when Pro reports no new findings.

An evidence-backed repeat, superseded point, or explicit out-of-scope suggestion may coexist with closure only when the latest substantive review does not leave it unresolved.

**Forward-test fixture — blocked carryover:** Round 1 finding `F-1` requires validating a migration against a production schema snapshot, but access is not currently authorized, so it remains `blocked`; a later substantive Pro review says, “No further material issues found.”

Expected: remain `BLOCKED`. Resolve the prerequisite, move `F-1` to an allowed resolved disposition with evidence, and send a focused re-review; enter `CLOSED` only if that latest review and the ledger then satisfy all three conditions.

Do not close because tests pass, changes were made, a time or round budget elapsed, Pro was quiet, or the user-facing result looks good. Those facts may support dispositions but cannot replace the latest substantive verdict.

At closure, report the final verdict, dispositions, local validation, changed files or decisions, remaining nonmaterial or out-of-scope notes, bundle identity, conversation URL, and observed reasoning mode.
