# 每日问候 - HK416 晨间简报

每天自动推送一份 HK416 风格的早安报告到微信，包含天气、今日事项、长期目标。

---

## 文件结构

```
每日问候/
├── send_daily_msg.py      # 推送脚本（天气+任务+渲染消息）
├── tasks.json             # 任务数据（每日/每周/长期）
├── 50_transparent.png     # HK416 透明照片（150x277）
├── 50.webp                # 原始照片备份
└── README.md              # 本说明
```

工作流：`.github/workflows/daily-message.yml`

---

## 消息内容

```
[HK416透明照片]

早。

2026-07-12 星期六 08:00

Guangzhou。晴，37度，体感42...。高温预警；紫外线强。

今天要做的事：跑步30分钟、学习Agent。

别忘了：AI小说第一章、学习贝斯、交通职业学习。

……别死了。
```

---

## 配置说明

### 修改任务 → `tasks.json`

```json
{
  "daily": ["跑步30分钟", "学习Agent"],
  "weekly": {
    "周一": ["组会"],
    "周二": [...],
    ...
  },
  "long_term": ["AI小说第一章", "学习贝斯", "交通职业学习"]
}
```

### 修改城市 → workflow 中 MSG_CITY

### 修改语气/布局 → `send_daily_msg.py` 中的 `desp` 部分

---

## 技术栈

| 组件 | 说明 |
|------|------|
| 天气 | wttr.in 免费API，无需密钥 |
| 推送 | Server酱 Turbo (sctapi.ftqq.com) |
| 定时 | GitHub Actions cron (schedule) |
| 照片 | 透明PNG，GitHub raw CDN |
| 语言 | Python 3，纯标准库（除PIL用于本地测试） |

---

## 定时配置

| 时间 | Cron | UTC |
|------|------|-----|
| 09:07 | `7 1 * * *` | 01:07 |
| 12:07 | `7 4 * * *` | 04:07 |
| 18:07 | `7 10 * * *` | 10:07 |

`workflow_dispatch` 手动触发：随时可用。

---

## 已知问题

- **GitHub Actions schedule 首次激活可能延迟24小时**，今天（7/12）定时未触发，手动发送正常
- **本机443端口被封**，git push 需要走 API 或等待网络恢复
- Server酱 **不支持HTML**，仅Markdown，文字环绕图片无法实现
- 仓库已设为**公开**（照片需要外网访问）

---

## API密钥

| 密钥 | 存储位置 | 用途 |
|------|----------|------|
| SCT_SENDKEY | GitHub Secret | Server酱推送 |
| GH_PAT | GitHub Secret | 图片推送回仓库（当前简化版未用） |

---

## 手动测试

```bash
# 触发GitHub Actions
# 或直接运行
cd 每日问候
SCT_SENDKEY=你的密钥 MSG_CITY=Guangzhou python send_daily_msg.py
```

---

## 链接

- 仓库：https://github.com/dhusuw/-
- Server酱：https://sct.ftqq.com/
- 天气API：https://wttr.in/Guangzhou?format=j1
- 照片URL：https://raw.githubusercontent.com/dhusuw/-/main/%E6%AF%8F%E6%97%A5%E9%97%AE%E5%80%99/50_transparent.png
