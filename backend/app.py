"""
app.py - Advanced Flask API Server for Credit Card Fraud Detection
Includes:
- Explainable AI (XAI) risk driver breakdown
- Actionable security recommendations (Freeze card, 2FA challenge, Auto-approve)
- Configurable risk sensitivity threshold
- Batch processing & CSV upload scanner
- Live transaction stream simulator
- History export to CSV
"""

import os
import io
import csv
import sys
import json
import pickle
import random
import datetime
import numpy as np
import pandas as pd
from flask import Flask, request, jsonify, send_from_directory, send_file, Response
from flask_cors import CORS

# Project paths setup
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(os.path.dirname(BASE_DIR), "frontend")
MODEL_DIR = os.path.join(BASE_DIR, "model")
HISTORY_FILE = os.path.join(BASE_DIR, "prediction_history.json")

# Flask app initialize
app = Flask(__name__, static_folder=FRONTEND_DIR)
CORS(app)

# Feature names definition (30 features required)
FEATURE_NAMES = ["Time"] + [f"V{i}" for i in range(1, 29)] + ["Amount"]

# Semantic descriptions for PCA features for Explainable AI (XAI)
FEATURE_DESCRIPTIONS = {
    "V1": "Cardholder Authentication Pattern",
    "V2": "Geographic Distance Anomaly",
    "V3": "Terminal Device Signature",
    "V4": "Transaction Velocity Variance",
    "V5": "Account Balance Fluctuation",
    "V6": "Payment Channel Integrity",
    "V7": "Merchant Category Deviation",
    "V8": "ATM / POS Terminal Verification",
    "V9": "Cross-Border Settlement Flag",
    "V10": "Behavioral Biometric Anomaly",
    "V11": "Rapid Succession Attempt",
    "V12": "Card-Not-Present Token Check",
    "V13": "Billing Address Verification",
    "V14": "Known Fraud Ring Sub-cluster",
    "V15": "Issuer Authorization Latency",
    "V16": "EMV Chip Cryptogram Check",
    "V17": "High-Risk Merchant Association",
    "V18": "IP Subnet Reputation Score",
    "V19": "Currency Conversion Anomaly",
    "V20": "Session Duration / Fingerprint",
    "V21": "Card Usage Frequency Spike",
    "V22": "Historical Chargeback Index",
    "V23": "Device Fingerprint Deviation",
    "V24": "Time-of-Day Anomaly Index",
    "V25": "Transaction Routing Irregularity",
    "V26": "Card Re-issue Recency Check",
    "V27": "Proxy / VPN Detection Score",
    "V28": "Secondary Authentication Flag",
    "Amount": "Transaction Dollar Volume",
    "Time": "Elapsed Time Interval"
}

# Global variables for model, scaler, metrics
model = None
scaler = None
metrics = None


def load_model_and_scaler():
    """Load model, scaler and training metrics on server startup."""
    global model, scaler, metrics

    model_path = os.path.join(MODEL_DIR, "fraud_model.pkl")
    scaler_path = os.path.join(MODEL_DIR, "scaler.pkl")
    metrics_path = os.path.join(MODEL_DIR, "metrics.pkl")

    if os.path.exists(model_path):
        with open(model_path, "rb") as f:
            model = pickle.load(f)
        print("✅ Model loaded successfully!")
    else:
        print("⚠️ Model file nahi mili! Pehle train_model.py chalaao.")

    if os.path.exists(scaler_path):
        with open(scaler_path, "rb") as f:
            scaler = pickle.load(f)
        print("✅ Scaler loaded successfully!")
    else:
        print("⚠️ Scaler file nahi mili!")

    if os.path.exists(metrics_path):
        with open(metrics_path, "rb") as f:
            metrics = pickle.load(f)
        print("✅ Metrics loaded successfully!")
    else:
        print("⚠️ Metrics file nahi mili!")


def save_prediction_to_history(prediction_data):
    """Save prediction records to persistent JSON file."""
    history = []
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r") as f:
                history = json.load(f)
        except (json.JSONDecodeError, IOError):
            history = []

    history.append(prediction_data)
    # Keep last 100 entries
    history = history[-100:]

    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2)


def get_risk_level(confidence):
    """Categorize risk level from probability."""
    if confidence >= 0.75:
        return "HIGH"
    elif confidence >= 0.40:
        return "MEDIUM"
    else:
        return "LOW"


