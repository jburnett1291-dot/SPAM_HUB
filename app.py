"""
═══════════════════════════════════════════════════════════════════════════
 QCL HUB — BRANDING v2  (fixes the blank front page)
═══════════════════════════════════════════════════════════════════════════

 WHAT BROKE IN v1
 ----------------
 1. components.html(..., height=0)
    Streamlit renders that in an IFRAME. `position:fixed; inset:0` is scoped
    to the iframe, which was 0px tall — so the splash never covered the page,
    and the component still consumed a layout slot. It's also deprecated:
        "st.components.v1.html will be removed after 2026-06-01"

 2. .stApp > * { position:relative; z-index:1 }
    Forcing position onto every direct child of .stApp collapses Streamlit's
    own scroll/stacking containers. THIS is what blanked the front page.

 THE FIX
 -------
 No iframe. No pseudo-element. No z-index rules at all.
 The watermark opacity is baked INTO the PNG's alpha channel, then set as a
 normal `background-image` on .stApp, layered over your existing gradient.
 Nothing to stack means nothing to break.

 The splash is pure CSS injected into the real DOM via st.markdown, so
 position:fixed actually covers the viewport, and it removes itself with an
 animation (no JS, no iframe).

 PASTE: replace the whole render_brand / _logo_* section from hub_patch.py.
═══════════════════════════════════════════════════════════════════════════
"""

import os
import io
import base64
import numpy as np
import streamlit as st

try:
    _ROOT = os.path.dirname(os.path.abspath(__file__))
except NameError:
    _ROOT = os.getcwd()

GH_USER_REPO = os.environ.get("HUB_REPO", "jburnett1291-dot/SPAM_HUB")
GH_BRANCH_HUB = os.environ.get("HUB_BRANCH", "main")
GH_RAW = f"https://raw.githubusercontent.com/{GH_USER_REPO}/{GH_BRANCH_HUB}"
LOGO_FILE = os.environ.get("HUB_LOGO", "Logo.png")


def _logo_bytes(name=LOGO_FILE):
    p = os.path.join(_ROOT, name)
    if os.path.exists(p):
        try:
            with open(p, "rb") as fh:
                return fh.read()
        except Exception:
            pass
    try:
        import urllib.request
        with urllib.request.urlopen(f"{GH_RAW}/{name}", timeout=8) as r:
            if r.status == 200:
                return r.read()
    except Exception:
        pass
    return None


def _key_background(im, tol=38):
    """Drop a flat backdrop so the mark sits on the dark theme without a box.
    Only fires when all four corners agree — art that already has alpha is
    left alone."""
    w, h = im.size
    px = im.load()
    corners = [px[0, 0], px[w - 1, 0], px[0, h - 1], px[w - 1, h - 1]]
    r0 = sum(c[0] for c in corners) // 4
    g0 = sum(c[1] for c in corners) // 4
    b0 = sum(c[2] for c in corners) // 4
    if not all(abs(c[0] - r0) < 28 and abs(c[1] - g0) < 28 and abs(c[2] - b0) < 28
               for c in corners):
        return im
    arr = np.array(im).astype(int)
    dist = (np.abs(arr[:, :, 0] - r0) + np.abs(arr[:, :, 1] - g0) + np.abs(arr[:, :, 2] - b0))
    arr[:, :, 3] = np.where(dist < tol * 3, 0, arr[:, :, 3])
    from PIL import Image
    return Image.fromarray(arr.astype("uint8"), "RGBA")


@st.cache_data(ttl=3600, show_spinner=False)
def logo_uri(alpha=1.0, max_px=900):
    """Transparent-background logo as a data URI.

    `alpha` is multiplied straight into the PNG. That's the whole trick: a
    5%-alpha image needs no CSS opacity, so it can be a plain background-image
    and never touches stacking or layout.
    """
    raw = _logo_bytes()
    if not raw:
        return ""
    try:
        from PIL import Image
        im = Image.open(io.BytesIO(raw)).convert("RGBA")
        if max(im.size) > max_px:                       # 1MB logo -> keep it light
            im.thumbnail((max_px, max_px), Image.LANCZOS)
        im = _key_background(im)
        if alpha < 1.0:
            a = im.split()[-1].point(lambda p: int(p * max(0.0, min(1.0, alpha))))
            im.putalpha(a)
        buf = io.BytesIO()
        im.save(buf, "PNG", optimize=True)
        return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()
    except Exception:
        return "data:image/png;base64," + base64.b64encode(raw).decode()


