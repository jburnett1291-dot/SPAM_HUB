
"""
═══════════════════════════════════════════════════════════════════════════
 QCL HUB — HISTORY LOADER v2  (local only, cannot hang)
═══════════════════════════════════════════════════════════════════════════

 WHAT WENT WRONG IN v1
 ---------------------
     for url in (...):
         d = pd.read_csv(url)          # <-- NO TIMEOUT

 pd.read_csv() on a URL has no timeout argument. It inherits Python's default
 socket timeout, which is None — wait forever. With two legacy filenames plus
 a manifest lookup, that's up to five blocking requests on cold start, inside
 load_data(), before a single pixel renders. Private repo, slow DNS, or a
 stalled 404 and the page just never paints. No error, no traceback. Blank.

 v2 READS LOCAL FILES ONLY. Zero network calls in the data path, so it
 physically cannot hang. Streamlit Cloud checks out your whole repo, so a CSV
 committed to the repo IS a local file — the network fallback was never
 needed in the first place.

 Network fetch is still available, but it's opt-in, off by default, and every
 call has a hard timeout.
═══════════════════════════════════════════════════════════════════════════
"""

import os
import json
import socket
import pandas as pd
import streamlit as st

try:
    _ROOT = os.path.dirname(os.path.abspath(__file__))
except NameError:
    _ROOT = os.getcwd()

HISTORY_DIR = os.path.join(_ROOT, "history")

# Era offsets keep archived seasons from colliding with live QCL seasons.
ERA_OFFSET = {"SPAM": 100, "LEGACY": 200, "PRESEASON": 300}
DEFAULT_ERA = "SPAM"

# Root-level files checked when history/ doesn't exist.
LEGACY_ROOT_FILES = [("SPAM_Raw_Data_v2.csv", "SPAM"), ("spam_history.csv", "SPAM")]

# OFF by default. Only flip this on once the page is confirmed loading, and
# note that every request below is hard-capped at HISTORY_NET_TIMEOUT seconds.
HISTORY_ALLOW_NETWORK = os.environ.get("HISTORY_ALLOW_NETWORK", "0") == "1"
HISTORY_NET_TIMEOUT = 6
GH_RAW = (f"https://raw.githubusercontent.com/"
          f"{os.environ.get('HUB_REPO', 'jburnett1291-dot/SPAM_HUB')}/"
          f"{os.environ.get('HUB_BRANCH', 'main')}")


def _era_of(fname):
    up = str(fname).upper()
    for era in ERA_OFFSET:
        if era in up:
            return era
    return DEFAULT_ERA


def _read_local(fname):
    """history/<f> then root <f>. Disk only — no sockets, no hanging."""
    for p in (os.path.join(HISTORY_DIR, fname), os.path.join(_ROOT, fname)):
        if os.path.exists(p):
            try:
                return pd.read_csv(p), f"local:{os.path.relpath(p, _ROOT)}"
            except Exception as e:
                return None, f"FAILED {fname} ({type(e).__name__}: {e})"
    return None, f"missing:{fname}"


def _read_remote(fname):
    """Opt-in only, and every request is timeout-capped."""
    if not HISTORY_ALLOW_NETWORK:
        return None, f"missing:{fname}"
    import urllib.request
    import io as _io
    for url in (f"{GH_RAW}/history/{fname}", f"{GH_RAW}/{fname}"):
        try:
            with urllib.request.urlopen(url, timeout=HISTORY_NET_TIMEOUT) as r:
                if r.status == 200:
                    return pd.read_csv(_io.BytesIO(r.read())), f"github:{fname}"
        except (socket.timeout, TimeoutError):
            return None, f"TIMEOUT {fname}"
        except Exception:
            continue
    return None, f"missing:{fname}"


def _discover_history():
    """Every historical CSV to merge, as (filename, era). Filesystem only."""
    out, seen = [], set()
    mf = os.path.join(HISTORY_DIR, "manifest.json")
    if os.path.exists(mf):
        try:
            with open(mf, "r", encoding="utf-8") as fh:
                for ent in (json.load(fh) or []):
                    f = ent.get("file")
                    if f and f not in seen:
                        seen.add(f)
                        out.append((f, ent.get("era") or _era_of(f)))
        except Exception:
            pass
    if os.path.isdir(HISTORY_DIR):
        try:
            for f in sorted(os.listdir(HISTORY_DIR)):
                if f.lower().endswith(".csv") and f not in seen:
                    seen.add(f)
                    out.append((f, _era_of(f)))
        except Exception:
            pass
    for f, era in LEGACY_ROOT_FILES:
        if f not in seen:
            seen.add(f)
            out.append((f, era))
    return out


def _merge_history(df, health):
    """Fold archived seasons into the live sheet. Never raises, never hangs."""
    merged, notes = 0, []
    try:
        sources = _discover_history()
    except Exception as e:
        health["History sources"] = f"discovery failed ({type(e).__name__})"
        return df, health

    for fname, era in sources:
        sp, where = _read_local(fname)
        if sp is None and where.startswith("missing:"):
            sp, where = _read_remote(fname)
        if sp is None:
            if not where.startswith("missing:"):
                notes.append(f"⚠️ {where}")
            continue
        try:
            sp.columns = sp.columns.str.strip()
            if "Season" not in sp.columns:
                notes.append(f"⚠️ {fname}: no Season column")
                continue
            off = ERA_OFFSET.get(era, 100)
            sp["Season"] = pd.to_numeric(sp["Season"], errors="coerce") + off
            sp = sp[sp["Season"].notna()]
            if sp.empty:
                notes.append(f"⚠️ {fname}: no valid Season rows")
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
        health["⚠️ NO HISTORY"] = ("Commit your old-season CSVs to history/ "
                                   "or the repo root, then Refresh Sheet.")
    return df, health


# ═══════════════════════════════════════════════════════════════════════════
#  DIAGNOSTIC — paste at the VERY TOP of app.py, right after
#  st.set_page_config(...), to find where a blank page dies.
#  Delete it once the page renders.
# ═══════════════════════════════════════════════════════════════════════════
DIAGNOSTIC_SNIPPET = '''
# ---- TEMP DIAGNOSTIC: delete once the page renders ----
st.write("✅ 1. Streamlit is alive")

import os
_r = os.path.dirname(os.path.abspath(__file__))
st.write("✅ 2. Files at repo root:", sorted(os.listdir(_r))[:25])
st.write("   history/ exists:", os.path.isdir(os.path.join(_r, "history")))
st.write("   SPAM csv at root:", os.path.exists(os.path.join(_r, "SPAM_Raw_Data_v2.csv")))

try:
    _tmp = load_data()
    st.write("✅ 3. load_data() returned:", type(_tmp).__name__)
    if isinstance(_tmp, str):
        st.error("load_data returned an ERROR STRING: " + _tmp)
    else:
        st.write("   rows:", len(_tmp["df"]))
except Exception as _e:
    st.exception(_e)
st.stop()   # nothing below this runs while diagnosing
# ---- END DIAGNOSTIC ----
'''
