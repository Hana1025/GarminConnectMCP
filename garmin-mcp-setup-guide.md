# Garmin × Claude MCP Server 搭建指南

## 概述

本指南帮你搭建一个 MCP (Model Context Protocol) Server，让 Claude 直接访问你的 Garmin 健康与训练数据。搭建完成后，你可以直接在 Claude 里问：

- "分析我最近一个月的睡眠质量趋势"
- "我上周的训练负荷是否过大？"
- "我的静息心率最近有什么变化？"
- "基于我的 HRV 和 Body Battery，今天适合高强度训练吗？"

---

## 方案选择

有两条路线，根据你的需求选择：

| | 方案 A：garmy（推荐） | 方案 B：自己从零搭建 |
|---|---|---|
| 难度 | ⭐⭐ 简单 | ⭐⭐⭐⭐ 较复杂 |
| 特点 | 内置 MCP Server + 本地 SQLite 数据库 | 完全自定义，实时查询 Garmin API |
| 适合 | 快速上手，分析历史数据 | 需要自定义 tool 或实时数据 |

---

## 方案 A：使用 garmy（推荐，最快 10 分钟搞定）

### 前提条件

- Python 3.8+
- Garmin Connect 账号（就是你登录 Garmin Connect app/网页的账号）
- Claude Desktop 应用（macOS / Windows）

### 步骤 1：安装 garmy

```bash
# 安装完整版（包含本地数据库 + MCP Server）
pip install "garmy[all]"
```

### 步骤 2：登录 Garmin Connect

首次运行需要登录，后续会自动刷新 token：

```python
# login.py - 只需运行一次
from garmy import AuthClient

auth = AuthClient()
auth.login("你的garmin邮箱", "你的garmin密码")
print("✅ 登录成功！Token 已保存。")
```

```bash
python login.py
```

> ⚠️ 如果你的 Garmin 账号开启了 MFA（多因素验证），登录时会提示输入验证码。

### 步骤 3：同步数据到本地数据库

```bash
# 同步最近 30 天的数据
garmy-sync sync --last-days 30

# 查看同步状态
garmy-sync status
```

这会把你的健康数据保存到本地 SQLite 数据库，MCP Server 从本地库读取数据（更快、更稳定）。

### 步骤 4：配置 Claude Desktop

编辑 Claude Desktop 的配置文件：

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

添加以下内容：

```json
{
  "mcpServers": {
    "garmy-localdb": {
      "command": "garmy-mcp",
      "args": ["server", "--database", "/path/to/health.db", "--max-rows", "500"]
    }
  }
}
```

> 💡 用 `garmy-mcp config` 命令可以查看推荐的配置。
> 用 `garmy-mcp info --database health.db` 查看数据库路径和内容。

### 步骤 5：重启 Claude Desktop，开始提问！

重启 Claude Desktop 后，你就可以直接问关于训练和健康的问题了。

### 定期同步

建议设置定时任务自动同步：

```bash
# macOS/Linux: 添加 crontab，每天早上 7 点同步
crontab -e
# 添加这一行：
0 7 * * * /usr/local/bin/garmy-sync sync --last-days 7
```

```powershell
# Windows: 用 Task Scheduler 或 PowerShell
# 创建每日任务
schtasks /create /tn "GarmySync" /tr "garmy-sync sync --last-days 7" /sc daily /st 07:00
```

---

## 方案 B：从零搭建自定义 MCP Server

如果你需要更多自定义能力（比如实时查询、自定义分析工具），可以用 `python-garminconnect` + `FastMCP` 自己搭建。

### 步骤 1：安装依赖

```bash
pip install garminconnect mcp httpx
```

### 步骤 2：创建 MCP Server

创建文件 `garmin_mcp_server.py`：

