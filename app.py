import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import random
import re

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
    .flip-card-front, .flip-card-back { position: absolute; width: 100%; height: 100%; -webkit-backface-visibility: hidden; backface-visibility: hidden; border-radius: 12px; border: 3px solid #d4af37; box-shadow: 0 10px 30px rgba(0,0,0,0.5); }
    .flip-card-front { background: linear-gradient(145deg, #1c2128, #2a2d35); display: flex; flex-direction: column; justify-content: center; align-items: center; padding: 20px;}
    .flip-card-back { background-color: #161b22; color: white; transform: rotateY(180deg); padding: 15px; overflow-y: auto; text-align: left; }
    .stat-row { display: flex; justify-content: space-between; border-bottom: 1px dashed #333; padding: 6px 0; font-size: 13px; }
    .stat-val { font-weight: bold; color: #d4af37; }
    .stat-label { color: #8b949e; }
    .sim-box { background: #161b22; padding: 20px; border-radius: 10px; border: 2px solid #d4af37; text-align: center; box-shadow: 0 5px 15px rgba(0,0,0,0.5); margin-bottom: 20px; }
    
    /* Metrics Box */
    .metric-box { background: #2a2d35; border-left: 5px solid #d4af37; padding: 15px; border-radius: 5px; margin-bottom: 15px; text-align: center; }
    .metric-title { font-size: 14px; color: #aaa; text-transform: uppercase; }
    .metric-value { font-size: 24px; font-weight: bold; color: #fff; }
</style>
"""
st.markdown(css_styles, unsafe_allow_html=True)

# --- 2. DATA ENGINE ---
SHEET_ID = "1rksLYUcXQJ03uTacfIBD6SRsvtH-IE6djqT-LINwcH4"
URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"

def smart_name_scrubber(raw_name):
    if pd.isna(raw_name) or not isinstance(raw_name, str): return raw_name
    clean_name = re.sub(r'^[|Il\s]+', '', raw_name)
    clean_name = re.sub(r'^\[.*?\]\s*|^\(.*?\)\s*', '', clean_name)
    clean_name = clean_name.strip().title()
    
    typo_map = {
        "Tae": ["tae_", "taee", "t a e", "tae1"],
        "Buzz My PF": ["buzzmypf", "buzz_my_pf", "buzz my pf", "buzz my_pf"],
        "John Smith": ["johnsm1th", "j_smith", "john s"]
    }
    test_name = clean_name.lower()
    for official_name, typos in typo_map.items():
        if test_name in typos: return official_name
    return clean_name

@st.cache_data(ttl=60)
def load_data():
    try:
        # Pulling live data from the Google Sheet
        df = pd.read_csv(URL)
        df.columns = df.columns.str.strip()
        
        if 'Player/Team' in df.columns: df['Player/Team'] = df['Player/Team'].apply(smart_name_scrubber)
            
        req_cols = ['PTS', 'REB', 'AST', 'STL', 'BLK', 'TO', 'FGA', 'FGM', '3PM', '3PA', 'FTA', 'FTM', 'Game_ID', 'Win', 'Season', 'Type', 'Team Name']
        for c in req_cols:
            if c not in df.columns: df[c] = 0
            if c not in ['Type', 'Team Name', 'Player/Team']: df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)
            
        if 'Win' in df.columns: df['Win'] = pd.to_numeric(df['Win'], errors='coerce').fillna(0).apply(lambda x: 1 if x > 0 else 0)
        df['is_ff'] = (df['PTS'] == 0) & (df['FGA'] == 0) & (df['REB'] == 0)
        
        def calc_multis(row):
            if row['is_ff']: return pd.Series([0, 0])
            s = [row['PTS'], row['REB'], row['AST'], row['STL'], row['BLK']]
            tens = sum(1 for x in s if x >= 10)
            return pd.Series([1 if tens >= 2 else 0, 1 if tens >= 3 else 0])
        df[['DD', 'TD']] = df.apply(calc_multis, axis=1)
        
        df['PIE_Raw'] = (df['PTS'] + df['REB'] + df['AST'] + df['STL'] + df['BLK']) - (df['FGA'] * 0.5) - df['TO']
        df['Poss_Raw'] = df['FGA'] + 0.44 * df['FTA'] + df['TO']

        # --- ADVANCED PROXY METRICS & OPPONENT STATS PIPELINE ---
        df['Game_ID'] = pd.to_numeric(df['Game_ID'], errors='coerce')
        df['Game_Type'] = np.where(df['Game_ID'] >= 9000, 'Playoffs', 
                          np.where(df['Game_ID'] >= 8000, 'Tournament', 'Regular Season'))

        players_df = df[df['Type'].astype(str).str.lower() == 'player'].copy()
        players_df['Position_Num'] = players_df.groupby(['Game_ID', 'Team Name']).cumcount() + 1
        
        if 'FOULS' not in players_df.columns: players_df['FOULS'] = 0

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
        
        players_df['FB_Points'] = players_df[['FB_Points', 'PTS']].min(axis=1)

        df = df.merge(
            players_df[['Game_ID', 'Team Name', 'Player/Team', 'Tipped_Passes', 'Shots_Affected', 'FB_Points']],
            on=['Game_ID', 'Team Name', 'Player/Team'], how='left'
        )

        team_proxy_totals = df[df['Type'].astype(str).str.lower() == 'player'].groupby(['Game_ID', 'Team Name'])[['Tipped_Passes', 'Shots_Affected', 'FB_Points']].sum().reset_index()
        for col in ['Tipped_Passes', 'Shots_Affected', 'FB_Points']:
            df.loc[df['Type'].astype(str).str.lower() == 'team', col] = df.loc[df['Type'].astype(str).str.lower() == 'team'].set_index(['Game_ID', 'Team Name']).index.map(
                team_proxy_totals.set_index(['Game_ID', 'Team Name'])[col]
            ).fillna(0)

        team_game_logs = df[df['Type'].astype(str).str.lower() == 'team'][['Game_ID', 'Team Name', 'PTS', 'FGM', 'FGA', '3PM', '3PA', 'TO', 'FTA']].copy()
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
    except Exception as e: return str(e)

full_df = load_data()

# --- 2B. GLOBAL MILESTONE & CLUB TRACKER ---
if not isinstance(full_df, str):
    global_players = full_df[full_df['Type'].astype(str).str.lower() == 'player'].copy()
    season_totals = global_players.groupby(['Player/Team', 'Season']).sum(numeric_only=True).reset_index()

    def calc_clubs(row):
        clubs = []
        # Exclusive Clubs Tracker
        if row['REB'] >= 40 and row['STL'] >= 40 and row['AST'] >= 40: clubs.append(f"40/40/40 (S{int(row['Season'])})")
        elif row['REB'] >= 30 and row['STL'] >= 30 and row['AST'] >= 30: clubs.append(f"30/30/30 (S{int(row['Season'])})")
        if row['PTS'] >= 300 and row['3PM'] >= 100: clubs.append(f"300Pts/100 3s (S{int(row['Season'])})")
        if row['PTS'] >= 100 and row['REB'] >= 100: clubs.append(f"100Pts/100Reb (S{int(row['Season'])})")
        return clubs

    season_totals['Clubs'] = season_totals.apply(calc_clubs, axis=1)
    player_clubs = season_totals.groupby('Player/Team')['Clubs'].agg(lambda x: [item for sublist in x for item in sublist if item]).reset_index()

# --- 3. HTML & CHART GENERATORS ---
def generate_2k_player_card(player_name, stats, rank=""):
    rank_badge = f'<div style="position:absolute; top:-10px; right:-10px; background:#d4af37; color:#000; font-weight:bold; padding:8px; border-radius:50%; border:2px solid #fff; z-index:10;">#{rank}</div>' if rank else ""
    
    # Render Milestone Club Badges
    clubs_html = ""
    if 'Clubs' in stats and isinstance(stats['Clubs'], list) and len(stats['Clubs']) > 0:
        badges = "".join([f"<span style='background:#d4af37; color:#000; font-size:10px; font-weight:bold; padding:3px 5px; border-radius:4px; margin:2px; display:inline-block;'>{c}</span>" for c in stats['Clubs']])
        clubs_html = f"<div style='margin-top:10px; padding-top:8px; border-top:1px dashed #444; width:100%;'>{badges}</div>"

    return f'''<div class="flip-card" style="height: 380px;">
{rank_badge}
<div class="flip-card-inner">
<div class="flip-card-front">
<img src="https://upload.wikimedia.org/wikipedia/commons/7/7c/Profile_avatar_placeholder_large.png" style="width: 90px; border-radius: 50%; border: 2px solid #d4af37; margin-bottom: 10px;">
<h3 style="margin: 0; color: white; font-size: 18px;">{player_name}</h3>
<h2 style="color: #d4af37; margin-top: 5px; margin-bottom: 5px;">{stats.get('PIE', 0):.1f} PIE</h2>
{clubs_html}
</div>
<div class="flip-card-back">
<h4 style="color: #d4af37; border-bottom: 1px solid #333; padding-bottom: 3px; margin-top: 0; font-size: 14px;">Season Averages & Highs</h4>
<div class="stat-row"><span class="stat-label">GP</span> <span class="stat-val">{int(stats.get('GP', 0))}</span></div>
<div class="stat-row"><span class="stat-label">PPG | RPG | APG</span> <span class="stat-val">{stats.get('PTS/G', 0):.1f} | {stats.get('REB/G', 0):.1f} | {stats.get('AST/G', 0):.1f}</span></div>
<div class="stat-row"><span class="stat-label">GAME HIGHS</span> <span class="stat-val" style="color:#fff;">{int(stats.get('High_PTS', 0))}P | {int(stats.get('High_REB', 0))}R | {int(stats.get('High_AST', 0))}A</span></div>
<div class="stat-row"><span class="stat-label">STOCKS (Def)</span> <span class="stat-val">{stats.get('DEF', 0):.1f}</span></div>
<div class="stat-row"><span class="stat-label">DEF HIGHS</span> <span class="stat-val">{int(stats.get('High_STL', 0))}S | {int(stats.get('High_BLK', 0))}B</span></div>
<div class="stat-row"><span class="stat-label">FG% | 3P%</span> <span class="stat-val">{stats.get('FG%', 0):.1f}% | {stats.get('3P%', 0):.1f}%</span></div>
<div class="stat-row"><span class="stat-label">TS% | eFG%</span> <span class="stat-val">{stats.get('TS%', 0):.1f}% | {stats.get('eFG%', 0):.1f}%</span></div>
<div class="stat-row"><span class="stat-label">FB Pts | Shots Aff.</span> <span class="stat-val">{stats.get('FB_Points/G', 0):.1f} | {stats.get('Shots_Affected/G', 0):.1f}</span></div>
</div>
</div>
</div>'''

def generate_2k_player_row(player_name, rank, gp, ppg, rpg, apg, stocks, fg, ts, pie):
    color = "#ffd700" if rank == 1 else "#c0c0c0" if rank == 2 else "#cd7f32" if rank == 3 else "#00bfff"
    return f"""<div style="background: linear-gradient(145deg, #1c2128, #2a2d35); border-left: 6px solid {color}; border-radius: 8px; padding: 15px; margin-bottom: 12px; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 4px 6px rgba(0,0,0,0.3);">
<div style="display: flex; align-items: center; width: 25%;">
<h2 style="margin:0; color:{color}; margin-right: 20px; font-size: 28px; font-family: 'Arial Black', sans-serif;">#{int(rank)}</h2>
<div>
<h3 style="margin:0; color:white; font-size: 18px; text-transform: uppercase;">{player_name}</h3>
<div style="font-size: 14px; color: #aaa; margin-top: 2px;">GP: <span style="color:#fff; font-weight:bold;">{int(gp)}</span></div>
</div>
</div>
<div style="display: flex; width: 55%; justify-content: space-around; text-align: center;">
<div><div style="font-size:11px; color:#888; text-transform:uppercase;">PPG</div><div style="font-size:16px; font-weight:bold; color:#fff;">{ppg:.1f}</div></div>
<div><div style="font-size:11px; color:#888; text-transform:uppercase;">RPG</div><div style="font-size:16px; font-weight:bold; color:#fff;">{rpg:.1f}</div></div>
<div><div style="font-size:11px; color:#888; text-transform:uppercase;">APG</div><div style="font-size:16px; font-weight:bold; color:#fff;">{apg:.1f}</div></div>
<div><div style="font-size:11px; color:#888; text-transform:uppercase;">STOCKS</div><div style="font-size:16px; font-weight:bold; color:#fff;">{stocks:.1f}</div></div>
<div><div style="font-size:11px; color:#888; text-transform:uppercase;">FG%</div><div style="font-size:16px; font-weight:bold; color:#fff;">{fg:.1f}%</div></div>
<div><div style="font-size:11px; color:#888; text-transform:uppercase;">TS%</div><div style="font-size:16px; font-weight:bold; color:#fff;">{ts:.1f}%</div></div>
</div>
<div style="text-align: right; width: 20%;">
<div style="font-size: 11px; color: #888; text-transform: uppercase; font-weight: bold;">PIE Rating</div>
<div style="font-size: 24px; font-weight: bold; color: #d4af37;">{pie:.1f}</div>
</div>
</div>"""

def generate_mini_leaderboard(title, df, stat_col, color="#d4af37", top_n=5):
    html = f"<div style='background:#1c2128; padding:15px; border-radius:8px; border-left:4px solid {color}; margin-bottom:15px; box-shadow: 0 4px 6px rgba(0,0,0,0.3);'>"
    html += f"<h3 style='margin-top:0; color:#fff; font-size:16px; border-bottom:1px dashed #444; padding-bottom:8px; text-transform:uppercase;'>{title}</h3>"
    
    # Internal sorting to ensure accuracy
    sorted_df = df.sort_values(by=stat_col, ascending=False).head(top_n)
    
    for i, (_, row) in enumerate(sorted_df.iterrows()):
        val = row[stat_col]
        if pd.isna(val): continue
        
        # Formatting (Drop decimals if it is an exact integer)
        if val == int(val): val_str = f"{int(val)}"
        else: val_str = f"{val:.1f}"
            
        rank_color = "#ffd700" if i == 0 else "#888"
        
        # Auto-detect if it is a Player Name or Team Name
        name = row.get('Player/Team')
        if pd.isna(name) or name == 0 or str(name).strip() == '':
            name = row.get('Team Name', 'Unknown')
        
        html += f"<div style='display:flex; justify-content:space-between; align-items:center; margin-bottom:6px; font-size:14px;'>"
        html += f"<div><span style='color:{rank_color}; font-weight:bold; margin-right:8px;'>{i+1}.</span><span style='color:#ddd; font-weight:bold;'>{name}</span></div>"
        html += f"<span style='color:{color}; font-weight:bold;'>{val_str}</span>"
        html += f"</div>"
    html += "</div>"
    return html

def draw_dynamic_radar(p1_name, r1_vals, p2_name, r2_vals, categories, title):
    r1_vals = list(r1_vals) + [r1_vals[0]]
    r2_vals = list(r2_vals) + [r2_vals[0]]
    cats = list(categories) + [categories[0]]
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(r=r1_vals, theta=cats, fill='toself', name=p1_name, fillcolor='rgba(212, 175, 55, 0.4)', line=dict(color='#d4af37', width=2)))
    fig.add_trace(go.Scatterpolar(r=r2_vals, theta=cats, fill='toself', name=p2_name, fillcolor='rgba(204, 0, 0, 0.4)', line=dict(color='#cc0000', width=2)))
    fig.update_layout(title=dict(text=title, font=dict(color='white', size=16)), polar=dict(radialaxis=dict(visible=True, range=[0, 100], showticklabels=False, gridcolor='#444')), showlegend=True, template="plotly_dark", height=380, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', margin=dict(l=40, r=40, t=60, b=40))
    return fig

# --- 4. APP LOGIC & NAVIGATION ROUTING ---
if isinstance(full_df, str): 
    st.error(f"⚠️ DATA ERROR: {full_df}")
elif full_df is not None and not full_df.empty:
    
    seasons = sorted([int(s) for s in full_df['Season'].dropna().unique() if int(s) > 0], reverse=True)
    st.sidebar.title("⚙️ Hub Controls")
    view_mode = st.sidebar.radio("Navigation", [
        "🏠 League Home", 
        "🏆 Standings", 
        "📖 Record Book & Milestones", 
        "🏢 Team Pages", 
        "🗃️ Full Player Database", 
        "🔬 Advanced Analytics", 
        "⚔️ Head-to-Head Radar", 
        "🔮 Oracle Predictor", 
        "🏦 The Vault"
    ])
    st.sidebar.divider()
    scope_opts = [f"Season {s}" for s in seasons] + ["Career Stats"]
    selected_scope = st.sidebar.selectbox("Data Scope", scope_opts, index=0)
    
    if selected_scope == "Career Stats":
        df_active = full_df; banner_text = "CAREER TOTALS"
    else:
        target_season = int(selected_scope.replace("Season ", ""))
        df_active = full_df[full_df['Season'] == target_season]; banner_text = f"SEASON {target_season}"

    st.markdown(f'<div class="header-banner">🏀 SPAM LEAGUE HUB - {banner_text}</div>', unsafe_allow_html=True)

    # PLAYER STATS CALCULATION
    df_reg = df_active[df_active['Type'].astype(str).str.lower() == 'player'] if 'Type' in df_active.columns else df_active
    if not df_reg.empty:
        p_gp = df_reg.groupby('Player/Team')['Game_ID'].nunique().reset_index().rename(columns={'Game_ID': 'GP'})
        latest_teams = df_reg.sort_values('Season', ascending=False).groupby('Player/Team')['Team Name'].first().reset_index()
        p_stats = df_reg.groupby('Player/Team').mean(numeric_only=True).reset_index()
        p_stats = p_stats.merge(latest_teams, on='Player/Team', how='left')
        p_stats = p_stats.merge(p_gp, on='Player/Team', how='left')
        
        # Merge Clubs & Badges
        p_stats = p_stats.merge(player_clubs, on='Player/Team', how='left')

        # Calculate Individual Single Game Highs
        p_highs = df_reg.groupby('Player/Team').agg(
            High_PTS=('PTS', 'max'),
            High_REB=('REB', 'max'),
            High_AST=('AST', 'max'),
            High_STL=('STL', 'max'),
            High_BLK=('BLK', 'max'),
            High_3PM=('3PM', 'max')
        ).reset_index()
        p_stats = p_stats.merge(p_highs, on='Player/Team', how='left')

        # Add advanced proxies to the core variables 
        for col in ['PTS', 'REB', 'AST', 'STL', 'BLK', '3PM', '3PA', 'TO', 'FGA', 'FGM', 'FTA', 'FTM', 'Poss_Raw', 'FB_Points', 'Tipped_Passes', 'Shots_Affected']: 
            if col in p_stats.columns: p_stats[f'{col}/G'] = p_stats[col].round(1)

        p_stats['FG%'] = (p_stats['FGM'] / p_stats['FGA'].replace(0,1) * 100).round(1)
        p_stats['3P%'] = (p_stats['3PM'] / p_stats['3PA'].replace(0,1) * 100).round(1)
        p_stats['FT%'] = (p_stats['FTM'] / p_stats['FTA'].replace(0,1) * 100).round(1)
        p_stats['eFG%'] = ((p_stats['FGM'] + 0.5 * p_stats['3PM']) / p_stats['FGA'].replace(0,1) * 100).round(1)
        p_stats['TS%'] = (p_stats['PTS'] / (2 * (p_stats['FGA'] + 0.44 * p_stats['FTA']).replace(0, 1)) * 100).round(1)
        p_stats['AST/TO'] = (p_stats['AST'] / p_stats['TO'].replace(0, 0.1)).round(2)
        p_stats['PIE'] = p_stats['PIE_Raw'].round(1)
        p_stats['PPP'] = (p_stats['PTS'] / p_stats['Poss_Raw'].replace(0, 1)).round(2) 
        p_stats['DEF'] = p_stats['STL/G'] + p_stats['BLK/G']
        
        p_stats = p_stats.sort_values('PIE', ascending=False).reset_index(drop=True)
        p_stats['League_Rank'] = p_stats.index + 1

        max_league_gp = p_stats['GP'].max()
        qualifying_gp_min = max_league_gp * 0.6 if pd.notna(max_league_gp) else 0
        qualified_p_stats = p_stats[p_stats['GP'] >= qualifying_gp_min].copy()
        if qualified_p_stats.empty: qualified_p_stats = p_stats 

    # TEAM STATS CALCULATION
    t_stats = pd.DataFrame()
    if 'Type' in df_active.columns:
        team_df = df_active[df_active['Type'].astype(str).str.lower() == 'team']
        team_df = team_df[(team_df['Team Name'].astype(str) != '0') & (team_df['Team Name'].notna())]
        if not team_df.empty:
            t_stats = team_df.groupby('Team Name').sum(numeric_only=True).reset_index()
            t_stats['GP'] = team_df.groupby('Team Name')['Game_ID'].nunique().values
            t_stats['Win %'] = (t_stats['Win'] / t_stats['GP'].replace(0, 1) * 100).round(1)
            for col in ['PTS', 'REB', 'AST', 'STL', 'BLK', '3PM', '3PA', 'TO', 'FGA', 'FGM', 'FTA', 'FTM', 'Poss_Raw']: t_stats[f'{col}/G'] = (t_stats[col] / t_stats['GP']).round(1)
            t_stats['FG%'] = (t_stats['FGM'] / t_stats['FGA'].replace(0,1) * 100).round(1)
            t_stats['3P%'] = (t_stats['3PM'] / t_stats['3PA'].replace(0,1) * 100).round(1)
            t_stats['FT%'] = (t_stats['FTM'] / t_stats['FTA'].replace(0,1) * 100).round(1)
            t_stats['eFG%'] = ((t_stats['FGM'] + 0.5 * t_stats['3PM']) / t_stats['FGA'].replace(0,1) * 100).round(1)
            t_stats['TS%'] = (t_stats['PTS'] / (2 * (t_stats['FGA'] + 0.44 * t_stats['FTA']).replace(0, 1)) * 100).round(1)
            t_stats['AST/TO'] = (t_stats['AST'] / t_stats['TO'].replace(0, 0.1)).round(2)
            t_stats['OffRtg'] = (t_stats['PTS'] / t_stats['Poss_Raw'].replace(0, 1)) * 100
            t_stats['DEF'] = t_stats['STL/G'] + t_stats['BLK/G']

    # --- ROUTING ENGINE ---
    if view_mode == "🏠 League Home":
        st.subheader("👑 Official League Leaders (60% GP Qualifier)")
        c1, c2, c3, c4, c5 = st.columns(5)
        with c1: st.markdown(generate_mini_leaderboard("Points", qualified_p_stats, 'PTS/G', color="#cc0000"), unsafe_allow_html=True)
        with c2: st.markdown(generate_mini_leaderboard("Assists", qualified_p_stats, 'AST/G', color="#00bfff"), unsafe_allow_html=True)
        with c3: st.markdown(generate_mini_leaderboard("Rebounds", qualified_p_stats, 'REB/G', color="#32cd32"), unsafe_allow_html=True)
        with c4: st.markdown(generate_mini_leaderboard("Steals", qualified_p_stats, 'STL/G', color="#ff8c00"), unsafe_allow_html=True)
        with c5: st.markdown(generate_mini_leaderboard("Blocks", qualified_p_stats, 'BLK/G', color="#8a2be2"), unsafe_allow_html=True)

    elif view_mode == "🏆 Standings":
        st.subheader(f"🏆 {banner_text} Standings & Advanced Metrics")
        
        col1, col2 = st.columns(2)
        with col1:
            st_type = st.selectbox("Game Type Filter", ['All', 'Regular Season', 'Tournament', 'Playoffs'], key='standings_type')
        with col2:
            st_sort = st.selectbox("Sort By", ["Wins", "Point Differential", "Defensive Rating (Opp PPP)", "Offensive PPG"])

        standings_df = df_active[(df_active['Type'].astype(str).str.lower() == 'team')]
        if st_type != 'All': standings_df = standings_df[standings_df['Game_Type'] == st_type]

        if standings_df.empty:
            st.warning("No data found for this selection.")
        else:
            team_aggs = standings_df.groupby('Team Name').agg(
                Games=('Game_ID', 'nunique'), Wins=('Win', 'sum'), PPG=('PTS', 'mean'), Diff=('Point_Diff', 'mean'),
                Opp_FG=('Opp_FG%', 'mean'), Opp_3P=('Opp_3P%', 'mean'), Opp_PPP=('Opp_PPP', 'mean')
            ).reset_index()

            team_aggs['Win%'] = (team_aggs['Wins'] / team_aggs['Games'].replace(0,1)) * 100
            
            if st_sort == "Wins": team_aggs = team_aggs.sort_values(by=['Win%', 'Diff'], ascending=[False, False])
            elif st_sort == "Point Differential": team_aggs = team_aggs.sort_values(by=['Diff'], ascending=[False])
            elif st_sort == "Defensive Rating (Opp PPP)": team_aggs = team_aggs.sort_values(by=['Opp_PPP'], ascending=[True])
            else: team_aggs = team_aggs.sort_values(by=['PPG'], ascending=[False])
                
            cols = st.columns(4)
            for idx, row in team_aggs.reset_index(drop=True).iterrows():
                with cols[idx % 4]:
                    st.markdown(f"""
                    <div class="flip-card" style="height: 250px;">
                      <div class="flip-card-inner">
                        <div class="flip-card-front" style="background: linear-gradient(135deg, #1f1f1f, #333); border: 2px solid #d4af37; border-radius: 10px; display: flex; flex-direction: column; justify-content: center;">
                          <h2 style="color: #d4af37; margin:0; font-size:22px;">{row['Team Name']}</h2>
                          <h1 style="margin: 10px 0; font-size:36px;">{int(row['Wins'])} - {int(row['Games'] - row['Wins'])}</h1>
                          <p style="color: #aaa; margin:0;">Point Diff: {row['Diff']:+.1f}</p>
                          <p style="color: #aaa; margin-top:15px; font-size:12px;">Hover for Advanced Stats ⤵</p>
                        </div>
                        <div class="flip-card-back" style="background: linear-gradient(135deg, #d4af37, #b8860b); color: #000; border-radius: 10px; display: flex; flex-direction: column; justify-content: center; text-align: left; padding: 20px;">
                          <h4 style="border-bottom: 1px solid #000; padding-bottom: 5px; margin-top:0;">Advanced Metrics</h4>
                          <p style="margin:4px 0;"><b>Opp FG%:</b> {row['Opp_FG']:.1f}%</p>
                          <p style="margin:4px 0;"><b>Opp 3P%:</b> {row['Opp_3P']:.1f}%</p>
                          <p style="margin:4px 0;"><b>Opp PPP:</b> {row['Opp_PPP']:.2f}</p>
                          <p style="margin:4px 0;"><b>PPG:</b> {row['PPG']:.1f}</p>
                        </div>
                      </div>
                    </div>
                    """, unsafe_allow_html=True)

    elif view_mode == "📖 Record Book & Milestones":
        st.subheader(f"📖 {banner_text} Record Book & Milestones")
        
        tab_game, tab_miles = st.tabs(["🔥 Single Game Records", "🏔️ Milestone Tracker (Totals)"])
        
        with tab_game:
            st.markdown("### 🏆 Individual Single Game Highs")
            p_df = df_active[df_active['Type'].astype(str).str.lower() == 'player'].copy()
            
            c1, c2, c3 = st.columns(3)
            with c1:
                st.markdown(generate_mini_leaderboard("Points in a Game", p_df, 'PTS', color="#cc0000"), unsafe_allow_html=True)
                st.markdown(generate_mini_leaderboard("Steals in a Game", p_df, 'STL', color="#ff8c00"), unsafe_allow_html=True)
            with c2:
                st.markdown(generate_mini_leaderboard("Rebounds in a Game", p_df, 'REB', color="#32cd32"), unsafe_allow_html=True)
                st.markdown(generate_mini_leaderboard("Blocks in a Game", p_df, 'BLK', color="#8a2be2"), unsafe_allow_html=True)
            with c3:
                st.markdown(generate_mini_leaderboard("Assists in a Game", p_df, 'AST', color="#00bfff"), unsafe_allow_html=True)
                st.markdown(generate_mini_leaderboard("3-Pointers in a Game", p_df, '3PM', color="#d4af37"), unsafe_allow_html=True)

            st.markdown("### 🏢 Team Single Game Records")
            t_df = df_active[df_active['Type'].astype(str).str.lower() == 'team'].copy()
            if not t_df.empty:
                c4, c5, c6 = st.columns(3)
                with c4: st.markdown(generate_mini_leaderboard("Team Points", t_df, 'PTS', color="#cc0000"), unsafe_allow_html=True)
                with c5: st.markdown(generate_mini_leaderboard("Team Rebounds", t_df, 'REB', color="#32cd32"), unsafe_allow_html=True)
                with c6: st.markdown(generate_mini_leaderboard("Team Assists", t_df, 'AST', color="#00bfff"), unsafe_allow_html=True)

        with tab_miles:
            st.markdown("### 🏔️ All-Time Milestones & Totals Leaders")
            p_totals = p_df.groupby('Player/Team').sum(numeric_only=True).reset_index()
            t_totals = t_df.groupby('Team Name').sum(numeric_only=True).reset_index()
            
            st.markdown("#### Player Milestones")
            mc1, mc2, mc3 = st.columns(3)
            with mc1: st.markdown(generate_mini_leaderboard("Total Points", p_totals, 'PTS', color="#cc0000", top_n=10), unsafe_allow_html=True)
            with mc2: st.markdown(generate_mini_leaderboard("Total Rebounds", p_totals, 'REB', color="#32cd32", top_n=10), unsafe_allow_html=True)
            with mc3: st.markdown(generate_mini_leaderboard("Total Assists", p_totals, 'AST', color="#00bfff", top_n=10), unsafe_allow_html=True)
            
            mc4, mc5, mc6 = st.columns(3)
            with mc4: st.markdown(generate_mini_leaderboard("Total Steals", p_totals, 'STL', color="#ff8c00", top_n=10), unsafe_allow_html=True)
            with mc5: st.markdown(generate_mini_leaderboard("Total Blocks", p_totals, 'BLK', color="#8a2be2", top_n=10), unsafe_allow_html=True)
            with mc6: st.markdown(generate_mini_leaderboard("Total 3PM", p_totals, '3PM', color="#d4af37", top_n=10), unsafe_allow_html=True)

            st.markdown("#### Team Milestones")
            tc1, tc2 = st.columns(2)
            if not t_totals.empty:
                with tc1: st.markdown(generate_mini_leaderboard("Most Wins", t_totals, 'Win', color="#ffd700", top_n=5), unsafe_allow_html=True)
                with tc2: st.markdown(generate_mini_leaderboard("Total Points Scored", t_totals, 'PTS', color="#cc0000", top_n=5), unsafe_allow_html=True)

    elif view_mode == "🏢 Team Pages":
        available_teams = sorted([t for t in p_stats['Team Name'].unique() if str(t) != '0' and pd.notna(t)])
        if available_teams:
            selected_team = st.selectbox("Select Team Roster", available_teams)
            st.markdown(f"<div class='header-banner'>{selected_team} TEAM HUB</div>", unsafe_allow_html=True)
            
            team_data = df_active[(df_active['Team Name'] == selected_team)]
            
            tab_roster, tab_team_stats, tab_box_scores = st.tabs(["📋 Roster Binder", "📊 Season Stats & Analytics", "📓 Game-by-Game Box Scores"])

            with tab_roster:
                team_p_stats = p_stats[p_stats['Team Name'] == selected_team].reset_index(drop=True)
                cols = st.columns(4)
                for idx, row in team_p_stats.iterrows():
                    with cols[idx % 4]: st.markdown(generate_2k_player_card(row['Player/Team'], row, rank=row['League_Rank']), unsafe_allow_html=True)

            with tab_team_stats:
                st.subheader(f"{selected_team} Total Performance")
                t_team_only = team_data[team_data['Type'].astype(str).str.lower() == 'team']
                
                c1, c2, c3, c4 = st.columns(4)
                c1.markdown(f"<div class='metric-box'><div class='metric-title'>Points Per Game</div><div class='metric-value'>{t_team_only['PTS'].mean():.1f}</div></div>", unsafe_allow_html=True)
                c2.markdown(f"<div class='metric-box'><div class='metric-title'>Point Differential</div><div class='metric-value'>{t_team_only['Point_Diff'].mean():+.1f}</div></div>", unsafe_allow_html=True)
                c3.markdown(f"<div class='metric-box'><div class='metric-title'>Opponent FG%</div><div class='metric-value'>{t_team_only['Opp_FG%'].mean():.1f}%</div></div>", unsafe_allow_html=True)
                c4.markdown(f"<div class='metric-box'><div class='metric-title'>Opponent PPP</div><div class='metric-value'>{t_team_only['Opp_PPP'].mean():.2f}</div></div>", unsafe_allow_html=True)
                
                st.markdown("### Player Averages")
                p_team_only = team_data[team_data['Type'].astype(str).str.lower() == 'player']
                roster_stats = p_team_only.groupby('Player/Team').agg(
                    GP=('Game_ID', 'nunique'), PPG=('PTS', 'mean'), RPG=('REB', 'mean'), APG=('AST', 'mean'),
                    SPG=('STL', 'mean'), BPG=('BLK', 'mean'), FB_PPG=('FB_Points', 'mean'),
                    Tipped_Passes=('Tipped_Passes', 'mean'), Shots_Affected=('Shots_Affected', 'mean')
                ).round(1)
                st.dataframe(roster_stats, use_container_width=True)

            with tab_box_scores:
                st.subheader("Game-by-Game Logs")
                game_options = team_data['Game_ID'].dropna().unique()
                if len(game_options) > 0:
                    selected_game = st.selectbox("Select Game ID to view Box Score", sorted(game_options, reverse=True))
                    box_score_data = team_data[(team_data['Game_ID'] == selected_game) & (team_data['Type'].astype(str).str.lower() == 'player')]
                    
                    if not box_score_data.empty:
                        game_type = box_score_data['Game_Type'].iloc[0] if 'Game_Type' in box_score_data.columns else 'N/A'
                        st.markdown(f"**Game Type:** `{game_type}` | **Season:** `{box_score_data['Season'].iloc[0]}`")
                        display_cols = ['Player/Team', 'PTS', 'REB', 'AST', 'STL', 'BLK', 'TO', 'FGM', 'FGA', '3PM', '3PA', 'Tipped_Passes', 'Shots_Affected', 'FB_Points']
                        st.dataframe(box_score_data[[c for c in display_cols if c in box_score_data.columns]], use_container_width=True, hide_index=True)
                else:
                    st.info("No games found for this team in this scope.")

    elif view_mode == "🗃️ Full Player Database":
        st.subheader("🗃️ Complete League Roster")
        col1, col2 = st.columns(2)
        with col1: search_name = st.text_input("🔍 Search by Player Name")
        with col2: sort_metric = st.selectbox("Sort Roster By", ["PIE", "PTS/G", "REB/G", "AST/G", "DEF", "FG%", "TS%", "PPP", "FB_Points/G", "Tipped_Passes/G", "Shots_Affected/G"])
        
        filtered_df = p_stats.copy()
        if search_name: filtered_df = filtered_df[filtered_df['Player/Team'].str.contains(search_name, case=False, na=False)]
        filtered_df = filtered_df.sort_values(sort_metric, ascending=False).reset_index(drop=True)
        
        for idx, row in filtered_df.iterrows():
            st.markdown(generate_2k_player_row(row['Player/Team'], row['League_Rank'], row['GP'], row['PTS/G'], row['REB/G'], row['AST/G'], row['DEF'], row['FG%'], row['TS%'], row['PIE']), unsafe_allow_html=True)

    elif view_mode == "🔬 Advanced Analytics":
        st.subheader("🧪 Sabermetrics & Efficiency Lab")
        lens = st.selectbox("Analytics Lens", ["Efficiency (TS% vs PIE)", "Volume (Possessions vs Usage)", "Stats by Possession (PPP)"])
        plot_df = p_stats[p_stats['PTS/G'] > 0].copy()
        if lens == "Efficiency (TS% vs PIE)": fig = px.scatter(plot_df, x='TS%', y='PIE', size='PTS/G', color='Team Name', hover_name='Player/Team', template="plotly_dark", title="Efficiency Matrix: True Shooting vs. Overall Impact (PIE)")
        elif lens == "Volume (Possessions vs Usage)": fig = px.scatter(plot_df, x='Poss_Raw/G', y='FGA/G', size='PTS/G', color='Team Name', hover_name='Player/Team', template="plotly_dark", title="Volume Matrix: Possessions vs. FGA")
        elif lens == "Stats by Possession (PPP)": fig = px.scatter(plot_df, x='PPP', y='Poss_Raw/G', size='AST/G', color='Team Name', hover_name='Player/Team', template="plotly_dark", title="Pace Matrix: Points Per Possession vs. Total Possessions")
        st.plotly_chart(fig, use_container_width=True)

    elif view_mode == "⚔️ Head-to-Head Radar":
        st.subheader("🕸️ Dynamic Matchup Lab")
        mode = st.radio("Matchup Type", ["Player vs Player", "Team vs Team"], horizontal=True)
        def norm(val, mx): return min(100, (max(0, val) / mx) * 100) if mx > 0 else 0
        def rev_norm(val, mx): return max(0, 100 - (norm(val, mx)))

        if mode == "Player vs Player" and not df_reg.empty:
            c1, c2 = st.columns(2)
            player_list = p_stats['Player/Team'].tolist()
            if len(player_list) >= 2:
                with c1: p1_sel = st.selectbox("Player 1 (Gold)", player_list)
                with c2: p2_sel = st.selectbox("Player 2 (Red)", player_list, index=1)
                
                d1 = p_stats[p_stats['Player/Team'] == p1_sel].iloc[0]
                d2 = p_stats[p_stats['Player/Team'] == p2_sel].iloc[0]
                mx = p_stats.max(numeric_only=True)
                
                cats1 = ['Scoring (PPG)', 'Playmaking (APG)', 'Rebounding (RPG)', 'Defense (Stocks)', 'Efficiency (FG%)']
                r1_1 = [norm(d1['PTS/G'], mx['PTS/G']), norm(d1['AST/G'], mx['AST/G']), norm(d1['REB/G'], mx['REB/G']), norm(d1['DEF'], mx['DEF']), norm(d1['FG%'], 100)]
                r2_1 = [norm(d2['PTS/G'], mx['PTS/G']), norm(d2['AST/G'], mx['AST/G']), norm(d2['REB/G'], mx['REB/G']), norm(d2['DEF'], mx['DEF']), norm(d2['FG%'], 100)]
                
                cats2 = ['3P Vol (3PA)', '3P%', 'FT%', 'True Shooting', 'Effective FG%']
                r1_2 = [norm(d1['3PA/G'], mx['3PA/G']), norm(d1['3P%'], 100), norm(d1['FT%'], 100), norm(d1['TS%'], 100), norm(d1['eFG%'], 100)]
                r2_2 = [norm(d2['3PA/G'], mx['3PA/G']), norm(d2['3P%'], 100), norm(d2['FT%'], 100), norm(d2['TS%'], 100), norm(d2['eFG%'], 100)]
                
                row1_col1, row1_col2 = st.columns(2)
                with row1_col1: st.plotly_chart(draw_dynamic_radar(p1_sel, r1_1, p2_sel, r2_1, cats1, "The 5-Tool Core"), use_container_width=True)
                with row1_col2: st.plotly_chart(draw_dynamic_radar(p1_sel, r1_2, p2_sel, r2_2, cats2, "Sharpshooter Matrix"), use_container_width=True)

        elif mode == "Team vs Team" and not t_stats.empty:
            c1, c2 = st.columns(2)
            team_list = t_stats['Team Name'].tolist()
            if len(team_list) >= 2:
                with c1: t1_sel = st.selectbox("Team 1 (Gold)", team_list)
                with c2: t2_sel = st.selectbox("Team 2 (Red)", team_list, index=1)
                
                d1 = t_stats[t_stats['Team Name'] == t1_sel].iloc[0]
                d2 = t_stats[t_stats['Team Name'] == t2_sel].iloc[0]
                mx = t_stats.max(numeric_only=True)
                
                cats = ['Points (PPG)', 'Assists (APG)', 'Rebounds (RPG)', 'Defense (Stocks)', 'Offensive Rating']
                r1 = [norm(d1['PTS/G'], mx['PTS/G']), norm(d1['AST/G'], mx['AST/G']), norm(d1['REB/G'], mx['REB/G']), norm(d1['DEF'], mx['DEF']), norm(d1['OffRtg'], mx['OffRtg'])]
                r2 = [norm(d2['PTS/G'], mx['PTS/G']), norm(d2['AST/G'], mx['AST/G']), norm(d2['REB/G'], mx['REB/G']), norm(d2['DEF'], mx['DEF']), norm(d2['OffRtg'], mx['OffRtg'])]
                st.plotly_chart(draw_dynamic_radar(t1_sel, r1, t2_sel, r2, cats, "Tale of the Tape"), use_container_width=True)

    elif view_mode == "🔮 Oracle Predictor":
        st.subheader("🔮 SPAM Oracle Matchup Predictor")
        if not t_stats.empty and len(t_stats) >= 2:
            team_list = t_stats['Team Name'].tolist()
            c1, c2 = st.columns(2)
            with c1: t1_sel = st.selectbox("Home Team", team_list)
            with c2: t2_sel = st.selectbox("Away Team", team_list, index=1)
            
            if st.button("Simulate Matchup (1,000 Iterations)"):
                d1 = t_stats[t_stats['Team Name'] == t1_sel].iloc[0]
                d2 = t_stats[t_stats['Team Name'] == t2_sel].iloc[0]
                league_pace = t_stats['Poss_Raw/G'].mean()
                league_rtg = t_stats['OffRtg'].mean()
                
                t1_pace_adj = d1['Poss_Raw/G'] / league_pace
                t2_pace_adj = d2['Poss_Raw/G'] / league_pace
                game_pace = league_pace * t1_pace_adj * t2_pace_adj
                
                t1_def_rtg = league_rtg - (d1['DEF'] * 1.5)
                t2_def_rtg = league_rtg - (d2['DEF'] * 1.5)
                
                t1_exp_pts = (d1['OffRtg'] / league_rtg) * (t2_def_rtg / league_rtg) * (game_pace)
                t2_exp_pts = (d2['OffRtg'] / league_rtg) * (t1_def_rtg / league_rtg) * (game_pace)
                
                t1_wins = 0; t2_wins = 0
                sim_scores_1 = []; sim_scores_2 = []
                for _ in range(1000):
                    s1 = max(30, np.random.normal(t1_exp_pts, 8))
                    s2 = max(30, np.random.normal(t2_exp_pts, 8))
                    if s1 == s2: s1 += 1 
                    if s1 > s2: t1_wins += 1
                    else: t2_wins += 1
                    sim_scores_1.append(s1); sim_scores_2.append(s2)
                
                t1_win_pct = (t1_wins / 1000) * 100
                t2_win_pct = (t2_wins / 1000) * 100
                avg_score_1 = int(np.mean(sim_scores_1))
                avg_score_2 = int(np.mean(sim_scores_2))
                
                diff = abs(avg_score_1 - avg_score_2)
                if diff > 15: potg_text = "Blowout Warning! Total Domination."
                elif diff > 8: potg_text = "Solid Victory Expected."
                elif diff > 3: potg_text = "Close Game! Down to the wire."
                else: potg_text = "Coin Toss! Instant Classic Alert."
                
                colA, colB, colC = st.columns([1,2,1])
                with colA: st.markdown(f"<div class='sim-box'><h3 style='color:#d4af37; margin:0;'>{t1_sel}</h3><h1 style='font-size:48px; margin:0;'>{t1_win_pct:.1f}%</h1><p>Win Probability</p></div>", unsafe_allow_html=True)
                with colB: 
                    st.markdown(f"<div class='sim-box' style='background:#2a2d35;'><h4 style='color:#888; text-transform:uppercase;'>Expected Final Score</h4><h1 style='font-size:54px; margin:0;'>{avg_score_1} - {avg_score_2}</h1><p style='color:#d4af37; margin-top:10px;'>{potg_text}</p></div>", unsafe_allow_html=True)
                with colC: st.markdown(f"<div class='sim-box'><h3 style='color:#cc0000; margin:0;'>{t2_sel}</h3><h1 style='font-size:48px; margin:0;'>{t2_win_pct:.1f}%</h1><p>Win Probability</p></div>", unsafe_allow_html=True)
        else:
            st.warning("Need at least two teams with data to run simulations.")

    elif view_mode == "🏦 The Vault":
        st.subheader("🏦 THE VAULT: ALL-TIME LEAGUE LOGS")
        col1, col2 = st.columns([1, 2])
        with col1: vault_type = st.radio("View Totals For:", ["Players", "Teams"], horizontal=True)
        with col2: vault_game_filter = st.multiselect("Filter by Game Type", ['Regular Season', 'Tournament', 'Playoffs'], default=['Regular Season', 'Tournament', 'Playoffs'])
        
        vault_data = df_active[df_active['Game_Type'].isin(vault_game_filter)]
        
        if vault_type == "Players":
            v_df = vault_data[vault_data['Type'].astype(str).str.lower() == 'player']
            totals = v_df.groupby('Player/Team').agg(**{
                'Games': ('Game_ID', 'nunique'), 'PTS': ('PTS', 'sum'), 'REB': ('REB', 'sum'), 'AST': ('AST', 'sum'),
                'STL': ('STL', 'sum'), 'BLK': ('BLK', 'sum'), 'FGM': ('FGM', 'sum'), 'FGA': ('FGA', 'sum'),
                '3PM': ('3PM', 'sum'), '3PA': ('3PA', 'sum'), 'FB_Points': ('FB_Points', 'sum'),
                'Tipped_Passes': ('Tipped_Passes', 'sum'), 'Shots_Affected': ('Shots_Affected', 'sum')
            }).reset_index()
            st.dataframe(totals.sort_values(by='PTS', ascending=False), use_container_width=True, hide_index=True)
            
        else:
            v_df = vault_data[vault_data['Type'].astype(str).str.lower() == 'team']
            totals = v_df.groupby('Team Name').agg(
                Games=('Game_ID', 'nunique'), Wins=('Win', 'sum'), PTS=('PTS', 'sum'), Point_Diff=('Point_Diff', 'sum'),
                FB_Points=('FB_Points', 'sum'), Tipped_Passes=('Tipped_Passes', 'sum'), Shots_Affected=('Shots_Affected', 'sum')
            ).reset_index()
            st.dataframe(totals.sort_values(by='Wins', ascending=False), use_container_width=True, hide_index=True)
