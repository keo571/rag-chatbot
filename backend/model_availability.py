import os
from dotenv import load_dotenv
import google.generativeai as genai

# API key loaded from environment variables
load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# # List available models
# models = genai.list_models()
# for model in models:
#     print(model.name)

# Test the model
model = genai.GenerativeModel('gemini-1.5-flash')
response = model.generate_content("Hello, Gemini!")
print(response.text)