```python
#!/usr/bin/env python3
"""
Garmin Connect MCP Server
让 Claude 直接访问你的 Garmin 健康和训练数据
"""

import json
import os
from datetime import date, datetime, timedelta
from typing import Optional

from garminconnect import Garmin
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field

# ============================================================
# 初始化
# ============================================================

mcp = FastMCP("garmin_mcp")

# Garmin 客户端（延迟初始化）
_garmin_client: Optional[Garmin] = None
TOKEN_DIR = os.path.expanduser("~/.garminconnect")


def get_client() -> Garmin:
    """获取或创建 Garmin 客户端（自动处理 token 刷新）"""
    global _garmin_client
    if _garmin_client is None:
        email = os.environ.get("GARMIN_EMAIL", "")
        password = os.environ.get("GARMIN_PASSWORD", "")
        _garmin_client = Garmin(email, password)
        _garmin_client.login(TOKEN_DIR)
    return _garmin_client


def format_date(d: Optional[str] = None) -> str:
    """将日期字符串标准化，默认返回今天"""
    if d is None:
        return date.today().isoformat()
    return d


# ============================================================
# Tool 输入模型
# ============================================================

class DateInput(BaseModel):
    """单日期查询"""
    date: Optional[str] = Field(
        default=None,
        description="日期，格式 YYYY-MM-DD，默认今天"
    )


class DateRangeInput(BaseModel):
    """日期范围查询"""
    start_date: str = Field(
        ..., description="开始日期，格式 YYYY-MM-DD"
    )
    end_date: Optional[str] = Field(
        default=None,
        description="结束日期，格式 YYYY-MM-DD，默认今天"
    )


class ActivitiesInput(BaseModel):
    """活动列表查询"""
    limit: int = Field(
        default=20, description="返回活动数量，默认 20", ge=1, le=100
    )
    start: int = Field(
        default=0, description="分页偏移量", ge=0
    )


# ============================================================
# 健康数据 Tools
# ============================================================

@mcp.tool(
    name="garmin_daily_summary",
    annotations={
        "title": "每日健康摘要",
        "readOnlyHint": True,
        "destructiveHint": False,
    }
)
async def garmin_daily_summary(params: DateInput) -> str:
    """获取指定日期的每日健康摘要。

    包含：步数、卡路里、活动时间、静息心率、压力等。

    Args:
        params: 包含日期参数

    Returns:
        JSON 格式的每日摘要数据
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
    }
)
async def garmin_heart_rate(params: DateInput) -> str:
    """获取指定日期的心率数据。

    包含：静息心率、最高心率、全天心率曲线。

    Args:
        params: 包含日期参数

    Returns:
        JSON 格式的心率数据
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
    }
)
async def garmin_sleep(params: DateInput) -> str:
    """获取指定日期的睡眠数据。

    包含：睡眠时长、深睡/浅睡/REM 分布、睡眠评分。

    Args:
        params: 包含日期参数

    Returns:
        JSON 格式的睡眠数据
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
    }
)
async def garmin_stress(params: DateInput) -> str:
    """获取指定日期的压力水平数据。

    Args:
        params: 包含日期参数

    Returns:
        JSON 格式的压力数据
    """
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
    }
)
async def garmin_hrv(params: DateInput) -> str:
    """获取指定日期的 HRV（心率变异性）数据。

    HRV 是评估恢复状态和训练准备度的关键指标。

    Args:
        params: 包含日期参数

    Returns:
        JSON 格式的 HRV 数据
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
    }
)
async def garmin_body_battery(params: DateInput) -> str:
    """获取指定日期的 Body Battery（身体电量）数据。

    Body Battery 综合 HRV、压力、活动量和睡眠，评估你的能量水平。

    Args:
        params: 包含日期参数

    Returns:
        JSON 格式的 Body Battery 数据
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
    }
)
async def garmin_body_composition(params: DateInput) -> str:
    """获取指定日期的身体成分数据。

    包含：体重、体脂率、肌肉量、BMI 等。

    Args:
        params: 包含日期参数

    Returns:
        JSON 格式的身体成分数据
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
    }
)
async def garmin_training_status(params: DateInput) -> str:
    """获取训练状态和最大摄氧量（VO2 Max）数据。

    Args:
        params: 包含日期参数

    Returns:
        JSON 格式的训练状态数据
    """
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
    }
)
async def garmin_max_metrics(params: DateInput) -> str:
    """获取最大指标数据，包括 VO2 Max 和体适能年龄。

    Args:
        params: 包含日期参数

    Returns:
        JSON 格式的最大指标数据
    """
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
    }
)
async def garmin_activities(params: ActivitiesInput) -> str:
    """获取最近的训练活动列表。

    包含：活动类型、时间、距离、配速、心率等摘要信息。

    Args:
        params: 包含分页参数（limit, start）

    Returns:
        JSON 格式的活动列表
    """
    try:
        client = get_client()
        data = client.get_activities(params.start, params.limit)
        # 精简输出，只保留关键字段
        summary = []
        for act in data:
            summary.append({
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
            })
        return json.dumps(summary, indent=2, default=str)
    except Exception as e:
        return f"Error: {e}"


@mcp.tool(
    name="garmin_activity_detail",
    annotations={
        "title": "活动详情",
        "readOnlyHint": True,
        "destructiveHint": False,
    }
)
async def garmin_activity_detail(activity_id: str) -> str:
    """获取单个活动的详细数据。

    需要先用 garmin_activities 获取 activityId。

    Args:
        activity_id: Garmin 活动 ID

    Returns:
        JSON 格式的活动详情
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
    }
)
async def garmin_activity_splits(activity_id: str) -> str:
    """获取活动的分段/配速数据（如每公里配速）。

    Args:
        activity_id: Garmin 活动 ID

    Returns:
        JSON 格式的分段数据
    """
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
    }
)
async def garmin_activity_hr_zones(activity_id: str) -> str:
    """获取活动的心率区间分布（Zone 1-5 各多长时间）。

    Args:
        activity_id: Garmin 活动 ID

    Returns:
        JSON 格式的心率区间数据
    """
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
    }
)
async def garmin_personal_records(owner_display_name: str) -> str:
    """获取个人运动记录（PR）。

    Args:
        owner_display_name: Garmin Connect 显示名称

    Returns:
        JSON 格式的个人记录
    """
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
    }
)
async def garmin_race_predictions() -> str:
    """获取 Garmin 基于你当前体能的比赛成绩预测。

    包含 5K、10K、半马、全马的预测完赛时间。

    Returns:
        JSON 格式的比赛预测数据
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
    }
)
async def garmin_devices() -> str:
    """获取已连接的 Garmin 设备信息。

    Returns:
        JSON 格式的设备列表
    """
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
    }
)
async def garmin_weekly_summary(params: DateInput) -> str:
    """获取本周训练和健康数据的综合摘要。

    汇总最近 7 天的关键指标：活动总量、平均睡眠、心率趋势等。

    Args:
        params: 包含参考日期（默认今天，会回溯 7 天）

    Returns:
        JSON 格式的周摘要
    """
    try:
        client = get_client()
        end = date.fromisoformat(format_date(params.date))
        start = end - timedelta(days=6)

        summary = {
            "period": f"{start.isoformat()} ~ {end.isoformat()}",
            "daily_stats": [],
            "activities": [],
        }

        # 收集每天的摘要
        for i in range(7):
            d = (start + timedelta(days=i)).isoformat()
            try:
                stats = client.get_stats(d)
                summary["daily_stats"].append({
                    "date": d,
                    "steps": stats.get("totalSteps"),
                    "calories": stats.get("totalKilocalories"),
                    "restingHR": stats.get("restingHeartRate"),
                    "stressAvg": stats.get("averageStressLevel"),
                    "sleepHours": round(
                        stats.get("sleepingSeconds", 0) / 3600, 1
                    ),
                    "activeMinutes": stats.get("activeSeconds", 0) // 60,
                })
            except Exception:
                pass

        # 最近活动
        try:
            acts = client.get_activities(0, 20)
            for act in acts:
                act_date = act.get("startTimeLocal", "")[:10]
                if start.isoformat() <= act_date <= end.isoformat():
                    summary["activities"].append({
                        "name": act.get("activityName"),
                        "type": act.get("activityType", {}).get("typeKey"),
                        "date": act_date,
                        "duration_min": round(
                            act.get("duration", 0) / 60, 1
                        ),
                        "distance_km": round(
                            act.get("distance", 0) / 1000, 2
                        ),
                        "avgHR": act.get("averageHR"),
                        "calories": act.get("calories"),
                    })
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
```

