from google import genai

# Use your actual API key here
client = genai.Client(api_key="AIzaSyDxMP8PDQb8jyCHXi1ezuzqIpsX-uN9WPc")

response = client.models.generate_content(
    model="gemini-2.0-flash", 
    contents="Give me a one-sentence fun fact about scotch."
)

print(response.text)