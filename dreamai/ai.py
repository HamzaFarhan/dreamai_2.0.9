from enum import Enum

import litellm
import tiktoken
from dsp.modules.lm import LM as DSPyLM
from tenacity import Retrying, stop_after_attempt, wait_random

litellm.drop_params = True


class ModelName(str, Enum):
    GPT_3 = "gpt-3.5-turbo"
    GPT_4 = "gpt-4-turbo-preview"
    HAIKU = "claude-3-haiku-20240307"
    SONNET = "claude-3-sonnet-20240229"
    OPUS = "claude-3-opus-20240229"
    GEMINI = "gemini/gemini-pro"
    MISTRAL = "anyscale/mistralai/Mistral-7B-Instruct-v0.1"
    MIXTRAL = "anyscale/mistralai/Mixtral-8x7B-Instruct-v0.1"


MODEL = ModelName.GPT_3


def dspy_prompt(lm: DSPyLM) -> str:
    n = 1
    skip = 0
    provider: str = lm.provider
    last_prompt = None
    printed = []
    n = n + skip
    for x in reversed(lm.history[-100:]):
        prompt = x["prompt"]
        if prompt != last_prompt:
            if provider == "clarifai" or provider == "google":
                printed.append(
                    (
                        prompt,
                        x["response"],
                    ),
                )
            else:
                printed.append(
                    (
                        prompt,
                        x["response"].generations
                        if provider == "cohere"
                        else x["response"]["choices"],
                    ),
                )
        last_prompt = prompt
        if len(printed) >= n:
            break
    history_str = ""
    for idx, (prompt, choices) in enumerate(reversed(printed)):
        if (n - idx - 1) < skip:
            continue
        history_str += prompt
        text = ""
        if provider == "cohere":
            text = choices[0].text
        elif provider == "openai" or provider == "ollama":
            text = " " + lm._get_choice_text(choices[0]).strip()
        elif provider == "clarifai":
            text = choices
        elif provider == "google":
            text = choices[0].parts[0].text
        else:
            text = choices[0]["text"]
        history_str += text
        if len(choices) > 1:
            history_str += f" \t (and {len(choices)-1} other completions)"
    return history_str


def count_gpt_tokens(text: str, model: ModelName = MODEL) -> int:
    encoding = tiktoken.encoding_for_model(model)
    return len(encoding.encode(text))


def chat_message(role: str, content: str) -> dict[str, str]:
    return {"role": role, "content": content}


def system_message(content: str) -> dict[str, str]:
    return chat_message(role="system", content=content)


def user_message(content: str) -> dict[str, str]:
    return chat_message(role="user", content=content)


def assistant_message(content: str) -> dict[str, str]:
    return chat_message(role="assistant", content=content)


def oai_response(response) -> str:
    try:
        return response.choices[0].message.content
    except Exception:
        return response


def ai_retry_attempts(attempts: int = 3):
    return (
        Retrying(wait=wait_random(min=1, max=40), stop=stop_after_attempt(attempts))
        if attempts > 1
        else 1
    )
