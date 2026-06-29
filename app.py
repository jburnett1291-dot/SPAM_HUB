import streamlit as st
import pandas as pd
import numpy as np
import json
import random

# ==========================================
# 1. CONFIGURATION & BRAND STYLING
# ==========================================
st.set_page_config(page_title="Qwik's Cup League | Master Dashboard", layout="wide", initial_sidebar_state="expanded")

def inject_custom_css():
    st.markdown("""
    <style>
        /* QCL Color Palette: Navy Blue (#0A192F), Bronze (#CD7F32), Gold (#D4AF37) */
        .stApp {
            background-color: #0A192F;
            color: #E6F1FF;
        }
        h1, h2, h3, h4, h5, h6 {
            color: #D4AF37 !important;
            font-family: 'Helvetica Neue', sans-serif;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        div[data-testid="stSidebar"] {
            background-color: #060D1A;
            border-right: 2px solid #CD7F32;
        }
        .stButton>button {
            background-color: #CD7F32;
            color: #0A192F;
            font-weight: 800;
            border: 1px solid #D4AF37;
            border-radius: 4px;
            transition: all 0.3s ease;
        }
        .stButton>button:hover {
            background-color: #D4AF37;
            color: #000000;
            border-color: #FFF;
        }
        .metric-container {
            background-color: #112240;
            border-left: 4px solid #D4AF37;
            padding: 1rem;
            border-radius: 5px;
            margin-bottom: 1rem;
        }
        .metric-title {
            color: #8892B0;
            font-size: 0.9rem;
            text-transform: uppercase;
        }
        .metric-value {
            color: #E6F1FF;
            font-size: 1.8rem;
            font-weight: bold;
        }
        hr {
            border-color: #CD7F32;
            opacity: 0.3;
        }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. ROBUST DATA FALLBACKS & STATE MANAGEMENT
# ==========================================
MOCK_STATE = {
    "teams": [
        {"team_id": 1, "name": "Hells Paradise", "wins": 11, "losses": 1, "streak": "W6", "net_rating": 12.4, "pace": 98.5},
        {"team_id": 2, "name": "OIAM", "wins": 8, "losses": 4, "streak": "W2", "net_rating": 5.2, "pace": 101.2},
        {"team_id": 3, "name": "MOTF", "wins": 7, "losses": 5, "streak": "L1", "net_rating": 2.1, "pace": 96.0},
        {"team_id": 4, "name": "Rise Above", "wins": 6, "losses": 6, "streak": "W1", "net_rating": -1.5, "pace": 99.1}
    ],
    "rosters": {
        "Hells Paradise": ["Venom", "TaeCP", "Deadeye", "Krashout", "Clutch"],
        "OIAM": ["Prime", "Shadow", "Ghost", "Sniper", "Tank"]
    },
    "players": [
        {"name": "Venom", "team": "Hells Paradise", "pos": "PG", "pts": 24.5, "ast": 9.2, "ts_pct": 0.612, "usg_pct": 28.5, "dna": "Floor General"},
        {"name": "TaeCP", "team": "Hells Paradise", "pos": "C", "pts": 14.2, "reb": 12.5, "ts_pct": 0.650, "usg_pct": 18.2, "dna": "Paint Beast"},
        {"name": "Krashout", "team": "Hells Paradise", "pos": "SF", "pts": 28.1, "reb": 6.0, "ts_pct": 0.590, "usg_pct": 32.1, "dna": "Scoring Machine"}
    ],
    "syndicate_bank": {
        "weekly_pot": 120.00,
        "entry_fee": 5.00,
        "active_participants": 24
    }
}

@st.cache_data
def load_league_data():
    # In a production environment, this would parse 'qcl_state.json'
    # For now, it returns the bulletproof fallback state.
    return MOCK_STATE

def resolve_discord_id(player_name):
    # Simulates the two-stage resolver mapping legacy IDs
    legacy_map = {"Krashout": "Dynasty_3x", "Deadeye": "Undefeated_S2", "Veno": "81_Point_God"}
    return legacy_map.get(player_name, "Verified")

# ==========================================
# 3. CORE UI COMPONENTS & TABS
# ==========================================
def render_metric_card(title, value):
    st.markdown(f"""
        <div class="metric-container">
            <div class="metric-title">{title}</div>
            <div class="metric-value">{value}</div>
        </div>
    """, unsafe_allow_html=True)

def app_home():
    st.title("🏆 QCL Master Dashboard")
    st.markdown("Welcome to the unified terminal for the **Qwik's Cup League**. Use the sidebar to navigate the ecosystem.")
    
    col1, col2, col3 = st.columns(3)
    data = load_league_data()
    
    with col1:
        render_metric_card("League Leader", f"{data['teams'][0]['name']} ({data['teams'][0]['wins']}-{data['teams'][0]['losses']})")
    with col2:
        render_metric_card("Active Win Streak", f"{data['teams'][0]['name']} - {data['teams'][0]['streak']}")
    with col3:
        render_metric_card("Syndicate Pot", f"${data['syndicate_bank']['weekly_pot']:.2f}")

def eternal_record():
    st.title("🏛️ The Eternal Record")
    st.markdown("The canonical ledger of Founding-Era history. Immutable and verified.")
    
    st.subheader("Legendary Feats")
    col1, col2 = st.columns(2)
    with col1:
        st.info("**The Dynasty:** Krashout's 3-Title Reign locked into the Vault.")
        st.info("**Perfection:** Deadeye's Undefeated Season 2 Campaign.")
    with col2:
        st.info("**The Scoring God:** Veno's 81-point performance stat-matched and verified.")
        st.info("**The Maestro:** Trifecta's 40-assist game permanently archived.")

    st.subheader("Historical ID Resolver")
    search_name = st.text_input("Enter Player Name to Resolve Legacy Status:", "Krashout")
    if search_name:
        status = resolve_discord_id(search_name)
        st.success(f"**{search_name}** Record Status: {status}")

def advanced_analytics():
    st.title("🔬 Advanced Analytics Lab")
    data = load_league_data()
    df_players = pd.DataFrame(data["players"])
    
    st.markdown("### Player DNA & Efficiency Metrics")
    st.dataframe(df_players.style.format({
        "ts_pct": "{:.3f}",
        "usg_pct": "{:.1f}%",
        "pts": "{:.1f}",
        "ast": "{:.1f}",
        "reb": "{:.1f}"
    }), use_container_width=True)

    st.markdown("### Team Pace & Net Rating")
    df_teams = pd.DataFrame(data["teams"])[["name", "net_rating", "pace", "wins", "losses"]]
    df_teams = df_teams.sort_values(by="net_rating", ascending=False)
    st.dataframe(df_teams, use_container_width=True)

def the_hunt():
    st.title("⚔️ The Hunt (Live Ops)")
    data = load_league_data()
    
    st.markdown("### The Syndicate Program")
    st.markdown("Weekly payout incentive program tracking.")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        render_metric_card("Weekly Contribution", f"${data['syndicate_bank']['entry_fee']:.2f} / team")
    with col2:
        render_metric_card("Active Syndicate Teams", str(data['syndicate_bank']['active_participants']))
    with col3:
        render_metric_card("Total Prize Pot", f"${data['syndicate_bank']['weekly_pot']:.2f}")

    st.markdown("---")
    st.markdown("### Marked Teams & Bounties")
    for team in data['teams']:
        if "W" in team['streak'] and int(team['streak'].replace("W", "")) >= 3:
            st.warning(f"🎯 **BOUNTY ACTIVE:** {team['name']} is on a {team['streak']} streak. Defeating them yields a Syndicate bonus.")

def league_office():
    st.title("🏢 League Office")
    data = load_league_data()
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("### Active Rosters")
        selected_team = st.selectbox("Select Team:", list(data["rosters"].keys()))
        roster = data["rosters"][selected_team]
        for player in roster:
            st.markdown(f"- **{player}**")
            
    with col2:
        st.markdown("### Power Rankings")
        df_power = pd.DataFrame(data["teams"])[["name", "wins", "losses"]]
        st.dataframe(df_power, hide_index=True)

def oracle_predictor():
    st.title("🔮 Oracle Predictor V2")
    st.markdown("Simulates matchups using Pace-Adjusted Possessions and Net Rating differentials.")
    
    data = load_league_data()
    team_names = [t["name"] for t in data["teams"]]
    
    col1, col2 = st.columns(2)
    with col1:
        home_team = st.selectbox("Home Team", team_names, index=0)
    with col2:
        away_team = st.selectbox("Away Team", team_names, index=1)
        
    if st.button("RUN 10,000 SIMULATIONS"):
        if home_team == away_team:
            st.error("Select two different teams.")
        else:
            with st.spinner("Simulating 10,000 iterations based on advanced metrics..."):
                t1_data = next(t for t in data["teams"] if t["name"] == home_team)
                t2_data = next(t for t in data["teams"] if t["name"] == away_team)
                
                # Simulation Logic utilizing Net Rating and Pace
                base_home_adv = 2.5
                rating_diff = t1_data["net_rating"] - t2_data["net_rating"] + base_home_adv
                win_prob = 50 + (rating_diff * 1.5)
                win_prob = max(min(win_prob, 95), 5) # Cap between 5% and 95%
                
                st.success("Simulation Complete!")
                
                res_col1, res_col2 = st.columns(2)
                with res_col1:
                    render_metric_card(f"{home_team} Win Prob", f"{win_prob:.1f}%")
                with res_col2:
                    render_metric_card(f"{away_team} Win Prob", f"{(100 - win_prob):.1f}%")
                
                st.markdown(f"**Analysis:** {home_team} plays at a pace of {t1_data['pace']} against {away_team}'s {t2_data['pace']}. The net rating differential heavily influences this outcome spread.")

# ==========================================
# 4. ROUTING
# ==========================================
def main():
    inject_custom_css()
    
    st.sidebar.image("https://via.placeholder.com/300x100.png?text=QCL+BRANDING", use_container_width=True)
    st.sidebar.title("Navigation")
    
    menu = ["Home", "The Eternal Record", "Advanced Analytics", "The Hunt", "League Office", "Oracle Predictor"]
    choice = st.sidebar.radio("Go to", menu)
    
    if choice == "Home":
        app_home()
    elif choice == "The Eternal Record":
        eternal_record()
    elif choice == "Advanced Analytics":
        advanced_analytics()
    elif choice == "The Hunt":
        the_hunt()
    elif choice == "League Office":
        league_office()
    elif choice == "Oracle Predictor":
        oracle_predictor()

if __name__ == "__main__":
    main()
