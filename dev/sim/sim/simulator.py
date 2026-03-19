"""Core simulation engine — manages async user tasks."""

from __future__ import annotations

import asyncio
import logging
import random
from collections import deque
from datetime import datetime

from .content import get_user_spec, random_emoji, random_message
from .db import SIM_PASSWORD, SimDB
from .models import ActivityEvent, ActivityType, SimConfig, SimState, SimStatus, SimUser
from .stoat_client import StoatClient

logger = logging.getLogger(__name__)

MAX_LOG_SIZE = 300


class SimulatorEngine:
    """Orchestrates simulated user activity against the Stoat backend."""

    def __init__(self, stoat_url: str, mongo_url: str):
        self.client = StoatClient(stoat_url)
        self.db = SimDB(mongo_url)
        self.state = SimState()
        self._tasks: list[asyncio.Task] = []
        self._stop_event = asyncio.Event()

    async def close(self):
        await self.stop()
        await self.client.close()
        await self.db.close()

    def _log(self, user: str, action: ActivityType, channel: str = "", detail: str = ""):
        event = ActivityEvent(
            timestamp=datetime.now(),
            user=user,
            action=action,
            channel=channel,
            detail=detail,
        )
        self.state.log.append(event)
        # Trim log
        if len(self.state.log) > MAX_LOG_SIZE:
            self.state.log = self.state.log[-MAX_LOG_SIZE:]

    # -- provisioning --

    async def _provision_user(self, index: int) -> SimUser:
        """Create account in MongoDB, login, complete onboarding."""
        user_id, username, display_name = get_user_spec(index)

        sim_user = await self.db.create_account(user_id, username, display_name)

        # Login
        token = await self.client.login(sim_user.email, SIM_PASSWORD)
        sim_user.token = token

        # Onboarding
        needs_onboarding = await self.client.check_onboarding(token)
        if needs_onboarding:
            await self.client.complete_onboarding(token, username)
            await self.client.set_display_name(token, display_name)

        sim_user.active = True
        self._log(username, ActivityType.message, detail="provisioned and logged in")
        return sim_user

    async def _ensure_server(self, token: str):
        """Create the sim server and channels if they don't exist."""
        cfg = self.state.config

        if not self.state.server_id:
            resp = await self.client.create_server(token, cfg.server_name, "Activity simulator server")
            if resp:
                self.state.server_id = resp["server"]["_id"]
                for ch in resp.get("channels", []):
                    self.state.channels[ch["name"].lower()] = ch["_id"]
                self._log("system", ActivityType.channel_create, detail=f"created server: {cfg.server_name}")

        if not self.state.server_id:
            logger.error("Failed to create server")
            return

        # Create missing channels
        if cfg.create_missing_channels:
            for ch_name in cfg.target_channels:
                if ch_name.lower() not in self.state.channels:
                    ch_resp = await self.client.create_channel(token, self.state.server_id, ch_name)
                    if ch_resp:
                        self.state.channels[ch_name.lower()] = ch_resp["_id"]
                        self._log("system", ActivityType.channel_create, channel=ch_name, detail="created channel")

    async def _join_user_to_server(self, token: str):
        """Join a user to the server via invite."""
        if not self.state.channels:
            return
        first_ch_id = next(iter(self.state.channels.values()))
        code = await self.client.create_invite(self.state.users[0].token, first_ch_id)
        if code:
            await self.client.join_invite(token, code)

    # -- user activity loop --

    async def _user_loop(self, user: SimUser):
        """Main loop for one simulated user."""
        cfg = self.state.config

        while not self._stop_event.is_set():
            delay = random.uniform(cfg.min_delay_seconds, cfg.max_delay_seconds)
            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=delay)
                break  # stop event was set
            except asyncio.TimeoutError:
                pass  # normal — delay elapsed

            if not self.state.channels:
                continue

            # Pick a random action (weighted)
            action = random.choices(
                [ActivityType.message, ActivityType.reaction, ActivityType.typing],
                weights=[75, 15, 10],
                k=1,
            )[0]

            ch_name = random.choice(list(self.state.channels.keys()))
            ch_id = self.state.channels[ch_name]

            try:
                if action == ActivityType.message:
                    content = random_message()
                    await self.client.send_message(user.token, ch_id, content)
                    preview = content[:60] + "..." if len(content) > 60 else content
                    self._log(user.username, ActivityType.message, ch_name, preview)

                elif action == ActivityType.reaction:
                    # React to a recent message
                    messages = await self.client.get_messages(user.token, ch_id, limit=10)
                    if messages:
                        msg = random.choice(messages)
                        emoji = random_emoji()
                        await self.client.react(user.token, ch_id, msg["_id"], emoji)
                        self._log(user.username, ActivityType.reaction, ch_name, emoji)

                elif action == ActivityType.typing:
                    # Just log it — typing indicators are ephemeral
                    self._log(user.username, ActivityType.typing, ch_name, "typing...")

            except Exception as e:
                logger.warning(f"User {user.username} action failed: {e}")
                self._log(user.username, ActivityType.message, detail=f"error: {e}")

    # -- control --

    async def start(self, config: SimConfig | None = None):
        """Start the simulation."""
        if self.state.status == SimStatus.running:
            return

        if config:
            self.state.config = config

        self.state.status = SimStatus.starting
        self._stop_event.clear()
        self.state.users = []

        try:
            # Wait for API
            self._log("system", ActivityType.message, detail="waiting for Stoat API...")
            for _ in range(30):
                if await self.client.health_check():
                    break
                await asyncio.sleep(2)
            else:
                self._log("system", ActivityType.message, detail="API not reachable, aborting")
                self.state.status = SimStatus.stopped
                return

            # Provision users
            self._log("system", ActivityType.message, detail=f"provisioning {self.state.config.num_users} users...")
            for i in range(self.state.config.num_users):
                user = await self._provision_user(i)
                self.state.users.append(user)

            # Create server and channels (first user is the owner)
            await self._ensure_server(self.state.users[0].token)

            # Join all other users to the server
            for user in self.state.users[1:]:
                await self._join_user_to_server(user.token)

            # Start activity loops
            self.state.status = SimStatus.running
            self._log("system", ActivityType.message, detail="simulation started!")
            for user in self.state.users:
                task = asyncio.create_task(self._user_loop(user))
                self._tasks.append(task)

        except Exception as e:
            logger.exception("Failed to start simulation")
            self._log("system", ActivityType.message, detail=f"start failed: {e}")
            self.state.status = SimStatus.stopped

    async def stop(self):
        """Stop the simulation."""
        if self.state.status not in (SimStatus.running, SimStatus.starting):
            return

        self.state.status = SimStatus.stopping
        self._stop_event.set()

        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
            self._tasks.clear()

        for user in self.state.users:
            user.active = False

        self.state.status = SimStatus.stopped
        self._log("system", ActivityType.message, detail="simulation stopped")

    async def update_config(self, config: SimConfig):
        """Update config, restarting if running."""
        was_running = self.state.status == SimStatus.running
        if was_running:
            await self.stop()
        self.state.config = config
        if was_running:
            await self.start()
