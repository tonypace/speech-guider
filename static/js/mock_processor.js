// Mock Processor - Simulates Pink Trombone audio processor for visual-only mode
// Generates tract diameter arrays from articulatory parameters
// Based on research: IPA to Pink Trombone Parameter Mapping

class MockProcessor {
  constructor() {
    // Pink Trombone uses 44 segments for the oral tract
    this.tract = {
      length: 44,
      diameter: new Array(44).fill(1.5),
      
      // Nasal cavity (28 segments)
      nose: {
        length: 28,
        diameter: new Array(28).fill(0.5),
        start: 20,  // Index where nasal cavity branches off
        offset: -2,
        amplitude: {
          max: new Array(28).fill(0)
        }
      },
      
      // Tongue control
      tongue: {
        index: 22,
        diameter: 2.5,
        range: {
          index: { minValue: 12, maxValue: 32, center: 22 },
          diameter: { minValue: 1.0, maxValue: 4.0, center: 2.5 }
        }
      },
      
      // Lip position
      lip: { start: 39 },
      
      // Amplitude for wobble effect
      amplitude: {
        max: new Array(44).fill(0)
      }
    };
    
    // Voice parameters
    this._frequency = 140;  // Hz, base voicebox frequency
    this._intensity = 0.5;  // 0-1, voicing intensity
    this._tenseness = 0.6;  // For glottis UI later
    
    // Constriction points (for visual feedback)
    this.constrictions = [];
    
    // Store current params
    this._params = {
      tongueIndex: 0.5,
      tongueDiameter: 0.5,
      lipRounding: 0.5,
      voicing: 0.5
    };
  }

  // Set parameters for animation (stores target)
  setParameters(params) {
    // Just store the params - animation system will call updateFromParams
    this._targetParams = params;
  }

  // Update tract shape from our 4 articulatory parameters
  updateFromParams(params) {
    // Store params
    this._params = params;
    
    // Map tongueIndex (0-1) to tongue.index (12-32)
    // 0.0 = Back/Velar, 1.0 = Front/Alveolar
    this.tract.tongue.index = this.tract.tongue.range.index.minValue + 
                               params.tongueIndex * (this.tract.tongue.range.index.maxValue - this.tract.tongue.range.index.minValue);
    
    // Map tongueDiameter (0-1) to tongue.diameter (4.0-1.0, INVERTED)
    // 0.0 = Open/Low, 1.0 = Closed/High Constriction
    // In Pink Trombone: smaller diameter = lower tongue position (closer to bottom)
    //                   larger diameter = higher tongue position (closer to palate)
    // We need: 0.0 (open/low) = high diameter value (close to palate? No...)
    // Actually: In Pink Trombone, the diameter parameter represents distance from origin
    // So: low vowel (tongue down) = large diameter = far from origin = low on screen
    //     high vowel (tongue up) = small diameter = close to origin = high on screen
    // So we want: slider 0.0 (open) -> large diameter, slider 1.0 (closed) -> small diameter
    this.tract.tongue.diameter = this.tract.tongue.range.diameter.maxValue - 
                                  params.tongueDiameter * (this.tract.tongue.range.diameter.maxValue - this.tract.tongue.range.diameter.minValue);
    
    // Map voicing (0-1) to intensity
    this._intensity = params.voicing;
    
    // Generate tract diameter profile based on tongue position and lip rounding
    this._generateTractProfile();
    
    // Update nasal cavity based on velum (lipRounding can affect this)
    this._updateNasalCavity(params.lipRounding);
    
    // Update amplitudes for wobble effect
    this._updateAmplitudes();
  }

