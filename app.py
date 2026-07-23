"""
═══════════════════════════════════════════════════════════════════════════
 QCL HUB PATCH — Logo splash / watermark  +  Historical season loader
═══════════════════════════════════════════════════════════════════════════

 WHY OLD SEASONS AREN'T SHOWING
 ------------------------------
 app.py looks for history like this:

     _sp_path = os.path.join(_root, "SPAM_Raw_Data_v2.csv")
     if os.path.exists(_sp_path):        # <-- LOCAL file next to app.py

 Your repo root has cards/ cutouts/ logos/ qtcg/ templates/ Logo.png app.py
 fantasy_market.json popularity.json requirements.txt — and NO
 SPAM_Raw_Data_v2.csv. os.path.exists() returns False, the block is skipped
 SILENTLY, and Seasons 1–6 never load. No error. Just missing.

 This patch:
   * scans a history/ FOLDER so you can drop in as many old seasons as you like
   * falls back to raw.githubusercontent.com when a file isn't on disk
   * reports every source in Data Health, LOUDLY, including failures
   * keeps the +100 season offset so SPAM S1 never collides with QCL S1

 WHERE TO PASTE
 --------------
 1. Section 1 CONFIG  — add the GH_RAW / HISTORY_DIR constants
 2. Section 3 DATA ENGINE — replace the SPAM-merge try/except inside
    load_data() with  df, health = _merge_history(df, health)
 3. Section 2 STYLE, right after the st.markdown CSS block —
    call  render_brand()
═══════════════════════════════════════════════════════════════════════════
"""

import os
import io
import json
import base64
import pandas as pd
import numpy as np
import streamlit as st
import streamlit.components.v1 as components

# ── 1. CONFIG ADDITIONS ───────────────────────────────────────────────────
GH_USER_REPO = os.environ.get("HUB_REPO", "jburnett1291-dot/SPAM_HUB")
GH_BRANCH_HUB = os.environ.get("HUB_BRANCH", "main")
GH_RAW = f"https://raw.githubusercontent.com/{GH_USER_REPO}/{GH_BRANCH_HUB}"

try:
    _ROOT = os.path.dirname(os.path.abspath(__file__))
except NameError:
    _ROOT = os.getcwd()

HISTORY_DIR = os.path.join(_ROOT, "history")
LOGO_FILE = os.environ.get("HUB_LOGO", "Logo.png")

# Era offsets keep old-league seasons from colliding with QCL 1..N.
#   SPAM S1 -> 101, S6 -> 106.  Add more eras here as you archive them.
ERA_OFFSET = {"SPAM": 100, "LEGACY": 200, "PRESEASON": 300}
DEFAULT_ERA = "SPAM"

# Files checked at the repo root, in order, when history/ is empty.
LEGACY_ROOT_FILES = [("SPAM_Raw_Data_v2.csv", "SPAM"), ("spam_history.csv", "SPAM")]


# ── 2. LOGO: SPLASH + WATERMARK ───────────────────────────────────────────
@st.cache_data(ttl=3600)
def _logo_data_uri(name=LOGO_FILE):
    """Logo.png -> data URI. Tries disk first, then the repo over HTTPS."""
    p = os.path.join(_ROOT, name)
    if os.path.exists(p):
        try:
            with open(p, "rb") as fh:
                return "data:image/png;base64," + base64.b64encode(fh.read()).decode()
        except Exception:
            pass
    try:
        import urllib.request
        with urllib.request.urlopen(f"{GH_RAW}/{name}", timeout=8) as r:
            if r.status == 200:
                return "data:image/png;base64," + base64.b64encode(r.read()).decode()
    except Exception:
        pass
    return ""


