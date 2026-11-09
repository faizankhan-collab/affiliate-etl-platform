// Frontend Controller for Affiliate ETL & RPC Automator

let internalClicksFile = null;
let stagedNetworkFiles = []; // Array of { file, network }
let currentMasterData = [];
let currentSummary = null;

const SUPPORTED_NETWORKS = [
  { id: "auto", label: "⚡ Auto-Detect" },
  { id: "cuelinks", label: "Cuelinks" },
  { id: "admitad", label: "Admitad" },
  { id: "cashkaro", label: "Cashkaro" },
  { id: "zonet", label: "Zonet" },
  { id: "icubeswire", label: "Icubeswire" },
  { id: "adgama", label: "Adgama" },
  { id: "affinity", label: "Affinity" },
  { id: "pantech", label: "Pantech" },
  { id: "digimodo", label: "Digimodo" },
  { id: "generic", label: "Generic / Other" },
];

document.addEventListener("DOMContentLoaded", () => {
  setupThemeToggle();
  setupInternalClicksDropzone();
  setupNetworkFilesDropzone();
  setupActionButtons();
  setupSearchAndFilters();
  setupAliasesModal();
  setupRoutingAndHistory();
  restoreAppState();
});

// Theme Toggle Handling (Default: Dark Mode)
function setupThemeToggle() {
  const isDark = () => document.documentElement.classList.contains("dark");

  function updateThemeUI() {
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

  function toggleTheme() {
    if (isDark()) {
      document.documentElement.classList.remove("dark");
      localStorage.setItem("theme", "light");
    } else {
      document.documentElement.classList.add("dark");
      localStorage.setItem("theme", "dark");
    }
    updateThemeUI();
  }

  const btnTheme = document.getElementById("btn-theme-toggle");
  const btnThemeAnalytics = document.getElementById("btn-theme-toggle-analytics");
  if (btnTheme) btnTheme.addEventListener("click", toggleTheme);
  if (btnThemeAnalytics) btnThemeAnalytics.addEventListener("click", toggleTheme);

  updateThemeUI();
}

// 1. Internal Clicks Upload Handling
function setupInternalClicksDropzone() {
  const dropzone = document.getElementById("dropzone-clicks");
  const input = document.getElementById("input-clicks");
  const preview = document.getElementById("clicks-preview");
  const prompt = document.getElementById("clicks-prompt");
  const btnRemove = document.getElementById("btn-remove-clicks");

  dropzone.addEventListener("click", (e) => {
    if (e.target.closest("#btn-remove-clicks")) return;
    input.click();
  });

  input.addEventListener("change", (e) => {
    if (e.target.files.length > 0) {
      handleClicksFile(e.target.files[0]);
    }
  });

  dropzone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropzone.classList.add("border-blue-500", "bg-blue-50/30");
  });

  dropzone.addEventListener("dragleave", () => {
    dropzone.classList.remove("border-blue-500", "bg-blue-50/30");
  });

  dropzone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropzone.classList.remove("border-blue-500", "bg-blue-50/30");
    if (e.dataTransfer.files.length > 0) {
      handleClicksFile(e.dataTransfer.files[0]);
    }
  });

  btnRemove.addEventListener("click", () => {
    internalClicksFile = null;
    input.value = "";
    preview.classList.add("hidden");
    prompt.classList.remove("hidden");
    sessionStorage.removeItem("affiliate_clicks_info");
  });

  function handleClicksFile(file) {
    internalClicksFile = file;
    document.getElementById("clicks-filename").textContent = file.name;
    document.getElementById("clicks-filesize").textContent = formatBytes(file.size);
    prompt.classList.add("hidden");
    preview.classList.remove("hidden");
    try {
      sessionStorage.setItem("affiliate_clicks_info", JSON.stringify({ name: file.name, size: file.size }));
    } catch (e) {}
  }
}

// 2. Network Files Upload Handling
function setupNetworkFilesDropzone() {
  const dropzone = document.getElementById("dropzone-networks");
  const input = document.getElementById("input-networks");
  const btnClear = document.getElementById("btn-clear-networks");

  dropzone.addEventListener("click", () => input.click());

  input.addEventListener("change", (e) => {
    if (e.target.files.length > 0) {
      addNetworkFiles(Array.from(e.target.files));
    }
  });

  dropzone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropzone.classList.add("border-emerald-500", "bg-emerald-50/30");
  });

  dropzone.addEventListener("dragleave", () => {
    dropzone.classList.remove("border-emerald-500", "bg-emerald-50/30");
  });

  dropzone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropzone.classList.remove("border-emerald-500", "bg-emerald-50/30");
    if (e.dataTransfer.files.length > 0) {
      addNetworkFiles(Array.from(e.dataTransfer.files));
    }
  });

  btnClear.addEventListener("click", () => {
    stagedNetworkFiles = [];
    input.value = "";
    renderStagedFiles();
  });
}

function addNetworkFiles(files) {
  files.forEach((file) => {
    // Auto detect network hint from filename
    let detected = "auto";
    const fn = file.name.toLowerCase();
    if (
      fn.includes("cuelinks") ||
      fn.startsWith("campaigns_report") ||
      fn.startsWith("transactions_report")
    ) {
      detected = "cuelinks";
    } else if (fn.includes("cashkaro") || fn.includes("performance")) {
      detected = "cashkaro";
    } else if (fn.includes("admitad")) {
      detected = "admitad";
    } else if (fn.includes("zonet")) {
      detected = "zonet";
    } else if (fn.includes("icubes")) {
      detected = "icubeswire";
    } else {
      for (const net of SUPPORTED_NETWORKS) {
        if (net.id !== "auto" && net.id !== "generic" && fn.includes(net.id)) {
          detected = net.id;
          break;
        }
      }
    }
    stagedNetworkFiles.push({ file, network: detected });
  });
  renderStagedFiles();
}

function renderStagedFiles() {
  const listContainer = document.getElementById("staged-networks-list");
  const btnClear = document.getElementById("btn-clear-networks");
  if (!listContainer) return;
  listContainer.innerHTML = "";
  if (stagedNetworkFiles.length === 0) {
    if (btnClear) btnClear.classList.add("hidden");
    return;
  }
  if (btnClear) btnClear.classList.remove("hidden");

  stagedNetworkFiles.forEach((item, index) => {
    const row = document.createElement("div");
    row.className =
      "flex items-center justify-between p-2.5 bg-slate-50 border border-slate-200 rounded-xl text-xs";

    const left = document.createElement("div");
    left.className = "flex items-center space-x-2 truncate pr-2";
    left.innerHTML = `
      <i class="ph ph-file-spreadsheet text-emerald-600 text-lg"></i>
      <div class="truncate">
        <p class="font-medium text-slate-800 truncate">${escapeHtml(item.file.name)}</p>
        <p class="text-[10px] text-slate-400">${formatBytes(item.file.size)}</p>
      </div>
    `;

    const right = document.createElement("div");
    right.className = "flex items-center space-x-2 shrink-0";

    // Select for network override
    const select = document.createElement("select");
    select.className =
      "text-[11px] bg-white border border-slate-200 rounded-lg px-2 py-1 text-slate-700 font-medium focus:ring-1 focus:ring-emerald-500";
    SUPPORTED_NETWORKS.forEach((net) => {
      const opt = document.createElement("option");
      opt.value = net.id;
      opt.textContent = net.label;
      if (net.id === item.network) opt.selected = true;
      select.appendChild(opt);
    });
    select.addEventListener("change", (e) => {
      item.network = e.target.value;
    });

    // Remove button
    const removeBtn = document.createElement("button");
    removeBtn.className = "text-slate-400 hover:text-red-500 p-1";
    removeBtn.innerHTML = `<i class="ph ph-trash"></i>`;
    removeBtn.addEventListener("click", () => {
      stagedNetworkFiles.splice(index, 1);
      renderStagedFiles();
    });

    right.appendChild(select);
    right.appendChild(removeBtn);
    row.appendChild(left);
    row.appendChild(right);
    listContainer.appendChild(row);
  });
}

