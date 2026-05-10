#!/usr/bin/env python3
"""
Garmin Connect MCP Server — 让 Claude 通过 MCP 访问 Garmin 健康与训练数据。
"""

import json
import os
from datetime import date, timedelta
from typing import Optional

from garminconnect import Garmin
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field

# ============================================================
# 初始化
# ============================================================

mcp = FastMCP("garmin_mcp")

_garmin_client: Optional[Garmin] = None
TOKEN_DIR = os.path.expanduser(os.environ.get("GARMIN_TOKEN_DIR", "~/.garminconnect"))


def get_client() -> Garmin:
    """获取或创建 Garmin 客户端（自动处理 token 刷新）。"""
    global _garmin_client
    if _garmin_client is None:
        email = os.environ.get("GARMIN_EMAIL", "")
        password = os.environ.get("GARMIN_PASSWORD", "")
        _garmin_client = Garmin(email, password)
        _garmin_client.login(TOKEN_DIR)
    return _garmin_client


def format_date(d: Optional[str] = None) -> str:
    """将日期字符串标准化，默认返回今天。"""
    if d is None:
        return date.today().isoformat()
    return d


# ============================================================
# Tool 输入模型
# ============================================================


class DateInput(BaseModel):
    """单日期查询。"""

    date: Optional[str] = Field(
        default=None,
        description="日期，格式 YYYY-MM-DD，默认今天",
    )


class ActivitiesInput(BaseModel):
    """活动列表查询。"""

    limit: int = Field(default=20, description="返回活动数量，默认 20", ge=1, le=100)
    start: int = Field(default=0, description="分页偏移量", ge=0)


# ============================================================
# 健康数据 Tools
# ============================================================


@mcp.tool(
    name="garmin_daily_summary",
    annotations={
        "title": "每日健康摘要",
        "readOnlyHint": True,
        "destructiveHint": False,
    },
)
async def garmin_daily_summary(params: DateInput) -> str:
    """获取指定日期的每日健康摘要。

    包含：步数、卡路里、活动时间、静息心率、压力等。
    """
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
        "title": "心率数据",
        "readOnlyHint": True,
        "destructiveHint": False,
    },
)
async def garmin_heart_rate(params: DateInput) -> str:
    """获取指定日期的心率数据。

    包含：静息心率、最高心率、全天心率曲线。
    """
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
        "title": "睡眠数据",
        "readOnlyHint": True,
        "destructiveHint": False,
    },
)
async def garmin_sleep(params: DateInput) -> str:
    """获取指定日期的睡眠数据。

    包含：睡眠时长、深睡/浅睡/REM 分布、睡眠评分。
    """
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
        "title": "压力数据",
        "readOnlyHint": True,
        "destructiveHint": False,
    },
)
async def garmin_stress(params: DateInput) -> str:
    """获取指定日期的压力水平数据。"""
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
        "title": "HRV 心率变异性",
        "readOnlyHint": True,
        "destructiveHint": False,
    },
)
async def garmin_hrv(params: DateInput) -> str:
    """获取指定日期的 HRV（心率变异性）数据。

    HRV 是评估恢复状态和训练准备度的关键指标。
    """
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
        "title": "Body Battery 身体电量",
        "readOnlyHint": True,
        "destructiveHint": False,
    },
)
async def garmin_body_battery(params: DateInput) -> str:
    """获取指定日期的 Body Battery（身体电量）数据。

    Body Battery 综合 HRV、压力、活动量和睡眠，评估你的能量水平。
    """
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
        "title": "身体成分",
        "readOnlyHint": True,
        "destructiveHint": False,
    },
)
async def garmin_body_composition(params: DateInput) -> str:
    """获取指定日期的身体成分数据。

    包含：体重、体脂率、肌肉量、BMI 等。
    """
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
        "title": "训练状态",
        "readOnlyHint": True,
        "destructiveHint": False,
    },
)
async def garmin_training_status(params: DateInput) -> str:
    """获取训练状态和最大摄氧量（VO2 Max）数据。"""
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
        "title": "最大指标（VO2Max/体适能年龄）",
        "readOnlyHint": True,
        "destructiveHint": False,
    },
)
async def garmin_max_metrics(params: DateInput) -> str:
    """获取最大指标数据，包括 VO2 Max 和体适能年龄。"""
    try:
        client = get_client()
        d = format_date(params.date)
        data = client.get_max_metrics(d)
        return json.dumps(data, indent=2, default=str)
    except Exception as e:
        return f"Error: {e}"


