import streamlit as st
from google import genai
from PIL import Image
import base64
from pathlib import Path

# 1. Page Config (Makes it look like an app)
st.set_page_config(page_title="Keith's Scotch Sommelier", page_icon="🥃", layout="wide")

# --- Background image: set one of these (or leave both empty for no background) ---
BACKGROUND_IMAGE_URL = ""   # e.g. "https://example.com/whisky-bar.jpg"
BACKGROUND_IMAGE_PATH = "assets/PXL_20230117_045041805.MP~2.jpg"  # Your background image

def _get_background_css():
    if BACKGROUND_IMAGE_URL:
        url = BACKGROUND_IMAGE_URL
    elif BACKGROUND_IMAGE_PATH and Path(BACKGROUND_IMAGE_PATH).exists():
        with open(BACKGROUND_IMAGE_PATH, "rb") as f:
            data = base64.b64encode(f.read()).decode()
        ext = Path(BACKGROUND_IMAGE_PATH).suffix.lower()
        mime = "image/jpeg" if ext in (".jpg", ".jpeg") else "image/png" if ext == ".png" else "image/webp"
        url = f"data:{mime};base64,{data}"
    else:
        return ""
    return f"""
    <style>
    .stApp {{
        background: linear-gradient(rgba(0,0,0,0.4), rgba(0,0,0,0.4)),
                    url("{url}") center/cover no-repeat fixed;
    }}
    /* Optional: make main content area slightly opaque so it stands out */
    .stApp > div {{ background: rgba(255,255,255,0.92); }}
    </style>
    """

_bg_css = _get_background_css()
if _bg_css:
    st.markdown(_bg_css, unsafe_allow_html=True)

st.title("🥃 Keith's Scotch Sommelier")

# 2. Setup Gemini
# Tip: In a real app, we'd use 'st.secrets' to hide this!
API_KEY = st.secrets["GEMINI_API_KEY"] 
client = genai.Client(api_key=API_KEY)

# 3. The Camera Widget (Works on your phone!)
st.markdown("""
<style>
    /* Make the camera input area stand out */
    div[data-testid="stCameraInput"] {
        border: 3px solid #2563eb;
        border-radius: 16px;
        padding: 1rem;
        background: linear-gradient(145deg, #eff6ff 0%, #dbeafe 100%);
        box-shadow: 0 4px 14px rgba(37, 99, 235, 0.25);
    }
    div[data-testid="stCameraInput"] label {
        font-weight: 700 !important;
        font-size: 1.1rem !important;
        color: #1e40af !important;
    }
</style>
""", unsafe_allow_html=True)
st.markdown("### 📸 Take a photo of the bottle")
st.markdown("Point your camera at the whisky bottle label for the best result.")
img_file_buffer = st.camera_input("Take a photo of the bottle", label_visibility="collapsed")

if img_file_buffer is not None:
    # Open the image for Gemini
    img = Image.open(img_file_buffer)
    
    with st.spinner("Analyzing your scotch..."):
        try:
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=[
                    "Identify this scotch whisky from the bottle image. In your response, use this exact structure and headings:\n\n"
                    "**Scotch:** [name]\n\n"
                    "**Region:** [region]\n\n"
                    "**Primary Tasting Notes:** [2–4 main tasting notes, e.g. smoke, honey, citrus, peat]\n\n"
                    "**Food Pairing:** [suggestion]\n\n"
                    "Keep each section concise.",
                    img
                ]
            )
            
            # 4. Display the Result
            st.success("Analysis Complete!")
            st.markdown(response.text)
            
        except Exception as e:
            st.error(f"Error: {e}")

st.write("Cheers!")
