import streamlit as st
import pandas as pd
import plotly.express as px

# 1. UI & SLEEK CSS
st.set_page_config(page_title="SPAM LEAGUE CENTRAL", page_icon="🏀", layout="wide")

st.markdown("""
    <style>
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
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
        
        # Prevent "TOTAL" rows from skewing individual analytics
        df = df[~df['Player/Team'].astype(str).str.upper().str.contains('TOTAL')]
        df['is_ff'] = (df['PTS'] == 0) & (df['FGA'] == 0) & (df['REB'] == 0)
        
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
    
    # Initialize all mandatory columns with 0 to prevent KeyErrors
    mandatory_totals = ['PTS', 'REB', 'AST', 'STL', 'BLK', 'TO', '3PM', 'FGM', 'Win', 'DD', 'TD']
    for s in mandatory_totals:
        m[f'Total_{s}'] = m[s].astype(int) if s in m.columns else 0

    divisor = m['Played_GP'].replace(0, 1)
    avg_list = ['PTS', 'REB', 'AST', 'STL', 'BLK', 'TO', '3PM', '3PA', 'FTM', 'FTA', 'Poss_Raw', 'FGA', 'FGM', 'PIE_Raw']
    for a in avg_list:
        m[f'{a}/G'] = (m[a] / divisor).round(2) if a in m.columns else 0.0

    m['FG%'] = (m['FGM'] / m['FGA'].replace(0,1) * 100).round(2)
    m['TS%'] = (m['PTS'] / (2 * (m['FGA'] + 0.44 * m['FTA']).replace(0, 1)) * 100).round(2)
    m['PPS'] = (m['PTS'] / m['FGA'].replace(0, 1)).round(2)
    m['OffRtg'] = (m['PTS'] / m['Poss_Raw'].replace(0,1) * 100).round(1)
    m['DefRtg'] = (100 * (1 - ((m['STL'] + m['BLK'] + (m['REB'] * 0.7)) / m['Poss_Raw'].replace(0,1)))).round(1)
    m['PIE'] = m['PIE_Raw/G']
    m['Poss/G'] = m['Poss_Raw/G']
    
    m['Record'] = m['Total_Win'].astype(str) + "-" + (m['GP'] - m['Total_Win']).astype(str)
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

    # Ticker
    if not p_stats.empty:
        t_df = p_stats[p_stats['GP'] >= (p_stats['GP'].max() * 0.4)]
        leads = [f"🔥 {c}: {t_df.nlargest(1, f'{c}/G').index[0]} ({t_df.nlargest(1, f'{c}/G').iloc[0][f'{c}/G']})" for c in ['PTS', 'AST', 'REB', 'STL', 'BLK'] if not t_df.empty]
        st.markdown(f'<div class="ticker-wrap"><div class="ticker-content"><span class="ticker-item">{" • ".join(leads)}</span></div></div>', unsafe_allow_html=True)
    
    st.markdown(f'<div class="header-banner">🏀 SPAM HUB - {sel_box.upper()}</div>', unsafe_allow_html=True)

    tabs = st.tabs(["👤 PLAYERS", "🏘️ STANDINGS", "🔝 LEADERS", "⚔️ VERSUS", "🏆 POSTSEASON", "📖 HALL OF FAME", "🔐 THE VAULT"])

    with tabs[1]: # STANDINGS
        if not t_stats.empty:
            cols = ['Record', 'GP', 'PTS/G', 'AST/G', 'REB/G', 'Total_PTS', 'Total_AST', 'Total_REB', 'OffRtg', 'DefRtg', 'PIE']
            # Re-ensure columns exist just in case
            display_cols = [c for c in cols if c in t_stats.columns]
            st.dataframe(t_stats[display_cols].sort_values('Total_Win', ascending=False), width="stretch")

    with tabs[4]: # POSTSEASON
        p_mode = st.radio("Bracket", ["Playoffs (9000s)", "Tournament (8000s)"], horizontal=True)
        p_start = 9000 if "Playoffs" in p_mode else 8000
        p_data = df_active[(df_active['Game_ID'] >= p_start) & (df_active['Game_ID'] < p_start + 1000)]
        if p_data.empty: st.info("No Postseason data found.")
        else:
            ps_p = get_stats(p_data[p_data['Type'].str.lower() == 'player'], 'Player/Team').set_index('Player/Team')
            # Custom column selection per user images
            target_cols = ['PTS/G', 'REB/G', 'AST/G', 'STL/G', 'BLK/G', 'TO/G', '3PM/G', '3PA/G', 'FTM/G', 'FTA/G', 'Poss_Raw/G', 'FGA/G', 'FGM/G', 'PIE_Raw/G', 'FG%', 'TS%', 'PPS', 'OffRtg', 'DefRtg', 'PIE', 'Poss/G']
            # Ensure only existing columns are selected
            final_cols = [c for c in target_cols if c in ps_p.columns]
            st.dataframe(ps_p[final_cols].sort_values('PIE', ascending=False), width="stretch")

    with tabs[5]: # HALL OF FAME
        st.header("📖 HALL OF FAME")
        hof_type = st.radio("Highs For:", ["Players", "Teams"], horizontal=True)
        type_key = hof_type[:-1].lower()
        valid_hof = full_df[(full_df['Type'].str.lower() == type_key) & (full_df['is_ff'] == False)]
        
        if not valid_hof.empty:
            h_grid = st.columns(4)
            for i, col in enumerate(['PTS', 'REB', 'AST', 'STL', 'BLK', '3PM', 'TO', 'FGM']):
                val = valid_hof[col].max()
                if not pd.isna(val):
                    row = valid_hof.loc[valid_hof[col].idxmax()]
                    h_grid[i%4].metric(f"{col} Record", f"{int(val)}", f"by {row['Player/Team' if hof_type == 'Players' else 'Team Name']}")
        else: st.warning("No data found for records.")

    with tabs[6]: # THE VAULT
        if st.text_input("Passcode", type="password") == "SPAM2026":
            st.success("Access Granted.")
            adv = p_stats[p_stats['Played_GP'] > 0].reset_index().copy()
            if not adv.empty:
                v_view = st.selectbox("Analytics View", ["Vol vs Eff", "Eff Hub", "Poss Control", "Off vs Def"])
                # Map columns specifically for scatter plots based on images
                ap = adv.rename(columns={'FGA/G': 'FGA_G', 'PTS/G': 'PTS_G', 'Poss/G': 'Poss_G', 'TO/G': 'TO_G'})
                if v_view == "Vol vs Eff": fig = px.scatter(ap, x='FGA_G', y='PTS_G', size='PIE', color='Player/Team', template="plotly_dark")
                elif v_view == "Eff Hub": fig = px.scatter(ap, x='PPS', y='TS%', size='PTS_G', color='Player/Team', template="plotly_dark")
                elif v_view == "Off vs Def": fig = px.scatter(ap, x='OffRtg', y='DefRtg', size='PIE', color='Player/Team', template="plotly_dark"); fig.update_yaxes(autorange="reversed")
                st.plotly_chart(fig, use_container_width=True)

    st.markdown('<div style="text-align: center; color: #444; padding: 30px;">© 2026 SPAM LEAGUE HUB</div>', unsafe_allow_html=True)
