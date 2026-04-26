# 本機網頁備份規劃文件
## healthtreetw.org → 靜態網站 + GitHub Pages

> **使用對象**：桌面版 Claude Code（具備本機檔案系統、Git push 能力）
> **建立日期**：2026-04-22
> **版本**：v1
> **動機**：備份（首要）+ 省主機費（次要）+ 用不到 WordPress 完整功能

---

## 0. 為什麼要做這件事

| 動機 | 說明 |
|------|------|
| 主要：備份 | 整個網站變成 Git repo，天然有版本歷史；不用擔心 WordPress 主機掉檔或被駭 |
| 次要：省錢 | GitHub Pages 免費，省下 WordPress 主機費 |
| 第三：精簡 | 用不到 WordPress 的留言、會員等功能，靜態網站剛好夠用 |

---

## 1. 階段總覽

| 階段 | 任務 | 預估時間 | 工具 | 此階段完成判準 |
|------|------|---------|------|--------------|
| 階段 1 | 本機建立靜態網站，做版型 + 5-10 篇文章測試 | 1-2 週 | 桌面版 Claude Code + 本機 dev server | 瀏覽器能看到網站、版型響應式正常 |
| 階段 2 | 寫 WordPress → Markdown 匯出工具，搬 200+ 篇文章 | 2-4 週 | 桌面版 Claude Code + Python | 所有文章完整轉成 Markdown 並能在本機網站正常顯示 |
| 階段 3 | Push GitHub Pages，確認部署成功 | 1 週 | 桌面版 Claude Code + Git | 透過 github.io 網址能看到完整網站 |
| 階段 4 | （可選）改寫 Remote Task，自動發布到 GitHub | 2-3 個月 | 新 Chat | 週報能自動 commit Markdown 到 repo |
| 階段 5 | 確認穩定後，停掉 WordPress 主機 | 觀察 1-3 個月 | — | 不再使用 WordPress |

**重點：階段 1-3 跟現有 WordPress 並行，不影響現在的週報/月報運作。** 階段 4 才會涉及自動發布架構改變，那是另一個獨立大工程。

---

## 2. 階段 1：本機建立靜態網站

### 2.1 選套件：Hugo vs Astro vs Jekyll

我推薦 **Hugo**，理由：

| 比較項 | Hugo | Astro | Jekyll |
|-------|------|-------|--------|
| 速度（build） | 🟢 極快（Go 寫的） | 🟡 普通 | 🔴 慢 |
| 學習曲線 | 🟢 低（純 Markdown + 模板） | 🟡 中（要懂 JS） | 🟢 低 |
| GitHub Pages 原生支援 | 🟡 需 GitHub Actions | 🟡 需 GitHub Actions | 🟢 原生支援 |
| 中文社群與主題 | 🟢 多 | 🟡 少 | 🟡 普通 |
| 安裝複雜度 | 🟢 一個執行檔 | 🔴 要裝 Node.js + npm | 🔴 要裝 Ruby + gem |
| 適合你的情境 | ✅ 最適合 | 🟡 過度工程 | 🟡 速度問題 |

**Hugo 對你最適合的關鍵理由：**
- 一個執行檔就能跑，不用裝 Node.js / Ruby 環境
- Build 200+ 篇文章只要幾秒
- 純 Markdown 寫文章，跟 Remote Task 未來自動發布的流程契合
- 中文社群豐富，主題多

**請桌面版 Claude Code 直接以 Hugo 為前提開始。**

### 2.2 建議的主題

優先考慮這幾個（都支援響應式、適合內容型網站）：

1. **PaperMod** — 簡潔、快、響應式好、深淺色模式都支援
2. **Hextra** — 現代感、適合文件/知識型網站
3. **Anatole** — 中文寫作社群常用、簡約

請桌面版 Claude Code 在初次設定時，先用 **PaperMod** 試做，因為它最接近 healthtreetw.org 目前的風格（清爽、易讀）。

### 2.3 建議的資料夾結構

