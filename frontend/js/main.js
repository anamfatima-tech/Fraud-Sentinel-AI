/**
 * main.js - Enterprise Fraud Sentinel Frontend Controller
 * Features:
 * - Single transaction evaluation with Explainable AI (XAI)
 * - Dynamic risk sensitivity threshold
 * - Batch CSV Scanner with instant scoring
 * - Live Radar Stream continuous simulator
 * - LocalStorage persistence and report printing
 */

const API_BASE = window.location.origin;

let sampleData = null;
let currentThreshold = 0.50;
let streamInterval = null;
let streamActive = false;
let audioEnabled = true;
let audioCtx = null;
let cachedBatchData = null;

/**
 * Web Audio API Sound Synthesizer (Zero External Audio Dependencies)
 */
function playAudioAlert(type) {
    if (!audioEnabled) return;
    try {
        if (!audioCtx) {
            audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        }
        if (audioCtx.state === 'suspended') {
            audioCtx.resume();
        }

        const now = audioCtx.currentTime;
        const osc = audioCtx.createOscillator();
        const gain = audioCtx.createGain();
        osc.connect(gain);
        gain.connect(audioCtx.destination);

        if (type === "fraud") {
            // Urgent high-pitched warning beep
            osc.type = "sawtooth";
            osc.frequency.setValueAtTime(880, now);
            osc.frequency.exponentialRampToValueAtTime(440, now + 0.25);
            gain.gain.setValueAtTime(0.15, now);
            gain.gain.exponentialRampToValueAtTime(0.01, now + 0.25);
            osc.start(now);
            osc.stop(now + 0.25);
        } else {
            // Pleasant subtle confirmation chime
            osc.type = "sine";
            osc.frequency.setValueAtTime(523.25, now); // C5
            osc.frequency.exponentialRampToValueAtTime(659.25, now + 0.15); // E5
            gain.gain.setValueAtTime(0.08, now);
            gain.gain.exponentialRampToValueAtTime(0.01, now + 0.2);
            osc.start(now);
            osc.stop(now + 0.2);
        }
    } catch (e) {
        // Audio policy or unsupported
    }
}

function toggleAudioAlerts() {
    audioEnabled = !audioEnabled;
    const btn = document.getElementById("soundToggleBtn");
    if (btn) {
        btn.textContent = audioEnabled ? "🔊 Sound: ON" : "🔇 Sound: OFF";
        btn.classList.toggle("btn-secondary", audioEnabled);
    }
    showToast(audioEnabled ? "🔊 Sound effects enabled" : "🔇 Sound effects muted");
}

document.addEventListener("DOMContentLoaded", () => {
    console.log("🛡️ Enterprise Fraud Sentinel Initialized");
    loadSampleData();
    setupCollapsibles();
    setupDropZone();

    const form = document.getElementById("predictionForm");
    if (form) {
        form.addEventListener("submit", handlePrediction);
    }
});

/**
 * View Switcher: Single vs Batch vs Stream
 */
function switchView(mode) {
    document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
    document.getElementById("viewSingle").classList.add("hidden");
    document.getElementById("viewBatch").classList.add("hidden");
    document.getElementById("viewStream").classList.add("hidden");

    if (mode === "single") {
        document.getElementById("tabSingle").classList.add("active");
        document.getElementById("viewSingle").classList.remove("hidden");
    } else if (mode === "batch") {
        document.getElementById("tabBatch").classList.add("active");
        document.getElementById("viewBatch").classList.remove("hidden");
    } else if (mode === "stream") {
        document.getElementById("tabStream").classList.add("active");
        document.getElementById("viewStream").classList.remove("hidden");
    }
}

/**
 * Sensitivity Threshold Controller
 */
function updateThresholdDisplay(val) {
    currentThreshold = parseFloat(val) / 100.0;
    const label = document.getElementById("thresholdVal");
    if (label) label.textContent = `${val}%`;
}

/**
 * Sample Data Loader
 */
async function loadSampleData() {
    try {
        const response = await fetch(`${API_BASE}/sample_data.json`);
        if (response.ok) {
            sampleData = await response.json();
        }
    } catch (e) {
        console.warn("Sample data fetch error:", e);
    }
}

/**
 * Collapsible section toggler
 */
function setupCollapsibles() {
    document.querySelectorAll(".collapsible-header").forEach(header => {
        header.addEventListener("click", () => {
            header.classList.toggle("active");
            header.nextElementSibling.classList.toggle("open");
        });
    });
}