function getMonthDateRange(yearMonthStr) {
  if (!yearMonthStr || !yearMonthStr.includes("-")) {
    return { start_date: "2026-10-01", end_date: "2026-10-31", label: "October 2026" };
  }
  const parts = yearMonthStr.split("-");
  const year = parseInt(parts[0], 10);
  const month = parseInt(parts[1], 10);
  const lastDay = new Date(year, month, 0).getDate();
  const start_date = `${parts[0]}-${String(month).padStart(2, "0")}-01`;
  const end_date = `${parts[0]}-${String(month).padStart(2, "0")}-${String(lastDay).padStart(2, "0")}`;
  const dateObj = new Date(year, month - 1, 1);
  const label = dateObj.toLocaleString("en-US", { month: "long", year: "numeric" });
  return { start_date, end_date, label };
}

// 3. Pipeline Execution & Buttons
function setupActionButtons() {
  const btnRun = document.getElementById("btn-run-etl");
  const btnLoadDemo = document.getElementById("btn-load-demo");
  const btnCopyTsv = document.getElementById("btn-copy-tsv");
  const btnExportExcel = document.getElementById("btn-export-excel");
  const btnExportCsv = document.getElementById("btn-export-csv");
  const btnBotDropdown = document.getElementById("btn-bot-dropdown");
  const botDropdownMenu = document.getElementById("bot-dropdown-menu");
  const botCaret = document.getElementById("bot-caret");
  const optBotCuelinks = document.getElementById("opt-bot-cuelinks");
  const optBotAdmitad = document.getElementById("opt-bot-admitad");
  const optBotCashkaro = document.getElementById("opt-bot-cashkaro");
  const optBotZonet = document.getElementById("opt-bot-zonet");
  const optBotIcubeswire = document.getElementById("opt-bot-icubeswire");
  const optBotInrdeals = document.getElementById("opt-bot-inrdeals");
  const optBotCj = document.getElementById("opt-bot-cj");
  const optBotPantech = document.getElementById("opt-bot-pantech");
  const optBotFast6 = document.getElementById("opt-bot-fast-6");
  const optBotAll = document.getElementById("opt-bot-all");
  const dateRangePreset = document.getElementById("date-range-preset");
  const customDateInputs = document.getElementById("custom-date-inputs");
  const inputDateStart = document.getElementById("input-date-start");
  const inputDateEnd = document.getElementById("input-date-end");
  const activeRangePill = document.getElementById("active-range-pill");

  function getSelectedDateRange() {
    const preset = dateRangePreset ? dateRangePreset.value : "2026-10";
    let start_date = "2026-10-01";
    let end_date = "2026-10-31";
    let label = "October 2026";

    if (preset === "custom") {
      start_date = inputDateStart && inputDateStart.value ? inputDateStart.value : "2026-10-01";
      end_date = inputDateEnd && inputDateEnd.value ? inputDateEnd.value : "2026-10-31";
      label = `Custom (${start_date} to ${end_date})`;
    } else if (preset && preset.includes("-")) {
      const parts = preset.split("-");
      const year = parseInt(parts[0], 10);
      const month = parseInt(parts[1], 10);
      const lastDay = new Date(year, month, 0).getDate();
      start_date = `${parts[0]}-${String(month).padStart(2, "0")}-01`;
      end_date = `${parts[0]}-${String(month).padStart(2, "0")}-${String(lastDay).padStart(2, "0")}`;

      const monthNames = [
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December"
      ];
      label = `${monthNames[month - 1]} ${year}`;
    }

    const d1 = new Date(start_date);
    const d2 = new Date(end_date);
    const diffTime = Math.max(0, d2 - d1);
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24)) + 1;

    return { start_date, end_date, label, days: diffDays };
  }

  function updateDateRangeUI() {
    const range = getSelectedDateRange();
    if (activeRangePill) {
      if (dateRangePreset && dateRangePreset.value === "custom") {
        activeRangePill.textContent = `${range.days} Days Active (${range.start_date} to ${range.end_date})`;
      } else {
        activeRangePill.textContent = `${range.days} Days Active`;
      }
      activeRangePill.title = `Active Window: ${range.start_date} to ${range.end_date} (Synchronized for Clicks & Revenue)`;
    }
    const badgeDates = document.getElementById("badge-table-dates");
    if (badgeDates) {
      badgeDates.textContent = `📅 ${range.start_date} to ${range.end_date} (${range.days}d)`;
    }
    if (inputDateStart && range.start_date && dateRangePreset && dateRangePreset.value !== "custom") {
      inputDateStart.value = range.start_date;
    }
    if (inputDateEnd && range.end_date && dateRangePreset && dateRangePreset.value !== "custom") {
      inputDateEnd.value = range.end_date;
    }
  }

  if (dateRangePreset) {
    dateRangePreset.addEventListener("change", (e) => {
      if (e.target.value === "custom") {
        if (customDateInputs) customDateInputs.classList.remove("hidden");
      } else {
        if (customDateInputs) customDateInputs.classList.add("hidden");
      }
      updateDateRangeUI();
    });
  }

  if (inputDateStart) inputDateStart.addEventListener("change", updateDateRangeUI);
  if (inputDateEnd) inputDateEnd.addEventListener("change", updateDateRangeUI);

  // Initialize UI state
  updateDateRangeUI();

  // Toggle dropdown menu
  if (btnBotDropdown && botDropdownMenu) {
    btnBotDropdown.addEventListener("click", (e) => {
      e.stopPropagation();
      const isHidden = botDropdownMenu.classList.contains("hidden");
      if (isHidden) {
        botDropdownMenu.classList.remove("hidden");
        if (botCaret) botCaret.classList.add("rotate-180");
      } else {
        botDropdownMenu.classList.add("hidden");
        if (botCaret) botCaret.classList.remove("rotate-180");
      }
    });

    document.addEventListener("click", (e) => {
      if (!botDropdownMenu.contains(e.target) && !btnBotDropdown.contains(e.target)) {
        botDropdownMenu.classList.add("hidden");
        if (botCaret) botCaret.classList.remove("rotate-180");
      }
    });
  }

  async function syncSingleBot(networkKey) {
    if (botDropdownMenu) {
      botDropdownMenu.classList.add("hidden");
      if (botCaret) botCaret.classList.remove("rotate-180");
    }

    const { start_date, end_date, label, days } = getSelectedDateRange();
    const networkDisplay = {
      cuelinks: "Cuelinks",
      admitad: "Admitad",
      cashkaro: "Cashkaro",
      zonet: "Zonet",
      icubeswire: "iCubesWire",
      inrdeals: "INRDeals",
      cj: "CJ (Commission Junction)",
      pantech: "Pantech",
    }[networkKey] || networkKey;

    console.log(`[${networkDisplay} Bot] Syncing ${label} (${start_date} to ${end_date}, ${days} days)`);
    setLoading(true, `🤖 Bot connecting to ${networkDisplay} & fetching ${label} report (${start_date} to ${end_date})...`);

    try {
      const endpoint = `/api/bot/sync-${networkKey}`;
      let sampleFileUrl = `/api/sample-files/${networkKey}_bot_live.`;
      let mimeType = "text/csv";
      let ext = "csv";

      if (networkKey === "cuelinks") {
        sampleFileUrl += "xls";
        mimeType = "application/vnd.ms-excel";
        ext = "xls";
      } else if (networkKey === "admitad") {
        sampleFileUrl += "xlsx";
        mimeType = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet";
        ext = "xlsx";
      } else {
        sampleFileUrl += "csv";
        mimeType = "text/csv";
        ext = "csv";
      }

      const res = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ start_date, end_date }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || `${networkDisplay} bot sync failed`);

      const fileFetchUrl = data.filename ? `/api/sample-files/${encodeURIComponent(data.filename)}` : sampleFileUrl;
      const fileRes = await fetch(fileFetchUrl);
      if (!fileRes.ok) {
        throw new Error(`Failed to download report file from ${fileFetchUrl} (HTTP ${fileRes.status})`);
      }
      const fileBlob = await fileRes.blob();
      const displayFilename = data.filename || `${networkKey}_campaigns_${start_date}_to_${end_date}.${ext}`;
      const liveFile = new File([fileBlob], displayFilename, { type: mimeType });

      // Replace existing file for this network
      const existingIdx = stagedNetworkFiles.findIndex(
        (item) => item.network === networkKey || item.file.name.toLowerCase().includes(networkKey)
      );
      if (existingIdx >= 0) {
        stagedNetworkFiles.splice(existingIdx, 1);
      }

      stagedNetworkFiles.push({ file: liveFile, network: networkKey });
      renderStagedFiles();
      alert(`🎉 ${data.message}`);
    } catch (err) {
      alert(`Bot sync error (${networkDisplay}): ` + err.message);
    } finally {
      setLoading(false);
    }
  }

  async function fetchNetworkFile(networkKey, start_date, end_date) {
    const endpointMap = {
      cuelinks: { url: "/api/bot/sync-cuelinks", defaultExt: "xls", mime: "application/vnd.ms-excel", defaultFile: "cuelinks_bot_live.xls", label: "Cuelinks" },
      admitad: { url: "/api/bot/sync-admitad", defaultExt: "xlsx", mime: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", defaultFile: "admitad_bot_live.xlsx", label: "Admitad" },
      cashkaro: { url: "/api/bot/sync-cashkaro", defaultExt: "csv", mime: "text/csv", defaultFile: "cashkaro_bot_live.csv", label: "Cashkaro" },
      zonet: { url: "/api/bot/sync-zonet", defaultExt: "csv", mime: "text/csv", defaultFile: "zonet_bot_live.csv", label: "Zonet" },
      icubeswire: { url: "/api/bot/sync-icubeswire", defaultExt: "csv", mime: "text/csv", defaultFile: "icubeswire_bot_live.csv", label: "iCubesWire" },
      pantech: { url: "/api/bot/sync-pantech", defaultExt: "csv", mime: "text/csv", defaultFile: "pantech_bot_live.csv", label: "Pantech" },
      cj: { url: "/api/bot/sync-cj", defaultExt: "csv", mime: "text/csv", defaultFile: "cj_bot_live.csv", label: "CJ (Commission Junction)" },
    };

    const cfg = endpointMap[networkKey];
    if (!cfg) throw new Error("Unknown network: " + networkKey);

    const res = await fetch(cfg.url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ start_date, end_date }),
    });
    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || "Sync failed");
    }

    const fileFetchUrl = data.filename
      ? `/api/sample-files/${encodeURIComponent(data.filename)}`
      : `/api/sample-files/${cfg.defaultFile}`;
    const fileRes = await fetch(fileFetchUrl);
    if (!fileRes.ok) throw new Error("File download HTTP " + fileRes.status);
    const blob = await fileRes.blob();
    const finalName = data.filename || `${networkKey}_campaigns_${start_date}_to_${end_date}.${cfg.defaultExt}`;
    const liveFile = new File([blob], finalName, { type: cfg.mime });

    const exIdx = stagedNetworkFiles.findIndex(
      (item) => item.network === networkKey || item.file.name.toLowerCase().includes(networkKey)
    );
    if (exIdx >= 0) stagedNetworkFiles.splice(exIdx, 1);
    stagedNetworkFiles.push({ file: liveFile, network: networkKey });

    return {
      network: networkKey,
      label: cfg.label,
      count: data.rows_count || 0,
      message: data.message || `Fetched ${cfg.label}`,
    };
  }

  async function syncFast6Bots() {
    if (botDropdownMenu) {
      botDropdownMenu.classList.add("hidden");
      if (botCaret) botCaret.classList.remove("rotate-180");
    }

    const { start_date, end_date, label, days } = getSelectedDateRange();
    setLoading(true, `🚀 Fast Syncing 6 Networks (excluding CJ) in parallel for ${label} (${days} days)...`);

    const fastNetworks = ["cuelinks", "admitad", "cashkaro", "zonet", "icubeswire", "pantech"];
    try {
      const results = await Promise.allSettled(
        fastNetworks.map((net) => fetchNetworkFile(net, start_date, end_date))
      );

      const summaryResults = [];
      results.forEach((res, idx) => {
        const net = fastNetworks[idx];
        const netName = net.charAt(0).toUpperCase() + net.slice(1);
        if (res.status === "fulfilled") {
          summaryResults.push(`✅ ${res.value.label}: ${res.value.count} campaigns/clients`);
        } else {
          summaryResults.push(`❌ ${netName}: ${res.reason?.message || res.reason}`);
        }
      });

      renderStagedFiles();
      alert(`🚀 Fast Sync Finished (6 Networks, ${label}):\n\n` + summaryResults.join("\n"));
    } finally {
      setLoading(false);
    }
  }

  async function syncAllBots() {
    if (botDropdownMenu) {
      botDropdownMenu.classList.add("hidden");
      if (botCaret) botCaret.classList.remove("rotate-180");
    }

    const { start_date, end_date, label, days } = getSelectedDateRange();
    setLoading(true, `🤖 Syncing all 7 active networks in parallel for ${label} (Streaming CJ GraphQL ~15-30s)...`);

    const allNetworks = ["cuelinks", "admitad", "cashkaro", "zonet", "icubeswire", "pantech", "cj"];
    try {
      const results = await Promise.allSettled(
        allNetworks.map((net) => fetchNetworkFile(net, start_date, end_date))
      );

      const summaryResults = [];
      results.forEach((res, idx) => {
        const net = allNetworks[idx];
        const netName = net === "cj" ? "CJ (Commission Junction)" : (net.charAt(0).toUpperCase() + net.slice(1));
        if (res.status === "fulfilled") {
          summaryResults.push(`✅ ${res.value.label}: ${res.value.count} items`);
        } else {
          summaryResults.push(`❌ ${netName}: ${res.reason?.message || res.reason}`);
        }
      });

      renderStagedFiles();
      alert(`⚡ Full Multi-Bot Sync Finished (7 Networks, ${label}):\n\n` + summaryResults.join("\n"));
    } finally {
      setLoading(false);
    }
  }

  if (optBotCuelinks) {
    optBotCuelinks.addEventListener("click", () => syncSingleBot("cuelinks"));
  }
  if (optBotAdmitad) {
    optBotAdmitad.addEventListener("click", () => syncSingleBot("admitad"));
  }
  if (optBotCashkaro) {
    optBotCashkaro.addEventListener("click", () => syncSingleBot("cashkaro"));
  }
  if (optBotZonet) {
    optBotZonet.addEventListener("click", () => syncSingleBot("zonet"));
  }
  if (optBotIcubeswire) {
    optBotIcubeswire.addEventListener("click", () => syncSingleBot("icubeswire"));
  }
  if (optBotInrdeals) {
    optBotInrdeals.addEventListener("click", () => {
      alert("INRDeals API token is pending support approval (within 24h). Please drag & drop your INRDeals CSV/XLS export into Step 2 for now.");
    });
  }
  if (optBotCj) {
    optBotCj.addEventListener("click", () => syncSingleBot("cj"));
  }
  if (optBotPantech) {
    optBotPantech.addEventListener("click", () => syncSingleBot("pantech"));
  }
  if (optBotFast6) {
    optBotFast6.addEventListener("click", syncFast6Bots);
  }
  if (optBotAll) {
    optBotAll.addEventListener("click", syncAllBots);
  }

  btnRun.addEventListener("click", async () => {
    if (!internalClicksFile) {
      alert("Please upload the Buyhatke Internal Clicks base file first.");
      return;
    }
    if (stagedNetworkFiles.length === 0) {
      alert("Please upload at least one affiliate network export file.");
      return;
    }

    const formData = new FormData();
    formData.append("internal_clicks_file", internalClicksFile);

    const netMapping = {};
    stagedNetworkFiles.forEach((item) => {
      formData.append("network_files", item.file);
      netMapping[item.file.name] = item.network;
    });
    formData.append("network_mapping", JSON.stringify(netMapping));

    const usdRateInput = document.getElementById("input-usd-rate");
    if (usdRateInput && usdRateInput.value) {
      formData.append("usd_to_inr_rate", usdRateInput.value);
    }

    const { start_date, end_date, label, days } = getSelectedDateRange();
    if (start_date) formData.append("start_date", start_date);
    if (end_date) formData.append("end_date", end_date);

    setLoading(true, `Processing Multi-Network ETL Pipeline for ${label} (${days} days)...`);
    try {
      const res = await fetch("/api/upload-and-process", {
        method: "POST",
        body: formData,
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Processing failed");
      handleSuccessResults(data);
    } catch (err) {
      alert("Error running ETL pipeline: " + err.message);
    } finally {
      setLoading(false);
    }
  });

  btnLoadDemo.addEventListener("click", async () => {
    const { start_date, end_date, label, days } = getSelectedDateRange();
    setLoading(true, `Loading verified demo datasets for ${label} (${days} days)...`);
    try {
      const url = `/api/process-demo?start_date=${encodeURIComponent(start_date)}&end_date=${encodeURIComponent(end_date)}`;
      const res = await fetch(url, { method: "POST" });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Failed to load demo data");
      handleSuccessResults(data);
    } catch (err) {
      alert("Error loading demo data: " + err.message);
    } finally {
      setLoading(false);
    }
  });

  btnCopyTsv.addEventListener("click", () => {
    if (!currentMasterData.length) return;
    const headers = [
      "WEBSITE / BRAND",
      "AFFILIATE NETWORK",
      "SUM of INTERNAL CLICKS",
      "Revenue",
      "RPCs",
    ];
    let tsv = headers.join("\t") + "\n";
    currentMasterData.forEach((row) => {
      tsv += [
        row["WEBSITE / BRAND"],
        row["AFFILIATE NETWORK"],
        row["SUM of INTERNAL CLICKS"],
        row["Revenue"],
        row["RPCs"],
      ].join("\t") + "\n";
    });

    navigator.clipboard.writeText(tsv).then(() => {
      const copyText = document.getElementById("copy-text");
      const original = copyText.textContent;
      copyText.textContent = "Copied to Clipboard! (Cmd+V)";
      setTimeout(() => {
        copyText.textContent = original;
      }, 2500);
    });
  });

  btnExportExcel.addEventListener("click", () => triggerExportExcel());
  btnExportCsv.addEventListener("click", () => triggerExportCsv());
}

let currentReportId = null;

function triggerExportExcel() {
  if (!currentMasterData.length) return;
  fetch("/api/export/excel", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(currentMasterData),
  })
    .then((res) => {
      if (!res.ok) throw new Error("Excel export failed");
      return res.blob();
    })
    .then((blob) => {
      downloadBlob(blob, "Affiliate_Revenue_RPC_Master.xlsx");
    })
    .catch((err) => alert("Export failed: " + err.message));
}

