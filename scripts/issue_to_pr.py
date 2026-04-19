"""Script to parse a GitHub Issue submission and open a PR with the project JSON file."""

import base64
import json
import os
import re
import sys
from datetime import UTC, datetime
from typing import Any

import httpx


sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from importer import generate_filename as _generate_filename
from validator import ProjectValidator


MAX_TAGS = 10
HTTP_NOT_FOUND = 404
HTTP_UNPROCESSABLE_ENTITY = 422


def parse_field(body: str, label: str) -> str | None:
    pattern = rf"### {re.escape(label)}\s*\n\n(.+?)(?=\n### |\Z)"
    match = re.search(pattern, body, re.DOTALL)
    if not match:
        return None
    value = match.group(1).strip()
    return None if value == "_No response_" else value


def parse_issue_body(body: str) -> dict[str, Any]:
    return {
        "project_name": parse_field(body, "Project Name"),
        "description": parse_field(body, "Description"),
        "category": parse_field(body, "Category"),
        "country": parse_field(body, "Country"),
        "platform": parse_field(body, "Platform"),
        "url_repository": parse_field(body, "Repository URL"),
        "license": parse_field(body, "License"),
        "language": parse_field(body, "Language"),
        "owner_name": parse_field(body, "Owner Name"),
        "owner_type": parse_field(body, "Owner Type"),
        "owner_description": parse_field(body, "Owner Description"),
        "owner_website": parse_field(body, "Owner Website URL"),
        "is_a_startup": parse_field(body, "Is a Startup"),
        "url_documentation": parse_field(body, "Documentation URL"),
        "tags": parse_field(body, "Tags"),
    }


def generate_filename(name: str, url_repository: str) -> str:
    return _generate_filename(name, url_repository)


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


def build_project_json(parsed: dict[str, Any], filename: str) -> dict[str, Any]:
    data: dict[str, Any] = {
        "name": parsed["project_name"],
        "description": parsed["description"],
        "category": parsed["category"],
        "country": parsed["country"],
        "source": {
            "platform": parsed["platform"],
            "url_repository": parsed["url_repository"],
            "license": parsed["license"],
            "language": parsed["language"],
        },
        "owner": {
            "name": parsed["owner_name"] or parsed["project_name"],
            "type": parsed["owner_type"] or "individual",
        },
        "metadata": {
            "filename": filename,
            "filepath": f"awesome/projects/{filename}",
            "created_at": datetime.now(UTC).isoformat(),
        },
    }

    if parsed.get("owner_description"):
        data["owner"]["description"] = parsed["owner_description"]

    if parsed.get("owner_website"):
        data["owner"]["url_website"] = parsed["owner_website"]

    if parsed.get("is_a_startup") is not None:
        data["owner"]["is_a_startup"] = parsed["is_a_startup"] == "Yes"

    if parsed.get("url_documentation"):
        data["source"]["url_documentation"] = parsed["url_documentation"]

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


def github_request(method: str, path: str, token: str, **kwargs: Any) -> dict[str, Any]:
    url = f"https://api.github.com{path}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    response = httpx.request(method, url, headers=headers, **kwargs)
    response.raise_for_status()
    if response.content:
        return response.json()
    return {}


