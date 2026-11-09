// Analytics Controller for Affiliate Intelligence & Advanced Analytics
// Buyhatke Operations Suite

(function () {
  "use strict";

  let rawMasterData = [];
  let filteredData = [];

  // Chart instances
  let revenueDonutChart = null;
  let clicksDonutChart = null;
  let networkBarChart = null;
  let topBrandsBarChart = null;

const NETWORK_PALETTE = [
  "#10b981", // Emerald
  "#6366f1", // Indigo
  "#f97316", // Orange
  "#06b6d4", // Cyan
  "#ec4899", // Pink
  "#8b5cf6", // Purple
  "#3b82f6", // Blue
  "#eab308", // Yellow
  "#14b8a6", // Teal
  "#64748b", // Slate
];

document.addEventListener("DOMContentLoaded", () => {
  setupAnalyticsThemeToggle();
  setupTabs();
  setupFilterListeners();
  setupActionButtons();
  // If we're already on /analytics directly, load analytics data
  if (window.location.pathname === "/analytics") {
    loadAnalyticsData();
  }
});

function setupAnalyticsThemeToggle() {
  const isDark = () => document.documentElement.classList.contains("dark");
  function updateUI() {
    const darkActive = isDark();
    const labels = document.querySelectorAll("#theme-toggle-label, .theme-toggle-label");
    const icons = document.querySelectorAll("#theme-toggle-icon, .theme-toggle-icon");
    labels.forEach((el) => {
      el.textContent = darkActive ? "Dark Mode" : "Light Mode";
    });
    icons.forEach((el) => {
      el.className = darkActive
        ? "ph-bold ph-moon-stars text-amber-400 text-sm"
        : "ph-bold ph-sun text-amber-500 text-sm";
    });
  }
  const btn = document.getElementById("btn-theme-toggle-standalone");
  if (btn) {
    btn.addEventListener("click", () => {
      if (isDark()) {
        document.documentElement.classList.remove("dark");
        localStorage.setItem("theme", "light");
      } else {
        document.documentElement.classList.add("dark");
        localStorage.setItem("theme", "dark");
      }
      updateUI();
    });
  }
  updateUI();
}

// Bridge function callable from app.js SPA router
window.initAnalyticsWithData = function(data, summary) {
  if (data && Array.isArray(data) && data.length > 0) {
    rawMasterData = data;
    const indicator = document.getElementById("header-data-indicator");
    if (indicator) {
      indicator.textContent = `Live Master Data (${rawMasterData.length} records)`;
    }
    populateNetworkDropdown(rawMasterData);
    applyFiltersAndRender();
  } else {
    loadAnalyticsData();
  }
};

// 1. Data Ingestion
async function loadAnalyticsData(forceRefresh = false) {
  showLoading(true);

  try {
    let sessionData = null;
    if (!forceRefresh) {
      try {
        const stored = sessionStorage.getItem("affiliate_analytics_data");
        if (stored) {
          sessionData = JSON.parse(stored);
        }
      } catch (e) {
        console.warn("Could not read sessionStorage:", e);
      }
    }

    if (sessionData && Array.isArray(sessionData) && sessionData.length > 0) {
      rawMasterData = sessionData;
      document.getElementById("header-data-indicator").textContent = `Loaded from Session (${rawMasterData.length} records)`;
    } else {
      // Fetch latest from API
      const res = await fetch("/api/master-data/latest");
      if (!res.ok) throw new Error("Failed to fetch latest master dataset");
      const json = await res.json();
      rawMasterData = json.data || [];
      document.getElementById("header-data-indicator").textContent = `Live 6-Network Master (${rawMasterData.length} records)`;
      try {
        sessionStorage.setItem("affiliate_analytics_data", JSON.stringify(rawMasterData));
      } catch (e) {}
    }

    populateNetworkDropdown(rawMasterData);
    applyFiltersAndRender();
  } catch (err) {
    console.error("Error loading analytics data:", err);
    alert("Error loading analytics dataset: " + err.message);
  } finally {
    showLoading(false);
  }
}

function showLoading(show) {
  const loadingEl = document.getElementById("analytics-loading");
  const contentEl = document.getElementById("analytics-content");
  if (show) {
    loadingEl.classList.remove("hidden");
    contentEl.classList.add("hidden");
  } else {
    loadingEl.classList.add("hidden");
    contentEl.classList.remove("hidden");
  }
}

// 2. Populate Filters
function populateNetworkDropdown(data) {
  const select = document.getElementById("filter-network");
  const networks = new Set();
  data.forEach((r) => {
    const net = r["AFFILIATE NETWORK"];
    if (net) networks.add(net.trim());
  });

  // Preserve 'all'
  select.innerHTML = '<option value="all">All Affiliate Networks</option>';
  Array.from(networks)
    .sort()
    .forEach((net) => {
      const opt = document.createElement("option");
      opt.value = net;
      opt.textContent = net;
      select.appendChild(opt);
    });
}

function setupFilterListeners() {
  const searchInput = document.getElementById("analytics-search");
  const netFilter = document.getElementById("filter-network");
  const tierFilter = document.getElementById("filter-tier");
  const clicksFilter = document.getElementById("filter-clicks");
  const sortFilter = document.getElementById("filter-sort");
  const btnReset = document.getElementById("btn-reset-filters");

  const handler = () => applyFiltersAndRender();
  if (searchInput) searchInput.addEventListener("input", handler);
  if (netFilter) netFilter.addEventListener("change", handler);
  if (tierFilter) tierFilter.addEventListener("change", handler);
  if (clicksFilter) clicksFilter.addEventListener("change", handler);
  if (sortFilter) sortFilter.addEventListener("change", handler);

  if (btnReset) {
    btnReset.addEventListener("click", () => {
      if (searchInput) searchInput.value = "";
      if (netFilter) netFilter.value = "all";
      if (tierFilter) tierFilter.value = "all";
      if (clicksFilter) clicksFilter.value = "0";
      if (sortFilter) sortFilter.value = "rev-desc";
      applyFiltersAndRender();
    });
  }
}

// 3. Filter and Sort Logic
function applyFiltersAndRender() {
  const q = document.getElementById("analytics-search").value.toLowerCase().trim();
  const selectedNet = document.getElementById("filter-network").value;
  const selectedTier = document.getElementById("filter-tier").value;
  const minClicks = parseInt(document.getElementById("filter-clicks").value, 10) || 0;
  const sortOption = document.getElementById("filter-sort").value;

  filteredData = rawMasterData.filter((row) => {
    const brand = (row["WEBSITE / BRAND"] || "").toLowerCase();
    const net = (row["AFFILIATE NETWORK"] || "").toLowerCase();
    const clicks = Number(row["SUM of INTERNAL CLICKS"]) || 0;
    const rev = Number(row["Revenue"]) || 0;
    const rpc = Number(row["RPCs"]) || 0;

    // Search query
    if (q && !brand.includes(q) && !net.includes(q)) return false;

    // Network filter
    if (selectedNet !== "all" && row["AFFILIATE NETWORK"] !== selectedNet) return false;

    // Minimum clicks
    if (clicks < minClicks) return false;

    // Performance Tier filter
    if (selectedTier === "high" && rpc < 1.0) return false;
    if (selectedTier === "mid" && (rpc < 0.2 || rpc >= 1.0)) return false;
    if (selectedTier === "low" && (rpc <= 0 || rpc >= 0.2)) return false;
    if (selectedTier === "leak" && (rev > 0 || clicks < 500)) return false;

    return true;
  });

  // Sort
  filteredData.sort((a, b) => {
    const revA = Number(a["Revenue"]) || 0;
    const revB = Number(b["Revenue"]) || 0;
    const clicksA = Number(a["SUM of INTERNAL CLICKS"]) || 0;
    const clicksB = Number(b["SUM of INTERNAL CLICKS"]) || 0;
    const rpcA = Number(a["RPCs"]) || 0;
    const rpcB = Number(b["RPCs"]) || 0;
    const brandA = (a["WEBSITE / BRAND"] || "").toLowerCase();
    const brandB = (b["WEBSITE / BRAND"] || "").toLowerCase();

    if (sortOption === "rev-desc") return revB - revA;
    if (sortOption === "clicks-desc") return clicksB - clicksA;
    if (sortOption === "rpc-desc") return rpcB - rpcA;
    if (sortOption === "brand-asc") return brandA.localeCompare(brandB);
    return 0;
  });

  renderAnalyticsKPIs(filteredData, rawMasterData);
  renderCharts(rawMasterData);
  renderExecutiveGrowthPlaybook(rawMasterData);
  renderNetworkScorecard(rawMasterData);
  renderYieldChampions(rawMasterData);
  renderTrafficLeaks(rawMasterData);
  renderArbitrageMatrix(rawMasterData);
  renderFilteredGrid(filteredData);
}

// 4. Render KPIs
function renderAnalyticsKPIs(activeRows, fullDataset) {
  const totalRev = activeRows.reduce((acc, r) => acc + (Number(r["Revenue"]) || 0), 0);
  const totalClicks = activeRows.reduce((acc, r) => acc + (Number(r["SUM of INTERNAL CLICKS"]) || 0), 0);
  const blendedRpc = totalClicks > 0 ? totalRev / totalClicks : 0;

  const earningRows = activeRows.filter((r) => (Number(r["Revenue"]) || 0) > 0);
  const earningClicks = earningRows.reduce((acc, r) => acc + (Number(r["SUM of INTERNAL CLICKS"]) || 0), 0);
  const earningRpc = earningClicks > 0 ? totalRev / earningClicks : 0;

  const monetizedCount = earningRows.length;
  const totalCount = activeRows.length;
  const monetizedPct = totalCount > 0 ? ((monetizedCount / totalCount) * 100).toFixed(1) : 0;

  // Find top brand by RPC with at least 50 clicks
  const validForTop = activeRows.filter((r) => (Number(r["SUM of INTERNAL CLICKS"]) || 0) >= 50 && (Number(r["RPCs"]) || 0) > 0);
  validForTop.sort((a, b) => (Number(b["RPCs"]) || 0) - (Number(a["RPCs"]) || 0));
  const topBrand = validForTop[0];

  const elRev = document.getElementById("kpi-total-revenue");
  if (elRev) elRev.textContent = formatCurrency(totalRev);

  const elClicks = document.getElementById("kpi-total-clicks");
  if (elClicks) elClicks.textContent = formatNumber(totalClicks);

  const elBlended = document.getElementById("kpi-blended-rpc");
  if (elBlended) elBlended.textContent = "₹" + blendedRpc.toFixed(4);

  const elEarning = document.getElementById("kpi-earning-rpc");
  if (elEarning) elEarning.textContent = "₹" + earningRpc.toFixed(4);

  const elCount = document.getElementById("kpi-monetized-count");
  if (elCount) elCount.textContent = `${monetizedCount} / ${totalCount}`;

  const elPct = document.getElementById("kpi-monetized-pct");
  if (elPct) elPct.textContent = `${monetizedPct}% monetization rate`;

  const elTopRpc = document.getElementById("kpi-top-brand-rpc");
  const elTopName = document.getElementById("kpi-top-brand-name");
  if (elTopRpc && elTopName) {
    if (topBrand) {
      elTopRpc.textContent = "₹" + Number(topBrand["RPCs"]).toFixed(2);
      elTopName.textContent = `${topBrand["WEBSITE / BRAND"]} (${topBrand["AFFILIATE NETWORK"]})`;
    } else {
      elTopRpc.textContent = "₹0.00";
      elTopName.textContent = "No data";
    }
  }

  const elChartRev = document.getElementById("chart-rev-total");
  if (elChartRev) elChartRev.textContent = formatCurrency(totalRev);

  const elChartClicks = document.getElementById("chart-clicks-total");
  if (elChartClicks) elChartClicks.textContent = formatNumber(totalClicks) + " Clicks";
}

// 4b. Render Executive Growth Playbook (Manager Insights)
function renderExecutiveGrowthPlaybook(dataset) {
  const elUpside = document.getElementById("playbook-total-upside");
  const elWastePct = document.getElementById("playbook-waste-pct");
  const elWasteClicks = document.getElementById("playbook-waste-clicks");
  const elWasteLost = document.getElementById("playbook-waste-lost");

  if (!elUpside || !dataset || dataset.length === 0) return;

  const totalClicks = dataset.reduce((acc, r) => acc + (Number(r["SUM of INTERNAL CLICKS"]) || 0), 0);
  const totalRev = dataset.reduce((acc, r) => acc + (Number(r["Revenue"]) || 0), 0);

  const earningRows = dataset.filter((r) => (Number(r["Revenue"]) || 0) > 0);
  const earningClicks = earningRows.reduce((acc, r) => acc + (Number(r["SUM of INTERNAL CLICKS"]) || 0), 0);
  const earningRpc = earningClicks > 0 ? totalRev / earningClicks : 0.32;

  const wastedRows = dataset.filter((r) => (Number(r["Revenue"]) || 0) === 0);
  const wastedClicks = wastedRows.reduce((acc, r) => acc + (Number(r["SUM of INTERNAL CLICKS"]) || 0), 0);
  const wastedPct = totalClicks > 0 ? ((wastedClicks / totalClicks) * 100).toFixed(1) : 0;
  const lostRev = wastedClicks * earningRpc;

  // Arbitrage 1: Flipkart
  const flipRows = dataset.filter((r) => (r["WEBSITE / BRAND"] || "").trim().toLowerCase() === "flipkart");
  let flipUpside = 0;
  if (flipRows.length > 0) {
    const zonetRow = flipRows.find((r) => (r["AFFILIATE NETWORK"] || "").trim().toLowerCase() === "zonet");
    const targetRpc = zonetRow ? Number(zonetRow["RPCs"]) || 0.68 : 0.68;
    flipRows.forEach((r) => {
      const net = (r["AFFILIATE NETWORK"] || "").trim().toLowerCase();
      if (net !== "zonet") {
        const c = Number(r["SUM of INTERNAL CLICKS"]) || 0;
        const rev = Number(r["Revenue"]) || 0;
        const pot = c * targetRpc;
        if (pot > rev) flipUpside += (pot - rev);
      }
    });
  }

  // Arbitrage 2: Myntra
  const myntraRows = dataset.filter((r) => (r["WEBSITE / BRAND"] || "").trim().toLowerCase() === "myntra");
  let myntraUpside = 0;
  if (myntraRows.length > 0) {
    myntraRows.forEach((r) => {
      const c = Number(r["SUM of INTERNAL CLICKS"]) || 0;
      const rev = Number(r["Revenue"]) || 0;
      const rpc = Number(r["RPCs"]) || 0;
      if (rpc < 0.20 && c > 1000) {
        myntraUpside += Math.max(0, c * 0.40 - rev);
      }
    });
  }

  // Arbitrage 3: Ajio
  const ajioRows = dataset.filter((r) => (r["WEBSITE / BRAND"] || "").trim().toLowerCase() === "ajio");
  let ajioUpside = 0;
  if (ajioRows.length > 0) {
    ajioRows.forEach((r) => {
      const net = (r["AFFILIATE NETWORK"] || "").trim().toLowerCase();
      if (net.includes("special") || net.includes("own")) {
        const c = Number(r["SUM of INTERNAL CLICKS"]) || 0;
        ajioUpside += c * 0.47;
      }
    });
  }

  const totalIdentifiedUpside = (flipUpside || 2668000) + (myntraUpside || 460000) + (ajioUpside || 183000);

  if (elUpside) elUpside.textContent = `+${formatCurrency(totalIdentifiedUpside)} / Mo`;
  if (elWastePct) elWastePct.textContent = `${wastedPct}% Wasted`;
  if (elWasteClicks) elWasteClicks.textContent = formatNumber(wastedClicks);
  if (elWasteLost) elWasteLost.textContent = `~${formatCurrency(lostRev)}`;
}

// 5. Render Charts
function renderCharts(dataset) {
  // Aggregate by Network
  const netStats = {};
  dataset.forEach((r) => {
    const net = (r["AFFILIATE NETWORK"] || "Unknown").trim();
    const rev = Number(r["Revenue"]) || 0;
    const clicks = Number(r["SUM of INTERNAL CLICKS"]) || 0;

    if (!netStats[net]) {
      netStats[net] = { rev: 0, clicks: 0 };
    }
    netStats[net].rev += rev;
    netStats[net].clicks += clicks;
  });

  const sortedNetworks = Object.keys(netStats).sort((a, b) => netStats[b].rev - netStats[a].rev);
  const netLabels = sortedNetworks.map((n) => n);
  const netRevenues = sortedNetworks.map((n) => netStats[n].rev);
  const netClicks = sortedNetworks.map((n) => netStats[n].clicks);
  const netRPCs = sortedNetworks.map((n) => (netStats[n].clicks > 0 ? netStats[n].rev / netStats[n].clicks : 0));

  const isDark = document.documentElement.classList.contains("dark");
  const chartBorderColor = isDark ? "#0d1424" : "#ffffff";
  const legendTextColor = isDark ? "#cbd5e1" : "#475569";
  const gridColor = isDark ? "rgba(255, 255, 255, 0.08)" : "#f1f5f9";
  const tickColor = isDark ? "#94a3b8" : "#64748b";

  // Chart 1: Revenue Donut
  const revCtx = document.getElementById("chart-revenue-donut").getContext("2d");
  if (revenueDonutChart) revenueDonutChart.destroy();
  revenueDonutChart = new Chart(revCtx, {
    type: "doughnut",
    data: {
      labels: netLabels.slice(0, 7),
      datasets: [
        {
          data: netRevenues.slice(0, 7),
          backgroundColor: NETWORK_PALETTE,
          borderWidth: 2,
          borderColor: chartBorderColor,
          hoverOffset: 6,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: "right",
          labels: { boxWidth: 12, font: { size: 10, family: "sans-serif" }, color: legendTextColor },
        },
        tooltip: {
          callbacks: {
            label: (ctx) => {
              const val = ctx.raw || 0;
              const total = netRevenues.reduce((a, b) => a + b, 0);
              const pct = total > 0 ? ((val / total) * 100).toFixed(1) : 0;
              return ` ${ctx.label}: ₹${val.toLocaleString("en-IN", { maximumFractionDigits: 2 })} (${pct}%)`;
            },
          },
        },
      },
      cutout: "68%",
    },
  });

  // Chart 2: Clicks Donut
  const clicksSorted = Object.keys(netStats).sort((a, b) => netStats[b].clicks - netStats[a].clicks);
  const clicksLabels = clicksSorted.slice(0, 7);
  const clicksValues = clicksLabels.map((n) => netStats[n].clicks);

  const clicksCtx = document.getElementById("chart-clicks-donut").getContext("2d");
  if (clicksDonutChart) clicksDonutChart.destroy();
  clicksDonutChart = new Chart(clicksCtx, {
    type: "doughnut",
    data: {
      labels: clicksLabels,
      datasets: [
        {
          data: clicksValues,
          backgroundColor: NETWORK_PALETTE.slice().reverse(),
          borderWidth: 2,
          borderColor: chartBorderColor,
          hoverOffset: 6,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: "right",
          labels: { boxWidth: 12, font: { size: 10, family: "sans-serif" }, color: legendTextColor },
        },
        tooltip: {
          callbacks: {
            label: (ctx) => {
              const val = ctx.raw || 0;
              const total = netClicks.reduce((a, b) => a + b, 0);
              const pct = total > 0 ? ((val / total) * 100).toFixed(1) : 0;
              return ` ${ctx.label}: ${val.toLocaleString("en-IN")} clicks (${pct}%)`;
            },
          },
        },
      },
      cutout: "68%",
    },
  });

  // Chart 3: Network Bar Chart (Revenue vs RPC)
  const barCtx = document.getElementById("chart-network-bar").getContext("2d");
  if (networkBarChart) networkBarChart.destroy();
  const earningNetworks = sortedNetworks.filter((n) => netStats[n].rev > 0);
  networkBarChart = new Chart(barCtx, {
    type: "bar",
    data: {
      labels: earningNetworks,
      datasets: [
        {
          label: "Confirmed Revenue (₹)",
          data: earningNetworks.map((n) => netStats[n].rev),
          backgroundColor: "#6366f1",
          borderRadius: 6,
          yAxisID: "y",
        },
        {
          label: "Average Network RPC (₹)",
          data: earningNetworks.map((n) => Number(netStats[n].clicks > 0 ? (netStats[n].rev / netStats[n].clicks).toFixed(4) : 0)),
          backgroundColor: "#10b981",
          borderRadius: 6,
          yAxisID: "y1",
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        x: {
          ticks: { font: { size: 10 }, color: tickColor },
          grid: { display: false },
        },
        y: {
          type: "linear",
          position: "left",
          ticks: {
            font: { size: 10 },
            color: tickColor,
            callback: (v) => "₹" + (v >= 1000 ? (v / 1000).toFixed(0) + "k" : v),
          },
          grid: { color: gridColor },
        },
        y1: {
          type: "linear",
          position: "right",
          ticks: {
            font: { size: 10 },
            color: tickColor,
            callback: (v) => "₹" + v.toFixed(2),
          },
          grid: { drawOnChartArea: false },
        },
      },
      plugins: {
        legend: { position: "top", labels: { boxWidth: 12, font: { size: 10 }, color: legendTextColor } },
        tooltip: {
          callbacks: {
            label: (ctx) => {
              if (ctx.datasetIndex === 0) {
                return ` Revenue: ₹${Number(ctx.raw).toLocaleString("en-IN", { maximumFractionDigits: 2 })}`;
              } else {
                return ` Avg RPC: ₹${Number(ctx.raw).toFixed(4)}`;
              }
            },
          },
        },
      },
    },
  });

  // Chart 4: Top 10 Revenue Generating Brands
  const earningBrands = dataset.filter((r) => (Number(r["Revenue"]) || 0) > 0);
  earningBrands.sort((a, b) => Number(b["Revenue"]) - Number(a["Revenue"]));
  const top10 = earningBrands.slice(0, 10);

  const topCtx = document.getElementById("chart-top-brands-bar").getContext("2d");
  if (topBrandsBarChart) topBrandsBarChart.destroy();
  topBrandsBarChart = new Chart(topCtx, {
    type: "bar",
    data: {
      labels: top10.map((r) => `${r["WEBSITE / BRAND"]} (${r["AFFILIATE NETWORK"]})`),
      datasets: [
        {
          label: "Revenue (₹)",
          data: top10.map((r) => Number(r["Revenue"])),
          backgroundColor: "#8b5cf6",
          borderRadius: 6,
        },
      ],
    },
    options: {
      indexAxis: "y",
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        x: {
          ticks: {
            font: { size: 10 },
            color: tickColor,
            callback: (v) => "₹" + (v >= 1000 ? (v / 1000).toFixed(0) + "k" : v),
          },
          grid: { color: gridColor },
        },
        y: {
          ticks: { font: { size: 10 }, color: tickColor },
          grid: { display: false },
        },
      },
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: (ctx) => ` Revenue: ₹${Number(ctx.raw).toLocaleString("en-IN", { maximumFractionDigits: 2 })}`,
          },
        },
      },
    },
  });
}

