"""Simple mock test for articulatory module without pyclts dependency."""
# ruff: noqa: E402  # noqa to allow non-top-level import for mock setup

import sys
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


# Mock the clts module
class MockCLTS:
    """Mock CLTS module for testing."""

    class TranscriptionSystem:
        def __init__(self, name):
            pass


# Inject mock before importing articulatory module
clts_mock = types.ModuleType("clts")
clts_mock.TranscriptionSystem = MockCLTS.TranscriptionSystem  # type: ignore[attr-defined]
sys.modules["clts"] = clts_mock

# Now import our module (after mock setup)
from src.models.articulatory import (
    ArticulatoryMapper,
    ArticulatoryParameters,
    PhonemeDescription,
    format_with_html_tooltips,
)


def test_basic_structure():
    """Test that basic data structures work without pyclts."""
    print("\n=== Testing Basic Articulatory Structure (No pyclts) ===")

    # Test dataclass instantiation
    params = ArticulatoryParameters(
        tongue_index=0.5, tongue_diameter=0.5, lip_rounding=0.5, voicing=0.5
    )
    print(f"✓ ArticulatoryParameters created: tongue_index={params.tongue_index}")

    description = PhonemeDescription(
        technical_name="Voiced Alveolar Fricative",
        ipa_symbol="z",
        features={"place": "alveolar", "manner": "fricative", "voicing": "voiced"},
        tooltips={
            "place": "Tongue against bony ridge",
            "manner": "Air through narrow channel",
            "voicing": "Vibrating vocal cords",
        },
    )
    print(f"✓ PhonemeDescription created: {description.technical_name}")

    # Test mapper initialization
    mapper = ArticulatoryMapper()
    print("✓ ArticulatoryMapper initialized")
    print(f"  Feature definitions: {list(mapper._feature_definitions.keys())}")
    print(f"  Tooltip definitions: {len(mapper._tooltip_definitions)} entries")

    # Test parameter mapping
    mapped_params = mapper.map_to_parameters(description)
    print(f"✓ Parameters mapped: tongue_index={mapped_params.tongue_index:.2f}")

    # Test delta calculation
    target_params = ArticulatoryParameters(0.7, 0.3, 0.8, 0.9)
    predicted_params = ArticulatoryParameters(0.3, 0.7, 0.2, 0.1)
    delta_desc, highlight = mapper.calculate_delta(target_params, predicted_params)
    print(f"✓ Delta calculation: {delta_desc}, highlight={highlight}")

    # Test HTML formatting
    html = format_with_html_tooltips(description)
    print(f"✓ HTML formatting successful ({len(html)} chars)")
    print(f"  Contains tooltip: {'tooltip' in html}")

    print("\n✅ All basic structure tests passed!")
    return True


def test_javascript_assets():
    """Test that JavaScript and CSS assets exist."""
    print("\n=== Testing Static Assets ===")

    js_path = Path("src/ui/assets/vocal_tract.js")
    css_path = Path("src/ui/assets/vocal_tract.css")

    assert js_path.exists(), "JavaScript file not found"
    assert css_path.exists(), "CSS file not found"

    print(f"✓ JavaScript file: {js_path} ({js_path.stat().st_size} bytes)")
    print(f"✓ CSS file: {css_path} ({css_path.stat().st_size} bytes)")

    # Check basic content
    js_content = js_path.read_text()
    css_content = css_path.read_text()

    assert "VocalTract" in js_content, "JavaScript missing VocalTract class"
    assert ".tooltip" in css_content, "CSS missing tooltip styling"

    print("✓ JavaScript contains VocalTract class")
    print("✓ CSS contains tooltip styling")

    print("\n✅ All static asset tests passed!")
    return True


if __name__ == "__main__":
    try:
        test_basic_structure()
        test_javascript_assets()
        print("\n" + "=" * 50)
        print("ALL MOCK TESTS PASSED ✅")
        print("=" * 50)
        print("\nNote: Full articulatory functionality requires pyclts installation:")
        print("  pip install pyclts")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
