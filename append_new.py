#!/usr/bin/env python3
"""append_new.py — 将 loveforever.md 提取的条目安全追加到 youcat_master.json。
不覆盖原有数据，只做 .extend() 追加。"""

import json
import os
import re
import sys
import time
import requests

# ── 配置 ──────────────────────────────────────────────
API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
API_URL = "https://api.deepseek.com/chat/completions"
MODEL = "deepseek-chat"
CHUNK_SIZE = 3000
MIN_CHUNK = 80
CALL_INTERVAL = 0.6
MAX_RETRIES = 3

SRC_FILE = "loveforever.md"
JSON_FILE = "youcat_master.json"
BACKUP_FILE = "youcat_master_before_append.backup.json"

# ── 工具函数 ──────────────────────────────────────────

def clean_text(text: str) -> str:
    """去掉 HTML / markdown 噪音，保留纯文本。"""
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'!\[.*?\]\(.*?\)', '', text)
    text = re.sub(r'\[\]\{#.*?\}', '', text)
    text = re.sub(r'\{[=.]?\w+\}', '', text)
    text = re.sub(r'`</?\w+>`', '', text)
    text = re.sub(r'^\s*images/[\w./-]+\s*$', '', text, flags=re.MULTILINE)
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r'^[ \t]+', '', text, flags=re.MULTILINE)
    return text.strip()


def chunk_text(text: str, size: int = CHUNK_SIZE) -> list:
    """按段落边界切块，~size 字符。"""
    paragraphs = text.split('\n\n')
    chunks = []
    buf = ""
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        if len(buf) + len(para) + 2 <= size:
            buf = (buf + '\n\n' + para) if buf else para
        else:
            if len(buf) >= MIN_CHUNK:
                chunks.append(buf)
            if len(para) > size:
                for j in range(0, len(para), size):
                    piece = para[j:j+size].strip()
                    if len(piece) >= MIN_CHUNK:
                        chunks.append(piece)
                buf = ""
            else:
                buf = para
    if buf and len(buf) >= MIN_CHUNK:
        chunks.append(buf)
    return chunks


# ── DeepSeek API ──────────────────────────────────────

SYSTEM_PROMPT = (
    "你是一位天主教教理数据提取专家。请从提供的文本中提取结构化条目。\n\n"
    "对于文本中每一个独立的概念、主题或教理观点，创建一个包含以下字段的条目：\n"
    '- topic_category: 大类，如"婚姻"、"爱与身份"、"孤独"、"订婚"、"家庭"、"道德生活"等\n'
    '- concept: 具体概念或主题（中文）\n'
    '- reference_id: 条目编号（如有），否则写"无"\n'
    '- theological_definition: 教理层面的深度定义和解释\n'
    '- scripture_and_history: 相关的圣经引用或历史背景\n'
    '- ethical_application: 伦理教化和现实生活道德准则的延伸\n'
    '- location_tags: 相关的历史地理位置英文名数组，如["Rome","Jerusalem"]，无则为[]\n\n'
    '只返回纯 JSON，格式如下：\n'
    '{"entries":[{"topic_category":"...","concept":"...","reference_id":"...",'
    '"theological_definition":"...","scripture_and_history":"...",'
    '"ethical_application":"...","location_tags":[...]}]}\n\n'
    '请尽量提取所有不同的条目。如果文本中没有可提取的条目，返回{"entries":[]}。'
)


def call_api(chunk: str) -> dict:
    """调用 DeepSeek API，返回解析后的 JSON。"""
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"请从以下文本提取所有天主教教理条目，返回 JSON：\n\n{chunk}"},
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.2,
        "max_tokens": 4096,
    }
    session = requests.Session()
    session.trust_env = False

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = session.post(API_URL, headers=headers, json=payload,
                                timeout=180, proxies={})
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            return json.loads(content)
        except Exception as e:
            if attempt < MAX_RETRIES:
                print(f"    重试 {attempt}/{MAX_RETRIES}: {e}")
                time.sleep(3 * attempt)
            else:
                raise


# ── 主流程 ────────────────────────────────────────────

def main():
    # 1. 加载现有数据库
    if not os.path.exists(JSON_FILE):
        print(f"[错误] 找不到 {JSON_FILE}，请先确认文件存在")
        sys.exit(1)

    with open(JSON_FILE, 'r', encoding='utf-8') as f:
        db = json.load(f)
    old_entries = db.get("entries", [])
    print(f"[1/4] 已加载现有数据: {len(old_entries)} 条记录")

    # 2. 备份原文件
    import shutil
    shutil.copy2(JSON_FILE, BACKUP_FILE)
    print(f"[2/4] 已备份原文件到: {BACKUP_FILE}")

    # 3. 读取并切块新文件
    if not os.path.exists(SRC_FILE):
        print(f"[错误] 找不到 {SRC_FILE}")
        sys.exit(1)

    with open(SRC_FILE, 'r', encoding='utf-8') as f:
        raw = f.read()
    cleaned = clean_text(raw)
    chunks = chunk_text(cleaned)
    print(f"[3/4] 新文件切为 {len(chunks)} 块，开始提取...")
    print(f"{'='*50}")

    new_entries = []
    for i, chunk in enumerate(chunks):
        pct = ((i+1) / len(chunks)) * 100
        print(f"  [{i+1}/{len(chunks)} {pct:.1f}%] ({len(chunk)} chars)...",
              end=" ", flush=True)

        try:
            result = call_api(chunk)
            entries = result.get("entries", [])
            if entries:
                new_entries.extend(entries)
                print(f"OK +{len(entries)}")
            else:
                print("- none")
        except Exception as e:
            print(f"ERR: {e}")

        time.sleep(CALL_INTERVAL)

    print(f"{'='*50}")
    print(f"  新提取条目: {len(new_entries)} 条")

    # 4. 合并并写回
    all_entries = old_entries + new_entries
    with open(JSON_FILE, 'w', encoding='utf-8') as f:
        json.dump({"entries": all_entries}, f, ensure_ascii=False, indent=2)

    # 打印文件大小
    new_size = os.path.getsize(JSON_FILE) / 1024
    print(f"[4/4] 已写回 {JSON_FILE}")
    print(f"      旧条目: {len(old_entries)} + 新增: {len(new_entries)} = 总计: {len(all_entries)}")
    print(f"      文件大小: {new_size:.0f} KB")
    print(f"      备份保留在: {BACKUP_FILE}")


if __name__ == "__main__":
    main()
