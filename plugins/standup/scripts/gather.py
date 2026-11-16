#!/usr/bin/env python3
"""Gather the PRs a standup brief covers, as JSON on stdout.

Open PRs you authored (optionally filtered by label and by having no assignee),
each with its description, changed files, review state and CI state, plus the
PRs you merged since the last workday.

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

VIEW_FIELDS = "body,files,isDraft,reviewDecision,reviewRequests,latestReviews,mergeable,createdAt,updatedAt"
CUBIC_MARKER = "<!-- This is an auto-generated description by cubic"


CONFIG_PATH = os.path.expanduser("~/.claude/standup-brief.json")
CONFIG_KEYS = {"label", "repo", "unassigned"}


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


def search(state_args, args):
    query = ["search", "prs", "--author=@me", "--limit", "100",
             "--json", "number,title,repository,assignees,url,labels"]
    query += state_args
    if args.label:
        query += ["--label", args.label]
    if args.repo:
        query += ["--repo", args.repo]
    return gh(*query)


def ci_summary(repo, number):
    result = subprocess.run(["gh", "pr", "checks", str(number), "-R", repo, "--json", "name,bucket"],
                            capture_output=True, text=True)
    if not result.stdout.strip().startswith("["):
        return {"unavailable": result.stderr.strip().splitlines()[0][:200] if result.stderr.strip() else "no checks"}
    checks = json.loads(result.stdout)
    counts = {}
    for check in checks:
        counts[check["bucket"]] = counts.get(check["bucket"], 0) + 1
    return {"counts": counts, "failing": [c["name"] for c in checks if c["bucket"] == "fail"]}


def details(pr, body_chars):
    repo = pr["repository"]["nameWithOwner"]
    view = gh("pr", "view", str(pr["number"]), "-R", repo, "--json", VIEW_FIELDS)
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
        "ci": ci_summary(repo, pr["number"]),
        "mergeable": view.get("mergeable"),
        "created": view.get("createdAt", "")[:10],
        "updated": view.get("updatedAt", "")[:10],
        "files": [f"{f['path']} +{f['additions']}/-{f['deletions']}" for f in view.get("files", [])],
        "body": body[:body_chars],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--label", help="Only PRs with this label, e.g. 'M & F'")
    parser.add_argument("--repo", help="Only PRs in this repo, e.g. owner/name")
    parser.add_argument("--unassigned", action="store_true", help="Only open PRs with no assignee")
    parser.add_argument("--any-assignee", dest="unassigned", action="store_false",
                        help="Include assigned PRs, overriding the config file")
    parser.add_argument("--body-chars", type=int, default=6000)
    parser.set_defaults(**load_config())
    args = parser.parse_args()

    open_args = ["--state", "open"] + (["--no-assignee"] if args.unassigned else [])
    since = last_workday(datetime.date.today()).isoformat()
    merged = search(["--merged", "--merged-at", f">={since}"], args)

    print(json.dumps({
        "since": since,
        "open": [details(pr, args.body_chars) for pr in search(open_args, args)],
        "merged_since": [{"repo": p["repository"]["nameWithOwner"], "number": p["number"],
                          "title": p["title"], "url": p["url"]} for p in merged],
    }, indent=2))


if __name__ == "__main__":
    main()
