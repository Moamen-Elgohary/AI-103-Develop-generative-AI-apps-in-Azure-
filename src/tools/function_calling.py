import os
import time
from dotenv import load_dotenv
from openai import OpenAI
from azure.identity import DefaultAzureCredential, get_bearer_token_provider


def get_time():
    return f"The time is {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}"


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

        function_tools = [
            {
                "type": "function",
                "name": "get_time",
                "description": "Get the current time"
            }
        ]

        messages = [
            {"role": "developer", "content": "You are an AI assistant that provides information."}
        ]

        print("Assistant: Enter a prompt (or type 'quit' to exit)")
        while True:
            prompt = input("\nYou: ")
            if prompt.lower() == "quit":
                print("Assistant: Goodbye!")
                break

            messages.append({"role": "user", "content": prompt})

            response = openai_client.responses.create(
                model=model_deployment,
                input=messages,
                tools=function_tools
            )

            messages += response.output

            for item in response.output:
                if item.type == "function_call" and item.name == "get_time":
                    current_time = get_time()
                    messages.append({
                        "type": "function_call_output",
                        "call_id": item.call_id,
                        "output": current_time
                    })

                    response = openai_client.responses.create(
                        model=model_deployment,
                        instructions="Answer only with the tool output.",
                        input=messages,
                        tools=function_tools
                    )

            print(response.output_text)

    except Exception as ex:
        print(ex)


if __name__ == '__main__':
    main()