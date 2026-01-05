"""Integration tests for CLI key management commands."""

import os

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from typer.testing import CliRunner

# Set test environment before importing app modules
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

from app.auth.schemas import APIKeyCreate
from app.auth.service import APIKeyService
from app.cli.keys import app as keys_app

runner = CliRunner()


class TestKeysCreateCommand:
    """Tests for the keys create command."""

    def test_keys_create_requires_name(self) -> None:
        """Test that create command requires --name."""
        result = runner.invoke(keys_app, ["create", "--client-id", "test-client"])

        assert result.exit_code != 0
        # Check either stdout or output (Typer may use different outputs)
        output = (
            result.stdout or str(result.output) if hasattr(result, "output") else ""
        )
        assert "Missing option" in output or "--name" in output or result.exit_code == 2

    def test_keys_create_requires_client_id(self) -> None:
        """Test that create command requires --client-id."""
        result = runner.invoke(keys_app, ["create", "--name", "Test Key"])

        assert result.exit_code != 0
        output = (
            result.stdout or str(result.output) if hasattr(result, "output") else ""
        )
        assert (
            "Missing option" in output
            or "--client-id" in output
            or result.exit_code == 2
        )


class TestKeysListCommand:
    """Tests for the keys list command."""

    def test_keys_list_help(self) -> None:
        """Test keys list command help output."""
        result = runner.invoke(keys_app, ["list", "--help"])

        assert result.exit_code == 0
        output = result.stdout or ""
        assert "List all API keys" in output or "list" in output.lower()


class TestKeysRevokeCommand:
    """Tests for the keys revoke command."""

    def test_keys_revoke_requires_key_prefix(self) -> None:
        """Test that revoke command requires key prefix argument."""
        result = runner.invoke(keys_app, ["revoke"])

        # Just check it fails - Typer exit code 2 means missing argument
        assert result.exit_code != 0


class TestKeysInfoCommand:
    """Tests for the keys info command."""

    def test_keys_info_requires_key_prefix(self) -> None:
        """Test that info command requires key prefix argument."""
        result = runner.invoke(keys_app, ["info"])

        # Just check it fails - Typer exit code 2 means missing argument
        assert result.exit_code != 0


class TestAPIKeyService:
    """Tests for APIKeyService used by CLI commands."""

    def test_key_generation(self) -> None:
        """Test API key generation produces valid keys."""
        key = APIKeyService.generate_key()

        assert key.startswith("sk_")
        assert len(key) >= 32

    def test_key_prefix_extraction(self) -> None:
        """Test key prefix extraction."""
        key = "sk_abcdefghijklmnopqrstuvwxyz123456"
        prefix = APIKeyService.get_key_prefix(key)

        assert prefix == "sk_abcdefghi"
        assert len(prefix) == 12

    def test_key_hashing_and_verification(self) -> None:
        """Test key hashing and verification."""
        key = APIKeyService.generate_key()
        key_hash = APIKeyService.hash_key(key)

        assert APIKeyService.verify_key(key, key_hash)
        assert not APIKeyService.verify_key("wrong_key", key_hash)

    @pytest.mark.asyncio
    async def test_create_key(self, db_session: AsyncSession) -> None:
        """Test creating a new API key."""
        data = APIKeyCreate(name="Integration Test Key", client_id="integration-client")

        result = await APIKeyService.create_key(db_session, data)

        assert result.name == "Integration Test Key"
        assert result.client_id == "integration-client"
        assert result.key.startswith("sk_")
        assert result.key_prefix == result.key[:12]

    @pytest.mark.asyncio
    async def test_validate_key(self, db_session: AsyncSession) -> None:
        """Test validating an API key."""
        # Create a key
        data = APIKeyCreate(name="Validate Test Key", client_id="validate-client")
        created = await APIKeyService.create_key(db_session, data)
        await db_session.commit()

        # Validate the key
        validated = await APIKeyService.validate_key(db_session, created.key)

        assert validated is not None
        assert str(validated.id) == created.id

    @pytest.mark.asyncio
    async def test_validate_invalid_key(self, db_session: AsyncSession) -> None:
        """Test validating an invalid API key."""
        result = await APIKeyService.validate_key(db_session, "sk_invalid_key_12345")

        assert result is None

    @pytest.mark.asyncio
    async def test_revoke_key(self, db_session: AsyncSession) -> None:
        """Test revoking an API key."""
        # Create a key
        data = APIKeyCreate(name="Revoke Test Key", client_id="revoke-client")
        created = await APIKeyService.create_key(db_session, data)
        await db_session.commit()

        # Revoke the key
        revoked = await APIKeyService.revoke_key(db_session, created.id)
        await db_session.commit()

        assert revoked is True

        # Verify the key is no longer valid
        validated = await APIKeyService.validate_key(db_session, created.key)
        assert validated is None

    @pytest.mark.asyncio
    async def test_list_keys(self, db_session: AsyncSession) -> None:
        """Test listing API keys."""
        # Create some keys
        for i in range(3):
            data = APIKeyCreate(name=f"List Test Key {i}", client_id=f"list-client-{i}")
            await APIKeyService.create_key(db_session, data)
        await db_session.commit()

        # List keys
        keys, total = await APIKeyService.list_keys(db_session)

        assert total >= 3
        assert len(keys) >= 3