function triggerExportCsv() {
  if (!currentMasterData.length) return;
  fetch("/api/export/csv", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(currentMasterData),
  })
    .then((res) => {
      if (!res.ok) throw new Error("CSV export failed");
      return res.blob();
    })
    .then((blob) => {
      downloadBlob(blob, "Affiliate_Revenue_RPC_Master.csv");
    })
    .catch((err) => alert("Export failed: " + err.message));
}

function triggerCopyTsv(feedbackElId = "copy-text") {
  if (!currentMasterData.length) return;
  const headers = [
    "WEBSITE / BRAND",
    "AFFILIATE NETWORK",
    "SUM of INTERNAL CLICKS",
    "Revenue",
    "RPCs",
  ];
  let tsv = headers.join("\t") + "\n";
  currentMasterData.forEach((row) => {
    tsv += [
      row["WEBSITE / BRAND"],
      row["AFFILIATE NETWORK"],
      row["SUM of INTERNAL CLICKS"],
      row["Revenue"],
      row["RPCs"],
    ].join("\t") + "\n";
  });

  navigator.clipboard.writeText(tsv).then(() => {
    const el = document.getElementById(feedbackElId);
    if (el) {
      const orig = el.textContent;
      el.textContent = "Copied to Clipboard! (Cmd+V)";
      setTimeout(() => {
        el.textContent = orig;
      }, 2500);
    }
  });
}

