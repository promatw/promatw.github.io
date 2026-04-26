# HealthTree TW 靜態備份站 — 開發慣例

> 這份文件記錄 stage 跨越時要遵守的決策，避免之後重蹈覆轍。
> 自動發布相關的條目，**寫進 Project Instruction**，讓未來的 agent 自動遵循。

---

## 通則（Debug 經驗總結）

WP REST API 匯入的 HTML 帶很多 **inline 屬性**，PaperMod 預設 CSS 不會幫你收口。
看到下列訊號要主動在 `assets/css/extended/blocksy-style.css` 加約束：

- `<iframe width="1200" height="675">` → 影片放大撐破欄（YouTube embed，已修）
- `<img>` 沒有 wrapper figure → 圖片可能超寬（已用 `.post-content img { max-width: 100% }` 處理）
- `<table>` 沒有 wrapper → 寬表格在手機會橫向溢出
- `<a>` 內含純文字 URL（不是 anchor） → 「閱讀原文」類連結點不動，由 `import_wp.py` 改寫（已修）

**改完一定要驗三個視窗**：① 桌機最寬、② 360px 模擬手機、③ 線上 Ctrl+F5 強制刷新（避開 PaperMod fingerprinted CSS bundle 快取）。

---

## URL Slug 規則（重要）

**所有文章 slug 一律使用 ASCII（英文+數字+連字號），不允許中文。**

理由：
- Hugo 在處理 URL-encoded 中文 slug 時會產生雙重編碼問題（`%e5` → `%25e5`）
- CDN / GitHub Pages 對非 ASCII URL 有時表現不穩定
- 分享連結時純英文較整齊

### 命名格式

| 文章類型 | Slug 格式 | 範例 |
|---|---|---|
| 每日國際資訊摘要 | `YYYY-MM-DD-mm-digest` | `2026-04-22-mm-digest` |
| 同日多篇摘要 | `YYYY-MM-DD-mm-digest-2` | `2026-04-22-mm-digest-2` |
| 週報 | `YYYY-MM-DD-mm-weekly` | `2026-04-15-mm-weekly` |
| 月報 | `YYYY-MM-mm-monthly` | `2026-03-mm-monthly` |
| 認識 MM 系列 | `know-NN` | `know-01` |
| 醫療進展系列 | `status-NN` | `status-05` |
| 日常保健系列 | `life-NN` | `life-01` |
| 活動花絮系列 | `event-NN` | `event-03` |

### 對 import 腳本的處理
- `tools/import_wp.py` 內 `ascii_slug_fallback()` 在偵測到非 ASCII slug 時會自動依
  上述格式產生英文 slug（依 post date + 標題關鍵字「摘要 / 週報 / 月報」判斷）
- 原始 WP URL 保留在 front matter 的 `original_url`，如有需要可建 redirect

### 對未來自動發布的要求（Stage 4+）
- Remote Schedule Task 自動發布 AI 摘要時，**直接以英文 slug 命名**
- 不要產生中文 slug，免得每次都要再做轉換
- 預設用 `YYYY-MM-DD-mm-digest` 格式

---

## 分類 Slug 對應表

WP slug → Hugo 分類顯示名稱（**文章 front matter 的 `categories` 一律用英文 slug**）：

| WP slug | 中文顯示名稱（_index.md title） |
|---|---|
| life | 日常保健 |
| event | 活動花絮 |
| know | 認識 MM |
| status | 醫療進展 |

### 重要：分類 URL 結構（避免主選單失效）

- 文章 front matter：`categories = ["know"]`（英文 slug，**不要寫中文**）
- 分類顯示名稱：放在 `content/categories/<slug>/_index.md` 的 `title:` 欄位
- Hugo 自動產生的 term page 路徑會是 `/categories/know/`，**和 hugo.toml 主選單的硬編碼 URL 對得上**

如果文章 categories 用中文（例如 `["認識 MM"]`），Hugo 會把 term page 放到
`/categories/認識-mm/`，主選單連到 `/categories/know/` 就會變成空頁面（曾發生過）。
所以一律用英文 slug。

### 文章卡片上的分類顯示（中文）

- 文章列表卡片 (`layouts/_default/list.html`) 的 `entry-meta-line` 不直接印
  英文 slug，而是用 `site.GetPage "/categories/<slug>"` 反查 _index.md 的
  `title:` 顯示中文（例如 "認識 MM"）。
- 所以**新增分類時**：除了在 `hugo.toml` 加選單，也要建立
  `content/categories/<slug>/_index.md`，內容只需 `title: "<中文名稱>"`，
  否則卡片上會 fallback 顯示英文 slug。

---

## 「閱讀原文」連結格式（重要）

**所有 `閱讀原文` 連結一律寫成正規 `<a>` 標籤，不要用「閱讀原文：純文字 URL」。**

### 正確寫法

```html
<p>👉 <a href="https://example.com/foo" target="_blank" rel="noopener">閱讀原文</a></p>
```

### 錯誤寫法（不能點，原站常出現）

