"""
train_model.py - Credit Card Fraud Detection Model Training
Yeh script model ko train karta hai aur save karta hai.
Agar creditcard.csv nahi milta toh synthetic data generate karta hai demo ke liye.
"""

import os
import sys
import pickle
import warnings
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    confusion_matrix,
    classification_report,
)

# SMOTE for handling class imbalance - fraud bahut kam hai (~0.17%)
from imblearn.over_sampling import SMOTE

warnings.filterwarnings("ignore")

# Paths set karo - model directory mein save hoga
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(SCRIPT_DIR, "fraud_model.pkl")
SCALER_PATH = os.path.join(SCRIPT_DIR, "scaler.pkl")
METRICS_PATH = os.path.join(SCRIPT_DIR, "metrics.pkl")

# Dataset ka path - project root mein ya model folder mein dhoondo
PROJECT_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))
DATASET_PATHS = [
    os.path.join(PROJECT_ROOT, "creditcard.csv"),
    os.path.join(SCRIPT_DIR, "creditcard.csv"),
    os.path.join(os.path.dirname(SCRIPT_DIR), "creditcard.csv"),
]


def generate_synthetic_data(n_samples=10000, fraud_ratio=0.017):
    """
    Synthetic data generate karo jab real dataset available nahi ho.
    Real dataset ki tarah 30 features + Class column banega.
    Fraud ratio ~1.7% rakhte hain (real data ke similar).
    """
    print("\n⚠️  creditcard.csv nahi mili! Synthetic data generate kar rahe hain...")
    print(f"   Total samples: {n_samples}, Fraud ratio: {fraud_ratio*100:.1f}%\n")

    from sklearn.datasets import make_classification

    n_fraud = int(n_samples * fraud_ratio)
    n_legit = n_samples - n_fraud

    # 28 PCA features generate karo (V1-V28 ke liye)
    X, y = make_classification(
        n_samples=n_samples,
        n_features=28,
        n_informative=15,
        n_redundant=5,
        n_classes=2,
        weights=[1 - fraud_ratio, fraud_ratio],
        random_state=42,
        flip_y=0.01,
    )

    # DataFrame banao real dataset jaisa
    columns = [f"V{i}" for i in range(1, 29)]
    df = pd.DataFrame(X, columns=columns)

    # Time column add karo (0 se 172792 tak, real data ki tarah)
    df.insert(0, "Time", np.sort(np.random.uniform(0, 172792, n_samples)))

    # Amount column add karo (realistic transaction amounts)
    # Legit transactions usually chhote hote hain, fraud mein variation zyada hoti hai
    amounts = np.where(
        y == 0,
        np.random.exponential(scale=88, size=n_samples),  # Legit: avg ~$88
        np.random.exponential(scale=122, size=n_samples),  # Fraud: avg ~$122
    )
    df["Amount"] = np.round(np.abs(amounts), 2)

    # Class column (0 = Legit, 1 = Fraud)
    df["Class"] = y

    print(f"✅ Synthetic dataset ready: {df.shape[0]} rows, {df.shape[1]} columns")
    return df


def load_dataset():
    """
    Dataset load karo - pehle real CSV dhoondo, nahi mili toh synthetic banao.
    """
    for path in DATASET_PATHS:
        if os.path.exists(path):
            print(f"📂 Dataset found: {path}")
            df = pd.read_csv(path)
            print(f"✅ Loaded: {df.shape[0]} rows, {df.shape[1]} columns")
            return df

    # Real dataset nahi mili, synthetic generate karo
    return generate_synthetic_data()


def analyze_dataset(df):
    """
    Dataset ka analysis karo - class distribution, basic stats, etc.
    """
    print("\n" + "=" * 60)
    print("📊 DATASET ANALYSIS")
    print("=" * 60)

    total = len(df)
    fraud = df["Class"].sum()
    legit = total - fraud

    print(f"\n   Total Transactions : {total:,}")
    print(f"   Legitimate (0)     : {legit:,} ({legit/total*100:.2f}%)")
    print(f"   Fraudulent (1)     : {fraud:,} ({fraud/total*100:.2f}%)")
    print(f"\n   Class Imbalance Ratio: 1:{legit//max(fraud, 1)}")
    print(f"\n   Amount Stats:")
    print(f"     Mean  : ${df['Amount'].mean():.2f}")
    print(f"     Median: ${df['Amount'].median():.2f}")
    print(f"     Max   : ${df['Amount'].max():.2f}")

    return {
        "total_transactions": int(total),
        "legit_count": int(legit),
        "fraud_count": int(fraud),
        "fraud_percentage": round(fraud / total * 100, 4),
        "amount_mean": round(df["Amount"].mean(), 2),
        "amount_median": round(df["Amount"].median(), 2),
        "amount_max": round(df["Amount"].max(), 2),
    }


