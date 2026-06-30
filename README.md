# TrendRadar 小红书/抖音内容面板

这是一个只保留“小红书 + 抖音 + vibe coding 关键词”的本地采集与公开展示项目。

它不再运行原版 TrendRadar 的多平台热榜、MCP、通知推送、蓝色最终报告页。现在只做三件事：

1. 你在配置面板里改平台和关键词。
2. 本地浏览器采集小红书/抖音搜索内容，并用 `vibecase_agent` 打标过滤。
3. GitHub Pages 展示内容卡片、筛选标签和统计面板。

## 页面

- 内容页：https://awoele.github.io/TrendRadar/content/
- 统计页：https://awoele.github.io/TrendRadar/stats/
- 配置页：https://awoele.github.io/TrendRadar/config/

配置页是静态页面，别人能打开但不能保存。只有拿到你仓库写入权限的 GitHub token 才能读取并提交配置。

## 保留的东西

- `config/config.yaml`：只保留 `xiaohongshu` 和 `douyin`。
- `config/frequency_words.txt`：vibe coding 相关搜索词；`[GLOBAL_FILTER]` 后是过滤词。
- `data/imports/*.csv`：已抓取、已打标、会进入内容页的数据。
- `web/config-panel`：配置面板。
- `web/content-panel`：内容卡片面板。
- `web/stats-panel`：统计面板。
- `scripts/prepare_pages_artifact.py`：生成 GitHub Pages 静态产物。
- `local-collect-xhs-douyin.ps1`：本地采集小红书/抖音并导入面板。
- `local-publish-free-pages.ps1`：测试、生成、提交、推送面板。

## 本地采集

采集依赖本机已有的 `D:\Documents\agents` 项目，因为小红书/抖音需要真实浏览器登录和风控处理。

运行最近 7 天采集：

```powershell
powershell -ExecutionPolicy Bypass -File "D:\Documents\热点库\TrendRadar\local-collect-xhs-douyin.ps1"
```

运行最近 15 天采集：

```powershell
powershell -ExecutionPolicy Bypass -File "D:\Documents\热点库\TrendRadar\local-collect-xhs-douyin.ps1" -Days 15
```

脚本会打开浏览器。需要登录或扫码时，在浏览器里完成后回到终端按 Enter。

输出会复制到：

```text
data/imports/02_xhs_douyin_vibecoding_<since>_<until>.csv
```

然后会重新生成本地：

```text
public/content/index.html
```

## 发布

验证并生成本地 `public/`：

```powershell
powershell -ExecutionPolicy Bypass -File "D:\Documents\热点库\TrendRadar\local-publish-free-pages.ps1"
```

提交并推送到公开 Pages 仓库：

```powershell
powershell -ExecutionPolicy Bypass -File "D:\Documents\热点库\TrendRadar\local-publish-free-pages.ps1" -Push
```

推送后 GitHub Actions 会重新发布内容页、统计页和配置页。

## 免费边界

这个方案本身免费：本地电脑采集、GitHub 仓库存数据、GitHub Actions/Pages 发布。

限制也很明确：小红书和抖音有登录/扫码/风控，不能保证无人值守长期稳定抓取。脚本会保留已抓到的数据，遇到平台验证时需要你手动处理。
