"""End-to-end Fairplay Radar gameplay detection pipeline."""

from __future__ import annotations

import pandas as pd

from engine.anomaly_detector import detect_anomalies
from engine.feature_engineering import engineer_player_features
from engine.preprocessing import preprocess_gameplay_data
from engine.risk_scoring import calculate_risk_score


def run_detection_pipeline(data: pd.DataFrame) -> pd.DataFrame:
    """Run preprocessing, feature engineering, anomaly detection, and scoring.

    The output of each stage is passed directly to the next stage in the
    requested order. Anomalies are statistical screening signals and are not
    confirmed fraud.

    Args:
        data: Raw gameplay records as a pandas DataFrame.

    Returns:
        A player-level DataFrame containing engineered features, anomaly
        labels and scores, risk scores, risk reasons, and risk levels.

    Raises:
        TypeError: If ``data`` is not a pandas DataFrame.
        RuntimeError: If any pipeline stage fails. The original exception is
            preserved as the cause.
    """

    if not isinstance(data, pd.DataFrame):
        raise TypeError("Pipeline input must be provided as a pandas DataFrame.")

    try:
        preprocessed = preprocess_gameplay_data(data)
    except Exception as error:
        raise RuntimeError(f"Gameplay preprocessing failed: {error}") from error

    try:
        player_features = engineer_player_features(preprocessed)
    except Exception as error:
        raise RuntimeError(f"Player feature engineering failed: {error}") from error

    try:
        anomaly_features = detect_anomalies(player_features)
    except Exception as error:
        raise RuntimeError(f"Anomaly detection failed: {error}") from error

    try:
        return calculate_risk_score(anomaly_features)
    except Exception as error:
        raise RuntimeError(f"Risk scoring failed: {error}") from error