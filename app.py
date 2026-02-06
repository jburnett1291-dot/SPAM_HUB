import streamlit as st

import pandas as pd

import plotly.express as px

from pathlib import Path



# 1. UI & SEAMLESS EMBEDDING

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



# 2. DATA ENGINE (FIXED KEYERRORS)

SHEET_ID = "1rksLYUcXQJ03uTacfIBD6SRsvtH-IE6djqT-LINwcH4"

URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"



@st.cache_data(ttl=60)

def load_data():

    try:

        df = pd.read_csv(URL)

        df.columns = df.columns.str.strip()

        

        # Ensure 'Win' and 'Game_ID' exist for sorting

        for c in ['PTS', 'REB', 'AST', 'STL', 'BLK', 'FGA', 'Game_ID', 'Win']:

            if c in df.columns:

                df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)

            else:

                df[c] = 0 # Create the column if missing to prevent KeyError

        

        df['PIE'] = (df['PTS'] + df['REB'] + df['AST'] + df['STL'] + df['BLK']) - (df.get('FGA', 0) * 0.5)

        

        # Separate Players and Teams (TOTAL rows)

        df_p = df[df['Type'].str.lower() == 'player'].copy()

        df_t = df[df['Type'].str.lower() == 'team'].copy()



        # Calculate Player Averages

        gp = df_p.groupby('Player/Team')['Game_ID'].nunique().reset_index(name='GP')

        p_avg = pd.merge(df_p.groupby(['Player/Team', 'Team Name']).sum(numeric_only=True).reset_index(), gp, on='Player/Team')

        for s in ['PTS', 'REB', 'AST', 'STL', 'BLK']:

            p_avg[f'{s}/G'] = (p_avg[s] / p_avg['GP']).round(1)



        # Team Standings (Uses the 'TOTAL' rows from your sheet)

        t_stats = df_t.groupby('Team Name').agg({

            'Win': 'sum', 'Game_ID': 'count', 'PTS': 'sum', 'REB': 'sum', 'AST': 'sum'

        }).reset_index()

        t_stats['Loss'] = (t_stats['Game_ID'] - t_stats['Win']).astype(int)

        t_stats['Record'] = t_stats['Win'].astype(int).astype(str) + "-" + t_stats['Loss'].astype(str)

        

        return p_avg, df_p, t_stats

    except Exception as e:

        st.error(f"Sync Error: {e}"); return None, None, None



p_avg, df_raw, t_stats = load_data()



# 3. BROADCAST INTERFACE

