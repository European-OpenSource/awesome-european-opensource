"""Tests for scripts/issue_to_pr.py"""

import os
from unittest.mock import patch

from issue_to_pr import (
    build_project_json,
    generate_filename,
    main,
    normalize_tags,
    parse_field,
    parse_issue_body,
    validate_json,
)


MAX_TAGS = 10
ISSUE_NUMBER = 42


# ---------------------------------------------------------------------------
# parse_field
# ---------------------------------------------------------------------------


class TestParseField:
    def test_extracts_simple_value(self):
        body = "### Project Name\n\nCertMate\n\n### Next\n\nOther"
        assert parse_field(body, "Project Name") == "CertMate"

    def test_trims_surrounding_whitespace(self):
        body = "### Project Name\n\n  My Tool  \n\n### Next\n\nOther"
        assert parse_field(body, "Project Name") == "My Tool"

    def test_no_response_returns_none(self):
        body = "### Tags\n\n_No response_\n\n### Next\n\nOther"
        assert parse_field(body, "Tags") is None

    def test_missing_field_returns_none(self):
        body = "### Description\n\nsome text"
        assert parse_field(body, "Nonexistent Field") is None

    def test_multiline_value(self):
        body = "### Description\n\nLine one\nLine two\n\n### Next\n\nOther"
        result = parse_field(body, "Description")
        assert "Line one" in result
        assert "Line two" in result

    def test_last_field_no_trailing_section(self):
        body = "### Tags\n\nssl, cert"
        assert parse_field(body, "Tags") == "ssl, cert"


# ---------------------------------------------------------------------------
# parse_issue_body
# ---------------------------------------------------------------------------


class TestParseIssueBody:
    def test_all_fields_extracted(self, valid_issue_body):
        result = parse_issue_body(valid_issue_body)
        assert result["project_name"] == "CertMate"
        assert result["category"] == "app"
        assert result["country"] == "Italy"
        assert result["platform"] == "GitHub"
        assert result["url_repository"] == "https://github.com/fabriziosalmi/certmate"
        assert result["license"] == "MIT"
        assert result["language"] == "Python"
        assert result["owner_name"] == "Fabrizio Salmi"
        assert result["owner_type"] == "individual"
        assert result["tags"] == "ssl, certificate, monitoring"

    def test_optional_no_response_fields_are_none(self, valid_issue_body):
        result = parse_issue_body(valid_issue_body)
        assert result["owner_description"] is None
        assert result["owner_website"] is None

    def test_minimal_body_required_fields_present(self, minimal_issue_body):
        result = parse_issue_body(minimal_issue_body)
        assert result["project_name"] == "MyProject"
        assert result["url_repository"] == "https://gitlab.com/owner/myproject"
        assert result["owner_name"] is None
        assert result["tags"] is None


# ---------------------------------------------------------------------------
# generate_filename
# ---------------------------------------------------------------------------


class TestGenerateFilename:
    def test_matches_existing_file_pattern(self):
        # Verified against certmate-3aec74.json already in the repo
        fn = generate_filename("CertMate", "https://github.com/fabriziosalmi/certmate")
        assert fn == "certmate-3aec74.json"

    def test_produces_json_extension(self):
        fn = generate_filename("MyTool", "https://github.com/owner/mytool")
        assert fn.endswith(".json")

    def test_slug_is_lowercase_hyphenated(self):
        fn = generate_filename("My Cool Tool!", "https://github.com/x/y")
        slug = fn.rsplit("-", 1)[0]
        assert slug == slug.lower()
        assert " " not in slug
        assert "!" not in slug

    def test_same_inputs_produce_same_filename(self):
        fn1 = generate_filename("Proj", "https://github.com/a/b")
        fn2 = generate_filename("Proj", "https://github.com/a/b")
        assert fn1 == fn2

    def test_different_urls_produce_different_filenames(self):
        fn1 = generate_filename("Proj", "https://github.com/a/b")
        fn2 = generate_filename("Proj", "https://github.com/a/c")
        assert fn1 != fn2


# ---------------------------------------------------------------------------
# normalize_tags
# ---------------------------------------------------------------------------


