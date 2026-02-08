import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path

# 1. PERMANENT CONFIG
st.set_page_config(page_title="SPAM LEAGUE HUB", page_icon="🏀", layout="wide")

# 2. DATA ENGINE
SHEET_ID = "1rksLYUcXQJ03uTacfIBD6SRsvtH-IE6djqT-LINwcH4"
URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"

@st.cache_data(ttl=30)
def load_data():
    try:
        df = pd.read_csv(URL)
        df.columns = df.columns.str.strip()
        # Numeric cleanup
        cols = ['PTS', 'REB', 'AST', 'STL', 'BLK', 'FGA', 'FGM', '3PM', 'FTA', 'Game_ID', 'Win']
        for c in cols:
            df[c] = pd.to_numeric(df.get(c, 0), errors='coerce').fillna(0)
        
        # Double-Double & Triple-Double Logic
        def calc_multis(row):
            main_stats = [row['PTS'], row['REB'], row['AST'], row['STL'], row['BLK']]
            tens = sum(1 for s in main_stats if s >= 10)
            return pd.Series([1 if tens >= 2 else 0, 1 if tens >= 3 else 0])
        
        df[['DD', 'TD']] = df.apply(calc_multis, axis=1)
        df['PIE'] = (df['PTS'] + df['REB'] + df['AST'] + df['STL'] + df['BLK']) - (df['FGA'] * 0.5)
        
        df_p = df[df['Type'].str.lower() == 'player'].copy()
        df_t = df[df['Type'].str.lower() == 'team'].copy()

        # Player Averages
        gp = df_p.groupby('Player/Team')['Game_ID'].nunique().reset_index(name='GP')
        p_sums = df_p.groupby(['Player/Team', 'Team Name']).sum(numeric_only=True).reset_index()
        p_avg = pd.merge(p_sums, gp, on='Player/Team')
        
        for s in ['PTS', 'REB', 'AST', 'STL', 'BLK']:
            p_avg[f'{s}/G'] = (p_avg[s] / p_avg['GP'].replace(0,1)).round(1)
        
        p_avg['FG%'] = (p_avg['FGM'] / p_avg['FGA'].replace(0,1) * 100).round(1)
        p_avg['TS%'] = (p_avg['PTS'] / (2 * (p_avg['FGA'] + 0.44 * p_avg.get('FTA', 0))).replace(0,1) * 100).round(1)

        # Team Averages
        t_stats = df_t.groupby('Team Name').agg({
            'Win': 'sum', 'Game_ID': 'count', 'PTS': 'sum', 'REB': 'sum', 
            'AST': 'sum', 'STL': 'sum', 'BLK': 'sum', 'FGA': 'sum', 'FGM': 'sum'
        }).reset_index()
        t_stats['Loss'] = (t_stats['Game_ID'] - t_stats['Win']).astype(int)
        t_stats['Record'] = t_stats['Win'].astype(int).astype(str) + "-" + t_stats['Loss'].astype(str)
        t_stats['FG%'] = (t_stats['FGM'] / t_stats['FGA'].replace(0,1) * 100).round(1)
        for s in ['PTS', 'REB', 'AST', 'STL', 'BLK']:
            t_stats[f'{s}_Avg'] = (t_stats[s] / t_stats['Game_ID'].replace(0,1)).round(1)

        return p_avg, df, t_stats
    except Exception as e:
        return None, str(e), None

# 3. SESSION STATE TRANSITION
if 'entered' not in st.session_state:
    st.session_state.entered = False