# ============================================================
# 训练活动 Tools
# ============================================================


@mcp.tool(
    name="garmin_activities",
    annotations={
        "title": "活动列表",
        "readOnlyHint": True,
        "destructiveHint": False,
    },
)
async def garmin_activities(params: ActivitiesInput) -> str:
    """获取最近的训练活动列表。

    包含：活动类型、时间、距离、配速、心率等摘要信息。
    """
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
        "title": "活动详情",
        "readOnlyHint": True,
        "destructiveHint": False,
    },
)
async def garmin_activity_detail(activity_id: str) -> str:
    """获取单个活动的详细数据。

    需要先用 garmin_activities 获取 activityId。
    """
    try:
        client = get_client()
        data = client.get_activity(activity_id)
        return json.dumps(data, indent=2, default=str)
    except Exception as e:
        return f"Error: {e}"


@mcp.tool(
    name="garmin_activity_splits",
    annotations={
        "title": "活动分段数据",
        "readOnlyHint": True,
        "destructiveHint": False,
    },
)
async def garmin_activity_splits(activity_id: str) -> str:
    """获取活动的分段/配速数据（如每公里配速）。"""
    try:
        client = get_client()
        data = client.get_activity_splits(activity_id)
        return json.dumps(data, indent=2, default=str)
    except Exception as e:
        return f"Error: {e}"


@mcp.tool(
    name="garmin_activity_hr_zones",
    annotations={
        "title": "活动心率区间",
        "readOnlyHint": True,
        "destructiveHint": False,
    },
)
async def garmin_activity_hr_zones(activity_id: str) -> str:
    """获取活动的心率区间分布（Zone 1-5 各多长时间）。"""
    try:
        client = get_client()
        data = client.get_activity_hr_in_timezones(activity_id)
        return json.dumps(data, indent=2, default=str)
    except Exception as e:
        return f"Error: {e}"


# ============================================================
# 综合分析 Tools
# ============================================================


@mcp.tool(
    name="garmin_personal_records",
    annotations={
        "title": "个人记录",
        "readOnlyHint": True,
        "destructiveHint": False,
    },
)
async def garmin_personal_records(owner_display_name: str) -> str:
    """获取个人运动记录（PR）。"""
    try:
        client = get_client()
        data = client.get_personal_record(owner_display_name)
        return json.dumps(data, indent=2, default=str)
    except Exception as e:
        return f"Error: {e}"


@mcp.tool(
    name="garmin_race_predictions",
    annotations={
        "title": "比赛成绩预测",
        "readOnlyHint": True,
        "destructiveHint": False,
    },
)
async def garmin_race_predictions() -> str:
    """获取 Garmin 基于你当前体能的比赛成绩预测。

    包含 5K、10K、半马、全马的预测完赛时间。
    """
    try:
        client = get_client()
        data = client.get_race_predictions()
        return json.dumps(data, indent=2, default=str)
    except Exception as e:
        return f"Error: {e}"


@mcp.tool(
    name="garmin_devices",
    annotations={
        "title": "设备信息",
        "readOnlyHint": True,
        "destructiveHint": False,
    },
)
async def garmin_devices() -> str:
    """获取已连接的 Garmin 设备信息。"""
    try:
        client = get_client()
        data = client.get_devices()
        return json.dumps(data, indent=2, default=str)
    except Exception as e:
        return f"Error: {e}"


@mcp.tool(
    name="garmin_weekly_summary",
    annotations={
        "title": "周训练总结",
        "readOnlyHint": True,
        "destructiveHint": False,
    },
)
async def garmin_weekly_summary(params: DateInput) -> str:
    """获取本周训练和健康数据的综合摘要。

    汇总最近 7 天的关键指标：活动总量、平均睡眠、心率趋势等。
    """
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
# 启动服务
# ============================================================

if __name__ == "__main__":
    mcp.run()
