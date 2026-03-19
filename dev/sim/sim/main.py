"""FastAPI app for the Stoat Activity Simulator."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from .models import SimConfig, SimState
from .simulator import SimulatorEngine

STOAT_API_URL = os.environ.get("STOAT_API_URL", "http://delta:14702")
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://mongodb:27017")

engine: SimulatorEngine | None = None
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    global engine
    engine = SimulatorEngine(STOAT_API_URL, MONGO_URL)
    yield
    await engine.close()


app = FastAPI(title="Stoat Activity Simulator", lifespan=lifespan)


# -- Pages --

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {
        "request": request,
        "state": engine.state,
    })


# -- htmx partials --

@app.get("/partial/status", response_class=HTMLResponse)
async def partial_status(request: Request):
    return templates.TemplateResponse("partials/status.html", {
        "request": request,
        "state": engine.state,
    })


@app.get("/partial/log", response_class=HTMLResponse)
async def partial_log(request: Request):
    return templates.TemplateResponse("partials/log.html", {
        "request": request,
        "log": reversed(engine.state.log[-50:]),
    })


@app.get("/partial/users", response_class=HTMLResponse)
async def partial_users(request: Request):
    return templates.TemplateResponse("partials/users.html", {
        "request": request,
        "users": engine.state.users,
    })


@app.get("/partial/channels", response_class=HTMLResponse)
async def partial_channels(request: Request):
    return templates.TemplateResponse("partials/channels.html", {
        "request": request,
        "channels": engine.state.channels,
        "config": engine.state.config,
    })


# -- API actions --

@app.post("/api/start", response_class=HTMLResponse)
async def api_start(request: Request):
    form = await request.form()
    config = SimConfig(
        num_users=int(form.get("num_users", 5)),
        server_name=form.get("server_name", "Sim Server"),
        target_channels=[ch.strip() for ch in form.get("channels", "general,random,links").split(",") if ch.strip()],
        min_delay_seconds=float(form.get("min_delay", 2.0)),
        max_delay_seconds=float(form.get("max_delay", 15.0)),
        create_missing_channels=form.get("create_channels") == "on",
    )
    # Start in background so response returns immediately
    import asyncio
    asyncio.create_task(engine.start(config))

    return templates.TemplateResponse("partials/status.html", {
        "request": request,
        "state": engine.state,
    })


@app.post("/api/stop", response_class=HTMLResponse)
async def api_stop(request: Request):
    import asyncio
    asyncio.create_task(engine.stop())

    return templates.TemplateResponse("partials/status.html", {
        "request": request,
        "state": engine.state,
    })


@app.post("/api/channels/add", response_class=HTMLResponse)
async def api_add_channel(request: Request):
    form = await request.form()
    name = form.get("channel_name", "").strip()
    if name and name.lower() not in engine.state.config.target_channels:
        engine.state.config.target_channels.append(name.lower())
        # If running, create the channel in Stoat
        if engine.state.server_id and engine.state.users:
            token = engine.state.users[0].token
            if name.lower() not in engine.state.channels:
                ch = await engine.client.create_channel(token, engine.state.server_id, name)
                if ch:
                    engine.state.channels[name.lower()] = ch["_id"]

    return templates.TemplateResponse("partials/channels.html", {
        "request": request,
        "channels": engine.state.channels,
        "config": engine.state.config,
    })


@app.delete("/api/channels/{name}", response_class=HTMLResponse)
async def api_remove_channel(request: Request, name: str):
    name_lower = name.lower()
    if name_lower in engine.state.config.target_channels:
        engine.state.config.target_channels.remove(name_lower)

    return templates.TemplateResponse("partials/channels.html", {
        "request": request,
        "channels": engine.state.channels,
        "config": engine.state.config,
    })


# -- JSON API --

@app.get("/api/state")
async def api_state() -> SimState:
    return engine.state