class TestNormalizeTags:
    def test_returns_empty_list_for_none(self):
        assert normalize_tags(None) == []

    def test_returns_empty_list_for_empty_string(self):
        assert normalize_tags("") == []

    def test_lowercases_and_strips(self):
        assert normalize_tags("  SSL , Cert ") == ["ssl", "cert"]

    def test_deduplicates(self):
        result = normalize_tags("ssl, SSL, Ssl")
        assert result == ["ssl"]

    def test_truncates_tag_to_24_chars(self):
        long_tag = "a" * 30
        result = normalize_tags(long_tag)
        assert result == ["a" * 24]

    def test_max_10_tags(self):
        tags = ", ".join(str(i) for i in range(15))
        result = normalize_tags(tags)
        assert len(result) == MAX_TAGS

    def test_preserves_order_of_first_occurrence(self):
        result = normalize_tags("beta, alpha, gamma")
        assert result == ["beta", "alpha", "gamma"]


# ---------------------------------------------------------------------------
# build_project_json
# ---------------------------------------------------------------------------


class TestBuildProjectJson:
    def _parsed(self, **overrides):
        base = {
            "project_name": "TestApp",
            "description": "A test application.",
            "category": "app",
            "country": "Italy",
            "platform": "GitHub",
            "url_repository": "https://github.com/owner/testapp",
            "license": "MIT",
            "language": "Python",
            "owner_name": None,
            "owner_type": None,
            "owner_description": None,
            "owner_website": None,
            "is_a_startup": None,
            "url_documentation": None,
            "tags": None,
        }
        base.update(overrides)
        return base

    def test_required_fields_present(self):
        data = build_project_json(self._parsed(), "testapp-abc123.json")
        assert data["name"] == "TestApp"
        assert data["description"] == "A test application."
        assert data["category"] == "app"
        assert data["source"]["platform"] == "GitHub"
        assert data["source"]["license"] == "MIT"

    def test_metadata_fields(self):
        data = build_project_json(self._parsed(), "testapp-abc123.json")
        assert data["metadata"]["filename"] == "testapp-abc123.json"
        assert data["metadata"]["filepath"] == "awesome/projects/testapp-abc123.json"
        assert "created_at" in data["metadata"]

    def test_owner_defaults_when_missing(self):
        data = build_project_json(self._parsed(), "f.json")
        assert data["owner"]["name"] == "TestApp"
        assert data["owner"]["type"] == "individual"

    def test_owner_fields_used_when_provided(self):
        parsed = self._parsed(owner_name="Alice", owner_type="organization")
        data = build_project_json(parsed, "f.json")
        assert data["owner"]["name"] == "Alice"
        assert data["owner"]["type"] == "organization"

    def test_optional_owner_description_included(self):
        parsed = self._parsed(owner_description="Great org")
        data = build_project_json(parsed, "f.json")
        assert data["owner"]["description"] == "Great org"

    def test_optional_url_documentation_included(self):
        parsed = self._parsed(url_documentation="https://docs.example.com")
        data = build_project_json(parsed, "f.json")
        assert data["source"]["url_documentation"] == "https://docs.example.com"

    def test_is_a_startup_yes_maps_to_true(self):
        parsed = self._parsed(is_a_startup="Yes")
        data = build_project_json(parsed, "f.json")
        assert data["owner"]["is_a_startup"] is True

    def test_is_a_startup_no_maps_to_false(self):
        parsed = self._parsed(is_a_startup="No")
        data = build_project_json(parsed, "f.json")
        assert data["owner"]["is_a_startup"] is False

    def test_tags_normalized_and_included(self):
        parsed = self._parsed(tags="ssl, cert, monitoring")
        data = build_project_json(parsed, "f.json")
        assert data["tags"] == ["ssl", "cert", "monitoring"]

    def test_no_tags_key_when_empty(self):
        data = build_project_json(self._parsed(), "f.json")
        assert "tags" not in data


# ---------------------------------------------------------------------------
# validate_json
# ---------------------------------------------------------------------------


