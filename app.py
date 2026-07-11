"""
QCL LEAGUE HUB — Streamlit Analytics Dashboard
================================================
Qwik's Cup League (QCL) / NBA 2K Pro-Am analytics front end.

Data source : Google Sheet (CSV export) — Type='Total' rows are source of truth.
Run         : streamlit run qcl_hub.py

v3.0 CHANGELOG
--------------
* ORACLE REBUILT  : true Monte Carlo (vectorized, N sims) over a FIVE-MAN ROTATION
                    only. Rotation = top 5 by Games Played (PIE tiebreak), fully
                    overridable. Scratches scale team output. Outputs win prob,
                    spread, total, moneyline, margin distribution, MVP odds.
* LINEUP LAB      : build any 5-man unit, compare head-to-head vs another unit.
* PLAYER SPOTLIGHT: game logs, rolling form, W/L splits, opponent splits.
* INTERACTIVITY   : global filters, search, watchlist, sortable/exportable tables,
                    tunable award thresholds, CSV downloads on every table.
* FIXES           : real TS% (uses FTA), real eFG% (uses 3PM) — no more proxies.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import re

# =============================================================================
# 1. CONFIG
# =============================================================================
st.set_page_config(page_title="QCL LEAGUE CENTRAL", page_icon="🏀", layout="wide")

SHEET_ID = "1rksLYUcXQJ03uTacfIBD6SRsvtH-IE6djqT-LINwcH4"
URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"

GOLD, SILVER, BRONZE = "#d4af37", "#a0a0a0", "#cd7f32"
GREEN, RED, BLUE = "#00ff88", "#ff5555", "#00bfff"
ROTATION_SIZE = 5  # 2K Pro-Am: only five bodies on the floor

# =============================================================================
# 2. STYLE
# =============================================================================
st.markdown("""
<style>
    .stApp { background: radial-gradient(circle at top, #121212 0%, #000000 100%); color: #e0e0e0; font-family: 'Helvetica Neue', sans-serif; }
    .header-banner {
        padding: 20px; text-align: center;
        background: linear-gradient(90deg, #d4af37 0%, #f7e08a 50%, #d4af37 100%);
        color: #000; font-family: 'Arial Black'; font-size: 26px; border-radius: 5px;
        margin-bottom: 20px; text-transform: uppercase; letter-spacing: 2px;
    }
    .metric-box { background: #1e1e1e; border-left: 4px solid #d4af37; padding: 15px; border-radius: 4px; text-align: center; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }
    .metric-title { font-size: 12px; color: #888; text-transform: uppercase; letter-spacing: 1px; }
    .metric-value { font-size: 22px; font-weight: 900; color: #fff; margin-top: 5px; }
    .metric-sub { font-size: 11px; color: #666; margin-top: 3px; }

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

    .award-card { background: #161b22; border: 1px solid #d4af37; padding: 20px; border-radius: 8px; text-align: center; height: 100%; box-shadow: 0 5px 15px rgba(0,0,0,0.5); }

    .flip-card { background-color: transparent; width: 100%; perspective: 1000px; margin-bottom: 25px; }
    .flip-card-inner { position: relative; width: 100%; height: 100%; text-align: center; transition: transform 0.6s; transform-style: preserve-3d; }
    .flip-card:hover .flip-card-inner { transform: rotateY(180deg); }
    .flip-card-front, .flip-card-back { position: absolute; width: 100%; height: 100%; -webkit-backface-visibility: hidden; backface-visibility: hidden; border-radius: 12px; border: 3px solid #d4af37; box-shadow: 0 10px 30px rgba(0,0,0,0.5); }
    .flip-card-front { background: linear-gradient(145deg, #1c2128, #2a2d35); display: flex; flex-direction: column; justify-content: center; align-items: center; padding: 20px; }
    .flip-card-back { background-color: #161b22; color: white; transform: rotateY(180deg); padding: 15px; overflow-y: auto; text-align: left; }
    .stat-row { display: flex; justify-content: space-between; border-bottom: 1px dashed #333; padding: 6px 0; font-size: 13px; }
    .stat-val { font-weight: bold; color: #d4af37; }
    .stat-label { color: #8b949e; }
    .sim-box { background: #161b22; padding: 20px; border-radius: 10px; border: 2px solid #d4af37; text-align: center; box-shadow: 0 5px 15px rgba(0,0,0,0.5); margin-bottom: 20px; }

    .chip { display:inline-block; background:#d4af37; color:#000; font-size:11px; font-weight:bold; padding:4px 9px; border-radius:12px; margin:2px; }
    .line-box { background:#0d1117; border:1px solid #30363d; border-radius:8px; padding:14px; text-align:center; }
    .line-label { color:#8b949e; font-size:11px; text-transform:uppercase; letter-spacing:1px; }
    .line-value { color:#fff; font-size:20px; font-weight:900; margin-top:4px; }
</style>
""", unsafe_allow_html=True)


# =============================================================================
# 3. DATA ENGINE
# =============================================================================
def basic_name_clean(raw_name):
    """Remove pure OCR junk only: edge pipes/whitespace and [bracket]/(paren) tags.
    Never alters casing or strips letters from the gamertag itself."""
    if pd.isna(raw_name) or not isinstance(raw_name, str):
        return raw_name
    n = re.sub(r'^[|\s]+|[|\s]+$', '', raw_name)
    n = re.sub(r'^\[.*?\]\s*|^\(.*?\)\s*', '', n)
    return n.strip()


def name_match_key(name):
    """OCR-tolerant identity key: strips leading I/l/| prefix runs (2K clan-tag
    misreads), folds l<->i confusion, case-insensitive. Grouping only — display
    names are never modified by this."""
    k = re.sub(r'^[|Il\s]+', '', str(name))
    return k.strip().lower().replace('l', 'i').replace(' ', '')


@st.cache_data(ttl=60, show_spinner="Pulling the league sheet...")
def load_data():
    try:
        df = pd.read_csv(URL)
        df.columns = df.columns.str.strip()
        health = {}
        df = df[df['Player/Team'] != 'Player/Team']
        df = df[df['Team Name'].notna()
                & (df['Team Name'].astype(str).str.strip() != '')
                & (df['Team Name'].astype(str) != '0')]
        health['Rows loaded'] = len(df)

        # --- TYPE NORMALIZATION: Player/player/Xbox/blank -> Player; Team/Total/TOTAL -> Team ---
        raw_type = df['Type'].astype(str).str.strip().str.lower()
        total_name = df['Player/Team'].astype(str).str.strip().str.upper().isin(['TOTAL', 'TOTALS', 'TEAM TOTAL'])
        is_team_row = raw_type.isin(['team', 'total', 'team total', 'totals']) | total_name
        health['Players recovered (bad Type)'] = int((~is_team_row & (raw_type != 'player')).sum())
        df['Type'] = np.where(is_team_row, 'Team', 'Player')

        # --- CANONICAL NAMES: clean OCR junk, unify variants under most-used spelling ---
        df['Player/Team'] = df['Player/Team'].apply(basic_name_clean)
        p_names = df.loc[df['Type'] == 'Player', 'Player/Team'].dropna()
        counts = p_names.value_counts()
        canon = {}
        for name, cnt in counts.items():
            k = name_match_key(name)
            if k not in canon or cnt > canon[k][1]:
                canon[k] = (name, cnt)

        def to_canonical(n):
            if not isinstance(n, str):
                return n
            hit = canon.get(name_match_key(n))
            return hit[0] if hit else n

        df.loc[df['Type'] == 'Player', 'Player/Team'] = df.loc[df['Type'] == 'Player', 'Player/Team'].map(to_canonical)
        health['Name variants unified'] = int(sum(1 for n in counts.index if canon[name_match_key(n)][0] != n))

        req_cols = ['PTS', 'REB', 'AST', 'STL', 'BLK', 'FOULS', 'TO', 'FGA', 'FGM', '3PM', '3PA',
                    'FTA', 'FTM', 'OREB', 'DREB', 'MIN', 'Q1', 'Q2', 'Q3', 'Q4',
                    'Game_ID', 'Win', 'Season', 'Type', 'Team Name']
        for c in req_cols:
            if c not in df.columns:
                df[c] = 0
            if c not in ['Type', 'Team Name', 'Player/Team', 'Win']:
                df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)

        df['Win'] = pd.to_numeric(df['Win'], errors='coerce')   # keep NaN; derived from score later
        df['Game_ID'] = pd.to_numeric(df['Game_ID'], errors='coerce')

        # --- DROP rows with no game/season identity; build cross-season-safe game key ---
        pre = len(df)
        df = df[df['Game_ID'].notna() & (df['Season'] > 0)]
        health['Rows dropped (no Game_ID/Season)'] = pre - len(df)
        df['GKey'] = df['Season'].astype(int).astype(str) + '-' + df['Game_ID'].astype(int).astype(str)

        # --- DEDUPE double-entered rows (keep the fuller stat line) ---
        pre = len(df)
        df['_bulk'] = df['PTS'] + df['FGA'] + df['REB']
        df = (df.sort_values('_bulk')
                .drop_duplicates(subset=['Season', 'Game_ID', 'Team Name', 'Player/Team', 'Type'], keep='last')
                .drop(columns='_bulk')
                .sort_index())
        health['Duplicate rows removed'] = pre - len(df)

        df['PIE_Raw'] = (df['PTS'] + df['REB'] + df['AST'] + df['STL'] + df['BLK']) - (df['FGA'] * 0.5) - df['TO']
        df['Poss_Raw'] = df['FGA'] + 0.44 * df['FTA'] + df['TO']

        # --- HOLLINGER GAME SCORE (falls back to 0.42*REB when OREB/DREB not tracked) ---
        reb_term = np.where((df['OREB'] + df['DREB']) > 0,
                            0.7 * df['OREB'] + 0.3 * df['DREB'],
                            0.42 * df['REB'])
        df['Game_Score'] = (df['PTS'] + 0.4 * df['FGM'] - 0.7 * df['FGA'] - 0.4 * (df['FTA'] - df['FTM'])
                            + reb_term + df['STL'] + 0.7 * df['AST'] + 0.7 * df['BLK']
                            - 0.4 * df['FOULS'] - df['TO'])

        # --- TEAM TOTALS: recorded box-screen totals preferred; rebuilt from players as fallback ---
        key = ['Season', 'Game_ID', 'Team Name']
        players = df[df['Type'] == 'Player'].copy()
        recorded = df[df['Type'] == 'Team'].copy()
        recorded = recorded[recorded['PTS'] > 0].drop_duplicates(subset=key, keep='last')

        sum_cols = ['PTS', 'REB', 'AST', 'STL', 'BLK', 'FOULS', 'TO', 'FGA', 'FGM', '3PM', '3PA',
                    'FTA', 'FTM', 'OREB', 'DREB', 'Q1', 'Q2', 'Q3', 'Q4',
                    'Poss_Raw', 'PIE_Raw', 'Game_Score']
        rebuilt = players.groupby(key).agg({**{c: 'sum' for c in sum_cols},
                                            'Win': 'max', 'GKey': 'first'}).reset_index()
        rebuilt = rebuilt.merge(recorded[key].assign(_rec=1), on=key, how='left')
        rebuilt = rebuilt[rebuilt['_rec'].isna()].drop(columns=['_rec'])

        team_rows = pd.concat([recorded, rebuilt], ignore_index=True)
        team_rows['Type'] = 'Team'
        team_rows['Player/Team'] = team_rows['Team Name'].astype(str) + " TOTALS"
        health['Team totals (recorded / rebuilt)'] = f"{len(recorded)} / {len(rebuilt)}"

        # --- NEW-SCHEMA COVERAGE & CONSISTENCY ---
        q_sum = team_rows[['Q1', 'Q2', 'Q3', 'Q4']].sum(axis=1)
        has_q = q_sum > 0
        health['Quarter data coverage'] = f"{int(has_q.sum())}/{len(team_rows)} team-games"
        q_mismatch = int((has_q & (q_sum != team_rows['PTS'])).sum())
        if q_mismatch:
            health['⚠️ Quarters ≠ PTS'] = q_mismatch
        reb_split = df[df['Type'] == 'Player'][['OREB', 'DREB']].sum(axis=1) > 0
        health['OREB/DREB coverage'] = f"{int(reb_split.sum())}/{int((df['Type'] == 'Player').sum())} player rows"
        ft_cov = int((df.loc[df['Type'] == 'Player', 'FTA'] > 0).sum())
        health['FTA coverage'] = f"{ft_cov}/{int((df['Type'] == 'Player').sum())} player rows"

        # --- WIN RECONCILIATION: fill missing Win from head-to-head score ---
        n_teams = team_rows.groupby(['Season', 'Game_ID'])['Team Name'].transform('nunique')
        max_pts = team_rows.groupby(['Season', 'Game_ID'])['PTS'].transform('max')
        min_pts = team_rows.groupby(['Season', 'Game_ID'])['PTS'].transform('min')
        derived = pd.Series(np.where((n_teams == 2) & (max_pts != min_pts),
                                     (team_rows['PTS'] == max_pts).astype(float), np.nan),
                            index=team_rows.index)
        health['Wins derived from score'] = int((team_rows['Win'].isna() & derived.notna()).sum())
        team_rows['Win'] = team_rows['Win'].fillna(derived)

        win_map = team_rows.set_index(key)['Win']
        mapped = players.set_index(key).index.map(win_map)
        players['Win'] = players['Win'].fillna(pd.Series(mapped, index=players.index))
        df = pd.concat([players, team_rows], ignore_index=True)
        df['Win'] = pd.to_numeric(df['Win'], errors='coerce').fillna(0).apply(lambda x: 1 if x > 0 else 0)

        # --- ADVANCED RATINGS (PER GAME) ---
        p_mask = df['Type'].astype(str).str.lower() == 'player'
        team_poss = df[p_mask].groupby(['Season', 'Game_ID', 'Team Name'])['Poss_Raw'].transform('sum')
        df.loc[p_mask, 'USG_Game'] = np.where(team_poss > 0, df.loc[p_mask, 'Poss_Raw'] / team_poss * 100, 0)
        df['ORtg_Game'] = np.where(df['Poss_Raw'] > 0, df['PTS'] / df['Poss_Raw'] * 100, 0)

        # --- PROXY STATS (2K box screen doesn't expose these; derived from role) ---
        df['Game_Type'] = np.where(df['Game_ID'] >= 9000, 'Playoffs',
                                   np.where(df['Game_ID'] >= 8000, 'Tournament', 'Regular Season'))
        players_df = df[df['Type'].astype(str).str.lower() == 'player'].copy()
        players_df = players_df.sort_values(by=['Season', 'Game_ID', 'Team Name'])
        players_df['Position_Num'] = players_df.groupby(['Season', 'Game_ID', 'Team Name']).cumcount() + 1

        players_df['Tipped_Passes'] = np.where(players_df['Position_Num'] <= 2,
                                               (players_df['STL'] * 2.2) + (players_df['FOULS'] * 0.4),
                                               (players_df['STL'] * 1.2) + (players_df['BLK'] * 0.2)
                                               ).round().astype(int)
        players_df['Shots_Affected'] = np.where(players_df['Position_Num'] >= 3,
                                                (players_df['BLK'] * 3.0) + (players_df['REB'] * 0.4) + (players_df['FOULS'] * 0.5),
                                                (players_df['BLK'] * 1.5) + (players_df['STL'] * 0.4)
                                                ).round().astype(int)
        players_df['FB_Points'] = np.where(players_df['Position_Num'] <= 2,
                                           (players_df['STL'] * 2.0) + (players_df['FGM'] * 0.4),
                                           (players_df['STL'] * 1.0) + (players_df['FGM'] * 0.1)
                                           ).round().astype(int)
        players_df['FB_Points'] = players_df[['FB_Points', 'PTS']].min(axis=1)

        df = df.merge(players_df[['Season', 'Game_ID', 'Team Name', 'Player/Team',
                                  'Tipped_Passes', 'Shots_Affected', 'FB_Points', 'Position_Num']],
                      on=['Season', 'Game_ID', 'Team Name', 'Player/Team'], how='left')

        t_proxy = (df[df['Type'] == 'Player']
                   .groupby(['Season', 'Game_ID', 'Team Name'])[['Tipped_Passes', 'Shots_Affected', 'FB_Points']]
                   .sum().reset_index())
        for col in ['Tipped_Passes', 'Shots_Affected', 'FB_Points']:
            df.loc[df['Type'] == 'Team', col] = (df.loc[df['Type'] == 'Team']
                                                 .set_index(['Season', 'Game_ID', 'Team Name']).index
                                                 .map(t_proxy.set_index(['Season', 'Game_ID', 'Team Name'])[col])
                                                 ).fillna(0)

        # --- MATCHUP LOGIC & SOS ---
        t_logs = df[df['Type'] == 'Team'][['Game_ID', 'Team Name', 'PTS', 'FGM', 'FGA', '3PM', '3PA',
                                           'TO', 'FTA', 'Win', 'Season']].copy()
        t_logs['Team_Win_Pct'] = t_logs.groupby(['Season', 'Team Name'])['Win'].transform('mean')

        # SEASON-AWARE PAIRING: only true head-to-head games (exactly 2 teams share Season+Game_ID)
        n_in_game = t_logs.groupby(['Season', 'Game_ID'])['Team Name'].transform('nunique')
        pairable = t_logs[n_in_game == 2]
        opps = pd.merge(pairable, pairable, on=['Season', 'Game_ID'], suffixes=('', '_Opp'))
        opps = opps[opps['Team Name'] != opps['Team Name_Opp']]
        opps = opps.drop_duplicates(subset=['Season', 'Game_ID', 'Team Name'])

        opps['Point_Diff'] = opps['PTS'] - opps['PTS_Opp']
        opps['Opp_Possessions'] = opps['FGA_Opp'] + (0.44 * opps['FTA_Opp']) + opps['TO_Opp']
        opps['Opp_PPP'] = np.where(opps['Opp_Possessions'] > 0, opps['PTS_Opp'] / opps['Opp_Possessions'], 0)
        opps['Opp_FG%'] = np.where(opps['FGA_Opp'] > 0, (opps['FGM_Opp'] / opps['FGA_Opp']) * 100, 0)

        df = pd.merge(df, opps[['Season', 'Game_ID', 'Team Name', 'Point_Diff', 'Opp_PPP', 'Opp_FG%',
                                'Team Name_Opp', 'Team_Win_Pct_Opp', 'PTS_Opp']],
                      on=['Season', 'Game_ID', 'Team Name'], how='left')

        for src, dst in [('Point_Diff', 'Point_Diff'), ('Opp_PPP', 'Opp_PPP'),
                         ('Team_Win_Pct_Opp', 'SOS_Game'), ('Team Name_Opp', 'Opp_Name'),
                         ('PTS_Opp', 'Opp_PTS')]:
            df[dst] = df.groupby(['Season', 'Game_ID', 'Team Name'])[src].transform('first')

        return {'df': df, 'health': health}
    except Exception as e:
        return str(e)


_loaded = load_data()
if isinstance(_loaded, str):
    st.error(f"⚠️ DATA ERROR: {_loaded}")
    st.stop()

full_df = _loaded['df']
DATA_HEALTH = _loaded['health']

if full_df is None or full_df.empty:
    st.warning("Sheet loaded but contains no usable rows.")
    st.stop()


# =============================================================================
# 4. GLOBAL MILESTONE / CLUB TRACKER
# =============================================================================
@st.cache_data(ttl=60)
def build_clubs(df):
    gp = df[df['Type'].astype(str).str.lower() == 'player'].copy()
    season_totals = gp.groupby(['Player/Team', 'Season']).sum(numeric_only=True).reset_index()

    def calc_clubs(row):
        clubs = []
        if row['REB'] >= 40 and row['STL'] >= 40 and row['AST'] >= 40:
            clubs.append("40/40/40 Club")
        elif row['REB'] >= 30 and row['STL'] >= 30 and row['AST'] >= 30:
            clubs.append("30/30/30 Club")
        if row['PTS'] >= 300 and row['3PM'] >= 100:
            clubs.append("300 Pts / 100 3s")
        if row['PTS'] >= 100 and row['REB'] >= 100:
            clubs.append("100 Pts / 100 Reb")
        return clubs

    season_totals['Clubs'] = season_totals.apply(calc_clubs, axis=1)
    pc = season_totals.groupby('Player/Team')['Clubs'].agg(
        lambda x: [i for sub in x for i in sub if i]).reset_index()
    pc['Clubs'] = pc['Clubs'].apply(lambda x: sorted(set(x)))
    return pc


player_clubs = build_clubs(full_df)


# =============================================================================
# 5. RENDER HELPERS
# =============================================================================
def dl(df, label, fname, key):
    """Download button for any table."""
    st.download_button(label, df.to_csv(index=False).encode('utf-8'),
                       file_name=fname, mime='text/csv', key=key, use_container_width=True)


def norm(val, mx):
    return min(100, (max(0, val) / mx) * 100) if mx > 0 else 0


def draw_shot_profile(fgm, fga, tpm, tpa):
    twopm, twopa = fgm - tpm, fga - tpa
    three_pct = (tpm / tpa * 100) if tpa > 0 else 0
    two_pct = (twopm / twopa * 100) if twopa > 0 else 0
    return f"""
    <div style="display:flex; justify-content:space-between; margin-bottom:2px; font-size:11px; color:#aaa;"><span>Interior (2PT)</span><span>{two_pct:.1f}% ({int(twopm)}/{int(twopa)})</span></div>
    <div class="shot-bar-container"><div class="shot-bar-fill" style="width:{two_pct}%; background:#d4af37;"></div></div>
    <div style="display:flex; justify-content:space-between; margin-top:10px; margin-bottom:2px; font-size:11px; color:#aaa;"><span>Perimeter (3PT)</span><span>{three_pct:.1f}% ({int(tpm)}/{int(tpa)})</span></div>
    <div class="shot-bar-container"><div class="shot-bar-fill" style="width:{three_pct}%; background:#00bfff;"></div></div>
    """


def generate_sleek_box_score(df_game):
    df_game = df_game.sort_values(by='PTS', ascending=False)
    html = ("<table class='sleek-table'><tr><th>Player</th><th>PTS</th><th>REB</th><th>AST</th>"
            "<th>STL</th><th>BLK</th><th>FG</th><th>3PT</th><th>PIE</th></tr>")
    for _, r in df_game.iterrows():
        html += (f"<tr><td class='player-name'>{r['Player/Team']}</td><td>{int(r['PTS'])}</td>"
                 f"<td>{int(r['REB'])}</td><td>{int(r['AST'])}</td><td>{int(r['STL'])}</td>"
                 f"<td>{int(r['BLK'])}</td><td>{int(r['FGM'])}/{int(r['FGA'])}</td>"
                 f"<td>{int(r['3PM'])}/{int(r['3PA'])}</td><td>{r['PIE_Raw']:.1f}</td></tr>")
    return html + "</table>"


def render_podium(title, top3_df, stat_col):
    if len(top3_df) < 3:
        return ""
    p1, p2, p3 = top3_df.iloc[0], top3_df.iloc[1], top3_df.iloc[2]
    html = f"<div style='text-align:center; margin-bottom:10px;'><h3 style='color:#fff; text-transform:uppercase;'>{title}</h3></div>"
    html += "<div class='podium-container'>"
    html += f"<div class='podium podium-3'><div class='podium-name'>{p3['Player/Team']}</div><div class='podium-stat'>{p3[stat_col]:.0f}</div></div>"
    html += f"<div class='podium podium-1'><div class='podium-name'>{p1['Player/Team']}</div><div class='podium-stat'>{p1[stat_col]:.0f}</div></div>"
    html += f"<div class='podium podium-2'><div class='podium-name'>{p2['Player/Team']}</div><div class='podium-stat'>{p2[stat_col]:.0f}</div></div>"
    return html + "</div>"


def generate_2k_player_card(player_name, stats, rank=""):
    rank_badge = (f'<div style="position:absolute; top:-10px; right:-10px; background:#d4af37; color:#000; '
                  f'font-weight:bold; padding:8px; border-radius:50%; border:2px solid #fff; z-index:10;">#{rank}</div>'
                  if rank else "")
    clubs_html = ""
    if isinstance(stats.get('Clubs'), list) and stats['Clubs']:
        badges = "".join([f"<span class='chip'>{c}</span>" for c in stats['Clubs']])
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
<div class="stat-row"><span class="stat-label">PPG | RPG | APG</span> <span class="stat-val">{stats.get('PTS', 0):.1f} | {stats.get('REB', 0):.1f} | {stats.get('AST', 0):.1f}</span></div>
<div class="stat-row"><span class="stat-label">SEASON HIGHS</span> <span class="stat-val" style="color:#fff;">{int(stats.get('High_PTS', 0))}P | {int(stats.get('High_REB', 0))}R | {int(stats.get('High_AST', 0))}A</span></div>
<div class="stat-row"><span class="stat-label">CAREER HIGHS</span> <span class="stat-val" style="color:#d4af37;">{int(stats.get('AT_High_PTS', 0))}P | {int(stats.get('AT_High_REB', 0))}R | {int(stats.get('AT_High_AST', 0))}A</span></div>
<div class="stat-row"><span class="stat-label">DEF HIGHS (SZN)</span> <span class="stat-val">{int(stats.get('High_STL', 0))}S | {int(stats.get('High_BLK', 0))}B</span></div>
<div class="stat-row"><span class="stat-label">FG% | 3P% | TS%</span> <span class="stat-val">{stats.get('FG%', 0):.1f}% | {stats.get('3P%', 0):.1f}% | {stats.get('TS%', 0):.1f}%</span></div>
<div class="stat-row"><span class="stat-label">USG | NetRtg</span> <span class="stat-val">{stats.get('USG', 0):.1f}% | {stats.get('NetRtg', 0):+.1f}</span></div>
</div>
</div>
</div>'''


def generate_mini_leaderboard(title, df, stat_col, color=GOLD, top_n=5, name_col=None):
    html = (f"<div style='background:#1c2128; padding:15px; border-radius:8px; border-left:4px solid {color}; "
            f"margin-bottom:15px; box-shadow: 0 4px 6px rgba(0,0,0,0.3);'>")
    html += (f"<h3 style='margin-top:0; color:#fff; font-size:16px; border-bottom:1px dashed #444; "
             f"padding-bottom:8px; text-transform:uppercase;'>{title}</h3>")
    sorted_df = df.sort_values(by=stat_col, ascending=False).head(top_n)
    for i, (_, row) in enumerate(sorted_df.iterrows()):
        val = row[stat_col]
        if pd.isna(val):
            continue
        val_str = f"{int(val)}" if float(val) == int(val) else f"{val:.1f}"
        rank_color = "#ffd700" if i == 0 else "#888"
        name = row.get(name_col, 'Unknown') if name_col else row.get('Player/Team')
        if pd.isna(name) or str(name).strip() == '0':
            name = row.get('Team Name', 'Unknown')
        html += ("<div style='display:flex; justify-content:space-between; align-items:center; margin-bottom:6px; font-size:14px;'>"
                 f"<div><span style='color:{rank_color}; font-weight:bold; margin-right:8px;'>{i+1}.</span>"
                 f"<span style='color:#ddd; font-weight:bold;'>{name}</span></div>"
                 f"<span style='color:{color}; font-weight:bold;'>{val_str}</span></div>")
    return html + "</div>"


def draw_dynamic_radar(p1_name, r1_vals, p2_name, r2_vals, categories, title):
    r1_vals = list(r1_vals) + [r1_vals[0]]
    r2_vals = list(r2_vals) + [r2_vals[0]]
    cats = list(categories) + [categories[0]]
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(r=r1_vals, theta=cats, fill='toself', name=p1_name,
                                  fillcolor='rgba(212, 175, 55, 0.4)', line=dict(color=GOLD, width=2)))
    fig.add_trace(go.Scatterpolar(r=r2_vals, theta=cats, fill='toself', name=p2_name,
                                  fillcolor='rgba(204, 0, 0, 0.4)', line=dict(color='#cc0000', width=2)))
    fig.update_layout(title=dict(text=title, font=dict(color='white', size=16)),
                      polar=dict(radialaxis=dict(visible=True, range=[0, 100], showticklabels=False, gridcolor='#444')),
                      showlegend=True, template="plotly_dark", height=380,
                      paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                      margin=dict(l=40, r=40, t=60, b=40))
    return fig


def american_odds(p):
    p = min(max(p, 0.01), 0.99)
    return f"-{int(round(100 * p / (1 - p)))}" if p >= 0.5 else f"+{int(round(100 * (1 - p) / p))}"


# =============================================================================
# 6. SESSION STATE
# =============================================================================
if 'watchlist' not in st.session_state:
    st.session_state.watchlist = []


def toggle_watch(name):
    if name in st.session_state.watchlist:
        st.session_state.watchlist.remove(name)
    else:
        st.session_state.watchlist.append(name)


# =============================================================================
# 7. SIDEBAR / NAV
# =============================================================================
seasons = sorted([int(s) for s in full_df['Season'].dropna().unique() if int(s) > 0], reverse=True)

st.sidebar.title("⚙️ Hub Controls")
VIEWS = [
    "🏠 League Home & Awards",
    "🏆 Power Rankings & SOS",
    "🏢 Franchise Hub",
    "🔦 Player Spotlight",
    "🗃️ Full Player Database",
    "⚔️ Head-to-Head Radar",
    "🧪 Lineup Lab",
    "🥊 Rivalry Corner",
    "🔮 Oracle Predictor",
    "🔬 Advanced Analytics Lab",
    "🏦 The Vault",
    "📖 Record Book & Milestones",
]
view_mode = st.sidebar.radio("Navigation", VIEWS)
st.sidebar.divider()

scope_opts = [f"Season {s}" for s in seasons] + ["Career Stats"]
selected_scope = st.sidebar.selectbox("Data Scope", scope_opts, index=0)

game_type_opts = ["All Games", "Regular Season", "Playoffs", "Tournament"]
game_type = st.sidebar.selectbox("Game Type", game_type_opts, index=0)

min_gp_filter = st.sidebar.slider("Min Games Played (tables)", 0, 20, 1)

if st.sidebar.button("🔄 Refresh Sheet", use_container_width=True):
    st.cache_data.clear()
    st.rerun()

if DATA_HEALTH:
    with st.sidebar.expander("🩺 Data Health"):
        for hk, hv in DATA_HEALTH.items():
            st.markdown(f"**{hk}:** {hv}")

if st.session_state.watchlist:
    with st.sidebar.expander(f"⭐ Watchlist ({len(st.session_state.watchlist)})", expanded=True):
        for w in list(st.session_state.watchlist):
            wc1, wc2 = st.columns([3, 1])
            wc1.markdown(f"**{w}**")
            if wc2.button("✕", key=f"unwatch_{w}"):
                toggle_watch(w)
                st.rerun()

target_season = seasons[0] if selected_scope == "Career Stats" else int(selected_scope.replace("Season ", ""))
df_active = full_df if selected_scope == "Career Stats" else full_df[full_df['Season'] == target_season]
if game_type != "All Games":
    df_active = df_active[df_active['Game_Type'] == game_type]

banner_text = "CAREER TOTALS" if selected_scope == "Career Stats" else f"SEASON {target_season}"
if game_type != "All Games":
    banner_text += f" • {game_type.upper()}"

st.markdown(f'<div class="header-banner">🏀 QCL LEAGUE HUB — {banner_text}</div>', unsafe_allow_html=True)

if df_active.empty:
    st.warning("No games match the current scope / game-type filter.")
    st.stop()


# =============================================================================
# 8. CORE STAT ENGINE
# =============================================================================
p_df = df_active[df_active['Type'].astype(str).str.lower() == 'player'].copy()
t_df = df_active[df_active['Type'].astype(str).str.lower() == 'team'].copy()
full_p_df = full_df[full_df['Type'].astype(str).str.lower() == 'player'].copy()

p_all_time_highs = full_p_df.groupby('Player/Team').agg(
    AT_High_PTS=('PTS', 'max'), AT_High_REB=('REB', 'max'), AT_High_AST=('AST', 'max')
).reset_index()

p_stats = p_df.groupby('Player/Team').agg(**{
    'GP': ('GKey', 'nunique'),
    'PTS': ('PTS', 'mean'), 'REB': ('REB', 'mean'), 'AST': ('AST', 'mean'),
    'STL': ('STL', 'mean'), 'BLK': ('BLK', 'mean'), 'TO': ('TO', 'mean'),
    'FGM': ('FGM', 'mean'), 'FGA': ('FGA', 'mean'),
    '3PM': ('3PM', 'mean'), '3PA': ('3PA', 'mean'),
    'FTM': ('FTM', 'mean'), 'FTA': ('FTA', 'mean'),
    'PIE_Raw': ('PIE_Raw', 'mean'), 'POS': ('Position_Num', 'mean'),
    'Team': ('Team Name', 'last'),
    'Tipped_Passes': ('Tipped_Passes', 'mean'), 'Shots_Affected': ('Shots_Affected', 'mean'),
    'FB_Points': ('FB_Points', 'mean'),
    'USG': ('USG_Game', 'mean'), 'ORtg': ('ORtg_Game', 'mean'), 'GmSc': ('Game_Score', 'mean'),
    'Wins': ('Win', 'sum'),
}).reset_index()

p_stats.rename(columns={'PIE_Raw': 'PIE'}, inplace=True)
p_stats['DEF'] = p_stats['STL'] + p_stats['BLK']
p_stats['Win%'] = (p_stats['Wins'] / p_stats['GP'].replace(0, 1)).round(3)

# REAL TS% — uses actual FTA (no more 0.2*FGA proxy)
ts_den = 2 * (p_stats['FGA'] + 0.44 * p_stats['FTA'])
p_stats['TS%'] = np.where(ts_den > 0, p_stats['PTS'] / ts_den * 100, 0)
# REAL eFG%
p_stats['eFG%'] = np.where(p_stats['FGA'] > 0,
                           (p_stats['FGM'] + 0.5 * p_stats['3PM']) / p_stats['FGA'] * 100, 0)

p_stats = p_stats.merge(player_clubs, on='Player/Team', how='left')
p_stats['Clubs'] = p_stats['Clubs'].apply(lambda x: x if isinstance(x, list) else [])

p_highs = p_df.groupby('Player/Team').agg(
    High_PTS=('PTS', 'max'), High_REB=('REB', 'max'), High_AST=('AST', 'max'),
    High_STL=('STL', 'max'), High_BLK=('BLK', 'max'), High_3PM=('3PM', 'max')
).reset_index()
p_stats = p_stats.merge(p_highs, on='Player/Team', how='left')
p_stats = p_stats.merge(p_all_time_highs, on='Player/Team', how='left')

p_stats['FG%'] = (p_stats['FGM'] / p_stats['FGA'].replace(0, 1) * 100)
p_stats['3P%'] = (p_stats['3PM'] / p_stats['3PA'].replace(0, 1) * 100)

for col in ['PTS', 'REB', 'AST', 'STL', 'BLK', 'TO', '3PM', '3PA', 'FGM', 'FGA', 'FTM', 'FTA',
            'FB_Points', 'Tipped_Passes', 'Shots_Affected', 'PIE', 'TS%', 'eFG%',
            'FG%', '3P%', 'USG', 'ORtg', 'GmSc', 'DEF']:
    if col in p_stats.columns:
        p_stats[col] = p_stats[col].round(1)

p_stats = p_stats.sort_values('PIE', ascending=False).reset_index(drop=True)
p_stats['League_Rank'] = p_stats.index + 1

# --- TEAM STATS ---
t_stats = t_df.groupby('Team Name').agg(
    GP=('GKey', 'nunique'), Wins=('Win', 'sum'), PPG=('PTS', 'mean'),
    PTS_SD=('PTS', 'std'), OppPPG=('Opp_PTS', 'mean'),
    Diff=('Point_Diff', 'mean'), Opp_PPP=('Opp_PPP', 'mean'), SOS=('SOS_Game', 'mean'),
    Poss=('Poss_Raw', 'mean'), RPG=('REB', 'mean'), APG=('AST', 'mean'),
    SPG=('STL', 'mean'), BPG=('BLK', 'mean'), TOPG=('TO', 'mean'),
    FGM=('FGM', 'mean'), FGA=('FGA', 'mean'), TPM=('3PM', 'mean'),
).reset_index()
t_stats['Win%'] = (t_stats['Wins'] / t_stats['GP'].replace(0, 1)).round(3)
t_stats['DEF'] = t_stats['SPG'] + t_stats['BPG']
t_stats['eFG%'] = np.where(t_stats['FGA'] > 0,
                           (t_stats['FGM'] + 0.5 * t_stats['TPM']) / t_stats['FGA'] * 100, 0)
t_stats['ORtg'] = np.where(t_stats['Poss'] > 0, t_stats['PPG'] / t_stats['Poss'] * 100, 0).round(1)
t_stats['DRtg'] = (t_stats['Opp_PPP'] * 100).round(1)
t_stats['NetRtg'] = (t_stats['ORtg'] - t_stats['DRtg']).round(1)
t_stats['Pace'] = t_stats['Poss'].round(1)
t_stats['PTS_SD'] = t_stats['PTS_SD'].fillna(7.0).clip(lower=3.5, upper=14.0)

# --- PLAYER DRtg / NetRtg ---
if not t_stats.empty:
    p_stats = p_stats.merge(
        t_stats[['Team Name', 'DRtg']].rename(columns={'Team Name': 'Team', 'DRtg': 'Team_DRtg'}),
        on='Team', how='left')
    lg_def = p_stats['DEF'].mean()
    p_stats['DRtg'] = (p_stats['Team_DRtg'].fillna(t_stats['DRtg'].mean())
                       - (p_stats['DEF'] - lg_def) * 2.0).round(1)
else:
    p_stats['DRtg'] = 0.0
p_stats['NetRtg'] = (p_stats['ORtg'] - p_stats['DRtg']).round(1)

# Filtered view used by the browsable tables
p_view = p_stats[p_stats['GP'] >= min_gp_filter].copy()


# =============================================================================
# 9. ROTATION + MONTE CARLO ENGINE  (⭐ THE FIX)
# =============================================================================
def get_rotation(team_name, size=ROTATION_SIZE, exclude=None, pool=None):
    """Only five bodies play in Pro-Am. Rotation = most-used players by GAMES PLAYED,
    PIE as the tiebreak. Anyone in `exclude` is scratched."""
    src = p_stats if pool is None else pool
    roster = src[src['Team'] == team_name].copy()
    if exclude:
        roster = roster[~roster['Player/Team'].isin(exclude)]
    roster = roster.sort_values(['GP', 'PIE', 'PTS'], ascending=[False, False, False])
    return roster.head(size).reset_index(drop=True)


def full_roster(team_name):
    r = p_stats[p_stats['Team'] == team_name].copy()
    return r.sort_values(['GP', 'PIE'], ascending=[False, False])


def run_monte_carlo(t1, t2, rot1, rot2, n_sims=2000, hca=1.5, star_conc=6.0,
                    variance=1.0, seed=None):
    """
    Vectorized Monte Carlo over the two FIVE-MAN rotations.

    Team score model:
        expected = PPG  x  opponent-defense factor  x  SOS adjustment
                        x  rotation-availability factor  ( +/- HCA )
    Rotation availability factor = (sum of PPG of the five who are actually
    playing) / (sum of PPG of the team's default five). Scratch a star, the
    projected score drops accordingly.

    Player distribution: Dirichlet over the five rotation players' scoring shares.
    `star_conc` controls how tightly the ball sticks to the usage hierarchy
    (low = chaotic, high = the star always gets his).
    """
    rng = np.random.default_rng(seed)

    d1 = t_stats[t_stats['Team Name'] == t1].iloc[0]
    d2 = t_stats[t_stats['Team Name'] == t2].iloc[0]

    lg_opp_ppp = t_stats['Opp_PPP'].mean()
    lg_opp_ppp = lg_opp_ppp if lg_opp_ppp and lg_opp_ppp > 0 else 1.0

    # Opponent defense factor: facing a good D suppresses you.
    def1 = float(d2['Opp_PPP'] / lg_opp_ppp) if d2['Opp_PPP'] > 0 else 1.0   # D that T1 faces
    def2 = float(d1['Opp_PPP'] / lg_opp_ppp) if d1['Opp_PPP'] > 0 else 1.0   # D that T2 faces

    # Availability factor from the actual five on the floor
    def avail(team, rot):
        base = get_rotation(team)  # default healthy five
        base_sum = float(base['PTS'].sum())
        rot_sum = float(rot['PTS'].sum())
        if base_sum <= 0:
            return 1.0
        return float(np.clip(rot_sum / base_sum, 0.55, 1.30))

    av1, av2 = avail(t1, rot1), avail(t2, rot2)

    sos1 = float(d1['SOS']) if pd.notna(d1['SOS']) else 0.5
    sos2 = float(d2['SOS']) if pd.notna(d2['SOS']) else 0.5

    exp1 = float(d1['PPG']) * def1 * (1 + (sos1 - 0.5) * 0.5) * av1 + hca
    exp2 = float(d2['PPG']) * def2 * (1 + (sos2 - 0.5) * 0.5) * av2

    sd1 = float(d1['PTS_SD']) * variance
    sd2 = float(d2['PTS_SD']) * variance

    # ---- team scores ----
    s1 = np.rint(rng.normal(exp1, sd1, n_sims)).astype(int)
    s2 = np.rint(rng.normal(exp2, sd2, n_sims)).astype(int)
    floor = 25
    s1 = np.clip(s1, floor, None)
    s2 = np.clip(s2, floor, None)

    # ---- overtime: break ties with a coin-flip bucket ----
    tie = s1 == s2
    if tie.any():
        flip = rng.random(tie.sum()) < 0.5
        bump = rng.integers(2, 7, tie.sum())
        s1[tie] = s1[tie] + np.where(flip, bump, 0)
        s2[tie] = s2[tie] + np.where(flip, 0, bump)

    w1 = (s1 > s2)

    # ---- player scoring distribution over the five ----
    def player_pts(rot, scores):
        base = rot['PTS'].to_numpy(dtype=float)
        if base.sum() <= 0:
            base = np.ones(len(rot))
        alpha = np.clip(base / base.sum(), 0.02, None) * star_conc * len(rot)
        shares = rng.dirichlet(alpha, size=n_sims)           # (n_sims, 5)
        return shares * scores[:, None]

    pp1 = player_pts(rot1, s1)
    pp2 = player_pts(rot2, s2)

    # ---- MVP: scoring + baseline impact + winner bonus ----
    def impact(rot):
        return (1.1 * rot['REB'].to_numpy(dtype=float)
                + 1.4 * rot['AST'].to_numpy(dtype=float)
                + 2.0 * rot['STL'].to_numpy(dtype=float)
                + 2.0 * rot['BLK'].to_numpy(dtype=float))

    m1 = pp1 + impact(rot1)[None, :] + np.where(w1, 4.0, 0.0)[:, None]
    m2 = pp2 + impact(rot2)[None, :] + np.where(~w1, 4.0, 0.0)[:, None]
    mvp_matrix = np.hstack([m1, m2])
    names = list(rot1['Player/Team']) + list(rot2['Player/Team'])
    teams = [t1] * len(rot1) + [t2] * len(rot2)
    mvp_idx = mvp_matrix.argmax(axis=1)
    mvp_counts = np.bincount(mvp_idx, minlength=len(names))

    return {
        'n': n_sims,
        's1': s1, 's2': s2,
        'exp1': exp1, 'exp2': exp2,
        'win1': float(w1.mean()), 'win2': float(1 - w1.mean()),
        'margin': s1 - s2,
        'pp1': pp1, 'pp2': pp2,
        'mvp': pd.DataFrame({'Player': names, 'Team': teams,
                             'MVP %': (mvp_counts / n_sims * 100).round(1)}
                            ).sort_values('MVP %', ascending=False).reset_index(drop=True),
        'avail': (av1, av2),
    }


def projected_box(rot, pp):
    """Median simulated points per player + season-average support stats."""
    med = np.median(pp, axis=0).round(0).astype(int)
    p20 = np.percentile(pp, 20, axis=0).round(0).astype(int)
    p80 = np.percentile(pp, 80, axis=0).round(0).astype(int)
    return pd.DataFrame({
        'Player': rot['Player/Team'],
        'GP': rot['GP'].astype(int),
        'PROJ PTS': med,
        'Range': [f"{a}–{b}" for a, b in zip(p20, p80)],
        'REB': rot['REB'].round(1),
        'AST': rot['AST'].round(1),
        'STL': rot['STL'].round(1),
        'BLK': rot['BLK'].round(1),
        'USG%': rot['USG'].round(1),
    })


# =============================================================================
# 10. VIEWS
# =============================================================================

# ------------------------------------------------------------------ HOME -----
if view_mode == "🏠 League Home & Awards":
    hc1, hc2, hc3, hc4 = st.columns(4)
    hc1.markdown(f"<div class='metric-box'><div class='metric-title'>Games Logged</div><div class='metric-value'>{df_active['GKey'].nunique()}</div></div>", unsafe_allow_html=True)
    hc2.markdown(f"<div class='metric-box'><div class='metric-title'>Active Players</div><div class='metric-value'>{p_stats['Player/Team'].nunique()}</div></div>", unsafe_allow_html=True)
    hc3.markdown(f"<div class='metric-box'><div class='metric-title'>Teams</div><div class='metric-value'>{t_stats['Team Name'].nunique()}</div></div>", unsafe_allow_html=True)
    hc4.markdown(f"<div class='metric-box'><div class='metric-title'>League PPG</div><div class='metric-value'>{t_stats['PPG'].mean():.1f}</div></div>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    qual_pct = st.slider("Award eligibility — % of league-leading GP required", 30, 90, 60, 5) / 100
    qual_p = p_stats[p_stats['GP'] >= (p_stats['GP'].max() * qual_pct)]
    st.caption(f"{len(qual_p)} of {len(p_stats)} players qualify "
               f"({int(np.ceil(p_stats['GP'].max() * qual_pct))}+ games).")

    def render_award_row(title, sorted_df, stat_col, label=None):
        st.markdown(f"#### {title}")
        if sorted_df.empty:
            st.info("Not enough qualifying players yet.")
            return
        label = label or stat_col
        cols = st.columns(3)
        for i, (_, r) in enumerate(sorted_df.head(3).iterrows()):
            medal = "🥇" if i == 0 else "🥈" if i == 1 else "🥉"
            with cols[i]:
                st.markdown(
                    f"<div class='award-card'><h3>{medal} {r['Player/Team']}</h3>"
                    f"<p style='color:#aaa;'>{r['Team']}</p>"
                    f"<h2 style='color:#d4af37;'>{r[stat_col]:.1f} {label}</h2>"
                    f"<p>{r['PTS']:.1f} PTS | {r['REB']:.1f} REB | {r['AST']:.1f} AST</p></div>",
                    unsafe_allow_html=True)
                if st.button(("★ Watching" if r['Player/Team'] in st.session_state.watchlist else "☆ Watch"),
                             key=f"w_{title}_{i}", use_container_width=True):
                    toggle_watch(r['Player/Team'])
                    st.rerun()

    a_tabs = st.tabs(["MVP", "DPOY", "Big Man", "6th Man", "Most Improved", "All-League"])

    with a_tabs[0]:
        render_award_row("Most Valuable Player", qual_p.sort_values('PIE', ascending=False), 'PIE')
    with a_tabs[1]:
        render_award_row("Defensive Player of the Year", qual_p.sort_values('DEF', ascending=False), 'DEF', 'STOCKS')
    with a_tabs[2]:
        render_award_row("Big Man of the Year", qual_p[qual_p['POS'] >= 3].sort_values('PIE', ascending=False), 'PIE')
    with a_tabs[3]:
        rot_names = pd.concat([get_rotation(t) for t in t_stats['Team Name']])['Player/Team'] \
            if not t_stats.empty else pd.Series(dtype=str)
        bench_pool = qual_p[~qual_p['Player/Team'].isin(rot_names)]
        st.caption("6th Man = best qualifier who is NOT in his team's top-5 rotation (by GP).")
        render_award_row("6th Man of the Year", bench_pool.sort_values('PIE', ascending=False), 'PIE')
    with a_tabs[4]:
        st.markdown("#### 🚀 Most Improved Player")
        prev_seasons = [s for s in seasons if s < target_season]
        if selected_scope == "Career Stats":
            st.info("Switch to a single-season scope to view the MIP race.")
        elif not prev_seasons:
            st.info("MIP requires a previous season for comparison.")
        else:
            prev_s = max(prev_seasons)

            def season_line(s):
                d = full_p_df[full_p_df['Season'] == s]
                return d.groupby('Player/Team').agg(GP=('GKey', 'nunique'),
                                                    PIE=('PIE_Raw', 'mean'),
                                                    PTS=('PTS', 'mean')).reset_index()

            mip = season_line(target_season).merge(season_line(prev_s), on='Player/Team',
                                                   suffixes=('', '_Prev'))
            mip = mip[(mip['GP'] >= 3) & (mip['GP_Prev'] >= 3)]
            mip['Jump'] = mip['PIE'] - mip['PIE_Prev']
            mip = mip.sort_values('Jump', ascending=False)
            if mip.empty:
                st.info("No players with 3+ games in both seasons yet.")
            else:
                mc = st.columns(3)
                for i, (_, r) in enumerate(mip.head(3).iterrows()):
                    medal = "🥇" if i == 0 else "🥈" if i == 1 else "🥉"
                    jc = GREEN if r['Jump'] >= 0 else RED
                    with mc[i]:
                        st.markdown(
                            f"<div class='award-card'><h3>{medal} {r['Player/Team']}</h3>"
                            f"<p style='color:#aaa;'>S{prev_s} → S{target_season}</p>"
                            f"<h2 style='color:{jc};'>{r['Jump']:+.1f} PIE</h2>"
                            f"<p>{r['PIE_Prev']:.1f} → {r['PIE']:.1f} PIE | {r['PTS']:.1f} PPG now</p></div>",
                            unsafe_allow_html=True)
                dl(mip[['Player/Team', 'PIE_Prev', 'PIE', 'Jump']], "⬇️ MIP race CSV", "mip_race.csv", "dl_mip")
    with a_tabs[5]:
        st.markdown("#### 🏅 All-League Teams (by PIE)")
        al = qual_p.sort_values('PIE', ascending=False).head(15).reset_index(drop=True)

        def render_all_league(col, title, squad, border):
            with col:
                html = (f"<div style='background:#161b22; border:2px solid {border}; border-radius:8px; padding:15px;'>"
                        f"<h4 style='color:{border}; text-align:center; text-transform:uppercase; margin-top:0;'>{title}</h4>")
                for _, r in squad.iterrows():
                    html += (f"<div class='stat-row'><span style='color:#fff; font-weight:bold;'>{r['Player/Team']}</span>"
                             f"<span class='stat-label'>{r['Team']}</span>"
                             f"<span class='stat-val'>{r['PIE']:.1f}</span></div>")
                st.markdown(html + "</div>", unsafe_allow_html=True)

        a1, a2, a3 = st.columns(3)
        render_all_league(a1, "1st Team", al.head(5), GOLD)
        render_all_league(a2, "2nd Team", al.iloc[5:10], SILVER)
        render_all_league(a3, "3rd Team", al.iloc[10:15], BRONZE)

    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown("### 🔥 Streak Trends")
    look = st.slider("Form window (games)", 2, 8, 3)
    recent_p = p_df.sort_values(['Player/Team', 'Season', 'Game_ID']).groupby('Player/Team').tail(look)
    recent_stats = recent_p.groupby('Player/Team').agg(Recent_PIE=('PIE_Raw', 'mean')).reset_index()
    trend = p_stats.merge(recent_stats, on='Player/Team')
    trend = trend[trend['GP'] >= max(look, 2)]
    trend['Swing'] = trend['Recent_PIE'] - trend['PIE']

    tc1, tc2 = st.columns(2)
    with tc1:
        st.markdown(f"<h4 style='color:{GREEN};'>📈 Heating Up</h4>", unsafe_allow_html=True)
        for _, r in trend.sort_values('Swing', ascending=False).head(4).iterrows():
            st.markdown(f"<div style='background:#1a2b1a; padding:10px; border-left:4px solid {GREEN}; margin-bottom:5px;'>"
                        f"<b>{r['Player/Team']}</b> <span style='color:#888;'>({r['Team']})</span> | "
                        f"+{r['Swing']:.1f} PIE over avg</div>", unsafe_allow_html=True)
    with tc2:
        st.markdown(f"<h4 style='color:{RED};'>📉 Cooling Down</h4>", unsafe_allow_html=True)
        for _, r in trend.sort_values('Swing', ascending=True).head(4).iterrows():
            st.markdown(f"<div style='background:#2b1a1a; padding:10px; border-left:4px solid {RED}; margin-bottom:5px;'>"
                        f"<b>{r['Player/Team']}</b> <span style='color:#888;'>({r['Team']})</span> | "
                        f"{r['Swing']:.1f} PIE under avg</div>", unsafe_allow_html=True)


# --------------------------------------------------------- POWER RANKINGS ----
elif view_mode == "🏆 Power Rankings & SOS":
    st.subheader("📊 League Power Index")
    st.markdown("Tune the weights — the board re-sorts live.")

    wc1, wc2, wc3 = st.columns(3)
    w_win = wc1.slider("Win% weight", 0.0, 1.0, 0.50, 0.05)
    w_sos = wc2.slider("SOS weight", 0.0, 1.0, 0.25, 0.05)
    w_net = wc3.slider("NetRtg weight", 0.0, 1.0, 0.25, 0.05)
    tot_w = max(w_win + w_sos + w_net, 0.01)

    ranks = t_stats.copy()
    net_norm = (ranks['NetRtg'] - ranks['NetRtg'].min()) / max(ranks['NetRtg'].max() - ranks['NetRtg'].min(), 0.01)
    ranks['True_Power'] = ((ranks['Win%'] * w_win) + (ranks['SOS'].fillna(0.5) * w_sos) + (net_norm * w_net)) / tot_w
    ranks = ranks.sort_values('True_Power', ascending=False).reset_index(drop=True)

    form_map, streak_map, win_streak_len = {}, {}, {}
    for team, g in t_df.sort_values(['Season', 'Game_ID']).groupby('Team Name'):
        seq = [int(w) for w in g['Win'].tolist()]
        if not seq:
            form_map[team], streak_map[team], win_streak_len[team] = "-", "-", 0
            continue
        form_map[team] = " ".join([f"<span style='color:{GREEN}; font-weight:bold;'>W</span>" if w
                                   else f"<span style='color:{RED}; font-weight:bold;'>L</span>"
                                   for w in seq[-5:]])
        s = 0
        for w in reversed(seq):
            if w == seq[-1]:
                s += 1
            else:
                break
        streak_map[team] = f"{'W' if seq[-1] else 'L'}{s}"
        win_streak_len[team] = s if seq[-1] else 0

    html = ("<table class='sleek-table'><tr><th>Rank</th><th>Team</th><th>Record</th><th>Win%</th>"
            "<th>SOS</th><th>NetRtg</th><th>Pt Diff</th><th>Form (L5)</th><th>Streak</th></tr>")
    for i, r in ranks.iterrows():
        medal = "🥇 " if i == 0 else "🥈 " if i == 1 else "🥉 " if i == 2 else f"{i+1}. "
        tname = r['Team Name']
        marked = (" <span style='background:#cc0000; color:#fff; font-size:10px; font-weight:bold; "
                  "padding:2px 6px; border-radius:4px; letter-spacing:1px;'>🎯 MARKED</span>"
                  if win_streak_len.get(tname, 0) >= 3 else "")
        stk = streak_map.get(tname, '-')
        sc = GREEN if stk.startswith('W') else RED if stk.startswith('L') else '#888'
        nc = GREEN if r['NetRtg'] >= 0 else RED
        sos_v = r['SOS'] if pd.notna(r['SOS']) else 0.0
        html += (f"<tr><td style='font-size:16px;'>{medal}</td><td class='player-name'>{tname}{marked}</td>"
                 f"<td>{int(r['Wins'])}-{int(r['GP']-r['Wins'])}</td><td>{r['Win%']:.3f}</td>"
                 f"<td style='color:{BLUE};'>{sos_v:.3f}</td>"
                 f"<td style='color:{nc}; font-weight:bold;'>{r['NetRtg']:+.1f}</td>"
                 f"<td>{r['Diff']:+.1f}</td><td>{form_map.get(tname, '-')}</td>"
                 f"<td style='color:{sc}; font-weight:bold;'>{stk}</td></tr>")
    st.markdown(html + "</table>", unsafe_allow_html=True)
    st.caption("🎯 MARKED = active 3+ game win streak. Bounty-eligible under The Hunt.")
    dl(ranks[['Team Name', 'Wins', 'GP', 'Win%', 'SOS', 'NetRtg', 'Diff', 'True_Power']],
       "⬇️ Power rankings CSV", "power_rankings.csv", "dl_pr")


# ----------------------------------------------------------- FRANCHISE HUB ---
elif view_mode == "🏢 Franchise Hub":
    teams = sorted([t for t in p_stats['Team'].dropna().unique() if str(t) != '0'])
    if not teams:
        st.info("No teams in scope.")
    else:
        sel_team = st.selectbox("Select Franchise", teams)
        st.markdown(f"<div class='header-banner'>{sel_team}</div>", unsafe_allow_html=True)

        t_data = t_df[t_df['Team Name'] == sel_team]
        p_data = p_df[p_df['Team Name'] == sel_team]
        t_row = t_stats[t_stats['Team Name'] == sel_team].iloc[0]

        tab_dash, tab_rot, tab_binder, tab_box = st.tabs(
            ["📋 Dashboard", "🔁 Rotation", "📇 Player Binder", "📓 Box Scores"])

        with tab_dash:
            c1, c2, c3, c4 = st.columns(4)
            wins = int(t_row['Wins'])
            losses = int(t_row['GP'] - wins)
            c1.markdown(f"<div class='metric-box'><div class='metric-title'>Record</div><div class='metric-value'>{wins} - {losses}</div><div class='metric-sub'>{t_row['Win%']:.3f}</div></div>", unsafe_allow_html=True)
            c2.markdown(f"<div class='metric-box'><div class='metric-title'>Point Diff</div><div class='metric-value'>{t_row['Diff']:+.1f}</div></div>", unsafe_allow_html=True)
            c3.markdown(f"<div class='metric-box'><div class='metric-title'>Net Rating</div><div class='metric-value'>{t_row['NetRtg']:+.1f}</div><div class='metric-sub'>ORtg {t_row['ORtg']:.1f} / DRtg {t_row['DRtg']:.1f}</div></div>", unsafe_allow_html=True)
            sos_v = t_row['SOS'] if pd.notna(t_row['SOS']) else 0
            c4.markdown(f"<div class='metric-box'><div class='metric-title'>Strength of Sched</div><div class='metric-value'>{sos_v:.3f}</div></div>", unsafe_allow_html=True)

            sc1, sc2 = st.columns(2)
            with sc1:
                st.markdown("### 🎯 Team Identity vs League")
                lg_avg = t_stats.mean(numeric_only=True)
                mx = t_stats.max(numeric_only=True)
                cats = ['Scoring', 'Playmaking', 'Rebounding', 'Defense', 'Efficiency']
                r1 = [norm(t_row['PPG'], mx['PPG']), norm(t_row['APG'], mx['APG']),
                      norm(t_row['RPG'], mx['RPG']), norm(t_row['DEF'], mx['DEF']),
                      norm(t_row['eFG%'], mx['eFG%'])]
                r2 = [norm(lg_avg['PPG'], mx['PPG']), norm(lg_avg['APG'], mx['APG']),
                      norm(lg_avg['RPG'], mx['RPG']), norm(lg_avg['DEF'], mx['DEF']),
                      norm(lg_avg['eFG%'], mx['eFG%'])]
                st.plotly_chart(draw_dynamic_radar(sel_team, r1, "League Avg", r2, cats, "Team Identity"),
                                use_container_width=True)
            with sc2:
                st.markdown("### 📈 Game-by-Game Margin")
                gl = t_data.sort_values(['Season', 'Game_ID']).reset_index(drop=True)
                gl['G'] = gl.index + 1
                fig = px.bar(gl, x='G', y='Point_Diff', template='plotly_dark',
                             color=gl['Point_Diff'].apply(lambda x: 'W' if x > 0 else 'L'),
                             color_discrete_map={'W': GREEN, 'L': RED},
                             labels={'Point_Diff': 'Margin', 'G': 'Game'})
                fig.update_layout(showlegend=False, height=380,
                                  paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig, use_container_width=True)

        with tab_rot:
            st.markdown("### 🔁 Five-Man Rotation (by Games Played)")
            st.caption("This is the exact five the Oracle simulates. GP is the primary sort — "
                       "PIE only breaks ties.")
            rot = get_rotation(sel_team)
            bench = full_roster(sel_team)
            bench = bench[~bench['Player/Team'].isin(rot['Player/Team'])]

            html = ("<table class='sleek-table'><tr><th>#</th><th>Player</th><th>GP</th><th>PPG</th>"
                    "<th>RPG</th><th>APG</th><th>USG%</th><th>PIE</th></tr>")
            for i, r in rot.iterrows():
                html += (f"<tr><td style='color:{GOLD}; font-weight:bold;'>{i+1}</td>"
                         f"<td class='player-name'>{r['Player/Team']}</td><td>{int(r['GP'])}</td>"
                         f"<td>{r['PTS']:.1f}</td><td>{r['REB']:.1f}</td><td>{r['AST']:.1f}</td>"
                         f"<td>{r['USG']:.1f}</td><td style='color:{GOLD}; font-weight:bold;'>{r['PIE']:.1f}</td></tr>")
            st.markdown(html + "</table>", unsafe_allow_html=True)

            if not bench.empty:
                st.markdown("#### 🪑 Depth (outside the five)")
                st.dataframe(bench[['Player/Team', 'GP', 'PTS', 'REB', 'AST', 'PIE']],
                             use_container_width=True, hide_index=True)

        with tab_binder:
            q = st.text_input("Search roster", "", key="binder_q")
            team_p = p_stats[p_stats['Team'] == sel_team]
            if q:
                team_p = team_p[team_p['Player/Team'].str.contains(q, case=False, na=False)]
            team_p = team_p.reset_index(drop=True)
            cols = st.columns(4)
            for idx, row in team_p.iterrows():
                with cols[idx % 4]:
                    st.markdown(generate_2k_player_card(row['Player/Team'], row, rank=row['League_Rank']),
                                unsafe_allow_html=True)

        with tab_box:
            game_opts = sorted(p_data[['Season', 'Game_ID']].dropna().drop_duplicates()
                               .itertuples(index=False, name=None), reverse=True)
            if not game_opts:
                st.info("No games logged.")
            else:
                sel_game = st.selectbox("Select Game", game_opts,
                                        format_func=lambda t: f"S{int(t[0])} • Game {int(t[1])}")
                g_data = p_data[(p_data['Season'] == sel_game[0]) & (p_data['Game_ID'] == sel_game[1])]
                if not g_data.empty:
                    potg = g_data.loc[g_data['PIE_Raw'].idxmax()]
                    opp = g_data['Opp_Name'].iloc[0] if 'Opp_Name' in g_data else "—"
                    st.markdown(
                        f"<div style='background: linear-gradient(90deg, #111, #333); padding:15px; "
                        f"border-left:5px solid #d4af37; margin-bottom:15px;'>"
                        f"<h4 style='margin:0; color:#aaa;'>PLAYER OF THE GAME — vs {opp}</h4>"
                        f"<h2 style='margin:0; color:#fff;'>{potg['Player/Team']}</h2>"
                        f"<p style='margin:0; color:#d4af37;'>{int(potg['PTS'])} PTS | {int(potg['REB'])} REB "
                        f"| {int(potg['AST'])} AST | {potg['PIE_Raw']:.1f} PIE</p></div>",
                        unsafe_allow_html=True)
                    st.markdown(generate_sleek_box_score(g_data), unsafe_allow_html=True)
                    st.markdown("#### Game Shot Profile")
                    st.markdown(draw_shot_profile(g_data['FGM'].sum(), g_data['FGA'].sum(),
                                                  g_data['3PM'].sum(), g_data['3PA'].sum()),
                                unsafe_allow_html=True)


# -------------------------------------------------------- PLAYER SPOTLIGHT ---
elif view_mode == "🔦 Player Spotlight":
    st.subheader("🔦 Player Spotlight")
    names = sorted(p_stats['Player/Team'].tolist())
    if not names:
        st.info("No players in scope.")
    else:
        default_i = names.index(st.session_state.watchlist[0]) if (
            st.session_state.watchlist and st.session_state.watchlist[0] in names) else 0
        sel = st.selectbox("Player", names, index=default_i)
        row = p_stats[p_stats['Player/Team'] == sel].iloc[0]
        logs = p_df[p_df['Player/Team'] == sel].sort_values(['Season', 'Game_ID']).reset_index(drop=True)

        top = st.columns([1, 3])
        with top[0]:
            st.markdown(generate_2k_player_card(sel, row, rank=row['League_Rank']), unsafe_allow_html=True)
            if st.button("★ Toggle Watchlist", use_container_width=True):
                toggle_watch(sel)
                st.rerun()
        with top[1]:
            m = st.columns(5)
            for col, (lab, val) in zip(m, [("PPG", f"{row['PTS']:.1f}"), ("RPG", f"{row['REB']:.1f}"),
                                           ("APG", f"{row['AST']:.1f}"), ("STOCKS", f"{row['DEF']:.1f}"),
                                           ("TS%", f"{row['TS%']:.1f}%")]):
                col.markdown(f"<div class='metric-box'><div class='metric-title'>{lab}</div>"
                             f"<div class='metric-value'>{val}</div></div>", unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)

            metric = st.selectbox("Trend metric", ['PIE_Raw', 'PTS', 'REB', 'AST', 'STL', 'BLK',
                                                   'Game_Score', 'USG_Game'], index=0)
            logs['G'] = logs.index + 1
            logs['Rolling'] = logs[metric].rolling(3, min_periods=1).mean()
            fig = go.Figure()
            fig.add_trace(go.Bar(x=logs['G'], y=logs[metric], name=metric,
                                 marker_color=['#2f6b3f' if w else '#6b2f2f' for w in logs['Win']]))
            fig.add_trace(go.Scatter(x=logs['G'], y=logs['Rolling'], name='3-game avg',
                                     line=dict(color=GOLD, width=3)))
            fig.add_hline(y=logs[metric].mean(), line_dash="dot", line_color="#888")
            fig.update_layout(template='plotly_dark', height=320, paper_bgcolor='rgba(0,0,0,0)',
                              plot_bgcolor='rgba(0,0,0,0)', margin=dict(l=10, r=10, t=30, b=10))
            st.plotly_chart(fig, use_container_width=True)

        st.markdown("### 🔀 Splits")
        s1, s2 = st.columns(2)
        with s1:
            st.markdown("**Wins vs Losses**")
            spl = logs.groupby('Win').agg(GP=('GKey', 'nunique'), PTS=('PTS', 'mean'),
                                          REB=('REB', 'mean'), AST=('AST', 'mean'),
                                          PIE=('PIE_Raw', 'mean')).reset_index()
            spl['Win'] = spl['Win'].map({1: 'W', 0: 'L'})
            st.dataframe(spl.round(1), use_container_width=True, hide_index=True)
        with s2:
            st.markdown("**By Opponent**")
            if 'Opp_Name' in logs.columns:
                opp = logs.groupby('Opp_Name').agg(GP=('GKey', 'nunique'), PTS=('PTS', 'mean'),
                                                   PIE=('PIE_Raw', 'mean')).reset_index()
                st.dataframe(opp.round(1).sort_values('PIE', ascending=False),
                             use_container_width=True, hide_index=True)

        st.markdown("### 📓 Game Log")
        show = logs[['Season', 'Game_ID', 'Opp_Name', 'Win', 'PTS', 'REB', 'AST', 'STL', 'BLK',
                     'FGM', 'FGA', '3PM', '3PA', 'TO', 'PIE_Raw', 'Game_Score']].copy()
        show['Win'] = show['Win'].map({1: 'W', 0: 'L'})
        st.dataframe(show.round(1), use_container_width=True, hide_index=True)
        dl(show, "⬇️ Game log CSV", f"{sel}_gamelog.csv", "dl_log")


# ------------------------------------------------------------- DATABASE ------
elif view_mode == "🗃️ Full Player Database":
    st.subheader("🗃️ Interactive Player Universe")

    f1, f2, f3 = st.columns([2, 2, 2])
    q = f1.text_input("🔍 Search player")
    team_filter = f2.multiselect("Teams", sorted(p_view['Team'].dropna().unique().tolist()))
    sort_by = f3.selectbox("Sort by", ['PIE', 'PTS', 'REB', 'AST', 'DEF', 'GmSc', 'NetRtg',
                                       'USG', 'TS%', 'GP'], index=0)

    view = p_view.copy()
    if q:
        view = view[view['Player/Team'].str.contains(q, case=False, na=False)]
    if team_filter:
        view = view[view['Team'].isin(team_filter)]
    view = view.sort_values(sort_by, ascending=False)

    x_ax = st.selectbox("Scatter X-axis", ['TS%', 'USG', 'eFG%', 'ORtg', 'FG%', 'GP'], index=0)
    fig = px.scatter(view, x=x_ax, y="PIE", size="PTS", color="Team",
                     hover_name="Player/Team",
                     hover_data={"PTS": True, "REB": True, "AST": True, "DEF": True, "GP": True, "Team": False},
                     template="plotly_dark", title=f"League Landscape: {x_ax} vs Impact (PIE)")
    fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
    st.plotly_chart(fig, use_container_width=True)

    st.markdown(f"### 📊 Master Roster — {len(view)} players")
    cols = ['Player/Team', 'Team', 'GP', 'PTS', 'REB', 'AST', 'STL', 'BLK', 'TO',
            'FG%', '3P%', 'TS%', 'eFG%', 'USG', 'ORtg', 'DRtg', 'NetRtg', 'GmSc', 'PIE']
    st.dataframe(view[cols], use_container_width=True, hide_index=True,
                 column_config={"PIE": st.column_config.ProgressColumn(
                     "PIE", min_value=0, max_value=float(max(p_stats['PIE'].max(), 1)), format="%.1f")})
    dl(view[cols], "⬇️ Roster CSV", "qcl_roster.csv", "dl_roster")


# ------------------------------------------------------------------ H2H ------
elif view_mode == "⚔️ Head-to-Head Radar":
    st.subheader("🕸️ Player Head-to-Head")
    player_list = sorted(p_stats['Player/Team'].tolist())
    if len(player_list) < 2:
        st.info("Need at least two players.")
    else:
        c1, c2 = st.columns(2)
        p1_sel = c1.selectbox("Player 1 (Gold)", player_list)
        p2_sel = c2.selectbox("Player 2 (Red)", player_list, index=1)

        d1 = p_stats[p_stats['Player/Team'] == p1_sel].iloc[0]
        d2 = p_stats[p_stats['Player/Team'] == p2_sel].iloc[0]
        mx = p_stats.max(numeric_only=True)

        cats = ['Scoring', 'Playmaking', 'Rebounding', 'Defense', 'Efficiency', 'Usage']
        r1 = [norm(d1['PTS'], mx['PTS']), norm(d1['AST'], mx['AST']), norm(d1['REB'], mx['REB']),
              norm(d1['DEF'], mx['DEF']), norm(d1['TS%'], 75), norm(d1['USG'], mx['USG'])]
        r2 = [norm(d2['PTS'], mx['PTS']), norm(d2['AST'], mx['AST']), norm(d2['REB'], mx['REB']),
              norm(d2['DEF'], mx['DEF']), norm(d2['TS%'], 75), norm(d2['USG'], mx['USG'])]

        cA, cB = st.columns([3, 2])
        with cA:
            st.plotly_chart(draw_dynamic_radar(p1_sel, r1, p2_sel, r2, cats, "The 6-Tool Core"),
                            use_container_width=True)
        with cB:
            st.markdown("#### Tale of the Tape")
            rows = [('GP', 'GP', 0), ('PPG', 'PTS', 1), ('RPG', 'REB', 1), ('APG', 'AST', 1),
                    ('STOCKS', 'DEF', 1), ('TS%', 'TS%', 1), ('USG%', 'USG', 1),
                    ('GmSc', 'GmSc', 1), ('PIE', 'PIE', 1)]
            html = "<table class='sleek-table'><tr><th>" + p1_sel + "</th><th>Stat</th><th>" + p2_sel + "</th></tr>"
            for label, col, dec in rows:
                v1, v2 = d1[col], d2[col]
                c1c = GOLD if v1 >= v2 else "#888"
                c2c = "#cc0000" if v2 >= v1 else "#888"
                html += (f"<tr><td style='color:{c1c}; font-weight:bold;'>{v1:.{dec}f}</td>"
                         f"<td style='color:#8b949e;'>{label}</td>"
                         f"<td style='color:{c2c}; font-weight:bold;'>{v2:.{dec}f}</td></tr>")
            st.markdown(html + "</table>", unsafe_allow_html=True)


# ------------------------------------------------------------- LINEUP LAB ----
elif view_mode == "🧪 Lineup Lab":
    st.subheader("🧪 Lineup Lab — Build Any Five")
    st.markdown("Assemble two five-man units from anywhere in the league and see which unit wins on paper.")

    names = sorted(p_stats['Player/Team'].tolist())
    if len(names) < 10:
        st.info("Need at least 10 players in scope.")
    else:
        lc1, lc2 = st.columns(2)
        with lc1:
            u1 = st.multiselect("Unit A (Gold) — pick 5", names, default=names[:5], max_selections=5)
        with lc2:
            u2 = st.multiselect("Unit B (Red) — pick 5", names, default=names[5:10], max_selections=5)

        if len(u1) == 5 and len(u2) == 5:
            a = p_stats[p_stats['Player/Team'].isin(u1)]
            b = p_stats[p_stats['Player/Team'].isin(u2)]

            def unit_line(u):
                return dict(PTS=u['PTS'].sum(), REB=u['REB'].sum(), AST=u['AST'].sum(),
                            DEF=u['DEF'].sum(), TS=u['TS%'].mean(), PIE=u['PIE'].sum(),
                            TO=u['TO'].sum())

            la, lb = unit_line(a), unit_line(b)
            mx = {k: max(la[k], lb[k]) for k in la}
            cats = ['Scoring', 'Rebounding', 'Playmaking', 'Defense', 'Efficiency', 'Impact']
            ra = [norm(la['PTS'], mx['PTS']), norm(la['REB'], mx['REB']), norm(la['AST'], mx['AST']),
                  norm(la['DEF'], mx['DEF']), norm(la['TS'], mx['TS']), norm(la['PIE'], mx['PIE'])]
            rb = [norm(lb['PTS'], mx['PTS']), norm(lb['REB'], mx['REB']), norm(lb['AST'], mx['AST']),
                  norm(lb['DEF'], mx['DEF']), norm(lb['TS'], mx['TS']), norm(lb['PIE'], mx['PIE'])]

            r1, r2 = st.columns([3, 2])
            with r1:
                st.plotly_chart(draw_dynamic_radar("Unit A", ra, "Unit B", rb, cats, "Unit vs Unit"),
                                use_container_width=True)
            with r2:
                edge = la['PIE'] - lb['PIE']
                winner = "UNIT A" if edge > 0 else "UNIT B"
                color = GOLD if edge > 0 else "#cc0000"
                st.markdown(f"<div class='sim-box'><div class='line-label'>Composite Edge</div>"
                            f"<h1 style='color:{color}; margin:6px 0;'>{winner}</h1>"
                            f"<div class='line-value'>{abs(edge):.1f} PIE</div>"
                            f"<p style='color:#888; margin-top:8px;'>A {la['PTS']:.1f} PPG "
                            f"vs B {lb['PTS']:.1f} PPG</p></div>", unsafe_allow_html=True)

            st.markdown("#### Unit Sheets")
            uc1, uc2 = st.columns(2)
            cols = ['Player/Team', 'Team', 'GP', 'PTS', 'REB', 'AST', 'DEF', 'TS%', 'PIE']
            uc1.dataframe(a[cols], use_container_width=True, hide_index=True)
            uc2.dataframe(b[cols], use_container_width=True, hide_index=True)
        else:
            st.info("Pick exactly five players per unit.")


# ---------------------------------------------------------- RIVALRY CORNER ---
elif view_mode == "🥊 Rivalry Corner":
    st.subheader("🥊 Rivalry Corner")
    min_meets = st.slider("Minimum meetings to qualify as a rivalry", 2, 10, 4)

    matchups = full_df[full_df['Type'].astype(str).str.lower() == 'team'].copy()
    if 'Opp_Name' not in matchups.columns:
        st.error("Matchup data not available.")
    else:
        matchups = matchups[matchups['Opp_Name'].notna()]
        matchups['Pairing'] = matchups.apply(
            lambda r: " vs ".join(sorted([str(r['Team Name']), str(r['Opp_Name'])])), axis=1)
        rivals = matchups.groupby('Pairing').agg(Games=('GKey', 'nunique')).reset_index()
        rivals = rivals[rivals['Games'] >= min_meets].sort_values('Games', ascending=False)

        if rivals.empty:
            st.info(f"No teams have played {min_meets}+ games against each other yet.")
        else:
            for _, riv in rivals.iterrows():
                t1, t2 = riv['Pairing'].split(" vs ")
                t1_wins = len(matchups[(matchups['Team Name'] == t1) & (matchups['Opp_Name'] == t2) & (matchups['Win'] == 1)])
                t2_wins = len(matchups[(matchups['Team Name'] == t2) & (matchups['Opp_Name'] == t1) & (matchups['Win'] == 1)])
                with st.expander(f"⚔️ {t1} vs {t2} — {riv['Games']} meetings ({t1_wins}-{t2_wins})", expanded=False):
                    st.markdown(
                        f"<div style='display:flex; justify-content:space-around; margin:10px 0;'>"
                        f"<div style='text-align:center;'><h2 style='color:{GREEN};'>{t1_wins}</h2><p>{t1}</p></div>"
                        f"<div style='text-align:center;'><h2 style='color:{RED};'>{t2_wins}</h2><p>{t2}</p></div></div>",
                        unsafe_allow_html=True)
                    gk = matchups[matchups['Pairing'] == riv['Pairing']][['Season', 'Game_ID']].drop_duplicates()
                    for (gs, gid) in sorted(gk.itertuples(index=False, name=None), reverse=True)[:5]:
                        g_rows = matchups[(matchups['Season'] == gs) & (matchups['Game_ID'] == gid)
                                          & (matchups['Pairing'] == riv['Pairing'])]
                        if len(g_rows) == 2:
                            r1, r2 = g_rows.iloc[0], g_rows.iloc[1]
                            st.markdown(f"<span style='color:#888;'>S{int(gs)} • G{int(gid)}</span> &nbsp; "
                                        f"{r1['Team Name']} <b style='color:#fff;'>{int(r1['PTS'])}</b> — "
                                        f"{r2['Team Name']} <b style='color:#fff;'>{int(r2['PTS'])}</b>",
                                        unsafe_allow_html=True)


# ------------------------------------------------------- ORACLE PREDICTOR ----
elif view_mode == "🔮 Oracle Predictor":
    st.subheader("🔮 QCL Oracle — Monte Carlo Matchup Engine")
    st.markdown("**Five men on the floor.** The Oracle simulates only each team's top-5 rotation "
                "by games played — not the whole roster. Scratch a starter and the projection moves.")

    if len(t_stats) < 2:
        st.info("Need at least two teams with logged games.")
    else:
        team_names = t_stats.sort_values('Win%', ascending=False)['Team Name'].tolist()
        c1, c2 = st.columns(2)
        t1_sel = c1.selectbox("🏠 Home Team", team_names, index=0)
        t2_sel = c2.selectbox("✈️ Away Team", team_names, index=min(1, len(team_names) - 1))

        if t1_sel == t2_sel:
            st.warning("Pick two different teams.")
            st.stop()

        with st.expander("⚙️ Simulation Settings", expanded=True):
            sc1, sc2, sc3, sc4 = st.columns(4)
            n_sims = sc1.select_slider("Simulations", [500, 1000, 2500, 5000, 10000], value=2500)
            hca = sc2.slider("Home court edge (pts)", 0.0, 5.0, 1.5, 0.5)
            variance = sc3.slider("Chaos multiplier", 0.5, 2.0, 1.0, 0.1,
                                  help="Scales game-to-game score variance. 2.0 = anything can happen.")
            star_conc = sc4.slider("Ball-hog factor", 2.0, 15.0, 6.0, 0.5,
                                   help="High = the star always eats. Low = points spread randomly.")

            ec1, ec2 = st.columns(2)
            r1_full = full_roster(t1_sel)['Player/Team'].tolist()
            r2_full = full_roster(t2_sel)['Player/Team'].tolist()
            out1 = ec1.multiselect(f"🚑 Scratches — {t1_sel}", r1_full, key="out1")
            out2 = ec2.multiselect(f"🚑 Scratches — {t2_sel}", r2_full, key="out2")

        rot1 = get_rotation(t1_sel, exclude=out1)
        rot2 = get_rotation(t2_sel, exclude=out2)

        if len(rot1) < 1 or len(rot2) < 1:
            st.error("Not enough available players to field a rotation.")
            st.stop()

        # --- show who is actually playing ---
        rc1, rc2 = st.columns(2)
        for col, tname, rot in [(rc1, t1_sel, rot1), (rc2, t2_sel, rot2)]:
            with col:
                st.markdown(f"##### 🔁 {tname} — Active Five")
                html = "<table class='sleek-table'><tr><th>Player</th><th>GP</th><th>PPG</th><th>USG%</th><th>PIE</th></tr>"
                for _, r in rot.iterrows():
                    html += (f"<tr><td class='player-name'>{r['Player/Team']}</td><td>{int(r['GP'])}</td>"
                             f"<td>{r['PTS']:.1f}</td><td>{r['USG']:.1f}</td>"
                             f"<td style='color:{GOLD}; font-weight:bold;'>{r['PIE']:.1f}</td></tr>")
                st.markdown(html + "</table>", unsafe_allow_html=True)
                if len(rot) < ROTATION_SIZE:
                    st.warning(f"Only {len(rot)} available — shorthanded.")

        if st.button("🔮 RUN SIMULATION", type="primary", use_container_width=True):
            with st.spinner(f"Running {n_sims:,} games..."):
                res = run_monte_carlo(t1_sel, t2_sel, rot1, rot2, n_sims=n_sims, hca=hca,
                                      star_conc=star_conc, variance=variance)

            p1, p2 = res['win1'], res['win2']
            med1, med2 = int(np.median(res['s1'])), int(np.median(res['s2']))
            spread = float(np.mean(res['margin']))
            total = float(np.mean(res['s1'] + res['s2']))

            fav = t1_sel if spread > 0 else t2_sel
            st.markdown(
                f"<div class='sim-box'>"
                f"<h4 style='color:#888; letter-spacing:2px;'>PROJECTED FINAL — MEDIAN OF {res['n']:,} SIMS</h4>"
                f"<h1 style='font-size:54px; margin:6px 0;'>"
                f"<span style='color:{GREEN if med1 > med2 else '#fff'};'>{med1}</span>"
                f" <span style='color:#555;'>—</span> "
                f"<span style='color:{GREEN if med2 > med1 else '#fff'};'>{med2}</span></h1>"
                f"<p style='color:#aaa; margin:0;'>{t1_sel} (H) vs {t2_sel} (A)</p></div>",
                unsafe_allow_html=True)

            # --- win probability bar ---
            fig = go.Figure()
            fig.add_trace(go.Bar(y=['Win Probability'], x=[p1 * 100], orientation='h',
                                 name=t1_sel, marker_color=GOLD,
                                 text=f"{t1_sel} {p1*100:.1f}%", textposition='inside',
                                 insidetextanchor='middle'))
            fig.add_trace(go.Bar(y=['Win Probability'], x=[p2 * 100], orientation='h',
                                 name=t2_sel, marker_color='#cc0000',
                                 text=f"{t2_sel} {p2*100:.1f}%", textposition='inside',
                                 insidetextanchor='middle'))
            fig.update_layout(barmode='stack', height=110, template='plotly_dark', showlegend=False,
                              xaxis=dict(visible=False), yaxis=dict(visible=False),
                              paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                              margin=dict(l=0, r=0, t=10, b=10))
            st.plotly_chart(fig, use_container_width=True)

            # --- the book ---
            b1, b2, b3, b4 = st.columns(4)
            b1.markdown(f"<div class='line-box'><div class='line-label'>Spread</div>"
                        f"<div class='line-value'>{fav} {-abs(spread):.1f}</div></div>", unsafe_allow_html=True)
            b2.markdown(f"<div class='line-box'><div class='line-label'>Total (O/U)</div>"
                        f"<div class='line-value'>{total:.1f}</div></div>", unsafe_allow_html=True)
            b3.markdown(f"<div class='line-box'><div class='line-label'>{t1_sel} ML</div>"
                        f"<div class='line-value'>{american_odds(p1)}</div></div>", unsafe_allow_html=True)
            b4.markdown(f"<div class='line-box'><div class='line-label'>{t2_sel} ML</div>"
                        f"<div class='line-value'>{american_odds(p2)}</div></div>", unsafe_allow_html=True)
            st.caption("Lines are model output, not a sportsbook. Feed them to the casino module at your own risk.")

            st.markdown("<br>", unsafe_allow_html=True)
            o_tabs = st.tabs(["📊 Distributions", "📋 Projected Box Scores", "🏆 MVP Odds"])

            with o_tabs[0]:
                dc1, dc2 = st.columns(2)
                with dc1:
                    mfig = px.histogram(x=res['margin'], nbins=40, template='plotly_dark',
                                        labels={'x': f'Margin ({t1_sel} − {t2_sel})'},
                                        title="Margin of Victory Distribution")
                    mfig.update_traces(marker_color=GOLD)
                    mfig.add_vline(x=0, line_dash="dash", line_color=RED)
                    mfig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                                       showlegend=False)
                    st.plotly_chart(mfig, use_container_width=True)
                with dc2:
                    sfig = go.Figure()
                    sfig.add_trace(go.Histogram(x=res['s1'], name=t1_sel, marker_color=GOLD, opacity=0.7))
                    sfig.add_trace(go.Histogram(x=res['s2'], name=t2_sel, marker_color='#cc0000', opacity=0.7))
                    sfig.update_layout(barmode='overlay', template='plotly_dark',
                                       title="Score Distributions",
                                       paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                    st.plotly_chart(sfig, use_container_width=True)

                blow = float((np.abs(res['margin']) >= 15).mean() * 100)
                close = float((np.abs(res['margin']) <= 5).mean() * 100)
                k1, k2, k3 = st.columns(3)
                k1.markdown(f"<div class='line-box'><div class='line-label'>Nail-biter (≤5)</div>"
                            f"<div class='line-value'>{close:.0f}%</div></div>", unsafe_allow_html=True)
                k2.markdown(f"<div class='line-box'><div class='line-label'>Blowout (15+)</div>"
                            f"<div class='line-value'>{blow:.0f}%</div></div>", unsafe_allow_html=True)
                k3.markdown(f"<div class='line-box'><div class='line-label'>Roster Health</div>"
                            f"<div class='line-value'>{res['avail'][0]*100:.0f}% / {res['avail'][1]*100:.0f}%</div></div>",
                            unsafe_allow_html=True)

            with o_tabs[1]:
                bx1 = projected_box(rot1, res['pp1'])
                bx2 = projected_box(rot2, res['pp2'])
                pc1, pc2 = st.columns(2)
                with pc1:
                    st.markdown(f"##### {t1_sel}")
                    st.dataframe(bx1, use_container_width=True, hide_index=True)
                    dl(bx1, "⬇️ CSV", f"{t1_sel}_proj.csv", "dl_bx1")
                with pc2:
                    st.markdown(f"##### {t2_sel}")
                    st.dataframe(bx2, use_container_width=True, hide_index=True)
                    dl(bx2, "⬇️ CSV", f"{t2_sel}_proj.csv", "dl_bx2")
                st.caption("PROJ PTS = median simulated points. Range = 20th–80th percentile outcomes.")

            with o_tabs[2]:
                mvp = res['mvp']
                top = mvp.iloc[0]
                st.markdown(f"<div class='sim-box'><div class='line-label'>Most Likely Game MVP</div>"
                            f"<h1 style='color:{GOLD}; margin:8px 0;'>{top['Player']}</h1>"
                            f"<p style='color:#aaa;'>{top['Team']} — wins it in {top['MVP %']}% of simulations</p></div>",
                            unsafe_allow_html=True)
                mfig = px.bar(mvp, x='MVP %', y='Player', orientation='h', color='Team',
                              template='plotly_dark',
                              color_discrete_map={t1_sel: GOLD, t2_sel: '#cc0000'})
                mfig.update_layout(yaxis=dict(autorange="reversed"), height=380,
                                   paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(mfig, use_container_width=True)
                dl(mvp, "⬇️ MVP odds CSV", "mvp_odds.csv", "dl_mvp")


# ------------------------------------------------------- ANALYTICS LAB -------
elif view_mode == "🔬 Advanced Analytics Lab":
    st.subheader("🔬 The Analytics Lab")

    lab = st.tabs(["Four Factors", "Pace & Space", "Team Ratings", "Player Ratings", "Correlations"])

    with lab[0]:
        st.markdown("### 📈 Four Factors")
        html = ("<table class='sleek-table'><tr><th>Team</th><th>eFG%</th><th>TO/G</th>"
                "<th>Opp PPP</th><th>Pace</th></tr>")
        for _, r in t_stats.sort_values('Win%', ascending=False).iterrows():
            html += (f"<tr><td class='player-name'>{r['Team Name']}</td><td>{r['eFG%']:.1f}%</td>"
                     f"<td>{r['TOPG']:.1f}</td><td>{r['Opp_PPP']:.2f}</td><td>{r['Pace']:.1f}</td></tr>")
        st.markdown(html + "</table>", unsafe_allow_html=True)

    with lab[1]:
        st.markdown("### 🏃 Offense vs Defense Quadrants")
        fig = px.scatter(t_stats, x='PPG', y='Opp_PPP', text='Team Name', size='GP',
                         title="Right = better offense. Lower = better defense.",
                         template="plotly_dark", color='Win%', color_continuous_scale='YlOrBr')
        fig.update_traces(textposition='top center')
        fig.update_yaxes(autorange="reversed")
        fig.add_hline(y=t_stats['Opp_PPP'].mean(), line_dash="dot", line_color="#555")
        fig.add_vline(x=t_stats['PPG'].mean(), line_dash="dot", line_color="#555")
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=520)
        st.plotly_chart(fig, use_container_width=True)

    with lab[2]:
        st.markdown("### 🧮 Team Ratings Board")
        st.caption("Points scored / allowed per 100 possessions. Pace = possessions per game.")
        html = "<table class='sleek-table'><tr><th>Team</th><th>ORtg</th><th>DRtg</th><th>NetRtg</th><th>Pace</th></tr>"
        for _, r in t_stats.sort_values('NetRtg', ascending=False).iterrows():
            nc = GREEN if r['NetRtg'] >= 0 else RED
            html += (f"<tr><td class='player-name'>{r['Team Name']}</td><td>{r['ORtg']:.1f}</td>"
                     f"<td>{r['DRtg']:.1f}</td><td style='color:{nc}; font-weight:bold;'>{r['NetRtg']:+.1f}</td>"
                     f"<td>{r['Pace']:.1f}</td></tr>")
        st.markdown(html + "</table>", unsafe_allow_html=True)
        dl(t_stats, "⬇️ Team ratings CSV", "team_ratings.csv", "dl_tr")

    with lab[3]:
        st.markdown("### 🎖️ Player Ratings Engine")
        st.caption("USG% = share of team possessions used. ORtg = pts per 100 individual possessions. "
                   "DRtg = team defense adjusted for stocks. GmSc = Hollinger Game Score.")
        st.dataframe(p_view[['Player/Team', 'Team', 'GP', 'USG', 'ORtg', 'DRtg', 'NetRtg', 'GmSc', 'PIE']]
                     .sort_values('NetRtg', ascending=False),
                     use_container_width=True, hide_index=True)

    with lab[4]:
        st.markdown("### 🔗 What Actually Wins Games?")
        if len(t_stats) >= 3:
            corr_cols = ['PPG', 'OppPPG', 'eFG%', 'TOPG', 'RPG', 'APG', 'SPG', 'BPG', 'Pace', 'NetRtg']
            corr = t_stats[corr_cols + ['Win%']].corr()['Win%'].drop('Win%').sort_values()
            fig = px.bar(x=corr.values, y=corr.index, orientation='h', template='plotly_dark',
                         labels={'x': 'Correlation with Win%', 'y': ''},
                         color=corr.values, color_continuous_scale='RdYlGn')
            fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                              height=420, coloraxis_showscale=False)
            st.plotly_chart(fig, use_container_width=True)
            st.caption("Correlation, not causation — and with a small sample it moves fast.")
        else:
            st.info("Need at least 3 teams for correlation analysis.")


# ---------------------------------------------------------------- VAULT ------
elif view_mode == "🏦 The Vault":
    st.subheader("🏦 THE VAULT — Master Ledger & Hall of Fame")
    p_tot = p_df.groupby('Player/Team').sum(numeric_only=True).reset_index()

    st.markdown("### 🏆 Hall of Fame Podiums")
    stat_pick = st.multiselect("Podiums to show", ['PTS', 'AST', 'REB', 'STL', 'BLK', '3PM'],
                               default=['PTS', 'AST', 'REB', 'STL'])
    labels = {'PTS': 'Scoring', 'AST': 'Assist', 'REB': 'Rebound', 'STL': 'Steals',
              'BLK': 'Blocks', '3PM': '3-Point'}
    for i in range(0, len(stat_pick), 2):
        cols = st.columns(2)
        for j, s in enumerate(stat_pick[i:i + 2]):
            with cols[j]:
                st.markdown(render_podium(f"All-Time {labels[s]} Leaders",
                                          p_tot.sort_values(s, ascending=False), s),
                            unsafe_allow_html=True)

    st.markdown("### 🗃️ The Master Ledger")
    q = st.text_input("🔍 Search the ledger")
    ledger = p_tot[['Player/Team', 'PTS', 'REB', 'AST', 'STL', 'BLK', 'FGM', 'FGA', '3PM', '3PA',
                    'FTM', 'FTA', 'Tipped_Passes', 'Shots_Affected', 'FB_Points', 'TO', 'FOULS']]
    if q:
        ledger = ledger[ledger['Player/Team'].str.contains(q, case=False, na=False)]
    st.dataframe(ledger.sort_values('PTS', ascending=False), use_container_width=True, hide_index=True)
    dl(ledger, "⬇️ Master ledger CSV", "qcl_master_ledger.csv", "dl_vault")


# ----------------------------------------------------------- RECORD BOOK -----
elif view_mode == "📖 Record Book & Milestones":
    st.subheader(f"📖 {banner_text} Record Book")
    tab_game, tab_miles, tab_team = st.tabs(["🔥 Single Game", "🏔️ Career Totals", "🏟️ Team Records"])

    with tab_game:
        depth = st.slider("Show top N", 3, 15, 5, key="rb_depth")
        st.markdown("### 🏆 Current Scope — Single Game Highs")
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown(generate_mini_leaderboard("Points", p_df, 'PTS', "#cc0000", depth, "Player/Team"), unsafe_allow_html=True)
            st.markdown(generate_mini_leaderboard("Steals", p_df, 'STL', "#ff8c00", depth, "Player/Team"), unsafe_allow_html=True)
        with c2:
            st.markdown(generate_mini_leaderboard("Rebounds", p_df, 'REB', "#32cd32", depth, "Player/Team"), unsafe_allow_html=True)
            st.markdown(generate_mini_leaderboard("Blocks", p_df, 'BLK', "#8a2be2", depth, "Player/Team"), unsafe_allow_html=True)
        with c3:
            st.markdown(generate_mini_leaderboard("Assists", p_df, 'AST', "#00bfff", depth, "Player/Team"), unsafe_allow_html=True)
            st.markdown(generate_mini_leaderboard("3-Pointers", p_df, '3PM', GOLD, depth, "Player/Team"), unsafe_allow_html=True)

        if selected_scope != "Career Stats":
            st.markdown("<hr>", unsafe_allow_html=True)
            st.markdown("### 🏛️ All-Time Single Game Highs (Franchise History)")
            ac1, ac2, ac3 = st.columns(3)
            with ac1:
                st.markdown(generate_mini_leaderboard("All-Time Points", full_p_df, 'PTS', "#cc0000", depth, "Player/Team"), unsafe_allow_html=True)
                st.markdown(generate_mini_leaderboard("All-Time Steals", full_p_df, 'STL', "#ff8c00", depth, "Player/Team"), unsafe_allow_html=True)
            with ac2:
                st.markdown(generate_mini_leaderboard("All-Time Rebounds", full_p_df, 'REB', "#32cd32", depth, "Player/Team"), unsafe_allow_html=True)
                st.markdown(generate_mini_leaderboard("All-Time Blocks", full_p_df, 'BLK', "#8a2be2", depth, "Player/Team"), unsafe_allow_html=True)
            with ac3:
                st.markdown(generate_mini_leaderboard("All-Time Assists", full_p_df, 'AST', "#00bfff", depth, "Player/Team"), unsafe_allow_html=True)
                st.markdown(generate_mini_leaderboard("All-Time 3PM", full_p_df, '3PM', GOLD, depth, "Player/Team"), unsafe_allow_html=True)

    with tab_miles:
        p_totals = p_df.groupby('Player/Team').sum(numeric_only=True).reset_index()
        mc1, mc2, mc3 = st.columns(3)
        mc1.markdown(generate_mini_leaderboard("Total Points", p_totals, 'PTS', "#cc0000", 10, "Player/Team"), unsafe_allow_html=True)
        mc2.markdown(generate_mini_leaderboard("Total Rebounds", p_totals, 'REB', "#32cd32", 10, "Player/Team"), unsafe_allow_html=True)
        mc3.markdown(generate_mini_leaderboard("Total Assists", p_totals, 'AST', "#00bfff", 10, "Player/Team"), unsafe_allow_html=True)
        mc4, mc5, mc6 = st.columns(3)
        mc4.markdown(generate_mini_leaderboard("Total Steals", p_totals, 'STL', "#ff8c00", 10, "Player/Team"), unsafe_allow_html=True)
        mc5.markdown(generate_mini_leaderboard("Total Blocks", p_totals, 'BLK', "#8a2be2", 10, "Player/Team"), unsafe_allow_html=True)
        mc6.markdown(generate_mini_leaderboard("Total 3PM", p_totals, '3PM', GOLD, 10, "Player/Team"), unsafe_allow_html=True)

        st.markdown("### 🎖️ Club Memberships")
        clubbed = p_stats[p_stats['Clubs'].apply(len) > 0]
        if clubbed.empty:
            st.info("No club memberships earned yet.")
        else:
            for _, r in clubbed.iterrows():
                chips = "".join([f"<span class='chip'>{c}</span>" for c in r['Clubs']])
                st.markdown(f"<div style='background:#161b22; padding:10px; border-left:3px solid {GOLD}; "
                            f"margin-bottom:6px;'><b style='color:#fff;'>{r['Player/Team']}</b> "
                            f"<span style='color:#888;'>({r['Team']})</span><br>{chips}</div>",
                            unsafe_allow_html=True)

    with tab_team:
        t_totals = t_df.groupby('Team Name').sum(numeric_only=True).reset_index()
        if t_totals.empty:
            st.info("No team totals in scope.")
        else:
            tc1, tc2 = st.columns(2)
            tc1.markdown(generate_mini_leaderboard("Most Wins", t_totals, 'Win', "#ffd700", 8, "Team Name"), unsafe_allow_html=True)
            tc2.markdown(generate_mini_leaderboard("Total Points Scored", t_totals, 'PTS', "#cc0000", 8, "Team Name"), unsafe_allow_html=True)

            st.markdown("### 💥 Biggest Blowouts")
            blow = t_df.sort_values('Point_Diff', ascending=False).head(10)
            html = "<table class='sleek-table'><tr><th>Season</th><th>Game</th><th>Winner</th><th>Score</th><th>Margin</th></tr>"
            for _, r in blow.iterrows():
                if pd.isna(r['Point_Diff']) or r['Point_Diff'] <= 0:
                    continue
                html += (f"<tr><td>S{int(r['Season'])}</td><td>G{int(r['Game_ID'])}</td>"
                         f"<td class='player-name'>{r['Team Name']}</td>"
                         f"<td>{int(r['PTS'])} — {int(r['Opp_PTS']) if pd.notna(r['Opp_PTS']) else '?'}</td>"
                         f"<td style='color:{GOLD}; font-weight:bold;'>+{int(r['Point_Diff'])}</td></tr>")
            st.markdown(html + "</table>", unsafe_allow_html=True)


st.sidebar.divider()
st.sidebar.caption("QCL HUB v3.0 • QSPN Analytics • Ball or Mute")
