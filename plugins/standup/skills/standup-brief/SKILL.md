---
name: standup-brief
description: Write a standup brief of your own work in the meeting's two parts — PRs to hand out for review, then what you finished and what you're working on today (in-progress Jira tickets and PRs not yet labeled for review) — with a few bullets under each PR on how its code works, enough to answer "how does that work?". Use when the user says "standup brief", "prep my standup", "what do I say at standup", or asks to describe their PRs or current work for a meeting.
argument-hint: "[--label <label>] [--repo <owner/name>] [--unassigned | --any-assignee] [--jira-jql <jql>]"
---

# Standup brief

Standup has two parts: first the team hands out PRs for review, then each person says what they finished and what they're working on today. The brief follows that order. Each item opens with a sentence or two the user can read out, followed by a few short bullets on how the code works, for when someone asks.

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

Then run `jira_jql` with whatever Jira tool this session has (for example the Atlassian connector's JQL search), asking for summary, status and description. If no Jira tool is available or it fails, carry on without Jira and say so in one line in part 2.

## 2. Read the code

For every PR in `open` and `in_progress`, read its `code_diff.path` in full; the description alone isn't enough. If `code_diff.cut_files` lists files, read those files' full diffs with `gh pr diff`. Work out:

- the root cause: what the old code did that produced the bug or gap
- the mechanism of the fix: which function, component or class changes, and what it does now
- the one or two decisions a reviewer would question: a trade-off, an edge case, or something it deliberately leaves out
- for an in-progress PR, what's unfinished: the draft flag, TODOs, missing tests, or open work named in the description

When there are more than four PRs in all, hand each PR's reading to a subagent in parallel, giving it the diff path and the description, and asking for the points above in under 100 words. Don't narrate the subagents' progress; write nothing until the brief is ready.

## 3. Write the brief

Use markdown laid out like a blog post, so the user can skim headings and stop on the one they need: a title, a one-line summary, a `##` heading per part with a rule between parts, and a `###` headline per item that leads with a plain name (no ticket key in the headline). Under each headline goes an italic byline with the link, then the spoken paragraph, then the bullets. Leave a blank line between every block. Use exactly this shape:

```markdown
# Standup · <weekday, month day>

<one line of counts, e.g. "5 PRs to hand out · 4 things in progress · 3 finished since Friday">

---

## 🔍 PRs to hand out for review

### Plain 3–6 word name
*[BSD-12345](PR url) · <reviewer, or "needs a reviewer"> · <CI: passing / failing: names / running>*

One or two plain sentences: what changes for the user.

- **Before:** one sentence on the root cause, naming the function or file in backticks.
- **Now:** one or two bullets on the mechanism, each naming the code it lives in.
- **Note:** one bullet on a trade-off or something it deliberately leaves out. Leave this out if there's nothing a reviewer would ask about.

---

## 🛠️ What I'm working on

### Finished since <day>
- [BSD-111](url) plain name
- [BSD-222](url) plain name

### Plain 3–6 word name
*[BSD-12345](PR or Jira url) · <PR: draft / not labeled for review yet / none yet> · <CI if there's a PR>*

One or two plain sentences: what it's for and where it stands.

- **Now:** one or two bullets on how the code works so far (only when there's a PR).
- **Left to do:** one line (only when there's a PR).
```

- In part 1, list the PRs in `open`, newest activity first. If there are none, write "Nothing new for review" and the filters that were applied.
- In part 2, "Finished since" lists `merged_since`; write "Nothing" if it's empty. Then list the Jira tickets and the `in_progress` PRs, matched by the ticket key in the PR title, so a ticket with a PR appears once. For a ticket with no PR, base its sentences on the ticket's summary and description, with no bullets.

## Rules

- The paragraph under each byline is read aloud: plain words a PM would follow, no file or function names. The bullets are for an engineer's follow-up question: name real functions, files and classes in backticks, and say what each does.
- Keep each item's bullets to about 60 words, three bullets at most (four with **Left to do**). No nested bullets, no test details.
- Report only what the diff, description, ticket and JSON show. Never guess at behavior, CI or review state. When `ci` is null, leave CI out without comment. Show a Jira status only when it came from the Jira query.
- Don't post, comment, assign, label or transition anything. This skill only reads.
