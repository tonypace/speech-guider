// Pink Trombone Core - Ported from original by Neil Thapen
// Audio synthesis removed - pure visual demonstration
// For FastAPI web application with interactive UI

class TractUI {
  constructor(canvas, processor) {
    console.log('[TractUI.constructor] Creating with canvas:', canvas, 'processor:', processor);
    this._canvas = canvas;
    this._context = canvas.getContext('2d');
    this._processor = processor;
    
    // Tract geometry (from original Pink Trombone)
    this._tract = {
      origin: { x: 340, y: 460 },
      radius: 298,
      scale: 60,
      scalar: 1,
      angle: {
        scale: 0.64,
        offset: -0.25,
      },
    };
    
    this._isDrawing = false;
    console.log('[TractUI.constructor] Initial processor._params:', processor._params);
    console.log('[TractUI.constructor] Initial processor.tract.tongue:', processor.tract.tongue);
  }

  draw() {
    console.log('[TractUI.draw] Called, _isDrawing:', this._isDrawing);
    if (this._isDrawing) {
      console.log('[TractUI.draw] Already drawing, returning');
      return;
    }
    this._isDrawing = true;
    
    this._context.clearRect(0, 0, this._canvas.width, this._canvas.height);
    this._context.lineCap = this._context.lineJoin = 'round';
    
    console.log('[TractUI.draw] Drawing tongue control, tract, nose, amplitudes');
    this._drawTongueControl();
    this._drawTract();
    this._drawNose();
    this._drawAmplitudes();
    
    this._isDrawing = false;
    console.log('[TractUI.draw] Complete');
  }

  _drawTract() {
    const ctx = this._context;
    const processor = this._processor;
    
    // Main tract - pink fill
    ctx.beginPath();
    ctx.lineWidth = 2;
    ctx.strokeStyle = ctx.fillStyle = 'pink';
    
    // Upper wall - starts at (1, 0) and goes outward following diameters
    this._moveTo(1, 0);
    for (let index = 1; index < processor.tract.length; index++) {
      this._lineTo(index, processor.tract.diameter[index]);
    }
    
    // Lower wall - goes back down to (1, 0) to close the shape
    for (let index = processor.tract.length - 1; index >= 1; index--) {
      this._lineTo(index, 0);
    }
    
    ctx.closePath();
    ctx.stroke();
    ctx.fill();
    
    // Draw constriction line (purple)
    ctx.beginPath();
    ctx.lineWidth = 5;
    ctx.strokeStyle = '#C070C6';
    ctx.lineJoin = ctx.lineCap = 'round';
    
    this._moveTo(1, processor.tract.diameter[0]);
    for (let index = 2; index < processor.tract.length; index++) {
      this._lineTo(index, processor.tract.diameter[index]);
    }
    
    // Lower wall constriction line
    this._moveTo(1, 0);
    for (let index = 2; index <= processor.tract.nose.start - 2; index++) {
      this._lineTo(index, 0);
    }
    
    const velum = processor.tract.nose.diameter[0];
    const velumAngle = velum * 4;
    
    this._moveTo(processor.tract.nose.start + velumAngle - 2, 0);
    for (let index = processor.tract.nose.start + Math.ceil(velumAngle) - 2; 
         index < processor.tract.length; index++) {
      this._lineTo(index, 0);
    }
    
    ctx.stroke();
  }

  _drawNose() {
    const ctx = this._context;
    const processor = this._processor;
    const velum = processor.tract.nose.diameter[0];
    const velumAngle = velum * 4;
    
    // Nasal cavity fill
    ctx.beginPath();
    ctx.lineWidth = 2;
    ctx.strokeStyle = ctx.fillStyle = 'pink';
    this._moveTo(processor.tract.nose.start, -processor.tract.nose.offset);
    
    for (let index = 1; index < processor.tract.nose.length; index++) {
      this._lineTo(
        index + processor.tract.nose.start,
        -processor.tract.nose.offset - processor.tract.nose.diameter[index] * 0.9
      );
    }
    
    for (let index = processor.tract.nose.length - 1; index >= 1; index--) {
      this._lineTo(index + processor.tract.nose.start, -processor.tract.nose.offset);
    }
    
    ctx.closePath();
    ctx.fill();
    
    // Velum connection
    ctx.beginPath();
    ctx.lineWidth = 2;
    ctx.strokeStyle = ctx.fillStyle = 'pink';
    this._moveTo(processor.tract.nose.start - 2, 0);
    this._lineTo(processor.tract.nose.start, -processor.tract.nose.offset);
    this._lineTo(processor.tract.nose.start + velumAngle, -processor.tract.nose.offset);
    this._lineTo(processor.tract.nose.start + velumAngle - 2, 0);
    ctx.closePath();
    ctx.stroke();
    ctx.fill();
    
    // Nasal constriction line
    ctx.beginPath();
    ctx.lineWidth = 5;
    ctx.strokeStyle = '#C070C6';
    ctx.lineJoin = 'round';
    
    this._moveTo(processor.tract.nose.start, -processor.tract.nose.offset);
    for (let index = 1; index < processor.tract.nose.length; index++) {
      this._lineTo(
        index + processor.tract.nose.start,
        -processor.tract.nose.offset - processor.tract.nose.diameter[index] * 0.9
      );
    }
    
    this._moveTo(processor.tract.nose.start + velumAngle, -processor.tract.nose.offset);
    for (let index = Math.ceil(velumAngle); index < processor.tract.nose.length; index++) {
      this._lineTo(index + processor.tract.nose.start, -processor.tract.nose.offset);
    }
    
    ctx.stroke();
    
    // Velum line with alpha based on opening
    ctx.globalAlpha = velum * 5;
    ctx.beginPath();
    this._moveTo(processor.tract.nose.start - 2, 0);
    this._lineTo(processor.tract.nose.start, -processor.tract.nose.offset);
    this._lineTo(processor.tract.nose.start + velumAngle, -processor.tract.nose.offset);
    this._lineTo(processor.tract.nose.start + velumAngle - 2, 0);
    ctx.stroke();
    ctx.globalAlpha = 1;
  }

