const API_BASE = "";

const elements = {
  apiStatus: document.getElementById("api-status"),
  sidebarStatus: document.getElementById("sidebar-status"),
  scanButton: document.getElementById("scan-button"),
  currentDate: document.getElementById("current-date"),
  lastUpdated: document.getElementById("last-updated"),

  total: document.getElementById("total-anomalies"),
  critical: document.getElementById("critical-count"),
  high: document.getElementById("high-count"),
  medium: document.getElementById("medium-count"),
  low: document.getElementById("low-count"),

  severityChart: document.getElementById("severity-chart"),
  typeChart: document.getElementById("type-chart"),

  search: document.getElementById("search-input"),
  severityFilter: document.getElementById("severity-filter"),
  anomalyTable: document.getElementById("anomaly-table"),
  resultCount: document.getElementById("result-count"),
  footerCount: document.getElementById("table-footer-count"),
  toast: document.getElementById("toast")
};

let allAnomalies = [];

const severityColors = {
  CRITICAL: "#e45d6b",
  HIGH: "#ee994e",
  MEDIUM: "#d5aa3d",
  LOW: "#36a982"
};

function showToast(message) {
  elements.toast.textContent = message;
  elements.toast.classList.add("show");

  setTimeout(() => {
    elements.toast.classList.remove("show");
  }, 3000);
}

function setApiStatus(connected) {
  if (connected) {
    elements.apiStatus.className = "connection-pill";
    elements.apiStatus.innerHTML =
      '<span class="live-dot"></span> API Connected';

    elements.sidebarStatus.textContent = "Connected successfully";
  } else {
    elements.apiStatus.className = "connection-pill offline";
    elements.apiStatus.innerHTML =
      '<span class="live-dot"></span> API Offline';

    elements.sidebarStatus.textContent = "Backend unavailable";
  }
}

function formatDate(value) {
  if (!value) return "—";

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return String(value);
  }

  return date.toLocaleString("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit"
  });
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, character => {
    const entities = {
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#039;"
    };

    return entities[character];
  });
}

function getSeverityCounts(anomalies) {
  const counts = {
    CRITICAL: 0,
    HIGH: 0,
    MEDIUM: 0,
    LOW: 0
  };

  anomalies.forEach(anomaly => {
    const severity = String(anomaly.severity || "").toUpperCase();

    if (Object.prototype.hasOwnProperty.call(counts, severity)) {
      counts[severity]++;
    }
  });

  return counts;
}

function updateStatistics(anomalies) {
  const counts = getSeverityCounts(anomalies);

  elements.total.textContent = anomalies.length;
  elements.critical.textContent = counts.CRITICAL;
  elements.high.textContent = counts.HIGH;
  elements.medium.textContent = counts.MEDIUM;
  elements.low.textContent = counts.LOW;
}

function renderSeverityChart(anomalies) {
  const counts = getSeverityCounts(anomalies);
  const total = anomalies.length;

  const order = ["CRITICAL", "HIGH", "MEDIUM", "LOW"];

  elements.severityChart.innerHTML = order.map(severity => {
    const count = counts[severity];
    const percentage = total > 0 ? (count / total) * 100 : 0;
    const color = severityColors[severity];

    return `
      <div class="severity-row">
        <span class="severity-name">${severity}</span>
        <div class="bar-track">
          <div
            class="bar-fill"
            style="width:${percentage}%; background:${color};"
          ></div>
        </div>
        <span class="severity-count">${count}</span>
      </div>
    `;
  }).join("");
}

function renderCategoryChart(anomalies) {
  const categories = {};

  anomalies.forEach(anomaly => {
    const type = anomaly.anomaly_type || "OTHER";
    categories[type] = (categories[type] || 0) + 1;
  });

  const entries = Object.entries(categories)
    .sort((a, b) => b[1] - a[1]);

  if (entries.length === 0) {
    elements.typeChart.innerHTML =
      '<div class="chart-empty">No anomaly categories detected</div>';
    return;
  }

  const maximum = Math.max(...entries.map(item => item[1]));

  elements.typeChart.innerHTML = entries.map(([type, count]) => {
    const percentage = maximum > 0 ? (count / maximum) * 100 : 0;

    return `
      <div class="category-row">
        <span class="category-name">${escapeHtml(type.replaceAll("_", " "))}</span>
        <div class="bar-track">
          <div
            class="bar-fill"
            style="width:${percentage}%; background:#746be0;"
          ></div>
        </div>
        <span class="category-count">${count}</span>
      </div>
    `;
  }).join("");
}

