# ============================================================
# scoring.py — Entry Readiness Score Engine
# ============================================================
# Scores each stock 0-100 on "how ready is it to buy now?"
# Criteria: Discount to FV + Quality + FII Signal + 52W Proximity
# ============================================================

import pandas as pd
import numpy as np
from config import (ER_WEIGHT_DISCOUNT, ER_WEIGHT_QUALITY,
                    ER_WEIGHT_FII, ER_WEIGHT_PROXIMITY,
                    STATUS_STRONG, STATUS_CLOSE, STATUS_WATCH)


def _discount_score(discount_pct: float) -> float:
    """Score how deep below fair value the stock is. 40% = 100, 0% = 0."""
    return float(min(100, max(0, discount_pct * 2.5)))


def _quality_score(score_quality) -> float:
    """Use V2's pre-computed quality pillar score directly."""
    try:
        return float(min(100, max(0, score_quality or 0)))
    except Exception:
        return 50.0


def _fii_score(fii_selling_4q, fii_trend_pct) -> float:
    """Score FII signal. Selling = contrarian opportunity."""
    try:
        selling = bool(fii_selling_4q)
        trend   = float(fii_trend_pct or 0)
        if selling:
            return 100.0                   # FII consistently selling = maximum signal
        elif trend < -1:
            return 70.0                    # FII reducing (not full 4Q yet)
        elif trend > 2:
            return 30.0                    # FII buying — crowded
        else:
            return 50.0                    # Neutral
    except Exception:
        return 50.0


def _proximity_score(pct_above_52w_low) -> float:
    """Score closeness to 52W low. 0% above = 100, 50% above = 0."""
    try:
        pct = float(pct_above_52w_low or 50)
        return float(max(0, 100 - pct * 2))
    except Exception:
        return 50.0


def _get_status(score: float) -> tuple[str, str]:
    """Return (emoji + label, css_class) for a given Entry Readiness score."""
    if score >= STATUS_STRONG:
        return "🟢 STRONG ENTRY",  "strong"
    elif score >= STATUS_CLOSE:
        return "🟡 APPROACHING",   "close"
    elif score >= STATUS_WATCH:
        return "🟠 ON RADAR",      "watch"
    else:
        return "⚪ TOO EARLY",     "early"


def compute_entry_readiness(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add Entry_Readiness score and status columns to the DataFrame.
    Works with V2 column names (after COL_MAP rename).
    """
    df = df.copy()

    def _safe(col, default=0):
        if col in df.columns:
            return pd.to_numeric(df[col], errors="coerce").fillna(default)
        return pd.Series([default] * len(df), index=df.index)

    def _safeb(col):
        if col in df.columns:
            return df[col].fillna(False).astype(bool)
        return pd.Series([False] * len(df), index=df.index)

    # ── Raw inputs ────────────────────────────────────────────────────────────
    price      = _safe("Price")
    fair_value = _safe("Fair_Value")
    quality    = _safe("Score_Quality")
    fii_sell   = _safeb("FII_Selling_4Q")
    fii_trend  = _safe("FII_Trend_Pct")
    prox       = _safe("Pct_Above_52W_Low", 50)

    # ── Discount to fair value % ──────────────────────────────────────────────
    df["Discount_Pct"] = ((fair_value - price) / fair_value.replace(0, np.nan) * 100
                          ).fillna(0).clip(-100, 100).round(1)

    # ── Component scores ──────────────────────────────────────────────────────
    df["_sc_discount"]  = df["Discount_Pct"].apply(_discount_score)
    df["_sc_quality"]   = quality.apply(_quality_score)
    df["_sc_fii"]       = [_fii_score(fii_sell[i], fii_trend[i]) for i in range(len(df))]
    df["_sc_proximity"] = prox.apply(_proximity_score)

    # ── Entry Readiness Score (0-100) ─────────────────────────────────────────
    df["Entry_Readiness"] = (
        df["_sc_discount"]  * ER_WEIGHT_DISCOUNT +
        df["_sc_quality"]   * ER_WEIGHT_QUALITY  +
        df["_sc_fii"]       * ER_WEIGHT_FII       +
        df["_sc_proximity"] * ER_WEIGHT_PROXIMITY
    ).clip(0, 100).round(1)

    # ── Status ────────────────────────────────────────────────────────────────
    statuses = [_get_status(s) for s in df["Entry_Readiness"]]
    df["Status"]       = [s[0] for s in statuses]
    df["Status_Class"] = [s[1] for s in statuses]

    # Clean up intermediate columns
    df.drop(columns=["_sc_discount","_sc_quality","_sc_fii","_sc_proximity"],
            inplace=True, errors="ignore")

    return df.sort_values("Entry_Readiness", ascending=False).reset_index(drop=True)
