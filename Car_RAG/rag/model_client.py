import os
from groq import Groq, RateLimitError

client = Groq(api_key=os.environ["GROQ_API_KEY"])

MODELS = [
    "qwen/qwen3.8-27b",
]


def chat_completion(**kwargs):
    last_error = None

    # הסרת המודל שהועבר מהקוד הקורא
    kwargs.pop("model", None)

    for model in MODELS:
        try:
            return client.chat.completions.create(
                model=model,
                **kwargs
            )

        except RateLimitError as e:
            last_error = e
            print(f"Rate limit reached for {model}. Trying next model.")

    raise last_error