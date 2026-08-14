import os
import asyncio
from dotenv import load_dotenv
from openai import AsyncOpenAI
from azure.identity import DefaultAzureCredential, get_bearer_token_provider


async def main():
    os.system('cls' if os.name == 'nt' else 'clear')

    try:
        load_dotenv()
        azure_openai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        model_deployment = os.getenv("MODEL_DEPLOYMENT")

        token_provider = get_bearer_token_provider(
            DefaultAzureCredential(), "https://ai.azure.com/.default"
        )

        openai_client = AsyncOpenAI(
            base_url=azure_openai_endpoint,
            api_key=token_provider
        )

        response = await openai_client.responses.create(
            model=model_deployment,
            input="Explain quantum computing briefly."
        )

        print(f"Response: {response.output_text}")
        print(f"Response ID: {response.id}")
        print(f"Tokens used: {response.usage.total_tokens}")
        print(f"Status: {response.status}")

    except Exception as ex:
        print(ex)


if __name__ == '__main__':
    asyncio.run(main())