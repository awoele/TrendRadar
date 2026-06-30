# 免费公开面板方案

当前仓库只发布小红书和抖音的 vibe coding 内容面板。

## 公开内容

GitHub Pages 会公开这些静态文件：

- `public/content/index.html`
- `public/stats/index.html`
- `public/config/index.html`
- `public/content.json`
- `public/stats.json`
- `public/manifest.json`

仓库公开后，别人也能看到这些配置和导入数据：

- `config/config.yaml`
- `config/frequency_words.txt`
- `data/imports/*.csv`

不要把登录态、cookie、webhook、邮箱密码或任何平台密钥放进仓库。

## 只有你能配置

配置面板是静态页面，没有服务端账号系统。它通过 GitHub API 保存配置：

- 没有 token 的访问者只能看到页面，不能保存。
- 只有拥有 `awoele/TrendRadar` 写入权限的 token 才能读取并提交配置。
- 推荐 fine-grained token 权限：`Contents: Read and write`，`Actions: Read and write`。

配置保存到 `master` 后，`Free Public Pages` workflow 会重新发布页面。

## 本地采集

GitHub Pages 不负责抓取。抓取在本机运行：

```powershell
powershell -ExecutionPolicy Bypass -File "D:\Documents\热点库\TrendRadar\local-collect-xhs-douyin.ps1" -Days 7
```

这条命令会：

1. 读取 `config/frequency_words.txt` 里的关键词。
2. 调用 `D:\Documents\agents\scripts\collect_authenticated.cjs` 打开本地浏览器。
3. 只搜索小红书和抖音。
4. 用 `vibecase_agent` 打标过滤。
5. 把 `case_radar.csv` 复制进 `data/imports/`。
6. 重新生成 `public/content.json` 和面板。

小红书/抖音遇到登录、扫码或安全验证时，需要在打开的浏览器里手动完成。

## 发布

```powershell
powershell -ExecutionPolicy Bypass -File "D:\Documents\热点库\TrendRadar\local-publish-free-pages.ps1" -Push
```

发布后：

- 内容页：https://awoele.github.io/TrendRadar/content/
- 统计页：https://awoele.github.io/TrendRadar/stats/
- 配置页：https://awoele.github.io/TrendRadar/config/

## 已删除的旧路线

这些能力已经从当前仓库删除：

- 原版多平台热榜后端。
- MCP server。
- 通知推送。
- 本地长驻服务。
- 蓝色最终报告页。
- Last30Days 旁路面板。
- TikHub 抖音热榜试验。

当前只保留小红书/抖音搜索内容、可配置面板、内容面板和统计面板。
