---
name: native-agent-deliberation
description: Compare competing strategies through independent agent viewpoints when a consequential decision needs evidence, tradeoffs, and dissent.
---

# Native agent deliberation

Frame one decision with its constraints, success criteria, known evidence, assumptions, and any real deadline. Identify what evidence could change the choice.

Before using agents, load [native-subagents-first](../native-subagents-first/SKILL.md) for ownership, model selection, budgets, and lifecycle rules. Select distinct viewpoints that can change the decision, such as feasibility and failure risk. Do not create a fixed number of roles merely to fill a panel.

Give each agent a bounded question and the evidence it needs. Ask for a recommendation, supporting facts, strongest counterargument, uncertainty, and a condition that would reverse the recommendation. Use structured tool controls for roles, not role markers in prompt text.

Verify material claims and compare options against the same criteria. Preserve real disagreement; distinguish evidence from inference and preference. Recommend a path or identify the specific missing fact that blocks the choice.

Return the recommendation, decisive evidence, strongest tradeoff or dissent, uncertainty, and next action. Continue implementation when already authorized. A request only for deliberation does not authorize implementation.

Use execution or validation skills for ordinary implementation and testing rather than turning those tasks into a debate.