function formatShortDate(dStr) {
  if (!dStr) return "";
  try {
    const parts = dStr.split("-");
    if (parts.length === 3) {
      const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
      const m = months[parseInt(parts[1], 10) - 1];
      const d = parseInt(parts[2], 10);
      return `${m} ${d}`;
    }
  } catch (e) {}
  return dStr;
}

function setReportViewMeta(title, dateRange, timestamp) {
  const titleEl = document.getElementById("report-page-title");
  const dateEl = document.getElementById("report-page-date-range");
  const timeEl = document.getElementById("report-page-timestamp");

  let cleanTitle = title || "Reconciliation Report";
  const runMatch = cleanTitle.match(/^(\d{4}-\d{2}-\d{2})\s+to\s+(\d{4}-\d{2}-\d{2})(?:\s+Run)?$/i);
  if (runMatch) {
    cleanTitle = `${formatShortDate(runMatch[1])} – ${formatShortDate(runMatch[2])}, ${runMatch[1].split("-")[0]}`;
  } else {
    cleanTitle = cleanTitle.replace(/\s+Run$/i, "");
  }

  if (titleEl) titleEl.textContent = cleanTitle;

  if (dateEl) {
    const daysMatch = (dateRange || "").match(/\((\d+\s*Days?)\)/i);
    if (daysMatch) {
      dateEl.textContent = `${daysMatch[1]} Active`;
    } else {
      dateEl.textContent = dateRange;
    }
  }

  if (timeEl) {
    timeEl.textContent = timestamp
      ? `Saved ${new Date(timestamp).toLocaleDateString()}`
      : "Active Run";
  }
}

