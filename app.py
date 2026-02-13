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
    .league-footer {
        position: fixed; left: 0; bottom: 0; width: 100%;
        background: rgba(0, 0, 0, 0.95); color: #d4af37;
        text-align: center; padding: 12px; font-weight: bold;
        border-top: 2px solid #d4af37; z-index: 999; font-size: 15px;
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
        req_cols = ['PTS', 'REB', 'AST', 'STL', 'BLK', 'TO', 'FGA', 'FGM', '3PM', '3PA', 'FTA', 'FTM', 'Game_ID', 'Win', 'Season']
        for c in req_cols:
            if c not in df.columns: df[c] = 0
            df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)
        
        # FF RULE: If ID is 1111 OR stats are all 0, it's a forfeit
        df['is_ff'] = (df['Game_ID'] == 1111) | ((df['PTS'] == 0) & (df['FGA'] == 0) & (df['REB'] == 0))
        
        def get_game_type(gid):
            if gid >= 9000: return "Playoff"
            if gid >= 8000: return "Tournament"
            if gid < 400: return "Regular" 
            return "Excluded"
        df['Game_Category'] = df['Game_ID'].apply(get_game_type)
        
        return df[df['Game_Category'] != "Excluded"]
    except Exception as e: return str(e)

full_df = load_data()

# 3. STATS LOGIC
def get_stats(dataframe, group):
    if dataframe.empty: return pd.DataFrame()
    
    # Track 1: STANDINGS (Looks at every row)
    total_gp = dataframe.groupby(group).size().reset_index(name='GP')
    total_wins = dataframe.groupby(group)['Win'].sum().reset_index(name='W')
    
    # Track 2: STATS (Filters out Forfeits)
    played_df = dataframe[dataframe['is_ff'] == False]
    played_gp = played_df.groupby(group).size().reset_index(name='Played_GP')
    sums = played_df.groupby(group).sum(numeric_only=True).reset_index()
    
    # Merge Tracks
    m = pd.merge(total_gp, total_wins, on=group)
    m = pd.merge(m, sums.drop(columns=['Win'], errors='ignore'), on=group, how='left').fillna(0)
    m = pd.merge(m, played_gp, on=group, how='left').fillna(0)
    
    # Final Standings Math
    m['L'] = (m['GP'] - m['W']).astype(int)
    m['W'] = m['W'].astype(int)
    m['Win%'] = (m['W'] / m['GP']).round(3)
    
    # Per Game Math
    divisor = m['Played_GP'].replace(0, 1)
    for col in ['PTS', 'REB', 'AST', 'STL', 'BLK', 'TO', 'FGM', 'FGA']:
        m[f'{col}/G'] = (m[col] / divisor).round(2)
        
    m['FG%'] = (m['FGM'] / m['FGA'].replace(0,1) * 100).round(1)
    return m

# 5. APP CONTENT
if isinstance(full_df, str): st.error(f"⚠️ DATA ERROR: {full_df}")
elif full_df is not None:
    seasons = sorted(full_df['Season'].unique(), reverse=True)
    with st.sidebar: sel_box = st.selectbox("Scope", ["CAREER STATS"] + [f"Season {int(s)}" for s in seasons], index=1)
    df_active = full_df if sel_box == "CAREER STATS" else full_df[full_df['Season'] == int(sel_box.replace("Season ", ""))]

    p_stats = get_stats(df_active[df_active['Type'].str.lower() == 'player'], 'Player/Team').set_index('Player/Team')
    t_stats = get_stats(df_active[df_active['Type'].str.lower() == 'team'], 'Team Name').set_index('Team Name')

    leads = [f"🔥 {c}: {p_stats.nlargest(1, f'{c}/G').index[0]} ({p_stats.nlargest(1, f'{c}/G').iloc[0][f'{c}/G']})" for c in ['PTS', 'AST', 'REB'] if not p_stats.empty]
    st.markdown(f'<div class="ticker-wrap"><div class="ticker-content"><span class="ticker-item">{" • ".join(leads)}</span></div></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="header-banner">🏀 SPAM HUB - {sel_box.upper()}</div>', unsafe_allow_html=True)

    tabs = st.tabs(["👤 PLAYERS", "🏘️ STANDINGS", "🔝 LEADERS", "⚔️ VERSUS", "🏟️ POSTSEASON", "🔐 THE VAULT"])

    with tabs[0]:
        st.dataframe(p_stats[['GP', 'PTS/G', 'REB/G', 'AST/G', 'FG%']].sort_values('PTS/G', ascending=False), width="stretch")

    with tabs[1]:
        if not t_stats.empty:
            t_disp = t_stats.sort_values(['Win%', 'W'], ascending=False)[['W', 'L', 'Win%', 'PTS/G', 'REB/G', 'AST/G']]
            st.dataframe(t_disp, width="stretch")

    with tabs[2]:
        cat = st.selectbox("Stat", ["PTS/G", "REB/G", "AST/G"])
        st.plotly_chart(px.bar(p_stats.nlargest(10, cat), x=cat, template="plotly_dark", color_discrete_sequence=['#d4af37']), use_container_width=True)

    with tabs[3]:
        v1, v2 = st.columns(2)
        if not p_stats.empty:
            p1 = v1.selectbox("Choice A", p_stats.index); p2 = v2.selectbox("Choice B", p_stats.index)
            st.table(pd.concat([p_stats.loc[[p1]], p_stats.loc[[p2]]])[['PTS/G', 'REB/G', 'AST/G', 'FG%']])

    with tabs[4]:
        ps_df = df_active[df_active['Game_Category'].isin(['Playoff', 'Tournament'])]
        if not ps_df.empty:
            st.dataframe(get_stats(ps_df, 'Player/Team').set_index('Player/Team')[['GP', 'PTS/G']], width="stretch")
        else: st.info("No Postseason games found.")

    with tabs[5]:
        if st.text_input("Passcode", type="password") == "SPAM2026":
            st.success("Access Granted.")
            st.dataframe(p_stats[['W', 'L', 'GP']], width="stretch")

    st.markdown('<div style="text-align: center; color: #444; padding: 70px;">© 2026 SPAM LEAGUE HUB</div>', unsafe_allow_html=True)
