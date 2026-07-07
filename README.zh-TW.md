# 譯幕 Yimu — 即時語音翻譯字幕工具

> English documentation: [README.md](README.md)

即時擷取電腦正在播放的聲音（YouTube、線上會議、直播、Podcast），
透過**語音原生翻譯**（音訊直接進翻譯模型）翻成**繁體中文**，
以懸浮字幕視窗顯示在螢幕下方——不需要字幕軌、不綁平台。

- **雙引擎**，app 內即時切換：Gemini Live（有免費額度）／
  OpenAI gpt-realtime-translate（計時收費）
- 台灣在地化：OpenAI 只輸出簡體，程式用 OpenCC 自動轉成
  台灣用語繁體（人工智慧，不是人工智能）
- 單人本機使用：無伺服器、無帳號，key 存本機 `.env`
- 僅支援 **Windows**（音訊擷取用 WASAPI loopback）
- 只顯示文字字幕，不播放翻譯語音；來源已是中文時字幕保持安靜
- **會議友善**：可選的 Markdown 逐字稿（存到 Downloads）、
  本機講者標記、麥克風混音——自己說的話也能進逐字稿

完整設計故事見
[case study](https://www.huiyingchung.com/yimu-case-study.html)（英文）。

## 安裝

需要 Python 3.11 以上。

```
pip install -r requirements.txt
```

選裝——只有想在逐字稿裡標記講者才需要
（會拖 PyTorch，約 1–2 GB）：

```
pip install resemblyzer
```

## 取得 API key

把 `.env.example` 複製一份改名為 `.env`，填入要用的引擎的 key：

**Gemini（預設引擎，免費）**
1. 開 [Google AI Studio](https://aistudio.google.com/apikey)，
   用 Google 帳號登入。
2. 按「Create API key」，貼進 `.env`：`GEMINI_API_KEY=你的key`

免費額度有速率限制，個人看影片、開會一般夠用；
超限時字幕視窗會顯示 429 並自動退避重試。

**OpenAI（選用的第二引擎，計費）**
1. 到 [platform.openai.com](https://platform.openai.com/api-keys)
   建 key（需要有儲值的 API 帳號）。
2. 貼進 `.env`：`OPENAI_API_KEY=你的key`

按音訊時長計費，約 **$0.034/分鐘（≈ $2/小時）**——
設定面板的引擎選項旁也標了這個價格，刻意的。

## 使用

```
python main.py
```

或直接雙擊 `start_translator.bat`（無黑窗；桌面的
「譯幕 Yimu」捷徑指向它）。

- 字幕視窗出現在螢幕下方置中，永遠置頂、半透明黑底白字。
- 播放任何英文（或多數其他語言）的聲音，2～3 秒內出現中文字幕。
- **拖曳**：按住視窗任意處移動。
- **設定**：右鍵選單選「設定…」。
- **退出**：按 `Esc`，或右鍵選單選「結束」。

## 設定面板

右鍵 →「設定…」。外觀類選項**邊調邊即時預覽**（沒有字幕時
視窗會顯示預覽文字），按「取消」全部還原、按「套用」才存進
`settings.json`（刪掉檔案即回復預設）。選項分區如下：

- **翻譯引擎**：Gemini（預設，免費）／ OpenAI（計費，
  需要 `.env` 有 `OPENAI_API_KEY`）。切換會自動重連，不用重開程式。
- **譯文**：字級（10–32pt）、顯示行數（1–10 行，
  視窗高度自動跟著調整）。
- **原文**：在字幕上方顯示原語言辨識文字，可獨立調
  原文字級與行數（開關沒勾時子選項反灰）。
- **記錄**：把逐字稿存成帶時間戳的 Markdown 檔（在 Downloads
  資料夾）；內容可選「原文＋譯文／只有譯文／只有原文」，
  對照模式下譯文以引用縮排配對在原文下方。
  **標記講者**：聲音換人時插入「講者 1／2…」標題——本機運算、
  免費、推測性質，需另裝 `resemblyzer`（選項旁有「說明」
  連結）。**擷取麥克風**：把你的聲音混進翻譯流，開會時
  自己說的話也會有字幕和逐字稿——建議戴耳機避免回音。
  都不會多花 API 費用（計費看時長不看音量）。
- **視窗**：透明度（30%–100%）、視窗寬度（螢幕的 30%–100%），
  拖動即時預覽。
- **介面語言**：English（預設）／中文，切換立即生效。
  字幕輸出一律是繁體中文。

其他進階預設值（目標語言、逐字稿資料夾等）在 `config.py`。

## 常見問題

**字幕一直沒出現？**
- 檢查聲音是否從「預設輸出裝置」播放——工具只錄預設喇叭/耳機。
  換過輸出裝置後要重啟工具。
- 看 console 或狀態列有沒有錯誤訊息（API key 無效、
  找不到 loopback 裝置都會用白話顯示）。

**顯示 429 / rate limited？**
免費額度用盡，工具會自動退避重連；等一下，或到 AI Studio 檢查配額。

**播中文影片沒有字幕？**
預期行為：來源已是中文時翻譯模型保持安靜
（`config.py` 的 `ECHO_TARGET_LANGUAGE = False`）。

**模型名稱失效（連線一直失敗）？**
兩個模型名以 2026 年中為準，未來可能更換。查
[Gemini Live Translation 文件](https://ai.google.dev/gemini-api/docs/live-api/live-translate)
或 OpenAI realtime translation 文件的最新名稱，
改 `config.py` 的 `MODEL_NAME`／`OPENAI_MODEL_NAME`。

## 架構

```
audio_capture.py      WASAPI loopback → 依引擎取樣率的單聲道 PCM chunk
                      （Gemini 16kHz／OpenAI 24kHz）→ asyncio.Queue；
                      可選麥克風混音（以麥克風流當時鐘，loopback
                      靜音也不會卡住）
translator.py         Gemini Live session：音訊 queue 進、譯文 delta 出
translator_openai.py  OpenAI gpt-realtime-translate（WebSocket、介面同上；
                      OpenCC 繁化層、echo 過濾、有上限的靜音尾巴）
transcript.py         句子級 Markdown 逐字稿寫入器（時間戳、
                      內容模式、講者標題）
diarizer.py           可選的本機講者辨識（resemblyzer 聲紋嵌入
                      ＋線上餘弦分群）
subtitle_ui.py        tkinter 懸浮字幕視窗（置頂、可拖曳、預覽文字）
settings_ui.py        分區設定面板（即時預覽、語言即時切換）
main.py               tkinter 主執行緒 + 可重啟的背景 pipeline（Backend）
config.py             預設值 + settings.json 載入/儲存
```

每個引擎一個模組、同一個介面（queue 進、callback 出）——
加新引擎就是加一個模組。

---

Built in collaboration with AI; the design decisions, content, and
direction are mine.
