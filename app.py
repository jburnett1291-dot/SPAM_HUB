import streamlit as st
import pandas as pd
import numpy as np
import re
import math
import random
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Arc
from io import BytesIO

# --- 1. CONFIGURATION & CONSTANTS ---
SHEET_ID = "1rksLYUcXQJ03uTacfIBD6SRsvtH-IE6djqT-LINwcH4"
URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"

st.set_page_config(
    page_title="QCL QSPN Analytics Dashboard",
    page_icon="🏀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. DATA PROCESSING ENGINE (Identical to Discord Bot) ---
def smart_name_scrubber(raw_name):
    if pd.isna(raw_name) or not isinstance(raw_name, str): 
        return raw_name
    return re.sub(r'^\[.*?\]\s*|^\(.*?\)\s*', '', re.sub(r'^[|Il\s]+', '', raw_name)).strip().title()

@st.cache_data(ttl=300)
def load_and_process_stats():
    try:
        df = pd.read_csv(URL)
        df.columns = df.columns.str.strip()
        df = df[df['Player/Team'] != 'Player/Team']
        df = df[df['Team Name'].notna() & (df['Team Name'].astype(str).str.strip() != '') & (df['Team Name'].astype(str) != '0')]
        
        if 'Player/Team' in df.columns: 
            df['Player/Team'] = df['Player/Team'].apply(smart_name_scrubber)
            
        req_cols = ['PTS', 'REB', 'AST', 'STL', 'BLK', 'FOULS', 'TO', 'FGA', 'FGM', '3PM', '3PA', 'FTA', 'FTM', 'OREB', 'DREB', 'MIN', 'Q1', 'Q2', 'Q3', 'Q4', 'Game_ID', 'Win', 'Season', 'Type', 'Team Name']
        for c in req_cols:
            if c not in df.columns: df[c] = 0
            if c not in ['Type', 'Team Name', 'Player/Team']: 
                df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)
            
        df['Win'] = pd.to_numeric(df['Win'], errors='coerce').fillna(0).apply(lambda x: 1 if x > 0 else 0)
        df['Game_ID'] = pd.to_numeric(df['Game_ID'], errors='coerce')
        
        # Deduplication Layer
        df = df.drop_duplicates(subset=['Type', 'Player/Team', 'Team Name', 'Game_ID', 'Season'], keep='first').copy()
        
        df.loc[df['Team Name'] == 'ChosenOne', 'Team Name'] = 'Smoke Chasers'
        df.loc[df['Player/Team'] == 'TaeCP', 'Position_Num'] = 5 

        df['PIE_Raw'] = (df['PTS'] + df['REB'] + df['AST'] + df['STL'] + df['BLK']) - (df['FGA'] * 0.5) - df['TO']
        df['Poss_Raw'] = df['FGA'] + 0.44 * df['FTA'] + df['TO']

        # Isolate baseline players to build clean Team rows
        df = df[df['Type'].astype(str).str.lower() != 'team'].copy()
        sum_cols = ['PTS', 'REB', 'AST', 'STL', 'BLK', 'FOULS', 'TO', 'FGA', 'FGM', '3PM', '3PA', 'FTA', 'FTM', 'Poss_Raw']
        team_rows = df.groupby(['Game_ID', 'Team Name', 'Season']).agg({**{c: 'sum' for c in sum_cols}, 'Win': 'first'}).reset_index()
        team_rows['Type'] = 'Team'
        team_rows['Player/Team'] = team_rows['Team Name'] + " TOTALS"
        df = pd.concat([df, team_rows], ignore_index=True)

        players_df = df[df['Type'].astype(str).str.lower() == 'player'].copy()
        players_df = players_df.sort_values(by=['Game_ID', 'Team Name'])
        players_df['Position_Num'] = players_df.groupby(['Game_ID', 'Team Name']).cumcount() + 1
        
        # Identity Multipliers
        players_df['Tipped_Passes'] = np.where(players_df['Position_Num'] <= 2, (players_df['STL'] * 2.2) + (players_df['FOULS'] * 0.4), (players_df['STL'] * 1.2) + (players_df['BLK'] * 0.2)).round().astype(int)
        players_df['Shots_Affected'] = np.where(players_df['Position_Num'] >= 3, (players_df['BLK'] * 3.0) + (players_df['REB'] * 0.4) + (players_df['FOULS'] * 0.5), (players_df['BLK'] * 1.5) + (players_df['STL'] * 0.4)).round().astype(int)
        players_df['FB_Points'] = np.where(players_df['Position_Num'] <= 2, (players_df['STL'] * 2.0) + (players_df['FGM'] * 0.4), (players_df['STL'] * 1.0) + (players_df['FGM'] * 0.1)).round().astype(int)
        players_df['FB_Points'] = players_df[['FB_Points', 'PTS']].min(axis=1)

        df = df.merge(players_df[['Game_ID', 'Season', 'Team Name', 'Player/Team', 'Tipped_Passes', 'Shots_Affected', 'FB_Points']], on=['Game_ID', 'Season', 'Team Name', 'Player/Team'], how='left')

        t_proxy = df[df['Type'].astype(str).str.lower() == 'player'].groupby(['Game_ID', 'Season', 'Team Name'])[['Tipped_Passes', 'Shots_Affected', 'FB_Points']].sum().reset_index()
        for col in ['Tipped_Passes', 'Shots_Affected', 'FB_Points']:
            df.loc[df['Type'].astype(str).str.lower() == 'team', col] = df.loc[df['Type'].astype(str).str.lower() == 'team'].set_index(['Game_ID', 'Season', 'Team Name']).index.map(t_proxy.set_index(['Game_ID', 'Season', 'Team Name'])[col]).fillna(0)

        # GP Skew Resolution
        gp_counts = df[df['Type'].astype(str).str.lower() == 'player'].groupby('Player/Team')['Game_ID'].nunique().reset_index()
        gp_counts.rename(columns={'Game_ID': 'GP'}, inplace=True)
        df = pd.merge(df, gp_counts, on='Player/Team', how='left')
        
        t_gp_counts = df[df['Type'].astype(str).str.lower() == 'team'].groupby('Team Name')['Game_ID'].nunique().reset_index()
        t_gp_counts.rename(columns={'Game_ID': 'GP_Team'}, inplace=True)
        df = pd.merge(df, t_gp_counts, on='Team Name', how='left')
        df['GP'] = df['GP'].fillna(df['GP_Team'])

        # Opponent/Network Splits
        t_logs = df[df['Type'].astype(str).str.lower() == 'team'][['Game_ID', 'Team Name', 'PTS', 'FGA', 'TO', 'FTA', 'Win', 'Season']].copy()
        t_logs['Team_Win_Pct'] = t_logs.groupby(['Season', 'Team Name'])['Win'].transform('mean')
        opps = pd.merge(t_logs, t_logs, on=['Game_ID', 'Season'], suffixes=('', '_Opp'))
        opps = opps[opps['Team Name'] != opps['Team Name_Opp']]
        opps['Point_Diff'] = opps['PTS'] - opps['PTS_Opp']
        opps['Opp_Possessions'] = opps['FGA_Opp'] + (0.44 * opps['FTA_Opp']) + opps['TO_Opp']
        opps['Opp_PPP'] = np.where(opps['Opp_Possessions'] > 0, opps['PTS_Opp'] / opps['Opp_Possessions'], 0)

        df = pd.merge(df, opps[['Game_ID', 'Season', 'Team Name', 'Point_Diff', 'Opp_PPP', 'Team Name_Opp', 'Team_Win_Pct_Opp', 'PTS_Opp']], on=['Game_ID', 'Season', 'Team Name'], how='left')
        for col in ['Point_Diff', 'Opp_PPP', 'Team_Win_Pct_Opp', 'Team Name_Opp', 'PTS_Opp']:
            df[col] = df.groupby(['Game_ID', 'Season', 'Team Name'])[col].transform('first')
        df.rename(columns={'Team_Win_Pct_Opp': 'SOS_Game', 'Team Name_Opp': 'Opp_Name'}, inplace=True)

        # Advanced Advanced Metric Derivations
        df['2PM'] = (df['FGM'] - df['3PM']).clip(lower=0)
        df['2PA'] = (df['FGA'] - df['3PA']).clip(lower=0)
        df['eFG%'] = (np.where(df['FGA'] > 0, (df['FGM'] + 0.5 * df['3PM']) / df['FGA'] * 100, 0)).round(1)
        df['FT_Rate'] = (np.where(df['FGA'] > 0, df['FTA'] / df['FGA'] * 100, 0)).round(1)
        df['3PA_Rate'] = (np.where(df['FGA'] > 0, df['3PA'] / df['FGA'] * 100, 0)).round(1)
        df['AST_TO'] = (np.where(df['TO'] > 0, df['AST'] / df['TO'], df['AST'])).round(2)
        df['Stocks'] = df['STL'] + df['BLK']
        
        _keys = ['Game_ID', 'Season', 'Team Name']
        _pl = df['Type'].astype(str).str.lower() == 'player'
        _tt = df[_pl].groupby(_keys).agg(
            T_PTS=('PTS', 'sum'), T_FGM=('FGM', 'sum'), T_FGA=('FGA', 'sum'),
            T_3PA=('3PA', 'sum'), T_FTA=('FTA', 'sum'), T_TO=('TO', 'sum'),
            T_REB=('REB', 'sum'), T_AST=('AST', 'sum')).reset_index()
        _tt['T_Missed'] = (_tt['T_FGA'] - _tt['T_FGM']).clip(lower=0)
        _tt['T_OREB'] = (_tt['T_Missed'] * 0.27).round()
        _tt['T_DREB'] = (_tt['T_REB'] - _tt['T_OREB']).clip(lower=0)
        _tt['T_Poss'] = (_tt['T_FGA'] + 0.44 * _tt['T_FTA'] + _tt['T_TO'] - _tt['T_OREB']).clip(lower=0)
        
        _opp = _tt.merge(_tt, on=['Game_ID', 'Season'], suffixes=('', '_O'))
        _opp = _opp[_opp['Team Name'] != _opp['Team Name_O']].copy()
        _opp['ORtg'] = (np.where(_opp['T_Poss'] > 0, 100 * _opp['T_PTS'] / _opp['T_Poss'], 0)).round(1)
        _opp['DRtg'] = (np.where(_opp['T_Poss_O'] > 0, 100 * _opp['T_PTS_O'] / _opp['T_Poss_O'], 0)).round(1)
        _opp['NetRtg'] = (_opp['ORtg'] - _opp['DRtg']).round(1)
        _opp['Pace'] = ((_opp['T_Poss'] + _opp['T_Poss_O']) / 2).round(1)
        _opp['O2PA'] = (_opp['T_FGA_O'] - _opp['T_3PA_O']).clip(lower=0)
        
        _mcols = ['Game_ID', 'Season', 'Team Name', 'T_PTS', 'T_FGM', 'T_FGA', 'T_FTA', 'T_TO', 'T_REB', 'T_AST',
                  'T_OREB', 'T_DREB', 'T_Poss', 'T_REB_O', 'T_OREB_O', 'T_DREB_O', 'T_Poss_O', 'O2PA',
                  'ORtg', 'DRtg', 'NetRtg', 'Pace']
        df = df.merge(_opp[_mcols], on=_keys, how='left')
        
        df['OREB_est'] = np.where(df['T_REB'] > 0, (df['T_OREB'] * df['REB'] / df['T_REB']).round(), 0)
        df['DREB_est'] = (df['REB'] - df['OREB_est']).clip(lower=0)
        df['Poss'] = (df['FGA'] + 0.44 * df['FTA'] + df['TO'] - df['OREB_est']).clip(lower=0)
        df['PPP'] = (np.where(df['Poss'] > 0, df['PTS'] / df['Poss'], 0)).round(2)
        df['TOV%'] = (np.where(df['Poss'] > 0, df['TO'] / df['Poss'] * 100, 0)).round(1)
        df['EFF'] = (df['PTS'] + df['REB'] + df['AST'] + df['STL'] + df['BLK']
                     - (df['FGA'] - df['FGM']) - (df['FTA'] - df['FTM']) - df['TO'])
        df['Game_Score'] = (df['PTS'] + 0.4 * df['FGM'] - 0.7 * df['FGA'] - 0.4 * (df['FTA'] - df['FTM'])
                            + 0.7 * df['OREB_est'] + 0.3 * df['DREB_est'] + df['STL'] + 0.7 * df['AST']
                            + 0.7 * df['BLK'] - 0.4 * df['FOULS'] - df['TO']).round(1)
        df['USG%'] = (np.where(df['T_Poss'] > 0, df['Poss'] / df['T_Poss'] * 100, 0)).round(1)
        df['AST%'] = (np.where((df['T_FGM'] - df['FGM']) > 0, df['AST'] / (df['T_FGM'] - df['FGM']) * 100, 0)).round(1)
        df['TRB%'] = (np.where((df['T_REB'] + df['T_REB_O']) > 0, df['REB'] / (df['T_REB'] + df['T_REB_O']) * 100, 0)).round(1)
        
        # Recast standard analytical mappings
        df['FG%'] = np.where(df['FGA'] > 0, df['FGM'] / df['FGA'], 0)
        df['3P%'] = np.where(df['3PA'] > 0, df['3PM'] / df['3PA'], 0)
        df['TS%'] = np.where((df['FGA'] + 0.44 * df['FTA']) > 0, df['PTS'] / (2 * (df['FGA'] + 0.44 * df['FTA'])), 0)
        df['Impact'] = df['PIE_Raw']
        df.rename(columns={'Player/Team': 'PlayerName', 'Team Name': 'TeamName'}, inplace=True)
        
        return df
    except Exception as e:
        st.error(f"Failed to compile data from source sheet: {e}")
        return None