function loadSampleFraud() {
    if (!sampleData || !sampleData.fraud_samples) {
        showToast("⚠️ Sample data loading, please wait...");
        return;
    }
    const samples = sampleData.fraud_samples;
    const sample = samples[Math.floor(Math.random() * samples.length)];
    fillForm(sample);
    showToast(`🔴 Loaded: ${sample.label}`);
    openAllCollapsibles();
}

function loadSampleLegit() {
    if (!sampleData || !sampleData.legit_samples) {
        showToast("⚠️ Sample data loading, please wait...");
        return;
    }
    const samples = sampleData.legit_samples;
    const sample = samples[Math.floor(Math.random() * samples.length)];
    fillForm(sample);
    showToast(`🟢 Loaded: ${sample.label}`);
    openAllCollapsibles();
}

function fillForm(data) {
    const featureNames = ["Time", ...Array.from({ length: 28 }, (_, i) => `V${i + 1}`), "Amount"];
    featureNames.forEach(name => {
        const input = document.getElementById(`input_${name}`);
        if (input && data[name] !== undefined) {
            input.value = data[name];
        }
    });
}

function openAllCollapsibles() {
    document.querySelectorAll(".collapsible-header").forEach(header => {
        header.classList.add("active");
        header.nextElementSibling.classList.add("open");
    });
}

function clearForm() {
    const form = document.getElementById("predictionForm");
    if (form) form.reset();
    document.getElementById("resultPlaceholder").style.display = "block";
    document.getElementById("resultDisplay").classList.remove("visible");
    hideError();
    showToast("🧹 Form fields cleared");
}

/**
 * Single Transaction Evaluation
 */
async function handlePrediction(event) {
    event.preventDefault();
    hideError();

    const featureNames = ["Time", ...Array.from({ length: 28 }, (_, i) => `V${i + 1}`), "Amount"];
    const data = { threshold: currentThreshold };
    let hasEmpty = false;

    featureNames.forEach(name => {
        const input = document.getElementById(`input_${name}`);
        if (input) {
            const val = input.value.trim();
            if (val === "" || isNaN(parseFloat(val))) {
                hasEmpty = true;
            } else {
                data[name] = parseFloat(val);
            }
        }
    });

    if (hasEmpty) {
        showError("Incomplete Input", "Please provide numeric values for all 30 features.");
        return;
    }

    showLoading(true);

    try {
        const res = await fetch(`${API_BASE}/api/predict`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(data)
        });

        const result = await res.json();

        if (!res.ok) {
            showError(result.error || "Evaluation Failed", result.details || "API rejected request");
            return;
        }

        displayResult(result);
    } catch (e) {
        showError("Connection Error", "Cannot reach backend. Ensure server is active: python app.py");
    } finally {
        showLoading(false);
    }
}

/**
 * Render Verdict, Recommendations & Explainability Factors
 */
function displayResult(result) {
    const isFraud = result.prediction === "Fraud";
    const confidence = result.confidence;

    // Play synthesized sound alert
    playAudioAlert(isFraud ? "fraud" : "clean");

    // Badge
    const badge = document.getElementById("predictionBadge");
    badge.className = `prediction-badge ${isFraud ? "fraud" : "legit"}`;
    badge.querySelector(".badge-icon").textContent = isFraud ? "🚨" : "🛡️";
    badge.querySelector(".badge-text").textContent = isFraud ? "FRAUD DETECTED" : "TRANSACTION LEGITIMATE";

    // Confidence Bar
    const confFill = document.getElementById("confidenceFill");
    const confVal = document.getElementById("confidenceValue");
    confFill.style.width = `${confidence * 100}%`;
    confFill.className = `confidence-fill ${isFraud ? "fraud" : "legit"}`;
    confVal.textContent = `${(confidence * 100).toFixed(1)}%`;

    // Probability meters
    document.getElementById("fraudProb").textContent = `${(result.fraud_probability * 100).toFixed(1)}%`;
    document.getElementById("legitProb").textContent = `${(result.legit_probability * 100).toFixed(1)}%`;

    // Action Recommendation Alert Banner
    const actionBanner = document.getElementById("actionBanner");
    const rec = result.recommendation;
    if (rec) {
        let bannerClass = "approve";
        if (rec.action.includes("BLOCK")) bannerClass = "block";
        else if (rec.action.includes("2FA")) bannerClass = "challenge";

        actionBanner.className = `action-banner ${bannerClass}`;
        document.getElementById("actionTitle").textContent = rec.title;
        document.getElementById("actionDesc").textContent = rec.description;
    }

    // Explainable AI Factors
    const factorsList = document.getElementById("riskFactorsList");
    factorsList.innerHTML = "";
    const factors = result.risk_factors || [];

    factors.forEach(f => {
        const factorCard = document.createElement("div");
        factorCard.className = "factor-card";
        factorCard.innerHTML = `
            <div class="factor-header">
                <span class="factor-name">${f.feature} • ${f.name}</span>
                <span class="factor-impact ${f.impact}">${f.impact} Risk</span>
            </div>
            <div class="factor-reason">${f.reason} (Value: <strong>${f.value}</strong>)</div>
            <div class="factor-meter">
                <div class="factor-meter-fill" style="width: ${f.severity}%;"></div>
            </div>
        `;
        factorsList.appendChild(factorCard);
    });

    document.getElementById("resultPlaceholder").style.display = "none";
    document.getElementById("resultDisplay").classList.add("visible");
}

