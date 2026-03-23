// Simplified Pink Trombone - Visual-only vocal tract animator
// Based on the original Pink Trombone by Neil Thapen
// Audio synthesis removed - pure visual demonstration

class VocalTract {
    constructor(canvas) {
        this.canvas = canvas;
        this.ctx = canvas.getContext('2d');
        this.width = canvas.width;
        this.height = canvas.height;
        
        // Animation state
        this.currentParams = this.getRestingParams();
        this.targetParams = this.getRestingParams();
        this.animationProgress = 0;
        this.isAnimating = false;
        this.highlightZone = null;
        this.highlightIntensity = 0;
        this.highlightDirection = 1;
    }

    getRestingParams() {
        return {
            tongueIndex: 0.5,
            tongueDiameter: 0.5,
            lipRounding: 0.5,
            voicing: 0.5
        };
    }

    setParameters(params) {
        this.targetParams = {
            tongueIndex: params.tongueIndex,
            tongueDiameter: params.tongueDiameter,
            lipRounding: params.lipRounding,
            voicing: params.voicing
        };
    }

    setHighlightZone(zone) {
        this.highlightZone = zone;
        this.highlightIntensity = 0;
        this.highlightDirection = 1;
    }

    startAnimation() {
        this.animationProgress = 0;
        this.isAnimating = true;
        this.animate();
    }

    animate() {
        if (!this.isAnimating) return;

        // Animation duration in frames (60fps)
        const animationDuration = 30;
        
        if (this.animationProgress < animationDuration) {
            this.animationProgress++;
            
            // Ease-in-out function
            const t = this.animationProgress / animationDuration;
            const easedT = t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2;
            
            // Interpolate parameters
            this.currentParams = {
                tongueIndex: this.lerp(this.getRestingParams().tongueIndex, this.targetParams.tongueIndex, easedT),
                tongueDiameter: this.lerp(this.getRestingParams().tongueDiameter, this.targetParams.tongueDiameter, easedT),
                lipRounding: this.lerp(this.getRestingParams().lipRounding, this.targetParams.lipRounding, easedT),
                voicing: this.lerp(this.getRestingParams().voicing, this.targetParams.voicing, easedT)
            };
            
            this.draw();
            requestAnimationFrame(() => this.animate());
        } else {
            this.currentParams = {...this.targetParams};
            this.draw();
        }
    }

    lerp(start, end, t) {
        return start + (end - start) * t;
    }

    draw() {
        const ctx = this.ctx;
        
        // Clear canvas
        ctx.clearRect(0, 0, this.width, this.height);
        
        // Update highlight intensity (pulsing effect)
        if (this.highlightZone) {
            this.highlightIntensity += 0.08 * this.highlightDirection;
            if (this.highlightIntensity > 1) {
                this.highlightIntensity = 1;
                this.highlightDirection = -1;
            } else if (this.highlightIntensity < 0.3) {
                this.highlightIntensity = 0.3;
                this.highlightDirection = 1;
            }
        }
        
        // Draw vocal tract cross-section
        this.drawTract();
        this.drawTongue();
        this.drawLips();
        this.drawGlottis();
        
        // Draw highlight if active
        if (this.highlightZone) {
            this.drawHighlight();
        }
    }

    drawTract() {
        const ctx = this.ctx;
        const centerY = this.height / 2;
        const tractWidth = this.width * 0.8;
        const tractHeight = this.height * 0.6;
        const startX = (this.width - tractWidth) / 2;
        
        // Draw outer wall of vocal tract
        ctx.fillStyle = '#e8d4c3';
        ctx.strokeStyle = '#c9b8a5';
        ctx.lineWidth = 2;
        
        ctx.beginPath();
        ctx.moveTo(startX, centerY - tractHeight / 2);
        ctx.lineTo(startX + tractWidth, centerY - tractHeight * 0.3);
        ctx.lineTo(startX + tractWidth, centerY + tractHeight * 0.6);
        ctx.lineTo(startX + tractWidth * 0.2, centerY + tractHeight / 2);
        ctx.closePath();
        ctx.fill();
        ctx.stroke();
        
        // Draw nasal cavity area
        ctx.beginPath();
        ctx.moveTo(startX + tractWidth * 0.4, centerY - tractHeight * 0.3);
        ctx.quadraticCurveTo(
            startX + tractWidth * 0.5, centerY - tractHeight * 0.6,
            startX + tractWidth * 0.7, centerY - tractHeight * 0.3
        );
        ctx.strokeStyle = '#d4c4b3';
        ctx.stroke();
    }

