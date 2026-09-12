---
name: consult-chatgpt-pro
description: Consult ChatGPT Pro when requested or when an unresolved, consequential question needs an external reasoning review. Reconcile its advice with local evidence.
---

# Consult ChatGPT Pro

Use Pro as a consultant. Codex owns the decision, implementation, local validation, and completion of the user's task. Pro can assess only the material supplied in its current conversation; do not imply it inspected omitted files or ran local checks.

## Prepare and consult

Define the question, scope, success criteria, available evidence, and requested verdict. Keep optional suggestions outside the task unless the user expands it.

- Read [context packets](references/context-packets.md) when selecting evidence or building and verifying the ZIP. Include only authorized task evidence. For rollout-derived evidence, use the typed exporter in `native-agent-evals`; never attach a source rollout or conversation export.
- Read [ChatGPT browser execution](references/chatgpt-browser.md) before selecting a browser or mode, transmitting evidence, waiting, or collecting a response. Verify Pro when the user requires it, and use a fresh conversation for each substantive review.
- Read [reconciliation and closure](references/closure-loop.md) when acting on advice, preparing re-review, or deciding closure. It owns finding dispositions and recurring-failure review. Isolated findings permit focused re-review; an activated recurring-failure gate requires full-scope re-review.

Send the smallest complete verified packet. Wait for a substantive response without forcing an early answer. If required evidence cannot be supplied, narrow the verdict explicitly or report the consultation as `BLOCKED`.

## Reconcile and finish

Verify material recommendations locally. Implement changes already authorized by the task, validate the affected result, and return current evidence for re-review while material findings remain. An internal review checkpoint does not require renewed user permission.

Keep a compact ledger of the ZIP SHA-256, conversation URL, observed mode, included evidence and omissions, findings and dispositions, local validation, and current state. Update it on material changes rather than every wait.

Use `CLOSED` only when the latest substantive Pro verdict covers the declared scope, explicitly leaves no unresolved material finding, and every material finding has an evidence-backed resolved disposition. Missing evidence or an ambiguous verdict remains `BLOCKED`; use `ABANDONED` only when the user ends the consultation. A time limit or passing tests cannot substitute for the verdict.

Report the outcome and ledger, then complete any remaining authorized task work. Review closure alone does not finish the user's objective.
