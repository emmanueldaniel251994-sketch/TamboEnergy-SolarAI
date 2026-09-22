import os
import sqlite3

import joblib
import matplotlib.pyplot as plt
import pandas as pd

from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    ConfusionMatrixDisplay
)
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder


# ============================================================
# PATHS
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

DB_PATH = os.path.join(
    BASE_DIR,
    "backend",
    "tamboenergy_solarai.db"
)

MODEL_PATH = os.path.join(
    BASE_DIR,
    "ml",
    "fault_model.joblib"
)

ENCODER_PATH = os.path.join(
    BASE_DIR,
    "ml",
    "label_encoder.joblib"
)

METRICS_PATH = os.path.join(
    BASE_DIR,
    "ml",
    "model_metrics.txt"
)

CONFUSION_MATRIX_PATH = os.path.join(
    BASE_DIR,
    "ml",
    "confusion_matrix.png"
)


# ============================================================
# LOAD TELEMETRY DATA
# ============================================================

connection = sqlite3.connect(
    DB_PATH
)

query = """
SELECT
    pv_voltage,
    pv_current,
    pv_power,
    battery_voltage,
    battery_current,
    battery_soc,
    load_power,
    temperature,
    error_code,
    fault_type
FROM telemetry
"""

df = pd.read_sql_query(
    query,
    connection
)

connection.close()


print("================================")
print("DATASET")
print("================================")

print(
    "Rows:",
    len(df)
)

print(
    "\nColumns:"
)

print(
    df.columns.tolist()
)


# ============================================================
# CLEAN DATA
# ============================================================

# Convert null fault labels to normal
df["fault_type"] = df[
    "fault_type"
].fillna(
    "normal"
)


# Convert error code into a binary feature
df["has_error_code"] = (
    df["error_code"]
    .notna()
    .astype(int)
)


# Remove raw string error code
df = df.drop(
    columns=[
        "error_code"
    ]
)


# Remove rows missing target
df = df.dropna(
    subset=[
        "fault_type"
    ]
)


# Fill missing numeric values
numeric_columns = [
    "pv_voltage",
    "pv_current",
    "pv_power",
    "battery_voltage",
    "battery_current",
    "battery_soc",
    "load_power",
    "temperature",
    "has_error_code"
]

for column in numeric_columns:

    df[column] = (
        df[column]
        .fillna(
            df[column].median()
        )
    )


# ============================================================
# FEATURES + TARGET
# ============================================================

FEATURE_COLUMNS = [
    "pv_voltage",
    "pv_current",
    "pv_power",
    "battery_voltage",
    "battery_current",
    "battery_soc",
    "load_power",
    "temperature",
    "has_error_code"
]


X = df[
    FEATURE_COLUMNS
]

y_text = df[
    "fault_type"
]


# ============================================================
# LABEL ENCODER
# ============================================================

label_encoder = LabelEncoder()

y = label_encoder.fit_transform(
    y_text
)


print(
    "\nClasses:"
)

for class_name in (
    label_encoder.classes_
):

    print(
        "-",
        class_name
    )


# ============================================================
# TRAIN / TEST SPLIT
# ============================================================

X_train, X_test, y_train, y_test = (
    train_test_split(
        X,
        y,
        test_size=0.20,
        random_state=42,
        stratify=y
    )
)


print(
    "\nTraining rows:",
    len(X_train)
)

print(
    "Testing rows:",
    len(X_test)
)


# ============================================================
# MODEL
# ============================================================

model = RandomForestClassifier(
    n_estimators=250,
    max_depth=None,
    random_state=42,
    class_weight="balanced",
    n_jobs=-1
)


# ============================================================
# TRAIN
# ============================================================

print("\n================================")
print("TRAINING MODEL")
print("================================")

model.fit(
    X_train,
    y_train
)


# ============================================================
# PREDICT
# ============================================================

predictions = model.predict(
    X_test
)


# ============================================================
# ACCURACY
# ============================================================

accuracy = accuracy_score(
    y_test,
    predictions
)


print(
    f"\nAccuracy: {accuracy:.4f}"
)


# ============================================================
# CLASSIFICATION REPORT
# ============================================================

report = classification_report(
    y_test,
    predictions,
    target_names=label_encoder.classes_,
    zero_division=0
)


print(
    "\nClassification Report:"
)

print(
    report
)


# ============================================================
# SAVE METRICS
# ============================================================

with open(
    METRICS_PATH,
    "w",
    encoding="utf-8"
) as file:

    file.write(
        f"Accuracy: {accuracy:.4f}\n\n"
    )

    file.write(
        report
    )


# ============================================================
# CONFUSION MATRIX
# ============================================================

ConfusionMatrixDisplay.from_predictions(
    y_test,
    predictions,
    display_labels=label_encoder.classes_,
    xticks_rotation=45
)

plt.title(
    "TamboEnergy SolarAI Fault Classifier"
)

plt.tight_layout()

plt.savefig(
    CONFUSION_MATRIX_PATH
)

plt.close()


# ============================================================
# SAVE MODEL
# ============================================================

joblib.dump(
    model,
    MODEL_PATH
)

joblib.dump(
    label_encoder,
    ENCODER_PATH
)


print("\n================================")
print("TRAINING COMPLETE")
print("================================")

print(
    "Model saved:"
)

print(
    MODEL_PATH
)

print(
    "\nLabel encoder saved:"
)

print(
    ENCODER_PATH
)

print(
    "\nMetrics saved:"
)

print(
    METRICS_PATH
)

print(
    "\nConfusion matrix saved:"
)

print(
    CONFUSION_MATRIX_PATH
)