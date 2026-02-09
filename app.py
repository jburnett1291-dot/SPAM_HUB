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

# 2. DATA ENGINE (FIXED FOR FF RECORD REFLECTION)
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
        
        # Identify FF: Rows where core stats are 0 (indicates forfeit)
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
    # 4. FILTERS
    seasons = sorted(full_df['Season'].unique(), reverse=True)
    opts = ["CAREER STATS"] + [f"Season {int(s)}" for s in seasons]
    with st.sidebar: sel_box = st.selectbox("League Scope", opts, index=1)
    df_active = full_df if sel_box == "CAREER STATS" else full_df[full_df['Season'] == int(sel_box.replace("Season ", ""))]

    def get_stats(dataframe, group):
        # FIX: Ensure GP counts every row (including FF)
        total_gp = dataframe.groupby(group).size().reset_index(name='GP')
        # Stats only for games actually played
        played_df = dataframe[dataframe['is_ff'] == False]
        played_gp = played_df.groupby(group).size().reset_index(name='Played_GP')
        
        sums = dataframe.groupby(group).sum(numeric_only=True).reset_index()
        m = pd.merge(sums, total_gp, on=group)
        m = pd.merge(m, played_gp, on=group, how='left').fillna(0)
        
        divisor = m['Played_GP'].replace(0, 1)
        for col in ['PTS', 'REB', 'AST', 'STL', 'BLK', 'TO', '3PM', '3PA', 'FTM', 'FTA', 'Poss']:
            m[f'{col}/G'] = (m[col] / divisor).round(2)
            
        m['FG%'] = (m['FGM'] / m['FGA'].replace(0,1) * 100).round(2)
        m['3P%'] = (m['3PM'] / m['3PA'].replace(0,1) * 100).round(2)
        m['FT%'] = (m['FTM'] / m['FTA'].replace(0,1) * 100).round(2)
        m['PIE'] = (m['PIE'] / divisor).round(2)
        return m

    p_stats = get_stats(df_active[df_active['Type'].str.lower() == 'player'], 'Player/Team').set_index('Player/Team')
    t_stats = get_stats(df_active[df_active['Type'].str.lower() == 'team'], 'Team Name').set_index('Team Name')

    # 5. TICKER
    leads = [f"🔥 {c}: {p_stats.nlargest(1, f'{c}/G').index[0]} ({p_stats.nlargest(1, f'{c}/G').iloc[0][f'{c}/G']})" for c in ['PTS', 'AST', 'REB', 'STL', 'BLK']]
    st.markdown(f'<div class="ticker-wrap"><div class="ticker-content"><span class="ticker-item">{" • ".join(leads)}</span></div></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="header-banner">🏀 SPAM HUB - {sel_box.upper()}</div>', unsafe_allow_html=True)

    tabs = st.tabs(["👤 PLAYERS", "🏘️ STANDINGS", "🔝 LEADERS", "⚔️ VERSUS", "📖 HALL OF FAME", "🔐 THE VAULT"])

    with tabs[0]: # PLAYERS
        p_disp = p_stats[['GP', 'PTS/G', 'REB/G', 'AST/G', 'FG%', 'PIE']].sort_values('PIE', ascending=False)
        sel_p = st.dataframe(p_disp, width="stretch", on_select="rerun", selection_mode="single-row")
        if len(sel_p.selection.rows) > 0: show_card(p_disp.index[sel_p.selection.rows[0]], p_stats, df_active, True)

    with tabs[1]: # STANDINGS (FIXED FOR FF REFLECTION)
        t_stats['Record'] = t_stats['Win'].astype(int).astype(str) + "-" + (t_stats['GP'] - t_stats['Win']).astype(int).astype(str)
        t_disp = t_stats.sort_values('Win', ascending=False)[['Record', 'PTS/G', 'REB/G', 'FG%']]
        sel_t = st.dataframe(t_disp, width="stretch", on_select="rerun", selection_mode="single-row")
        if len(sel_t.selection.rows) > 0: show_card(t_disp.index[sel_t.selection.rows[0]], t_stats, df_active, False)

    with tabs[2]: # LEADERS
        l_cat = st.selectbox("Category", ["PTS/G", "REB/G", "AST/G", "STL/G", "BLK/G", "TO/G", "PIE"])
        t10 = p_stats.nlargest(10, l_cat)[[l_cat]]
        st.dataframe(t10, width="stretch")
        fig = px.bar(t10, x=l_cat, y=t10.index, orientation='h', template="plotly_dark", color_discrete_sequence=['#d4af37'])
        fig.update_layout(yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig, width="stretch")

    with tabs[3]: # VERSUS
        v1, v2 = st.columns(2)
        p1 = v1.selectbox("P1", p_stats.index, index=0); p2 = v2.selectbox("P2", p_stats.index, index=1)
        d1, d2 = p_stats.loc[p1], p_stats.loc[p2]
        for s in ['PTS/G', 'REB/G', 'AST/G', 'STL/G', 'BLK/G', 'TO/G', 'FG%', 'PIE']:
            c1, c2 = st.columns(2)
            c1.metric(f"{p1} {s}", d1[s], round(d1[s]-d2[s], 2)); c2.metric(f"{p2} {s}", d2[s], round(d2[s]-d1[s], 2))

    with tabs[4]: # HALL OF FAME
        st.header("🏆 HALL OF FAME RECORD BOOK")
        hof_type = st.radio("Record Type", ["Players", "Teams"], horizontal=True)
        h_cols = ['PTS', 'REB', 'AST', 'STL', 'BLK', '3PM', 'TO']
        valid_games = full_df[(full_df['Type'].str.lower() == hof_type[:-1].lower()) & (full_df['is_ff'] == False)]
        st.subheader(f"🔥 {hof_type} Single Game Season Highs")
        grid = st.columns(4)
        for i, col in enumerate(h_cols):
            if not valid_games.empty:
                val = valid_games[col].max()
                name_col = 'Player/Team' if hof_type == "Players" else 'Team Name'
                holder = valid_games.loc[valid_games[col].idxmax()][name_col]
                grid[i%4].metric(f"Record: {col}", f"{int(val)}", f"by {holder}")
        st.divider()
        cat_hof = st.selectbox("All-Time Category", ['PTS', 'REB', 'AST', 'STL', 'BLK', 'TO', '3PM', 'DD', 'TD', 'GP', 'Win'])
        career_df = get_stats(full_df[full_df['Type'].str.lower() == hof_type[:-1].lower()], 'Player/Team' if hof_type == "Players" else "Team Name")
        st.table(career_df.nlargest(10, cat_hof).reset_index(drop=True)[[career_df.columns[0], 'GP', cat_hof]])

    with tabs[5]: # THE VAULT
        st.header("🔐 THE VAULT")
        if st.text_input("Passcode", type="password") == "SPAM2026":
            st.success("Access Granted.")
            st.markdown("### 🧪 Advanced Stats")
            adv = p_stats[p_stats['Played_GP'] > 0].reset_index().copy()
            if not adv.empty:
                adv['TS%'] = (adv['PTS'] / (2 * (adv['FGA'] + 0.44 * adv['FTA']).replace(0, 1)) * 100).round(2)
                adv['PPS'] = (adv['PTS'] / adv['FGA'].replace(0, 1)).round(2)
                st.dataframe(adv[['Player/Team', 'Poss/G', 'TS%', 'PPS', 'PIE']], width="stretch", hide_index=True)
                fig_v = px.scatter(adv, x='FGA/G', y='PTS/G', size='Poss/G', color='Player/Team', template="plotly_dark")
                st.plotly_chart(fig_v, use_container_width=True)
            
            st.markdown("### 🔥 Streak Tracker")
            streaks = []
            for player in p_stats.index:
                p_games = df_active[(df_active['Player/Team'] == player) & (df_active['is_ff'] == False)]
                if len(p_games) >= 3:
                    avg_pts = p_stats.loc[player, 'PTS/G']
                    l3_avg = p_games.sort_values('Game_ID', ascending=False).head(3)['PTS'].mean()
                    if l3_avg > avg_pts * 1.20: streaks.append({"Entity": player, "Status": "🔥 HOT", "Trend": f"+{round(l3_avg - avg_pts, 1)} PPG"})
                    elif l3_avg < avg_pts * 0.80: streaks.append({"Entity": player, "Status": "❄️ COLD", "Trend": f"{round(l3_avg - avg_pts, 1)} PPG"})
            if streaks: st.table(pd.DataFrame(streaks))

    st.markdown('<div style="text-align: center; color: #444; padding: 30px;">© 2026 SPAM LEAGUE HUB</div>', unsafe_allow_html=True)