  // Generate tract diameter array based on tongue position
  // Uses research-based algorithm from IPA mapping
  _generateTractProfile() {
    const baseDiameter = 1.5;  // Resting diameter
    const tongueIdx = this.tract.tongue.index;
    const tongueDia = this.tract.tongue.diameter;
    const lipRounding = this._params.lipRounding;
    const tongueDiameterParam = this._params.tongueDiameter;  // 0.0-1.0 from slider
    const lipStart = this.tract.lip.start;
    
    for (let i = 0; i < this.tract.length; i++) {
      // Distance from tongue center (using quadratic falloff for smoother curve)
      const distance = Math.abs(i - tongueIdx);
      const normalizedDist = distance / 12;  // Wider influence for smoother curve
      const influence = Math.max(0, 1 - normalizedDist * normalizedDist);  // Quadratic falloff
      
      // Calculate diameter at this point
      // The constriction depends on how "closed" the tongue is (1.0 - tongueDiaParam)
      // High tongueDiameterParam (1.0) = high tongue = small tract diameter
      // Low tongueDiameterParam (0.0) = low tongue = large tract diameter
      const constrictionAmount = tongueDiameterParam * 1.2;  // Max constriction
      let diameter = baseDiameter - influence * constrictionAmount;
      
      // Apply lip rounding constriction at the lips
      // Lip rounding affects the opening at the end of the tract
      if (i >= lipStart - 3) {
        // Closer to lip start = more rounding effect
        const lipDistance = Math.max(0, (i - (lipStart - 3)) / 5);  // 0 to 1
        const lipInfluence = Math.min(1, lipDistance);
        // Higher lip rounding = smaller opening
        // Bilabials need lipRounding = 1.0 to create closure
        const lipConstriction = lipRounding * 1.3 * lipInfluence;
        diameter = Math.max(0.1, diameter - lipConstriction);
      }
      
      // Ensure minimum diameter (prevents negative values)
      diameter = Math.max(0.15, diameter);
      
      // Special handling for stops (tongueDiameter = 1.0)
      // Complete closure at tongue position
      if (tongueDiameterParam >= 0.95 && i >= tongueIdx - 1 && i <= tongueIdx + 1) {
        diameter = 0.1;  // Complete blockage
      }
      
      this.tract.diameter[i] = diameter;
    }
    
    // Set fixed points
    this.tract.diameter[0] = 0.6;  // Glottis
    this.tract.diameter[1] = 0.6;  // Near glottis
  }

  // Update nasal cavity opening (velum)
  // For nasal consonants, velum opens
  _updateNasalCavity(lipRounding) {
    // Check if this might be a nasal sound based on tongue configuration
    // Nasals typically have complete oral closure but open velum
    const isNasal = this._params.tongueDiameter >= 0.98 && this._params.voicing > 0;
    
    // Velum diameter (0 = closed, 0.4 = open for nasals)
    let velumOpening = 0;
    if (isNasal) {
      velumOpening = 0.4;  // Open for nasal sounds
    } else if (lipRounding > 0.85) {
      // Slight opening for heavily rounded sounds (optional)
      velumOpening = (lipRounding - 0.85) * 0.5;
    }
    
    this.tract.nose.diameter[0] = Math.min(0.4, velumOpening);
    
    // Nasal cavity profile
    for (let i = 1; i < this.tract.nose.length; i++) {
      // Slightly tapered nasal cavity
      this.tract.nose.diameter[i] = 0.5 - (i / this.tract.nose.length) * 0.2;
    }
  }

  // Update amplitude arrays for wobble visualization
  _updateAmplitudes() {
    const intensity = this._intensity;
    
    for (let i = 0; i < this.tract.length; i++) {
      // Amplitude is higher where there's more space (less constriction)
      // and proportional to intensity
      const space = this.tract.diameter[i];
      this.tract.amplitude.max[i] = space * intensity * 0.5;
    }
    
    for (let i = 0; i < this.tract.nose.length; i++) {
      const space = this.tract.nose.diameter[i];
      this.tract.nose.amplitude.max[i] = space * intensity * 0.3;
    }
  }

  // Add a constriction point (for visual feedback)
  addConstriction(index, diameter) {
    this.constrictions.push({ index, diameter });
  }

  // Remove all constrictions
  clearConstrictions() {
    this.constrictions = [];
  }

  // Getters for voice parameters
  get frequency() {
    return this._frequency;
  }

  set frequency(value) {
    this._frequency = value;
  }

  get intensity() {
    return this._intensity;
  }

  get tenseness() {
    return this._tenseness;
  }

  set tenseness(value) {
    this._tenseness = value;
  }
}

// Phoneme preset definitions - Based on Research: IPA to Pink Trombone Parameter Mapping
// tongueIndex: 0.0 (Back/Velar) ↔ 1.0 (Front/Alveolar)
// tongueDiameter: 0.0 (Open/Low) ↔ 1.0 (Closed/High Constriction)
// lipRounding: 0.0 (Spread) ↔ 1.0 (Rounded)
// voicing: 0.0 (Voiceless) ↔ 1.0 (Voiced)

