# Dataset attribution for R4

These credits cover the frozen R4 streaming checkpoint, its inherited
nine-channel base model, and its ContentVec encoder.

- **Haskins Production Rate Comparison (HPRC)** — Mark Tiede, Carol Y.
  Espy-Wilson, Dolly Goldenberg, Vikramjit Mitra, Hosung Nam, and Ganesh
  Sivaraman. Used for base-model validation and testing.
  [Corpus](https://yale.app.box.com/s/cfn8hj2puveo65fq54rp1ml2mk7moj3h),
  [Study abstract](https://acousticalsociety.org/wp-content/uploads/2018/02/Boston_Monday.pdf).
- **LibriSpeech ASR Corpus** — Vassil Panayotov, Guoguo Chen, Daniel Povey, and
  Sanjeev Khudanpur. Used to pretrain the upstream ContentVec encoder.
  [Corpus](https://www.openslr.org/12),
  [ContentVec paper](https://proceedings.mlr.press/v162/qian22b/qian22b.pdf).
- **mngu0 Articulatory Corpus** — Korin Richmond, Phil Hoole, and Simon King.
  Used to train the inherited nine-channel base model.
  [Corpus publication](https://www.research.ed.ac.uk/en/publications/announcing-the-electromagnetic-articulography-day-1-subset-of-the/).
- **MOCHA-TIMIT** — Alan Wrench, Queen Margaret University College. Used for
  R4 training and validation. The optional contact decoder also references
  MOCHA electropalatography data.
  [Corpus](https://www.cstr.ed.ac.uk/research/projects/artic/mocha.html).
- **TORGO** — Frank Rudzicz, Aravind Kumar Namasivayam, and Talya Wolff. The
  control-speaker subset was used for R4 training.
  [Dataset](https://www.cs.toronto.edu/~complingweb/data/TORGO/torgo.html).
- **USC 75-Speaker Speech MRI Database** — Yongwan Lim, Asterios Toutios,
  Yannick Bliesener, Ye Tian, Sajan Goud Lingala, Colin Vaz, Tanner Sorensen,
  Miran Oh, Sarah Harper, Weiyi Chen, Yoonjeong Lee, Johannes Töger, Mairym
  Lloréns Montesserin, Caitlin Smith, Bianca Godinez, Louis Goldstein, Dani
  Byrd, Krishna S. Nayak, and Shrikanth S. Narayanan. Used for R4 training and
  validation. [Dataset](https://sail.usc.edu/span/75speakers/).
- **USC-TIMIT** — Shrikanth Narayanan, Asterios Toutios, Vikram Ramanarayanan,
  Adam Lammert, Jangwon Kim, Sungbok Lee, Krishna Nayak, Yoon-Chul Kim, Yinghua
  Zhu, Louis Goldstein, Dani Byrd, Erik Bresch, Prasanta Ghosh, Athanasios
  Katsamanis, and Michael Proctor. Used for R4 training and validation.
  [Dataset](https://sail.usc.edu/span/usc-timit/),
  [Zenodo record](https://zenodo.org/records/19422914).
- **Wisconsin X-ray Microbeam Speech Production Database (XRMB)** — John R.
  Westbury and the University of Wisconsin–Madison. Used for R4 training and
  validation. [Dataset handbook](https://ubeam.engr.wisc.edu/pdf/ubdbman.pdf).

## Processing and provenance

Base-model training included generated additive noise and speech babble mixed
from training recordings. Audio and articulatory data were processed into model
features and targets.

The R4 checkpoint records SHA-256 hashes matching
`data/evaluation/streaming_successor_v1/train_references.json` and
`configs/streaming/successor_v1/validation_training_references.json`. The
inherited base checkpoint identifies
`data/manifests/extension/vel_glo_lat_v1/train.json` and the repaired XRMB
training manifest.

Use of the original LDC TIMIT corpus in this checkpoint remains unverified.
[LDC TIMIT catalog](https://catalog.ldc.upenn.edu/LDC93S1).
