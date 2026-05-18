#!/usr/bin/env python3
"""build_db.py — 从 md_files 中的 YOUCAT 相关 Markdown 提取结构化 JSON 数据库。
使用 DeepSeek API，纯 requests + stdlib，无第三方 SDK。"""

import os
import re
import json
import time
import sys
import requests

# ── 配置 ──────────────────────────────────────────────
API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
API_URL = "https://api.deepseek.com/chat/completions"
MODEL = "deepseek-chat"
CHUNK_SIZE = 3000          # 每块约 3000 字符
MIN_CHUNK_LEN = 80         # 太短的块跳过
MAX_RETRIES = 3            # 单块失败重试次数
RETRY_DELAY = 3            # 重试等待秒数
CALL_INTERVAL = 0.6        # 调用间隔，避免触发频率限制
SAVE_EVERY = 8             # 每 N 块保存一次进度
OUTPUT_FILE = "youcat_master.json"
PROGRESS_FILE = "build_db_progress.json"
MD_DIR = "md_files"

# ── 清洗函数 ──────────────────────────────────────────
def clean_text(text: str) -> str:
    """去除 HTML 标签、图片引用、calibre 元数据等噪音，保留纯文本。"""
    # 去掉 SVG / image 块
    text = re.sub(r'<svg[^>]*>.*?</svg>', '', text, flags=re.DOTALL)
    # 去掉 HTML 标签
    text = re.sub(r'<[^>]+>', '', text)
    # 去掉 markdown 图片
    text = re.sub(r'!\[.*?\]\(.*?\)', '', text)
    # 去掉 calibre / epub 锚点行
    text = re.sub(r'\[\]\{#.*?\}', '', text)
    # 去掉 \{=html\} 之类的 pandoc 残余
    text = re.sub(r'\{[=.]?\w+\}', '', text)
    text = re.sub(r'`</?\w+>`', '', text)
    # 去掉纯图片路径行 (images/...)
    text = re.sub(r'^\s*images/[\w./-]+\s*$', '', text, flags=re.MULTILINE)
    # 压缩连续空行
    text = re.sub(r'\n{3,}', '\n\n', text)
    # 去掉行首多余空格
    text = re.sub(r'^[ \t]+', '', text, flags=re.MULTILINE)
    return text.strip()

# ── 切块 ──────────────────────────────────────────────
def chunk_text(text: str, size: int = CHUNK_SIZE) -> list:
    """按自然段落边界将文本切成 ~size 字符的块。"""
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
            if len(buf) >= MIN_CHUNK_LEN:
                chunks.append(buf)
            # 如果单段就超过 size，硬切
            if len(para) > size:
                for j in range(0, len(para), size):
                    piece = para[j:j+size].strip()
                    if len(piece) >= MIN_CHUNK_LEN:
                        chunks.append(piece)
                buf = ""
            else:
                buf = para
    if buf and len(buf) >= MIN_CHUNK_LEN:
        chunks.append(buf)
    return chunks

# ── API 调用 ──────────────────────────────────────────
def build_system_prompt() -> str:
    return (
        "你是一位天主教教理数据提取专家。请从提供的 YOUCAT（青年教理）文本中提取结构化条目。\n\n"
        "对于文本中每一个独立的概念、问答、教理主题，创建一个包含以下字段的条目：\n"
        '- topic_category: 大类，如"圣事"、"十诫"、"信经"、"祈祷"、"礼仪"、"道德生活"、"教会"、"圣经"等\n'
        '- concept: 具体概念或问题（中文或英文）\n'
        '- reference_id: 条目编号，如"YOUCAT #120"，如果没有则写"无"\n'
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

def build_user_prompt(chunk: str, context: str) -> str:
    ctx = f"前面已提取的概念摘要：{context}\n\n" if context else ""
    return f"{ctx}请从以下文本提取所有天主教教理条目，返回 JSON：\n\n{chunk}"

def call_api(chunk: str, context: str) -> dict:
    """调用 DeepSeek API，返回解析后的 JSON dict。"""
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": build_system_prompt()},
            {"role": "user", "content": build_user_prompt(chunk, context)},
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.2,
        "max_tokens": 4096,
    }

    session = requests.Session()
    session.trust_env = False  # 绕过系统代理

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = session.post(API_URL, headers=headers, json=payload,
                                timeout=180, proxies={})
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            return json.loads(content)
        except (requests.exceptions.RequestException, json.JSONDecodeError,
                KeyError, IndexError) as e:
            if attempt < MAX_RETRIES:
                print(f"    重试 {attempt}/{MAX_RETRIES}: {e}")
                time.sleep(RETRY_DELAY * attempt)
            else:
                raise

# ── 构建上下文摘要 ─────────────────────────────────────
def make_context(entries: list, max_concepts: int = 8) -> str:
    """从最近提取的条目中生成简短上下文。"""
    recent = entries[-max_concepts:]
    parts = []
    for e in recent:
        cat = e.get("topic_category", "")
        con = e.get("concept", "")
        if con:
            parts.append(f"[{cat}] {con}")
    return "；".join(parts)

