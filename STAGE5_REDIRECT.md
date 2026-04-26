# Stage 5：原網域轉址設定指南

> 把 `healthtreetw.org` 上的舊網址導到 `https://promatw.github.io/`。
> 你執行的是 WP / DNS 端的設定，這份文件給你具體步驟。

---

## 目標 URL 對照

| 舊（WordPress） | 新（GitHub Pages） |
|---|---|
| `https://healthtreetw.org/` | `https://promatw.github.io/` |
| `https://healthtreetw.org/know-02/` | `https://promatw.github.io/posts/know-02/` |
| `https://healthtreetw.org/<slug>/` | `https://promatw.github.io/posts/<slug>/` |
| `https://healthtreetw.org/about/` | `https://promatw.github.io/about/` |
| `https://healthtreetw.org/category/<x>/` | `https://promatw.github.io/categories/<x>/` |

**核心規則**：除了首頁、`/about/`、`/category/` 之外，所有 `/<slug>/` 都要加上 `/posts/` 前綴。

---

## 三種方案比較

| 方案 | 難度 | WP 關掉後還能用？ | 推薦情境 |
|---|---|---|---|
| **A. WP「Redirection」外掛** | 🟢 低 | ❌ 不能 | **目前推薦**，WP 還活著時最快 |
| **B. `.htaccess` 規則** | 🟡 中 | ❌ 不能（依賴 Apache 主機） | 你習慣 SSH / FTP 改檔 |
| **C. Cloudflare Bulk Redirects / Page Rules** | 🟡 中 | ✅ 可以 | 域名已在 Cloudflare、計畫關 WP |

---

## 方案 A：WP「Redirection」外掛（推薦先做這個）

### 步驟

1. WP 後台 → 外掛 → 安裝外掛 → 搜「**Redirection**」（作者：John Godley，超過百萬安裝）→ 安裝並啟用
2. 工具 → Redirection → 完成首次精靈設定（全部用預設）
3. 切到「**Redirects**」分頁 → 「Add new」
4. **規則 1：所有文章**
   - Source URL：`^/([^/]+)/?$`
   - 勾選「Regex」
   - Target URL：`https://promatw.github.io/posts/$1/`
   - HTTP code：301（永久轉址，SEO 友善）
5. **規則 2：首頁**
   - Source URL：`^/$`
   - 勾選「Regex」
   - Target URL：`https://promatw.github.io/`
   - HTTP code：301
6. **規則 3：about 頁**
   - Source URL：`/about/`
   - 不勾 Regex
   - Target URL：`https://promatw.github.io/about/`
   - HTTP code：301
7. **規則 4：分類頁**
   - Source URL：`^/category/([^/]+)/?$`
   - 勾選「Regex」
   - Target URL：`https://promatw.github.io/categories/$1/`
   - HTTP code：301

### ⚠️ 順序重要

WP「Redirection」外掛是**由上而下**比對，第一個 match 就跳。
所以建議排成：規則 2（首頁）→ 規則 3（about 精準）→ 規則 4（category）→ 規則 1（萬用 catchall 放最後）。
否則規則 1 的 `^/([^/]+)/?$` 會先吃掉 `/about/` 並導到 `/posts/about/`（404）。

### 驗證

從外部裝置（手機 4G、不要在 WP 後台登入狀態）打：

```
https://healthtreetw.org/know-02/   → 應該跳到 https://promatw.github.io/posts/know-02/
https://healthtreetw.org/about/      → 應該跳到 https://promatw.github.io/about/
https://healthtreetw.org/            → 應該跳到 https://promatw.github.io/
```

或用 curl 看 301 狀態碼：

```bash
curl -I https://healthtreetw.org/know-02/
# 應該看到：
# HTTP/1.1 301 Moved Permanently
# Location: https://promatw.github.io/posts/know-02/
```

### 排除：圖片 / wp-content

`/wp-content/uploads/...` 的圖片 URL 在轉址後會變成 `/posts/wp-content/...` 然後 404。
**不需要特別處理**，因為：
- 我們的備份站已把所有用到的圖片重新存放在 `/images/<year>/<month>/<file>.jpg`
- 文章內 `<img src>` 路徑也已改寫
- 真的有人手動貼舊圖片連結點進來就 404，可接受

如果你想精緻一點，可以再加一條「不轉址」例外（Redirection 外掛支援）：
- Source：`^/wp-content/`
- 勾「Regex」
- 在「URL options」選「Pass-through」（不轉址，照原本 404）

---

## 方案 B：`.htaccess` 規則（如果你習慣 SSH）

如果你的 WP 主機是 Apache（多數共享主機都是），把以下加在 `.htaccess` **頂端**（在 `# BEGIN WordPress` 之前）：

