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

        response_ids = []

        print("Assistant: Enter a prompt (or type 'quit' to exit)")
        while True:
            input_text = input('\nYou: ')
            if input_text.lower() == "quit":
                print("Assistant: Goodbye!")
                break
            if len(input_text) == 0:
                print("Please enter a prompt.")
                continue

            stream = openai_client.responses.create(
                model=model_deployment,
                input=input_text,
                previous_response_id=response_ids[-1] if response_ids else None,
                stream=True
            )

            print("\nAssistant: ", end="")
            for event in stream:
                if event.type == "response.output_text.delta":
                    print(event.delta, end="", flush=True)
                elif event.type == "response.completed":
                    response_ids.append(event.response.id)

            print(f"\nResponse ID: {response_ids[-1]}")

    except Exception as ex:
        print(ex)


if __name__ == '__main__':
    main()