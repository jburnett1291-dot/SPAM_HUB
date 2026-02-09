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
        
        # Core Stats Mapping
        cols = ['PTS', 'REB', 'AST', 'STL', 'BLK', 'FGA', 'FGM', '3PM', '3PA', 'FTA', 'Game_ID', 'Win', 'Season']
        for c in cols:
            if c not in df.columns: df[c] = 0
            df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)
        
        # 2-Pointer Logic
        df['2PM'] = df['FGM'] - df['3PM']
        df['2PA'] = df['FGA'] - df['3PA']
        
        # Efficiency Metrics
        def calc_multis(row):
            stats = [row['PTS'], row['REB'], row['AST'], row['STL'], row['BLK']]
            tens = sum(1 for s in stats if s >= 10)
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
    # 3. FILTERS
    seasons_list = sorted(full_df['Season'].unique(), reverse=True)
    options = ["CAREER STATS (ALL SEASONS)"] + [f"Season {int(s)}" for s in seasons_list]
    with st.sidebar:
        sel_box = st.selectbox("League Scope", options, index=1)

    if sel_box == "CAREER STATS (ALL SEASONS)":
        df_active = full_df.copy()
        display_label = "CAREER"
    else:
        s_num = int(sel_box.replace("Season ", ""))
        df_active = full_df[full_df['Season'] == s_num]
        display_label = f"SEASON {s_num}"

    # STAT PROCESSING
    def aggregate_stats(dataframe, group_col):
        gp = dataframe.groupby(group_col)['Game_ID'].nunique().reset_index(name='GP')
        sums = dataframe.groupby(group_col).sum(numeric_only=True).reset_index()
        merged = pd.merge(sums, gp, on=group_col)
        
        pg_cols = ['PTS', 'REB', 'AST', 'STL', 'BLK', '3PM', '3PA', '2PM', '2PA', 'FGM', 'FGA', 'Win']
        for s in pg_cols:
            merged[f'{s}/G'] = (merged[s] / merged['GP'].replace(0,1)).round(1)
        
        merged['FG%'] = (merged['FGM'] / merged['FGA'].replace(0,1) * 100).round(1).fillna(0)
        merged['3P%'] = (merged['3PM'] / merged['3PA'].replace(0,1) * 100).round(1).fillna(0)
        merged['2P%'] = (merged['2PM'] / merged['2PA'].replace(0,1) * 100).round(1).fillna(0)
        return merged

    p_data = aggregate_stats(df_active[df_active['Type'].str.lower() == 'player'], 'Player/Team')
    team_map = df_active[df_active['Type'].str.lower() == 'player'].groupby('Player/Team')['Team Name'].last().reset_index()
    p_data = pd.merge(p_data, team_map, on='Player/Team')

    t_raw = df_active[df_active['Type'].str.lower() == 'team']
    t_stats = aggregate_stats(t_raw, 'Team Name')
    # Use standard column for wins calculation
    t_wins = t_raw.groupby('Team Name')['Win'].sum().reset_index().rename(columns={'Win': 'Total_Wins'})
    t_stats = pd.merge(t_stats, t_wins, on='Team Name')
    t_stats['Loss'] = (t_stats['GP'] - t_stats['Total_Wins']).astype(int)
    t_stats['Record'] = t_stats['Total_Wins'].astype(str) + "-" + t_stats['Loss'].astype(str)

    # 4. UI
    leads = [f"🔥 {c}: {p_data.nlargest(1, c+'/G').iloc[0]['Player/Team']} ({p_data.nlargest(1, c+'/G').iloc[0][c+'/G']})" for c in ['PTS', 'AST', 'REB', 'STL', 'BLK'] if not p_data.empty]
    st.markdown(f'<div class="ticker-wrap"><div class="ticker-content"><span class="ticker-item">{" • ".join(leads)}</span></div></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="header-banner">🏀 SPAM HUB - {display_label}</div>', unsafe_allow_html=True)

    tabs = st.tabs(["👤 PLAYERS", "🏘️ STANDINGS", "🔝 LEADERS", "⚔️ VERSUS", "📖 HALL OF FAME"])

    with tabs[0]: # PLAYER HUB
        display_p = p_data[['Player/Team', 'Team Name', 'GP', 'PTS/G', 'REB/G', 'AST/G', 'FG%', 'PIE']].sort_values('PIE', ascending=False)
        sel_p = st.dataframe(display_p, width="stretch", hide_index=True, on_select="rerun", selection_mode="single-row")
        
        if len(sel_p.selection.rows) > 0:
            p_name = display_p.iloc[sel_p.selection.rows[0]]['Player/Team']
            row = p_data[p_data['Player/Team'] == p_name].iloc[0]
            st.markdown(f"### 🔎 Scouting: {p_name}")
            c = st.columns(5)
            c[0].metric("PPG", row['PTS/G']); c[1].metric("RPG", row['REB/G']); c[2].metric("APG", row['AST/G']); c[3].metric("SPG", row['STL/G']); c[4].metric("BPG", row['BLK/G'])
            
            st.markdown("#### 🎯 Efficiency & Form")
            s = st.columns(4)
            s[0].metric("FG%", f"{row['FG%']}%", f"{row['FGM/G']}/{row['FGA/G']}")
            s[1].metric("3P%", f"{row['3P%']}%", f"{row['3PM/G']}/{row['3PA/G']}")
            s[2].metric("2P%", f"{row['2P%']}%", f"{row['2PM/G']}/{row['2PA/G']}")
            s[3].metric("PIE", row['PIE'])

            f = st.columns(3)
            p_recent = df_active[df_active['Player/Team'] == p_name].sort_values(['Season', 'Game_ID'], ascending=False).head(3)
            for idx, (col, (_, game)) in enumerate(zip(f, p_recent.iterrows())):
                res = "✅ W" if game['Win'] == 1 else "❌ L"
                col.metric(f"Game {int(game['Game_ID'])}", f"{int(game['PTS'])} PTS", delta=res)

    with tabs[1]: # STANDINGS
        st.markdown("### Team Rankings")
        display_t = t_stats[['Team Name', 'Record', 'PTS/G', 'REB/G', 'AST/G', 'FG%']].sort_values('Record', ascending=False)
        sel_t = st.dataframe(display_t, width="stretch", hide_index=True, on_select="rerun", selection_mode="single-row")

        if len(sel_t.selection.rows) > 0:
            t_name = display_t.iloc[sel_t.selection.rows[0]]['Team Name']
            t_row = t_stats[t_stats['Team Name'] == t_name].iloc[0]
            st.markdown(f"### 🏘️ Team Report: {t_name}")
            tc = st.columns(3)
            tc[0].metric("Record", t_row['Record']); tc[1].metric("PPG", t_row['PTS/G']); tc[2].metric("FG%", f"{t_row['FG%']}%")
            
            ts = st.columns(3)
            ts[0].metric("3P%", f"{t_row['3P%']}%", f"{t_row['3PM/G']}/{t_row['3PA/G']}")
            ts[1].metric("2P%", f"{t_row['2P%']}%", f"{t_row['2PM/G']}/{t_row['2PA/G']}")
            ts[2].metric("Total Wins", int(t_row['Total_Wins']))

    with tabs[4]: # HALL OF FAME
        st.markdown("### 🏆 All-Time Highs")
        r = st.columns(4)
        def get_hof(col, t="player"):
            sub = full_df[full_df['Type'].str.lower() == t]
            if sub.empty: return "0", "N/A"
            idx = sub[col].idxmax()
            rec = sub.loc[idx]
            n = 'Player/Team' if t == "player" else 'Team Name'
            return f"{int(rec[col])}", f"{rec[n]} (S{int(rec['Season'])})"
        
        r[0].metric("Points", *get_hof('PTS')); r[0].metric("Steals", *get_hof('STL')); r[0].metric("3PM", *get_hof('3PM'))
        r[1].metric("Rebounds", *get_hof('REB')); r[1].metric("Blocks", *get_hof('BLK')); r[1].metric("3PA", *get_hof('3PA'))
        r[2].metric("Assists", *get_hof('AST')); r[2].metric("FGM", *get_hof('FGM')); r[2].metric("2PM", *get_hof('2PM'))
        r[3].metric("Game Win", *get_hof('Win')); r[3].metric("FGA", *get_hof('FGA')); r[3].metric("2PA", *get_hof('2PA'))
        
        st.divider()
        st.markdown("### 🎖️ Career Wins")
        rw = st.columns(2)
        c_p_wins = aggregate_stats(full_df[full_df['Type'].str.lower() == 'player'], 'Player/Team').nlargest(5, 'Win')[['Player/Team', 'Win']]
        rw[0].table(c_p_wins.rename(columns={'Win': 'Player Career Wins'}))
        c_t_wins = full_df[full_df['Type'].str.lower() == 'team'].groupby('Team Name')['Win'].sum().reset_index().nlargest(5, 'Win')
        rw[1].table(c_t_wins.rename(columns={'Win': 'Team Career Wins'}))

    st.markdown('<div style="text-align: center; color: #444; padding: 30px;">© 2026 SPAM LEAGUE HUB</div>', unsafe_allow_html=True)