async function loadSavedReports() {
  const container = document.getElementById("saved-reports-grid");
  const countPill = document.getElementById("saved-reports-count-pill");
  if (!container) return;

  try {
    const res = await fetch("/api/reports");
    const json = await res.json();
    const reports = json.reports || [];

    if (countPill) {
      countPill.textContent = `${reports.length} Saved`;
    }

    if (reports.length === 0) {
      container.innerHTML = `
        <div class="col-span-full p-8 text-center bg-slate-50 rounded-2xl border-2 border-dashed border-slate-200">
          <i class="ph-bold ph-bookmarks-simple text-3xl text-slate-300 mb-2 inline-block"></i>
          <p class="text-xs font-semibold text-slate-600">No saved reports yet</p>
          <p class="text-[11px] text-slate-400 mt-1">Run an ETL query above or click "Load Demo Data" to generate your first persistent report tile.</p>
        </div>
      `;
      return;
    }

    container.innerHTML = reports
      .map((rep) => {
        const rev = formatCurrency(rep.summary?.total_revenue || 0);
        const clicks = formatNumber(rep.summary?.total_internal_clicks || 0);
        const rpc = (rep.summary?.overall_portfolio_rpc || 0).toFixed(4);
        const matched = rep.summary?.matched_revenue_rows || 17;
        const total = rep.summary?.total_master_rows || 147;
        const createdDate = rep.created_at
          ? new Date(rep.created_at).toLocaleDateString()
          : "Saved";

        let displayTitle = rep.title || "Report";
        const runMatch = displayTitle.match(/^(\d{4}-\d{2}-\d{2})\s+to\s+(\d{4}-\d{2}-\d{2})(?:\s+Run)?$/i);
        if (runMatch) {
          displayTitle = `${formatShortDate(runMatch[1])} – ${formatShortDate(runMatch[2])}, ${runMatch[1].split("-")[0]}`;
        } else {
          displayTitle = displayTitle.replace(/\s+Run$/i, "");
        }

        return `
          <div class="report-tile bg-white dark:bg-[#0e1628] hover:bg-slate-50 dark:hover:bg-[#121c33] p-4 sm:p-5 rounded-2xl border border-slate-200 dark:border-slate-800 hover:border-indigo-500/50 dark:hover:border-indigo-500/50 shadow-xs hover:shadow-lg transition-all cursor-pointer group flex flex-col justify-between" data-report-id="${rep.id}">
            <div>
              <div class="flex items-start justify-between gap-2 mb-3">
                <div class="flex items-center space-x-2.5 min-w-0">
                  <div class="w-8 h-8 rounded-lg bg-indigo-500/10 dark:bg-indigo-500/20 text-indigo-600 dark:text-indigo-400 flex items-center justify-center shrink-0 border border-indigo-500/20">
                    <i class="ph-bold ph-calendar-check text-base"></i>
                  </div>
                  <div class="min-w-0">
                    <h4 class="font-bold text-slate-900 dark:text-white text-xs sm:text-sm group-hover:text-indigo-500 dark:group-hover:text-indigo-400 transition truncate" title="${rep.title}">
                      ${displayTitle}
                    </h4>
                    <span class="inline-flex items-center text-[10px] font-semibold text-slate-500 dark:text-slate-400 mt-0.5">
                      ${rep.days_count || 0} Days Active • Saved ${createdDate}
                    </span>
                  </div>
                </div>
                <button class="btn-delete-report text-slate-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-950/40 p-1.5 rounded-lg transition shrink-0" title="Delete report" data-report-id="${rep.id}" data-report-title="${rep.title.replace(/"/g, '&quot;')}">
                  <i class="ph-bold ph-trash text-sm"></i>
                </button>
              </div>

              <div class="grid grid-cols-2 gap-2 my-2.5 text-xs">
                <div class="bg-slate-50 dark:bg-[#060a14] p-2.5 rounded-xl border border-slate-200/60 dark:border-slate-800/80">
                  <span class="text-[10px] uppercase font-bold text-slate-500 dark:text-slate-400 tracking-wider block mb-0.5">Revenue</span>
                  <span class="text-xs sm:text-sm font-extrabold text-emerald-600 dark:text-emerald-400 font-mono tracking-tight">${rev}</span>
                </div>
                <div class="bg-slate-50 dark:bg-[#060a14] p-2.5 rounded-xl border border-slate-200/60 dark:border-slate-800/80">
                  <span class="text-[10px] uppercase font-bold text-slate-500 dark:text-slate-400 tracking-wider block mb-0.5">Clicks</span>
                  <span class="text-xs sm:text-sm font-extrabold text-blue-600 dark:text-blue-400 font-mono tracking-tight">${clicks}</span>
                </div>
                <div class="bg-slate-50 dark:bg-[#060a14] p-2.5 rounded-xl border border-slate-200/60 dark:border-slate-800/80">
                  <span class="text-[10px] uppercase font-bold text-slate-500 dark:text-slate-400 tracking-wider block mb-0.5">RPC</span>
                  <span class="text-xs sm:text-sm font-extrabold text-purple-600 dark:text-purple-400 font-mono tracking-tight">₹${rpc}</span>
                </div>
                <div class="bg-slate-50 dark:bg-[#060a14] p-2.5 rounded-xl border border-slate-200/60 dark:border-slate-800/80">
                  <span class="text-[10px] uppercase font-bold text-slate-500 dark:text-slate-400 tracking-wider block mb-0.5">Campaigns</span>
                  <span class="text-xs sm:text-sm font-extrabold text-slate-800 dark:text-white font-mono tracking-tight">${matched} / ${total}</span>
                </div>
              </div>
            </div>

            <div class="pt-2.5 border-t border-slate-100 dark:border-slate-800/80 flex items-center justify-between text-[11px] text-slate-400 dark:text-slate-500">
              <span>Saved ${createdDate}</span>
              <span class="text-indigo-600 dark:text-indigo-400 font-semibold group-hover:translate-x-1 transition-transform inline-flex items-center space-x-1">
                <span>View</span>
                <i class="ph-bold ph-arrow-right text-xs"></i>
              </span>
            </div>
          </div>
        `;
      })
      .join("");

    // Attach click listeners to tiles
    container.querySelectorAll(".report-tile").forEach((tile) => {
      tile.addEventListener("click", (e) => {
        if (e.target.closest(".btn-delete-report")) return;
        const repId = tile.getAttribute("data-report-id");
        if (repId) openSavedReport(repId);
      });
    });

    // Attach click listeners to delete buttons
    container.querySelectorAll(".btn-delete-report").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        e.stopPropagation();
        const repId = btn.getAttribute("data-report-id");
        const repTitle = btn.getAttribute("data-report-title") || repId;
        deleteSavedReport(repId, repTitle, e);
      });
    });
  } catch (err) {
    console.error("Error loading saved reports:", err);
  }
}