def train_and_evaluate():
    """
    Main training function:
    1. Data load karo
    2. Features scale karo
    3. SMOTE se balance karo
    4. RandomForest aur LogisticRegression dono train karo
    5. Best model save karo
    """
    print("\n🚀 Credit Card Fraud Detection - Model Training")
    print("=" * 60)

    # Step 1: Data load karo
    df = load_dataset()
    dataset_stats = analyze_dataset(df)

    # Step 2: Features aur target alag karo
    X = df.drop("Class", axis=1)
    y = df["Class"]

    # Step 3: Amount aur Time ko scale karo
    # V1-V28 already PCA transformed hain, unko scaling ki zaroorat nahi
    print("\n🔧 Scaling 'Time' and 'Amount' features...")
    scaler = StandardScaler()
    X[["Time", "Amount"]] = scaler.fit_transform(X[["Time", "Amount"]])

    # Step 4: Train-Test split (80-20)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    print(f"\n📦 Train set: {X_train.shape[0]} samples")
    print(f"📦 Test set : {X_test.shape[0]} samples")

    # Step 5: SMOTE apply karo - fraud samples ko oversample karo
    print("\n⚖️  Applying SMOTE to handle class imbalance...")
    smote = SMOTE(random_state=42)
    X_train_balanced, y_train_balanced = smote.fit_resample(X_train, y_train)
    print(f"   Before SMOTE: {dict(zip(*np.unique(y_train, return_counts=True)))}")
    print(
        f"   After SMOTE : {dict(zip(*np.unique(y_train_balanced, return_counts=True)))}"
    )

    # Step 6: Dono models train karo aur compare karo
    models = {
        "RandomForest": RandomForestClassifier(
            n_estimators=100, random_state=42, n_jobs=-1
        ),
        "LogisticRegression": LogisticRegression(
            max_iter=1000, random_state=42
        ),
    }

    results = {}
    best_model_name = None
    best_f1 = 0

    for name, model in models.items():
        print(f"\n{'='*60}")
        print(f"🤖 Training {name}...")
        print("=" * 60)

        model.fit(X_train_balanced, y_train_balanced)
        y_pred = model.predict(X_test)
        y_proba = model.predict_proba(X_test)[:, 1]

        # Metrics calculate karo
        acc = accuracy_score(y_test, y_pred)
        prec = precision_score(y_test, y_pred, zero_division=0)
        rec = recall_score(y_test, y_pred, zero_division=0)
        f1 = f1_score(y_test, y_pred, zero_division=0)
        roc = roc_auc_score(y_test, y_proba)
        cm = confusion_matrix(y_test, y_pred)

        results[name] = {
            "accuracy": round(acc, 4),
            "precision": round(prec, 4),
            "recall": round(rec, 4),
            "f1_score": round(f1, 4),
            "roc_auc": round(roc, 4),
            "confusion_matrix": cm.tolist(),
        }

        print(f"\n   Accuracy  : {acc:.4f}")
        print(f"   Precision : {prec:.4f}")
        print(f"   Recall    : {rec:.4f}")
        print(f"   F1-Score  : {f1:.4f}")
        print(f"   ROC-AUC   : {roc:.4f}")
        print(f"\n   Confusion Matrix:")
        print(f"   {cm}")
        print(f"\n{classification_report(y_test, y_pred, target_names=['Legit', 'Fraud'])}")

        # Best model track karo (F1-score ke basis par)
        if f1 > best_f1:
            best_f1 = f1
            best_model_name = name

    # Step 7: Best model save karo
    best_model = models[best_model_name]
    print(f"\n{'='*60}")
    print(f"🏆 Best Model: {best_model_name} (F1: {best_f1:.4f})")
    print("=" * 60)

    # Feature importance nikalo (RandomForest ke liye)
    feature_importance = {}
    if best_model_name == "RandomForest":
        importances = best_model.feature_importances_
        feature_names = X.columns.tolist()
        importance_pairs = sorted(
            zip(feature_names, importances), key=lambda x: x[1], reverse=True
        )
        feature_importance = {name: round(float(imp), 6) for name, imp in importance_pairs[:15]}
        print("\n📊 Top 10 Feature Importances:")
        for i, (feat, imp) in enumerate(importance_pairs[:10], 1):
            bar = "█" * int(imp * 100)
            print(f"   {i:2d}. {feat:8s}: {imp:.6f} {bar}")
    else:
        # LogisticRegression ke liye coefficients use karo
        coeffs = np.abs(best_model.coef_[0])
        feature_names = X.columns.tolist()
        importance_pairs = sorted(
            zip(feature_names, coeffs), key=lambda x: x[1], reverse=True
        )
        feature_importance = {name: round(float(imp), 6) for name, imp in importance_pairs[:15]}

    # Model aur scaler save karo
    print(f"\n💾 Saving model to: {MODEL_PATH}")
    with open(MODEL_PATH, "wb") as f:
        pickle.dump(best_model, f)

    print(f"💾 Saving scaler to: {SCALER_PATH}")
    with open(SCALER_PATH, "wb") as f:
        pickle.dump(scaler, f)

    # Metrics bhi save karo (API ke liye chahiye honge)
    metrics = {
        "best_model": best_model_name,
        "model_results": results,
        "dataset_stats": dataset_stats,
        "feature_importance": feature_importance,
    }
    print(f"💾 Saving metrics to: {METRICS_PATH}")
    with open(METRICS_PATH, "wb") as f:
        pickle.dump(metrics, f)

    print("\n✅ Training complete! Ab app.py chalaa ke server start karo.")
    print("   Command: python app.py")
    return metrics


if __name__ == "__main__":
    train_and_evaluate()
