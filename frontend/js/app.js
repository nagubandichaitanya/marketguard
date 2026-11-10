
const API_BASE = "";

const scanButton = document.getElementById("scan-button");
const apiStatus = document.getElementById("api-status");
const sidebarStatus = document.getElementById("sidebar-status");
const sidebarDot = document.getElementById("sidebar-status-dot");
const searchInput = document.getElementById("search-input");
const severityFilter = document.getElementById("severity-filter");
const anomalyTable = document.getElementById("anomaly-table");

let allAnomalies = [];

function showToast(message) {
    const toast = document.getElementById("toast");
    toast.textContent = message;
    toast.classList.add("show");

    setTimeout(() => {
        toast.classList.remove("show");
    }, 3500);
}

function setApiStatus(online) {
    apiStatus.textContent = online ? "● API Connected" : "● API Offline";
    sidebarStatus.textContent = online ? "System online" : "System offline";

    sidebarDot.className = online
        ? "status-dot online"
        : "status-dot offline";
}

function updateStats(data) {
    document.getElementById("total-anomalies").textContent =
        data.total_anomalies;

    document.getElementById("critical-count").textContent =
        data.critical_count;

    document.getElementById("high-count").textContent =
        data.high_count;

    document.getElementById("medium-count").textContent =
        data.medium_count;

    document.getElementById("low-count").textContent =
        data.low_count;
}

function renderSeverityChart(data) {
    const container = document.getElementById("severity-chart");

    const levels = [
        { name: "Critical", value: data.critical_count, color: "#e64f60" },
        { name: "High", value: data.high_count, color: "#ed963e" },
        { name: "Medium", value: data.medium_count, color: "#e4bd45" },
        { name: "Low", value: data.low_count, color: "#38aa86" }
    ];

    const maximum = Math.max(data.total_anomalies, 1);

    container.innerHTML = "";

    levels.forEach(level => {
        const row = document.createElement("div");
        row.className = "severity-row";

        const label = document.createElement("span");
        label.textContent = level.name;

        const track = document.createElement("div");
        track.className = "progress-track";

        const fill = document.createElement("div");
        fill.className = "progress-fill";
        fill.style.width = `${(level.value / maximum) * 100}%`;
        fill.style.background = level.color;

        track.appendChild(fill);

        const count = document.createElement("strong");
        count.textContent = level.value;

        row.append(label, track, count);
        container.appendChild(row);
    });
}

function renderTypeChart(byType) {
    const container = document.getElementById("type-chart");
    container.innerHTML = "";

    const entries = Object.entries(byType);
    const maximum = Math.max(...entries.map(item => item[1]), 1);

    if (entries.length === 0) {
        container.textContent = "No anomalies detected.";
        return;
    }

    entries.forEach(([type, count]) => {
        const row = document.createElement("div");
        row.className = "type-row";

        const label = document.createElement("div");
        label.className = "type-label";

        const name = document.createElement("span");
        name.textContent = type.replaceAll("_", " ");

        const value = document.createElement("strong");
        value.textContent = count;

        label.append(name, value);

        const track = document.createElement("div");
        track.className = "progress-track";

        const fill = document.createElement("div");
        fill.className = "progress-fill";
        fill.style.width = `${(count / maximum) * 100}%`;
        fill.style.background = "#526cf0";

        track.appendChild(fill);
        row.append(label, track);
        container.appendChild(row);
    });
}

function renderAnomalyTable(anomalies) {
    anomalyTable.innerHTML = "";

    if (anomalies.length === 0) {
        const row = document.createElement("tr");
        const cell = document.createElement("td");

        cell.colSpan = 6;
        cell.className = "empty-state";
        cell.textContent = "No matching anomalies found.";

        row.appendChild(cell);
        anomalyTable.appendChild(row);
    }

    anomalies.forEach(anomaly => {
        const row = document.createElement("tr");

        const seller = anomaly.records.seller_id || "N/A";
        const record = anomaly.records.listing_id
            || anomaly.records.payout_id
            || anomaly.records.dispute_id
            || anomaly.records.payout_line_id
            || anomaly.records.order_line_id
            || "N/A";

        const values = [
            anomaly.anomaly_id,
            anomaly.anomaly_type.replaceAll("_", " "),
            anomaly.severity,
            `${seller} / ${record}`,
            anomaly.recommendation,
            new Date(anomaly.detected_at).toLocaleString()
        ];

        values.forEach((value, index) => {
            const cell = document.createElement("td");

            if (index === 2) {
                const badge = document.createElement("span");
                badge.className = `severity-badge severity-${anomaly.severity}`;
                badge.textContent = anomaly.severity;
                cell.appendChild(badge);
            } else {
                cell.textContent = value;
            }

            if (index === 4) {
                cell.className = "recommendation";
            }

            row.appendChild(cell);
        });

        anomalyTable.appendChild(row);
    });

    document.getElementById("result-count").textContent =
        `Showing ${anomalies.length} of ${allAnomalies.length} anomalies`;
}

function applyFilters() {
    const query = searchInput.value.toLowerCase().trim();
    const severity = severityFilter.value;

    const filtered = allAnomalies.filter(anomaly => {
        const searchable = [
            anomaly.anomaly_id,
            anomaly.anomaly_type,
            anomaly.title,
            anomaly.description,
            anomaly.recommendation,
            JSON.stringify(anomaly.records)
        ].join(" ").toLowerCase();

        const matchesSearch = searchable.includes(query);
        const matchesSeverity =
            severity === "ALL" || anomaly.severity === severity;

        return matchesSearch && matchesSeverity;
    });

    renderAnomalyTable(filtered);
}

async function checkHealth() {
    try {
        const response = await fetch(`${API_BASE}/health`);

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        setApiStatus(true);
    } catch (error) {
        setApiStatus(false);
        console.error("Health check failed:", error);
    }
}

async function loadSummary() {
    const response = await fetch(`${API_BASE}/api/v1/anomalies/summary`);

    if (!response.ok) {
        throw new Error(`Summary request failed: HTTP ${response.status}`);
    }

    return await response.json();
}

async function runScan() {
    scanButton.disabled = true;
    scanButton.textContent = "Scanning...";

    try {
        const response = await fetch(
            `${API_BASE}/api/v1/anomalies/scan`,
            { method: "POST" }
        );

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || `HTTP ${response.status}`);
        }

        const data = await response.json();

        allAnomalies = data.anomalies;

        updateStats(data);
        renderSeverityChart(data);

        const summary = await loadSummary();
        renderTypeChart(summary.by_type);

        applyFilters();

        document.getElementById("last-updated").textContent =
            `Last scanned: ${new Date().toLocaleString()}`;

        setApiStatus(true);
        showToast(`Scan completed: ${data.total_anomalies} anomalies found.`);
    } catch (error) {
        console.error("Scan failed:", error);
        setApiStatus(false);
        showToast(`Scan failed: ${error.message}`);
    } finally {
        scanButton.disabled = false;
        scanButton.innerHTML = "<span>↻</span> Scan Now";
    }
}

scanButton.addEventListener("click", runScan);
searchInput.addEventListener("input", applyFilters);
severityFilter.addEventListener("change", applyFilters);

async function initializeDashboard() {
    await checkHealth();
    await runScan();
}

initializeDashboard();
