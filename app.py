import streamlit as st
import pandas as pd
import plotly.express as px
import os

# 1. SPAM LEAGUE BRANDING (GOLD & BLACK THEME)
st.set_page_config(page_title="SPAM LEAGUE CENTRAL", page_icon="🏀", layout="wide")

st.markdown("""
    <style>
    /* SPAM GOLD & BLACK THEME */
    .main { 
        background: radial-gradient(circle, #1a1a1a 0%, #050505 100%); 
        color: #d4af37; /* Gold Text */
    }
    
    /* PERFECT CENTER LOGO CONTAINER */
    .centered-splash {
        display: flex; flex-direction: column; align-items: center;
        justify-content: center; text-align: center; height: 50vh; width: 100%;
    }

    /* GLASSMORPHISM STAT CARDS (GOLD BORDERS) */
    [data-testid="stMetric"] {
        background: rgba(255, 255, 255, 0.03) !important;
        backdrop-filter: blur(12px);
        border: 1px solid rgba(212, 175, 55, 0.3) !important;
        border-left: 6px solid #d4af37 !important;
        border-radius: 12px !important;
        padding: 22px !important;
        transition: transform 0.3s ease;
    }
    [data-testid="stMetric"]:hover { transform: scale(1.05); border-color: #d4af37 !important; }

    .header-banner {
        padding: 20px; text-align: center; background: #d4af37;
        border-bottom: 5px solid #000; color: #000; 
        font-family: 'Arial Black'; font-size: 28px;
    }

    /* GOLD TICKER */
    @keyframes ticker { 0% { transform: translateX(100%); } 100% { transform: translateX(-100%); } }
    .ticker-wrap {
        width: 100%; overflow: hidden; background: #000; color: #d4af37;
        padding: 12px 0; font-family: 'Arial Black'; border-bottom: 2px solid #d4af37;
    }
    .ticker-content { display: inline-block; white-space: nowrap; animation: ticker 40s linear infinite; }
    .ticker-item { display: inline-block; margin-right: 80px; font-size: 20px; }
    
    .footer-bar {
        position: fixed; left: 0; bottom: 0; width: 100%;
        background-color: #000; color: #888; text-align: center;
        padding: 8px; border-top: 1px solid #d4af37; font-size: 11px; z-index: 100;
    }
    </style>
    """, unsafe_allow_html=True)

# --- SPLASH SCREEN ---
if 'spam_active' not in st.session_state: st.session_state.spam_active = False
if not st.session_state.spam_active:
    st.markdown('<div class="centered-splash">', unsafe_allow_html=True)
    if os.path.exists("logo.jpg"): st.image("logo.jpg", width=350)
    st.markdown("<h1 style='font-size: 80px; color: #d4af37; margin-bottom: 0px;'>SPAM LEAGUE</h1>", unsafe_allow_html=True)
    st.markdown("<h3 style='color: white; letter-spacing: 5px; margin-top: 0px;'>COMMISSIONER DATA TERMINAL</h3>", unsafe_allow_html=True)
    l, c, r = st.columns([1, 1, 1])
    with c:
        if st.button("ENTER SPAM CENTRAL", use_container_width=True):
            st.session_state.spam_active = True
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# 2. DATA ENGINE
SHEET_ID = "1rksLYUcXQJ03uTacfIBD6SRsvtH-IE6djqT-LINwcH4"
URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"

@st.cache_data(ttl=60)
def load_data():
    try:
        data = pd.read_csv(URL)
        data.columns = data.columns.str.strip()
        name_col, type_col, team_col = 'Player/Team', 'Type', 'Team Name'
        
        stats = ['PTS', 'REB', 'AST', 'STL', 'BLK', 'FGA', 'Game_ID']
        for col in stats:
            if col in data.columns:
                data[col] = pd.to_numeric(data[col], errors='coerce').fillna(0)
        
        # FIX: Calculate PIE before segmenting for ticker logic
        data['PIE'] = (data['PTS'] + data['REB'] + data['AST'] + data['STL'] + data['BLK']) - (data['FGA'] * 0.5)
        
        df_players = data[data[type_col].str.lower() == 'player'].copy()
        df_teams_raw = data[data[type_col].str.lower() == 'team'].copy()
        
        # PER GAME CALCS
        gp = df_players.groupby(name_col)['Game_ID'].nunique().reset_index(name='GP')
        totals = df_players.groupby([name_col, team_col]).sum(numeric_only=True).reset_index()
        p_avg = pd.merge(totals, gp, on=name_col)
        
        for s in ['PTS', 'REB', 'AST', 'STL', 'BLK']:
            p_avg[f'{s}/G'] = (p_avg[s] / p_avg['GP']).round(1)
            
        t_totals = df_teams_raw.groupby(name_col).sum(numeric_only=True).reset_index()
        return p_avg, df_players, t_totals, name_col, team_col
    except Exception as e:
        st.error(f"Sync Error: {e}"); return None, None, None, None, None

p_avg, df_raw, t_totals, name_col, team_col = load_data()

