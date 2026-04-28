import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

# --- 1. UI & SLEEK CSS ---
st.set_page_config(page_title="SPAM LEAGUE CENTRAL", page_icon="🏀", layout="wide")

css_styles = """
<style>
    .stApp { background: radial-gradient(circle at top, #1f1f1f 0%, #050505 100%); color: #e0e0e0; }
    .header-banner { 
        padding: 25px; text-align: center; 
        background: linear-gradient(90deg, #d4af37 0%, #f7e08a 50%, #d4af37 100%);
        color: #000; font-family: 'Arial Black'; font-size: 28px; border-radius: 8px; margin-bottom: 20px;
    }
    .flip-card { background-color: transparent; width: 100%; perspective: 1000px; margin-bottom: 25px; }
    .flip-card-inner { position: relative; width: 100%; height: 100%; text-align: center; transition: transform 0.6s; transform-style: preserve-3d; }
    .flip-card:hover .flip-card-inner { transform: rotateY(180deg); }
    .flip-card-front, .flip-card-back { position: absolute; width: 100%; height: 100%; -webkit-backface-visibility: hidden; backface-visibility: hidden; border-radius: 10px; }
    .flip-card-front { background: linear-gradient(135deg, #1f1f1f, #333); border: 2px solid #d4af37; display: flex; flex-direction: column; justify-content: center; }
    .flip-card-back { background: linear-gradient(135deg, #d4af37, #b8860b); color: #000; transform: rotateY(180deg); display: flex; flex-direction: column; justify-content: center; text-align: left; padding: 20px; }
    
    /* Metrics Box */
    .metric-box { background: #2a2d35; border-left: 5px solid #d4af37; padding: 15px; border-radius: 5px; margin-bottom: 15px; text-align: center; }
    .metric-title { font-size: 14px; color: #aaa; text-transform: uppercase; }
    .metric-value { font-size: 24px; font-weight: bold; color: #fff; }
</style>
"""
st.markdown(css_styles, unsafe_allow_html=True)

