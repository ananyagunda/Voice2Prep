"""Feature engineering helpers for Fairplay Radar gameplay data."""

from __future__ import annotations

from typing import Final

import pandas as pd


_PLAYER_ID_COLUMN: Final[str] = "player_id"
_SCORE_COLUMN: Final[str] = "score"
_KILLS_COLUMN: Final[str] = "kills"
_DEATHS_COLUMN: Final[str] = "deaths"
_PLAY_TIME_COLUMN: Final[str] = "play_time"
_ACTIONS_COLUMN: Final[str] = "actions"
_RAW_ACTION_INTERVAL_COLUMN: Final[str] = "action_interval"
_ACTION_INTERVAL_COLUMN: Final[str] = "average_action_interval"


def _numeric_copy(data: pd.DataFrame, column: str) -> pd.Series:
    """Return one numeric column without changing the source DataFrame."""

    return pd.to_numeric(data[column], errors="coerce")


def engineer_player_features(data: pd.DataFrame) -> pd.DataFrame:
    """Aggregate gameplay sessions into one behavioral row per player.

    ``play_time`` is expected to be measured in minutes. Per-minute features
    are calculated for each session and then averaged for the player. Sessions
    with zero or missing play time do not contribute to a per-minute average.
    The kill-death ratio uses total kills divided by total deaths; it is
    ``0.0`` when total deaths are zero.

    Args:
        data: Gameplay sessions containing a ``player_id`` column. Recognized
                metric columns ``score``, ``kills``, ``deaths``, ``play_time``,
                ``actions``, and ``action_interval`` are optional and are
                included only when present. ``action_interval`` is aggregated
                into the output feature ``average_action_interval``.

    Returns:
        A new DataFrame with one row per player. ``total_sessions`` and
        ``player_id`` are always present; optional feature columns are omitted
        when their source columns are unavailable.

    Raises:
        TypeError: If ``data`` is not a pandas DataFrame.
        ValueError: If the input is empty, lacks ``player_id``, or contains
            missing or blank player IDs.
    """

    if not isinstance(data, pd.DataFrame):
        raise TypeError("Gameplay data must be provided as a pandas DataFrame.")
    if data.empty:
        raise ValueError("Gameplay data must contain at least one session.")
    if _PLAYER_ID_COLUMN not in data.columns:
        raise ValueError("Gameplay data must contain a 'player_id' column.")

    player_ids = data[_PLAYER_ID_COLUMN]
    if player_ids.isna().any():
        raise ValueError("The 'player_id' column cannot contain missing values.")
    if pd.api.types.is_string_dtype(player_ids.dtype):
        blank_player_ids = player_ids.astype("string").str.strip().eq("")
        if blank_player_ids.any():
            raise ValueError("The 'player_id' column cannot contain blank values.")

    working = data.copy(deep=True)
    optional_numeric = (
        _SCORE_COLUMN,
        _KILLS_COLUMN,
        _DEATHS_COLUMN,
        _PLAY_TIME_COLUMN,
        _ACTIONS_COLUMN,
        _RAW_ACTION_INTERVAL_COLUMN,
    )
    for column in optional_numeric:
        if column in working.columns:
            working[column] = _numeric_copy(working, column)

    grouped = working.groupby(_PLAYER_ID_COLUMN, sort=False, dropna=False)
    features = grouped.size().rename("total_sessions").reset_index()

    if _SCORE_COLUMN in working.columns:
        features["average_score"] = grouped[_SCORE_COLUMN].mean().to_numpy()
        features["total_score"] = grouped[_SCORE_COLUMN].sum(min_count=1).to_numpy()

    if _KILLS_COLUMN in working.columns:
        features["average_kills"] = grouped[_KILLS_COLUMN].mean().to_numpy()
    if _DEATHS_COLUMN in working.columns:
        features["average_deaths"] = grouped[_DEATHS_COLUMN].mean().to_numpy()
    if _KILLS_COLUMN in working.columns and _DEATHS_COLUMN in working.columns:
        total_kills = grouped[_KILLS_COLUMN].sum(min_count=1)
        total_deaths = grouped[_DEATHS_COLUMN].sum(min_count=1)
        ratio = total_kills.div(total_deaths).where(total_deaths.ne(0), 0.0)
        features["kill_death_ratio"] = ratio.to_numpy()

    if _PLAY_TIME_COLUMN in working.columns:
        features["average_play_time"] = grouped[_PLAY_TIME_COLUMN].mean().to_numpy()

    has_play_time = _PLAY_TIME_COLUMN in working.columns
    if has_play_time:
        valid_play_time = working[_PLAY_TIME_COLUMN].gt(0)
        if _KILLS_COLUMN in working.columns:
            kills_per_minute = working[_KILLS_COLUMN].where(valid_play_time).div(
                working[_PLAY_TIME_COLUMN]
            )
            features["average_kills_per_minute"] = (
                kills_per_minute.groupby(working[_PLAYER_ID_COLUMN], sort=False)
                .mean()
                .to_numpy()
            )
        if _SCORE_COLUMN in working.columns:
            score_per_minute = working[_SCORE_COLUMN].where(valid_play_time).div(
                working[_PLAY_TIME_COLUMN]
            )
            features["average_score_per_minute"] = (
                score_per_minute.groupby(working[_PLAYER_ID_COLUMN], sort=False)
                .mean()
                .to_numpy()
            )
        if _ACTIONS_COLUMN in working.columns:
            actions_per_minute = working[_ACTIONS_COLUMN].where(valid_play_time).div(
                working[_PLAY_TIME_COLUMN]
            )
            features["average_actions_per_minute"] = (
                actions_per_minute.groupby(working[_PLAYER_ID_COLUMN], sort=False)
                .mean()
                .to_numpy()
            )

    if _RAW_ACTION_INTERVAL_COLUMN in working.columns:
        features[_ACTION_INTERVAL_COLUMN] = (
            grouped[_RAW_ACTION_INTERVAL_COLUMN].mean().to_numpy()
        )

    return features