# 4. SPLASH SCREEN (UI ONLY)
if not st.session_state.entered:
    st.markdown("""
        <style>
        .stApp { background: #050505; }
        .splash-outer {
            display: flex; flex-direction: column; align-items: center; justify-content: center;
            height: 80vh; width: 100%; text-align: center;
        }
        h1 { color: #d4af37; font-size: 80px; font-family: 'Arial Black'; margin-bottom: 0; }
        p { color: white; letter-spacing: 10px; font-size: 14px; margin-top: 0; opacity: 0.8; }
        </style>
        <div class="splash-outer">
            <h1>SPAM LEAGUE</h1>
            <p>COMMISSIONER HUB 2026</p>
        </div>
    """, unsafe_allow_html=True)
    
    _, col, _ = st.columns([2, 1, 2])
    if col.button("ENTER HUB", use_container_width=True):
        st.session_state.entered = True
        st.rerun()
    st.stop()

# 5. HUB INTERFACE (LOADS ONLY AFTER ENTRY)
st.markdown("""
    <style>
    #MainMenu, footer, header {visibility: hidden;}
    .stApp { background: radial-gradient(circle at top, #1a1a1a 0%, #050505 100%); }
    div[data-testid="stMetric"] { background: rgba(255, 255, 255, 0.05) !important; border-radius: 15px !important; border: 1px solid rgba(212, 175, 55, 0.1) !important; }
    .header-banner { padding: 20px; text-align: center; background: #d4af37; color: black; font-family: 'Arial Black'; font-size: 24px; border-radius: 0 0 20px 20px; }
    .ticker-wrap { background: black; color: #d4af37; padding: 10px; border-bottom: 1px solid #d4af37; font-weight: bold; overflow: hidden; white-space: nowrap; }
    </style>
    """, unsafe_allow_html=True)

p_avg, df_raw, t_stats = load_data()

