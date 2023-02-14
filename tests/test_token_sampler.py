from typing import List

from simplemma.tokenizer import Tokenizer

from simplemma.language_detector import TokenSampler, RELAXED_SPLIT_INPUT


class CustomTokenSampler(TokenSampler):
    def __init__(self, skip_tokens: int) -> None:
        super().__init__()
        self.skip_tokens: int = skip_tokens

    def sample_tokens(self, text: str) -> List[str]:
        return list(self.tokenizer.split_text(text))[self.skip_tokens :]


def test_token_sampler():
    sampler = TokenSampler()
    assert sampler.sample_tokens("ABCD Efgh ijkl mn") == ["ijkl"]
    assert sampler.sample_tokens("Abcd_E Abcde") == ["Abcd", "Abcde"]

    sampler = TokenSampler(capitalized_threshold=0)
    assert sampler.sample_tokens("ABCD Efgh ijkl mn") == ["ABCD", "Efgh", "ijkl"]

    sampler = TokenSampler(capitalized_threshold=0, max_tokens=1)
    assert sampler.sample_tokens("Efgh Efgh ijkl mn") == ["Efgh"]

    relaxed = TokenSampler(
        tokenizer=Tokenizer(splitting_regex=RELAXED_SPLIT_INPUT),
        max_tokens=1000,
        capitalized_threshold=0,
    )
    assert relaxed.sample_tokens("ABCD Efgh ijkl mn") == ["ABCD", "Efgh", "ijkl"]

    custom = CustomTokenSampler(3)
    assert custom.sample_tokens("ABCD Efgh ijkl mn") == []
