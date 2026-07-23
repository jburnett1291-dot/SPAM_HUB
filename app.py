import streamlit as st

st.set_page_config(page_title="QCL TEST", layout="wide")

st.title("✅ Streamlit is running")
st.write("If you can read this, the platform and your deploy are fine.")

import os
_r = os.path.dirname(os.path.abspath(__file__))

st.subheader("Repo root contents")
try:
    st.write(sorted(os.listdir(_r)))
except Exception as e:
    st.error(f"listdir failed: {e}")

st.subheader("Season file check")
for f in ("SPAM_Raw_Data_v2.csv", "spam_history.csv"):
    p = os.path.join(_r, f)
    st.write(f"`{f}` at root:", os.path.exists(p))

st.write("`history/` folder exists:", os.path.isdir(os.path.join(_r, "history")))

st.subheader("Can pandas read it?")
try:
    import pandas as pd
    p = os.path.join(_r, "SPAM_Raw_Data_v2.csv")
    if os.path.exists(p):
        d = pd.read_csv(p)
        d.columns = d.columns.str.strip()
        st.success(f"Read {len(d):,} rows")
        st.write("Seasons in file:",
                 sorted(pd.to_numeric(d.get("Season"), errors="coerce").dropna().unique().tolist()))
    else:
        st.warning("CSV not found at repo root — that's why old seasons are missing.")
except Exception as e:
    st.exception(e)

st.subheader("Logo check")
lp = os.path.join(_r, "Logo.png")
st.write("`Logo.png` exists:", os.path.exists(lp))
if os.path.exists(lp):
    st.write("size:", f"{os.path.getsize(lp)/1024/1024:.2f} MB")
    st.image(lp, width=180)
