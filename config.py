# ============================================================
# config.py — Bapi's Personal Watchlist Tracker
# ============================================================

APP_TITLE   = "🎯 Bapi's Watchlist Tracker"
APP_VERSION = "1.0"

# ── V2 Data source ────────────────────────────────────────────────────────────
# Reads directly from V2's GitHub — always latest daily data
V2_CSV_URL = (
    "https://raw.githubusercontent.com/BRRBlore/smart-stock-ranker"
    "/main/data/cloud_data.csv"
)

# ── Auto-selection criteria ───────────────────────────────────────────────────
MIN_QUALITY_SCORE   = 60    # confirmed growth stock (RoE + RoCE + Growth + Debt)
MIN_DISCOUNT_PCT    = 20    # minimum % below fair value to qualify
MIN_MCAP_CR         = 500   # ₹500 Cr minimum
MAX_MCAP_CR         = 50_000 # ₹50,000 Cr — mid & small cap focus

# ── Entry Readiness Score weights ─────────────────────────────────────────────
ER_WEIGHT_DISCOUNT  = 0.40  # how deep below fair value
ER_WEIGHT_QUALITY   = 0.30  # business quality score
ER_WEIGHT_FII       = 0.20  # institutional selling signal
ER_WEIGHT_PROXIMITY = 0.10  # closeness to 52W low

# ── Status thresholds ─────────────────────────────────────────────────────────
STATUS_STRONG  = 75   # 🟢 STRONG ENTRY
STATUS_CLOSE   = 60   # 🟡 APPROACHING
STATUS_WATCH   = 40   # 🟠 ON RADAR
                      # <40 = ⚪ TOO EARLY

# ── Manual picks file ─────────────────────────────────────────────────────────
MANUAL_CSV = "data/manual_picks.csv"

# ── Local data cache ─────────────────────────────────────────────────────────
CACHE_MINUTES = 60    # reload V2 data at most every 60 min
