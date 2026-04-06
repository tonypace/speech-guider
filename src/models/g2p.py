"""Grapheme-to-Phoneme conversion using espeak-ng subprocess."""

import subprocess
from typing import Optional


class G2PConverter:
    """Handles conversion from text to IPA phonemes using espeak-ng."""

    ESPEAK_PATH = "/usr/local/bin/espeak-ng"

    def __init__(self, espeak_path: Optional[str] = None, language: str = "en-us") -> None:
        """Initialize G2P converter.

        Args:
            espeak_path: Path to espeak-ng binary (uses system default if None)
            language: Language code for espeak (default: en-us)
        """
        self.espeak_path = espeak_path or self.ESPEAK_PATH
        self.language = language
        self._verify_espeak()

    def _verify_espeak(self) -> None:
        """Verify that espeak-ng is accessible."""
        try:
            result = subprocess.run(
                [self.espeak_path, "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode != 0:
                raise RuntimeError(f"espeak-ng command failed: {result.stderr}")

            print(f"Using espeak-ng: {result.stderr.strip()}")
        except FileNotFoundError:
            raise FileNotFoundError(
                f"espeak-ng not found at {self.espeak_path}. Install with: brew install espeak-ng"
            )
        except subprocess.TimeoutExpired:
            raise RuntimeError("espeak-ng command timed out")

    def convert_to_ipa(self, text: str, strip: bool = True, with_stress: bool = False) -> str:
        """Convert text to IPA phoneme string.

        Args:
            text: Input text to convert
            strip: Remove whitespace from output
            with_stress: Include stress markers

        Returns:
            IPA phoneme string
        """
        if not text.strip():
            return ""

        args = [
            self.espeak_path,
            "-q",  # quiet mode
            "-v",  # speak out
            self.language,
            "--ipa",  # output IPA
        ]

        if with_stress:
            args.append("--stress")

        try:
            result = subprocess.run(
                args + [text],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode != 0:
                raise RuntimeError(f"espeak-ng failed: {result.stderr}")

            ipa_output = result.stdout

            if strip:
                ipa_output = ipa_output.strip()

            return ipa_output

        except subprocess.TimeoutExpired:
            raise RuntimeError("espeak-ng conversion timed out")

    # Multi-character IPA symbols (sorted by length for greedy matching)
    IPA_MULTICHAR = {
        # 4-character tokens
        "dʑʲ",
        "tɕʲ",
        "tʃʰ",
        "tʃʲ",
        "dʒʲ",
        "tsʲ",
        "dˤdˤ",
        "cʰcʰ",
        # 3-character tokens
        "tɕ",
        "dʑ",
        "tʃ",
        "dʒ",
        "ts",
        "pf",
        "tS",
        "dZ",
        "tsh",
        "tɕh",
        "pʰ",
        "tʰ",
        "kʰ",
        "cʰ",
        "ʈʰ",
        "ɖʰ",
        "ɟʰ",
        "ɡʰ",
        "bʰ",
        "dʰ",
        "pʲ",
        "bʲ",
        "tʲ",
        "dʲ",
        "kʲ",
        "ɡʲ",
        "sʲ",
        "ɕʲ",
        "ʒʲ",
        "ʂʲ",
        "aɪɚ",
        "aɪə",
        "ɑːɹ",
        "ɔːɹ",
        "oːɹ",
        "iɛ5",
        "iɛ2",
        "iɛ4",
        # Diphthongs (2-char)
        "aɪ",
        "eɪ",
        "oʊ",
        "aʊ",
        "ɔɪ",
        "iə",
        "ʊə",
        "eʊ",
        "ɪu",
        "əɪ",
        "uɪ",
        "æi",
        "ɛɪ",
        "iʊ",
        "eə",
        "oɪ",
        "əʊ",
        # Long vowels
        "iː",
        "uː",
        "eː",
        "oː",
        "ɔː",
        "ɑː",
        "ɜː",
        "æː",
        "yː",
        "ɛː",
        "øː",
        "ʊː",
        "ɪː",
        # R-colored
        "ɚ",
        "ɝ",
        "ɛɹ",
        "ɪɹ",
        "ʊɹ",
        "ɑɹ",
        "ɔɹ",
        "oɹ",
        # Other multi-char
        "nʲ",
        "rʲ",
        "mʲ",
        "dʲʲ",
        "nʲʲ",
        "əl",
        "n̩",
        "l̩",
        "r̩",
        "m̩",
    }

    def tokenize_ipa(self, ipa_string: str) -> list[str]:
        """Tokenize IPA string into phoneme tokens using greedy longest-match.

        Args:
            ipa_string: IPA phoneme string

        Returns:
            List of IPA phoneme tokens
        """
        tokens = []
        i = 0
        while i < len(ipa_string):
            matched = False
            # Try longest matches first (4, 3, 2 chars)
            for length in range(min(4, len(ipa_string) - i), 0, -1):
                substr = ipa_string[i : i + length]
                if substr in self.IPA_MULTICHAR:
                    tokens.append(substr)
                    i += length
                    matched = True
                    break
            if not matched:
                # Single character phoneme
                tokens.append(ipa_string[i])
                i += 1
        return tokens

    def text_to_ipa_list(self, text: str) -> list[str]:
        """Convert text to list of IPA phonemes.

        Args:
            text: Input text

        Returns:
            List of IPA phoneme strings (properly tokenized)
        """
        ipa_string = self.convert_to_ipa(text, strip=True, with_stress=False)

        # Clean up espeak-ng output formatting
        ipa_string = ipa_string.replace(" ", "")
        ipa_string = ipa_string.replace("\n", "")
        ipa_string = ipa_string.replace("◌", "")  # Remove null symbol if present

        return self.tokenize_ipa(ipa_string) if ipa_string else []
