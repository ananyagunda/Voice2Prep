"""Transparent rule-based risk scoring for Fairplay Radar players."""

from __future__ import annotations

from typing import Final, Literal

import pandas as pd


_PLAYER_ID_COLUMN: Final[str] = "player_id"
_RISK_SCORE_COLUMN: Final[str] = "risk_score"
_RISK_REASONS_COLUMN: Final[str] = "risk_reasons"
_RISK_LEVEL_COLUMN: Final[str] = "risk_level"
_ANOMALY_LABEL_COLUMN: Final[str] = "anomaly_label"

# Each signal contributes 20 points. Five signals therefore produce a
# maximum of 100 points, making the result easy to explain to dashboard users.
_SIGNAL_POINTS: Final[int] = 20
_KILLS_PER_MINUTE_LIMIT: Final[float] = 10.0
_SCORE_PER_MINUTE_LIMIT: Final[float] = 1_000.0
_ACTIONS_PER_MINUTE_LIMIT: Final[float] = 100.0
_ACTION_INTERVAL_LIMIT: Final[float] = 1.0


def _numeric_value(row: pd.Series, column: str) -> float | None:
    """Return a finite numeric value from a row, or ``None`` if unavailable."""

    if column not in row:
        return None
    value = pd.to_numeric(row[column], errors="coerce")
    if pd.isna(value) or not pd.api.types.is_number(value):
        return None
    value = float(value)
    return value if pd.notna(value) and value not in (float("inf"), float("-inf")) else None


def _score_player(row: pd.Series) -> tuple[int, str]:
    """Apply the documented rules to one player row."""

    score = 0
    reasons: list[str] = []
    signals = (
        (
            "average_kills_per_minute",
            _KILLS_PER_MINUTE_LIMIT,
            "very high average kills per minute",
            lambda value, limit: value > limit,
        ),
        (
            "average_score_per_minute",
            _SCORE_PER_MINUTE_LIMIT,
            "very high average score per minute",
            lambda value, limit: value > limit,
        ),
        (
            "average_actions_per_minute",
            _ACTIONS_PER_MINUTE_LIMIT,
            "very high average actions per minute",
            lambda value, limit: value > limit,
        ),
        (
            "average_action_interval",
            _ACTION_INTERVAL_LIMIT,
            "very low average action interval",
            lambda value, limit: value < limit,
        ),
    )
    for column, limit, reason, matches in signals:
        value = _numeric_value(row, column)
        if value is not None and matches(value, limit):
            score += _SIGNAL_POINTS
            reasons.append(f"{reason} (threshold: {limit:g})")

    anomaly_label = _numeric_value(row, _ANOMALY_LABEL_COLUMN)
    if anomaly_label == -1:
        score += _SIGNAL_POINTS
        reasons.append("Isolation Forest marked this player as anomalous")

    return min(score, 100), "; ".join(reasons) or "No risk signals detected"


def _risk_level(score: int) -> Literal["low", "medium", "high"]:
    """Map a 0-100 score to the exact ``low``, ``medium``, or ``high`` label."""

    if score >= 60:
        return "high"
    if score >= 30:
        return "medium"
    return "low"


def calculate_risk_score(data: pd.DataFrame) -> pd.DataFrame:
    """Calculate explainable risk scores for player-level feature rows.

    The rules add 20 points for each available signal: unusually high kills,
    score, or actions per minute; unusually short action intervals; and an
    anomaly label of ``-1``. Missing or non-finite optional values simply do
    not contribute points. The resulting score is a screening indicator, not
    confirmation of fraud.

    Args:
        data: Player-level features, optionally including anomaly detector
            output columns.

    Returns:
        A copy of ``data`` with ``risk_score``, ``risk_reasons``, and
        ``risk_level`` columns.

    Raises:
        TypeError: If ``data`` is not a pandas DataFrame.
        ValueError: If ``player_id`` is missing, empty, or contains missing
            values.
    """

    if not isinstance(data, pd.DataFrame):
        raise TypeError("Player features must be provided as a pandas DataFrame.")
    if _PLAYER_ID_COLUMN not in data.columns:
        raise ValueError("Player features must contain a 'player_id' column.")
    if data.empty:
        raise ValueError("Player features must contain at least one player.")
    if data[_PLAYER_ID_COLUMN].isna().any():
        raise ValueError("The 'player_id' column cannot contain missing values.")
    if pd.api.types.is_string_dtype(data[_PLAYER_ID_COLUMN].dtype):
        blank_player_ids = data[_PLAYER_ID_COLUMN].astype("string").str.strip().eq("")
        if blank_player_ids.any():
            raise ValueError("The 'player_id' column cannot contain blank values.")

    scored = [_score_player(row) for _, row in data.iterrows()]
    result = data.copy(deep=True)
    result[_RISK_SCORE_COLUMN] = [score for score, _ in scored]
    result[_RISK_REASONS_COLUMN] = [reasons for _, reasons in scored]
    result[_RISK_LEVEL_COLUMN] = [
        _risk_level(score) for score, _ in scored
    ]
    return result