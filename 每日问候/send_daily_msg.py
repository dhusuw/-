"""
每日报告推送脚本
PIL渲染：人物左 + 文字右 → 单张图片 → Server酱推送
GitHub Actions 每日定时触发
"""

import os
import json
import urllib.request
import urllib.parse
from datetime import datetime, timezone, timedelta
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont


# ── 配置 ──────────────────────────────────────────────

PHOTO_FILE = "50_transparent.png"
REPORT_FILE = "daily_report.png"
IMG_W = 150
CANVAS_W = 800
CANVAS_H = 390
PAD = 20
TEXT_X = IMG_W + PAD + 15


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
            notes.append("天气不错，适合出门")
    except Exception:
        notes.append("天气数据异常")
    return notes


def weather_narrative(weather: dict) -> str:
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
        uv_text = {0:"无",1:"极低",2:"低",3:"中等",4:"中等",5:"中高",6:"高",7:"很高",8:"很高",9:"极高",10:"极高",11:"极端"}.get(uv, str(uv))
        return f"{desc}，{temp}° 体感{feels}°  湿度{hum}%  UV{uv_text}  {lo}°~{hi}°"
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


# ── 字体 ──────────────────────────────────────────────

def get_font(size: int) -> ImageFont.FreeTypeFont:
    candidates = [
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf",
        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
        "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/simsun.ttc",
        "C:/Windows/Fonts/simhei.ttf",
    ]
    for p in candidates:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


# ── 渲染 ──────────────────────────────────────────────

def render_report(
    photo_path: str,
    output_path: str,
    date_str: str,
    weekday_str: str,
    time_str: str,
    city: str,
    weather_str: str,
    notes: list[str],
    tasks_line: str,
    lt_line: str,
):
    img = Image.new("RGBA", (CANVAS_W, CANVAS_H), (18, 18, 24, 255))
    draw = ImageDraw.Draw(img)

    # 人物照片
    try:
        photo = Image.open(photo_path)
        if photo.mode != "RGBA":
            photo = photo.convert("RGBA")
        ph = int(IMG_W * photo.height / photo.width)
        photo = photo.resize((IMG_W, ph), Image.LANCZOS)
        img.paste(photo, (PAD, PAD), photo)
    except Exception:
        pass

    font_large = get_font(32)
    font_mid = get_font(20)
    font_small = get_font(17)
    white = (240, 240, 240, 255)
    grey = (180, 180, 190, 255)
    accent = (120, 200, 255, 255)

    y = PAD + 5

    # 问候
    draw.text((TEXT_X, y), "早。", font=font_large, fill=white)
    y += 45

    # 日期时间
    draw.text((TEXT_X, y), f"{date_str}  星期{weekday_str}  {time_str}", font=font_mid, fill=grey)
    y += 35

    # 分隔线
    y += 5
    draw.line([(TEXT_X, y), (CANVAS_W - PAD, y)], fill=(60, 60, 70, 255), width=1)
    y += 15

    # 天气
    draw.text((TEXT_X, y), f"{city}  {weather_str}", font=font_small, fill=white)
    y += 28

    # 注意事项
    notes_str = "  ·  ".join(notes)
    draw.text((TEXT_X, y), notes_str, font=font_small, fill=accent)
    y += 35

    # 分隔线
    draw.line([(TEXT_X, y), (CANVAS_W - PAD, y)], fill=(60, 60, 70, 255), width=1)
    y += 15

    # 今日事项
    draw.text((TEXT_X, y), "今日事项", font=font_mid, fill=accent)
    y += 30
    draw.text((TEXT_X, y), tasks_line, font=font_small, fill=white)
    y += 35

    # 别忘了
    draw.text((TEXT_X, y), "别忘了", font=font_mid, fill=accent)
    y += 30
    draw.text((TEXT_X, y), lt_line, font=font_small, fill=grey)
    y += 38

    # 结尾
    draw.text((TEXT_X, y), "……别死了。", font=font_small, fill=(150, 150, 160, 255))

    img.save(output_path, "PNG", optimize=True)
    print(f"报告已渲染: {output_path} ({img.size})")


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
    photo_path = script_dir / PHOTO_FILE
    report_path = script_dir / REPORT_FILE

    now = datetime.now(timezone(timedelta(hours=8)))
    date_str = now.strftime("%Y-%m-%d")
    weekday_str = ["一", "二", "三", "四", "五", "六", "日"][now.weekday()]
    time_str = now.strftime("%H:%M")

    weather = fetch_weather(city)
    notes = weather_notes(weather)
    weather_str = weather_narrative(weather)
    tasks = load_tasks(str(tasks_path))
    tasks_list = get_tasks_list(tasks, weekday_str)
    tasks_line = "、".join(tasks_list) if tasks_list else "暂无安排"
    lt_list = tasks.get("long_term", [])
    lt_line = "、".join(lt_list) if lt_list else "无"

    # 渲染报告图片
    render_report(
        str(photo_path), str(report_path),
        date_str, weekday_str, time_str, city,
        weather_str, notes, tasks_line, lt_line,
    )

    # 推到仓库（GH_PAT 已在 workflow 中注入）
    gh_pat = os.environ.get("GH_PAT", "")
    remote_url = f"https://dhusuw:{gh_pat}@github.com/dhusuw/-.git"
    os.chdir(str(script_dir))
    os.system(f"git add {REPORT_FILE}")
    os.system(f"git diff --cached --quiet || git commit -m \"daily report\"")
    os.system(f"git push {remote_url} main")

    # 图片 URL
    encoded = "%E6%AF%8F%E6%97%A5%E9%97%AE%E5%80%99"
    img_url = f"https://raw.githubusercontent.com/dhusuw/-/main/{encoded}/{REPORT_FILE}?ts={now.strftime('%H%M%S')}"

    title = f"HK416 · {date_str}"
    desp = f"![report]({img_url})"

    result = send_serverchan(sendkey, title, desp)
    print(f"推送结果: {result}")
    if result.get("code") != 0:
        raise SystemExit(f"推送失败: {result}")


if __name__ == "__main__":
    main()
