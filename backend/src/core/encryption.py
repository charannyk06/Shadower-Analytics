"""Data encryption utilities for securing sensitive information."""

import os
import base64
from typing import Optional
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
from cryptography.hazmat.backends import default_backend
from sqlalchemy import TypeDecorator, String
import logging

logger = logging.getLogger(__name__)


class DataEncryption:
    """
    Encryption handler for sensitive data at rest.

    Uses Fernet (symmetric encryption) with key derivation.
    """

    def __init__(self):
        """Initialize encryption with master key from environment."""
        self.master_key = os.getenv("MASTER_ENCRYPTION_KEY")
        self.salt = os.getenv("ENCRYPTION_SALT", "default-salt-change-me").encode()

        if not self.master_key:
            logger.warning(
                "MASTER_ENCRYPTION_KEY not set. Using default (insecure for production)"
            )
            self.master_key = "default-key-change-in-production"

    def get_encryption_key(self, context: str = "") -> bytes:
        """
        Derive encryption key from master key using PBKDF2.

        Args:
            context: Additional context for key derivation (e.g., field name)

        Returns:
            Derived encryption key suitable for Fernet
        """
        # Combine salt with context for key derivation
        context_salt = self.salt + context.encode()

        # Use PBKDF2 for key derivation
        kdf = PBKDF2(
            algorithm=hashes.SHA256(),
            length=32,
            salt=context_salt,
            iterations=100000,
            backend=default_backend(),
        )

        # Derive key and encode for Fernet
        key = base64.urlsafe_b64encode(kdf.derive(self.master_key.encode()))
        return key

    def encrypt_field(self, data: str, field_name: str = "") -> str:
        """
        Encrypt a sensitive field.

        Args:
            data: The plaintext data to encrypt
            field_name: Field name for context-specific encryption

        Returns:
            Encrypted data as base64 string
        """
        if not data:
            return data

        try:
            key = self.get_encryption_key(field_name)
            f = Fernet(key)
            encrypted = f.encrypt(data.encode())
            return encrypted.decode()
        except Exception as e:
            logger.error(f"Encryption failed for field {field_name}: {e}")
            raise

    def decrypt_field(self, encrypted_data: str, field_name: str = "") -> str:
        """
        Decrypt a sensitive field.

        Args:
            encrypted_data: The encrypted data to decrypt
            field_name: Field name for context-specific decryption

        Returns:
            Decrypted plaintext data
        """
        if not encrypted_data:
            return encrypted_data

        try:
            key = self.get_encryption_key(field_name)
            f = Fernet(key)
            decrypted = f.decrypt(encrypted_data.encode())
            return decrypted.decode()
        except Exception as e:
            logger.error(f"Decryption failed for field {field_name}: {e}")
            raise

    def encrypt_bytes(self, data: bytes, context: str = "") -> bytes:
        """
        Encrypt raw bytes.

        Args:
            data: The raw bytes to encrypt
            context: Context for key derivation

        Returns:
            Encrypted bytes
        """
        if not data:
            return data

        key = self.get_encryption_key(context)
        f = Fernet(key)
        return f.encrypt(data)

    def decrypt_bytes(self, encrypted_data: bytes, context: str = "") -> bytes:
        """
        Decrypt raw bytes.

        Args:
            encrypted_data: The encrypted bytes
            context: Context for key derivation

        Returns:
            Decrypted bytes
        """
        if not encrypted_data:
            return encrypted_data

        key = self.get_encryption_key(context)
        f = Fernet(key)
        return f.decrypt(encrypted_data)


# Global encryption instance
_encryptor: Optional[DataEncryption] = None


def get_encryptor() -> DataEncryption:
    """Get or create global encryption instance."""
    global _encryptor
    if _encryptor is None:
        _encryptor = DataEncryption()
    return _encryptor


class EncryptedString(TypeDecorator):
    """
    SQLAlchemy type decorator for automatic field encryption.

    Usage:
        class User(Base):
            ssn = Column(EncryptedString('ssn', 255))
            api_key = Column(EncryptedString('api_key', 255))
    """

    impl = String
    cache_ok = True

    def __init__(self, encryption_context: str = "", *args, **kwargs):
        """
        Initialize encrypted string column.

        Args:
            encryption_context: Context for encryption (e.g., field name)
            *args, **kwargs: Arguments passed to String type
        """
        self.encryption_context = encryption_context
        self.encryptor = get_encryptor()
        super().__init__(*args, **kwargs)

    def process_bind_param(self, value, dialect):
        """Encrypt value before storing in database."""
        if value is not None:
            return self.encryptor.encrypt_field(value, self.encryption_context)
        return value

    def process_result_value(self, value, dialect):
        """Decrypt value when reading from database."""
        if value is not None:
            return self.encryptor.decrypt_field(value, self.encryption_context)
        return value


class EncryptedJSON(TypeDecorator):
    """
    SQLAlchemy type decorator for automatic JSON field encryption.

    Usage:
        class Config(Base):
            sensitive_config = Column(EncryptedJSON('config'))
    """

    impl = String
    cache_ok = True

    def __init__(self, encryption_context: str = "", *args, **kwargs):
        """
        Initialize encrypted JSON column.

        Args:
            encryption_context: Context for encryption (e.g., field name)
            *args, **kwargs: Arguments passed to String type
        """
        self.encryption_context = encryption_context
        self.encryptor = get_encryptor()
        super().__init__(*args, **kwargs)

    def process_bind_param(self, value, dialect):
        """Encrypt JSON value before storing in database."""
        if value is not None:
            import json

            json_str = json.dumps(value)
            return self.encryptor.encrypt_field(json_str, self.encryption_context)
        return value

    def process_result_value(self, value, dialect):
        """Decrypt and parse JSON value when reading from database."""
        if value is not None:
            import json

            decrypted = self.encryptor.decrypt_field(value, self.encryption_context)
            return json.loads(decrypted)
        return value


def generate_encryption_key() -> str:
    """
    Generate a new Fernet encryption key.

    Returns:
        Base64-encoded encryption key
    """
    return Fernet.generate_key().decode()


def generate_master_key() -> str:
    """
    Generate a new master encryption key.

    Returns:
        Random string suitable for master key
    """
    import secrets

    return secrets.token_urlsafe(32)
