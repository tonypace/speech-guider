// Mock Processor - Simulates Pink Trombone audio processor for visual-only mode
// Generates tract diameter arrays from articulatory parameters

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
        offset: -2
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
  }

  // Update tract shape from our 4 articulatory parameters
  updateFromParams(params) {
    // params: { tongueIndex, tongueDiameter, lipRounding, voicing }
    
    // Map tongueIndex (0-1) to tongue.index (12-32)
    this.tract.tongue.index = this.tract.tongue.range.index.minValue + 
                               params.tongueIndex * (this.tract.tongue.range.index.maxValue - this.tract.tongue.range.index.minValue);
    
    // Map tongueDiameter (0-1) to tongue.diameter (1.0-4.0)
    // Higher diameter = closer to palate = more constricted
    this.tract.tongue.diameter = this.tract.tongue.range.diameter.minValue + 
                                  params.tongueDiameter * (this.tract.tongue.range.diameter.maxValue - this.tract.tongue.range.diameter.minValue);
    
    // Map voicing (0-1) to intensity
    this._intensity = params.voicing;
    
    // Generate tract diameter profile based on tongue position
    this._generateTractProfile();
    
    // Update nasal cavity based on velum (lipRounding can affect this)
    this._updateNasalCavity(params.lipRounding);
    
    // Update amplitudes for wobble effect
    this._updateAmplitudes();
  }

  // Generate tract diameter array based on tongue position
  // PLACEHOLDER: This needs research-based algorithm
  _generateTractProfile() {
    const baseDiameter = 1.5;  // Resting diameter
    const tongueIdx = this.tract.tongue.index;
    const tongueDia = this.tract.tongue.diameter;
    
    for (let i = 0; i < this.tract.length; i++) {
      // Distance from tongue center
      const distance = Math.abs(i - tongueIdx);
      
      // Tongue influence falls off with distance
      const influence = Math.max(0, 1 - distance / 8);
      
      // Calculate diameter at this point
      // Higher tongue diameter = smaller tract diameter (more constriction)
      let diameter = baseDiameter - influence * (tongueDia - 1.0) * 0.5;
      
      // Ensure minimum diameter
      diameter = Math.max(0.1, diameter);
      
      this.tract.diameter[i] = diameter;
    }
    
    // Set fixed points
    this.tract.diameter[0] = 0.6;  // Glottis
    this.tract.diameter[1] = 0.6;  // Near glottis
  }

  // Update nasal cavity opening (velum)
  // lipRounding affects velum opening in this simplified model
  _updateNasalCavity(lipRounding) {
    // Velum diameter (0 = closed, 1 = open)
    // For now, keep it mostly closed unless specifically opened
    const velumOpening = lipRounding > 0.8 ? (lipRounding - 0.8) * 5 : 0;
    
    this.tract.nose.diameter[0] = velumOpening;
    
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

// Phoneme preset definitions
// Format: [tongueIndex, tongueDiameter, lipRounding, voicing]
const PhonemePresets = {
  'i': { name: 'beat', params: { tongueIndex: 0.75, tongueDiameter: 0.9, lipRounding: 0.1, voicing: 1.0 } },
  'ɪ': { name: 'bit', params: { tongueIndex: 0.72, tongueDiameter: 0.7, lipRounding: 0.1, voicing: 1.0 } },
  'e': { name: 'bait', params: { tongueIndex: 0.68, tongueDiameter: 0.6, lipRounding: 0.1, voicing: 1.0 } },
  'æ': { name: 'bat', params: { tongueIndex: 0.60, tongueDiameter: 0.3, lipRounding: 0.2, voicing: 1.0 } },
  'a': { name: 'father', params: { tongueIndex: 0.50, tongueDiameter: 0.2, lipRounding: 0.3, voicing: 1.0 } },
  'ɑ': { name: 'hot', params: { tongueIndex: 0.45, tongueDiameter: 0.25, lipRounding: 0.6, voicing: 1.0 } },
  'ɔ': { name: 'caught', params: { tongueIndex: 0.40, tongueDiameter: 0.4, lipRounding: 0.8, voicing: 1.0 } },
  'o': { name: 'boat', params: { tongueIndex: 0.35, tongueDiameter: 0.7, lipRounding: 0.9, voicing: 1.0 } },
  'ʊ': { name: 'book', params: { tongueIndex: 0.38, tongueDiameter: 0.6, lipRounding: 0.85, voicing: 1.0 } },
  'u': { name: 'boot', params: { tongueIndex: 0.30, tongueDiameter: 0.9, lipRounding: 0.95, voicing: 1.0 } },
  'ə': { name: 'schwa', params: { tongueIndex: 0.55, tongueDiameter: 0.4, lipRounding: 0.4, voicing: 1.0 } },
  'ʌ': { name: 'cup', params: { tongueIndex: 0.48, tongueDiameter: 0.35, lipRounding: 0.3, voicing: 1.0 } },
  'ɝ': { name: 'bird', params: { tongueIndex: 0.52, tongueDiameter: 0.5, lipRounding: 0.4, voicing: 1.0 } },
  
  // Voiceless fricatives (for testing voiceless sounds)
  's': { name: 'sip', params: { tongueIndex: 0.65, tongueDiameter: 0.1, lipRounding: 0.0, voicing: 0.0 } },
  'ʃ': { name: 'ship', params: { tongueIndex: 0.55, tongueDiameter: 0.15, lipRounding: 0.2, voicing: 0.0 } },
  'f': { name: 'fin', params: { tongueIndex: 0.70, tongueDiameter: 0.05, lipRounding: 0.1, voicing: 0.0 } },
  
  // Voiced stops
  'b': { name: 'bat', params: { tongueIndex: 0.65, tongueDiameter: 0.0, lipRounding: 0.0, voicing: 0.0 } },
  'd': { name: 'dad', params: { tongueIndex: 0.55, tongueDiameter: 0.0, lipRounding: 0.0, voicing: 0.0 } },
  'g': { name: 'go', params: { tongueIndex: 0.35, tongueDiameter: 0.0, lipRounding: 0.0, voicing: 0.0 } },
};

// Export for Gradio
window.MockProcessor = MockProcessor;
window.PhonemePresets = PhonemePresets;
