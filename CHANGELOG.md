# Changelog

## 2.0.0

A ground-up rebuild for the agent era.

### Newsroom
- Rebuilt on modern **LangGraph**: a typed `StateGraph`, one reporter subgraph per topic fanned out
  in parallel with `Send`, runtime context, retry policies, and error isolation (one failed story
  never sinks the edition).
- **Any chat model** through LangChain's `init_chat_model` (OpenAI, Anthropic, Google, Groq, Mistral,
  Ollama, ...), with typed **structured outputs** instead of JSON prompting.
- New **assignment editor** plans targeted searches per topic; reporters search in parallel with full
  article text from Tavily.
- The **curator** keeps only on-topic, real URLs and picks the photo. When nothing relevant turns up,
  the reporter **widens the time range** (week, month, year) before giving up.
- **Inline citations** on every factual claim, linked to the numbered sources.
- Writer and critic loop with a revision budget, plus a pull quote, reading time and an
  **editor-in-chief's note** opening each edition.
- **AI illustrations** in three house styles (Ink, Engraving, Risograph), sized per layout slot and
  always labeled, with automatic fallback to news photos.
- Editions in **17 languages**, with right-to-left support.

### App
- A new newsprint design for the app and three redesigned layouts, with dark mode, mobile and
  **print / save as PDF**.
- **Live newsroom**: per-topic progress streamed from the graph, and stories pop onto a live front page
  as they finish.
- Archive of recent editions, Open Graph previews for sharing, copy-link, keyboard shortcut.
- Bring-your-own keys in the UI (stored only in your browser).
- A single FastAPI server with a streaming NDJSON API; the v1 endpoint still works.
- `python -m backend.cli` for terminal and cron use, and a LangGraph Studio config.

### Project
- Security headers and CSP, input validation that never echoes secrets, concurrency limits,
  non-root Docker image with a health check, `.dockerignore` (fixes `.env` being copied into images).
- Test suite covering the full graph with a fake model and search, CI on Python 3.11 to 3.13, ruff,
  Dependabot, issue and PR templates, security policy.
