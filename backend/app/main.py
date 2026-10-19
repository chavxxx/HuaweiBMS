"""Main FastAPI Application for Huawei EMS B1 Battery Manager."""

import asyncio
import json
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from .routes import (
    alarms,
    audit,
    batteries,
    config_manager,
    diagnostics,
    history,
    ports,
    registers,
    settings,
    telemetry,
    updates,
)
from .state import app_context

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("huawei_bms.main")


main_loop: Optional[asyncio.AbstractEventLoop] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global main_loop
    main_loop = asyncio.get_running_loop()
    logger.info("Huawei EMS B1 Battery Manager backend starting...")
    yield
    logger.info("Shutting down Huawei EMS B1 Battery Manager backend...")
    app_context.telemetry_service.stop_polling()
    app_context.serial_client.disconnect()


app = FastAPI(
    title="Huawei EMS B1 Battery Manager API",
    description="Production-grade local desktop and serial communication service for Huawei EMS B1 / ESS BMS.",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS for local desktop UI / Vite dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include all route modules
app.include_router(ports.router)
app.include_router(telemetry.router)
app.include_router(config_manager.router)
app.include_router(alarms.router)
app.include_router(diagnostics.router)
app.include_router(registers.router)
app.include_router(history.router)
app.include_router(audit.router)
app.include_router(settings.router)
app.include_router(updates.router)
app.include_router(batteries.router)


# WebSocket for high-frequency live telemetry and protocol stream
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        connections = list(self.active_connections)
        dead_connections = []
        for connection in connections:
            try:
                await connection.send_json(message)
            except Exception:
                dead_connections.append(connection)
        for dc in dead_connections:
            self.disconnect(dc)


ws_manager = ConnectionManager()


# Hook telemetry service callback to WebSocket broadcast
def on_telemetry_event(payload: dict):
    global main_loop
    try:
        loop = main_loop
        if loop is None or not loop.is_running():
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = None
        if loop and loop.is_running():
            asyncio.run_coroutine_threadsafe(ws_manager.broadcast(payload), loop)
    except Exception as e:
        logger.debug("Failed to dispatch telemetry event to WebSocket: %s", e)


app_context.telemetry_service.register_listener(on_telemetry_event)


@app.websocket("/ws/telemetry")
async def websocket_telemetry_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        # Send initial state immediately
        await websocket.send_json({
            "type": "INITIAL_STATE",
            "freshness": app_context.telemetry_service.get_freshness_status(),
            "telemetry": app_context.telemetry_service.latest_telemetry,
            "electrical": app_context.telemetry_service.latest_electrical,
            "cells": app_context.telemetry_service.latest_cells
        })
        while True:
            # Keep connection open, handle client heartbeats
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception:
        ws_manager.disconnect(websocket)


@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "app": "Huawei EMS B1 Battery Manager",
        "version": "1.0.0",
        "simulation_mode": app_context.telemetry_service.use_simulation,
        "connected": app_context.serial_client.is_connected
    }


# Mount production frontend build if present
import sys
from pathlib import Path
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

def resolve_frontend_dist() -> Path:
    candidates = []
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        meipass = Path(sys._MEIPASS)
        candidates.extend([
            meipass / "frontend" / "dist",
            meipass / "dist",
            meipass / "resources" / "dist"
        ])
    candidates.extend([
        Path(__file__).resolve().parent.parent.parent / "frontend" / "dist",
        Path(__file__).resolve().parent.parent / "frontend" / "dist",
        Path.cwd() / "frontend" / "dist",
        Path.cwd() / "dist",
    ])
    for c in candidates:
        if c.exists() and (c / "index.html").exists():
            return c
    return candidates[0]

DIST_DIR = resolve_frontend_dist()
if DIST_DIR.exists() and (DIST_DIR / "index.html").exists():
    assets_dir = DIST_DIR / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        # Do not intercept API or WebSocket routes
        if full_path.startswith("api") or full_path.startswith("ws"):
            return JSONResponse(status_code=404, content={"detail": f"Route /{full_path} not found"})
        file_path = DIST_DIR / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(DIST_DIR / "index.html")
