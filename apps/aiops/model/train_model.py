#!/usr/bin/env python3
"""
Lab 4.1 — AIOps: Train Isolation Forest Anomaly Detection Model
================================================================
Script này đọc CSV metrics từ Prometheus (do prometheus_collector.py tạo),
train mô hình Isolation Forest, và lưu model + scaler ra thư mục /model/.

Output files:
  - /model/anomaly_model.pkl   : Trained Isolation Forest model
  - /model/scaler.pkl          : StandardScaler (normalize input)
  - /model/threshold.txt       : Anomaly score threshold (percentile 95)
  - /model/model_info.json     : Metadata (training date, n_samples, features)

Cách dùng:
  python train_model.py \
    --input  /model/metrics_dataset.csv \
    --output /model
"""

import argparse
import json
import os
import sys
import warnings
from datetime import datetime, timezone

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

warnings.filterwarnings("ignore")

# ─────────────── Hyperparameters mặc định ─────────────────────────────── #

# contamination = ước tính % anomaly trong training data
# 0.05 = giả định 5% data trong quá khứ là bất thường (spike thoáng qua)
CONTAMINATION   = float(os.getenv("IF_CONTAMINATION", "0.05"))
N_ESTIMATORS    = int(os.getenv("IF_N_ESTIMATORS",   "200"))
RANDOM_STATE    = int(os.getenv("IF_RANDOM_STATE",   "42"))
THRESHOLD_PCT   = float(os.getenv("IF_THRESHOLD_PCT", "5"))   # percentile 5 (scores âm nhất)

FEATURE_COLS = [
    "cpu_usage_percent",
    "memory_usage_percent",
    "network_receive_bytes_per_sec",
]


# ────────────────────────── Training logic ────────────────────────────── #

def load_data(input_path: str) -> pd.DataFrame:
    print(f"[1/5] Đọc file: {input_path}")
    if not os.path.exists(input_path):
        print(f"[ERROR] File không tồn tại: {input_path}", file=sys.stderr)
        sys.exit(1)

    df = pd.read_csv(input_path)
    missing = [c for c in FEATURE_COLS if c not in df.columns]
    if missing:
        print(f"[ERROR] Thiếu cột: {missing}", file=sys.stderr)
        sys.exit(1)

    df = df[FEATURE_COLS].dropna()
    print(f"       Samples: {len(df)} | Features: {FEATURE_COLS}")
    return df


def normalize(df: pd.DataFrame):
    print("[2/5] Normalize dữ liệu (StandardScaler)...")
    scaler = StandardScaler()
    X = scaler.fit_transform(df[FEATURE_COLS])
    print(f"       Mean  : {scaler.mean_.round(3)}")
    print(f"       Scale : {scaler.scale_.round(3)}")
    return X, scaler


def train(X: np.ndarray):
    print(f"[3/5] Train Isolation Forest (n_estimators={N_ESTIMATORS}, contamination={CONTAMINATION})...")
    model = IsolationForest(
        n_estimators=N_ESTIMATORS,
        contamination=CONTAMINATION,
        random_state=RANDOM_STATE,
        n_jobs=-1,            # dùng tất cả CPU cores
        max_samples="auto",
    )
    model.fit(X)

    # Tính anomaly scores (âm càng nhiều = càng bất thường)
    scores = model.decision_function(X)
    print(f"       Score range : [{scores.min():.4f}, {scores.max():.4f}]")
    print(f"       Score mean  : {scores.mean():.4f}")

    return model, scores


def compute_threshold(scores: np.ndarray) -> float:
    """
    Threshold = percentile 5 của score phân phối training.
    Điểm nào thấp hơn threshold → ANOMALY.
    Dùng percentile 5 thay vì đường phân cách contamination cứng
    để tránh false positive.
    """
    threshold = float(np.percentile(scores, THRESHOLD_PCT))
    print(f"[4/5] Tính threshold (percentile {THRESHOLD_PCT}): {threshold:.6f}")
    return threshold


def save_artifacts(model, scaler, threshold: float, n_samples: int, output_dir: str):
    print(f"[5/5] Lưu artifacts vào: {output_dir}")
    os.makedirs(output_dir, exist_ok=True)

    model_path     = os.path.join(output_dir, "anomaly_model.pkl")
    scaler_path    = os.path.join(output_dir, "scaler.pkl")
    threshold_path = os.path.join(output_dir, "threshold.txt")
    info_path      = os.path.join(output_dir, "model_info.json")

    joblib.dump(model,  model_path)
    joblib.dump(scaler, scaler_path)

    with open(threshold_path, "w") as f:
        f.write(str(threshold))

    info = {
        "trained_at":      datetime.now(timezone.utc).isoformat(),
        "n_samples":       n_samples,
        "features":        FEATURE_COLS,
        "n_estimators":    N_ESTIMATORS,
        "contamination":   CONTAMINATION,
        "threshold_pct":   THRESHOLD_PCT,
        "threshold_value": threshold,
        "model_type":      "IsolationForest",
        "sklearn_version": __import__("sklearn").__version__,
    }
    with open(info_path, "w") as f:
        json.dump(info, f, indent=2)

    print(f"       ✓ {model_path}")
    print(f"       ✓ {scaler_path}")
    print(f"       ✓ {threshold_path}")
    print(f"       ✓ {info_path}")


def quick_validation(model, scaler, threshold: float):
    """
    Kiểm tra nhanh model với dữ liệu giả:
    - Normal: CPU 40%, RAM 60%, Network 1MB/s → KHÔNG phải anomaly
    - Spike:  CPU 99%, RAM 98%, Network 500MB/s → LÀ anomaly
    """
    print("\n── Validation nhanh ──────────────────────────────────────────")
    test_cases = [
        ("Normal traffic",  [40.0,  60.0,  1_000_000]),
        ("CPU spike",       [99.0,  65.0,  1_100_000]),
        ("Memory pressure", [55.0,  97.0,  980_000]),
        ("Network flood",   [45.0,  62.0,  500_000_000]),
        ("Full storm",      [98.0,  96.0,  450_000_000]),
    ]

    for label, values in test_cases:
        X_test    = scaler.transform([values])
        score     = model.decision_function(X_test)[0]
        is_anomaly = score < threshold
        status    = "🔴 ANOMALY" if is_anomaly else "🟢 Normal "
        print(f"  {status}  | Score: {score:+.4f} | {label}")
    print("──────────────────────────────────────────────────────────────")


# ─────────────────────────────── Main ─────────────────────────────────── #

def main():
    parser = argparse.ArgumentParser(description="AIOps Isolation Forest Trainer")
    parser.add_argument("--input",  default=os.getenv("INPUT_PATH",  "/model/metrics_dataset.csv"))
    parser.add_argument("--output", default=os.getenv("OUTPUT_PATH", "/model"))
    args = parser.parse_args()

    print("=" * 60)
    print("  AIOps Lab 4.1 — Isolation Forest Training")
    print("=" * 60)

    df       = load_data(args.input)
    X, scaler = normalize(df)
    model, scores = train(X)
    threshold     = compute_threshold(scores)
    save_artifacts(model, scaler, threshold, len(df), args.output)
    quick_validation(model, scaler, threshold)

    print("\n[✓] Training hoàn tất!")


if __name__ == "__main__":
    main()