  _drawTongueControl() {
    const ctx = this._context;
    const processor = this._processor;
    
    ctx.lineCap = ctx.lineJoin = 'round';
    ctx.strokeStyle = ctx.fillStyle = '#FFEEF5'; // palePink
    ctx.globalAlpha = 1.0;
    ctx.beginPath();
    ctx.lineWidth = 45;
    
    // Draw tongue control area
    this._moveTo(processor.tract.tongue.range.index.minValue, processor.tract.tongue.range.diameter.minValue);
    for (let index = processor.tract.tongue.range.index.minValue + 1; 
         index <= processor.tract.tongue.range.index.maxValue; index++) {
      this._lineTo(index, processor.tract.tongue.range.diameter.minValue);
    }
    this._lineTo(processor.tract.tongue.range.index.center, processor.tract.tongue.range.diameter.maxValue);
    ctx.closePath();
    ctx.stroke();
    ctx.fill();
    
    // Draw control points
    ctx.fillStyle = 'orchid';
    ctx.globalAlpha = 0.3;
    
    [0, -4.25, -8.5, 4.25, 8.5, -6.1, 6.1, 0, 0].forEach((indexOffset, _index) => {
      const diameter = _index < 5
        ? processor.tract.tongue.range.diameter.minValue
        : _index < 8
        ? processor.tract.tongue.range.diameter.center
        : processor.tract.tongue.range.diameter.maxValue;
      
      indexOffset *= processor.tract.length / 44;
      this._drawCircle(processor.tract.tongue.range.index.center + indexOffset, diameter, 3);
    });
    
    // Draw current tongue position
    const tongueAngle = this._getAngle(processor.tract.tongue.index);
    const tongueRadius = this._getRadius(processor.tract.tongue.index, processor.tract.tongue.diameter);
    
    ctx.lineWidth = 4;
    ctx.strokeStyle = 'orchid';
    ctx.globalAlpha = 0.7;
    ctx.beginPath();
    ctx.arc(this._getX(tongueAngle, tongueRadius), this._getY(tongueAngle, tongueRadius), 18, 0, 2 * Math.PI);
    ctx.stroke();
    ctx.globalAlpha = 0.15;
    ctx.fill();
    ctx.globalAlpha = 1;
    ctx.fillStyle = 'orchid';
  }

  _drawAmplitudes() {
    const ctx = this._context;
    const processor = this._processor;
    
    ctx.strokeStyle = 'orchid';
    ctx.lineCap = 'butt';
    ctx.globalAlpha = 0.3;
    
    // Oral tract amplitudes
    for (let index = 2; index < processor.tract.length - 1; index++) {
      ctx.beginPath();
      ctx.lineWidth = Math.sqrt(processor.tract.amplitude.max[index]) * 3;
      
      this._moveTo(index, 0);
      this._lineTo(index, processor.tract.diameter[index]);
      
      ctx.stroke();
    }
    
    // Nasal cavity amplitudes
    for (let index = 1; index < processor.tract.nose.length - 1; index++) {
      ctx.beginPath();
      ctx.lineWidth = Math.sqrt(processor.tract.nose.amplitude.max[index]) * 3;
      
      this._moveTo(processor.tract.nose.start + index, -processor.tract.nose.offset);
      this._lineTo(
        processor.tract.nose.start + index,
        -processor.tract.nose.offset - processor.tract.nose.diameter[index] * 0.9
      );
      
      ctx.stroke();
    }
    
    ctx.globalAlpha = 1;
  }

