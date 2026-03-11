#!/usr/bin/env python3
"""
Seed script for the Stoat dev environment.

Creates test users (pre-verified in MongoDB), then uses the REST API to:
- Complete onboarding (set usernames)
- Create servers and channels
- Send sample messages
- Create cross-server invite links

Designed to run as a Kubernetes Job or locally against the dev stack.
"""

import argparse
import json
import os
import sys
import time
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

DELTA_URL = os.environ.get("DELTA_URL", "http://localhost:14702")
MONGO_URI = os.environ.get("MONGO_URI", "mongodb://mongodb.stoat.svc:27017")
DB_NAME = "revolt"

# Deterministic IDs (26-char alphanumeric, matching Revolt's ULID format)
# We use fixed IDs so the seed is idempotent.
TEST_PASSWORD = "StoatDev#2026!"

USER_SPECS = [
    {
        "id": "01KKEJRMR73ABFWKAH17JT6SVW",
        "email": "alice@dev.stoat.local",
        "username": "alice",
        "display_name": "Alice",
        "password": TEST_PASSWORD,
    },
    {
        "id": "01KKEJRMR77B769PVC3EGB7SFR",
        "email": "bob@dev.stoat.local",
        "username": "bob",
        "display_name": "Bob",
        "password": TEST_PASSWORD,
    },
    {
        "id": "01KKEJRMR78VEK67QFZPAZ56CD",
        "email": "carol@dev.stoat.local",
        "username": "carol",
        "display_name": "Carol",
        "password": TEST_PASSWORD,
    },
]

SERVER_SPECS = [
    {
        "name": "Stoat Dev",
        "description": "General development discussion",
        "channels": ["general", "random", "bugs"],
    },
    {
        "name": "Design Lab",
        "description": "UI/UX design work",
        "channels": ["feedback", "mockups"],
    },
]

