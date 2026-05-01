# ============================================================
# app.py — Bapi's Personal Watchlist Tracker
# ============================================================
# Tab 1: Auto Watchlist  — stocks auto-selected by criteria
# Tab 2: Manual Picks    — stocks you add yourself
# Tab 3: Stock Lookup    — deep dive on any stock
# ============================================================

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import os
from datetime import datetime

from config import (APP_TITLE, V2_CSV_URL, MIN_QUALITY_SCORE,
                    MIN_DISCOUNT_PCT, MIN_MCAP_CR, MAX_MCAP_CR,
                    MANUAL_CSV, CACHE_MINUTES)
from scoring import compute_entry_readiness

st.set_page_config(
    page_title="Bapi's Watchlist",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)



# ── Column map: V2 lowercase → display names ──────────────────────────────────
COL_MAP = {
    "ticker":"Ticker","name":"Name","sector":"Sector",
    "price":"Price","pe":"PE","pb":"PB","roe":"RoE","roce":"RoCE",
    "de":"DE","revenue_growth":"Revenue_Growth","market_cap_cr":"Market_Cap_Cr",
    "price_3m_ret":"Price_3M_Ret","price_6m_ret":"Price_6M_Ret",
    "low_52w":"Low_52W","high_52w":"High_52W",
    "pct_above_52w_low":"Pct_Above_52W_Low",
    "fii_pct":"FII_Pct","dii_pct":"DII_Pct","promoter_pct":"Promoter_Pct",
    "fii_selling_4q":"FII_Selling_4Q","dii_buying_4q":"DII_Buying_4Q",
    "fii_trend_pct":"FII_Trend_Pct","dii_trend_pct":"DII_Trend_Pct",
    "fii_label":"FII_Label","dii_label":"DII_Label",
    "composite_score":"Composite_Score","grade":"Grade","rank":"Rank",
    "score_value":"Score_Value","score_quality":"Score_Quality",
    "score_momentum":"Score_Momentum","score_smartmoney":"Score_SmartMoney",
    "fair_value":"Fair_Value","buy_zone_low":"Buy_Zone_Low",
    "buy_zone_high":"Buy_Zone_High","strong_buy_below":"Strong_Buy_Below",
    "value_signal":"Value_Signal","last_updated":"Last_Updated",
}

# ── Data loading ──────────────────────────────────────────────────────────────
@st.cache_data(ttl=CACHE_MINUTES * 60)
def load_v2_data() -> pd.DataFrame:
    """Load V2 cloud_data.csv from GitHub. Always fresh daily data."""
    try:
        df = pd.read_csv(V2_CSV_URL)
        df.columns = [COL_MAP.get(c, c) for c in df.columns]
        df = compute_entry_readiness(df)
        return df
    except Exception as e:
        st.error(f"Could not load V2 data: {e}")
        return pd.DataFrame()


def load_manual_picks() -> pd.DataFrame:
    """Load manual picks CSV."""
    try:
        if os.path.exists(MANUAL_CSV):
            df = pd.read_csv(MANUAL_CSV)
            if df.empty or len(df.columns) < 3:
                return pd.DataFrame(columns=["ticker","name","note",
                                             "target_buy_price","conviction","added_on"])
            return df
    except Exception:
        pass
    return pd.DataFrame(columns=["ticker","name","note",
                                  "target_buy_price","conviction","added_on"])


def save_manual_picks(df: pd.DataFrame):
    """Save manual picks to CSV."""
    os.makedirs("data", exist_ok=True)
    df.to_csv(MANUAL_CSV, index=False)


# ── Helpers ───────────────────────────────────────────────────────────────────
def _fmt_price(v):
    try: return f"₹{float(v):,.1f}"
    except: return "—"

def _fmt_pct(v, plus=False):
    try:
        f = float(v)
        return f"{'+' if plus and f>0 else ''}{f:.1f}%"
    except: return "—"

def _fmt_score(v):
    try: return f"{float(v):.1f}"
    except: return "—"

def _status_color(status: str) -> str:
    if "STRONG" in status: return "#E8F5E9"
    if "APPROACH" in status: return "#FFF9C4"
    if "RADAR" in status: return "#FFF3E0"
    return "#F5F5F5"

