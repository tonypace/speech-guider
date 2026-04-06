"""Deprecated Wav2Vec2 model management for forced alignment and phoneme recognition."""

import json
from pathlib import Path
from typing import Optional

import torch
from transformers import (
    AutoModelForCTC,
    Wav2Vec2FeatureExtractor,
)

InferenceOutput = dict[str, torch.Tensor | str]  # type: ignore[misc]


class SimplePhonemeTokenizer:
    """Custom phoneme tokenizer for IPA-based Wav2Vec2 models."""

    def __init__(self, vocab_file: str):
        """Initialize tokenizer with vocabulary file.

        Args:
            vocab_file: Path to vocabulary JSON file
        """
        with open(vocab_file, "r") as f:
            self.vocab = json.load(f)
        self.reverse_vocab = {v: k for k, v in self.vocab.items()}
        self.pad_token = "<pad>"
        self.speech_token = "<pad>"  # CTC blank token

    def get_vocab(self) -> dict[str, int]:
        """Get vocabulary mapping."""
        return self.vocab  # type: ignore[no-any-return]

    def decode(self, ids) -> str:
        """Decode token IDs to phoneme string using CTC collapse.

        Args:
            ids: Token IDs to decode

        Returns:
            Decoded phoneme string
        """
        result = []
        _prev_id = None

        for id_item in ids:
            # Handle both single integers and lists/tensors
            if hasattr(id_item, "item"):
                id_val = id_item.item()
            elif isinstance(id_item, (list, tuple)):
                if len(id_item) > 0:
                    id_val = id_item[0]
                    if hasattr(id_val, "item"):
                        id_val = id_val.item()
                else:
                    continue
            else:
                id_val = id_item

            # Remove blank/pad tokens (ID 0=<pad>, 1=<s>, 2=</s>, 3=<unk>)
            if id_val in [0, 1, 2, 3]:
                _prev_id = None
                continue

            # Remove consecutive duplicates (CTC collapse)
            if id_val != _prev_id:
                if id_val in self.reverse_vocab:
                    result.append(self.reverse_vocab[id_val])
                _prev_id = id_val

        return "".join(result)

    def batch_decode(self, ids_list) -> list[str]:
        """Decode multiple sequences.

        Args:
            ids_list: List of token ID sequences

        Returns:
            List of decoded strings
        """
        return [self.decode(ids) for ids in ids_list]


