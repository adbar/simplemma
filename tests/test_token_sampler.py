from typing import Iterable, List

from simplemma import (
    BaseTokenSampler,
    MostCommonTokenSampler,
    RelaxedMostCommonTokenSampler,
)


class CustomTokenSampler(BaseTokenSampler):
    def __init__(self, skip_tokens: int) -> None:
        super().__init__()
        self.skip_tokens: int = skip_tokens

    def sample_tokens(self, tokens: Iterable[str]) -> List[str]:
        return list(tokens)[self.skip_tokens :]


def test_token_sampler():
    sampler = MostCommonTokenSampler()
    assert sampler.sample_text("ABCD Efgh ijkl mn") == ["ijkl"]
    assert sampler.sample_text("Abcd_E Abcde") == ["Abcd", "Abcde"]

    sampler = MostCommonTokenSampler(capitalized_threshold=0)
    assert sampler.sample_text("ABCD Efgh ijkl mn") == ["ABCD", "Efgh", "ijkl"]

    sampler = MostCommonTokenSampler(capitalized_threshold=0, sample_size=1)
    assert sampler.sample_text("Efgh Efgh ijkl mn") == ["Efgh"]

    relaxed = RelaxedMostCommonTokenSampler()
    assert relaxed.sample_text("ABCD Efgh ijkl mn") == ["ABCD", "Efgh", "ijkl"]

    custom = CustomTokenSampler(3)
    assert custom.sample_text("ABCD Efgh ijkl mn") == []
