"""ML Model Trainer — trains failure prediction models on startup data.

Trains scikit-learn Random Forest and optionally XGBoost ensemble models
using data from the failed_startups table and/or an external Kaggle CSV.

Outputs:
- Saved model files in data/models/ (joblib format)
- Training metrics logged to ml_models table

Run:
    python -c "from agents.ml_trainer_agent import MLTrainer; MLTrainer({}).train()"
    python run_agent.py --pipeline analysis   (includes ml_predictor agent)

Config options:
    training_data_path: str — path to external CSV (default: None)
    min_training_samples: int — minimum rows to train (default: 50)
    test_split: float — train/test split ratio (default: 0.2)
    model_output_dir: str — where to save models (default: data/models)
"""

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

_logger = logging.getLogger(__name__)

# Default feature columns used for prediction
FEATURE_COLUMNS = [
    "sector_encoded",
    "funding_bin",
    "country_risk_index",
    "age_at_shutdown",
    "is_manufacturing",
    "has_funding",
    "funding_per_year",
]

# Sector encoding — map sectors to numeric codes based on risk rank
_SECTOR_ENCODING = {
    "Cybersecurity": 1,
    "SaaS": 2,
    "AI/ML": 3,
    "Gaming": 4,
    "Fintech": 5,
    "Biotech": 6,
    "E-commerce": 7,
    "Healthtech": 8,
    "Travel": 9,
    "PropTech": 10,
    "Food Tech": 11,
    "Robotics": 12,
    "Construction": 13,
    "Social Media": 14,
    "EdTech": 15,
    "3D Printing": 16,
    "Micro-mobility": 17,
    "EV/Automotive": 18,
    "Battery Manufacturing": 19,
    "Crypto/Blockchain": 20,
}

# Country risk index (lower = safer startup environment)
_COUNTRY_RISK_INDEX = {
    "US": 1.0,
    "United States": 1.0,
    "UK": 0.95,
    "United Kingdom": 0.95,
    "Germany": 0.9,
    "Canada": 0.9,
    "Australia": 0.85,
    "France": 0.88,
    "India": 1.15,
    "China": 1.1,
    "Brazil": 1.2,
    "Singapore": 0.85,
    "Netherlands": 0.87,
    "Israel": 0.92,
    "Sweden": 0.85,
    "Japan": 0.88,
    "South Korea": 0.9,
    "Ireland": 0.87,
    "Estonia": 0.9,
    "Global": 1.0,
}

# Manufacturing keywords for feature detection
_MFG_KEYWORDS = [
    "manufacturing",
    "factory",
    "production",
    "battery",
    "semiconductor",
    "chip",
    "3d printing",
    "robotics",
    "ev",
    "electric vehicle",
    "automotive",
    "supply chain",
    "fabrication",
    "assembly",
    "industrial",
    "steel",
    "solar panel",
    "textile",
    "construction",
    "pharmaceutical",
]


def _encode_sector(sector: str) -> float:
    """Map sector name to numeric encoding (higher = riskier)."""
    if not sector:
        return 10.0  # unknown = average
    for key, val in _SECTOR_ENCODING.items():
        if key.lower() in sector.lower() or sector.lower() in key.lower():
            return float(val)
    return 10.0


def _country_risk(country: str) -> float:
    """Return risk index for a country (1.0 = US baseline)."""
    if not country:
        return 1.05
    for key, val in _COUNTRY_RISK_INDEX.items():
        if key.lower() in country.lower():
            return val
    return 1.1  # default: slightly above baseline


def _is_manufacturing(sector: str, sub_sector: str = "") -> int:
    """Detect if a startup is in manufacturing."""
    combined = f"{sector} {sub_sector}".lower()
    return 1 if any(kw in combined for kw in _MFG_KEYWORDS) else 0


