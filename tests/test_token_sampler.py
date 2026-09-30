from simplemma import (
    MostCommonTokenSampler,
    RelaxedMostCommonTokenSampler,
)

from .conftest import CustomTokenSampler


def test_token_sampler() -> None:
    sampler = MostCommonTokenSampler()
    assert sampler.sample_text("Abcd_E Abcde") == ["Abcd", "Abcde"]

    sampler = MostCommonTokenSampler(capitalized_threshold=0)
    assert sampler.sample_text("ABCD Efgh ijkl mn") == ["ABCD", "Efgh", "ijkl"]

    sampler = MostCommonTokenSampler(capitalized_threshold=0, sample_size=1)
    assert sampler.sample_text("Efgh Efgh ijkl mn") == ["Efgh"]

    relaxed = RelaxedMostCommonTokenSampler()
    assert relaxed.sample_text("ABCD Efgh ijkl mn") == ["ABCD", "Efgh", "ijkl"]

    custom = CustomTokenSampler(3)
    assert custom.sample_text("ABCD Efgh ijkl mn") == []


def test_sample_tokens_empty_token() -> None:
    sampler = MostCommonTokenSampler()
    assert sampler.sample_tokens(["hello", "", "World", "hello"]) == ["hello", ""]


def test_capitalized_threshold() -> None:
    sampler = MostCommonTokenSampler()
    # 2 of 3 capitalized is under the 0.8 threshold, so they are removed
    assert sampler.sample_text("ABCD Efgh ijkl mn") == ["ijkl"]
    # 4 of 4 capitalized meets the threshold, so they are kept
    assert sorted(sampler.sample_text("Abcd Efgh Ijkl Mnop")) == [
        "Abcd",
        "Efgh",
        "Ijkl",
        "Mnop",
    ]
