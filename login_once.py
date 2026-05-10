"""一次性登录 Garmin Connect，将 token 保存到本地（默认 ~/.garminconnect）。"""

import os
import sys
from pathlib import Path

from garminconnect import (
    Garmin,
    GarminConnectAuthenticationError,
    GarminConnectConnectionError,
    GarminConnectTooManyRequestsError,
)

TOKEN_DIR = os.path.expanduser(os.environ.get("GARMIN_TOKEN_DIR", "~/.garminconnect"))


def main() -> None:
    email = os.environ.get("GARMIN_EMAIL", "").strip()
    password = os.environ.get("GARMIN_PASSWORD", "")
    if not email or not password:
        print(
            "请设置环境变量 GARMIN_EMAIL 与 GARMIN_PASSWORD 后重试。",
            file=sys.stderr,
        )
        sys.exit(1)

    token_path = str(Path(TOKEN_DIR).expanduser().resolve())
    client = Garmin(email, password)

    try:
        mfa_pending, _ = client.login(token_path)
    except GarminConnectTooManyRequestsError as e:
        print(
            "Garmin 返回频率限制（429），所有登录方式都未成功。\n"
            "可过 15～60 分钟再试，或换网络/IP（例如手机热点），避免短时间内重复运行登录脚本。",
            file=sys.stderr,
        )
        print(f"详情: {e}", file=sys.stderr)
        sys.exit(1)
    except GarminConnectAuthenticationError as e:
        print(f"账号或验证失败: {e}", file=sys.stderr)
        sys.exit(1)
    except GarminConnectConnectionError as e:
        print(f"网络或 Garmin 服务异常: {e}", file=sys.stderr)
        sys.exit(1)

    if mfa_pending:
        print(
            "需要完成 MFA（多因素验证）。请在交互式终端按库提示输入验证码，"
            "或使用支持 MFA 的流程。",
            file=sys.stderr,
        )
        sys.exit(2)

    print("登录成功，token 已保存。")
    print(f"  目录: {token_path}")
    print(f"  显示名: {getattr(client, 'display_name', '') or '(未返回)'}")
    print(
        "\n说明: 日志里若出现「mobile … 429」，表示手机端登录接口被限流；"
        "库会继续尝试网页等其它方式。只要出现本脚本的「登录成功」，会话一般可用。"
    )


if __name__ == "__main__":
    main()
