import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
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
    .stat-row { display: flex; justify-content: space-between; border-bottom: 1px dashed #333; padding: 6px 0; font-size: 14px; }
    .stat-val { font-weight: bold; color: #d4af37; }
    .stat-label { color: #8b949e; }
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
        df = pd.read_csv(URL)
        df.columns = df.columns.str.strip()
        
        if 'Player/Team' in df.columns:
            df['Player/Team'] = df['Player/Team'].apply(smart_name_scrubber)
            
        req_cols = ['PTS', 'REB', 'AST', 'STL', 'BLK', 'TO', 'FGA', 'FGM', '3PM', '3PA', 'FTA', 'FTM', 'Game_ID', 'Win', 'Season', 'Type', 'Team Name']
        for c in req_cols:
            if c not in df.columns: df[c] = 0
            if c not in ['Type', 'Team Name', 'Player/Team']: 
                df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)
            
        if 'Win' in df.columns: df['Win'] = pd.to_numeric(df['Win'], errors='coerce').fillna(0).apply(lambda x: 1 if x > 0 else 0)
        df['is_ff'] = (df['PTS'] == 0) & (df['FGA'] == 0) & (df['REB'] == 0)
        df['PIE_Raw'] = (df['PTS'] + df['REB'] + df['AST'] + df['STL'] + df['BLK']) - (df['FGA'] * 0.5) - df['TO']
        df['Poss_Raw'] = df['FGA'] + 0.44 * df['FTA'] + df['TO']
        return df
    except Exception as e: return str(e)

full_df = load_data()

# --- 3. HTML & CHART GENERATORS ---
def generate_2k_player_card(player_name, stats, rank=""):
    rank_badge = f'<div style="position:absolute; top:-10px; right:-10px; background:#d4af37; color:#000; font-weight:bold; padding:8px; border-radius:50%; border:2px solid #fff; z-index:10;">#{rank}</div>' if rank else ""
    return f'''<div class="flip-card" style="height: 320px;">
{rank_badge}
<div class="flip-card-inner">
<div class="flip-card-front">
<img src="https://upload.wikimedia.org/wikipedia/commons/7/7c/Profile_avatar_placeholder_large.png" style="width: 100px; border-radius: 50%; border: 2px solid #d4af37; margin-bottom: 15px;">
<h3 style="margin: 0; color: white;">{player_name}</h3>
<h2 style="color: #d4af37; margin-top: 5px;">{stats.get('PIE', 0):.1f} PIE</h2>
</div>
<div class="flip-card-back">
<h4 style="color: #d4af37; border-bottom: 1px solid #333; padding-bottom: 5px; margin-top: 0;">Season Averages</h4>
<div class="stat-row"><span class="stat-label">PPG</span> <span class="stat-val">{stats.get('PTS/G', 0):.1f}</span></div>
<div class="stat-row"><span class="stat-label">RPG</span> <span class="stat-val">{stats.get('REB/G', 0):.1f}</span></div>
<div class="stat-row"><span class="stat-label">APG</span> <span class="stat-val">{stats.get('AST/G', 0):.1f}</span></div>
<div class="stat-row"><span class="stat-label">SPG | BPG</span> <span class="stat-val">{stats.get('STL/G', 0):.1f} | {stats.get('BLK/G', 0):.1f}</span></div>
<div class="stat-row"><span class="stat-label">FG%</span> <span class="stat-val">{stats.get('FG%', 0)}%</span></div>
<div class="stat-row"><span class="stat-label">TS%</span> <span class="stat-val">{stats.get('TS%', 0):.1f}%</span></div>
</div>
</div>
</div>'''

def generate_2k_standings_row(team, rank, wins, losses, win_pct, ppg, rpg, apg, off_rtg):
    color = "#ffd700" if rank == 1 else "#c0c0c0" if rank == 2 else "#cd7f32" if rank == 3 else "#00bfff"
    return f"""<div style="background: linear-gradient(145deg, #1c2128, #2a2d35); border-left: 6px solid {color}; border-radius: 8px; padding: 15px; margin-bottom: 12px; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 4px 6px rgba(0,0,0,0.3);">
<div style="display: flex; align-items: center; width: 30%;">
<h2 style="margin:0; color:{color}; margin-right: 20px; font-size: 28px; font-family: 'Arial Black', sans-serif;">#{rank}</h2>
<div>
<h3 style="margin:0; color:white; font-size: 18px; text-transform: uppercase;">{team}</h3>
<div style="font-size: 14px; color: #aaa; margin-top: 2px;">Record: <span style="color:#fff; font-weight:bold;">{int(wins)}-{int(losses)}</span></div>
</div>
</div>
<div style="display: flex; width: 45%; justify-content: space-around; text-align: center;">
<div><div style="font-size:11px; color:#888; text-transform:uppercase;">Win %</div><div style="font-size:16px; font-weight:bold; color:#fff;">{win_pct:.3f}</div></div>
<div><div style="font-size:11px; color:#888; text-transform:uppercase;">PPG</div><div style="font-size:16px; font-weight:bold; color:#fff;">{ppg:.1f}</div></div>
<div><div style="font-size:11px; color:#888; text-transform:uppercase;">RPG</div><div style="font-size:16px; font-weight:bold; color:#fff;">{rpg:.1f}</div></div>
<div><div style="font-size:11px; color:#888; text-transform:uppercase;">APG</div><div style="font-size:16px; font-weight:bold; color:#fff;">{apg:.1f}</div></div>
</div>
<div style="text-align: right; width: 25%;">
<div style="font-size: 11px; color: #888; text-transform: uppercase; font-weight: bold;">Offensive Rtg</div>
<div style="font-size: 24px; font-weight: bold; color: #00ff00;">{off_rtg:.1f}</div>
</div>
</div>"""

def generate_mini_leaderboard(title, df, stat_col, color="#d4af37"):
    html = f"<div style='background:#1c2128; padding:15px; border-radius:8px; border-left:4px solid {color}; margin-bottom:15px; box-shadow: 0 4px 6px rgba(0,0,0,0.3);'>"
    html += f"<h3 style='margin-top:0; color:#fff; font-size:16px; border-bottom:1px dashed #444; padding-bottom:8px; text-transform:uppercase;'>{title}</h3>"
    for i, (_, row) in enumerate(df.head(5).iterrows()):
        val_str = f"{row[stat_col]:.1f}"
        rank_color = "#ffd700" if i == 0 else "#888"
        html += f"<div style='display:flex; justify-content:space-between; align-items:center; margin-bottom:6px; font-size:14px;'>"
        html += f"<div><span style='color:{rank_color}; font-weight:bold; margin-right:8px;'>{i+1}.</span><span style='color:#ddd; font-weight:bold;'>{row['Player/Team']}</span></div>"
        html += f"<span style='color:{color}; font-weight:bold;'>{val_str}</span>"
        html += f"</div>"
    html += "</div>"
    return html

def draw_dynamic_radar(p1_name, r1_vals, p2_name, r2_vals, categories, title):
    # Ensure the loop closes for the radar chart
    r1_vals = list(r1_vals) + [r1_vals[0]]
    r2_vals = list(r2_vals) + [r2_vals[0]]
    cats = list(categories) + [categories[0]]
    
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(r=r1_vals, theta=cats, fill='toself', name=p1_name, fillcolor='rgba(212, 175, 55, 0.4)', line=dict(color='#d4af37', width=2)))
    fig.add_trace(go.Scatterpolar(r=r2_vals, theta=cats, fill='toself', name=p2_name, fillcolor='rgba(204, 0, 0, 0.4)', line=dict(color='#cc0000', width=2)))
    fig.update_layout(
        title=dict(text=title, font=dict(color='white', size=16)),
        polar=dict(radialaxis=dict(visible=True, range=[0, 100], showticklabels=False, gridcolor='#444')),
        showlegend=True, template="plotly_dark", height=380, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=40, r=40, t=60, b=40)
    )
    return fig

