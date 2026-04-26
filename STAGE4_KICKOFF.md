# Stage 4：自動發週報到 GitHub — 新 Chat Kickoff Pack

> 這份文件是給「新開的 Claude.ai chat」看的交接包。
> 把這份檔 + `CONVENTIONS.md` + `weekly_report_remote_task_v5.md` 一起丟給新 chat，
> 它就能在 1-2 小時內把 v6 prompt 測試完。

---

## 0. 一頁快速理解

**現況**：HealthTree TW 已經有兩套並行系統：

```
┌────────────────────────────────────────────────────────────┐
│  WordPress (healthtreetw.org)                              │
│    ├─ 人工發布的 19 篇文章（已被匯入 GitHub）              │
│    └─ Remote Schedule Task v5 每週一自動發週報            │  ← Stage 4 要把這個
│                                                            │     改成發到 GitHub
├────────────────────────────────────────────────────────────┤
│  GitHub Pages (promatw.github.io)                          │
│    ├─ Hugo + PaperMod 靜態站                               │
│    ├─ 19 篇文章 + About 已匯入                             │
│    └─ Push 觸發 Actions → build → deploy（30 秒）         │
└────────────────────────────────────────────────────────────┘
```

**Stage 4 任務**：把 v5 prompt 改成 v6，**核心邏輯不動**（Claude 抓文翻譯摘要），
只把「發布」與「狀態儲存」這兩個 I/O 點從 WP REST API 換成 GitHub Contents API。

**不要做的事**：
- ❌ 不要把任務搬到 GitHub Actions cron（會失去 Claude 的 reasoning 能力）
- ❌ 不要動 v5 的 SITES 清單、輪替邏輯、build_item_html、HTML 排版
- ❌ 不要關掉現在的 WP（觀察期還沒結束，Stage 5 才處理）

---

## 1. 為什麼留在 claude.ai Remote Task

| 比較 | claude.ai Remote Task | GitHub Actions cron |
|---|---|---|
| 排程 | ✅ Cron | ✅ Cron |
| WebFetch + 多語翻譯 | ✅ Claude 直接做 | ❌ 只能跑 deterministic code |
| 要做必須 | — | 寫 Python + 呼叫 Anthropic API + multi-turn |
| 成本 | 訂閱已涵蓋 | 按 token 計費（每週 0.5–2 USD） |
| v5 的智慧累積 | ✅ 直接續用 | 重做一次 |

**結論**：v5 的「智慧」必須是 Claude，所以排程留在 claude.ai；GitHub 只負責收 commit、build、deploy。

---

## 2. 認證設定（你執行前要先準備）

### 2.1 建立 GitHub Fine-grained Personal Access Token

1. https://github.com/settings/tokens?type=beta → Generate new token
2. **Token name**：`promatw-weekly-publisher`
3. **Expiration**：1 year（到期前要記得 rotate）
4. **Repository access**：Only select repositories → `promatw/promatw.github.io`
5. **Permissions**：
   - **Contents**：Read and write ← **必要**（commit 檔案）
   - **Metadata**：Read-only（PAT 預設給）
   - 其他全部不勾
6. Generate → 複製 token（`github_pat_...`），**只會顯示一次**

### 2.2 Token 填入 v6 prompt 的設定區

```python
GH_TOKEN  = "github_pat_..."     # 上一步複製的
GH_REPO   = "promatw/promatw.github.io"
GH_BRANCH = "main"
```

### 2.3 第一次手動 Run Now 測試

claude.ai → 該 task → **Run Now**（不要直接排程）。
看 console 印出的 `✅ commit 成功` 後，去 https://github.com/promatw/promatw.github.io/commits/main 確認有新 commit。
等 30-60 秒後 https://promatw.github.io/posts/<新 slug>/ 可以打開。
都 OK 才把 cron 開起來。

---

## 3. v5 → v6 的差異（最少改動）

### 3.1 設定區

