"""
tools/credential_manager.py
Stores portal login credentials encrypted at rest using Fernet symmetric encryption.
Credentials are never logged or sent to the LLM.
"""

import json
import os
from pathlib import Path
from cryptography.fernet import Fernet
from pydantic import BaseModel
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


class PortalCredential(BaseModel):
    portal: str
    username: str
    password: str
    extra: dict = {}   # e.g. {"otp_secret": "..."} for TOTP portals


class CredentialManager:
    """Encrypted JSON credential vault. One file, Fernet-encrypted."""

    VAULT_PATH = Path("./data/credentials.vault")

    def __init__(self):
        key = os.getenv("CREDENTIAL_ENCRYPTION_KEY")
        if not key:
            raise ValueError(
                "Set CREDENTIAL_ENCRYPTION_KEY in .env\n"
                "Generate one: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
            )
        self._fernet = Fernet(key.encode())
        self.VAULT_PATH.parent.mkdir(parents=True, exist_ok=True)

    def _load(self) -> dict:
        if not self.VAULT_PATH.exists():
            return {}
        data = self._fernet.decrypt(self.VAULT_PATH.read_bytes())
        return json.loads(data)

    def _save(self, vault: dict):
        self.VAULT_PATH.write_bytes(
            self._fernet.encrypt(json.dumps(vault).encode())
        )

    def set(self, portal: str, username: str, password: str, **extra):
        vault = self._load()
        vault[portal.lower()] = {
            "username": username,
            "password": password,
            "extra": extra,
        }
        self._save(vault)
        print(f"✓ Credentials saved for {portal}")

    def get(self, portal: str) -> Optional[PortalCredential]:
        vault = self._load()
        data = vault.get(portal.lower())
        if not data:
            return None
        return PortalCredential(portal=portal, **data)

    def list_portals(self) -> list[str]:
        return list(self._load().keys())

    def remove(self, portal: str):
        vault = self._load()
        vault.pop(portal.lower(), None)
        self._save(vault)


# CLI helper – run: python -m tools.credential_manager
if __name__ == "__main__":
    import getpass
    mgr = CredentialManager()
    print("Job Agent – Credential Setup")
    print("=" * 40)
    portals = ["linkedin", "indeed", "naukri", "cutshort", "instahire", "foundit", "glassdoor"]
    for p in portals:
        ans = input(f"Add credentials for {p}? (y/N): ").strip().lower()
        if ans == "y":
            user = input("  Email/Username: ").strip()
            pwd = getpass.getpass("  Password: ")
            mgr.set(p, user, pwd)
    print("\nStored portals:", mgr.list_portals())