async function openSavedReport(reportId) {
  try {
    const res = await fetch(`/api/reports/${encodeURIComponent(reportId)}`);
    if (!res.ok) throw new Error("Report not found");
    const report = await res.json();
    currentReportId = report.id;
    currentMasterData = report.data || [];
    currentSummary = report.summary || {};

    saveAppState();

    setReportViewMeta(
      report.title || "Saved Query Report",
      `${report.start_date} to ${report.end_date} (${report.days_count || 0} Days)`,
      report.created_at
    );

    renderKPIs(currentSummary);
    renderMasterTable(currentMasterData);
    if (currentSummary.network_processing_logs) {
      renderProcessingLogs(currentSummary.network_processing_logs);
    }

    const badgeDates = document.getElementById("badge-table-dates");
    if (badgeDates) {
      badgeDates.textContent = `📅 ${report.start_date} to ${report.end_date} (${report.days_count || 0}d)`;
    }

    switchToView("report", true, reportId);
  } catch (err) {
    console.error("Error opening saved report:", err);
    alert("Could not load saved report: " + err.message);
  }
}

async function deleteSavedReport(reportId, reportTitle, event) {
  if (event) event.stopPropagation();
  if (
    !confirm(
      `Are you sure you want to delete "${reportTitle}"? It will be removed permanently from your saved queries.`
    )
  ) {
    return;
  }
  try {
    const res = await fetch(`/api/reports/${encodeURIComponent(reportId)}`, {
      method: "DELETE",
    });
    const data = await res.json();
    if (data.success) {
      await loadSavedReports();
      if (currentReportId === reportId) {
        switchToView("master", true);
      }
    } else {
      alert("Failed to delete report: " + (data.detail || "Unknown error"));
    }
  } catch (err) {
    console.error("Error deleting report:", err);
    alert("Error deleting report: " + err.message);
  }
}

// SPA Routing and View Management (Zero Page Reload)
function switchToView(viewName, pushHistory = true, reportId = null) {
  const viewMaster = document.getElementById("view-master");
  const viewReport = document.getElementById("view-report");
  const viewAnalytics = document.getElementById("view-analytics");
  const headerMaster = document.getElementById("header-master-nav");
  const headerAnalytics = document.getElementById("header-analytics-nav");

  if (viewName === "analytics") {
    if (viewMaster) viewMaster.classList.add("hidden");
    if (viewReport) viewReport.classList.add("hidden");
    if (headerMaster) headerMaster.classList.add("hidden");
    if (viewAnalytics) viewAnalytics.classList.remove("hidden");
    if (headerAnalytics) headerAnalytics.classList.remove("hidden");

    if (pushHistory) {
      history.pushState({ view: "analytics" }, "", "/analytics");
    }

    if (window.initAnalyticsWithData) {
      window.initAnalyticsWithData(currentMasterData, currentSummary);
    }
    window.scrollTo({ top: 0, behavior: "smooth" });
  } else if (viewName === "report") {
    if (viewMaster) viewMaster.classList.add("hidden");
    if (viewAnalytics) viewAnalytics.classList.add("hidden");
    if (headerAnalytics) headerAnalytics.classList.add("hidden");
    if (viewReport) viewReport.classList.remove("hidden");
    if (headerMaster) headerMaster.classList.remove("hidden");

    const rId = reportId || currentReportId || "latest";
    if (pushHistory) {
      history.pushState({ view: "report", reportId: rId }, "", `/report/${rId}`);
    }
    window.scrollTo({ top: 0, behavior: "smooth" });
  } else {
    // Switch to master
    if (viewAnalytics) viewAnalytics.classList.add("hidden");
    if (headerAnalytics) headerAnalytics.classList.add("hidden");
    if (viewReport) viewReport.classList.add("hidden");
    if (viewMaster) viewMaster.classList.remove("hidden");
    if (headerMaster) headerMaster.classList.remove("hidden");

    if (pushHistory) {
      history.pushState({ view: "master" }, "", "/");
    }

    loadSavedReports();
    window.scrollTo({ top: 0, behavior: "smooth" });
  }
}

function setupRoutingAndHistory() {
  const btnOpenAnalytics = document.getElementById("btn-open-analytics");
  const navBtnAnalytics = document.getElementById("nav-btn-analytics");
  const btnBackToMaster = document.getElementById("btn-back-to-master");
  const btnBackFromReport = document.getElementById("btn-back-from-report");
  const btnReportAnalytics = document.getElementById("btn-report-analytics");
  const btnReportCopyTsv = document.getElementById("btn-report-copy-tsv");
  const btnReportExportExcel = document.getElementById("btn-report-export-excel");
  const btnReportExportCsv = document.getElementById("btn-report-export-csv");
  const btnReportDelete = document.getElementById("btn-report-delete");
  const btnRefreshSaved = document.getElementById("btn-refresh-saved-reports");

  if (btnOpenAnalytics) {
    btnOpenAnalytics.addEventListener("click", () => {
      saveAppState();
      switchToView("analytics", true);
    });
  }

  if (navBtnAnalytics) {
    navBtnAnalytics.addEventListener("click", (e) => {
      e.preventDefault();
      saveAppState();
      switchToView("analytics", true);
    });
  }

  if (btnBackToMaster) {
    btnBackToMaster.addEventListener("click", () => {
      switchToView("master", true);
    });
  }

  if (btnBackFromReport) {
    btnBackFromReport.addEventListener("click", () => {
      switchToView("master", true);
    });
  }

  if (btnReportAnalytics) {
    btnReportAnalytics.addEventListener("click", () => {
      saveAppState();
      switchToView("analytics", true);
    });
  }

  if (btnReportCopyTsv) {
    btnReportCopyTsv.addEventListener("click", () => triggerCopyTsv("report-copy-text"));
  }

  if (btnReportExportExcel) {
    btnReportExportExcel.addEventListener("click", () => triggerExportExcel());
  }

  if (btnReportExportCsv) {
    btnReportExportCsv.addEventListener("click", () => triggerExportCsv());
  }

  if (btnReportDelete) {
    btnReportDelete.addEventListener("click", () => {
      const repTitle =
        document.getElementById("report-page-title")?.textContent || "this report";
      if (currentReportId) {
        deleteSavedReport(currentReportId, repTitle);
      }
    });
  }

  if (btnRefreshSaved) {
    btnRefreshSaved.addEventListener("click", loadSavedReports);
  }

  window.addEventListener("popstate", (e) => {
    const path = window.location.pathname;
    const hash = window.location.hash;
    if (path === "/analytics" || e.state?.view === "analytics") {
      switchToView("analytics", false);
    } else if (path.startsWith("/report/") || hash.startsWith("#report/")) {
      const rId = path.startsWith("/report/")
        ? path.replace("/report/", "")
        : hash.replace("#report/", "");
      openSavedReport(rId);
    } else {
      switchToView("master", false);
    }
  });

  const path = window.location.pathname;
  const hash = window.location.hash;
  if (path === "/analytics" || hash === "#analytics") {
    switchToView("analytics", false);
  } else if (path.startsWith("/report/") || hash.startsWith("#report/")) {
    const rId = path.startsWith("/report/")
      ? path.replace("/report/", "")
      : hash.replace("#report/", "");
    openSavedReport(rId);
  } else {
    loadSavedReports();
  }
}

