"""Script to parse a GitHub Issue submission and open a PR with the project JSON file."""

import argparse
import base64
import json
import os
import re
import sys
from typing import Any

import httpx


sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from importer import (
    generate_filename,
    get_timestamp,
    sanitize_description,
    sanitize_name,
    sanitize_text,
)
from validator import ProjectValidator


MAX_TAGS = 10
HTTP_NOT_FOUND = 404
HTTP_UNPROCESSABLE_ENTITY = 422

LABEL_CHECK = "check-submission"
LABEL_APPROVED = "approved-submission"

ISSUE_FIELDS: dict[str, str] = {
    "project_name": "Project Name",
    "description": "Description",
    "category": "Category",
    "country": "Country",
    "platform": "Platform",
    "url_repository": "Repository URL",
    "license": "License",
    "language": "Language",
    "owner_name": "Owner Name",
    "owner_type": "Owner Type",
    "owner_description": "Owner Description",
    "owner_website": "Owner Website URL",
    "is_a_startup": "Is a Startup",
    "url_documentation": "Documentation URL",
    "tags": "Tags",
}


def parse_field(body: str, label: str) -> str | None:
    pattern = rf"### {re.escape(label)}\s*\n\n(.+?)(?=\n### |\Z)"
    match = re.search(pattern, body, re.DOTALL)
    if not match:
        return None
    value = match.group(1).strip()
    return None if value == "_No response_" else value


def parse_issue_body(body: str) -> dict[str, Any]:
    sections: dict[str, str] = {}
    for match in re.finditer(r"### (.+?)\s*\n\n(.+?)(?=\n### |\Z)", body, re.DOTALL):
        sections[match.group(1).strip()] = match.group(2).strip()

    result: dict[str, Any] = {}
    for key, label in ISSUE_FIELDS.items():
        raw = sections.get(label)
        result[key] = None if (raw is None or raw == "_No response_") else raw
    return result


def normalize_tags(raw: str | None) -> list[str]:
    if not raw:
        return []
    seen: set[str] = set()
    result = []
    for tag in raw.split(","):
        normalized = tag.strip().lower()[:24]
        if normalized and normalized not in seen:
            seen.add(normalized)
            result.append(normalized)
        if len(result) == MAX_TAGS:
            break
    return result


def parse_country(raw: str | None) -> list[str]:
    """Split comma-separated country input into a list of sanitized strings."""
    if not raw:
        return []
    return [sanitize_text(c) for c in raw.split(",") if sanitize_text(c)]


def build_project_json(parsed: dict[str, Any], filename: str) -> dict[str, Any]:
    data: dict[str, Any] = {
        "name": sanitize_name(parsed["project_name"] or ""),
        "description": sanitize_description(parsed["description"] or ""),
        "category": sanitize_text(parsed["category"] or "").lower(),
        "country": parse_country(parsed.get("country")),
        "source": {
            "platform": sanitize_text(parsed["platform"] or ""),
            "url_repository": sanitize_text(parsed["url_repository"] or ""),
            "license": sanitize_text(parsed["license"] or ""),
            "language": sanitize_text(parsed["language"] or ""),
        },
        "owner": {
            "name": sanitize_name(parsed["owner_name"] or ""),
            "type": sanitize_text(parsed["owner_type"] or "individual").lower(),
        },
        "metadata": {
            "filename": filename,
            "filepath": f"awesome/projects/{filename}",
            "created_at": get_timestamp(),
        },
    }

    if parsed.get("owner_description"):
        data["owner"]["description"] = sanitize_description(parsed["owner_description"])

    if parsed.get("owner_website"):
        data["owner"]["url_website"] = sanitize_text(parsed["owner_website"])

    if parsed.get("is_a_startup") is not None:
        data["owner"]["is_a_startup"] = parsed["is_a_startup"] == "Yes"

    if parsed.get("url_documentation"):
        data["source"]["url_documentation"] = sanitize_text(parsed["url_documentation"])

    tags = normalize_tags(parsed.get("tags"))
    if tags:
        data["tags"] = tags

    return data


def validate_json(data: dict[str, Any]) -> list[str]:
    validator = ProjectValidator()
    _, errors = validator.validate(data=data, check_file_exists=False)
    if errors:
        return [e["message"] for e in errors]
    return []


class GitHubClient:
    BASE_URL = "https://api.github.com"

    def __init__(self, token: str) -> None:
        self._client = httpx.Client(
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            }
        )

    def request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        response = self._client.request(method, f"{self.BASE_URL}{path}", **kwargs)
        response.raise_for_status()
        return response.json() if response.content else {}

    def __enter__(self) -> "GitHubClient":
        return self

    def __exit__(self, *args: Any) -> None:
        self._client.close()