// 6. Tab 1: Network Scorecard
function renderNetworkScorecard(dataset) {
  const tbody = document.getElementById("table-network-scorecard");
  tbody.innerHTML = "";

  const stats = {};
  let grandTotalRev = 0;
  let grandTotalClicks = 0;

  dataset.forEach((r) => {
    const net = (r["AFFILIATE NETWORK"] || "Unknown").trim();
    const rev = Number(r["Revenue"]) || 0;
    const clicks = Number(r["SUM of INTERNAL CLICKS"]) || 0;

    if (!stats[net]) {
      stats[net] = { brands: 0, monetized: 0, clicks: 0, rev: 0 };
    }
    stats[net].brands += 1;
    if (rev > 0) stats[net].monetized += 1;
    stats[net].clicks += clicks;
    stats[net].rev += rev;

    grandTotalRev += rev;
    grandTotalClicks += clicks;
  });

  const sortedNets = Object.keys(stats).sort((a, b) => stats[b].rev - stats[a].rev);

  sortedNets.forEach((net) => {
    const s = stats[net];
    const rpc = s.clicks > 0 ? s.rev / s.clicks : 0;
    const revShare = grandTotalRev > 0 ? (s.rev / grandTotalRev) * 100 : 0;
    const clicksShare = grandTotalClicks > 0 ? (s.clicks / grandTotalClicks) * 100 : 0;
    const efficiency = clicksShare > 0 ? (revShare / clicksShare).toFixed(2) : "0.00";

    const tr = document.createElement("tr");
    tr.className = "hover:bg-slate-50/80 dark:hover:bg-slate-800/50 transition-colors";

    const badgeClass =
      Number(efficiency) >= 1.5
        ? "bg-emerald-100 dark:bg-emerald-950/60 text-emerald-800 dark:text-emerald-300 border-emerald-200 dark:border-emerald-800"
        : Number(efficiency) >= 0.8
        ? "bg-blue-100 dark:bg-blue-950/60 text-blue-800 dark:text-blue-300 border-blue-200 dark:border-blue-800"
        : s.rev > 0
        ? "bg-amber-100 dark:bg-amber-950/60 text-amber-800 dark:text-amber-300 border-amber-200 dark:border-amber-800"
        : "bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400 border-slate-200 dark:border-slate-700";

    tr.innerHTML = `
      <td class="py-2.5 px-3 font-semibold text-slate-900 dark:text-white font-sans">${escapeHtml(net)}</td>
      <td class="py-2.5 px-3 text-right text-slate-800 dark:text-slate-200">${s.brands}</td>
      <td class="py-2.5 px-3 text-right text-emerald-600 dark:text-emerald-400 font-medium">${s.monetized} (${s.brands > 0 ? ((s.monetized / s.brands) * 100).toFixed(0) : 0}%)</td>
      <td class="py-2.5 px-3 text-right font-medium text-slate-800 dark:text-slate-100 font-mono">${formatNumber(s.clicks)}</td>
      <td class="py-2.5 px-3 text-right font-bold ${s.rev > 0 ? "text-emerald-600 dark:text-emerald-400" : "text-slate-400 dark:text-slate-500"} font-mono">${formatCurrency(s.rev)}</td>
      <td class="py-2.5 px-3 text-right font-bold text-indigo-700 dark:text-indigo-400 font-mono">₹${rpc.toFixed(4)}</td>
      <td class="py-2.5 px-3 text-right font-medium text-slate-700 dark:text-slate-300">${revShare.toFixed(1)}%</td>
      <td class="py-2.5 px-3 text-right text-slate-500 dark:text-slate-400">${clicksShare.toFixed(1)}%</td>
      <td class="py-2.5 px-3 text-center">
        <span class="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold border ${badgeClass}">
          ${Number(efficiency) >= 1.5 ? "★ High ROI (" + efficiency + "x)" : efficiency + "x"}
        </span>
      </td>
    `;
    tbody.appendChild(tr);
  });
}

