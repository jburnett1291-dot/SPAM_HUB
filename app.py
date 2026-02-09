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
            if c in df.columns:
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
    # 3. GLOBAL FILTERS
    seasons_list = sorted(full_df['Season'].unique(), reverse=True)
    options = ["CAREER STATS (ALL SEASONS)"] + [f"Season {int(s)}" for s in seasons_list]
    
    with st.sidebar:
        st.markdown("### 🗓️ LEAGUE SCOPE")
        sel_box = st.selectbox("Select View", options, index=1)
        st.divider()

    if sel_box == "CAREER STATS (ALL SEASONS)":
        df_active = full_df.copy()
        display_label = "CAREER TOTALS"
    else:
        s_num = int(sel_box.replace("Season ", ""))
        df_active = full_df[full_df['Season'] == s_num]
        display_label = f"SEASON {s_num}"

    # PRE-PROCESS STATS
    def aggregate_stats(dataframe, group_col):
        gp = dataframe.groupby(group_col)['Game_ID'].nunique().reset_index(name='GP')
        sums = dataframe.groupby(group_col).sum(numeric_only=True).reset_index()
        merged = pd.merge(sums, gp, on=group_col)
        for s in ['PTS', 'REB', 'AST', 'STL', 'BLK', '3PM', 'FGA', 'FGM', 'Win']:
            merged[f'{s}/G'] = (merged[s] / merged['GP'].replace(0,1)).round(1)
        merged['FG%'] = (merged['FGM'] / merged['FGA'].replace(0,1) * 100).round(1)
        return merged

    p_data = aggregate_stats(df_active[df_active['Type'].str.lower() == 'player'], 'Player/Team')
    team_map = df_active[df_active['Type'].str.lower() == 'player'].groupby('Player/Team')['Team Name'].last().reset_index()
    p_data = pd.merge(p_data, team_map, on='Player/Team')

    t_raw = df_active[df_active['Type'].str.lower() == 'team']
    t_stats = aggregate_stats(t_raw, 'Team Name')
    t_stats['Record_Win'] = t_raw.groupby('Team Name')['Win'].sum().values.astype(int)
    t_stats['Loss'] = (t_stats['GP'] - t_stats['Record_Win']).astype(int)
    t_stats['Record'] = t_stats['Record_Win'].astype(str) + "-" + t_stats['Loss'].astype(str)

    # UI RENDERING
    leads = [f"🔥 {c}: {p_data.nlargest(1, c+'/G').iloc[0]['Player/Team']} ({p_data.nlargest(1, c+'/G').iloc[0][c+'/G']})" for c in ['PTS', 'AST', 'REB', 'STL', 'BLK'] if not p_data.empty]
    st.markdown(f'<div class="ticker-wrap"><div class="ticker-content"><span class="ticker-item">{" • ".join(leads)}</span></div></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="header-banner">🏀 SPAM HUB - {display_label}</div>', unsafe_allow_html=True)

    tabs = st.tabs(["👤 PLAYERS", "🏘️ STANDINGS", "🔝 LEADERS", "⚔️ VERSUS", "📖 HALL OF FAME"])

    with tabs[0]: # PLAYER HUB
        display_p = p_data[['Player/Team', 'Team Name', 'GP', 'PTS/G', 'REB/G', 'AST/G', 'STL/G', 'BLK/G', 'FG%', 'PIE']].sort_values('PIE', ascending=False)
        sel_p = st.dataframe(display_p.rename(columns={'STL/G': 'SPG', 'BLK/G': 'BPG'}), width="stretch", hide_index=True, on_select="rerun", selection_mode="single-row")
        
        if len(sel_p.selection.rows) > 0:
            p_name = display_p.iloc[sel_p.selection.rows[0]]['Player/Team']
            row = p_data[p_data['Player/Team'] == p_name].iloc[0]
            st.markdown(f"### 🔎 Scouting Report: {p_name}")
            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric("PPG", row['PTS/G']); c2.metric("RPG", row['REB/G']); c3.metric("APG", row['AST/G'])
            c4.metric("SPG", row['STL/G']); c5.metric("BPG", row['BLK/G'])
            
            st.markdown("#### 🕒 Recent Form (Last 3 Games)")
            f1, f2, f3 = st.columns(3)
            p_recent = df_active[df_active['Player/Team'] == p_name].sort_values(['Season', 'Game_ID'], ascending=False).head(3)
            for idx, (col, (_, game)) in enumerate(zip([f1, f2, f3], p_recent.iterrows())):
                res = "✅ W" if game['Win'] == 1 else "❌ L"
                col.metric(f"Game {int(game['Game_ID'])}", f"{int(game['PTS'])} PTS", delta=res)
            st.line_chart(df_active[df_active['Player/Team'] == p_name].sort_values(['Season', 'Game_ID']).set_index('Game_ID')['PTS'])

    with tabs[1]: # STANDINGS
        st.markdown("### Team Rankings")
        display_t = t_stats[['Team Name', 'Record', 'PTS/G', 'REB/G', 'AST/G', 'STL/G', 'BLK/G', 'FG%']].sort_values('Record', ascending=False)
        sel_t = st.dataframe(display_t.rename(columns={'STL/G': 'SPG', 'BLK/G': 'BPG'}), width="stretch", hide_index=True, on_select="rerun", selection_mode="single-row")

        if len(sel_t.selection.rows) > 0:
            t_name = display_t.iloc[sel_t.selection.rows[0]]['Team Name']
            t_row = t_stats[t_stats['Team Name'] == t_name].iloc[0]
            st.markdown(f"### 🏘️ Team Scouting Report: {t_name}")
            tc1, tc2, tc3, tc4, tc5 = st.columns(5)
            tc1.metric("Record", t_row['Record']); tc2.metric("Team PPG", t_row['PTS/G']); tc3.metric("Team RPG", t_row['REB/G'])
            tc4.metric("Team FG%", f"{t_row['FG%']}%"); tc5.metric("GP", int(t_row['GP']))
            
            st.markdown("#### 🕒 Recent Team Results")
            tf1, tf2, tf3 = st.columns(3)
            t_recent = df_active[(df_active['Type'].str.lower() == 'team') & (df_active['Team Name'] == t_name)].sort_values(['Season', 'Game_ID'], ascending=False).head(3)
            for idx, (col, (_, game)) in enumerate(zip([tf1, tf2, tf3], t_recent.iterrows())):
                res = "✅ W" if game['Win'] == 1 else "❌ L"
                col.metric(f"Game {int(game['Game_ID'])}", f"{int(game['PTS'])} PTS", delta=res)
            st.line_chart(df_active[(df_active['Type'].str.lower() == 'team') & (df_active['Team Name'] == t_name)].sort_values(['Season', 'Game_ID']).set_index('Game_ID')['PTS'])

    with tabs[2]: # LEADERS
        cat = st.selectbox("Category", ["PTS/G", "REB/G", "AST/G", "STL/G", "BLK/G", "FG%", "PIE"])
        t10 = p_data.nlargest(10, cat)[['Player/Team', 'Team Name', cat]].reset_index(drop=True)
        st.table(t10)
        st.plotly_chart(px.bar(t10, x=cat, y='Player/Team', orientation='h', template="plotly_dark", color_discrete_sequence=['#d4af37']), width="stretch")

    with tabs[3]: # VERSUS
        v_mode = st.radio("Mode", ["Player vs Player", "Team vs Team"], horizontal=True)
        v1, v2 = st.columns(2)
        if v_mode == "Player vs Player":
            p1_name = v1.selectbox("P1", p_data['Player/Team'].unique(), index=0)
            p2_name = v2.selectbox("P2", p_data['Player/Team'].unique(), index=1)
            d1, d2 = p_data[p_data['Player/Team']==p1_name].iloc[0], p_data[p_data['Player/Team']==p2_name].iloc[0]
            for s in ['PTS/G', 'REB/G', 'AST/G', 'STL/G', 'BLK/G', 'FG%']:
                sc1, sc2 = st.columns(2)
                sc1.metric(f"{p1_name} {s}", d1[s], delta=round(d1[s]-d2[s], 1))
                sc2.metric(f"{p2_name} {s}", d2[s], delta=round(d2[s]-d1[s], 1))
        else:
            tm1 = v1.selectbox("T1", t_stats['Team Name'].unique(), index=0)
            tm2 = v2.selectbox("T2", t_stats['Team Name'].unique(), index=1)
            td1, td2 = t_stats[t_stats['Team Name']==tm1].iloc[0], t_stats[t_stats['Team Name']==tm2].iloc[0]
            for s in ['PTS/G', 'REB/G', 'AST/G', 'FG%']:
                sc1, sc2 = st.columns(2)
                sc1.metric(f"{tm1} {s}", td1[s], delta=round(td1[s]-td2[s], 1))
                sc2.metric(f"{tm2} {s}", td2[s], delta=round(td2[s]-td1[s], 1))

    with tabs[4]: # HALL OF FAME
        st.markdown("### 🏆 Single Game Records & Totals")
        r1, r2, r3 = st.columns(3)
        def get_hof(col, t="player"):
            sub = full_df[full_df['Type'].str.lower() == t]
            if sub.empty: return "0", "N/A"
            idx = sub[col].idxmax()
            rec = sub.loc[idx]
            name_col = 'Player/Team' if t == "player" else 'Team Name'
            return f"{int(rec[col])}", f"{rec[name_col]} (S{int(rec['Season'])})"
        
        r1.metric("Points", *get_hof('PTS')); r1.metric("Steals", *get_hof('STL'))
        r2.metric("Rebounds", *get_hof('REB')); r2.metric("Blocks", *get_hof('BLK'))
        r3.metric("Assists", *get_hof('AST')); r3.metric("3PM", *get_hof('3PM'))
        
        st.divider()
        st.markdown("### 🎖️ Career Wins & Milestones")
        rw1, rw2 = st.columns(2)
        c_p_wins = aggregate_stats(full_df[full_df['Type'].str.lower() == 'player'], 'Player/Team').nlargest(5, 'Win')[['Player/Team', 'Win']]
        rw1.write("**Career Player Wins**")
        rw1.table(c_p_wins.rename(columns={'Win': 'Total Wins'}))
        c_t_wins = full_df[full_df['Type'].str.lower() == 'team'].groupby('Team Name')['Win'].sum().reset_index().nlargest(5, 'Win')
        rw2.write("**Career Team Wins**")
        rw2.table(c_t_wins.rename(columns={'Win': 'Total Wins'}))

    st.markdown('<div style="text-align: center; color: #444; padding: 30px;">© 2026 SPAM LEAGUE HUB</div>', unsafe_allow_html=True)
