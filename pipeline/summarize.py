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

MAP_PROMPT = (
    "You are summarizing part {index} of {total} of a longer meeting/conversation transcript. "
    "Write a detailed, well-structured summary of ONLY this segment in Markdown format, including "
    "timestamps for key events or topics discussed.\n"
    "This is a partial excerpt, not the whole conversation - do not write an overall introduction, "
    "conclusion, or title, just capture what happens in this segment.\n\n"
    "Transcript segment:\n"
    "{transcript}"
)

REDUCE_PROMPT = (
    "You are given a series of section-by-section summaries covering an entire meeting/conversation "
    "transcript, in chronological order. Combine them into a single, comprehensive, well-structured "
    "summary in Markdown format, including timestamps for key events or topics discussed. Merge "
    "redundant or overlapping information across sections into one coherent narrative.\n"
    "Ensure the very first line of your response is a top-level markdown heading containing a "
    "suitable title for this summary, for example:\n"
    "# Detailed Summary of the Discussion\n"
    "Do not put any other text before the title.\n\n"
    "Section summaries:\n"
    "{sections}"
)


@dataclass
class SummaryResult:
    markdown: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


def _complete(client: OpenAI, cfg: Config, prompt: str) -> SummaryResult:
    try:
        response = client.chat.completions.create(
            model=cfg.ai_model,
            messages=[{"role": "user", "content": prompt}],
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


def _chunk_transcript(transcript_text: str, max_chunk_chars: int) -> list[str]:
    """Split a transcript into chunks on line boundaries, each within max_chunk_chars.

    Transcript lines are individual diarized utterances (e.g. "[00:00:00 - 00:00:08]
    SPEAKER_00: ..."), so splitting on line boundaries never cuts an utterance in half.
    """
    lines = transcript_text.splitlines()
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0

    for line in lines:
        line_len = len(line) + 1
        if current and current_len + line_len > max_chunk_chars:
            chunks.append("\n".join(current))
            current = []
            current_len = 0
        current.append(line)
        current_len += line_len

    if current:
        chunks.append("\n".join(current))

    return chunks


def summarize(transcript_text: str, cfg: Config) -> SummaryResult:
    client = OpenAI(base_url=cfg.ai_base_url, api_key=cfg.ai_api_key)

    chunks = _chunk_transcript(transcript_text, cfg.ai_summary_chunk_chars)
    if len(chunks) <= 1:
        return _complete(client, cfg, PROMPT.format(transcript=transcript_text))

    # Map: summarize each chunk independently so no single LLM call has to prefill
    # the whole transcript at once - this bounds peak prefill memory regardless of
    # how long the source recording is.
    section_summaries: list[str] = []
    prompt_tokens = completion_tokens = total_tokens = 0
    for index, chunk in enumerate(chunks, start=1):
        result = _complete(client, cfg, MAP_PROMPT.format(index=index, total=len(chunks), transcript=chunk))
        section_summaries.append(result.markdown)
        prompt_tokens += result.prompt_tokens
        completion_tokens += result.completion_tokens
        total_tokens += result.total_tokens

    # Reduce: merge the section summaries (much shorter than the raw transcript)
    # into one final summary in a single call.
    sections = "\n\n".join(f"### Section {i}\n{s}" for i, s in enumerate(section_summaries, start=1))
    final = _complete(client, cfg, REDUCE_PROMPT.format(sections=sections))

    return SummaryResult(
        markdown=final.markdown,
        prompt_tokens=prompt_tokens + final.prompt_tokens,
        completion_tokens=completion_tokens + final.completion_tokens,
        total_tokens=total_tokens + final.total_tokens,
    )
