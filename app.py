import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import re # <-- This is the new engine for the Smart Scrubber

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

# --- THE SMART SCRUBBER FUNCTION ---
def smart_name_scrubber(raw_name):
    """Dynamically strips OCR garbage and clan tags without needing a dictionary."""
    if pd.isna(raw_name) or not isinstance(raw_name, str): 
        return raw_name
        
    # Nuke the OCR vertical line artifacts at the START of the name
    clean_name = re.sub(r'^[|Il\s]+', '', raw_name)
    
    # Nuke common bracketed clan tags at the start like [SPAM] Kay or (QSPN) Kay
    clean_name = re.sub(r'^\[.*?\]\s*|^\(.*?\)\s*', '', clean_name)
    
    # Strip accidental trailing spaces and force standard Title Case
    return clean_name.strip().title()

@st.cache_data(ttl=60)
def load_data():
    try:
        df = pd.read_csv(URL)
        df.columns = df.columns.str.strip()
        
        # --- APPLY THE INVISIBLE SCRUBBER ---
        if 'Player/Team' in df.columns:
            df['Player/Team'] = df['Player/Team'].apply(smart_name_scrubber)
            
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