```
healthtree-static/                # 整個 Hugo 專案
├── archetypes/
│   └── default.md                # 新文章預設模板（含 front matter）
├── content/
│   └── posts/                    # 所有文章
│       ├── 2026-04-22-多發性骨髓瘤國際資訊摘要.md
│       ├── 2026-04-21-多發性骨髓瘤國際資訊摘要.md
│       └── ...
├── data/
│   └── state.json                # 給 Remote Task 用的狀態檔（取代 WP 的 daily_health_news_state）
├── static/
│   └── images/                   # 靜態圖片
├── themes/
│   └── PaperMod/                 # 主題（用 git submodule）
├── hugo.toml                     # Hugo 設定檔
├── .github/
│   └── workflows/
│       └── deploy.yml            # GitHub Actions 自動 build + 部署
└── README.md
```

### 2.4 文章 Markdown front matter 範例

```markdown
---
title: "2026-04-22 多發性骨髓瘤國際資訊摘要"
date: 2026-04-22T08:00:00+08:00
draft: false
categories: ["日常保健"]
tags: ["週報", "多發性骨髓瘤"]
---

<div style="background:#f0f7ff;border-left:4px solid #1a73e8;padding:15px 20px;...">
<p><strong>📋 關於本專欄</strong><br>
本日報由 AI 自動整理...
</div>

## 🔹 文章標題

**來源：**HealthTree　｜　**原始語言：**英文（en）

文章內文段落...

👉 [閱讀原文](https://...)

---
```

**重點**：因為我們已經習慣寫純 HTML（樣式約定備忘），直接把現有文章 HTML 貼進 Markdown 即可，Hugo 預設會把 HTML 直接渲染（不會 escape）。

### 2.5 階段 1 的具體步驟（給桌面版 Claude Code）

1. 安裝 Hugo（Windows: `choco install hugo-extended` 或下載 zip）
2. `hugo new site healthtree-static`
3. `cd healthtree-static`
4. `git init`
5. `git submodule add https://github.com/adityatelange/hugo-PaperMod themes/PaperMod`
6. 編輯 `hugo.toml`：設定中文 lang、theme、選單、首頁顯示文章列表
7. 手動寫 5-10 篇測試文章放到 `content/posts/`（從現有日報 2026-04-22、04-21、04-20 等手動轉 Markdown 即可）
8. `hugo server` 啟動本機 dev server，瀏覽器開 `http://localhost:1313` 確認版型
9. 反覆調整 `hugo.toml` 跟 PaperMod 設定，直到視覺符合期待
10. 手機開瀏覽器（連同網段）確認響應式正常

**階段 1 完成判準**：
- [ ] 瀏覽器看得到網站，5-10 篇測試文章顯示正常
- [ ] 手機看也正常（響應式）
- [ ] 樣式跟現有 WordPress 網站「相近」（不需要 100% 一樣）
- [ ] 文章內的 `<h2>🔹 標題`、`<a href="..." target="_blank">` 等元素都正常顯示
- [ ] 文章內的開頭淺藍說明框（v5 週報那個樣式）能正常顯示

---

## 3. 階段 2：WordPress → Markdown 匯出工具

### 3.1 工具設計

寫一個 Python 腳本（`export_wp_to_md.py`），做以下事：

1. 讀取 WordPress REST API（用現成的 wp_request 邏輯，包含 Mod_Security 繞過 headers）
2. 抓取所有 status=publish 的文章（分頁取，per_page=100）
3. 對每篇文章：
   - 取出 title、date、content、categories、tags、slug
   - 組成 Markdown front matter
   - 把 content（HTML）直接放進 Markdown body
   - 檔名格式：`{date}-{slug}.md`
4. 寫入 `content/posts/` 資料夾
5. 處理特殊狀況：
   - 圖片：把 WordPress 上的圖片下載到 `static/images/`，把 content 內的圖片 URL 從絕對路徑改成相對路徑
   - 內部連結：WordPress 文章互相連結的部分，要重寫成新的 GitHub Pages URL 結構
   - 留言：忽略（靜態網站不需要）

### 3.2 注意事項

- **保留現有 WordPress 不動** —— 匯出工具是「複製」不是「搬移」
- 圖片處理是大坑，可能要花最多時間
- 內部連結重寫可以**先放著**，第一輪只做基礎匯出，連結問題第二輪再處理
- 月報、週報、日報之間的「改草稿關聯」，靜態網站不需要保留（直接全部當已發布）

### 3.3 階段 2 完成判準

- [ ] `content/posts/` 有 200+ 篇 Markdown 檔案
- [ ] `hugo server` 跑起來能看到完整網站
- [ ] 隨機抽 5 篇文章看，內容跟 WordPress 上一致（含圖片）
- [ ] 沒有 build error 或 warning

