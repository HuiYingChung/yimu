# 譯幕 Yimu — 即時語音翻譯字幕工具

> **Yimu** turns anything your Windows machine plays — videos, meetings,
> livestreams — into live Traditional Chinese subtitles in a floating
> window. Speech-native translation (Gemini Live / OpenAI Realtime),
> no caption track needed, localized for Taiwan. Docs below are in
> Traditional Chinese; the [case study](https://www.huiyingchung.com/yimu-case-study.html)
> tells the full story in English.

即時擷取電腦正在播放的聲音（YouTube、線上會議、任何英文或外語內容），
透過 Gemini 或 OpenAI 的即時翻譯 API 翻成**繁體中文**，
以懸浮字幕視窗顯示在螢幕下方。

- 單人本機使用，僅支援 **Windows**（音訊擷取用 WASAPI loopback）
- 只顯示文字字幕，不播放翻譯語音
- 來源是中文時字幕保持安靜（不會鸚鵡學舌）

## 安裝

需要 Python 3.11 以上。

```
pip install -r requirements.txt
```

## 取得免費 API key

1. 開 [Google AI Studio](https://aistudio.google.com/apikey)，用 Google 帳號登入。
2. 按「Create API key」，複製產生的 key。
3. 在專案資料夾把 `.env.example` 複製一份改名為 `.env`，
   把 key 貼進去：

```
GEMINI_API_KEY=你的key
```

免費額度有速率限制，個人看影片、開會使用一般夠用；
超限時字幕視窗會顯示 429 並自動退避重試。

## 使用

```
python main.py
```

或直接雙擊 `start_translator.bat`（無黑窗；桌面的
「即時字幕翻譯」捷徑指向它）。

- 字幕視窗出現在螢幕下方置中，永遠置頂、半透明黑底白字。
- 播放任何英文（或其他語言）的聲音，2～3 秒內出現中文字幕。
- **拖曳**：按住視窗任意處移動。
- **設定**：右鍵選單選「設定…」。
- **退出**：按 `Esc`，或右鍵選單選「結束」。

## 設定面板

右鍵 →「設定…」可以調整，按「套用」立即生效並記住
（存到 `settings.json`，刪掉即回復預設）：

- **翻譯引擎**：Gemini（預設，有免費額度）／ OpenAI
  （gpt-realtime-translate，**計時收費約 $0.034/分鐘 ≈ $2/小時**，
  需要 `.env` 有 `OPENAI_API_KEY`）。切換會自動重連，不用重開程式。
- **字級**：10–32pt。
- **顯示行數**：1–10 行（視窗高度自動跟著調整）。
- **顯示原文**：字幕上方多一行原語言辨識文字。
- **透明度**：30%–100%。

其他進階預設值（目標語言、視窗寬度等）在 `config.py`。

OpenAI 引擎的輸出語言只支援泛用 `zh`（簡體），程式會用 OpenCC
自動轉成繁體（台灣用語），字幕觀感與 Gemini 引擎一致。

## 常見問題

**字幕一直沒出現？**
- 檢查聲音是否從「預設輸出裝置」播放——工具只錄預設喇叭/耳機。
  換過輸出裝置後要重啟工具。
- 看 console 有沒有錯誤訊息（API key 無效、找不到 loopback 裝置
  都會直接顯示）。

**顯示 429 / rate limited？**
免費額度用盡，工具會自動退避重連；等一下，或到 AI Studio 檢查配額。

**播中文影片沒有字幕？**
預期行為：來源已是中文時翻譯模型保持安靜
（`config.py` 的 `ECHO_TARGET_LANGUAGE = False`）。

**模型名稱失效（連線一直失敗）？**
`gemini-3.5-live-translate-preview` 是 preview 模型，名稱可能更換。
查 [Live Translation 文件](https://ai.google.dev/gemini-api/docs/live-api/live-translate)
的最新模型名，改 `config.py` 的 `MODEL_NAME`。

## 架構

```
audio_capture.py      WASAPI loopback → 16kHz 單聲道 PCM chunk（asyncio.Queue）
translator.py         Gemini Live session：送音訊、收譯文 delta（queue 進、callback 出）
translator_openai.py  OpenAI gpt-realtime-translate 引擎（介面同上，24kHz）
subtitle_ui.py        tkinter 懸浮字幕視窗（置頂、可拖曳）
settings_ui.py        設定面板（引擎、字級、原文、透明度）
main.py               組裝：UI 主執行緒 + 可重啟的背景 pipeline（Backend）
config.py             預設值 + settings.json 載入/儲存
```

---

Built in collaboration with AI; the design decisions, content, and
direction are mine.
