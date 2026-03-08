"""
ML Property Valuation Model (Task #12)
Uses XGBoost/LightGBM trained on Land Registry historical data.
Target: <15% MAPE on held-out test set.
"""
import logging
import os
import pickle
import re
from datetime import datetime, timedelta
from typing import Optional, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

try:
    import xgboost as xgb
    import lightgbm as lgb
    from sklearn.ensemble import GradientBoostingRegressor
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import mean_absolute_percentage_error
    from sklearn.preprocessing import LabelEncoder
    ML_AVAILABLE = True
except (ImportError, OSError):
    ML_AVAILABLE = False
    logger.warning("ML libraries not available - using statistical fallback")

MODEL_PATH = os.environ.get('ML_MODEL_PATH', '/app/models/valuation_model.pkl')
FEATURE_COLS = [
    'property_type_enc',
    'bedrooms',
    'floor_area_sqm',
    'postcode_district_enc',
    'postcode_sector_enc',
    'area_avg_price_1yr',
    'area_avg_price_3yr',
    'area_avg_price_5yr',
    'area_growth_pct_1yr',
    'area_growth_pct_5yr',
    'area_growth_pct_10yr',
    'area_transaction_count',
    'month_of_year',
    'year',
]


class PropertyValuationModel:
    """
    Gradient boosting model for UK property valuation.
    Falls back to statistical comparables if ML unavailable.
    """

    def __init__(self):
        self.model = None
        self.label_encoders = {}
        self.feature_means = {}
        self.is_trained = False
        self._load_model()

    def _load_model(self):
        if os.path.exists(MODEL_PATH):
            try:
                with open(MODEL_PATH, 'rb') as f:
                    saved = pickle.load(f)
                self.model = saved['model']
                self.label_encoders = saved['label_encoders']
                self.feature_means = saved['feature_means']
                self.is_trained = True
                logger.info("Loaded valuation model from %s", MODEL_PATH)
            except Exception as e:
                logger.warning("Could not load model: %s", e)

    def _save_model(self):
        os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
        with open(MODEL_PATH, 'wb') as f:
            pickle.dump({
                'model': self.model,
                'label_encoders': self.label_encoders,
                'feature_means': self.feature_means,
            }, f)
        logger.info("Model saved to %s", MODEL_PATH)

    def train(self, db_session) -> dict:
        """Train on Land Registry + property data from database."""
        if not ML_AVAILABLE:
            logger.warning("ML libraries not available, skipping training")
            return {'error': 'ML libraries not available'}

        logger.info("Loading training data from database...")
        from backend.models.sales_history import SalesHistory
        from backend.models.property import Property
        from sqlalchemy import func

        # Get sales with property features
        cutoff = datetime.utcnow() - timedelta(days=365 * 10)
        rows = (
            db_session.query(
                SalesHistory.sale_price,
                SalesHistory.sale_date,
                SalesHistory.property_type,
                SalesHistory.postcode,
                SalesHistory.address,
            )
            .filter(SalesHistory.sale_date >= cutoff)
            .filter(SalesHistory.sale_price > 10000)
            .filter(SalesHistory.sale_price < 10_000_000)
            .limit(500_000)
            .all()
        )

        if len(rows) < 1000:
            logger.warning("Insufficient training data (%d rows)", len(rows))
            return {'error': 'insufficient_data', 'rows': len(rows)}

        logger.info("Loaded %d training records", len(rows))
        df = pd.DataFrame(rows, columns=['sale_price', 'sale_date', 'property_type', 'postcode', 'address'])

        df = self._engineer_features(df, db_session)
        df = df.dropna(subset=['sale_price'] + [c for c in FEATURE_COLS if c in df.columns])

        X = df[[c for c in FEATURE_COLS if c in df.columns]]
        y = np.log1p(df['sale_price'])  # log transform for better distribution

        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.15, random_state=42)

        logger.info("Training LightGBM on %d samples...", len(X_train))
        self.model = lgb.LGBMRegressor(
            n_estimators=500,
            learning_rate=0.05,
            max_depth=8,
            num_leaves=63,
            min_child_samples=20,
            subsample=0.8,
            colsample_bytree=0.8,
            reg_alpha=0.1,
            reg_lambda=0.1,
            random_state=42,
            n_jobs=-1,
        )
        self.model.fit(
            X_train, y_train,
            eval_set=[(X_test, y_test)],
            callbacks=[lgb.early_stopping(50, verbose=False), lgb.log_evaluation(100)],
        )

        y_pred = self.model.predict(X_test)
        mape = mean_absolute_percentage_error(np.expm1(y_test), np.expm1(y_pred))
        logger.info("Model MAPE: %.1f%%", mape * 100)

        self.is_trained = True
        self.feature_means = {col: float(X[col].mean()) for col in X.columns}
        self._save_model()

        return {
            'mape': float(mape),
            'train_samples': len(X_train),
            'test_samples': len(X_test),
            'features': list(X.columns),
        }

    def _engineer_features(self, df: pd.DataFrame, db_session) -> pd.DataFrame:
        """Add engineered features to training data."""
        # Property type encoding
        le_type = LabelEncoder()
        df['property_type_enc'] = le_type.fit_transform(df['property_type'].fillna('unknown'))
        self.label_encoders['property_type'] = le_type

        # Postcode features
        df['postcode_district'] = df['postcode'].str.extract(r'^([A-Z]{1,2}\d{1,2}[A-Z]?)')
        df['postcode_sector'] = df['postcode'].str.extract(r'^([A-Z]{1,2}\d{1,2}[A-Z]?\s*\d)')

        le_dist = LabelEncoder()
        le_sect = LabelEncoder()
        df['postcode_district_enc'] = le_dist.fit_transform(df['postcode_district'].fillna('unknown'))
        df['postcode_sector_enc'] = le_sect.fit_transform(df['postcode_sector'].fillna('unknown'))
        self.label_encoders['postcode_district'] = le_dist
        self.label_encoders['postcode_sector'] = le_sect

        # Date features
        df['sale_date'] = pd.to_datetime(df['sale_date'])
        df['month_of_year'] = df['sale_date'].dt.month
        df['year'] = df['sale_date'].dt.year

        # Area statistics (compute from training data itself)
        now_yr = datetime.utcnow().year
        for years, col_suffix in [(1, '1yr'), (3, '3yr'), (5, '5yr'), (10, '10yr')]:
            cutoff_yr = now_yr - years
            mask = df['year'] >= cutoff_yr
            area_stats = (
                df[mask].groupby('postcode_district')['sale_price']
                .agg(['mean', 'count'])
                .rename(columns={'mean': f'area_avg_{col_suffix}', 'count': f'area_count_{col_suffix}'})
            )
            df = df.merge(area_stats, on='postcode_district', how='left')

        # Growth rates
        df['area_avg_price_1yr'] = df.get('area_avg_1yr', df['sale_price'])
        df['area_avg_price_3yr'] = df.get('area_avg_3yr', df['sale_price'])
        df['area_avg_price_5yr'] = df.get('area_avg_5yr', df['sale_price'])
        df['area_avg_price_10yr'] = df.get('area_avg_10yr', df['sale_price'])

        # Growth percentages
        df['area_growth_pct_1yr'] = (
            (df['area_avg_price_1yr'] - df['area_avg_price_3yr']) / df['area_avg_price_3yr'].clip(1)
        ).clip(-1, 5)
        df['area_growth_pct_5yr'] = (
            (df['area_avg_price_5yr'] - df['area_avg_price_10yr']) / df['area_avg_price_10yr'].clip(1)
        ).clip(-1, 10)
        df['area_growth_pct_10yr'] = (
            (df['area_avg_price_1yr'] - df['area_avg_price_10yr']) / df['area_avg_price_10yr'].clip(1)
        ).clip(-1, 20)
        df['area_transaction_count'] = df.get('area_count_1yr', 0).fillna(0)

        # Bedrooms - not directly in sales history, use property_type proxy
        df['bedrooms'] = df['property_type'].map({
            'detached': 4, 'semi-detached': 3, 'terraced': 3, 'flat': 2, 'other': 3
        }).fillna(3)
        df['floor_area_sqm'] = df['bedrooms'] * 25  # rough proxy

        return df

    def predict(
        self,
        address: str,
        postcode: str,
        property_type: str,
        bedrooms: Optional[int],
        floor_area_sqm: Optional[float],
        area_stats: dict,
    ) -> Tuple[Optional[float], float]:
        """
        Returns (estimated_value, confidence_score 0-1).
        Falls back to statistical comparables if model not available.
        """
        if self.is_trained and ML_AVAILABLE and self.model:
            try:
                return self._ml_predict(postcode, property_type, bedrooms, floor_area_sqm, area_stats)
            except Exception as e:
                logger.warning("ML prediction failed, using fallback: %s", e)

        return self._statistical_predict(postcode, property_type, bedrooms, area_stats)

    def _ml_predict(self, postcode, property_type, bedrooms, floor_area_sqm, area_stats):
        district = re.sub(r'\s+\d[A-Z]{2}$', '', postcode).strip() if postcode else 'unknown'
        sector = postcode[:postcode.rfind(' ')] if ' ' in postcode else postcode[:4]

        # Encode categoricals
        le_type = self.label_encoders.get('property_type')
        le_dist = self.label_encoders.get('postcode_district')
        le_sect = self.label_encoders.get('postcode_sector')

        def safe_encode(le, val):
            if le is None:
                return 0
            try:
                return le.transform([val])[0]
            except ValueError:
                return 0

        now = datetime.utcnow()
        features = {
            'property_type_enc': safe_encode(le_type, property_type or 'unknown'),
            'bedrooms': bedrooms or 3,
            'floor_area_sqm': floor_area_sqm or ((bedrooms or 3) * 25),
            'postcode_district_enc': safe_encode(le_dist, district),
            'postcode_sector_enc': safe_encode(le_sect, sector),
            'area_avg_price_1yr': area_stats.get('avg_price_1yr', 250000),
            'area_avg_price_3yr': area_stats.get('avg_price_3yr', 240000),
            'area_avg_price_5yr': area_stats.get('avg_price_5yr', 220000),
            'area_growth_pct_1yr': area_stats.get('growth_pct_1yr', 0.03),
            'area_growth_pct_5yr': area_stats.get('growth_pct_5yr', 0.15),
            'area_growth_pct_10yr': area_stats.get('growth_pct_10yr', 0.30),
            'area_transaction_count': area_stats.get('transaction_count', 50),
            'month_of_year': now.month,
            'year': now.year,
        }

        feature_cols = [c for c in FEATURE_COLS if c in features]
        X = pd.DataFrame([{c: features.get(c, self.feature_means.get(c, 0)) for c in feature_cols}])

        log_pred = self.model.predict(X)[0]
        estimated = float(np.expm1(log_pred))
        confidence = min(0.9, area_stats.get('transaction_count', 10) / 100)
        return estimated, confidence

    def _statistical_predict(self, postcode, property_type, bedrooms, area_stats):
        """Fallback: use area average with type/bedroom adjustments."""
        base = area_stats.get('avg_price_1yr', area_stats.get('avg_price_3yr', 250000))
        if not base:
            return None, 0.3

        # Type multipliers relative to area average (terraced as baseline)
        type_multipliers = {
            'detached': 1.45, 'semi-detached': 1.10, 'terraced': 1.0,
            'flat': 0.75, 'unknown': 1.0,
        }
        bed_multipliers = {1: 0.7, 2: 0.85, 3: 1.0, 4: 1.2, 5: 1.45, 6: 1.65}

        t_mult = type_multipliers.get(property_type or 'unknown', 1.0)
        b_mult = bed_multipliers.get(bedrooms or 3, 1.0)

        estimated = base * t_mult * b_mult
        confidence = 0.5 if area_stats.get('transaction_count', 0) > 20 else 0.3
        return float(estimated), confidence


