import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path

# 1. UI & SLEEK CSS
st.set_page_config(page_title="SPAM LEAGUE CENTRAL", page_icon="🏀", layout="wide")

st.markdown("""
    <style>
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    div[data-testid="stToolbar"] {visibility: hidden;} [data-testid="stStatusWidget"] {display: none;}
    .block-container { padding: 0rem !important; margin: 0rem !important; }
    
    .stApp { 
        background: radial-gradient(circle at top, #1f1f1f 0%, #050505 100%); 
        color: #e0e0e0; 
        font-family: 'Inter', sans-serif;
    }

    div[data-testid="stMetric"] { 
        background: rgba(255, 255, 255, 0.05) !important; 
        backdrop-filter: blur(10px);
        border: 1px solid rgba(212, 175, 55, 0.2) !important; 
        border-radius: 20px !important; 
        padding: 20px !important;
        transition: transform 0.3s ease;
    }
    div[data-testid="stMetric"]:hover {
        transform: translateY(-5px);
        border-color: #d4af37 !important;
    }

    .stTabs [data-baseweb="tab-list"] { gap: 10px; background-color: transparent; }
    .stTabs [data-baseweb="tab"] {
        height: 50px; background-color: rgba(255, 255, 255, 0.03);
        border-radius: 12px 12px 0px 0px; color: #888; border: none; transition: all 0.3s;
    }
    .stTabs [aria-selected="true"] {
        background-color: rgba(212, 175, 55, 0.1) !important;
        color: #d4af37 !important;
        border-bottom: 3px solid #d4af37 !important;
    }

    .header-banner { 
        padding: 25px; text-align: center; 
        background: linear-gradient(90deg, #d4af37 0%, #f7e08a 50%, #d4af37 100%);
        color: #000; font-family: 'Arial Black'; font-size: 28px;
        letter-spacing: 2px; box-shadow: 0 4px 15px rgba(0,0,0,0.5);
    }

    @keyframes ticker { 0% { transform: translateX(100%); } 100% { transform: translateX(-100%); } }
    .ticker-wrap { width: 100%; overflow: hidden; background: #000; color: #d4af37; padding: 12px 0; border-bottom: 1px solid #333; }
    .ticker-content { display: inline-block; white-space: nowrap; animation: ticker 45s linear infinite; }
    .ticker-item { display: inline-block; margin-right: 100px; font-weight: bold; font-size: 16px; }
    </style>
    """, unsafe_allow_html=True)

# 2. DATA ENGINE
SHEET_ID = "1rksLYUcXQJ03uTacfIBD6SRsvtH-IE6djqT-LINwcH4"
URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"

@st.cache_data(ttl=60)
def load_data():
    try:
        df = pd.read_csv(URL)
        df.columns = df.columns.str.strip()
        core_cols = ['PTS', 'REB', 'AST', 'STL', 'BLK', 'FGA', 'FGM', 'FTA', 'Game_ID', 'Win']
        for c in core_cols:
            df[c] = pd.to_numeric(df.get(c, 0), errors='coerce').fillna(0)
        
        df['PIE'] = (df['PTS'] + df['REB'] + df['AST'] + df['STL'] + df['BLK']) - (df['FGA'] * 0.5)
        df_p = df[df['Type'].str.lower() == 'player'].copy()
        df_t = df[df['Type'].str.lower() == 'team'].copy()

        # Player Calcs
        gp = df_p.groupby('Player/Team')['Game_ID'].nunique().reset_index(name='GP')
        p_sums = df_p.groupby(['Player/Team', 'Team Name']).sum(numeric_only=True).reset_index()
        p_avg = pd.merge(p_sums, gp, on='Player/Team')
        
        for s in ['PTS', 'REB', 'AST', 'STL', 'BLK']:
            p_avg[f'{s}/G'] = (p_avg[s] / p_avg['GP']).round(1)
        
        p_avg['FG%'] = (p_avg['FGM'] / p_avg['FGA'].replace(0,1) * 100).round(1)
        p_avg['TS%'] = (p_avg['PTS'] / (2 * (p_avg['FGA'] + 0.44 * p_avg.get('FTA', 0))).replace(0,1) * 100).round(1)

        # Team Calcs
        t_stats = df_t.groupby('Team Name').agg({
            'Win': 'sum', 'Game_ID': 'count', 'PTS': 'sum', 'REB': 'sum', 
            'AST': 'sum', 'STL': 'sum', 'BLK': 'sum', 'FGA': 'sum', 'FGM': 'sum'
        }).reset_index()
        t_stats['Loss'] = t_stats['Game_ID'] - t_stats['Win']
        t_stats['Record'] = t_stats['Win'].astype(str) + "-" + t_stats['Loss'].astype(str)
        t_stats['FG%'] = (t_stats['FGM'] / t_stats['FGA'].replace(0,1) * 100).round(1)
        
        for s in ['PTS', 'REB', 'AST', 'STL', 'BLK']:
            t_stats[f'{s}_Avg'] = (t_stats[s] / t_stats['Game_ID']).round(1)

        return p_avg, df_p, t_stats
    except:
        return None, None, None

p_avg, df_raw, t_stats = load_data()

