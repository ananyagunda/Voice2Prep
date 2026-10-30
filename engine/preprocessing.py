"""Utilities for validating and cleaning Fairplay Radar gameplay data.

The functions in this module deliberately do not mutate a caller's
``DataFrame``.  This makes them safe to use from a file-upload handler and
keeps each preprocessing step easy to test independently.
"""

from __future__ import annotations

from io import BytesIO, StringIO
from os import PathLike
from pathlib import Path
from typing import IO, Iterable, Sequence, Union

import pandas as pd


# These are the fields needed by the first Fairplay Radar scoring pipeline.
# Callers can pass a different set to ``preprocess_gameplay_data`` when their
# CSV uses a different schema.
DEFAULT_REQUIRED_COLUMNS: tuple[str, ...] = (
    "player_id",
    "score",
    "kills",
    "deaths",
)
DEFAULT_NUMERIC_COLUMNS: tuple[str, ...] = (
    "score",
    "kills",
    "deaths",
    "play_time",
)

CsvSource = Union[
    str,
    PathLike[str],
    IO[str],
    IO[bytes],
    bytes,
]


def validate_required_columns(
    data: pd.DataFrame,
    required_columns: Iterable[str] = DEFAULT_REQUIRED_COLUMNS,
) -> None:
    """Raise ``ValueError`` when ``data`` has no rows or misses required fields."""

    if len(data.columns) == 0:
        raise ValueError("The uploaded CSV is empty and contains no columns.")
    if data.empty:
        raise ValueError("The uploaded CSV contains no gameplay records.")

    required = tuple(required_columns)
    missing = [column for column in required if column not in data.columns]
    if missing:
        missing_text = ", ".join(missing)
        available_text = ", ".join(str(column) for column in data.columns)
        raise ValueError(
            f"Missing required column(s): {missing_text}. "
            f"Available columns: {available_text or 'none'}."
        )


def convert_numeric_columns(
    data: pd.DataFrame,
    numeric_columns: Iterable[str] = DEFAULT_NUMERIC_COLUMNS,
) -> pd.DataFrame:
    """Convert selected columns to numeric values without raising on bad data.

    Values such as ``"not available"`` become ``NaN``.  Missing values are
    intentionally filled in a separate step so callers can inspect or replace
    them using their preferred policy.
    """

    cleaned = data.copy()
    for column in numeric_columns:
        if column in cleaned.columns:
            cleaned[column] = pd.to_numeric(cleaned[column], errors="coerce")
    return cleaned


def handle_missing_values(
    data: pd.DataFrame,
    numeric_columns: Iterable[str] = DEFAULT_NUMERIC_COLUMNS,
    text_fill_value: str = "Unknown",
) -> pd.DataFrame:
    """Fill missing values using median numeric values and ``text_fill_value``.

    Numeric columns with no usable values are filled with ``0``.  This avoids
    returning a column that still contains missing values after conversion,
    while keeping the behavior deterministic for a completely invalid column.
    Columns not listed as numeric are treated as text-like values.
    """

    cleaned = data.copy()
    numeric_names = set(numeric_columns)

    for column in cleaned.columns:
        if column in numeric_names:
            median = cleaned[column].median()
            fill_value = 0 if pd.isna(median) else median
            cleaned[column] = cleaned[column].fillna(fill_value)
        else:
            cleaned[column] = cleaned[column].fillna(text_fill_value)

    return cleaned


def preprocess_gameplay_data(
    data: pd.DataFrame,
    required_columns: Sequence[str] = DEFAULT_REQUIRED_COLUMNS,
    numeric_columns: Sequence[str] = DEFAULT_NUMERIC_COLUMNS,
    text_fill_value: str = "Unknown",
) -> pd.DataFrame:
    """Validate and return a clean copy of gameplay data.

    Args:
        data: Raw gameplay records as a pandas ``DataFrame``.
        required_columns: Columns that must be present in the input.
        numeric_columns: Columns that should contain numeric values. Columns
            absent from the input are ignored, allowing optional metrics such
            as ``play_time``.
        text_fill_value: Value used for missing non-numeric fields.

    Returns:
        A new ``DataFrame`` with numeric columns converted and missing values
        filled. The original ``data`` is never modified.

    Raises:
        TypeError: If ``data`` is not a pandas ``DataFrame``.
        ValueError: If the input has no columns or misses required columns.
    """

    if not isinstance(data, pd.DataFrame):
        raise TypeError("Gameplay data must be provided as a pandas DataFrame.")
    if len(data.columns) == 0:
        raise ValueError("The uploaded CSV is empty and contains no columns.")

    validate_required_columns(data, required_columns)
    converted = convert_numeric_columns(data, numeric_columns)
    cleaned = handle_missing_values(converted, numeric_columns, text_fill_value)
    return cleaned.reset_index(drop=True)


def read_gameplay_csv(source: CsvSource, **read_csv_kwargs: object) -> pd.DataFrame:
    """Read an uploaded CSV source and return its cleaned gameplay records.

    ``source`` may be a path, text/binary file-like object, or CSV bytes.
    Pandas parsing errors are wrapped with an actionable message for upload
    interfaces.
    """

    if isinstance(source, bytes):
        source = BytesIO(source)
    elif isinstance(source, str) and "\n" in source:
        source = StringIO(source)
    elif isinstance(source, PathLike):
        source = Path(source)

    try:
        return pd.read_csv(source, **read_csv_kwargs)
    except (
        OSError,
        TypeError,
        ValueError,
        UnicodeError,
        pd.errors.EmptyDataError,
        pd.errors.ParserError,
    ) as error:
        raise ValueError(f"Unable to read the uploaded gameplay CSV: {error}") from error


def load_and_preprocess_gameplay_csv(
    source: CsvSource,
    required_columns: Sequence[str] = DEFAULT_REQUIRED_COLUMNS,
    numeric_columns: Sequence[str] = DEFAULT_NUMERIC_COLUMNS,
    text_fill_value: str = "Unknown",
    **read_csv_kwargs: object,
) -> pd.DataFrame:
    """Read, validate, and clean an uploaded gameplay CSV in one call."""

    raw_data = read_gameplay_csv(source, **read_csv_kwargs)
    return preprocess_gameplay_data(
        raw_data,
        required_columns=required_columns,
        numeric_columns=numeric_columns,
        text_fill_value=text_fill_value,
    )