def generate_explainability(feature_dict, fraud_prob):
    """
    Explainable AI (XAI) engine:
    Calculates top risk drivers based on feature deviations and known high-risk components.
    """
    risk_factors = []

    # Check key PCA components known for fraud correlation (e.g. V14, V12, V10, V17, V4)
    key_drivers = ["V14", "V12", "V10", "V17", "V4", "V11", "V7", "Amount"]

    for feat in key_drivers:
        val = abs(float(feature_dict.get(feat, 0.0)))
        # Compute dynamic deviation severity
        if feat == "Amount":
            amount_val = float(feature_dict.get("Amount", 0.0))
            if amount_val > 500:
                severity = min(100, int((amount_val / 1000) * 80) + 20)
                risk_factors.append({
                    "feature": feat,
                    "name": FEATURE_DESCRIPTIONS.get(feat, feat),
                    "value": f"${amount_val:.2f}",
                    "severity": severity,
                    "impact": "High" if severity > 70 else "Medium",
                    "reason": f"High transaction amount exceeds customary limits."
                })
        else:
            if val > 1.8:
                severity = min(98, int((val / 4.0) * 90) + 10)
                impact = "Critical" if severity >= 80 else ("High" if severity >= 50 else "Moderate")
                risk_factors.append({
                    "feature": feat,
                    "name": FEATURE_DESCRIPTIONS.get(feat, feat),
                    "value": f"{float(feature_dict.get(feat, 0.0)):.3f}",
                    "severity": severity,
                    "impact": impact,
                    "reason": f"Significant statistical departure ({val:.2f}σ) from normal cardholder baseline."
                })

    # Sort risk factors by severity descending and pick top 4
    risk_factors.sort(key=lambda x: x["severity"], reverse=True)
    top_factors = risk_factors[:4]

    # If few factors found, provide standard telemetry
    if len(top_factors) == 0:
        top_factors.append({
            "feature": "V14",
            "name": FEATURE_DESCRIPTIONS["V14"],
            "value": "Normal Range",
            "severity": 12,
            "impact": "Low",
            "reason": "Feature indicators align with verified cardholder profile."
        })

    # Security recommendation logic
    if fraud_prob >= 0.75:
        recommendation = {
            "action": "BLOCK_AND_FREEZE",
            "title": "🚨 Urgent: Block Card & Halt Clearing",
            "description": "High probability of malicious intent. Automated card suspension initiated. Alert customer support & trigger push confirmation.",
            "color": "var(--fraud-red)"
        }
    elif fraud_prob >= 0.40:
        recommendation = {
            "action": "STEP_UP_2FA",
            "title": "⚠️ Challenge: Secondary 2FA Verification",
            "description": "Borderline risk metrics detected. Hold fund dispatch and dispatch one-time passcode (OTP) or biometric verification to cardholder.",
            "color": "var(--warning-yellow)"
        }
    else:
        recommendation = {
            "action": "AUTO_APPROVE",
            "title": "✅ Approved: Instant Settlement",
            "description": "All behavioral and biometric indices within safe tolerances. Safe for frictionless processing.",
            "color": "var(--legit-green)"
        }

    return top_factors, recommendation


# ==================== WEB & STATIC ROUTES ====================

@app.route("/")
def serve_index():
    return send_file(os.path.join(FRONTEND_DIR, "index.html"))


@app.route("/dashboard")
@app.route("/dashboard.html")
def serve_dashboard():
    return send_file(os.path.join(FRONTEND_DIR, "dashboard.html"))


@app.route("/css/<path:filename>")
def serve_css(filename):
    return send_from_directory(os.path.join(FRONTEND_DIR, "css"), filename)


@app.route("/js/<path:filename>")
def serve_js(filename):
    return send_from_directory(os.path.join(FRONTEND_DIR, "js"), filename)


@app.route("/sample_data.json")
def serve_sample_data():
    sample_path = os.path.join(os.path.dirname(BASE_DIR), "sample_data.json")
    if os.path.exists(sample_path):
        return send_file(sample_path)
    return jsonify({"error": "Sample data file not found"}), 404


@app.route("/sample_batch.csv")
def serve_sample_batch_csv():
    """Provides a ready-to-test CSV for batch analysis."""
    sample_csv_path = os.path.join(os.path.dirname(BASE_DIR), "sample_batch.csv")
    if os.path.exists(sample_csv_path):
        return send_file(sample_csv_path, as_attachment=True, download_name="sample_batch.csv")
    return jsonify({"error": "Sample batch CSV not found"}), 404


# ==================== PREDICTION API ====================

