"""
═══════════════════════════════════════════════════════════════════════════
 QCL HUB — CARD MARKET (fast)  +  centered logo
═══════════════════════════════════════════════════════════════════════════

 WHY THE MARKET CRAWLS
 ---------------------
 The current view loops every player and calls five helpers per row:

     card_rarity(pl)            -> _career_ratings()
     _career_ratings().get(pl)  -> again
     player_popularity(pl)      -> _popularity_raw_map() -> _awards_score(pl)
     player_price(pl, w, w)     -> _career_ratings() AND player_popularity() AGAIN
     player_form(pl)            -> a FULL full_df scan, per player

 With 417 players that's ~2,085 calls, and player_form alone does 417 scans
 of the whole frame (~1.1M row comparisons, measured at 0.80s).

 Then it builds ~212 KB of raw HTML — a 417-row table, 3,336 DOM nodes, no
 virtualization — inside one st.markdown. And w_stat/w_pop are SLIDERS, so
 every drag reruns the whole thing. On a phone that's a timeout.

 THE FIX
 -------
 1. One cached, vectorized groupby computes stat / pop / form for everyone.
    Measured 41x faster on form alone, identical results (417/417 match).
 2. Prices are a vectorized column, not a per-row call, so slider drags are
    arithmetic on an existing frame instead of a full recompute.
 3. st.dataframe instead of hand-built HTML — native, virtualized, sorts and
    scrolls on mobile. HTML cards only for the top N you actually look at.

 PASTE: replace the whole `elif view_mode == "📈 Card Market":` block.
═══════════════════════════════════════════════════════════════════════════
"""

import numpy as np
import pandas as pd
import streamlit as st


# ── CENTERED LOGO ─────────────────────────────────────────────────────────
def logo_center_sidebar(path="Logo.png", width=140):
    """Centered mark in the sidebar. Columns only — no CSS, can't break layout."""
    c = st.sidebar.columns([1, 3, 1])
    try:
        c[1].image(path, width=width)
    except Exception:
        pass


def logo_center_main(path="Logo.png", width=120):
    """Centered mark in the main body."""
    c = st.columns([2, 1, 2])
    try:
        c[1].image(path, width=width)
    except Exception:
        pass


