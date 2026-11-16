#!/usr/bin/env python3
"""Gather the PRs a standup brief covers, as JSON on stdout.

- open: open PRs you authored (optionally filtered by label and by having no
  assignee), each with its description, changed files, review state and CI state
- in_progress: your open PRs with no label at all, i.e. not ready for review yet
- merged_since: PRs you merged since the last workday
- jira_jql: the JQL the skill runs for your in-progress Jira tickets

Default filters come from ~/.claude/standup-brief.json, e.g.
{"label": "M & F", "unassigned": true}; command-line arguments override them.
"""
import argparse
import datetime
import json
import os
import re
import subprocess
import sys
import tempfile

VIEW_FIELDS = "body,files,headRefOid,isDraft,reviewDecision,reviewRequests,latestReviews,mergeable,createdAt,updatedAt"
CUBIC_MARKER = "<!-- This is an auto-generated description by cubic"


CONFIG_PATH = os.path.expanduser("~/.claude/standup-brief.json")
CONFIG_KEYS = {"label", "repo", "unassigned", "jira_jql"}
DEFAULT_JIRA_JQL = 'assignee = currentUser() AND status = "In Progress" ORDER BY updated DESC'


def load_config():
    if not os.path.exists(CONFIG_PATH):
        return {}
    with open(CONFIG_PATH) as f:
        config = json.load(f)
    unknown = set(config) - CONFIG_KEYS
    if unknown:
        sys.exit(f"{CONFIG_PATH}: unknown keys {sorted(unknown)}; allowed: {sorted(CONFIG_KEYS)}")
    return config


def gh(*args):
    result = subprocess.run(["gh", *args], capture_output=True, text=True)
    if result.returncode != 0:
        sys.exit(f"gh {' '.join(args)} failed: {result.stderr.strip()}")
    return json.loads(result.stdout or "null")


def last_workday(today):
    days_back = 3 if today.weekday() == 0 else 2 if today.weekday() == 6 else 1
    return today - datetime.timedelta(days=days_back)


def search(state_args, args, use_label=True):
    query = ["search", "prs", "--author=@me", "--limit", "100",
             "--json", "number,title,repository,assignees,url,labels"]
    query += state_args
    if use_label and args.label:
        query += ["--label", args.label]
    if args.repo:
        query += ["--repo", args.repo]
    return gh(*query)


def try_gh(*args):
    result = subprocess.run(["gh", *args], capture_output=True, text=True)
    if result.returncode != 0 or not result.stdout.strip():
        return None
    return json.loads(result.stdout)


def ci_summary(repo, number, sha):
    """CI state from whatever the token can read: PR checks, else Actions runs plus commit status."""
    checks = try_gh("pr", "checks", str(number), "-R", repo, "--json", "name,bucket")
    if checks is not None:
        return {
            "source": "checks",
            "pending": [c["name"] for c in checks if c["bucket"] == "pending"],
            "failing": [c["name"] for c in checks if c["bucket"] == "fail"],
            "passed": sum(1 for c in checks if c["bucket"] == "pass"),
        }

    runs = try_gh("run", "list", "-R", repo, "--commit", sha, "--limit", "100",
                  "--json", "workflowName,status,conclusion")
    status = try_gh("api", f"repos/{repo}/commits/{sha}/status")
    if runs is None and status is None:
        return None

    latest = {}
    for run in runs or []:
        latest.setdefault(run["workflowName"], run)
    return {
        "source": "actions",
        "pending": [n for n, r in latest.items() if r["status"] != "completed"],
        "failing": [n for n, r in latest.items()
                    if r["conclusion"] in ("failure", "timed_out", "cancelled", "startup_failure")],
        "passed": sum(1 for r in latest.values() if r["conclusion"] == "success"),
        "commit_status": status["state"] if status and status.get("total_count") else None,
    }


TEST_PATH = re.compile(r"(^|/)(spec|specs|test|tests|__tests__|e2e|features)/|\.(test|spec)\.[jt]sx?$|_spec\.rb$|_test\.rb$")
SKIP_PATH = re.compile(r"(\.lock|lock\.json|\.snap|\.min\.js|\.svg|\.png|\.jpg)$")


