---
name: consult-chatgpt-pro
description: Consult ChatGPT Pro or another ChatGPT extended-reasoning mode with a faithful task-relevant context packet, reconcile its advice against local evidence, and run focused follow-ups to closure. Use when the user explicitly asks for ChatGPT Pro, GPT Pro, or extended reasoning, or when a second opinion would materially improve a high-risk plan or architecture choice, difficult or repeated troubleshooting, post-implementation or code/work review, visual review, or synthesis of conflicting analyses. Skip implicit consultation for trivial tasks and questions already decided by authoritative local evidence.
---

# Consult ChatGPT Pro

## Operating contract

Use ChatGPT Pro as a reasoning consultant. Codex remains responsible for gathering local evidence, making decisions, implementing authorized changes, validating them, and reporting the final judgment.

Assume Pro can see only what is sent in the current conversation. Never imply that it inspected the local machine, repository, terminal, browser, tests, or omitted files.

Keep the consultation inside the user's task and success criteria. Treat suggestions outside that boundary as out of scope unless the user expands it.

## Context boundary

Include only task-relevant evidence the user has authorized and preserve it faithfully.

Never attach a source rollout or conversation export. Obtain rollout-derived evidence only through the typed structural exporter in `native-agent-evals`.

If required context is unavailable, narrow the requested verdict explicitly or mark the consultation `BLOCKED`.

## Required references

Read [references/context-packets.md](references/context-packets.md) before building or inspecting a context packet.

Read [references/chatgpt-browser.md](references/chatgpt-browser.md) before opening ChatGPT, selecting a reasoning mode, transmitting context, waiting, or collecting a response.

Read [references/closure-loop.md](references/closure-loop.md) before classifying findings, acting on advice, preparing re-review, or deciding closure.

## Frame the review

Define the mode, one-sentence question, task boundary, success criteria, evidence available, local validation, and requested verdict.

## Keep a compact ledger

Record the exact ZIP SHA-256, conversation URL, observed reasoning mode, included files and material omissions, material findings and dispositions, local validation, changed decisions/files, and current state.

Update it after each send, substantive response, local action, and re-review. Keep it concise enough to survive browser waits without becoming a second packet.

## Run the loop

Use these states as needed:

`FRAMED → EVIDENCE_READY → PACKET_READY → SENT → WAITING → RECONCILING → ACTIONED → RE_REVIEW → CLOSED`

Use `BLOCKED` when required context, authorization, Browser access, a substantive response, or a closure verdict is unavailable. Use `ABANDONED` only when the user ends the consultation.

Build the smallest complete current packet, send its atomic ZIP in a fresh conversation, wait for a substantive result, verify and disposition findings locally, and re-review while material findings remain.

Classify each new post-change finding with the closure reference. When the same missing rule or boundary recurs, or the risk spans separately implemented surfaces, complete its owned equivalence-class matrix, freeze the validated candidate bytes, regenerate derived evidence, and request one brand-new full-scope Pro review. Do not drip-feed equivalent fixes.

## Closure and handoff

Apply the three-condition closure gate in the closure reference; any missing or ambiguous verdict remains `BLOCKED`.

Report the final ledger and closure state.
