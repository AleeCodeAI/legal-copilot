from typing import Dict, List, Tuple

from tiktoken import get_encoding
from transformers.tokenization_utils_base import PreTrainedTokenizerBase

"""
Compatibility wrapper for OpenAI's tiktoken tokenizer.

Docling's HybridChunker expects a Hugging Face-style tokenizer.
This adapter exposes the minimal interface required while using
tiktoken under the hood.
"""


class OpenAITokenizerWrapper(PreTrainedTokenizerBase):
    """Minimal Hugging Face-compatible wrapper around tiktoken."""

    def __init__(
        self,
        model_name: str = "cl100k_base",
        max_length: int = 8191,
        **kwargs,
    ):
        super().__init__(model_max_length=max_length, **kwargs)

        self.tokenizer = get_encoding(model_name)
        self._vocab_size = self.tokenizer.n_vocab

    def __len__(self) -> int:
        """Return vocabulary size."""
        return self._vocab_size

    @property
    def vocab_size(self) -> int:
        """Vocabulary size."""
        return self._vocab_size

    def tokenize(self, text: str, **kwargs) -> List[str]:
        """Tokenize text into token ID strings."""
        return [str(token) for token in self.tokenizer.encode(text)]

    def _tokenize(self, text: str) -> List[str]:
        return self.tokenize(text)

    def _convert_token_to_id(self, token: str) -> int:
        return int(token)

    def _convert_id_to_token(self, index: int) -> str:
        return str(index)

    def get_vocab(self) -> Dict[str, int]:
        """Return a Hugging Face-style vocabulary mapping."""
        return {str(i): i for i in range(self._vocab_size)}

    def convert_tokens_to_string(self, tokens: List[str]) -> str:
        """Convert token ID strings back to text."""
        token_ids = [int(token) for token in tokens]
        return self.tokenizer.decode(token_ids)

    def save_vocabulary(self, *args, **kwargs) -> Tuple[str, ...]:
        """Required by Hugging Face tokenizer interface."""
        return ()

    @classmethod
    def from_pretrained(cls, *args, **kwargs):
        """Match Hugging Face's from_pretrained interface."""
        return cls(**kwargs)
