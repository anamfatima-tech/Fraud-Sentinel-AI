# 🛡️ FraudSentinel AI - Enterprise Credit Card Fraud Detection Suite

An advanced, full-stack, enterprise-grade AI solution for real-time credit card fraud prevention, explainability, batch file scanning, and security operations center (SOC) telemetry.

---

## ✨ Advanced Enterprise Features

1. **🧠 Explainable AI (XAI) & Anomaly Attribution**:
   - Beyond a binary "Fraud/Legit" verdict, the system reveals the **exact risk drivers** (e.g., statistical deviations in authentication vectors $V_{14}, V_{12}, V_{10}$, transaction velocity $V_4$, or unusual spending volume).
   - Provides severity percentage and statistical anomaly standard-deviation scores ($\sigma$).

2. **⚡ Actionable Security Incident Recommendations**:
   - Automatically directs banking operators with real-world recommendations:
     - 🚨 **Immediate Block & Freeze**: Suspends clearing and flags cardholder.
     - ⚠️ **Step-Up 2FA Challenge**: Holds funds in escrow and prompts SMS/biometric verification.
     - ✅ **Frictionless Auto-Approve**: Instant settlement for clean risk profiles.

3. **🎛️ Dynamic Sensitivity Threshold Controller**:
   - Adjustable threshold slider ($10\% - 90\%$).
   - Banks can tune sensitivity during high-risk holiday sales seasons to catch aggressive fraud or relax it to minimize false positives.

4. **📁 Bulk CSV Transaction Scanner**:
   - Drag-and-drop or upload CSV spreadsheets of transactions.
   - Instantly scores batches, calculates total financial exposure, and renders an interactive risk manifest with filter buttons (`All`, `Fraud Only`, `Clean Only`).
   - Includes ready-to-test `sample_batch.csv` download.

5. **⚡ Live Radar Stream Simulator**:
   - Continuous simulated ingestion feed processing live transactions every ~2 seconds with visual/audio threat interception alerts.

6. **🔊 Web Audio API Sound Synthesizer**:
   - Real-time synthesized audio alerts (880Hz alert tone on fraud detection; 523Hz chime on clean transactions). Zero external audio dependencies.

7. **📊 SOC Analytics Dashboard & Historical CSV Export**:
   - Interactive Chart.js class distribution, live threat timelines, and feature importance attribution charts.
   - One-click **Export Audit CSV** and **Print Investigation Dossier** for compliance.

---

## 📁 Project Architecture

```
credit-card-fraud-detection/
│
├── start.bat                     # ⚡ 1-Click launcher for Windows
├── sample_batch.csv              # 📁 Ready-to-upload batch test spreadsheet
├── sample_data.json              # 📋 3 legit + 3 fraud test transactions
├── README.md                     # 📖 Project documentation
│
├── backend/
│   ├── app.py                    # 🐍 Advanced Flask API server & XAI engine
│   ├── prediction_history.json   # 💾 Persistent audit log file
│   ├── requirements.txt          # 📦 Python library dependencies
│   │
│   ├── model/
│   │   ├── train_model.py        # 🏋️ ML Training script (SMOTE + Random Forest)
│   │   ├── fraud_model.pkl       # 🤖 Trained ML model
│   │   ├── scaler.pkl            # 📏 StandardScaler object
│   │   └── metrics.pkl           # 📊 Evaluation telemetry & feature importances
│   │
│   └── utils/
│       └── preprocess.py         # 🛠️ Data validation & scaling helpers
│
└── frontend/
    ├── index.html                # 🖥️ Suite interface (Single, Batch Scanner, Live Radar)
    ├── dashboard.html            # 📊 SOC Analytics & Telemetry dashboard
    ├── css/
    │   └── style.css             # 🎨 Modern clean light-white theme
    └── js/
        ├── main.js               # ⚡ Frontend controller (XAI, audio, batch, stream)
        └── dashboard.js          # 📈 Chart.js visualization engine & audit management
```

---

## 🚀 Quickstart Guide

### Option 1: 1-Click Launch (Windows)
Double-click `start.bat` in the project root. It starts the backend server and launches your browser automatically at `http://localhost:5000`.

### Option 2: Manual Terminal Launch
```bash
# 1. Install dependencies
cd backend
pip install -r requirements.txt

# 2. Train Model (Optional - pre-trained models already included)
python model/train_model.py

# 3. Launch Flask Server
python app.py
```