/**
 * Batch CSV Scanner
 */
function setupDropZone() {
    const dropZone = document.getElementById("dropZone");
    if (!dropZone) return;

    ["dragenter", "dragover"].forEach(eventName => {
        dropZone.addEventListener(eventName, e => {
            e.preventDefault();
            dropZone.classList.add("dragover");
        });
    });

    ["dragleave", "drop"].forEach(eventName => {
        dropZone.addEventListener(eventName, e => {
            e.preventDefault();
            dropZone.classList.remove("dragover");
        });
    });

    dropZone.addEventListener("drop", e => {
        const files = e.dataTransfer.files;
        if (files.length > 0) processCsvFile(files[0]);
    });
}

function handleCsvUpload(event) {
    const file = event.target.files[0];
    if (file) processCsvFile(file);
}

async function processCsvFile(file) {
    if (!file.name.endsWith(".csv")) {
        showToast("⚠️ Please upload a valid CSV file");
        return;
    }

    showToast(`📂 Uploading & scanning: ${file.name}...`);
    const formData = new FormData();
    formData.append("file", file);

    try {
        const res = await fetch(`${API_BASE}/api/predict/batch`, {
            method: "POST",
            body: formData
        });

        const data = await res.json();
        if (!res.ok) {
            showError("Batch Processing Failed", data.error || "Invalid file format");
            return;
        }

        renderBatchResults(data);
        showToast(`✅ Successfully scanned ${data.summary.total_transactions} transactions!`);
    } catch (e) {
        showError("Batch Error", "Could not process CSV. Verify backend is running.");
    }
}

function renderBatchResults(data) {
    cachedBatchData = data.results || [];
    const s = data.summary;
    document.getElementById("batchTotal").textContent = s.total_transactions;
    document.getElementById("batchFraud").textContent = `${s.fraud_count} (${s.fraud_rate}%)`;
    document.getElementById("batchLegit").textContent = s.legit_count;
    document.getElementById("batchFlaggedAmt").textContent = `$${s.flagged_amount.toFixed(2)}`;

    populateBatchTable(cachedBatchData);
    document.getElementById("batchSummarySection").classList.remove("hidden");
}

function filterBatchResults(type) {
    if (!cachedBatchData) return;
    let filtered = cachedBatchData;
    if (type === "fraud") {
        filtered = cachedBatchData.filter(r => r.prediction === "Fraud");
    } else if (type === "clean") {
        filtered = cachedBatchData.filter(r => r.prediction === "Legit");
    }
    populateBatchTable(filtered);
}

function populateBatchTable(rows) {
    const tbody = document.getElementById("batchTableBody");
    if (!tbody) return;
    if (rows.length === 0) {
        tbody.innerHTML = `<tr><td colspan="6" class="text-center" style="padding: 1.5rem; color: var(--text-muted);">No records match filter.</td></tr>`;
        return;
    }
    tbody.innerHTML = rows.map(r => `
        <tr>
            <td style="font-weight: 700; color: var(--text-muted);">#${r.row_id}</td>
            <td style="font-weight: 600;">$${r.amount ? r.amount.toFixed(2) : "0.00"}</td>
            <td>
                <span class="status-badge ${r.prediction === 'Fraud' ? 'fraud' : 'legit'}">
                    ${r.prediction === 'Fraud' ? '🚨 FRAUD' : '✅ CLEAN'}
                </span>
            </td>
            <td style="font-family: 'JetBrains Mono', monospace;">${(r.fraud_probability * 100).toFixed(1)}%</td>
            <td>${(r.confidence * 100).toFixed(1)}%</td>
            <td>
                <span class="risk-badge ${(r.risk_level || 'low').toLowerCase()}">${r.risk_level || 'N/A'}</span>
            </td>
        </tr>
    `).join("");
}

