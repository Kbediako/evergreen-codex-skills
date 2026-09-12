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

- Run checks appropriate to changed behavior and required project validation. Broaden or repeat them only when changes, failures, or unresolved regression risks justify it.
- Inspect current files, diffs, schemas, configuration, and dependency contracts for implementation claims.
- Reproduce errors and falsify competing hypotheses for debugging claims.
- Observe the live UI for visual or interaction claims.
- Compare plans against requirements, constraints, ownership, rollback, and acceptance gates.
- For evaluation or analytical claims, test construct validity, treatment/baseline comparability, omitted controls, and whether the evidence can distinguish the claimed effect.
- Ask the user when policy, priority, or scope cannot be decided technically.

Record exact commands or checks, outcomes, affected files, and unresolved uncertainty. Never state that Pro executed local validation.

## Apply advice within authority

Make changes already authorized by the task, including authorized external actions. If a recommendation needs new authority or an unresolved user decision, pause that item and request direction while continuing independent authorized work.

After changes, run proportionate validation and update every affected finding. Inspect the resulting diff or decision record before asking for re-review.

## Close invariant families before re-review

For each new post-change finding, identify the missing rule and affected representation or lifecycle boundary. An umbrella label alone does not prove recurrence. When the same rule or boundary recurs, or the risk spans separately implemented surfaces, read [recurring findings](recurring-findings.md) and complete its bounded coverage, local review, and frozen-evidence procedure before the next send. That branch requires a fresh full-scope Pro review even when the task scope is unchanged. Handle isolated findings with focused re-review.

## Prepare an independent re-review handoff

Open a fresh conversation for every substantive review. Keep sequence labels and prior assistant text out of the reviewer-visible prompt, filenames, title, and message. Send a compact current-state handoff containing:

- Original task, current boundary, success criteria, and requested verdict.
- Current bundle identity.
- Each known material risk, its disposition, and the evidence supporting it.
- Exact changed files or decisions and a concise diff summary.
- Validation commands or checks with exact results.
- Remaining disagreement, missing evidence, and residual risk.
- Any deliberately omitted or newly added context.

Ask Pro to identify only unresolved in-scope material findings and to end with an explicit closure verdict. Do not drip-feed unrelated material or ask it to repeat findings that are already resolved.

A focused re-review can close only the findings and affected scope explicitly supplied in that handoff. Do not promote a narrow verdict to package-wide closure unless the handoff re-establishes the full review contract, includes every changed or transitively affected surface, and asks for that package-wide verdict. Record the reviewed closure scope in the ledger.

Record every conversation URL and internal sequence only in the local ledger. Treat each response as an independent review of the supplied current state, not as confirmation of an earlier reviewer.

## Evaluate the latest review

Treat a response as substantive only when it evaluates the supplied work rather than merely acknowledging it or reporting progress.

If the review identifies a new or repeated in-scope material finding, add or map it in the ledger and apply the invariant-family trigger before the next handoff. Repetition alone proves nothing.

If it suggests out-of-scope work, restate the boundary and ask whether any unresolved material issue remains inside it. Preserve the suggestion and residual risk in the ledger.

If the verdict is absent or ambiguous after a complete response, ask for the verdict without reopening the whole review. Until it arrives, use `BLOCKED`.

If Pro is unavailable, interrupted, or the conversation cannot be observed, preserve the latest evidence and use `BLOCKED`. Do not manufacture a terminal verdict.

## Apply the closure gate

Set `CLOSED` only when all three conditions hold:

1. The latest substantive Pro review covers the declared closure scope and explicitly reports no unresolved in-scope material finding.
2. Every in-scope material finding has a resolved disposition: `accepted-actioned`, `accepted-no-change`, `rejected-evidence`, `superseded`, or properly authorized `out-of-scope`.
3. No finding remains `blocked` or otherwise unresolved; any blocked finding forces `BLOCKED` even when Pro reports no new findings.

An evidence-backed repeat, superseded point, or explicit out-of-scope suggestion may coexist with closure only when the latest substantive review does not leave it unresolved.

Do not close because tests pass, changes were made, a time or round budget elapsed, Pro was quiet, or the user-facing result looks good. Those facts may support dispositions but cannot replace the latest substantive verdict.

At closure, report the final verdict, dispositions, local validation, changed files or decisions, remaining nonmaterial or out-of-scope notes, bundle identity, conversation URL, and observed reasoning mode. Then continue any unfinished work already authorized by the user's end-to-end objective; review closure alone does not complete that objective.