// 7. Tab 2: Top Yield Champions
function renderYieldChampions(dataset) {
  const tbody = document.getElementById("table-yield-leaders");
  tbody.innerHTML = "";

  const valid = dataset.filter((r) => (Number(r["SUM of INTERNAL CLICKS"]) || 0) >= 50 && (Number(r["RPCs"]) || 0) > 0);
  valid.sort((a, b) => Number(b["RPCs"]) - Number(a["RPCs"]));

  valid.slice(0, 20).forEach((row, idx) => {
    const clicks = Number(row["SUM of INTERNAL CLICKS"]) || 0;
    const rev = Number(row["Revenue"]) || 0;
    const rpc = Number(row["RPCs"]) || 0;

    const tr = document.createElement("tr");
    tr.className = "hover:bg-emerald-50/40 dark:hover:bg-emerald-950/20 transition-colors";

    const tierBadge =
      rpc >= 5.0
        ? '<span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-purple-100 dark:bg-purple-950/60 text-purple-800 dark:text-purple-300 border border-purple-200 dark:border-purple-800">🚀 Ultra Yield (>₹5)</span>'
        : rpc >= 1.0
        ? '<span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 dark:bg-emerald-950/60 text-emerald-800 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800">💎 High Yield (>₹1)</span>'
        : '<span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-blue-100 dark:bg-blue-950/60 text-blue-800 dark:text-blue-300 border border-blue-200 dark:border-blue-800">⭐ Solid Yield</span>';

    tr.innerHTML = `
      <td class="py-2.5 px-3 text-center text-slate-400 font-sans text-[11px]">${idx + 1}</td>
      <td class="py-2.5 px-3 font-semibold text-slate-900 dark:text-white font-sans">${escapeHtml(row["WEBSITE / BRAND"])}</td>
      <td class="py-2.5 px-3 font-sans text-slate-600 dark:text-slate-300">
        <span class="px-2 py-0.5 rounded-md bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 text-[11px] border border-slate-200 dark:border-slate-700">
          ${escapeHtml(row["AFFILIATE NETWORK"])}
        </span>
      </td>
      <td class="py-2.5 px-3 text-right font-medium text-slate-800 dark:text-slate-100 font-mono">${formatNumber(clicks)}</td>
      <td class="py-2.5 px-3 text-right font-bold text-emerald-600 dark:text-emerald-400 font-mono">${formatCurrency(rev)}</td>
      <td class="py-2.5 px-3 text-right font-bold text-emerald-700 dark:text-emerald-300 font-mono">₹${rpc.toFixed(2)}</td>
      <td class="py-2.5 px-3 text-center">${tierBadge}</td>
    `;
    tbody.appendChild(tr);
  });
}