  _drawCircle(index, diameter, arcRadius) {
    const angle = this._getAngle(index);
    const radius = this._getRadius(index, diameter);
    
    this._context.beginPath();
    this._context.arc(this._getX(angle, radius), this._getY(angle, radius), arcRadius, 0, 2 * Math.PI);
    this._context.fill();
  }

  // Polar coordinate transformations (from original Pink Trombone)
  _getAngle(index) {
    return this._tract.angle.offset + 
           (index * this._tract.angle.scale * Math.PI) / (this._processor.tract.lip.start - 1);
  }

  _getWobble(index) {
    let wobble = this._processor.tract.amplitude.max[this._processor.tract.length - 1] +
                 this._processor.tract.nose.amplitude.max[this._processor.tract.nose.length - 1];
    wobble *= (0.03 * Math.sin(2 * index - 50 * (Date.now() / 1000)) * index) / this._processor.tract.length;
    return wobble;
  }

  _getRadius(index, diameter) {
    return this._tract.radius - this._tract.scale * diameter;
  }

  _getX(angle, radius) {
    return this._tract.origin.x - radius * Math.cos(angle);
  }

  _getY(angle, radius) {
    return this._tract.origin.y - radius * Math.sin(angle);
  }

  _moveTo(index, diameter) {
    this.__to(index, diameter, true);
  }

  _lineTo(index, diameter) {
    this.__to(index, diameter, false);
  }

  __to(index, diameter, moveTo) {
    const wobble = this._getWobble(index);
    const angle = this._getAngle(index) + wobble;
    const radius = this._getRadius(index, diameter) + 100 * wobble;
    
    const x = this._getX(angle, radius);
    const y = this._getY(angle, radius);
    
    if (moveTo) this._context.moveTo(x, y);
    else this._context.lineTo(x, y);
  }

  // Animation support
  setParameters(params) {
    console.log('[TractUI.setParameters] Called with:', params);
    // Store target parameters for interpolation
    this._targetParams = params;
    this._animationProgress = 0;
    this._isAnimating = false;
    
    // Store current params as starting point
    this._startParams = {
      tongueIndex: this._processor._params.tongueIndex,
      tongueDiameter: this._processor._params.tongueDiameter,
      lipRounding: this._processor._params.lipRounding,
      voicing: this._processor._params.voicing
    };
    console.log('[TractUI.setParameters] startParams:', this._startParams);
    console.log('[TractUI.setParameters] _targetParams:', this._targetParams);
  }

  startAnimation() {
    console.log('[TractUI.startAnimation] Called');
    console.log('[TractUI.startAnimation] _isAnimating:', this._isAnimating);
    console.log('[TractUI.startAnimation] _targetParams:', this._targetParams);
    if (this._isAnimating) {
      console.log('[TractUI.startAnimation] Already animating, returning');
      return;
    }
    if (!this._targetParams) {
      console.log('[TractUI.startAnimation] No target params, returning');
      return;
    }
    
    this._isAnimating = true;
    this._animationProgress = 0;
    console.log('[TractUI.startAnimation] Starting animation loop');
    this._animate();
  }

  _animate() {
    if (!this._isAnimating) {
      console.log('[TractUI._animate] Animation stopped');
      return;
    }
    
    const duration = 30; // frames (60fps = 0.5 seconds)
    
    if (this._animationProgress < duration) {
      this._animationProgress++;
      console.log(`[TractUI._animate] Frame ${this._animationProgress}/${duration}`);
      
      // Ease-in-out function
      const t = this._animationProgress / duration;
      const easedT = t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2;
      
      // Interpolate parameters
      const currentParams = {
        tongueIndex: this._lerp(this._startParams.tongueIndex, this._targetParams.tongueIndex, easedT),
        tongueDiameter: this._lerp(this._startParams.tongueDiameter, this._targetParams.tongueDiameter, easedT),
        lipRounding: this._lerp(this._startParams.lipRounding, this._targetParams.lipRounding, easedT),
        voicing: this._lerp(this._startParams.voicing, this._targetParams.voicing, easedT)
      };
      
      console.log(`[TractUI._animate] Interpolated params:`, currentParams);
      
      // Update processor
      this._processor.updateFromParams(currentParams);
      
      // Draw
      this.draw();
      
      // Continue animation
      requestAnimationFrame(() => this._animate());
    } else {
      // Animation complete
      console.log('[TractUI._animate] Animation complete, final draw');
      this._isAnimating = false;
      this._processor.updateFromParams(this._targetParams);
      this.draw();
    }
  }

  _lerp(start, end, t) {
    return start + (end - start) * t;
  }
}

// Export for Gradio
window.TractUI = TractUI;
