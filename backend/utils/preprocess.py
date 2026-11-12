"""
preprocess.py - Feature Engineering Helpers
Yeh module data ko model ke liye ready karta hai (scaling, validation, etc.)
"""

import numpy as np
import joblib
import os

# Model aur scaler files ka path define karo
MODEL_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "model")
MODEL_PATH = os.path.join(MODEL_DIR, "fraud_model.pkl")
SCALER_PATH = os.path.join(MODEL_DIR, "scaler.pkl")

# Saare 30 features jo model ko chahiye
FEATURE_NAMES = ["Time"] + [f"V{i}" for i in range(1, 29)] + ["Amount"]


def validate_input(data: dict) -> tuple:
    """
    Input data ko validate karo - saare 30 features hone chahiye aur numeric hone chahiye.
    Returns: (is_valid: bool, error_message: str or None, features: list or None)
    """
    missing = []
    invalid = []
    features = []

    for feat in FEATURE_NAMES:
        if feat not in data:
            missing.append(feat)
            continue
        try:
            # String ya kuch bhi ho, float mein convert karo
            val = float(data[feat])
            features.append(val)
        except (ValueError, TypeError):
            invalid.append(feat)

    if missing:
        return False, f"Missing features: {', '.join(missing)}", None
    if invalid:
        return False, f"Invalid (non-numeric) features: {', '.join(invalid)}", None

    return True, None, features


def scale_features(features: list, scaler=None) -> np.ndarray:
    """
    Features ko scale karo - Amount aur Time columns ko StandardScaler se transform karo.
    Baaki V1-V28 pehle se PCA transformed hain, unko as-is rakhna hai.
    """
    features_array = np.array(features).reshape(1, -1)

    if scaler is None:
        # Agar scaler nahi diya toh file se load karo
        if not os.path.exists(SCALER_PATH):
            raise FileNotFoundError(
                "Scaler file nahi mili! Pehle train_model.py chalaao."
            )
        scaler = joblib.load(SCALER_PATH)

    # Sirf Time (index 0) aur Amount (index 29) ko scale karo
    features_array[0, 0] = scaler.transform([[features_array[0, 0], features_array[0, 29]]])[0, 0]
    features_array[0, 29] = scaler.transform([[features_array[0, 0], features_array[0, 29]]])[0, 1]

    return features_array


def get_risk_level(confidence: float) -> str:
    """
    Confidence score ke basis par risk level decide karo.
    HIGH: 80%+, MEDIUM: 50-80%, LOW: 50% se neeche
    """
    if confidence >= 0.80:
        return "HIGH"
    elif confidence >= 0.50:
        return "MEDIUM"
    else:
        return "LOW"


def load_model():
    """
    Trained model ko file se load karo.
    Agar model file nahi hai toh error dega.
    """
    if not os.path.exists(MODEL_PATH):
        raise FileNotFoundError(
            "Model file nahi mili! Pehle train_model.py chalaao."
        )
    return joblib.load(MODEL_PATH)


def load_scaler():
    """
    Trained scaler ko file se load karo.
    """
    if not os.path.exists(SCALER_PATH):
        raise FileNotFoundError(
            "Scaler file nahi mili! Pehle train_model.py chalaao."
        )
    return joblib.load(SCALER_PATH)
