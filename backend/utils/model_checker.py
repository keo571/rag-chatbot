"""
Utility script to check model availability and test basic functionality.
This script helps verify API keys and model access before running the main application.
"""

import os
from typing import List, Dict, Any
from dotenv import load_dotenv
import google.generativeai as genai
from langchain_google_genai import GoogleGenerativeAI

# Load environment variables
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

class ModelChecker:
    def __init__(self, api_key: str = None):
        """Initialize the model checker with optional API key."""
        self.api_key = api_key or GOOGLE_API_KEY
        if not self.api_key:
            raise ValueError("No API key provided. Set GOOGLE_API_KEY in .env file or pass it directly.")
        
        genai.configure(api_key=self.api_key)

    def list_available_models(self) -> List[Dict[str, Any]]:
        """Get a list of all available models and their basic information."""
        try:
            models = genai.list_models()
            return [
                {
                    "name": model.name,
                    "description": model.description,
                    "input_token_limit": model.input_token_limit,
                    "output_token_limit": model.output_token_limit,
                    "supported_generation_methods": model.supported_generation_methods,
                }
                for model in models
            ]
        except Exception as e:
            print(f"Error listing models: {str(e)}")
            return []

    def test_model(self, model_name: str = "gemini-1.5-pro") -> Dict[str, Any]:
        """Test a specific model with a simple prompt."""
        try:
            model = GoogleGenerativeAI(
                model=model_name,
                google_api_key=self.api_key,
                temperature=0.7
            )
            
            response = model.invoke("Say hello and introduce yourself briefly.")
            
            return {
                "status": "success",
                "model": model_name,
                "response": response,
            }
        except Exception as e:
            return {
                "status": "error",
                "model": model_name,
                "error": str(e)
            }

def main():
    """Main function to run model availability checks."""
    try:
        checker = ModelChecker()
        
        # List all available models
        print("\n=== Available Models ===")
        models = checker.list_available_models()
        for model in models:
            print(f"\nModel: {model['name']}")
            print(f"Description: {model['description']}")
            print(f"Input token limit: {model['input_token_limit']}")
            print(f"Output token limit: {model['output_token_limit']}")
            print("Supported methods:", ", ".join(model['supported_generation_methods']))
        
        # Test specific models
        test_models = ["gemini-1.5-pro", "gemini-1.5-flash"]
        print("\n=== Model Tests ===")
        for model_name in test_models:
            print(f"\nTesting {model_name}...")
            result = checker.test_model(model_name)
            if result["status"] == "success":
                print("✓ Success!")
                print(f"Response: {result['response']}")
            else:
                print("✗ Failed!")
                print(f"Error: {result['error']}")

    except Exception as e:
        print(f"\n❌ Setup Error: {str(e)}")
        print("Please check your API key and internet connection.")

if __name__ == "__main__":
    main() 