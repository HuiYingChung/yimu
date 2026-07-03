# desktop_realtime_translator — Repo 規則

> 全域規則見 ~/.claude/CLAUDE.md（自動載入）。本檔只放這個 repo
> 特有的事。硬規則不得被本檔覆蓋。

## 這個專案是什麼
Windows 桌面工具：即時擷取系統播放的聲音（影片、線上會議），
經 Gemini Live API 翻譯成繁體中文，以懸浮視窗顯示字幕。
單人本機使用，Huiying 自用。

## 技術棧與部署
- Python 3.11＋，無框架；tkinter（標準庫）做 UI。
- 音訊：pyaudiowpatch（WASAPI loopback，僅 Windows）。
- 翻譯：Gemini Live API，模型 `gemini-3.5-live-translate-preview`
  （google-genai SDK）。模型名若失效，查
  https://ai.google.dev/gemini-api/docs/live-api/live-translate
- 不部署——本機執行 `python main.py`。

## 適用的共用標準
- [ ] standards/serverless-ai-proxy.md（**不適用**：本機桌面工具、
  單人使用，key 存本機 .env 不進 git；無前端網站、無 serverless 層。
  不要為此案加 proxy——徒增延遲。若未來變成多人／網頁版再掛。）
- [ ] standards/database.md（無持久化資料）
- [x] standards/verification.md（一律適用）

## 這個 repo 的驗證方式
- 階段模組可獨立跑：`python audio_capture.py`（存 5 秒 wav 人耳驗）、
  `python translator.py`（terminal 印譯文）。
- 端到端：播英文 YouTube 3 分鐘，字幕延遲 < 3 秒、不崩潰；
  播中文內容字幕保持安靜（echo_target_language=False）。
- 音訊與 UI 的驗收需 Huiying 在真機確認，不能只看 code。

## 已知的坑與注意事項
- pyaudiowpatch 只能在 Windows 跑。
- Live API session 有時長上限；斷線要自動重連（backoff、
  保留既有字幕），429 額度用盡要浮到 UI。
- loopback 裝置取樣率依系統設定（44.1k/48kHz 立體聲），
  送 API 前必須轉 16kHz 單聲道 int16 PCM。
- translator.py 介面固定為「queue 進、text callback 出」——
  未來換 OpenAI GPT-Realtime-Translate 只重寫此檔。

## 環境變數
見 `.env.example`。只有 `GEMINI_API_KEY`（Google AI Studio 免費取得）。