@st.cache_data(ttl=3600)
def _logo_transparent_uri(name=LOGO_FILE, tol=38):
    """Key out a flat backdrop so the mark sits cleanly over the dark theme.

    Your Logo.png is a solid-background render, so pasting it raw leaves a
    visible box. This samples the four corners and drops anything close to
    that colour, then returns a real transparent PNG.
    """
    p = os.path.join(_ROOT, name)
    raw = None
    if os.path.exists(p):
        try:
            with open(p, "rb") as fh:
                raw = fh.read()
        except Exception:
            raw = None
    if raw is None:
        try:
            import urllib.request
            with urllib.request.urlopen(f"{GH_RAW}/{name}", timeout=8) as r:
                raw = r.read() if r.status == 200 else None
        except Exception:
            raw = None
    if not raw:
        return ""
    try:
        from PIL import Image
        im = Image.open(io.BytesIO(raw)).convert("RGBA")
        w, h = im.size
        px = im.load()
        corners = [px[0, 0], px[w - 1, 0], px[0, h - 1], px[w - 1, h - 1]]
        r0 = sum(c[0] for c in corners) // 4
        g0 = sum(c[1] for c in corners) // 4
        b0 = sum(c[2] for c in corners) // 4
        # only key if the corners agree — otherwise the art already has alpha
        if not all(abs(c[0] - r0) < 28 and abs(c[1] - g0) < 28 and abs(c[2] - b0) < 28
                   for c in corners):
            buf = io.BytesIO()
            im.save(buf, "PNG")
            return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()
        arr = np.array(im).astype(int)
        dist = (np.abs(arr[:, :, 0] - r0) + np.abs(arr[:, :, 1] - g0) + np.abs(arr[:, :, 2] - b0))
        arr[:, :, 3] = np.where(dist < tol * 3, 0, arr[:, :, 3])
        out = Image.fromarray(arr.astype("uint8"), "RGBA")
        buf = io.BytesIO()
        out.save(buf, "PNG")
        return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()
    except Exception:
        return "data:image/png;base64," + base64.b64encode(raw).decode()


def render_brand(splash=True, watermark=True, splash_ms=1600, wm_opacity=0.05):
    """Call once, right after the main CSS block."""
    uri = _logo_transparent_uri()
    if not uri:
        return

    if watermark:
        st.markdown(f"""
<style>
  .stApp::before {{
    content:''; position:fixed; inset:0;
    background:url('{uri}') center 45% / min(58vw,720px) no-repeat;
    opacity:{wm_opacity}; pointer-events:none; z-index:0;
  }}
  .stApp > * {{ position:relative; z-index:1; }}
</style>""", unsafe_allow_html=True)

    if splash and not st.session_state.get("_qcl_splash_done"):
        st.session_state["_qcl_splash_done"] = True
        components.html(f"""
<div id="qspl">
  <img src="{uri}">
  <div class="tag">QWIK'S CUP LEAGUE</div>
  <div class="sub">Win the Cup. Own the Month. Build the Legacy.</div>
</div>
<style>
  #qspl {{ position:fixed; inset:0; z-index:99999; display:flex; flex-direction:column;
          align-items:center; justify-content:center; gap:14px;
          background:radial-gradient(circle at 50% 40%,#14181f 0%,#000 100%);
          animation:qsplout .7s ease {splash_ms}ms forwards; }}
  #qspl img {{ width:min(46vw,340px); filter:drop-shadow(0 0 40px rgba(212,175,55,.45));
              animation:qsplin .9s cubic-bezier(.2,.8,.2,1); }}
  #qspl .tag {{ color:#d4af37; font:900 22px/1 'Helvetica Neue',sans-serif; letter-spacing:6px;
               animation:qsplin 1.1s cubic-bezier(.2,.8,.2,1); }}
  #qspl .sub {{ color:#7e8794; font:600 12px/1 'Helvetica Neue',sans-serif; letter-spacing:3px;
               animation:qsplin 1.3s cubic-bezier(.2,.8,.2,1); }}
  @keyframes qsplin {{ from{{opacity:0; transform:scale(.86) translateY(14px);}} to{{opacity:1;}} }}
  @keyframes qsplout {{ to{{opacity:0; visibility:hidden;}} }}
</style>""", height=0)


def brand_header(text):
    """Gold banner with the mark inline — drop-in for the existing header-banner."""
    uri = _logo_transparent_uri()
    badge = (f"<img src='{uri}' style='height:38px;vertical-align:middle;margin-right:12px;"
             f"filter:drop-shadow(0 2px 4px rgba(0,0,0,.5));'>" if uri else "")
    st.markdown(f"<div class='header-banner'>{badge}{text}</div>", unsafe_allow_html=True)


