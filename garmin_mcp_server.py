#!/usr/bin/env python3
"""
Garmin Connect MCP server — exposes health and training data to MCP clients (e.g. Claude).
"""

import json
import os
from datetime import date, timedelta
from typing import Optional

from garminconnect import Garmin
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field

# ============================================================
# Setup
# ============================================================

mcp = FastMCP("garmin_mcp")

_garmin_client: Optional[Garmin] = None
TOKEN_DIR = os.path.expanduser(os.environ.get("GARMIN_TOKEN_DIR", "~/.garminconnect"))


def get_client() -> Garmin:
    """Return a cached Garmin client (handles token refresh)."""
    global _garmin_client
    if _garmin_client is None:
        email = os.environ.get("GARMIN_EMAIL", "")
        password = os.environ.get("GARMIN_PASSWORD", "")
        _garmin_client = Garmin(email, password)
        _garmin_client.login(TOKEN_DIR)
    return _garmin_client


def format_date(d: Optional[str] = None) -> str:
    """Normalize date string; default to today."""
    if d is None:
        return date.today().isoformat()
    return d


# ============================================================
# Tool input models
# ============================================================


class DateInput(BaseModel):
    """Single-day query."""

    date: Optional[str] = Field(
        default=None,
        description="Date as YYYY-MM-DD; defaults to today",
    )


class ActivitiesInput(BaseModel):
    """Activity list query."""

    limit: int = Field(
        default=20, description="Max activities to return (default 20)", ge=1, le=100
    )
    start: int = Field(default=0, description="Pagination offset", ge=0)


# ============================================================
# Health tools
# ============================================================


@mcp.tool(
    name="garmin_daily_summary",
    annotations={
        "title": "Daily health summary",
        "readOnlyHint": True,
        "destructiveHint": False,
    },
)
async def garmin_daily_summary(params: DateInput) -> str:
    """Daily health summary for a date (steps, calories, activity, resting HR, stress, etc.)."""
    try:
        client = get_client()
        d = format_date(params.date)
        stats = client.get_stats(d)
        return json.dumps(stats, indent=2, default=str)
    except Exception as e:
        return f"Error: {e}"


@mcp.tool(
    name="garmin_heart_rate",
    annotations={
        "title": "Heart rate",
        "readOnlyHint": True,
        "destructiveHint": False,
    },
)
async def garmin_heart_rate(params: DateInput) -> str:
    """Heart rate for a date (resting, max, intraday curve)."""
    try:
        client = get_client()
        d = format_date(params.date)
        data = client.get_heart_rates(d)
        return json.dumps(data, indent=2, default=str)
    except Exception as e:
        return f"Error: {e}"


@mcp.tool(
    name="garmin_sleep",
    annotations={
        "title": "Sleep",
        "readOnlyHint": True,
        "destructiveHint": False,
    },
)
async def garmin_sleep(params: DateInput) -> str:
    """Sleep for a night (duration, deep/light/REM, score)."""
    try:
        client = get_client()
        d = format_date(params.date)
        data = client.get_sleep_data(d)
        return json.dumps(data, indent=2, default=str)
    except Exception as e:
        return f"Error: {e}"


@mcp.tool(
    name="garmin_stress",
    annotations={
        "title": "Stress",
        "readOnlyHint": True,
        "destructiveHint": False,
    },
)
async def garmin_stress(params: DateInput) -> str:
    """Stress levels for a date."""
    try:
        client = get_client()
        d = format_date(params.date)
        data = client.get_stress_data(d)
        return json.dumps(data, indent=2, default=str)
    except Exception as e:
        return f"Error: {e}"


@mcp.tool(
    name="garmin_hrv",
    annotations={
        "title": "HRV",
        "readOnlyHint": True,
        "destructiveHint": False,
    },
)
async def garmin_hrv(params: DateInput) -> str:
    """Heart rate variability (HRV) for a date — useful for recovery / readiness."""
    try:
        client = get_client()
        d = format_date(params.date)
        data = client.get_hrv_data(d)
        return json.dumps(data, indent=2, default=str)
    except Exception as e:
        return f"Error: {e}"


