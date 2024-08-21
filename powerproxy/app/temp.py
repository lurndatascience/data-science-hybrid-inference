"""
Script to test the proxy's ability to support response streaming.

Tested with openai package version 1.12.0.
"""
from azure.identity import DefaultAzureCredential
from openai.lib.azure import AzureOpenAI


def set_openai_api_key():
    default_credential = DefaultAzureCredential()
    token = default_credential.get_token("https://cognitiveservices.azure.com/.default")
    print(token)
    return token.token


llm = AzureOpenAI(
    azure_endpoint="http://localhost",
    azure_deployment="llama3",
    api_version="2024-02-01",
    azure_ad_token="eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJhdWQiOiJodHRwczovL2NvZ25pdGl2ZXNlcnZpY2VzLmF6dXJlLmNvbS8iLCJpc3MiOiJodHRwczovLmxvZ2luLm1pY3Jvc29mdG9ubGluZS5jb20vIiwic3ViIjoiMTIzNDU2Nzg5MDEyMzQ1NiIsIm5hbWUiOiJKb2UgU21pdGgiLCJleHAiOjE2MzA5MjQ0MDAsImlhdCI6MTYzMDkxNzIwMH0.rwNRfJkeIunvKJ5rT3z4UFAI54fWzzhBoHYjUgUg84j9RyqlXef2PqL5RbL1Q2r2eW8d1B6vhEuZkVfknZQmnl-pLMLhtfTfUve8N8GzUJ9UO5Ri5kAqHL1wD4JcczkGz6tGpKQhIhCRhLLGplv6mJxxQW3-Pv5zZTif9aM29_GM",
    # api_key="sk-xx"
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
        model="llama3",
        messages=messages,
        stream=True,
    )

for chunk in response:
    print(chunk)
