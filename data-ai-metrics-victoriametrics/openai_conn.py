import logging
import os
from time import sleep
from dotenv import load_dotenv
load_dotenv()

from openai import OpenAI

from traceloop.sdk import Traceloop
from traceloop.sdk.decorators import workflow


Traceloop.init(app_name="random_joke_generator")

client = OpenAI(
    api_key=os.environ.get("OPENAI_API_KEY"),
    base_url="https://api.openai.com/v1/",
)

@workflow("generate_joke")
def get_random_joke():
    print("Inside Completion")
    completion = client.chat.completions.create(
        model="gpt-5-mini",
        messages=[
            { "role": "system", "content": "You are a stand up comedian" },
            { "role": "user", "content": "Tell me a random joke" },
        ],
    )
    print(f"Response {completion.choices[0].message.content}")
    return completion.choices[0].message.content

if __name__ == "__main__":
    while True:
        joke = get_random_joke()
        logging.info(f'\n---\n{joke}\n---\n')
        sleep(10)