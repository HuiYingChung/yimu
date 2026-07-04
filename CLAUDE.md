# desktop_realtime_translator — Repo 規則

> 全域規則見 ~/.claude/CLAUDE.md（自動載入）。本檔只放這個 repo
> 特有的事。硬規則不得被本檔覆蓋。

## 這個專案是什麼
譯幕 Yimu——Windows 桌面工具：即時擷取系統播放的聲音（影片、
線上會議），經 Gemini 或 OpenAI 即時翻譯 API 翻成繁體中文，
以懸浮視窗顯示字幕。單人本機使用，Huiying 自用。

## 技術棧與部署
- Python 3.11＋，無框架；tkinter（標準庫）做 UI。
- 音訊：pyaudiowpatch（WASAPI loopback，僅 Windows）。
- 翻譯：預設 Gemini Live API，模型 `gemini-3.5-live-translate-preview`
  （google-genai SDK）。模型名若失效，查
  https://ai.google.dev/gemini-api/docs/live-api/live-translate
- 引擎可切換（右鍵選單 → 設定，或 settings.json 的 PROVIDER）：
  Gemini（免費額度、16kHz）／ OpenAI gpt-realtime-translate
  （WebSocket、24kHz、$0.034/min、輸出只有簡體 zh → OpenCC 客端繁化）。
- 使用者設定存 settings.json（gitignored），覆蓋 config.py 預設值。
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
- 設定面板：套用後即時生效、settings.json 內容正確、
  切換引擎會重連（切到 OpenAI 空殼要看到明確錯誤）。
- 音訊與 UI 的驗收需 Huiying 在真機確認，不能只看 code。

## 已知的坑與注意事項
- pyaudiowpatch 只能在 Windows 跑。且 **WASAPI loopback 在完全靜音時
  不會送出任何 frame**——`stream.read()` 會一直卡住，這是正常特性，
  測試時必須確保有聲音在播。
- **`echo_target_language=False` 只讓音訊安靜**；`output_transcription`
  照樣逐字回顯中文輸入（2026-07 實測）。字幕安靜靠 translator.py 的
  `_is_echo()` client 端過濾，不要移除。
- tkinter `<Configure>` handler 內不可無條件呼叫 `geometry()`——
  會觸發無限事件迴圈，視窗卡死（見 subtitle_ui.py `_reposition()`）。
- tkinter 明確設過 `geometry()` 後視窗不再隨內容自動長高——
  每次更新字幕後要用 reqheight 重設（見 subtitle_ui.py `_render()`）。
- Live API session 有時長上限；斷線要自動重連（backoff、
  保留既有字幕），429 額度用盡要浮到 UI。
- loopback 裝置取樣率依系統設定（44.1k/48kHz 立體聲），
  送 API 前必須轉 16kHz 單聲道 int16 PCM。
- 翻譯引擎介面固定為「queue 進、text callback 出」——每個引擎
  一個模組（translator.py＝Gemini、translator_openai.py＝OpenAI），
  main.py 依 PROVIDER 載入，取樣率讀引擎的 SAMPLE_RATE class attr
  （Gemini 16k、OpenAI 24k，送錯會變速變調）。
- OpenAI 端點只收兩碼語言代碼（zh-Hant 會被拒，只有 zh＝簡體），
  繁化靠 OpenCC s2twp；echo 過濾要繁簡雙向比對。
- OpenAI 靠「聽到結尾靜音」才 finalize 最後一句，而 loopback 停播
  時不送 frame——兩者相撞會讓最後一句永遠卡住。解法：sender 斷流
  後補送 3 秒靜音尾巴（見 translator_openai.py，計費考量有上限）。
  Gemini 不需要，別把這邏輯搬過去。

## 環境變數
見 `.env.example`。`GEMINI_API_KEY`（Google AI Studio 免費取得）；
`OPENAI_API_KEY` 只在選 OpenAI 引擎時需要（計時收費）。
真 key 一律放 `.env`，不放 `.env.example`（會進 git）。
