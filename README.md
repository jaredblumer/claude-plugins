# jaredblumer-plugins

Personal Claude Code plugins.

## Install

```bash
claude plugin marketplace add jaredblumer/claude-plugins
claude plugin install standup@jaredblumer-plugins
```

Update after changes: `claude plugin marketplace update jaredblumer-plugins`.

## Plugins

### standup

`/standup:standup-brief [--label <label>] [--repo <owner/name>] [--unassigned | --any-assignee]`

A standup brief of your own work: PRs for review (what each does and how the code works, from its diff), what you're working on now (Jira tickets In Progress plus open PRs with no label yet), and what merged since your last standup. Read-only; needs `gh` logged in, and a Jira tool in the session (such as the Atlassian connector) for the Jira part.

Example: `/standup:standup-brief --label "M & F" --unassigned`

To run it with no arguments, save your usual filters in `~/.claude/standup-brief.json`:

```json
{ "label": "M & F", "unassigned": true }
```

Arguments still override the file for a one-off run, and `--any-assignee` includes assigned PRs. Add `"jira_jql"` to change which Jira tickets count as in progress (default: `assignee = currentUser() AND status = "In Progress"`).
