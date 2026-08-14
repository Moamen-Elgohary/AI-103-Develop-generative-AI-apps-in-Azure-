## Model Parameters

response = openai_client.responses.create(
    model=model_deployment,
    instructions="You are a helpful AI assistant that answers questions clearly and concisely in no more than 8 words.",
    input="Explain neural networks.",
    temperature=0.8,                     # Randomness of output, 0-2 (higher = more creative/random)
    top_p=1.0,                           # Nucleus sampling alt to temperature (usually adjust one, not both)
    max_output_tokens=100,               # Max length of the generated response
    stream=False,                        # If True, streams tokens as they're generated
    tools=[],                            # List of tool/function definitions the model can call
    tool_choice="auto",                  # Controls tool use: "auto", "none", or force a specific tool
    previous_response_id=None,           # ID of a prior response to continue a multi-turn conversation
    reasoning={"effort": "medium"},      # Controls reasoning depth (for reasoning-capable models)
    text={"format": {"type": "text"}},   # Output formatting, e.g. plain text or structured JSON schema
    truncation="auto"                    # How to handle input exceeding context: "auto" or "disabled"
)

## Response ID tracking

response_ids = []

response = openai_client.responses.create(
        model=model_deployment,
        instructions="You are a helpful AI assistant that explains technology concepts clearly.",
        input=input_text,
        previous_response_id=response_ids[-1] if response_ids else None
)

response_ids.append(response.id)

## Retrieving a previous response

try:
    response_id = "resp_67cb61fa3a448190bcf2c42d96f0d1a8"  # Example ID
    previous_response = openai_client.responses.retrieve(response_id)
    print(f"Previous response: {previous_response.output_text}")

except Exception as ex:
    print(f"Error: {ex}")

## Streaming

stream = openai_client.responses.create(
    model=model_deployment,
    input="Write a short story about a robot learning to paint.",
    stream=True
)
for event in stream:
    print(event, end="", flush=True)