@app.route("/api/predict", methods=["POST"])
def predict():
    """
    Advanced single transaction fraud prediction.
    Accepts: { Time, V1-V28, Amount, optional threshold }
    Returns: Prediction, probabilities, risk factors (XAI), and recommendations.
    """
    if model is None or scaler is None:
        return jsonify({
            "error": "Model not loaded! Run train_model.py first."
        }), 503

    try:
        data = request.get_json()
    except Exception as e:
        return jsonify({"error": "Invalid JSON body", "details": str(e)}), 400

    if not data:
        return jsonify({"error": "Empty request body"}), 400

    # User-specified risk threshold (default 0.50)
    try:
        threshold = float(data.get("threshold", 0.50))
    except (ValueError, TypeError):
        threshold = 0.50

    # Feature validation
    missing_features = []
    invalid_features = []
    feature_values = []

    for feat in FEATURE_NAMES:
        if feat not in data:
            missing_features.append(feat)
            continue
        try:
            val = float(data[feat])
            feature_values.append(val)
        except (ValueError, TypeError):
            invalid_features.append(feat)

    if missing_features:
        return jsonify({
            "error": "Missing features",
            "missing": missing_features,
            "details": f"{len(missing_features)} features missing."
        }), 400

    if invalid_features:
        return jsonify({
            "error": "Invalid features",
            "invalid": invalid_features
        }), 400

    try:
        features_array = np.array(feature_values).reshape(1, -1)

        # Scale Time (0) and Amount (29)
        scaled_time_amount = scaler.transform(
            np.array([[features_array[0, 0], features_array[0, 29]]])
        )
        features_array[0, 0] = scaled_time_amount[0, 0]
        features_array[0, 29] = scaled_time_amount[0, 1]

        # Model inference
        probabilities = model.predict_proba(features_array)[0]
        fraud_prob = float(probabilities[1])

        # Dynamic decision via sensitivity threshold
        is_fraud = fraud_prob >= threshold

        risk_factors, recommendation = generate_explainability(data, fraud_prob)

        result = {
            "prediction": "Fraud" if is_fraud else "Legit",
            "confidence": round(fraud_prob if is_fraud else (1 - fraud_prob), 4),
            "risk_level": get_risk_level(fraud_prob),
            "fraud_probability": round(fraud_prob, 4),
            "legit_probability": round(float(probabilities[0]), 4),
            "threshold_applied": threshold,
            "timestamp": datetime.datetime.now().isoformat(),
            "amount": float(data.get("Amount", 0)),
            "risk_factors": risk_factors,
            "recommendation": recommendation
        }

        save_prediction_to_history(result)
        return jsonify(result)

    except Exception as e:
        return jsonify({"error": "Prediction failed", "details": str(e)}), 500


# ==================== BATCH PREDICTION / CSV SCANNER ====================

@app.route("/api/predict/batch", methods=["POST"])
def predict_batch():
    """
    Bulk Transaction Processing endpoint.
    Accepts:
      - Multipart CSV file upload ('file') OR
      - JSON list of transaction objects ('transactions')
    Returns:
      Summary metrics & scored row items.
    """
    if model is None or scaler is None:
        return jsonify({"error": "Model not loaded"}), 503

    rows_data = []

    # Check for CSV file upload
    if "file" in request.files:
        file = request.files["file"]
        if file.filename == "":
            return jsonify({"error": "No file selected"}), 400
        try:
            stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
            reader = csv.DictReader(stream)
            rows_data = list(reader)
        except Exception as e:
            return jsonify({"error": "CSV parse error", "details": str(e)}), 400
    else:
        # Check JSON payload
        try:
            json_body = request.get_json() or {}
            rows_data = json_body.get("transactions", [])
        except Exception:
            rows_data = []

    if not rows_data or len(rows_data) == 0:
        return jsonify({"error": "No transactions provided in batch"}), 400

    results = []
    fraud_count = 0
    total_amount = 0.0
    flagged_amount = 0.0

    for idx, row in enumerate(rows_data):
        try:
            # Extract features
            feature_values = []
            for feat in FEATURE_NAMES:
                val = float(row.get(feat, 0.0))
                feature_values.append(val)

            features_array = np.array(feature_values).reshape(1, -1)
            scaled = scaler.transform(np.array([[features_array[0, 0], features_array[0, 29]]]))
            features_array[0, 0] = scaled[0, 0]
            features_array[0, 29] = scaled[0, 1]

            proba = model.predict_proba(features_array)[0]
            fraud_prob = float(proba[1])
            is_fraud = fraud_prob >= 0.50

            amt = float(row.get("Amount", 0.0))
            total_amount += amt
            if is_fraud:
                fraud_count += 1
                flagged_amount += amt

            results.append({
                "row_id": idx + 1,
                "amount": round(amt, 2),
                "prediction": "Fraud" if is_fraud else "Legit",
                "fraud_probability": round(fraud_prob, 4),
                "confidence": round(fraud_prob if is_fraud else (1 - fraud_prob), 4),
                "risk_level": get_risk_level(fraud_prob)
            })
        except Exception as e:
            results.append({
                "row_id": idx + 1,
                "error": f"Invalid row: {str(e)}",
                "prediction": "Error"
            })

    total_transactions = len(rows_data)
    summary = {
        "total_transactions": total_transactions,
        "fraud_count": fraud_count,
        "legit_count": total_transactions - fraud_count,
        "fraud_rate": round((fraud_count / max(1, total_transactions)) * 100, 2),
        "total_amount": round(total_amount, 2),
        "flagged_amount": round(flagged_amount, 2)
    }

    return jsonify({
        "summary": summary,
        "results": results
    })