function saveAppState() {
  try {
    if (currentMasterData && currentMasterData.length > 0) {
      sessionStorage.setItem("affiliate_master_data", JSON.stringify(currentMasterData));
      sessionStorage.setItem("affiliate_analytics_data", JSON.stringify(currentMasterData));
    }
    if (currentSummary) {
      sessionStorage.setItem("affiliate_summary", JSON.stringify(currentSummary));
      sessionStorage.setItem("affiliate_analytics_summary", JSON.stringify(currentSummary));
    }
    if (internalClicksFile) {
      sessionStorage.setItem(
        "affiliate_clicks_info",
        JSON.stringify({ name: internalClicksFile.name, size: internalClicksFile.size })
      );
    }
  } catch (e) {
    console.warn("Storage save error:", e);
  }
}

function restoreAppState() {
  try {
    const savedData = sessionStorage.getItem("affiliate_master_data");
    const savedSummary = sessionStorage.getItem("affiliate_summary");
    if (savedData) {
      currentMasterData = JSON.parse(savedData);
      currentSummary = savedSummary ? JSON.parse(savedSummary) : {};
      renderKPIs(currentSummary);
      renderMasterTable(currentMasterData);
      if (currentSummary.network_processing_logs) {
        renderProcessingLogs(currentSummary.network_processing_logs);
      }
      document.getElementById("section-kpis").classList.remove("hidden");
      document.getElementById("section-results").classList.remove("hidden");
      if (currentSummary.network_processing_logs && currentSummary.network_processing_logs.length > 0) {
        document.getElementById("section-logs").classList.remove("hidden");
      }
    }

    const clicksInfo = sessionStorage.getItem("affiliate_clicks_info");
    if (clicksInfo) {
      const parsed = JSON.parse(clicksInfo);
      document.getElementById("clicks-filename").textContent = parsed.name;
      document.getElementById("clicks-filesize").textContent = formatBytes(parsed.size);
      document.getElementById("clicks-prompt").classList.add("hidden");
      document.getElementById("clicks-preview").classList.remove("hidden");
    }
  } catch (e) {
    console.warn("Storage restore error:", e);
  }
}

function handleSuccessResults(response) {
  currentMasterData = response.data || [];
  currentSummary = response.summary || {};

  saveAppState();

  renderKPIs(currentSummary);
  renderMasterTable(currentMasterData);
  renderProcessingLogs(currentSummary.network_processing_logs || []);

  const badgeDates = document.getElementById("badge-table-dates");
  if (badgeDates && currentSummary.date_range) {
    badgeDates.textContent = `📅 Window: ${currentSummary.date_range}`;
  }

  const dateWindow = currentSummary.date_window || {};
  const sDate = currentSummary.start_date || dateWindow.start_date || "2026-10-01";
  const eDate = currentSummary.end_date || dateWindow.end_date || "2026-10-31";
  const days = dateWindow.total_days || 31;
  const title = currentSummary.date_range
    ? `${currentSummary.date_range} Run`
    : `${sDate} to ${eDate} Run`;

  currentReportId = `report_${sDate.replace(/-/g, "")}_${eDate.replace(/-/g, "")}`;
  setReportViewMeta(
    title,
    `${sDate} to ${eDate} (${days} Days)`,
    new Date().toISOString()
  );

  // Reload saved reports so the tile appears in the grid
  loadSavedReports();

  // Switch to dedicated report page view
  switchToView("report", true, currentReportId);
}

function renderKPIs(summary) {
  const kpiRev = document.getElementById("kpi-revenue");
  if (kpiRev) kpiRev.textContent = formatCurrency(summary.total_revenue || 0);

  const kpiClicks = document.getElementById("kpi-clicks");
  if (kpiClicks) kpiClicks.textContent = formatNumber(summary.total_internal_clicks || 0);

  const kpiRpc = document.getElementById("kpi-rpc");
  if (kpiRpc) kpiRpc.textContent = (summary.overall_portfolio_rpc || 0).toFixed(4);

  const matched = summary.matched_revenue_rows || 0;
  const total = summary.total_master_rows || 0;
  const kpiRows = document.getElementById("kpi-rows-count");
  if (kpiRows) kpiRows.textContent = `${matched} / ${total}`;

  const kpiMatchedPill = document.getElementById("kpi-matched-pill");
  if (kpiMatchedPill) kpiMatchedPill.textContent = `${matched} campaigns generating revenue`;

  // Date Synchronization Audit Banner
  const dateSyncWin = document.getElementById("sync-date-window");
  const dateSyncRows = document.getElementById("sync-rows-text");
  if (dateSyncWin && summary.date_range) {
    dateSyncWin.textContent = summary.date_range;
  }
  if (dateSyncRows && summary.internal_clicks_diag) {
    const diag = summary.internal_clicks_diag;
    if (diag.is_date_filtered) {
      dateSyncRows.textContent = `${diag.filtered_records_count || 'Daily'} records filtered (${diag.total_internal_clicks ? formatNumber(diag.total_internal_clicks) : ''} clicks)`;
    } else {
      dateSyncRows.textContent = `Full Monthly Tracking Period (${diag.total_internal_clicks ? formatNumber(diag.total_internal_clicks) : ''} clicks)`;
    }
  }

  // Orphaned records check
  const orphans = summary.orphaned_affiliate_records || [];
  const orphanBanner = document.getElementById("banner-orphans");
  const orphanText = document.getElementById("kpi-orphan-text");

  if (orphans.length > 0) {
    if (orphanBanner) orphanBanner.classList.remove("hidden");
    if (orphanText) {
      orphanText.textContent = `${orphans.length} unmatched network records!`;
      orphanText.className = "text-[11px] text-amber-600 font-semibold mt-1";
    }

    const totalOrphanRev = orphans.reduce((acc, r) => acc + (r.revenue || 0), 0);
    const summaryText = document.getElementById("orphans-summary-text");
    if (summaryText) {
      summaryText.textContent =
        `${orphans.length} brand entries with total ${formatCurrency(totalOrphanRev)} were found in affiliate reports but do not exist in the internal clicks master sheet.`;
    }

    const tbody = document.getElementById("orphans-table-body");
    if (tbody) {
      tbody.innerHTML = "";
      orphans.forEach((o) => {
        const tr = document.createElement("tr");
        tr.innerHTML = `
          <td class="py-1 font-medium">${escapeHtml(o.network)}</td>
          <td class="py-1 text-slate-600">${escapeHtml(o.original_brand)}</td>
          <td class="py-1 font-semibold text-slate-800">${escapeHtml(o.brand)}</td>
          <td class="py-1 text-right font-mono font-bold text-emerald-700">${formatCurrency(o.revenue)}</td>
        `;
        tbody.appendChild(tr);
      });
    }

    const btnToggle = document.getElementById("btn-toggle-orphans");
    if (btnToggle) {
      btnToggle.onclick = () => {
        const details = document.getElementById("orphans-details");
        if (details) details.classList.toggle("hidden");
      };
    }
  } else {
    if (orphanBanner) orphanBanner.classList.add("hidden");
    if (orphanText) {
      orphanText.textContent = "0 orphaned records (100% matched)";
      orphanText.className = "text-[11px] text-slate-500 mt-1";
    }
  }
}

