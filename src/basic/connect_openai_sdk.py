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
  base_url = "https://{resource-name}.openai.azure.com/openai/v1/",  
  api_key=token_provider,
)