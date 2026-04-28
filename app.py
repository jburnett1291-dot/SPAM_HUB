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
    .stApp { background: radial-gradient(circle at top, #121212 0%, #000000 100%); color: #e0e0e0; font-family: 'Helvetica Neue', sans-serif; }
    .header-banner { 
        padding: 20px; text-align: center; 
        background: linear-gradient(90deg, #d4af37 0%, #f7e08a 50%, #d4af37 100%);
        color: #000; font-family: 'Arial Black'; font-size: 26px; border-radius: 5px; margin-bottom: 20px; text-transform: uppercase; letter-spacing: 2px;
    }
    .metric-box { background: #1e1e1e; border-left: 4px solid #d4af37; padding: 15px; border-radius: 4px; text-align: center; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }
    .metric-title { font-size: 12px; color: #888; text-transform: uppercase; letter-spacing: 1px; }
    .metric-value { font-size: 22px; font-weight: 900; color: #fff; margin-top: 5px; }
    
    .sleek-table { width: 100%; border-collapse: collapse; margin: 15px 0; font-size: 13px; text-align: center; background: #161616; border-radius: 8px; overflow: hidden; }
    .sleek-table th { background: #222; color: #d4af37; padding: 12px; font-weight: bold; text-transform: uppercase; border-bottom: 2px solid #333; }
    .sleek-table td { padding: 10px; border-bottom: 1px solid #222; color: #ddd; }
    .sleek-table tr:hover { background: #1f1f1f; }
    .sleek-table td.player-name { text-align: left; font-weight: bold; color: #fff; }
    
    .podium-container { display: flex; justify-content: center; align-items: flex-end; margin: 30px 0; height: 200px; gap: 10px; }
    .podium { display: flex; flex-direction: column; align-items: center; justify-content: flex-end; text-align: center; width: 120px; border-radius: 8px 8px 0 0; }
    .podium-1 { background: linear-gradient(to top, #d4af37, #ffd700); height: 160px; color: #000; box-shadow: 0 0 20px rgba(212,175,55,0.4); z-index: 3; }
    .podium-2 { background: linear-gradient(to top, #a0a0a0, #e0e0e0); height: 120px; color: #000; z-index: 2; }
    .podium-3 { background: linear-gradient(to top, #cd7f32, #d2691e); height: 90px; color: #000; z-index: 1; }
    .podium-name { font-weight: bold; font-size: 14px; margin-bottom: 5px; padding: 0 5px; }
    .podium-stat { font-size: 20px; font-weight: 900; margin-bottom: 10px; }
    
    .shot-bar-container { background: #222; height: 20px; border-radius: 10px; width: 100%; position: relative; margin-top: 5px; overflow: hidden; }
    .shot-bar-fill { height: 100%; position: absolute; left: 0; top: 0; border-radius: 10px; }
    
    .award-card { background: #161b22; border: 1px solid #d4af37; padding: 20px; border-radius: 8px; text-align: center; height: 100%; }
    .award-title { color: #d4af37; font-size: 14px; text-transform: uppercase; font-weight: bold; letter-spacing: 1px; border-bottom: 1px solid #333; padding-bottom: 10px; margin-bottom: 15px; }
    
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
    return clean_name.strip().title()

@st.cache_data(ttl=60)
def load_data():
    try:
        df = pd.read_csv(URL)
        df.columns = df.columns.str.strip()
        df = df[df['Player/Team'] != 'Player/Team']
        df = df[df['Team Name'].notna() & (df['Team Name'].astype(str).str.strip() != '') & (df['Team Name'].astype(str) != '0')]
        if 'Player/Team' in df.columns: df['Player/Team'] = df['Player/Team'].apply(smart_name_scrubber)
            
        req_cols = ['PTS', 'REB', 'AST', 'STL', 'BLK', 'FOULS', 'TO', 'FGA', 'FGM', '3PM', '3PA', 'FTA', 'FTM', 'Game_ID', 'Win', 'Season', 'Type', 'Team Name']
        for c in req_cols:
            if c not in df.columns: df[c] = 0
            if c not in ['Type', 'Team Name', 'Player/Team']: df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)
            
        df['Win'] = pd.to_numeric(df['Win'], errors='coerce').fillna(0).apply(lambda x: 1 if x > 0 else 0)
        df['Game_ID'] = pd.to_numeric(df['Game_ID'], errors='coerce')
        
        # --- PLAYER EFFICIENCY ---
        df['PIE_Raw'] = (df['PTS'] + df['REB'] + df['AST'] + df['STL'] + df['BLK']) - (df['FGA'] * 0.5) - df['TO']
        df['Poss_Raw'] = df['FGA'] + 0.44 * df['FTA'] + df['TO']

        # --- AUTO-CALCULATE TEAM TOTALS ---
        df = df[df['Type'].astype(str).str.lower() != 'team'].copy()
        sum_cols = ['PTS', 'REB', 'AST', 'STL', 'BLK', 'FOULS', 'TO', 'FGA', 'FGM', '3PM', '3PA', 'FTA', 'FTM', 'Poss_Raw']
        team_rows = df.groupby(['Game_ID', 'Team Name', 'Season']).agg({**{c: 'sum' for c in sum_cols}, 'Win': 'first'}).reset_index()
        team_rows['Type'] = 'Team'
        team_rows['Player/Team'] = team_rows['Team Name'] + " TOTALS"
        df = pd.concat([df, team_rows], ignore_index=True)

        # --- PROXY STATS ---
        df['Game_Type'] = np.where(df['Game_ID'] >= 9000, 'Playoffs', np.where(df['Game_ID'] >= 8000, 'Tournament', 'Regular Season'))
        players_df = df[df['Type'].astype(str).str.lower() == 'player'].copy()
        players_df = players_df.sort_values(by=['Game_ID', 'Team Name'])
        players_df['Position_Num'] = players_df.groupby(['Game_ID', 'Team Name']).cumcount() + 1
        
        players_df['Tipped_Passes'] = np.where(players_df['Position_Num'] <= 2, (players_df['STL'] * 2.2) + (players_df['FOULS'] * 0.4), (players_df['STL'] * 1.2) + (players_df['BLK'] * 0.2)).round().astype(int)
        players_df['Shots_Affected'] = np.where(players_df['Position_Num'] >= 3, (players_df['BLK'] * 3.0) + (players_df['REB'] * 0.4) + (players_df['FOULS'] * 0.5), (players_df['BLK'] * 1.5) + (players_df['STL'] * 0.4)).round().astype(int)
        players_df['FB_Points'] = np.where(players_df['Position_Num'] <= 2, (players_df['STL'] * 2.0) + (players_df['FGM'] * 0.4), (players_df['STL'] * 1.0) + (players_df['FGM'] * 0.1)).round().astype(int)
        players_df['FB_Points'] = players_df[['FB_Points', 'PTS']].min(axis=1)

        df = df.merge(players_df[['Game_ID', 'Team Name', 'Player/Team', 'Tipped_Passes', 'Shots_Affected', 'FB_Points', 'Position_Num']], on=['Game_ID', 'Team Name', 'Player/Team'], how='left')

        t_proxy = df[df['Type'].astype(str).str.lower() == 'player'].groupby(['Game_ID', 'Team Name'])[['Tipped_Passes', 'Shots_Affected', 'FB_Points']].sum().reset_index()
        for col in ['Tipped_Passes', 'Shots_Affected', 'FB_Points']:
            df.loc[df['Type'].astype(str).str.lower() == 'team', col] = df.loc[df['Type'].astype(str).str.lower() == 'team'].set_index(['Game_ID', 'Team Name']).index.map(t_proxy.set_index(['Game_ID', 'Team Name'])[col]).fillna(0)

        # --- MATCHUP LOGIC & SOS ---
        t_logs = df[df['Type'].astype(str).str.lower() == 'team'][['Game_ID', 'Team Name', 'PTS', 'FGM', 'FGA', '3PM', '3PA', 'TO', 'FTA', 'Win', 'Season']].copy()
        t_logs['Team_Win_Pct'] = t_logs.groupby(['Season', 'Team Name'])['Win'].transform('mean')
        
        opps = pd.merge(t_logs, t_logs, on='Game_ID', suffixes=('', '_Opp'))
        opps = opps[opps['Team Name'] != opps['Team Name_Opp']]
        
        opps['Point_Diff'] = opps['PTS'] - opps['PTS_Opp']
        opps['Opp_Possessions'] = opps['FGA_Opp'] + (0.44 * opps['FTA_Opp']) + opps['TO_Opp']
        opps['Opp_PPP'] = np.where(opps['Opp_Possessions'] > 0, opps['PTS_Opp'] / opps['Opp_Possessions'], 0)
        opps['Opp_FG%'] = np.where(opps['FGA_Opp'] > 0, (opps['FGM_Opp'] / opps['FGA_Opp']) * 100, 0)

        df = pd.merge(df, opps[['Game_ID', 'Team Name', 'Point_Diff', 'Opp_PPP', 'Opp_FG%', 'Team Name_Opp', 'Team_Win_Pct_Opp']], on=['Game_ID', 'Team Name'], how='left')

        df['Point_Diff'] = df.groupby(['Game_ID', 'Team Name'])['Point_Diff'].transform('first')
        df['Opp_PPP'] = df.groupby(['Game_ID', 'Team Name'])['Opp_PPP'].transform('first')
        df['SOS_Game'] = df.groupby(['Game_ID', 'Team Name'])['Team_Win_Pct_Opp'].transform('first')
        df['Opp_Name'] = df.groupby(['Game_ID', 'Team Name'])['Team Name_Opp'].transform('first')

        return df
    except Exception as e: return str(e)

full_df = load_data()

# --- 2B. GLOBAL MILESTONE & CLUB TRACKER ---
if not isinstance(full_df, str):
    global_players = full_df[full_df['Type'].astype(str).str.lower() == 'player'].copy()
    season_totals = global_players.groupby(['Player/Team', 'Season']).sum(numeric_only=True).reset_index()

    def calc_clubs(row):
        clubs = []
        if row['REB'] >= 40 and row['STL'] >= 40 and row['AST'] >= 40: clubs.append(f"40/40/40 (S{int(row['Season'])})")
        elif row['REB'] >= 30 and row['STL'] >= 30 and row['AST'] >= 30: clubs.append(f"30/30/30 (S{int(row['Season'])})")
        if row['PTS'] >= 300 and row['3PM'] >= 100: clubs.append(f"300Pts/100 3s (S{int(row['Season'])})")
        if row['PTS'] >= 100 and row['REB'] >= 100: clubs.append(f"100Pts/100Reb (S{int(row['Season'])})")
        return clubs

    season_totals['Clubs'] = season_totals.apply(calc_clubs, axis=1)
    player_clubs = season_totals.groupby('Player/Team')['Clubs'].agg(lambda x: [item for sublist in x for item in sublist if item]).reset_index()

# --- 3. HTML & CHART GENERATORS ---
def draw_shot_profile(fgm, fga, tpm, tpa):
    twopm = fgm - tpm
    twopa = fga - tpa
    three_pct = (tpm/tpa*100) if tpa > 0 else 0
    two_pct = (twopm/twopa*100) if twopa > 0 else 0
    return f"""
    <div style="display:flex; justify-content:space-between; margin-bottom:2px; font-size:11px; color:#aaa;"><span>Interior (2PT)</span><span>{two_pct:.1f}% ({int(twopm)}/{int(twopa)})</span></div>
    <div class="shot-bar-container"><div class="shot-bar-fill" style="width:{two_pct}%; background:#d4af37;"></div></div>
    <div style="display:flex; justify-content:space-between; margin-top:10px; margin-bottom:2px; font-size:11px; color:#aaa;"><span>Perimeter (3PT)</span><span>{three_pct:.1f}% ({int(tpm)}/{int(tpa)})</span></div>
    <div class="shot-bar-container"><div class="shot-bar-fill" style="width:{three_pct}%; background:#00bfff;"></div></div>
    """

def generate_sleek_box_score(df_game):
    df_game = df_game.sort_values(by='PTS', ascending=False)
    html = "<table class='sleek-table'><tr><th>Player</th><th>PTS</th><th>REB</th><th>AST</th><th>STL</th><th>BLK</th><th>FG</th><th>3PT</th><th>PIE</th></tr>"
    for _, row in df_game.iterrows():
        html += f"<tr><td class='player-name'>{row['Player/Team']}</td><td>{int(row['PTS'])}</td><td>{int(row['REB'])}</td><td>{int(row['AST'])}</td><td>{int(row['STL'])}</td><td>{int(row['BLK'])}</td><td>{int(row['FGM'])}/{int(row['FGA'])}</td><td>{int(row['3PM'])}/{int(row['3PA'])}</td><td>{row['PIE_Raw']:.1f}</td></tr>"
    html += "</table>"
    return html

def render_podium(title, top3_df, stat_col):
    if len(top3_df) < 3: return ""
    p1, p2, p3 = top3_df.iloc[0], top3_df.iloc[1], top3_df.iloc[2]
    
    html = f"<div style='text-align:center; margin-bottom:10px;'><h3 style='color:#fff; text-transform:uppercase;'>{title}</h3></div>"
    html += "<div class='podium-container'>"
    html += f"<div class='podium podium-3'><div class='podium-name'>{p3['Player/Team']}</div><div class='podium-stat'>{p3[stat_col]:.1f}</div></div>"
    html += f"<div class='podium podium-1'><div class='podium-name'>{p1['Player/Team']}</div><div class='podium-stat'>{p1[stat_col]:.1f}</div></div>"
    html += f"<div class='podium podium-2'><div class='podium-name'>{p2['Player/Team']}</div><div class='podium-stat'>{p2[stat_col]:.1f}</div></div>"
    html += "</div>"
    return html

def generate_2k_player_card(player_name, stats, rank=""):
    rank_badge = f'<div style="position:absolute; top:-10px; right:-10px; background:#d4af37; color:#000; font-weight:bold; padding:8px; border-radius:50%; border:2px solid #fff; z-index:10;">#{rank}</div>' if rank else ""
    
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

def generate_mini_leaderboard(title, df, stat_col, color="#d4af37", top_n=5, name_col=None):
    html = f"<div style='background:#1c2128; padding:15px; border-radius:8px; border-left:4px solid {color}; margin-bottom:15px; box-shadow: 0 4px 6px rgba(0,0,0,0.3);'>"
    html += f"<h3 style='margin-top:0; color:#fff; font-size:16px; border-bottom:1px dashed #444; padding-bottom:8px; text-transform:uppercase;'>{title}</h3>"
    
    sorted_df = df.sort_values(by=stat_col, ascending=False).head(top_n)
    
    for i, (_, row) in enumerate(sorted_df.iterrows()):
        val = row[stat_col]
        if pd.isna(val): continue
        
        if val == int(val): val_str = f"{int(val)}"
        else: val_str = f"{val:.1f}"
            
        rank_color = "#ffd700" if i == 0 else "#888"
        
        if name_col:
            name = row.get(name_col, 'Unknown')
        else:
            name = row.get('Player/Team')
            if pd.isna(name) or name == 0 or str(name).strip() == '' or str(name) == '0':
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
        "🏠 League Home & Awards", 
        "🏆 Power Rankings & SOS", 
        "📖 Record Book & Milestones", 
        "🏢 Team Pages", 
        "🗃️ Full Player Database", 
        "⚔️ Rivalry Corner", 
        "🔮 Oracle Predictor", 
        "🔬 Advanced Analytics", 
        "🏦 The Vault"
    ])
    st.sidebar.divider()
    scope_opts = [f"Season {s}" for s in seasons] + ["Career Stats"]
    selected_scope = st.sidebar.selectbox("Data Scope", scope_opts, index=0)
    
    target_season = seasons[0] if selected_scope == "Career Stats" else int(selected_scope.replace("Season ", ""))
    df_active = full_df if selected_scope == "Career Stats" else full_df[full_df['Season'] == target_season]
    banner_text = "CAREER TOTALS" if selected_scope == "Career Stats" else f"SEASON {target_season}"

    st.markdown(f'<div class="header-banner">🏀 SPAM LEAGUE HUB - {banner_text}</div>', unsafe_allow_html=True)

    # Core Stat Generation
    p_df = df_active[df_active['Type'].astype(str).str.lower() == 'player']
    t_df = df_active[df_active['Type'].astype(str).str.lower() == 'team']
    
    # DICTIONARY UNPACKING FIX FOR 3PM & 3PA
    p_stats = p_df.groupby('Player/Team').agg(**{
        'GP': ('Game_ID', 'nunique'), 'PTS': ('PTS', 'mean'), 'REB': ('REB', 'mean'), 'AST': ('AST', 'mean'), 'STL': ('STL', 'mean'), 'BLK': ('BLK', 'mean'),
        'FGM': ('FGM', 'mean'), 'FGA': ('FGA', 'mean'), '3PM': ('3PM', 'mean'), '3PA': ('3PA', 'mean'), 'PIE': ('PIE_Raw', 'mean'), 'POS': ('Position_Num', 'mean'), 'Team': ('Team Name', 'last')
    }).reset_index()
    
    p_stats['DEF'] = p_stats['STL'] + p_stats['BLK']
    p_stats['TS%'] = (p_stats['PTS'] / (2 * (p_stats['FGA'] + 0.44 * (p_stats['FGA']*0.2)).replace(0, 1)) * 100) # Proxy FTA
    
    # Merge Clubs & Badges for Player Cards
    p_stats = p_stats.merge(player_clubs, on='Player/Team', how='left')

    p_highs = df_active[df_active['Type'].astype(str).str.lower() == 'player'].groupby('Player/Team').agg(
        High_PTS=('PTS', 'max'), High_REB=('REB', 'max'), High_AST=('AST', 'max'),
        High_STL=('STL', 'max'), High_BLK=('BLK', 'max'), High_3PM=('3PM', 'max')
    ).reset_index()
    p_stats = p_stats.merge(p_highs, on='Player/Team', how='left')

    t_stats = t_df.groupby('Team Name').agg(
        GP=('Game_ID', 'nunique'), Wins=('Win', 'sum'), PPG=('PTS', 'mean'), Diff=('Point_Diff', 'mean'), 
        Opp_PPP=('Opp_PPP', 'mean'), SOS=('SOS_Game', 'mean')
    ).reset_index()
    t_stats['Win%'] = t_stats['Wins'] / t_stats['GP'].replace(0, 1)

    if view_mode == "🏠 League Home & Awards":
        st.markdown("### 🏆 End of Season Awards Tracker")
        
        qual_p = p_stats[p_stats['GP'] >= (p_stats['GP'].max() * 0.5)]
        
        # Award Logic
        mvp = qual_p.sort_values('PIE', ascending=False).iloc[0] if not qual_p.empty else None
        dpoy = qual_p.sort_values('DEF', ascending=False).iloc[0] if not qual_p.empty else None
        bmoty = qual_p[qual_p['POS'] >= 3].sort_values('PIE', ascending=False).iloc[0] if not qual_p[qual_p['POS'] >= 3].empty else None
        
        debut_seasons = full_df[full_df['Type'].str.lower() == 'player'].groupby('Player/Team')['Season'].min().reset_index()
        rookies = debut_seasons[debut_seasons['Season'] == target_season]['Player/Team'].tolist()
        roty = qual_p[qual_p['Player/Team'].isin(rookies)].sort_values('PIE', ascending=False).iloc[0] if rookies and not qual_p[qual_p['Player/Team'].isin(rookies)].empty else None

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            if mvp is not None: st.markdown(f"<div class='award-card'><div class='award-title'>Most Valuable Player</div><h2>{mvp['Player/Team']}</h2><p style='color:#aaa;'>{mvp['Team']}</p><h3 style='color:#d4af37;'>{mvp['PIE']:.1f} PIE</h3><p>{mvp['PTS']:.1f} PTS | {mvp['AST']:.1f} AST</p></div>", unsafe_allow_html=True)
        with c2:
            if dpoy is not None: st.markdown(f"<div class='award-card'><div class='award-title'>Defensive Player of Year</div><h2>{dpoy['Player/Team']}</h2><p style='color:#aaa;'>{dpoy['Team']}</p><h3 style='color:#d4af37;'>{dpoy['DEF']:.1f} STOCKS</h3><p>{dpoy['STL']:.1f} STL | {dpoy['BLK']:.1f} BLK</p></div>", unsafe_allow_html=True)
        with c3:
            if bmoty is not None: st.markdown(f"<div class='award-card'><div class='award-title'>Big Man of the Year</div><h2>{bmoty['Player/Team']}</h2><p style='color:#aaa;'>{bmoty['Team']}</p><h3 style='color:#d4af37;'>{bmoty['REB']:.1f} REB/G</h3><p>{bmoty['PTS']:.1f} PTS | {bmoty['BLK']:.1f} BLK</p></div>", unsafe_allow_html=True)
        with c4:
            if roty is not None: st.markdown(f"<div class='award-card'><div class='award-title'>Rookie of the Year</div><h2>{roty['Player/Team']}</h2><p style='color:#aaa;'>{roty['Team']}</p><h3 style='color:#d4af37;'>{roty['PIE']:.1f} PIE</h3><p>Class of S{target_season}</p></div>", unsafe_allow_html=True)
            else: st.markdown(f"<div class='award-card'><div class='award-title'>Rookie of the Year</div><h2>N/A</h2><p style='color:#aaa;'>No qualifying rookies</p></div>", unsafe_allow_html=True)

        st.markdown("<hr>", unsafe_allow_html=True)
        st.markdown("### 🔥 Streak Trends (Last 3 Games)")
        recent_p = p_df.sort_values(['Player/Team', 'Game_ID']).groupby('Player/Team').tail(3)
        recent_stats = recent_p.groupby('Player/Team').agg(Recent_PIE=('PIE_Raw', 'mean')).reset_index()
        trend = p_stats.merge(recent_stats, on='Player/Team')
        trend['Swing'] = trend['Recent_PIE'] - trend['PIE']
        
        tc1, tc2 = st.columns(2)
        with tc1:
            st.markdown("<h4 style='color:#00ff00;'>📈 Heating Up</h4>", unsafe_allow_html=True)
            for _, r in trend.sort_values('Swing', ascending=False).head(3).iterrows():
                st.markdown(f"<div style='background:#1a2b1a; padding:10px; border-left:4px solid #00ff00; margin-bottom:5px;'><b>{r['Player/Team']}</b> | +{r['Swing']:.1f} PIE over avg</div>", unsafe_allow_html=True)
        with tc2:
            st.markdown("<h4 style='color:#ff0000;'>📉 Cooling Down</h4>", unsafe_allow_html=True)
            for _, r in trend.sort_values('Swing', ascending=True).head(3).iterrows():
                st.markdown(f"<div style='background:#2b1a1a; padding:10px; border-left:4px solid #ff0000; margin-bottom:5px;'><b>{r['Player/Team']}</b> | {r['Swing']:.1f} PIE under avg</div>", unsafe_allow_html=True)

    elif view_mode == "🏆 Power Rankings & SOS":
        st.subheader("📊 League Power Index")
        st.markdown("Strength of Schedule (SOS) represents the average Win% of opponents faced. A higher SOS means a tougher schedule.")
        
        ranks = t_stats.copy()
        ranks['True_Power'] = (ranks['Win%'] * 0.6) + (ranks['SOS'] * 0.4)
        ranks = ranks.sort_values('True_Power', ascending=False).reset_index(drop=True)
        
        html = "<table class='sleek-table'><tr><th>Rank</th><th>Team</th><th>Record</th><th>Win%</th><th>SOS</th><th>Pt Diff</th><th>Opp PPP</th></tr>"
        for i, r in ranks.iterrows():
            medal = "🥇 " if i==0 else "🥈 " if i==1 else "🥉 " if i==2 else f"{i+1}. "
            html += f"<tr><td style='font-size:16px;'>{medal}</td><td class='player-name'>{r['Team Name']}</td><td>{int(r['Wins'])}-{int(r['GP']-r['Wins'])}</td><td>{r['Win%']:.3f}</td><td style='color:#00bfff;'>{r['SOS']:.3f}</td><td>{r['Diff']:+.1f}</td><td>{r['Opp_PPP']:.2f}</td></tr>"
        html += "</table>"
        st.markdown(html, unsafe_allow_html=True)

    elif view_mode == "📖 Record Book & Milestones":
        st.subheader(f"📖 {banner_text} Record Book & Milestones")
        tab_game, tab_miles = st.tabs(["🔥 Single Game Records", "🏔️ Milestone Tracker (Totals)"])
        
        with tab_game:
            st.markdown("### 🏆 Individual Single Game Highs")
            c1, c2, c3 = st.columns(3)
            with c1:
                st.markdown(generate_mini_leaderboard("Points in a Game", p_df, 'PTS', color="#cc0000", name_col="Player/Team"), unsafe_allow_html=True)
                st.markdown(generate_mini_leaderboard("Steals in a Game", p_df, 'STL', color="#ff8c00", name_col="Player/Team"), unsafe_allow_html=True)
            with c2:
                st.markdown(generate_mini_leaderboard("Rebounds in a Game", p_df, 'REB', color="#32cd32", name_col="Player/Team"), unsafe_allow_html=True)
                st.markdown(generate_mini_leaderboard("Blocks in a Game", p_df, 'BLK', color="#8a2be2", name_col="Player/Team"), unsafe_allow_html=True)
            with c3:
                st.markdown(generate_mini_leaderboard("Assists in a Game", p_df, 'AST', color="#00bfff", name_col="Player/Team"), unsafe_allow_html=True)
                st.markdown(generate_mini_leaderboard("3-Pointers in a Game", p_df, '3PM', color="#d4af37", name_col="Player/Team"), unsafe_allow_html=True)

            st.markdown("### 🏢 Team Single Game Records")
            t_df_valid = t_df[(t_df['Team Name'].astype(str) != '0') & (t_df['Team Name'].notna())].copy()
            
            if not t_df_valid.empty:
                c4, c5, c6 = st.columns(3)
                with c4: st.markdown(generate_mini_leaderboard("Team Points", t_df_valid, 'PTS', color="#cc0000", name_col="Team Name"), unsafe_allow_html=True)
                with c5: st.markdown(generate_mini_leaderboard("Team Rebounds", t_df_valid, 'REB', color="#32cd32", name_col="Team Name"), unsafe_allow_html=True)
                with c6: st.markdown(generate_mini_leaderboard("Team Assists", t_df_valid, 'AST', color="#00bfff", name_col="Team Name"), unsafe_allow_html=True)

        with tab_miles:
            st.markdown("### 🏔️ All-Time Milestones & Totals Leaders")
            p_totals = p_df.groupby('Player/Team').sum(numeric_only=True).reset_index()
            t_totals = t_df.groupby('Team Name').sum(numeric_only=True).reset_index()
            
            st.markdown("#### Player Milestones")
            mc1, mc2, mc3 = st.columns(3)
            with mc1: st.markdown(generate_mini_leaderboard("Total Points", p_totals, 'PTS', color="#cc0000", top_n=10, name_col="Player/Team"), unsafe_allow_html=True)
            with mc2: st.markdown(generate_mini_leaderboard("Total Rebounds", p_totals, 'REB', color="#32cd32", top_n=10, name_col="Player/Team"), unsafe_allow_html=True)
            with mc3: st.markdown(generate_mini_leaderboard("Total Assists", p_totals, 'AST', color="#00bfff", top_n=10, name_col="Player/Team"), unsafe_allow_html=True)
            
            mc4, mc5, mc6 = st.columns(3)
            with mc4: st.markdown(generate_mini_leaderboard("Total Steals", p_totals, 'STL', color="#ff8c00", top_n=10, name_col="Player/Team"), unsafe_allow_html=True)
            with mc5: st.markdown(generate_mini_leaderboard("Total Blocks", p_totals, 'BLK', color="#8a2be2", top_n=10, name_col="Player/Team"), unsafe_allow_html=True)
            with mc6: st.markdown(generate_mini_leaderboard("Total 3PM", p_totals, '3PM', color="#d4af37", top_n=10, name_col="Player/Team"), unsafe_allow_html=True)

            st.markdown("#### Team Milestones")
            tc1, tc2 = st.columns(2)
            if not t_totals.empty:
                with tc1: st.markdown(generate_mini_leaderboard("Most Wins", t_totals, 'Win', color="#ffd700", top_n=5, name_col="Team Name"), unsafe_allow_html=True)
                with tc2: st.markdown(generate_mini_leaderboard("Total Points Scored", t_totals, 'PTS', color="#cc0000", top_n=5, name_col="Team Name"), unsafe_allow_html=True)

    elif view_mode == "🏢 Team Pages":
        teams = sorted([t for t in p_stats['Team'].unique() if str(t) != '0'])
        if teams:
            sel_team = st.sidebar.selectbox("Select Team", teams)
            st.markdown(f"<div class='header-banner'>{sel_team} Franchise Hub</div>", unsafe_allow_html=True)
            
            t_data = t_df[t_df['Team Name'] == sel_team]
            p_data = p_df[p_df['Team Name'] == sel_team]
            
            tab_dash, tab_box = st.tabs(["📋 Season Dashboard", "📓 Sleek Box Scores"])
            
            with tab_dash:
                c1, c2, c3 = st.columns(3)
                c1.markdown(f"<div class='metric-box'><div class='metric-title'>Record</div><div class='metric-value'>{int(t_data['Win'].sum())} - {int(len(t_data)-t_data['Win'].sum())}</div></div>", unsafe_allow_html=True)
                c2.markdown(f"<div class='metric-box'><div class='metric-title'>Point Diff</div><div class='metric-value'>{t_data['Point_Diff'].mean():+.1f}</div></div>", unsafe_allow_html=True)
                c3.markdown(f"<div class='metric-box'><div class='metric-title'>Opp PPP (Def Rating)</div><div class='metric-value'>{t_data['Opp_PPP'].mean():.2f}</div></div>", unsafe_allow_html=True)
                
                st.markdown("### 🎯 Shot Profile & Efficiency")
                sc1, sc2 = st.columns([1, 2])
                with sc1:
                    fgm, fga = p_data['FGM'].sum(), p_data['FGA'].sum()
                    tpm, tpa = p_data['3PM'].sum(), p_data['3PA'].sum()
                    st.markdown(draw_shot_profile(fgm, fga, tpm, tpa), unsafe_allow_html=True)
                with sc2:
                    st.markdown("### 🏆 Best 5 Lineup (By PIE)")
                    best_5 = p_stats[p_stats['Team'] == sel_team].sort_values('PIE', ascending=False).head(5)
                    html = "<table class='sleek-table'><tr><th>Player</th><th>PTS</th><th>REB</th><th>AST</th><th>PIE</th></tr>"
                    for _, r in best_5.iterrows(): html += f"<tr><td class='player-name'>{r['Player/Team']}</td><td>{r['PTS']:.1f}</td><td>{r['REB']:.1f}</td><td>{r['AST']:.1f}</td><td style='color:#d4af37; font-weight:bold;'>{r['PIE']:.1f}</td></tr>"
                    st.markdown(html + "</table>", unsafe_allow_html=True)
                
                # Best/Worst Game
                st.markdown("### 🎢 Highs & Lows")
                b_game = t_data.loc[t_data['Point_Diff'].idxmax()] if not t_data.empty else None
                w_game = t_data.loc[t_data['Point_Diff'].idxmin()] if not t_data.empty else None
                if b_game is not None:
                    st.success(f"**Best Win:** Game {int(b_game['Game_ID'])} vs {b_game['Opp_Name']} (+{int(b_game['Point_Diff'])} Pts)")
                if w_game is not None:
                    st.error(f"**Worst Loss:** Game {int(w_game['Game_ID'])} vs {w_game['Opp_Name']} ({int(w_game['Point_Diff'])} Pts)")

                st.markdown("### 📋 The Roster Binder")
                team_p_stats = p_stats[p_stats['Team'] == sel_team].reset_index(drop=True)
                cols = st.columns(4)
                for idx, row in team_p_stats.iterrows():
                    with cols[idx % 4]: st.markdown(generate_2k_player_card(row['Player/Team'], row, rank=row['League_Rank']), unsafe_allow_html=True)

            with tab_box:
                game_opts = sorted(p_data['Game_ID'].dropna().unique(), reverse=True)
                if game_opts:
                    sel_game = st.selectbox("Select Game", game_opts)
                    g_data = p_data[p_data['Game_ID'] == sel_game]
                    
                    potg = g_data.loc[g_data['PIE_Raw'].idxmax()]
                    st.markdown(f"<div style='background: linear-gradient(90deg, #111, #333); padding:15px; border-left:5px solid #d4af37; margin-bottom:15px;'><h4 style='margin:0; color:#aaa;'>PLAYER OF THE GAME</h4><h2 style='margin:0; color:#fff;'>{potg['Player/Team']}</h2><p style='margin:0; color:#d4af37;'>{int(potg['PTS'])} PTS | {int(potg['REB'])} REB | {potg['PIE_Raw']:.1f} PIE</p></div>", unsafe_allow_html=True)
                    
                    st.markdown(generate_sleek_box_score(g_data), unsafe_allow_html=True)
                    
                    st.markdown("#### Game Shot Profile")
                    st.markdown(draw_shot_profile(g_data['FGM'].sum(), g_data['FGA'].sum(), g_data['3PM'].sum(), g_data['3PA'].sum()), unsafe_allow_html=True)

    elif view_mode == "🗃️ Full Player Database":
        st.subheader("🗃️ Advanced Player Database")
        
        sel_p = st.selectbox("Select Player for 5-Tool Deep Dive", sorted(p_stats['Player/Team'].unique()))
        p_row = p_stats[p_stats['Player/Team'] == sel_p].iloc[0]
        lg_avg = p_stats.mean(numeric_only=True)
        
        c1, c2 = st.columns([1, 2])
        with c1:
            st.markdown(f"<div class='award-card'><h2 style='color:#d4af37;'>{sel_p}</h2><h4 style='color:#fff;'>{p_row['Team']}</h4><hr><p><b>PTS:</b> {p_row['PTS']:.1f}</p><p><b>REB:</b> {p_row['REB']:.1f}</p><p><b>AST:</b> {p_row['AST']:.1f}</p><p><b>DEF:</b> {p_row['DEF']:.1f}</p><p><b>TS%:</b> {p_row['TS%']:.1f}%</p></div>", unsafe_allow_html=True)
        with c2:
            def norm(val, mx): return min(100, (max(0, val) / mx) * 100) if mx > 0 else 0
            mx = p_stats.max(numeric_only=True)
            r1 = [norm(p_row['PTS'], mx['PTS']), norm(p_row['AST'], mx['AST']), norm(p_row['REB'], mx['REB']), norm(p_row['DEF'], mx['DEF']), norm(p_row['TS%'], 100)]
            r2 = [norm(lg_avg['PTS'], mx['PTS']), norm(lg_avg['AST'], mx['AST']), norm(lg_avg['REB'], mx['REB']), norm(lg_avg['DEF'], mx['DEF']), norm(lg_avg['TS%'], 100)]
            st.plotly_chart(draw_dynamic_radar(sel_p, r1, "League Avg", r2, ['Scoring', 'Playmaking', 'Rebounding', 'Defense', 'Efficiency'], "5-Tool Profile vs League"), use_container_width=True)
            
        st.markdown("### 📋 Complete League Roster")
        st.dataframe(p_stats[['Player/Team', 'Team', 'GP', 'PTS', 'REB', 'AST', 'STL', 'BLK', 'TS%', 'PIE']].sort_values('PIE', ascending=False), use_container_width=True, hide_index=True)

    elif view_mode == "⚔️ Rivalry Corner":
        st.subheader("⚔️ Rivalry Corner")
        st.markdown("Teams that have faced off 5+ times. The ultimate bad blood matchups.")
        
        matchups = full_df[full_df['Type'].str.lower() == 'team'].copy()
        if 'Opp_Name' in matchups.columns:
            matchups['Pairing'] = matchups.apply(lambda r: " vs ".join(sorted([str(r['Team Name']), str(r['Opp_Name'])])), axis=1)
            rivals = matchups.groupby('Pairing').agg(Games=('Game_ID', 'nunique')).reset_index()
            rivals = rivals[rivals['Games'] >= 5].sort_values('Games', ascending=False)
            
            if rivals.empty:
                st.info("No teams have played 5+ games against each other yet.")
            else:
                for _, riv in rivals.iterrows():
                    teams = riv['Pairing'].split(" vs ")
                    t1, t2 = teams[0], teams[1]
                    t1_wins = len(matchups[(matchups['Team Name'] == t1) & (matchups['Opp_Name'] == t2) & (matchups['Win'] == 1)])
                    t2_wins = len(matchups[(matchups['Team Name'] == t2) & (matchups['Opp_Name'] == t1) & (matchups['Win'] == 1)])
                    
                    st.markdown(f"<div style='background:#161b22; border:1px solid #d4af37; border-radius:8px; padding:20px; margin-bottom:15px;'><h3 style='text-align:center; color:#fff;'>{t1} <span style='color:#d4af37;'>vs</span> {t2}</h3><h4 style='text-align:center; color:#aaa;'>{riv['Games']} Meetings</h4><div style='display:flex; justify-content:space-around; margin-top:15px;'><div style='text-align:center;'><h2 style='color:#00ff00;'>{t1_wins} Wins</h2><p>{t1}</p></div><div style='text-align:center;'><h2 style='color:#ff0000;'>{t2_wins} Wins</h2><p>{t2}</p></div></div></div>", unsafe_allow_html=True)
        else:
            st.error("Matchup data not available.")

    elif view_mode == "🔬 Advanced Analytics":
        st.subheader("🔬 The Analytics Lab")
        st.markdown("Comprehensive dashboard replacing the old scatter plots.")
        
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("### 📈 Four Factors (Team Efficiency)")
            html = "<table class='sleek-table'><tr><th>Team</th><th>eFG%</th><th>TO/G</th><th>Opp PPP</th></tr>"
            for _, r in t_stats.sort_values('Win%', ascending=False).iterrows():
                t_eff = t_df[t_df['Team Name'] == r['Team Name']]
                efg = ((t_eff['FGM'].sum() + 0.5 * t_eff['3PM'].sum()) / t_eff['FGA'].sum() * 100) if t_eff['FGA'].sum() > 0 else 0
                to_g = t_eff['TO'].sum() / r['GP'] if r['GP'] > 0 else 0
                html += f"<tr><td class='player-name'>{r['Team Name']}</td><td>{efg:.1f}%</td><td>{to_g:.1f}</td><td>{r['Opp_PPP']:.2f}</td></tr>"
            st.markdown(html + "</table>", unsafe_allow_html=True)
        
        with c2:
            st.markdown("### 🏃 Pace & Space Quadrants")
            fig = px.scatter(t_stats, x='PPG', y='Opp_PPP', text='Team Name', 
                             title="Offense (Right is better) vs Defense (Lower is better)",
                             template="plotly_dark", color='Win%')
            fig.update_traces(textposition='top center')
            fig.update_yaxes(autorange="reversed")
            st.plotly_chart(fig, use_container_width=True)

    elif view_mode == "🔮 Oracle Predictor":
        st.subheader("🔮 SPAM Oracle Matchup Predictor")
        st.markdown("Simulates 4 Quarters, utilizes SOS adjustments, and generates a projected Box Score + MVP.")
        if not t_stats.empty and len(t_stats) >= 2:
            c1, c2 = st.columns(2)
            with c1: t1_sel = st.selectbox("Home Team", t_stats['Team Name'].tolist())
            with c2: t2_sel = st.selectbox("Away Team", t_stats['Team Name'].tolist(), index=1)
            
            if st.button("Simulate Matchup"):
                d1 = t_stats[t_stats['Team Name'] == t1_sel].iloc[0]
                d2 = t_stats[t_stats['Team Name'] == t2_sel].iloc[0]
                
                lg_ppg = t_stats['PPG'].mean()
                t1_adj_off = d1['PPG'] * (1 + (d1['SOS'] - 0.5))
                t2_adj_def = d2['Opp_PPP'] * 100 
                
                t1_exp = (t1_adj_off + t2_adj_def) / 2
                t2_exp = (d2['PPG'] * (1 + (d2['SOS'] - 0.5)) + (d1['Opp_PPP'] * 100)) / 2
                
                q_scores_1, q_scores_2 = [], []
                for _ in range(4):
                    q_scores_1.append(max(8, int(np.random.normal(t1_exp / 4, 3))))
                    q_scores_2.append(max(8, int(np.random.normal(t2_exp / 4, 3))))
                
                s1, s2 = sum(q_scores_1), sum(q_scores_2)
                if s1 == s2: s1 += 1; q_scores_1[-1] += 1
                
                win_team = t1_sel if s1 > s2 else t2_sel
                
                def generate_sim_box(team_name, total_pts):
                    roster = p_stats[p_stats['Team'] == team_name].sort_values('PTS', ascending=False)
                    if roster.empty: return pd.DataFrame()
                    team_ppg = roster['PTS'].sum()
                    sim_box = []
                    pts_pool = total_pts
                    for i, (_, p) in enumerate(roster.iterrows()):
                        if i == len(roster) - 1: share = pts_pool
                        else: share = int(total_pts * (p['PTS'] / team_ppg))
                        pts_pool -= share
                        sim_box.append({'Player': p['Player/Team'], 'PTS': share, 'REB': int(p['REB']), 'AST': int(p['AST'])})
                    return pd.DataFrame(sim_box)

                sb1 = generate_sim_box(t1_sel, s1)
                sb2 = generate_sim_box(t2_sel, s2)
                
                st.markdown(f"<div class='sim-box' style='background:#2a2d35;'><h4 style='color:#888;'>FINAL SCORE</h4><h1 style='font-size:54px; margin:0;'><span style='color:{'#00ff00' if s1>s2 else '#fff'};'>{s1}</span> - <span style='color:{'#00ff00' if s2>s1 else '#fff'};'>{s2}</span></h1><p>{t1_sel} vs {t2_sel}</p></div>", unsafe_allow_html=True)
                
                colA, colB = st.columns(2)
                with colA:
                    st.markdown(f"### {t1_sel} Box Score")
                    st.dataframe(sb1, hide_index=True, use_container_width=True)
                with colB:
                    st.markdown(f"### {t2_sel} Box Score")
                    st.dataframe(sb2, hide_index=True, use_container_width=True)
                    
                all_sim_p = pd.concat([sb1, sb2])
                mvp = all_sim_p.loc[all_sim_p['PTS'].idxmax()]
                st.success(f"🏆 **Simulated Game MVP:** {mvp['Player']} with {mvp['PTS']} Points!")

    elif view_mode == "🏦 The Vault":
        st.subheader("🏦 THE VAULT: HALL OF FAME")
        st.markdown("All-Time League Leaders mapped cleanly. No more Excel views.")
        
        p_tot = p_df.groupby('Player/Team').sum(numeric_only=True).reset_index()
        
        c1, c2 = st.columns(2)
        with c1: st.markdown(render_podium("All-Time Scoring Leaders", p_tot.sort_values('PTS', ascending=False), 'PTS'), unsafe_allow_html=True)
        with c2: st.markdown(render_podium("All-Time Assist Leaders", p_tot.sort_values('AST', ascending=False), 'AST'), unsafe_allow_html=True)
        
        c3, c4 = st.columns(2)
        with c3: st.markdown(render_podium("All-Time Rebound Leaders", p_tot.sort_values('REB', ascending=False), 'REB'), unsafe_allow_html=True)
        with c4: st.markdown(render_podium("All-Time Steals Leaders", p_tot.sort_values('STL', ascending=False), 'STL'), unsafe_allow_html=True)

        st.markdown("### 📜 The Top 10 Lists")
        tc1, tc2, tc3 = st.columns(3)
        with tc1: st.markdown(generate_mini_leaderboard("Points", p_tot, 'PTS', top_n=10, name_col="Player/Team"), unsafe_allow_html=True)
        with tc2: st.markdown(generate_mini_leaderboard("Assists", p_tot, 'AST', top_n=10, name_col="Player/Team"), unsafe_allow_html=True)
        with tc3: st.markdown(generate_mini_leaderboard("Rebounds", p_tot, 'REB', top_n=10, name_col="Player/Team"), unsafe_allow_html=True)
