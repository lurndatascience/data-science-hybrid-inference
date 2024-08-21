import uvicorn
from azure.identity import DefaultAzureCredential
from fastapi import FastAPI
from pydantic import BaseModel
from openai import AzureOpenAI

app = FastAPI()


class Prompt(BaseModel):
    prompt: str


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

@app.post("/chat_completions")
async def generate_essay(prompt: Prompt):
    """
    Script to test the proxy's support for requests responding with a one-time response.

    Tested with openai package version 1.12.0.
    """

    messages = [
        {
            "role": "system",
            "content": "You are an AI assistant that helps people find information.",
        },
        {"role": "user", "content": "Tell me a joke!"},
        {
            "role": "assistant",
            "content": "Why did the tomato turn red? Because it saw the salad dressing!",
        },
        {"role": "user", "content": prompt.prompt},
    ]

    completion = llm.chat.completions.create(
        model="gpt-4",
        messages=messages,
        temperature=0.7,
        max_tokens=800,
        top_p=0.95,
        frequency_penalty=0,
        presence_penalty=0,
        stop=None
    )
    print(completion.choices[0].message.content)

    return {"response": completion.choices[0].message.content}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)