if p_avg is not None:

    # TICKER LOGIC

    ticker_items = []

    for cat in ['PTS', 'AST', 'REB', 'STL', 'BLK']:

        lead = p_avg.nlargest(1, f'{cat}/G').iloc[0]

        ticker_items.append(f"🔥 {cat} LEADER: {lead['Player/Team']} ({lead[cat+'/G']})")

    

    last_3 = sorted(df_raw['Game_ID'].unique())[-3:]

    for gid in last_3:

        mvp = df_raw[df_raw['Game_ID'] == gid].nlargest(1, 'PIE').iloc[0]

        ticker_items.append(f"🎮 G{int(gid)} MVP: {mvp['Player/Team']} ({int(mvp['PTS'])} PTS)")



    st.markdown(f'<div class="ticker-wrap"><div class="ticker-content"><span class="ticker-item">{"  •  ".join(ticker_items)}</span></div></div>', unsafe_allow_html=True)

    st.markdown('<div class="header-banner">🏀 SPAM LEAGUE CENTRAL</div>', unsafe_allow_html=True)



    tabs = st.tabs(["👤 PLAYERS", "🏘️ TEAM STANDINGS", "🔝 LEADERBOARDS", "⚔️ VERSUS", "📖 RECORDS"])



    # --- TAB 1: INTERACTIVE PLAYER HUB ---

    with tabs[0]:

        st.subheader("Click a player row below to view full Scouting Report")

        

        main_table = p_avg[['Player/Team', 'Team Name', 'GP', 'PTS/G', 'REB/G', 'AST/G', 'PIE']].sort_values('PIE', ascending=False)

        

        # The Selection Logic

        selection = st.dataframe(

            main_table,

            use_container_width=True,

            hide_index=True,

            on_select="rerun",

            selection_mode="single-row"

        )

        

        if len(selection.selection.rows) > 0:

            p_idx = selection.selection.rows[0]

            p_name = main_table.iloc[p_idx]['Player/Team']

            p_history = df_raw[df_raw['Player/Team'] == p_name].sort_values('Game_ID', ascending=False)

            

            st.divider()

            st.header(f"🔍 {p_name} Scouting Report")

            c1, c2 = st.columns([1, 2])

            with c1:

                st.metric("SEASON PTS HIGH", int(p_history['PTS'].max()))

                st.metric("SEASON REB HIGH", int(p_history['REB'].max()))

                st.metric("SEASON AST HIGH", int(p_history['AST'].max()))

            with c2:

                last_g = p_history.iloc[0]

                st.markdown(f"#### LAST GAME (Game {int(last_g['Game_ID'])})")

                lc1, lc2, lc3 = st.columns(3)

                lc1.metric("PTS", int(last_g['PTS']))

                lc2.metric("REB", int(last_g['REB']))

                lc3.metric("AST", int(last_g['AST']))

                st.line_chart(p_history.set_index('Game_ID')['PTS'], height=150)

            st.table(p_history[['Game_ID', 'PTS', 'REB', 'AST', 'PIE']].head(5))

        else:

            st.info("👆 Click a player row above to load their game highs and last game stats.")



    # --- TAB 2: STANDINGS (FIXED ERROR) ---

    with tabs[1]:

        st.subheader("🏘️ Team Standings & Records")

        # Safety sort to prevent KeyError

        if 'Win' in t_stats.columns:

            standings_display = t_stats.sort_values('Win', ascending=False)

        else:

            standings_display = t_stats

            

        st.dataframe(

            standings_display[['Team Name', 'Record', 'PTS', 'REB', 'AST']], 

            use_container_width=True, 

            hide_index=True

        )



    # --- TAB 3: LEADERBOARDS (FIXED ERROR) ---

    with tabs[2]:

        st.subheader("🔝 Top 10 Leaders")

        cat_sel = st.selectbox("Choose Category", ["PTS/G", "REB/G", "AST/G", "PIE"])

        fig = px.bar(p_avg.nlargest(10, cat_sel), x=cat_sel, y='Player/Team', color=cat_sel, orientation='h', template="plotly_dark")

        st.plotly_chart(fig, use_container_width=True)



    # --- TAB 4: VERSUS ---

    with tabs[3]:

        v1, v2 = st.columns(2)

        p1 = v1.selectbox("P1", p_avg['Player/Team'].unique(), index=0)

        p2 = v2.selectbox("P2", p_avg['Player/Team'].unique(), index=1)

        d1, d2 = p_avg[p_avg['Player/Team']==p1].iloc[0], p_avg[p_avg['Player/Team']==p2].iloc[0]

        for s in ['PTS/G', 'REB/G', 'AST/G', 'PIE']:

            sc1, sc2 = st.columns(2)

            sc1.metric(f"{p1} {s}", d1[s], delta=round(d1[s]-d2[s], 1))

            sc2.metric(f"{p2} {s}", d2[s], delta=round(d2[s]-d1[s], 1))



    # --- TAB 5: RECORDS ---

    with tabs[4]:

        st.metric("League Scoring High", int(df_raw['PTS'].max()), df_raw.loc[df_raw['PTS'].idxmax(), 'Player/Team'])



    st.markdown('<div style="text-align: center; color: #444; padding: 20px;">© 2026 SPAM LEAGUE HUB</div>', unsafe_allow_html=True)