# ── 3. HISTORY LOADER (the actual season fix) ─────────────────────────────
def _read_csv_any(fname):
    """history/<f> or root <f> on disk, else the same path from the repo over HTTPS."""
    for p in (os.path.join(HISTORY_DIR, fname), os.path.join(_ROOT, fname)):
        if os.path.exists(p):
            try:
                return pd.read_csv(p), f"local:{os.path.relpath(p, _ROOT)}"
            except Exception as e:
                return None, f"FAILED local {fname} ({type(e).__name__})"
    for url in (f"{GH_RAW}/history/{fname}", f"{GH_RAW}/{fname}"):
        try:
            d = pd.read_csv(url)
            if len(d):
                return d, f"github:{url.replace(GH_RAW + '/', '')}"
        except Exception:
            continue
    return None, f"NOT FOUND {fname}"


def _era_of(fname):
    up = str(fname).upper()
    for era in ERA_OFFSET:
        if era in up:
            return era
    return DEFAULT_ERA


@st.cache_data(ttl=300, show_spinner=False)
def _history_manifest():
    """history/manifest.json  ->  [{"file": "...", "era": "SPAM"}, ...]
    Optional. Without it, every CSV in history/ is auto-detected."""
    for p in (os.path.join(HISTORY_DIR, "manifest.json"),):
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as fh:
                    d = json.load(fh)
                if isinstance(d, list):
                    return d
            except Exception:
                pass
    try:
        import urllib.request
        with urllib.request.urlopen(f"{GH_RAW}/history/manifest.json", timeout=8) as r:
            if r.status == 200:
                d = json.loads(r.read().decode())
                if isinstance(d, list):
                    return d
    except Exception:
        pass
    return []


def _discover_history():
    """Every historical CSV to merge, as (filename, era)."""
    out, seen = [], set()
    for ent in _history_manifest():
        f = ent.get("file")
        if f and f not in seen:
            seen.add(f)
            out.append((f, ent.get("era") or _era_of(f)))
    if os.path.isdir(HISTORY_DIR):
        for f in sorted(os.listdir(HISTORY_DIR)):
            if f.lower().endswith(".csv") and f not in seen:
                seen.add(f)
                out.append((f, _era_of(f)))
    for f, era in LEGACY_ROOT_FILES:
        if f not in seen:
            seen.add(f)
            out.append((f, era))
    return out


def _merge_history(df, health):
    """Fold every historical season into the live sheet.

    Replaces the old silent try/except. Anything that fails is reported in
    Data Health instead of vanishing.
    """
    sources = _discover_history()
    merged, notes = 0, []
    for fname, era in sources:
        sp, where = _read_csv_any(fname)
        if sp is None:
            if not where.startswith("NOT FOUND"):
                notes.append(f"⚠️ {where}")
            continue
        try:
            sp.columns = sp.columns.str.strip()
            if "Season" not in sp.columns:
                notes.append(f"⚠️ {fname}: no Season column — skipped")
                continue
            off = ERA_OFFSET.get(era, 100)
            sp["Season"] = pd.to_numeric(sp["Season"], errors="coerce") + off
            sp = sp[sp["Season"].notna()]
            if sp.empty:
                notes.append(f"⚠️ {fname}: no rows with a valid Season")
                continue
            seas = sorted({int(s) - off for s in sp["Season"].unique()})
            df = pd.concat([df, sp], ignore_index=True)
            merged += len(sp)
            notes.append(f"✅ {era} {where} — {len(sp):,} rows, seasons {seas}")
        except Exception as e:
            notes.append(f"⚠️ {fname}: {type(e).__name__}")
    health["History rows merged"] = f"{merged:,}"
    health["History sources"] = " | ".join(notes) if notes else "none found"
    if merged == 0:
        health["⚠️ NO HISTORY LOADED"] = (
            "Put your old-season CSVs in a history/ folder in the repo "
            "(or SPAM_Raw_Data_v2.csv at the root) and commit them.")
    return df, health
