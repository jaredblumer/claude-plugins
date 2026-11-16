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

A standup brief of your own PRs: what each open PR does, how it was built, its review and CI state, and what merged since your last standup. Read-only; needs `gh` logged in.

Example: `/standup:standup-brief --label "M & F" --unassigned`

To run it with no arguments, save your usual filters in `~/.claude/standup-brief.json`:

```json
{ "label": "M & F", "unassigned": true }
```

Arguments still override the file for a one-off run, and `--any-assignee` includes assigned PRs.
