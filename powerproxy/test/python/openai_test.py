"""
Script to test the proxy's ability to support response streaming.

Tested with openai package version 1.12.0.
"""
from azure.identity import DefaultAzureCredential
from openai.lib.azure import AzureOpenAI


def set_openai_api_key():
    default_credential = DefaultAzureCredential()
    token = default_credential.get_token("https://cognitiveservices.azure.com/.default")
    return token.token


llm = AzureOpenAI(
    azure_endpoint="http://localhost",
    azure_deployment="gpt-4",
    api_version="2024-02-01",
    azure_ad_token=set_openai_api_key(),
)

messages=[
        {
            "role": "system",
            "content": "You are an AI assistant that helps people find information.",
        },
        {"role": "user", "content": "Tell me a joke!"},
        {
            "role": "assistant",
            "content": "Why did the tomato turn red? Because it saw the salad dressing!",
        },
        {"role": "user", "content": "Yeah, that's a great one."},
    ]

response = llm.chat.completions.create(
        model="gpt-4",
        messages=messages,
        stream=True,
    )

for chunk in response:
    print(chunk)
