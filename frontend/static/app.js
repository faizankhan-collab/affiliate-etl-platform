// Frontend Controller for Affiliate ETL & RPC Automator

let internalClicksFile = null;
let stagedNetworkFiles = []; // Array of { file, network }
let currentMasterData = [];
let currentSummary = null;

// Lightweight IndexedDB helper for persisting raw File objects across page reloads
const FileStore = {
  dbName: "AffiliateETLStorage",
  storeName: "files",
  openDB() {
    return new Promise((resolve, reject) => {
      if (typeof indexedDB === "undefined") {
        return resolve(null);
      }
      const req = indexedDB.open(this.dbName, 1);
      req.onupgradeneeded = (e) => {
        const db = e.target.result;
        if (!db.objectStoreNames.contains(this.storeName)) {
          db.createObjectStore(this.storeName);
        }
      };
      req.onsuccess = () => resolve(req.result);
      req.onerror = () => resolve(null);
    });
  },
  async setFile(key, file) {
    try {
      const db = await this.openDB();
      if (!db) return false;
      return new Promise((resolve) => {
        const tx = db.transaction(this.storeName, "readwrite");
        const store = tx.objectStore(this.storeName);
        const req = store.put(file, key);
        req.onsuccess = () => resolve(true);
        req.onerror = () => resolve(false);
      });
    } catch (e) {
      console.warn("IndexedDB setFile error:", e);
      return false;
    }
  },
  async getFile(key) {
    try {
      const db = await this.openDB();
      if (!db) return null;
      return new Promise((resolve) => {
        const tx = db.transaction(this.storeName, "readonly");
        const store = tx.objectStore(this.storeName);
        const req = store.get(key);
        req.onsuccess = () => resolve(req.result || null);
        req.onerror = () => resolve(null);
      });
    } catch (e) {
      console.warn("IndexedDB getFile error:", e);
      return null;
    }
  },
  async removeFile(key) {
    try {
      const db = await this.openDB();
      if (!db) return false;
      return new Promise((resolve) => {
        const tx = db.transaction(this.storeName, "readwrite");
        const store = tx.objectStore(this.storeName);
        const req = store.delete(key);
        req.onsuccess = () => resolve(true);
        req.onerror = () => resolve(false);
      });
    } catch (e) {
      console.warn("IndexedDB removeFile error:", e);
      return false;
    }
  }
};

// Persistent storage helper for Saved Reports (IndexedDB + LocalStorage fallback)
const ReportStore = {
  dbName: "AffiliateETLReportsDB",
  storeName: "saved_reports",
  openDB() {
    return new Promise((resolve) => {
      if (typeof indexedDB === "undefined") return resolve(null);
      const req = indexedDB.open(this.dbName, 1);
      req.onupgradeneeded = (e) => {
        const db = e.target.result;
        if (!db.objectStoreNames.contains(this.storeName)) {
          db.createObjectStore(this.storeName, { keyPath: "id" });
        }
      };
      req.onsuccess = () => resolve(req.result);
      req.onerror = () => resolve(null);
    });
  },
  async saveReport(report) {
    if (!report || !report.id) return false;
    try {
      const db = await this.openDB();
      if (db) {
        await new Promise((resolve) => {
          const tx = db.transaction(this.storeName, "readwrite");
          const store = tx.objectStore(this.storeName);
          const req = store.put(report);
          req.onsuccess = () => resolve(true);
          req.onerror = () => resolve(false);
        });
      }
      // Also write metadata to localStorage backup so it survives even if IndexedDB clears
      const localKey = "affiliate_reports_backup";
      const existing = JSON.parse(localStorage.getItem(localKey) || "{}");
      const metaObj = {
        id: report.id,
        title: report.title,
        start_date: report.start_date,
        end_date: report.end_date,
        days_count: report.days_count,
        created_at: report.created_at,
        usd_to_inr_rate: report.usd_to_inr_rate,
        summary: report.summary,
        // Store up to 500 rows in localStorage to avoid storage quota limit
        data: (report.data && report.data.length > 500) ? report.data.slice(0, 500) : (report.data || []),
      };
      existing[report.id] = metaObj;
      localStorage.setItem(localKey, JSON.stringify(existing));
      return true;
    } catch (e) {
      console.warn("ReportStore save error:", e);
      return false;
    }
  },
  async getReport(id) {
    try {
      const db = await this.openDB();
      if (db) {
        const rep = await new Promise((resolve) => {
          const tx = db.transaction(this.storeName, "readonly");
          const store = tx.objectStore(this.storeName);
          const req = store.get(id);
          req.onsuccess = () => resolve(req.result || null);
          req.onerror = () => resolve(null);
        });
        if (rep) return rep;
      }
      const existing = JSON.parse(localStorage.getItem("affiliate_reports_backup") || "{}");
      return existing[id] || null;
    } catch (e) {
      return null;
    }
  },
  async getAllReports() {
    try {
      const db = await this.openDB();
      if (db) {
        const list = await new Promise((resolve) => {
          const tx = db.transaction(this.storeName, "readonly");
          const store = tx.objectStore(this.storeName);
          const req = store.getAll();
          req.onsuccess = () => resolve(req.result || []);
          req.onerror = () => resolve([]);
        });
        if (list && list.length > 0) return list;
      }
      const existing = JSON.parse(localStorage.getItem("affiliate_reports_backup") || "{}");
      return Object.values(existing);
    } catch (e) {
      return [];
    }
  },
  async deleteReport(id) {
    try {
      const db = await this.openDB();
      if (db) {
        const tx = db.transaction(this.storeName, "readwrite");
        const store = tx.objectStore(this.storeName);
        store.delete(id);
      }
      const existing = JSON.parse(localStorage.getItem("affiliate_reports_backup") || "{}");
      delete existing[id];
      localStorage.setItem("affiliate_reports_backup", JSON.stringify(existing));
      return true;
    } catch (e) {
      return false;
    }
  }
};

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
  try {
    setupRoutingAndHistory();
  } catch (err) {
    console.error("Routing setup error:", err);
  }
  setupInternalClicksDropzone();
  setupNetworkFilesDropzone();
  setupActionButtons();
  setupSearchAndFilters();
  setupAliasesModal();
  setupSaveReportModal();
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