def _signal_color(sig: str) -> str:
    s = str(sig).upper()
    if "STRONG BUY" in s: return "#1B5E20"
    if "BUY"        in s: return "#2E7D32"
    if "WATCH"      in s: return "#F57F17"
    if "OVERVALUED" in s: return "#B71C1C"
    return "#555555"


# ── Main app ──────────────────────────────────────────────────────────────────
df = load_v2_data()

with st.sidebar:
    st.title("⚙️ Controls")
    if st.button("🔄 Refresh Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    if not df.empty and "Last_Updated" in df.columns:
        lu = df["Last_Updated"].dropna().iloc[0] if len(df) > 0 else "—"
        st.caption(f"V2 data: {lu}")

    st.divider()
    st.subheader("🔧 Criteria")
    min_quality  = st.slider("Min Quality Score", 40, 90, MIN_QUALITY_SCORE, step=5)
    min_discount = st.slider("Min Discount to FV %", 5, 50, MIN_DISCOUNT_PCT, step=5)
    min_mcap     = st.slider("Min Market Cap (₹Cr)", 200, 5000, MIN_MCAP_CR, step=100)
    max_mcap     = st.slider("Max Market Cap (₹Cr)", 5000, 100000, MAX_MCAP_CR, step=5000)
    fii_required = st.checkbox("FII Selling 4Q+ required", value=False)

    st.divider()
    # Value signal filter
    sig_options = ["STRONG BUY","BUY","WATCH","FAIR VALUE","OVERVALUED"]
    sel_signals = st.multiselect("Value Signal", sig_options, default=[],
                                  placeholder="All signals", key="sig_filter")

    # Company search
    all_names_sidebar = sorted(df["Name"].dropna().unique().tolist()) if not df.empty and "Name" in df.columns else []
    search_company = st.multiselect("🔎 Search Company", options=all_names_sidebar,
                                     default=[], placeholder="Type to search...",
                                     key="company_search")

    st.divider()
    if not df.empty and "Sector" in df.columns:
        all_sectors = sorted(df["Sector"].dropna().unique().tolist())
        sel_sectors = st.multiselect("Sectors", all_sectors, default=all_sectors, key="sectors")
    else:
        sel_sectors = []

st.title(APP_TITLE)
st.caption("Automated watchlist for growth stocks at value prices · Thesis: buy quality on dips, sell at fair value")

if df.empty:
    st.warning("No data loaded. Check V2 GitHub URL in config.py.")
    st.stop()

# ── Apply filters to get auto-watchlist ───────────────────────────────────────
wl = df.copy()
if "Score_Quality"  in wl.columns: wl = wl[pd.to_numeric(wl["Score_Quality"], errors="coerce").fillna(0) >= min_quality]
if "Discount_Pct"   in wl.columns: wl = wl[pd.to_numeric(wl["Discount_Pct"],  errors="coerce").fillna(0) >= min_discount]
if "Market_Cap_Cr"  in wl.columns:
    mc = pd.to_numeric(wl["Market_Cap_Cr"], errors="coerce").fillna(0)
    wl = wl[(mc >= min_mcap) & (mc <= max_mcap)]
if fii_required and "FII_Selling_4Q" in wl.columns:
    wl = wl[wl["FII_Selling_4Q"].astype(bool)]
if sel_sectors and "Sector" in wl.columns:
    wl = wl[wl["Sector"].isin(sel_sectors)]

# Value signal filter
if sel_signals and "Value_Signal" in wl.columns:
    wl = wl[wl["Value_Signal"].str.contains("|".join(sel_signals), na=False, regex=True)]

# Company search — show ONLY the searched companies (bypass all other filters)
if search_company and "Name" in df.columns:
    wl = df[df["Name"].isin(search_company)].copy()
    if "Entry_Readiness" not in wl.columns:
        wl = compute_entry_readiness(wl)

# Sort by Entry Readiness
if "Entry_Readiness" in wl.columns:
    wl = wl.sort_values("Entry_Readiness", ascending=False).reset_index(drop=True)

# ── Summary metrics ───────────────────────────────────────────────────────────
n_strong  = len(wl[wl["Status"].str.contains("STRONG",  na=False)]) if "Status" in wl.columns else 0
n_close   = len(wl[wl["Status"].str.contains("APPROACH",na=False)]) if "Status" in wl.columns else 0
n_radar   = len(wl[wl["Status"].str.contains("RADAR",   na=False)]) if "Status" in wl.columns else 0
avg_er    = wl["Entry_Readiness"].mean() if "Entry_Readiness" in wl.columns and len(wl) > 0 else 0

c1,c2,c3,c4,c5 = st.columns(5)
c1.metric("Qualifying Stocks", str(len(wl)))
c2.metric("🟢 Strong Entry",   str(n_strong))
c3.metric("🟡 Approaching",    str(n_close))
c4.metric("🟠 On Radar",       str(n_radar))
c5.metric("Avg Entry Score",   f"{avg_er:.1f}/100")

# ══════════════════════════════════════════════════════════════════════════════
# TABS
# ══════════════════════════════════════════════════════════════════════════════
t1, t2, t3 = st.tabs(["🎯 Auto Watchlist", "➕ Manual Picks", "🔍 Stock Lookup"])


# ══════ TAB 1 — AUTO WATCHLIST ════════════════════════════════════════════════
with t1:
    if wl.empty:
        st.info(f"No stocks match current criteria (Quality ≥ {min_quality}, Discount ≥ {min_discount}%). "
                f"Try reducing thresholds in the sidebar.")
    else:
        st.subheader(f"📋 {len(wl)} stocks qualify — sorted by Entry Readiness")
        st.caption(
            f"Criteria: Quality Score ≥ {min_quality}  ·  Discount to Fair Value ≥ {min_discount}%  "
            f"·  Market Cap ₹{min_mcap:,}–{max_mcap:,} Cr"
            + ("  ·  FII Selling required" if fii_required else "")
        )

        # ── Track which company is selected via session state ──────────────────
        if "selected_company" not in st.session_state:
            st.session_state["selected_company"] = None

        # ── SUMMARY TABLE — one row per stock, company name is a button ────────
        # Header row
        h = st.columns([3, 2, 1.2, 1.2, 1.5, 1.5, 1.2, 1.2, 1.5])
        for col, label in zip(h, ["Company","Sector","Price","Entry Score",
                                   "Status","Signal","Quality","Discount %","Fair Value"]):
            col.markdown(f"**{label}**")
        st.markdown("---")

        for _, row in wl.iterrows():
            name  = str(row.get("Name",""))
            sect  = str(row.get("Sector",""))
            price = float(row.get("Price",0) or 0)
            er    = float(row.get("Entry_Readiness",0) or 0)
            status= str(row.get("Status",""))
            sig   = str(row.get("Value_Signal",""))
            qual  = float(row.get("Score_Quality",0) or 0)
            disc  = float(row.get("Discount_Pct",0) or 0)
            fv    = float(row.get("Fair_Value",0) or 0)

            # Row colour based on status
            is_selected = st.session_state.get("selected_company") == name

            c1,c2,c3,c4,c5,c6,c7,c8,c9 = st.columns([3,2,1.2,1.2,1.5,1.5,1.2,1.2,1.5])
            # Company name as a clickable button
            btn_label = f"{'▶ ' if is_selected else ''}{name}"
            if c1.button(btn_label, key=f"btn_{name}", use_container_width=True):
                if st.session_state.get("selected_company") == name:
                    st.session_state["selected_company"] = None  # toggle off
                else:
                    st.session_state["selected_company"] = name
                st.rerun()
            c2.write(sect)
            c3.write(f"₹{price:.0f}")
            c4.write(f"**{er:.0f}**")
            c5.write(status.split("  ")[0] if "  " in status else status[:15])
            c6.write(sig.split()[0] if sig else "—")
            c7.write(f"{qual:.0f}")
            c8.write(f"{disc:.1f}%")
            c9.write(f"₹{fv:.0f}")

        st.divider()

        # ── DETAIL PANEL — shows when a company is selected ────────────────────
        sel_name = st.session_state.get("selected_company")
        if sel_name:
            match = wl[wl["Name"] == sel_name]
            if match.empty:
                match = df[df["Name"] == sel_name]
            if not match.empty:
                row   = match.iloc[0]
                er    = float(row.get("Entry_Readiness",0) or 0)
                status= str(row.get("Status",""))
                sig   = str(row.get("Value_Signal",""))
                price = float(row.get("Price",0) or 0)
                fv    = float(row.get("Fair_Value",0) or 0)
                disc  = float(row.get("Discount_Pct",0) or 0)
                qual  = float(row.get("Score_Quality",0) or 0)
                roe   = float(row.get("RoE",0) or 0)
                roce  = float(row.get("RoCE",0) or 0)
                de    = float(row.get("DE",0) or 0)
                rg    = float(row.get("Revenue_Growth",0) or 0)
                fii_s = bool(row.get("FII_Selling_4Q",False))
                dii_b = bool(row.get("DII_Buying_4Q",False))
                fii_t = float(row.get("FII_Trend_Pct",0) or 0)
                prom  = float(row.get("Promoter_Pct",0) or 0)
                mc    = float(row.get("Market_Cap_Cr",0) or 0)
                bz_lo = float(row.get("Buy_Zone_Low",0) or 0)
                bz_hi = float(row.get("Buy_Zone_High",0) or 0)
                sbz   = float(row.get("Strong_Buy_Below",0) or 0)
                p3m   = float(row.get("Price_3M_Ret",0) or 0)
                prox  = float(row.get("Pct_Above_52W_Low",50) or 50)
                sect  = str(row.get("Sector",""))

                st.markdown(f"### 📊 {sel_name}  —  {sect}")
                banner_col = _status_color(status)
                st.markdown(
                    f"<div style='background:{banner_col};padding:10px 16px;"
                    f"border-radius:8px;font-size:15px;font-weight:600;margin-bottom:12px'>"
                    f"{status}  ·  Entry Readiness: {er:.1f}/100</div>",
                    unsafe_allow_html=True)

                a,b,c,d,e,f6 = st.columns(6)
                a.metric("Entry Score",  f"{er:.1f}")
                b.metric("Price",        f"₹{price:.0f}")
                c.metric("Fair Value",   f"₹{fv:.0f}")
                d.metric("Discount",     f"{disc:.1f}%", delta=f"BZ ₹{bz_lo:.0f}–{bz_hi:.0f}")
                e.metric("Quality",      f"{qual:.0f}/100")
                f6.metric("Signal",      sig.split()[0] if sig else "—")

                st.divider()
                left, mid, right = st.columns(3)
                with left:
                    st.markdown("**📊 Quality**")
                    for k,v in {"RoE":f"{roe:.1f}%","RoCE":f"{roce:.1f}%",
                                "Rev Growth":f"{rg:.1f}%","D/E":f"{de:.2f}x",
                                "MCap":f"₹{mc:,.0f}Cr","3M Ret":f"{p3m:+.1f}%"}.items():
                        ka,va=st.columns([2,3]); ka.caption(k); va.write(v)
                with mid:
                    st.markdown("**💰 Valuation**")
                    for k,v in {"Price":f"₹{price:.0f}","Fair Value":f"₹{fv:.0f}",
                                "Strong Buy":f"₹{sbz:.0f}","Buy Zone":f"₹{bz_lo:.0f}–₹{bz_hi:.0f}",
                                "Discount":f"{disc:.1f}%","Signal":sig}.items():
                        ka,va=st.columns([2,3]); ka.caption(k); va.write(v)
                with right:
                    st.markdown("**📡 Smart Money**")
                    fii_icon = "🔴 Selling 4Q+" if fii_s else "🟢 Not selling"
                    dii_icon = "🟢 Buying 4Q+" if dii_b else "⚪ Neutral"
                    combo    = "✅ Classic setup" if fii_s and dii_b else ("⚠️ FII only" if fii_s else "—")
                    for k,v in {"FII":fii_icon,"DII":dii_icon,"Setup":combo,
                                "FII Trend":f"{fii_t:+.1f}%","Promoter":f"{prom:.1f}%",
                                "52W Prox":f"{prox:.1f}%"}.items():
                        ka,va=st.columns([2,3]); ka.caption(k); va.write(v)

                # Entry Readiness breakdown
                st.divider()
                st.markdown("**Entry Readiness Breakdown**")
                from scoring import (_discount_score, _quality_score,
                                     _fii_score, _proximity_score)
                sc_d = _discount_score(disc)
                sc_q = _quality_score(qual)
                sc_f = _fii_score(fii_s, fii_t)
                sc_p = _proximity_score(prox)
                bdata = pd.DataFrame({
                    "Component": ["Discount to FV (40%)","Quality Score (30%)",
                                  "FII Signal (20%)","52W Proximity (10%)"],
                    "Score (0–100)": [sc_d, sc_q, sc_f, sc_p],
                    "Weighted":      [sc_d*0.40, sc_q*0.30, sc_f*0.20, sc_p*0.10],
                })
                fig_b = go.Figure(go.Bar(
                    x=bdata["Weighted"], y=bdata["Component"],
                    orientation="h",
                    marker_color=["#1565C0","#2E7D32","#6A1B9A","#E65100"],
                    text=[f"{v:.0f}/100" for v in bdata["Score (0–100)"]],
                    textposition="outside",
                ))
                fig_b.update_layout(
                    xaxis=dict(range=[0,50], title="Weighted contribution"),
                    height=200, margin=dict(l=10,r=80,t=10,b=20))
                st.plotly_chart(fig_b, use_container_width=True)

                # Add to Manual Picks
                st.divider()
                manual_df_curr = load_manual_picks()
                already = (not manual_df_curr.empty and "name" in manual_df_curr.columns
                           and sel_name in manual_df_curr["name"].tolist())
                if already:
                    st.success(f"✅ {sel_name} is already in your Manual Picks.")
                else:
                    with st.expander(f"➕ Add {sel_name} to Manual Picks"):
                        with st.form(f"add_wl_{sel_name}"):
                            note_wl = st.text_input("Your thesis note (optional)")
                            tgt_wl  = st.number_input("Target buy price (₹)",
                                                       min_value=0.0,
                                                       value=float(bz_lo) if bz_lo > 0 else float(price),
                                                       step=1.0)
                            conv_wl = st.selectbox("Conviction", ["High","Medium","Low"])
                            if st.form_submit_button(f"➕ Add {sel_name}"):
                                new_row = pd.DataFrame([{
                                    "ticker":           str(row.get("Ticker","")),
                                    "name":             sel_name,
                                    "note":             note_wl,
                                    "target_buy_price": tgt_wl,
                                    "conviction":       conv_wl,
                                    "added_on":         datetime.now().strftime("%Y-%m-%d"),
                                }])
                                manual_df_curr = pd.concat([manual_df_curr, new_row], ignore_index=True)
                                save_manual_picks(manual_df_curr)
                                st.success(f"✅ Added {sel_name} to Manual Picks!")
                                st.rerun()

        # ── BUBBLE CHART ───────────────────────────────────────────────────────
        st.divider()
        st.markdown("**📈 Entry Readiness Map** — top-right = high quality + deep value")
        if len(wl) > 1 and all(c in wl.columns for c in ["Discount_Pct","Score_Quality","Entry_Readiness"]):
            fig = px.scatter(
                wl, x="Discount_Pct", y="Score_Quality",
                size="Entry_Readiness", color="Entry_Readiness",
                color_continuous_scale="RdYlGn", range_color=[30,100],
                hover_name="Name",
                hover_data={"Entry_Readiness":":.1f","Status":True,
                            "Value_Signal":True,"Price":":.0f","Fair_Value":":.0f"},
                labels={"Discount_Pct":"Discount to Fair Value %",
                        "Score_Quality":"Quality Score (0–100)",
                        "Entry_Readiness":"Entry Readiness"},
            )
            fig.add_vline(x=min_discount, line_dash="dot", line_color="grey",
                          annotation_text=f"Min {min_discount}%")
            fig.add_hline(y=min_quality, line_dash="dot", line_color="grey",
                          annotation_text=f"Min quality {min_quality}")
            fig.update_layout(height=420, coloraxis_showscale=True,
                              margin=dict(t=30,b=40,l=60,r=40))
            st.plotly_chart(fig, use_container_width=True)


# ══════ TAB 2 — MANUAL PICKS ══════════════════════════════════════════════════
with t2:
    st.subheader("➕ Manual Picks")
    st.caption(
        "Add stocks that didn't make the auto list but you're interested in. "
        "V2 data is auto-filled — you just add your note and target price."
    )

    manual_df = load_manual_picks()

    # ── Add new pick ───────────────────────────────────────────────────────────
    with st.form("add_pick"):
        st.markdown("**Add a stock to your manual watchlist**")
        col1, col2, col3 = st.columns([3,2,2])
        with col1:
            all_names = df["Name"].dropna().tolist() if "Name" in df.columns else []
            pick_name = st.selectbox("Stock", [""] + sorted(all_names), key="pick_name")
        with col2:
            pick_target = st.number_input("Your target buy price (₹)", min_value=0.0, value=0.0, step=1.0)
        with col3:
            pick_conviction = st.selectbox("Conviction", ["High","Medium","Low"])
        pick_note = st.text_input("Why are you watching this? (your thesis note)")
        submitted = st.form_submit_button("➕ Add to Watchlist")

        if submitted and pick_name:
            # Get ticker from V2
            ticker_row = df[df["Name"] == pick_name]
            ticker_val = ticker_row["Ticker"].iloc[0] if not ticker_row.empty and "Ticker" in ticker_row.columns else ""
            new_row = pd.DataFrame([{
                "ticker":          ticker_val,
                "name":            pick_name,
                "note":            pick_note,
                "target_buy_price":pick_target if pick_target > 0 else "",
                "conviction":      pick_conviction,
                "added_on":        datetime.now().strftime("%Y-%m-%d"),
            }])
            manual_df = pd.concat([manual_df, new_row], ignore_index=True)
            save_manual_picks(manual_df)
            st.success(f"✅ Added {pick_name} to your manual watchlist!")
            st.rerun()

    st.divider()

    # ── Show manual picks with V2 data ────────────────────────────────────────
    if manual_df.empty or len(manual_df) == 0:
        st.info("No manual picks yet. Add stocks above that you're watching but didn't auto-qualify.")
    else:
        st.markdown(f"**Your {len(manual_df)} manual picks:**")

        for _, mrow in manual_df.iterrows():
            mname = str(mrow.get("name",""))
            mnote = str(mrow.get("note",""))
            mtarget = mrow.get("target_buy_price","")
            mconv  = str(mrow.get("conviction",""))
            madded = str(mrow.get("added_on",""))

            # Look up V2 data
            v2row = df[df["Name"] == mname]
            has_v2 = not v2row.empty

            if has_v2:
                r = v2row.iloc[0]
                mprice = float(r.get("Price",0) or 0)
                mfv    = float(r.get("Fair_Value",0) or 0)
                mdisc  = float(r.get("Discount_Pct",0) or 0)
                msig   = str(r.get("Value_Signal",""))
                mqual  = float(r.get("Score_Quality",0) or 0)
                mer    = float(r.get("Entry_Readiness",0) or 0)
                mstatus= str(r.get("Status",""))
                header = (f"{mstatus}  **{mname}** [{mconv} conviction]  ·  "
                         f"₹{mprice:.0f}  ·  Discount: {mdisc:.1f}%  ·  Entry Score: {mer:.0f}")
            else:
                header = f"⚪ **{mname}** [{mconv} conviction] — not in V2 universe"

            with st.expander(header):
                if mnote:
                    st.info(f"📝 Your thesis: {mnote}")

                if has_v2:
                    a,b,c,d = st.columns(4)
                    a.metric("Price", f"₹{mprice:.0f}")
                    a.metric("Fair Value", f"₹{mfv:.0f}")
                    b.metric("Discount", f"{mdisc:.1f}%")
                    b.metric("Signal", msig.split()[0] if msig else "—")
                    c.metric("Quality Score", f"{mqual:.0f}/100")
                    c.metric("Entry Readiness", f"{mer:.1f}")
                    if mtarget and float(str(mtarget).replace("","0") or 0) > 0:
                        try:
                            tgt = float(mtarget)
                            upside = (tgt - mprice) / mprice * 100 if mprice > 0 else 0
                            d.metric("Your Target", f"₹{tgt:.0f}")
                            d.metric("Upside to Target", f"{upside:+.1f}%")
                        except Exception:
                            d.metric("Your Target", str(mtarget))
                    d.metric("Added", madded)

                # Remove button
                if st.button(f"🗑️ Remove {mname}", key=f"rm_{mname}_{madded}"):
                    manual_df = manual_df[manual_df["name"] != mname].reset_index(drop=True)
                    save_manual_picks(manual_df)
                    st.rerun()


# ══════ TAB 3 — STOCK LOOKUP ══════════════════════════════════════════════════
with t3:
    st.subheader("🔍 Stock Lookup")
    st.caption("Search any stock from the V2 universe — full entry readiness profile.")

    all_names = sorted(df["Name"].dropna().unique().tolist()) if "Name" in df.columns else []
    lookup_name = st.selectbox("Search stock", [""] + all_names, key="lookup")

    if lookup_name:
        rows = df[df["Name"] == lookup_name]
        if rows.empty:
            st.warning(f"{lookup_name} not found in V2 data.")
        else:
            r = rows.iloc[0]
            er     = float(r.get("Entry_Readiness",0) or 0)
            status = str(r.get("Status",""))
            sig    = str(r.get("Value_Signal",""))
            price  = float(r.get("Price",0) or 0)
            fv     = float(r.get("Fair_Value",0) or 0)
            disc   = float(r.get("Discount_Pct",0) or 0)
            qual   = float(r.get("Score_Quality",0) or 0)
            roe    = float(r.get("RoE",0) or 0)
            roce   = float(r.get("RoCE",0) or 0)
            de     = float(r.get("DE",0) or 0)
            rg     = float(r.get("Revenue_Growth",0) or 0)
            fii_s  = bool(r.get("FII_Selling_4Q",False))
            dii_b  = bool(r.get("DII_Buying_4Q",False))
            fii_t  = float(r.get("FII_Trend_Pct",0) or 0)
            prom   = float(r.get("Promoter_Pct",0) or 0)
            bz_lo  = float(r.get("Buy_Zone_Low",0) or 0)
            bz_hi  = float(r.get("Buy_Zone_High",0) or 0)
            sbz    = float(r.get("Strong_Buy_Below",0) or 0)
            prox   = float(r.get("Pct_Above_52W_Low",50) or 50)
            mc     = float(r.get("Market_Cap_Cr",0) or 0)
            sect   = str(r.get("Sector",""))
            comp   = float(r.get("Composite_Score",0) or 0)
            grade  = str(r.get("Grade",""))
            rnk    = str(r.get("Rank","—"))

            # Header
            st.markdown(f"## {lookup_name}")
            st.markdown(f"**{sect}**  ·  ₹{mc:,.0f} Cr  ·  V2 Rank #{rnk} ({grade})")

            # Status banner
            col = _status_color(status)
            st.markdown(
                f'<div style="background:{col};padding:12px 16px;border-radius:8px;'
                f'font-size:16px;font-weight:600;margin:12px 0">'
                f'{status}  ·  Entry Readiness: {er:.1f}/100</div>',
                unsafe_allow_html=True
            )

            # Verdict
            qualifies = (qual >= min_quality and disc >= min_discount and
                         min_mcap <= mc <= max_mcap)
            if qualifies:
                st.success(f"✅ This stock qualifies for your watchlist (Quality ≥ {min_quality}, Discount ≥ {min_discount}%)")
            else:
                reasons = []
                if qual < min_quality: reasons.append(f"Quality {qual:.0f} < {min_quality}")
                if disc < min_discount: reasons.append(f"Discount {disc:.1f}% < {min_discount}%")
                if mc < min_mcap: reasons.append(f"MCap ₹{mc:,.0f}Cr < ₹{min_mcap:,}Cr")
                if mc > max_mcap: reasons.append(f"MCap ₹{mc:,.0f}Cr > ₹{max_mcap:,}Cr")
                st.warning(f"⚠️ Does not qualify: {' · '.join(reasons)}")

            st.divider()
            c1, c2, c3 = st.columns(3)

            with c1:
                st.markdown("#### 💰 Valuation")
                for k,v in {
                    "Current Price":  f"₹{price:.0f}",
                    "Fair Value":     f"₹{fv:.0f}",
                    "Discount to FV": f"{disc:.1f}%",
                    "Strong Buy":     f"₹{sbz:.0f}",
                    "Buy Zone":       f"₹{bz_lo:.0f} – ₹{bz_hi:.0f}",
                    "V2 Signal":      sig,
                    "52W Proximity":  f"{prox:.1f}% above low",
                }.items():
                    a,b = st.columns([2,3]); a.caption(k); b.write(v)

            with c2:
                st.markdown("#### 📊 Quality")
                for k,v in {
                    "Quality Score":    f"{qual:.1f}/100",
                    "RoE":              f"{roe:.1f}%",
                    "RoCE":             f"{roce:.1f}%",
                    "Revenue Growth":   f"{rg:.1f}%",
                    "Debt/Equity":      f"{de:.2f}x",
                    "V2 Composite":     f"{comp:.1f}/100",
                    "V2 Grade":         grade,
                }.items():
                    a,b = st.columns([2,3]); a.caption(k); b.write(v)

            with c3:
                st.markdown("#### 📡 Smart Money")
                for k,v in {
                    "FII Selling 4Q+": "Yes 🔴" if fii_s else "No 🟢",
                    "DII Buying 4Q+":  "Yes 🟢" if dii_b else "No ⚪",
                    "FII Trend (4Q)":  f"{fii_t:+.1f}%",
                    "Promoter":        f"{prom:.1f}%",
                    "Classic Setup":   "✅ Yes" if fii_s and dii_b else "❌ No",
                }.items():
                    a,b = st.columns([2,3]); a.caption(k); b.write(v)

            # Entry readiness breakdown
            st.divider()
            st.markdown("#### Entry Readiness Breakdown")
            from scoring import (_discount_score, _quality_score,
                                 _fii_score, _proximity_score)
            sc_d = _discount_score(disc)
            sc_q = _quality_score(qual)
            sc_f = _fii_score(fii_s, fii_t)
            sc_p = _proximity_score(prox)
            bdata = {
                "Component": ["Discount to FV (40%)","Quality Score (30%)",
                               "FII Signal (20%)","52W Proximity (10%)"],
                "Raw Score":  [sc_d, sc_q, sc_f, sc_p],
                "Weight":     [0.40, 0.30, 0.20, 0.10],
                "Contribution":[sc_d*0.40, sc_q*0.30, sc_f*0.20, sc_p*0.10],
            }
            bd = pd.DataFrame(bdata)
            bd["Total"] = bd["Contribution"].sum()
            st.dataframe(
                bd[["Component","Raw Score","Weight","Contribution"]]
                .style.format({"Raw Score":"{:.1f}","Weight":"{:.0%}","Contribution":"{:.1f}"}),
                use_container_width=True, hide_index=True
            )
            st.markdown(f"**Total Entry Readiness: {er:.1f}/100**  ·  {status}")

            # Add to manual picks shortcut
            st.divider()
            if not qualifies:
                with st.expander("➕ Add to Manual Picks anyway"):
                    with st.form(f"add_{lookup_name}"):
                        note2   = st.text_input("Your thesis note")
                        tgt2    = st.number_input("Target buy price (₹)", min_value=0.0, value=float(bz_lo) if bz_lo > 0 else 0.0)
                        conv2   = st.selectbox("Conviction", ["High","Medium","Low"])
                        if st.form_submit_button("Add to Manual Picks"):
                            ticker_v = str(r.get("Ticker",""))
                            new_row = pd.DataFrame([{
                                "ticker": ticker_v, "name": lookup_name,
                                "note": note2, "target_buy_price": tgt2,
                                "conviction": conv2,
                                "added_on": datetime.now().strftime("%Y-%m-%d"),
                            }])
                            manual_df = load_manual_picks()
                            manual_df = pd.concat([manual_df, new_row], ignore_index=True)
                            save_manual_picks(manual_df)
                            st.success(f"✅ Added {lookup_name} to Manual Picks!")
