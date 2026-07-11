"""
每日报告推送脚本
包含：问好 → 天气/注意事项 → 今日目标 → 长期目标
通过 Server酱 发送到微信 · GitHub Actions 每日定时触发
"""

import os
import json
import urllib.request
import urllib.parse
from datetime import datetime, timezone, timedelta
from pathlib import Path


# ── 天气 ──────────────────────────────────────────────

def fetch_weather(city: str) -> dict:
    """wttr.in 免费天气 API，无需密钥"""
    url = f"https://wttr.in/{urllib.parse.quote(city)}?format=j1"
    req = urllib.request.Request(url, headers={"User-Agent": "daily-report/1.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))


def weather_notes(weather: dict) -> list[str]:
    """根据天气数据生成注意事项"""
    notes = []
    try:
        cur = weather["current_condition"][0]
        temp_c = int(cur["temp_C"])
        humidity = int(cur["humidity"])
        uv = int(cur["uvIndex"])
        weather_desc = cur["weatherDesc"][0]["value"].lower()
        windspeed = int(cur["windspeedKmph"])

        if "rain" in weather_desc or "drizzle" in weather_desc or "shower" in weather_desc:
            notes.append("今日有雨，出门记得带伞")
        if temp_c >= 35:
            notes.append("高温预警，注意防暑，减少户外活动")
        elif temp_c >= 30:
            notes.append("天气较热，注意补充水分")
        elif temp_c <= 10:
            notes.append("气温偏低，注意保暖")
        if uv >= 6:
            notes.append("紫外线强，外出注意防晒")
        if humidity >= 85:
            notes.append("湿度较大，体感闷热")
        if windspeed >= 30:
            notes.append("风力较大，注意出行安全")
        if not notes:
            notes.append("天气不错，适合出门")
    except Exception:
        notes.append("天气数据解析异常，请自行判断")
    return notes


def format_weather(weather: dict) -> str:
    """格式化天气信息"""
    try:
        cur = weather["current_condition"][0]
        fc = weather["weather"][0]
        return (
            f"**🌤 {cur['weatherDesc'][0]['value']}  {cur['temp_C']}°C**  "
            f"体感 {cur['FeelsLikeC']}°C  |  湿度 {cur['humidity']}%  |  风力 {cur['windspeedKmph']}km/h\n"
            f"🌡 今日 {fc['mintempC']}°C ~ {fc['maxtempC']}°C  |  UV指数 {cur['uvIndex']}"
        )
    except Exception:
        return "天气数据获取失败"


def format_weather_narrative(weather: dict) -> str:
    """口述风格天气"""
    try:
        cur = weather["current_condition"][0]
        fc = weather["weather"][0]
        desc = cur["weatherDesc"][0]["value"]
        temp = cur["temp_C"]
        feels = cur["FeelsLikeC"]
        hi = fc["maxtempC"]
        lo = fc["mintempC"]
        uv = cur["uvIndex"]
        hum = cur["humidity"]

        uv_text = {0:"无", 1:"极低", 2:"低", 3:"中等", 4:"中等", 5:"中高", 6:"高", 7:"很高", 8:"很高", 9:"极高", 10:"极高", 11:"极端"}.get(uv, str(uv))
        return f"{desc}，{temp}度，体感{feels}，湿度百分之{hum}，UV{uv_text}。今日{lo}到{hi}度"
    except Exception:
        return "天气数据获取失败"


# ── 目标 ──────────────────────────────────────────────

def load_tasks(tasks_path: str) -> dict:
    """加载任务数据"""
    with open(tasks_path, "r", encoding="utf-8") as f:
        return json.load(f)


def format_tasks(tasks: dict, weekday_str: str) -> str:
    """格式化今日目标"""
    lines = []

    # 每日任务
    if tasks.get("daily"):
        for i, t in enumerate(tasks["daily"], 1):
            lines.append(f"{i}. {t}")

    # 星期任务
    week_key = f"周{weekday_str}"
    weekly = tasks.get("weekly", {})
    if week_key in weekly:
        for t in weekly[week_key]:
            lines.append(f"📌 {t}")

    return "\n".join(lines) if lines else "暂无安排"


def get_tasks_list(tasks: dict, weekday_str: str) -> list[str]:
    """提取今日任务为列表"""
    items = list(tasks.get("daily", []))
    week_key = f"周{weekday_str}"
    weekly = tasks.get("weekly", {})
    if week_key in weekly:
        items.extend(weekly[week_key])
    return items


def format_long_term(tasks: dict) -> str:
    """格式化长期目标"""
    lt = tasks.get("long_term", [])
    if not lt:
        return "暂无"
    return "\n".join(f"▸ {t}" for t in lt)


# ── 照片 ──────────────────────────────────────────────

PHOTO_URL = "https://raw.githubusercontent.com/dhusuw/-/main/%E6%AF%8F%E6%97%A5%E9%97%AE%E5%80%99/50_transparent.png"


# ── 发送 ──────────────────────────────────────────────

def send_serverchan(sendkey: str, title: str, desp: str) -> dict:
    url = f"https://sctapi.ftqq.com/{sendkey}.send"
    data = urllib.parse.urlencode({"title": title, "desp": desp}).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))


# ── 主流程 ────────────────────────────────────────────

def main():
    sendkey = os.environ["SCT_SENDKEY"]
    city = os.environ.get("MSG_CITY", "Guangzhou")
    script_dir = Path(__file__).parent
    tasks_path = script_dir / "tasks.json"

    now = datetime.now(timezone(timedelta(hours=8)))
    date_str = now.strftime("%Y-%m-%d")
    weekday_str = ["一", "二", "三", "四", "五", "六", "日"][now.weekday()]
    time_str = now.strftime("%H:%M")

    # 1. 天气
    weather = fetch_weather(city)
    notes = weather_notes(weather)

    # 2. 目标
    tasks = load_tasks(str(tasks_path))

    # 3. 组装口述简报
    title = f"HK416 · {date_str} 简报"

    # 天气一句话
    weather_line = format_weather_narrative(weather)

    # 注意事项
    notes_line = "；".join(notes) if notes else "天气正常，无需特别注意。"

    # 今日任务
    tasks_list = get_tasks_list(tasks, weekday_str)
    tasks_line = "、".join(tasks_list) if tasks_list else "暂无安排"

    # 长期目标
    lt_list = tasks.get("long_term", [])
    lt_line = "、".join(lt_list) if lt_list else "无"

    desp = f"""![HK416]({PHOTO_URL}) 早。

{date_str} 星期{weekday_str} {time_str}

{city}。{weather_line}。{notes_line}

今天要做的事：{tasks_line}。

别忘了：{lt_line}。

……别死了。"""

    result = send_serverchan(sendkey, title, desp)
    print(f"推送结果: {result}")

    if result.get("code") != 0:
        raise SystemExit(f"推送失败: {result}")


if __name__ == "__main__":
    main()
