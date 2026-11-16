---
name: standup-brief
description: Write a standup brief of your own work — open PRs ready for review (what each does and how the code works, deep enough to answer "how does that work?"), what you're working on now (in-progress Jira tickets and PRs not yet labeled for review), and what merged since your last standup. Use when the user says "standup brief", "prep my standup", "what do I say at standup", or asks to describe their PRs or current work for a meeting.
argument-hint: "[--label <label>] [--repo <owner/name>] [--unassigned | --any-assignee] [--jira-jql <jql>]"
---

# Standup brief

Standup goes in this order: assign PRs for review, then say what each person is working on now. Give the user a short spoken summary of each item, and under it enough about how the code works that they can answer a teammate's follow-up questions without opening the PR.

## 1. Gather

Run the gather script with the user's arguments passed through unchanged (`$ARGUMENTS`):

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/gather.py" $ARGUMENTS
```

Default filters come from `~/.claude/standup-brief.json` (keys `label`, `repo`, `unassigned`, `jira_jql`); arguments override them, and `--any-assignee` turns off a configured `unassigned`. It prints JSON:

- `open`: PRs for review, matching `filters`
- `in_progress`: the user's open PRs with no label at all. No label means not ready for review, even when the ticket says Code Review.
- `merged_since`: PRs merged since `since` (the last workday)
- `jira_jql`: the query for the user's in-progress Jira tickets

Each PR carries its description, code files, test files, review and CI state, and `code_diff.path`, a saved diff of its code without tests, lockfiles or assets. If `gh` isn't logged in, stop and say so.

Then run `jira_jql` with whatever Jira tool this session has (for example the Atlassian connector's JQL search), asking for summary, status and description. If no Jira tool is available or it fails, carry on without Jira and say so in one line under "Working on now".

## 2. Read the code

For every PR in `open` and `in_progress`, read its `code_diff.path` in full; the description alone isn't enough. If `code_diff.cut_files` lists files, read those files' full diffs with `gh pr diff`. Work out:

- the root cause: what the old code did that produced the bug or gap
- the mechanism of the fix: which function, component or class changes, what it does now, and how data flows through it
- any decision a reviewer would question: a trade-off, an edge case it handles, or something it deliberately leaves out
- what the tests prove, from `test_files` and the description

For an in-progress PR, also note what looks unfinished: TODOs, a draft flag, missing tests, or a description that names open work.

When there are more than four PRs in all, hand each PR's reading to a subagent in parallel, giving it the diff path and the description, and asking for the points above.

## 3. Write the brief

Use markdown. Start with one line of counts, e.g. "4 PRs for review (2 need a reviewer), 3 things in progress, 3 merged since Friday."

### For review

One section per PR in `open`, newest activity first:

```markdown
#### [BSD-12345: 3–6 word plain name](PR url)

**Say this:** Two or three plain sentences for the meeting: the problem a user saw, and what the fix does, in product terms. No file names.

**How it works**
- **Root cause:** what the old code did wrong, naming the function or file in backticks.
- **The fix:** 2–5 bullets, one per step of the mechanism, each naming the code it lives in, e.g. "`undo_redo_middleware.ts` merges consecutive edits to the same field into one undo step, and closes the step when the selection changes."
- **Worth knowing:** 1–3 bullets on trade-offs, edge cases or what it deliberately doesn't cover. Leave this out if there's nothing a reviewer would ask about.
- **Tests:** one line on what the new or changed tests prove.

**Status:** Draft or ready · reviewers (assignees, requested, who approved or requested changes) · CI · conflicts.
**Ask:** what the user needs from the team. Leave this line out when nothing is blocked.
```

If `open` is empty, say "Nothing new for review" and which filters were applied.

### Working on now

Merge the Jira tickets and `in_progress` PRs into one list, matching them by the ticket key in the PR title, so a ticket with a PR appears once. For each:

```markdown
#### [BSD-12345: 3–6 word plain name](PR url, or the Jira url when there's no PR)

**Say this:** One or two plain sentences: what it's for and where it stands.

**How it works so far** (only when there's a PR)
- 2–4 bullets in the same style as "The fix" above, from the diff.
- **Left to do:** what's unfinished, from the draft flag, TODOs, missing tests or the description.

**Status:** Jira status · PR: none yet / draft / open but not labeled for review · CI.
```

For a ticket with no PR, base "Say this" on the ticket's summary and description, and say there's no PR yet.

### Merged since <day>

One bullet per PR: the linked ticket key and one sentence on what changed for users.

## Rules

- "Say this" is spoken: plain words a PM would follow, no code names. "How it works" is for the follow-up question from an engineer: name real functions, files and classes in backticks, and explain what each does in the flow rather than just listing it.
- Keep "How it works" to about 120 words per PR, and "How it works so far" to about 80. Bullets, not paragraphs.
- Report only what the diff, description, ticket and JSON show. Never guess at behavior, CI or review state. When `ci` is null, leave CI out of the status without comment.
- Don't post, comment, assign, label or transition anything. This skill only reads.