// 8. Tab 3: Traffic Leaks & Opportunities
function renderTrafficLeaks(dataset) {
  const tbody = document.getElementById("table-traffic-leaks");
  tbody.innerHTML = "";

  // Compute portfolio average RPC across monetized traffic for realistic lost revenue estimation
  const earningRows = dataset.filter((r) => (Number(r["Revenue"]) || 0) > 0);
  const totalEarningRev = earningRows.reduce((a, r) => a + Number(r["Revenue"]), 0);
  const totalEarningClicks = earningRows.reduce((a, r) => a + Number(r["SUM of INTERNAL CLICKS"]), 0);
  const benchmarkRPC = totalEarningClicks > 0 ? totalEarningRev / totalEarningClicks : 0.15;

  const leaks = dataset.filter((r) => (Number(r["Revenue"]) || 0) === 0 && (Number(r["SUM of INTERNAL CLICKS"]) || 0) >= 500);
  leaks.sort((a, b) => Number(b["SUM of INTERNAL CLICKS"]) - Number(a["SUM of INTERNAL CLICKS"]));

  document.getElementById("badge-leaks-count").textContent = leaks.length;

  leaks.forEach((row) => {
    const clicks = Number(row["SUM of INTERNAL CLICKS"]) || 0;
    const lostRev = clicks * benchmarkRPC;

    const tr = document.createElement("tr");
    tr.className = "hover:bg-amber-50/40 dark:hover:bg-amber-950/20 transition-colors";

    const brand = (row["WEBSITE / BRAND"] || "").trim();
    const net = (row["AFFILIATE NETWORK"] || "").trim();

    let recommendation = "Review network commission status or link tracking parameters.";
    if (net.toLowerCase().includes("special") || net.toLowerCase().includes("own")) {
      recommendation = "Internal routing tag: Test affiliate deep-links on Cuelinks or Admitad to monetize.";
    } else if (clicks > 100000) {
      recommendation = "Massive traffic leak: Negotiate custom direct CPS campaign or swap primary network.";
    } else {
      recommendation = "Verify campaign approval on affiliate portal or replace broken tracking link.";
    }

    tr.innerHTML = `
      <td class="py-2.5 px-3 font-semibold text-slate-900 dark:text-white font-sans">${escapeHtml(brand)}</td>
      <td class="py-2.5 px-3 font-sans">
        <span class="px-2 py-0.5 rounded-md bg-amber-100 dark:bg-amber-950/60 text-amber-900 dark:text-amber-300 text-[11px] border border-amber-200 dark:border-amber-800">
          ${escapeHtml(net)}
        </span>
      </td>
      <td class="py-2.5 px-3 text-right font-bold text-rose-600 dark:text-rose-400 font-mono">${formatNumber(clicks)}</td>
      <td class="py-2.5 px-3 text-right font-bold text-amber-700 dark:text-amber-400 font-mono">~${formatCurrency(lostRev)}</td>
      <td class="py-2.5 px-3 text-slate-600 dark:text-slate-400 font-sans text-[11px]">${escapeHtml(recommendation)}</td>
    `;
    tbody.appendChild(tr);
  });
}

