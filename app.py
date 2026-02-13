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
        
        # Base FF Rule
        df['is_ff'] = (df['PTS'] == 0) & (df['FGA'] == 0) & (df['REB'] == 0)
        
        # Categorization Logic
        def get_game_type(gid):
            if gid >= 9000: return "Playoff"
            if gid >= 8000: return "Tournament"
            if gid < 400: return "Regular" 
            return "Excluded"
        df['Game_Category'] = df['Game_ID'].apply(get_game_type)

        def calc_multis(row):
            if row['is_ff']: return pd.Series([0, 0])
            s = [row['PTS'], row['REB'], row['AST'], row['STL'], row['BLK']]
            tens = sum(1 for x in s if x >= 10)
            return pd.Series([1 if tens >= 2 else 0, 1 if tens >= 3 else 0])
        df[['DD', 'TD']] = df.apply(calc_multis, axis=1)
        df['PIE_Raw'] = (df['PTS'] + df['REB'] + df['AST'] + df['STL'] + df['BLK']) - (df['FGA'] * 0.5) - df['TO']
        df['Poss_Raw'] = df['FGA'] + 0.44 * df['FTA'] + df['TO']
        df['FG%_Raw'] = (df['FGM'] / df['FGA'].replace(0,1) * 100).round(1)
        return df[df['Game_Category'] != "Excluded"]
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
    
    stat_list = ['PTS', 'REB', 'AST', 'STL', 'BLK', 'TO', '3PM', '3PA', 'FTM', 'FTA', 'Poss_Raw', 'FGA', 'FGM', 'PIE_Raw', 'DD', 'TD']
    for col in stat_list:
        m[f'{col}/G'] = (m[col] / divisor).round(2)
        
    m['FG%'] = (m['FGM'] / m['FGA'].replace(0,1) * 100).round(2)
    m['TS%'] = (m['PTS'] / (2 * (m['FGA'] + 0.44 * m['FTA']).replace(0, 1)) * 100).round(2)
    m['PPS'] = (m['PTS'] / m['FGA'].replace(0, 1)).round(2)
    m['Win%'] = (m['Win'] / m['GP']).round(3)
    m['OffRtg'] = (m['PTS'] / m['Poss_Raw'].replace(0,1) * 100).round(1)
    m['DefRtg'] = (100 * (1 - ((m['STL'] + m['BLK'] + (m['REB'] * 0.7)) / m['Poss_Raw'].replace(0,1)))).round(1)
    m['PIE'] = m['PIE_Raw/G']
    m['Poss/G'] = m['Poss_Raw/G']
    return m

# 4. DIALOG CARDS (Preserved)
@st.dialog("🏀 SCOUTING REPORT", width="large")
def show_card(name, stats_df, raw_df, is_player=True):
    row = stats_df.loc[name]
    st.title(f"{'👤' if is_player else '🏘️'} {name}")
    c = st.columns(5); c[0].metric("PPG", row['PTS/G']); c[1].metric("RPG", row['REB/G']); c[2].metric("APG", row['AST/G']); c[3].metric("SPG", row['STL/G']); c[4].metric("BPG", row['BLK/G'])
    st.markdown("---"); st.subheader("🏆 Season Highs")
    s_col = 'Player/Team' if is_player else 'Team Name'
    personal = raw_df[(raw_df[s_col] == name) & (raw_df['Type'].str.lower() == ('player' if is_player else 'team'))]
    h = st.columns(5); h[0].metric("Max PTS", int(personal['PTS'].max())); h[1].metric("Max REB", int(personal['REB'].max())); h[2].metric("Max AST", int(personal['AST'].max())); h[3].metric("Max STL", int(personal['STL'].max())); h[4].metric("Max BLK", int(personal['BLK'].max()))
    if st.button("Close Card", use_container_width=True): st.rerun()

