"""Telemetry, Electrical, and Cell Monitoring Routes."""

from fastapi import APIRouter
from ..state import app_context

router = APIRouter(prefix="/api/telemetry", tags=["Telemetry"])


@router.get("/latest")
def get_latest_telemetry():
    """Retrieve top-level battery overview telemetry and freshness."""
    return {
        "freshness": app_context.telemetry_service.get_freshness_status(),
        "telemetry": app_context.telemetry_service.latest_telemetry,
        "electrical": app_context.telemetry_service.latest_electrical,
        "cells": app_context.telemetry_service.latest_cells
    }


@router.get("/electrical")
def get_electrical_telemetry():
    """Retrieve detailed DC bus, power limits, and energy counter measurements."""
    return {
        "freshness": app_context.telemetry_service.get_freshness_status(),
        "electrical": app_context.telemetry_service.latest_electrical
    }


@router.get("/cells")
def get_cell_telemetry():
    """Retrieve individual cell voltages, temperature sensors, and delta V spread."""
    return {
        "freshness": app_context.telemetry_service.get_freshness_status(),
        "cells": app_context.telemetry_service.latest_cells
    }
