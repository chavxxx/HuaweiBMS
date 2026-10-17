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
    config_manager,
    diagnostics,
    history,
    ports,
    registers,
    settings,
    telemetry,
)
from .state import app_context

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("huawei_bms.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
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
        dead_connections = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                dead_connections.append(connection)
        for dc in dead_connections:
            self.disconnect(dc)


ws_manager = ConnectionManager()


# Hook telemetry service callback to WebSocket broadcast
def on_telemetry_event(payload: dict):
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.run_coroutine_threadsafe(ws_manager.broadcast(payload), loop)
    except Exception:
        pass


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