```diff
- WP_URL  = "https://healthtreetw.org"
- WP_USER = "your_username"
- WP_PASS = "xxxx xxxx xxxx xxxx"
+ GH_TOKEN  = "github_pat_..."
+ GH_REPO   = "promatw/promatw.github.io"
+ GH_BRANCH = "main"
```

### 3.2 取代 `wp_request` → `gh_get_file` / `gh_put_file`

```python
GH_API = "https://api.github.com"

def gh_request(method, path, data=None):
    url = f"{GH_API}{path}"
    headers = {
        "Authorization": f"Bearer {GH_TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "promatw-weekly/1.0",
    }
    body = json.dumps(data).encode() if data else None
    if body:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode()) if r.status != 204 else {}
    except urllib.error.HTTPError as e:
        print(f"[HTTP {e.code}] {method} {url} → {e.read().decode()[:300]}")
        return None

def gh_get_file(path):
    """讀 repo 中某檔，回傳 (content_str, sha)。檔案不存在回 ('', None)."""
    res = gh_request("GET", f"/repos/{GH_REPO}/contents/{path}?ref={GH_BRANCH}")
    if res is None:
        return "", None
    content = base64.b64decode(res["content"]).decode("utf-8")
    return content, res["sha"]

def gh_put_file(path, content_str, sha=None, message=""):
    """寫 / 更新 repo 中某檔。新檔不傳 sha；既有檔必須帶 sha 才能更新。"""
    body = {
        "message": message or f"chore: update {path}",
        "content": base64.b64encode(content_str.encode("utf-8")).decode("ascii"),
        "branch": GH_BRANCH,
    }
    if sha:
        body["sha"] = sha
    return gh_request("PUT", f"/repos/{GH_REPO}/contents/{path}", data=body)
```

### 3.3 步驟一/六：狀態儲存 — 從 WP settings 換成 repo 檔案

把狀態存在 `data/state.json`（`.gitignore` **不要**加 data/，這檔要進 commit）。

```python
# 步驟一
state_path = "data/state.json"
state_str, state_sha = gh_get_file(state_path)
state = json.loads(state_str) if state_str else {"rotation_index": 0, "seen_articles": []}
rotation_index = state.get("rotation_index", 0)
seen_articles  = state.get("seen_articles", [])
seen_urls      = set(entry.split("||")[1] for entry in seen_articles if "||" in entry)
```

```python
# 步驟六
new_seen = [f"{item['site']}||{item['url']}" for item in collected]
state["seen_articles"]  = (seen_articles + new_seen)[-40:]
state["rotation_index"] = (rotation_index + 5) % 20
new_state_str = json.dumps(state, ensure_ascii=False, indent=2)
gh_put_file(
    state_path,
    new_state_str,
    sha=state_sha,
    message=f"chore(state): rotate {rotation_index} → {state['rotation_index']}",
)
```

### 3.4 步驟五：發布 — 從 WP posts POST 換成 commit Markdown 檔

```python
# v6 步驟五
today_str = datetime.now().strftime("%Y-%m-%d")
post_title = f"{today_str} 多發性骨髓瘤國際資訊摘要"

# slug 衝突處理：如果同一天已有 digest，加 -2 / -3
base_slug = f"{today_str}-mm-digest"
slug = base_slug
suffix = 2
while True:
    existing, _ = gh_get_file(f"content/posts/{slug}.md")
    if not existing:
        break
    slug = f"{base_slug}-{suffix}"
    suffix += 1

md_body = (
    "+++\n"
    f'title = "{post_title}"\n'
    f'date = "{datetime.now().isoformat()}"\n'
    f'slug = "{slug}"\n'
    f'categories = ["status"]\n'      # CONVENTIONS.md：必須英文 slug
    "draft = false\n"
    "+++\n\n"
    f"{html_content}"
)

result = gh_put_file(
    f"content/posts/{slug}.md",
    md_body,
    sha=None,                          # 新檔，不帶 sha
    message=f"feat(post): {post_title}",
)

if not result or "content" not in result:
    print(f"❌ commit 失敗：{result}")
    raise SystemExit(1)

post_url = f"https://promatw.github.io/posts/{slug}/"
print(f"✅ commit 成功！檔案：content/posts/{slug}.md")
print(f"   稍候約 30-60 秒後可瀏覽：{post_url}")
```