# 3. SPLASH SCREEN
if 'entered' not in st.session_state: st.session_state.entered = False
if not st.session_state.entered:
    st.markdown('<div style="display: flex; flex-direction: column; align-items: center; justify-content: center; height: 95vh; width: 100%;">', unsafe_allow_html=True)
    st.markdown("<h1 style='font-size: 80px; color: #d4af37; margin: 0;'>SPAM LEAGUE</h1>", unsafe_allow_html=True)
    if st.button("ENTER HUB"):
        st.session_state.entered = True
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# 4. MAIN HUB
if p_avg is not None:
    leads = [f"🔥 {c}: {p_avg.nlargest(1, c+'/G').iloc[0]['Player/Team']} ({p_avg.nlargest(1, c+'/G').iloc[0][c+'/G']})" for c in ['PTS', 'AST', 'REB', 'STL', 'BLK']]
    st.markdown(f'<div class="ticker-wrap"><div class="ticker-content"><span class="ticker-item">{" • ".join(leads)}</span></div></div>', unsafe_allow_html=True)
    st.markdown('<div class="header-banner">🏀 SPAM LEAGUE CENTRAL</div>', unsafe_allow_html=True)

    tabs = st.tabs(["👤 PLAYERS", "🏘️ STANDINGS", "🔝 LEADERS", "⚔️ VERSUS", "📖 RECORDS"])

    with tabs[0]: # PLAYER HUB
        table = p_avg[['Player/Team', 'Team Name', 'GP', 'PTS/G', 'REB/G', 'AST/G', 'STL/G', 'BLK/G', 'FG%', 'TS%', 'PIE']].sort_values('PIE', ascending=False)
        sel = st.dataframe(table.rename(columns={'STL/G': 'SPG', 'BLK/G': 'BPG'}), use_container_width=True, hide_index=True, on_select="rerun", selection_mode="single-row")
        
        if len(sel.selection.rows) > 0:
            row_data = table.iloc[sel.selection.rows[0]]
            name = row_data['Player/Team']
            hist = df_raw[df_raw['Player/Team'] == name].sort_values('Game_ID')
            
            st.markdown(f"### 🔎 Detailed Scouting: {name}")
            
            # Row 1: Traditional Stats
            m1, m2, m3, m4, m5 = st.columns(5)
            m1.metric("PPG", row_data['PTS/G'])
            m2.metric("RPG", row_data['REB/G'])
            m3.metric("APG", row_data['AST/G'])
            m4.metric("SPG", row_data['STL/G'])
            m5.metric("BPG", row_data['BLK/G'])
            
            # Row 2: Efficiency Stats
            e1, e2, e3, e4 = st.columns(4)
            e1.metric("FG%", f"{row_data['FG%']}%")
            e2.metric("TS%", f"{row_data['TS%']}%")
            e3.metric("PIE (Impact)", row_data['PIE'])
            e4.metric("Games Played", int(row_data['GP']))

            st.line_chart(hist.set_index('Game_ID')['PTS'])

    with tabs[1]: # STANDINGS (FIXED KEYERROR)
        st.markdown("### League Standings")
        # Ensure we sort by Win while it's still in the dataframe
        standings_df = t_stats.sort_values('Win', ascending=False)
        # Then display only relevant columns
        display_standings = standings_df[['Team Name', 'Record', 'PTS_Avg', 'STL_Avg', 'BLK_Avg', 'FG%']]
        st.dataframe(display_standings.rename(columns={'STL_Avg': 'SPG', 'BLK_Avg': 'BPG'}), use_container_width=True, hide_index=True)

    with tabs[2]: # LEADERS
        cat = st.selectbox("Category", ["PTS/G", "REB/G", "AST/G", "STL/G", "BLK/G", "FG%", "TS%", "PIE"])
        t10 = p_avg.nlargest(10, cat)[['Player/Team', cat]]
        st.plotly_chart(px.bar(t10, x=cat, y='Player/Team', orientation='h', template="plotly_dark", color_discrete_sequence=['#d4af37']), use_container_width=True)

    with tabs[3]: # VERSUS
        v1, v2 = st.columns(2)
        p1 = v1.selectbox("Player 1", p_avg['Player/Team'].unique())
        p2 = v2.selectbox("Player 2", p_avg['Player/Team'].unique(), index=1)
        d1 = p_avg[p_avg['Player/Team']==p1].iloc[0]
        d2 = p_avg[p_avg['Player/Team']==p2].iloc[0]
        
        for s in ['PTS/G', 'REB/G', 'AST/G', 'STL/G', 'BLK/G', 'FG%', 'TS%', 'PIE']:
            c1, c2 = st.columns(2)
            c1.metric(f"{p1} {s}", d1[s], delta=round(d1[s]-d2[s], 1))
            c2.metric(f"{p2} {s}", d2[s], delta=round(d2[s]-d1[s], 1))

    with tabs[4]: # RECORDS
        c1, c2 = st.columns(2)
        c1.metric("All-Time Scoring", f"{int(df_raw['PTS'].max())} PTS", df_raw.loc[df_raw['PTS'].idxmax()]['Player/Team'])
        c2.metric("Defensive Master", f"{int(df_raw['BLK'].max())} BLK", df_raw.loc[df_raw['BLK'].idxmax()]['Player/Team'])

    st.markdown('<div style="text-align: center; color: #444; padding: 30px;">— SPAM LEAGUE DATA TERMINAL 2026 —</div>', unsafe_allow_html=True)
