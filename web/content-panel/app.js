(function () {
  const dom = {
    snapshotTitle: document.getElementById("snapshotTitle"),
    totalCount: document.getElementById("totalCount"),
    visibleCount: document.getElementById("visibleCount"),
    searchInput: document.getElementById("searchInput"),
    platformSelect: document.getElementById("platformSelect"),
    clearButton: document.getElementById("clearButton"),
    platformStrip: document.getElementById("platformStrip"),
    contentList: document.getElementById("contentList"),
    emptyState: document.getElementById("emptyState")
  };

  const state = {
    content: null,
    query: "",
    platformId: ""
  };

  const COVER_PALETTES = [
    ["#0f766e", "#2563eb"],
    ["#7c3aed", "#0891b2"],
    ["#b91c1c", "#f59e0b"],
    ["#166534", "#0f766e"],
    ["#1d4ed8", "#9333ea"],
    ["#be123c", "#334155"]
  ];

  function formatNumber(value) {
    return new Intl.NumberFormat("zh-CN").format(Number(value || 0));
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

  function snapshotLabel(snapshot) {
    if (!snapshot) {
      return "暂无快照";
    }
    return `${snapshot.date || ""} ${snapshot.time || ""}`.trim();
  }

  function itemBadge(item) {
    if (item.source_type === "topic_import") {
      return "选题";
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
    return tags.slice(0, 8);
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
      parts.push(`热度 ${item.hot_score}`);
    }
    if (item.recent_hot_score) {
      parts.push(`近期 ${item.recent_hot_score}`);
    }
    return parts.join(" · ");
  }

  function coverTitle(item) {
    const title = String(item.title || "未命名内容").trim();
    return title.length > 28 ? `${title.slice(0, 28)}...` : title;
  }

  function renderCover(item, linkUrl) {
    const imageUrl = safeImageUrl(item.cover_url || item.coverUrl || "");
    const [coverA, coverB] = coverPalette(item);
    const tagName = linkUrl ? "a" : "div";
    const linkAttrs = linkUrl
      ? ` href="${escapeHtml(linkUrl)}" target="_blank" rel="noopener noreferrer"`
      : "";
    const imageHtml = imageUrl
      ? `<img class="cover-image" src="${escapeHtml(imageUrl)}" alt="" loading="lazy" onerror="this.hidden=true">`
      : "";

    return `
      <${tagName} class="content-cover${imageUrl ? " has-image" : ""}" style="--cover-a: ${coverA}; --cover-b: ${coverB};"${linkAttrs}>
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

  function currentPlatforms() {
    return Array.isArray(state.content && state.content.platforms)
      ? state.content.platforms
      : [];
  }

  function setPlatformFilter(platformId, shouldToggle = true) {
    state.platformId = shouldToggle && state.platformId === platformId ? "" : platformId;
    dom.platformSelect.value = state.platformId;
    renderPlatformControls(currentPlatforms());
    renderItems();
  }

  function filteredItems() {
    const content = state.content || { items: [] };
    const query = state.query.trim().toLowerCase();
    return content.items.filter((item) => {
      if (state.platformId && item.platform_id !== state.platformId) {
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
        item.hook,
        item.content_value,
        item.category_label,
        item.url
      ].some((value) => String(value || "").toLowerCase().includes(query));
    });
  }

  function renderItems() {
    const items = filteredItems();
    dom.visibleCount.textContent = formatNumber(items.length);
    dom.contentList.innerHTML = "";
    dom.emptyState.hidden = Boolean(items.length);

    items.forEach((item) => {
      const article = document.createElement("article");
      article.className = "content-card";
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
          </div>
          ${titleHtml}
          ${meta ? `<div class="content-detail">${escapeHtml(meta)}</div>` : ""}
          ${score ? `<div class="content-score">${escapeHtml(score)}</div>` : ""}
          ${tagsHtml}
          ${snippet ? `<p class="content-snippet">${escapeHtml(snippet)}</p>` : ""}
          <div class="content-meta">${escapeHtml(item.platform_id || "")}</div>
        </div>
      `;
      dom.contentList.appendChild(article);
    });
  }

  function render(content) {
    state.content = content;
    const platforms = Array.isArray(content.platforms) ? content.platforms : [];
    const items = Array.isArray(content.items) ? content.items : [];
    dom.snapshotTitle.textContent = snapshotLabel(content.snapshot);
    dom.totalCount.textContent = formatNumber(content.total || items.length);
    renderPlatformControls(platforms);
    renderItems();
  }

  function bindEvents() {
    dom.searchInput.addEventListener("input", () => {
      state.query = dom.searchInput.value;
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
      setPlatformFilter(button.getAttribute("data-platform-id") || "");
    });

    dom.clearButton.addEventListener("click", () => {
      state.query = "";
      state.platformId = "";
      dom.searchInput.value = "";
      dom.platformSelect.value = "";
      renderPlatformControls(currentPlatforms());
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
      dom.emptyState.hidden = false;
      dom.emptyState.textContent = error.message;
    }
  }

  boot();
})();