const PhonemePresets = {
  // VOWELS
  // High Front
  'i': { name: 'beat', params: { tongueIndex: 1.00, tongueDiameter: 0.85, lipRounding: 0.00, voicing: 1.0 } },
  'ɪ': { name: 'kit', params: { tongueIndex: 0.85, tongueDiameter: 0.70, lipRounding: 0.00, voicing: 1.0 } },
  
  // Mid Front
  'e': { name: 'dress', params: { tongueIndex: 0.80, tongueDiameter: 0.40, lipRounding: 0.00, voicing: 1.0 } },
  'ɛ': { name: 'dress', params: { tongueIndex: 0.78, tongueDiameter: 0.40, lipRounding: 0.00, voicing: 1.0 } },
  
  // Low Front
  'æ': { name: 'trap', params: { tongueIndex: 1.00, tongueDiameter: 0.10, lipRounding: 0.00, voicing: 1.0 } },
  'a': { name: 'father', params: { tongueIndex: 0.00, tongueDiameter: 0.10, lipRounding: 0.00, voicing: 1.0 } },
  
  // Central
  'ə': { name: 'about', params: { tongueIndex: 0.50, tongueDiameter: 0.50, lipRounding: 0.10, voicing: 1.0 } },
  
  // Back
  'ʌ': { name: 'strut', params: { tongueIndex: 0.30, tongueDiameter: 0.35, lipRounding: 0.00, voicing: 1.0 } },
  'ɑ': { name: 'hot', params: { tongueIndex: 0.00, tongueDiameter: 0.10, lipRounding: 0.00, voicing: 1.0 } },
  'ɔ': { name: 'thought', params: { tongueIndex: 0.10, tongueDiameter: 0.35, lipRounding: 0.60, voicing: 1.0 } },
  
  // High Back Rounded
  'ʊ': { name: 'foot', params: { tongueIndex: 0.15, tongueDiameter: 0.70, lipRounding: 0.70, voicing: 1.0 } },
  'u': { name: 'goose', params: { tongueIndex: 0.00, tongueDiameter: 0.85, lipRounding: 1.00, voicing: 1.0 } },
  'o': { name: 'boat', params: { tongueIndex: 0.15, tongueDiameter: 0.70, lipRounding: 0.90, voicing: 1.0 } },
  
  // Rhotic
  'ɝ': { name: 'bird', params: { tongueIndex: 0.52, tongueDiameter: 0.50, lipRounding: 0.40, voicing: 1.0 } },
  
  // PLOSIVES (Stops) - tongueDiameter = 1.0 for complete closure
  'p': { name: 'pat', params: { tongueIndex: 0.50, tongueDiameter: 1.00, lipRounding: 1.00, voicing: 0.0 } },
  'b': { name: 'bat', params: { tongueIndex: 0.50, tongueDiameter: 1.00, lipRounding: 1.00, voicing: 1.0 } },
  't': { name: 'tap', params: { tongueIndex: 1.00, tongueDiameter: 1.00, lipRounding: 0.00, voicing: 0.0 } },
  'd': { name: 'dad', params: { tongueIndex: 1.00, tongueDiameter: 1.00, lipRounding: 0.00, voicing: 1.0 } },
  'k': { name: 'cat', params: { tongueIndex: 0.00, tongueDiameter: 1.00, lipRounding: 0.00, voicing: 0.0 } },
  'g': { name: 'go', params: { tongueIndex: 0.00, tongueDiameter: 1.00, lipRounding: 0.00, voicing: 1.0 } },
  
  // FRICATIVES - tongueDiameter 0.90-0.96 for turbulence
  'f': { name: 'fin', params: { tongueIndex: 0.70, tongueDiameter: 0.95, lipRounding: 0.80, voicing: 0.0 } },
  'v': { name: 'van', params: { tongueIndex: 0.70, tongueDiameter: 0.95, lipRounding: 0.80, voicing: 1.0 } },
  's': { name: 'sip', params: { tongueIndex: 1.00, tongueDiameter: 0.95, lipRounding: 0.00, voicing: 0.0 } },
  'z': { name: 'zip', params: { tongueIndex: 1.00, tongueDiameter: 0.95, lipRounding: 0.00, voicing: 1.0 } },
  'ʃ': { name: 'ship', params: { tongueIndex: 0.80, tongueDiameter: 0.93, lipRounding: 0.40, voicing: 0.0 } },
  'ʒ': { name: 'measure', params: { tongueIndex: 0.80, tongueDiameter: 0.93, lipRounding: 0.40, voicing: 1.0 } },
  'h': { name: 'hat', params: { tongueIndex: 0.00, tongueDiameter: 0.50, lipRounding: 0.00, voicing: 0.0 } },
  
  // APPROXIMANTS
  'w': { name: 'wet', params: { tongueIndex: 0.00, tongueDiameter: 0.80, lipRounding: 1.00, voicing: 1.0 } },
  'j': { name: 'yes', params: { tongueIndex: 0.85, tongueDiameter: 0.80, lipRounding: 0.00, voicing: 1.0 } },
  'l': { name: 'let', params: { tongueIndex: 1.00, tongueDiameter: 0.85, lipRounding: 0.00, voicing: 1.0 } },
  'r': { name: 'red', params: { tongueIndex: 0.70, tongueDiameter: 0.80, lipRounding: 0.50, voicing: 1.0 } },
};

// Export for Gradio
window.MockProcessor = MockProcessor;
window.PhonemePresets = PhonemePresets;
