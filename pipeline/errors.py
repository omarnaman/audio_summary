class PipelineError(Exception):
    """Base class for all conversion pipeline errors."""


class AsrServiceError(PipelineError):
    """Raised when the ASR microservice request fails or times out."""


class SummarizationError(PipelineError):
    """Raised when the summarization LLM call fails."""