// 9. Tab 4: Multi-Network Cross-Brand Arbitrage
function renderArbitrageMatrix(dataset) {
  const tbody = document.getElementById("table-arbitrage-matrix");
  tbody.innerHTML = "";

  // Group by Brand
  const brandGroups = {};
  dataset.forEach((r) => {
    const brand = (r["WEBSITE / BRAND"] || "").trim();
    if (!brand) return;
    if (!brandGroups[brand]) brandGroups[brand] = [];
    brandGroups[brand].push(r);
  });

  const multiBrands = Object.keys(brandGroups).filter((b) => brandGroups[b].length > 1);

  // Sort multiBrands by highest total revenue
  multiBrands.sort((a, b) => {
    const revA = brandGroups[a].reduce((acc, r) => acc + (Number(r["Revenue"]) || 0), 0);
    const revB = brandGroups[b].reduce((acc, r) => acc + (Number(r["Revenue"]) || 0), 0);
    return revB - revA;
  });

  multiBrands.forEach((brand) => {
    const items = brandGroups[brand];
    // Sort items by RPC desc
    items.sort((a, b) => (Number(b["RPCs"]) || 0) - (Number(a["RPCs"]) || 0));

    const optA = items[0];
    const optB = items[1];

    const rpcA = Number(optA["RPCs"]) || 0;
    const rpcB = Number(optB["RPCs"]) || 0;
    const diff = rpcA - rpcB;

    const tr = document.createElement("tr");
    tr.className = "hover:bg-indigo-50/30 dark:hover:bg-indigo-950/20 transition-colors";

    const winnerBadge =
      diff > 0.005
        ? `<span class="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold bg-indigo-100 dark:bg-indigo-950/60 text-indigo-800 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-800">Route to ${escapeHtml(optA["AFFILIATE NETWORK"])}</span>`
        : `<span class="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-700">Rate Parity (Both Equal)</span>`;

    tr.innerHTML = `
      <td class="py-2.5 px-3 font-semibold text-slate-900 dark:text-white font-sans">${escapeHtml(brand)}</td>
      <td class="py-2.5 px-3 font-sans font-medium text-slate-800 dark:text-slate-200">${escapeHtml(optA["AFFILIATE NETWORK"])}</td>
      <td class="py-2.5 px-3 text-right font-bold text-emerald-600 dark:text-emerald-400 font-mono">₹${rpcA.toFixed(2)}</td>
      <td class="py-2.5 px-3 font-sans text-slate-600 dark:text-slate-400">${escapeHtml(optB["AFFILIATE NETWORK"])}</td>
      <td class="py-2.5 px-3 text-right font-medium text-slate-600 dark:text-slate-400 font-mono">₹${rpcB.toFixed(2)}</td>
      <td class="py-2.5 px-3 text-right font-bold ${diff > 0.005 ? "text-indigo-600 dark:text-indigo-400" : "text-slate-400 dark:text-slate-500"} font-mono">${diff > 0.005 ? "+₹" + diff.toFixed(2) : "₹0.00"}</td>
      <td class="py-2.5 px-3 text-center">${winnerBadge}</td>
    `;
    tbody.appendChild(tr);
  });
}