# --- 2. DATA PROCESSING & ADVANCED LOGIC ---
@st.cache_data
def load_and_process_data():
    # Load your CSV here (Replace with your actual file path if needed)
    df = pd.read_csv("SPAM - Sheet1 (4).csv")
    
    # Clean basic columns
    df['Game_ID'] = pd.to_numeric(df['Game_ID'], errors='coerce')
    
    # 1. GAME TYPE CATEGORIZATION
    df['Game_Type'] = np.where(df['Game_ID'] >= 9000, 'Playoffs', 
                      np.where(df['Game_ID'] >= 8000, 'Tournament', 'Regular Season'))

    # 2. ADVANCED PROXY STATS LOGIC (Positions 1-5 assigned automatically)
    players_df = df[df['Type'] == 'Player'].copy()
    players_df['Position_Num'] = players_df.groupby(['Game_ID', 'Team Name']).cumcount() + 1

    players_df['Tipped_Passes'] = np.where(
        players_df['Position_Num'] <= 2,
        (players_df['STL'] * 2.2) + (players_df['FOULS'] * 0.4),  
        (players_df['STL'] * 1.2) + (players_df['BLK'] * 0.2)     
    ).round().astype(int)

    players_df['Shots_Affected'] = np.where(
        players_df['Position_Num'] >= 3,
        (players_df['BLK'] * 3.0) + (players_df['REB'] * 0.4) + (players_df['FOULS'] * 0.5), 
        (players_df['BLK'] * 1.5) + (players_df['STL'] * 0.4)                                
    ).round().astype(int)

    players_df['FB_Points'] = np.where(
        players_df['Position_Num'] <= 2,
        (players_df['STL'] * 2.0) + (players_df['FGM'] * 0.4),  
        (players_df['STL'] * 1.0) + (players_df['FGM'] * 0.1)   
    ).round().astype(int)
    
    # Safeguard: FB points cannot exceed actual points
    players_df['FB_Points'] = players_df[['FB_Points', 'PTS']].min(axis=1)

    df = df.merge(
        players_df[['Game_ID', 'Team Name', 'Player/Team', 'Tipped_Passes', 'Shots_Affected', 'FB_Points']],
        on=['Game_ID', 'Team Name', 'Player/Team'], how='left'
    )

    team_proxy_totals = df[df['Type'] == 'Player'].groupby(['Game_ID', 'Team Name'])[['Tipped_Passes', 'Shots_Affected', 'FB_Points']].sum().reset_index()
    for col in ['Tipped_Passes', 'Shots_Affected', 'FB_Points']:
        df.loc[df['Type'] == 'Team', col] = df.loc[df['Type'] == 'Team'].set_index(['Game_ID', 'Team Name']).index.map(
            team_proxy_totals.set_index(['Game_ID', 'Team Name'])[col]
        ).fillna(0)

    # 3. OPPONENT STATS & POINT DIFFERENTIAL
    team_game_logs = df[df['Type'] == 'Team'][['Game_ID', 'Team Name', 'PTS', 'FGM', 'FGA', '3PM', '3PA', 'TO', 'FTA']].copy()
    opp_matchups = pd.merge(team_game_logs, team_game_logs, on='Game_ID', suffixes=('', '_Opp'))
    opp_matchups = opp_matchups[opp_matchups['Team Name'] != opp_matchups['Team Name_Opp']]

    opp_matchups['Point_Diff'] = opp_matchups['PTS'] - opp_matchups['PTS_Opp']
    opp_matchups['Opp_Possessions'] = opp_matchups['FGA_Opp'] + (0.44 * opp_matchups['FTA_Opp']) + opp_matchups['TO_Opp']
    opp_matchups['Opp_PPP'] = np.where(opp_matchups['Opp_Possessions'] > 0, opp_matchups['PTS_Opp'] / opp_matchups['Opp_Possessions'], 0)
    opp_matchups['Opp_FG%'] = np.where(opp_matchups['FGA_Opp'] > 0, (opp_matchups['FGM_Opp'] / opp_matchups['FGA_Opp']) * 100, 0)
    opp_matchups['Opp_3P%'] = np.where(opp_matchups['3PA_Opp'] > 0, (opp_matchups['3PM_Opp'] / opp_matchups['3PA_Opp']) * 100, 0)

    metrics_to_merge = opp_matchups[['Game_ID', 'Team Name', 'Point_Diff', 'Opp_PPP', 'Opp_FG%', 'Opp_3P%']]
    df = pd.merge(df, metrics_to_merge, on=['Game_ID', 'Team Name'], how='left')

    df['Point_Diff'] = df.groupby(['Game_ID', 'Team Name'])['Point_Diff'].transform('first')
    df['Opp_PPP'] = df.groupby(['Game_ID', 'Team Name'])['Opp_PPP'].transform('first')
    df['Opp_FG%'] = df.groupby(['Game_ID', 'Team Name'])['Opp_FG%'].transform('first')
    df['Opp_3P%'] = df.groupby(['Game_ID', 'Team Name'])['Opp_3P%'].transform('first')

    return df

df = load_and_process_data()

# --- 3. SIDEBAR NAVIGATION ---
st.sidebar.image("https://upload.wikimedia.org/wikipedia/commons/thumb/7/7a/Basketball_ball.svg/1024px-Basketball_ball.svg.png", width=100)
st.sidebar.markdown("## Navigation")
selection = st.sidebar.radio("Go to", ["Home (Standings)", "Team Hub", "The Vault"])

