# 轉載文章到 promatw.github.io（新 Chat 提示詞範本）

> 從網路看到一篇文章想轉載到 GitHub 備份站時，用這份。
> 5/7 之後 WP 關掉，這會是常態流程。

---

## 怎麼用

1. 開一個新的 **Claude Code** session
2. 工作目錄切到：`C:\work2\local_github_healthtreetw\healthtree-static\`
3. 把下方「**提示詞**」整段（從 `---START---` 到 `---END---` 之間）複製貼上送出
4. 跟著它的問題回答即可

---

## 提示詞

```
---START---

我要轉載一篇文章到 promatw.github.io（這個 repo 的 Hugo 靜態站）。
請完整讀完下面所有指示後，再依步驟跟我互動。

【你需要先讀的檔】
- CONVENTIONS.md（站台所有規則）
- content/posts/ 下的範例文章（特別是我選定範本後那篇）

【流程：先問我 4 件事，等我都回答才動手】

問題 1：文章來源
  - 我會給 URL，或直接貼純文字 / HTML 內容
  - 如果是 URL，你用 WebFetch 抓

問題 2：分類（必須選一個英文 slug）
  - know   → 認識 MM
  - status → 醫療進展
  - life   → 日常保健
  - event  → 活動花絮

問題 3：排版風格範本
  - 列出 content/posts/ 中我選的分類底下既有文章（檔名 + 標題），
    讓我選一篇當範本
  - 提示：digest 類（如 2026-04-27-mm-digest.md）是「多條目 + h2 + 閱讀原文」風格；
    know-01 / status-01 等是單篇圖文 + 小標風格。請依範本判斷

問題 4：處理方式
  - 模式 A：直接整篇轉載（保留原文結構）
  - 模式 B：改寫 / 翻譯 / 摘要後轉載（這時請我說明改寫程度）

【執行：四個問題都回答後】

1. 抓內容（WebFetch 或讀我貼的純文字）

2. 處理圖片（如有）：
   - 下載到 static/images/<year>/<month>/<file>，year/month 用今天日期
   - 內文 <img src> 改寫為 /images/<year>/<month>/<file>
   - 如果原圖太大或來源不穩，告訴我哪些圖你跳過

3. 處理連結：
   - 「閱讀原文」必須 <a href="..." target="_blank" rel="noopener">閱讀原文</a> 格式
   - 內文外連 <a> 都加 target="_blank" rel="noopener"

4. 處理多媒體：
   - YouTube：保留 <figure class="wp-block-embed ..."><div class="wp-block-embed__wrapper"><iframe ...></iframe></div></figure> 結構，
     CSS 已就位會自動 16:9 縮放。不要拆成裸 iframe
   - 非中文內容若選模式 B，翻成繁體中文

5. 寫入 content/posts/<slug>.md：
   - slug 必須 ASCII（英文 + 數字 + 連字號），不要中文
   - slug 命名建議：
     · digest 類：YYYY-MM-DD-mm-digest（同日重複加 -2 / -3）
     · 一般文章：依分類加流水號，如 status-06 / know-04 / life-02
   - Front matter（TOML，+++ 包起來）：
     +++
     title = "..."
     date  = "<ISO 8601 含時間，例 2026-04-27T15:30:00>"
     slug  = "..."
     categories = ["<選定的英文 slug>"]
     original_url = "<來源 URL，沒有就省略>"
     draft = false
     +++

6. 完成後：
   - 顯示完整 .md 內容讓我預覽（不要直接 commit）
   - 我說 OK 才執行：
       git add content/posts/<slug>.md  static/images/<year>/<month>/...
       git commit -m "feat(post): <title>"
       git push
   - 告訴我「等 30-60 秒後可瀏覽 https://promatw.github.io/posts/<slug>/」

【絕對不要做的事】
- 不要直接修改 hugo.toml、layouts/、assets/ 任何檔（這些是站台基礎，要動先問我）
- 不要 push 到任何非 main 分支
- 不要建 draft = true 的草稿（站台設定 buildDrafts = false 不會顯示）
- 不要動 themes/PaperMod/（git submodule）
- 不要 commit 含 token / Application Password 的內容（git secret scanner 會擋）

請開始問我問題 1。

---END---
```

---

## 範本對照表（給你 / 給新 Chat 參考）

| 範本檔名 | 風格 | 適合什麼 |
|---|---|---|
| `2026-04-27-mm-digest.md` | digest（多條目 + 開頭說明框 + h2 + hr） | 自動週報 / 多篇彙整 |
| `know-01.md` | 單篇長文（多張圖 + 多層小標） | 完整介紹 / 翻譯整篇 |
| `know-02.md` | 影片彙整（多支 YouTube + 簡單說明） | 影片資源整理 |
| `status-01.md` | 單篇新聞（圖 + 純段落） | 一則新聞 / 治療進展 |
| `status-04.md` | 廣播翻譯（長文純文字） | 訪談 / podcast 翻譯 |
| `event-02.md` | 活動流程（時程表） | 活動公告 |
| `event-03.md` | 活動花絮（多圖回顧） | 活動回顧 |
| `life-01.md` | 一般保健文章 | 日常保健資訊 |
| `2026-04-mm-monthly.md` | 月報（多條目較長 + 分區） | 自動月報 |

選範本時依「結構像不像」挑，不一定要同分類。例如轉載一篇純新聞放 status，可以拿 `status-01.md` 當範本即可。

---

## 兩個流程的差異速查

| 情境 | 觸發點 | 用什麼 | 何時用 |
|---|---|---|---|
| 1. 自動週報 | 每週一 08:00 cron | claude.ai Remote Schedule Task v6 | 已上線（5/7 後仍持續） |
| 2. 手動轉載 | 看到網路文章想收 | 新 Claude Code chat + 這份提示詞 | 5/7 後常態，手動觸發 |

兩個流程都把檔丟進同一個 repo 的 `content/posts/`，GitHub Actions 一視同仁 build + deploy。
