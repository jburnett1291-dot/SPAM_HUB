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
        df['is_ff'] = (df['PTS'] == 0) & (df['FGA'] == 0) & (df['REB'] == 0)
        
        def get_game_type(gid):
            if gid >= 9000: return "Playoff"
            if gid >= 8000: return "Tournament"
            if gid < 400: return "Regular" 
            return "Excluded"
        
        df['Game_Category'] = df['Game_ID'].apply(get_game_type)
        df = df[df['Game_Category'] != "Excluded"]

        def calc_multis(row):
            if row['is_ff']: return pd.Series([0, 0])
            s = [row['PTS'], row['REB'], row['AST'], row['STL'], row['BLK']]
            tens = sum(1 for x in s if x >= 10)
            return pd.Series([1 if tens >= 2 else 0, 1 if tens >= 3 else 0])
        
        df[['DD', 'TD']] = df.apply(calc_multis, axis=1)
        df['PIE_Raw'] = (df['PTS'] + df['REB'] + df['AST'] + df['STL'] + df['BLK']) - (df['FGA'] * 0.5) - df['TO']
        df['Poss_Raw'] = df['FGA'] + 0.44 * df['FTA'] + df['TO']
        return df
    except Exception as e: return str(e)

full_df = load_data()

# 3. STATS LOGIC
def get_stats(dataframe, group):
    if dataframe.empty: return pd.DataFrame()
    total_gp = dataframe.groupby(group).size().reset_index(name='GP')
    played_df = dataframe[dataframe['is_ff'] == False]
    played_gp = played_df.groupby(group).size().reset_index(name='Played_GP')
    sums = dataframe.groupby(group).sum(numeric_only=True).reset_index()
    m = pd.merge(sums, total_gp, on=group)
    m = pd.merge(m, played_gp, on=group, how='left').fillna(0)
    divisor = m['Played_GP'].replace(0, 1)
    for col in ['PTS', 'REB', 'AST', 'STL', 'BLK', 'TO', '3PM', '3PA', 'FTM', 'FTA', 'Poss_Raw', 'FGA', 'FGM', 'PIE_Raw', 'DD', 'TD']:
        m[f'{col}/G'] = (m[col] / divisor).round(2)
    m['FG%'] = (m['FGM'] / m['FGA'].replace(0,1) * 100).round(2)
    m['TS%'] = (m['PTS'] / (2 * (m['FGA'] + 0.44 * m['FTA']).replace(0, 1)) * 100).round(2)
    m['PPS'] = (m['PTS'] / m['FGA'].replace(0, 1)).round(2)
    m['OffRtg'] = (m['PTS'] / m['Poss_Raw'].replace(0,1) * 100).round(1)
    m['DefRtg'] = (100 * (1 - ((m['STL'] + m['BLK'] + (m['REB'] * 0.7)) / m['Poss_Raw'].replace(0,1)))).round(1)
    m['PIE'] = m['PIE_Raw/G']
    m['Poss/G'] = m['Poss_Raw/G']
    return m

