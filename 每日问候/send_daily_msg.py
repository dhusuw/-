"""
每日报告推送脚本
3个时段：早上6:38 / 中午12:07 / 晚上18:07
通过 Server酱 发送到微信 · GitHub Actions 定时触发
"""

import os
import json
import urllib.request
import urllib.parse
from datetime import datetime, timezone, timedelta
from pathlib import Path


# ── 配置 ──────────────────────────────────────────────

PHOTO_URL = "https://raw.githubusercontent.com/dhusuw/-/main/%E6%AF%8F%E6%97%A5%E9%97%AE%E5%80%99/50_transparent.png"


# ── 时段判断 ──────────────────────────────────────────

def get_period(hour: int) -> tuple[str, str]:
    """根据北京时间小时返回 (问候语, 时段标签)"""
    if 5 <= hour < 11:
        return "早上好", "morning"
    elif 11 <= hour < 14:
        return "中午好", "noon"
    else:
        return "晚上好", "evening"


# ── 天气 ──────────────────────────────────────────────

def fetch_weather(city: str) -> dict:
    url = f"https://wttr.in/{urllib.parse.quote(city)}?format=j1"
    req = urllib.request.Request(url, headers={"User-Agent": "daily-report/1.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))


def weather_notes(weather: dict) -> list[str]:
    notes = []
    try:
        cur = weather["current_condition"][0]
        temp_c = int(cur["temp_C"])
        humidity = int(cur["humidity"])
        uv = int(cur["uvIndex"])
        weather_desc = cur["weatherDesc"][0]["value"].lower()
        windspeed = int(cur["windspeedKmph"])
        if "rain" in weather_desc or "drizzle" in weather_desc or "shower" in weather_desc:
            notes.append("有雨，带伞")
        if temp_c >= 35:
            notes.append("高温预警，注意防暑")
        elif temp_c >= 30:
            notes.append("较热，多喝水")
        elif temp_c <= 10:
            notes.append("天冷，保暖")
        if uv >= 6:
            notes.append("紫外线强，防晒")
        if humidity >= 85:
            notes.append("湿度大，闷热")
        if windspeed >= 30:
            notes.append("风大，注意安全")
        if not notes:
            notes.append("天气不错")
    except Exception:
        notes.append("天气数据异常")
    return notes


def format_weather_detailed(weather: dict, period: str) -> str:
    """根据时段输出详细天气"""
    try:
        cur = weather["current_condition"][0]
        fc_today = weather["weather"][0]
        desc = cur["weatherDesc"][0]["value"]
        temp = cur["temp_C"]
        feels = cur["FeelsLikeC"]
        hum = cur["humidity"]
        wind = cur["windspeedKmph"]
        wind_dir = cur["winddir16Point"]
        uv = cur["uvIndex"]
        uv_text = {0:"无",1:"极低",2:"低",3:"中等",4:"中等",5:"中高",6:"高",7:"很高",8:"很高",9:"极高",10:"极高",11:"极端"}.get(uv, str(uv))
        visibility = cur.get("visibility", "?")

        hi = fc_today["maxtempC"]
        lo = fc_today["mintempC"]
        sunrise = fc_today["astronomy"][0].get("sunrise", "?")
        sunset = fc_today["astronomy"][0].get("sunset", "?")

        # 逐小时预报（3小时间隔）
        hourly_lines = []
        for h in fc_today.get("hourly", []):
            h_time = int(h["time"]) // 100  # "600" -> 6
            h_desc = h["weatherDesc"][0]["value"]
            h_temp = h["tempC"]
            h_wind = h["windspeedKmph"]
            h_hum = h["humidity"]
            hourly_lines.append(f"  {h_time:02d}:00  {h_desc}  {h_temp}°C  风{h_wind}km/h  湿度{h_hum}%")

        if period == "morning":
            block = "\n".join(hourly_lines[:4])  # 00-09时
            return (
                f"当前 {desc}，{temp}°C，体感{feels}°C\n"
                f"湿度 {hum}%  |  {wind_dir}风 {wind}km/h  |  UV {uv_text}  |  能见度 {visibility}km\n"
                f"今日 {lo}°C ~ {hi}°C\n"
                f"日出 {sunrise}  |  日落 {sunset}\n\n"
                f"上午逐时：\n{block}"
            )
        elif period == "noon":
            block = "\n".join(hourly_lines[2:6])  # 06-15时
            return (
                f"当前 {desc}，{temp}°C，体感{feels}°C\n"
                f"湿度 {hum}%  |  {wind_dir}风 {wind}km/h  |  UV {uv_text}  |  能见度 {visibility}km\n"
                f"今日最高 {hi}°C  |  最低 {lo}°C\n\n"
                f"午间逐时：\n{block}"
            )
        else:  # evening
            block = "\n".join(hourly_lines[4:])  # 15-24时
            return (
                f"当前 {desc}，{temp}°C，体感{feels}°C\n"
                f"湿度 {hum}%  |  {wind_dir}风 {wind}km/h  |  UV {uv_text}  |  能见度 {visibility}km\n"
                f"今日最高 {hi}°C  |  夜间最低 {lo}°C\n\n"
                f"晚间逐时：\n{block}"
            )
    except Exception:
        return "天气数据获取失败"


# ── 目标 ──────────────────────────────────────────────

def load_tasks(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_tasks_list(tasks: dict, weekday_str: str) -> list[str]:
    items = list(tasks.get("daily", []))
    week_key = f"周{weekday_str}"
    weekly = tasks.get("weekly", {})
    if week_key in weekly:
        items.extend(weekly[week_key])
    return items


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
    hour = now.hour

    # 时段
    greeting, period = get_period(hour)

    # 天气
    weather = fetch_weather(city)
    notes = weather_notes(weather)
    weather_str = format_weather_detailed(weather, period)
    notes_line = "；".join(notes) if notes else "天气正常"

    # 目标
    tasks = load_tasks(str(tasks_path))
    tasks_list = get_tasks_list(tasks, weekday_str)
    tasks_line = "、".join(tasks_list) if tasks_list else "暂无安排"
    lt_list = tasks.get("long_term", [])
    lt_line = "、".join(lt_list) if lt_list else "无"

    # 组装消息
    title = f"HK416 · {greeting}"
    emoji = {"morning": "☀️", "noon": "🌤", "evening": "🌙"}.get(period, "")

    desp = f"""![HK416]({PHOTO_URL})

{greeting}。

{date_str} 星期{weekday_str} {time_str} {emoji}

{city}

{weather_str}

{notes_line}

今天要做的事：{tasks_line}。

别忘了：{lt_line}。

……别死了。"""

    result = send_serverchan(sendkey, title, desp)
    print(f"时段: {period} | 推送结果: {result}")
    if result.get("code") != 0:
        raise SystemExit(f"推送失败: {result}")


if __name__ == "__main__":
    main()
