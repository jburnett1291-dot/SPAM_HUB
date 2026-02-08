import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path

# 1. INITIAL CONFIG (Must be first)
st.set_page_config(page_title="SPAM LEAGUE CENTRAL", page_icon="🏀", layout="wide")

# 2. DATA ENGINE
SHEET_ID = "1rksLYUcXQJ03uTacfIBD6SRsvtH-IE6djqT-LINwcH4"
URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"

@st.cache_data(ttl=60)
def load_data():
    try:
        df = pd.read_csv(URL)
        df.columns = df.columns.str.strip()
        cols_to_fix = ['PTS', 'REB', 'AST', 'STL', 'BLK', 'FGA', 'FGM', '3PM', 'FTA', 'Game_ID', 'Win']
        for c in cols_to_fix:
            df[c] = pd.to_numeric(df.get(c, 0), errors='coerce').fillna(0)
        
        def calc_multis(row):
            main_stats = [row['PTS'], row['REB'], row['AST'], row['STL'], row['BLK']]
            tens = sum(1 for s in main_stats if s >= 10)
            return pd.Series([1 if tens >= 2 else 0, 1 if tens >= 3 else 0])
        
        df[['DD_Count', 'TD_Count']] = df.apply(calc_multis, axis=1)
        df['PIE'] = (df['PTS'] + df['REB'] + df['AST'] + df['STL'] + df['BLK']) - (df['FGA'] * 0.5)
        df_p = df[df['Type'].str.lower() == 'player'].copy()
        df_t = df[df['Type'].str.lower() == 'team'].copy()

        if df_p.empty: return None, None, None

        gp = df_p.groupby('Player/Team')['Game_ID'].nunique().reset_index(name='GP')
        p_sums = df_p.groupby(['Player/Team', 'Team Name']).sum(numeric_only=True).reset_index()
        p_avg = pd.merge(p_sums, gp, on='Player/Team')
        
        for s in ['PTS', 'REB', 'AST', 'STL', 'BLK']:
            p_avg[f'{s}/G'] = (p_avg[s] / p_avg['GP'].replace(0,1)).round(1)
        
        p_avg['FG%'] = (p_avg['FGM'] / p_avg['FGA'].replace(0,1) * 100).round(1)
        p_avg['TS%'] = (p_avg['PTS'] / (2 * (p_avg['FGA'] + 0.44 * p_avg.get('FTA', 0))).replace(0,1) * 100).round(1)

        t_stats = df_t.groupby('Team Name').agg({
            'Win': 'sum', 'Game_ID': 'count', 'PTS': 'sum', 'REB': 'sum', 
            'AST': 'sum', 'STL': 'sum', 'BLK': 'sum', 'FGA': 'sum', 'FGM': 'sum'
        }).reset_index()
        t_stats['Win'] = t_stats['Win'].astype(int)
        t_stats['Loss'] = (t_stats['Game_ID'] - t_stats['Win']).astype(int)
        t_stats['Record'] = t_stats['Win'].astype(str) + "-" + t_stats['Loss'].astype(str)
        t_stats['FG%'] = (t_stats['FGM'] / t_stats['FGA'].replace(0,1) * 100).round(1)
        for s in ['PTS', 'REB', 'AST', 'STL', 'BLK']:
            t_stats[f'{s}_Avg'] = (t_stats[s] / t_stats['Game_ID'].replace(0,1)).round(1)

        return p_avg, df_p, t_stats
    except:
        return None, None, None

# 3. UI STYLE & SPLASH LOGIC
if 'entered' not in st.session_state:
    st.session_state.entered = False