Then open:
- 🔍 **Fraud Detection Suite**: [http://localhost:5000](http://localhost:5000)
- 📊 **SOC Analytics Dashboard**: [http://localhost:5000/dashboard](http://localhost:5000/dashboard)

---

## 📖 Detailed Step-by-Step Guide (Shuru Se Aakhir Tak Yeh Project Kaise Bana Hai)

Yahan is project ke banne ki puri kahani aur technical details di gayi hain:

### Phase 1: Problem & Machine Learning Pipeline (`backend/model/`)

1. **Dataset Samjhna**:
   - Dataset me 30 features hote hain:
     - `Time`: Pehli transaction ke baad beete hue seconds.
     - `Amount`: Transaction kitne dollars ki hai.
     - `V1 se V28`: Customer privacy aur banking secrets chupane ke liye bank ne actual features (cardholder age, location, merchant, etc.) par **PCA (Principal Component Analysis)** lagaya hua hai.
     - `Class`: `0` = Legitimate (Clean), `1` = Fraudulent.

2. **Class Imbalance Problem & SMOTE Solution**:
   - Real-world credit card data me fraud sirf **~0.17%** hota hai (yaani 1,000 me se sirf 1-2 fraud).
   - Agar normal model train karenge toh woh sabko "Legit" predict karega aur 99.8% accuracy dikhayega, lekin ek bhi fraud nahi pakad payega!
   - **Solution**: Humne `imblearn` library se **SMOTE (Synthetic Minority Over-sampling Technique)** use kiya. SMOTE ne fraud class ke mathematical synthetic samples create karke training set ko 50:50 balance kiya.

3. **Feature Normalization (`StandardScaler`)**:
   - `V1-V28` pehle se zero-mean normalized hote hain, lekin `Time` (0 se 1,72,000) aur `Amount` ($0 se $25,000) ka scale bahut bada hota hai.
   - Humne `StandardScaler` se sirf `Time` aur `Amount` ko normalize kiya aur scaler ko `scaler.pkl` me save kiya.

4. **Model Training & Comparison (`train_model.py`)**:
   - Humne **Random Forest Classifier** (`n_estimators=100`) aur **Logistic Regression** dono ko train karke compare kiya.
   - Random Forest ne **97.9%+ Accuracy**, high Precision aur strong ROC-AUC score achieve kiya.
   - Best model ko `fraud_model.pkl` me aur evaluation metrics ko `metrics.pkl` me dump kiya.

---

### Phase 2: Backend Flask API Engine (`backend/app.py`)

Backend server Python Flask me banaya gaya hai aur isme 6 primary endpoints hain:

| Endpoint | Method | Kaam Kya Hai? |
|---|---|---|
| `/` | `GET` | Main detection web page serve karta hai |
| `/dashboard` | `GET` | SOC Analytics Dashboard serve karta hai |
| `/api/predict` | `POST` | Single transaction ka fraud probability, Explainable AI factors aur security recommendation return karta hai |
| `/api/predict/batch` | `POST` | Upload ki gayi CSV file ko scan karke summary + scored rows manifest deta hai |
| `/api/simulate/stream`| `GET` | Live radar simulator ke liye real-time transaction telemetry emit karta hai |
| `/api/stats` | `GET` | Model metrics aur top 10 feature importance weights return karta hai |
| `/api/history/export` | `GET` | Transaction audit log ko downloadable CSV file me export karta hai |

---

### Phase 3: Explainable AI (XAI) & Heuristic Rules

Bankers aur fraud analysts ko sirf "Fraud" bolna kaafi nahi hota. Humne backend me Explainability engine likha:
- Yeh feature values ka standard deviation check karta hai ($|\sigma| > 1.8$).
- Agar $V_{14}, V_{12}, V_{10}, V_4$ me extreme departure ho ya transaction amount unusually high ho, toh woh specific risk factors unke real-world meaning ke sath return karta hai.
- Iske sath 3-tier action recommendations generate hoti hain:
  - 🚨 **`BLOCK_AND_FREEZE`** ($Risk \ge 75\%$)
  - ⚠️ **`STEP_UP_2FA`** ($40\% \le Risk < 75\%$)
  - ✅ **`AUTO_APPROVE`** ($Risk < 40\%$)

---

### Phase 4: Frontend UI/UX Design (`frontend/`)

1. **Light White Modern Theme (`style.css`)**:
   - Slate-white background (`#f1f5f9`), crisp white cards (`#ffffff`), soft multi-layered box shadows aur Google Font **Inter**.
   - V1-V28 features ke liye 4 collapsible accordion cards banaye gaye taaki page clutter-free rahe.

2. **3-in-1 View Switcher (`main.js`)**:
   - **Single Transaction**: Quick test buttons (`Load Sample Fraud` / `Load Sample Legit`) ke sath.
   - **Bulk CSV Scanner**: Drag & drop CSV box + instant filter buttons (`All`, `Fraud Only`, `Clean Only`).
   - **Live Radar Stream**: Real-time simulated threat ticker feed.

3. **Synthesized Audio Alert System**:
   - Web Audio API ka use karke browser me bina kisi audio file ke programmatic sound beeps generate kiye:
     - Fraud detect hone par: **Urgent High-Pitch Beep (880Hz)**.
     - Clean transaction par: **Soft Confirmation Chime (523Hz)**.
     - Header me sound mute/unmute button.

4. **SOC Analytics Dashboard (`dashboard.js`)**:
   - **Chart.js** library se 3 high-contrast responsive charts:
     - Class distribution doughnut chart.
     - Threat timeline graph.
     - Top 10 feature importances horizontal bar chart.
   - One-click **Export Audit CSV** aur **Clear Logs** functionality.
