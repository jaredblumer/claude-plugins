---
name: standup-brief
description: Write a standup brief of your own pull requests — what each open PR does, how it was implemented, where it stands (draft, review, CI), and what merged since your last standup — in short spoken sentences you can read out in the meeting. Use when the user says "standup brief", "prep my standup", "what do I say at standup", or asks to describe their open PRs for a meeting.
argument-hint: "[--label <label>] [--repo <owner/name>] [--unassigned | --any-assignee]"
---

# Standup brief

Turn the user's open PRs into something they can say out loud in about a minute per PR.

## 1. Gather

Run the gather script with the user's arguments passed through unchanged (`$ARGUMENTS`):

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/gather.py" $ARGUMENTS
```

Default filters come from `~/.claude/standup-brief.json` (keys `label`, `repo`, `unassigned`); arguments override them, and `--any-assignee` turns off a configured `unassigned`. It prints JSON: `open` (each PR's description, changed files, review and CI state), `merged_since` (PRs merged since the last workday) and `since`. If `gh` isn't logged in, stop and say so.

When a PR's description doesn't explain how the change works, read its diff (`gh pr diff <number> -R <repo>`) for just that PR. Don't read diffs the description already explains.

## 2. Write the brief

Lead with a one-line count, e.g. "4 open PRs waiting on review, 1 merged since Friday."

Then for each open PR, newest activity first:

- **Heading:** the ticket key and a 3–6 word plain name, linked to the PR.
- **What:** one sentence on the problem the user saw before, in product terms.
- **How:** one or two sentences on the implementation — the mechanism, not a file list. Name a file or class only when it's what a teammate would ask about.
- **Status:** draft / ready, who reviewed or is requested, CI passing or failing (name failing checks), conflicts. Say "needs a reviewer" when it has neither an assignee nor a review request.
- **Ask** (only if there is one): what the user needs from the team, such as a reviewer or a decision.

Then "Merged since <day>": one line per merged PR.

## Rules

- Write sentences the user can say verbatim: no markdown tables, no code blocks, no jargon a PM in the room wouldn't follow without a gloss.
- Keep each PR to about 60 words.
- Report only what the JSON or diff shows. Never guess at CI, review state or behavior.
- Don't post, comment or assign anything. This skill only reads.