if not st.session_state.entered:
    # SPLASH SCREEN CSS
    st.markdown("""
        <style>
        .stApp { background: #050505; }
        .splash-outer {
            display: flex;
            align-items: center;
            justify-content: center;
            height: 90vh;
            width: 100%;
        }
        .splash-box {
            text-align: center;
            animation: fadeIn 1.5s ease-in;
        }
        @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
        h1 { font-family: 'Arial Black'; color: #d4af37; font-size: 72px; margin-bottom: 0px; text-shadow: 2px 2px 10px rgba(212, 175, 55, 0.3); }
        p { color: white; letter-spacing: 12px; margin-top: 5px; font-weight: 200; }
        </style>
        <div class="splash-outer">
            <div class="splash-box">
                <h1>SPAM LEAGUE</h1>
                <p>COMMISSIONER TERMINAL</p>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    # Centering the button using columns
    _, btn_col, _ = st.columns([2, 1, 2])
    with btn_col:
        if st.button("PRESS TO ENTER HUB", use_container_width=True):
            st.session_state.entered = True
            st.rerun()
    st.stop()

# 4. MAIN INTERFACE CSS (ONLY LOADS AFTER ENTER)
st.markdown("""
    <style>
    #MainMenu, footer, header {visibility: hidden;}
    .stApp { background: radial-gradient(circle at top, #1f1f1f 0%, #050505 100%); }
    div[data-testid="stMetric"] { background: rgba(255, 255, 255, 0.05) !important; border: 1px solid rgba(212, 175, 55, 0.2) !important; border-radius: 20px !important; }
    .header-banner { padding: 25px; text-align: center; background: linear-gradient(90deg, #d4af37 0%, #f7e08a 50%, #d4af37 100%); color: #000; font-family: 'Arial Black'; font-size: 28px; }
    @keyframes ticker { 0% { transform: translateX(100%); } 100% { transform: translateX(-100%); } }
    .ticker-wrap { width: 100%; overflow: hidden; background: #000; color: #d4af37; padding: 12px 0; border-bottom: 1px solid #333; }
    .ticker-content { display: inline-block; white-space: nowrap; animation: ticker 45s linear infinite; }
    .ticker-item { display: inline-block; margin-right: 100px; font-weight: bold; font-size: 16px; }
    </style>
    """, unsafe_allow_html=True)

p_avg, df_raw, t_stats = load_data()

if p_avg is not None:
    # TICKER
    leads = [f"🔥 {c}: {p_avg.nlargest(1, c+'/G').iloc[0]['Player/Team']} ({p_avg.nlargest(1, c+'/G').iloc[0][c+'/G']})" for c in ['PTS', 'AST', 'REB', 'STL', 'BLK']]
    st.markdown(f'<div class="ticker-wrap"><div class="ticker-content"><span class="ticker-item">{" • ".join(leads)}</span></div></div>', unsafe_allow_html=True)
    st.markdown('<div class="header-banner">🏀 SPAM LEAGUE HUB</div>', unsafe_allow_html=True)

    tabs = st.tabs(["👤 PLAYERS", "🏘️ STANDINGS", "🔝 LEADERS", "⚔️ VERSUS", "📖 RECORDS"])

    with tabs[0]: # PLAYER HUB
        table = p_avg[['Player/Team', 'Team Name', 'GP', 'DD_Count', 'TD_Count', 'PTS/G', 'REB/G', 'AST/G', 'STL/G', 'BLK/G', 'FG%', 'TS%', 'PIE']].sort_values('PIE', ascending=False)
        sel = st.dataframe(table.rename(columns={'STL/G': 'SPG', 'BLK/G': 'BPG', 'DD_Count': 'DD', 'TD_Count': 'TD'}), use_container_width=True, hide_index=True, on_select="rerun", selection_mode="single-row")
        
        if len(sel.selection.rows) > 0:
            row = table.iloc[sel.selection.rows[0]]
            st.markdown(f"### 🔎 Scouting Report: {row['Player/Team']}")
            m_cols = st.columns(5)
            stats = [("PPG", 'PTS/G'), ("RPG", 'REB/G'), ("APG", 'AST/G'), ("SPG", 'STL/G'), ("BPG", 'BLK/G')]
            for i, (label, col) in enumerate(stats): m_cols[i].metric(label, row[col])
            
            e_cols = st.columns(5)
            e_stats = [("FG%", f"{row['FG%']}%"), ("TS%", f"{row['TS%']}%"), ("PIE", row['PIE']), ("DDs", int(row['DD_Count'])), ("TDs", int(row['TD_Count']))]
            for i, (label, val) in enumerate(e_stats): e_cols[i].metric(label, val)
            
            st.line_chart(df_raw[df_raw['Player/Team'] == row['Player/Team']].sort_values('Game_ID').set_index('Game_ID')['PTS'])

    with tabs[1]: # STANDINGS
        st.dataframe(t_stats.sort_values('Win', ascending=False)[['Team Name', 'Record', 'PTS_Avg', 'REB_Avg', 'AST_Avg', 'STL_Avg', 'BLK_Avg', 'FG%']]
                     .rename(columns={'STL_Avg': 'SPG', 'BLK_Avg': 'BPG'}), use_container_width=True, hide_index=True)

    with tabs[2]: # LEADERS
        cat = st.selectbox("Category", ["PTS/G", "REB/G", "AST/G", "STL/G", "BLK/G", "FG%", "TS%", "DD_Count", "TD_Count", "PIE"])
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
            for s in ['PTS/G', 'REB/G', 'AST/G', 'STL/G', 'BLK/G', 'FG%', 'TS%', 'DD_Count', 'TD_Count']:
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
        r1, r2, r3 = st.columns(3)
        def get_rec(col):
            idx = df_raw[col].idxmax()
            return f"{int(df_raw.loc[idx][col])}", df_raw.loc[idx]['Player/Team']
        r1.metric("Points High", *get_rec('PTS')); r1.metric("Steals High", *get_rec('STL')); r1.metric("DD King", int(p_avg['DD_Count'].max()), p_avg.loc[p_avg['DD_Count'].idxmax()]['Player/Team'])
        r2.metric("Rebounds High", *get_rec('REB')); r2.metric("Blocks High", *get_rec('BLK')); r2.metric("TD King", int(p_avg['TD_Count'].max()), p_avg.loc[p_avg['TD_Count'].idxmax()]['Player/Team'])
        r3.metric("Assists High", *get_rec('AST')); r3.metric("3PM High", *get_rec('3PM')); r3.metric("FGA High", *get_rec('FGA'))

    st.markdown('<div style="text-align: center; color: #444; padding: 30px;">— SPAM LEAGUE HUB 2026 —</div>', unsafe_allow_html=True)
