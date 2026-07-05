"""
LLM Explainer Wrapper for OceanInsight AI
Translates highly technical metrics (JSON/arrays) into simple, understandable English for non-experts.

Using Groq (Llama 3)
- Blazing fast free API
- Get key at: https://console.groq.com/
- Install: venv\\Scripts\\python.exe -m pip install groq python-dotenv
"""

import os
import sys
import json
from dotenv import load_dotenv

try:
    from groq import Groq
except ImportError:
    pass # Handled below

class SimpleExplainerLLM:
    def __init__(self, api_key=None):
        if 'groq' not in sys.modules:
            print("Please install the SDK first: \nvenv\\Scripts\\python.exe -m pip install groq python-dotenv")
            sys.exit(1)
            
        load_dotenv() # Load variables from .env
        self.api_key = api_key or os.environ.get("GROQ_API_KEY")
        
        if not self.api_key or self.api_key == "your_groq_api_key_here":
            print("ERROR: GROQ_API_KEY not configured.")
            print("1. Get a free key at https://console.groq.com/")
            print("2. Add it to your .env file: GROQ_API_KEY=gsk_...")
            sys.exit(1)
            
        self.client = Groq(api_key=self.api_key)
        
        # System instruction to force simple, non-technical language
        self.system_instruction = (
            "You are OceanInsight AI, a friendly environmental assistant. "
            "You will receive raw JSON data from our oceanographic ML pipeline (temperatures, anomalies, risk scores). "
            "Your job is to translate this technical data into a short, VERY simple, 1-paragraph summary for a non-technical user. "
            "Do NOT use technical terms like 'recon_error', 'z_npi', or 'MiniBatchKMeans'. Use analogies if helpful. "
            "Keep it brief, clear, and actionable. Conclude with a 1-sentence takeaway."
        )
        
        # Recommended: Llama 3.1 8B or 70B for blazing fast inference
        self.model_name = 'llama-3.1-8b-instant'

    def explain_data(self, raw_json_data: str, context: str = "General Data Overview"):
        """
        Passes raw pipeline JSON outputs to the LLM and asks for a simple explanation.
        """
        prompt = (
            f"Context: {context}\n"
            f"Raw AI Output Data:\n{raw_json_data}\n\n"
            "Please explain what this means in simple terms. What should the user care about here?"
        )
        
        try:
            chat_completion = self.client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": self.system_instruction
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                model=self.model_name,
                temperature=0.3, # Low temp for factual reporting
                max_tokens=256,
            )
            return chat_completion.choices[0].message.content
        except Exception as e:
            return f"[LLM Error] Could not generate explanation: {e}"

# ==========================================
# Example usage bridging the two tools
# ==========================================
if __name__ == "__main__":
    from ocean_agent import OceanInsightTools
    
    print("Loading Ocean Platform Data...")
    tools = OceanInsightTools("data/processed/unified.parquet")
    
    # 1. Fetch raw complex data using our internal tools
    raw_anomaly_data = tools.get_anomalies()
    print("\n--- RAW TECHNICAL OUTPUT ---")
    print(raw_anomaly_data)
    
    # 2. Ask the LLM to explain it simply
    print("\n--- AI SIMPLE EXPLANATION ---")
    explainer = SimpleExplainerLLM()
    simple_text = explainer.explain_data(raw_anomaly_data, context="Recent Ocean Anomalies")
    print(simple_text)