# 5. APP CONTENT
if isinstance(full_df, str): st.error(f"⚠️ DATA ERROR: {full_df}")
elif full_df is not None:
    seasons = sorted(full_df['Season'].unique(), reverse=True)
    with st.sidebar: sel_box = st.selectbox("Scope", ["CAREER STATS"] + [f"Season {int(s)}" for s in seasons], index=1)
    df_active = full_df if sel_box == "CAREER STATS" else full_df[full_df['Season'] == int(sel_box.replace("Season ", ""))]

    p_stats = get_stats(df_active[df_active['Type'].str.lower() == 'player'], 'Player/Team').set_index('Player/Team')
    t_stats = get_stats(df_active[df_active['Type'].str.lower() == 'team'], 'Team Name').set_index('Team Name')

    leads = [f"🔥 {c}: {p_stats.nlargest(1, f'{c}/G').index[0]} ({p_stats.nlargest(1, f'{c}/G').iloc[0][f'{c}/G']})" for c in ['PTS', 'AST', 'REB', 'STL', 'BLK'] if not p_stats.empty]
    st.markdown(f'<div class="ticker-wrap"><div class="ticker-content"><span class="ticker-item">{" • ".join(leads)}</span></div></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="header-banner">🏀 SPAM HUB - {sel_box.upper()}</div>', unsafe_allow_html=True)

    tabs = st.tabs(["👤 PLAYERS", "🏘️ STANDINGS", "🔝 LEADERS", "⚔️ VERSUS", "🏟️ POSTSEASON", "📖 RECORD BOOK", "🔐 THE VAULT"])

    # (Tabs 0-4 contain previous logic)
    with tabs[0]: st.dataframe(p_stats[['GP', 'PTS/G', 'REB/G', 'AST/G', 'FG%', 'PIE']].sort_values('PIE', ascending=False), width="stretch")
    with tabs[1]: 
        t_stats['Record'] = t_stats['Win'].astype(int).astype(str) + "-" + (t_stats['GP'] - t_stats['Win']).astype(int).astype(str)
        st.dataframe(t_stats[['Record', 'PTS/G', 'REB/G', 'AST/G', 'FG%']].sort_values('Win', ascending=False), width="stretch")
    with tabs[2]:
        l_cat = st.selectbox("Category", ["PTS/G", "REB/G", "AST/G", "STL/G", "BLK/G", "PIE"])
        st.plotly_chart(px.bar(p_stats.nlargest(10, l_cat), x=l_cat, y=p_stats.nlargest(10, l_cat).index, orientation='h', template="plotly_dark", color_discrete_sequence=['#d4af37']), use_container_width=True)
    with tabs[3]: st.info("Compare players or teams in the 'Versus' mode.")
    with tabs[4]: st.info("Postseason game tracking (8k/9k Game IDs).")

    with tabs[5]:
        st.header("🏆 RECORD BOOK")
        hof_type = st.radio("Highs For", ["Players", "Teams"], horizontal=True)
        h_cols = ['PTS', 'REB', 'AST', 'STL', 'BLK', '3PM']
        entity_col = 'Player/Team' if hof_type == "Players" else "Team Name"
        
        # 1. CURRENT SCOPE HIGHS
        st.subheader(f"✨ {sel_box} Single-Game Highs")
        valid_active = df_active[(df_active['Type'].str.lower() == hof_type[:-1].lower()) & (df_active['is_ff'] == False)]
        g1 = st.columns(6)
        for i, col in enumerate(h_cols):
            if not valid_active.empty:
                val = valid_active[col].max()
                entity = valid_active.loc[valid_active[col].idxmax()][entity_col]
                g1[i].metric(f"{col}", f"{int(val)}", f"{entity}")

        # 2. ALL-TIME HIGHS
        st.subheader("🐐 All-Time Single-Game Highs")
        valid_all = full_df[(full_df['Type'].str.lower() == hof_type[:-1].lower()) & (full_df['is_ff'] == False)]
        g2 = st.columns(6)
        for i, col in enumerate(h_cols):
            if not valid_all.empty:
                val = valid_all[col].max()
                entity = valid_all.loc[valid_all[col].idxmax()][entity_col]
                g2[i].metric(f"All-Time {col}", f"{int(val)}", f"{entity}")

        st.divider()
        
        # 3. LEADERS TABLE (TOGGLE)
        st.subheader("📜 Statistical Leaders")
        l_scope = st.segmented_control("Leaderboard Range", ["Current Scope", "All-Time"], default="Current Scope")
        l_cat = st.selectbox("Stat Category", ['PTS', 'REB', 'AST', 'STL', 'BLK', '3PM', 'DD', 'TD', 'GP', 'Win'])
        
        target_df = df_active if l_scope == "Current Scope" else full_df
        career_df = get_stats(target_df[target_df['Type'].str.lower() == hof_type[:-1].lower()], entity_col)
        
        if not career_df.empty:
            st.table(career_df.nlargest(10, l_cat).reset_index(drop=True)[[entity_col, 'GP', l_cat]])

    with tabs[6]:
        st.header("🔐 THE VAULT")
        if st.text_input("Passcode", type="password") == "SPAM2026":
            st.success("Access Granted.")
            
            # Restore Streaks
            st.subheader("🔥 Momentum & Cold Streaks")
            streaks = []
            for player in p_stats.index:
                # Look at recent games from full history for this player
                p_games = full_df[(full_df['Player/Team'] == player) & (full_df['is_ff'] == False)].sort_values(['Season', 'Game_ID'], ascending=False)
                if len(p_games) >= 3:
                    avg_pts = p_stats.loc[player, 'PTS/G']
                    l3_avg = p_games.head(3)['PTS'].mean()
                    if l3_avg > avg_pts * 1.25: streaks.append({"Player": player, "Status": "🔥 ON FIRE", "Trend": f"+{round(l3_avg - avg_pts, 1)} PPG"})
                    elif l3_avg < avg_pts * 0.75: streaks.append({"Player": player, "Status": "❄️ COLD", "Trend": f"{round(l3_avg - avg_pts, 1)} PPG"})
            
            if streaks: st.table(pd.DataFrame(streaks))
            else: st.info("No active streaks detected.")

            st.divider()
            st.subheader("📊 Advanced Player Efficiency")
            st.dataframe(p_stats[['Poss/G', 'PPS', 'TS%', 'OffRtg', 'DefRtg', 'PIE']].sort_values('PIE', ascending=False), width="stretch")

    st.markdown('<div style="text-align: center; color: #444; padding: 30px;">© 2026 SPAM LEAGUE HUB</div>', unsafe_allow_html=True)
