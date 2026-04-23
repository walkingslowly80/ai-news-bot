"""AI News Bot - 매일 AI 회사 소식을 한국어 요약과 함께 Slack으로 전송"""
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
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
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
                summary = re.sub(r"<[^>]+>", "", entry.get("summary", "") or "").strip()[:1500]
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

def summarize_with_gemini(items):
    """Google Gemini API로 한국어 요약 생성 (무료, 하루 1500회)"""
    if not GOOGLE_API_KEY or not items: return None
    text = "\n\n".join(
        f"[{i+1}] 출처: {it['source']}\n제목: {it['title']}\n내용: {it['summary']}"
        for i, it in enumerate(items)
    )
    prompt = f"""다음은 AI 회사들의 최신 소식입니다. 각 항목을 2-3문장의 한국어로 요약해주세요.

요구사항:
- 각 항목 번호를 그대로 유지하세요 (예: [1], [2])
- 명사형 종결("~함", "~출시")로 간결하게
- 기술 용어는 영어 그대로 (GPT-5, Claude Opus 등)
- 핵심만! 마케팅 문구는 제외

소식 목록:
{text}

번호별 한국어 요약 (다른 설명 없이 [1] 요약 [2] 요약 형식으로):"""
    
    try:
        r = requests.post(
            "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent",
            headers={"Content-Type": "application/json"},
            params={"key": GOOGLE_API_KEY},
            json={
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.3, "maxOutputTokens": 2000}
            },
            timeout=60
        )
        r.raise_for_status()
        return r.json()["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        print(f"[summary] Gemini 오류: {e}")
        return None

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
        summary = summaries.get(i) or it["summary"][:300]
        # 요약이 있으면 한국어 요약 표시, 없으면 원문 요약
        if summaries.get(i):
            t = f"{it['emoji']} *<{it['link']}|{it['title']}>*\n_{it['source']}_\n\n📝 *한국어 요약*\n{summary}"
        else:
            t = f"{it['emoji']} *<{it['link']}|{it['title']}>*\n_{it['source']}_\n{summary}"
        t = t[:2900]
        blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": t}})
        blocks.append({"type": "divider"})
    return blocks

def main():
    if not SLACK_WEBHOOK_URL: raise SystemExit("SLACK_WEBHOOK_URL 없음")
    state = load_state()
    items = fetch_new_items(state)
    print(f"신규 {len(items)}건")
    if not items: return
    
    summaries = {}
    if GOOGLE_API_KEY:
        print("[summary] Gemini로 한국어 요약 생성 중...")
        raw = summarize_with_gemini(items)
        if raw: 
            summaries = parse_summary(raw, len(items))
            print(f"  → {len(summaries)}개 요약 완료")
    else:
        print("[summary] GOOGLE_API_KEY 없음, 원문 요약 사용")
    
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
