import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path

# 1. UI CONFIG & SCROLL-FREE CSS
st.set_page_config(page_title="SPAM LEAGUE CENTRAL", page_icon="🏀", layout="wide")

st.markdown("""
    <style>
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    div[data-testid="stToolbar"] {visibility: hidden;} [data-testid="stStatusWidget"] {display: none;}
    
    /* REMOVE ALL PADDING & PREVENT SCROLLING ON SPLASH */
    .block-container { padding: 0rem !important; }
    html, body, [data-testid="stAppViewContainer"] { height: 100vh; overflow: hidden; }
    
    .stApp { background: radial-gradient(circle, #1a1a1a 0%, #050505 100%); color: #d4af37; }
    
    /* VERTICAL & HORIZONTAL CENTERING */
    .splash-wrapper {
        display: flex; flex-direction: column; align-items: center; justify-content: center;
        height: 100vh; width: 100vw; text-align: center;
    }

    [data-testid="stMetric"] { background: rgba(255, 255, 255, 0.03) !important; border-left: 6px solid #d4af37 !important; border-radius: 12px !important; padding: 22px !important; }
    .header-banner { padding: 20px; text-align: center; background: #d4af37; border-bottom: 5px solid #000; color: #000; font-family: 'Arial Black'; font-size: 28px; }
    
    @keyframes ticker { 0% { transform: translateX(100%); } 100% { transform: translateX(-100%); } }
    .ticker-wrap { width: 100%; overflow: hidden; background: #000; color: #d4af37; padding: 12px 0; font-family: 'Arial Black'; border-bottom: 2px solid #d4af37; }
    .ticker-content { display: inline-block; white-space: nowrap; animation: ticker 65s linear infinite; }
    .ticker-item { display: inline-block; margin-right: 80px; font-size: 18px; }
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
        
        # REQUIRED COLUMN SAFETY
        for c in ['PTS', 'REB', 'AST', 'STL', 'BLK', 'FGA', 'Game_ID', 'Win']:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)
            else:
                df[c] = 0
        
        df['PIE'] = (df['PTS'] + df['REB'] + df['AST'] + df['STL'] + df['BLK']) - (df.get('FGA', 0) * 0.5)
        
        # FILTER BY TYPE COLUMN
        df_p = df[df['Type'].str.lower() == 'player'].copy()
        df_t = df[df['Type'].str.lower() == 'team'].copy()
        
        # PLAYER AVERAGES
        gp = df_p.groupby('Player/Team')['Game_ID'].nunique().reset_index(name='GP')
        p_avg = pd.merge(df_p.groupby(['Player/Team', 'Team Name']).sum(numeric_only=True).reset_index(), gp, on='Player/Team')
        for s in ['PTS', 'REB', 'AST', 'STL', 'BLK']:
            p_avg[f'{s}/G'] = (p_avg[s] / p_avg['GP']).round(1)
        
        # TEAM STANDINGS (Aggregating Team Rows)
        t_stats = df_t.groupby('Team Name').agg({
            'Win': 'sum', 'Game_ID': 'count', 'PTS': 'sum', 'REB': 'sum', 'AST': 'sum', 'STL': 'sum', 'BLK': 'sum'
        }).reset_index()
        t_stats['Loss'] = (t_stats['Game_ID'] - t_stats['Win']).astype(int)
        t_stats['Record'] = t_stats['Win'].astype(int).astype(str) + "-" + t_stats['Loss'].astype(str)
        
        for s in ['PTS', 'REB', 'AST', 'STL', 'BLK']:
            t_stats[f'{s}_Avg'] = (t_stats[s] / t_stats['Game_ID']).round(1)
            
        return p_avg, df_p, t_stats
    except Exception: return None, None, None

p_avg, df_raw, t_stats = load_data()

# 3. SPLASH SCREEN (NO SCROLL)
if 'hub_entered' not in st.session_state: st.session_state.hub_entered = False
if not st.session_state.hub_entered:
    st.markdown('<div class="splash-wrapper">', unsafe_allow_html=True)
    logo_path = Path(__file__).parent / "logo.jpg"
    if logo_path.exists(): st.image(str(logo_path), width=350)
    st.markdown("<h1 style='font-size: 70px; color: #d4af37;'>SPAM LEAGUE</h1>", unsafe_allow_html=True)
    if st.button("PRESS TO ENTER HUB", use_container_width=True):
        st.session_state.hub_entered = True
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# 4. MAIN INTERFACE
# Re-enable scrolling for the dashboard content
st.markdown("<style>html, body, [data-testid='stAppViewContainer'] { overflow: auto; }</style>", unsafe_allow_html=True)

if p_avg is not None:
    # TICKER
    ticker_items = []
    for cat in ['PTS', 'AST', 'REB']:
        lead = p_avg.nlargest(1, f'{cat}/G').iloc[0]
        ticker_items.append(f"🔥 {cat} LEADER: {lead['Player/Team']} ({lead[cat+'/G']})")
    st.markdown(f'<div class="ticker-wrap"><div class="ticker-content"><span class="ticker-item">{"  •  ".join(ticker_items)}</span></div></div>', unsafe_allow_html=True)
    st.markdown('<div class="header-banner">🏀 SPAM LEAGUE CENTRAL</div>', unsafe_allow_html=True)

    tabs = st.tabs(["👤 PLAYERS", "🏘️ STANDINGS", "🔝 LEADERBOARDS", "⚔️ VERSUS", "📖 RECORDS"])

    with tabs[0]: # PLAYERS
        table = p_avg[['Player/Team', 'Team Name', 'GP', 'PTS/G', 'REB/G', 'AST/G', 'PIE']].sort_values('PIE', ascending=False)
        sel = st.dataframe(table, use_container_width=True, hide_index=True, on_select="rerun", selection_mode="single-row")
        if len(sel.selection.rows) > 0:
            p_name = table.iloc[sel.selection.rows[0]]['Player/Team']
            p_hist = df_raw[df_raw['Player/Team'] == p_name].sort_values('Game_ID', ascending=False)
            st.header(f"🔍 {p_name}")
            c1, c2 = st.columns([1, 2])
            with c1: st.metric("PTS HIGH", int(p_hist['PTS'].max())); st.metric("REB HIGH", int(p_hist['REB'].max())); st.metric("AST HIGH", int(p_hist['AST'].max()))
            with c2: st.line_chart(p_hist.set_index('Game_ID')['PTS'], height=200)

    with tabs[1]: # STANDINGS (FIXED KEYERROR)
        st.dataframe(t_stats[['Team Name', 'Record', 'PTS', 'REB', 'AST']].sort_values('Win', ascending=False), use_container_width=True, hide_index=True)

    with tabs[2]: # LEADERBOARDS
        cat = st.selectbox("Category", ["PTS/G", "REB/G", "AST/G", "PIE"])
        t10 = p_avg[['Player/Team', 'Team Name', cat]].nlargest(10, cat).reset_index(drop=True)
        t10.index += 1
        st.table(t10)
        st.plotly_chart(px.bar(t10, x=cat, y='Player/Team', orientation='h', template="plotly_dark", color_continuous_scale="Purp"), use_container_width=True)

    with tabs[3]: # VERSUS
        v_mode = st.radio("Matchup", ["Player vs Player", "Team vs Team"], horizontal=True)
        v1, v2 = st.columns(2)
        if v_mode == "Player vs Player":
            p1 = v1.selectbox("P1", p_avg['Player/Team'].unique(), index=0)
            p2 = v2.selectbox("P2", p_avg['Player/Team'].unique(), index=1)
            d1, d2 = p_avg[p_avg['Player/Team']==p1].iloc[0], p_avg[p_avg['Player/Team']==p2].iloc[0]
            for s in ['PTS/G', 'REB/G', 'AST/G', 'PIE']:
                sc1, sc2 = st.columns(2)
                sc1.metric(f"{p1} {s}", d1[s], delta=round(d1[s]-d2[s],1)); sc2.metric(f"{p2} {s}", d2[s], delta=round(d2[s]-d1[s],1))
        else:
            t1 = v1.selectbox("Team 1", t_stats['Team Name'].unique(), index=0)
            t2 = v2.selectbox("Team 2", t_stats['Team Name'].unique(), index=1)
            td1, td2 = t_stats[t_stats['Team Name']==t1].iloc[0], t_stats[t_stats['Team Name']==t2].iloc[0]
            for s in ['PTS_Avg', 'REB_Avg', 'AST_Avg']:
                sc1, sc2 = st.columns(2)
                sc1.metric(f"{t1} {s.split('_')[0]}", td1[s], delta=round(td1[s]-td2[s],1)); sc2.metric(f"{t2} {s.split('_')[0]}", td2[s], delta=round(td2[s]-td1[s],1))

    with tabs[4]: # RECORDS
        r_p = df_raw.loc[df_raw['PTS'].idxmax()]; r_r = df_raw.loc[df_raw['REB'].idxmax()]
        r_s = df_raw.loc[df_raw['STL'].idxmax()]; r_b = df_raw.loc[df_raw['BLK'].idxmax()]
        st.metric("Points Record", int(r_p['PTS']), r_p['Player/Team'])
        st.metric("Rebounds Record", int(r_r['REB']), r_r['Player/Team'])
        st.metric("Steals Record", int(r_s['STL']), r_s['Player/Team'])
        st.metric("Blocks Record", int(r_b['BLK']), r_b['Player/Team'])