def create_pr(
    gh: GitHubClient,
    json_data: dict[str, Any],
    filename: str,
    issue_number: int,
    repo: str,
) -> str:
    branch_name = f"submission/issue-{issue_number}"
    file_path = f"awesome/projects/{filename}"
    project_name = json_data["name"]

    ref_data = gh.request("GET", f"/repos/{repo}/git/ref/heads/main")
    main_sha = ref_data["object"]["sha"]

    try:
        gh.request(
            "POST",
            f"/repos/{repo}/git/refs",
            json={"ref": f"refs/heads/{branch_name}", "sha": main_sha},
        )
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == HTTP_UNPROCESSABLE_ENTITY:
            gh.request(
                "PATCH",
                f"/repos/{repo}/git/refs/heads/{branch_name}",
                json={"sha": main_sha, "force": True},
            )
        else:
            raise

    file_sha: str | None = None
    try:
        existing = gh.request(
            "GET",
            f"/repos/{repo}/contents/{file_path}",
            params={"ref": branch_name},
        )
        file_sha = existing.get("sha")
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code != HTTP_NOT_FOUND:
            raise

    content_b64 = base64.b64encode(
        (json.dumps(json_data, indent=2, ensure_ascii=False) + "\n").encode()
    ).decode()
    put_body: dict[str, Any] = {
        "message": f"feat(awesome:projects): add {project_name} (closes #{issue_number})",
        "content": content_b64,
        "branch": branch_name,
    }
    if file_sha:
        put_body["sha"] = file_sha
    gh.request("PUT", f"/repos/{repo}/contents/{file_path}", json=put_body)

    pr_body = (
        f"Automated submission from issue #{issue_number}.\n\nCloses #{issue_number}"
    )
    try:
        pr_data = gh.request(
            "POST",
            f"/repos/{repo}/pulls",
            json={
                "title": f"feat(awesome:projects): add {project_name}",
                "head": branch_name,
                "base": "main",
                "body": pr_body,
            },
        )
        return pr_data["html_url"]
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == HTTP_UNPROCESSABLE_ENTITY:
            prs = gh.request(
                "GET",
                f"/repos/{repo}/pulls",
                params={"head": f"{repo.split('/')[0]}:{branch_name}", "state": "open"},
            )
            if prs:
                return prs[0]["html_url"]
        raise


def post_comment(gh: GitHubClient, issue_number: int, repo: str, message: str) -> None:
    gh.request(
        "POST",
        f"/repos/{repo}/issues/{issue_number}/comments",
        json={"body": message},
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Process a GitHub issue submission into a PR"
    )
    parser.add_argument("--issue-number", type=int, required=True, metavar="N")
    parser.add_argument("--repo", required=True, metavar="OWNER/REPO")
    parser.add_argument("--issue-body", required=True, metavar="TEXT")
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument(
        "--output-dir",
        metavar="PATH",
        help="Write submission JSON to this directory before creating the PR",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("[ERROR] GITHUB_TOKEN environment variable is required")
        return 1

    validate_only = args.validate_only
    mode = "validate-only" if validate_only else "full"
    print(
        f"[INFO] Processing issue #{args.issue_number} from {args.repo} (mode: {mode})"
    )

    parsed = parse_issue_body(args.issue_body)
    retrigger_label = LABEL_CHECK if validate_only else LABEL_APPROVED

    with GitHubClient(token) as gh:
        if not parsed.get("project_name") or not parsed.get("url_repository"):
            msg = f"Could not parse required fields (Project Name, Repository URL) from the issue body. Please check the issue format and re-trigger by removing and re-adding the `{retrigger_label}` label."
            post_comment(
                gh,
                args.issue_number,
                args.repo,
                f":x: **Submission check failed**\n\n{msg}",
            )
            return 1

        filename = generate_filename(parsed["project_name"], parsed["url_repository"])
        print(f"[INFO] Generated filename: {filename}")

        json_data = build_project_json(parsed, filename)

        errors = validate_json(json_data)
        if errors:
            error_list = "\n".join(f"- {e}" for e in errors)
            if validate_only:
                msg = f":x: **Validation failed**\n\n{error_list}\n\nFix the issue body and re-trigger by removing and re-adding the `{LABEL_CHECK}` label."
            else:
                msg = f":x: **Submission failed — validation errors**\n\n{error_list}\n\nFix the issue body and re-trigger by removing and re-adding the `{LABEL_APPROVED}` label."
            post_comment(gh, args.issue_number, args.repo, msg)
            print(f"[ERROR] Validation failed: {errors}")
            return 1

        if args.output_dir:
            output_path = os.path.join(args.output_dir, filename)
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(json_data, f, indent=2, ensure_ascii=False)
                f.write("\n")
            print(f"[INFO] Written submission to: {output_path}")

        if validate_only:
            msg = f":white_check_mark: **Validation passed!**\n\nThe submission is valid. A maintainer can now add the `{LABEL_APPROVED}` label to create the PR."
            post_comment(gh, args.issue_number, args.repo, msg)
            print("[INFO] Validation passed (validate-only mode, skipping PR creation)")
            return 0

        print("[INFO] Validation passed, creating PR...")
        pr_url = create_pr(gh, json_data, filename, args.issue_number, args.repo)
        msg = f":white_check_mark: **Submission processed!**\n\nA pull request has been opened: {pr_url}\n\nThe PR will be reviewed and merged by a maintainer."
        post_comment(gh, args.issue_number, args.repo, msg)
        print(f"[INFO] PR created: {pr_url}")
        return 0


if __name__ == "__main__":
    sys.exit(main())