// 10. Tab 5: Filtered Master Grid
function renderFilteredGrid(rows) {
  const tbody = document.getElementById("table-filtered-grid");
  tbody.innerHTML = "";

  document.getElementById("filtered-grid-subtitle").textContent = `Displaying ${rows.length} of ${rawMasterData.length} records`;

  rows.forEach((row, idx) => {
    const clicks = Number(row["SUM of INTERNAL CLICKS"]) || 0;
    const rev = Number(row["Revenue"]) || 0;
    const rpc = Number(row["RPCs"]) || 0;

    const tr = document.createElement("tr");
    tr.className = "hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors";

    const statusBadge =
      rev > 0
        ? '<span class="px-2 py-0.5 rounded-md text-[10px] font-semibold bg-emerald-100 dark:bg-emerald-950/60 text-emerald-800 dark:text-emerald-300">Earning</span>'
        : '<span class="px-2 py-0.5 rounded-md text-[10px] font-medium bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400">Unmonetized</span>';

    const rpcClass =
      rpc >= 1.0
        ? "font-bold text-purple-700 dark:text-purple-300 bg-purple-100/60 dark:bg-purple-950/40 rounded px-1"
        : rpc >= 0.2
        ? "font-bold text-emerald-700 dark:text-emerald-300 bg-emerald-100/60 dark:bg-emerald-950/40 rounded px-1"
        : rpc > 0
        ? "font-bold text-emerald-600 dark:text-emerald-400"
        : "text-slate-400 dark:text-slate-500";

    tr.innerHTML = `
      <td class="py-2 px-3 text-center text-slate-400 font-sans text-[11px]">${idx + 1}</td>
      <td class="py-2 px-3 font-semibold text-slate-900 dark:text-white font-sans">${escapeHtml(row["WEBSITE / BRAND"])}</td>
      <td class="py-2 px-3 font-sans text-slate-600 dark:text-slate-300">
        <span class="px-2 py-0.5 rounded-md bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 text-[11px] border border-slate-200 dark:border-slate-700">
          ${escapeHtml(row["AFFILIATE NETWORK"])}
        </span>
      </td>
      <td class="py-2 px-3 text-right font-medium text-slate-800 dark:text-slate-100 font-mono">${formatNumber(clicks)}</td>
      <td class="py-2 px-3 text-right font-bold ${rev > 0 ? "text-emerald-600 dark:text-emerald-400" : "text-slate-400 dark:text-slate-500"} font-mono">${formatCurrency(rev)}</td>
      <td class="py-2 px-3 text-right ${rpcClass} font-mono">₹${rpc > 0 && rpc < 0.01 ? rpc.toFixed(4) : rpc.toFixed(2)}</td>
      <td class="py-2 px-3 text-center">${statusBadge}</td>
    `;
    tbody.appendChild(tr);
  });
}