def write_code_diff(repo, number, out_dir, file_chars):
    """Save the PR's diff without tests, lockfiles and assets, each file capped, for reading how it works."""
    result = subprocess.run(["gh", "pr", "diff", str(number), "-R", repo], capture_output=True, text=True)
    if result.returncode != 0:
        return None
    kept, cut = [], []
    for chunk in re.split(r"(?m)^(?=diff --git )", result.stdout):
        match = re.match(r"diff --git a/(\S+)", chunk)
        if not match or TEST_PATH.search(match.group(1)) or SKIP_PATH.search(match.group(1)):
            continue
        if len(chunk) > file_chars:
            cut.append(match.group(1))
            chunk = chunk[:file_chars] + f"\n... [cut at {file_chars} chars; read the rest with gh pr diff]\n"
        kept.append(chunk)
    path = os.path.join(out_dir, f"{repo.replace('/', '_')}_{number}.diff")
    with open(path, "w") as f:
        f.write("".join(kept))
    return {"path": path, "cut_files": cut}


def details(pr, body_chars, out_dir, file_chars):
    repo = pr["repository"]["nameWithOwner"]
    view = gh("pr", "view", str(pr["number"]), "-R", repo, "--json", VIEW_FIELDS)
    files = view.get("files", [])
    body = (view.get("body") or "").split(CUBIC_MARKER)[0].strip()
    body = re.sub(r"<img[^>]*>", "[image]", body)
    return {
        "repo": repo,
        "number": pr["number"],
        "title": pr["title"],
        "url": pr["url"],
        "assignees": [a["login"] for a in pr.get("assignees", [])],
        "labels": [l["name"] for l in pr.get("labels", [])],
        "draft": view.get("isDraft"),
        "review_decision": view.get("reviewDecision") or "NONE",
        "review_requests": [r.get("login") or r.get("name") for r in view.get("reviewRequests", [])],
        "latest_reviews": [{"author": r["author"]["login"], "state": r["state"]} for r in view.get("latestReviews", [])],
        "ci": ci_summary(repo, pr["number"], view["headRefOid"]),
        "mergeable": view.get("mergeable"),
        "created": view.get("createdAt", "")[:10],
        "updated": view.get("updatedAt", "")[:10],
        "files": [f"{f['path']} +{f['additions']}/-{f['deletions']}" for f in files if not TEST_PATH.search(f["path"])],
        "test_files": [f["path"] for f in files if TEST_PATH.search(f["path"])],
        "body": body[:body_chars],
        "code_diff": write_code_diff(repo, pr["number"], out_dir, file_chars),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--label", help="Only PRs with this label, e.g. 'M & F'")
    parser.add_argument("--repo", help="Only PRs in this repo, e.g. owner/name")
    parser.add_argument("--unassigned", action="store_true", help="Only open PRs with no assignee")
    parser.add_argument("--any-assignee", dest="unassigned", action="store_false",
                        help="Include assigned PRs, overriding the config file")
    parser.add_argument("--jira-jql", dest="jira_jql",
                        help="JQL for your in-progress Jira tickets (default: assigned to you, status In Progress)")
    parser.add_argument("--body-chars", type=int, default=6000)
    parser.add_argument("--diff-file-chars", type=int, default=8000,
                        help="Cap on each changed file's diff in the saved code diff")
    parser.set_defaults(**load_config())
    args = parser.parse_args()
    out_dir = tempfile.mkdtemp(prefix="standup-brief-")

    open_args = ["--state", "open"] + (["--no-assignee"] if args.unassigned else [])
    since = last_workday(datetime.date.today()).isoformat()
    merged = search(["--merged", "--merged-at", f">={since}"], args)

    unlabeled = search(["--state", "open", "--no-label"], args, use_label=False)

    print(json.dumps({
        "since": since,
        "filters": {"label": args.label, "repo": args.repo, "unassigned": args.unassigned},
        "jira_jql": args.jira_jql or DEFAULT_JIRA_JQL,
        "open": [details(pr, args.body_chars, out_dir, args.diff_file_chars) for pr in search(open_args, args)],
        "in_progress": [details(pr, args.body_chars, out_dir, args.diff_file_chars) for pr in unlabeled],
        "merged_since": [{"repo": p["repository"]["nameWithOwner"], "number": p["number"],
                          "title": p["title"], "url": p["url"]} for p in merged],
    }, indent=2))


if __name__ == "__main__":
    main()