# --- 4. PAGE: HOME (STANDINGS) ---
if selection == "Home (Standings)":
    st.markdown("<div class='header-banner'>LEAGUE STANDINGS & ADVANCED METRICS</div>", unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        st_season = st.selectbox("Select Season", sorted(df['Season'].dropna().unique(), reverse=True), key='standings_season')
    with col2:
        st_type = st.selectbox("Game Type", ['All', 'Regular Season', 'Tournament', 'Playoffs'], key='standings_type')

    standings_df = df[(df['Type'] == 'Team') & (df['Season'] == st_season)]
    if st_type != 'All':
        standings_df = standings_df[standings_df['Game_Type'] == st_type]

    if standings_df.empty:
        st.warning("No data found for this selection.")
    else:
        team_aggs = standings_df.groupby('Team Name').agg(
            Games=('Game_ID', 'nunique'),
            Wins=('Win', 'sum'),
            PPG=('PTS', 'mean'),
            Diff=('Point_Diff', 'mean'),
            Opp_FG=('Opp_FG%', 'mean'),
            Opp_3P=('Opp_3P%', 'mean'),
            Opp_PPP=('Opp_PPP', 'mean')
        ).reset_index()

        team_aggs['Win%'] = (team_aggs['Wins'] / team_aggs['Games']) * 100
        team_aggs = team_aggs.sort_values(by=['Win%', 'Diff'], ascending=[False, False])

        cols = st.columns(4)
        for idx, row in team_aggs.iterrows():
            with cols[idx % 4]:
                st.markdown(f"""
                <div class="flip-card" style="height: 250px;">
                  <div class="flip-card-inner">
                    <div class="flip-card-front">
                      <h2 style="color: #d4af37; margin:0;">{row['Team Name']}</h2>
                      <h1 style="margin: 10px 0;">{int(row['Wins'])} - {int(row['Games'] - row['Wins'])}</h1>
                      <p style="color: #aaa; margin:0;">Point Diff: {row['Diff']:+.1f}</p>
                      <p style="color: #aaa; margin-top:15px; font-size:12px;">Hover for Advanced Stats ⤵</p>
                    </div>
                    <div class="flip-card-back">
                      <h4 style="border-bottom: 1px solid #000; padding-bottom: 5px; margin-top:0;">Advanced Metrics</h4>
                      <p><b>Opp FG%:</b> {row['Opp_FG']:.1f}%</p>
                      <p><b>Opp 3P%:</b> {row['Opp_3P']:.1f}%</p>
                      <p><b>Opp PPP:</b> {row['Opp_PPP']:.2f}</p>
                      <p><b>PPG:</b> {row['PPG']:.1f}</p>
                    </div>
                  </div>
                </div>
                """, unsafe_allow_html=True)

# --- 5. PAGE: TEAM HUB ---
elif selection == "Team Hub":
    teams_list = sorted(df[df['Type'] == 'Team']['Team Name'].unique())
    selected_team = st.sidebar.selectbox("Select Team", teams_list)
    
    st.markdown(f"<div class='header-banner'>{selected_team} TEAM HUB</div>", unsafe_allow_html=True)
    team_data = df[(df['Team Name'] == selected_team)]
    
    tab_team_stats, tab_box_scores = st.tabs(["📊 Season Stats & Analytics", "📓 Game-by-Game Box Scores"])

    with tab_team_stats:
        st.subheader(f"{selected_team} Total Performance")
        t_team_only = team_data[team_data['Type'] == 'Team']
        
        c1, c2, c3, c4 = st.columns(4)
        c1.markdown(f"<div class='metric-box'><div class='metric-title'>Points Per Game</div><div class='metric-value'>{t_team_only['PTS'].mean():.1f}</div></div>", unsafe_allow_html=True)
        c2.markdown(f"<div class='metric-box'><div class='metric-title'>Point Differential</div><div class='metric-value'>{t_team_only['Point_Diff'].mean():+.1f}</div></div>", unsafe_allow_html=True)
        c3.markdown(f"<div class='metric-box'><div class='metric-title'>Opponent FG%</div><div class='metric-value'>{t_team_only['Opp_FG%'].mean():.1f}%</div></div>", unsafe_allow_html=True)
        c4.markdown(f"<div class='metric-box'><div class='metric-title'>Opponent PPP</div><div class='metric-value'>{t_team_only['Opp_PPP'].mean():.2f}</div></div>", unsafe_allow_html=True)
        
        st.markdown("### Player Averages")
        p_team_only = team_data[team_data['Type'] == 'Player']
        roster_stats = p_team_only.groupby('Player/Team').agg(
            GP=('Game_ID', 'nunique'),
            PPG=('PTS', 'mean'),
            RPG=('REB', 'mean'),
            APG=('AST', 'mean'),
            SPG=('STL', 'mean'),
            BPG=('BLK', 'mean'),
            FB_PPG=('FB_Points', 'mean'),
            Tipped_Passes=('Tipped_Passes', 'mean'),
            Shots_Affected=('Shots_Affected', 'mean')
        ).round(1)
        st.dataframe(roster_stats, use_container_width=True)

    with tab_box_scores:
        st.subheader("Game-by-Game Logs")
        game_options = team_data['Game_ID'].unique()
        selected_game = st.selectbox("Select Game ID to view Box Score", sorted(game_options, reverse=True))
        
        box_score_data = team_data[(team_data['Game_ID'] == selected_game) & (team_data['Type'] == 'Player')]
        
        if not box_score_data.empty:
            st.markdown(f"**Game Type:** `{box_score_data['Game_Type'].iloc[0]}` | **Season:** `{box_score_data['Season'].iloc[0]}`")
            display_cols = ['Player/Team', 'GRD', 'PTS', 'REB', 'AST', 'STL', 'BLK', 'TO', 'FGM', 'FGA', '3PM', '3PA', 'Tipped_Passes', 'Shots_Affected', 'FB_Points']
            st.dataframe(box_score_data[display_cols], use_container_width=True, hide_index=True)

# --- 6. PAGE: THE VAULT ---
elif selection == "The Vault":
    st.markdown("<div class='header-banner'>THE VAULT: ALL-TIME TOTALS</div>", unsafe_allow_html=True)
    
    col1, col2 = st.columns([1, 2])
    with col1:
        vault_type = st.radio("View Totals For:", ["Players", "Teams"], horizontal=True)
    with col2:
        vault_game_filter = st.multiselect("Filter by Game Type", ['Regular Season', 'Tournament', 'Playoffs'], default=['Regular Season', 'Tournament', 'Playoffs'])
    
    vault_data = df[df['Game_Type'].isin(vault_game_filter)]
    
    if vault_type == "Players":
        v_df = vault_data[vault_data['Type'] == 'Player']
        totals = v_df.groupby('Player/Team').agg(
            Games=('Game_ID', 'nunique'),
            PTS=('PTS', 'sum'),
            REB=('REB', 'sum'),
            AST=('AST', 'sum'),
            STL=('STL', 'sum'),
            BLK=('BLK', 'sum'),
            FGM=('FGM', 'sum'),
            FGA=('FGA', 'sum'),
            3PM=('3PM', 'sum'),
            3PA=('3PA', 'sum'),
            FB_Points=('FB_Points', 'sum'),
            Tipped_Passes=('Tipped_Passes', 'sum'),
            Shots_Affected=('Shots_Affected', 'sum')
        ).reset_index()
        st.dataframe(totals.sort_values(by='PTS', ascending=False), use_container_width=True, hide_index=True)
        
    else:
        v_df = vault_data[vault_data['Type'] == 'Team']
        totals = v_df.groupby('Team Name').agg(
            Games=('Game_ID', 'nunique'),
            Wins=('Win', 'sum'),
            PTS=('PTS', 'sum'),
            Point_Diff=('Point_Diff', 'sum'),
            FB_Points=('FB_Points', 'sum'),
            Tipped_Passes=('Tipped_Passes', 'sum'),
            Shots_Affected=('Shots_Affected', 'sum')
        ).reset_index()
        st.dataframe(totals.sort_values(by='Wins', ascending=False), use_container_width=True, hide_index=True)
