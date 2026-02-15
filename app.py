import streamlit as st
from google import genai
from PIL import Image

# 1. Page Config (Makes it look like an app)
st.set_page_config(page_title="Scotch Sommelier", page_icon="🥃")
st.title("🥃 Scotch Sommelier")

# 2. Setup Gemini
# Tip: In a real app, we'd use 'st.secrets' to hide this!
API_KEY = st.secrets["GEMINI_API_KEY"] 
client = genai.Client(api_key=API_KEY)

# 3. The Camera Widget (Works on your phone!)
img_file_buffer = st.camera_input("Take a photo of the bottle")

if img_file_buffer is not None:
    # Open the image for Gemini
    img = Image.open(img_file_buffer)
    
    with st.spinner("Analyzing your scotch..."):
        try:
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=["Identify this scotch, its region, and a food pairing.", img]
            )
            
            # 4. Display the Result
            st.success("Analysis Complete!")
            st.markdown(response.text)
            
        except Exception as e:
            st.error(f"Error: {e}")

st.write("Tip: Take the photo in good lighting for the best results!")