"""Pydantic models for simulator configuration and state."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


class SimStatus(str, Enum):
    stopped = "stopped"
    running = "running"
    starting = "starting"
    stopping = "stopping"


class SimConfig(BaseModel):
    num_users: int = Field(default=5, ge=1, le=20)
    server_name: str = "Sim Server"
    target_channels: list[str] = Field(default_factory=lambda: ["general", "random", "links"])
    min_delay_seconds: float = Field(default=2.0, ge=0.5)
    max_delay_seconds: float = Field(default=15.0, ge=1.0)
    create_missing_channels: bool = True


class SimUser(BaseModel):
    user_id: str
    username: str
    email: str
    display_name: str
    token: str | None = None
    active: bool = False


class ActivityType(str, Enum):
    message = "message"
    reaction = "reaction"
    typing = "typing"
    edit = "edit"
    channel_create = "channel_create"


class ActivityEvent(BaseModel):
    timestamp: datetime = Field(default_factory=datetime.now)
    user: str
    action: ActivityType
    channel: str = ""
    detail: str = ""


class SimState(BaseModel):
    status: SimStatus = SimStatus.stopped
    config: SimConfig = Field(default_factory=SimConfig)
    users: list[SimUser] = Field(default_factory=list)
    log: list[ActivityEvent] = Field(default_factory=list)
    server_id: str | None = None
    channels: dict[str, str] = Field(default_factory=dict)  # name -> id
