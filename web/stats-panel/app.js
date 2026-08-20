(function () {
  const dom = {
    statusBand: document.getElementById("statusBand"),
    dataCutoff: document.getElementById("dataCutoff"),
    generatedAt: document.getElementById("generatedAt"),
    totalUnique: document.getElementById("totalUnique"),
    structuredItems: document.getElementById("structuredItems"),
    duplicateRate: document.getElementById("duplicateRate"),
    riskReview: document.getElementById("riskReview"),
    platformCount: document.getElementById("platformCount"),
    platformRows: document.getElementById("platformRows"),
    keywordRows: document.getElementById("keywordRows"),
    collectionStatus: document.getElementById("collectionStatus"),
    emptyTemplate: document.getElementById("emptyTemplate"),
    viewDescription: document.getElementById("viewDescription"),
    reportHeadline: document.getElementById("reportHeadline"),
    reportSummary: document.getElementById("reportSummary"),
    reportMeta: document.getElementById("reportMeta"),
    reportUnit: document.getElementById("reportUnit"),
    reportScope: document.getElementById("reportScope"),
    reportKpis: document.getElementById("reportKpis"),
    insightCards: document.getElementById("insightCards"),
    structuredBase: document.getElementById("structuredBase"),
    dimensionCards: document.getElementById("dimensionCards"),
    qualityScore: document.getElementById("qualityScore"),
    qualitySummary: document.getElementById("qualitySummary"),
    qualityRows: document.getElementById("qualityRows"),
    comparisonHead: document.getElementById("comparisonHead"),
    comparisonRows: document.getElementById("comparisonRows"),
    comparisonCards: document.getElementById("comparisonCards"),
    opportunityRows: document.getElementById("opportunityRows"),
    recipeRows: document.getElementById("recipeRows"),
    methodRules: document.getElementById("methodRules"),
    safeClaims: document.getElementById("safeClaims"),
    unsupportedClaims: document.getElementById("unsupportedClaims")
  };

  const viewTabs = Array.from(document.querySelectorAll("[data-view]"));
  const viewPanels = {
    dashboard: document.getElementById("dashboardView"),
    report: document.getElementById("reportView")
  };
  const viewDescriptions = {
    dashboard: "快速查看样本规模、来源构成与高频标签",
    report: "阅读带分母、证据边界和验收条件的深度判断"
  };

  function formatNumber(value) {
    const number = Number(value || 0);
    return new Intl.NumberFormat("zh-CN").format(number);
  }

  function formatPercent(rate, digits) {
    const number = Number(rate || 0) * 100;
    return `${number.toFixed(typeof digits === "number" ? digits : 1)}%`;
  }

  function formatDate(value, includeTime) {
    const dateOnly = String(value || "").match(/^(\d{4})-(\d{2})-(\d{2})$/);
    if (dateOnly) {
      return `${dateOnly[1]}/${dateOnly[2]}/${dateOnly[3]}`;
    }
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) {
      return "未知";
    }
    const options = {
      year: "numeric",
      month: "2-digit",
      day: "2-digit"
    };
    if (includeTime) {
      options.hour = "2-digit";
      options.minute = "2-digit";
      options.hour12 = false;
    }
    return new Intl.DateTimeFormat("zh-CN", options).format(date);
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

  function setView(view, options) {
    const nextView = view === "report" ? "report" : "dashboard";
    const settings = options || {};

    viewTabs.forEach((tab) => {
      const selected = tab.dataset.view === nextView;
      tab.setAttribute("aria-selected", String(selected));
      tab.tabIndex = selected ? 0 : -1;
    });
    Object.entries(viewPanels).forEach(([name, panel]) => {
      panel.hidden = name !== nextView;
    });
    dom.viewDescription.textContent = viewDescriptions[nextView];
    document.title = nextView === "report"
      ? "TrendRadar 深度报告"
      : "TrendRadar 统计";

    if (settings.updateUrl !== false) {
      const url = new URL(window.location.href);
      url.hash = nextView === "report" ? "report" : "";
      window.history.replaceState(null, "", url);
    }
    if (settings.focus) {
      const activeTab = viewTabs.find((tab) => tab.dataset.view === nextView);
      if (activeTab) {
        activeTab.focus();
      }
    }
  }

  function bindViewTabs() {
    viewTabs.forEach((tab, index) => {
      tab.addEventListener("click", () => {
        setView(tab.dataset.view, { focus: false });
      });
      tab.addEventListener("keydown", (event) => {
        if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) {
          return;
        }
        event.preventDefault();
        let nextIndex = index;
        if (event.key === "ArrowLeft") {
          nextIndex = (index - 1 + viewTabs.length) % viewTabs.length;
        } else if (event.key === "ArrowRight") {
          nextIndex = (index + 1) % viewTabs.length;
        } else if (event.key === "Home") {
          nextIndex = 0;
        } else if (event.key === "End") {
          nextIndex = viewTabs.length - 1;
        }
        setView(viewTabs[nextIndex].dataset.view, { focus: true });
      });
    });
    window.addEventListener("hashchange", () => {
      setView(window.location.hash === "#report" ? "report" : "dashboard", {
        updateUrl: false
      });
    });
  }

  function renderSummary(stats) {
    const report = stats.analysis_report || {};
    if (!report.version) {
      const totals = stats.totals || {};
      dom.dataCutoff.textContent = "深度报告未生成";
      dom.generatedAt.textContent = formatDate(stats.generated_at, true);
      dom.totalUnique.textContent = formatNumber(
        totals.content_items || totals.crawled_titles || 0
      );
      dom.structuredItems.textContent = "—";
      dom.duplicateRate.textContent = "—";
      dom.riskReview.textContent = "—";
      return;
    }
    const scope = report.scope || {};
    const quality = report.sample_quality || {};
    const risk = report.risk_summary || {};
    const windowData = ((scope.date_windows || {}).structured || {});

    dom.dataCutoff.textContent = windowData.end
      ? formatDate(windowData.end, false)
      : "暂无结构化日期";
    dom.generatedAt.textContent = formatDate(stats.generated_at, true);
    dom.totalUnique.textContent = formatNumber(scope.total_items);
    dom.structuredItems.textContent = formatNumber(scope.structured_items);
    dom.duplicateRate.textContent = formatPercent(quality.duplicate_rate);
    dom.riskReview.textContent = formatNumber(risk.count);
  }

  function renderPlatforms(platforms, total) {
    const items = Array.isArray(platforms) ? platforms : [];
    dom.platformRows.innerHTML = "";
    dom.platformCount.textContent = `${items.length} 个来源`;
    if (!items.length) {
      const row = document.createElement("tr");
      const cell = document.createElement("td");
      cell.colSpan = 4;
      cell.appendChild(emptyNode("暂无来源构成"));
      row.appendChild(cell);
      dom.platformRows.appendChild(row);
      return;
    }

    items.forEach((platform) => {
      const count = Number(platform.count || 0);
      const share = Number.isFinite(Number(platform.share))
        ? Number(platform.share)
        : count / Math.max(Number(total || 0), 1);
      const width = count ? Math.max(3, Math.round(share * 100)) : 0;
      const row = document.createElement("tr");
      row.innerHTML = `
        <td>
          <div class="platform-name">
            <strong>${escapeHtml(platform.name || platform.id || "未知来源")}</strong>
            <span>${escapeHtml(platform.id || platform.name || "-")}</span>
          </div>
        </td>
        <td>${formatNumber(count)}</td>
        <td>${platform.structured_count === undefined ? "—" : formatNumber(platform.structured_count)}</td>
        <td class="bar-cell">
          <div class="bar-value"><span>${formatPercent(share)}</span></div>
          <div class="bar-track" role="img" aria-label="占当前样本 ${escapeHtml(formatPercent(share))}">
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
      dom.keywordRows.appendChild(emptyNode("暂无结构化标签"));
      return;
    }

    items.forEach((keyword) => {
      const platforms = Array.isArray(keyword.platforms)
        ? keyword.platforms.map((item) => item.name).slice(0, 3).join(" / ")
        : "";
      const item = document.createElement("div");
      item.className = "rank-item";
      item.innerHTML = `
        <div class="rank-copy">
          <span class="dimension-badge">${escapeHtml(keyword.dimension_label || "标签")}</span>
          <strong title="${escapeHtml(keyword.name || "")}">${escapeHtml(compactKeywordName(keyword.name || "未命名"))}</strong>
          <span>${escapeHtml(platforms || "暂无来源")}</span>
        </div>
        <span class="count-badge">${formatNumber(keyword.matched || 0)}</span>
      `;
      dom.keywordRows.appendChild(item);
    });
  }

  function renderCollectionStatus(status) {
    const value = status || {};
    dom.collectionStatus.innerHTML = `
      <span class="state-marker" aria-hidden="true"></span>
      <div>
        <strong>${escapeHtml(value.label || "采集状态未知")}</strong>
        <p>${escapeHtml(value.detail || "当前产物没有可验证的采集运行记录。")}</p>
      </div>
    `;
  }

  function createMetaChip(text, tone) {
    const chip = document.createElement("span");
    chip.className = `meta-chip${tone ? ` ${tone}` : ""}`;
    chip.textContent = text;
    return chip;
  }

  function renderReportHero(report) {
    const scope = report.scope || {};
    const summary = report.executive_summary || {};
    const windows = scope.date_windows || {};
    const structuredWindow = windows.structured || {};

    dom.reportHeadline.textContent = summary.headline || "当前样本尚不足以形成结构化判断";
    dom.reportSummary.textContent = summary.summary || "分析报告暂无内容。";
    dom.reportUnit.textContent = scope.unit || "精确 URL 唯一内容";
    dom.reportScope.textContent = `当前静态样本 · ${formatNumber(scope.source_files)} 个数据批次`;
    dom.reportMeta.innerHTML = "";
    dom.reportMeta.appendChild(createMetaChip(`结构化选题 N=${formatNumber(scope.structured_items)}`, "teal"));
    if (structuredWindow.start && structuredWindow.end) {
      dom.reportMeta.appendChild(createMetaChip(`选题窗口 ${structuredWindow.start} — ${structuredWindow.end}`));
    }
    if (scope.freshness_days !== null && scope.freshness_days !== undefined) {
      dom.reportMeta.appendChild(createMetaChip(`距数据截止 ${formatNumber(scope.freshness_days)} 天`, "amber"));
    }
  }

  function renderReportKpis(report) {
    const scope = report.scope || {};
    const sample = report.sample_quality || {};
    const candidate = report.candidate_pool || {};
    const cards = [
      {
        label: "原始导入行",
        value: formatNumber(sample.raw_rows),
        detail: `${formatNumber(scope.source_files)} 个非 smoke 数据批次`,
        tone: "neutral"
      },
      {
        label: "精确 URL 唯一内容",
        value: formatNumber(sample.unique_items),
        detail: `重复 ${formatNumber(sample.duplicate_urls)} 条 · ${formatPercent(sample.duplicate_rate)}`,
        tone: "blue"
      },
      {
        label: "结构化标签覆盖",
        value: formatPercent(scope.structured_rate),
        detail: `${formatNumber(scope.structured_items)}/${formatNumber(scope.total_items)} 条`,
        tone: "teal"
      },
      {
        label: "低风险候选池",
        value: formatNumber(candidate.safe_count),
        detail: `占结构化样本 ${formatPercent(candidate.safe_rate)}`,
        tone: "teal"
      }
    ];

    dom.reportKpis.innerHTML = "";
    cards.forEach((card) => {
      const article = document.createElement("article");
      article.className = `report-kpi ${card.tone}`;
      article.innerHTML = `
        <span>${escapeHtml(card.label)}</span>
        <strong>${escapeHtml(card.value)}</strong>
        <p>${escapeHtml(card.detail)}</p>
      `;
      dom.reportKpis.appendChild(article);
    });
  }

  function renderInsights(insights) {
    const items = Array.isArray(insights) ? insights : [];
    dom.insightCards.innerHTML = "";
    if (!items.length) {
      dom.insightCards.appendChild(emptyNode("当前样本不足以生成决策摘要"));
      return;
    }

    dom.insightCards.setAttribute("role", "list");
    const gridHead = document.createElement("div");
    gridHead.className = "insight-grid-head";
    gridHead.setAttribute("aria-hidden", "true");
    gridHead.setAttribute("role", "presentation");
    gridHead.innerHTML = "<span>优先级 / 结论</span><span>证据</span><span>判断</span><span>动作</span>";
    dom.insightCards.appendChild(gridHead);

    items.forEach((insight) => {
      const article = document.createElement("article");
      article.className = "insight-card";
      article.setAttribute("role", "listitem");
      article.innerHTML = `
        <header class="insight-head">
          <div class="insight-flags">
            <span class="priority-badge ${escapeHtml(String(insight.priority || "P2").toLowerCase())}">${escapeHtml(insight.priority || "P2")}</span>
            <span class="insight-type">${escapeHtml(insight.type || "分析判断")}</span>
          </div>
          <h3>${escapeHtml(insight.title || "未命名判断")}</h3>
        </header>
        <div class="evidence-chain">
          <section class="chain-step evidence">
            <span>证据</span>
            <p>${escapeHtml(insight.evidence || "暂无")}</p>
          </section>
          <section class="chain-step judgment">
            <span>判断</span>
            <p>${escapeHtml(insight.judgment || "暂无")}</p>
          </section>
          <section class="chain-step action">
            <span>动作</span>
            <p>${escapeHtml(insight.action || "暂无")}</p>
          </section>
        </div>
        <footer class="insight-foot">
          <span><b>责任角色</b>${escapeHtml(insight.owner || "待分配")}</span>
          <span><b>验收条件</b>${escapeHtml(insight.acceptance || "待定义")}</span>
        </footer>
      `;
      dom.insightCards.appendChild(article);
    });
  }

  function renderDimensions(report) {
    const preferred = [
      "case_type",
      "built_thing",
      "target_audience",
      "hook",
      "tool_stack",
      "content_value"
    ];
    const dimensions = Array.isArray(report.dimensions) ? report.dimensions : [];
    const byId = Object.fromEntries(dimensions.map((item) => [item.id, item]));
    const scope = report.scope || {};
    dom.structuredBase.textContent = `N = ${formatNumber(scope.structured_items)}`;
    dom.dimensionCards.innerHTML = "";

    preferred.forEach((id) => {
      const dimension = byId[id];
      if (!dimension) {
        return;
      }
      const card = document.createElement("article");
      card.className = "dimension-card";
      const rows = (dimension.items || []).slice(0, 5).map((item) => `
        <div class="distribution-row">
          <div class="distribution-label">
            <span>${escapeHtml(item.name)}</span>
            <b>${formatNumber(item.count)} · ${formatPercent(item.rate)}</b>
          </div>
          <div class="mini-track" role="img" aria-label="${escapeHtml(item.name)} ${escapeHtml(formatPercent(item.rate))}">
            <span style="width:${Math.max(2, Number(item.rate || 0) * 100)}%"></span>
          </div>
        </div>
      `).join("");
      card.innerHTML = `
        <header>
          <h3>${escapeHtml(dimension.label)}</h3>
          <span>字段覆盖 ${formatPercent(dimension.coverage)}</span>
        </header>
        <div class="distribution-list">${rows || '<p class="empty">暂无标签</p>'}</div>
      `;
      dom.dimensionCards.appendChild(card);
    });
  }

  function renderQuality(report) {
    const fieldQuality = ((report.sample_quality || {}).field_quality || {});
    const fields = Array.isArray(fieldQuality.core_fields) ? fieldQuality.core_fields : [];
    dom.qualityScore.textContent = `总体 ${formatPercent(fieldQuality.core_completeness)}`;
    const lowest = fields.slice().sort((a, b) => Number(a.rate) - Number(b.rate))[0];
    dom.qualitySummary.textContent = lowest
      ? `最低覆盖字段为“${lowest.label}”，仍缺 ${formatNumber(lowest.missing)} 条；空值不按否定处理。`
      : "暂无字段完整度数据。";
    dom.qualityRows.innerHTML = "";

    fields.forEach((field) => {
      const row = document.createElement("div");
      row.className = "quality-row";
      row.innerHTML = `
        <div>
          <span>${escapeHtml(field.label)}</span>
          <b>${formatPercent(field.rate)}</b>
        </div>
        <div class="quality-track" role="img" aria-label="${escapeHtml(field.label)}覆盖 ${escapeHtml(formatPercent(field.rate))}">
          <span style="width:${Number(field.rate || 0) * 100}%"></span>
        </div>
        <small>${formatNumber(field.count)}/${formatNumber(field.denominator)} · 缺 ${formatNumber(field.missing)}</small>
      `;
      dom.qualityRows.appendChild(row);
    });
  }

  function renderComparisons(comparisons) {
    const items = Array.isArray(comparisons) ? comparisons.slice(0, 8) : [];
    dom.comparisonHead.innerHTML = "";
    dom.comparisonRows.innerHTML = "";
    dom.comparisonCards.innerHTML = "";
    if (!items.length) {
      const row = document.createElement("tr");
      const cell = document.createElement("td");
      cell.colSpan = 4;
      cell.appendChild(emptyNode("至少需要两个有结构化标签的平台样本"));
      row.appendChild(cell);
      dom.comparisonRows.appendChild(row);
      dom.comparisonCards.appendChild(emptyNode("至少需要两个有结构化标签的平台样本"));
      return;
    }

    const platforms = items[0].platforms || [];
    const header = document.createElement("tr");
    header.innerHTML = `
      <th>维度 / 标签</th>
      ${platforms.map((platform) => `<th>${escapeHtml(platform.name)}</th>`).join("")}
      <th>占比差</th>
    `;
    dom.comparisonHead.appendChild(header);

    items.forEach((item) => {
      const rates = Object.fromEntries((item.platforms || []).map((platform) => [platform.id, platform]));
      const row = document.createElement("tr");
      row.innerHTML = `
        <td data-label="维度 / 标签">
          <span class="table-dimension">${escapeHtml(item.dimension_label || "标签")}</span>
          <strong>${escapeHtml(item.label)}</strong>
        </td>
        ${platforms.map((platform) => {
          const value = rates[platform.id] || {};
          return `<td data-label="${escapeHtml(platform.name)}"><strong>${formatPercent(value.rate)}</strong><span>${formatNumber(value.count)}/${formatNumber(value.denominator)} · 覆盖 ${formatPercent(value.coverage)}</span></td>`;
        }).join("")}
        <td data-label="占比差"><span class="delta-pill">${(Number(item.gap || 0) * 100).toFixed(1)}pp</span></td>
      `;
      dom.comparisonRows.appendChild(row);

      const gap = (Number(item.gap || 0) * 100).toFixed(1);
      const card = document.createElement("article");
      card.className = "comparison-card";
      card.innerHTML = `
        <header>
          <div>
            <span class="table-dimension">${escapeHtml(item.dimension_label || "标签")}</span>
            <h3>${escapeHtml(item.label)}</h3>
          </div>
          <span class="delta-pill" aria-label="占比差 ${gap} 个百分点">${gap}pp</span>
        </header>
        <dl class="comparison-card-metrics">
          ${platforms.map((platform) => {
            const value = rates[platform.id] || {};
            return `
              <div>
                <dt>${escapeHtml(platform.name)}</dt>
                <dd>
                  <strong>${formatPercent(value.rate)}</strong>
                  <span>${formatNumber(value.count)}/${formatNumber(value.denominator)} · 覆盖 ${formatPercent(value.coverage)}</span>
                </dd>
              </div>
            `;
          }).join("")}
        </dl>
      `;
      dom.comparisonCards.appendChild(card);
    });
  }

  function renderOpportunities(opportunities) {
    const items = Array.isArray(opportunities) ? opportunities.slice(0, 6) : [];
    dom.opportunityRows.innerHTML = "";
    if (!items.length) {
      dom.opportunityRows.appendChild(emptyNode("没有达到 N≥10 的候选方向"));
      return;
    }

    items.forEach((item, index) => {
      const row = document.createElement("article");
      row.className = "opportunity-row";
      const mainPlatform = (item.platforms || [])[0];
      row.innerHTML = `
        <span class="opportunity-rank">${String(index + 1).padStart(2, "0")}</span>
        <div class="opportunity-copy">
          <div>
            <h3>${escapeHtml(item.label)}</h3>
            <span>${mainPlatform ? `主要来源 ${escapeHtml(mainPlatform.name)}` : "来源未知"}</span>
          </div>
          <p>样本 ${formatNumber(item.count)} · 候选信号 ${formatNumber(item.candidate_count)} · 风险标记 ${formatNumber(item.risk_count)}</p>
          <div class="candidate-track" role="img" aria-label="低风险候选 ${formatNumber(item.safe_candidate_count)} 条">
            <span style="width:${Number(item.safe_candidate_rate || 0) * 100}%"></span>
          </div>
        </div>
        <div class="candidate-count">
          <strong>${formatNumber(item.safe_candidate_count)}</strong>
          <span>低风险候选</span>
        </div>
      `;
      dom.opportunityRows.appendChild(row);
    });
  }

  function renderRecipes(recipes) {
    const items = Array.isArray(recipes) ? recipes.slice(0, 5) : [];
    dom.recipeRows.innerHTML = "";
    if (!items.length) {
      dom.recipeRows.appendChild(emptyNode("没有达到 N≥10 的叙事组合"));
      return;
    }

    items.forEach((item) => {
      const row = document.createElement("article");
      row.className = "recipe-row";
      row.innerHTML = `
        <div class="recipe-labels">
          <span>${escapeHtml(item.built_thing)}</span>
          <i aria-hidden="true">×</i>
          <span>${escapeHtml(item.hook)}</span>
        </div>
        <div class="recipe-metrics">
          <strong>${formatNumber(item.count)} 条</strong>
          <span>${formatNumber(item.safe_candidate_count)} 条低风险候选</span>
        </div>
      `;
      dom.recipeRows.appendChild(row);
    });
  }

  function renderList(target, items) {
    target.innerHTML = "";
    (Array.isArray(items) ? items : []).forEach((value) => {
      const item = document.createElement("li");
      item.textContent = value;
      target.appendChild(item);
    });
  }

  function renderMethodology(methodology) {
    const value = methodology || {};
    renderList(dom.methodRules, value.rules);
    renderList(dom.safeClaims, value.safe_claims);
    renderList(dom.unsupportedClaims, value.unsupported_claims);
  }

  function renderReport(report) {
    if (!report || !report.version) {
      viewPanels.report.classList.add("is-unavailable");
      dom.reportHeadline.textContent = "深度报告尚未生成";
      dom.reportSummary.textContent = "请重新构建静态产物，确保 stats.json 包含 analysis_report。";
      dom.reportMeta.innerHTML = "";
      dom.reportUnit.textContent = "当前不可用";
      dom.reportScope.textContent = "数据看板仍可读取兼容字段";
      dom.reportKpis.innerHTML = "";
      dom.reportKpis.appendChild(emptyNode("暂无报告数据"));
      return;
    }
    viewPanels.report.classList.remove("is-unavailable");
    renderReportHero(report);
    renderReportKpis(report);
    renderInsights(report.insights);
    renderDimensions(report);
    renderQuality(report);
    renderComparisons(report.platform_comparisons);
    renderOpportunities(report.opportunities);
    renderRecipes(report.recipes);
    renderMethodology(report.methodology);
  }

  function render(stats) {
    const report = stats.analysis_report || {};
    renderSummary(stats);
    renderPlatforms(stats.platforms, (report.scope || {}).total_items);
    renderKeywords(stats.keywords);
    renderCollectionStatus(stats.collection_status);
    renderReport(report);
  }

  async function boot() {
    bindViewTabs();
    setView(window.location.hash === "#report" ? "report" : "dashboard", {
      updateUrl: false
    });

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
      dom.dataCutoff.textContent = "统计加载失败";
      dom.platformRows.innerHTML = "";
      dom.keywordRows.innerHTML = "";
      dom.collectionStatus.innerHTML = "";
      dom.keywordRows.appendChild(emptyNode(error.message));
      dom.reportHeadline.textContent = "报告加载失败";
      dom.reportSummary.textContent = `无法读取统计数据：${error.message}`;
    }
  }

  boot();
})();
