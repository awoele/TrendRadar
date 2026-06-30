(function () {
  const dom = {
    statusBand: document.getElementById("statusBand"),
    updatedAt: document.getElementById("updatedAt"),
    totalCrawled: document.getElementById("totalCrawled"),
    totalMatched: document.getElementById("totalMatched"),
    matchRate: document.getElementById("matchRate"),
    failedCount: document.getElementById("failedCount"),
    platformCount: document.getElementById("platformCount"),
    platformRows: document.getElementById("platformRows"),
    keywordRows: document.getElementById("keywordRows"),
    failedPlatforms: document.getElementById("failedPlatforms"),
    emptyTemplate: document.getElementById("emptyTemplate")
  };

  function formatNumber(value) {
    const number = Number(value || 0);
    return new Intl.NumberFormat("zh-CN").format(number);
  }

  function formatPercent(part, total) {
    if (!total) {
      return "0%";
    }
    return `${Math.round((part / total) * 100)}%`;
  }

  function formatDate(value) {
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) {
      return "未知";
    }
    return new Intl.DateTimeFormat("zh-CN", {
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      hour12: false
    }).format(date);
  }

  function escapeHtml(value) {
    return String(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function compactKeywordName(value) {
    const parts = String(value || "").trim().split(/\s+/).filter(Boolean);
    if (parts.length <= 6) {
      return parts.join(" ");
    }
    return `${parts.slice(0, 6).join(" / ")} ...`;
  }

  function emptyNode(text) {
    const node = dom.emptyTemplate.content.firstElementChild.cloneNode(true);
    node.textContent = text || "暂无数据";
    return node;
  }

  function renderSummary(stats) {
    const totals = stats.totals || {};
    const crawled = Number(totals.crawled_titles || 0);
    const matched = Number(totals.matched_titles || 0);
    const failed = Number(totals.failed_platforms || 0);

    dom.updatedAt.textContent = formatDate(stats.generated_at);
    dom.totalCrawled.textContent = formatNumber(crawled);
    dom.totalMatched.textContent = formatNumber(matched);
    dom.matchRate.textContent = formatPercent(matched, crawled);
    dom.failedCount.textContent = formatNumber(failed);
  }

  function renderPlatforms(platforms) {
    const items = Array.isArray(platforms) ? platforms : [];
    dom.platformRows.innerHTML = "";
    dom.platformCount.textContent = `${items.length} 个平台`;
    if (!items.length) {
      const row = document.createElement("tr");
      const cell = document.createElement("td");
      cell.colSpan = 4;
      cell.appendChild(emptyNode("暂无平台统计"));
      row.appendChild(cell);
      dom.platformRows.appendChild(row);
      return;
    }

    const maxCrawled = Math.max(...items.map((item) => Number(item.crawled || 0)), 1);
    items.forEach((platform) => {
      const crawled = Number(platform.crawled || 0);
      const matched = Number(platform.matched || 0);
      const width = Math.max(4, Math.round((crawled / maxCrawled) * 100));
      const row = document.createElement("tr");
      row.innerHTML = `
        <td>
          <div class="platform-name">
            <strong>${escapeHtml(platform.name || platform.id || "未知平台")}</strong>
            <span>${escapeHtml(platform.id || platform.name || "-")}</span>
          </div>
        </td>
        <td>${formatNumber(crawled)}</td>
        <td>${formatNumber(matched)}</td>
        <td class="bar-cell">
          <div class="bar-track" aria-label="${escapeHtml(formatPercent(crawled, maxCrawled))}">
            <div class="bar-fill" style="width: ${width}%"></div>
          </div>
        </td>
      `;
      dom.platformRows.appendChild(row);
    });
  }

  function renderKeywords(keywords) {
    const items = Array.isArray(keywords) ? keywords.slice(0, 12) : [];
    dom.keywordRows.innerHTML = "";
    if (!items.length) {
      dom.keywordRows.appendChild(emptyNode("暂无关键词命中"));
      return;
    }

    items.forEach((keyword) => {
      const platforms = Array.isArray(keyword.platforms)
        ? keyword.platforms.map((item) => item.name).slice(0, 3).join(" / ")
        : "";
      const item = document.createElement("div");
      item.className = "rank-item";
      item.innerHTML = `
        <div>
          <strong title="${escapeHtml(keyword.name || "")}">${escapeHtml(compactKeywordName(keyword.name || "未命名"))}</strong>
          <span>${escapeHtml(platforms || "暂无平台")}</span>
        </div>
        <span class="count-badge">${formatNumber(keyword.matched || 0)}</span>
      `;
      dom.keywordRows.appendChild(item);
    });
  }

  function renderFailures(failedPlatforms) {
    const items = Array.isArray(failedPlatforms) ? failedPlatforms : [];
    dom.failedPlatforms.innerHTML = "";
    if (!items.length) {
      dom.failedPlatforms.appendChild(emptyNode("本次没有失败平台"));
      return;
    }

    items.forEach((name) => {
      const item = document.createElement("div");
      item.className = "failure-item";
      item.textContent = name;
      dom.failedPlatforms.appendChild(item);
    });
  }

  function render(stats) {
    renderSummary(stats);
    renderPlatforms(stats.platforms);
    renderKeywords(stats.keywords);
    renderFailures(stats.failed_platforms);
  }

  async function boot() {
    try {
      const response = await fetch(`../stats.json?ts=${Date.now()}`, {
        cache: "no-store"
      });
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      const stats = await response.json();
      render(stats);
    } catch (error) {
      dom.statusBand.classList.add("bad");
      dom.updatedAt.textContent = "统计加载失败";
      dom.platformRows.innerHTML = "";
      dom.keywordRows.innerHTML = "";
      dom.failedPlatforms.innerHTML = "";
      dom.keywordRows.appendChild(emptyNode(error.message));
    }
  }

  boot();
})();
