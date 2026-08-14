import os
from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient

load_dotenv()

project_endpoint = os.getenv("PROJECT_ENDPOINT")

project_client = AIProjectClient(
    credential=DefaultAzureCredential(),
    endpoint=project_endpoint
)

openai_client = project_client.get_openai_client(api_version="2024-10-21")

try:
    project_client.connections.list()
    print("Auth/connection successful")
except Exception as e:
    print("Connection failed:", e)