def _build_features(row: dict) -> dict:
    """Build ML feature vector from a startup record.

    Args:
        row: dict with keys from failed_startups table.

    Returns:
        dict mapping feature names to numeric values.
    """
    sector = row.get("sector", "")
    sub_sector = row.get("manufacturing_sub_sector", "")
    funding = row.get("funding_raised_usd") or 0
    year_founded = row.get("year_founded") or 2020
    year_shutdown = row.get("year_shutdown") or 2024
    country = row.get("country", "") or row.get("region", "")

    age_at_shutdown = max(0, year_shutdown - year_founded)

    # Funding bins: 0=unknown, 1=<1M, 2=1-10M, 3=10-100M, 4=100M+
    if funding <= 0:
        funding_bin = 0
    elif funding < 1_000_000:
        funding_bin = 1
    elif funding < 10_000_000:
        funding_bin = 2
    elif funding < 100_000_000:
        funding_bin = 3
    else:
        funding_bin = 4

    funding_per_year = funding / max(age_at_shutdown, 1)

    return {
        "sector_encoded": _encode_sector(sector),
        "funding_bin": float(funding_bin),
        "country_risk_index": _country_risk(country),
        "age_at_shutdown": float(age_at_shutdown),
        "is_manufacturing": float(_is_manufacturing(sector, sub_sector)),
        "has_funding": 1.0 if funding > 0 else 0.0,
        "funding_per_year": min(funding_per_year / 1_000_000, 100.0),  # cap at $100M/yr
    }


def load_training_data_from_db(conn) -> tuple[list[dict], list[int]]:
    """Load failed startups from database as training data.

    All records in failed_startups are positive examples (failed=True).
    Returns (features_list, labels_list).
    """
    cursor = conn.cursor()
    cursor.execute(
        """SELECT id, sector, manufacturing_sub_sector, country, region,
                  funding_raised_usd, year_founded, year_shutdown, failure_reason
           FROM failed_startups"""
    )
    rows = cursor.fetchall()
    cursor.close()

    features = []
    labels = []
    for row in rows:
        row_dict = dict(row)
        features.append(_build_features(row_dict))
        labels.append(1)  # All are failures

    return features, labels


def load_training_data_from_csv(csv_path: str) -> tuple[list[dict], list[int]]:
    """Load training data from external CSV (e.g., Kaggle dataset).

    Expected columns (flexible matching):
    - status/label/target: 0=operating, 1=failed/closed
    - sector/industry/category
    - funding/funding_total_usd/funding_raised
    - country/country_code/hq
    - founded/year_founded
    - Any text columns for failure reasons

    Returns (features_list, labels_list).
    """
    import csv

    features = []
    labels = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Detect label column
            label = 1  # default: failed
            for col in ("status", "label", "target", "state", "is_closed"):
                val = row.get(col, "").strip().lower()
                if val in (
                    "0",
                    "operating",
                    "active",
                    "open",
                    "alive",
                    "acquired",
                    "ipo",
                ):
                    label = 0
                elif val in ("1", "failed", "closed", "dead", "shutdown", "bankrupt"):
                    label = 1
                break

            # Map CSV columns to our feature format
            row_dict = {
                "sector": row.get("sector")
                or row.get("industry")
                or row.get("category")
                or "",
                "manufacturing_sub_sector": row.get("subcategory") or "",
                "country": row.get("country")
                or row.get("country_code")
                or row.get("hq")
                or "",
                "region": row.get("region") or "",
                "funding_raised_usd": _parse_funding(
                    row.get("funding")
                    or row.get("funding_total_usd")
                    or row.get("funding_raised")
                    or "0"
                ),
                "year_founded": _parse_int(
                    row.get("founded") or row.get("year_founded") or "2020"
                ),
                "year_shutdown": _parse_int(
                    row.get("shutdown_year")
                    or row.get("closed_year")
                    or str(datetime.now().year)
                ),
                "failure_reason": row.get("failure_reason") or row.get("reason") or "",
            }
            features.append(_build_features(row_dict))
            labels.append(label)

    return features, labels


def _parse_funding(val: str) -> float:
    """Parse funding string like '$50M', '50000000', '$1.2B' to float."""
    if not val:
        return 0.0
    val = val.strip().lstrip("$").replace(",", "")
    val_lower = val.lower()
    try:
        if val_lower.endswith("b"):
            return float(val[:-1]) * 1_000_000_000
        elif val_lower.endswith("m"):
            return float(val[:-1]) * 1_000_000
        elif val_lower.endswith("k"):
            return float(val[:-1]) * 1_000
        return float(val)
    except (ValueError, IndexError):
        return 0.0


def _parse_int(val: str) -> int:
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return 2020


