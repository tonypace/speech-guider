import json
import sys
from pathlib import Path
from typing import Any, Union

import gradio as gr  # type: ignore
import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).parent))

from src.audio import AudioContext, PitchContour, ProsodyAnalyzer, ProsodyMetrics
from src.models.alignment import ForcedAligner, PronunciationError, SentenceAlignment
from src.models.articulatory import ArticulatoryMapper, format_with_html_tooltips


class AnalysisState:
    """State holder for analysis results."""

    alignment: None | SentenceAlignment

    def __init__(self) -> None:
        self.errors: list[PronunciationError] = []
        self.alignment: None | SentenceAlignment = None
        self.mapper = ArticulatoryMapper()
        self.selected_error_index = 0


state = AnalysisState()

# Cache for Wav2Vec2 model to avoid reloading on every analysis
_cached_aligner: ForcedAligner | None = None


def get_aligner() -> ForcedAligner:
    """Get or create cached ForcedAligner instance."""
    global _cached_aligner
    if _cached_aligner is None:
        print("Initializing Wav2Vec2 aligner (first time)...")
        _cached_aligner = ForcedAligner()
        print("Wav2Vec2 aligner initialized and cached.")
    return _cached_aligner


def analyze_audio(audio_filepath: str | None, target_text: str) -> tuple[dict[str, Any], str]:
    """Analyze audio and return error list with prosody feedback.

    Args:
        audio_filepath: Path to audio file
        target_text: Target sentence to analyze

    Returns:
        Gradio update for error_select and feedback markdown
    """
    if audio_filepath is None:
        raise gr.Error("Please record or upload audio first.")

    if not target_text.strip():
        raise gr.Error("Please enter the target sentence.")

    progress = gr.Progress()
    progress(0.1, desc="Loading audio file...")

    try:
        audio_context = AudioContext(audio_filepath)
    except Exception as e:
        raise gr.Error(f"Failed to load audio file: {e}")

    progress(0.3, desc="Analyzing pronunciation...")
    errors: list[PronunciationError] = []
    alignment = None
    aligner = None

    try:
        from scipy.io import wavfile

        sample_rate, audio_data = wavfile.read(audio_filepath)
        if audio_data.dtype == np.int16:
            audio_data = audio_data.astype(np.float32) / 32768.0
        elif audio_data.dtype == np.int32:
            audio_data = audio_data.astype(np.float32) / 2147483648.0

        if len(audio_data.shape) > 1:
            audio_data = np.mean(audio_data, axis=1)

        if sample_rate != 16000:
            import scipy.signal as signal

            num_samples = int(len(audio_data) * 16000 / sample_rate)
            audio_data = signal.resample(audio_data, num_samples)
            sample_rate = 16_000

        audio_tensor = torch.from_numpy(audio_data).float()

        aligner = get_aligner()
        errors, alignment = aligner.analyze_pronunciation(audio_tensor, target_text)

    except Exception:
        progress(0.8, desc="Analysis encountered issues...")
        errors = []
        alignment = None

    progress(0.6, desc="Extracting prosody metrics...")
    prosody_analyzer = ProsodyAnalyzer(audio_context)

    if alignment:
        vowel_timestamps = [
            (phoneme.start_time, phoneme.end_time)
            for word in alignment.words
            for phoneme in word.phonemes
            if phoneme.is_vowel
        ]

        word_timestamps = [(word.word, word.start_time, word.end_time) for word in alignment.words]

        prosody: Union[PitchContour, ProsodyMetrics] = prosody_analyzer.analyze_complete(
            vowel_timestamps, word_timestamps
        )
    else:
        prosody = prosody_analyzer.analyze_pitch()

    progress(0.9, desc="Generating comprehensive feedback...")

    if alignment and hasattr(alignment, "overall_score"):
        overall_score: float = float(alignment.overall_score)
    else:
        overall_score = 0.0

    comprehensive_feedback = format_prosody_feedback(overall_score, prosody)

    state.errors = errors
    state.alignment = alignment

    error_display_list = format_error_list(errors)
    selected_value = (
        error_display_list[0]
        if error_display_list and error_display_list[0] != "No errors detected"
        else None
    )

    return (
        gr.update(choices=error_display_list, value=selected_value),
        comprehensive_feedback,
    )


