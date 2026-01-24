import json
from typing import Any, Dict, List, Optional, Union
from transformers import PreTrainedTokenizer

class FlumeTokenizer(PreTrainedTokenizer):
    """
    Simple character-level tokenizer for Flume.
    """

    model_input_names = ["input_ids", "attention_mask"]

    def __init__(
        self,
        chars: Optional[str] = " abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.,!?;:'\"()-\n",
        bos_token="<BOS>",
        eos_token="<EOS>",
        unk_token="<UNK>",
        pad_token="<PAD>",
        **kwargs
    ):
        self.chars = chars
        self._char_to_idx = {c: i for i, c in enumerate(chars)}
        self._idx_to_char = {i: c for i, c in enumerate(chars)}

        offset = len(chars)
        self._char_to_idx[pad_token] = offset
        self._char_to_idx[unk_token] = offset + 1
        self._char_to_idx[bos_token] = offset + 2
        self._char_to_idx[eos_token] = offset + 3

        self._idx_to_char[offset] = pad_token
        self._idx_to_char[offset + 1] = unk_token
        self._idx_to_char[offset + 2] = bos_token
        self._idx_to_char[offset + 3] = eos_token

        super().__init__(
            bos_token=bos_token,
            eos_token=eos_token,
            unk_token=unk_token,
            pad_token=pad_token,
            **kwargs
        )

    @property
    def vocab_size(self) -> int:
        return len(self._idx_to_char)

    def get_vocab(self) -> Dict[str, int]:
        return self._char_to_idx.copy()

    def _tokenize(self, text: str) -> List[str]:
        return list(text)

    def _convert_token_to_id(self, token: str) -> int:
        return self._char_to_idx.get(token, self._char_to_idx[self.unk_token])

    def _convert_id_to_token(self, index: int) -> str:
        return self._idx_to_char.get(index, self.unk_token)

    def convert_tokens_to_string(self, tokens: List[str]) -> str:
        return "".join(tokens)

    def save_vocabulary(self, save_directory: str, filename_prefix: Optional[str] = None) -> tuple[str]:
        import os
        vocab_file = os.path.join(save_directory, (filename_prefix or "") + "vocab.json")
        with open(vocab_file, "w", encoding="utf-8") as f:
            json.dump(self._char_to_idx, f, ensure_ascii=False)
        return (vocab_file,)
