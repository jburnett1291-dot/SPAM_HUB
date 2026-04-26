import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

# --- 1. UI & SLEEK CSS (PORTED FROM MLB WITH 2K AESTHETICS) ---
st.set_page_config(page_title="SPAM LEAGUE CENTRAL", page_icon="🏀", layout="wide")

css_styles = """
<style>
    .stApp { background: radial-gradient(circle at top, #1f1f1f 0%, #050505 100%); color: #e0e0e0; }
    .header-banner { 
        padding: 25px; text-align: center; 
        background: linear-gradient(90deg, #d4af37 0%, #f7e08a 50%, #d4af37 100%);
        color: #000; font-family: 'Arial Black'; font-size: 28px; border-radius: 8px; margin-bottom: 20px;
    }
    
    /* 3D FLIP CARD ENGINE (ADAPTED FOR 2K) */
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

# --- 2. DATA ENGINE & CUSTOM 20-MINUTE PACE MATH ---
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
            
        # Hard binary win column
        if 'Win' in df.columns:
            df['Win'] = df['Win'].apply(lambda x: 1 if x > 0 else 0)
            
        df['is_ff'] = (df['PTS'] == 0) & (df['FGA'] == 0) & (df['REB'] == 0)
        
        # Multiplier Logic (DD / TD)
        def calc_multis(row):
            if row['is_ff']: return pd.Series([0, 0])
            s = [row['PTS'], row['REB'], row['AST'], row['STL'], row['BLK']]
            tens = sum(1 for x in s if x >= 10)
            return pd.Series([1 if tens >= 2 else 0, 1 if tens >= 3 else 0])
        df[['DD', 'TD']] = df.apply(calc_multis, axis=1)
        
        # Custom 20-Minute League Stat Formulas
        df['PIE_Raw'] = (df['PTS'] + df['REB'] + df['AST'] + df['STL'] + df['BLK']) - (df['FGA'] * 0.5) - df['TO']
        
        # Adjusted Possession Formula for 20-min format (Base estimation)
        df['Poss_Raw'] = df['FGA'] + 0.44 * df['FTA'] + df['TO']
        return df
    except Exception as e: return str(e)

full_df = load_data()

# --- 3. HTML GENERATORS (PORTED FROM MLB) ---
def generate_2k_player_card(player_name, stats, rank=""):
    rank_badge = f'<div style="position:absolute; top:-10px; right:-10px; background:#d4af37; color:#000; font-weight:bold; padding:8px; border-radius:50%; border:2px solid #fff; z-index:10;">#{rank}</div>' if rank else ""
    
    return f'''
    <div class="flip-card" style="height: 320px;">
        {rank_badge}
        <div class="flip-card-inner">
            <div class="flip-card-front">
                <img src="https://upload.wikimedia.org/wikipedia/commons/7/7c/Profile_avatar_placeholder_large.png" style="width: 100px; border-radius: 50%; border: 2px solid #d4af37; margin-bottom: 15px;">
                <h3 style="margin: 0; color: white;">{player_name}</h3>
                <h2 style="color: #d4af37; margin-top: 5px;">{stats['PIE']:.1f} PIE</h2>
            </div>
            <div class="flip-card-back">
                <h4 style="color: #d4af37; border-bottom: 1px solid #333; padding-bottom: 5px; margin-top: 0;">Season Averages</h4>
                <div class="stat-row"><span class="stat-label">PPG</span> <span class="stat-val">{stats['PTS/G']:.1f}</span></div>
                <div class="stat-row"><span class="stat-label">RPG</span> <span class="stat-val">{stats['REB/G']:.1f}</span></div>
                <div class="stat-row"><span class="stat-label">APG</span> <span class="stat-val">{stats['AST/G']:.1f}</span></div>
                <div class="stat-row"><span class="stat-label">SPG | BPG</span> <span class="stat-val">{stats['STL/G']:.1f} | {stats['BLK/G']:.1f}</span></div>
                <div class="stat-row"><span class="stat-label">FG%</span> <span class="stat-val">{stats['FG%']}%</span></div>
                <div class="stat-row"><span class="stat-label">3PM/G</span> <span class="stat-val">{stats['3PM/G']:.1f}</span></div>
            </div>
        </div>
    </div>
    '''

def draw_2k_comparison_radar(p1_name, p1_stats, p2_name, p2_stats, maxes):
    # Normalize stats to a 0-100 scale for the radar based on league maximums
    def norm(val, max_val): return min(100, (val / max_val) * 100) if max_val > 0 else 0
    
    categories = ['Scoring (PPG)', 'Playmaking (APG)', 'Rebounding (RPG)', 'Defense (Stocks)', 'Efficiency (FG%)', 'Scoring (PPG)']
    
    r1 = [norm(p1_stats['PTS/G'], maxes['PTS']), norm(p1_stats['AST/G'], maxes['AST']), norm(p1_stats['REB/G'], maxes['REB']), norm(p1_stats['STL/G'] + p1_stats['BLK/G'], maxes['DEF']), norm(p1_stats['FG%'], 100), norm(p1_stats['PTS/G'], maxes['PTS'])]
    r2 = [norm(p2_stats['PTS/G'], maxes['PTS']), norm(p2_stats['AST/G'], maxes['AST']), norm(p2_stats['REB/G'], maxes['REB']), norm(p2_stats['STL/G'] + p2_stats['BLK/G'], maxes['DEF']), norm(p2_stats['FG%'], 100), norm(p2_stats['PTS/G'], maxes['PTS'])]

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(r=r1, theta=categories, fill='toself', name=p1_name, fillcolor='rgba(212, 175, 55, 0.4)', line=dict(color='#d4af37', width=2)))
    fig.add_trace(go.Scatterpolar(r=r2, theta=categories, fill='toself', name=p2_name, fillcolor='rgba(204, 0, 0, 0.4)', line=dict(color='#cc0000', width=2)))
    fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100], showticklabels=False)), showlegend=True, template="plotly_dark", height=400, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
    return fig

# --- 4. APP LOGIC ---
if isinstance(full_df, str): st.error(f"⚠️ DATA ERROR: {full_df}")
elif full_df is not None:
    st.markdown('<div class="header-banner">🏀 SPAM LEAGUE INTELLIGENCE HUB</div>', unsafe_allow_html=True)

    # Simplified Aggregation for Demo
    df_reg = full_df[full_df['Type'].str.lower() == 'player']
    p_stats = df_reg.groupby('Player/Team').mean(numeric_only=True).reset_index()
    for col in ['PTS', 'REB', 'AST', 'STL', 'BLK', '3PM']: p_stats[f'{col}/G'] = p_stats[col].round(1)
    p_stats['FG%'] = (p_stats['FGM'] / p_stats['FGA'].replace(0,1) * 100).round(1)
    p_stats['PIE'] = p_stats['PIE_Raw'].round(1)
    p_stats = p_stats.sort_values('PIE', ascending=False).reset_index(drop=True)

    tab1, tab2 = st.tabs(["📋 Roster Binder", "⚔️ Head-to-Head Radar"])

    with tab1:
        st.subheader("Player Analytics Binder")
        cols = st.columns(4)
        for idx, row in p_stats.head(12).iterrows():
            with cols[idx % 4]:
                st.markdown(generate_2k_player_card(row['Player/Team'], row, rank=idx+1), unsafe_allow_html=True)

    with tab2:
        st.subheader("🕸️ Attribute Web Comparison")
        c1, c2 = st.columns(2)
        with c1: p1_sel = st.selectbox("Player 1 (Gold)", p_stats['Player/Team'].tolist())
        with c2: p2_sel = st.selectbox("Player 2 (Red)", p_stats['Player/Team'].tolist(), index=1)
        
        if p1_sel and p2_sel:
            p1_data = p_stats[p_stats['Player/Team'] == p1_sel].iloc[0]
            p2_data = p_stats[p_stats['Player/Team'] == p2_sel].iloc[0]
            
            league_maxes = {'PTS': p_stats['PTS/G'].max(), 'AST': p_stats['AST/G'].max(), 'REB': p_stats['REB/G'].max(), 'DEF': (p_stats['STL/G'] + p_stats['BLK/G']).max()}
            st.plotly_chart(draw_2k_comparison_radar(p1_sel, p1_data, p2_sel, p2_data, league_maxes), use_container_width=True)