class TestValidateJson:
    def _valid_data(self):
        return {
            "name": "TestApp",
            "description": "A test application for the catalog.",
            "category": "app",
            "country": "Italy",
            "source": {
                "platform": "GitHub",
                "url_repository": "https://github.com/owner/testapp",
                "license": "MIT",
                "language": "Python",
            },
            "owner": {"name": "Owner", "type": "individual"},
            "metadata": {
                "filename": "testapp-abc123.json",
                "filepath": "awesome/projects/testapp-abc123.json",
                "created_at": "2026-01-01T00:00:00+00:00",
            },
        }

    def test_valid_data_returns_no_errors(self):
        errors = validate_json(self._valid_data())
        assert errors == []

    def test_invalid_license_returns_error(self):
        data = self._valid_data()
        data["source"]["license"] = "NOT-A-LICENSE"
        errors = validate_json(data)
        assert len(errors) > 0

    def test_invalid_category_returns_error(self):
        data = self._valid_data()
        data["category"] = "not-a-category"
        errors = validate_json(data)
        assert len(errors) > 0

    def test_missing_required_field_returns_error(self):
        data = self._valid_data()
        del data["source"]
        errors = validate_json(data)
        assert len(errors) > 0

    def test_description_too_long_returns_error(self):
        data = self._valid_data()
        data["description"] = "x" * 513
        errors = validate_json(data)
        assert len(errors) > 0


# ---------------------------------------------------------------------------
# main() — end-to-end with mocked GitHub API
# ---------------------------------------------------------------------------


MOCK_ENV = {
    "GITHUB_TOKEN": "fake-token",
    "ISSUE_BODY": "",
    "ISSUE_NUMBER": "42",
    "REPO_FULL_NAME": "European-OpenSource/awesome-european-opensource",
}


class TestMain:
    def test_exits_1_when_env_vars_missing(self):
        with patch.dict(os.environ, {}, clear=True):
            assert main() == 1

    def test_exits_1_when_token_missing(self):
        env = {k: v for k, v in MOCK_ENV.items() if k != "GITHUB_TOKEN"}
        with patch.dict(os.environ, env, clear=True):
            assert main() == 1

    def test_exits_1_and_posts_comment_when_body_unparseable(self):
        env = {**MOCK_ENV, "ISSUE_BODY": "this body has no structured fields"}
        with (
            patch.dict(os.environ, env, clear=True),
            patch("issue_to_pr.post_comment") as mock_comment,
        ):
            result = main()
        assert result == 1
        mock_comment.assert_called_once()
        assert "failed" in mock_comment.call_args[0][3].lower()

    def test_exits_1_and_posts_comment_on_validation_failure(self, valid_issue_body):
        bad_body = valid_issue_body.replace("MIT", "NOT-A-REAL-LICENSE")
        env = {**MOCK_ENV, "ISSUE_BODY": bad_body}
        with (
            patch.dict(os.environ, env, clear=True),
            patch("issue_to_pr.post_comment") as mock_comment,
        ):
            result = main()
        assert result == 1
        mock_comment.assert_called_once()
        comment_text = mock_comment.call_args[0][3]
        assert "validation" in comment_text.lower() or "error" in comment_text.lower()

    def test_happy_path_creates_pr_and_posts_comment(self, valid_issue_body):
        fake_pr_url = (
            "https://github.com/European-OpenSource/awesome-european-opensource/pull/99"
        )
        env = {**MOCK_ENV, "ISSUE_BODY": valid_issue_body}

        with (
            patch.dict(os.environ, env, clear=True),
            patch("issue_to_pr.create_pr", return_value=fake_pr_url) as mock_pr,
            patch("issue_to_pr.post_comment") as mock_comment,
        ):
            result = main()

        assert result == 0
        mock_pr.assert_called_once()
        mock_comment.assert_called_once()
        comment_text = mock_comment.call_args[0][3]
        assert fake_pr_url in comment_text

    def test_happy_path_passes_correct_repo_and_issue(self, valid_issue_body):
        fake_pr_url = (
            "https://github.com/European-OpenSource/awesome-european-opensource/pull/42"
        )
        env = {**MOCK_ENV, "ISSUE_BODY": valid_issue_body}

        with (
            patch.dict(os.environ, env, clear=True),
            patch("issue_to_pr.create_pr", return_value=fake_pr_url) as mock_pr,
            patch("issue_to_pr.post_comment"),
        ):
            main()

        _, _, issue_number, repo, _ = mock_pr.call_args[0]
        assert issue_number == ISSUE_NUMBER
        assert repo == "European-OpenSource/awesome-european-opensource"
