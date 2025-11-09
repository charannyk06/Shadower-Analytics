"""Tests for input validation security functions."""

import pytest
from fastapi import HTTPException
from src.utils.validators import (
    validate_agent_id,
    validate_workspace_id,
    validate_user_id,
    sanitize_html_content,
    validate_sql_identifier,
)


class TestAgentIDValidation:
    """Test agent ID validation."""

    def test_valid_agent_ids(self):
        """Test that valid agent IDs pass validation."""
        valid_ids = [
            "agent_123",
            "my-agent",
            "agent_abc_123",
            "ABC-123-XYZ",
            "a",  # Single character
            "a" * 255,  # Max length
        ]
        for agent_id in valid_ids:
            assert validate_agent_id(agent_id) == agent_id

    def test_path_traversal_blocked(self):
        """Test that path traversal attacks are blocked."""
        malicious_ids = [
            "../../etc/passwd",
            "../config",
            "agent/../../etc/passwd",
            "agent\\..\\..\\windows\\system32",
            "..",
        ]
        for agent_id in malicious_ids:
            with pytest.raises(HTTPException) as exc_info:
                validate_agent_id(agent_id)
            assert exc_info.value.status_code == 400
            assert "path traversal" in exc_info.value.detail.lower()

    def test_invalid_characters_blocked(self):
        """Test that invalid characters are blocked."""
        invalid_ids = [
            "agent@123",
            "agent#123",
            "agent$123",
            "agent 123",  # Space
            "agent\n123",  # Newline
            "agent<script>",
            "agent'OR'1'='1",
        ]
        for agent_id in invalid_ids:
            with pytest.raises(HTTPException) as exc_info:
                validate_agent_id(agent_id)
            assert exc_info.value.status_code == 400

    def test_empty_string_rejected(self):
        """Test that empty strings are rejected."""
        with pytest.raises(HTTPException) as exc_info:
            validate_agent_id("")
        assert exc_info.value.status_code == 400

    def test_none_rejected(self):
        """Test that None values are rejected."""
        with pytest.raises(HTTPException) as exc_info:
            validate_agent_id(None)
        assert exc_info.value.status_code == 400

    def test_too_long_rejected(self):
        """Test that overly long IDs are rejected."""
        long_id = "a" * 256  # Over 255 char limit
        with pytest.raises(HTTPException) as exc_info:
            validate_agent_id(long_id)
        assert exc_info.value.status_code == 400


class TestWorkspaceIDValidation:
    """Test workspace ID validation."""

    def test_valid_workspace_ids(self):
        """Test that valid workspace IDs pass validation."""
        valid_ids = [
            "workspace_123",
            "my-workspace",
            "WS-ABC-123",
            "w",  # Single character
            "a" * 64,  # Max length
        ]
        for workspace_id in valid_ids:
            assert validate_workspace_id(workspace_id) == workspace_id

    def test_path_traversal_blocked(self):
        """Test that path traversal attacks are blocked."""
        malicious_ids = [
            "../../etc/passwd",
            "../config",
            "workspace/../../etc/passwd",
        ]
        for workspace_id in malicious_ids:
            with pytest.raises(HTTPException) as exc_info:
                validate_workspace_id(workspace_id)
            assert exc_info.value.status_code == 400

    def test_too_long_rejected(self):
        """Test that overly long IDs are rejected (max 64 chars)."""
        long_id = "a" * 65
        with pytest.raises(HTTPException) as exc_info:
            validate_workspace_id(long_id)
        assert exc_info.value.status_code == 400


class TestUserIDValidation:
    """Test user ID validation."""

    def test_valid_user_ids(self):
        """Test that valid user IDs pass validation."""
        valid_ids = [
            "user_123",
            "john-doe",
            "USER-ABC-123",
            "u",  # Single character
            "a" * 255,  # Max length
        ]
        for user_id in valid_ids:
            assert validate_user_id(user_id) == user_id

    def test_path_traversal_blocked(self):
        """Test that path traversal attacks are blocked."""
        malicious_ids = [
            "../../etc/passwd",
            "../admin",
        ]
        for user_id in malicious_ids:
            with pytest.raises(HTTPException) as exc_info:
                validate_user_id(user_id)
            assert exc_info.value.status_code == 400