### 步骤 3：首次登录保存 Token

```bash
# 设置环境变量
export GARMIN_EMAIL="你的邮箱"
export GARMIN_PASSWORD="你的密码"

# 运行一次确保 token 保存成功
python -c "
from garminconnect import Garmin
import os
client = Garmin(os.environ['GARMIN_EMAIL'], os.environ['GARMIN_PASSWORD'])
client.login('~/.garminconnect')
print('✅ Token 已保存到 ~/.garminconnect/')
"
```

### 步骤 4：配置 Claude Desktop

编辑配置文件，添加：

```json
{
  "mcpServers": {
    "garmin": {
      "command": "python",
      "args": ["/你的路径/garmin_mcp_server.py"],
      "env": {
        "GARMIN_EMAIL": "你的邮箱",
        "GARMIN_PASSWORD": "你的密码"
      }
    }
  }
}
```

### 步骤 5：重启 Claude Desktop，开始使用

---

## 可以问 Claude 的问题示例

搭建完成后，试试这些问题：

### 日常健康
- "我今天的健康数据怎么样？"
- "昨晚睡眠质量如何？深睡时间够吗？"
- "我最近一周的压力水平趋势是什么？"
- "我的 Body Battery 现在还有多少？"

### 训练分析
- "列出我最近 10 次跑步训练"
- "分析我上次跑步的配速和心率关系"
- "我最近的有氧训练效果如何？"
- "基于我的 VO2Max，预测我的半马成绩"

### 综合建议
- "根据我的 HRV 和睡眠数据，今天适合做什么训练？"
- "帮我总结这一周的训练和恢复情况"
- "我的静息心率最近有下降趋势吗？说明了什么？"
- "对比我最近 5 次跑步，哪次表现最好？为什么？"

---

## 常见问题

### Q: Token 过期怎么办？
garminconnect 库会自动刷新 token。如果遇到认证错误，重新运行登录脚本即可。

### Q: MFA 验证怎么处理？
首次登录时在终端输入 MFA 验证码。Token 保存后，后续使用不需要再输入。

### Q: 可以用 Claude.ai 网页版吗？
目前 MCP Server 主要支持 Claude Desktop 应用。网页版的 MCP 支持还在发展中。
如果你想在 claude.ai 使用，可以考虑：
1. 定期导出数据为 CSV 上传
2. 部署为远程 MCP Server（需要公网地址）

### Q: 数据安全吗？
- 所有数据存储在你本地
- MCP Server 运行在你的电脑上
- 没有数据发送到第三方服务器
- 建议使用环境变量存储密码，不要硬编码

### Q: Garmin 会不会封号？
这些库使用的是与 Garmin 官方 App 相同的认证方式。正常使用查询数据不会触发封号，但建议：
- 不要过于频繁地调用 API
- 不要并发大量请求
- 使用本地数据库缓存（方案 A）可以减少 API 调用