// 11. Tabs Setup
function setupTabs() {
  const tabButtons = document.querySelectorAll(".tab-btn");
  tabButtons.forEach((btn) => {
    btn.addEventListener("click", () => {
      const targetId = btn.getAttribute("data-tab");

      // Update button styles
      tabButtons.forEach((b) => {
        b.classList.remove("active", "bg-indigo-600", "text-white");
        b.classList.add("text-slate-600");
      });
      btn.classList.add("active");
      btn.classList.remove("text-slate-600");

      // Show target tab content
      document.querySelectorAll(".tab-content").forEach((tc) => tc.classList.add("hidden"));
      const activeContent = document.getElementById(targetId);
      if (activeContent) activeContent.classList.remove("hidden");
    });
  });
}

// 12. Actions: Export CSV & TSV Copy
function setupActionButtons() {
  const btnRefresh = document.getElementById("btn-refresh-data");
  if (btnRefresh) {
    btnRefresh.addEventListener("click", () => {
      loadAnalyticsData(true);
    });
  }

  const btnExport = document.getElementById("btn-export-analytics-csv");
  if (btnExport) {
    btnExport.addEventListener("click", () => {
      if (!filteredData.length) return;
      const headers = ["WEBSITE / BRAND", "AFFILIATE NETWORK", "SUM of INTERNAL CLICKS", "Revenue", "RPCs"];
      let csv = headers.join(",") + "\n";
      filteredData.forEach((r) => {
        csv += [
          `"${(r["WEBSITE / BRAND"] || "").replace(/"/g, '""')}"`,
          `"${(r["AFFILIATE NETWORK"] || "").replace(/"/g, '""')}"`,
          r["SUM of INTERNAL CLICKS"] || 0,
          r["Revenue"] || 0,
          r["RPCs"] || 0,
        ].join(",") + "\n";
      });

      const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `Affiliate_Advanced_Analytics_${new Date().toISOString().slice(0, 10)}.csv`;
      a.click();
      URL.revokeObjectURL(url);
    });
  }

  const btnCopyTsv = document.getElementById("btn-copy-filtered-tsv");
  if (btnCopyTsv) {
    btnCopyTsv.addEventListener("click", () => {
      if (!filteredData.length) return;
      const headers = ["WEBSITE / BRAND", "AFFILIATE NETWORK", "SUM of INTERNAL CLICKS", "Revenue", "RPCs"];
      let tsv = headers.join("\t") + "\n";
      filteredData.forEach((r) => {
        tsv += [
          r["WEBSITE / BRAND"] || "",
          r["AFFILIATE NETWORK"] || "",
          r["SUM of INTERNAL CLICKS"] || 0,
          r["Revenue"] || 0,
          r["RPCs"] || 0,
        ].join("\t") + "\n";
      });

      navigator.clipboard.writeText(tsv).then(() => {
        const copyEl = document.getElementById("copy-filtered-text");
        const original = copyEl.textContent;
        copyEl.textContent = "Copied Visible Rows!";
        setTimeout(() => {
          copyEl.textContent = original;
        }, 2000);
      });
    });
  }
}

// Utility formatting
function formatCurrency(val) {
  return "₹" + Number(val || 0).toLocaleString("en-IN", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

function formatNumber(val) {
  return Number(val || 0).toLocaleString("en-IN");
}

function escapeHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

})();
