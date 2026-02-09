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
        border-radius: 20px !important; padding: 20px !important;
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

# 2. DATA ENGINE (SUPER-CLEANER)
SHEET_ID = "1rksLYUcXQJ03uTacfIBD6SRsvtH-IE6djqT-LINwcH4"
URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"

@st.cache_data(ttl=10) # Reduced TTL to force-refresh more often
def load_data():
    try:
        df = pd.read_csv(URL)
        df.columns = df.columns.str.strip()
        
        # Super-Clean Win Column
        if 'Win' in df.columns:
            df['Win'] = pd.to_numeric(df['Win'], errors='coerce').fillna(0).astype(int)
        
        req_cols = ['PTS', 'REB', 'AST', 'STL', 'BLK', 'TO', 'FGA', 'FGM', '3PM', '3PA', 'FTA', 'FTM', 'Game_ID', 'Season']
        for c in req_cols:
            if c not in df.columns: df[c] = 0
            df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)
        
        # FF Detection: Stats are 0 but Season is valid
        df['is_ff'] = (df['PTS'] == 0) & (df['FGA'] == 0) & (df['REB'] == 0)
        
        def calc_multis(row):
            if row['is_ff']: return pd.Series([0, 0])
            s = [row['PTS'], row['REB'], row['AST'], row['STL'], row['BLK']]
            tens = sum(1 for x in s if x >= 10)
            return pd.Series([1 if tens >= 2 else 0, 1 if tens >= 3 else 0])
        df[['DD', 'TD']] = df.apply(calc_multis, axis=1)
        
        df['PIE'] = (df['PTS'] + df['REB'] + df['AST'] + df['STL'] + df['BLK']) - (df['FGA'] * 0.5) - df['TO']
        df['Poss'] = df['FGA'] + 0.44 * df['FTA'] + df['TO']
        return df
    except Exception as e:
        return str(e)

full_df = load_data()

# 3. DIALOG CARDS
@st.dialog("🏀 SCOUTING REPORT", width="large")
def show_card(name, stats_df, raw_df, is_player=True):
    row = stats_df.loc[name]
    st.title(f"{'👤' if is_player else '🏘️'} {name}")
    c = st.columns(5)
    c[0].metric("PPG", row['PTS/G']); c[1].metric("RPG", row['REB/G']); c[2].metric("APG", row['AST/G'])
    c[3].metric("SPG", row['STL/G']); c[4].metric("BPG", row['BLK/G'])
    st.markdown("---")
    s = st.columns(5)
    s[0].metric("FG%", f"{row['FG%']}%"); s[1].metric("3P%", f"{row['3P%']}%"); 
    s[2].metric("FT%", f"{row['FT%']}%"); s[3].metric("TO/G", row['TO/G']); s[4].metric("PIE", row['PIE'])
    
    st.markdown("#### 🕒 Recent Form")
    search_col = 'Player/Team' if is_player else 'Team Name'
    pt_type = 'player' if is_player else 'team'
    recent = raw_df[(raw_df[search_col] == name) & (raw_df['Type'].str.lower() == pt_type)].sort_values(['Season', 'Game_ID'], ascending=False).head(3)
    
    f_cols = st.columns(3)
    for idx, (col, (_, g)) in enumerate(zip(f_cols, recent.iterrows())):
        res = "✅ W" if g['Win'] == 1 else "❌ L"
        val = "FORFEIT" if g['is_ff'] else f"{int(g['PTS'])} PTS"
        col.metric(f"Game {int(g['Game_ID'])}", val, delta=res)
    
    if st.button("Close Card"): st.rerun()

if isinstance(full_df, str):
    st.error(f"⚠️ DATA ERROR: {full_df}")
else:
    # 4. PROCESSING
    seasons = sorted(full_df['Season'].unique(), reverse=True)
    opts = ["CAREER STATS"] + [f"Season {int(s)}" for s in seasons]
    with st.sidebar: sel_box = st.selectbox("League Scope", opts, index=1)
    df_active = full_df if sel_box == "CAREER STATS" else full_df[full_df['Season'] == int(sel_box.replace("Season ", ""))]

    def get_stats(dataframe, group):
        # GP uses total rows (including FF)
        gp_counts = dataframe.groupby(group).size().reset_index(name='GP')
        # Stats only for actual games
        played_df = dataframe[dataframe['is_ff'] == False]
        played_gp = played_df.groupby(group).size().reset_index(name='Played_GP')
        
        sums = dataframe.groupby(group).sum(numeric_only=True).reset_index()
        m = pd.merge(sums, gp_counts, on=group)
        m = pd.merge(m, played_gp, on=group, how='left').fillna(0)
        
        divisor = m['Played_GP'].replace(0, 1)
        for col in ['PTS', 'REB', 'AST', 'STL', 'BLK', 'TO', '3PM', '3PA', 'FTM', 'FTA', 'Poss', 'FGA']:
            m[f'{col}/G'] = (m[col] / divisor).round(2)
        m['FG%'] = (m['FGM'] / m['FGA'].replace(0,1) * 100).round(2)
        m['3P%'] = (m['3PM'] / m['3PA'].replace(0,1) * 100).round(2)
        m['FT%'] = (m['FTM'] / m['FTA'].replace(0,1) * 100).round(2)
        m['PIE'] = (m['PIE'] / divisor).round(2)
        return m

    p_stats = get_stats(df_active[df_active['Type'].str.lower() == 'player'], 'Player/Team').set_index('Player/Team')
    t_stats = get_stats(df_active[df_active['Type'].str.lower() == 'team'], 'Team Name').set_index('Team Name')

    leads = [f"🔥 {c}: {p_stats.nlargest(1, f'{c}/G').index[0]} ({p_stats.nlargest(1, f'{c}/G').iloc[0][f'{c}/G']})" for c in ['PTS', 'AST', 'REB', 'STL', 'BLK']]
    st.markdown(f'<div class="ticker-wrap"><div class="ticker-content"><span class="ticker-item">{" • ".join(leads)}</span></div></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="header-banner">🏀 SPAM HUB - {sel_box.upper()}</div>', unsafe_allow_html=True)

    tabs = st.tabs(["👤 PLAYERS", "🏘️ STANDINGS", "🔝 LEADERS", "⚔️ VERSUS", "📖 HALL OF FAME", "🔐 THE VAULT"])

    with tabs[1]: # STANDINGS (FORCE SORT & RECORD RE-CALC)
        t_stats['Wins'] = t_stats['Win'].astype(int)
        t_stats['Losses'] = (t_stats['GP'] - t_stats['Wins']).astype(int)
        t_stats['Record'] = t_stats['Wins'].astype(str) + "-" + t_stats['Losses'].astype(str)
        
        t_disp = t_stats.sort_values(['Wins', 'GP'], ascending=[False, True])[['Record', 'PTS/G', 'REB/G', 'FG%']]
        st.dataframe(t_disp, width="stretch")

    # [REST OF TABS REMAIN ACTIVE]
