# Codex Skill Index for Antigravity

This file is a compact map of useful Codex skills and working rules. It is not
a copy of Codex internals. Use it to decide what workflow to follow before
acting in this workspace.

First read and follow:
`D:\AI\Antigravity\.agents\rules\codex_operating_protocol.md`.

## Core Process Skills

- `using-superpowers`: Before any nontrivial task, check whether a specialized
  skill/workflow applies. Do not start by guessing.
- `systematic-debugging`: For bugs, account failures, broken tools, build
  failures, CI failures, and unexpected behavior. Reproduce first, read exact
  errors, identify root cause, then fix one thing at a time.
- `verification-before-completion`: Before claiming something is fixed or
  working, run a fresh verification command and report evidence.
- `brainstorming`: Before designing new features, workflows, integrations, or
  broad behavioral changes. Understand the goal first, compare approaches, then
  implement only after the design is clear.
- `writing-plans`: Use after a design is approved and before implementation of
  multi-step work.
- `test-driven-development`: Use when changing code behavior. Prefer a failing
  reproduction before implementation.
- `using-git-worktrees`: Use when risky or parallel feature work should be
  isolated from the current working tree.

## Domain Skills Available in Codex

- `github:*`: GitHub repository, PR, CI, review, and publishing workflows.
- `openai-docs`: Current Codex/OpenAI product docs, model choice, settings,
  scheduled tasks, skills, and API/product questions.
- `documents`, `pdf`, `presentations`, `spreadsheets`: Office/PDF artifact work
  with render/verification workflows.
- `sites:*`: Website/app build and hosting workflows when a site project is
  present.
- `browser:control-in-app-browser`: Browser automation and UI verification.
- `imagegen`, `visualize`: Visual/image generation or interactive visual tools.
- `skill-creator`, `plugin-creator`, `skill-installer`: Extend Codex itself.

## Practical Rule

Antigravity does not need to imitate every Codex skill literally. It should
apply the same discipline:

1. Read project rules first.
2. Find the smallest reliable workflow for the task.
3. Use existing repo patterns.
4. Do not edit unrelated files.
5. Verify with fresh evidence before reporting success.
6. Write durable conclusions to `hermes-brain` only when the user asks or when
   the result is a stable rule that future agents need.
