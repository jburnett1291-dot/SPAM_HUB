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
        
        # Ensure all columns exist
        req_cols = ['PTS', 'REB', 'AST', 'STL', 'BLK', 'FGA', 'FGM', '3PM', '3PA', 'FTA', 'Game_ID', 'Win', 'Season']
        for c in req_cols:
            if c not in df.columns: df[c] = 0
            df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)
        
        # Derived Splits
        df['2PM'] = df['FGM'] - df['3PM']
        df['2PA'] = df['FGA'] - df['3PA']
        
        def calc_multis(row):
            s = [row['PTS'], row['REB'], row['AST'], row['STL'], row['BLK']]
            tens = sum(1 for x in s if x >= 10)
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
    seasons = sorted(full_df['Season'].unique(), reverse=True)
    opts = ["CAREER STATS"] + [f"Season {int(s)}" for s in seasons]
    with st.sidebar:
        sel_box = st.selectbox("League Scope", opts, index=1)

    if sel_box == "CAREER STATS":
        df_active = full_df.copy()
        label = "CAREER"
    else:
        s_num = int(sel_box.replace("Season ", ""))
        df_active = full_df[full_df['Season'] == s_num]
        label = f"SEASON {s_num}"

    def get_stats(dataframe, group):
        gp = dataframe.groupby(group)['Game_ID'].nunique().reset_index(name='GP')
        sums = dataframe.groupby(group).sum(numeric_only=True).reset_index()
        m = pd.merge(sums, gp, on=group)
        pg = ['PTS', 'REB', 'AST', 'STL', 'BLK', '3PM', '3PA', '2PM', '2PA', 'FGM', 'FGA', 'Win']
        for col in pg:
            m[f'{col}/G'] = (m[col] / m['GP'].replace(0,1)).round(1)
        m['FG%'] = (m['FGM'] / m['FGA'].replace(0,1) * 100).round(1)
        return m

    # Players
    p_data = get_stats(df_active[df_active['Type'].str.lower() == 'player'], 'Player/Team')
    teams = df_active[df_active['Type'].str.lower() == 'player'].groupby('Player/Team')['Team Name'].last().reset_index()
    p_data = pd.merge(p_data, teams, on='Player/Team')

    # Teams
    t_raw = df_active[df_active['Type'].str.lower() == 'team']
    t_stats = get_stats(t_raw, 'Team Name')
    t_stats['Wins'] = t_raw.groupby('Team Name')['Win'].sum().values.astype(int)
    t_stats['Loss'] = (t_stats['GP'] - t_stats['Wins']).astype(int)
    t_stats['Record'] = t_stats['Wins'].astype(str) + "-" + t_stats['Loss'].astype(str)

    # 4. UI
    leads = [f"🔥 {c}: {p_data.nlargest(1, c+'/G').iloc[0]['Player/Team']} ({p_data.nlargest(1, c+'/G').iloc[0][c+'/G']})" for c in ['PTS', 'AST', 'REB'] if not p_data.empty]
    st.markdown(f'<div class="ticker-wrap"><div class="ticker-content"><span class="ticker-item">{" • ".join(leads)}</span></div></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="header-banner">🏀 SPAM HUB - {label}</div>', unsafe_allow_html=True)

    tabs = st.tabs(["👤 PLAYERS", "🏘️ STANDINGS", "🔝 LEADERS", "⚔️ VERSUS", "📖 HALL OF FAME"])

    with tabs[0]: # PLAYER HUB
        p_table = p_data[['Player/Team', 'Team Name', 'GP', 'PTS/G', 'REB/G', 'AST/G', 'FG%', 'PIE']].sort_values('PIE', ascending=False)
        sel_p = st.dataframe(p_table, width="stretch", hide_index=True, on_select="rerun", selection_mode="single-row")
        if len(sel_p.selection.rows) > 0:
            name = p_table.iloc[sel_p.selection.rows[0]]['Player/Team']
            row = p_data[p_data['Player/Team'] == name].iloc[0]
            st.markdown(f"### 🔎 Scouting: {name}")
            c = st.columns(5); c[0].metric("PPG", row['PTS/G']); c[1].metric("RPG", row['REB/G']); c[2].metric("APG", row['AST/G']); c[3].metric("SPG", row['STL/G']); c[4].metric("BPG", row['BLK/G'])
            f = st.columns(3); p_rec = df_active[df_active['Player/Team'] == name].sort_values(['Season', 'Game_ID'], ascending=False).head(3)
            for _, g in p_rec.iterrows(): f[len(f)-3].metric(f"Game {int(g['Game_ID'])}", f"{int(g['PTS'])} PTS", "✅ W" if g['Win'] else "❌ L")
            st.line_chart(df_active[df_active['Player/Team'] == name].sort_values(['Season', 'Game_ID']).set_index('Game_ID')['PTS'])

    with tabs[1]: # STANDINGS
        st.markdown("### Team Rankings")
        t_disp = t_stats[['Team Name', 'Record', 'PTS/G', 'REB/G', 'AST/G', 'FG%']].sort_values('Record', ascending=False)
        sel_t = st.dataframe(t_disp, width="stretch", hide_index=True, on_select="rerun", selection_mode="single-row")
        if len(sel_t.selection.rows) > 0:
            tn = t_disp.iloc[sel_t.selection.rows[0]]['Team Name']
            tr = t_stats[t_stats['Team Name'] == tn].iloc[0]
            st.markdown(f"### 🏘️ Team Report: {tn}")
            tc = st.columns(3); tc[0].metric("Record", tr['Record']); tc[1].metric("PPG", tr['PTS/G']); tc[2].metric("FG%", f"{tr['FG%']}%")
            tf = st.columns(3); t_rec = df_active[(df_active['Type'].str.lower()=='team') & (df_active['Team Name']==tn)].sort_values(['Season', 'Game_ID'], ascending=False).head(3)
            for _, g in t_rec.iterrows(): tf[len(tf)-3].metric(f"Game {int(g['Game_ID'])}", f"{int(g['PTS'])} PTS", "✅ W" if g['Win'] else "❌ L")

    with tabs[2]: # LEADERS
        cat = st.selectbox("Stat", ["PTS/G", "REB/G", "AST/G", "STL/G", "BLK/G", "PIE"])
        t10 = p_data.nlargest(10, cat)[['Player/Team', 'Team Name', cat]].reset_index(drop=True)
        st.table(t10); st.plotly_chart(px.bar(t10, x=cat, y='Player/Team', orientation='h', template="plotly_dark", color_discrete_sequence=['#d4af37']))

    with tabs[3]: # VERSUS
        v_m = st.radio("Mode", ["Player vs Player", "Team vs Team"], horizontal=True)
        v1, v2 = st.columns(2)
        if v_m == "Player vs Player":
            n1 = v1.selectbox("P1", p_data['Player/Team'].unique()); n2 = v2.selectbox("P2", p_data['Player/Team'].unique())
            r1, r2 = p_data[p_data['Player/Team']==n1].iloc[0], p_data[p_data['Player/Team']==n2].iloc[0]
            for s in ['PTS/G', 'REB/G', 'AST/G', 'FG%', 'PIE']:
                c1, c2 = st.columns(2); c1.metric(f"{n1} {s}", r1[s], round(r1[s]-r2[s],1)); c2.metric(f"{n2} {s}", r2[s], round(r2[s]-r1[s],1))
        else:
            n1 = v1.selectbox("T1", t_stats['Team Name'].unique()); n2 = v2.selectbox("T2", t_stats['Team Name'].unique())
            r1, r2 = t_stats[t_stats['Team Name']==n1].iloc[0], t_stats[t_stats['Team Name']==n2].iloc[0]
            for s in ['PTS/G', 'REB/G', 'AST/G', 'FG%']:
                c1, c2 = st.columns(2); c1.metric(f"{n1} {s}", r1[s], round(r1[s]-r2[s],1)); c2.metric(f"{n2} {s}", r2[s], round(r2[s]-r1[s],1))

    with tabs[4]: # HALL OF FAME
        st.markdown("### 🏅 Hall of Fame Record Book")
        cat_hof = st.selectbox("Stat Category", ['PTS', 'REB', 'AST', 'STL', 'BLK', '3PM', '3PA', '2PM', '2PA', 'FGM', 'FGA', 'PIE'])
        p_only = full_df[full_df['Type'].str.lower() == 'player']
        if not p_only.empty:
            rec = p_only.loc[p_only[cat_hof].idxmax()]
            st.metric(f"Record Holder: {rec['Player/Team']} (Season {int(rec['Season'])})", f"{int(rec[cat_hof]) if cat_hof != 'PIE' else rec[cat_hof]}")
            st.table(p_only.nlargest(10, cat_hof)[['Player/Team', 'Season', 'Game_ID', cat_hof]].reset_index(drop=True))

    st.markdown('<div style="text-align: center; color: #444; padding: 30px;">© 2026 SPAM LEAGUE HUB</div>', unsafe_allow_html=True)