def select_error(error_text: str | None) -> tuple[str, str, str, str]:
    """Select an error to display in the vocal tract visualization.

    Args:
        error_text: Selected error text from radio button

    Returns:
        Tuple of (incorrect_description, correct_description, animation_json, highlight_json)
    """
    if not error_text or error_text == "No errors detected":
        return (
            "",
            "",
            json.dumps({"left": {}, "right": {}}),
            json.dumps({"zone": None}),
        )

    # Extract index from error text (e.g., "1. 'today'..." -> 0)
    try:
        error_index = int(error_text.split(".")[0]) - 1
    except (ValueError, IndexError):
        return (
            "",
            "",
            json.dumps({"left": {}, "right": {}}),
            json.dumps({"zone": None}),
        )

    if error_index < 0 or error_index >= len(state.errors):
        return (
            "",
            "",
            json.dumps({"left": {}, "right": {}}),
            json.dumps({"zone": None}),
        )

    state.selected_error_index = error_index
    error = state.errors[error_index]

    # Parse target and predicted phonemes
    target_description = state.mapper.parse_phoneme(error.target_phoneme)
    predicted_description = state.mapper.parse_phoneme(error.predicted_phoneme)

    # Create HTML descriptions with tooltips
    incorrect_html = f"Predicted: /{predicted_description.ipa_symbol}/<br>{format_with_html_tooltips(predicted_description)}"
    correct_html = f"Target: /{target_description.ipa_symbol}/<br>{format_with_html_tooltips(target_description)}"

    # Map to animation parameters
    target_params = state.mapper.map_to_parameters(target_description)
    predicted_params = state.mapper.map_to_parameters(predicted_description)

    # Calculate highlight zone
    delta_description, highlight_zone = state.mapper.calculate_delta(
        target_params, predicted_params
    )

    animation_json = json.dumps(
        {
            "left": {
                "tongueIndex": predicted_params.tongue_index,
                "tongueDiameter": predicted_params.tongue_diameter,
                "lipRounding": predicted_params.lip_rounding,
                "voicing": predicted_params.voicing,
            },
            "right": {
                "tongueIndex": target_params.tongue_index,
                "tongueDiameter": target_params.tongue_diameter,
                "lipRounding": target_params.lip_rounding,
                "voicing": target_params.voicing,
            },
        }
    )

    highlight_json = json.dumps({"zone": highlight_zone})

    return incorrect_html, correct_html, animation_json, highlight_json


def format_error_list(errors: list[PronunciationError]) -> list:
    """Format errors as a Gradio choice list.

    Args:
        errors: List of pronunciation errors

    Returns:
        List of error descriptions for display
    """
    if not errors:
        return ["No errors detected"]

    error_list = []
    for i, error in enumerate(errors):
        clean_target = error.target_phoneme.strip(" /")
        clean_predicted = error.predicted_phoneme.strip(" /")
        error_text = f"{i + 1}. '{error.word_context}': /{clean_target}/ → /{clean_predicted}/"
        error_list.append(error_text)

    return error_list


def format_prosody_feedback(overall_score: float, prosody) -> str:
    """Format prosody metrics into user-friendly feedback.

    Args:
        overall_score: Overall pronunciation score
        prosody: ProsodyMetrics or PitchContour object

    Returns:
        Formatted prosody feedback string
    """
    pitch = prosody.pitch if hasattr(prosody, "pitch") else prosody
    f0_range = pitch.f0_range

    intonation_flag = "Flat intonation" if f0_range < 50 else "Good pitch variation"

    feedback = f"""## Prosody Analysis

### Pitch & Intonation
• **F0 Range**: {f0_range:.1f}Hz - {intonation_flag}
• **Overall Score**: {overall_score:.2f}
"""

    if hasattr(prosody, "rhythm") and prosody.rhythm:
        npvi_value = prosody.rhythm.npvi
        rhythm_type = prosody.rhythm.classification

        if rhythm_type == "stress-timed":
            rhythm_feedback = "Good English rhythm (stress-timed)"
        elif rhythm_type == "syllable-timed":
            rhythm_feedback = "Syllable-timed (robotic/staccato)"
        else:
            rhythm_feedback = rhythm_type

        feedback += f"\n### Rhythm Analysis\n• **nPVI**: {npvi_value:.1f} - {rhythm_feedback}\n"

    if hasattr(prosody, "stress") and prosody.stress:
        stress_word = prosody.stress.primary_stress_word
        stress_time = prosody.stress.primary_stress_time
        feedback += (
            f"\n### Stress Pattern\n• **Primary Stress**: '{stress_word}' (at {stress_time:.2f}s)\n"
        )

    return feedback


