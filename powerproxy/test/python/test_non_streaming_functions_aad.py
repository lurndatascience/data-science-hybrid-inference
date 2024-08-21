"""
Script to test the proxy's ability to support response streaming when functions are used.

Tested with openai package version 1.12.0.
"""

from azure.identity import DefaultAzureCredential
from openai import AzureOpenAI
import json

def set_openai_api_key():
    default_credential = DefaultAzureCredential()
    token = default_credential.get_token("https://cognitiveservices.azure.com/.default")
    return token.token

def suggest_book_name():
    functions = [
        {
            "name": "search_books",
            "description": "Find books which are helpful for personal development",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "The name of the book to be searched.",
                    },
                    "summary": {
                        "type": "string",
                        "description": "The full summary of what the book is about.",
                    },
                    "price": {
                        "type": "number",
                        "description": "The price of the book",
                    },
                    "features": {
                        "type": "string",
                        "description": "A comma separated list of features (i.e. hardcover, audiobook, etc.)",
                    },
                },
                "required": ["name", "summary"],
            },
        }
    ]

    messages = [
        {
            "role": "user",
            "content": "Book on How to manage habits.",
        }
    ]

    llm = AzureOpenAI(
        azure_endpoint="http://localhost",
        azure_deployment="gpt-4",
        api_version="2024-02-01",
        azure_ad_token=set_openai_api_key(),
    )

    completion = llm.chat.completions.create(
        model="gpt-4",
        functions=functions,
        messages=messages,
        temperature=0.7,
        max_tokens=800,
        top_p=0.95,
        frequency_penalty=0,
        presence_penalty=0,
        stop=None
    )

    suggested_name = json.loads(completion.choices[0].message.function_call.arguments)['name']
    return suggested_name

# Get a suggested name for the book
suggested_name = suggest_book_name()
print("Suggested name for the book:", suggested_name)