function renderMasterTable(rows) {
  const tbody = document.getElementById("master-table-body");
  tbody.innerHTML = "";

  document.getElementById("table-row-count").textContent = `Showing ${rows.length} rows`;

  rows.forEach((row, idx) => {
    const tr = document.createElement("tr");
    tr.className = "table-row-hover transition-colors";

    const clicks = row["SUM of INTERNAL CLICKS"] || 0;
    const rev = row["Revenue"] || 0;
    const rpc = row["RPCs"] || 0;

    const revClass =
      rev > 0 ? "font-bold text-emerald-600 dark:text-emerald-400" : "text-slate-400 dark:text-slate-500";
    const rpcClass =
      rpc > 0.20
        ? "font-bold text-emerald-700 dark:text-emerald-300 bg-emerald-50 dark:bg-emerald-950/40 rounded px-1.5 py-0.5"
        : rpc > 0
        ? "font-bold text-emerald-600 dark:text-emerald-400"
        : "text-slate-400 dark:text-slate-500";

    const rpcDisplay =
      rpc > 0 && rpc < 0.01 ? rpc.toFixed(4) : rpc.toFixed(2);

    tr.innerHTML = `
      <td class="py-2.5 px-4 text-center text-slate-400 font-sans text-[11px]">${idx + 1}</td>
      <td class="py-2.5 px-4 font-sans font-medium text-slate-900 dark:text-white">${escapeHtml(row["WEBSITE / BRAND"])}</td>
      <td class="py-2.5 px-4 font-sans text-slate-600 dark:text-slate-300">
        <span class="px-2 py-0.5 rounded-md bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 text-[11px] border border-slate-200 dark:border-slate-700">
          ${escapeHtml(row["AFFILIATE NETWORK"])}
        </span>
      </td>
      <td class="py-2.5 px-4 text-right font-medium text-slate-800 dark:text-slate-100 font-mono">${formatNumber(clicks)}</td>
      <td class="py-2.5 px-4 text-right ${revClass} font-mono">${formatCurrency(rev)}</td>
      <td class="py-2.5 px-4 text-right ${rpcClass} font-mono">${rpcDisplay}</td>
    `;
    tbody.appendChild(tr);
  });
}

function renderProcessingLogs(logs) {
  const container = document.getElementById("logs-container");
  container.innerHTML = "";

  logs.forEach((log) => {
    const isSuccess = log.status === "success";
    const item = document.createElement("div");
    item.className = `flex items-center justify-between p-2.5 rounded-xl border text-xs ${
      isSuccess
        ? "bg-slate-50 border-slate-200"
        : "bg-red-50 border-red-200 text-red-800"
    }`;

    item.innerHTML = `
      <div class="flex items-center space-x-2">
        <i class="ph-bold ${isSuccess ? "ph-check-circle text-emerald-600" : "ph-x-circle text-red-500"} text-base"></i>
        <div>
          <span class="font-medium text-slate-800">${escapeHtml(log.filename)}</span>
          <span class="text-slate-400 mx-1.5">•</span>
          <span class="text-slate-500 font-sans">Adapter: <strong>${escapeHtml(log.detected_network)}</strong></span>
          ${log.is_date_scaled ? '<span class="ml-1.5 px-1.5 py-0.5 rounded text-[10px] bg-blue-100 text-blue-700 font-medium">Scaled to Range</span>' : ''}
        </div>
      </div>
      <div class="text-right">
        ${
          isSuccess
            ? `<span class="font-mono text-emerald-700 font-bold">${formatCurrency(log.total_revenue || 0)}</span>
               <span class="text-[11px] text-slate-400 ml-1">(${log.records_count} records)</span>`
            : `<span class="text-red-600 font-semibold">${escapeHtml(log.error_message || "Error")}</span>`
        }
      </div>
    `;
    container.appendChild(item);
  });
}

// 4. Search and Table Filtering
function setupSearchAndFilters() {
  const searchInput = document.getElementById("search-table");
  searchInput.addEventListener("input", (e) => {
    const q = e.target.value.toLowerCase().trim();
    if (!q) {
      renderMasterTable(currentMasterData);
      return;
    }
    const filtered = currentMasterData.filter((r) => {
      const b = (r["WEBSITE / BRAND"] || "").toLowerCase();
      const n = (r["AFFILIATE NETWORK"] || "").toLowerCase();
      return b.includes(q) || n.includes(q);
    });
    renderMasterTable(filtered);
  });
}

// 5. Aliases Modal Handling
function setupAliasesModal() {
  const modal = document.getElementById("modal-aliases");
  const btnOpen = document.getElementById("btn-open-rules");
  const btnClose = document.getElementById("btn-close-modal");
  const btnSave = document.getElementById("btn-save-alias");
  const listContainer = document.getElementById("aliases-list");

  btnOpen.addEventListener("click", () => {
    loadAliases();
    modal.classList.remove("hidden");
  });

  btnClose.addEventListener("click", () => {
    modal.classList.add("hidden");
  });

  modal.addEventListener("click", (e) => {
    if (e.target === modal) modal.classList.add("hidden");
  });

  btnSave.addEventListener("click", async () => {
    const rawInput = document.getElementById("input-alias-raw");
    const canInput = document.getElementById("input-alias-canonical");
    const raw = rawInput.value.trim();
    const can = canInput.value.trim();
    if (!raw || !can) {
      alert("Please fill in both the raw name and canonical brand name.");
      return;
    }

    try {
      const res = await fetch("/api/aliases", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ raw_name: raw, canonical_brand: can }),
      });
      if (!res.ok) throw new Error("Failed to save alias");
      rawInput.value = "";
      canInput.value = "";
      loadAliases();
    } catch (err) {
      alert("Error saving alias: " + err.message);
    }
  });

  async function loadAliases() {
    listContainer.innerHTML = "<p class='text-slate-400 py-2'>Loading rules...</p>";
    try {
      const res = await fetch("/api/aliases");
      const data = await res.json();
      listContainer.innerHTML = "";
      const entries = Object.entries(data.aliases || {});
      entries.slice(0, 30).forEach(([raw, can]) => {
        const item = document.createElement("div");
        item.className = "py-1.5 flex items-center justify-between text-slate-700";
        item.innerHTML = `
          <span class="font-mono text-slate-500">${escapeHtml(raw)}</span>
          <div class="flex items-center space-x-1">
            <i class="ph ph-arrow-right text-slate-400"></i>
            <span class="font-semibold text-emerald-700">${escapeHtml(can)}</span>
          </div>
        `;
        listContainer.appendChild(item);
      });
    } catch (err) {
      listContainer.innerHTML = "<p class='text-red-500'>Error loading aliases</p>";
    }
  }
}

// Utilities
function formatNumber(num) {
  return new Intl.NumberFormat("en-IN").format(num);
}

function formatCurrency(val) {
  return "₹ " + new Intl.NumberFormat("en-IN", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(val);
}

function formatBytes(bytes) {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + " " + sizes[i];
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

function downloadBlob(blob, filename) {
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  window.URL.revokeObjectURL(url);
}

function setLoading(isLoading, text = "Processing...") {
  const btnRun = document.getElementById("btn-run-etl");
  if (isLoading) {
    btnRun.disabled = true;
    btnRun.innerHTML = `<i class="ph ph-spinner animate-spin"></i><span>${text}</span>`;
  } else {
    btnRun.disabled = false;
    btnRun.innerHTML = `<i class="ph-bold ph-play"></i><span>Run ETL & Calculate RPCs</span>`;
  }
}
