import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path
import os

# 1. THEME & BORDER-KILL CSS
st.set_page_config(page_title="SPAM LEAGUE CENTRAL", page_icon="🏀", layout="wide")

st.markdown("""
    <style>
    /* REMOVE ALL BORDERS AND PADDING FOR EMBEDDING */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    div[data-testid="stToolbar"] {visibility: hidden;}
    [data-testid="stStatusWidget"] {display: none;}
    .block-container {padding: 0rem !important;}
    .stApp {bottom: 0; background: radial-gradient(circle, #1a1a1a 0%, #050505 100%); color: #d4af37;}
    
    /* SPAM BRANDING */
    .centered-splash { display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center; height: 50vh; width: 100%; }
    [data-testid="stMetric"] { background: rgba(255, 255, 255, 0.03) !important; backdrop-filter: blur(12px); border: 1px solid rgba(212, 175, 55, 0.3) !important; border-left: 6px solid #d4af37 !important; border-radius: 12px !important; padding: 22px !important; }
    .header-banner { padding: 20px; text-align: center; background: #d4af37; border-bottom: 5px solid #000; color: #000; font-family: 'Arial Black'; font-size: 28px; }
    @keyframes ticker { 0% { transform: translateX(100%); } 100% { transform: translateX(-100%); } }
    .ticker-wrap { width: 100%; overflow: hidden; background: #000; color: #d4af37; padding: 12px 0; font-family: 'Arial Black'; border-bottom: 2px solid #d4af37; }
    .ticker-content { display: inline-block; white-space: nowrap; animation: ticker 40s linear infinite; }
    .ticker-item { display: inline-block; margin-right: 80px; font-size: 20px; }
    </style>
    """, unsafe_allow_html=True)

# Logo Discovery
current_dir = Path(__file__).parent if "__file__" in locals() else Path.cwd()
logo_path = current_dir / "logo.jpg"

if 'spam_active' not in st.session_state: st.session_state.spam_active = False
if not st.session_state.spam_active:
    st.markdown('<div class="centered-splash">', unsafe_allow_html=True)
    if logo_path.exists(): st.image(str(logo_path), width=400)
    st.markdown("<h1 style='font-size: 80px; color: #d4af37;'>SPAM LEAGUE</h1>", unsafe_allow_html=True)
    if st.button("ENTER SPAM CENTRAL", use_container_width=True):
        st.session_state.spam_active = True
        st.rerun()
    st.stop()

# Data & Tabs (Same as before, now with Border-Kill applied)
SHEET_ID = "1rksLYUcXQJ03uTacfIBD6SRsvtH-IE6djqT-LINwcH4"
URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"

@st.cache_data(ttl=60)
def load_data():
    data = pd.read_csv(URL)
    data.columns = data.columns.str.strip()
    data['PIE'] = (data['PTS'] + data['REB'] + data['AST'] + data['STL'] + data['BLK']) - (pd.to_numeric(data['FGA'], errors='coerce').fillna(0) * 0.5)
    df_p = data[data['Type'].str.lower() == 'player'].copy()
    gp = df_p.groupby('Player/Team')['Game_ID'].nunique().reset_index(name='GP')
    p_avg = pd.merge(df_p.groupby(['Player/Team', 'Team Name']).sum(numeric_only=True).reset_index(), gp, on='Player/Team')
    for s in ['PTS', 'REB', 'AST']: p_avg[f'{s}/G'] = (p_avg[s] / p_avg['GP']).round(1)
    return p_avg, df_p

p_avg, df_raw = load_data()
st.markdown('<div class="header-banner">🏀 SPAM LEAGUE CENTRAL</div>', unsafe_allow_html=True)
st.dataframe(p_avg.sort_values('PTS/G', ascending=False), use_container_width=True, hide_index=True)

