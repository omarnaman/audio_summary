from dataclasses import dataclass

from openai import OpenAI

from config import Config
from pipeline.errors import SummarizationError

PROMPT = (
    "Please read the attached meeting/conversation transcript. Write a comprehensive, "
    "well-structured summary of it in Markdown format, including timestamps for key events "
    "or topics discussed.\n"
    "Ensure the very first line of your response is a top-level markdown heading containing "
    "a suitable title for this summary, for example:\n"
    "# Detailed Summary of the Discussion\n"
    "Do not put any other text before the title.\n\n"
    "Transcript:\n"
    "{transcript}"
)


@dataclass
class SummaryResult:
    markdown: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


def summarize(transcript_text: str, cfg: Config) -> SummaryResult:
    client = OpenAI(base_url=cfg.ai_base_url, api_key=cfg.ai_api_key)

    try:
        response = client.chat.completions.create(
            model=cfg.ai_model,
            messages=[{"role": "user", "content": PROMPT.format(transcript=transcript_text)}],
        )
    except Exception as e:
        raise SummarizationError(f"Summarization request failed: {e}") from e

    markdown = response.choices[0].message.content
    if not markdown:
        raise SummarizationError("Summarization endpoint returned an empty response")

    prompt_tokens = 0
    completion_tokens = 0
    total_tokens = 0
    if response.usage:
        prompt_tokens = response.usage.prompt_tokens or 0
        completion_tokens = response.usage.completion_tokens or 0
        total_tokens = response.usage.total_tokens or 0

    return SummaryResult(
        markdown=markdown,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
    )
