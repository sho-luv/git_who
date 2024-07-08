import os
import sys
import asyncio
from openai import AsyncOpenAI
import importlib.util
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("No OPENAI_API_KEY found in environment variables.")

# Check if rich is installed
rich_installed = importlib.util.find_spec('rich') is not None

if rich_installed:
    from rich.console import Console
    from rich import print
    console = Console()
else:
    console = None

# OpenAI client initialization
client = AsyncOpenAI(
    api_key = os.environ["OPENAI_API_KEY"],
)

async def ask_openai(question, context):
    response = await client.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": f"{context}\n\nQuestion: {question}",
            }
        ],
        model="gpt-3.5-turbo",
    )

    # Access the response content correctly
    response_content = response.choices[0].message.content
    
    # Print the response content
    # if console:
    #     console.print(response_content)
    # else:
    #     print(response_content)
    
    return response_content

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Ask OpenAI a question with context.")
    parser.add_argument("question", type=str, help="The question to ask OpenAI.")
    parser.add_argument("context", type=str, help="The context for the question.")

    if len(sys.argv)==1:
        parser.print_help()
        sys.exit(1)

    args = parser.parse_args()

    # Run the ask_openai function with provided arguments
    asyncio.run(ask_openai(args.question, args.context))

