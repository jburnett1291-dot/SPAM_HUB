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
    </style>
    """, unsafe_allow_html=True)

# 2. UPDATED DATA ENGINE (With TO, FTM, FTA, GP)
SHEET_ID = "1rksLYUcXQJ03uTacfIBD6SRsvtH-IE6djqT-LINwcH4"
URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"

@st.cache_data(ttl=60)
def load_data():
    try:
        df = pd.read_csv(URL)
        df.columns = df.columns.str.strip()
        # Track all requested stats
        req_cols = ['PTS', 'REB', 'AST', 'STL', 'BLK', 'TO', 'FGM', 'FGA', '3PM', '3PA', 'FTM', 'FTA', 'Game_ID', 'Win', 'Season']
        for c in req_cols:
            if c not in df.columns: df[c] = 0
            df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)
        
        # DD & TD Logic
        def calc_multis(row):
            s = [row['PTS'], row['REB'], row['AST'], row['STL'], row['BLK']]
            tens = sum(1 for x in s if x >= 10)
            return pd.Series([1 if tens >= 2 else 0, 1 if tens >= 3 else 0])
        df[['DD', 'TD']] = df.apply(calc_multis, axis=1)
        
        return df
    except Exception as e:
        return str(e)

full_df = load_data()

# 3. MODAL POP-UPS WITH AUTO-RESET
@st.dialog("🏀 SCOUTING REPORT", width="large")
def show_card(name, stats_df, raw_df, type='player'):
    row = stats_df[stats_df.index == name].iloc[0] if type=='player' else stats_df[stats_df['Team Name'] == name].iloc[0]
    st.title(f"Scouting: {name}")
    
    # Grid Layout
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("PPG", row['PTS/G']); c2.metric("RPG", row['REB/G']); c3.metric("APG", row['AST/G'])
    c4.metric("SPG", row['STL/G']); c5.metric("BPG", row['BLK/G'])
    
    st.markdown("---")
    s1, s2, s3, s4 = st.columns(4)
    s1.metric("FG%", f"{row['FG%']}%"); s2.metric("3P%", f"{row['3P%']}%")
    s3.metric("FT%", f"{row['FT%']}%"); s4.metric("GP", int(row['GP']))
    
    # FORM
    st.subheader("🕒 Recent Form")
    recent = raw_df[raw_df['Player/Team' if type=='player' else 'Team Name'] == name].sort_values(['Season', 'Game_ID'], ascending=False).head(3)
    cols = st.columns(3)
    for idx, (col, (_, g)) in enumerate(zip(cols, recent.iterrows())):
        col.metric(f"Game {int(g['Game_ID'])}", f"{int(g['PTS'])} PTS", "✅ W" if g['Win'] else "❌ L")

    if st.button("Close & Clear Selection", use_container_width=True):
        st.rerun()

if isinstance(full_df, str):
    st.error(f"⚠️ DATA ERROR: {full_df}")
else:
    # 4. GLOBAL FILTERS
    seasons = sorted(full_df['Season'].unique(), reverse=True)
    opts = ["CAREER STATS"] + [f"Season {int(s)}" for s in seasons]
    with st.sidebar: sel_box = st.selectbox("League Scope", opts, index=1)
    
    df_active = full_df if sel_box == "CAREER STATS" else full_df[full_df['Season'] == int(sel_box.replace("Season ", ""))]

    def get_stats(dataframe, group):
        gp = dataframe.groupby(group)['Game_ID'].nunique().reset_index(name='GP')
        sums = dataframe.groupby(group).sum(numeric_only=True).reset_index()
        m = pd.merge(sums, gp, on=group)
        for col in ['PTS', 'REB', 'AST', 'STL', 'BLK', 'TO', '3PM', '3PA', 'FTM', 'FTA']:
            m[f'{col}/G'] = (m[col] / m['GP'].replace(0,1)).round(1)
        m['FG%'] = (m['FGM'] / m['FGA'].replace(0,1) * 100).round(1)
        m['3P%'] = (m['3PM'] / m['3PA'].replace(0,1) * 100).round(1)
        m['FT%'] = (m['FTM'] / m['FTA'].replace(0,1) * 100).round(1)
        return m

    p_stats = get_stats(df_active[df_active['Type'].str.lower() == 'player'], 'Player/Team').set_index('Player/Team')
    t_stats = get_stats(df_active[df_active['Type'].str.lower() == 'team'], 'Team Name')

    st.markdown(f'<div class="header-banner">🏀 SPAM HUB - {sel_box.upper()}</div>', unsafe_allow_html=True)
    tabs = st.tabs(["👤 PLAYERS", "🏘️ STANDINGS", "🔝 LEADERS", "⚔️ VERSUS", "📖 HALL OF FAME"])

    with tabs[0]: # PLAYERS
        sel_p = st.dataframe(p_stats[['GP', 'PTS/G', 'REB/G', 'AST/G', 'FG%']], width="stretch", hide_index=False, on_select="rerun", selection_mode="single-row")
        if len(sel_p.selection.rows) > 0:
            show_card(p_stats.index[sel_p.selection.rows[0]], p_stats, df_active, 'player')

    with tabs[1]: # STANDINGS
        sel_t = st.dataframe(t_stats[['Team Name', 'GP', 'PTS/G', 'FG%']], width="stretch", hide_index=True, on_select="rerun", selection_mode="single-row")
        if len(sel_t.selection.rows) > 0:
            show_card(t_stats.iloc[sel_t.selection.rows[0]]['Team Name'], t_stats, df_active, 'team')

    with tabs[4]: # UPDATED HALL OF FAME
        st.header("🏆 HALL OF FAME RECORD BOOK")
        
        # SEASON HIGHS (SINGLE GAME)
        st.subheader("🔥 Single Game Season Highs")
        h_cols = ['PTS', 'REB', 'AST', 'STL', 'BLK', '3PM', 'TO']
        p_only = full_df[full_df['Type'].str.lower() == 'player']
        
        # Grid display for records
        grid = st.columns(4)
        for idx, col in enumerate(h_cols):
            if not p_only.empty:
                record_val = p_only[col].max()
                holder = p_only.loc[p_only[col].idxmax()]['Player/Team']
                grid[idx % 4].metric(f"Record: {col}", f"{int(record_val)}", f"by {holder}")

        st.divider()
        
        # CAREER LEADERS DROPDOWN
        st.subheader("👤 All-Time Career Leaders")
        cat = st.selectbox("Stat Category", ['PTS', 'REB', 'AST', 'STL', 'BLK', '3PM', '3PA', 'FTM', 'FTA', 'DD', 'TD', 'GP'])
        career = get_stats(full_df[full_df['Type'].str.lower() == 'player'], 'Player/Team')
        st.table(career.nlargest(10, cat)[['Player/Team', 'GP', cat]].reset_index(drop=True))

    st.markdown('<div style="text-align: center; color: #444; padding: 30px;">© 2026 SPAM LEAGUE HUB</div>', unsafe_allow_html=True)