# --- 3. GRAPHICS ENGINE ---
def draw_basketball_court(ax):
    ax.set_facecolor('#d2ab71') 
    ax.plot([-250, 250], [-47.5, -47.5], color='white', lw=2) 
    ax.plot([-250, -250], [-47.5, 422.5], color='white', lw=2)
    ax.plot([250, 250], [-47.5, 422.5], color='white', lw=2)
    ax.plot([-80, -80], [-47.5, 143.5], color='white', lw=2)
    ax.plot([80, 80], [-47.5, 143.5], color='white', lw=2)
    ax.plot([-80, 80], [143.5, 143.5], color='white', lw=2)
    ax.plot([-220, -220], [-47.5, 92.5], color='white', lw=2)
    ax.plot([220, 220], [-47.5, 92.5], color='white', lw=2)
    arc = Arc((0, 0), 475, 475, theta1=22, theta2=158, color='white', lw=2); ax.add_patch(arc)
    ax.add_patch(Circle((0, 0), 7.5, color='#ff3333', fill=False, lw=2))
    ax.plot([-30, 30], [-7.5, -7.5], color='black', lw=2)

def draw_radar_chart(player_name, p_stats, lg_avg, era_title):
    cats = ['Scoring', 'Playmaking', 'Rebounding', 'Defense', 'Efficiency']
    N = len(cats)
    def norm(val, mx): return min(100, (max(0, val) / mx) * 100) if mx > 0 else 0
    mx = {'PTS': 40, 'AST': 15, 'REB': 25, 'DEF': 10, 'TS%': 100}
    
    p_vals = [norm(p_stats['PTS'], mx['PTS']), norm(p_stats['AST'], mx['AST']), norm(p_stats['REB'], mx['REB']), norm(p_stats['DEF'], mx['DEF']), norm(p_stats['TS%'], mx['TS%'])]
    p_vals += p_vals[:1]
    
    l_vals = [norm(lg_avg['PTS'], mx['PTS']), norm(lg_avg['AST'], mx['AST']), norm(lg_avg['REB'], mx['REB']), norm(lg_avg['DEF'], mx['DEF']), norm(lg_avg['TS%'], mx['TS%'])]
    l_vals += l_vals[:1]
    
    angles = [n / float(N) * 2 * math.pi for n in range(N)]
    angles += angles[:1]
    
    fig, ax = plt.subplots(figsize=(6, 6), subplot_kw=dict(polar=True))
    fig.patch.set_facecolor('#0e1117')
    ax.set_facecolor('#1f232d')
    
    ax.plot(angles, p_vals, linewidth=2, linestyle='solid', label=f"{player_name} ({era_title})", color='#d4af37')
    ax.fill(angles, p_vals, alpha=0.4, color='#d4af37')
    ax.plot(angles, l_vals, linewidth=2, linestyle='dashed', label='League Avg', color='#888888')
    
    plt.xticks(angles[:-1], cats, color='white', size=12)
    ax.set_yticklabels([])
    ax.spines['polar'].set_color('#444444')
    plt.legend(loc='upper right', bbox_to_anchor=(1.2, 1.1), facecolor='#0e1117', labelcolor='white')
    return fig

