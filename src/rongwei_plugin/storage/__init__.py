"""Local-only encrypted customer data storage."""

from .local_vault import LocalVault, VaultError

__all__ = ["LocalVault", "VaultError"]