### 3.5 `build_item_html` — 不動

v5 已經是正確格式（`<h2>` + `<p>` + `<a>` 可點的「閱讀原文」+ `<hr>`）。
Hugo 設定 `goldmark.renderer.unsafe = true`，inline HTML 直接渲染，不需要轉 Markdown。

### 3.6 開頭說明框、結尾 — 不動

`html_content` 整段沿用 v5。發到 Hugo 時就是 markdown 檔的 body 部分，前面加 Hugo front matter 即可。

---

## 4. 規則對齊（CONVENTIONS.md 摘要）

新 chat 動手前**必看** `healthtree-static/CONVENTIONS.md`，重點：

| 規則 | 在 v6 怎麼遵守 |
|---|---|
| URL slug 必須 ASCII | `slug = "{today_str}-mm-digest"` 已是 ASCII ✓ |
| `categories` 用英文 slug | `categories = ["status"]`（v6 已寫死） |
| Front matter 必須含 title/date/slug/categories/draft | v6 範本已含 ✓ |
| 「閱讀原文」必須 `<a target="_blank" rel="noopener">` | v5 `build_item_html` 已產出 ✓ |
| 圖片路徑 `/images/<year>/<month>/...` | 週報目前沒嵌圖，不需要處理；如未來要嵌圖再寫下載邏輯 |
| iframe / table 要靠 CSS 收口 | 週報目前不嵌 YouTube，不需處理；嵌的話 CSS 已就位 |

---

## 5. 給新 Chat 的第一段 Prompt（你開新 chat 時直接貼）

```
我要把現有的 weekly report Remote Schedule Task 從 WordPress 改發到 GitHub。

請先讀以下三份檔（我會貼給你）：
1. weekly_report_remote_task_v5.md — 現有 v5 任務的 prompt
2. healthtree-static/CONVENTIONS.md — 靜態站的開發規則
3. healthtree-static/STAGE4_KICKOFF.md — 這次任務的整體規劃

讀完後請：
1. 摘要一下你理解的「v5 → v6 要改什麼、不改什麼」（30 秒對齊）
2. 產出 weekly_report_remote_task_v6.md 完整內容（基於 v5，套用 STAGE4_KICKOFF.md 第 3 節的差異）
3. 告訴我我這邊要準備什麼（GitHub PAT 步驟在 STAGE4_KICKOFF.md 第 2 節）

請不要動 v5 的 SITES 清單、輪替邏輯、build_item_html、HTML 排版（這些已經穩定）。
```

---

## 6. 新 Chat 的完成判準

- [ ] `weekly_report_remote_task_v6.md` 寫好放進 `local_github_healthtreetw/`
- [ ] GitHub PAT 建好並填進 v6
- [ ] claude.ai 上把 v6 設成 Remote Schedule Task（cron `0 0 * * 1`）
- [ ] 第一次 Run Now 成功，repo 看到 commit、Pages 上看到新文章
- [ ] 設好 cron 後等下一個週一自動跑成功
- [ ] 把舊的 v5（發 WP 的）關掉或暫停，避免雙發

---

## 7. 後續（更後面的階段）

當 Stage 4 v6 穩定跑 4 週、Stage 5 轉址也設好（見 `STAGE5_REDIRECT.md`）後：
- 觀察 1-3 個月（計畫書 Stage 5 觀察期）
- 確認沒有人靠 WP 找文章後，關 WP 主機（退訂主機方案）
- 把 Cloudflare Workers 接管 healthtreetw.org → promatw.github.io 的轉址
- 整個 backup plan 收工
