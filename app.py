import streamlit as st
from google import genai
from PIL import Image
from pathlib import Path

# 1. Page Config (Makes it look like an app)
st.set_page_config(page_title="Keith's Scotch Sommelier", page_icon="🥃", layout="wide")

# Global styling inspired by dim, leather-and-velvet whiskey bars
st.markdown("""
<style>
/* App background and typography */
.stApp {
    background: radial-gradient(circle at top left, #2b1a12 0, #080608 45%, #050308 100%);
    color: #f8e9d8;
    font-family: "Georgia", "Times New Roman", serif;
}

/* Sidebar */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #151016 0%, #050308 100%);
    border-right: 1px solid rgba(248, 233, 216, 0.12);
}

/* Titles */
h1, h2, h3, h4 {
    color: #f8e9d8;
    letter-spacing: 0.04em;
}

/* Buttons */
.stButton > button {
    background: linear-gradient(135deg, #c88a3d, #8a5a1f);
    color: #1b0f09;
    border-radius: 999px;
    border: 1px solid rgba(255, 210, 150, 0.6);
    box-shadow: 0 0 0 1px rgba(0, 0, 0, 0.6), 0 8px 24px rgba(0, 0, 0, 0.65);
    font-weight: 600;
}
.stButton > button:hover {
    background: linear-gradient(135deg, #e2a857, #a26524);
    box-shadow: 0 10px 28px rgba(0, 0, 0, 0.8);
}

/* Status messages in warmer, intimate frames */
div[data-testid="stSuccess"], div[data-testid="stWarning"], div[data-testid="stError"] {
    border-radius: 12px;
    border: 1px solid rgba(255, 210, 150, 0.35);
    background-color: rgba(18, 10, 5, 0.95);
}

/* Response section titles (Scotch, Region, The Nose, etc.) pop from body text */
.stMarkdown strong {
    color: #d9a441;
    font-size: 1.1em;
    letter-spacing: 0.04em;
    font-weight: 700;
}
</style>
""", unsafe_allow_html=True)

# Image shown at the bottom after a successful bottle scan
BOTTOM_IMAGE_PATH = "assets/PXL_20230117_045041805.MP~2.jpg"

st.title("🥃 Keith's Scotch Sommelier")
st.markdown(
    "_An intimate, low-lit guide to choosing your next dram._"
)

left_col, right_col = st.columns([1.1, 1.2])

# 2. Setup Gemini
# Tip: In a real app, we'd use 'st.secrets' to hide this!
API_KEY = st.secrets["GEMINI_API_KEY"] 
client = genai.Client(api_key=API_KEY)

# 3. The Tasting Room layout + Camera Widget (Works on your phone!)
with left_col:
    st.markdown("### The Tasting Room")
    st.markdown(
        "Think of this like your favorite whiskey bar—warm light, worn leather, "
        "and a bartender who actually knows what’s on the back bar."
    )
    st.markdown(
        "- **Step 1**: Hold the label in soft, even light.\n"
        "- **Step 2**: Fill most of the frame with the bottle.\n"
        "- **Step 3**: Let your digital sommelier handle the rest."
    )

with right_col:
    st.markdown("""
    <style>
        /* Camera input panel styled like a back-bar spotlight */
        div[data-testid="stCameraInput"] {
            border: 2px solid rgba(248, 233, 216, 0.35);
            border-radius: 20px;
            padding: 1.25rem;
            background: radial-gradient(circle at top left,
                        rgba(29, 46, 40, 0.98) 0%,
                        rgba(10, 12, 16, 0.98) 55%,
                        rgba(5, 6, 10, 1) 100%);
            box-shadow: 0 18px 45px rgba(0, 0, 0, 0.85),
                        0 0 0 1px rgba(0, 0, 0, 0.9);
        }
        div[data-testid="stCameraInput"] label {
            font-weight: 700 !important;
            font-size: 1.05rem !important;
            letter-spacing: 0.08em !important;
            text-transform: uppercase;
            color: #f8e9d8 !important;
        }
    </style>
    """, unsafe_allow_html=True)
    st.markdown("### 📸 Capture the bottle")
    st.markdown(
        "Point your camera at the whisky label, as if you’re showing it across the bar "
        "to a trusted bartender."
    )
    img_file_buffer = st.camera_input("Take a photo of the bottle", label_visibility="collapsed")

if img_file_buffer is not None:
    # Open the image for Gemini
    img = Image.open(img_file_buffer)
    
    with st.spinner("Analyzing your scotch..."):
        try:
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=[
                    "Look at this bottle image and determine if it is a scotch whisky.\n\n"
                    "IF it IS scotch whisky, respond with this exact structure:\n\n"
                    "**Scotch:** [name]\n\n"
                    "**Region:** [region]\n\n"
                    "**The Nose:** [aroma-focused notes, 2–4 key impressions]\n\n"
                    "**The Palate:** [flavor and texture on the tongue, 2–4 key impressions]\n\n"
                    "**The Finish:** [how the flavor lingers, 2–4 key impressions]\n\n"
                    "**Food Pairing:** [Provide ONE detailed food pairing recommendation including the specific dish, why it complements the scotch's flavor profile, and any preparation notes. Focus on a single, well-explained pairing, not a list.]\n\n"
                    "**Skill Level:** [Choose one: Beginners, Novices, or Experienced. Consider the scotch's complexity, intensity, and typical drinker preferences.]\n\n"
                    "Keep each section concise but informative.\n\n"
                    "IF it is NOT scotch whisky, respond with ONLY this exact message (nothing else):\n\n"
                    "That's not scotch! Put that down immediately and go pour yourself a proper drink! SMH.",
                    img
                ]
            )
            
            # 4. Display the Result
            response_text = response.text.strip()
            
            # Check if it's the non-scotch message
            if "That's not scotch!" in response_text:
                st.warning(response_text)
                st.markdown(
                    '<div style="text-align: center; margin-top: 1rem;">'
                    '<img src="https://c.tenor.com/19455666.gif" '
                    'alt="Disappointed head shake" style="max-width: 300px;">'
                    '</div>',
                    unsafe_allow_html=True
                )
            else:
                st.success("Analysis Complete!")
                st.markdown(response_text)
                st.write("Cheers!")
                if Path(BOTTOM_IMAGE_PATH).exists():
                    st.image(BOTTOM_IMAGE_PATH, use_container_width=True)
            
        except Exception as e:
            st.error(f"Error: {e}")
