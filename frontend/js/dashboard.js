/**
 * dashboard.js - SOC Analytics Controller
 */

const API_BASE = window.location.origin;

let doughnutChart = null;
let lineChart = null;
let barChart = null;

document.addEventListener("DOMContentLoaded", () => {
    initDashboard();
});

async function initDashboard() {
    showSkeletons(true);

    try {
        const [statsRes, historyRes] = await Promise.all([
            fetch(`${API_BASE}/api/stats`),
            fetch(`${API_BASE}/api/history`)
        ]);

        let stats = null;
        let history = [];

        if (statsRes.ok) stats = await statsRes.json();
        if (historyRes.ok) history = await historyRes.json();

        updateStatCards(stats, history);
        createDoughnutChart(stats, history);
        createLineChart(history);
        createBarChart(stats);
        updateHistoryTable(history);
    } catch (error) {
        console.error("Dashboard data load error:", error);
    } finally {
        showSkeletons(false);
    }
}

function updateStatCards(stats, history) {
    const totalPredictions = stats?.prediction_stats?.total_predictions || history.length;
    const fraudCount = stats?.prediction_stats?.fraud_count || history.filter(h => h.prediction === "Fraud").length;
    const fraudRate = totalPredictions > 0 ? ((fraudCount / totalPredictions) * 100).toFixed(1) : "0.0";

    const modelResults = stats?.model_results || {};
    const bestModel = stats?.model_name || "RandomForest";
    let accuracy = "N/A";
    if (modelResults[bestModel]) {
        accuracy = (modelResults[bestModel].accuracy * 100).toFixed(1) + "%";
    }

    animateValue("totalPredictions", totalPredictions);
    animateValue("fraudCount", fraudCount);
    document.getElementById("fraudRate").textContent = fraudRate + "%";
    document.getElementById("modelAccuracy").textContent = accuracy;

    const modelNameEl = document.getElementById("modelName");
    if (modelNameEl) modelNameEl.textContent = `${bestModel} (SMOTE Balanced)`;
}

function animateValue(elementId, target) {
    const el = document.getElementById(elementId);
    if (!el) return;

    let current = 0;
    const steps = 25;
    const increment = target / steps;
    const stepTime = 600 / steps;

    const timer = setInterval(() => {
        current += increment;
        if (current >= target) {
            current = target;
            clearInterval(timer);
        }
        el.textContent = Math.round(current);
    }, stepTime);
}

function createDoughnutChart(stats, history) {
    const ctx = document.getElementById("doughnutChart");
    if (!ctx) return;

    let fraudCount, legitCount;
    if (stats?.dataset_stats?.fraud_count) {
        fraudCount = stats.dataset_stats.fraud_count;
        legitCount = stats.dataset_stats.legit_count;
    } else {
        fraudCount = history.filter(h => h.prediction === "Fraud").length;
        legitCount = history.filter(h => h.prediction === "Legit").length;
    }

    if (fraudCount === 0 && legitCount === 0) {
        legitCount = 100;
        fraudCount = 2;
    }

    if (doughnutChart) doughnutChart.destroy();

    doughnutChart = new Chart(ctx, {
        type: "doughnut",
        data: {
            labels: ["Legitimate", "Fraudulent"],
            datasets: [{
                data: [legitCount, fraudCount],
                backgroundColor: ["rgba(5, 150, 105, 0.8)", "rgba(220, 38, 38, 0.8)"],
                borderColor: ["#059669", "#dc2626"],
                borderWidth: 2,
                hoverOffset: 6
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: "bottom",
                    labels: { color: "#475569", font: { size: 12, family: "'Inter', sans-serif", weight: "600" }, usePointStyle: true }
                },
                tooltip: {
                    backgroundColor: "#0f172a",
                    titleColor: "#f8fafc",
                    bodyColor: "#cbd5e1",
                    padding: 10,
                    cornerRadius: 8
                }
            },
            cutout: "68%"
        }
    });
}