# Read JavaScript content for injection (at module level for use in launch())
# Load Pink Trombone animation files in order: core -> processor -> animation lab
_JS_PATH = Path("src/ui/assets/vocal_tract.js")
_JS_CONTENT = _JS_PATH.read_text() if _JS_PATH.exists() else ""

# Load Pink Trombone files
_PINK_TROMBONE_CORE_PATH = Path("src/ui/assets/pink_trombone_core.js")
_PINK_TROMBONE_CORE = (
    _PINK_TROMBONE_CORE_PATH.read_text() if _PINK_TROMBONE_CORE_PATH.exists() else ""
)

_MOCK_PROCESSOR_PATH = Path("src/ui/assets/mock_processor.js")
_MOCK_PROCESSOR = _MOCK_PROCESSOR_PATH.read_text() if _MOCK_PROCESSOR_PATH.exists() else ""

_ANIMATION_LAB_PATH = Path("src/ui/assets/animation_lab.js")
_ANIMATION_LAB = _ANIMATION_LAB_PATH.read_text() if _ANIMATION_LAB_PATH.exists() else ""

# Combine all JS content (order matters!)
_ALL_JS_CONTENT = (
    _PINK_TROMBONE_CORE + "\n" + _MOCK_PROCESSOR + "\n" + _ANIMATION_LAB + "\n" + _JS_CONTENT
)


