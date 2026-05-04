"""Santiago's Swim Scout — Streamlit frontend."""
import httpx
import streamlit as st

BACKEND_URL = st.secrets.get("BACKEND_URL", "http://localhost:8000")

st.set_page_config(
    page_title="Santiago's Swim Scout",
    page_icon="🏊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
    .block-container { padding-top: 2rem; }
    .status-badge {
        display: inline-block;
        font-size: 1.4rem;
        font-weight: 700;
        padding: 0.4rem 1.2rem;
        border-radius: 2rem;
        margin-bottom: 1rem;
    }
    .badge-green  { background: #d4edda; color: #155724; }
    .badge-yellow { background: #fff3cd; color: #856404; }
    .badge-red    { background: #f8d7da; color: #721c24; }
    .agent-header { font-size: 1.05rem; font-weight: 600; margin-bottom: 0.5rem; }
</style>
""", unsafe_allow_html=True)


@st.cache_data(ttl=3600)
def fetch_locations() -> list[dict]:
    try:
        resp = httpx.get(f"{BACKEND_URL}/locations", timeout=10.0)
        resp.raise_for_status()
        return resp.json()["locations"]
    except Exception as e:
        st.error(f"Could not reach backend: {e}")
        return []


def detect_status(coaching: str) -> tuple[str, str]:
    """Return (badge_class, label) from the coach's overall status line."""
    text = coaching.upper()
    if "NO-GO" in text or "🔴" in coaching:
        return "badge-red", "🔴 NO-GO"
    if "CAUTION" in text or "🟡" in coaching:
        return "badge-yellow", "🟡 CAUTION"
    if "GO" in text or "🟢" in coaching:
        return "badge-green", "🟢 GO"
    return "badge-yellow", "🟡 UNKNOWN"


# ── Header ───────────────────────────────────────────────────────────────────
st.title("🏊 Santiago's Swim Scout")
st.caption("An AI crew that evaluates open water swimming conditions in real time.")
st.divider()

# ── Location picker ───────────────────────────────────────────────────────────
locations = fetch_locations()
if not locations:
    st.stop()

options = {loc["display"]: loc["key"] for loc in locations}

col_pick, col_btn = st.columns([4, 1])
with col_pick:
    selected_display = st.selectbox("Select a location", list(options.keys()), label_visibility="collapsed")
with col_btn:
    scout_clicked = st.button("🔍 Scout It", type="primary", use_container_width=True)

st.divider()

# ── Scout run ─────────────────────────────────────────────────────────────────
if scout_clicked:
    location_key = options[selected_display]

    with st.spinner(f"Crew deploying to {selected_display}…"):
        try:
            resp = httpx.post(
                f"{BACKEND_URL}/scout",
                json={"location": location_key},
                timeout=180.0,
            )
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPStatusError as e:
            st.error(f"Backend error {e.response.status_code}: {e.response.text}")
            st.stop()
        except Exception as e:
            st.error(f"Could not reach backend: {e}")
            st.stop()

    coaching = data.get("coaching", "")
    badge_class, badge_label = detect_status(coaching)

    # Overall status badge
    st.markdown(
        f'<div class="status-badge {badge_class}">{badge_label}</div>',
        unsafe_allow_html=True,
    )
    st.subheader(selected_display)
    st.divider()

    # Three agent tabs
    tab_data, tab_safety, tab_coach = st.tabs([
        "📡 Data Fetcher",
        "🛡️ Safety Officer",
        "🏅 Coach",
    ])

    with tab_data:
        st.markdown(data["conditions"]["summary"])
        with st.expander("Raw sensor data"):
            st.json(data["conditions"]["raw_data"])

    with tab_safety:
        st.markdown(data["safety"]["summary"])
        with st.expander("Raw safety data"):
            st.json(data["safety"]["raw_data"])

    with tab_coach:
        st.markdown(coaching)
