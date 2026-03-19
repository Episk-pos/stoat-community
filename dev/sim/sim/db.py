"""MongoDB helpers for managing simulated user accounts."""

from __future__ import annotations

from argon2 import PasswordHasher
from motor.motor_asyncio import AsyncIOMotorClient

from .models import SimUser

_ph = PasswordHasher()

# Sim users use a recognizable email pattern
SIM_EMAIL_DOMAIN = "sim.stoat.local"
SIM_PASSWORD = "SimUser#2026!"


def _sim_email(username: str) -> str:
    return f"{username}@{SIM_EMAIL_DOMAIN}"


class SimDB:
    """Manage sim accounts directly in MongoDB."""

    def __init__(self, mongo_url: str = "mongodb://mongodb:27017", db_name: str = "revolt"):
        self._client = AsyncIOMotorClient(mongo_url)
        self._db = self._client[db_name]

    async def close(self):
        self._client.close()

    async def create_account(self, user_id: str, username: str, display_name: str) -> SimUser:
        """Insert a pre-verified account + user doc into MongoDB.

        Returns a SimUser (without token — call login separately).
        """
        email = _sim_email(username)
        pw_hash = _ph.hash(SIM_PASSWORD)

        # Account doc (authifier)
        existing = await self._db.accounts.find_one({"_id": user_id})
        if not existing:
            await self._db.accounts.insert_one({
                "_id": user_id,
                "email": email,
                "email_normalised": email.lower(),
                "password": pw_hash,
                "disabled": False,
                "verification": {"status": "Verified"},
                "lockout": None,
                "deletion": None,
                "mfa": {},
                "password_reset": None,
            })

        return SimUser(
            user_id=user_id,
            username=username,
            email=email,
            display_name=display_name,
        )

    async def list_sim_accounts(self) -> list[dict]:
        """Find all accounts with sim email domain."""
        cursor = self._db.accounts.find(
            {"email": {"$regex": f"@{SIM_EMAIL_DOMAIN}$"}},
            {"_id": 1, "email": 1},
        )
        return await cursor.to_list(length=100)

    async def delete_account(self, user_id: str):
        """Remove a sim account and its user doc."""
        await self._db.accounts.delete_one({"_id": user_id})
        await self._db.users.delete_one({"_id": user_id})

    async def delete_all_sim_accounts(self):
        """Remove all sim accounts."""
        accounts = await self.list_sim_accounts()
        for acc in accounts:
            await self.delete_account(acc["_id"])
