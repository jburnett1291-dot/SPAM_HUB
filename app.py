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
        def calc_multis(row):
            if row['is_ff']: return pd.Series([0, 0])
            s = [row['PTS'], row['REB'], row['AST'], row['STL'], row['BLK']]
            tens = sum(1 for x in s if x >= 10)
            return pd.Series([1 if tens >= 2 else 0, 1 if tens >= 3 else 0])
        df[['DD', 'TD']] = df.apply(calc_multis, axis=1)
        df['PIE_Raw'] = (df['PTS'] + df['REB'] + df['AST'] + df['STL'] + df['BLK']) - (df['FGA'] * 0.5) - df['TO']
        df['Poss_Raw'] = df['FGA'] + 0.44 * df['FTA'] + df['TO']
        df['FG%_Raw'] = (df['FGM'] / df['FGA'].replace(0,1) * 100).round(1)
        return df
    except Exception as e: return str(e)

full_df = load_data()

# 3. STATS LOGIC
def get_stats(dataframe, group):
    total_gp = dataframe.groupby(group).size().reset_index(name='GP')
    played_df = dataframe[dataframe['is_ff'] == False]
    played_gp = played_df.groupby(group).size().reset_index(name='Played_GP')
    sums = dataframe.groupby(group).sum(numeric_only=True).reset_index()
    m = pd.merge(sums, total_gp, on=group)
    m = pd.merge(m, played_gp, on=group, how='left').fillna(0)
    divisor = m['Played_GP'].replace(0, 1)
    for col in ['PTS', 'REB', 'AST', 'STL', 'BLK', 'TO', '3PM', '3PA', 'FTM', 'FTA', 'Poss_Raw', 'FGA', 'FGM', 'PIE_Raw']:
        m[f'{col}/G'] = (m[col] / divisor).round(2)
    m['FG%'] = (m['FGM'] / m['FGA'].replace(0,1) * 100).round(2)
    m['TS%'] = (m['PTS'] / (2 * (m['FGA'] + 0.44 * m['FTA']).replace(0, 1)) * 100).round(2)
    m['PPS'] = (m['PTS'] / m['FGA'].replace(0, 1)).round(2)
    m['OffRtg'] = (m['PTS'] / m['Poss_Raw'].replace(0,1) * 100).round(1)
    # AUTHENTIC DEF RTG: 100 * (1 - (STL + BLK + (REB * 0.7)) / Possessions)
    m['DefRtg'] = (100 * (1 - ((m['STL'] + m['BLK'] + (m['REB'] * 0.7)) / m['Poss_Raw'].replace(0,1)))).round(1)
    m['PIE'] = m['PIE_Raw/G']
    m['Poss/G'] = m['Poss_Raw/G']
    return m

# 4. DIALOG CARDS
@st.dialog("🏀 SCOUTING REPORT", width="large")
def show_card(name, stats_df, raw_df, is_player=True):
    row = stats_df.loc[name]
    st.title(f"{'👤' if is_player else '🏘️'} {name}")
    c = st.columns(5); c[0].metric("PPG", row['PTS/G']); c[1].metric("RPG", row['REB/G']); c[2].metric("APG", row['AST/G']); c[3].metric("SPG", row['STL/G']); c[4].metric("BPG", row['BLK/G'])
    st.markdown("---"); st.subheader("🏆 Season Highs")
    s_col = 'Player/Team' if is_player else 'Team Name'
    personal = raw_df[(raw_df[s_col] == name) & (raw_df['Type'].str.lower() == ('player' if is_player else 'team'))]
    h = st.columns(5); h[0].metric("Max PTS", int(personal['PTS'].max() if not personal.empty else 0)); h[1].metric("Max REB", int(personal['REB'].max() if not personal.empty else 0)); h[2].metric("Max AST", int(personal['AST'].max() if not personal.empty else 0)); h[3].metric("Max STL", int(personal['STL'].max() if not personal.empty else 0)); h[4].metric("Max BLK", int(personal['BLK'].max() if not personal.empty else 0))
    st.markdown("---"); st.subheader("🕒 Recent Form")
    recent = personal.sort_values(['Season', 'Game_ID'], ascending=False).head(3)
    for _, g in recent.iterrows():
        res = "✅ W" if g['Win'] == 1 else "❌ L"
        label = f"Game {int(g['Game_ID'])} | {res}"
        if g['is_ff']: st.info(f"{label} - FORFEIT")
        else:
            f = st.columns(6); f[0].metric(f"{label}", f"{int(g['PTS'])} PTS"); f[1].metric("REB", int(g['REB'])); f[2].metric("AST", int(g['AST'])); f[3].metric("STL", int(g['STL'])); f[4].metric("BLK", int(g['BLK'])); f[5].metric("FG%", f"{g['FG%_Raw']}%")
    if st.button("Close Card & Clear Selection", use_container_width=True): st.rerun()

