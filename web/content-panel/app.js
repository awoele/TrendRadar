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

  function snapshotLabel(snapshot) {
    if (!snapshot) {
      return "暂无快照";
    }
    return `${snapshot.date || ""} ${snapshot.time || ""}`.trim();
  }

  function renderPlatformControls(platforms) {
    dom.platformSelect.innerHTML = '<option value="">全部平台</option>';
    dom.platformStrip.innerHTML = "";

    platforms.forEach((platform) => {
      const option = document.createElement("option");
      option.value = platform.id;
      option.textContent = `${platform.name} (${platform.count})`;
      dom.platformSelect.appendChild(option);

      const chip = document.createElement("span");
      chip.className = "platform-chip";
      chip.innerHTML = `${escapeHtml(platform.name)} <strong>${formatNumber(platform.count)}</strong>`;
      dom.platformStrip.appendChild(chip);
    });
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
      article.className = "content-item";
      const title = escapeHtml(item.title || "未命名内容");
      const url = item.url ? escapeHtml(item.url) : "";
      const titleHtml = url
        ? `<a class="content-title" href="${url}" target="_blank" rel="noopener noreferrer">${title}</a>`
        : `<span class="content-title">${title}</span>`;

      article.innerHTML = `
        <div>
          <span class="content-rank">#${escapeHtml(item.rank || "-")}</span>
          <span class="content-platform">${escapeHtml(item.platform_name || item.platform_id || "未知平台")}</span>
        </div>
        <div>${titleHtml}</div>
        <div class="content-meta">${escapeHtml(item.platform_id || "")}</div>
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
      state.platformId = dom.platformSelect.value;
      renderItems();
    });

    dom.clearButton.addEventListener("click", () => {
      state.query = "";
      state.platformId = "";
      dom.searchInput.value = "";
      dom.platformSelect.value = "";
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