function createLineChart(history) {
    const ctx = document.getElementById("lineChart");
    if (!ctx) return;

    const fraudTimeline = [];
    const legitTimeline = [];
    const labels = [];

    history.slice(0, 20).reverse().forEach((item, index) => {
        const time = item.timestamp
            ? new Date(item.timestamp).toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit", second: "2-digit" })
            : `#${index + 1}`;
        labels.push(time);
        fraudTimeline.push(item.prediction === "Fraud" ? 1 : 0);
        legitTimeline.push(item.prediction === "Legit" ? 1 : 0);
    });

    if (labels.length === 0) {
        labels.push("Live Stream");
        fraudTimeline.push(0);
        legitTimeline.push(0);
    }

    if (lineChart) lineChart.destroy();

    lineChart = new Chart(ctx, {
        type: "line",
        data: {
            labels: labels,
            datasets: [
                {
                    label: "Fraudulent",
                    data: fraudTimeline,
                    borderColor: "#dc2626",
                    backgroundColor: "rgba(220, 38, 38, 0.08)",
                    fill: true,
                    tension: 0.35,
                    pointRadius: 4,
                    pointBackgroundColor: "#fff",
                    pointBorderColor: "#dc2626",
                    pointBorderWidth: 2
                },
                {
                    label: "Legitimate",
                    data: legitTimeline,
                    borderColor: "#059669",
                    backgroundColor: "rgba(5, 150, 105, 0.08)",
                    fill: true,
                    tension: 0.35,
                    pointRadius: 4,
                    pointBackgroundColor: "#fff",
                    pointBorderColor: "#059669",
                    pointBorderWidth: 2
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: { ticks: { color: "#94a3b8", maxTicksLimit: 8 }, grid: { color: "rgba(226, 232, 240, 0.6)" } },
                y: { ticks: { color: "#94a3b8", stepSize: 1 }, grid: { color: "rgba(226, 232, 240, 0.6)" } }
            },
            plugins: {
                legend: { labels: { color: "#475569", font: { size: 12, family: "'Inter', sans-serif" }, usePointStyle: true } }
            }
        }
    });
}

function createBarChart(stats) {
    const ctx = document.getElementById("barChart");
    if (!ctx) return;

    const featureImportance = stats?.feature_importance || {};
    const sortedFeatures = Object.entries(featureImportance)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 10);

    const labels = sortedFeatures.map(([name]) => name);
    const values = sortedFeatures.map(([, val]) => val);

    if (labels.length === 0) {
        labels.push("V14", "V10", "V12", "V17", "V4");
        values.push(0.08, 0.065, 0.05, 0.045, 0.04);
    }

    if (barChart) barChart.destroy();

    barChart = new Chart(ctx, {
        type: "bar",
        data: {
            labels: labels,
            datasets: [{
                label: "Importance Weight",
                data: values,
                backgroundColor: "rgba(37, 99, 235, 0.7)",
                borderColor: "#2563eb",
                borderWidth: 1.5,
                borderRadius: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            indexAxis: "y",
            scales: {
                x: { ticks: { color: "#94a3b8" }, grid: { color: "rgba(226, 232, 240, 0.6)" } },
                y: { ticks: { color: "#334155", font: { weight: "600" } }, grid: { display: false } }
            },
            plugins: {
                legend: { display: false }
            }
        }
    });
}

function updateHistoryTable(history) {
    const tbody = document.getElementById("historyTableBody");
    if (!tbody) return;

    if (history.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="6" class="text-center" style="padding: 2.5rem; color: var(--text-muted);">
                    No incident records logged. Run transaction evaluations to populate this audit trail.
                </td>
            </tr>
        `;
        return;
    }

    tbody.innerHTML = history.map((item, index) => `
        <tr>
            <td style="font-weight: 700; color: var(--text-muted); font-family: 'JetBrains Mono', monospace;">#${index + 1}</td>
            <td>
                <span class="status-badge ${item.prediction === "Fraud" ? "fraud" : "legit"}">
                    ${item.prediction === "Fraud" ? "🚨 FRAUD" : "✅ CLEAN"}
                </span>
            </td>
            <td style="font-weight: 700; font-family: 'JetBrains Mono', monospace;">${(item.confidence * 100).toFixed(1)}%</td>
            <td>
                <span class="risk-badge ${(item.risk_level || 'low').toLowerCase()}">
                    ${item.risk_level || "LOW"}
                </span>
            </td>
            <td style="font-weight: 600; font-family: 'JetBrains Mono', monospace;">\$${(item.amount || 0).toFixed(2)}</td>
            <td style="color: var(--text-muted); font-size: 0.78rem;">
                ${item.timestamp ? new Date(item.timestamp).toLocaleString() : "N/A"}
            </td>
        </tr>
    `).join("");
}

async function clearAuditHistory() {
    if (!confirm("Are you sure you want to purge all historical prediction logs?")) return;

    try {
        const res = await fetch(`${API_BASE}/api/history`, { method: "DELETE" });
        if (res.ok) {
            initDashboard();
        }
    } catch (e) {
        alert("Could not clear history");
    }
}

function showSkeletons(show) {
    document.querySelectorAll(".skeleton-loader").forEach(el => el.style.display = show ? "block" : "none");
    document.querySelectorAll(".data-content").forEach(el => el.style.display = show ? "none" : "block");
}

function refreshDashboard() {
    initDashboard();
}