```apache
<IfModule mod_rewrite.c>
RewriteEngine On

# 首頁
RewriteRule ^$ https://promatw.github.io/ [R=301,L]

# /about/
RewriteRule ^about/?$ https://promatw.github.io/about/ [R=301,L]

# /category/<x>/ → /categories/<x>/
RewriteRule ^category/([^/]+)/?$ https://promatw.github.io/categories/$1/ [R=301,L]

# /wp-content/* → 不轉址（讓 WP 處理或 404）
RewriteRule ^wp-content/ - [L]

# /wp-admin/, /wp-login.php → 不轉址（你還要登入 WP）
RewriteRule ^wp-admin/ - [L]
RewriteRule ^wp-login\.php$ - [L]

# 其他 /<slug>/ → /posts/<slug>/
RewriteRule ^([^/]+)/?$ https://promatw.github.io/posts/$1/ [R=301,L]
</IfModule>
```

**注意**：必須先排除 `/wp-admin/` 和 `/wp-login.php`，否則你登不進 WP 後台。

---

## 方案 C：Cloudflare（WP 關掉後唯一可用的方案）

### 前置：域名要先掛在 Cloudflare

1. Cloudflare 註冊 → 添加 `healthtreetw.org` → 把 nameserver 切到 Cloudflare 提供的兩個（這步在域名註冊商那邊改）
2. 等 24 小時 DNS 生效

### 設定 Bulk Redirects（免費方案 20 條夠用）

Cloudflare Dashboard → 你的域名 → **Bulk Redirects** → Create a List：

| Source URL | Target URL | Status |
|---|---|---|
| `https://healthtreetw.org/` | `https://promatw.github.io/` | 301 |
| `https://healthtreetw.org/about/` | `https://promatw.github.io/about/` | 301 |
| `https://healthtreetw.org/know-01/` | `https://promatw.github.io/posts/know-01/` | 301 |
| `https://healthtreetw.org/know-02/` | `https://promatw.github.io/posts/know-02/` | 301 |
| ... | ... | 301 |

19 篇文章 + about + 首頁 = 21 條，**剛好超過 free plan 上限（20）**。

### 替代：Cloudflare Workers（free tier 100k 請求/天）

寫一個 Worker，邏輯：
```js
export default {
  async fetch(request) {
    const url = new URL(request.url);
    const path = url.pathname;
    let target;
    if (path === "/") target = "https://promatw.github.io/";
    else if (path.startsWith("/about/")) target = "https://promatw.github.io/about/";
    else if (path.startsWith("/category/"))
      target = "https://promatw.github.io/categories/" + path.slice("/category/".length);
    else if (path.startsWith("/wp-")) return new Response("Not found", { status: 404 });
    else target = "https://promatw.github.io/posts" + path;
    return Response.redirect(target, 301);
  }
}
```
綁到 `healthtreetw.org/*` 路由。**無上限、不限文章數**。

---

## 我的推薦執行順序

1. **現在（WP 還活著）**：用方案 A（WP Redirection 外掛）
   - 30 分鐘設好，立即可驗證
   - SEO 上 301 累積一段時間後 Google 會把舊網址的 ranking 轉到新網址
2. **觀察 1-3 個月**（計畫書 Stage 5 的觀察期）
   - 看 GitHub Pages 是否穩定（每週都有新摘要、沒有 build 失敗）
   - 看訪客是否都正確到新站（Google Analytics / Cloudflare Analytics）
3. **準備關 WP 之前**：先切到方案 C（Cloudflare Workers）
   - 確認 healthtreetw.org/know-02/ 還是會 301 到新站
4. **最後關掉 WP 主機 + 退訂主機方案**

---

## 完成判準（給你打勾）

- [ ] 方案 A 設好，4 條規則都運作
- [ ] 從手機 4G 測 5 個 URL：首頁、`/about/`、`/know-02/`、`/status-01/`、不存在的 `/aaaaa/`
- [ ] WP 後台還能正常登入（`/wp-admin/` 沒被誤轉）
- [ ] Search Console 提交「網址變更」（如有設）
- [ ] 把這份檔保留在 repo 以備未來切方案 C 用

---

## 備註：為什麼不用 GitHub Pages 自訂網域？

技術上可以把 `healthtreetw.org` 設為 promatw.github.io 的 custom domain，DNS CNAME 指過去，
那舊網址會直接「變成」新站。但 URL 路徑不一樣（`/know-02/` vs `/posts/know-02/`），
換完後舊路徑全部 404。要解決需在每篇 Hugo 文章 front matter 加 `aliases = ["/<old-slug>/"]`
讓 Hugo 產生 client-side redirect HTML。

這個方案的缺點：
- 域名一旦切過去，原 WP 就無法服務了（DNS 不能同時指兩邊）
- 必須一次到位，沒有觀察期
- aliases 機制依賴 JS / meta refresh，比 301 慢一拍

所以**保留兩個網域、用 301 轉址**是更穩妥的路徑，這也是上面三個方案的共通設計。