class MLTrainer:
    """Trains and persists ML models for startup failure prediction."""

    def __init__(self, config: dict | None = None):
        self.config = config or {}
        self.model_dir = Path(self.config.get("model_output_dir", "data/models"))
        self.model_dir.mkdir(parents=True, exist_ok=True)
        self.min_samples = self.config.get("min_training_samples", 50)
        self.test_split = self.config.get("test_split", 0.2)

    def train(self, conn=None) -> dict:
        """Train ML models and save to disk.

        Args:
            conn: Optional DB connection. If None, creates one.

        Returns:
            dict with training results: models_trained, metrics, errors.
        """
        from db.connection import get_connection
        from db import schema

        if conn is None:
            conn = get_connection()
            own_conn = True
        else:
            own_conn = False

        try:
            schema.init_schema(conn)
            results = {"models_trained": [], "errors": [], "total_rows": 0}

            # Load data from database
            db_features, db_labels = load_training_data_from_db(conn)
            _logger.info("Loaded %d rows from database", len(db_features))

            # Load data from external CSV if configured
            csv_path = self.config.get("training_data_path")
            csv_features, csv_labels = [], []
            if csv_path and os.path.exists(csv_path):
                csv_features, csv_labels = load_training_data_from_csv(csv_path)
                _logger.info("Loaded %d rows from CSV %s", len(csv_features), csv_path)

            # Combine datasets
            all_features = db_features + csv_features
            all_labels = db_labels + csv_labels
            results["total_rows"] = len(all_features)

            if len(all_features) < self.min_samples:
                results["errors"].append(
                    f"Insufficient training data: {len(all_features)} rows (need {self.min_samples})"
                )
                _logger.warning(
                    "Skipping ML training — only %d rows available", len(all_features)
                )
                return results

            # Build feature matrix
            import numpy as np

            X = np.array([[f[col] for col in FEATURE_COLUMNS] for f in all_features])
            y = np.array(all_labels, dtype=int)

            # For failure prediction, we need both classes.
            # If all labels are 1 (all failures), use synthetic negatives via risk scoring.
            if len(np.unique(y)) < 2:
                _logger.info(
                    "All labels are failures — generating synthetic survival examples"
                )
                X, y = self._generate_synthetic_negatives(X, all_features, db_features)

            # Train Random Forest
            rf_result = self._train_random_forest(X, y)
            if rf_result:
                results["models_trained"].append(rf_result)
                self._log_model_to_db(conn, rf_result)

            # Train XGBoost if available
            xgb_result = self._train_xgboost(X, y)
            if xgb_result:
                results["models_trained"].append(xgb_result)
                self._log_model_to_db(conn, xgb_result)

            return results

        finally:
            if own_conn:
                conn.close()

    def _generate_synthetic_negatives(
        self, X, features: list[dict], db_features: list[dict]
    ) -> tuple:
        """Generate synthetic 'survived' examples by perturbing failure features.

        Creates balanced dataset by flipping risk features of failed startups
        to represent companies that survived with similar profiles.
        """
        import numpy as np

        rng = np.random.RandomState(42)
        n = len(features)

        # Create negatives by modifying failure features toward "safer" values
        X_neg = X.copy()
        y_neg = np.zeros(n, dtype=int)

        # Reduce sector risk (move toward low-risk sectors)
        X_neg[:, 0] = np.clip(X_neg[:, 0] * rng.uniform(0.3, 0.7, n), 1, 20)
        # Increase funding bin
        X_neg[:, 1] = np.clip(X_neg[:, 1] + rng.uniform(0, 2, n), 0, 4)
        # Reduce country risk
        X_neg[:, 2] = np.clip(X_neg[:, 2] * rng.uniform(0.7, 0.95, n), 0.8, 1.3)
        # Increase age (survived longer)
        X_neg[:, 3] = X_neg[:, 3] + rng.uniform(2, 8, n)

        # Combine
        X_combined = np.vstack([X, X_neg])
        y_combined = np.concatenate([np.ones(n, dtype=int), y_neg])
        return X_combined, y_combined

    def _train_random_forest(self, X, y) -> dict | None:
        """Train a Random Forest classifier."""
        try:
            from sklearn.ensemble import RandomForestClassifier
            from sklearn.model_selection import train_test_split
            from sklearn.metrics import (
                accuracy_score,
                f1_score,
                precision_score,
                recall_score,
            )
            import joblib

            X_train, X_test, y_train, y_test = train_test_split(
                X,
                y,
                test_size=self.test_split,
                random_state=42,
                stratify=y,
            )

            model = RandomForestClassifier(
                n_estimators=100,
                max_depth=10,
                min_samples_split=5,
                min_samples_leaf=2,
                class_weight="balanced",
                random_state=42,
            )
            model.fit(X_train, y_train)
            y_pred = model.predict(X_test)

            metrics = {
                "accuracy": round(accuracy_score(y_test, y_pred), 4),
                "f1_score": round(f1_score(y_test, y_pred, average="weighted"), 4),
                "precision": round(
                    precision_score(
                        y_test, y_pred, average="weighted", zero_division=0
                    ),
                    4,
                ),
                "recall": round(
                    recall_score(y_test, y_pred, average="weighted", zero_division=0), 4
                ),
            }

            model_path = self.model_dir / "startup_failure_rf.joblib"
            joblib.dump(model, model_path)
            _logger.info("Random Forest trained — %s", metrics)

            return {
                "model_name": "startup_failure_rf",
                "model_type": "random_forest",
                "model_path": str(model_path),
                "training_rows": len(X),
                "features_used": FEATURE_COLUMNS,
                **metrics,
            }

        except ImportError:
            _logger.warning("scikit-learn not installed — skipping Random Forest")
            return None
        except Exception as e:
            _logger.error("Random Forest training failed: %s", e)
            return None

    def _train_xgboost(self, X, y) -> dict | None:
        """Train an XGBoost classifier (optional dependency)."""
        try:
            from xgboost import XGBClassifier
            from sklearn.model_selection import train_test_split
            from sklearn.metrics import (
                accuracy_score,
                f1_score,
                precision_score,
                recall_score,
            )
            import joblib

            X_train, X_test, y_train, y_test = train_test_split(
                X,
                y,
                test_size=self.test_split,
                random_state=42,
                stratify=y,
            )

            model = XGBClassifier(
                n_estimators=100,
                max_depth=6,
                learning_rate=0.1,
                scale_pos_weight=sum(y_train == 0) / max(sum(y_train == 1), 1),
                random_state=42,
                use_label_encoder=False,
                eval_metric="logloss",
            )
            model.fit(X_train, y_train)
            y_pred = model.predict(X_test)

            metrics = {
                "accuracy": round(accuracy_score(y_test, y_pred), 4),
                "f1_score": round(f1_score(y_test, y_pred, average="weighted"), 4),
                "precision": round(
                    precision_score(
                        y_test, y_pred, average="weighted", zero_division=0
                    ),
                    4,
                ),
                "recall": round(
                    recall_score(y_test, y_pred, average="weighted", zero_division=0), 4
                ),
            }

            model_path = self.model_dir / "startup_failure_xgb.joblib"
            joblib.dump(model, model_path)
            _logger.info("XGBoost trained — %s", metrics)

            return {
                "model_name": "startup_failure_xgb",
                "model_type": "xgboost",
                "model_path": str(model_path),
                "training_rows": len(X),
                "features_used": FEATURE_COLUMNS,
                **metrics,
            }

        except ImportError:
            _logger.info("XGBoost not installed — skipping")
            return None
        except Exception as e:
            _logger.error("XGBoost training failed: %s", e)
            return None

    def _log_model_to_db(self, conn, result: dict) -> None:
        """Record trained model metadata in the ml_models table."""
        cursor = conn.cursor()
        try:
            cursor.execute(
                """INSERT INTO ml_models
                   (model_name, model_type, model_path, trained_at, training_rows,
                    features_used, accuracy, f1_score, precision_score, recall_score, is_active)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 1)
                   ON DUPLICATE KEY UPDATE
                   trained_at = VALUES(trained_at),
                   training_rows = VALUES(training_rows),
                   accuracy = VALUES(accuracy),
                   f1_score = VALUES(f1_score),
                   is_active = VALUES(is_active)""",
                (
                    result["model_name"],
                    result["model_type"],
                    result["model_path"],
                    datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
                    result["training_rows"],
                    json.dumps(result["features_used"]),
                    result.get("accuracy"),
                    result.get("f1_score"),
                    result.get("precision"),
                    result.get("recall"),
                ),
            )
            conn.commit()
        except Exception as e:
            _logger.warning("Failed to log model to DB: %s", e)
        finally:
            cursor.close()

    def load_best_model(self) -> tuple:
        """Load the best available trained model.

        Returns:
            (model, model_name, features) or (None, None, None) if no model exists.
        """
        import joblib

        # Prefer XGBoost (usually higher accuracy), fall back to RF
        for model_file, model_name in [
            ("startup_failure_xgb.joblib", "startup_failure_xgb"),
            ("startup_failure_rf.joblib", "startup_failure_rf"),
        ]:
            path = self.model_dir / model_file
            if path.exists():
                try:
                    model = joblib.load(path)
                    return model, model_name, FEATURE_COLUMNS
                except Exception as e:
                    _logger.warning("Failed to load model %s: %s", model_file, e)

        return None, None, None