    drawTongue() {
        const ctx = this.ctx;
        const centerY = this.height / 2;
        const tongueLength = this.width * 0.35;
        const tongueHeight = this.height * 0.2;
        const startX = (this.width - tongueLength) / 2;
        
        // Calculate tongue position based on parameters
        const tongueX = startX + this.currentParams.tongueIndex * tongueLength * 0.8;
        const tongueY = centerY + (1 - this.currentParams.tongueDiameter) * (this.height * 0.25);
        const tongueConstriction = 1 - this.currentParams.tongueDiameter;
        
        // Draw tongue
        ctx.fillStyle = '#d4a5a5';
        ctx.strokeStyle = '#c49494';
        ctx.lineWidth = 2;
        
        ctx.beginPath();
        
        // Tongue base (attached to bottom of mouth)
        ctx.moveTo(startX, centerY + this.height * 0.2);
        
        // Tongue body rising up based on constriction
        const controlX1 = startX + tongueLength * 0.3;
        const controlY1 = centerY + this.height * 0.2 - tongueHeight * 0.3;
        const targetX = tongueX;
        const targetY = tongueY;
        
        ctx.quadraticCurveTo(controlX1, controlY1, targetX, targetY);
        
        // Tongue tip
        const tipX = targetX + tongueLength * 0.15;
        const tipY = targetY + tongueHeight * 0.2;
        ctx.quadraticCurveTo(targetX + tongueLength * 0.1, targetY + tongueHeight * 0.4, tipX, tipY);
        
        // Back to base
        ctx.quadraticCurveTo(startX + tongueLength * 0.2, centerY + this.height * 0.25, startX, centerY + this.height * 0.2);
        
        ctx.fill();
        ctx.stroke();
    }

    drawLips() {
        const ctx = this.ctx;
        const centerX = this.width * 0.9;
        const centerY = this.height / 2;
        
        // Calculate lip shape based on rounding parameter
        const lipWidth = 30 + (1 - this.currentParams.lipRounding) * 20;
        const lipHeight = 10 + this.currentParams.lipRounding * 10;
        
        // Draw upper lip
        ctx.fillStyle = '#c9a090';
        ctx.beginPath();
        ctx.ellipse(centerX, centerY - lipHeight, lipWidth / 2, lipHeight / 3, 0, 0, Math.PI * 2);
        ctx.fill();
        
        // Draw lower lip
        ctx.beginPath();
        ctx.ellipse(centerX, centerY + lipHeight, lipWidth / 2, lipHeight / 2, 0, 0, Math.PI * 2);
        ctx.fill();
        
        // Draw opening between lips
        ctx.fillStyle = '#800000';
        ctx.beginPath();
        const openingWidth = lipWidth * (0.5 + this.currentParams.tongueDiameter * 0.5);
        ctx.beginPath();
        ctx.ellipse(centerX, centerY, openingWidth / 2, 3, 0, 0, Math.PI * 2);
        ctx.fill();
    }

    drawGlottis() {
        const ctx = this.ctx;
        const centerX = this.width * 0.15;
        const centerY = this.height / 2;
        
        // Draw epiglottis
        ctx.fillStyle = '#d4a090';
        ctx.beginPath();
        ctx.moveTo(centerX, centerY - 20);
        ctx.quadraticCurveTo(centerX - 15, centerY, centerX, centerY + 20);
        ctx.quadraticCurveTo(centerX + 15, centerY, centerX, centerY - 20);
        ctx.fill();
        
        // Draw vocal cords area
        const voicing = this.currentParams.voicing;
        const cordGap = 8 * (1 - voicing);
        
        ctx.fillStyle = voicing > 0.5 ? '#c04040' : '#808080';
        
        // Left vocal cord
        ctx.beginPath();
        ctx.ellipse(centerX - 5 - cordGap / 2, centerY, 4, 6, 0, 0, Math.PI * 2);
        ctx.fill();
        
        // Right vocal cord
        ctx.beginPath();
        ctx.ellipse(centerX + 5 + cordGap / 2, centerY, 4, 6, 0, 0, Math.PI * 2);
        ctx.fill();
    }

