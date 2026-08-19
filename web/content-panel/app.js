(function () {
  const dom = {
    snapshotTitle: document.getElementById("snapshotTitle"),
    snapshotPill: document.getElementById("snapshotPill"),
    totalCount: document.getElementById("totalCount"),
    visibleCount: document.getElementById("visibleCount"),
    platformCountMetric: document.getElementById("platformCountMetric"),
    topHeatMetric: document.getElementById("topHeatMetric"),
    topHeatMetricLabel: document.getElementById("topHeatMetricLabel"),
    resultContext: document.getElementById("resultContext"),
    resultStatus: document.getElementById("resultStatus"),
    activeFilterCount: document.getElementById("activeFilterCount"),
    searchInput: document.getElementById("searchInput"),
    platformSelect: document.getElementById("platformSelect"),
    caseTypeSelect: document.getElementById("caseTypeSelect"),
    builtThingSelect: document.getElementById("builtThingSelect"),
    toolStackSelect: document.getElementById("toolStackSelect"),
    hookSelect: document.getElementById("hookSelect"),
    contentValueSelect: document.getElementById("contentValueSelect"),
    riskFlagSelect: document.getElementById("riskFlagSelect"),
    sortSelect: document.getElementById("sortSelect"),
    clearButton: document.getElementById("clearButton"),
    collectionRunList: document.getElementById("collectionRunList"),
    platformStrip: document.getElementById("platformStrip"),
    contentList: document.getElementById("contentList"),
    emptyState: document.getElementById("emptyState"),
    loadMoreWrap: document.getElementById("loadMoreWrap"),
    loadMoreButton: document.getElementById("loadMoreButton")
  };

  const state = {
    content: null,
    query: "",
    platformId: "douyin-favorites",
    sortBy: "published_at",
    visibleLimit: 36,
    topicFilters: {
      caseType: "",
      builtThing: "",
      toolStack: "",
      hook: "",
      contentValue: "",
      riskFlag: ""
    }
  };

  const topicFilterFields = [
    { stateKey: "caseType", itemKey: "case_type", selectKey: "caseTypeSelect", label: "全部类型", split: false },
    { stateKey: "builtThing", itemKey: "built_thing", selectKey: "builtThingSelect", label: "全部方向", split: true },
    { stateKey: "toolStack", itemKey: "tool_stack", selectKey: "toolStackSelect", label: "全部工具", split: true },
    { stateKey: "hook", itemKey: "hook", selectKey: "hookSelect", label: "全部爆点", split: true },
    { stateKey: "contentValue", itemKey: "content_value", selectKey: "contentValueSelect", label: "全部价值", split: true },
    { stateKey: "riskFlag", itemKey: "risk_flag", selectKey: "riskFlagSelect", label: "全部风险", split: true }
  ];

  const platformOrder = [
    "douyin-favorites",
    "douyin-topic",
    "xiaohongshu-topic"
  ];

  const PLATFORM_ACCENTS = {
    "douyin-favorites": "#0f8f65",
    "douyin-topic": "#2563eb",
    "xiaohongshu-topic": "#c2413d"
  };

  const COVER_PALETTES = [
    ["#0f766e", "#2563eb"],
    ["#7c3aed", "#0891b2"],
    ["#b91c1c", "#f59e0b"],
    ["#166534", "#0f766e"],
    ["#1d4ed8", "#9333ea"],
    ["#be123c", "#334155"]
  ];

  const SORT_LABELS = {
    published_at: "最新发布",
    hot_score: "热度最高",
    recent_hot_score: "近期热度",
    likes: "点赞最多"
  };

  function formatNumber(value) {
    return new Intl.NumberFormat("zh-CN").format(Number(value || 0));
  }

  function formatCompactNumber(value) {
    const numeric = numericValue(value);
    if (numeric >= 100000000) {
      return `${(numeric / 100000000).toFixed(numeric >= 1000000000 ? 0 : 1).replace(/\.0$/, "")}亿`;
    }
    if (numeric >= 10000) {
      return `${(numeric / 10000).toFixed(numeric >= 1000000 ? 1 : 2).replace(/\.0+$/, "")}万`;
    }
    return formatNumber(Math.round(numeric));
  }

  function escapeHtml(value) {
    return String(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function safeExternalUrl(value) {
    const url = String(value || "").trim();
    if (!url) {
      return "";
    }
    if (/^http:\/\//i.test(url)) {
      return url;
    }
    if (/^\/\//.test(url)) {
      return `https:${url}`;
    }
    if (/^https:\/\//i.test(url)) {
      return url;
    }
    return "";
  }

  function safeImageUrl(value) {
    const url = safeExternalUrl(value);
    if (/^http:\/\//i.test(url)) {
      return `https://${url.slice(7)}`;
    }
    return url;
  }

  function platformAccent(item) {
    return PLATFORM_ACCENTS[item.platform_id] || "#6d5bd0";
  }

  function hashText(value) {
    let hash = 0;
    const text = String(value || "");
    for (let index = 0; index < text.length; index += 1) {
      hash = (hash * 31 + text.charCodeAt(index)) >>> 0;
    }
    return hash;
  }

  function coverPalette(item) {
    const key = `${item.platform_id || ""}${item.title || ""}`;
    return COVER_PALETTES[hashText(key) % COVER_PALETTES.length];
  }

  function numericValue(value) {
    const parsed = Number.parseFloat(String(value || "").replace(/,/g, ""));
    return Number.isFinite(parsed) ? parsed : 0;
  }

  function snapshotLabel(snapshot, runs = []) {
    if (snapshot && (snapshot.date || snapshot.time)) {
      return `${snapshot.date || ""} ${snapshot.time || ""}`.trim();
    }
    const latestRun = Array.isArray(runs) ? runs[0] : null;
    if (latestRun && latestRun.end_date) {
      return `数据截至 ${latestRun.end_date}`;
    }
    return "等待首次快照";
  }

  function updateFreshnessState(snapshot, runs) {
    const latestRun = Array.isArray(runs) ? runs[0] : null;
    const dateValue = (snapshot && snapshot.date) || (latestRun && latestRun.end_date) || "";
    const snapshotDate = dateValue ? Date.parse(`${dateValue}T00:00:00`) : 0;
    const isStale = snapshotDate && Date.now() - snapshotDate > 14 * 24 * 60 * 60 * 1000;
    dom.snapshotPill.classList.toggle("stale", Boolean(isStale));
    dom.snapshotPill.setAttribute("data-state", isStale ? "数据待更新" : "数据有效");
  }

  function formatDateWindow(run) {
    const start = run.start_date || "";
    const end = run.end_date || "";
    if (start && end && start !== end) {
      return `${start} - ${end}`;
    }
    return start || end || "未记录";
  }

  function formatUpdatedAt(value) {
    if (!value) {
      return "未记录";
    }
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) {
      return String(value);
    }
    return date.toLocaleString("zh-CN", {
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit"
    });
  }

  function runPlatformSummary(run) {
    const platforms = Array.isArray(run.platforms) ? run.platforms : [];
    if (!platforms.length) {
      return "未知平台";
    }
    return platforms
      .map((platform) => `${platform.name || platform.id} ${formatNumber(platform.count)}`)
      .join(" / ");
  }

  function runKeywordSummary(run) {
    const keywords = Array.isArray(run.keywords) ? run.keywords : [];
    if (!keywords.length) {
      return "未记录关键词";
    }
    const preview = keywords.slice(0, 4).join("、");
    return keywords.length > 4 ? `${preview} 等 ${formatNumber(run.keyword_count || keywords.length)} 个` : preview;
  }

  function runSourceSummary(run) {
    const sources = Array.isArray(run.sources) ? run.sources : [];
    if (!sources.length) {
      return "导入记录";
    }
    const labels = sources.map((source) => {
      const value = String(source || "").toLowerCase();
      if (value.includes("douyin:favorites")) {
        return "抖音收藏";
      }
      if (value.includes("tikhub:douyin_keyword_search")) {
        return "抖音关键词采集";
      }
      if (value.includes("redfox:xiaohongshu-crawler")) {
        return "小红书关键词采集";
      }
      if (value.includes("xiaohongshu") || value.includes("redfox_xhs") || value.includes("backfill_xhs")) {
        return "小红书历史导入";
      }
      if (value.includes("douyin")) {
        return "抖音历史导入";
      }
      return "历史数据导入";
    }).filter((label, index, all) => all.indexOf(label) === index);
    return labels.slice(0, 2).join(" / ");
  }

  function renderCollectionRuns(runs) {
    const collectionRuns = Array.isArray(runs) ? runs : [];
    dom.collectionRunList.innerHTML = "";

    if (!collectionRuns.length) {
      dom.collectionRunList.innerHTML = '<article class="run-card muted-run">暂无抓取记录</article>';
      return;
    }

    collectionRuns.slice(0, 8).forEach((run) => {
      const card = document.createElement("article");
      card.className = "run-card";
      card.innerHTML = `
        <div class="run-card-top">
          <span>${escapeHtml(runPlatformSummary(run))}</span>
          <strong>${formatNumber(run.row_count || 0)}</strong>
        </div>
        <div class="run-window">${escapeHtml(formatDateWindow(run))}</div>
        <div class="run-detail">${escapeHtml(runKeywordSummary(run))}</div>
        <div class="run-meta">
          <span>${escapeHtml(formatUpdatedAt(run.updated_at))}</span>
          <span>${escapeHtml(runSourceSummary(run))}</span>
        </div>
      `;
      dom.collectionRunList.appendChild(card);
    });
  }

  function itemBadge(item) {
    if (item.source_type === "topic_import") {
      return "选题";
    }
    if (item.source_type === "favorite_import") {
      return "\u6536\u85cf";
    }
    if (item.source_type === "search_import") {
      return "搜索";
    }
    return `#${item.rank || "-"}`;
  }

  function itemMeta(item) {
    const parts = [];
    if (item.author) {
      parts.push(item.author);
    }
    if (item.published_at) {
      parts.push(item.published_at);
    }
    if (item.likes) {
      parts.push(`${item.likes} 赞`);
    }
    return parts.join(" · ");
  }

  function contentSnippet(item) {
    const text = String(item.description || "").trim();
    if (!text) {
      return "";
    }
    return text.length > 96 ? `${text.slice(0, 96)}...` : text;
  }

  function splitTopicValue(value) {
    return String(value || "")
      .split(/[、,，;；|]/)
      .map((tag) => tag.trim())
      .filter(Boolean);
  }

  function topicValues(item, key, shouldSplit) {
    const value = item[key];
    if (shouldSplit) {
      return splitTopicValue(value);
    }
    const text = String(value || "").trim();
    return text ? [text] : [];
  }

  function countTopicValues(items, field) {
    const counts = new Map();
    items.forEach((item) => {
      topicValues(item, field.itemKey, field.split).forEach((value) => {
        counts.set(value, (counts.get(value) || 0) + 1);
      });
    });
    return Array.from(counts, ([value, count]) => ({ value, count }))
      .sort((a, b) => b.count - a.count || a.value.localeCompare(b.value, "zh-CN"))
      .map((entry) => entry.value);
  }

  function populateSelect(select, label, values, selectedValue) {
    select.innerHTML = "";

    const emptyOption = document.createElement("option");
    emptyOption.value = "";
    emptyOption.textContent = label;
    select.appendChild(emptyOption);

    values.forEach((value) => {
      const option = document.createElement("option");
      option.value = value;
      option.textContent = value;
      option.selected = value === selectedValue;
      select.appendChild(option);
    });

    select.value = selectedValue || "";
  }

  function populateTopicFilters(items) {
    topicFilterFields.forEach((field) => {
      populateSelect(
        dom[field.selectKey],
        field.label,
        countTopicValues(items, field),
        state.topicFilters[field.stateKey]
      );
    });
    dom.sortSelect.value = state.sortBy;
  }

  function matchesTopicFilter(item, field) {
    const selected = state.topicFilters[field.stateKey];
    if (!selected) {
      return true;
    }
    return topicValues(item, field.itemKey, field.split).includes(selected);
  }

  function numericValue(value) {
    const text = String(value || "").trim();
    if (!text) {
      return 0;
    }
    const match = text.match(/-?\d+(?:\.\d+)?/);
    const number = match ? Number(match[0]) : 0;
    if (text.includes("万")) {
      return number * 10000;
    }
    return number;
  }

  function dateValue(value) {
    const text = String(value || "").trim();
    if (!text) {
      return 0;
    }
    const time = Date.parse(text);
    return Number.isNaN(time) ? 0 : time;
  }

  function compareNewestFirst(a, b) {
    return dateValue(b.published_at) - dateValue(a.published_at);
  }

  function sortItems(items) {
    return items.slice().sort((a, b) => {
      if (state.sortBy === "published_at") {
        return compareNewestFirst(a, b);
      }
      return numericValue(b[state.sortBy]) - numericValue(a[state.sortBy]) || compareNewestFirst(a, b);
    });
  }

  function topicTags(item) {
    const tags = [];
    [
      item.case_type,
      item.built_thing,
      item.tool_stack,
      item.hook,
      item.content_value,
      item.risk_flag
    ].forEach((value) => {
      splitTopicValue(value).forEach((tag) => {
        if (!tags.includes(tag)) {
          tags.push(tag);
        }
      });
    });
    return tags.slice(0, 4);
  }

  function renderTopicTags(item) {
    const tags = topicTags(item);
    if (!tags.length) {
      return "";
    }
    return `
      <div class="content-tags">
        ${tags.map((tag) => `<span>${escapeHtml(tag)}</span>`).join("")}
      </div>
    `;
  }

  function topicScore(item) {
    const parts = [];
    if (item.hot_score) {
      parts.push(`热度 ${formatNumber(Math.round(numericValue(item.hot_score)))}`);
    }
    if (item.recent_hot_score) {
      parts.push(`近期 ${formatNumber(Math.round(numericValue(item.recent_hot_score)))}`);
    }
    if (!parts.length && item.likes) {
      parts.push(`点赞 ${formatNumber(item.likes)}`);
    }
    return parts.join(" · ");
  }

  function itemHeatMetric(item) {
    const hotScore = numericValue(item.hot_score) || numericValue(item.recent_hot_score);
    if (hotScore) {
      return { kind: "hot", value: hotScore };
    }
    const likes = numericValue(item.likes);
    if (likes) {
      return { kind: "likes", value: likes };
    }
    return null;
  }

  function coverTitle(item) {
    const title = String(item.title || "未命名内容").trim();
    return title.length > 34 ? `${title.slice(0, 34)}...` : title;
  }

  function renderCover(item, linkUrl) {
    const imageUrl = safeImageUrl(item.cover_url || item.coverUrl || "");
    const [coverA, coverB] = coverPalette(item);
    const tagName = linkUrl ? "a" : "div";
    const linkAttrs = linkUrl
      ? ` href="${escapeHtml(linkUrl)}" target="_blank" rel="noopener noreferrer" aria-label="打开来源：${escapeHtml(item.title || "未命名内容")}"`
      : "";
    const imageHtml = imageUrl
      ? `<img class="cover-image" src="${escapeHtml(imageUrl)}" alt="" loading="lazy" onerror="this.hidden=true">`
      : "";

    return `
      <${tagName} class="content-cover${imageUrl ? " has-image" : ""}" style="--cover-a: ${coverA}; --cover-b: ${coverB}; --platform-accent: ${platformAccent(item)};"${linkAttrs}>
        ${imageHtml}
        <span class="cover-badge">${escapeHtml(itemBadge(item))}</span>
        <span class="cover-source">${escapeHtml(item.platform_name || item.platform_id || "未知平台")}</span>
        <span class="cover-title">${escapeHtml(coverTitle(item))}</span>
      </${tagName}>
    `;
  }

  function renderPlatformControls(platforms) {
    dom.platformSelect.innerHTML = '<option value="">全部平台</option>';
    dom.platformStrip.innerHTML = "";

    const allButton = document.createElement("button");
    const allActive = !state.platformId;
    const allCount = platforms.reduce((total, platform) => total + Number(platform.count || 0), 0);
    allButton.type = "button";
    allButton.className = `platform-chip${allActive ? " active" : ""}`;
    allButton.setAttribute("data-platform-id", "");
    allButton.setAttribute("aria-pressed", String(allActive));
    allButton.innerHTML = `全部平台 <strong>${formatNumber(allCount)}</strong>`;
    dom.platformStrip.appendChild(allButton);

    platforms.forEach((platform) => {
      const active = state.platformId === platform.id;
      const option = document.createElement("option");
      option.value = platform.id;
      option.textContent = `${platform.name} (${platform.count})`;
      option.selected = active;
      dom.platformSelect.appendChild(option);

      const button = document.createElement("button");
      button.type = "button";
      button.className = `platform-chip${active ? " active" : ""}`;
      button.setAttribute("data-platform-id", platform.id);
      button.setAttribute("aria-pressed", String(active));
      button.innerHTML = `${escapeHtml(platform.name)} <strong>${formatNumber(platform.count)}</strong>`;
      dom.platformStrip.appendChild(button);
    });

    dom.platformSelect.value = state.platformId;
  }

  function orderedPlatforms(platforms) {
    return (Array.isArray(platforms) ? platforms : []).slice().sort((a, b) => {
      const aIndex = platformOrder.indexOf(a.id);
      const bIndex = platformOrder.indexOf(b.id);
      const aRank = aIndex === -1 ? platformOrder.length : aIndex;
      const bRank = bIndex === -1 ? platformOrder.length : bIndex;
      return aRank - bRank || String(a.name || a.id || "").localeCompare(String(b.name || b.id || ""), "zh-CN");
    });
  }

  function ensurePlatformSelection(platforms) {
    const ids = new Set(platforms.map((platform) => platform.id));
    if (ids.has(state.platformId)) {
      return;
    }
    state.platformId = ids.has("douyin-favorites") ? "douyin-favorites" : (platforms[0] && platforms[0].id) || "";
  }

  function currentPlatforms() {
    return orderedPlatforms(Array.isArray(state.content && state.content.platforms)
      ? state.content.platforms
      : []);
  }

  function currentPlatformLabel() {
    const platform = currentPlatforms().find((item) => item.id === state.platformId);
    return platform ? platform.name : "全部平台";
  }

  function updateDashboardContext(items, renderedCount) {
    const resultCount = items.length;
    const activeFilters = Object.values(state.topicFilters).filter(Boolean).length;
    const metricPeaks = items.reduce((peaks, item) => {
      const metric = itemHeatMetric(item);
      if (metric) {
        peaks[metric.kind] = Math.max(peaks[metric.kind], metric.value);
      }
      return peaks;
    }, { hot: 0, likes: 0 });
    const queryLabel = state.query.trim() ? `“${state.query.trim().slice(0, 18)}” · ` : "";

    dom.visibleCount.textContent = formatNumber(resultCount);
    if (metricPeaks.hot) {
      dom.topHeatMetric.textContent = formatCompactNumber(metricPeaks.hot);
      dom.topHeatMetricLabel.textContent = "最高热度分 · 同口径比较";
    } else if (metricPeaks.likes) {
      dom.topHeatMetric.textContent = formatCompactNumber(metricPeaks.likes);
      dom.topHeatMetricLabel.textContent = "最高点赞 · 同口径比较";
    } else {
      dom.topHeatMetric.textContent = "-";
      dom.topHeatMetricLabel.textContent = "当前结果暂无热度数据";
    }
    dom.resultContext.textContent = `${queryLabel}${currentPlatformLabel()} · ${SORT_LABELS[state.sortBy] || "最新发布"}`;
    dom.resultStatus.textContent = resultCount
      ? `已展示 ${formatNumber(renderedCount)} / ${formatNumber(resultCount)}`
      : "0 条结果";
    dom.activeFilterCount.textContent = activeFilters ? `${activeFilters} 项已启用` : "未启用";
    dom.activeFilterCount.classList.toggle("active", Boolean(activeFilters));
  }

  function setPlatformFilter(platformId, shouldToggle = true) {
    state.platformId = shouldToggle && state.platformId === platformId ? "" : platformId;
    state.visibleLimit = 36;
    dom.platformSelect.value = state.platformId;
    renderPlatformControls(currentPlatforms());
    renderItems();
  }

  function filteredItems() {
    const content = state.content || { items: [] };
    const query = state.query.trim().toLowerCase();
    const filtered = content.items.filter((item) => {
      if (state.platformId && item.platform_id !== state.platformId) {
        return false;
      }
      if (!topicFilterFields.every((field) => matchesTopicFilter(item, field))) {
        return false;
      }
      if (!query) {
        return true;
      }
      return [
        item.title,
        item.platform_name,
        item.platform_id,
        item.case_type,
        item.built_thing,
        item.tool_stack,
        item.target_audience,
        item.hook,
        item.content_value,
        item.risk_flag,
        item.category_label,
        item.url
      ].some((value) => String(value || "").toLowerCase().includes(query));
    });

    return sortItems(filtered);
  }

  function renderItems() {
    const items = filteredItems();
    const visibleItems = items.slice(0, state.visibleLimit);
    const heatCeilings = items.reduce((peaks, item) => {
      const metric = itemHeatMetric(item);
      if (metric) {
        peaks[metric.kind] = Math.max(peaks[metric.kind], metric.value);
      }
      return peaks;
    }, { hot: 0, likes: 0 });
    dom.contentList.innerHTML = "";
    dom.emptyState.hidden = Boolean(items.length);
    dom.loadMoreWrap.hidden = visibleItems.length >= items.length;
    if (!dom.loadMoreWrap.hidden) {
      const remaining = items.length - visibleItems.length;
      dom.loadMoreButton.textContent = `再看 ${formatNumber(Math.min(24, remaining))} 条`;
    }
    updateDashboardContext(items, visibleItems.length);

    visibleItems.forEach((item) => {
      const article = document.createElement("article");
      article.className = "content-card";
      const heatMetric = itemHeatMetric(item);
      const heatLevel = heatMetric
        ? Math.max(4, Math.round((heatMetric.value / (heatCeilings[heatMetric.kind] || 1)) * 100))
        : 0;
      article.style.setProperty("--heat-level", `${heatLevel}%`);
      article.style.setProperty("--platform-accent", platformAccent(item));
      const title = escapeHtml(item.title || "未命名内容");
      const url = safeExternalUrl(item.url);
      const meta = itemMeta(item);
      const snippet = contentSnippet(item);
      const tagsHtml = renderTopicTags(item);
      const score = topicScore(item);
      const titleHtml = url
        ? `<a class="content-title" href="${escapeHtml(url)}" target="_blank" rel="noopener noreferrer">${title}</a>`
        : `<span class="content-title">${title}</span>`;

      article.innerHTML = `
        ${renderCover(item, url)}
        <div class="content-body">
          <div class="content-row">
            <span class="content-rank ${item.source_type === "search_import" ? "search" : ""} ${item.source_type === "topic_import" ? "topic" : ""}">${escapeHtml(itemBadge(item))}</span>
            <span class="content-platform">${escapeHtml(item.platform_name || item.platform_id || "未知平台")}</span>
            ${score ? `<span class="content-score">${escapeHtml(score)}</span>` : '<span class="content-score muted">暂缺热度</span>'}
          </div>
          ${titleHtml}
          ${meta ? `<div class="content-detail">${escapeHtml(meta)}</div>` : ""}
          ${tagsHtml}
          ${snippet ? `<p class="content-snippet">${escapeHtml(snippet)}</p>` : ""}
          <div class="content-footer">
            <span class="content-meta">${escapeHtml(item.author ? `作者 · ${item.author}` : "公开内容来源")}</span>
            ${url ? `<a class="source-link" href="${escapeHtml(url)}" target="_blank" rel="noopener noreferrer">查看原文 ↗</a>` : ""}
          </div>
        </div>
      `;
      dom.contentList.appendChild(article);
    });
  }

  function render(content) {
    state.content = content;
    const platforms = orderedPlatforms(Array.isArray(content.platforms) ? content.platforms : []);
    const items = Array.isArray(content.items) ? content.items : [];
    dom.snapshotTitle.textContent = snapshotLabel(content.snapshot, content.collection_runs || []);
    updateFreshnessState(content.snapshot, content.collection_runs || []);
    dom.totalCount.textContent = formatNumber(content.total || items.length);
    dom.platformCountMetric.textContent = formatNumber(platforms.length);
    renderCollectionRuns(content.collection_runs || []);
    ensurePlatformSelection(platforms);
    renderPlatformControls(platforms);
    populateTopicFilters(items);
    renderItems();
  }

  function bindEvents() {
    dom.searchInput.addEventListener("input", () => {
      state.query = dom.searchInput.value;
      state.visibleLimit = 36;
      renderItems();
    });

    dom.platformSelect.addEventListener("change", () => {
      setPlatformFilter(dom.platformSelect.value, false);
    });

    dom.platformStrip.addEventListener("click", (event) => {
      const button = event.target.closest("[data-platform-id]");
      if (!button) {
        return;
      }
      setPlatformFilter(button.getAttribute("data-platform-id") || "", false);
    });

    topicFilterFields.forEach((field) => {
      dom[field.selectKey].addEventListener("change", () => {
        state.topicFilters[field.stateKey] = dom[field.selectKey].value;
        state.visibleLimit = 36;
        renderItems();
      });
    });

    dom.sortSelect.addEventListener("change", () => {
      state.sortBy = dom.sortSelect.value || "published_at";
      state.visibleLimit = 36;
      renderItems();
    });

    dom.loadMoreButton.addEventListener("click", () => {
      state.visibleLimit += 24;
      renderItems();
    });

    dom.clearButton.addEventListener("click", () => {
      state.query = "";
      state.platformId = "douyin-favorites";
      state.sortBy = "published_at";
      state.visibleLimit = 36;
      Object.keys(state.topicFilters).forEach((key) => {
        state.topicFilters[key] = "";
      });
      dom.searchInput.value = "";
      dom.platformSelect.value = state.platformId;
      dom.sortSelect.value = "published_at";
      topicFilterFields.forEach((field) => {
        dom[field.selectKey].value = "";
      });
      renderPlatformControls(currentPlatforms());
      populateTopicFilters(Array.isArray(state.content && state.content.items) ? state.content.items : []);
      renderItems();
    });
  }

  async function boot() {
    bindEvents();
    try {
      const response = await fetch(`../content.json?ts=${Date.now()}`, {
        cache: "no-store"
      });
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      render(await response.json());
    } catch (error) {
      dom.snapshotTitle.textContent = "内容加载失败";
      dom.totalCount.textContent = "0";
      dom.visibleCount.textContent = "0";
      dom.platformCountMetric.textContent = "0";
      dom.topHeatMetric.textContent = "-";
      dom.topHeatMetricLabel.textContent = "当前结果暂无热度数据";
      dom.resultContext.textContent = "无法读取内容数据";
      dom.resultStatus.textContent = "加载失败";
      dom.loadMoreWrap.hidden = true;
      dom.emptyState.hidden = false;
      dom.emptyState.textContent = `内容加载失败：${error.message}`;
    }
  }

  boot();
})();
