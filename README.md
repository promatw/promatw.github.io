# HealthTree TW — 靜態備份站

`healthtreetw.org` 的靜態版本。使用 Hugo + PaperMod，部署於 GitHub Pages。

## 為什麼做這個

- **備份**：整個網站變成 Git repo，有版本歷史
- **省錢**：GitHub Pages 免費
- **精簡**：用不到 WordPress 的完整功能

## 技術堆疊

- [Hugo](https://gohugo.io/) extended v0.160.1
- [PaperMod](https://github.com/adityatelange/hugo-PaperMod) 主題
- GitHub Actions 自動部署到 GitHub Pages

## 本機開發

安裝 Hugo extended（v0.160.1 或以上）。本 repo 的 `../tools/hugo.exe` 已放一份 Windows 執行檔。

啟動 dev server：

```bash
hugo server -D
```

瀏覽器開 http://localhost:1313/

Build 靜態檔：

```bash
hugo --gc --minify
```

產出在 `public/`。

## 資料夾結構

```
healthtree-static/
├── archetypes/default.md        # 新文章預設 front matter
├── content/
│   ├── archives.md              # 彙整頁
│   └── posts/                   # 所有文章
├── data/                        # （保留給未來 Remote Task 狀態檔）
├── static/                      # 靜態圖片等
├── themes/PaperMod/             # 主題（git submodule）
├── hugo.toml                    # Hugo 設定
└── .github/workflows/deploy.yml # 自動部署
```

## 新增文章

```bash
hugo new content posts/2026-04-23-my-post.md
```

編輯 `content/posts/2026-04-23-my-post.md`，調整 front matter 後寫內容。

文章 Markdown 支援直接嵌入 HTML（已設定 `markup.goldmark.renderer.unsafe = true`），可沿用現有 WordPress 樣式約定（淺藍說明框、🔹 標題、`target="_blank"` 連結等）。

## 部署

push 到 `main` 分支後 GitHub Actions 會自動 build + 部署。

首次使用需在 GitHub repo settings → Pages → Source 選 **GitHub Actions**。

## 相關文件

- `../local_backup_plan_v1.md` — 整體備份規劃（階段 1–5）