def create_interface() -> gr.Blocks:
    """Create the Gradio interface with vocal tract visualization."""

    with gr.Blocks(
        title="Pronunciation & Prosody Evaluator",
        css_paths="src/ui/assets/vocal_tract.css",
        js="async () => { " + _ALL_JS_CONTENT + " }",
    ) as demo:
        gr.Markdown("# Pronunciation & Prosody Evaluator")
        gr.Markdown(
            "Record yourself reading the target sentence and receive instant feedback on pronunciation and intonation."
        )

        # Define all components first (in definition order, not visual order)
        target_text = gr.Textbox(
            label="Target Sentence",
            value="The weather is very hot today.",
            placeholder="Enter the sentence to practice...",
        )

        audio_input = gr.Audio(
            sources=["microphone", "upload"],
            type="filepath",
            label="Record or Upload Audio",
        )

        analyze_btn = gr.Button("Analyze Pronunciation", variant="primary")

        feedback_output = gr.Markdown(label="Feedback")

        error_select = gr.Radio(
            label="Detected Errors",
            choices=[],
            value=None,
            interactive=True,
        )

        vocal_tract_html = gr.HTML(
            value=get_vocal_tract_html(),
            show_label=False,
        )

        # Hidden state components
        incorrect_desc = gr.State(value="")
        correct_desc = gr.State(value="")
        animation_params = gr.State(value="")
        highlight_params = gr.State(value="")

        # Main analysis section
        gr.Markdown("## Analysis")

        with gr.Row():
            with gr.Column(scale=2):
                target_text
                audio_input
                analyze_btn

            with gr.Column(scale=3):
                feedback_output

        # Button click handler (now all components are defined)
        analyze_btn.click(
            fn=analyze_audio,
            inputs=[audio_input, target_text],
            outputs=[error_select, feedback_output],
            show_progress="full",
        )

        gr.Markdown("---")
        gr.Markdown("## Articulatory Feedback")

        gr.Markdown(
            "Select an error below to see the incorrect pronunciation on the left "
            "and the correct pronunciation on the right. Click 'Animate' to see "
            "the mouth/tongue position. Hover over technical terms for explanations."
        )

        with gr.Row():
            with gr.Column(scale=1):
                error_select

            with gr.Column(scale=3):
                vocal_tract_html

        error_select.change(
            fn=select_error,
            inputs=error_select,
            outputs=[
                incorrect_desc,
                correct_desc,
                animation_params,
                highlight_params,
            ],
        )

        # Add JavaScript callback to update vocal tract visualization when state changes
        animation_params.change(
            fn=None,
            inputs=[incorrect_desc, correct_desc, animation_params, highlight_params],
            js="""
            (left_html, right_html, animation_params, highlight_params) => {
                if (typeof window.updateVocalTractDescriptions === 'function') {
                    window.updateVocalTractDescriptions(left_html, right_html, animation_params, highlight_params);
                }
            }
            """,
        )

        # Animation Lab Tab
        gr.Markdown("---")
        gr.Markdown("## Animation Lab")
        gr.Markdown(
            "Interactive vocal tract visualization. Use the sliders to control articulatory parameters, "
            "or click phoneme buttons to see common English sounds."
        )

        with gr.Row():
            with gr.Column(scale=1):
                # Parameter sliders
                tongue_idx_slider = gr.Slider(
                    minimum=0,
                    maximum=1,
                    value=0.5,
                    step=0.01,
                    label="Tongue Position (front ← → back)",
                    elem_id="tongue-idx-slider",
                )
                tongue_dia_slider = gr.Slider(
                    minimum=0,
                    maximum=1,
                    value=0.5,
                    step=0.01,
                    label="Tongue Height (low ← → high)",
                    elem_id="tongue-dia-slider",
                )
                lip_round_slider = gr.Slider(
                    minimum=0,
                    maximum=1,
                    value=0.5,
                    step=0.01,
                    label="Lip Rounding (spread ← → rounded)",
                    elem_id="lip-round-slider",
                )
                voicing_slider = gr.Slider(
                    minimum=0,
                    maximum=1,
                    value=0.5,
                    step=0.01,
                    label="Voicing (voiceless ← → voiced)",
                    elem_id="voicing-slider",
                )

                gr.Markdown("### Phoneme Presets")

                # Vowel buttons
                with gr.Row():
                    gr.Button("i").click(
                        fn=lambda: None,
                        js="() => { if(window.setPhonemePreset) window.setPhonemePreset('i'); }",
                    )
                    gr.Button("ɪ").click(
                        fn=lambda: None,
                        js="() => { if(window.setPhonemePreset) window.setPhonemePreset('ɪ'); }",
                    )
                    gr.Button("e").click(
                        fn=lambda: None,
                        js="() => { if(window.setPhonemePreset) window.setPhonemePreset('e'); }",
                    )
                    gr.Button("æ").click(
                        fn=lambda: None,
                        js="() => { if(window.setPhonemePreset) window.setPhonemePreset('æ'); }",
                    )

                with gr.Row():
                    gr.Button("a").click(
                        fn=lambda: None,
                        js="() => { if(window.setPhonemePreset) window.setPhonemePreset('a'); }",
                    )
                    gr.Button("ɑ").click(
                        fn=lambda: None,
                        js="() => { if(window.setPhonemePreset) window.setPhonemePreset('ɑ'); }",
                    )
                    gr.Button("ɔ").click(
                        fn=lambda: None,
                        js="() => { if(window.setPhonemePreset) window.setPhonemePreset('ɔ'); }",
                    )
                    gr.Button("o").click(
                        fn=lambda: None,
                        js="() => { if(window.setPhonemePreset) window.setPhonemePreset('o'); }",
                    )

                with gr.Row():
                    gr.Button("ʊ").click(
                        fn=lambda: None,
                        js="() => { if(window.setPhonemePreset) window.setPhonemePreset('ʊ'); }",
                    )
                    gr.Button("u").click(
                        fn=lambda: None,
                        js="() => { if(window.setPhonemePreset) window.setPhonemePreset('u'); }",
                    )
                    gr.Button("ə").click(
                        fn=lambda: None,
                        js="() => { if(window.setPhonemePreset) window.setPhonemePreset('ə'); }",
                    )
                    gr.Button("ɝ").click(
                        fn=lambda: None,
                        js="() => { if(window.setPhonemePreset) window.setPhonemePreset('ɝ'); }",
                    )

                gr.Markdown("### Consonants")

                with gr.Row():
                    gr.Button("s").click(
                        fn=lambda: None,
                        js="() => { if(window.setPhonemePreset) window.setPhonemePreset('s'); }",
                    )
                    gr.Button("ʃ").click(
                        fn=lambda: None,
                        js="() => { if(window.setPhonemePreset) window.setPhonemePreset('ʃ'); }",
                    )
                    gr.Button("f").click(
                        fn=lambda: None,
                        js="() => { if(window.setPhonemePreset) window.setPhonemePreset('f'); }",
                    )

            with gr.Column(scale=2):
                # Pink Trombone canvas
                animation_canvas = gr.HTML(
                    value='<canvas id="pink-trombone-canvas" width="600" height="500" style="background-color: white; border: 1px solid #ccc;"></canvas>',
                    show_label=False,
                )

        # Update animation when sliders change
        for slider in [tongue_idx_slider, tongue_dia_slider, lip_round_slider, voicing_slider]:
            slider.change(
                fn=None,
                inputs=[tongue_idx_slider, tongue_dia_slider, lip_round_slider, voicing_slider],
                js="""
                (tongueIdx, tongueDia, lipRound, voicing) => {
                    if (window.updateAnimationParams) {
                        window.updateAnimationParams(tongueIdx, tongueDia, lipRound, voicing);
                    }
                }
                """,
            )

        gr.Markdown("---")
        gr.Markdown("### Instructions")
        gr.Markdown(
            "1. Read the target sentence aloud\n"
            "2. Click the microphone to record (or upload a .wav file)\n"
            "3. Click 'Analyze Pronunciation' to receive feedback\n"
            "4. Select an error to see articulatory visualization\n"
            "5. Click 'Animate' to see mouth/tongue positions\n"
            "6. Visit Animation Lab to experiment with vocal tract shapes"
        )

        gr.Markdown(
            "**Note**: This system uses IPA-based phoneme analysis. "
            "For best results, speak clearly and at a moderate pace."
        )

    return demo  # type: ignore[no-any-return]