def draw_shot_chart(player_name, stats):
    fig, ax = plt.subplots(figsize=(6, 5.5))
    fig.patch.set_facecolor('#0e1117')
    draw_basketball_court(ax)
    np.random.seed(hash(player_name) % (2**32))
    fgm = int(stats.get('FGM', 0))
    tpm = int(stats.get('3PM', 0))
    paint_shots = max(0, fgm - tpm)
    
    for _ in range(tpm):
        angle = np.random.uniform(np.pi/8, 7*np.pi/8)
        dist = np.random.uniform(240, 280)
        ax.scatter(dist*np.cos(angle), dist*np.sin(angle), color='#00ff00', s=60, edgecolors='black', zorder=5, marker='X')
    for _ in range(paint_shots):
        angle = np.random.uniform(0, np.pi)
        dist = np.random.uniform(10, 140)
        ax.scatter(dist*np.cos(angle), dist*np.sin(angle), color='#00a2ff', s=45, alpha=0.9, edgecolors='white', zorder=4)
        
    ax.set_xlim(-260, 260)
    ax.set_ylim(-60, 400)
    ax.axis('off')
    return fig

# --- 4. ORACLE & BETTING SYSTEM (1287 Iterations Matrix) ---
def run_1287_monte_carlo(team1, team2, df):
    p_df = df[df['Type'].str.lower() == 'player'].copy()
    t_df = df[df['Type'].str.lower() == 'team'].copy()

    def get_top_players(team_name):
        fallback = p_df[p_df['TeamName'].str.lower() == team_name.lower()]
        if not fallback.empty:
            return fallback.groupby('PlayerName').sum(numeric_only=True).nlargest(5, 'Impact').index.tolist()
        return []

    t1_p = get_top_players(team1)
    t2_p = get_top_players(team2)
    
    if not t1_p and not t2_p: 
        return None, "Both teams are completely new to the database. Matrix construction cancelled."

    def get_opp_ppg(t_name):
        team_games = t_df[t_df['TeamName'].str.lower() == t_name.lower()]
        if not team_games.empty and 'PTS_Opp' in team_games.columns:
            val = team_games['PTS_Opp'].mean()
            if pd.notna(val) and val > 0: return val
        return 74.0

    bets = []
    t1_proj_score = np.zeros(1287)
    t2_proj_score = np.zeros(1287)
    
    if t1_p:
        for p in t1_p:
            logs = p_df[p_df['PlayerName'] == p].sort_values('Game_ID', ascending=False)
            if logs.empty: continue
            l5 = logs.head(5)
            pts_mean = (l5['PTS'].mean() * 0.6) + (logs['PTS'].mean() * 0.4)
            reb_mean = (l5['REB'].mean() * 0.6) + (logs['REB'].mean() * 0.4)
            ast_mean = (l5['AST'].mean() * 0.6) + (logs['AST'].mean() * 0.4)
            
            sim_pts = np.maximum(0, np.random.normal(pts_mean, logs['PTS'].std() if len(logs) > 2 else 3.0, 1287))
            sim_reb = np.maximum(0, np.random.normal(reb_mean, logs['REB'].std() if len(logs) > 2 else 2.0, 1287))
            sim_ast = np.maximum(0, np.random.normal(ast_mean, logs['AST'].std() if len(logs) > 2 else 2.0, 1287))
            
            t1_proj_score += sim_pts
            
            pts_line = math.ceil(np.median(sim_pts) * 2) / 2
            reb_line = math.ceil(np.median(sim_reb) * 2) / 2
            ast_line = math.ceil(np.median(sim_ast) * 2) / 2
            if pts_line > 2: bets.append(f"{p} O/U {pts_line} PTS")
            if reb_line > 1: bets.append(f"{p} O/U {reb_line} REB")
            if ast_line > 1: bets.append(f"{p} O/U {ast_line} AST")
    else:
        t2_allowed = get_opp_ppg(team2)
        t1_proj_score = np.maximum(0, np.random.normal(t2_allowed - 2.5, 5.0, 1287))

    if t2_p:
        for p in t2_p:
            logs = p_df[p_df['PlayerName'] == p].sort_values('Game_ID', ascending=False)
            if logs.empty: continue
            l5 = logs.head(5)
            pts_mean = (l5['PTS'].mean() * 0.6) + (logs['PTS'].mean() * 0.4)
            reb_mean = (l5['REB'].mean() * 0.6) + (logs['REB'].mean() * 0.4)
            ast_mean = (l5['AST'].mean() * 0.6) + (logs['AST'].mean() * 0.4)
            
            sim_pts = np.maximum(0, np.random.normal(pts_mean, logs['PTS'].std() if len(logs) > 2 else 3.0, 1287))
            sim_reb = np.maximum(0, np.random.normal(reb_mean, logs['REB'].std() if len(logs) > 2 else 2.0, 1287))
            sim_ast = np.maximum(0, np.random.normal(ast_mean, logs['AST'].std() if len(logs) > 2 else 2.0, 1287))
            
            t2_proj_score += sim_pts
            
            pts_line = math.ceil(np.median(sim_pts) * 2) / 2
            reb_line = math.ceil(np.median(sim_reb) * 2) / 2
            ast_line = math.ceil(np.median(sim_ast) * 2) / 2
            if pts_line > 2: bets.append(f"{p} O/U {pts_line} PTS")
            if reb_line > 1: bets.append(f"{p} O/U {reb_line} REB")
            if ast_line > 1: bets.append(f"{p} O/U {ast_line} AST")
    else:
        t1_allowed = get_opp_ppg(team1)
        t2_proj_score = np.maximum(0, np.random.normal(t1_allowed - 2.5, 5.0, 1287))

    median_t1 = np.median(t1_proj_score)
    median_t2 = np.median(t2_proj_score)
    
    spread = math.ceil(abs(median_t1 - median_t2) * 2) / 2
    if spread == 0: spread = 1.5
    fav, dog = (team1, team2) if median_t1 > median_t2 else (team2, team1)
    
    t1_prob = np.sum(t1_proj_score > t2_proj_score) / 1287
    juice = 1.08
    
    def ml_odds(prob):
        p = max(0.05, min(0.95, prob))
        return f"-{int(100 * (p / (1 - p)) * juice)}" if p >= 0.5 else f"+{int(100 * ((1 - p) / p) / juice)}"

    team1_ml = ml_odds(t1_prob)
    team2_ml = ml_odds(1 - t1_prob)
    total_line = math.ceil((median_t1 + median_t2) * 2) / 2

    lines_summary = {
        "t1_proj": int(median_t1),
        "t2_proj": int(median_t2),
        "t1_ml": team1_ml,
        "t2_ml": team2_ml,
        "spread_line": f"{fav} -{spread} / {dog} +{spread}",
        "total_line": total_line,
        "props": list(set(bets))[:15]
    }
    return lines_summary, "Success"

