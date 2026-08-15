import os
from dotenv import load_dotenv
from openai import OpenAI
from azure.identity import DefaultAzureCredential, get_bearer_token_provider


def main():
    os.system('cls' if os.name == 'nt' else 'clear')

    try:
        load_dotenv()
        azure_openai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        model_deployment = os.getenv("MODEL_DEPLOYMENT")

        token_provider = get_bearer_token_provider(
            DefaultAzureCredential(), "https://ai.azure.com/.default"
        )

        openai_client = OpenAI(
            base_url=azure_openai_endpoint,
            api_key=token_provider
        )

        # Get response using the code_interpreter tool
        response = openai_client.responses.create(
            model=model_deployment,
            instructions="You are an AI assistant that provides information. Use the python tool to run code for math problems.",
            input="What is the square root of 16?",
            tools=[{"type": "code_interpreter", "container": {"type": "auto"}}]
        )
        print(response.output_text)

    except Exception as ex:
        print(ex)


if __name__ == '__main__':
    main()