@mcp.tool(
    name="garmin_body_battery",
    annotations={
        "title": "Body Battery",
        "readOnlyHint": True,
        "destructiveHint": False,
    },
)
async def garmin_body_battery(params: DateInput) -> str:
    """Body Battery for a date (energy estimate from HRV, stress, activity, sleep)."""
    try:
        client = get_client()
        d = format_date(params.date)
        data = client.get_body_battery(d)
        return json.dumps(data, indent=2, default=str)
    except Exception as e:
        return f"Error: {e}"


@mcp.tool(
    name="garmin_body_composition",
    annotations={
        "title": "Body composition",
        "readOnlyHint": True,
        "destructiveHint": False,
    },
)
async def garmin_body_composition(params: DateInput) -> str:
    """Body composition for a date (weight, body fat, muscle, BMI, etc.)."""
    try:
        client = get_client()
        d = format_date(params.date)
        data = client.get_body_composition(d)
        return json.dumps(data, indent=2, default=str)
    except Exception as e:
        return f"Error: {e}"


@mcp.tool(
    name="garmin_training_status",
    annotations={
        "title": "Training status",
        "readOnlyHint": True,
        "destructiveHint": False,
    },
)
async def garmin_training_status(params: DateInput) -> str:
    """Training status and VO2 Max-related data."""
    try:
        client = get_client()
        d = format_date(params.date)
        data = client.get_training_status(d)
        return json.dumps(data, indent=2, default=str)
    except Exception as e:
        return f"Error: {e}"


@mcp.tool(
    name="garmin_max_metrics",
    annotations={
        "title": "Max metrics (VO2 Max / fitness age)",
        "readOnlyHint": True,
        "destructiveHint": False,
    },
)
async def garmin_max_metrics(params: DateInput) -> str:
    """Max metrics including VO2 Max and fitness age."""
    try:
        client = get_client()
        d = format_date(params.date)
        data = client.get_max_metrics(d)
        return json.dumps(data, indent=2, default=str)
    except Exception as e:
        return f"Error: {e}"


# ============================================================
# Activity tools
# ============================================================


@mcp.tool(
    name="garmin_activities",
    annotations={
        "title": "Activity list",
        "readOnlyHint": True,
        "destructiveHint": False,
    },
)
async def garmin_activities(params: ActivitiesInput) -> str:
    """Recent activities (type, time, distance, pace, HR summary)."""
    try:
        client = get_client()
        data = client.get_activities(params.start, params.limit)
        summary = []
        for act in data:
            summary.append(
                {
                    "activityId": act.get("activityId"),
                    "activityName": act.get("activityName"),
                    "activityType": act.get("activityType", {}).get("typeKey"),
                    "startTime": act.get("startTimeLocal"),
                    "duration_min": round(act.get("duration", 0) / 60, 1),
                    "distance_km": round(act.get("distance", 0) / 1000, 2),
                    "avgHR": act.get("averageHR"),
                    "maxHR": act.get("maxHR"),
                    "calories": act.get("calories"),
                    "avgPace_min_km": act.get("averageSpeed"),
                    "elevationGain_m": act.get("elevationGain"),
                    "trainingEffect_aerobic": act.get("aerobicTrainingEffect"),
                    "trainingEffect_anaerobic": act.get("anaerobicTrainingEffect"),
                }
            )
        return json.dumps(summary, indent=2, default=str)
    except Exception as e:
        return f"Error: {e}"


@mcp.tool(
    name="garmin_activity_detail",
    annotations={
        "title": "Activity detail",
        "readOnlyHint": True,
        "destructiveHint": False,
    },
)
async def garmin_activity_detail(activity_id: str) -> str:
    """Full detail for one activity (use `activityId` from garmin_activities)."""
    try:
        client = get_client()
        data = client.get_activity(activity_id)
        return json.dumps(data, indent=2, default=str)
    except Exception as e:
        return f"Error: {e}"


@mcp.tool(
    name="garmin_activity_splits",
    annotations={
        "title": "Activity splits",
        "readOnlyHint": True,
        "destructiveHint": False,
    },
)
async def garmin_activity_splits(activity_id: str) -> str:
    """Splits / pace data for an activity (e.g. per km)."""
    try:
        client = get_client()
        data = client.get_activity_splits(activity_id)
        return json.dumps(data, indent=2, default=str)
    except Exception as e:
        return f"Error: {e}"