# 5. APP CONTENT
if isinstance(full_df, str): st.error(f"⚠️ DATA ERROR: {full_df}")
elif full_df is not None:
    seasons = sorted(full_df['Season'].unique(), reverse=True)
    with st.sidebar: sel_box = st.selectbox("Scope", ["CAREER STATS"] + [f"Season {int(s)}" for s in seasons], index=1)
    df_active = full_df if sel_box == "CAREER STATS" else full_df[full_df['Season'] == int(sel_box.replace("Season ", ""))]

    p_stats = get_stats(df_active[df_active['Type'].str.lower() == 'player'], 'Player/Team').set_index('Player/Team')
    t_stats = get_stats(df_active[df_active['Type'].str.lower() == 'team'], 'Team Name').set_index('Team Name')
    
    # 7-Game Min for Leaders/Ticker
    GAME_MIN = 7
    p_qualified = p_stats[p_stats['GP'] >= GAME_MIN] if not p_stats.empty else p_stats
    
    # Ticker (Qualified)
    leads = [f"🔥 {c}: {p_qualified.nlargest(1, f'{c}/G').index[0]} ({p_qualified.nlargest(1, f'{c}/G').iloc[0][f'{c}/G']})" for c in ['PTS', 'AST', 'REB', 'STL', 'BLK'] if not p_qualified.empty]
    st.markdown(f'<div class="ticker-wrap"><div class="ticker-content"><span class="ticker-item">{" • ".join(leads)}</span></div></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="header-banner">🏀 SPAM HUB - {sel_box.upper()}</div>', unsafe_allow_html=True)

    tabs = st.tabs(["👤 PLAYERS", "🏘️ STANDINGS", "🔝 LEADERS", "⚔️ VERSUS", "🏟️ POSTSEASON", "📖 RECORD BOOK", "🔐 THE VAULT"])

    # Locked Stats Columns
    locked_cols = ['GP', 'PTS/G', 'REB/G', 'AST/G', 'FGM/G', 'FGA/G', '3PM/G', '3PA/G', 'STL/G', 'BLK/G', 'TO/G', 'DD', 'TD']

    with tabs[0]:
        st.dataframe(p_stats[locked_cols].sort_values('PTS/G', ascending=False), width="stretch")
        l_avg_p = p_stats[['PTS/G', 'REB/G', 'AST/G', 'STL/G', 'BLK/G', 'FG%']].mean().round(2)
        st.markdown(f"""<div class="league-footer">PLAYER AVG: {l_avg_p['PTS/G']} PPG | {l_avg_p['REB/G']} RPG | {l_avg_p['AST/G']} APG | {l_avg_p['STL/G']} SPG | {l_avg_p['BLK/G']} BPG | {l_avg_p['FG%']}% FG</div>""", unsafe_allow_html=True)

    with tabs[1]:
        if not t_stats.empty:
            t_stats['Record'] = t_stats['Win'].astype(int).astype(str) + "-" + (t_stats['GP'] - t_stats['Win']).astype(int).astype(str)
            st.dataframe(t_stats.sort_values(['Win%', 'Win'], ascending=False)[['Record', 'PTS/G', 'REB/G', 'AST/G', 'FGM/G', 'FGA/G', 'STL/G', 'BLK/G', 'OffRtg', 'DefRtg']], width="stretch")
            l_avg_t = t_stats[['PTS/G', 'REB/G', 'AST/G', 'STL/G', 'BLK/G', 'FG%']].mean().round(2)
            st.markdown(f"""<div class="league-footer">TEAM AVG: {l_avg_t['PTS/G']} PPG | {l_avg_t['REB/G']} RPG | {l_avg_t['AST/G']} APG | {l_avg_t['STL/G']} SPG | {l_avg_t['BLK/G']} BPG | {l_avg_t['FG%']}% FG</div>""", unsafe_allow_html=True)

    with tabs[2]:
        l_cat = st.selectbox("Category", ["PTS/G", "REB/G", "AST/G", "STL/G", "BLK/G", "PIE"])
        t10 = p_qualified.nlargest(10, l_cat)[[l_cat]]
        st.dataframe(t10, width="stretch")
        st.plotly_chart(px.bar(t10, x=l_cat, y=t10.index, orientation='h', template="plotly_dark", color_discrete_sequence=['#d4af37']), use_container_width=True)

    with tabs[3]:
        v_mode = st.radio("Comparison Mode", ["Player vs Player", "Team vs Team"], horizontal=True)
        v1, mid, v2 = st.columns([2, 1, 2])
        v_metrics = ['PTS/G', 'REB/G', 'AST/G', 'STL/G', 'BLK/G', 'FG%', 'FGM/G', '3PM/G', 'TO/G', 'PIE']
        if v_mode == "Player vs Player":
            p1 = v1.selectbox("P1", p_stats.index, index=0); p2 = v2.selectbox("P2", p_stats.index, index=1); d1, d2 = p_stats.loc[p1], p_stats.loc[p2]
            v_avg = p_stats[v_metrics[:-1]].mean().round(2)
        else:
            p1 = v1.selectbox("T1", t_stats.index, index=0); p2 = v2.selectbox("T2", t_stats.index, index=1); d1, d2 = t_stats.loc[p1], t_stats.loc[p2]
            v_avg = t_stats[v_metrics[:-1]].mean().round(2)
        for s in v_metrics:
            c1, cm, c2 = st.columns([2, 1, 2])
            c1.metric(p1, d1[s]); c2.metric(p2, d2[s])
            if s in v_avg.index: cm.metric("AVG", v_avg[s])

    with tabs[4]:
        st.header("🏟️ POSTSEASON HUB")
        ps_view = st.radio("Tournament Mode", ["Playoffs (9000+)", "Tournaments (8000+)"], horizontal=True)
        cat_match = "Playoff" if "9000" in ps_view else "Tournament"
        ps_df = df_active[df_active['Game_Category'] == cat_match]
        if ps_df.empty: st.info(f"No {cat_match} games recorded.")
        else:
            ps_p = get_stats(ps_df[ps_df['Type'].str.lower() == 'player'], 'Player/Team').set_index('Player/Team')
            st.dataframe(ps_p[locked_cols], width="stretch")

    with tabs[5]:
        st.header("🏆 RECORD BOOK")
        hof_type = st.radio("Type", ["Players", "Teams"], horizontal=True)
        ent_col = 'Player/Team' if hof_type == "Players" else "Team Name"
        
        st.subheader("✨ Season Single-Game Highs")
        valid_active = df_active[(df_active['Type'].str.lower() == hof_type[:-1].lower()) & (df_active['is_ff'] == False)]
        h_cols = ['PTS', 'REB', 'AST', 'STL', 'BLK', '3PM']
        g1 = st.columns(6)
        for i, col in enumerate(h_cols):
            if not valid_active.empty:
                val = valid_active[col].max(); entity = valid_active.loc[valid_active[col].idxmax()][ent_col]
                g1[i].metric(f"{col}", f"{int(val)}", f"{entity}")

        st.divider()
        st.subheader("📜 All-Time Stat Leaders")
        hof_cat = st.selectbox("Stat", ['PTS', 'REB', 'AST', 'FGM', 'FGA', '3PM', '3PA', 'DD', 'TD', 'STL', 'BLK', 'TO', 'Win'])
        career_df = get_stats(full_df[full_df['Type'].str.lower() == hof_type[:-1].lower()], ent_col)
        if not career_df.empty:
            st.table(career_df.nlargest(15, hof_cat).reset_index(drop=True)[[ent_col, 'GP', hof_cat]])

    with tabs[6]:
        st.header("🔐 THE VAULT")
        if st.text_input("Passcode", type="password") == "SPAM2026":
            st.success("Access Granted.")
            
            # Hot/Cold Streaks (Restored)
            streaks = []
            for player in p_stats.index:
                p_games = df_active[(df_active['Player/Team'] == player) & (df_active['is_ff'] == False)]
                if len(p_games) >= 3:
                    avg_pts = p_stats.loc[player, 'PTS/G']; l3_avg = p_games.sort_values('Game_ID', ascending=False).head(3)['PTS'].mean()
                    if l3_avg > avg_pts * 1.20: streaks.append({"Entity": player, "Status": "🔥 HOT", "Trend": f"+{round(l3_avg - avg_pts, 1)} PPG"})
                    elif l3_avg < avg_pts * 0.80: streaks.append({"Entity": player, "Status": "❄️ COLD", "Trend": f"{round(l3_avg - avg_pts, 1)} PPG"})
            if streaks: st.write("**Momentum Tracker**"); st.table(pd.DataFrame(streaks))
            
            st.divider(); st.subheader("📊 Advanced Player Efficiency")
            st.dataframe(p_stats[['Poss/G', 'PPS', 'OffRtg', 'DefRtg', 'PIE']].sort_values('PIE', ascending=False), width="stretch")
            
            v_view = st.selectbox("Lab", ["Usage vs Error", "Inside vs Outside", "Impact Chart"])
            ap = p_stats.rename(columns={'FGM/G': 'FGM_G', '3PM/G': '3PM_G', 'Poss/G': 'Poss_G', 'TO/G': 'TO_G'})
            if v_view == "Usage vs Error": fig = px.scatter(ap, x='Poss_G', y='TO_G', size='AST/G', color=ap.index, template="plotly_dark")
            elif v_view == "Inside vs Outside": fig = px.scatter(ap, x='FGM_G', y='3PM_G', size='PTS/G', color=ap.index, template="plotly_dark")
            elif v_view == "Impact Chart": fig = px.scatter(ap, x='OffRtg', y='DefRtg', size='PIE', color=ap.index, template="plotly_dark"); fig.update_yaxes(autorange="reversed")
            st.plotly_chart(fig, use_container_width=True)

    st.markdown('<div style="text-align: center; color: #444; padding: 30px;">© 2026 SPAM LEAGUE HUB</div>', unsafe_allow_html=True)
