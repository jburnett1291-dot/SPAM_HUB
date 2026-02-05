import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path
import os

# 1. SPAM LEAGUE BRANDING & ELIMINATE TOOLBAR
st.set_page_config(page_title="SPAM LEAGUE CENTRAL", page_icon="🏀", layout="wide")

# This CSS hides the 'Edit', 'Share', and 'Deploy' buttons for a clean broadcast look
hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            div[data-testid="stToolbar"] {visibility: hidden;}
            .main { background: radial-gradient(circle, #1a1a1a 0%, #050505 100%); color: #d4af37; }
            .centered-splash { display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center; height: 50vh; width: 100%; }
            [data-testid="stMetric"] { background: rgba(255, 255, 255, 0.03) !important; backdrop-filter: blur(12px); border: 1px solid rgba(212, 175, 55, 0.3) !important; border-left: 6px solid #d4af37 !important; border-radius: 12px !important; padding: 22px !important; }
            .header-banner { padding: 20px; text-align: center; background: #d4af37; border-bottom: 5px solid #000; color: #000; font-family: 'Arial Black'; font-size: 28px; }
            @keyframes ticker { 0% { transform: translateX(100%); } 100% { transform: translateX(-100%); } }
            .ticker-wrap { width: 100%; overflow: hidden; background: #000; color: #d4af37; padding: 12px 0; font-family: 'Arial Black'; border-bottom: 2px solid #d4af37; }
            .ticker-content { display: inline-block; white-space: nowrap; animation: ticker 40s linear infinite; }
            .ticker-item { display: inline-block; margin-right: 80px; font-size: 20px; }
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)

# Path Logic for Logo (Detects logo.jpg in E:\SPAM_HUB)
current_dir = Path(__file__).parent if "__file__" in locals() else Path.cwd()
logo_path = current_dir / "logo.jpg"

# --- SPLASH SCREEN ---
if 'spam_active' not in st.session_state:
    st.session_state.spam_active = False

if not st.session_state.spam_active:
    st.markdown('<div class="centered-splash">', unsafe_allow_html=True)
    if logo_path.exists():
        st.image(str(logo_path), width=400)
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
        
        # Calculate PIE immediately for all rows
        data['PIE'] = (data['PTS'] + data['REB'] + data['AST'] + data['STL'] + data['BLK']) - (data['FGA'] * 0.5)
        
        df_p = data[data[type_col].str.lower() == 'player'].copy()
        df_t_raw = data[data[type_col].str.lower() == 'team'].copy()
        
        gp = df_p.groupby(name_col)['Game_ID'].nunique().reset_index(name='GP')
        p_avg = pd.merge(df_p.groupby([name_col, team_col]).sum(numeric_only=True).reset_index(), gp, on=name_col)
        for s in ['PTS', 'REB', 'AST', 'STL', 'BLK']:
            p_avg[f'{s}/G'] = (p_avg[s] / p_avg['GP']).round(1)
            
        t_totals = df_t_raw.groupby(name_col).sum(numeric_only=True).reset_index()
        return p_avg, df_p, t_totals, name_col, team_col
    except Exception as e:
        st.error(f"Sync Error: {e}"); return None, None, None, None, None

p_avg, df_raw, t_totals, name_col, team_col = load_data()

# 3. HUB BROADCAST
if p_avg is not None:
    if logo_path.exists(): st.sidebar.image(str(logo_path), use_container_width=True)
    st.markdown('<div class="header-banner">🏀 SPAM LEAGUE CENTRAL | OFFICIAL BROADCAST</div>', unsafe_allow_html=True)
    
    # TICKER LOGIC (Week 1 News + Recent Game Totals)
    week1_data = df_raw[df_raw['Game_ID'].astype(str).str.startswith('1')]
    week1_high = week1_data.nlargest(1, 'PTS').iloc[0] if not week1_data.empty else None
    last_game_ids = sorted(df_raw['Game_ID'].unique())[-2:]
    recent_news = [f"Game {gid} Total: {int(df_raw[df_raw['Game_ID'] == gid]['PTS'].sum())} PTS" for gid in last_game_ids]

    ticker_text = [
        f"🏆 WEEK 1 HIGH: {week1_high[name_col]} ({int(week1_high['PTS'])} PTS)" if week1_high is not None else "WAITING FOR WEEK 1 DATA",
        " | ".join(recent_news),
        f"🎯 LEADER: {p_avg.nlargest(1, 'PTS/G').iloc[0][name_col]} ({p_avg.nlargest(1, 'PTS/G').iloc[0]['PTS/G']})"
    ]
    st.markdown(f'<div class="ticker-wrap"><div class="ticker-content"><span class="ticker-item">{"  •  ".join(ticker_text)}</span></div></div>', unsafe_allow_html=True)

    # 4. TAB NAVIGATION
    tab_p, tab_lead, tab_t, tab_v, tab_r = st.tabs(["👤 PLAYERS", "🔝 STAT LEADERS", "🏘️ TEAM RANKINGS", "⚔️ VERSUS", "📖 RECORDS"])

    with tab_lead: # STAT LEADERS (With Table)
        st.header("🔝 CATEGORY LEADERS")
        cat = st.selectbox("Select Category", ["PTS/G", "REB/G", "AST/G", "STL/G", "BLK/G", "PIE"])
        top_list = p_avg[[name_col, team_col, cat]].sort_values(cat, ascending=False).head(10)
        fig = px.bar(top_list, x=cat, y=name_col, color=cat, orientation='h', template="plotly_dark", color_continuous_scale="Viridis")
        st.plotly_chart(fig, use_container_width=True)
        st.subheader(f"Detailed Rankings: {cat}")
        st.table(top_list)

    with tab_t: # POWER RANKINGS
        st.header("🏘️ TEAM POWER RANKINGS")
        team_power = p_avg.groupby(team_col)['PIE'].sum().reset_index().sort_values('PIE', ascending=False)
        for i, row in team_power.iterrows():
            st.metric(f"Rank {i+1}: {row[team_col]}", f"{round(row['PIE'], 1)} Impact Points")

    with tab_v: # FIX TEAM VS TEAM CRASH
        v_mode = st.radio("Mode", ["Player vs Player", "Team vs Team"], horizontal=True)
        c1, vs_text, c2 = st.columns([2, 0.5, 2])
        if v_mode == "Player vs Player":
            p1_n, p2_n = c1.selectbox("P1", p_avg[name_col].unique(), index=0), c2.selectbox("P2", p_avg[name_col].unique(), index=1)
            d1, d2 = p_avg[p_avg[name_col] == p1_n].iloc[0], p_avg[p_avg[name_col] == p2_n].iloc[0]
            for s in ['PTS/G', 'REB/G', 'AST/G', 'PIE']:
                sc1, sc2 = st.columns(2)
                sc1.metric(f"{p1_n} {s}", d1[s], delta=round(d1[s] - d2[s], 1))
                sc2.metric(f"{p2_n} {s}", d2[s], delta=round(d2[s] - d1[s], 1))
        else:
            t1_n, t2_n = c1.selectbox("T1", t_totals[name_col].unique(), index=0), c2.selectbox("T2", t_totals[name_col].unique(), index=1)
            t1, t2 = t_totals[t_totals[name_col] == t1_n].iloc[0], t_totals[t_totals[name_col] == t2_n].iloc[0]
            for s in ['PTS', 'REB', 'AST']:
                sc1, sc2 = st.columns(2)
                sc1.metric(f"{t1_n} {s}", int(t1[s]), delta=int(t1[s] - t2[s]))
                sc2.metric(f"{t2_n} {s}", int(t2[s]), delta=int(t2[s] - t1[s]))

    with tab_p: st.dataframe(p_avg[[name_col, team_col, 'GP', 'PTS/G', 'REB/G', 'AST/G', 'STL/G', 'BLK/G', 'PIE']].sort_values('PIE', ascending=False), use_container_width=True, hide_index=True)
    with tab_r: # RECORDS
        r_pts, r_reb = df_raw.nlargest(1, 'PTS').iloc[0], df_raw.nlargest(1, 'REB').iloc[0]
        c1, c2 = st.columns(2)
        c1.metric("Scoring Record (Game)", f"{int(r_pts['PTS'])}", r_pts[name_col])
        c2.metric("Rebound Record (Game)", f"{int(r_reb['REB'])}", r_reb[name_col])

    st.markdown('<div style="text-align: center; color: #444; padding: 20px;">© 2026 SPAM LEAGUE HUB | COMMISSIONER DESK</div>', unsafe_allow_html=True)
