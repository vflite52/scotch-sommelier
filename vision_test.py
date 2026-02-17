from google import genai
from PIL import Image
import os

# 1. Setup
client = genai.Client(api_key="AIzaSyDxMP8PDQb8jyCHXi1ezuzqIpsX-uN9WPc")
image_path = "uploads/bottle.jpg" # Place your photo here!

if os.path.exists(image_path):
    print(f"Found {image_path}! Asking the Sommelier...")
    
    # 2. Open and Analyze
    raw_image = Image.open(image_path)
    
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=[
            "You are a master scotch sommelier. Identify this bottle, "
            "tell me its region, and suggest one food pairing.", 
            raw_image
        ]
    )
    
    print("-" * 30)
    print(response.text)
else:
    print(f"I don't see a photo at {image_path} yet.")
    print("Please drop a photo named 'bottle.jpg' into your 'uploads' folder!")

    # 4. Save the review to your Digital Journal
with open("my_scotch_journal.txt", "a") as journal:
    journal.write(f"\n--- New Entry ---\n")
    journal.write(response.text)
    journal.write("\n" + "="*30 + "\n")

print("Review saved to my_scotch_journal.txt!")