function getRecordReference(anomaly) {
  const records = anomaly.records || {};

  const preferredKeys = [
    "seller_id",
    "listing_id",
    "payout_id",
    "payout_line_id",
    "dispute_id",
    "order_line_id",
    "fulfillment_id"
  ];

  for (const key of preferredKeys) {
    if (records[key]) {
      return records[key];
    }
  }

  const values = Object.values(records);

  return values.length ? values[0] : "—";
}

function renderTable(anomalies) {
  const searchTerm = elements.search.value.trim().toLowerCase();
  const selectedSeverity = elements.severityFilter.value;

  const filtered = anomalies.filter(anomaly => {
    const severity = String(anomaly.severity || "").toUpperCase();

    const searchableText = [
      anomaly.anomaly_id,
      anomaly.anomaly_type,
      anomaly.title,
      anomaly.description,
      JSON.stringify(anomaly.records || {})
    ].join(" ").toLowerCase();

    const matchesSearch = searchableText.includes(searchTerm);

    const matchesSeverity =
      selectedSeverity === "ALL" || severity === selectedSeverity;

    return matchesSearch && matchesSeverity;
  });

  elements.resultCount.textContent = `${filtered.length} records`;
  elements.footerCount.textContent = `${filtered.length} results`;

  if (filtered.length === 0) {
    elements.anomalyTable.innerHTML = `
      <tr>
        <td colspan="5" class="table-message">
          No matching anomalies found.
        </td>
      </tr>
    `;
    return;
  }

  elements.anomalyTable.innerHTML = filtered.map(anomaly => {
    const severity = String(anomaly.severity || "LOW").toLowerCase();
    const reference = getRecordReference(anomaly);

    return `
      <tr>
        <td>
          <div class="anomaly-title">
            ${escapeHtml(anomaly.title || anomaly.anomaly_type)}
          </div>
          <div class="anomaly-id">
            ${escapeHtml(anomaly.anomaly_id || "—")}
          </div>
        </td>

        <td>
          <span class="severity-badge ${escapeHtml(severity)}">
            ${escapeHtml(severity.toUpperCase())}
          </span>
        </td>

        <td>${escapeHtml(anomaly.description || "—")}</td>

        <td>
          <span class="record-reference">
            ${escapeHtml(reference)}
          </span>
        </td>

        <td>${escapeHtml(formatDate(anomaly.detected_at))}</td>
      </tr>
    `;
  }).join("");
}

function renderDashboard(anomalies) {
  allAnomalies = Array.isArray(anomalies) ? anomalies : [];

  updateStatistics(allAnomalies);
  renderSeverityChart(allAnomalies);
  renderCategoryChart(allAnomalies);
  renderTable(allAnomalies);

  elements.lastUpdated.textContent =
    `Last scanned: ${new Date().toLocaleTimeString("en-IN")}`;
}

async function checkHealth() {
  try {
    const response = await fetch(`${API_BASE}/health`);

    if (!response.ok) {
      throw new Error("Health check failed");
    }

    setApiStatus(true);
    return true;
  } catch (error) {
    setApiStatus(false);
    return false;
  }
}

async function runRiskScan(showMessage = true) {
  elements.scanButton.disabled = true;
  elements.scanButton.innerHTML =
    '<span class="scan-icon">↻</span><span>Scanning...</span>';

  try {
    const response = await fetch(
      `${API_BASE}/api/v1/anomalies/scan`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        }
      }
    );

    if (!response.ok) {
      throw new Error(`Scan failed with status ${response.status}`);
    }

    const data = await response.json();

    renderDashboard(data.anomalies || []);
    setApiStatus(true);

    if (showMessage) {
      showToast(`Risk scan completed: ${data.total_anomalies} anomalies found.`);
    }

  } catch (error) {
    console.error("Risk scan error:", error);
    setApiStatus(false);

    showToast("Unable to run risk scan. Check your backend server.");

  } finally {
    elements.scanButton.disabled = false;
    elements.scanButton.innerHTML =
      '<span class="scan-icon">↻</span><span>Run risk scan</span>';
  }
}

async function loadDashboard() {
  const connected = await checkHealth();

  if (connected) {
    await runRiskScan(false);
  } else {
    elements.anomalyTable.innerHTML = `
      <tr>
        <td colspan="5" class="table-message">
          Backend connection unavailable. Start the FastAPI server and refresh.
        </td>
      </tr>
    `;
  }
}

/* EVENT LISTENERS */

elements.scanButton.addEventListener("click", () => {
  runRiskScan(true);
});

elements.search.addEventListener("input", () => {
  renderTable(allAnomalies);
});

elements.severityFilter.addEventListener("change", () => {
  renderTable(allAnomalies);
});

/* INITIALIZE */

elements.currentDate.textContent =
  new Date().toLocaleDateString("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric"
  });

loadDashboard();