/**
 * Live Radar Stream Simulator
 */
function toggleStreamSimulation() {
    const btn = document.getElementById("toggleStreamBtn");
    const indicator = document.getElementById("streamStatusIndicator");

    if (streamActive) {
        clearInterval(streamInterval);
        streamActive = false;
        btn.textContent = "▶️ Resume Live Radar";
        btn.className = "btn btn-primary";
        indicator.innerHTML = `<div class="radar-pulse-dot" style="background: var(--text-muted);"></div><span>RADAR PAUSED</span>`;
        showToast("⏸️ Live radar stream paused");
    } else {
        streamActive = true;
        btn.textContent = "⏹️ Halt Radar Stream";
        btn.className = "btn btn-danger";
        indicator.innerHTML = `<div class="radar-pulse-dot"></div><span>MONITORING ACTIVE</span>`;
        showToast("⚡ Real-time ingestion stream engaged!");
        runStreamCycle();
        streamInterval = setInterval(runStreamCycle, 2200);
    }
}

async function runStreamCycle() {
    try {
        const res = await fetch(`${API_BASE}/api/simulate/stream`);
        const tx = await res.json();

        // Evaluate immediately
        const evalRes = await fetch(`${API_BASE}/api/predict`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ ...tx, threshold: currentThreshold })
        });
        const verdict = await evalRes.json();

        addStreamTickerItem(verdict);
    } catch (e) {
        console.warn("Stream evaluation skipped:", e);
    }
}

function addStreamTickerItem(item) {
    const ticker = document.getElementById("streamTicker");
    const isFraud = item.prediction === "Fraud";

    if (isFraud) {
        playAudioAlert("fraud");
    }

    const div = document.createElement("div");
    div.className = `stream-item ${isFraud ? 'fraud-alert' : ''}`;
    div.innerHTML = `
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <span style="font-size: 1.1rem;">${isFraud ? '🚨' : '💳'}</span>
            <div>
                <strong style="color: ${isFraud ? 'var(--fraud-red)' : 'var(--text-primary)'}">
                    ${isFraud ? 'SUSPICIOUS INTRUSION DETECTED' : 'Verified POS Settlement'}
                </strong>
                <div style="font-size: 0.72rem; color: var(--text-muted); font-family: 'JetBrains Mono', monospace;">
                    Amount: $${item.amount.toFixed(2)} • Time-Delta: ${new Date().toLocaleTimeString()}
                </div>
            </div>
        </div>
        <div style="text-align: right;">
            <span class="status-badge ${isFraud ? 'fraud' : 'legit'}">
                ${isFraud ? `BLOCKED (${(item.fraud_probability * 100).toFixed(0)}% Risk)` : `CLEARED`}
            </span>
        </div>
    `;

    // If placeholder present, clear it
    if (ticker.children.length === 1 && ticker.children[0].textContent.includes("Click Start")) {
        ticker.innerHTML = "";
    }

    ticker.insertBefore(div, ticker.firstChild);

    // Keep max 25 items in stream view
    if (ticker.children.length > 25) {
        ticker.removeChild(ticker.lastChild);
    }
}

/**
 * Print Audit Report Dossier
 */
function printDossier() {
    window.print();
}

/**
 * UI Utilities
 */
function showLoading(isLoading) {
    const btn = document.getElementById("predictBtn");
    const spinner = document.getElementById("loadingSpinner");
    const btnText = document.getElementById("btnText");

    btn.disabled = isLoading;
    if (isLoading) {
        spinner.classList.add("active");
        btnText.textContent = "Analyzing Network Vectors...";
    } else {
        spinner.classList.remove("active");
        btnText.textContent = "🛡️ Evaluate Fraud Risk";
    }
}

function showError(title, message) {
    const errorDiv = document.getElementById("errorMessage");
    document.getElementById("errTitle").textContent = title;
    document.getElementById("errDetails").textContent = message;
    errorDiv.classList.add("visible");
}

function hideError() {
    document.getElementById("errorMessage").classList.remove("visible");
}

function showToast(message) {
    const existing = document.querySelector(".toast");
    if (existing) existing.remove();

    const toast = document.createElement("div");
    toast.className = "toast";
    toast.textContent = message;
    document.body.appendChild(toast);

    requestAnimationFrame(() => toast.classList.add("visible"));
    setTimeout(() => {
        toast.classList.remove("visible");
        setTimeout(() => toast.remove(), 300);
    }, 3200);
}