# ── 主流程 ────────────────────────────────────────────
def main():
    import argparse
    parser = argparse.ArgumentParser(description="YOUCAT 知识提取工具")
    parser.add_argument("--source-dir", default=MD_DIR,
                        help=f"Markdown 源目录 (默认: {MD_DIR})")
    parser.add_argument("--append", action="store_true",
                        help="追加模式：加载已有 JSON 并追加新数据")
    parser.add_argument("--output", default=OUTPUT_FILE,
                        help=f"输出 JSON 文件 (默认: {OUTPUT_FILE})")
    args = parser.parse_args()

    source_dir = os.path.abspath(args.source_dir)
    output_file = os.path.abspath(args.output)
    # 进度文件跟随输出文件命名
    prog_file = output_file.replace(".json", "_progress.json")

    if not os.path.isdir(source_dir):
        print(f"错误：找不到 {source_dir} 目录")
        sys.exit(1)

    md_files = sorted([
        f for f in os.listdir(source_dir)
        if f.endswith('.md') and not f.startswith('~')
    ])
    print(f"找到 {len(md_files)} 个 Markdown 文件 (来源: {source_dir})：")
    for f in md_files:
        fpath = os.path.join(source_dir, f)
        size_kb = os.path.getsize(fpath) / 1024
        print(f"  - {f}  ({size_kb:.0f} KB)")

    # 初始化 entries
    all_entries = []
    processed_chunks = set()

    # 追加模式：加载已有 JSON
    if args.append:
        if os.path.exists(output_file):
            with open(output_file, 'r', encoding='utf-8') as f:
                existing = json.load(f)
            all_entries = existing.get("entries", [])
            print(f"\n[追加模式] 已加载 {len(all_entries)} 条已有记录")
        else:
            print(f"\n[追加模式] 警告：{output_file} 不存在，将创建新文件")

    # 断点续跑：检查进度文件
    if os.path.exists(prog_file):
        with open(prog_file, 'r', encoding='utf-8') as pf:
            progress = json.load(pf)
            # 进度文件中的 entries 可能比当前 all_entries 更新
            saved_entries = progress.get("entries", [])
            if len(saved_entries) > len(all_entries):
                all_entries = saved_entries
            processed_chunks = set(progress.get("processed_chunks", []))
            print(f"从进度文件恢复：已有 {len(all_entries)} 条记录，"
                  f"已处理 {len(processed_chunks)} 块")

    total_chunks_estimate = 0
    file_chunk_counts = {}

    # 先扫描所有文件计算总块数
    for md_file in md_files:
        fpath = os.path.join(source_dir, md_file)
        with open(fpath, 'r', encoding='utf-8') as f:
            raw = f.read()
        cleaned = clean_text(raw)
        chunks = chunk_text(cleaned)
        file_chunk_counts[md_file] = len(chunks)
        total_chunks_estimate += len(chunks)

    print(f"\n预计总块数: {total_chunks_estimate}")
    print(f"{'='*60}")

    chunk_idx = 0
    for md_file in md_files:
        fpath = os.path.join(source_dir, md_file)
        print(f"\n>> 处理: {md_file}")

        with open(fpath, 'r', encoding='utf-8') as f:
            raw = f.read()
        cleaned = clean_text(raw)
        chunks = chunk_text(cleaned)
        print(f"   切为 {len(chunks)} 块")

        for i, chunk in enumerate(chunks):
            chunk_id = f"{md_file}::{i}"
            if chunk_id in processed_chunks:
                continue

            # 进度显示
            pct = (chunk_idx / total_chunks_estimate) * 100 if total_chunks_estimate else 0
            print(f"   [{chunk_idx+1}/{total_chunks_estimate} {pct:.1f}%] "
                  f"({len(chunk)} chars)...", end=" ", flush=True)

            try:
                ctx = make_context(all_entries)
                result = call_api(chunk, ctx)
                entries = result.get("entries", [])

                if entries:
                    all_entries.extend(entries)
                    print(f"OK +{len(entries)} entries")
                else:
                    print("- none")

                processed_chunks.add(chunk_id)

            except Exception as e:
                print(f"ERR: {e}")
                # 仍然标记为已处理，避免卡住
                processed_chunks.add(chunk_id)

            chunk_idx += 1

            # 定期保存进度
            if chunk_idx % SAVE_EVERY == 0:
                _save(all_entries, processed_chunks, output_file, prog_file)
                print(f"   [SAVED] {len(all_entries)} entries | "
                      f"progress {chunk_idx}/{total_chunks_estimate}")

            time.sleep(CALL_INTERVAL)

    # 最终保存
    _save(all_entries, processed_chunks, output_file, prog_file)
    print(f"\n{'='*60}")
    print(f"Done! Total entries: {len(all_entries)}")
    print(f"Output: {output_file}")

    # 删除进度文件（任务完成）
    if os.path.exists(prog_file):
        os.remove(prog_file)


def _save(entries: list, processed: set, output_file: str, prog_file: str):
    """同时保存 JSON 输出和进度文件（覆写前备份旧文件）。"""
    import shutil
    if os.path.exists(output_file) and os.path.getsize(output_file) > 1000:
        bak = output_file + ".backup"
        shutil.copy2(output_file, bak)
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({"entries": entries}, f, ensure_ascii=False, indent=2)
    with open(prog_file, 'w', encoding='utf-8') as f:
        json.dump({
            "entries": entries,
            "processed_chunks": list(processed),
        }, f, ensure_ascii=False)


if __name__ == "__main__":
    main()
