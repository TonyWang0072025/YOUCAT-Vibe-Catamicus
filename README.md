<div align="center">
  <img src="guider.svg" alt="YOUCAT Vibe" width="120" />
  <h1>YOUCAT Vibe</h1>
  <p><em>Youth Catechism · AI Ethics Guide · 给年轻人的天主教宗教学 AI 向导</em></p>

  <p>
    <img src="https://img.shields.io/badge/python-3.10+-blue.svg" alt="Python">
    <img src="https://img.shields.io/badge/fastapi-0.100+-green.svg" alt="FastAPI">
    <img src="https://img.shields.io/badge/license-MIT-yellow.svg" alt="License">
    <img src="https://img.shields.io/badge/docker-ready-brightgreen.svg" alt="Docker">
  </p>
</div>

---

## English

### What is YOUCAT Vibe?

YOUCAT Vibe is a **Vibe Coding experiment** that brings the *Youth Catechism of the Catholic Church* (YOUCAT) to life through AI. It combines:

- **RAG-powered Q&A** — Ask anything about faith, ethics, or Church teaching. **Catamicus**, an AI mentor powered by DeepSeek, answers warmly using real YOUCAT knowledge fragments.
- **Interactive Holy Land Map** — Locations mentioned in conversations (Jerusalem, Rome, Assisi…) are automatically pinned on a Leaflet map.
- **Liturgical Calendar** — Browse the full Catholic liturgical year with proper colors (white, green, red, violet, rose) for each celebration.
- **Daily Wisdom** — A random quote from the YOUCAT ethical-application corpus, with bilingual (Chinese / English) support.
- **Full-text Search** — Search the entire YOUCAT knowledge base by concept, definition, or ethical application.

> Built with FastAPI + vanilla HTML/JS/Tailwind. No heavy frontend framework. Pure vibes.

### Quick Start

#### Option 1: Local venv

```bash
# Clone
git clone https://github.com/TonyWang0072025/youcat-vibe.git
cd YOUCAT-Vibe-Catamicus

# Create virtual environment
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set your DeepSeek API key
export DEEPSEEK_API_KEY="sk-your-key-here"   # Windows: set DEEPSEEK_API_KEY=sk-your-key-here

# Launch
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Then open **http://localhost:8000.

#### Option 2: Docker (recommended)

```bash
# Clone
git clone https://github.com/YOUR_USERNAME/youcat-vibe.git
cd youcat-vibe

# Create .env file with your API key
echo "DEEPSEEK_API_KEY=sk-your-key-here" > .env

# One-click start
docker-compose up -d
```

Then open **http://localhost:8000.

### Project Structure

```
youcat-vibe/
├── main.py                  # FastAPI backend (RAG, chat, calendar, quotes)
├── templates/
│   └── index.html           # Single-page frontend (vanilla JS + Tailwind + Leaflet)
├── youcat_master.json       # Structured YOUCAT knowledge base
├── calender/                # Liturgical calendar JSON files (by year)
├── static/tiles/            # Offline map tiles (optional)
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── .env.example
```

### Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python · FastAPI · Uvicorn |
| AI | DeepSeek Chat API (RAG) |
| Frontend | Vanilla HTML5 · CSS3 · JavaScript · Tailwind CSS |
| Map | Leaflet.js · OpenStreetMap |
| DevOps | Docker · Docker Compose · GitHub Actions |

### Environment Variables

| Variable | Required | Description |
|---|---|---|
| `DEEPSEEK_API_KEY` | Yes | Your DeepSeek API key |

Copy `.env.example` to `.env` and fill in your key.

---

## 中文

### 项目简介

YOUCAT Vibe 是一个 **Vibe Coding 实验项目**，它将《天主教青年教理》（YOUCAT）与 AI 技术相结合，打造了一个沉浸式的信仰探索工具：

- **RAG 智能问答** — 向 AI 导师 **卡米克斯 (Catamicus)** 提出任何关于信仰、伦理或教会教理的问题，基于真实的 YOUCAT 知识库片段作答。
- **圣地图览** — 对话中提及的地点（耶路撒冷、罗马、亚西西…）自动标记在交互式 Leaflet 地图上。
- **礼仪月历** — 浏览完整的天主教礼仪年，每个庆典都标注了对应的礼仪颜色（白、绿、红、紫、玫瑰）。
- **今日箴言** — 从 YOUCAT 伦理应用语料中随机抽取一条箴言，支持中英双语切换。
- **知识库全文搜索** — 按概念、教理定义或伦理应用搜索整个 YOUCAT 数据库。

> 技术栈：FastAPI + 原生 HTML/JS/Tailwind。无重型前端框架，纯 Vibe。

### 快速开始

#### 方式一：本地 venv

```bash
git clone https://github.com/YOUR_USERNAME/youcat-vibe.git
cd youcat-vibe

python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

pip install -r requirements.txt

# 设置 DeepSeek API Key
export DEEPSEEK_API_KEY="sk-your-key-here"   # Windows: set DEEPSEEK_API_KEY=sk-your-key-here

uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

浏览器打开 **http://localhost:8000

#### 方式二：Docker（推荐）

```bash
git clone https://github.com/YOUR_USERNAME/youcat-vibe.git
cd youcat-vibe

echo "DEEPSEEK_API_KEY=sk-your-key-here" > .env

docker-compose up -d
```

浏览器打开 **http://localhost:8000

### 项目结构

```
youcat-vibe/
├── main.py                  # FastAPI 后端（RAG、聊天、日历、箴言）
├── templates/
│   └── index.html           # 单页前端（原生 JS + Tailwind + Leaflet）
├── youcat_master.json       # 结构化 YOUCAT 知识库
├── calender/                # 礼仪年历 JSON 文件（按年）
├── static/tiles/            # 离线地图瓦片（可选）
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── .env.example
```

### 环境变量

| 变量 | 必填 | 说明 |
|---|---|---|
| `DEEPSEEK_API_KEY` | 是 | 你的 DeepSeek API 密钥 |

将 `.env.example` 复制为 `.env` 并填入你的密钥。

---

## License

MIT © 2025

---

<div align="center">
  <sub>Built with ❤️ and ☕ · <em>Vibe Coding since 2025</em></sub>
</div>
