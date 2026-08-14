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

        conversation_history = []

        print("Assistant: Enter a prompt (or type 'quit' to exit)")
        while True:
            input_text = input('\nYou: ')
            if input_text.lower() == "quit":
                print("Assistant: Goodbye!")
                break
            if len(input_text) == 0:
                print("Please enter a prompt.")
                continue

            conversation_history.append({
                "type": "message",
                "role": "user",
                "content": input_text
            })

            response = openai_client.responses.create(
                model=model_deployment,
                input=conversation_history
            )

            print(f"\nAssistant: {response.output_text}")
            print(f"Response ID: {response.id}")
            print(f"Tokens used: {response.usage.total_tokens}")
            print(f"Status: {response.status}")

            conversation_history += response.output

    except Exception as ex:
        print(ex)


if __name__ == '__main__':
    main()