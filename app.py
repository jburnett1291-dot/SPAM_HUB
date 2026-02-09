import streamlit as st
import pandas as pd
import plotly.express as px

# 1. UI & SLEEK CSS
st.set_page_config(page_title="SPAM LEAGUE CENTRAL", page_icon="🏀", layout="wide")

st.markdown("""
    <style>
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    div[data-testid="stToolbar"] {visibility: hidden;} [data-testid="stStatusWidget"] {display: none;}
    .block-container { padding: 0rem !important; margin: 0rem !important; }
    .stApp { background: radial-gradient(circle at top, #1f1f1f 0%, #050505 100%); color: #e0e0e0; }
    
    div[data-testid="stMetric"] { 
        background: rgba(255, 255, 255, 0.05) !important; 
        backdrop-filter: blur(10px);
        border: 1px solid rgba(212, 175, 55, 0.2) !important; 
        border-radius: 20px !important; 
        padding: 20px !important;
    }
    .header-banner { 
        padding: 25px; text-align: center; 
        background: linear-gradient(90deg, #d4af37 0%, #f7e08a 50%, #d4af37 100%);
        color: #000; font-family: 'Arial Black'; font-size: 28px;
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
        if 'Season' not in df.columns: df['Season'] = 1
        if '3PM' not in df.columns: df['3PM'] = 0
            
        cols_to_fix = ['PTS', 'REB', 'AST', 'STL', 'BLK', 'FGA', 'FGM', '3PM', 'FTA', 'Game_ID', 'Win', 'Season']
        for c in cols_to_fix:
            df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)
        
        def calc_multis(row):
            main_stats = [row['PTS'], row['REB'], row['AST'], row['STL'], row['BLK']]
            tens = sum(1 for s in main_stats if s >= 10)
            return pd.Series([1 if tens >= 2 else 0, 1 if tens >= 3 else 0])
        
        df[['DD_Count', 'TD_Count']] = df.apply(calc_multis, axis=1)
        df['PIE'] = (df['PTS'] + df['REB'] + df['AST'] + df['STL'] + df['BLK']) - (df['FGA'] * 0.5)
        return df
    except Exception as e:
        return str(e)

full_df = load_data()

if isinstance(full_df, str):
    st.error(f"⚠️ DATA ERROR: {full_df}")
else:
    # 3. SEASON FILTER (LIFETIME OPTION)
    seasons_list = sorted(full_df['Season'].unique(), reverse=True)
    options = ["LIFETIME (ALL SEASONS)"] + [f"Season {int(s)}" for s in seasons_list]
    
    with st.sidebar:
        st.markdown("### 🗓️ ARCHIVES")
        sel_box = st.selectbox("View Scope", options, index=1) # Defaults to most recent season
        st.divider()
        st.caption("Lifetime view aggregates all stats.")

    # Apply Filtering
    if sel_box == "LIFETIME (ALL SEASONS)":
        df_active = full_df.copy()
        display_label = "LIFETIME TOTALS"
    else:
        s_num = int(sel_box.replace("Season ", ""))
        df_active = full_df[full_df['Season'] == s_num]
        display_label = f"SEASON {s_num}"

    df_p_raw = df_active[df_active['Type'].str.lower() == 'player'].copy()
    df_t_raw = df_active[df_active['Type'].str.lower() == 'team'].copy()

    # Player Averages
    gp = df_p_raw.groupby('Player/Team')['Game_ID'].nunique().reset_index(name='GP')
    p_sums = df_p_raw.groupby(['Player/Team', 'Team Name']).sum(numeric_only=True).reset_index()
    p_avg = pd.merge(p_sums, gp, on='Player/Team')
    
    for s in ['PTS', 'REB', 'AST', 'STL', 'BLK']:
        p_avg[f'{s}/G'] = (p_avg[s] / p_avg['GP'].replace(0,1)).round(1)
    p_avg['FG%'] = (p_avg['FGM'] / p_avg['FGA'].replace(0,1) * 100).round(1)
    p_avg['TS%'] = (p_avg['PTS'] / (2 * (p_avg['FGA'] + 0.44 * p_avg.get('FTA', 0))).replace(0,1) * 100).round(1)

    # Team Standings
    t_stats = df_t_raw.groupby('Team Name').agg({
        'Win': 'sum', 'Game_ID': 'count', 'PTS': 'sum', 'REB': 'sum', 
        'AST': 'sum', 'STL': 'sum', 'BLK': 'sum', 'FGA': 'sum', 'FGM': 'sum'
    }).reset_index()
    t_stats['Win'] = t_stats['Win'].astype(int)
    t_stats['Loss'] = (t_stats['Game_ID'] - t_stats['Win']).astype(int)
    t_stats['Record'] = t_stats['Win'].astype(str) + "-" + t_stats['Loss'].astype(str)
    t_stats['FG%'] = (t_stats['FGM'] / t_stats['FGA'].replace(0,1) * 100).round(1)
    for s in ['PTS', 'REB', 'AST', 'STL', 'BLK']:
        t_stats[f'{s}_Avg'] = (t_stats[s] / t_stats['Game_ID'].replace(0,1)).round(1)

    # 4. UI RENDERING
    leads = [f"🔥 {c}: {p_avg.nlargest(1, c+'/G').iloc[0]['Player/Team']} ({p_avg.nlargest(1, c+'/G').iloc[0][c+'/G']})" for c in ['PTS', 'AST', 'REB', 'STL', 'BLK'] if not p_avg.empty]
    st.markdown(f'<div class="ticker-wrap"><div class="ticker-content"><span class="ticker-item">{" • ".join(leads)}</span></div></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="header-banner">🏀 SPAM LEAGUE CENTRAL - {display_label}</div>', unsafe_allow_html=True)

    tabs = st.tabs(["👤 PLAYERS", "🏘️ STANDINGS & FORM", "🔝 LEADERS", "⚔️ VERSUS", "📖 ALL-TIME RECORDS"])

    with tabs[0]: # PLAYER HUB
        table = p_avg[['Player/Team', 'Team Name', 'GP', 'DD_Count', 'TD_Count', 'PTS/G', 'REB/G', 'AST/G', 'STL/G', 'BLK/G', 'FG%', 'TS%', 'PIE']].sort_values('PIE', ascending=False)
        sel = st.dataframe(table.rename(columns={'STL/G': 'SPG', 'BLK/G': 'BPG', 'DD_Count': 'DD', 'TD_Count': 'TD'}), width="stretch", hide_index=True, on_select="rerun", selection_mode="single-row")
        
        if len(sel.selection.rows) > 0:
            row = table.iloc[sel.selection.rows[0]]
            st.markdown(f"### 🔎 Scouting: {row['Player/Team']}")
            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric("PPG", row['PTS/G']); c2.metric("RPG", row['REB/G']); c3.metric("APG", row['AST/G'])
            c4.metric("SPG", row['STL/G']); c5.metric("BPG", row['BLK/G'])
            hist = df_p_raw[df_p_raw['Player/Team'] == row['Player/Team']].sort_values('Game_ID')
            st.line_chart(hist.set_index('Game_ID')['PTS'])

    with tabs[1]: # STANDINGS & FORM
        st.markdown("### Team Power Rankings")
        st.dataframe(t_stats.sort_values('Win', ascending=False)[['Team Name', 'Record', 'PTS_Avg', 'REB_Avg', 'AST_Avg', 'STL_Avg', 'BLK_Avg', 'FG%']]
                     .rename(columns={'STL_Avg': 'SPG', 'BLK_Avg': 'BPG'}), width="stretch", hide_index=True)
        
        st.divider()
        st.markdown("### 🕒 Recent Team Form (Last 3 Games)")
        form_cols = st.columns(len(t_stats['Team Name'].unique()))
        for i, team in enumerate(t_stats['Team Name'].unique()):
            with form_cols[i % len(form_cols)]:
                st.write(f"**{team}**")
                recent = df_t_raw[df_t_raw['Team Name'] == team].sort_values('Game_ID', ascending=False).head(3)
                for _, game in recent.iterrows():
                    res = "✅ W" if game['Win'] == 1 else "❌ L"
                    st.caption(f"Game {int(game['Game_ID'])}: {res} ({int(game['PTS'])} pts)")

    with tabs[2]: # LEADERS
        cat = st.selectbox("Category", ["PTS/G", "REB/G", "AST/G", "STL/G", "BLK/G", "FG%", "TS%", "PIE"])
        t10 = p_avg.nlargest(10, cat)[['Player/Team', 'Team Name', cat]].reset_index(drop=True)
        t10.index += 1
        st.table(t10)

    with tabs[3]: # VERSUS
        v1, v2 = st.columns(2)
        p1 = v1.selectbox("P1", p_avg['Player/Team'].unique(), index=0)
        p2 = v2.selectbox("P2", p_avg['Player/Team'].unique(), index=1)
        if not p_avg.empty:
            d1, d2 = p_avg[p_avg['Player/Team']==p1].iloc[0], p_avg[p_avg['Player/Team']==p2].iloc[0]
            for s in ['PTS/G', 'REB/G', 'AST/G', 'PIE']:
                sc1, sc2 = st.columns(2)
                sc1.metric(f"{p1} {s}", d1[s], delta=round(d1[s]-d2[s], 1))
                sc2.metric(f"{p2} {s}", d2[s], delta=round(d2[s]-d1[s], 1))

    with tabs[4]: # ALL-TIME RECORDS
        st.markdown("### 🏆 League Hall of Fame")
        r1, r2, r3 = st.columns(3)
        def get_all_time(col):
            player_rows = full_df[full_df['Type'].str.lower() == 'player']
            if player_rows.empty: return "0", "N/A"
            idx = player_rows[col].idxmax()
            rec = player_rows.loc[idx]
            return f"{int(rec[col])}", f"{rec['Player/Team']} (S{int(rec['Season'])})"
        
        r1.metric("Most Points", *get_all_time('PTS'))
        r2.metric("Most Rebounds", *get_all_time('REB'))
        r3.metric("Most Assists", *get_all_time('AST'))
        r1.metric("Most Steals", *get_all_time('STL'))
        r2.metric("Most Blocks", *get_all_time('BLK'))
        r3.metric("Most 3PM", *get_all_time('3PM'))

    st.markdown(f'<div style="text-align: center; color: #444; padding: 30px;">© 2026 SPAM LEAGUE HUB</div>', unsafe_allow_html=True)
