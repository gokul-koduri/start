"""Z-score anomaly detection for signal spike identification.

Anomaly detection identifies when an entity's signal activity deviates
significantly from its historical baseline. This catches events like:
  - A company suddenly filing 10x more job postings (scaling signal)
  - A startup appearing in the news 5x more than usual (buzz spike)
  - A patent filing after 6 months of silence (innovation signal)

Algorithm: Rolling Z-score
  Z = (current_value - rolling_mean) / rolling_stddev
  If |Z| > threshold → anomaly detected

This is deliberately simple (vs. isolation forests, LSTM anomaly detection)
because:
  1. It's interpretable — you can explain WHY something is anomalous
  2. It works well with sparse, irregular signal data
  3. It requires no training — just a rolling window of historical values
  4. It's fast — O(1) per update with a rolling window
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass
from typing import Sequence


@dataclass
class AnomalyResult:
    """Result of anomaly detection for a single value."""

    z_score: float
    is_anomaly: bool
    rolling_mean: float
    rolling_stddev: float
    anomaly_type: str | None = None  # "spike" | "drop" | None

    def to_dict(self) -> dict:
        return {
            "z_score": round(self.z_score, 4),
            "is_anomaly": self.is_anomaly,
            "rolling_mean": round(self.rolling_mean, 4),
            "rolling_stddev": round(self.rolling_stddev, 4),
            "anomaly_type": self.anomaly_type,
        }


def z_score_anomaly(
    values: Sequence[float],
    window: int = 30,
    threshold: float = 2.0,
) -> AnomalyResult:
    """Detect anomalies using rolling Z-score on a time series.

    Args:
        values: Historical signal counts/values (chronological, oldest first).
            The last value is tested against the preceding window.
        window: Number of historical values for mean/stddev calculation.
        threshold: |Z| must exceed this to flag as anomaly.

    Returns:
        AnomalyResult with z_score, is_anomaly flag, and anomaly_type.

    Examples:
        >>> # Normal sequence — no anomaly
        >>> result = z_score_anomaly([1.0, 2.0, 1.5, 2.0, 1.8, 2.0])
        >>> result.is_anomaly
        False

        >>> # Spike — last value is much higher than baseline
        >>> result = z_score_anomaly([1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 10.0])
        >>> result.is_anomaly
        True
        >>> result.anomaly_type
        'spike'
    """
    if len(values) < 2:
        return AnomalyResult(
            z_score=0.0,
            is_anomaly=False,
            rolling_mean=0.0,
            rolling_stddev=0.0,
        )

    # Use the last N values before the current one as the baseline
    window_values = list(values[-(window + 1) : -1]) if len(values) > 1 else []
    current = values[-1]

    if len(window_values) < 2:
        return AnomalyResult(
            z_score=0.0,
            is_anomaly=False,
            rolling_mean=float(statistics.mean(window_values)) if window_values else 0.0,
            rolling_stddev=0.0,
        )

    mean = statistics.mean(window_values)
    stddev = statistics.stdev(window_values)

    if stddev == 0:
        # All historical values are identical — any deviation is notable
        if current != mean:
            return AnomalyResult(
                z_score=threshold + 1.0,  # Force anomaly flag
                is_anomaly=True,
                rolling_mean=mean,
                rolling_stddev=0.0,
                anomaly_type="spike" if current > mean else "drop",
            )
        return AnomalyResult(
            z_score=0.0,
            is_anomaly=False,
            rolling_mean=mean,
            rolling_stddev=0.0,
        )

    z = (current - mean) / stddev
    is_anomaly = abs(z) > threshold
    anomaly_type = None
    if is_anomaly:
        anomaly_type = "spike" if z > 0 else "drop"

    return AnomalyResult(
        z_score=round(z, 4),
        is_anomaly=is_anomaly,
        rolling_mean=round(mean, 4),
        rolling_stddev=round(stddev, 4),
        anomaly_type=anomaly_type,
    )


def detect_multi_signal_anomaly(
    signal_counts: dict[str, list[float]],
    threshold: float = 2.0,
) -> dict[str, AnomalyResult]:
    """Run anomaly detection across multiple signal types for an entity.

    Args:
        signal_counts: Map of signal_type → chronological values.
            Example: {"job_postings": [3, 4, 5, 4, 15], "news_mentions": [1, 2, 1, 2, 8]}
        threshold: Z-score threshold per signal type.

    Returns:
        Map of signal_type → AnomalyResult, only for types with anomalies.
    """
    anomalies: dict[str, AnomalyResult] = {}
    for signal_type, values in signal_counts.items():
        if len(values) >= 3:
            result = z_score_anomaly(values, threshold=threshold)
            if result.is_anomaly:
                anomalies[signal_type] = result
    return anomalies
