"""AI News Bot - 매일 AI 회사 소식을 한국어 요약과 함께 Slack으로 전송 (rate limit 대응 강화)"""
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
MAX_TOTAL_ITEMS = 10  # 15에서 10으로 축소

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
                summary = re.sub(r"<[^>]+>", "", entry.get("summary", "") or "").strip()[:1000]
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

def call_gemini(prompt, max_retries=3):
    """Gemini API 호출 + 자동 재시도"""
    for attempt in range(max_retries):
        try:
            r = requests.post(
                "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent",
                headers={"Content-Type": "application/json"},
                params={"key": GOOGLE_API_KEY},
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {"temperature": 0.3, "maxOutputTokens": 1000}
                },
                timeout=60
            )
            if r.status_code == 429:
                wait_time = 30 * (attempt + 1)  # 30초, 60초, 90초
                print(f"  ⏰ 429 에러, {wait_time}초 대기 후 재시도... ({attempt+1}/{max_retries})")
                time.sleep(wait_time)
                continue
            r.raise_for_status()
            data = r.json()
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except Exception as e:
            print(f"  ! 시도 {attempt+1} 실패: {e}")
            if attempt < max_retries - 1:
                time.sleep(10)
    return None

def summarize_each(items):
    """각 항목을 개별 요약 (rate limit 회피)"""
    if not GOOGLE_API_KEY or not items: 
        return {}
    
    summaries = {}
    for i, it in enumerate(items):
        prompt = f"""다음 AI 소식을 한국어로 2-3문장 요약하세요. 명사형 종결("~함", "~출시"), 사실만, 다른 설명 없이.

출처: {it['source']}
제목: {it['title']}
내용: {it['summary']}

요약:"""
        
        print(f"[summary] {i+1}/{len(items)}: {it['title'][:50]}...")
        result = call_gemini(prompt)
        if result:
            summaries[i] = result.strip()
            print(f"  ✓ 완료")
        else:
            print(f"  ✗ 실패")
        
        # 분당 15회 한도 회피: 항목 사이에 5초 대기
        if i < len(items) - 1:
            time.sleep(5)
    
    return summaries

def build_blocks(items, summaries):
    today = datetime.now(timezone(timedelta(hours=9))).strftime("%Y년 %m월 %d일 %H시")
    blocks = [
        {"type": "header", "text": {"type": "plain_text", "text": f"🤖 오늘의 AI 소식 ({today})"}},
        {"type": "context", "elements": [{"type": "mrkdwn", "text": f"신규 *{len(items)}건* | Anthropic 🟣 OpenAI 🟢 Google 🔵 기타 🟡"}]},
        {"type": "divider"},
    ]
    for i, it in enumerate(items):
        if summaries.get(i):
            t = f"{it['emoji']} *<{it['link']}|{it['title']}>*\n_{it['source']}_\n\n📝 *한국어 요약*\n{summaries[i]}"
        else:
            t = f"{it['emoji']} *<{it['link']}|{it['title']}>*\n_{it['source']}_\n{it['summary'][:300]}"
        t = t[:2900]
        blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": t}})
        blocks.append({"type": "divider"})
    return blocks

def main():
    if not SLACK_WEBHOOK_URL: 
        raise SystemExit("SLACK_WEBHOOK_URL 없음")
    
    print(f"[config] GOOGLE_API_KEY 등록됨: {bool(GOOGLE_API_KEY)}")
    
    state = load_state()
    items = fetch_new_items(state)
    print(f"신규 {len(items)}건")
    if not items: 
        print("새 글 없음. 종료.")
        return
    
    summaries = {}
    if GOOGLE_API_KEY:
        print("[summary] 항목별 한국어 요약 시작 (분당 한도 고려, 5초 간격)")
        summaries = summarize_each(items)
        print(f"  → 총 {len(summaries)}/{len(items)}개 요약 완료")
    
    blocks = build_blocks(items, summaries)
    for chunk in [blocks[i:i+45] for i in range(0, len(blocks), 45)]:
        r = requests.post(SLACK_WEBHOOK_URL, json={"blocks": chunk}, timeout=15)
        if r.status_code != 200: 
            raise SystemExit(f"Slack 실패: {r.text}")
        time.sleep(1)
    state["sent_ids"] = state.get("sent_ids", []) + [it["id"] for it in items]
    state["last_run"] = datetime.now(timezone.utc).isoformat()
    save_state(state)
    print("✅ 완료")

if __name__ == "__main__":
    main()
