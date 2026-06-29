(function () {
  const OWNER = "awoele";
  const REPO = "TrendRadar";
  const BRANCH = "master";
  const WORKFLOW_FILE = "free-pages.yml";
  const CONFIG_PATH = "config/config.yaml";
  const WORDS_PATH = "config/frequency_words.txt";
  const TOKEN_KEY = "trendradar_config_token";

  const PLATFORM_CATALOG = [
    { id: "toutiao", name: "今日头条" },
    { id: "baidu", name: "百度热搜" },
    { id: "bilibili-hot-search", name: "bilibili 热搜" },
    { id: "weibo", name: "微博" },
    { id: "douyin", name: "抖音" },
    { id: "zhihu", name: "知乎" },
    { id: "thepaper", name: "澎湃新闻" },
    { id: "ifeng", name: "凤凰网" },
    { id: "wallstreetcn-hot", name: "华尔街见闻" },
    { id: "cls", name: "财联社" },
    { id: "36kr", name: "36氪" },
    { id: "sspai", name: "少数派" },
    { id: "hellogithub", name: "HelloGitHub" },
    { id: "juejin", name: "稀土掘金" },
    { id: "v2ex", name: "V2EX" },
    { id: "ithome", name: "IT之家" }
  ];

  const dom = {
    tokenInput: document.getElementById("tokenInput"),
    rememberToken: document.getElementById("rememberToken"),
    unlockButton: document.getElementById("unlockButton"),
    forgetButton: document.getElementById("forgetButton"),
    authStatus: document.getElementById("authStatus"),
    configForm: document.getElementById("configForm"),
    reloadButton: document.getElementById("reloadButton"),
    saveButton: document.getElementById("saveButton"),
    reportMode: document.getElementById("reportMode"),
    rankThreshold: document.getElementById("rankThreshold"),
    maxNewsPerKeyword: document.getElementById("maxNewsPerKeyword"),
    requestInterval: document.getElementById("requestInterval"),
    timezone: document.getElementById("timezone"),
    sortByPositionFirst: document.getElementById("sortByPositionFirst"),
    reverseContentOrder: document.getElementById("reverseContentOrder"),
    platformGrid: document.getElementById("platformGrid"),
    platformCount: document.getElementById("platformCount"),
    customPlatformId: document.getElementById("customPlatformId"),
    customPlatformName: document.getElementById("customPlatformName"),
    addPlatformButton: document.getElementById("addPlatformButton"),
    keywordText: document.getElementById("keywordText"),
    keywordCount: document.getElementById("keywordCount"),
    saveStatus: document.getElementById("saveStatus")
  };

  const state = {
    token: "",
    configText: "",
    wordsText: "",
    availablePlatforms: PLATFORM_CATALOG.map((item) => ({ ...item })),
    selectedPlatforms: new Map(),
    selectedOrder: []
  };

  function setStatus(element, text, tone) {
    element.textContent = text;
    element.className = `status${tone ? ` ${tone}` : ""}`;
  }

  function setBusy(isBusy) {
    dom.unlockButton.disabled = isBusy;
    dom.reloadButton.disabled = isBusy;
    dom.saveButton.disabled = isBusy;
    dom.addPlatformButton.disabled = isBusy;
  }

  async function github(path, options = {}) {
    const response = await fetch(`https://api.github.com/repos/${OWNER}/${REPO}${path}`, {
      ...options,
      headers: {
        Accept: "application/vnd.github+json",
        Authorization: `Bearer ${state.token}`,
        ...(options.body ? { "Content-Type": "application/json" } : {}),
        "X-GitHub-Api-Version": "2022-11-28",
        ...(options.headers || {})
      }
    });
    const text = await response.text();
    const data = text ? JSON.parse(text) : null;
    if (!response.ok) {
      throw new Error(data && data.message ? data.message : `GitHub API ${response.status}`);
    }
    return data;
  }

  function decodeBase64Utf8(value) {
    const clean = value.replace(/\s/g, "");
    const binary = atob(clean);
    const bytes = Uint8Array.from(binary, (char) => char.charCodeAt(0));
    return new TextDecoder().decode(bytes);
  }

  function yamlString(value) {
    return `"${String(value).replace(/\\/g, "\\\\").replace(/"/g, '\\"')}"`;
  }

  function stripYamlScalar(value) {
    const trimmed = String(value || "").trim();
    if ((trimmed.startsWith('"') && trimmed.endsWith('"')) || (trimmed.startsWith("'") && trimmed.endsWith("'"))) {
      return trimmed.slice(1, -1);
    }
    return trimmed;
  }

  function sectionBounds(yaml, sectionName) {
    const headerExpression = new RegExp(`(^|\\r?\\n)${sectionName}:\\r?\\n`);
    const match = headerExpression.exec(yaml);
    if (!match) {
      return null;
    }
    const sectionStart = match.index + match[1].length;
    const bodyStart = match.index + match[0].length;
    const nextSectionExpression = /\r?\n\S/g;
    nextSectionExpression.lastIndex = bodyStart;
    const next = nextSectionExpression.exec(yaml);
    return {
      sectionStart,
      bodyStart,
      sectionEnd: next ? next.index : yaml.length
    };
  }

  function getSection(yaml, sectionName) {
    const bounds = sectionBounds(yaml, sectionName);
    return bounds ? yaml.slice(bounds.bodyStart, bounds.sectionEnd) : "";
  }

  function readSectionValue(yaml, sectionName, key, fallback) {
    const section = getSection(yaml, sectionName);
    const expression = new RegExp(`^\\s*${key}:\\s*([^#\\n]+)`, "m");
    const match = section.match(expression);
    return match ? stripYamlScalar(match[1]) : fallback;
  }

  function readBoolean(yaml, sectionName, key, fallback) {
    const value = readSectionValue(yaml, sectionName, key, fallback ? "true" : "false");
    return String(value).toLowerCase() === "true";
  }

  function readNumber(yaml, sectionName, key, fallback) {
    const value = Number.parseInt(readSectionValue(yaml, sectionName, key, String(fallback)), 10);
    return Number.isFinite(value) ? value : fallback;
  }

  function replaceLineInSection(yaml, sectionName, key, formattedValue) {
    const bounds = sectionBounds(yaml, sectionName);
    if (!bounds) {
      return yaml;
    }

    const before = yaml.slice(0, bounds.bodyStart);
    const body = yaml.slice(bounds.bodyStart, bounds.sectionEnd);
    const after = yaml.slice(bounds.sectionEnd);
    const lineExpression = new RegExp(`^(\\s*${key}:\\s*)[^#\\r\\n]*?(\\s*(?:#[^\\r\\n]*)?)$`, "m");

    if (lineExpression.test(body)) {
      return before + body.replace(lineExpression, `$1${formattedValue}$2`) + after;
    }

    const eol = yaml.includes("\r\n") ? "\r\n" : "\n";
    return `${before}${body.trimEnd()}${eol}  ${key}: ${formattedValue}${after}`;
  }

  function parsePlatforms(yaml) {
    const match = yaml.match(/^platforms:\s*\n([\s\S]*)$/m);
    if (!match) {
      return [];
    }
    const platforms = [];
    const expression = /^\s*-\s+id:\s*"([^"]+)"\s*\n\s*name:\s*"([^"]*)"/gm;
    let item;
    while ((item = expression.exec(match[1])) !== null) {
      platforms.push({ id: item[1], name: item[2] || item[1] });
    }
    return platforms;
  }

  function buildPlatformSection(platforms) {
    const lines = ["platforms:"];
    platforms.forEach((platform) => {
      lines.push(`  - id: ${yamlString(platform.id)}`);
      lines.push(`    name: ${yamlString(platform.name || platform.id)}`);
    });
    return `${lines.join("\n")}\n`;
  }

  function replacePlatformSection(yaml, platforms) {
    const nextSection = buildPlatformSection(platforms);
    if (/^platforms:\s*$/m.test(yaml)) {
      return yaml.replace(/^platforms:\s*\n[\s\S]*$/m, nextSection);
    }
    return `${yaml.trimEnd()}\n\n${nextSection}`;
  }

  function mergePlatforms(platforms) {
    const known = new Map(state.availablePlatforms.map((platform) => [platform.id, platform]));
    platforms.forEach((platform) => {
      if (known.has(platform.id)) {
        known.get(platform.id).name = platform.name || platform.id;
      } else {
        const next = { id: platform.id, name: platform.name || platform.id };
        state.availablePlatforms.push(next);
        known.set(next.id, next);
      }
    });
  }

  function selectedPlatformList() {
    const ordered = [];
    const seen = new Set();
    state.selectedOrder.forEach((id) => {
      if (state.selectedPlatforms.has(id)) {
        ordered.push({ id, name: state.selectedPlatforms.get(id) || id });
        seen.add(id);
      }
    });
    state.selectedPlatforms.forEach((name, id) => {
      if (!seen.has(id)) {
        ordered.push({ id, name: name || id });
      }
    });
    return ordered;
  }

  function renderPlatforms() {
    dom.platformGrid.innerHTML = "";
    state.availablePlatforms.forEach((platform) => {
      const active = state.selectedPlatforms.has(platform.id);
      const card = document.createElement("label");
      card.className = `platform-card${active ? " active" : ""}`;
      card.innerHTML = `
        <span class="platform-main">
          <input type="checkbox" ${active ? "checked" : ""} data-platform-check="${platform.id}">
          <span>
            <span class="platform-name">${escapeHtml(platform.name)}</span>
            <span class="platform-id">${escapeHtml(platform.id)}</span>
          </span>
        </span>
        <input type="text" value="${escapeAttribute(platform.name)}" data-platform-name="${platform.id}" aria-label="${escapeAttribute(platform.id)} 的显示名称">
      `;
      dom.platformGrid.appendChild(card);
    });
    dom.platformCount.textContent = `${state.selectedPlatforms.size} 个平台`;
  }

  function escapeHtml(value) {
    return String(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function escapeAttribute(value) {
    return escapeHtml(value).replace(/'/g, "&#39;");
  }

  function refreshKeywordCount() {
    const lines = dom.keywordText.value.split(/\r?\n/);
    const activeLines = lines.filter((line) => {
      const trimmed = line.trim();
      return trimmed && !trimmed.startsWith("#");
    });
    dom.keywordCount.textContent = `${activeLines.length} 行`;
  }

  function hydrateForm(configText, wordsText) {
    state.configText = configText;
    state.wordsText = wordsText;
    const platforms = parsePlatforms(configText);

    state.selectedPlatforms = new Map(platforms.map((platform) => [platform.id, platform.name]));
    state.selectedOrder = platforms.map((platform) => platform.id);
    mergePlatforms(platforms);

    dom.reportMode.value = readSectionValue(configText, "report", "mode", "incremental");
    dom.rankThreshold.value = readNumber(configText, "report", "rank_threshold", 5);
    dom.maxNewsPerKeyword.value = readNumber(configText, "report", "max_news_per_keyword", 0);
    dom.requestInterval.value = readNumber(configText, "crawler", "request_interval", 1000);
    dom.timezone.value = readSectionValue(configText, "app", "timezone", "Asia/Shanghai");
    dom.sortByPositionFirst.checked = readBoolean(configText, "report", "sort_by_position_first", false);
    dom.reverseContentOrder.checked = readBoolean(configText, "report", "reverse_content_order", true);
    dom.keywordText.value = wordsText;

    renderPlatforms();
    refreshKeywordCount();
    dom.configForm.classList.remove("locked");
  }

  async function readRepositoryFile(path) {
    const data = await github(`/contents/${path}?ref=${encodeURIComponent(BRANCH)}`);
    return decodeBase64Utf8(data.content);
  }

  async function loadConfig() {
    setBusy(true);
    setStatus(dom.authStatus, "正在读取仓库配置...", "");
    try {
      const repo = await github("");
      if (!repo.permissions || !repo.permissions.push) {
        throw new Error("这个 token 没有仓库写入权限。");
      }
      const [configText, wordsText] = await Promise.all([
        readRepositoryFile(CONFIG_PATH),
        readRepositoryFile(WORDS_PATH)
      ]);
      hydrateForm(configText, wordsText);
      setStatus(dom.authStatus, "已解锁，可以配置抓取规则。", "good");
      setStatus(dom.saveStatus, "当前配置来自 GitHub master 分支。", "");
    } catch (error) {
      dom.configForm.classList.add("locked");
      setStatus(dom.authStatus, `解锁失败：${error.message}`, "bad");
    } finally {
      setBusy(false);
    }
  }

  function collectConfigText() {
    const platforms = selectedPlatformList();
    if (!platforms.length) {
      throw new Error("至少选择一个抓取平台。");
    }
    platforms.forEach((platform) => {
      if (!/^[A-Za-z0-9._-]+$/.test(platform.id)) {
        throw new Error(`平台 ID 不合法：${platform.id}`);
      }
    });

    const keywordLines = dom.keywordText.value.split(/\r?\n/).filter((line) => {
      const trimmed = line.trim();
      return trimmed && !trimmed.startsWith("#");
    });
    if (!keywordLines.length) {
      throw new Error("至少保留一个抓取主题或关键词。");
    }

    let next = state.configText;
    next = replaceLineInSection(next, "report", "mode", yamlString(dom.reportMode.value));
    next = replaceLineInSection(next, "report", "rank_threshold", String(clampInt(dom.rankThreshold.value, 1, 100, 5)));
    next = replaceLineInSection(next, "report", "max_news_per_keyword", String(clampInt(dom.maxNewsPerKeyword.value, 0, 200, 0)));
    next = replaceLineInSection(next, "report", "sort_by_position_first", String(Boolean(dom.sortByPositionFirst.checked)).toLowerCase());
    next = replaceLineInSection(next, "report", "reverse_content_order", String(Boolean(dom.reverseContentOrder.checked)).toLowerCase());
    next = replaceLineInSection(next, "crawler", "request_interval", String(clampInt(dom.requestInterval.value, 50, 10000, 1000)));
    next = replaceLineInSection(next, "app", "timezone", yamlString(dom.timezone.value.trim() || "Asia/Shanghai"));
    next = replacePlatformSection(next, platforms);
    return next;
  }

  function clampInt(value, min, max, fallback) {
    const parsed = Number.parseInt(value, 10);
    if (!Number.isFinite(parsed)) {
      return fallback;
    }
    return Math.min(max, Math.max(min, parsed));
  }

  async function commitFiles(files, message) {
    const ref = await github(`/git/ref/heads/${encodeURIComponent(BRANCH)}`);
    const baseCommitSha = ref.object.sha;
    const baseCommit = await github(`/git/commits/${baseCommitSha}`);
    const treeEntries = [];

    for (const file of files) {
      const blob = await github("/git/blobs", {
        method: "POST",
        body: JSON.stringify({
          content: file.content,
          encoding: "utf-8"
        })
      });
      treeEntries.push({
        path: file.path,
        mode: "100644",
        type: "blob",
        sha: blob.sha
      });
    }

    const tree = await github("/git/trees", {
      method: "POST",
      body: JSON.stringify({
        base_tree: baseCommit.tree.sha,
        tree: treeEntries
      })
    });

    const commit = await github("/git/commits", {
      method: "POST",
      body: JSON.stringify({
        message,
        tree: tree.sha,
        parents: [baseCommitSha]
      })
    });

    await github(`/git/refs/heads/${encodeURIComponent(BRANCH)}`, {
      method: "PATCH",
      body: JSON.stringify({
        sha: commit.sha,
        force: false
      })
    });

    return commit.sha;
  }

  async function triggerWorkflow() {
    await github(`/actions/workflows/${encodeURIComponent(WORKFLOW_FILE)}/dispatches`, {
      method: "POST",
      body: JSON.stringify({ ref: BRANCH })
    });
  }

  async function saveConfig(event) {
    event.preventDefault();
    setBusy(true);
    setStatus(dom.saveStatus, "正在保存到 GitHub...", "");
    try {
      const nextConfig = collectConfigText();
      const nextWords = dom.keywordText.value.replace(/\r\n/g, "\n").trimEnd() + "\n";
      const sha = await commitFiles(
        [
          { path: CONFIG_PATH, content: nextConfig },
          { path: WORDS_PATH, content: nextWords }
        ],
        "chore: update TrendRadar config from panel"
      );

      let triggerText = "已提交，push 会自动发布。";
      try {
        await triggerWorkflow();
        triggerText = "已提交并触发发布。";
      } catch (error) {
        triggerText = `已提交；自动触发失败：${error.message}`;
      }

      state.configText = nextConfig;
      state.wordsText = nextWords;
      setStatus(dom.saveStatus, `${triggerText} 提交 ${sha.slice(0, 7)}。`, "good");
    } catch (error) {
      setStatus(dom.saveStatus, `保存失败：${error.message}`, "bad");
    } finally {
      setBusy(false);
    }
  }

  function setTokenFromInput() {
    state.token = dom.tokenInput.value.trim();
    if (!state.token) {
      setStatus(dom.authStatus, "请输入 GitHub token。", "warn");
      return false;
    }
    sessionStorage.setItem(TOKEN_KEY, state.token);
    if (dom.rememberToken.checked) {
      localStorage.setItem(TOKEN_KEY, state.token);
    } else {
      localStorage.removeItem(TOKEN_KEY);
    }
    return true;
  }

  function forgetToken() {
    state.token = "";
    dom.tokenInput.value = "";
    dom.rememberToken.checked = false;
    sessionStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(TOKEN_KEY);
    dom.configForm.classList.add("locked");
    setStatus(dom.authStatus, "已清除本浏览器里的 token。", "");
  }

  function addCustomPlatform() {
    const id = dom.customPlatformId.value.trim();
    const name = dom.customPlatformName.value.trim() || id;
    if (!id) {
      setStatus(dom.saveStatus, "请输入平台 ID。", "warn");
      return;
    }
    if (!/^[A-Za-z0-9._-]+$/.test(id)) {
      setStatus(dom.saveStatus, "平台 ID 只能包含字母、数字、点、下划线和短横线。", "bad");
      return;
    }

    const existing = state.availablePlatforms.find((platform) => platform.id === id);
    if (existing) {
      existing.name = name;
    } else {
      state.availablePlatforms.push({ id, name });
    }
    state.selectedPlatforms.set(id, name);
    if (!state.selectedOrder.includes(id)) {
      state.selectedOrder.push(id);
    }
    dom.customPlatformId.value = "";
    dom.customPlatformName.value = "";
    renderPlatforms();
  }

  function bindEvents() {
    dom.unlockButton.addEventListener("click", () => {
      if (setTokenFromInput()) {
        loadConfig();
      }
    });
    dom.reloadButton.addEventListener("click", () => {
      if (state.token || setTokenFromInput()) {
        loadConfig();
      }
    });
    dom.forgetButton.addEventListener("click", forgetToken);
    dom.addPlatformButton.addEventListener("click", addCustomPlatform);
    dom.keywordText.addEventListener("input", refreshKeywordCount);
    dom.configForm.addEventListener("submit", saveConfig);

    dom.platformGrid.addEventListener("change", (event) => {
      const checkId = event.target.getAttribute("data-platform-check");
      if (checkId) {
        const nameInput = dom.platformGrid.querySelector(`[data-platform-name="${CSS.escape(checkId)}"]`);
        if (event.target.checked) {
          state.selectedPlatforms.set(checkId, nameInput ? nameInput.value.trim() || checkId : checkId);
          if (!state.selectedOrder.includes(checkId)) {
            state.selectedOrder.push(checkId);
          }
        } else {
          state.selectedPlatforms.delete(checkId);
        }
        renderPlatforms();
      }

      const nameId = event.target.getAttribute("data-platform-name");
      if (nameId) {
        const value = event.target.value.trim() || nameId;
        const platform = state.availablePlatforms.find((item) => item.id === nameId);
        if (platform) {
          platform.name = value;
        }
        if (state.selectedPlatforms.has(nameId)) {
          state.selectedPlatforms.set(nameId, value);
        }
        renderPlatforms();
      }
    });
  }

  function boot() {
    renderPlatforms();
    refreshKeywordCount();
    const savedToken = sessionStorage.getItem(TOKEN_KEY) || localStorage.getItem(TOKEN_KEY) || "";
    if (savedToken) {
      dom.tokenInput.value = savedToken;
      dom.rememberToken.checked = Boolean(localStorage.getItem(TOKEN_KEY));
      state.token = savedToken;
      loadConfig();
    }
    bindEvents();
  }

  boot();
})();
