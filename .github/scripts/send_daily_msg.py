"""
每日消息推送脚本
通过 Server酱 (ServerChan) 发送消息到微信
GitHub Actions 每日定时触发
"""

import os
import json
import urllib.request
import urllib.parse
from datetime import datetime, timezone, timedelta


def send_serverchan(sendkey: str, title: str, desp: str = "") -> dict:
    """
    Server酱 Turbo 推送
    https://sct.ftqq.com/
    """
    url = f"https://sctapi.ftqq.com/{sendkey}.send"
    data = urllib.parse.urlencode({"title": title, "desp": desp}).encode("utf-8")

    req = urllib.request.Request(url, data=data, method="POST")
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main():
    sendkey = os.environ["SCT_SENDKEY"]
    title = os.environ.get("MSG_TITLE", "每日推送")
    desp = os.environ.get("MSG_DESP", "")

    # 模板变量替换
    now = datetime.now(timezone(timedelta(hours=8)))
    vars_map = {
        "{{ date }}": now.strftime("%Y-%m-%d"),
        "{{ time }}": now.strftime("%H:%M"),
        "{{ weekday }}": ["一", "二", "三", "四", "五", "六", "日"][now.weekday()],
    }
    for key, val in vars_map.items():
        title = title.replace(key, val)
        desp = desp.replace(key, val)

    result = send_serverchan(sendkey, title, desp)
    print(f"推送结果: {result}")

    if result.get("code") != 0:
        raise SystemExit(f"推送失败: {result}")


if __name__ == "__main__":
    main()