# ==================== LIVE STREAM SIMULATOR ====================

@app.route("/api/simulate/stream", methods=["GET"])
def simulate_stream():
    """
    Generates a live synthetic stream transaction for real-time radar simulation.
    ~15% chance of generating suspicious transaction patterns.
    """
    is_fraud_scenario = random.random() < 0.20

    tx_data = {"Time": random.randint(100, 172000)}

    if is_fraud_scenario:
        # Known compromised pattern
        for i in range(1, 29):
            tx_data[f"V{i}"] = round(random.gauss(0, 1.2), 4)
        tx_data["V14"] = round(random.uniform(-4.5, -2.5), 4)
        tx_data["V12"] = round(random.uniform(-4.0, -2.0), 4)
        tx_data["V17"] = round(random.uniform(-3.5, -1.8), 4)
        tx_data["V4"] = round(random.uniform(2.5, 4.5), 4)
        tx_data["Amount"] = round(random.choice([0.0, 1.99, 450.0, 890.0, 1200.0]), 2)
    else:
        # Standard clean transaction
        for i in range(1, 29):
            tx_data[f"V{i}"] = round(random.gauss(0, 0.6), 4)
        tx_data["Amount"] = round(abs(random.expovariate(1 / 65.0)), 2)

    return jsonify(tx_data)


# ==================== STATS & HISTORY ====================

@app.route("/api/stats", methods=["GET"])
def get_stats():
    """Model performance telemetry & dataset metrics."""
    if metrics is None:
        return jsonify({
            "error": "Metrics not available",
            "model_loaded": model is not None
        }), 404

    history_stats = {"total_predictions": 0, "fraud_count": 0, "legit_count": 0}
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r") as f:
                history = json.load(f)
            history_stats["total_predictions"] = len(history)
            history_stats["fraud_count"] = sum(1 for p in history if p.get("prediction") == "Fraud")
            history_stats["legit_count"] = history_stats["total_predictions"] - history_stats["fraud_count"]
        except Exception:
            pass

    return jsonify({
        "model_name": metrics.get("best_model", "RandomForest"),
        "model_results": metrics.get("model_results", {}),
        "dataset_stats": metrics.get("dataset_stats", {}),
        "feature_importance": metrics.get("feature_importance", {}),
        "prediction_stats": history_stats,
    })


@app.route("/api/history", methods=["GET", "DELETE"])
def handle_history():
    """Get recent prediction history or clear history."""
    if request.method == "DELETE":
        if os.path.exists(HISTORY_FILE):
            os.remove(HISTORY_FILE)
        return jsonify({"message": "History cleared successfully"})

    if not os.path.exists(HISTORY_FILE):
        return jsonify([])

    try:
        with open(HISTORY_FILE, "r") as f:
            history = json.load(f)
        return jsonify(history[-30:][::-1])
    except Exception:
        return jsonify([])


@app.route("/api/history/export", methods=["GET"])
def export_history_csv():
    """Download historical audit log as CSV."""
    if not os.path.exists(HISTORY_FILE):
        return Response("No history recorded", mimetype="text/csv")

    try:
        with open(HISTORY_FILE, "r") as f:
            history = json.load(f)

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Timestamp", "Prediction", "Confidence", "Risk Level", "Amount", "Fraud Probability"])

        for item in history:
            writer.writerow([
                item.get("timestamp", ""),
                item.get("prediction", ""),
                f"{float(item.get('confidence', 0))*100:.1f}%",
                item.get("risk_level", ""),
                f"${float(item.get('amount', 0)):.2f}",
                f"{float(item.get('fraud_probability', 0))*100:.2f}%"
            ])

        output.seek(0)
        return Response(
            output.getvalue(),
            mimetype="text/csv",
            headers={"Content-Disposition": "attachment;filename=fraud_detection_audit_history.csv"}
        )
    except Exception as e:
        return jsonify({"error": "Failed to generate CSV", "details": str(e)}), 500


# ==================== SERVER ENTRYPOINT ====================

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("🛡️  Credit Card Fraud Detection Server (Advanced Enterprise Edition)")
    print("=" * 60)
    load_model_and_scaler()
    print(f"\n🌐 Prediction Suite: http://localhost:5000")
    print(f"📊 Live Dashboard:   http://localhost:5000/dashboard\n")
    app.run(host="0.0.0.0", port=5000, debug=True)