# --- 4. APP LOGIC & NAVIGATION ROUTING ---
if isinstance(full_df, str): 
    st.error(f"⚠️ DATA ERROR: {full_df}")
elif full_df is not None and not full_df.empty:
    
    seasons = sorted([int(s) for s in full_df['Season'].unique() if pd.notna(s) and int(s) > 0], reverse=True)
    st.sidebar.title("⚙️ Hub Controls")
    view_mode = st.sidebar.radio("Navigation", ["🏠 League Home", "🏆 Standings", "🏢 Team Pages", "🔬 Advanced Analytics", "⚔️ Head-to-Head Radar"])
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
        latest_teams = df_reg.sort_values('Season', ascending=False).groupby('Player/Team')['Team Name'].first().reset_index()
        p_stats = df_reg.groupby('Player/Team').mean(numeric_only=True).reset_index()
        p_stats = p_stats.merge(latest_teams, on='Player/Team', how='left')

        for col in ['PTS', 'REB', 'AST', 'STL', 'BLK', '3PM', '3PA', 'TO', 'FGA', 'FGM', 'FTA', 'FTM', 'Poss_Raw']: p_stats[f'{col}/G'] = p_stats[col].round(1)
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

    # TEAM STATS CALCULATION
    t_stats = pd.DataFrame()
    if 'Type' in df_active.columns:
        team_df = df_active[df_active['Type'].astype(str).str.lower() == 'team']
        team_df = team_df[(team_df['Team Name'].astype(str) != '0') & (team_df['Team Name'].notna())]
        if not team_df.empty:
            t_stats = team_df.groupby('Team Name').sum(numeric_only=True).reset_index()
            t_stats['GP'] = team_df.groupby('Team Name')['Game_ID'].count().values
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
        st.subheader("👑 Official League Leaders (5-Tool)")
        c1, c2, c3, c4, c5 = st.columns(5)
        with c1: st.markdown(generate_mini_leaderboard("Points", p_stats.sort_values('PTS/G', ascending=False), 'PTS/G', color="#cc0000"), unsafe_allow_html=True)
        with c2: st.markdown(generate_mini_leaderboard("Assists", p_stats.sort_values('AST/G', ascending=False), 'AST/G', color="#00bfff"), unsafe_allow_html=True)
        with c3: st.markdown(generate_mini_leaderboard("Rebounds", p_stats.sort_values('REB/G', ascending=False), 'REB/G', color="#32cd32"), unsafe_allow_html=True)
        with c4: st.markdown(generate_mini_leaderboard("Steals", p_stats.sort_values('STL/G', ascending=False), 'STL/G', color="#ff8c00"), unsafe_allow_html=True)
        with c5: st.markdown(generate_mini_leaderboard("Blocks", p_stats.sort_values('BLK/G', ascending=False), 'BLK/G', color="#8a2be2"), unsafe_allow_html=True)

    elif view_mode == "🏆 Standings":
        st.subheader(f"🏆 {banner_text} Power Rankings")
        if not t_stats.empty:
            sort_stats = t_stats.sort_values(by=['Win', 'Win %', 'OffRtg'], ascending=[False, False, False]).reset_index(drop=True)
            for idx, row in sort_stats.iterrows():
                st.markdown(generate_2k_standings_row(row['Team Name'], idx + 1, row['Win'], row['GP']-row['Win'], row['Win %']/100, row['PTS/G'], row['REB/G'], row['AST/G'], row['OffRtg']), unsafe_allow_html=True)
        else:
            st.info("No team totals found in the dataset for this scope.")

    elif view_mode == "🏢 Team Pages":
        available_teams = sorted([t for t in p_stats['Team Name'].unique() if str(t) != '0' and pd.notna(t)])
        if available_teams:
            selected_team = st.selectbox("Select Team Roster", available_teams)
            st.subheader(f"📋 {selected_team} Roster Binder")
            team_p_stats = p_stats[p_stats['Team Name'] == selected_team].reset_index(drop=True)
            cols = st.columns(4)
            for idx, row in team_p_stats.iterrows():
                with cols[idx % 4]: st.markdown(generate_2k_player_card(row['Player/Team'], row, rank=""), unsafe_allow_html=True)

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
        def rev_norm(val, mx): return max(0, 100 - (norm(val, mx))) # Higher is worse (like Turnovers)

        if mode == "Player vs Player" and not df_reg.empty:
            c1, c2 = st.columns(2)
            player_list = p_stats['Player/Team'].tolist()
            if len(player_list) >= 2:
                with c1: p1_sel = st.selectbox("Player 1 (Gold)", player_list)
                with c2: p2_sel = st.selectbox("Player 2 (Red)", player_list, index=1)
                
                d1 = p_stats[p_stats['Player/Team'] == p1_sel].iloc[0]
                d2 = p_stats[p_stats['Player/Team'] == p2_sel].iloc[0]
                mx = p_stats.max(numeric_only=True)
                
                # RADAR 1: The 5-Tool Core
                cats1 = ['Scoring (PPG)', 'Playmaking (APG)', 'Rebounding (RPG)', 'Defense (Stocks)', 'Efficiency (FG%)']
                r1_1 = [norm(d1['PTS/G'], mx['PTS/G']), norm(d1['AST/G'], mx['AST/G']), norm(d1['REB/G'], mx['REB/G']), norm(d1['DEF'], mx['DEF']), norm(d1['FG%'], 100)]
                r2_1 = [norm(d2['PTS/G'], mx['PTS/G']), norm(d2['AST/G'], mx['AST/G']), norm(d2['REB/G'], mx['REB/G']), norm(d2['DEF'], mx['DEF']), norm(d2['FG%'], 100)]
                
                # RADAR 2: Sharpshooter Matrix
                cats2 = ['3P Vol (3PA)', '3P%', 'FT%', 'True Shooting', 'Effective FG%']
                r1_2 = [norm(d1['3PA/G'], mx['3PA/G']), norm(d1['3P%'], 100), norm(d1['FT%'], 100), norm(d1['TS%'], 100), norm(d1['eFG%'], 100)]
                r2_2 = [norm(d2['3PA/G'], mx['3PA/G']), norm(d2['3P%'], 100), norm(d2['FT%'], 100), norm(d2['TS%'], 100), norm(d2['eFG%'], 100)]
                
                # RADAR 3: Floor General Web
                cats3 = ['AST/TO Ratio', 'Total Assists', 'Turnovers (Low=Good)', 'Possessions Handled', 'Win %']
                r1_3 = [norm(d1['AST/TO'], mx['AST/TO']), norm(d1['AST/G'], mx['AST/G']), rev_norm(d1['TO/G'], mx['TO/G']), norm(d1['Poss_Raw/G'], mx['Poss_Raw/G']), norm(d1['Win'], mx['Win'])]
                r2_3 = [norm(d2['AST/TO'], mx['AST/TO']), norm(d2['AST/G'], mx['AST/G']), rev_norm(d2['TO/G'], mx['TO/G']), norm(d2['Poss_Raw/G'], mx['Poss_Raw/G']), norm(d2['Win'], mx['Win'])]
                
                # RADAR 4: Impact & Volume Engine
                cats4 = ['Overall Impact (PIE)', 'Pts Per Possession', 'Volume (FGA)', 'FT Attempts', 'Double-Doubles']
                r1_4 = [norm(d1['PIE'], mx['PIE']), norm(d1['PPP'], mx['PPP']), norm(d1['FGA/G'], mx['FGA/G']), norm(d1['FTA/G'], mx['FTA/G']), norm(d1['DD'], mx['DD'])]
                r2_4 = [norm(d2['PIE'], mx['PIE']), norm(d2['PPP'], mx['PPP']), norm(d2['FGA/G'], mx['FGA/G']), norm(d2['FTA/G'], mx['FTA/G']), norm(d2['DD'], mx['DD'])]
                
                row1_col1, row1_col2 = st.columns(2)
                with row1_col1: st.plotly_chart(draw_dynamic_radar(p1_sel, r1_1, p2_sel, r2_1, cats1, "The 5-Tool Core"), use_container_width=True)
                with row1_col2: st.plotly_chart(draw_dynamic_radar(p1_sel, r1_2, p2_sel, r2_2, cats2, "Sharpshooter Matrix"), use_container_width=True)
                
                row2_col1, row2_col2 = st.columns(2)
                with row2_col1: st.plotly_chart(draw_dynamic_radar(p1_sel, r1_3, p2_sel, r2_3, cats3, "Floor General Web"), use_container_width=True)
                with row2_col2: st.plotly_chart(draw_dynamic_radar(p1_sel, r1_4, p2_sel, r2_4, cats4, "Impact & Volume Engine"), use_container_width=True)

        elif mode == "Team vs Team" and not t_stats.empty:
            c1, c2 = st.columns(2)
            team_list = t_stats['Team Name'].tolist()
            if len(team_list) >= 2:
                with c1: t1_sel = st.selectbox("Team 1 (Gold)", team_list)
                with c2: t2_sel = st.selectbox("Team 2 (Red)", team_list, index=1)
                
                d1 = t_stats[t_stats['Team Name'] == t1_sel].iloc[0]
                d2 = t_stats[t_stats['Team Name'] == t2_sel].iloc[0]
                mx = t_stats.max(numeric_only=True)
                
                # RADAR 1: Team Core Stats
                cats1 = ['Points (PPG)', 'Assists (APG)', 'Rebounds (RPG)', 'Defense (Stocks)', 'Win %']
                r1_1 = [norm(d1['PTS/G'], mx['PTS/G']), norm(d1['AST/G'], mx['AST/G']), norm(d1['REB/G'], mx['REB/G']), norm(d1['DEF'], mx['DEF']), d1['Win %']]
                r2_1 = [norm(d2['PTS/G'], mx['PTS/G']), norm(d2['AST/G'], mx['AST/G']), norm(d2['REB/G'], mx['REB/G']), norm(d2['DEF'], mx['DEF']), d2['Win %']]
                
                # RADAR 2: Team Efficiency
                cats2 = ['Offensive Rating', 'True Shooting', 'Effective FG%', '3P%', 'AST/TO Ratio']
                r1_2 = [norm(d1['OffRtg'], mx['OffRtg']), norm(d1['TS%'], 100), norm(d1['eFG%'], 100), norm(d1['3P%'], 100), norm(d1['AST/TO'], mx['AST/TO'])]
                r2_2 = [norm(d2['OffRtg'], mx['OffRtg']), norm(d2['TS%'], 100), norm(d2['eFG%'], 100), norm(d2['3P%'], 100), norm(d2['AST/TO'], mx['AST/TO'])]
                
                row1_col1, row1_col2 = st.columns(2)
                with row1_col1: st.plotly_chart(draw_dynamic_radar(t1_sel, r1_1, t2_sel, r2_1, cats1, "Team 5-Tool Output"), use_container_width=True)
                with row1_col2: st.plotly_chart(draw_dynamic_radar(t1_sel, r1_2, t2_sel, r2_2, cats2, "Team Efficiency Engine"), use_container_width=True)
            else:
                st.info("Need more team data in this season to compare.")
