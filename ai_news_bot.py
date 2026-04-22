"""AI News Bot - 매일 AI 회사 소식을 Slack으로 전송"""
import os, json, time, re
from datetime import datetime, timezone, timedelta
from pathlib import Path
import feedparser, requests

FEEDS = [
    ("Anthropic News", "https://raw.githubusercontent.com/Olshansk/rss-feeds/main/feed_anthropic_news.xml", "🟣"),
    ("Anthropic Engineering", "https://raw.githubusercontent.com/Olshansk/rss-feeds/main/feed_anthropic_engineering.xml", "🟣"),
    ("Claude Code Changelog", "https://raw.githubusercontent.com/Olshansk/rss-feeds/main/feed_anthropic_changelog_claude_code.xml", "🟣"),
    ("OpenAI News", "https://openai.com/news/rss.xml", "🟢"),
    ("Google Research", "https://research.google/blog/rss/", "🔵"),
    ("Google DeepMind", "https://deepmind.google/blog/rss.xml", "🔵"),
    ("Hugging Face", "https://huggingface.co/blog/feed.xml", "🟡"),
]
SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
LOOKBACK_HOURS = 24
STATE_FILE = Path("state.json")
MAX_TOTAL_ITEMS = 15

def load_state():
    if STATE_FILE.exists():
        try: return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except: return {}
    return {}

def save_state(state):
    if len(state.get("sent_ids", [])) > 500:
        state["sent_ids"] = state["sent_ids"][-500:]
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

def fetch_new_items(state):
    sent_ids = set(state.get("sent_ids", []))
    cutoff = datetime.now(timezone.utc) - timedelta(hours=LOOKBACK_HOURS)
    new_items = []
    for source, url, emoji in FEEDS:
        try:
            print(f"[fetch] {source}")
            feed = feedparser.parse(url, request_headers={"User-Agent": "ai-news-bot/1.0"})
            for entry in feed.entries[:5]:
                eid = entry.get("id") or entry.get("link")
                if not eid or eid in sent_ids: continue
                pub = None
                for k in ("published_parsed", "updated_parsed"):
                    if entry.get(k):
                        pub = datetime(*entry[k][:6], tzinfo=timezone.utc); break
                if pub and pub < cutoff: continue
                summary = re.sub(r"<[^>]+>", "", entry.get("summary", "") or "").strip()[:500]
                new_items.append({
                    "id": eid, "source": source, "emoji": emoji,
                    "title": entry.get("title", "").strip(),
                    "link": entry.get("link", ""), "summary": summary,
                    "published": pub.isoformat() if pub else None,
                })
        except Exception as e:
            print(f"  ! {e}")
    new_items.sort(key=lambda x: x["published"] or "", reverse=True)
    return new_items[:MAX_TOTAL_ITEMS]

def summarize_with_claude(items):
    if not ANTHROPIC_API_KEY or not items: return None
    text = "\n\n".join(f"[{i+1}] {it['source']}\n제목: {it['title']}\n내용: {it['summary']}" for i, it in enumerate(items))
    prompt = f"다음 AI 소식들을 각각 1-2문장 한국어로 간결하게 요약. [1] [2] 형식 유지, 명사형 종결.\n\n{text}\n\n요약:"
    try:
        r = requests.post("https://api.anthropic.com/v1/messages",
            headers={"x-api-key": ANTHROPIC_API_KEY, "anthropic-version": "2023-06-01", "content-type": "application/json"},
            json={"model": "claude-haiku-4-5-20251001", "max_tokens": 2000, "messages": [{"role": "user", "content": prompt}]},
            timeout=60)
        r.raise_for_status()
        return r.json()["content"][0]["text"]
    except Exception as e:
        print(f"[summary] {e}"); return None

def parse_summary(text, n):
    result = {}
    for m in re.finditer(r"\[(\d+)\]\s*(.+?)(?=\[\d+\]|\Z)", text, re.DOTALL):
        i = int(m.group(1)) - 1
        if 0 <= i < n: result[i] = m.group(2).strip()
    return result

def build_blocks(items, summaries):
    today = datetime.now(timezone(timedelta(hours=9))).strftime("%Y년 %m월 %d일")
    blocks = [
        {"type": "header", "text": {"type": "plain_text", "text": f"🤖 오늘의 AI 소식 ({today})"}},
        {"type": "context", "elements": [{"type": "mrkdwn", "text": f"신규 *{len(items)}건* | Anthropic 🟣 OpenAI 🟢 Google 🔵 기타 🟡"}]},
        {"type": "divider"},
    ]
    for i, it in enumerate(items):
        s = summaries.get(i) or it["summary"][:200]
        t = f"{it['emoji']} *<{it['link']}|{it['title']}>*\n_{it['source']}_\n{s}"[:2900]
        blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": t}})
    return blocks

def main():
    if not SLACK_WEBHOOK_URL: raise SystemExit("SLACK_WEBHOOK_URL 없음")
    state = load_state()
    items = fetch_new_items(state)
    print(f"신규 {len(items)}건")
    if not items: return
    summaries = {}
    if ANTHROPIC_API_KEY:
        raw = summarize_with_claude(items)
        if raw: summaries = parse_summary(raw, len(items))
    blocks = build_blocks(items, summaries)
    for chunk in [blocks[i:i+45] for i in range(0, len(blocks), 45)]:
        r = requests.post(SLACK_WEBHOOK_URL, json={"blocks": chunk}, timeout=15)
        if r.status_code != 200: raise SystemExit(f"Slack 실패: {r.text}")
        time.sleep(1)
    state["sent_ids"] = state.get("sent_ids", []) + [it["id"] for it in items]
    state["last_run"] = datetime.now(timezone.utc).isoformat()
    save_state(state)
    print("✅ 완료")

if __name__ == "__main__":
    main()