function getSelectedDateRange() {
  const dateRangePreset = document.getElementById("date-range-preset");
  const inputDateStart = document.getElementById("input-date-start");
  const inputDateEnd = document.getElementById("input-date-end");

  const preset = dateRangePreset ? dateRangePreset.value : "2026-10";
  let start_date = "2026-10-01";
  let end_date = "2026-10-31";
  let label = "October 2026";
  let isCustom = false;

  if (preset === "custom") {
    isCustom = true;
    start_date = inputDateStart && inputDateStart.value ? inputDateStart.value : "2026-10-01";
    end_date = inputDateEnd && inputDateEnd.value ? inputDateEnd.value : "2026-10-31";
    label = `${start_date} to ${end_date}`;
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

  return { start_date, end_date, label, days: diffDays, isCustom };
}

function updateDateRangeUI() {
  const range = getSelectedDateRange();
  const activeRangePill = document.getElementById("active-range-pill");
  const dateRangePreset = document.getElementById("date-range-preset");
  const inputDateStart = document.getElementById("input-date-start");
  const inputDateEnd = document.getElementById("input-date-end");

  if (activeRangePill) {
    if (range.isCustom) {
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

  const liveScopeBadge = document.getElementById("live-clicks-active-scope-badge");
  if (liveScopeBadge) {
    if (range.isCustom) {
      liveScopeBadge.textContent = `📅 ${range.start_date} to ${range.end_date} (${range.days} Days)`;
    } else {
      liveScopeBadge.textContent = `📅 ${range.label} (${range.start_date} to ${range.end_date})`;
    }
  }

  if (inputDateStart && range.start_date && !range.isCustom) {
    inputDateStart.value = range.start_date;
  }
  if (inputDateEnd && range.end_date && !range.isCustom) {
    inputDateEnd.value = range.end_date;
  }
  checkDateRangeOverlap();
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
    FileStore.removeFile("internal_clicks");
    inspectClicksFileDates(null);
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
    FileStore.setFile("internal_clicks", file);
    inspectClicksFileDates(file);
  }

  setupLiveClicksControls();
}

function setupLiveClicksControls() {
  const tabLive = document.getElementById("tab-clicks-live");
  const tabUpload = document.getElementById("tab-clicks-upload");
  const panelLive = document.getElementById("panel-clicks-live");
  const panelUpload = document.getElementById("panel-clicks-upload");
  const btnFetch = document.getElementById("btn-fetch-live-clicks");
  const statusBox = document.getElementById("live-clicks-status-box");
  const totalLabel = document.getElementById("live-clicks-total-label");
  const topPreview = document.getElementById("live-clicks-top-preview");
  const btnClearLive = document.getElementById("btn-clear-live-clicks");

  // Tab switching
  if (tabLive && tabUpload && panelLive && panelUpload) {
    tabLive.addEventListener("click", () => {
      tabLive.className = "flex-1 py-1.5 px-3 rounded-lg bg-white dark:bg-slate-900 text-blue-600 dark:text-blue-400 shadow-xs transition flex items-center justify-center space-x-1.5 cursor-pointer font-semibold";
      tabUpload.className = "flex-1 py-1.5 px-3 rounded-lg text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 transition flex items-center justify-center space-x-1.5 cursor-pointer font-semibold";
      panelLive.classList.remove("hidden");
      panelUpload.classList.add("hidden");
    });

    tabUpload.addEventListener("click", () => {
      tabUpload.className = "flex-1 py-1.5 px-3 rounded-lg bg-white dark:bg-slate-900 text-blue-600 dark:text-blue-400 shadow-xs transition flex items-center justify-center space-x-1.5 cursor-pointer font-semibold";
      tabLive.className = "flex-1 py-1.5 px-3 rounded-lg text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 transition flex items-center justify-center space-x-1.5 cursor-pointer font-semibold";
      panelUpload.classList.remove("hidden");
      panelLive.classList.add("hidden");
    });
  }

  // Fetch Live Clicks (Uses single Master Date Scope)
  if (btnFetch) {
    btnFetch.addEventListener("click", async () => {
      const range = getSelectedDateRange();
      const fromDate = range.start_date;
      const uptoDate = range.end_date;
      const scopeDesc = range.isCustom ? `${fromDate} to ${uptoDate}` : range.label;

      const origBtnHtml = btnFetch.innerHTML;
      btnFetch.disabled = true;
      btnFetch.innerHTML = `<i class="ph ph-spinner animate-spin"></i><span>Fetching Live Clicks (${escapeHtml(fromDate)} to ${escapeHtml(uptoDate)})...</span>`;

      try {
        // 1. Fetch live CSV for pipeline processing
        const csvRes = await fetch(`/api/internal-clicks/download-csv?start_date=${encodeURIComponent(fromDate)}&end_date=${encodeURIComponent(uptoDate)}`);
        if (!csvRes.ok) {
          const errData = await csvRes.json().catch(() => ({}));
          throw new Error(errData.detail || `HTTP ${csvRes.status}`);
        }
        const csvBlob = await csvRes.blob();
        const filename = `buyhatke_live_clicks_${fromDate}_to_${uptoDate}.csv`;
        const liveFile = new File([csvBlob], filename, { type: "text/csv" });

        // Update internalClicksFile state seamlessly
        internalClicksFile = liveFile;
        FileStore.setFile("internal_clicks", liveFile);
        try {
          sessionStorage.setItem("affiliate_clicks_info", JSON.stringify({ name: filename, size: csvBlob.size }));
        } catch (e) {}

        // Inspect file dates for mismatch checking
        inspectClicksFileDates(liveFile);

        // Update upload panel preview as well for transparency
        const clicksFn = document.getElementById("clicks-filename");
        const clicksFs = document.getElementById("clicks-filesize");
        const clicksPrompt = document.getElementById("clicks-prompt");
        const clicksPreview = document.getElementById("clicks-preview");
        if (clicksFn) clicksFn.textContent = filename;
        if (clicksFs) clicksFs.textContent = formatBytes(csvBlob.size);
        if (clicksPrompt) clicksPrompt.classList.add("hidden");
        if (clicksPreview) clicksPreview.classList.remove("hidden");

        // 2. Fetch stats for live UI chip feedback
        const statsRes = await fetch(`/api/internal-clicks/stats?start_date=${encodeURIComponent(fromDate)}&end_date=${encodeURIComponent(uptoDate)}&page_size=1000`);
        if (statsRes.ok) {
          const statsData = await statsRes.json();
          const totals = statsData.data?.totals || {};
          const rows = statsData.data?.rows || [];
          const totalClicks = totals.internal_clicks || 0;

          if (totalLabel) {
            const scopeLabel = range.isCustom ? `${fromDate} to ${uptoDate} (${range.days} Days)` : `${range.label} (${fromDate} to ${uptoDate})`;
            totalLabel.textContent = `✅ ${totalClicks.toLocaleString()} internal clicks loaded for ${scopeLabel}`;
          }

          if (topPreview) {
            // Group by brand to show top 5
            const brandMap = new Map();
            rows.forEach((r) => {
              const b = r.website_name || "Direct";
              const c = r.internal_clicks || 0;
              brandMap.set(b, (brandMap.get(b) || 0) + c);
            });
            const sortedBrands = Array.from(brandMap.entries()).sort((a, b) => b[1] - a[1]).slice(0, 5);

            topPreview.innerHTML = sortedBrands
              .map(([bName, bClicks]) => {
                const clickFmt = bClicks >= 1000000 ? `${(bClicks / 1000000).toFixed(2)}M` : (bClicks >= 1000 ? `${(bClicks / 1000).toFixed(0)}k` : bClicks);
                return `<span class="px-2 py-0.5 rounded-md bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300 border border-emerald-300 dark:border-emerald-800 font-semibold">${escapeHtml(bName)}: ${clickFmt}</span>`;
              })
              .join("");
          }
        }

        if (statusBox) statusBox.classList.remove("hidden");

      } catch (err) {
        alert("Buyhatke Live Clicks API Error: " + err.message);
      } finally {
        btnFetch.disabled = false;
        btnFetch.innerHTML = origBtnHtml;
      }
    });
  }

  // Clear live clicks
  if (btnClearLive) {
    btnClearLive.addEventListener("click", () => {
      internalClicksFile = null;
      if (statusBox) statusBox.classList.add("hidden");
      sessionStorage.removeItem("affiliate_clicks_info");
      FileStore.removeFile("internal_clicks");
      inspectClicksFileDates(null);
      const clicksPrompt = document.getElementById("clicks-prompt");
      const clicksPreview = document.getElementById("clicks-preview");
      if (clicksPrompt) clicksPrompt.classList.remove("hidden");
      if (clicksPreview) clicksPreview.classList.add("hidden");
    });
  }
}

let internalClicksFileDates = null;

function inspectClicksFileDates(file) {
  const badgeDates = document.getElementById("clicks-file-dates");
  const mismatchBanner = document.getElementById("clicks-date-mismatch-banner");

  if (!file) {
    internalClicksFileDates = null;
    if (badgeDates) {
      badgeDates.classList.add("hidden");
      badgeDates.textContent = "";
    }
    if (mismatchBanner) mismatchBanner.classList.add("hidden");
    return;
  }

  // Read first 256KB to detect date column & min/max dates
  const slice = file.slice(0, 262144);
  const reader = new FileReader();
  reader.onload = function (e) {
    try {
      const text = e.target.result;
      const lines = text.split(/\r?\n/).filter((l) => l.trim().length > 0);
      if (lines.length < 2) return;

      const headers = lines[0]
        .split(",")
        .map((h) => h.trim().replace(/^["']|["']$/g, "").toLowerCase());
      const dateColIdx = headers.findIndex(
        (h) =>
          h === "date" ||
          h === "dates" ||
          h.includes("click date") ||
          h.includes("day date") ||
          h.includes("order date") ||
          h.includes("transaction date") ||
          h.includes("tracking date")
      );

      if (dateColIdx === -1) {
        internalClicksFileDates = null;
        if (badgeDates) badgeDates.classList.add("hidden");
        if (mismatchBanner) mismatchBanner.classList.add("hidden");
        return;
      }

      const parsedDates = [];
      for (let i = 1; i < lines.length; i++) {
        const row = lines[i].split(",");
        if (row.length > dateColIdx) {
          const raw = row[dateColIdx].trim().replace(/^["']|["']$/g, "");
          if (!raw) continue;
          if (/^\d{4}-\d{2}-\d{2}/.test(raw)) {
            parsedDates.push(raw.substring(0, 10));
          } else if (/^\d{1,2}[-/]\d{1,2}[-/]\d{4}/.test(raw)) {
            const parts = raw.split(/[-/]/);
            if (parts[2].length === 4) {
              const y = parts[2];
              const m = parts[1].padStart(2, "0");
              const d = parts[0].padStart(2, "0");
              parsedDates.push(`${y}-${m}-${d}`);
            }
          }
        }
      }

      if (parsedDates.length === 0) {
        internalClicksFileDates = null;
        if (badgeDates) badgeDates.classList.add("hidden");
        if (mismatchBanner) mismatchBanner.classList.add("hidden");
        return;
      }

      parsedDates.sort();
      const minDate = parsedDates[0];
      const maxDate = parsedDates[parsedDates.length - 1];
      internalClicksFileDates = { minDate, maxDate };

      if (badgeDates) {
        badgeDates.textContent = `📅 ${minDate} to ${maxDate}`;
        badgeDates.classList.remove("hidden");
      }

      checkDateRangeOverlap();
    } catch (err) {
      console.warn("Date inspection notice:", err);
    }
  };
  reader.readAsText(slice);
}

function checkDateRangeOverlap() {
  const mismatchBanner = document.getElementById("clicks-date-mismatch-banner");
  const mismatchDesc = document.getElementById("clicks-mismatch-desc");
  const btnSync = document.getElementById("btn-sync-sheet-dates");

  if (!internalClicksFileDates || !mismatchBanner) return;

  const { start_date, end_date } = getSelectedDateRange();
  const { minDate, maxDate } = internalClicksFileDates;

  // Check overlap: max(start1, start2) <= min(end1, end2)
  const hasOverlap = start_date <= maxDate && end_date >= minDate;

  if (!hasOverlap) {
    if (mismatchDesc) {
      mismatchDesc.innerHTML = `Sheet contains data from <strong class="underline">${minDate} to ${maxDate}</strong>, but your active filter is <strong>${start_date} to ${end_date}</strong>. Running now will result in 0 clicks.`;
    }
    mismatchBanner.classList.remove("hidden");
    if (btnSync) {
      btnSync.onclick = () => {
        if (dateRangePreset) dateRangePreset.value = "custom";
        if (customDateInputs) customDateInputs.classList.remove("hidden");
        if (inputDateStart) inputDateStart.value = minDate;
        if (inputDateEnd) inputDateEnd.value = maxDate;
        updateDateRangeUI();
        mismatchBanner.classList.add("hidden");
      };
    }
  } else {
    mismatchBanner.classList.add("hidden");
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

  if (inputDateStart) {
    inputDateStart.addEventListener("input", updateDateRangeUI);
    inputDateStart.addEventListener("change", updateDateRangeUI);
  }
  if (inputDateEnd) {
    inputDateEnd.addEventListener("input", updateDateRangeUI);
    inputDateEnd.addEventListener("change", updateDateRangeUI);
  }

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

  if (btnLoadDemo) {
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
  }

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

  const btnResetMaster = document.getElementById("btn-reset-master-table");
  if (btnResetMaster) {
    btnResetMaster.addEventListener("click", () => {
      sessionStorage.removeItem("affiliate_master_data");
      sessionStorage.removeItem("affiliate_summary");
      sessionStorage.removeItem("affiliate_analytics_data");
      sessionStorage.removeItem("affiliate_analytics_summary");
      currentMasterData = [];
      currentSummary = {};
      const secKpis = document.getElementById("section-kpis");
      const secResults = document.getElementById("section-results");
      const secLogs = document.getElementById("section-logs");
      if (secKpis) secKpis.classList.add("hidden");
      if (secResults) secResults.classList.add("hidden");
      if (secLogs) secLogs.classList.add("hidden");
      alert("Table cache reset! You can now run the ETL Engine fresh.");
    });
  }
}

let currentReportId = null;

function triggerExportExcel() {
  const rows = (currentRenderedRows && currentRenderedRows.length) ? currentRenderedRows : currentMasterData;
  if (!rows.length) return;
  fetch("/api/export/excel", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(rows),
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
  const rows = (currentRenderedRows && currentRenderedRows.length) ? currentRenderedRows : currentMasterData;
  if (!rows.length) return;
  fetch("/api/export/csv", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(rows),
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
  const rows = (currentRenderedRows && currentRenderedRows.length) ? currentRenderedRows : currentMasterData;
  if (!rows.length) return;
  const headers = [
    "WEBSITE / BRAND",
    "AFFILIATE NETWORK",
    "SUM of INTERNAL CLICKS",
    "Revenue",
    "RPCs",
  ];
  let tsv = headers.join("\t") + "\n";
  rows.forEach((row) => {
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
    // 1. Fetch from server
    let serverReports = [];
    try {
      const res = await fetch("/api/reports");
      if (res.ok) {
        const json = await res.json();
        serverReports = json.reports || [];
      }
    } catch (e) {
      console.warn("Server reports fetch warning:", e);
    }

    // 2. Fetch from client persistent storage (IndexedDB + localStorage fallback)
    let localReports = [];
    try {
      localReports = await ReportStore.getAllReports();
    } catch (e) {
      console.warn("Local reports fetch warning:", e);
    }

    // 3. Merge seamlessly (deduplicate by id, prefer newest)
    const mergedMap = new Map();
    serverReports.forEach((r) => mergedMap.set(r.id, r));
    localReports.forEach((r) => {
      if (!mergedMap.has(r.id)) {
        mergedMap.set(r.id, r);
        // Sync back to backend so server also has it
        try {
          fetch("/api/reports", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(r),
          });
        } catch (syncErr) {}
      } else {
        const existing = mergedMap.get(r.id);
        if (r.created_at && (!existing.created_at || r.created_at > existing.created_at)) {
          mergedMap.set(r.id, r);
        }
      }
    });

    const reports = Array.from(mergedMap.values()).sort((a, b) => {
      return (b.created_at || "").localeCompare(a.created_at || "");
    });

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
                      ${rep.days_count || 0} ${Number(rep.days_count) === 1 ? "Day" : "Days"} Active • Saved ${createdDate}
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
    let report = null;
    try {
      const res = await fetch(`/api/reports/${encodeURIComponent(reportId)}`);
      if (res.ok) {
        report = await res.json();
      }
    } catch (e) {
      console.warn("Server report fetch failed, attempting local ReportStore:", e);
    }

    // Fallback to local browser storage if server doesn't have it (e.g. Render restart)
    if (!report || !report.data || report.data.length === 0) {
      report = await ReportStore.getReport(reportId);
    }

    if (!report) throw new Error("Report not found on server or in local browser storage.");

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
    applyTableFiltersAndSort();
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
    await fetch(`/api/reports/${encodeURIComponent(reportId)}`, {
      method: "DELETE",
    });
  } catch (err) {}
  await ReportStore.deleteReport(reportId);
  await loadSavedReports();
  if (currentReportId === reportId) {
    switchToView("master", true);
  }
}

// SPA Routing and View Management (Zero Page Reload)
function switchToView(viewName, pushHistory = true, reportId = null) {
  const viewMaster = document.getElementById("view-master");
  const viewReport = document.getElementById("view-report");
  const viewAnalytics = document.getElementById("view-analytics");
  const viewCampaigns = document.getElementById("view-campaigns");
  const viewLive = document.getElementById("view-live");
  const headerMaster = document.getElementById("header-master-nav");
  const headerAnalytics = document.getElementById("header-analytics-nav");
  const headerCampaigns = document.getElementById("header-campaigns-nav");
  const headerLive = document.getElementById("header-live-nav");

  // Keep route class in sync on <html> for CSS isolation
  document.documentElement.classList.remove("route-campaigns", "route-analytics", "route-report", "route-master", "route-live");
  document.documentElement.classList.add(`route-${viewName}`);

  if (viewName === "live") {
    if (viewMaster) viewMaster.classList.add("hidden");
    if (viewReport) viewReport.classList.add("hidden");
    if (viewAnalytics) viewAnalytics.classList.add("hidden");
    if (viewCampaigns) viewCampaigns.classList.add("hidden");
    if (headerMaster) headerMaster.classList.add("hidden");
    if (headerAnalytics) headerAnalytics.classList.add("hidden");
    if (headerCampaigns) headerCampaigns.classList.add("hidden");

    if (viewLive) viewLive.classList.remove("hidden");
    if (headerLive) headerLive.classList.remove("hidden");

    if (pushHistory) {
      history.pushState({ view: "live" }, "", "/live");
    }

    initLiveDashboard();
    window.scrollTo({ top: 0, behavior: "smooth" });
  } else if (viewName === "campaigns") {
    if (viewMaster) viewMaster.classList.add("hidden");
    if (viewReport) viewReport.classList.add("hidden");
    if (viewAnalytics) viewAnalytics.classList.add("hidden");
    if (viewLive) viewLive.classList.add("hidden");
    if (headerMaster) headerMaster.classList.add("hidden");
    if (headerAnalytics) headerAnalytics.classList.add("hidden");
    if (headerLive) headerLive.classList.add("hidden");

    if (viewCampaigns) viewCampaigns.classList.remove("hidden");
    if (headerCampaigns) headerCampaigns.classList.remove("hidden");

    if (pushHistory) {
      history.pushState({ view: "campaigns" }, "", "/campaigns");
    }

    if (window.initCampaignFinder) {
      window.initCampaignFinder();
    }
    window.scrollTo({ top: 0, behavior: "smooth" });
  } else if (viewName === "analytics") {
    if (viewMaster) viewMaster.classList.add("hidden");
    if (viewReport) viewReport.classList.add("hidden");
    if (viewCampaigns) viewCampaigns.classList.add("hidden");
    if (viewLive) viewLive.classList.add("hidden");
    if (headerMaster) headerMaster.classList.add("hidden");
    if (headerCampaigns) headerCampaigns.classList.add("hidden");
    if (headerLive) headerLive.classList.add("hidden");

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
    if (viewCampaigns) viewCampaigns.classList.add("hidden");
    if (viewLive) viewLive.classList.add("hidden");
    if (headerAnalytics) headerAnalytics.classList.add("hidden");
    if (headerCampaigns) headerCampaigns.classList.add("hidden");
    if (headerLive) headerLive.classList.add("hidden");

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
    if (viewCampaigns) viewCampaigns.classList.add("hidden");
    if (headerCampaigns) headerCampaigns.classList.add("hidden");
    if (viewLive) viewLive.classList.add("hidden");
    if (headerLive) headerLive.classList.add("hidden");
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

let liveRpcChartInstance = null;

async function initLiveDashboard(forceRefresh = false) {
  const chartCanvas = document.getElementById("chart-live-rpc");
  const alertsContainer = document.getElementById("live-alerts-container");
  const merchantsTableBody = document.getElementById("live-merchants-table-body");
  const syncIndicator = document.getElementById("live-sync-indicator");
  const btnRefreshLive = document.getElementById("btn-refresh-live");
  const btnRefreshLiveStream = document.getElementById("btn-refresh-live-stream");

  if (forceRefresh) {
    if (btnRefreshLiveStream) {
      btnRefreshLiveStream.disabled = true;
      btnRefreshLiveStream.classList.add("opacity-75");
      btnRefreshLiveStream.innerHTML = '<i class="ph-bold ph-arrows-clockwise text-xs animate-spin text-amber-500"></i><span>Ingesting 7 Networks...</span>';
    }
    if (btnRefreshLive) {
      btnRefreshLive.disabled = true;
      btnRefreshLive.classList.add("opacity-75");
      btnRefreshLive.innerHTML = '<i class="ph-bold ph-arrows-clockwise text-sm text-red-500 animate-spin"></i><span>Ingesting...</span>';
    }
    if (syncIndicator) {
      syncIndicator.innerHTML = '<span class="w-2 h-2 rounded-full bg-amber-400 animate-spin"></span><span>⚡ Ingesting Live Networks & Buyhatke Clicks...</span>';
    }
  } else {
    if (syncIndicator) {
      syncIndicator.innerHTML = '<span class="w-2 h-2 rounded-full bg-amber-400 animate-spin"></span><span>Syncing Live Telemetry...</span>';
    }
  }

  try {
    let data;
    if (forceRefresh) {
      // ⚡ Powerful autonomous live ingest: triggers all 7 affiliate network bots and Buyhatke clicks concurrently
      const res = await fetch("/api/live/ingest-autonomous?lag_days=6", { method: "POST" });
      if (!res.ok) throw new Error("Autonomous Live Ingest returned status " + res.status);
      data = await res.json();
    } else {
      const res = await fetch("/api/live/rpc-timeseries?lag_days=6");
      if (!res.ok) throw new Error("Failed to load live RPC timeseries");
      data = await res.json();
    }
    if (!data.success) throw new Error(data.error || "Unknown server error");

    const summary = data.summary || {};
    const timeline = data.timeline || [];
    const alerts = data.alerts || [];
    const merchants = data.top_merchants_today || [];

    // 0. Update Trailing Live Window Badge & Legend
    const elWindowText = document.getElementById("live-chart-window-text");
    if (elWindowText && data.window_label) {
      elWindowText.textContent = `📅 ${data.window_label} (Rolling 30D Live)`;
    }

    const elPeakLegend = document.getElementById("live-chart-peak-legend");
    if (elPeakLegend && summary.peak_day) {
      elPeakLegend.innerHTML = `<strong>Peak:</strong> ${summary.peak_day.short_date} • ${summary.peak_day.note} (₹${summary.peak_day.rpc.toFixed(4)})`;
    }

    // 1. Update KPI Hero Cards
    const elAvgRpc = document.getElementById("live-kpi-avg-rpc");
    const elRpcRange = document.getElementById("live-kpi-rpc-range");
    const elPeakRpc = document.getElementById("live-kpi-peak-rpc");
    const elPeakDesc = document.getElementById("live-kpi-peak-desc");
    const elLowestRpc = document.getElementById("live-kpi-lowest-rpc");
    const elLowestDesc = document.getElementById("live-kpi-lowest-desc");
    const elTotalVol = document.getElementById("live-kpi-total-volume");
    const elTotalRev = document.getElementById("live-kpi-total-rev");

    if (elAvgRpc) elAvgRpc.textContent = `₹${(summary.avg_rpc || 0).toFixed(4)}`;
    if (elRpcRange && summary.lowest_day && summary.peak_day) {
      elRpcRange.innerHTML = `Daily Range: <span class="font-mono font-semibold text-slate-700 dark:text-slate-200">₹${summary.lowest_day.rpc.toFixed(4)} – ₹${summary.peak_day.rpc.toFixed(4)}</span>`;
    }
    if (elPeakRpc && summary.peak_day) elPeakRpc.textContent = `₹${summary.peak_day.rpc.toFixed(4)}`;
    if (elPeakDesc && summary.peak_day) {
      elPeakDesc.innerHTML = `<strong class="font-semibold text-emerald-700 dark:text-emerald-300">${summary.peak_day.short_date}</strong> • ${summary.peak_day.note} (₹${(summary.peak_day.revenue / 1000).toFixed(1)}k Rev)`;
    }
    if (elLowestRpc && summary.lowest_day) elLowestRpc.textContent = `₹${summary.lowest_day.rpc.toFixed(4)}`;
    if (elLowestDesc && summary.lowest_day) {
      elLowestDesc.innerHTML = `<strong class="font-semibold text-amber-700 dark:text-amber-300">${summary.lowest_day.short_date}</strong> • ${summary.lowest_day.note} (₹${(summary.lowest_day.revenue / 1000).toFixed(1)}k Rev)`;
    }
    if (elTotalVol) elTotalVol.textContent = `${((summary.total_clicks || 0) / 1000000).toFixed(2)}M`;
    if (elTotalRev) elTotalRev.innerHTML = `Net Revenue: <span class="font-mono font-bold text-emerald-600 dark:text-emerald-400">₹${Math.round(summary.total_revenue || 0).toLocaleString()}</span>`;

    // 2. Render Beautiful Daywise RPC Chart (Spline Curve with Ups & Downs)
    if (chartCanvas && typeof Chart !== "undefined") {
      if (liveRpcChartInstance) {
        liveRpcChartInstance.destroy();
      }

      const isDarkMode = document.documentElement.classList.contains("dark");
      const gridColor = isDarkMode ? "rgba(255, 255, 255, 0.06)" : "rgba(0, 0, 0, 0.05)";
      const textColor = isDarkMode ? "#94a3b8" : "#64748b";

      const ctx = chartCanvas.getContext("2d");
      const gradient = ctx.createLinearGradient(0, 0, 0, 320);
      gradient.addColorStop(0, "rgba(99, 102, 241, 0.40)");
      gradient.addColorStop(0.5, "rgba(16, 185, 129, 0.18)");
      gradient.addColorStop(1, "rgba(99, 102, 241, 0.0)");

      const labels = timeline.map((p) => p.short_date);
      const rpcData = timeline.map((p) => p.net_rpc);

      const peakDate = summary.peak_day?.date;
      const lowestDate = summary.lowest_day?.date;

      const pointBgColors = timeline.map((pt) => {
        if (peakDate && pt.date === peakDate) return "#10b981"; // Emerald for peak
        if (lowestDate && pt.date === lowestDate) return "#f59e0b"; // Amber for lowest
        return "#6366f1"; // Indigo default
      });

      const pointRadii = timeline.map((pt) => {
        if ((peakDate && pt.date === peakDate) || (lowestDate && pt.date === lowestDate)) return 6;
        return 3;
      });

      liveRpcChartInstance = new Chart(ctx, {
        type: "line",
        data: {
          labels: labels,
          datasets: [
            {
              label: "Net RPC (₹ per Click)",
              data: rpcData,
              borderColor: "#6366f1",
              borderWidth: 2.5,
              backgroundColor: gradient,
              fill: true,
              tension: 0.38,
              pointBackgroundColor: pointBgColors,
              pointBorderColor: isDarkMode ? "#0d1424" : "#ffffff",
              pointBorderWidth: 2,
              pointRadius: pointRadii,
              pointHoverRadius: 8,
              pointHoverBackgroundColor: "#6366f1",
              pointHoverBorderColor: "#ffffff",
              pointHoverBorderWidth: 2.5,
            },
          ],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          interaction: {
            mode: "index",
            intersect: false,
          },
          plugins: {
            legend: {
              display: false,
            },
            tooltip: {
              backgroundColor: isDarkMode ? "#0d1424" : "#ffffff",
              titleColor: isDarkMode ? "#f8fafc" : "#0f172a",
              bodyColor: isDarkMode ? "#cbd5e1" : "#334155",
              borderColor: isDarkMode ? "#334155" : "#e2e8f0",
              borderWidth: 1,
              padding: 12,
              boxPadding: 4,
              usePointStyle: true,
              callbacks: {
                title: function (context) {
                  const idx = context[0].dataIndex;
                  const pt = timeline[idx];
                  return `${pt.weekday}, ${pt.date}`;
                },
                label: function (context) {
                  const idx = context.dataIndex;
                  const pt = timeline[idx];
                  const chgSign = pt.change_pct >= 0 ? "+" : "";
                  return [
                    ` ⚡ Net RPC: ₹${pt.net_rpc.toFixed(4)} (${chgSign}${pt.change_pct}% vs prev)`,
                    ` 💰 Revenue: ₹${Math.round(pt.revenue).toLocaleString()}`,
                    ` 👆 Clicks: ${pt.clicks.toLocaleString()}`,
                  ];
                },
              },
            },
          },
          scales: {
            x: {
              grid: {
                color: gridColor,
                drawBorder: false,
              },
              ticks: {
                color: textColor,
                font: { size: 10, weight: 500 },
                maxRotation: 0,
                autoSkip: true,
                maxTicksLimit: 12,
              },
            },
            y: {
              grid: {
                color: gridColor,
                drawBorder: false,
              },
              ticks: {
                color: textColor,
                font: { size: 10, weight: 600 },
                callback: function (value) {
                  return "₹" + Number(value).toFixed(3);
                },
              },
            },
          },
        },
      });
    }

    // 3. Render Real-Time Anomaly & Downfall Alerts
    if (alertsContainer) {
      alertsContainer.innerHTML = alerts
        .map((a) => {
          const isCritical = a.severity === "critical";
          const isWarning = a.severity === "warning";
          const borderCls = isCritical
            ? "border-red-300 dark:border-red-800/80 bg-red-50/40 dark:bg-red-950/20"
            : isWarning
            ? "border-amber-300 dark:border-amber-800/80 bg-amber-50/40 dark:bg-amber-950/20"
            : "border-emerald-300 dark:border-emerald-800/80 bg-emerald-50/40 dark:bg-emerald-950/20";
          const badgeCls = isCritical
            ? "bg-red-100 dark:bg-red-900/60 text-red-700 dark:text-red-300"
            : isWarning
            ? "bg-amber-100 dark:bg-amber-900/60 text-amber-700 dark:text-amber-300"
            : "bg-emerald-100 dark:bg-emerald-900/60 text-emerald-700 dark:text-emerald-300";
          const icon = isCritical
            ? "ph-warning-octagon text-red-600 dark:text-red-400"
            : isWarning
            ? "ph-warning text-amber-600 dark:text-amber-400"
            : "ph-trend-up text-emerald-600 dark:text-emerald-400";

          return `
            <div class="p-4 rounded-2xl border ${borderCls} flex flex-col justify-between space-y-3 transition hover:shadow-sm">
              <div class="space-y-1.5">
                <div class="flex items-center justify-between">
                  <span class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md text-[10px] font-bold uppercase ${badgeCls}">
                    <i class="ph-bold ${icon}"></i>
                    <span>${escapeHtml(a.severity)}</span>
                  </span>
                  <span class="text-[10px] text-slate-400 font-medium">${escapeHtml(a.timestamp)}</span>
                </div>
                <h4 class="text-xs font-bold text-slate-900 dark:text-white leading-tight">
                  ${escapeHtml(a.title)}
                </h4>
                <p class="text-[11px] text-slate-600 dark:text-slate-300 leading-relaxed">
                  ${escapeHtml(a.desc)}
                </p>
              </div>
              <div class="pt-2 border-t border-slate-200/50 dark:border-slate-800/60 flex items-center justify-between text-[11px]">
                <span class="font-bold text-slate-700 dark:text-slate-300 font-mono">${escapeHtml(a.impact)}</span>
                <span class="text-indigo-600 dark:text-indigo-400 font-semibold">
                  ${escapeHtml(a.brand)} (${escapeHtml(a.network)})
                </span>
              </div>
            </div>
          `;
        })
        .join("");
    }

    // 4. Render Today's Live Merchant Table (Collective Brand Matrix)
    const elMerchantBadge = document.getElementById("live-merchant-date-badge");
    if (elMerchantBadge && timeline.length > 0) {
      const lastPoint = timeline[timeline.length - 1];
      elMerchantBadge.textContent = `📅 Latest Audited Day • ${lastPoint.short_date}, 2026`;
    }

    if (merchantsTableBody) {
      merchantsTableBody.innerHTML = merchants
        .map((m) => {
          const isCrit = m.health === "critical";
          const isWarn = m.health === "warning";
          const hasArbitrage = m.splits && m.splits.length > 1 && m.splits.some((s) => s.rpc >= 0.2) && m.splits.some((s) => s.rpc > 0 && s.rpc < 0.1);

          const statusBadge = isCrit
            ? '<span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-red-100 dark:bg-red-900/60 text-red-700 dark:text-red-300 flex items-center justify-center gap-1"><span class="w-1.5 h-1.5 rounded-full bg-red-500 animate-ping"></span>Zero Attribution</span>'
            : isWarn
            ? '<span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-100 dark:bg-amber-900/60 text-amber-700 dark:text-amber-300 flex items-center justify-center gap-1">Downfall</span>'
            : hasArbitrage
            ? '<span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-purple-100 dark:bg-purple-900/60 text-purple-700 dark:text-purple-300 flex items-center justify-center gap-1">🚀 Arbitrage</span>'
            : '<span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 dark:bg-emerald-900/60 text-emerald-700 dark:text-emerald-300 flex items-center justify-center gap-1">🟢 Normal</span>';

          const chgCls = m.change && m.change.startsWith("+")
            ? "text-emerald-600 dark:text-emerald-400 font-bold"
            : m.change && m.change.startsWith("-")
            ? "text-red-600 dark:text-red-400 font-bold"
            : "text-slate-500 font-medium";

          const initial = (m.brand || "M").charAt(0).toUpperCase();

          const splitsHtml = (m.splits && m.splits.length > 0)
            ? m.splits.map((s) => `
                <span class="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-medium bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-700/60" title="${escapeHtml(s.network)}: ${s.clicks.toLocaleString()} clicks (₹${s.revenue.toLocaleString()})">
                  <span class="font-semibold">${escapeHtml(s.network)}</span>
                  <span class="text-indigo-600 dark:text-indigo-400 font-bold">${s.share_pct}%</span>
                </span>
              `).join(" ")
            : `<span class="px-2 py-0.5 rounded-md bg-slate-100 dark:bg-slate-800 text-[11px] font-semibold text-slate-700 dark:text-slate-300">${escapeHtml(m.network)}</span>`;

          return `
            <tr class="hover:bg-slate-50/60 dark:hover:bg-slate-800/40 transition">
              <td class="py-3 px-4 font-sans font-bold text-slate-800 dark:text-slate-100 flex items-center space-x-2">
                <span class="w-6 h-6 rounded-lg bg-indigo-50 dark:bg-indigo-950/60 text-indigo-600 dark:text-indigo-400 flex items-center justify-center font-bold text-[10px]">
                  ${initial}
                </span>
                <span>${escapeHtml(m.brand)}</span>
              </td>
              <td class="py-3 px-4 font-sans">
                <div class="flex flex-wrap items-center gap-1">
                  ${splitsHtml}
                </div>
              </td>
              <td class="py-3 px-4 text-right font-bold text-slate-800 dark:text-slate-200">${m.clicks.toLocaleString()}</td>
              <td class="py-3 px-4 text-right font-bold ${m.revenue > 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-slate-400'}">₹${m.revenue.toLocaleString()}</td>
              <td class="py-3 px-4 text-right font-black ${isCrit ? 'text-red-600 dark:text-red-400' : (m.rpc > 0 ? 'text-slate-900 dark:text-white' : 'text-slate-400')}">₹${m.rpc.toFixed(4)}</td>
              <td class="py-3 px-4 text-right text-slate-500 dark:text-slate-400">₹${m.baseline_rpc.toFixed(4)}</td>
              <td class="py-3 px-4 text-right ${chgCls}">${escapeHtml(m.change || '0%')}</td>
              <td class="py-3 px-4 text-center font-sans">${statusBadge}</td>
            </tr>
          `;
        })
        .join("");
    }

    if (syncIndicator) {
      syncIndicator.innerHTML = '<span class="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span><span>Live Stream 100% Synced</span>';
    }

  } catch (err) {
    console.error("Live dashboard init error:", err);
    if (syncIndicator) {
      syncIndicator.innerHTML = '<span class="w-2 h-2 rounded-full bg-amber-500"></span><span>Offline Cache</span>';
    }
  } finally {
    if (btnRefreshLiveStream) {
      btnRefreshLiveStream.disabled = false;
      btnRefreshLiveStream.classList.remove("opacity-75");
      btnRefreshLiveStream.innerHTML = '<i class="ph-bold ph-lightning text-xs text-amber-500"></i><span>Live Ingest</span>';
    }
    if (btnRefreshLive) {
      btnRefreshLive.disabled = false;
      btnRefreshLive.classList.remove("opacity-75");
      btnRefreshLive.innerHTML = '<i class="ph-bold ph-arrows-clockwise text-sm text-red-500"></i><span>Refresh</span>';
    }
  }
}

function setupRoutingAndHistory() {
  const btnOpenAnalytics = document.getElementById("btn-open-analytics");
  const navBtnAnalytics = document.getElementById("nav-btn-analytics");
  const navBtnLiveDashboard = document.getElementById("nav-btn-live-dashboard");
  const navBtnCampaignFinder = document.getElementById("nav-btn-campaign-finder");
  const btnBackToMaster = document.getElementById("btn-back-to-master");
  const btnCampaignsBackToMaster = document.getElementById("btn-campaigns-back-to-master");
  const btnLiveBack = document.getElementById("btn-live-back");
  const btnRefreshLive = document.getElementById("btn-refresh-live");
  const btnThemeToggleLive = document.getElementById("btn-theme-toggle-live");
  const btnBackFromReport = document.getElementById("btn-back-from-report");
  const btnReportAnalytics = document.getElementById("btn-report-analytics");
  const btnReportCopyTsv = document.getElementById("btn-report-copy-tsv");
  const btnReportExportExcel = document.getElementById("btn-report-export-excel");
  const btnReportExportCsv = document.getElementById("btn-report-export-csv");
  const btnReportDelete = document.getElementById("btn-report-delete");
  const btnRefreshSaved = document.getElementById("btn-refresh-saved-reports");
  const btnThemeToggleCampaigns = document.getElementById("btn-theme-toggle-campaigns");

  if (navBtnLiveDashboard) {
    navBtnLiveDashboard.addEventListener("click", (e) => {
      e.preventDefault();
      saveAppState();
      switchToView("live", true);
    });
  }

  if (btnLiveBack) {
    btnLiveBack.addEventListener("click", () => {
      switchToView("master", true);
    });
  }

  if (btnRefreshLive) {
    btnRefreshLive.addEventListener("click", () => {
      initLiveDashboard(true);
    });
  }

  const btnRefreshLiveStream = document.getElementById("btn-refresh-live-stream");
  if (btnRefreshLiveStream) {
    btnRefreshLiveStream.addEventListener("click", () => {
      initLiveDashboard(true);
    });
  }

  if (btnThemeToggleLive) {
    btnThemeToggleLive.addEventListener("click", () => {
      const isDark = document.documentElement.classList.toggle("dark");
      localStorage.setItem("theme", isDark ? "dark" : "light");
      updateThemeButtons(isDark);
      if (liveRpcChartInstance) {
        initLiveDashboard();
      }
    });
  }

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

  if (navBtnCampaignFinder) {
    navBtnCampaignFinder.addEventListener("click", (e) => {
      e.preventDefault();
      saveAppState();
      switchToView("campaigns", true);
    });
  }

  if (btnBackToMaster) {
    btnBackToMaster.addEventListener("click", () => {
      switchToView("master", true);
    });
  }

  if (btnCampaignsBackToMaster) {
    btnCampaignsBackToMaster.addEventListener("click", () => {
      switchToView("master", true);
    });
  }

  if (btnThemeToggleCampaigns) {
    btnThemeToggleCampaigns.addEventListener("click", () => {
      const isDark = document.documentElement.classList.toggle("dark");
      localStorage.setItem("theme", isDark ? "dark" : "light");
      updateThemeButtons(isDark);
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
    if (path === "/live" || e.state?.view === "live" || hash === "#live") {
      switchToView("live", false);
    } else if (path === "/campaigns" || e.state?.view === "campaigns" || hash === "#campaigns") {
      switchToView("campaigns", false);
    } else if (path === "/analytics" || e.state?.view === "analytics" || hash === "#analytics") {
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
  if (path === "/live" || hash === "#live") {
    switchToView("live", false);
  } else if (path === "/campaigns" || hash === "#campaigns") {
    switchToView("campaigns", false);
  } else if (path === "/analytics" || hash === "#analytics") {
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
    // Cache version check: Automatically clear stale storage when engine is updated
    const APP_CACHE_VERSION = "2026.11.16.v4";
    if (sessionStorage.getItem("affiliate_app_version") !== APP_CACHE_VERSION) {
      sessionStorage.removeItem("affiliate_master_data");
      sessionStorage.removeItem("affiliate_summary");
      sessionStorage.removeItem("affiliate_analytics_data");
      sessionStorage.removeItem("affiliate_analytics_summary");
      sessionStorage.setItem("affiliate_app_version", APP_CACHE_VERSION);
    }

    const savedData = sessionStorage.getItem("affiliate_master_data");
    const savedSummary = sessionStorage.getItem("affiliate_summary");
    if (savedData) {
      currentMasterData = JSON.parse(savedData);
      currentSummary = savedSummary ? JSON.parse(savedSummary) : {};

      // Defensive check: Purge any stale Dell on CJ erroneous revenue artifact
      if (Array.isArray(currentMasterData)) {
        let purgedAmount = 0;
        currentMasterData = currentMasterData.filter(row => {
          const isDellCj = String(row["WEBSITE / BRAND"]).toLowerCase() === "dell" && String(row["AFFILIATE NETWORK"]).toLowerCase() === "cj";
          if (isDellCj && Number(row["Revenue"]) > 0) {
            purgedAmount += Number(row["Revenue"]);
            return false;
          }
          return true;
        });
        if (purgedAmount > 0 && currentSummary && currentSummary.total_revenue) {
          currentSummary.total_revenue = Math.max(0, currentSummary.total_revenue - purgedAmount);
          sessionStorage.setItem("affiliate_master_data", JSON.stringify(currentMasterData));
          sessionStorage.setItem("affiliate_summary", JSON.stringify(currentSummary));
        }
      }

      renderKPIs(currentSummary);
      applyTableFiltersAndSort();
      if (currentSummary.network_processing_logs) {
        renderProcessingLogs(currentSummary.network_processing_logs);
      }
      const isCampaignsView = window.location.pathname === "/campaigns" || 
                              window.location.hash === "#campaigns" || 
                              document.documentElement.classList.contains("route-campaigns");
      if (!isCampaignsView) {
        const secKpis = document.getElementById("section-kpis");
        const secRes = document.getElementById("section-results");
        if (secKpis) secKpis.classList.remove("hidden");
        if (secRes) secRes.classList.remove("hidden");
        if (currentSummary.network_processing_logs && currentSummary.network_processing_logs.length > 0) {
          const secLogs = document.getElementById("section-logs");
          if (secLogs) secLogs.classList.remove("hidden");
        }
      }
    }

    FileStore.getFile("internal_clicks").then((storedFile) => {
      if (storedFile && storedFile.name) {
        internalClicksFile = storedFile;
        const elName = document.getElementById("clicks-filename");
        const elSize = document.getElementById("clicks-filesize");
        const elPrompt = document.getElementById("clicks-prompt");
        const elPreview = document.getElementById("clicks-preview");
        if (elName) elName.textContent = storedFile.name;
        if (elSize) elSize.textContent = formatBytes(storedFile.size);
        if (elPrompt) elPrompt.classList.add("hidden");
        if (elPreview) elPreview.classList.remove("hidden");
        inspectClicksFileDates(storedFile);
      } else {
        internalClicksFile = null;
        sessionStorage.removeItem("affiliate_clicks_info");
        const elPrompt = document.getElementById("clicks-prompt");
        const elPreview = document.getElementById("clicks-preview");
        if (elPrompt) elPrompt.classList.remove("hidden");
        if (elPreview) elPreview.classList.add("hidden");
        inspectClicksFileDates(null);
      }
    }).catch(() => {
      internalClicksFile = null;
      const elPrompt = document.getElementById("clicks-prompt");
      const elPreview = document.getElementById("clicks-preview");
      if (elPrompt) elPrompt.classList.remove("hidden");
      if (elPreview) elPreview.classList.add("hidden");
      inspectClicksFileDates(null);
    });
  } catch (e) {
    console.warn("Storage restore error:", e);
  }
}

function handleSuccessResults(response) {
  currentMasterData = response.data || [];
  currentSummary = response.summary || {};

  saveAppState();

  renderKPIs(currentSummary);
  applyTableFiltersAndSort();
  renderProcessingLogs(currentSummary.network_processing_logs || []);

  const badgeDates = document.getElementById("badge-table-dates");
  if (badgeDates && currentSummary.date_range) {
    badgeDates.textContent = `📅 Window: ${currentSummary.date_range}`;
  }

  const dateWindow = currentSummary.date_window || {};
  const sDate = currentSummary.start_date || dateWindow.start_date || "2026-10-01";
  const eDate = currentSummary.end_date || dateWindow.end_date || "2026-10-31";
  const days = dateWindow.total_days || (
    sDate && eDate
      ? Math.max(1, Math.round((new Date(eDate) - new Date(sDate)) / (1000 * 60 * 60 * 24)) + 1)
      : 1
  );
  const title = currentSummary.date_range
    ? `${currentSummary.date_range} Run`
    : `${sDate} to ${eDate} Run`;

  currentReportId = `report_${sDate.replace(/-/g, "")}_${eDate.replace(/-/g, "")}`;
  setReportViewMeta(
    title,
    `${sDate} to ${eDate} (${days} ${days === 1 ? 'Day' : 'Days'})`,
    new Date().toISOString()
  );

  // Auto-persist report to browser storage so it is 100% durable across server reboots
  try {
    ReportStore.saveReport({
      id: currentReportId,
      title: title,
      start_date: sDate,
      end_date: eDate,
      days_count: days,
      created_at: new Date().toISOString(),
      usd_to_inr_rate: 94.74,
      summary: currentSummary,
      data: currentMasterData,
    });
  } catch (storeErr) {}

  // Reload saved reports so the tile appears in the grid
  loadSavedReports();

  // Switch to dedicated report page view
  switchToView("report", true, currentReportId);
}

function setupSaveReportModal() {
  const btnSave = document.getElementById("btn-save-current-report");
  const modal = document.getElementById("modal-save-report");
  const btnClose = document.getElementById("btn-close-save-report");
  const btnCancel = document.getElementById("btn-cancel-save-report");
  const btnConfirm = document.getElementById("btn-confirm-save-report");
  const inputTitle = document.getElementById("input-save-report-title");

  const datesEl = document.getElementById("save-report-dates");
  const revEl = document.getElementById("save-report-rev");
  const clicksEl = document.getElementById("save-report-clicks");
  const countEl = document.getElementById("save-report-count");

  function openModal() {
    if (!currentMasterData || currentMasterData.length === 0) {
      alert("No report data available to save. Please run the ETL Engine or load a dataset first.");
      return;
    }
    const dateRange = currentSummary?.date_range || "Reconciliation Period";
    const defaultTitle = `${dateRange} Reconciliation Report`;
    if (inputTitle) inputTitle.value = defaultTitle;

    if (datesEl) datesEl.textContent = dateRange;
    if (revEl) revEl.textContent = formatCurrency(currentSummary?.total_revenue || 0);
    if (clicksEl) clicksEl.textContent = formatNumber(currentSummary?.total_internal_clicks || 0);
    if (countEl) countEl.textContent = `${currentMasterData.length} Campaigns`;

    if (modal) modal.classList.remove("hidden");
  }

  function closeModal() {
    if (modal) modal.classList.add("hidden");
  }

  if (btnSave) btnSave.addEventListener("click", openModal);
  if (btnClose) btnClose.addEventListener("click", closeModal);
  if (btnCancel) btnCancel.addEventListener("click", closeModal);

  if (btnConfirm) {
    btnConfirm.addEventListener("click", async () => {
      const title = (inputTitle && inputTitle.value.trim()) || "Saved Report";
      const sDate = currentSummary?.start_date || "2026-10-01";
      const eDate = currentSummary?.end_date || "2026-10-31";
      const repId = `custom_${sDate.replace(/-/g, "")}_${eDate.replace(/-/g, "")}_${Date.now()}`;

      const reportPayload = {
        id: repId,
        title: title,
        start_date: sDate,
        end_date: eDate,
        days_count: Math.max(1, Math.ceil((new Date(eDate) - new Date(sDate)) / (1000 * 60 * 60 * 24)) + 1),
        created_at: new Date().toISOString(),
        usd_to_inr_rate: 94.74,
        summary: currentSummary || {},
        data: currentMasterData || [],
      };

      btnConfirm.disabled = true;
      btnConfirm.textContent = "Saving...";

      try {
        // 1. Save to local browser storage (IndexedDB + localStorage backup)
        await ReportStore.saveReport(reportPayload);

        // 2. Save to backend API
        try {
          await fetch("/api/reports", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(reportPayload),
          });
        } catch (serverErr) {
          console.warn("Backend save notice:", serverErr);
        }

        closeModal();
        currentReportId = repId;
        await loadSavedReports();
        alert(`✅ Report "${title}" saved successfully! It is permanently stored and available under Saved Reports.`);
      } catch (err) {
        alert("Failed to save report: " + err.message);
      } finally {
        btnConfirm.disabled = false;
        btnConfirm.textContent = "Save Report";
      }
    });
  }
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

let tableSortKey = "default";
let tableFilterPreset = "all";
let tableSearchQuery = "";
let currentRenderedRows = [];

function applyTableFiltersAndSort() {
  if (!Array.isArray(currentMasterData)) return;

  let rows = [...currentMasterData];

  // 1. Text Search Filter
  if (tableSearchQuery) {
    const q = tableSearchQuery.toLowerCase().trim();
    rows = rows.filter((r) => {
      const b = String(r["WEBSITE / BRAND"] || "").toLowerCase();
      const n = String(r["AFFILIATE NETWORK"] || "").toLowerCase();
      return b.includes(q) || n.includes(q);
    });
  }

  // 2. Preset Filter Chips
  if (tableFilterPreset === "revenue") {
    rows = rows.filter((r) => (Number(r["Revenue"]) || 0) > 0);
  } else if (tableFilterPreset === "bleed") {
    rows = rows.filter(
      (r) =>
        (Number(r["SUM of INTERNAL CLICKS"]) || 0) >= 500 &&
        (Number(r["Revenue"]) || 0) <= 0
    );
  } else if (tableFilterPreset === "high-rpc") {
    rows = rows.filter((r) => (Number(r["RPCs"]) || 0) >= 0.10);
  }

  // 3. Sorting
  if (tableSortKey === "rpc-desc") {
    rows.sort((a, b) => (Number(b["RPCs"]) || 0) - (Number(a["RPCs"]) || 0));
  } else if (tableSortKey === "rpc-asc") {
    rows.sort((a, b) => (Number(a["RPCs"]) || 0) - (Number(b["RPCs"]) || 0));
  } else if (tableSortKey === "rev-desc") {
    rows.sort((a, b) => (Number(b["Revenue"]) || 0) - (Number(a["Revenue"]) || 0));
  } else if (tableSortKey === "rev-asc") {
    rows.sort((a, b) => (Number(a["Revenue"]) || 0) - (Number(b["Revenue"]) || 0));
  } else if (tableSortKey === "clicks-desc") {
    rows.sort(
      (a, b) =>
        (Number(b["SUM of INTERNAL CLICKS"]) || 0) -
        (Number(a["SUM of INTERNAL CLICKS"]) || 0)
    );
  } else if (tableSortKey === "clicks-asc") {
    rows.sort(
      (a, b) =>
        (Number(a["SUM of INTERNAL CLICKS"]) || 0) -
        (Number(b["SUM of INTERNAL CLICKS"]) || 0)
    );
  } else if (tableSortKey === "brand-asc") {
    rows.sort((a, b) =>
      String(a["WEBSITE / BRAND"] || "").localeCompare(
        String(b["WEBSITE / BRAND"] || "")
      )
    );
  } else if (tableSortKey === "brand-desc") {
    rows.sort((a, b) =>
      String(b["WEBSITE / BRAND"] || "").localeCompare(
        String(a["WEBSITE / BRAND"] || "")
      )
    );
  } else if (tableSortKey === "network-asc") {
    rows.sort((a, b) =>
      String(a["AFFILIATE NETWORK"] || "").localeCompare(
        String(b["AFFILIATE NETWORK"] || "")
      )
    );
  } else if (tableSortKey === "network-desc") {
    rows.sort((a, b) =>
      String(b["AFFILIATE NETWORK"] || "").localeCompare(
        String(a["AFFILIATE NETWORK"] || "")
      )
    );
  }

  currentRenderedRows = rows;
  updateSortHeaderIndicators();
  renderMasterTable(rows, currentMasterData.length);
}

function updateSortHeaderIndicators() {
  const headers = document.querySelectorAll("th[data-sort-col]");
  headers.forEach((th) => {
    const col = th.getAttribute("data-sort-col");
    const indicator = th.querySelector(".sort-indicator");
    if (!indicator) return;

    const isActive =
      (col === "rpc" && (tableSortKey === "rpc-desc" || tableSortKey === "rpc-asc")) ||
      (col === "revenue" && (tableSortKey === "rev-desc" || tableSortKey === "rev-asc")) ||
      (col === "clicks" && (tableSortKey === "clicks-desc" || tableSortKey === "clicks-asc")) ||
      (col === "brand" && (tableSortKey === "brand-asc" || tableSortKey === "brand-desc")) ||
      (col === "network" && (tableSortKey === "network-asc" || tableSortKey === "network-desc"));

    if (isActive) {
      const isDesc = tableSortKey.endsWith("-desc");
      indicator.textContent = isDesc ? "↓" : "↑";
      indicator.className =
        "sort-indicator text-xs font-bold text-emerald-600 dark:text-emerald-400";
      th.classList.add("text-emerald-600", "dark:text-emerald-400");
    } else {
      indicator.textContent = "↕";
      indicator.className =
        "sort-indicator text-[10px] text-slate-400 dark:text-slate-600";
      th.classList.remove("text-emerald-600", "dark:text-emerald-400");
    }
  });

  const selectSort = document.getElementById("select-table-sort");
  if (selectSort && selectSort.value !== tableSortKey) {
    selectSort.value = tableSortKey;
  }
}

function handleColumnHeaderSort(col) {
  if (col === "original") {
    tableSortKey = "default";
  } else if (col === "rpc") {
    tableSortKey =
      tableSortKey === "rpc-desc"
        ? "rpc-asc"
        : tableSortKey === "rpc-asc"
        ? "default"
        : "rpc-desc";
  } else if (col === "revenue") {
    tableSortKey =
      tableSortKey === "rev-desc"
        ? "rev-asc"
        : tableSortKey === "rev-asc"
        ? "default"
        : "rev-desc";
  } else if (col === "clicks") {
    tableSortKey =
      tableSortKey === "clicks-desc"
        ? "clicks-asc"
        : tableSortKey === "clicks-asc"
        ? "default"
        : "clicks-desc";
  } else if (col === "brand") {
    tableSortKey =
      tableSortKey === "brand-asc"
        ? "brand-desc"
        : tableSortKey === "brand-desc"
        ? "default"
        : "brand-asc";
  } else if (col === "network") {
    tableSortKey =
      tableSortKey === "network-asc"
        ? "network-desc"
        : tableSortKey === "network-desc"
        ? "default"
        : "network-asc";
  }
  applyTableFiltersAndSort();
}

function handleFilterChipClick(filter) {
  tableFilterPreset = filter;
  const chipButtons = document.querySelectorAll(".table-filter-btn");
  chipButtons.forEach((btn) => {
    if (btn.getAttribute("data-filter") === filter) {
      btn.className =
        "table-filter-btn px-2.5 py-1 rounded-lg text-xs font-semibold bg-emerald-600 text-white shadow-2xs transition cursor-pointer";
    } else {
      btn.className =
        "table-filter-btn px-2.5 py-1 rounded-lg text-xs font-medium bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 border border-slate-200 dark:border-slate-700 transition cursor-pointer";
    }
  });
  applyTableFiltersAndSort();
}

function renderMasterTable(rows, totalCount) {
  const tbody = document.getElementById("master-table-body");
  if (!tbody) return;
  tbody.innerHTML = "";

  const countEl = document.getElementById("table-row-count");
  if (countEl) {
    const total = totalCount || (currentMasterData ? currentMasterData.length : rows.length);
    let label = `Showing ${rows.length} of ${total} rows`;
    if (tableFilterPreset !== "all") {
      const filterLabels = {
        revenue: "Revenue > 0",
        bleed: "Click Bleed (Rev = ₹0)",
        "high-rpc": "High RPC (≥ ₹0.10)",
      };
      label += ` • Filter: ${filterLabels[tableFilterPreset] || tableFilterPreset}`;
    }
    if (tableSortKey !== "default") {
      const sortLabels = {
        "rpc-desc": "RPCs (High → Low)",
        "rpc-asc": "RPCs (Low → High)",
        "rev-desc": "Revenue (High → Low)",
        "rev-asc": "Revenue (Low → High)",
        "clicks-desc": "Clicks (High → Low)",
        "clicks-asc": "Clicks (Low → High)",
        "brand-asc": "Brand (A → Z)",
        "brand-desc": "Brand (Z → A)",
        "network-asc": "Network (A → Z)",
        "network-desc": "Network (Z → A)",
      };
      label += ` • Sort: ${sortLabels[tableSortKey] || tableSortKey}`;
    }
    countEl.textContent = label;
  }

  if (rows.length === 0) {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td colspan="6" class="py-8 text-center text-slate-400 dark:text-slate-500 text-xs">
        <i class="ph-bold ph-funnel-x text-2xl mb-1 inline-block text-slate-300 dark:text-slate-600"></i>
        <p class="font-medium">No matching campaigns found</p>
        <p class="text-[11px] mt-0.5 text-slate-400 dark:text-slate-500">Try clearing filters or search query.</p>
      </td>
    `;
    tbody.appendChild(tr);
    return;
  }

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
  if (searchInput) {
    searchInput.addEventListener("input", (e) => {
      tableSearchQuery = e.target.value;
      applyTableFiltersAndSort();
    });
  }

  const selectSort = document.getElementById("select-table-sort");
  if (selectSort) {
    selectSort.addEventListener("change", (e) => {
      tableSortKey = e.target.value;
      applyTableFiltersAndSort();
    });
  }

  const filterChips = document.querySelectorAll(".table-filter-btn");
  filterChips.forEach((btn) => {
    btn.addEventListener("click", () => {
      const f = btn.getAttribute("data-filter");
      handleFilterChipClick(f);
    });
  });

  const sortableHeaders = document.querySelectorAll("th[data-sort-col]");
  sortableHeaders.forEach((th) => {
    th.addEventListener("click", () => {
      const col = th.getAttribute("data-sort-col");
      handleColumnHeaderSort(col);
    });
  });
}

// 5. Aliases Modal Handling
function setupAliasesModal() {
  const modal = document.getElementById("modal-aliases");
  const btnOpen = document.getElementById("btn-open-rules");
  const btnClose = document.getElementById("btn-close-modal");
  const btnSave = document.getElementById("btn-save-alias");
  const listContainer = document.getElementById("aliases-list");

  if (btnOpen) {
    btnOpen.addEventListener("click", () => {
      loadAliases();
      modal.classList.remove("hidden");
    });
  }

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

// =========================================================================
// 6. Universal Affiliate Campaign Finder (Cross-Network Arbitrage Engine)
// =========================================================================

let campaignState = {
  query: "",
  network: "all",
  country: "in",
  category: "all",
  status: "all",
  sort: "epc_desc"
};
let isCampaignFinderInitialized = false;

window.initCampaignFinder = function() {
  if (!isCampaignFinderInitialized) {
    setupCampaignFinderListeners();
    isCampaignFinderInitialized = true;
  }
  fetchCampaignNetworks();
  fetchAndRenderCampaigns();
};

async function fetchCampaignNetworks() {
  try {
    const res = await fetch("/api/campaigns/networks");
    if (res.ok) {
      const networks = await res.json();
      renderNetworkPills(networks);
      const totalAll = networks.find(n => n.id === "all");
      const badge = document.getElementById("catalog-total-badge");
      if (badge && totalAll) {
        badge.textContent = `${totalAll.count} Live Offers`;
      }
    }
  } catch (err) {
    console.error("Error fetching networks summary:", err);
  }
}

function renderNetworkPills(networks) {
  const container = document.getElementById("campaign-network-pills");
  if (!container || !networks || networks.length === 0) return;

  container.innerHTML = "";
  networks.forEach(net => {
    const btn = document.createElement("button");
    btn.type = "button";
    const isActive = campaignState.network === net.id;
    btn.className = `network-pill px-3 py-1.5 text-xs font-semibold rounded-xl transition cursor-pointer border ${
      isActive
        ? "active border-indigo-600 bg-indigo-600 text-white shadow-md shadow-indigo-600/30"
        : "border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/80 text-slate-700 dark:text-slate-200 hover:border-indigo-400 hover:text-indigo-400"
    }`;
    btn.dataset.network = net.id;
    
    let icon = "🌐";
    if (net.id === "cuelinks") icon = "🔗";
    else if (net.id === "cashkaro") icon = "⚡";
    else if (net.id === "cj") icon = "🌟";
    else if (net.id === "admitad") icon = "🛡️";
    else if (net.id === "inrdeals") icon = "₹";

    btn.innerHTML = `${icon} ${escapeHtml(net.name)} <span class="ml-1 opacity-80 font-bold">(${net.count.toLocaleString()})</span>`;
    
    btn.addEventListener("click", () => {
      campaignState.network = net.id;
      syncNetworkControls(net.id);
      fetchAndRenderCampaigns();
    });

    container.appendChild(btn);
  });
}

function syncNetworkControls(netId) {
  // Sync dropdown
  const selectNet = document.getElementById("select-campaign-network");
  if (selectNet && selectNet.value !== netId) {
    selectNet.value = netId;
  }

  // Sync pills
  document.querySelectorAll(".network-pill").forEach(p => {
    if (p.dataset.network === netId) {
      p.classList.add("active", "border-indigo-600", "bg-indigo-600", "text-white", "shadow-md", "shadow-indigo-600/30");
      p.classList.remove("border-slate-200", "dark:border-slate-800", "bg-white", "dark:bg-slate-900/80", "text-slate-700", "dark:text-slate-200");
    } else {
      p.classList.remove("active", "border-indigo-600", "bg-indigo-600", "text-white", "shadow-md", "shadow-indigo-600/30");
      p.classList.add("border-slate-200", "dark:border-slate-800", "bg-white", "dark:bg-slate-900/80", "text-slate-700", "dark:text-slate-200");
    }
  });

  // Sync header badge
  const badge = document.getElementById("active-network-name-badge");
  if (badge) {
    if (netId === "all") {
      badge.textContent = "All Networks (Cuelinks + CashKaro + CJ): Connected 🟢";
    } else if (netId === "cashkaro") {
      badge.textContent = "CashKaro Trackier: Connected 🟢";
    } else if (netId === "cuelinks") {
      badge.textContent = "Cuelinks API v3: Connected 🟢";
    } else if (netId === "cj") {
      badge.textContent = "CJ Affiliate: Connected 🟢";
    } else {
      badge.textContent = `${netId.toUpperCase()}: Connected 🟢`;
    }
  }
}

let campaignDebounceTimer = null;
const campaignClientCache = new Map();

function setupCampaignFinderListeners() {
  const searchInput = document.getElementById("campaign-search-input");
  const btnClear = document.getElementById("btn-clear-campaign-search");
  const btnViewAll = document.getElementById("btn-view-all-campaigns");
  const selectNetwork = document.getElementById("select-campaign-network");
  const selectCountry = document.getElementById("select-campaign-country");
  const selectCat = document.getElementById("select-campaign-category");
  const selectStatus = document.getElementById("select-campaign-status");
  const selectSort = document.getElementById("select-campaign-sort");
  const btnReset = document.getElementById("btn-reset-campaign-filters");
  const btnEmptyReset = document.getElementById("btn-empty-reset");

  if (searchInput) {
    // Instant search on Enter key
    searchInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        clearTimeout(campaignDebounceTimer);
        campaignState.query = e.target.value.trim();
        fetchAndRenderCampaigns();
      }
    });

    // Real-time active typing search (200ms debounce)
    searchInput.addEventListener("input", (e) => {
      campaignState.query = e.target.value.trim();
      if (btnClear) {
        if (campaignState.query.length > 0) {
          btnClear.classList.remove("hidden");
        } else {
          btnClear.classList.add("hidden");
        }
      }
      clearTimeout(campaignDebounceTimer);
      campaignDebounceTimer = setTimeout(() => {
        fetchAndRenderCampaigns();
      }, 200);
    });
  }

  if (btnClear) {
    btnClear.addEventListener("click", () => {
      if (searchInput) searchInput.value = "";
      campaignState.query = "";
      btnClear.classList.add("hidden");
      fetchAndRenderCampaigns();
    });
  }

  if (btnViewAll) {
    btnViewAll.addEventListener("click", () => {
      if (searchInput) searchInput.value = "";
      campaignState.query = "";
      if (btnClear) btnClear.classList.add("hidden");
      fetchAndRenderCampaigns();
    });
  }

  if (selectNetwork) {
    selectNetwork.addEventListener("change", (e) => {
      campaignState.network = e.target.value;
      syncNetworkControls(e.target.value);
      fetchAndRenderCampaigns();
    });
  }

  if (selectCountry) {
    selectCountry.addEventListener("change", (e) => {
      campaignState.country = e.target.value;
      fetchAndRenderCampaigns();
    });
  }

  document.querySelectorAll(".quick-chip").forEach(chip => {
    chip.addEventListener("click", () => {
      const b = chip.dataset.brand;
      if (searchInput) searchInput.value = b;
      campaignState.query = b;
      if (btnClear) btnClear.classList.remove("hidden");
      fetchAndRenderCampaigns();
    });
  });

  if (selectCat) {
    selectCat.addEventListener("change", (e) => {
      campaignState.category = e.target.value;
      fetchAndRenderCampaigns();
    });
  }

  if (selectStatus) {
    selectStatus.addEventListener("change", (e) => {
      campaignState.status = e.target.value;
      fetchAndRenderCampaigns();
    });
  }

  if (selectSort) {
    selectSort.addEventListener("change", (e) => {
      campaignState.sort = e.target.value;
      fetchAndRenderCampaigns();
    });
  }

  const resetAll = () => {
    campaignState = {
      query: "",
      network: "all",
      country: "in",
      category: "all",
      status: "all",
      sort: "epc_desc"
    };
    if (searchInput) searchInput.value = "";
    if (btnClear) btnClear.classList.add("hidden");
    if (selectNetwork) selectNetwork.value = "all";
    if (selectCountry) selectCountry.value = "in";
    if (selectCat) selectCat.value = "all";
    if (selectStatus) selectStatus.value = "all";
    if (selectSort) selectSort.value = "epc_desc";
    syncNetworkControls("all");
    fetchCampaignNetworks();
    fetchAndRenderCampaigns();
  };

  if (btnReset) btnReset.addEventListener("click", resetAll);
  if (btnEmptyReset) btnEmptyReset.addEventListener("click", resetAll);
}

function renderCampaignResults(data) {
  const cardsGrid = document.getElementById("campaign-cards-grid");
  const emptyState = document.getElementById("campaign-empty-state");
  const countLabel = document.getElementById("campaign-results-count");
  const compareCallout = document.getElementById("campaign-compare-callout");
  const compareDesc = document.getElementById("compare-callout-desc");

  if (!cardsGrid) return;
  const results = data.results || [];

  if (countLabel) {
    let netDisplay = "All Networks (Cuelinks + CashKaro + CJ)";
    if (campaignState.network === "cuelinks") netDisplay = "Cuelinks";
    else if (campaignState.network === "cashkaro") netDisplay = "CashKaro";
    else if (campaignState.network === "cj") netDisplay = "CJ Affiliate";
    countLabel.textContent = `Showing ${results.length} live campaigns across ${netDisplay}`;
  }

  // Check for Comparative Arbitrage Winner
  const bestWinner = results.find(r => r.is_best_payout && r.payout_diff_label);
  if (bestWinner && compareCallout && compareDesc) {
    compareCallout.classList.remove("hidden");
    compareDesc.innerHTML = `
      <strong>${escapeHtml(bestWinner.brand_name)}</strong> is active across multiple networks! 
      <span class="text-emerald-400 font-bold">${escapeHtml(bestWinner.network_name)}</span> pays the highest commission at 
      <span class="text-emerald-300 font-extrabold">${escapeHtml(bestWinner.payout_display)}</span> 
      (${escapeHtml(bestWinner.payout_diff_label)}).
    `;
  } else if (compareCallout) {
    compareCallout.classList.add("hidden");
  }

  if (results.length === 0) {
    cardsGrid.innerHTML = "";
    if (emptyState) emptyState.classList.remove("hidden");
    return;
  }

  if (emptyState) emptyState.classList.add("hidden");
  cardsGrid.innerHTML = "";

  results.forEach(c => {
    const card = createCampaignCard(c);
    cardsGrid.appendChild(card);
  });
}

async function fetchAndRenderCampaigns() {
  const cardsGrid = document.getElementById("campaign-cards-grid");
  if (!cardsGrid) return;

  const cacheKey = `${campaignState.query || ""}|${campaignState.network || "all"}|${campaignState.country || "all"}|${campaignState.category || "all"}|${campaignState.status || "all"}|${campaignState.sort || "epc_desc"}`;

  // Instant render from client cache if available (0ms response)
  if (campaignClientCache.has(cacheKey)) {
    renderCampaignResults(campaignClientCache.get(cacheKey));
    return;
  }

  let netSearchLabel = "All Networks (Cuelinks + CashKaro + CJ)";
  if (campaignState.network === "cuelinks") netSearchLabel = "Cuelinks API";
  else if (campaignState.network === "cashkaro") netSearchLabel = "CashKaro Trackier";
  else if (campaignState.network === "cj") netSearchLabel = "CJ Affiliate Lookup API";

  cardsGrid.innerHTML = `
    <div class="col-span-full py-12 text-center text-slate-400">
      <i class="ph ph-spinner animate-spin text-2xl text-sky-500"></i>
      <p class="text-xs mt-2">Searching live ${escapeHtml(netSearchLabel)} campaigns...</p>
    </div>
  `;

  try {
    const params = new URLSearchParams({
      query: campaignState.query || "",
      network: campaignState.network || "all",
      country: campaignState.country || "all",
      category: campaignState.category || "all",
      status: campaignState.status || "all",
      sort: campaignState.sort || "epc_desc"
    });

    const res = await fetch(`/api/campaigns/search?${params.toString()}`);
    if (!res.ok) throw new Error("Search request failed");
    const data = await res.json();
    campaignClientCache.set(cacheKey, data);
    renderCampaignResults(data);

  } catch (err) {
    console.error("Error searching campaigns:", err);
    if (cardsGrid) {
      cardsGrid.innerHTML = `
        <div class="col-span-full py-8 text-center text-rose-500">
          <p class="text-sm font-semibold">Error searching campaigns</p>
          <p class="text-xs mt-1 text-slate-400">${escapeHtml(err.message)}</p>
        </div>
      `;
    }
  }
}

function createCampaignCard(c) {
  const card = document.createElement("div");
  const isBest = Boolean(c.is_best_payout);

  card.className = `metric-card flex flex-col justify-between p-5 rounded-2xl bg-white dark:bg-[#0d1424] border ${
    isBest 
      ? "border-emerald-500/60 shadow-xl shadow-emerald-500/10 ring-1 ring-emerald-500/30" 
      : "border-slate-200 dark:border-slate-800/80 shadow-sm hover:border-indigo-500/40"
  } transition-all duration-200 relative overflow-hidden`;

  // Network badge colors
  let netColorClass = "bg-indigo-500/15 text-indigo-400 border-indigo-500/30";
  const nid = (c.network_id || "").toLowerCase();
  if (nid === "cuelinks") netColorClass = "bg-sky-500/15 text-sky-400 border-sky-500/30";
  else if (nid === "cashkaro") netColorClass = "bg-rose-500/15 text-rose-400 border-rose-500/30";
  else if (nid === "admitad") netColorClass = "bg-emerald-500/15 text-emerald-400 border-emerald-500/30";
  else if (nid === "inrdeals") netColorClass = "bg-purple-500/15 text-purple-400 border-purple-500/30";
  else if (nid === "cj") netColorClass = "bg-amber-500/15 text-amber-400 border-amber-500/30";

  // Status badge
  let statusHtml = '<span class="inline-flex items-center space-x-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-500/15 text-emerald-400 border border-emerald-500/30"><span class="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span><span>Active</span></span>';
  if (c.status === "apply_required") {
    statusHtml = '<span class="inline-flex items-center space-x-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-500/15 text-amber-400 border border-amber-500/30"><span class="w-1.5 h-1.5 rounded-full bg-amber-400"></span><span>Approval Needed</span></span>';
  } else if (c.status === "paused") {
    statusHtml = '<span class="inline-flex items-center space-x-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-rose-500/15 text-rose-400 border border-rose-500/30"><span class="w-1.5 h-1.5 rounded-full bg-rose-400"></span><span>Paused</span></span>';
  }

  // Best payout badge
  let bestBadgeHtml = "";
  if (isBest) {
    bestBadgeHtml = `
      <div class="mb-2">
        <span class="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-[10px] font-black bg-gradient-to-r from-emerald-500/20 to-teal-500/20 text-emerald-400 border border-emerald-500/40 uppercase tracking-wide">
          <span>🏆 Top Payout</span>
          ${c.payout_diff_label ? `<span class="opacity-75 font-normal ml-1">(${escapeHtml(c.payout_diff_label.replace("🏆 ", ""))})</span>` : ""}
        </span>
      </div>
    `;
  }

  const brandInitial = (c.brand_name || "C").charAt(0).toUpperCase();
  const logoHtml = c.image_url && !c.image_url.includes("Placeholder")
    ? `<img src="${escapeHtml(c.image_url)}" alt="${escapeHtml(c.brand_name)}" class="w-9 h-9 rounded-xl object-contain bg-white dark:bg-slate-800 p-1 border border-slate-200 dark:border-slate-700 shrink-0" onerror="this.onerror=null; this.src=''; this.classList.add('hidden');" />`
    : `<div class="w-9 h-9 rounded-xl bg-gradient-to-tr from-sky-600 to-indigo-600 flex items-center justify-center font-bold text-sm text-white shrink-0 border border-sky-500/40">${brandInitial}</div>`;

  const networkName = c.network_name || (nid === "cashkaro" ? "CashKaro" : (nid === "cj" ? "CJ Affiliate" : "Cuelinks"));
  const panelUrl = c.panel_url || (nid === "cashkaro" 
    ? `/api/campaigns/open?network=cashkaro&id=${encodeURIComponent(c.id)}` 
    : (nid === "cj"
      ? `/api/campaigns/open?network=cj&id=${encodeURIComponent(c.id)}`
      : `/api/campaigns/open?network=cuelinks&brand=${encodeURIComponent(c.brand_name)}`));

  const payoutColorClass = isBest 
    ? 'text-emerald-500 dark:text-emerald-400' 
    : (nid === 'cashkaro' ? 'text-rose-500 dark:text-rose-400' : (nid === 'cj' ? 'text-amber-500 dark:text-amber-400' : 'text-sky-600 dark:text-sky-400'));

  const defaultDesc = nid === "cashkaro" 
    ? "Live CashKaro Trackier offer." 
    : (nid === "cj" ? "CJ Affiliate advertiser offer." : "Active Cuelinks v3 campaign offer.");

  const epcPrefix = nid === 'cj' ? '$' : '₹';
  const applyTitle = nid === 'cashkaro' 
    ? 'Request Approval on CashKaro Trackier Portal' 
    : (nid === 'cj' ? 'Join Program on CJ Affiliate Member Portal' : 'Apply on Cuelinks Dashboard');
  const applyText = nid === 'cashkaro' ? 'Request Approval' : (nid === 'cj' ? 'Apply on CJ' : 'Apply on Dashboard');

  card.innerHTML = `
    <div>
      ${bestBadgeHtml}
      
      <!-- Top Card Row: Brand & Network -->
      <div class="flex items-center justify-between gap-2 mb-3">
        <div class="flex items-center space-x-2.5 min-w-0">
          ${logoHtml}
          <div class="truncate">
            <h4 class="text-sm font-bold text-slate-900 dark:text-white truncate" title="${escapeHtml(c.brand_name)}">
              ${escapeHtml(c.brand_name)}
            </h4>
            <span class="text-[11px] text-slate-500 dark:text-slate-400">${escapeHtml(c.category || "General")}</span>
          </div>
        </div>
        <span class="inline-flex items-center px-2 py-0.5 rounded-lg text-[10px] font-bold border uppercase tracking-wide shrink-0 ${netColorClass}">
          ${escapeHtml(networkName)}
        </span>
      </div>

      <!-- Campaign Title & Domain -->
      <p class="text-xs font-semibold text-slate-800 dark:text-slate-200 line-clamp-1 mb-1" title="${escapeHtml(c.campaign_title)}">
        ${escapeHtml(c.campaign_title)}
      </p>
      ${c.domain ? `<p class="text-[11px] text-sky-500 dark:text-sky-400 font-mono mb-3 truncate">${escapeHtml(c.domain)}</p>` : '<div class="mb-3"></div>'}

      <!-- Payout Box -->
      <div class="p-3 rounded-xl bg-slate-50 dark:bg-[#070b14]/80 border ${isBest ? 'border-emerald-500/40 bg-emerald-950/10' : 'border-slate-100 dark:border-slate-800'} mb-3">
        <div class="flex items-center justify-between">
          <div>
            <span class="text-[10px] uppercase font-bold text-slate-400 tracking-wider">Commission Payout</span>
            <div class="text-base sm:text-lg font-black ${payoutColorClass}">
              ${escapeHtml(c.payout_display)}
            </div>
          </div>
          <div>
            ${statusHtml}
          </div>
        </div>
      </div>

      <!-- Description snippet -->
      <p class="text-[11px] text-slate-500 dark:text-slate-400 line-clamp-2 mb-4 leading-relaxed">
        ${escapeHtml(c.description || defaultDesc)}
      </p>

      <!-- Metadata chips -->
      <div class="flex items-center space-x-3 text-[10px] text-slate-400 pb-3 border-b border-slate-100 dark:border-slate-800/80 mb-3">
        <span class="flex items-center space-x-1">
          <i class="ph ph-clock text-xs"></i>
          <span>${c.cookie_days || '30 Days'} Cookie</span>
        </span>
        <span class="flex items-center space-x-1">
          <i class="ph ph-globe text-xs text-slate-400"></i>
          <span>${c.geo || 'India'}</span>
        </span>
        ${c.epc_7d && c.epc_7d !== '0.0' && c.epc_7d !== '0.00' ? `
        <span class="flex items-center space-x-1">
          <i class="ph ph-chart-line-up text-xs text-emerald-400"></i>
          <span>EPC: ${epcPrefix}${c.epc_7d}</span>
        </span>` : ''}
      </div>
    </div>

    <!-- 1-Click Action Buttons -->
    <div class="grid grid-cols-2 gap-2 pt-1">
      <a 
        href="${escapeHtml(panelUrl)}" 
        target="_blank" 
        rel="noopener noreferrer" 
        class="inline-flex items-center justify-center space-x-1.5 py-2 px-2.5 rounded-xl text-[11px] font-bold bg-slate-100 dark:bg-slate-800/90 hover:bg-sky-600 hover:text-white text-slate-800 dark:text-slate-200 border border-slate-200 dark:border-slate-700 transition cursor-pointer text-center"
        title="View verified campaign details on ${escapeHtml(networkName)}"
      >
        <span>View on ${escapeHtml(networkName)}</span>
        <i class="ph-bold ph-arrow-square-out text-xs"></i>
      </a>
      ${c.tracking_url ? `
      <button 
        type="button" 
        onclick="copyCampaignLink(this, '${escapeHtml(c.tracking_url)}')" 
        class="inline-flex items-center justify-center space-x-1.5 py-2 px-2.5 rounded-xl text-[11px] font-bold bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white shadow-xs transition cursor-pointer text-center"
        title="Copy live tracking affiliate link"
      >
        <i class="ph-bold ph-copy text-xs"></i>
        <span>Copy Link</span>
      </button>` : `
      <a 
        href="${escapeHtml(c.publisher_url || panelUrl)}" 
        target="_blank" 
        rel="noopener noreferrer" 
        class="inline-flex items-center justify-center py-2 px-2 rounded-xl text-[11px] font-semibold bg-amber-500/10 text-amber-500 dark:text-amber-400 border border-amber-500/20 text-center hover:bg-amber-500/20 transition cursor-pointer"
        title="${applyTitle}"
      >
        <span>${applyText}</span>
        <i class="ph-bold ph-arrow-square-out text-xs ml-1"></i>
      </a>`}
    </div>
  `;

  return card;
}

window.copyCampaignLink = function(btn, url) {
  if (!url) return;
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(url).then(() => showCopiedFeedback(btn));
  } else {
    const el = document.createElement("textarea");
    el.value = url;
    document.body.appendChild(el);
    el.select();
    document.execCommand("copy");
    document.body.removeChild(el);
    showCopiedFeedback(btn);
  }
};

function showCopiedFeedback(btn) {
  const origHtml = btn.innerHTML;
  btn.innerHTML = `<i class="ph-bold ph-check text-xs"></i><span>Copied!</span>`;
  btn.classList.add("bg-emerald-700");
  setTimeout(() => {
    btn.innerHTML = origHtml;
    btn.classList.remove("bg-emerald-700");
  }, 1800);
}
