# 🤖 AI News Slack Bot

> Anthropic, OpenAI, Google 등 주요 AI 회사의 최신 소식을 매일 아침 9시(KST)에 한국어 요약과 함께 Slack으로 전송하는 자동화 봇

[![GitHub Actions](https://img.shields.io/badge/GitHub_Actions-자동실행-2088FF?logo=githubactions&logoColor=white)](https://github.com/features/actions)
[![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Slack](https://img.shields.io/badge/Slack-Webhook-4A154B?logo=slack&logoColor=white)](https://api.slack.com/messaging/webhooks)
[![Gemini](https://img.shields.io/badge/Gemini-2.0_Flash-8E75B2?logo=google&logoColor=white)](https://ai.google.dev/)

---

## ✨ 주요 기능

- 📰 **8개 주요 AI 소스** 자동 수집 (Anthropic, OpenAI, Google, Hugging Face 등)
- 🇰🇷 **Google Gemini로 한국어 자동 요약** (완전 무료)
- 🔄 **중복 방지** - 이미 보낸 글은 다시 안 보냄
- ⏰ **매일 아침 9시(KST) 자동 발송**
- 💰 **운영 비용 0원** - GitHub Actions + Gemini 무료 한도

---

## 📸 미리보기

Slack에 이런 메시지가 매일 도착해요:

```
🤖 오늘의 AI 소식 (2026년 04월 23일)
신규 6건 | Anthropic 🟣 OpenAI 🟢 Google 🔵 기타 🟡

────────────────────────────────────────

🟣 Claude Opus 4.7 launches with improved coding
Anthropic News

📝 한국어 요약
Anthropic이 코딩, 에이전트, 비전, 다단계 작업 성능이
크게 향상된 최신 Opus 모델을 출시. 기존 모델 대비
정확도와 일관성 크게 개선됨.

────────────────────────────────────────

🟢 GPT-5 mini available for developers
OpenAI News

📝 한국어 요약
OpenAI가 개발자용 GPT-5 mini 모델을 출시함.
기존 GPT-4o mini 대비 가격 30% 저렴, 응답 속도 2배 향상.
```

---

## 🛠️ 기술 스택

| 분류 | 기술 |
|------|------|
| 🐍 언어 | Python 3.12 |
| ⚙️ 자동화 | GitHub Actions (cron) |
| 📡 RSS 파싱 | feedparser |
| 🌐 HTTP 요청 | requests |
| 🤖 AI 요약 | Google Gemini 2.0 Flash |
| 💬 메시지 전송 | Slack Incoming Webhook |

---

## 📰 모니터링 소스

| 출처 | 분야 | 이모지 |
|------|------|:---:|
| Anthropic News | Claude 공식 소식 | 🟣 |
| Anthropic Engineering | Claude 엔지니어링 블로그 | 🟣 |
| Claude Code Changelog | Claude Code 업데이트 | 🟣 |
| OpenAI News | GPT/ChatGPT 공식 소식 | 🟢 |
| Google Research | 구글 AI 연구 | 🔵 |
| Google DeepMind | DeepMind/Gemini 소식 | 🔵 |
| Hugging Face | 오픈소스 AI 커뮤니티 | 🟡 |

---

## 🚀 빠른 시작

처음 설치하시는 분은 다음 가이드를 따라하세요.

### 1. GitHub 저장소 생성

이 저장소를 포크하거나 새 저장소에 파일을 복사하세요.

### 2. Slack Webhook 발급

1. [Slack API 페이지](https://api.slack.com/apps) → "Create New App" → "From scratch"
2. 좌측 메뉴 "Incoming Webhooks" → 활성화
3. "Add New Webhook to Workspace" → 채널 선택 → 허용
4. 생성된 Webhook URL 복사 (`https://hooks.slack.com/services/...`)

### 3. Google Gemini API 키 발급 (선택)

한국어 요약 기능을 사용하려면:

1. [Google AI Studio](https://aistudio.google.com/apikey) 접속
2. Gmail 계정으로 로그인
3. "Create API key" → "Create API key in new project"
4. 생성된 키 복사 (`AIza...`)

> 💡 **무료**: 하루 1,500회 무료. 신용카드 등록 불필요.

### 4. GitHub Secrets 등록

저장소 → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

| Name | Value | 필수 |
|------|-------|:---:|
| `SLACK_WEBHOOK_URL` | Slack Webhook URL | ✅ |
| `GOOGLE_API_KEY` | Gemini API 키 | ❌ (한국어 요약용) |

### 5. 첫 실행 테스트

저장소 → **Actions** 탭 → **AI News Daily Digest** → **Run workflow**

1~2분 후 Slack 채널에 메시지가 도착하면 성공! 🎉

---

## ⚙️ 커스터마이징

### 발송 시간 변경

`.github/workflows/daily-digest.yml`의 cron 수정:

```yaml
- cron: "0 0 * * *"     # UTC 0시 = 한국 09시 (현재)
- cron: "0 9 * * *"     # 한국 18시
- cron: "0 0,12 * * *"  # 하루 2번 (오전 9시, 오후 9시)
```

> 💡 GitHub Actions cron은 정확하지 않을 수 있어요. 정시 대신 `17 0 * * *` 처럼 어긋난 분으로 설정하면 더 안정적입니다.

### 모니터링 소스 추가/제거

`ai_news_bot.py`의 `FEEDS` 리스트 수정:

```python
FEEDS = [
    ("이름", "RSS_URL", "🟣"),
    # 추가하고 싶은 피드...
    ("Meta AI", "https://ai.meta.com/blog/rss/", "🟠"),
    ("xAI News", "https://raw.githubusercontent.com/Olshansk/rss-feeds/main/feed_xainews.xml", "⚫"),
]
```

### 한 번에 보낼 글 개수 조정

`ai_news_bot.py`:

```python
MAX_TOTAL_ITEMS = 15   # 기본값. 너무 길면 줄이기
```

### 한국어 요약 끄기

GitHub Secrets에서 `GOOGLE_API_KEY`를 등록하지 않으면 자동으로 RSS 원문 요약을 사용합니다.

---

## 💰 비용

| 항목 | 무료 한도 | 본 봇 사용량 | 실제 비용 |
|------|----------|------------|---------|
| GitHub Actions | 월 2,000분 무료 | 월 약 30분 | $0 |
| Gemini API | 일 1,500회 무료 | 일 약 7회 | $0 |
| Slack Webhook | 무제한 무료 | - | $0 |
| **합계** | | | **$0/월** ✅ |

---

## 📂 프로젝트 구조

```
ai-news-bot/
├── .github/
│   └── workflows/
│       └── daily-digest.yml    # GitHub Actions 자동화 설정
├── ai_news_bot.py              # 메인 봇 스크립트
├── requirements.txt            # Python 의존성
├── state.json                  # 발송 이력 (자동 갱신)
└── README.md                   # 이 파일
```

---

## 🐛 문제 해결

### 메시지가 안 와요

1. **Actions 탭에서 실행 결과 확인**
   - ✅ 초록 체크 + "신규 0건" → 정상! 그날 새 글이 없는 것
   - ❌ 빨간 X → 로그 확인 필요

2. **로그 확인 방법**
   - Actions 탭 → 실패한 실행 클릭 → "send-digest" 클릭
   - "Run python ai_news_bot.py" 펼쳐서 에러 메시지 확인

### 자동 실행이 안 돼요

GitHub Actions의 cron은 정확하지 않을 수 있어요. 다음을 시도:

1. **수동 실행**으로 한 번 깨우기 (Run workflow 버튼)
2. cron 시간을 **정시 아닌 분**으로 변경 (`0 0` → `17 0`)
3. **하루 여러 번** 실행하도록 변경 (`0 0,12 * * *`)

### 같은 메시지가 반복돼요

`state.json` 파일이 GitHub에 커밋되지 않아서 그래요. workflow 파일에 다음이 있는지 확인:

```yaml
permissions:
  contents: write
```

### Gemini 한국어 요약이 안 와요

1. `GOOGLE_API_KEY` Secret 등록 확인
2. workflow 파일에 환경변수 전달되는지 확인:
   ```yaml
   env:
     GOOGLE_API_KEY: ${{ secrets.GOOGLE_API_KEY }}
   ```
3. 로그에서 `Gemini 오류` 메시지 확인

---

## 🔒 보안

- 🔐 모든 API 키는 GitHub Secrets에 안전하게 저장
- 📝 코드에 비밀키가 직접 들어가지 않음
- 💳 신용카드 등록 안 해도 운영 가능 (Gemini 무료 한도)

---

## 📝 라이선스

MIT License - 자유롭게 사용/수정/배포하세요.

---

## 🙏 감사의 말

- [Olshansk/rss-feeds](https://github.com/Olshansk/rss-feeds) - Anthropic RSS 피드 제공
- [Google AI Studio](https://aistudio.google.com/) - 무료 Gemini API
- [GitHub Actions](https://github.com/features/actions) - 무료 자동화 인프라

---

<div align="center">

**매일 아침 자동으로 오는 AI 뉴스, 즐거운 AI 라이프 보내세요!** 🚀

⭐ 도움이 되셨다면 Star를 눌러주세요!

</div>