    drawHighlight() {
        if (!this.highlightZone || this.highlightIntensity <= 0) return;
        
        const ctx = this.ctx;
        const centerY = this.height / 2;
        
        // Amber aura
        ctx.shadowColor = `rgba(255, 191, 0, ${this.highlightIntensity})`;
        ctx.shadowBlur = 20 + this.highlightIntensity * 15;
        ctx.strokeStyle = `rgba(255, 191, 0, ${this.highlightIntensity * 0.8})`;
        ctx.lineWidth = 3 + this.highlightIntensity * 2;
        
        switch (this.highlightZone) {
            case 'lips':
                // Draw circle around lips
                ctx.beginPath();
                ctx.arc(this.width * 0.9, centerY, 40, 0, Math.PI * 2);
                ctx.stroke();
                break;
                
            case 'tongue_tip':
                // Draw circle around tongue tip area
                const tongueTipX = (this.width * 0.5) + this.currentParams.tongueIndex * (this.width * 0.35);
                const tongueTipY = centerY + (1 - this.currentParams.tongueDiameter) * (this.height * 0.25) + 20;
                ctx.beginPath();
                ctx.arc(tongueTipX, tongueTipY, 30, 0, Math.PI * 2);
                ctx.stroke();
                break;
                
            case 'tongue_body':
                // Draw circle around tongue body
                const tongueBodyX = (this.width * 0.4) + this.currentParams.tongueIndex * (this.width * 0.25);
                const tongueBodyY = centerY + (1 - this.currentParams.tongueDiameter) * (this.height * 0.25);
                ctx.beginPath();
                ctx.arc(tongueBodyX, tongueBodyY, 40, 0, Math.PI * 2);
                ctx.stroke();
                break;
                
            case 'glottis':
                // Draw circle around glottis
                ctx.beginPath();
                ctx.arc(this.width * 0.15, centerY, 35, 0, Math.PI * 2);
                ctx.stroke();
                break;
        }
        
        // Reset shadow
        ctx.shadowColor = 'transparent';
        ctx.shadowBlur = 0;
        ctx.strokeStyle = 'black';
        ctx.lineWidth = 2;
    }
}

// Global animation loop for highlighting
let animationId = null;

function startHighlightAnimation(tract) {
    if (animationId) {
        cancelAnimationFrame(animationId);
    }
    
    function animateHighlight() {
        if (tract.highlightZone) {
            tract.draw();
            animationId = requestAnimationFrame(animateHighlight);
        }
    }
    
    animateHighlight();
}

// Global state for vocal tract visualization
window.leftTract = null;
window.rightTract = null;
window.currentAnimationParams = { left: {}, right: {} };
window.currentHighlightParams = { zone: null };

// Update vocal tract descriptions and animation params
window.updateVocalTractDescriptions = function(incorrectHtml, correctHtml, animationJson, highlightJson) {
    // Update text descriptions
    const leftDesc = document.getElementById('left-description');
    const rightDesc = document.getElementById('right-description');
    const leftPhoneme = document.getElementById('left-phoneme');
    const rightPhoneme = document.getElementById('right-phoneme');
    
    if (leftDesc) leftDesc.innerHTML = incorrectHtml || "No error selected";
    if (rightDesc) rightDesc.innerHTML = correctHtml || "No error selected";
    
    // Extract phonemes from HTML
    const leftMatch = incorrectHtml ? incorrectHtml.match(/\/([^\/]+)\//) : null;
    const rightMatch = correctHtml ? correctHtml.match(/\/([^\/]+)\//) : null;
    
    if (leftMatch && leftPhoneme) leftPhoneme.textContent = leftMatch[1];
    if (rightMatch && rightPhoneme) rightPhoneme.textContent = rightMatch[1];
    
    // Parse animation params
    try {
        if (animationJson && typeof animationJson === 'string' && animationJson.trim().length > 0) {
            const params = JSON.parse(animationJson);
            if (params && params.left) window.currentAnimationParams.left = params.left;
            if (params && params.right) window.currentAnimationParams.right = params.right;
        }
    } catch (e) {
        console.error('Failed to parse animation JSON:', e);
    }
    
    // Parse highlight params
    try {
        if (highlightJson && typeof highlightJson === 'string' && highlightJson.trim().length > 0) {
            const highlight = JSON.parse(highlightJson);
            if (highlight && highlight.zone) window.currentHighlightParams.zone = highlight.zone;
        }
    } catch (e) {
        console.error('Failed to parse highlight JSON:', e);
    }
    
    // Draw updated tracts
    if (window.leftTract) window.leftTract.draw();
    if (window.rightTract) window.rightTract.draw();
};

// Animation triggers for vocal tract panels
window.animateLeft = function() {
    if (window.leftTract && window.currentAnimationParams.left) {
        window.leftTract.setHighlightZone(null);
        window.leftTract.setParameters(window.currentAnimationParams.left);
        window.leftTract.startAnimation();
    }
};

window.animateRight = function() {
    if (window.rightTract && window.currentAnimationParams.right) {
        window.rightTract.setHighlightZone(window.currentHighlightParams.zone);
        window.rightTract.setParameters(window.currentAnimationParams.right);
        window.rightTract.startAnimation();
    }
};

// Initialize vocal tracts when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    const leftCanvas = document.getElementById('vocal-tract-left');
    const rightCanvas = document.getElementById('vocal-tract-right');
    
    if (leftCanvas && typeof VocalTract !== 'undefined') {
        window.leftTract = new VocalTract(leftCanvas);
        window.leftTract.draw();
    }
    
    if (rightCanvas && typeof VocalTract !== 'undefined') {
        window.rightTract = new VocalTract(rightCanvas);
        window.rightTract.draw();
    }
});

// Export for Gradio integration
window.VocalTract = VocalTract;
window.startHighlightAnimation = startHighlightAnimation;