if p_avg is not None and not isinstance(df_raw, str):
    # TICKER
    leads = [f"{c}: {p_avg.nlargest(1, c+'/G').iloc[0]['Player/Team']} ({p_avg.nlargest(1, c+'/G').iloc[0][c+'/G']})" for c in ['PTS', 'AST', 'REB', 'STL', 'BLK']]
    st.markdown(f'<div class="ticker-wrap">🔥 {" • ".join(leads)}</div>', unsafe_allow_html=True)
    st.markdown('<div class="header-banner">🏀 SPAM LEAGUE CENTRAL</div>', unsafe_allow_html=True)

    tabs = st.tabs(["👤 PLAYERS", "🏘️ STANDINGS", "🔝 LEADERS", "⚔️ VERSUS", "📖 RECORDS"])

    with tabs[0]: # PLAYER HUB
        table = p_avg[['Player/Team', 'Team Name', 'GP', 'DD', 'TD', 'PTS/G', 'REB/G', 'AST/G', 'STL/G', 'BLK/G', 'FG%', 'TS%', 'PIE']].sort_values('PIE', ascending=False)
        sel = st.dataframe(table.rename(columns={'STL/G': 'SPG', 'BLK/G': 'BPG'}), use_container_width=True, hide_index=True, on_select="rerun", selection_mode="single-row")
        
        if len(sel.selection.rows) > 0:
            row = table.iloc[sel.selection.rows[0]]
            st.markdown(f"### 🔎 {row['Player/Team']} | {row['Team Name']}")
            m1, m2, m3, m4, m5 = st.columns(5)
            m1.metric("PPG", row['PTS/G']); m2.metric("RPG", row['REB/G']); m3.metric("APG", row['AST/G']); m4.metric("SPG", row['STL/G']); m5.metric("BPG", row['BLK/G'])
            e1, e2, e3, e4, e5 = st.columns(5)
            e1.metric("FG%", f"{row['FG%']}%"); e2.metric("TS%", f"{row['TS%']}%"); e3.metric("PIE", row['PIE']); e4.metric("DDs", int(row['DD'])); e5.metric("TDs", int(row['TD']))
            
            # Game Log Graph
            hist = df_raw[(df_raw['Player/Team'] == row['Player/Team']) & (df_raw['Type'].str.lower() == 'player')].sort_values('Game_ID')
            st.line_chart(hist.set_index('Game_ID')['PTS'])

    with tabs[1]: # STANDINGS
        st.dataframe(t_stats.sort_values('Win', ascending=False)[['Team Name', 'Record', 'PTS_Avg', 'REB_Avg', 'AST_Avg', 'STL_Avg', 'BLK_Avg', 'FG%']]
                     .rename(columns={'STL_Avg': 'SPG', 'BLK_Avg': 'BPG'}), use_container_width=True, hide_index=True)

    with tabs[2]: # LEADERS
        cat = st.selectbox("Category", ["PTS/G", "REB/G", "AST/G", "STL/G", "BLK/G", "FG%", "TS%", "DD", "TD", "PIE"])
        t10 = p_avg.nlargest(10, cat)[['Player/Team', 'Team Name', cat]].reset_index(drop=True)
        t10.index += 1
        st.table(t10)
        st.plotly_chart(px.bar(t10, x=cat, y='Player/Team', orientation='h', template="plotly_dark", color_discrete_sequence=['#d4af37']), use_container_width=True)

    with tabs[3]: # VERSUS
        v_mode = st.radio("Mode", ["Player vs Player", "Team vs Team"], horizontal=True)
        v1, v2 = st.columns(2)
        if v_mode == "Player vs Player":
            p1 = v1.selectbox("P1", p_avg['Player/Team'].unique(), index=0)
            p2 = v2.selectbox("P2", p_avg['Player/Team'].unique(), index=1)
            d1, d2 = p_avg[p_avg['Player/Team']==p1].iloc[0], p_avg[p_avg['Player/Team']==p2].iloc[0]
            for s in ['PTS/G', 'REB/G', 'AST/G', 'STL/G', 'BLK/G', 'FG%', 'TS%', 'DD', 'TD']:
                sc1, sc2 = st.columns(2)
                sc1.metric(f"{p1} {s}", d1[s], delta=round(d1[s]-d2[s], 1))
                sc2.metric(f"{p2} {s}", d2[s], delta=round(d2[s]-d1[s], 1))
        else:
            t1 = v1.selectbox("T1", t_stats['Team Name'].unique(), index=0)
            t2 = v2.selectbox("T2", t_stats['Team Name'].unique(), index=1)
            td1, td2 = t_stats[t_stats['Team Name']==t1].iloc[0], t_stats[t_stats['Team Name']==t2].iloc[0]
            for s in ['PTS_Avg', 'REB_Avg', 'AST_Avg', 'STL_Avg', 'BLK_Avg', 'FG%']:
                sc1, sc2 = st.columns(2)
                sc1.metric(f"{t1} {s}", td1[s], delta=round(td1[s]-td2[s], 1))
                sc2.metric(f"{t2} {s}", td2[s], delta=round(td2[s]-td1[s], 1))

    with tabs[4]: # RECORDS
        st.markdown("### 🏆 Single Game Highs")
        players_only = df_raw[df_raw['Type'].str.lower() == 'player']
        r1, r2, r3 = st.columns(3)
        def get_rec(col):
            idx = players_only[col].idxmax()
            return f"{int(players_only.loc[idx][col])}", players_only.loc[idx]['Player/Team']
        
        r1.metric("Points", *get_rec('PTS')); r1.metric("Steals", *get_rec('STL')); r1.metric("DD Total", int(p_avg['DD'].max()), p_avg.loc[p_avg['DD'].idxmax()]['Player/Team'])
        r2.metric("Rebounds", *get_rec('REB')); r2.metric("Blocks", *get_rec('BLK')); r2.metric("TD Total", int(p_avg['TD'].max()), p_avg.loc[p_avg['TD'].idxmax()]['Player/Team'])
        r3.metric("Assists", *get_rec('AST')); r3.metric("3PM", *get_rec('3PM')); r3.metric("FGA High", *get_rec('FGA'))

else:
    st.error("DATABASE OFFLINE: Please check Google Sheet permissions or CSV format.")
    if st.button("RETRY CONNECTION"): st.rerun()
