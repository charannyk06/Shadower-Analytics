"""Input validation and sanitization for security."""

import re
import html
import os
from typing import Any, Optional, List, Set
from pydantic import BaseModel, validator, field_validator
import logging

logger = logging.getLogger(__name__)


class SecureInputValidator:
    """
    Security-focused input validator and sanitizer.

    Protects against SQL injection, XSS, and other injection attacks.
    """

    # SQL injection prevention patterns
    SQL_BLACKLIST = [
        "SELECT",
        "INSERT",
        "UPDATE",
        "DELETE",
        "DROP",
        "CREATE",
        "ALTER",
        "EXEC",
        "EXECUTE",
        "UNION",
        "DECLARE",
        "CAST",
        "CONVERT",
        "SCRIPT",
        "--",
        "/*",
        "*/",
        ";--",
        "xp_",
        "sp_",
    ]

    # XSS prevention
    ALLOWED_HTML_TAGS: Set[str] = {"b", "i", "u", "strong", "em", "p", "br", "span"}
    ALLOWED_HTML_ATTRIBUTES: Set[str] = set()

    # Allowed file extensions for uploads
    ALLOWED_FILE_EXTENSIONS = {".csv", ".json", ".xlsx", ".pdf", ".txt"}

    # Allowed MIME types for uploads
    ALLOWED_MIME_TYPES = {
        "text/csv",
        "application/json",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/pdf",
        "text/plain",
    }

    # File size limits (in bytes)
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

    @staticmethod
    def sanitize_sql_input(value: str) -> str:
        """
        Sanitize input to prevent SQL injection.

        Note: This is a defense-in-depth measure. Always use parameterized queries.

        Args:
            value: Input string to sanitize

        Returns:
            Sanitized string

        Raises:
            ValueError: If dangerous SQL keywords detected
        """
        if not value:
            return value

        # Check for SQL keywords
        upper_value = value.upper()
        for keyword in SecureInputValidator.SQL_BLACKLIST:
            if keyword in upper_value:
                logger.warning(f"Dangerous SQL keyword detected: {keyword}")
                raise ValueError(
                    f"Input contains potentially dangerous SQL keyword: {keyword}"
                )

        # Remove special SQL characters (defense in depth)
        # Allow only alphanumeric, spaces, and safe punctuation
        sanitized = re.sub(r"[^\w\s\-\.\@]", "", value)

        return sanitized

    @staticmethod
    def sanitize_html_input(value: str, strip_tags: bool = True) -> str:
        """
        Sanitize HTML input to prevent XSS attacks.

        Args:
            value: Input string potentially containing HTML
            strip_tags: If True, strip all HTML tags. If False, allow safe tags.

        Returns:
            Sanitized string
        """
        if not value:
            return value

        if strip_tags:
            # Strip all HTML tags
            cleaned = re.sub(r"<[^>]*>", "", value)
        else:
            # Allow only safe HTML tags (would need bleach library for full implementation)
            # For now, escape all HTML
            cleaned = value

        # Escape HTML entities
        cleaned = html.escape(cleaned)

        return cleaned

    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """
        Sanitize filename to prevent directory traversal attacks.

        Args:
            filename: Original filename

        Returns:
            Sanitized filename
        """
        if not filename:
            return filename

        # Remove path separators
        filename = os.path.basename(filename)

        # Remove dangerous characters
        filename = re.sub(r'[^\w\s\-\.]', '', filename)

        # Prevent hidden files
        if filename.startswith("."):
            filename = "_" + filename[1:]

        # Limit length
        if len(filename) > 255:
            name, ext = os.path.splitext(filename)
            filename = name[:250] + ext

        return filename

    @staticmethod
    def validate_file_upload(
        filename: str,
        content_type: str,
        file_size: int,
        allowed_extensions: Optional[Set[str]] = None,
        allowed_mime_types: Optional[Set[str]] = None,
        max_size: Optional[int] = None,
    ) -> bool:
        """
        Validate uploaded file for security.

        Args:
            filename: Name of the uploaded file
            content_type: MIME type of the file
            file_size: Size of file in bytes
            allowed_extensions: Set of allowed file extensions
            allowed_mime_types: Set of allowed MIME types
            max_size: Maximum file size in bytes

        Returns:
            True if file is valid

        Raises:
            ValueError: If file validation fails
        """
        # Use defaults if not provided
        allowed_extensions = allowed_extensions or SecureInputValidator.ALLOWED_FILE_EXTENSIONS
        allowed_mime_types = allowed_mime_types or SecureInputValidator.ALLOWED_MIME_TYPES
        max_size = max_size or SecureInputValidator.MAX_FILE_SIZE

        # Check file size
        if file_size > max_size:
            raise ValueError(
                f"File size {file_size} bytes exceeds maximum {max_size} bytes"
            )

        # Check file extension
        file_ext = os.path.splitext(filename)[1].lower()
        if file_ext not in allowed_extensions:
            raise ValueError(
                f"File extension {file_ext} not allowed. Allowed: {allowed_extensions}"
            )

        # Check MIME type
        if content_type not in allowed_mime_types:
            raise ValueError(
                f"MIME type {content_type} not allowed. Allowed: {allowed_mime_types}"
            )

        return True

    @staticmethod
    def sanitize_search_query(query: str, max_length: int = 200) -> str:
        """
        Sanitize search query input.

        Args:
            query: Search query string
            max_length: Maximum allowed length

        Returns:
            Sanitized query string
        """
        if not query:
            return query

        # Limit length
        query = query[:max_length]

        # Remove special characters that could be used for injection
        query = re.sub(r'[<>"\';\\]', '', query)

        # Trim whitespace
        query = query.strip()

        return query

    @staticmethod
    def validate_email(email: str) -> bool:
        """
        Validate email address format.

        Args:
            email: Email address to validate

        Returns:
            True if valid email format

        Raises:
            ValueError: If email is invalid
        """
        if not email:
            raise ValueError("Email address is required")

        # Basic email regex
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(pattern, email):
            raise ValueError("Invalid email address format")

        # Check length
        if len(email) > 254:  # RFC 5321
            raise ValueError("Email address too long")

        return True

    @staticmethod
    def validate_url(url: str, allowed_schemes: Optional[List[str]] = None) -> bool:
        """
        Validate URL format and scheme.

        Args:
            url: URL to validate
            allowed_schemes: List of allowed URL schemes (default: http, https)

        Returns:
            True if valid URL

        Raises:
            ValueError: If URL is invalid
        """
        if not url:
            raise ValueError("URL is required")

        allowed_schemes = allowed_schemes or ["http", "https"]

        # Basic URL regex
        pattern = r'^(https?|ftp)://[^\s/$.?#].[^\s]*$'
        if not re.match(pattern, url):
            raise ValueError("Invalid URL format")

        # Check scheme
        scheme = url.split("://")[0].lower()
        if scheme not in allowed_schemes:
            raise ValueError(
                f"URL scheme {scheme} not allowed. Allowed: {allowed_schemes}"
            )

        # Check for common dangerous patterns
        dangerous_patterns = ["javascript:", "data:", "vbscript:"]
        url_lower = url.lower()
        for pattern in dangerous_patterns:
            if pattern in url_lower:
                raise ValueError(f"Dangerous URL pattern detected: {pattern}")

        return True

    @staticmethod
    def validate_workspace_id(workspace_id: str) -> bool:
        """
        Validate workspace ID format.

        Args:
            workspace_id: Workspace ID to validate

        Returns:
            True if valid

        Raises:
            ValueError: If workspace ID is invalid
        """
        if not workspace_id:
            raise ValueError("Workspace ID is required")

        # Expected format: ws_[alphanumeric]{10,}
        pattern = r'^ws_[a-zA-Z0-9]{10,}$'
        if not re.match(pattern, workspace_id):
            raise ValueError(
                "Invalid workspace ID format. Expected: ws_[alphanumeric]{10,}"
            )

        return True

    @staticmethod
    def validate_uuid(uuid_str: str) -> bool:
        """
        Validate UUID format.

        Args:
            uuid_str: UUID string to validate

        Returns:
            True if valid UUID

        Raises:
            ValueError: If UUID is invalid
        """
        if not uuid_str:
            raise ValueError("UUID is required")

        # UUID v4 pattern
        pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'
        if not re.match(pattern, uuid_str.lower()):
            raise ValueError("Invalid UUID format")

        return True


# Pydantic validators for common use cases
class SecureStringField(str):
    """String field with automatic sanitization."""

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not isinstance(v, str):
            raise ValueError("Must be a string")
        # Sanitize HTML by default
        return SecureInputValidator.sanitize_html_input(v)


class EmailField(str):
    """Email field with validation."""

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not isinstance(v, str):
            raise ValueError("Must be a string")
        SecureInputValidator.validate_email(v)
        return v.lower()


class URLField(str):
    """URL field with validation."""

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not isinstance(v, str):
            raise ValueError("Must be a string")
        SecureInputValidator.validate_url(v)
        return v