def render_brand(splash=True, watermark=True, wm_opacity=0.06, splash_ms=1500):
    """Call ONCE, right after your main CSS block in Section 2."""

    # ---- watermark: baked alpha, layered over the existing gradient ----
    if watermark:
        wm = logo_uri(alpha=wm_opacity, max_px=760)
        if wm:
            st.markdown(f"""
<style>
  .stApp {{
    background-image:
      url('{wm}'),
      radial-gradient(circle at top, #121212 0%, #000000 100%);
    background-repeat: no-repeat, no-repeat;
    background-position: center 42%, center;
    background-size: min(56vw, 660px) auto, cover;
    background-attachment: fixed, fixed;
  }}
</style>""", unsafe_allow_html=True)

    # ---- splash: real DOM, pure CSS, self-removing. No iframe. ----
    if splash and not st.session_state.get("_qcl_splash"):
        st.session_state["_qcl_splash"] = True
        full = logo_uri(alpha=1.0, max_px=520)
        if full:
            st.markdown(f"""
<div class="qcl-splash">
  <img src="{full}" alt="">
  <div class="qcl-splash-tag">QWIK'S CUP LEAGUE</div>
  <div class="qcl-splash-sub">Win the Cup. Own the Month. Build the Legacy.</div>
</div>
<style>
  .qcl-splash {{
    position: fixed; inset: 0;
    display: flex; flex-direction: column;
    align-items: center; justify-content: center; gap: 16px;
    background: radial-gradient(circle at 50% 42%, #141821 0%, #000 100%);
    animation: qclSplashOut .65s ease {splash_ms}ms forwards;
  }}
  .qcl-splash img {{
    width: min(42vw, 300px);
    filter: drop-shadow(0 0 38px rgba(212,175,55,.42));
    animation: qclPop .85s cubic-bezier(.2,.85,.25,1) both;
  }}
  .qcl-splash-tag {{
    color:#d4af37; font:900 20px/1 'Helvetica Neue',Arial,sans-serif;
    letter-spacing:6px; animation: qclPop 1.05s cubic-bezier(.2,.85,.25,1) both;
  }}
  .qcl-splash-sub {{
    color:#79818d; font:600 11px/1 'Helvetica Neue',Arial,sans-serif;
    letter-spacing:3px; animation: qclPop 1.25s cubic-bezier(.2,.85,.25,1) both;
  }}
  @keyframes qclPop {{ from {{ opacity:0; transform:scale(.88) translateY(12px); }}
                       to   {{ opacity:1; transform:none; }} }}
  /* pointer-events:none FIRST so a slow fade can never eat a click */
  @keyframes qclSplashOut {{ from {{ opacity:1; }}
                             to   {{ opacity:0; visibility:hidden; pointer-events:none; }} }}
</style>""", unsafe_allow_html=True)


def brand_header(text):
    """Gold banner with the mark inline. Drop-in for your header-banner div."""
    u = logo_uri(alpha=1.0, max_px=180)
    badge = (f"<img src='{u}' style='height:36px;vertical-align:middle;margin-right:12px;"
             f"filter:drop-shadow(0 2px 4px rgba(0,0,0,.55));'>" if u else "")
    st.markdown(f"<div class='header-banner'>{badge}{text}</div>", unsafe_allow_html=True)


def brand_sidebar():
    """Small mark at the top of the sidebar."""
    u = logo_uri(alpha=1.0, max_px=260)
    if u:
        st.sidebar.markdown(
            f"<div style='text-align:center;padding:6px 0 14px;'>"
            f"<img src='{u}' style='width:112px;max-width:80%;'></div>",
            unsafe_allow_html=True)