---

## 4. 階段 3：Push GitHub Pages

### 4.1 GitHub repo 設定

- Repo 名稱：建議 `healthtree-tw` 或 `healthtreetw-static`
- 設為 Public（GitHub Pages 免費版只支援 Public repo）
- Branch：`main` 為原始碼，`gh-pages` 為部署成果（由 GitHub Actions 自動產生）

### 4.2 GitHub Actions workflow

在 `.github/workflows/deploy.yml` 設定：每次 push 到 main 時，自動 build Hugo 並部署到 gh-pages branch。

桌面版 Claude Code 可以參考 [Hugo 官方文件的 GitHub Pages 部署範例](https://gohugo.io/host-and-deploy/host-on-github-pages/)。

### 4.3 自訂網域（可選）

如果想用自己的網域（例如 `healthtreetw.org` 或新網域），需要：
1. 在 GitHub repo settings → Pages → Custom domain 填入
2. 在網域 DNS 設定 CNAME 指向 `<username>.github.io`

**這個動作會影響現有 WordPress 網站可達性**，所以建議：
- 先用 GitHub 預設網址（`<username>.github.io/healthtree-tw`）測試
- 確認所有功能正常後，再考慮網域切換
- 網域切換最好挑離峰時間，並做好溝通公告

### 4.4 階段 3 完成判準

- [ ] `git push origin main` 後，GitHub Actions 跑成功
- [ ] 透過 `<username>.github.io/healthtree-tw` 可以瀏覽網站
- [ ] 所有頁面、文章、圖片正常顯示
- [ ] 行動裝置開啟正常

---

## 5. 階段 4：自動發布到 GitHub（未來工作）

**這個階段建議另開新 Chat 處理，這份規劃文件不展開細節。**

關鍵差異：

| 環節 | 現在（WordPress） | 未來（GitHub） |
|------|------------------|---------------|
| 發布方式 | `POST /wp-json/wp/v2/posts` | GitHub API `PUT /repos/.../contents/{path}` commit Markdown 檔 |
| 即時可見 | ✅ 立即 | ❌ 等 GitHub Actions build（30 秒-2 分鐘）|
| 狀態儲存 | WordPress Settings API | repo 裡的 `data/state.json` |
| 認證 | Application Password | GitHub Personal Access Token |

開新 Chat 時必須帶以下內容：
- 這份規劃文件
- 階段 3 完成後的 repo URL
- 現有 weekly_report_remote_task_v5.md（v5 週報 Prompt）
- Project Instructions v8

---

## 6. 給桌面版 Claude Code 的執行原則

1. **不影響現有 WordPress** —— 階段 1-3 完全在本機 + 新 GitHub repo 操作，原 healthtreetw.org 維持運作
2. **每個階段都要有可驗證的成果** —— 不要一次衝完，每階段做完都先確認沒問題再進下一階段
3. **Git commit 要勤** —— 每完成一小段功能就 commit，方便回滾
4. **遇到困難先停下來問用戶** —— 圖片路徑、網域切換、內部連結重寫等都是有風險的操作

---

## 7. 預期會踩到的坑（提醒清單）

| 坑 | 預防方式 |
|----|---------|
| 中文檔名在 GitHub 顯示亂碼 | 文章檔名用 slug（拉丁字符），中文標題寫在 front matter |
| WordPress 文章內含 shortcode（如 `[gallery]`） | 匯出時要寫 regex 處理或人工確認 |
| 圖片路徑失效 | 階段 2 必須完整下載圖片到 static/images/ |
| Hugo 版本相容性 | 鎖定主題的 git commit hash，避免主題更新後跑不起來 |
| GitHub Actions 用了過多免費額度 | Public repo 通常不會有問題，但要監控 |
| RSS / sitemap.xml | Hugo 有內建，但要確認跟 WordPress 原本的相容 |

---

## 8. 不在這次規劃範圍的事

- 會員登入、病友配對功能（你先前提過想另開 Chat 討論的旁支）
- 月報格式調整（已決定保持現狀）
- 週報細節調整（v5 已交付，下週一執行後再評估）

---

## 變更記錄

| 版本 | 日期 | 變更 |
|------|------|------|
| v1 | 2026-04-22 | 初版 |
