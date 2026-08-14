import os
from dotenv import load_dotenv
from openai import OpenAI
from azure.identity import DefaultAzureCredential, get_bearer_token_provider

load_dotenv()

azure_openai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")

token_provider = get_bearer_token_provider(
    DefaultAzureCredential(), "https://ai.azure.com/.default"
)

openai_client = OpenAI(  
  base_url = os.getenv("AZURE_OPENAI_BASE_URL"),  
  api_key=token_provider(),
)

try:
    models = openai_client.models.list()
    print("Connection successful. Available models:")
    for m in models:
        print("-", m.id)
except Exception as e:
    print("Connection failed:", e)