class TestXSSSanitization:
    """Test XSS sanitization."""

    def test_script_tags_escaped(self):
        """Test that script tags are properly escaped."""
        malicious_inputs = [
            ("<script>alert('XSS')</script>", "&lt;script&gt;alert('XSS')&lt;/script&gt;"),
            ("<img src=x onerror=alert('XSS')>", "&lt;img src=x onerror=alert('XSS')&gt;"),
            ("<svg onload=alert('XSS')>", "&lt;svg onload=alert('XSS')&gt;"),
        ]
        for malicious, expected in malicious_inputs:
            sanitized = sanitize_html_content(malicious)
            assert sanitized == expected
            assert "<script>" not in sanitized
            assert "<img" not in sanitized
            assert "<svg" not in sanitized

    def test_html_entities_escaped(self):
        """Test that HTML entities are properly escaped."""
        test_cases = [
            ("Test & More", "Test &amp; More"),
            ("<div>Content</div>", "&lt;div&gt;Content&lt;/div&gt;"),
            ('Say "Hello"', "Say &quot;Hello&quot;"),
            ("It's a test", "It&#x27;s a test"),
        ]
        for input_str, expected in test_cases:
            sanitized = sanitize_html_content(input_str)
            assert sanitized == expected

    def test_normal_text_unchanged(self):
        """Test that normal text passes through unchanged."""
        normal_texts = [
            "Hello World",
            "This is a normal message",
            "User123 logged in",
        ]
        for text in normal_texts:
            assert sanitize_html_content(text) == text

    def test_too_long_content_rejected(self):
        """Test that overly long content is rejected."""
        long_content = "a" * 10001  # Over 10000 char limit
        with pytest.raises(HTTPException) as exc_info:
            sanitize_html_content(long_content)
        assert exc_info.value.status_code == 400
        assert "too long" in exc_info.value.detail.lower()

    def test_custom_max_length(self):
        """Test that custom max length works."""
        content = "a" * 100
        # Should pass with higher limit
        assert sanitize_html_content(content, max_length=200) == content
        # Should fail with lower limit
        with pytest.raises(HTTPException):
            sanitize_html_content(content, max_length=50)


class TestSQLIdentifierValidation:
    """Test SQL identifier validation."""

    def test_valid_identifiers(self):
        """Test that valid SQL identifiers pass."""
        valid_identifiers = [
            "table_name",
            "column_name",
            "_private",
            "CamelCase",
        ]
        for identifier in valid_identifiers:
            assert validate_sql_identifier(identifier) == identifier

    def test_sql_injection_blocked(self):
        """Test that SQL injection attempts are blocked."""
        malicious_identifiers = [
            "table; DROP TABLE users--",
            "column' OR '1'='1",
            "name--",
        ]
        for identifier in malicious_identifiers:
            with pytest.raises(HTTPException) as exc_info:
                validate_sql_identifier(identifier)
            assert exc_info.value.status_code == 400

    def test_sql_keywords_blocked(self):
        """Test that SQL keywords are blocked."""
        keywords = [
            "select",
            "SELECT",
            "insert",
            "update",
            "delete",
            "drop",
            "create",
            "alter",
            "truncate",
            "exec",
            "execute",
            "union",
            "where",
        ]
        for keyword in keywords:
            with pytest.raises(HTTPException) as exc_info:
                validate_sql_identifier(keyword)
            assert exc_info.value.status_code == 400
            assert "keyword" in exc_info.value.detail.lower()

    def test_invalid_start_character_blocked(self):
        """Test that identifiers starting with numbers are blocked."""
        with pytest.raises(HTTPException):
            validate_sql_identifier("123table")
