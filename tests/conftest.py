"""Shared test scaffolding (pytest auto-discovers this)."""

from collections.abc import Iterable

from simplemma import BaseTokenSampler


class CustomTokenSampler(BaseTokenSampler):
    """A trivial sampler that drops the first `skip_tokens` tokens; used by the
    token-sampler and language-detector tests."""

    def __init__(self, skip_tokens: int) -> None:
        super().__init__()
        self.skip_tokens: int = skip_tokens

    def sample_tokens(self, tokens: Iterable[str]) -> list[str]:
        return list(tokens)[self.skip_tokens :]
