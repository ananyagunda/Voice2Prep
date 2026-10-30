"""Anomaly detection for Fairplay Radar player-level features."""

from __future__ import annotations

from typing import Final

import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler


_PLAYER_ID_COLUMN: Final[str] = "player_id"
_ANOMALY_LABEL_COLUMN: Final[str] = "anomaly_label"
_ANOMALY_SCORE_COLUMN: Final[str] = "anomaly_score"
_MINIMUM_PLAYERS: Final[int] = 5
_CONTAMINATION: Final[float] = 0.05
_RANDOM_STATE: Final[int] = 42


def _prepare_numeric_features(data: pd.DataFrame) -> pd.DataFrame:
    """Return finite numeric features with missing values safely imputed."""

    numeric = data.select_dtypes(include="number").drop(
        columns=[_PLAYER_ID_COLUMN], errors="ignore"
    )
    if numeric.empty:
        raise ValueError(
            "Anomaly detection requires at least one numeric feature column "
            "besides 'player_id'."
        )

    prepared = numeric.replace([float("inf"), float("-inf")], pd.NA)
    for column in prepared.columns:
        prepared[column] = pd.to_numeric(prepared[column], errors="coerce")
        median = prepared[column].median()
        prepared[column] = prepared[column].fillna(0.0 if pd.isna(median) else median)

    return prepared.astype(float)


def _fit_detector(features: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    """Scale features, fit Isolation Forest, and return labels and scores."""

    scaled_features = StandardScaler().fit_transform(features)
    detector = IsolationForest(
        contamination=_CONTAMINATION,
        random_state=_RANDOM_STATE,
    )
    detector.fit(scaled_features)

    labels = pd.Series(detector.predict(scaled_features), index=features.index)
    # Isolation Forest's decision function is higher for normal observations.
    # Negating it makes a larger returned score mean more suspicious behavior.
    scores = pd.Series(-detector.decision_function(scaled_features), index=features.index)
    return labels, scores


def detect_anomalies(data: pd.DataFrame) -> pd.DataFrame:
    """Detect unusual player behavior from player-level features.

    This function identifies statistical outliers; an anomaly is not a
    confirmation of fraud. Missing and infinite numeric values are replaced
    with the column median, or ``0.0`` when a column has no finite values.

    Args:
        data: Player-level features containing ``player_id`` and one or more
            numeric feature columns.

    Returns:
        A copy of ``data`` with ``anomaly_label`` (``-1`` for an anomaly and
        ``1`` for a normal player) and ``anomaly_score``. Higher scores are
        more suspicious.

    Raises:
        TypeError: If ``data`` is not a pandas DataFrame.
        ValueError: If player IDs or numeric features are missing, or fewer
            than five players are provided.
    """

    if not isinstance(data, pd.DataFrame):
        raise TypeError("Player features must be provided as a pandas DataFrame.")
    if _PLAYER_ID_COLUMN not in data.columns:
        raise ValueError("Player features must contain a 'player_id' column.")
    if len(data) < _MINIMUM_PLAYERS:
        raise ValueError(
            "Anomaly detection requires at least 5 players; "
            f"received {len(data)}."
        )
    if data[_PLAYER_ID_COLUMN].isna().any():
        raise ValueError("The 'player_id' column cannot contain missing values.")

    numeric_features = _prepare_numeric_features(data)
    labels, scores = _fit_detector(numeric_features)

    result = data.copy(deep=True)
    result[_ANOMALY_LABEL_COLUMN] = labels.to_numpy()
    result[_ANOMALY_SCORE_COLUMN] = scores.to_numpy()
    return result