class Wav2Vec2Model:
    """Deprecated Wav2Vec2 wrapper retained as a fallback alignment path.

    The preferred SSL backbone for new articulatory work is DistilHuBERT.
    This class remains for legacy forced alignment when AAI/SSL pathways are
    unavailable.
    """

    MODEL_NAME = "facebook/wav2vec2-xlsr-53-espeak-cv-ft"
    SAMPLE_RATE = 16000

    def __init__(self, model_name: str = MODEL_NAME, device: Optional[str] = None) -> None:
        """Initialize Wav2Vec2 model and processor.

        Args:
            model_name: Hugging Face model identifier
            device: Device to load model on ('cuda', 'mps', 'cpu', or None for auto-detect)
        """
        self.model_name = model_name

        if device is None:
            self.device = self._auto_detect_device()
        else:
            self.device = device

        self._load_model()

    def _auto_detect_device(self) -> str:
        """Auto-detect the best available device.

        Priority: CUDA > MPS > CPU

        Returns:
            Device string ('cuda', 'mps', or 'cpu')
        """
        if torch.cuda.is_available():
            return "cuda"
        if torch.backends.mps.is_available():
            return "mps"
        return "cpu"

    def _load_model(self) -> None:
        """Load Wav2Vec2 model and custom phoneme tokenizer."""
        print("WARNING: Wav2Vec2 is deprecated and should only be used as a fallback path.")
        print(f"Loading Wav2Vec2 model: {self.model_name}")
        print(f"Device: {self.device}")

        try:
            from huggingface_hub import hf_hub_download

            # Cache vocab file locally to avoid repeated downloads
            cache_dir = Path.home() / ".cache" / "huggingface" / "hub"
            cached_vocab = (
                cache_dir / f"models--{self.model_name.replace('/', '--')}" / "vocab.json"
            )

            if cached_vocab.exists():
                vocab_file = str(cached_vocab)
                print("Using cached vocab.json")
            else:
                # Download vocab file
                vocab_file = hf_hub_download(repo_id=self.model_name, filename="vocab.json")
                print("Downloaded vocab.json from HF Hub")

            # Load feature extractor
            self.feature_extractor = Wav2Vec2FeatureExtractor.from_pretrained(self.model_name)

            # Create custom phoneme tokenizer
            self.tokenizer_obj = SimplePhonemeTokenizer(vocab_file)

            # Create processor wrapper
            class SimpleProcessor:
                def __init__(
                    self,
                    tokenizer: SimplePhonemeTokenizer,
                    feature_extractor: Wav2Vec2FeatureExtractor,
                ):
                    self._tokenizer_internal = tokenizer
                    self.feature_extractor = feature_extractor

                def __call__(self, audio, sampling_rate=None, return_tensors="pt"):
                    inputs = self.feature_extractor(
                        audio,
                        sampling_rate=sampling_rate,
                        return_tensors=return_tensors,
                    )
                    return inputs

                def decode(self, ids):
                    return self._tokenizer_internal.decode(ids)

                def batch_decode(self, ids_list):
                    return self._tokenizer_internal.batch_decode(ids_list)

                @property
                def tokenizer(self):
                    return self._tokenizer_internal

                @tokenizer.setter
                def tokenizer(self, value):
                    self._tokenizer_internal = value

            self.processor = SimpleProcessor(self.tokenizer_obj, self.feature_extractor)

        except Exception as e:
            print(f"Custom tokenizer loading failed with error: {e}")
            raise

        self.model = AutoModelForCTC.from_pretrained(self.model_name)
        self.model.to(self.device)
        self.model.eval()

        print("Model loaded successfully.")

    def transcribe(
        self, audio_tensor: torch.Tensor, sample_rate: int = SAMPLE_RATE
    ) -> InferenceOutput:
        """Transcribe audio to phoneme logits and decode predicted IPA.

        Args:
            audio_tensor: Audio waveform tensor (1D or 2D)
            sample_rate: Sample rate of the audio

        Returns:
            Dictionary containing:
                - logits: Raw CTC output logits (frame-level phoneme probabilities)
                - predicted_phonemes: Decoded sequence of predicted phonemes
                - tokens: Token IDs of predicted phonemes
        """
        if audio_tensor.dim() == 2:
            audio_tensor = audio_tensor.squeeze()

        if sample_rate != self.SAMPLE_RATE:
            # TODO: Add resampling logic
            raise ValueError(f"Audio sample rate must be {self.SAMPLE_RATE}Hz")

        inputs = self.processor(audio_tensor, sampling_rate=self.SAMPLE_RATE, return_tensors="pt")
        inputs = inputs.to(self.device)

        with torch.no_grad():
            logits = self.model(inputs.input_values).logits

        # Get predicted phoneme IDs (remove batch dimension)
        predicted_ids = torch.argmax(logits, dim=-1)

        # Decode phoneme sequence
        predicted_phonemes = self.processor.decode(predicted_ids[0])

        # Return both raw logits for alignment and decoded phonemes for comparison
        return {
            "logits": logits.squeeze(),
            "predicted_phonemes": predicted_phonemes,
            "token_ids": predicted_ids[0],
        }  # type: ignore[return-value]

    def cleanup(self) -> None:
        """Free GPU memory."""
        if hasattr(self, "model"):
            del self.model
        if hasattr(self, "processor"):
            del self.processor

        # Cleanup device-specific memory
        if self.device == "cuda" and torch.cuda.is_available():
            torch.cuda.empty_cache()
        elif self.device == "mps" and torch.backends.mps.is_available():
            torch.mps.empty_cache()
