# Speech Guider — local noncommercial installer

This package installs Speech Guider, its offline backend, R4, and OmniVoice in
one app bundle. The app requires Apple Silicon and macOS 26 or later. Presets
and prosody summaries remain in your application data directory.

## Attribution

**R4 decoder** — built by Tony Pace.

**ContentVec** — credit to the ContentVec authors and to lengyue233 for the
Hugging Face conversion. The bundle uses a local seven-layer export of the
encoder.

- https://github.com/auspicious3000/contentvec
- https://huggingface.co/lengyue233/content-vec-best

**OmniVoice** — by Han Zhu and the k2-fsa/Xiaomi authors. GGUF conversion and
the C++ port are by Serveurperso and contributors.

Built with Higgs Materials licensed from Boson AI USA, Inc., Copyright Boson AI USA, Inc., All Rights Reserved and Meta Llama 3 licensed under the Meta Llama 3 Community License, Copyright Meta Platforms, Inc., All Right Reserved. based on Meta Llama 3

- https://huggingface.co/k2-fsa/OmniVoice
- https://huggingface.co/Serveurperso/OmniVoice-GGUF
- https://github.com/ServeurpersoCom/omnivoice.cpp