def create_pr(
    json_data: dict[str, Any],
    filename: str,
    issue_number: int,
    repo: str,
    token: str,
) -> str:
    branch_name = f"submission/issue-{issue_number}"
    file_path = f"awesome/projects/{filename}"
    project_name = json_data.get("name", filename)

    # 1. Get SHA of main branch
    ref_data = github_request("GET", f"/repos/{repo}/git/ref/heads/main", token)
    main_sha = ref_data["object"]["sha"]

    # 2. Create or update the submission branch
    try:
        github_request(
            "POST",
            f"/repos/{repo}/git/refs",
            token,
            json={"ref": f"refs/heads/{branch_name}", "sha": main_sha},
        )
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == HTTP_UNPROCESSABLE_ENTITY:
            # Branch already exists — update it to point to main SHA
            github_request(
                "PATCH",
                f"/repos/{repo}/git/refs/heads/{branch_name}",
                token,
                json={"sha": main_sha, "force": True},
            )
        else:
            raise

    # 3. Check if file already exists to get its SHA (needed for update)
    file_sha: str | None = None
    try:
        existing = github_request(
            "GET",
            f"/repos/{repo}/contents/{file_path}",
            token,
            params={"ref": branch_name},
        )
        file_sha = existing.get("sha")
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code != HTTP_NOT_FOUND:
            raise

    # 4. Commit the file
    content_b64 = base64.b64encode(
        json.dumps(json_data, indent=2, ensure_ascii=False).encode()
    ).decode()
    put_body: dict[str, Any] = {
        "message": f"feat: add {project_name} (closes #{issue_number})",
        "content": content_b64,
        "branch": branch_name,
    }
    if file_sha:
        put_body["sha"] = file_sha
    github_request("PUT", f"/repos/{repo}/contents/{file_path}", token, json=put_body)

    # 5. Open PR
    pr_body = (
        f"Automated submission from issue #{issue_number}.\n\nCloses #{issue_number}"
    )
    try:
        pr_data = github_request(
            "POST",
            f"/repos/{repo}/pulls",
            token,
            json={
                "title": f"feat: add {project_name}",
                "head": branch_name,
                "base": "main",
                "body": pr_body,
            },
        )
        return pr_data["html_url"]
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == HTTP_UNPROCESSABLE_ENTITY:
            # PR already exists — find it
            prs = github_request(
                "GET",
                f"/repos/{repo}/pulls",
                token,
                params={"head": f"{repo.split('/')[0]}:{branch_name}", "state": "open"},
            )
            if prs:
                return prs[0]["html_url"]
        raise


def post_comment(issue_number: int, repo: str, token: str, message: str) -> None:
    github_request(
        "POST",
        f"/repos/{repo}/issues/{issue_number}/comments",
        token,
        json={"body": message},
    )


def main() -> int:
    token = os.environ.get("GITHUB_TOKEN")
    issue_body = os.environ.get("ISSUE_BODY")
    issue_number_raw = os.environ.get("ISSUE_NUMBER")
    repo = os.environ.get("REPO_FULL_NAME")

    missing = [
        name
        for name, val in [
            ("GITHUB_TOKEN", token),
            ("ISSUE_BODY", issue_body),
            ("ISSUE_NUMBER", issue_number_raw),
            ("REPO_FULL_NAME", repo),
        ]
        if not val
    ]
    if missing:
        print(f"[ERROR] Missing required environment variables: {', '.join(missing)}")
        return 1

    issue_number = int(issue_number_raw)  # type: ignore[arg-type]

    print(f"[INFO] Processing issue #{issue_number} from {repo}")

    parsed = parse_issue_body(issue_body)  # type: ignore[arg-type]

    if not parsed.get("project_name") or not parsed.get("url_repository"):
        msg = "Could not parse required fields (Project Name, Repository URL) from the issue body. Please check the issue format and re-trigger by removing and re-adding the `approved-submission` label."
        post_comment(issue_number, repo, token, f":x: **Submission failed**\n\n{msg}")  # type: ignore[arg-type]
        return 1

    filename = generate_filename(parsed["project_name"], parsed["url_repository"])  # type: ignore[arg-type]
    print(f"[INFO] Generated filename: {filename}")

    json_data = build_project_json(parsed, filename)

    errors = validate_json(json_data)
    if errors:
        error_list = "\n".join(f"- {e}" for e in errors)
        msg = f":x: **Submission failed — validation errors**\n\n{error_list}\n\nFix the issue body and re-trigger by removing and re-adding the `approved-submission` label."
        post_comment(issue_number, repo, token, msg)  # type: ignore[arg-type]
        print(f"[ERROR] Validation failed: {errors}")
        return 1

    print("[INFO] Validation passed, creating PR...")
    pr_url = create_pr(json_data, filename, issue_number, repo, token)  # type: ignore[arg-type]

    msg = f":white_check_mark: **Submission processed!**\n\nA pull request has been opened: {pr_url}\n\nThe PR will be reviewed and merged by a maintainer."
    post_comment(issue_number, repo, token, msg)  # type: ignore[arg-type]
    print(f"[INFO] PR created: {pr_url}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
