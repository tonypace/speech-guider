// Animation Lab - Interactive vocal tract visualization
// Integrates Pink Trombone drawing with Gradio 5.x

console.log('=== ANIMATION LAB SCRIPT LOADING ===');

// Global Animation Lab instance
window.animationLab = null;

class AnimationLab {
  constructor() {
    this.processor = null;
    this.tractUI = null;
    this.canvas = null;
    this.isRunning = false;
    this.animationId = null;
    
    // Current parameters
    this.params = {
      tongueIndex: 0.5,
      tongueDiameter: 0.5,
      lipRounding: 0.5,
      voicing: 0.5
    };
  }

  init() {
    console.log('Initializing Animation Lab...');
    
    // Find canvas
    this.canvas = document.getElementById('pink-trombone-canvas');
    if (!this.canvas) {
      console.error('Canvas not found: pink-trombone-canvas');
      return false;
    }
    
    // Set canvas size
    this.canvas.width = 600;
    this.canvas.height = 500;
    
    // Create processor
    this.processor = new window.MockProcessor();
    
    // Create TractUI
    this.tractUI = new window.TractUI(this.canvas, this.processor);
    
    // Update with initial params
    this.updateParams(this.params);
    
    // Start animation loop
    this.startAnimation();
    
    console.log('Animation Lab initialized successfully');
    return true;
  }

  updateParams(newParams) {
    // Merge new params
    Object.assign(this.params, newParams);
    
    // Update processor
    if (this.processor) {
      this.processor.updateFromParams(this.params);
    }
    
    // Redraw
    if (this.tractUI) {
      this.tractUI.draw();
    }
  }

  setPhoneme(presetKey) {
    const preset = window.PhonemePresets[presetKey];
    if (!preset) {
      console.error('Unknown phoneme preset:', presetKey);
      return;
    }
    
    console.log('Setting phoneme:', preset.name, preset.params);
    this.updateParams(preset.params);
    
    // Update Gradio sliders if they exist
    this.updateGradioSliders(preset.params);
  }

  updateGradioSliders(params) {
    // Try to find and update Gradio slider components
    const sliderIds = {
      tongueIndex: 'tongue-idx-slider',
      tongueDiameter: 'tongue-dia-slider',
      lipRounding: 'lip-round-slider',
      voicing: 'voicing-slider'
    };
    
    for (const [param, value] of Object.entries(params)) {
      const sliderId = sliderIds[param];
      if (sliderId) {
        const slider = document.getElementById(sliderId);
        if (slider) {
          slider.value = value;
          // Trigger change event
          slider.dispatchEvent(new Event('input'));
        }
      }
    }
  }

  startAnimation() {
    if (this.isRunning) return;
    this.isRunning = true;
    this.animate();
  }

  stopAnimation() {
    this.isRunning = false;
    if (this.animationId) {
      cancelAnimationFrame(this.animationId);
      this.animationId = null;
    }
  }

  animate() {
    if (!this.isRunning) return;
    
    // Redraw (wobble effect updates automatically via Date.now())
    if (this.tractUI) {
      this.tractUI.draw();
    }
    
    this.animationId = requestAnimationFrame(() => this.animate());
  }
}

// Initialize Animation Lab when tab becomes visible
window.initAnimationLab = function() {
  if (window.animationLab) {
    console.log('Animation Lab already initialized');
    return;
  }
  
  // Check if we're on the Animation Lab tab
  const canvas = document.getElementById('pink-trombone-canvas');
  if (!canvas) {
    console.log('Animation Lab canvas not found, will retry...');
    setTimeout(window.initAnimationLab, 500);
    return;
  }
  
  // Check if required classes are loaded
  if (!window.TractUI || !window.MockProcessor) {
    console.log('Pink Trombone classes not loaded yet, will retry...');
    setTimeout(window.initAnimationLab, 500);
    return;
  }
  
  window.animationLab = new AnimationLab();
  window.animationLab.init();
};

// Phoneme button handlers
window.setPhonemePreset = function(phoneme) {
  if (window.animationLab) {
    window.animationLab.setPhoneme(phoneme);
  } else {
    console.error('Animation Lab not initialized');
  }
};

// Parameter update handler from Gradio sliders
window.updateAnimationParams = function(tongueIndex, tongueDiameter, lipRounding, voicing) {
  if (window.animationLab) {
    window.animationLab.updateParams({
      tongueIndex: tongueIndex,
      tongueDiameter: tongueDiameter,
      lipRounding: lipRounding,
      voicing: voicing
    });
  }
};

// Auto-initialization with polling
(function pollForAnimationLab() {
  // Check if we're on the Animation Lab tab by looking for the canvas
  const canvas = document.getElementById('pink-trombone-canvas');
  if (canvas && window.TractUI && window.MockProcessor) {
    console.log('Animation Lab elements found, initializing...');
    window.initAnimationLab();
  } else {
    // Not ready yet, try again
    setTimeout(pollForAnimationLab, 500);
  }
})();

console.log('Animation Lab script loaded');