def get_vocal_tract_html() -> str:
    """Get the HTML structure for vocal tract visualization.

    Returns:
        HTML string containing the markup for panels and canvases.
    """
    html = """
    <div class="vocal-tract-container">
        <div class="vocal-tract-panels">
            <div class="vocal-tract-panel">
                <div class="vocal-tract-header">
                    <span class="vocal-tract-title">What you're doing</span>
                    <span id="left-phoneme" class="vocal-tract-phoneme">-</span>
                </div>

                <div class="vocal-tract-canvas-wrapper">
                    <canvas id="vocal-tract-left" width="400" height="300"></canvas>
                </div>

                <div id="left-description" class="vocal-tract-features">
                    No error selected
                </div>

                <div class="vocal-tract-actions">
                    <button class="vocal-tract-button" onclick="window.animateLeft()">Animate</button>
                </div>
            </div>

            <div class="vocal-tract-panel">
                <div class="vocal-tract-header">
                    <span class="vocal-tract-title">What you should do</span>
                    <span id="right-phoneme" class="vocal-tract-phoneme">-</span>
                </div>

                <div class="vocal-tract-canvas-wrapper">
                    <canvas id="vocal-tract-right" width="400" height="300"></canvas>
                </div>

                <div id="right-description" class="vocal-tract-features">
                    No error selected
                </div>

                <div class="vocal-tract-actions">
                    <button class="vocal-tract-button" onclick="window.animateRight()">Animate</button>
                </div>
            </div>
        </div>
    </div>
    """

    return html


if __name__ == "__main__":
    demo = create_interface()
    demo.launch()