# --- 5. APPLICATION INTERFACE UI ---
full_df = load_and_process_stats()

if full_df is not None:
    st.sidebar.title("🏀 QSPN Hub Platform")
    
    # Global Filter Scope
    all_seasons = sorted([int(s) for s in full_df['Season'].dropna().unique()], reverse=True)
    scope_options = ["Eternal Record", "Latest Season"] + [f"Season {s}" for s in all_seasons]
    selected_scope = st.sidebar.selectbox("Analytical Split Horizon", scope_options)
    
    # Refine data frame based on user split scope choices
    df_working = full_df.copy()
    era_title = "Eternal Record"
    if selected_scope == "Latest Season":
        target_szn = int(full_df['Season'].max())
        df_working = df_working[df_working['Season'] == target_szn]
        era_title = f"Season {target_szn}"
    elif "Season" in selected_scope:
        target_szn = int(selected_scope.split(" ")[1])
        df_working = df_working[df_working['Season'] == target_szn]
        era_title = f"Season {target_szn}"

    app_mode = st.sidebar.radio("Navigation View Terminal", ["Scouting Profile", "Team Matrix", "Monte Carlo Oracle"])

    # ====== SCOUTING PROFILE VIEW ======
    if app_mode == "Scouting Profile":
        st.header("📋 Player Scouting Engine Split")
        player_list = sorted(df_working[df_working['Type'].str.lower() == 'player']['PlayerName'].dropna().unique())
        selected_player = st.selectbox("Select Target Operational Asset", player_list)
        
        if selected_player:
            p_data = df_working[(df_working['Type'].str.lower() == 'player') & (df_working['PlayerName'] == selected_player)]
            
            if not p_data.empty:
                # Compile Stats
                pts, reb, ast = p_data['PTS'].mean(), p_data['REB'].mean(), p_data['AST'].mean()
                stl, blk, pie = p_data['STL'].mean(), p_data['BLK'].mean(), p_data['PIE_Raw'].mean()
                gp_count = len(p_data)
                
                fga, fta, to = p_data['FGA'].mean(), p_data['FTA'].mean(), p_data['TO'].mean()
                fg_pct = (p_data['FGM'].sum() / p_data['FGA'].sum() * 100) if p_data['FGA'].sum() > 0 else 0.0
                tp_pct = (p_data['3PM'].sum() / p_data['3PA'].sum() * 100) if p_data['3PA'].sum() > 0 else 0.0
                ts_pct = (p_data['PTS'].sum() / (2 * (p_data['FGA'].sum() + 0.44 * p_data['FTA'].sum())) * 100) if (p_data['FGA'].sum() + 0.44 * p_data['FTA'].sum()) > 0 else 0.0
                
                # Metrics Banner
                m1, m2, m3, m4, m5 = st.columns(5)
                m1.metric("Impact (PIE)", f"{pie:.1f}")
                m2.metric("Scoring Production", f"{pts:.1f} PPG")
                m3.metric("Playmaking Asset", f"{ast:.1f} APG")
                m4.metric("Glass Control", f"{reb:.1f} RPG")
                m5.metric("Sample Vol (GP)", f"{int(gp_count)}")
                
                st.markdown("---")
                
                c1, c2 = st.columns(2)
                with c1:
                    st.subheader("Base Metric Volatility Matrix")
                    st.text(f"PTS: {pts:.1f}  | REB: {reb:.1f} | AST: {ast:.1f}")
                    st.text(f"STL: {stl:.1f}  | BLK: {blk:.1f} | TO: {to:.1f}")
                    st.text(f"FG%: {fg_pct:.1f}% | 3P%: {tp_pct:.1f}% | TS%: {ts_pct:.1f}%")
                    
                    st.subheader("Identity Tracker Values")
                    st.write(f"🔹 **Tipped Passes (Est):** {int(p_data['Tipped_Passes'].mean())}")
                    st.write(f"🔹 **Shots Affected (Est):** {int(p_data['Shots_Affected'].mean())}")
                    st.write(f"🔹 **Fast Break Points (Est):** {int(p_data['FB_Points'].mean())}")
                
                with c2:
                    # Construct matching averages for radar boundary lines
                    p_df_all = df_working[df_working['Type'].str.lower() == 'player']
                    lg_df = p_df_all.groupby('PlayerName').mean(numeric_only=True)
                    lg_avg = {'PTS': lg_df['PTS'].mean(), 'AST': lg_df['AST'].mean(), 'REB': lg_df['REB'].mean(), 'DEF': lg_df['STL'].mean()+lg_df['BLK'].mean(), 'TS%': 55.0}
                    p_stats = {'PTS': pts, 'AST': ast, 'REB': reb, 'DEF': stl+blk, 'TS%': ts_pct}
                    
                    radar_fig = draw_radar_chart(selected_player, p_stats, lg_avg, era_title)
                    st.pyplot(radar_fig)
                    
                st.markdown("---")
                st.subheader("Interactive Shot Map Footprint")
                shot_fig = draw_shot_chart(selected_player, {'FGM': p_data['FGM'].sum(), '3PM': p_data['3PM'].sum()})
                st.pyplot(shot_fig)

    # ====== TEAM MATRIX VIEW ======
    elif app_mode == "Team Matrix":
        st.header("🗂️ Franchise Matrix Systems")
        team_list = sorted(df_working[df_working['Type'].str.lower() == 'team']['TeamName'].dropna().unique())
        selected_team = st.selectbox("Select Focus Franchise Portfolio", team_list)
        
        if selected_team:
            t_data = df_working[(df_working['Type'].str.lower() == 'team') & (df_working['TeamName'] == selected_team)]
            p_data_t = df_working[(df_working['Type'].str.lower() == 'player') & (df_working['TeamName'] == selected_team)]
            
            if not t_data.empty:
                wins = int(t_data['Win'].sum())
                losses = len(t_data) - wins
                wpct = (wins / len(t_data)) * 100
                
                col1, col2, col3 = st.columns(3)
                col1.metric("Record Profile", f"{wins}W - {losses}L")
                col2.metric("Point Production Average", f"{t_data['PTS'].mean():.1f} PPG")
                col3.metric("Win Pct Efficiency", f"{wpct:.1f}%")
                
                st.subheader("Roster Analytical Output Split")
                roster_summary = p_data_t.groupby('PlayerName').agg({
                    'PTS': 'mean', 'REB': 'mean', 'AST': 'mean', 'STL': 'mean', 'BLK': 'mean', 'Impact': 'sum'
                }).rename(columns={
                    'PTS': 'PPG', 'REB': 'RPG', 'AST': 'APG', 'STL': 'SPG', 'BLK': 'BPG', 'Impact': 'Total Impact Value'
                })
                st.dataframe(roster_summary.style.format(precision=1), use_container_width=True)

    # ====== MONTE CARLO ORACLE VIEW ======
    elif app_mode == "Monte Carlo Oracle":
        st.header("🧠 QSPN Monte Carlo Projection Engine")
        team_list = sorted(full_df[full_df['Type'].str.lower() == 'team']['TeamName'].dropna().unique())
        
        c1, c2 = st.columns(2)
        t1 = c1.selectbox("Home / Franchise Asset Alpha", team_list, index=0)
        t2 = c2.selectbox("Away / Franchise Asset Beta", team_list, index=min(1, len(team_list)-1))
        
        if st.button("Execute 1,287 Simulation Runs"):
            if t1 == t2:
                st.warning("Identity loop detected. Please configure unique opponents.")
            else:
                with st.spinner("Processing projection arrays across rolling matrices..."):
                    lines, msg = run_1287_monte_carlo(t1, t2, full_df)
                    
                    if lines:
                        st.success("Simulation parameters locked. Projections outputted successfully.")
                        
                        o1, o2 = st.columns(2)
                        with o1:
                            st.subheader("Projected Sharp Score Outcomes")
                            st.metric(f"{t1} Score Proj", lines['t1_proj'])
                            st.metric(f"{t2} Score Proj", lines['t2_proj'])
                            
                            st.subheader("Opening Market Vectors")
                            st.write(f"🎫 **{t1} Moneyline:** `{lines['t1_ml']}`")
                            st.write(f"🎫 **{t2} Moneyline:** `{lines['t2_ml']}`")
                            st.write(f"📊 **Calculated Handicap Spread:** `{lines['spread_line']}`")
                            st.write(f"🎯 **Game O/U Total Line:** `{lines['total_line']}`")
                        
                        with o2:
                            st.subheader("Derivative Projections (Player Matrix)")
                            for prop in lines['props']:
                                st.write(f"▫️ {prop}")
                    else:
                        st.error(msg)
else:
    st.info("System initializing... Synchronizing cloud connections.")