# 3. HEADER & DYNAMIC TICKER
if p_avg is not None:
    st.markdown('<div class="header-banner">🏀 SPAM LEAGUE CENTRAL | OFFICIAL BROADCAST</div>', unsafe_allow_html=True)
    
    # TICKER LOGIC
    # 1. Week 1 High (Game IDs starting with '1')
    week1_data = df_raw[df_raw['Game_ID'].astype(str).str.startswith('1')]
    week1_high = week1_data.nlargest(1, 'PTS').iloc[0] if not week1_data.empty else None
    
    # 2. Last Game Results (Total Scores)
    last_game_ids = sorted(df_raw['Game_ID'].unique())[-2:]
    recent_news = []
    for gid in last_game_ids:
        game_total = df_raw[df_raw['Game_ID'] == gid]['PTS'].sum()
        recent_news.append(f"Game {gid} Total Score: {int(game_total)} PTS")

    ticker_text = [
        f"🏆 WEEK 1 HIGH: {week1_high[name_col]} ({int(week1_high['PTS'])} PTS)" if week1_high is not None else "WEEK 1 STATS PENDING",
        " | ".join(recent_news),
        f"🎯 LEAGUE SCORER: {p_avg.nlargest(1, 'PTS/G').iloc[0][name_col]} ({p_avg.nlargest(1, 'PTS/G').iloc[0]['PTS/G']})",
    ]
    st.markdown(f'<div class="ticker-wrap"><div class="ticker-content"><span class="ticker-item">{"  •  ".join(ticker_text)}</span></div></div>', unsafe_allow_html=True)

    # 4. TAB NAVIGATION
    tab_p, tab_lead, tab_t, tab_v, tab_r = st.tabs(["👤 PLAYERS", "🔝 STAT LEADERS", "🏘️ TEAM RANKINGS", "⚔️ VERSUS", "📖 RECORDS"])

    with tab_p:
        st.dataframe(p_avg[[name_col, team_col, 'GP', 'PTS/G', 'REB/G', 'AST/G', 'STL/G', 'BLK/G', 'PIE']].sort_values('PIE', ascending=False), use_container_width=True, hide_index=True)

    with tab_lead:
        st.header("🔝 CATEGORY LEADERS")
        cat = st.selectbox("Select Stat Category", ["PTS/G", "REB/G", "AST/G", "STL/G", "BLK/G", "PIE"])
        top_list = p_avg[[name_col, team_col, cat]].sort_values(cat, ascending=False).head(10)
        
        fig = px.bar(top_list, x=cat, y=name_col, color=cat, orientation='h', template="plotly_dark", color_continuous_scale="Viridis")
        st.plotly_chart(fig, use_container_width=True)
        # Fix: Added requested list underneath the graph
        st.subheader(f"Top 10 Rankings: {cat}")
        st.table(top_list)

    with tab_t:
        st.header("🏘️ TEAM POWER RANKINGS")
        # Power Rankings based on Team PIE
        team_power = p_avg.groupby(team_col)['PIE'].sum().reset_index().sort_values('PIE', ascending=False)
        for i, row in team_power.iterrows():
            st.metric(f"Rank {i+1}: {row[team_col]}", f"{round(row['PIE'], 1)} Impact Points")

    with tab_v:
        st.header("⚔️ HEAD-TO-HEAD")
        v_mode = st.radio("Mode", ["Player vs Player", "Team vs Team"], horizontal=True)
        c1, vs_text, c2 = st.columns([2, 0.5, 2])
        if v_mode == "Player vs Player":
            p1 = c1.selectbox("Player 1", p_avg[name_col].unique(), index=0)
            p2 = c2.selectbox("Player 2", p_avg[name_col].unique(), index=1)
            d1, d2 = p_avg[p_avg[name_col] == p1].iloc[0], p_avg[p_avg[name_col] == p2].iloc[0]
            for s in ['PTS/G', 'REB/G', 'AST/G', 'PIE']:
                sc1, sc2 = st.columns(2)
                sc1.metric(f"{p1} {s}", d1[s], delta=round(d1[s] - d2[s], 1))
                sc2.metric(f"{p2} {s}", d2[s], delta=round(d2[s] - d1[s], 1))
        else:
            t1_n = c1.selectbox("Team 1", t_totals[name_col].unique(), index=0)
            t2_n = c2.selectbox("Team 2", t_totals[name_col].unique(), index=1)
            t1, t2 = t_totals[t_totals[name_col] == t1_n].iloc[0], t_totals[t_totals[name_col] == t2_n].iloc[0]
            for s in ['PTS', 'REB', 'AST']:
                sc1, sc2 = st.columns(2)
                # Fix: Changed t1[n] to t1[s] to resolve Team vs Team crash
                sc1.metric(f"{t1_n} {s}", int(t1[s]), delta=int(t1[s] - t2[s]))
                sc2.metric(f"{t2_n} {s}", int(t2[s]), delta=int(t2[s] - t1[s]))

    with tab_r:
        st.header("📖 SEASON RECORDS")
        r_pts, r_reb = df_raw.nlargest(1, 'PTS').iloc[0], df_raw.nlargest(1, 'REB').iloc[0]
        c1, c2 = st.columns(2)
        c1.metric("Most Points (Game)", f"{int(r_pts['PTS'])}", r_pts[name_col])
        c2.metric("Most Rebounds (Game)", f"{int(r_reb['REB'])}", r_reb[name_col])

    st.markdown('<div class="footer-bar">© 2026 SPAM LEAGUE HUB | COMMISSIONER ACCESS</div>', unsafe_allow_html=True)