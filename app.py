import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path

# 1. UI & BRANDING CONFIG
st.set_page_config(page_title="SPAM LEAGUE CENTRAL", page_icon="🏀", layout="wide")

st.markdown("""
    <style>
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    div[data-testid="stToolbar"] {visibility: hidden;} [data-testid="stStatusWidget"] {display: none;}
    .block-container { padding: 0rem !important; }
    .stApp { background: radial-gradient(circle, #1a1a1a 0%, #050505 100%); color: #d4af37; bottom: 0; }
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
        data = pd.read_csv(URL)
        data.columns = data.columns.str.strip()
        num_cols = ['PTS', 'REB', 'AST', 'STL', 'BLK', 'FGA', 'Game_ID', 'Win']
        for c in num_cols:
            if c in data.columns:
                data[c] = pd.to_numeric(data[c], errors='coerce').fillna(0)
        
        data['PIE'] = (data['PTS'] + data['REB'] + data['AST'] + data['STL'] + data['BLK']) - (data.get('FGA', 0) * 0.5)
        df_p = data[data['Type'].str.lower() == 'player'].copy()
        df_t = data[data['Type'].str.lower() == 'team'].copy()

        gp = df_p.groupby('Player/Team')['Game_ID'].nunique().reset_index(name='GP')
        p_avg = pd.merge(df_p.groupby(['Player/Team', 'Team Name']).sum(numeric_only=True).reset_index(), gp, on='Player/Team')
        for s in ['PTS', 'REB', 'AST', 'STL', 'BLK']:
            p_avg[f'{s}/G'] = (p_avg[s] / p_avg['GP']).round(1)

        t_standings = df_t.groupby('Team Name').agg({
            'Win': 'sum', 'Game_ID': 'count', 'PTS': 'sum', 'REB': 'sum', 'AST': 'sum'
        }).reset_index()
        t_standings['Loss'] = (t_standings['Game_ID'] - t_standings['Win']).astype(int)
        t_standings['Record'] = t_standings['Win'].astype(int).astype(str) + "-" + t_standings['Loss'].astype(str)
        
        return p_avg, df_p, t_standings
    except Exception as e:
        st.error(f"Sync Error: {e}"); return None, None, None

p_avg, df_raw, t_stats = load_data()

# 3. BROADCAST INTERFACE
if p_avg is not None:
    # TICKER
    ticker_items = []
    for cat in ['PTS', 'AST', 'REB']:
        lead = p_avg.nlargest(1, f'{cat}/G').iloc[0]
        ticker_items.append(f"🔥 {cat} LEADER: {lead['Player/Team']} ({lead[cat+'/G']})")
    
    last_3 = sorted(df_raw['Game_ID'].unique())[-3:]
    for gid in last_3:
        mvp = df_raw[df_raw['Game_ID'] == gid].nlargest(1, 'PIE').iloc[0]
        ticker_items.append(f"🎮 G{gid} MVP: {mvp['Player/Team']} ({int(mvp['PTS'])} PTS)")

    st.markdown(f'<div class="ticker-wrap"><div class="ticker-content"><span class="ticker-item">{"  •  ".join(ticker_items)}</span></div></div>', unsafe_allow_html=True)
    st.markdown('<div class="header-banner">🏀 SPAM LEAGUE CENTRAL</div>', unsafe_allow_html=True)

    tabs = st.tabs(["👤 PLAYERS", "🏘️ TEAM STANDINGS", "🔝 LEADERBOARDS", "⚔️ VERSUS", "📖 RECORDS"])

    with tabs[0]:
        st.subheader("Select a player to view Game Highs & Last Game Results")
        
        # INTERACTIVE DATAFRAME - CLICKABLE
        event = st.dataframe(
            p_avg[['Player/Team', 'Team Name', 'GP', 'PTS/G', 'REB/G', 'AST/G', 'PIE']].sort_values('PIE', ascending=False),
            use_container_width=True,
            hide_index=True,
            on_select="rerun",
            selection_mode="single-row"
        )
        
        # CHECK IF PLAYER IS CLICKED
        if len(event.selection.rows) > 0:
            selected_idx = event.selection.rows[0]
            player_name = p_avg.sort_values('PIE', ascending=False).iloc[selected_idx]['Player/Team']
            
            p_history = df_raw[df_raw['Player/Team'] == player_name].sort_values('Game_ID', ascending=False)
            
            st.markdown(f"## 📊 Scouting Report: {player_name}")
            c1, c2, c3 = st.columns(3)
            
            # 1. Season Highs
            with c1:
                st.write("**SEASON HIGHS**")
                st.metric("PTS", int(p_history['PTS'].max()))
                st.metric("REB", int(p_history['REB'].max()))
                st.metric("AST", int(p_history['AST'].max()))
            
            # 2. Last Game
            with c2:
                last_g = p_history.iloc[0]
                st.write(f"**LAST GAME (G{int(last_g['Game_ID'])})**")
                st.metric("PTS", int(last_g['PTS']))
                st.metric("REB", int(last_g['REB']))
                st.metric("AST", int(last_g['AST']))
                
            # 3. Game Log Graph
            with c3:
                st.write("**PTS TREND**")
                st.line_chart(p_history.set_index('Game_ID')['PTS'], height=200)

            st.markdown("### Full Season Game Log")
            st.table(p_history[['Game_ID', 'PTS', 'REB', 'AST', 'STL', 'BLK', 'PIE']].head(10))
        else:
            st.info("💡 Click a row in the table above to reveal player-specific stats!")

    with tabs[1]: # TEAM STANDINGS
        st.dataframe(t_stats[['Team Name', 'Record', 'PTS', 'REB', 'AST']].sort_values('Win', ascending=False), 
                     use_container_width=True, hide_index=True)

    with tabs[2]: # LEADERBOARDS
        cat = st.selectbox("Category:", ["PTS/G", "REB/G", "AST/G", "PIE"])
        st.plotly_chart(px.bar(p_avg.nlargest(10, cat), x=cat, y='Player/Team', orientation='h', template="plotly_dark", color_continuous_scale="Purp"), use_container_width=True)

    with tabs[3]: # VERSUS
        v1, v2 = st.columns(2)
        p1 = v1.selectbox("P1", p_avg['Player/Team'].unique(), index=0)
        p2 = v2.selectbox("P2", p_avg['Player/Team'].unique(), index=1)
        st.write(f"Comparing {p1} vs {p2}") # Simplified for logic check

    with tabs[4]: # RECORDS
        st.metric("League Scoring Record", int(df_raw['PTS'].max()), df_raw.loc[df_raw['PTS'].idxmax(), 'Player/Team'])

    st.markdown('<div style="text-align: center; color: #444; padding: 20px;">© 2026 SPAM LEAGUE HUB</div>', unsafe_allow_html=True)




