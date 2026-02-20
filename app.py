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
    if dataframe.empty: return pd.DataFrame()
    total_gp = dataframe.groupby(group).size().reset_index(name='GP')
    played_df = dataframe[dataframe['is_ff'] == False]
    played_gp = played_df.groupby(group).size().reset_index(name='Played_GP')
    
    sums = dataframe.groupby(group).sum(numeric_only=True).reset_index()
    m = pd.merge(sums, total_gp, on=group)
    m = pd.merge(m, played_gp, on=group, how='left').fillna(0)
    
    # Career/Season Totals
    for col in ['PTS', 'REB', 'AST', 'STL', 'BLK', 'TO', '3PM', '3PA', 'FGM', 'FGA', 'Win', 'DD', 'TD']:
        m[f'Total_{col}'] = m[col].astype(int)
    
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
    opts = ["CAREER STATS"] + [f"Season {int(s)}" for s in seasons]
    with st.sidebar: sel_box = st.selectbox("Scope", opts, index=1)
    df_active = full_df if sel_box == "CAREER STATS" else full_df[full_df['Season'] == int(sel_box.replace("Season ", ""))]

    df_reg = df_active[~df_active['Game_ID'].between(8000, 9999)]
    p_stats = get_stats(df_reg[df_reg['Type'].str.lower() == 'player'], 'Player/Team').set_index('Player/Team')
    t_stats = get_stats(df_reg[df_reg['Type'].str.lower() == 'team'], 'Team Name').set_index('Team Name')

    # Ticker Game Min Fix
    if not p_stats.empty:
        ticker_gp_min = p_stats['GP'].max() * 0.4
        ticker_df = p_stats[p_stats['GP'] >= ticker_gp_min]
        if not ticker_df.empty:
            leads = [f"🔥 {c}: {ticker_df.nlargest(1, f'{c}/G').index[0]} ({ticker_df.nlargest(1, f'{c}/G').iloc[0][f'{c}/G']})" for c in ['PTS', 'AST', 'REB', 'STL', 'BLK']]
            st.markdown(f'<div class="ticker-wrap"><div class="ticker-content"><span class="ticker-item">{" • ".join(leads)}</span></div></div>', unsafe_allow_html=True)
    
    st.markdown(f'<div class="header-banner">🏀 SPAM HUB - {sel_box.upper()}</div>', unsafe_allow_html=True)

    tabs = st.tabs(["👤 PLAYERS", "🏘️ STANDINGS", "🔝 LEADERS", "⚔️ VERSUS", "🏆 POSTSEASON", "📖 HALL OF FAME", "🔐 THE VAULT"])

    with tabs[2]: # LEADERS TAB
        gp_leader_val = p_stats['GP'].max()
        min_gp = gp_leader_val * 0.4
        st.caption(f"Qualified Leaders (Min {min_gp:.1f} Games Played)")
        filt_p = p_stats[p_stats['GP'] >= min_gp]
        l_cat = st.selectbox("Category", ["PTS/G", "REB/G", "AST/G", "STL/G", "BLK/G", "3PM/G", "FGM/G", "TO/G", "PIE"])
        t10 = filt_p.nlargest(10, l_cat)[[l_cat, 'GP', 'FG%', 'TS%', 'FGA/G', '3PA/G']]
        st.dataframe(t10, width="stretch")

    with tabs[4]: # POSTSEASON TAB
        st.header("🏆 POSTSEASON BRACKETOLOGY")
        p_mode = st.radio("Postseason Scope", ["Playoffs (9000s)", "Tournament (8000s)"], horizontal=True)
        range_start = 9000 if "Playoffs" in p_mode else 8000
        p_data = df_active[(df_active['Game_ID'] >= range_start) & (df_active['Game_ID'] < range_start + 1000)]
        
        if p_data.empty: st.info(f"No {p_mode} data found.")
        else:
            ps_stats = get_stats(p_data[p_data['Type'].str.lower() == 'player'], 'Player/Team').set_index('Player/Team')
            st.subheader(f"{p_mode} Player Analytics")
            st.dataframe(ps_stats.sort_values('PIE', ascending=False), width="stretch")
            
            st.divider()
            st.subheader("🔥 Single Game Records")
            ph_grid = st.columns(5)
            for i, col in enumerate(['PTS', 'REB', 'AST', 'STL', 'BLK']):
                val = p_data[col].max(); row = p_data.loc[p_data[col].idxmax()]
                ph_grid[i].metric(f"{col}", f"{int(val)}", f"by {row['Player/Team']}")

    with tabs[5]: # HALL OF FAME / MILESTONES
        st.header("📖 HALL OF FAME")
        st.subheader("🎯 Milestone Tracker")
        career_p = get_stats(full_df[full_df['Type'].str.lower() == 'player'], 'Player/Team').set_index('Player/Team')
        
        # Increment Dictionary
        inc = {"Total_PTS": 250, "Total_AST": 100, "Total_REB": 150, "Total_STL": 25, "Total_BLK": 10, 
               "Total_TD": 10, "Total_DD": 10, "Total_3PM": 50, "Total_FGM": 100, "Total_Win": 100}
        
        m_sel = st.selectbox("Milestone Category", list(inc.keys()))
        val_inc = inc[m_sel]
        
        career_p['Level'] = (career_p[m_sel] // val_inc) * val_inc
        career_p['Progress'] = career_p[m_sel] % val_inc
        ms_view = career_p[career_p[m_sel] >= val_inc].sort_values(m_sel, ascending=False)
        st.table(ms_view[[m_sel, 'Level']])

    with tabs[6]: # THE VAULT (RESTORED ORIGINAL)
        st.header("🔐 THE VAULT")
        if st.text_input("Passcode", type="password") == "SPAM2026":
            st.success("Access Granted.")
            adv = p_stats[p_stats['Played_GP'] > 0].reset_index().copy()
            if not adv.empty:
                st.markdown("### 📊 Advanced Analytics")
                st.dataframe(adv[['Player/Team', 'Poss/G', 'PPS', 'TS%', 'FGM/G', 'FGA/G', '3PM/G', '3PA/G', 'OffRtg', 'DefRtg', 'PIE']].sort_values('OffRtg', ascending=False), width="stretch", hide_index=True)
                v_view = st.selectbox("View", ["Vol vs Eff", "Eff Hub", "Poss Control", "Splits", "Off vs Def"])
                ap = adv.rename(columns={'FGA/G': 'FGA_G', 'PTS/G': 'PTS_G', 'Poss/G': 'Poss_G', 'TO/G': 'TO_G', 'FGM/G': 'FGM_G', '3PM/G': '3PM_G'})
                if v_view == "Vol vs Eff": fig = px.scatter(ap, x='FGA_G', y='PTS_G', size='PIE', color='Player/Team', template="plotly_dark")
                elif v_view == "Eff Hub": fig = px.scatter(ap, x='PPS', y='TS%', size='PTS_G', color='Player/Team', template="plotly_dark")
                elif v_view == "Poss Control": fig = px.scatter(ap, x='Poss_G', y='TO_G', size='AST/G', color='Player/Team', template="plotly_dark")
                elif v_view == "Splits": fig = px.scatter(ap, x='FGM_G', y='3PM_G', size='PTS_G', color='Player/Team', template="plotly_dark")
                elif v_view == "Off vs Def": fig = px.scatter(ap, x='OffRtg', y='DefRtg', size='PIE', color='Player/Team', template="plotly_dark"); fig.update_yaxes(autorange="reversed")
                st.plotly_chart(fig, use_container_width=True)
            
            st.divider(); st.subheader("📅 Season Totals Archive")
            st.dataframe(p_stats.filter(like='Total_'), width="stretch")

    st.markdown('<div style="text-align: center; color: #444; padding: 30px;">© 2026 SPAM LEAGUE HUB</div>', unsafe_allow_html=True)
