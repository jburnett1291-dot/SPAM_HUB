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

# 2. SUPER-CLEANER DATA ENGINE
SHEET_ID = "1rksLYUcXQJ03uTacfIBD6SRsvtH-IE6djqT-LINwcH4"
URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"

@st.cache_data(ttl=10) # Reduced TTL to see updates faster
def load_data():
    try:
        df = pd.read_csv(URL)
        df.columns = df.columns.str.strip() # Remove hidden spaces from headers
        
        # Super-Clean the 'Win' column: Convert W/L or strings to 1/0
        if 'Win' in df.columns:
            df['Win'] = df['Win'].astype(str).str.upper().str.strip()
            df['Win'] = df['Win'].apply(lambda x: 1 if x in ['1', '1.0', 'W', 'WIN'] else 0)
        
        # Ensure all numeric cols are numeric
        req_cols = ['PTS', 'REB', 'AST', 'STL', 'BLK', 'TO', 'FGA', 'FGM', '3PM', '3PA', 'FTA', 'FTM', 'Game_ID', 'Season']
        for c in req_cols:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)
            else:
                df[c] = 0
        
        # FF Logic: Row is FF if major stats are zero but Season is present
        df['is_ff'] = (df['PTS'] == 0) & (df['REB'] == 0) & (df['FGA'] == 0)
        
        # Multi and PIE logic
        df['PIE'] = (df['PTS'] + df['REB'] + df['AST'] + df['STL'] + df['BLK']) - (df['FGA'] * 0.5) - df['TO']
        df['Poss'] = df['FGA'] + 0.44 * df['FTA'] + df['TO']
        return df
    except Exception as e:
        return str(e)

full_df = load_data()

# 3. STATS LOGIC (Fixed for FF Records)
def get_stats(dataframe, group):
    # Total Games (Record) includes FF rows
    total_gp = dataframe.groupby(group).size().reset_index(name='GP')
    # Stats averages only use rows with actual data
    played_df = dataframe[dataframe['is_ff'] == False]
    played_gp = played_df.groupby(group).size().reset_index(name='Played_GP')
    
    sums = dataframe.groupby(group).sum(numeric_only=True).reset_index()
    m = pd.merge(sums, total_gp, on=group)
    m = pd.merge(m, played_gp, on=group, how='left').fillna(0)
    
    divisor = m['Played_GP'].replace(0, 1)
    for col in ['PTS', 'REB', 'AST', 'STL', 'BLK', 'TO', '3PM', '3PA', 'FTM', 'FTA', 'Poss', 'FGA']:
        m[f'{col}/G'] = (m[col] / divisor).round(2)
    
    m['FG%'] = (m['FGM'] / m['FGA'].replace(0,1) * 100).round(2)
    m['3P%'] = (m['3PM'] / m['3PA'].replace(0,1) * 100).round(2)
    m['FT%'] = (m['FTM'] / m['FTA'].replace(0,1) * 100).round(2)
    m['PIE'] = (m['PIE'] / divisor).round(2)
    return m

# 4. DIALOG CARDS
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
    # FILTERS
    seasons = sorted(full_df['Season'].unique(), reverse=True)
    opts = ["CAREER STATS"] + [f"Season {int(s)}" for s in seasons]
    with st.sidebar: sel_box = st.selectbox("League Scope", opts, index=1)
    df_active = full_df if sel_box == "CAREER STATS" else full_df[full_df['Season'] == int(sel_box.replace("Season ", ""))]

    p_stats = get_stats(df_active[df_active['Type'].str.lower() == 'player'], 'Player/Team').set_index('Player/Team')
    t_stats = get_stats(df_active[df_active['Type'].str.lower() == 'team'], 'Team Name').set_index('Team Name')

    leads = [f"🔥 {c}: {p_stats.nlargest(1, f'{c}/G').index[0]} ({p_stats.nlargest(1, f'{c}/G').iloc[0][f'{c}/G']})" for c in ['PTS', 'AST', 'REB', 'STL', 'BLK']]
    st.markdown(f'<div class="ticker-wrap"><div class="ticker-content"><span class="ticker-item">{" • ".join(leads)}</span></div></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="header-banner">🏀 SPAM HUB - {sel_box.upper()}</div>', unsafe_allow_html=True)

    tabs = st.tabs(["👤 PLAYERS", "🏘️ STANDINGS", "🔝 LEADERS", "⚔️ VERSUS", "📖 HALL OF FAME", "🔐 THE VAULT"])

    with tabs[1]: # STANDINGS
        # Record calculation
        t_stats['Wins'] = t_stats['Win'].astype(int)
        t_stats['Losses'] = (t_stats['GP'] - t_stats['Wins']).astype(int)
        t_stats['Record'] = t_stats['Wins'].astype(str) + "-" + t_stats['Losses'].astype(str)
        
        t_display = t_stats.sort_values('Wins', ascending=False)[['Record', 'PTS/G', 'REB/G', 'FG%']]
        sel_t = st.dataframe(t_display, width="stretch", on_select="rerun", selection_mode="single-row")
        if len(sel_t.selection.rows) > 0:
            show_card(t_display.index[sel_t.selection.rows[0]], t_stats, df_active, False)

    # ... [Rest of your tabs (Players, Leaders, Versus, HOF, Vault) remain the same as previous version]