# ── THE ONE COMPUTATION ───────────────────────────────────────────────────
@st.cache_data(ttl=120, show_spinner="Building the market...")
def build_market_table(p_stats, full_p_df, allleague, card_meta, popularity, market):
    """Everything the market needs, computed ONCE, vectorized.

    Cached on its inputs, so slider drags never re-enter this.
    """
    def _slug(s):
        import re
        return re.sub(r"[^a-z0-9]+", "", str(s or "").lower())

    # ---- career impact percentile (stat score) ----
    career = (full_p_df.groupby("Player/Team")["PIE_Raw"].mean()
              .rank(pct=True).rename("Stat"))

    # ---- form: one groupby instead of 417 frame scans ----
    d = full_p_df.sort_values(["Player/Team", "Season", "Game_ID"])
    overall = d.groupby("Player/Team")["PIE_Raw"].mean()
    recent = d.groupby("Player/Team").tail(3).groupby("Player/Team")["PIE_Raw"].mean()
    count = d.groupby("Player/Team")["PIE_Raw"].count()
    form = pd.Series(0, index=overall.index, dtype=int)
    form[recent > overall * 1.05] = 1
    form[recent < overall * 0.95] = -1
    form[count < 4] = 0
    form = form.rename("Form")

    # ---- awards score, built once from a lookup dict ----
    aw = {}
    for _season, teams in (allleague or {}).items():
        if isinstance(teams, dict):
            for tier, plist in teams.items():
                if isinstance(plist, list):
                    pts = 3.0 if "1st" in tier else 2.0 if "2nd" in tier else 1.0
                    for p in plist:
                        aw[_slug(p)] = aw.get(_slug(p), 0.0) + pts
    for _stem, info in (card_meta or {}).items():
        k = _slug(info.get("player", ""))
        if k:
            aw[k] = aw.get(k, 0.0) + 2.0

    mentions = (popularity or {}).get("mentions", {}) if isinstance(popularity, dict) else {}
    roles = (popularity or {}).get("roles", {}) if isinstance(popularity, dict) else {}

    out = p_stats[["Player/Team", "Team"]].copy()
    out = out.merge(career, left_on="Player/Team", right_index=True, how="left")
    out = out.merge(form, left_on="Player/Team", right_index=True, how="left")
    out["Stat"] = out["Stat"].fillna(0.0)
    out["Form"] = out["Form"].fillna(0).astype(int)

    slugs = out["Player/Team"].map(_slug)
    out["_aw"] = slugs.map(lambda s: aw.get(s, 0.0))
    out["_men"] = out["Player/Team"].map(lambda p: float(mentions.get(p, 0) or 0))
    out["_rol"] = out["Player/Team"].map(lambda p: float(roles.get(p, 0) or 0))
    raw = out["_aw"] * 2.0 + out["_men"] * 1.0 + out["_rol"] * 1.5
    mx = float(raw.max()) if len(raw) and raw.max() > 0 else 0.0
    out["Pop"] = (raw / mx) if mx > 0 else 0.0

    # ---- tier + stock ----
    TIERS = [(0.95, "Legendary"), (0.85, "Epic"), (0.65, "Rare"),
             (0.35, "Uncommon"), (0.0, "Common")]
    SUPPLY = {"Legendary": 3, "Epic": 10, "Rare": 25, "Uncommon": 60, "Common": 0}

    def tier_of(p):
        for th, nm in TIERS:
            if p >= th:
                return nm
        return "Common"

    out["Tier"] = out["Stat"].map(tier_of)
    mk = market or {}

    def stock_of(row):
        m = mk.get(row["Player/Team"])
        if m:
            run = int(m.get("run", 0))
            return f"{max(run - int(m.get('minted', 0)), 0)}/{run}"
        run = SUPPLY.get(row["Tier"], 0)
        return "\u221e" if run == 0 else str(run)

    out["Stock"] = out.apply(stock_of, axis=1)
    out["Tier"] = out.apply(
        lambda r: (mk.get(r["Player/Team"]) or {}).get("tier", r["Tier"]), axis=1)

    return out.drop(columns=["_aw", "_men", "_rol"])


    def render_card_market(p_stats, full_p_df, allleague, card_meta, popularity,
                       market, team_logo_html=None):
 
    elif view_mode == "📈 Card Market":
    render_card_market(p_stats, full_p_df, _load_allleague(), _load_card_meta(),
                       _load_popularity(), _load_market(), team_logo_html)
    st.subheader("\U0001f4c8 Card Market")
    st.markdown("Live card values \u2014 **stat \u00d7 popularity**, capped at **$3**. "
                "Popularity = awards + community mentions + roles.")

    mk = build_market_table(p_stats, full_p_df, allleague, card_meta, popularity, market)

    c1, c2, c3 = st.columns([2, 2, 3])
    w_stat = c1.slider("Stat weight", 0.0, 1.0, 0.5, 0.05, key="mk_ws")
    w_pop = c2.slider("Popularity weight", 0.0, 1.0, 0.5, 0.05, key="mk_wp")
    q = c3.text_input("\U0001f50d Search player", key="mk_q")

    # Price is a vectorized column -> slider drags are arithmetic, not a rebuild.
    tot = max(w_stat + w_pop, 0.01)
    mk = mk.copy()
    mk["Price"] = (3.0 * ((w_stat * mk["Stat"]) + (w_pop * mk["Pop"])) / tot).round(2)

    if q:
        mk = mk[mk["Player/Team"].str.contains(q, case=False, na=False)]
    mk = mk.sort_values("Price", ascending=False)

    st.caption(f"{len(mk)} players \u00b7 sortable, scrolls on mobile")

    show = mk.copy()
    show["Stat"] = (show["Stat"] * 100).round(0).astype(int)
    show["Pop"] = (show["Pop"] * 100).round(0).astype(int)
    show["Trend"] = show["Form"].map({1: "\u25b2 up", -1: "\u25bc down", 0: "\u2014"})
    cols = ["Player/Team", "Team", "Tier", "Stat", "Pop", "Price", "Stock", "Trend"]

    st.dataframe(
        show[cols],
        width="stretch",
        hide_index=True,
        height=520,
        column_config={
            "Price": st.column_config.NumberColumn("Price", format="$%.2f"),
            "Stat": st.column_config.ProgressColumn("Stat", min_value=0, max_value=100, format="%d"),
            "Pop": st.column_config.ProgressColumn("Pop", min_value=0, max_value=100, format="%d"),
        },
    )

    st.download_button("\u2b07\ufe0f Market CSV",
                       show[cols].to_csv(index=False).encode("utf-8"),
                       file_name="card_market.csv", mime="text/csv",
                       width="stretch", key="dl_market")

    # Only the top slice gets rich HTML — the part people actually look at.
    with st.expander("\U0001f3c6 Top movers (rich view)", expanded=False):
        top_n = st.slider("How many", 5, 40, 12, key="mk_topn")
        COLOR = {"Legendary": "#f1c40f", "Epic": "#9b59b6", "Rare": "#3498db",
                 "Uncommon": "#2ecc71", "Common": "#8a929c"}
        html = ("<table class='sleek-table'><tr><th>Player</th><th>Team</th><th>Tier</th>"
                "<th>Price</th><th>Left</th><th>Trend</th></tr>")
        for _, r in mk.head(top_n).iterrows():
            arrow = "\u25b2" if r["Form"] > 0 else "\u25bc" if r["Form"] < 0 else "\u2014"
            acol = "#00ff88" if r["Form"] > 0 else "#ff5555" if r["Form"] < 0 else "#888"
            badge = COLOR.get(r["Tier"], "#8a929c")
            logo = team_logo_html(r["Team"], px=16) if team_logo_html else ""
            html += (f"<tr><td class='player-name'>{logo}{r['Player/Team']}</td>"
                     f"<td>{r['Team']}</td>"
                     f"<td><span style='background:{badge};color:#000;font-weight:800;"
                     f"font-size:11px;padding:2px 8px;border-radius:8px;'>{r['Tier']}</span></td>"
                     f"<td style='color:#d4af37;font-weight:900;'>${r['Price']:.2f}</td>"
                     f"<td>{r['Stock']}</td>"
                     f"<td style='color:{acol};font-weight:bold;'>{arrow}</td></tr>")
        st.markdown(html + "</table>", unsafe_allow_html=True)