```html
<!-- 錯：URL 是純文字，沒包 <a> -->
<p style="margin:0;font-size:13px;color:#3a5cc7;">👉 閱讀原文：https://example.com/foo</p>

<!-- 錯：完全沒 URL，無法自動修 -->
<p style="margin:0;font-size:13px;color:#3a5cc7;">👉 閱讀原文</p>
```

### 對 import 腳本的處理

`tools/import_wp.py` 內 `fix_read_original_link()` 用 regex 把
`<p ...>👉 閱讀原文：URL</p>` 自動改寫為正常 anchor。全形/半形冒號都接受，
URL 後常見尾部標點 (`.,;)）。、`) 會 trim 掉。沒 URL 的則無法修，會留下純文字。

### 對未來自動發布的要求（Stage 4+）

- AI 摘要產出 / Remote Schedule Task 寫入 WP（或直接寫入 Hugo）時，
  **每筆原文連結必須以 `<a href="..." target="_blank" rel="noopener">閱讀原文</a>` 形式輸出**
- 不要寫「閱讀原文：URL」純文字格式
- 不要省略 URL（沒 URL 的條目，整個刪掉或留空，不要放孤兒「閱讀原文」字樣）

---

## 圖片路徑

WP 上傳：`https://healthtreetw.org/wp-content/uploads/<year>/<month>/<file>.jpg`
本地備份：`healthtree-static/static/images/<year>/<month>/<file>.jpg`
文章內路徑：`/images/<year>/<month>/<file>.jpg`

`tools/import_wp.py` 自動處理路徑改寫並下載原檔。

---

## YouTube / 影片嵌入格式

WP 來源是 Gutenberg 的 `wp-block-embed`：

```html
<figure class="wp-block-embed is-type-video is-provider-youtube wp-block-embed-youtube wp-embed-aspect-16-9 wp-has-aspect-ratio">
  <div class="wp-block-embed__wrapper">
    <iframe loading="lazy" title="..." width="1200" height="675"
            src="https://www.youtube.com/embed/<id>?feature=oembed"
            frameborder="0" allowfullscreen></iframe>
  </div>
</figure>
```

**iframe 寫死的 1200×675** 在 PaperMod 沒有預設約束，會撐爆欄寬。
`assets/css/extended/blocksy-style.css` 內有對應規則（搜 `.wp-block-embed`）：
- `.wp-block-embed` → `max-width: 100%`
- `.wp-block-embed__wrapper` → `position: relative; aspect-ratio: 16 / 9`
- `.wp-block-embed iframe` → `position: absolute; width/height 100%`

**未來自動發布要求**：保留原 WP 的 `figure.wp-block-embed > div.wp-block-embed__wrapper > iframe` 結構，
不要拆掉外層 `figure` / `wrapper` div，CSS 才能吃到。

### Debug 經驗（2026-04-26）

- **症狀**：桌機與手機進入含 YouTube 的文章，影片框被放大，撐破內容欄寬。
- **根因**：WP 來源 iframe 寫死 `width="1200" height="675"`。原站靠 Blocksy 主題
  CSS（`.wp-embed-aspect-16-9` + `aspect-ratio` + `max-width: 100%`）收回欄寬，
  PaperMod 沒有對應規則，iframe 直接以 1200px 渲染。
- **教訓 / 通則**：
  1. WP 內容裡任何 inline 寬高（iframe / img / video / table）都要先當「會破版」處理，
     在 `assets/css/extended/blocksy-style.css` 用 `max-width: 100%` 收口。
  2. 想用 `aspect-ratio` 等比縮放時，必須讓 iframe 有 `position: absolute` 充滿父層
     `wrapper`，否則 iframe 屬性的 height 會無視 aspect-ratio。
  3. 改 CSS 後測試：① 本機 `hugo server` 開最寬桌機、② 視窗縮到 360px 模擬手機、
     ③ 線上強制刷新（Ctrl+F5）以避開 PaperMod 的 fingerprint CSS bundle 快取。
- **預防**：將來新主題 / 重大改版時，跑一次 `posts/know-02/`（多支 YouTube）+
  含表格 / 含 `<img width=...>` 的文章作為視覺回歸基準。

---

## Hugo 設定要點

- `goldmark.renderer.unsafe = true`（允許 inline HTML，因 WP 內容是 HTML）
- `defaultTheme = "light"` + `disableThemeToggle = true`（站內鎖定淺色）
- `pagination.pagerSize = 10`
- `params.label.text = "HealthTree TW"`（標題用，logo 顯示時被 header.html 覆蓋為純星星圖示）

---

## 待辦：寫進 Project Instruction

當 Stage 4 自動發布啟動前，把以下幾條寫進 Project Instruction：

1. **URL slug 必須英文**（見上方表格）
2. **Front matter 必須含**：`title`, `date`, `slug`, `categories`, `draft = false`
3. **`categories` 值用英文 slug**（如 `["know"]`），**不要寫中文** ── Hugo 自動產生
   的 term page URL 才會跟主選單對得上；中文顯示由 `_index.md` 的 title 提供
4. **「閱讀原文」連結用 `<a href="..." target="_blank" rel="noopener">閱讀原文</a>` 格式**，
   不要寫「閱讀原文：純文字 URL」、也不要產出沒 URL 的孤兒字樣
5. **發布前先 local Hugo build 驗證**，再 commit + push