# 5. APP CONTENT
if isinstance(full_df, str): st.error(f"⚠️ DATA ERROR: {full_df}")
elif full_df is not None:
    seasons = sorted(full_df['Season'].unique(), reverse=True)
    opts = ["CAREER STATS"] + [f"Season {int(s)}" for s in seasons]
    with st.sidebar: sel_box = st.selectbox("Scope", opts, index=1)
    df_active = full_df if sel_box == "CAREER STATS" else full_df[full_df['Season'] == int(sel_box.replace("Season ", ""))]

    p_stats = get_stats(df_active[df_active['Type'].str.lower() == 'player'], 'Player/Team').set_index('Player/Team')
    t_stats = get_stats(df_active[df_active['Type'].str.lower() == 'team'], 'Team Name').set_index('Team Name')

    leads = [f"🔥 {c}: {p_stats.nlargest(1, f'{c}/G').index[0]} ({p_stats.nlargest(1, f'{c}/G').iloc[0][f'{c}/G']})" for c in ['PTS', 'AST', 'REB', 'STL', 'BLK']]
    st.markdown(f'<div class="ticker-wrap"><div class="ticker-content"><span class="ticker-item">{" • ".join(leads)}</span></div></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="header-banner">🏀 SPAM HUB - {sel_box.upper()}</div>', unsafe_allow_html=True)

    tabs = st.tabs(["👤 PLAYERS", "🏘️ STANDINGS", "🔝 LEADERS", "⚔️ VERSUS", "📖 HALL OF FAME", "🔐 THE VAULT"])

    with tabs[0]:
        p_disp = p_stats[['GP', 'PTS/G', 'REB/G', 'AST/G', 'FG%', 'TO/G', 'PIE']].sort_values('PIE', ascending=False)
        sel_p = st.dataframe(p_disp, width="stretch", on_select="rerun", selection_mode="single-row")
        if len(sel_p.selection.rows) > 0: show_card(p_disp.index[sel_p.selection.rows[0]], p_stats, df_active, True)

    with tabs[1]:
        t_stats['Record'] = t_stats['Win'].astype(int).astype(str) + "-" + (t_stats['GP'] - t_stats['Win']).astype(int).astype(str)
        t_disp = t_stats.sort_values('Win', ascending=False)[['Record', 'PTS/G', 'REB/G', 'AST/G', 'TO/G', 'FG%']]
        sel_t = st.dataframe(t_disp, width="stretch", on_select="rerun", selection_mode="single-row")
        if len(sel_t.selection.rows) > 0: show_card(t_disp.index[sel_t.selection.rows[0]], t_stats, df_active, False)

    with tabs[2]:
        l_cat = st.selectbox("Category", ["PTS/G", "REB/G", "AST/G", "STL/G", "BLK/G", "TO/G", "PIE"])
        t10 = p_stats.nlargest(10, l_cat)[[l_cat]]
        st.dataframe(t10, width="stretch"); st.plotly_chart(px.bar(t10, x=l_cat, y=t10.index, orientation='h', template="plotly_dark", color_discrete_sequence=['#d4af37']), width="stretch")

    with tabs[3]:
        v_mode = st.radio("Comparison Mode", ["Player vs Player", "Team vs Team"], horizontal=True)
        v1, v2 = st.columns(2)
        if v_mode == "Player vs Player":
            p1 = v1.selectbox("P1", p_stats.index, index=0); p2 = v2.selectbox("P2", p_stats.index, index=1); d1, d2 = p_stats.loc[p1], p_stats.loc[p2]
            metrics = ['PTS/G', 'REB/G', 'AST/G', 'STL/G', 'BLK/G', 'TO/G', 'FG%', 'PIE']
        else:
            p1 = v1.selectbox("T1", t_stats.index, index=0); p2 = v2.selectbox("T2", t_stats.index, index=1); d1, d2 = t_stats.loc[p1], t_stats.loc[p2]
            metrics = ['Record', 'PTS/G', 'REB/G', 'AST/G', 'TO/G', 'FG%', 'OffRtg', 'DefRtg']
        for s in metrics:
            c1, c2 = st.columns(2)
            if s == 'Record': c1.metric(f"{p1} {s}", d1[s]); c2.metric(f"{p2} {s}", d2[s])
            else: c1.metric(f"{p1} {s}", d1[s], round(d1[s]-d2[s], 2)); c2.metric(f"{p2} {s}", d2[s], round(d2[s]-d1[s], 2))

    with tabs[4]:
        st.header("🏆 HALL OF FAME"); hof_type = st.radio("Type", ["Players", "Teams"], horizontal=True); h_cols = ['PTS', 'REB', 'AST', 'STL', 'BLK', '3PM', 'TO']; valid_games = df_active[(df_active['Type'].str.lower() == hof_type[:-1].lower()) & (df_active['is_ff'] == False)]
        grid = st.columns(4)
        for i, col in enumerate(h_cols):
            if not valid_games.empty: val = valid_games[col].max(); grid[i%4].metric(f"Record: {col}", f"{int(val)}", f"by {valid_games.loc[valid_games[col].idxmax()]['Player/Team' if hof_type == 'Players' else 'Team Name']}")
        st.divider(); cat_hof = st.selectbox("All-Time", ['PTS', 'REB', 'AST', 'STL', 'BLK', 'TO', '3PM', 'DD', 'TD', 'GP', 'Win']); career_df = get_stats(full_df[full_df['Type'].str.lower() == hof_type[:-1].lower()], 'Player/Team' if hof_type == "Players" else "Team Name")
        st.table(career_df.nlargest(10, cat_hof).reset_index(drop=True)[[career_df.columns[0], 'GP', cat_hof]])

    with tabs[5]:
        st.header("🔐 THE VAULT")
        if st.text_input("Passcode", type="password") == "SPAM2026":
            st.success("Access Granted.")
            adv = p_stats[p_stats['Played_GP'] > 0].reset_index().copy()
            if not adv.empty:
                st.markdown("### 📊 Advanced Analytics")
                st.dataframe(adv[['Player/Team', 'Poss/G', 'PPS', 'TS%', 'FGM/G', 'FGA/G', '3PM/G', '3PA/G', 'OffRtg', 'DefRtg', 'PIE']].sort_values('OffRtg', ascending=False), width="stretch", hide_index=True)
                st.markdown("---"); st.markdown("### 🧪 Analysis Visualizer")
                v_view = st.selectbox("View", ["Vol vs Eff", "Eff Hub", "Poss Control", "Splits", "Off vs Def"])
                ap = adv.rename(columns={'FGA/G': 'FGA_G', 'PTS/G': 'PTS_G', 'Poss/G': 'Poss_G', 'TO/G': 'TO_G', 'FGM/G': 'FGM_G', '3PM/G': '3PM_G'})
                if v_view == "Vol vs Eff": fig = px.scatter(ap, x='FGA_G', y='PTS_G', size='PIE', color='Player/Team', template="plotly_dark")
                elif v_view == "Eff Hub": fig = px.scatter(ap, x='PPS', y='TS%', size='PTS_G', color='Player/Team', template="plotly_dark")
                elif v_view == "Poss Control": fig = px.scatter(ap, x='Poss_G', y='TO_G', size='AST/G', color='Player/Team', template="plotly_dark")
                elif v_view == "Splits": fig = px.scatter(ap, x='FGM_G', y='3PM_G', size='PTS_G', color='Player/Team', template="plotly_dark")
                elif v_view == "Off vs Def": fig = px.scatter(ap, x='OffRtg', y='DefRtg', size='PIE', color='Player/Team', template="plotly_dark"); fig.update_yaxes(autorange="reversed")
                st.plotly_chart(fig, use_container_width=True)
            st.divider(); streaks = []
            for player in p_stats.index:
                p_games = df_active[(df_active['Player/Team'] == player) & (df_active['is_ff'] == False)]
                if len(p_games) >= 3:
                    avg_pts = p_stats.loc[player, 'PTS/G']; l3_avg = p_games.sort_values('Game_ID', ascending=False).head(3)['PTS'].mean()
                    if l3_avg > avg_pts * 1.20: streaks.append({"Entity": player, "Status": "🔥 HOT", "Trend": f"+{round(l3_avg - avg_pts, 1)} PPG"})
                    elif l3_avg < avg_pts * 0.80: streaks.append({"Entity": player, "Status": "❄️ COLD", "Trend": f"{round(l3_avg - avg_pts, 1)} PPG"})
            if streaks: st.table(pd.DataFrame(streaks))

    st.markdown('<div style="text-align: center; color: #444; padding: 30px;">© 2026 SPAM LEAGUE HUB</div>', unsafe_allow_html=True)