@mcp.tool(
    name="garmin_activity_hr_zones",
    annotations={
        "title": "Activity HR zones",
        "readOnlyHint": True,
        "destructiveHint": False,
    },
)
async def garmin_activity_hr_zones(activity_id: str) -> str:
    """Time in HR zones (Z1–Z5) for an activity."""
    try:
        client = get_client()
        data = client.get_activity_hr_in_timezones(activity_id)
        return json.dumps(data, indent=2, default=str)
    except Exception as e:
        return f"Error: {e}"


# ============================================================
# Combined / misc tools
# ============================================================


@mcp.tool(
    name="garmin_personal_records",
    annotations={
        "title": "Personal records",
        "readOnlyHint": True,
        "destructiveHint": False,
    },
)
async def garmin_personal_records(owner_display_name: str) -> str:
    """Personal records (PRs) for the given Connect display name."""
    try:
        client = get_client()
        data = client.get_personal_record(owner_display_name)
        return json.dumps(data, indent=2, default=str)
    except Exception as e:
        return f"Error: {e}"


@mcp.tool(
    name="garmin_race_predictions",
    annotations={
        "title": "Race predictions",
        "readOnlyHint": True,
        "destructiveHint": False,
    },
)
async def garmin_race_predictions() -> str:
    """Predicted race times (5K, 10K, half, marathon) from current fitness."""
    try:
        client = get_client()
        data = client.get_race_predictions()
        return json.dumps(data, indent=2, default=str)
    except Exception as e:
        return f"Error: {e}"


@mcp.tool(
    name="garmin_devices",
    annotations={
        "title": "Devices",
        "readOnlyHint": True,
        "destructiveHint": False,
    },
)
async def garmin_devices() -> str:
    """Paired Garmin devices."""
    try:
        client = get_client()
        data = client.get_devices()
        return json.dumps(data, indent=2, default=str)
    except Exception as e:
        return f"Error: {e}"


@mcp.tool(
    name="garmin_weekly_summary",
    annotations={
        "title": "Weekly summary",
        "readOnlyHint": True,
        "destructiveHint": False,
    },
)
async def garmin_weekly_summary(params: DateInput) -> str:
    """Rolling 7-day summary ending on the given date (stats + recent activities)."""
    try:
        client = get_client()
        end = date.fromisoformat(format_date(params.date))
        start = end - timedelta(days=6)

        summary: dict = {
            "period": f"{start.isoformat()} ~ {end.isoformat()}",
            "daily_stats": [],
            "activities": [],
        }

        for i in range(7):
            d = (start + timedelta(days=i)).isoformat()
            try:
                stats = client.get_stats(d)
                summary["daily_stats"].append(
                    {
                        "date": d,
                        "steps": stats.get("totalSteps"),
                        "calories": stats.get("totalKilocalories"),
                        "restingHR": stats.get("restingHeartRate"),
                        "stressAvg": stats.get("averageStressLevel"),
                        "sleepHours": round(
                            stats.get("sleepingSeconds", 0) / 3600,
                            1,
                        ),
                        "activeMinutes": stats.get("activeSeconds", 0) // 60,
                    }
                )
            except Exception:
                pass

        try:
            acts = client.get_activities(0, 20)
            for act in acts:
                act_date = act.get("startTimeLocal", "")[:10]
                if start.isoformat() <= act_date <= end.isoformat():
                    summary["activities"].append(
                        {
                            "name": act.get("activityName"),
                            "type": act.get("activityType", {}).get("typeKey"),
                            "date": act_date,
                            "duration_min": round(act.get("duration", 0) / 60, 1),
                            "distance_km": round(act.get("distance", 0) / 1000, 2),
                            "avgHR": act.get("averageHR"),
                            "calories": act.get("calories"),
                        }
                    )
        except Exception:
            pass

        return json.dumps(summary, indent=2, default=str)
    except Exception as e:
        return f"Error: {e}"


# ============================================================
# Entrypoint
# ============================================================

if __name__ == "__main__":
    mcp.run()