SAMPLE_MESSAGES = [
    ("alice", "general", "Hey everyone! Welcome to the dev server."),
    ("bob", "general", "Thanks Alice! Glad to be here."),
    ("carol", "general", "Hi all — just joined. Excited to test things out."),
    ("alice", "random", "Anyone tried the new sidebar yet?"),
    ("bob", "bugs", "Found an issue with the message input on mobile."),
    ("carol", "feedback", "The new color scheme looks great!"),
    ("alice", "feedback", "Agreed, much easier on the eyes."),
    ("bob", "mockups", "Uploading the new nav wireframes shortly."),
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def api(method, path, token=None, body=None):
    """Make an HTTP request to the Delta API."""
    url = f"{DELTA_URL}{path}"
    headers = {"Content-Type": "application/json"}
    if token:
        headers["x-session-token"] = token
    data = json.dumps(body).encode() if body else None
    req = Request(url, data=data, headers=headers, method=method)
    try:
        with urlopen(req) as resp:
            raw = resp.read()
            return json.loads(raw) if raw else {}
    except HTTPError as e:
        raw = e.read().decode(errors="replace")
        # Treat "already exists" style errors as idempotent success
        if e.code == 409:
            return None
        print(f"  API error {e.code} {method} {path}: {raw}", file=sys.stderr)
        raise


def wait_for_api(timeout=120):
    """Block until the Delta API is reachable."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            api("GET", "/")
            return
        except (URLError, OSError):
            time.sleep(2)
    print("ERROR: Delta API not reachable after timeout", file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------------------
# MongoDB seeding (accounts + users)
# ---------------------------------------------------------------------------

def seed_mongo_accounts():
    """Insert pre-verified accounts and user documents directly into MongoDB."""
    try:
        from pymongo import MongoClient
    except ImportError:
        print("ERROR: pymongo is required. Install with: pip install pymongo", file=sys.stderr)
        sys.exit(1)

    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]

    for spec in USER_SPECS:
        # --- Account document (authifier) ---
        existing = db.accounts.find_one({"_id": spec["id"]})
        if existing:
            print(f"  account {spec['username']} already exists, skipping")
            continue

        # Hash password with argon2 (matching authifier's format)
        try:
            from argon2 import PasswordHasher
            ph = PasswordHasher()
            pw_hash = ph.hash(spec["password"])
        except ImportError:
            print("ERROR: argon2-cffi is required. Install with: pip install argon2-cffi", file=sys.stderr)
            sys.exit(1)

        account_doc = {
            "_id": spec["id"],
            "email": spec["email"],
            "email_normalised": spec["email"].lower(),
            "password": pw_hash,
            "disabled": False,
            "verification": {"status": "Verified"},
            "lockout": None,
            "deletion": None,
            "mfa": {},
            "password_reset": None,
        }
        db.accounts.insert_one(account_doc)
        print(f"  created account: {spec['username']} ({spec['email']})")

    client.close()


# ---------------------------------------------------------------------------
# API seeding (login, servers, channels, messages)
# ---------------------------------------------------------------------------

def login_user(spec):
    """Login a user and return the session token."""
    resp = api("POST", "/auth/session/login", body={
        "email": spec["email"],
        "password": spec["password"],
    })
    return resp["token"]


def seed_servers_and_messages():
    """Create servers, channels, and messages via the API."""
    try:
        from pymongo import MongoClient
    except ImportError:
        print("ERROR: pymongo required", file=sys.stderr)
        sys.exit(1)

    mongo = MongoClient(MONGO_URI)
    db = mongo[DB_NAME]

    # Login all users and complete onboarding
    tokens = {}
    for spec in USER_SPECS:
        print(f"  logging in as {spec['username']}...")
        tokens[spec["username"]] = login_user(spec)

        # Complete onboarding (set username) if needed
        hello = api("GET", "/onboard/hello", token=tokens[spec["username"]])
        if hello and hello.get("onboarding"):
            print(f"    completing onboarding for {spec['username']}...")
            api("POST", "/onboard/complete", token=tokens[spec["username"]], body={
                "username": spec["username"],
            })

        # Set display name
        api("PATCH", "/users/@me", token=tokens[spec["username"]], body={
            "display_name": spec["display_name"],
        })

    alice_token = tokens["alice"]
    alice_id = USER_SPECS[0]["id"]

    # Track created servers and channels
    servers = {}
    channels = {}  # channel name -> channel id

    for server_spec in SERVER_SPECS:
        # Check if server already exists (by name, owned by alice)
        existing = db.servers.find_one({"name": server_spec["name"], "owner": alice_id})
        if existing:
            print(f"  server '{server_spec['name']}' already exists, skipping")
            servers[server_spec["name"]] = existing["_id"]
            # Load existing channels
            for ch in db.channels.find({"server": existing["_id"]}):
                channels[ch["name"].lower()] = ch["_id"]
            continue

        print(f"  creating server: {server_spec['name']}...")
        resp = api("POST", "/servers/create", token=alice_token, body={
            "name": server_spec["name"],
            "description": server_spec.get("description", ""),
        })
        if resp is None:
            print(f"    server creation returned None, skipping")
            continue

        server_id = resp["server"]["_id"]
        servers[server_spec["name"]] = server_id

        # The default "General" channel is created automatically
        for ch in resp.get("channels", []):
            channels[ch["name"].lower()] = ch["_id"]

        # Create additional channels
        for ch_name in server_spec["channels"]:
            if ch_name.lower() in channels:
                continue
            print(f"    creating channel: #{ch_name}")
            ch_resp = api("POST", f"/servers/{server_id}/channels", token=alice_token, body={
                "type": "Text",
                "name": ch_name,
            })
            if ch_resp:
                channels[ch_name.lower()] = ch_resp["_id"]

        # Have bob and carol join via invite
        if server_spec["channels"]:
            first_ch = channels.get(server_spec["channels"][0].lower())
            if first_ch:
                invite_resp = api("POST", f"/channels/{first_ch}/invites", token=alice_token)
                if invite_resp:
                    invite_code = invite_resp["_id"]
                    for username in ["bob", "carol"]:
                        print(f"    {username} joining via invite...")
                        try:
                            api("POST", f"/invites/{invite_code}", token=tokens[username])
                        except HTTPError:
                            pass  # already a member

    # Send sample messages (skip if any already exist in first channel)
    first_ch_id = channels.get("general")
    if first_ch_id and db.messages.find_one({"channel": first_ch_id}):
        print("  messages already seeded, skipping")
    else:
        print("  sending sample messages...")
        for username, ch_name, content in SAMPLE_MESSAGES:
            ch_id = channels.get(ch_name.lower())
            if not ch_id:
                print(f"    channel #{ch_name} not found, skipping message")
                continue
            api("POST", f"/channels/{ch_id}/messages", token=tokens[username], body={
                "content": content,
            })
        print(f"  sent {len(SAMPLE_MESSAGES)} messages")

    mongo.close()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Seed the Stoat dev environment")
    parser.add_argument("--skip-wait", action="store_true", help="Skip waiting for API")
    parser.add_argument("--accounts-only", action="store_true",
                        help="Only seed MongoDB accounts (no API calls)")
    args = parser.parse_args()

    print("=== Stoat Dev Seed ===")

    if not args.skip_wait:
        print("Waiting for Delta API...")
        wait_for_api()
        print("API is ready.")

    print("Seeding accounts in MongoDB...")
    seed_mongo_accounts()

    if not args.accounts_only:
        print("Seeding servers, channels, and messages via API...")
        seed_servers_and_messages()

    print()
    print("=== Seed complete! ===")
    print()
    print(f"Test accounts (all passwords: '{TEST_PASSWORD}'):")
    for spec in USER_SPECS:
        print(f"  {spec['display_name']:10s}  {spec['email']}")
    print()


if __name__ == "__main__":
    main()
