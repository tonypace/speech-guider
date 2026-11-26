export const DEFAULT_STATE = {
    lip_aperture: 0.25,
    lip_protrusion: 0.71,
    labiodental_retraction: 0,
    tongue_tip_constriction_location: 0.2,
    tongue_tip_constriction_degree: 1,
    lateral_tongue_drop: 0,
    velic_aperture: 0,
    tongue_body_constriction_location: 0.7,
    tongue_body_constriction_degree: 1,
    glottal_aperture: 0,
};

const TIP_DOMAIN_START = 0.0;
const TIP_DOMAIN_MID = 0.135;
const TIP_DOMAIN_END = 0.34;
const BODY_DOMAIN_START = 0.22;
const BODY_DOMAIN_MID = 0.48;
const BODY_DOMAIN_END = 0.88;
const PHARYNX_START = 0.86;
const TEETH = [[50, 265], [53, 256], [56, 247], [60, 239]];
const ALVEOLAR_RIDGE = [[60, 239], [80, 237], [98, 207], [122, 192]];
const HARD_PALATE = [[122, 192], [155, 172], [205, 172], [240, 190]];
const DEFAULT_SOFT_PALATE = [HARD_PALATE[3], [260, 190], [275, 205], [280, 230]];
const DEFAULT_THROAT = [DEFAULT_SOFT_PALATE[3], [290, 270], [300, 320], [300, 350]];
const TONGUE_TIP_REST_DISTANCE = 32;
const TONGUE_BODY_REST_DISTANCE = 36;
const LIP_APERTURE_MAX = 40;
const LIP_PROTRUSION_MAX = 14;
const VELIC_APERTURE_MAX = 40;
const ORAL_REFERENCE_POINT = { x: 190, y: 300 };
const JAW_HINGE_PIVOT = { x: 225, y: 290 };
const FRAME_RENDER_INTERVAL_MS = 33;

function clamp(value, min, max) {
    return Math.max(min, Math.min(max, value));
}

function lerp(start, end, t) {
    return start + (end - start) * t;
}

function normalizedScalar(value, fallback) {
    const numericValue = Number(value);
    if (!Number.isFinite(numericValue)) return fallback;
    return clamp(numericValue, 0, 1);
}

function legacyStateToNormalized(state = {}) {
    const converted = { ...state };
    const divisors = {
        lip_aperture: LIP_APERTURE_MAX,
        lip_protrusion: LIP_PROTRUSION_MAX,
        tongue_tip_constriction_degree: 40,
        lateral_tongue_drop: 40,
        velic_aperture: VELIC_APERTURE_MAX,
        tongue_body_constriction_degree: 30,
        glottal_aperture: 30,
    };
    Object.entries(divisors).forEach(([key, divisor]) => {
        if (!(key in converted)) return;
        const numericValue = Number(converted[key]);
        converted[key] = Number.isFinite(numericValue)
            ? clamp(numericValue / divisor, 0, 1)
            : DEFAULT_STATE[key];
    });
    return converted;
}

function cubicPoint(p0, p1, p2, p3, t) {
    const mt = 1 - t;
    return {
        x: (mt ** 3) * p0.x + 3 * (mt ** 2) * t * p1.x + 3 * mt * (t ** 2) * p2.x + (t ** 3) * p3.x,
        y: (mt ** 3) * p0.y + 3 * (mt ** 2) * t * p1.y + 3 * mt * (t ** 2) * p2.y + (t ** 3) * p3.y,
    };
}

function quadraticPoint(p0, p1, p2, t) {
    const mt = 1 - t;
    return {
        x: (mt ** 2) * p0.x + 2 * mt * t * p1.x + (t ** 2) * p2.x,
        y: (mt ** 2) * p0.y + 2 * mt * t * p1.y + (t ** 2) * p2.y,
    };
}

function distance(a, b) {
    return Math.hypot(b.x - a.x, b.y - a.y);
}

function cubicPath([, first, second, end]) {
    return `C ${first.join(' ')}, ${second.join(' ')}, ${end.join(' ')}`;
}

function cubicLength(curve, steps = 70) {
    const [p0, p1, p2, p3] = curve.map(([x, y]) => ({ x, y }));
    let length = 0;
    let prev = p0;
    for (let index = 1; index <= steps; index += 1) {
        const pt = cubicPoint(p0, p1, p2, p3, index / steps);
        length += distance(prev, pt);
        prev = pt;
    }
    return length;
}

function sampleRoofSection(curves, steps, start, end, startLength = 0) {
    const samples = [];
    let sectionLength = 0;
    for (let curveIndex = 0; curveIndex < curves.length; curveIndex += 1) {
        const [p0, p1, p2, p3] = curves[curveIndex].map(([x, y]) => ({ x, y }));
        const initialStep = curveIndex === 0 ? 0 : 1;
        for (let index = initialStep; index <= steps; index += 1) {
            const point = cubicPoint(p0, p1, p2, p3, index / steps);
            if (samples.length) sectionLength += distance(samples[samples.length - 1], point);
            samples.push({ ...point, length: startLength + sectionLength });
        }
    }
    const denom = sectionLength || 1;
    return {
        samples: samples.map((point, idx) => ({
            ...point,
            position: idx === samples.length - 1 ? end : lerp(start, end, (point.length - startLength) / denom),
        })),
        sectionLength,
        endLength: startLength + sectionLength,
    };
}

function transformJawPoint(x, y, jawTy, jawDeg) {
    if (!jawDeg) return { x, y: y + jawTy };
    const rad = (jawDeg * Math.PI) / 180;
    const cos = Math.cos(rad);
    const sin = Math.sin(rad);
    const dx = x - JAW_HINGE_PIVOT.x;
    const dy = y - JAW_HINGE_PIVOT.y;
    return {
        x: JAW_HINGE_PIVOT.x + dx * cos - dy * sin,
        y: JAW_HINGE_PIVOT.y + dx * sin + dy * cos + jawTy,
    };
}

const DEFAULT_TEETH_LENGTH = cubicLength(TEETH, 70);
const DEFAULT_ALVEOLAR_LENGTH = cubicLength(ALVEOLAR_RIDGE, 70);
const DEFAULT_HARD_PALATE_LENGTH = cubicLength(HARD_PALATE, 70);
const DEFAULT_ANTERIOR_LENGTH = DEFAULT_TEETH_LENGTH + DEFAULT_ALVEOLAR_LENGTH + DEFAULT_HARD_PALATE_LENGTH;
const DEFAULT_CLOSED_TOTAL_LENGTH = (
    DEFAULT_ANTERIOR_LENGTH
      + cubicLength(DEFAULT_SOFT_PALATE, 128)
      + cubicLength(DEFAULT_THROAT, 128)
);
const ALVEOLAR_END = (DEFAULT_TEETH_LENGTH + DEFAULT_ALVEOLAR_LENGTH) / DEFAULT_CLOSED_TOTAL_LENGTH;
const SOFT_PALATE_START = DEFAULT_ANTERIOR_LENGTH / DEFAULT_CLOSED_TOTAL_LENGTH;
const ANTERIOR_ROOF_SECTION = sampleRoofSection([TEETH, ALVEOLAR_RIDGE, HARD_PALATE], 70, 0, SOFT_PALATE_START, 0);
const ANTERIOR_ROOF = ANTERIOR_ROOF_SECTION.samples;
const ANTERIOR_ROOF_LENGTH = ANTERIOR_ROOF_SECTION.endLength;

function createSvgMarkup(prefix) {
    return `
      <svg id="${prefix}-mouth-svg" width="100%" height="100%" class="border rounded bg-gray-50 w-full" viewBox="0 90 310 310">
        <defs>
          <marker id="${prefix}-arrow" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
            <path d="M 0 0 L 10 5 L 0 10 z" fill="#ef4444"></path>
          </marker>
          <pattern id="${prefix}-voicing-pattern" width="12" height="12" patternUnits="userSpaceOnUse" patternTransform="rotate(45 0 0)">
            <line id="${prefix}-voicing-line" x1="0" y1="0" x2="0" y2="12" stroke="#eab308" stroke-width="0" stroke-linecap="round"></line>
          </pattern>
          <clipPath id="${prefix}-oral-voicing-clip">
            <rect id="${prefix}-oral-voicing-clip-rect" x="0" y="0" width="400" height="400"></rect>
          </clipPath>
        </defs>

        <path id="${prefix}-outside-air" fill="#bae6fd" opacity="0.6"></path>
        <path id="${prefix}-nasal-tract-fill" fill="#ffad91" opacity="0.6"></path>
        <path id="${prefix}-oral-tract-fill" fill="#ffb4a2" opacity="0.6"></path>
        <path id="${prefix}-nasal-voicing" fill="url(#${prefix}-voicing-pattern)" pointer-events="none"></path>
        <path id="${prefix}-oral-voicing" fill="url(#${prefix}-voicing-pattern)" clip-path="url(#${prefix}-oral-voicing-clip)" pointer-events="none"></path>
        <path id="${prefix}-palate-tissue" fill="#fda4af" opacity="0.35" pointer-events="none"></path>
        <path id="${prefix}-uvula" fill="#fda4af" stroke="#e11d48" stroke-width="2" stroke-linejoin="round" pointer-events="none"></path>

        <g>
          <g stroke="#334155" stroke-width="6" fill="none" stroke-linecap="round" stroke-linejoin="round">
            <path id="${prefix}-upper-face" d=""></path>
            <path d="M 15 190 C 120 70, 250 70, 280 230 C 290 270, 300 320, 300 350" stroke="#e11d48"></path>
            <path id="${prefix}-nasal-floor" d="M 40 215 C 100 130, 220 140, 240 190" stroke="#e11d48"></path>
            <path id="${prefix}-palate" d="" stroke="#e11d48"></path>
          </g>
        </g>

        <g id="${prefix}-jaw-group">
          <path d="M 60 290 Q 67 296 74 296" fill="none" stroke="#e11d48" stroke-width="6" stroke-linecap="round"></path>
          <path id="${prefix}-lower-face" d="" stroke="#475569" stroke-width="6" fill="none" stroke-linecap="round" stroke-linejoin="round"></path>
        </g>

        <g id="${prefix}-tongue-trail-group" pointer-events="none"></g>
        <path id="${prefix}-tongue" d="" fill="#fb7185" stroke="#e11d48" stroke-width="3" opacity="1.0"></path>
        <path id="${prefix}-tip-contact-arc" d="" fill="none" stroke="#f59e0b" stroke-width="5" stroke-linecap="round" opacity="0" pointer-events="none"></path>
        <path id="${prefix}-body-contact-arc" d="" fill="none" stroke="#f59e0b" stroke-width="5" stroke-linecap="round" opacity="0" pointer-events="none"></path>
        <circle id="${prefix}-lip-contact-seal" cx="46" cy="260" r="5" fill="#f59e0b" stroke="#ffffff" stroke-width="1.5" opacity="0" pointer-events="none"></circle>
        <path id="${prefix}-upper-teeth" d="M 51 242 Q 55.5 234 60 239 C 56 248, 53 256, 50 264 C 48 258, 48.5 250, 51 242 Z" fill="#ffffff" stroke="#000000" stroke-width="1.5" stroke-linejoin="round"></path>
        <g id="${prefix}-lower-teeth-group">
          <path id="${prefix}-lower-teeth" d="M 51 287 Q 55.5 295 60 290 C 56 281, 53 273, 50 265 C 48 271, 48.5 279, 51 287 Z" fill="#ffffff" stroke="#000000" stroke-width="1.5" stroke-linejoin="round"></path>
        </g>
        <path id="${prefix}-roof-track-debug" fill="none" stroke="#10b981" stroke-width="2" stroke-dasharray="4" opacity="0" pointer-events="none"></path>
        <line id="${prefix}-normal-line" x1="0" y1="0" x2="0" y2="0" stroke="#ef4444" stroke-width="1.5" stroke-dasharray="4" marker-end="url(#${prefix}-arrow)"></line>
        <circle id="${prefix}-anchor-point" cx="0" cy="0" r="3" fill="#3b82f6"></circle>
        <g id="${prefix}-wind-icon" stroke="#0f172a" stroke-width="2.5" stroke-linecap="round" fill="none" opacity="0">
          <path d="M 8 -8 H -12 M 8 -8 C 10.2 -8 12 -9.8 12 -12 C 12 -14.2 10.2 -16 8 -16 C 5.8 -16 4 -14.2 4 -12" />
          <path d="M 12 0 H -16 M 12 0 C 14.2 0 16 1.8 16 4 C 16 6.2 14.2 8 12 8 C 9.8 8 8 6.2 8 4" />
          <path d="M 4 8 H -8 M 4 8 C 6.2 8 8 9.8 8 12 C 8 14.2 6.2 16 4 16 C 1.8 16 0 14.2 0 12" />
        </g>
        <g id="${prefix}-anatomy-labels" font-size="9" font-weight="600" fill="#64748b" pointer-events="none" opacity="0.85">
          <text x="6" y="256">Lips</text>
          <text x="148" y="164" text-anchor="middle">Palate</text>
          <text x="278" y="182" text-anchor="middle">Velum</text>
          <text x="160" y="330" text-anchor="middle" fill="#881337" opacity="0.75">Tongue</text>
        </g>
        <g id="${prefix}-larynx-view" transform="translate(260, 385)">
          <text x="0" y="-18" font-size="9" font-weight="bold" text-anchor="middle" fill="#64748b">Glottis</text>
          <circle cx="0" cy="0" r="14" fill="#fb7185" stroke="#334155" stroke-width="2" />
          <polygon id="${prefix}-glottis-hole" fill="#0f172a" points="0,-10 0,10 0,10" />
          <line id="${prefix}-vf-left" x1="0" y1="-10" x2="0" y2="10" stroke="#f8fafc" stroke-width="2" stroke-linecap="round" />
          <line id="${prefix}-vf-right" x1="0" y1="-10" x2="0" y2="10" stroke="#f8fafc" stroke-width="2" stroke-linecap="round" />
        </g>
      </svg>`;
}

export class SvgArticulatoryRenderer {
    constructor(container, options = {}) {
        this.container = container;
        this.prefix = options.prefix || 'svg-articulatory';
        this.state = this._normalizeState({ ...DEFAULT_STATE, ...(options.state || {}) });
        this.highlightZone = options.highlightZone || null;
        this.isRunning = false;
        this.animationId = null;
        this._voicingOffset = 0;
        this._lastFrameRenderAt = 0;
        this._frameDirty = true;
        this._mounted = false;
        this._elements = {};
        
        // History Trail configuration
        this.showHistory = options.showHistory !== false;
        this.maxHistory = options.maxHistory || 20;
        this.history = []; // Stores { tip: {x,y}, body: {x,y} }

        // Exaggerated visual contact configuration
        const ex = options.contactExaggeration || {};
        this.contactExaggeration = {
            enabled: Boolean(ex.enabled ?? options.exaggerateContact ?? false),
            tipFloor: normalizedScalar(ex.tipFloor ?? 0.38, 0.38),
            bodyFloor: normalizedScalar(ex.bodyFloor ?? 0.38, 0.38),
            lipFloor: normalizedScalar(ex.lipFloor ?? 0.39, 0.39),
            knee: normalizedScalar(ex.knee ?? 0.56, 0.56),
            gamma: clamp(Number(ex.gamma ?? 1.85) || 1.85, 0.5, 4.0),
            winnerGain: clamp(Number(ex.winnerGain ?? 1.15) || 1.15, 0, 3.0),
            maxHalfSpan: clamp(Number(ex.maxHalfSpan ?? 0.045) || 0.045, 0.012, 0.09),
            showContactHighlight: ex.showContactHighlight !== false,
        };
    }

    setContactExaggeration(config = {}) {
        const current = this.contactExaggeration || {};
        const next = typeof config === 'boolean' ? { enabled: config } : config;
        this.contactExaggeration = {
            ...current,
            ...next,
            enabled: Boolean(next.enabled ?? current.enabled),
            tipFloor: normalizedScalar(next.tipFloor ?? current.tipFloor, 0.38),
            bodyFloor: normalizedScalar(next.bodyFloor ?? current.bodyFloor, 0.38),
            lipFloor: normalizedScalar(next.lipFloor ?? current.lipFloor, 0.39),
            knee: normalizedScalar(next.knee ?? current.knee, 0.56),
            gamma: clamp(Number(next.gamma ?? current.gamma) || 1.85, 0.5, 4.0),
            winnerGain: clamp(Number(next.winnerGain ?? current.winnerGain) || 1.15, 0, 3.0),
            maxHalfSpan: clamp(Number(next.maxHalfSpan ?? current.maxHalfSpan) || 0.045, 0.012, 0.09),
            showContactHighlight: next.showContactHighlight !== undefined ? Boolean(next.showContactHighlight) : current.showContactHighlight,
        };
        if (this._mounted) this.render();
    }

    mount() {
        if (!this.container || this._mounted) return;
        this.container.innerHTML = createSvgMarkup(this.prefix);
        this._cacheElements();
        this._mounted = true;
        this.render();
    }

    _cacheElements() {
        const ids = [
            'mouth-svg', 'outside-air', 'nasal-tract-fill', 'oral-tract-fill', 'nasal-voicing',
            'oral-voicing', 'oral-voicing-clip-rect', 'palate-tissue', 'uvula',
            'upper-face', 'nasal-floor', 'palate',
            'jaw-group', 'lower-face', 'tongue', 'tongue-trail-group', 'tip-contact-arc', 'body-contact-arc',
            'lip-contact-seal', 'upper-teeth', 'lower-teeth-group', 'lower-teeth',
            'roof-track-debug', 'normal-line', 'anchor-point', 'wind-icon',
            'glottis-hole', 'vf-left', 'vf-right', 'voicing-pattern', 'voicing-line',
            'larynx-view',
        ];
        for (const id of ids) {
            this._elements[id] = this.container.querySelector(`#${this.prefix}-${id}`);
        }
    }

    $(name) {
        return this._elements[name];
    }

    setState(nextState) {
        this.setNormalizedState(nextState);
    }

    setNormalizedState(nextState) {
        this.state = this._normalizeState({ ...this.state, ...nextState });
        this._frameDirty = true;
        if (!this._mounted) this.mount();
        this.render();
    }

    setLegacyState(nextState) {
        this.setNormalizedState(legacyStateToNormalized(nextState));
    }

    setParameters(nextState) {
        this.setState(nextState);
    }

    updateFromSchema(nextState) {
        this.setState(nextState);
    }

    setHighlightZone(zone) {
        this.highlightZone = zone;
        this._frameDirty = true;
        this.render();
    }

    setPhonemePreset(params) {
        this.setState(params);
    }

    startAnimation() {
        if (this.isRunning) return;
        this.isRunning = true;
        const tick = (timestamp) => {
            if (!this.isRunning) return;
            this._renderVoicing(timestamp);
            if (this._frameDirty && (timestamp - this._lastFrameRenderAt >= FRAME_RENDER_INTERVAL_MS)) {
                this._renderFrame();
                this._lastFrameRenderAt = timestamp;
                this._frameDirty = false;
            }
            this.animationId = requestAnimationFrame(tick);
        };
        this.animationId = requestAnimationFrame(tick);
    }

    stopAnimation() {
        this.isRunning = false;
        if (this.animationId) {
            cancelAnimationFrame(this.animationId);
            this.animationId = null;
        }
    }

    destroy() {
        this.stopAnimation();
        if (this.container) this.container.innerHTML = '';
        this._mounted = false;
    }

    render() {
        if (!this._mounted) this.mount();
        this._renderFrame();
        this._lastFrameRenderAt = performance.now();
        this._frameDirty = false;
        this._renderVoicing(performance.now());
    }

    _buildRoofTrack(geometry = this._buildVisiblePalateGeometry(this.state.velic_aperture * VELIC_APERTURE_MAX)) {
        const roofEnd = { x: 300, y: 350 };
        const softPalateSection = sampleRoofSection(
            [geometry.softPalate],
            128,
            SOFT_PALATE_START,
            PHARYNX_START,
            ANTERIOR_ROOF_LENGTH,
        );
        const throatSection = sampleRoofSection(
            [geometry.throat],
            128,
            PHARYNX_START,
            1,
            softPalateSection.endLength,
        );
        const samples = [
            ...ANTERIOR_ROOF,
            ...softPalateSection.samples.slice(1),
            ...throatSection.samples.slice(1),
        ];

        return {
            path: `M ${TEETH[0].join(' ')} ${cubicPath(TEETH)} ${geometry.palateCurves} ${geometry.throatClosure}`,
            samples,
            totalLength: throatSection.endLength,
            end: roofEnd,
        };
    }

    _buildVisiblePalateGeometry(vel) {
        const velFactor = clamp(vel / 40, 0, 1);
        
        const velumEndX = lerp(280, 250, velFactor);
        const velumEndY = lerp(230, 235, velFactor);
        
        const softPalateControl1X = lerp(260, 245, velFactor);
        const softPalateControl1Y = lerp(190, 210, velFactor);
        
        const softPalateControl2X = lerp(275, 248, velFactor);
        const softPalateControl2Y = lerp(205, 225, velFactor);
        
        const throatCurveControl1X = lerp(290, 270, velFactor);
        const throatCurveControl1Y = lerp(270, 280, velFactor);
        
        const throatCurveControl2X = lerp(300, 290, velFactor);
        const throatCurveControl2Y = lerp(320, 320, velFactor);

        const softPalate = [
            HARD_PALATE[3],
            [softPalateControl1X, softPalateControl1Y],
            [softPalateControl2X, softPalateControl2Y],
            [velumEndX, velumEndY],
        ];
        const throat = [
            softPalate[3],
            [throatCurveControl1X, throatCurveControl1Y],
            [throatCurveControl2X, throatCurveControl2Y],
            [300, 350],
        ];
        const palateCurves = [ALVEOLAR_RIDGE, HARD_PALATE, softPalate].map(cubicPath).join(' ');
        const path = `M ${ALVEOLAR_RIDGE[0].join(' ')} ${palateCurves}`;
        const throatClosure = cubicPath(throat);

        return {
            path,
            palateCurves,
            throatClosure,
            softPalate,
            throat,
            velumEndX,
            velumEndY,
            throatCurveControl1X,
            throatCurveControl1Y,
            throatCurveControl2X,
            throatCurveControl2Y,
            softPalateControl1X,
            softPalateControl1Y,
            softPalateControl2X,
            softPalateControl2Y,
        };
    }

    _buildVisiblePalatePath(vel) {
        return this._buildVisiblePalateGeometry(vel).path;
    }

    _normalizeState(state) {
        return {
            ...DEFAULT_STATE,
            ...state,
            lip_aperture: normalizedScalar(state.lip_aperture, DEFAULT_STATE.lip_aperture),
            lip_protrusion: normalizedScalar(state.lip_protrusion, DEFAULT_STATE.lip_protrusion),
            labiodental_retraction: normalizedScalar(state.labiodental_retraction, DEFAULT_STATE.labiodental_retraction),
            tongue_tip_constriction_location: normalizedScalar(state.tongue_tip_constriction_location, DEFAULT_STATE.tongue_tip_constriction_location),
            tongue_tip_constriction_degree: normalizedScalar(state.tongue_tip_constriction_degree, DEFAULT_STATE.tongue_tip_constriction_degree),
            lateral_tongue_drop: normalizedScalar(state.lateral_tongue_drop, DEFAULT_STATE.lateral_tongue_drop),
            velic_aperture: normalizedScalar(state.velic_aperture, DEFAULT_STATE.velic_aperture),
            tongue_body_constriction_location: normalizedScalar(state.tongue_body_constriction_location, DEFAULT_STATE.tongue_body_constriction_location),
            tongue_body_constriction_degree: normalizedScalar(state.tongue_body_constriction_degree, DEFAULT_STATE.tongue_body_constriction_degree),
            glottal_aperture: normalizedScalar(state.glottal_aperture, DEFAULT_STATE.glottal_aperture),
        };
    }

    _sampleRoofTrack(roofTrack, s) {
        const position = clamp(s, 0, 1);
        const samples = roofTrack.samples;
        if (!samples.length) {
            return {
                anchorX: 0,
                anchorY: 0,
                inwardNormalX: 0,
                inwardNormalY: 1,
            };
        }
        let index = samples.findIndex((sample) => sample.position >= position);
        if (index < 0) index = samples.length - 1;
        const upper = samples[index];
        const lower = samples[Math.max(0, index - 1)];
        const next = samples[Math.min(samples.length - 1, index + 1)];
        const previous = samples[Math.max(0, index - 2)];
        const interpolate = upper.position > lower.position;
        const weight = interpolate ? (position - lower.position) / (upper.position - lower.position) : 1;
        const current = {
            x: lerp(lower.x, upper.x, weight),
            y: lerp(lower.y, upper.y, weight),
        };
        const tangentX = lerp(upper.x - previous.x, next.x - lower.x, weight);
        const tangentY = lerp(upper.y - previous.y, next.y - lower.y, weight);
        let normalX = -tangentY;
        let normalY = tangentX;
        const normalLength = Math.hypot(normalX, normalY) || 1;
        normalX /= normalLength;
        normalY /= normalLength;

        const towardOralX = ORAL_REFERENCE_POINT.x - current.x;
        const towardOralY = ORAL_REFERENCE_POINT.y - current.y;
        if ((normalX * towardOralX) + (normalY * towardOralY) < 0) {
            normalX *= -1;
            normalY *= -1;
        }

        return {
            anchorX: current.x,
            anchorY: current.y,
            inwardNormalX: normalX,
            inwardNormalY: normalY,
        };
    }

    _mapLocation(location, domain) {
        const value = clamp(location, 0, 1);
        if (domain === 'tip') {
            if (value <= 0.5) return lerp(TIP_DOMAIN_START, TIP_DOMAIN_MID, value * 2);
            return lerp(TIP_DOMAIN_MID, TIP_DOMAIN_END, (value - 0.5) * 2);
        }
        if (value <= 0.5) return lerp(BODY_DOMAIN_START, BODY_DOMAIN_MID, value * 2);
        return lerp(BODY_DOMAIN_MID, BODY_DOMAIN_END, (value - 0.5) * 2);
    }

    _surfaceForRoofPosition(position) {
        const value = clamp(position, 0, 1);
        if (value < 0.035) return 'upper_teeth';
        if (value < ALVEOLAR_END) return 'alveolar_ridge';
        if (value < SOFT_PALATE_START) return 'hard_palate';
        if (value < PHARYNX_START) return 'velum';
        return 'pharynx';
    }

    _projectInside(anchor, normal, point, minimumDistance = 2) {
        const offsetX = point.x - anchor.x;
        const offsetY = point.y - anchor.y;
        const inwardDistance = (offsetX * normal.x) + (offsetY * normal.y);
        if (inwardDistance >= minimumDistance) return point;
        const correction = minimumDistance - inwardDistance;
        return {
            x: point.x + normal.x * correction,
            y: point.y + normal.y * correction,
        };
    }

    _signedRoofDistance(point, roofTrack) {
        const samples = roofTrack.samples;
        let best = 0;
        let bestDistSq = Infinity;
        for (let i = 0; i < samples.length; i += 1) {
            const dx = samples[i].x - point.x;
            const dy = samples[i].y - point.y;
            const distSq = dx * dx + dy * dy;
            if (distSq < bestDistSq) {
                best = i;
                bestDistSq = distSq;
            }
        }
        const current = samples[best];
        const before = samples[Math.max(0, best - 1)];
        const after = samples[Math.min(samples.length - 1, best + 1)];
        let nx = -(after.y - before.y);
        let ny = after.x - before.x;
        const length = Math.hypot(nx, ny) || 1;
        nx /= length;
        ny /= length;
        if (nx * (ORAL_REFERENCE_POINT.x - current.x) + ny * (ORAL_REFERENCE_POINT.y - current.y) < 0) {
            nx *= -1;
            ny *= -1;
        }
        const sd = (point.x - current.x) * nx + (point.y - current.y) * ny;
        return { sd, nx, ny };
    }

    _constrainSegmentInsideRoof(p0, p1, p2, p3, roofTrack, adjustP1 = true, adjustP2 = true) {
        let c1 = { ...p1 };
        let c2 = { ...p2 };
        const samplesPerPass = 40;
        for (let pass = 0; pass < 6; pass += 1) {
            let adjusted = false;
            for (let step = 1; step < samplesPerPass; step += 1) {
                const t = step / samplesPerPass;
                const pt = cubicPoint(p0, c1, c2, p3, t);
                const { sd, nx, ny } = this._signedRoofDistance(pt, roofTrack);
                if (sd < 0) {
                    const b1 = adjustP1 ? 3 * ((1 - t) ** 2) * t : 0;
                    const b2 = adjustP2 ? 3 * (1 - t) * (t ** 2) : 0;
                    const denom = b1 + b2;
                    if (denom > 1e-6) {
                        const shift = (-sd + 0.15) / denom;
                        if (adjustP1) {
                            c1 = { x: c1.x + nx * shift, y: c1.y + ny * shift };
                        }
                        if (adjustP2) {
                            c2 = { x: c2.x + nx * shift, y: c2.y + ny * shift };
                        }
                        adjusted = true;
                    }
                }
            }
            if (!adjusted) break;
        }
        return [c1, c2];
    }

    _getTonguePoint(location, degree, domain, roofTrack) {
        const roofPosition = this._mapLocation(location, domain);
        const anchor = this._sampleRoofTrack(roofTrack, roofPosition);
        const restDistance = domain === 'tip' ? TONGUE_TIP_REST_DISTANCE : TONGUE_BODY_REST_DISTANCE;
        const normalizedDegree = normalizedScalar(degree, 1);
        const distanceFromRoof = normalizedDegree * restDistance;

        return {
            ...anchor,
            roofPosition,
            surface: this._surfaceForRoofPosition(roofPosition),
            distanceFromRoof,
            targetX: anchor.anchorX + anchor.inwardNormalX * distanceFromRoof,
            targetY: anchor.anchorY + anchor.inwardNormalY * distanceFromRoof,
        };
    }

    _isEffectiveTongueClosure(normalizedDegree, lateralDrop) {
        return normalizedDegree <= 0.03 && lateralDrop < 8;
    }

    _hasTongueSurfaceContact(normalizedDegree) {
        return normalizedDegree <= 0.03;
    }

    _isEffectiveLipClosure(lipAperture) {
        return lipAperture <= 2;
    }

    _contactPatchHandles(point, roofTrack, halfSpan = 0.012) {
        const before = this._sampleRoofTrack(roofTrack, point.roofPosition - halfSpan);
        const after = this._sampleRoofTrack(roofTrack, point.roofPosition + halfSpan);
        const inset = 0.5;
        return {
            before: {
                x: before.anchorX + before.inwardNormalX * inset,
                y: before.anchorY + before.inwardNormalY * inset,
            },
            after: {
                x: after.anchorX + after.inwardNormalX * inset,
                y: after.anchorY + after.inwardNormalY * inset,
            },
        };
    }

    _effectiveDegrees() {
        const s = this.state;
        const rawLa = normalizedScalar(s.lip_aperture, DEFAULT_STATE.lip_aperture);
        const rawTtcd = normalizedScalar(s.tongue_tip_constriction_degree, DEFAULT_STATE.tongue_tip_constriction_degree);
        const rawTbcd = normalizedScalar(s.tongue_body_constriction_degree, DEFAULT_STATE.tongue_body_constriction_degree);
        const ex = this.contactExaggeration;
        if (!ex || !ex.enabled) {
            return {
                la: rawLa,
                ttcd: rawTtcd,
                tbcd: rawTbcd,
                tipHalfSpan: 0.012,
                bodyHalfSpan: 0.012,
            };
        }

        const channels = [
            { key: 'la', val: rawLa, floor: ex.lipFloor },
            { key: 'ttcd', val: rawTtcd, floor: ex.tipFloor },
            { key: 'tbcd', val: rawTbcd, floor: ex.bodyFloor },
        ];
        let dominant = channels[0];
        channels.forEach((c) => {
            if ((c.val - c.floor) < (dominant.val - dominant.floor)) dominant = c;
        });
        const othersMean = channels
            .filter((c) => c.key !== dominant.key)
            .reduce((acc, c) => acc + c.val, 0) / 2;

        const mapDegree = (val, floor, isDominant) => {
            const lead = (isDominant && val < ex.knee) ? Math.max(0, othersMean - val) : 0;
            const eff = val - ex.winnerGain * lead;
            if (eff <= floor) return 0;
            const knee = Math.max(floor + 0.02, ex.knee);
            if (eff <= knee) {
                return 0.5 * (((eff - floor) / (knee - floor)) ** ex.gamma);
            }
            return clamp(0.5 + 0.5 * ((eff - knee) / Math.max(0.02, 1 - knee)), 0, 1);
        };

        const la = mapDegree(rawLa, ex.lipFloor, dominant.key === 'la');
        const ttcd = mapDegree(rawTtcd, ex.tipFloor, dominant.key === 'ttcd');
        const tbcd = mapDegree(rawTbcd, ex.bodyFloor, dominant.key === 'tbcd');

        const squashSpan = (rawVal, floor, effVal) => {
            if (effVal > 0.03) return 0.012;
            const depth = clamp((floor - rawVal + 0.06) / 0.16, 0, 1);
            return lerp(0.024, ex.maxHalfSpan, depth);
        };

        return {
            la,
            ttcd,
            tbcd,
            tipHalfSpan: squashSpan(rawTtcd, ex.tipFloor, ttcd),
            bodyHalfSpan: squashSpan(rawTbcd, ex.bodyFloor, tbcd),
        };
    }

    _buildRoofArcPath(roofTrack, centerPosition, halfSpan) {
        const startPos = clamp(centerPosition - halfSpan, 0, 1);
        const endPos = clamp(centerPosition + halfSpan, 0, 1);
        const steps = 12;
        const pts = [];
        for (let i = 0; i <= steps; i += 1) {
            const pos = lerp(startPos, endPos, i / steps);
            const s = this._sampleRoofTrack(roofTrack, pos);
            pts.push(`${i === 0 ? 'M' : 'L'} ${s.anchorX.toFixed(2)} ${s.anchorY.toFixed(2)}`);
        }
        return pts.join(' ');
    }

    geometrySnapshot() {
        const roofTrack = this._buildRoofTrack();
        const eff = this._effectiveDegrees();
        const tip = this._getTonguePoint(
            this.state.tongue_tip_constriction_location,
            eff.ttcd,
            'tip',
            roofTrack,
        );
        const body = this._getTonguePoint(
            this.state.tongue_body_constriction_location,
            eff.tbcd,
            'body',
            roofTrack,
        );
        const lateral = this.state.lateral_tongue_drop * 40;
        return {
            tip: {
                gap: tip.distanceFromRoof,
                roofPosition: tip.roofPosition,
                surface: tip.surface,
                surfaceContact: tip.distanceFromRoof <= 0.5,
                strokeOverlap: tip.distanceFromRoof <= 4.5,
                airwayClosure: this._isEffectiveTongueClosure(eff.ttcd, lateral),
            },
            body: {
                gap: body.distanceFromRoof,
                roofPosition: body.roofPosition,
                surface: body.surface,
                surfaceContact: body.distanceFromRoof <= 0.5,
                strokeOverlap: body.distanceFromRoof <= 4.5,
                airwayClosure: this._isEffectiveTongueClosure(eff.tbcd, lateral),
            },
        };
    }

    _getOralVoicingClipX({ lipAperture, lipProtrusion, lateralDrop, ttcd, tbcd, tip, body }) {
        let clipX = 0;

        if (this._isEffectiveLipClosure(lipAperture)) {
            clipX = Math.max(clipX, 52 - lipProtrusion * 0.2);
        }

        if (this._isEffectiveTongueClosure(ttcd, lateralDrop)) {
            clipX = Math.max(clipX, tip.anchorX);
        }

        if (this._isEffectiveTongueClosure(tbcd, lateralDrop)) {
            clipX = Math.max(clipX, body.anchorX);
        }

        return clipX;
    }

    _renderFrame() {
        const s = this.state;
        const jaw = this.$('jaw-group');
        const lowerTeeth = this.$('lower-teeth-group');
        const upperFace = this.$('upper-face');
        const lowerFace = this.$('lower-face');
        const palate = this.$('palate');
        const palateTissue = this.$('palate-tissue');
        const uvula = this.$('uvula');
        const tongue = this.$('tongue');
        const roofTrackDebug = this.$('roof-track-debug');
        const outsideAir = this.$('outside-air');
        const nasalTractFill = this.$('nasal-tract-fill');
        const oralTractFill = this.$('oral-tract-fill');
        const nasalVoicing = this.$('nasal-voicing');
        const oralVoicing = this.$('oral-voicing');
        const clipRect = this.$('oral-voicing-clip-rect');
        const anchor = this.$('anchor-point');
        const normalLine = this.$('normal-line');
        const wind = this.$('wind-icon');
        const glottisHole = this.$('glottis-hole');
        const vfLeft = this.$('vf-left');
        const vfRight = this.$('vf-right');
        const larynxView = this.$('larynx-view');

        const tipContactArc = this.$('tip-contact-arc');
        const bodyContactArc = this.$('body-contact-arc');
        const lipContactSeal = this.$('lip-contact-seal');

        const eff = this._effectiveDegrees();
        const la = eff.la * LIP_APERTURE_MAX;
        const lpOffset = s.lip_protrusion >= 0.5
            ? lerp(0, LIP_PROTRUSION_MAX, (s.lip_protrusion - 0.5) * 2)
            : lerp(-4, 0, s.lip_protrusion * 2);
        const ldr = s.labiodental_retraction;
        const ttcl = clamp(s.tongue_tip_constriction_location, 0, 1);
        const ttcd = eff.ttcd;
        const lat = s.lateral_tongue_drop * 40;
        const vel = s.velic_aperture * VELIC_APERTURE_MAX;
        const tbcl = clamp(s.tongue_body_constriction_location, 0, 1);
        const tbcd = eff.tbcd;
        const glo = s.glottal_aperture * 30;
        const visiblePalateGeometry = this._buildVisiblePalateGeometry(vel);
        const roofTrack = this._buildRoofTrack(visiblePalateGeometry);
        const {
            path: visiblePalatePath,
            throatClosure,
            velumEndX,
            velumEndY,
            throatCurveControl1X,
            throatCurveControl1Y,
            throatCurveControl2X,
            throatCurveControl2Y,
            softPalateControl1X,
            softPalateControl1Y,
            softPalateControl2X,
            softPalateControl2Y,
        } = visiblePalateGeometry;

        const jawTy = la * 0.7;
        const jawDeg = -la * 0.12;
        const jawTransform = jawDeg === 0
            ? `translate(0, ${jawTy})`
            : `translate(0, ${jawTy.toFixed(2)}) rotate(${jawDeg.toFixed(2)}, ${JAW_HINGE_PIVOT.x}, ${JAW_HINGE_PIVOT.y})`;
        if (jaw) jaw.setAttribute('transform', jawTransform);
        if (lowerTeeth) lowerTeeth.setAttribute('transform', jawTransform);
        if (roofTrackDebug) roofTrackDebug.setAttribute('d', roofTrack.path);

        const upperLipMidX = 22 - lpOffset * 0.45;
        const upperLipTipX = 27 - lpOffset;
        const upperLipLowX = 32 - lpOffset * 0.45;
        const upperLipCornerX = 46 - lpOffset * 0.2;
        const upperLipC3X = 43 - lpOffset * 0.2;

        const retractX = ldr * 12;
        const elevateY = ldr * 6 * clamp(1 - la / LIP_APERTURE_MAX, 0.25, 1);
        const lowerLipStartX = upperLipCornerX + retractX * 0.75;
        const lowerLipStartY = 260 - elevateY * 0.75;
        const lowerLipC1X = 27 - lpOffset + retractX * 1.4;
        const lowerLipC1Y = 265 - elevateY;
        const lowerLipC2X = 27 + retractX * 0.7;
        const lowerLipC2Y = 280 - elevateY * 0.35;

        const upperFaceLip = `C 35 225, ${upperLipMidX} 230, ${upperLipTipX} 240 C ${upperLipLowX} 255, ${upperLipC3X} 260, ${upperLipCornerX} 260`;
        const upperFacePath = `M 90 20 C 75 60, 60 90, 65 110 C 70 120, 65 130, 50 145 C 30 165, 10 170, 15 190 C 20 205, 40 205, 40 215 ${upperFaceLip}`;
        const lowerFacePath = `M ${lowerLipStartX} ${lowerLipStartY} C ${lowerLipC1X} ${lowerLipC1Y}, ${lowerLipC2X} ${lowerLipC2Y}, 42 295 C 47 310, 42 320, 32 335 C 22 355, 60 365, 120 380`;
        if (upperFace) upperFace.setAttribute('d', upperFacePath);
        if (lowerFace) lowerFace.setAttribute('d', lowerFacePath);
        if (palate) palate.setAttribute('d', visiblePalatePath);

        if (palateTissue) {
            const alvReverse = `C ${ALVEOLAR_RIDGE[2].join(' ')}, ${ALVEOLAR_RIDGE[1].join(' ')}, ${ALVEOLAR_RIDGE[0].join(' ')}`;
            const hardReverse = `C ${HARD_PALATE[2].join(' ')}, ${HARD_PALATE[1].join(' ')}, ${HARD_PALATE[0].join(' ')}`;
            const palateTissuePath = [
                'M 40 215',
                'C 100 130, 220 140, 240 190',
                `C ${softPalateControl1X} ${softPalateControl1Y - 4}, ${softPalateControl2X} ${softPalateControl2Y - 4}, ${velumEndX + 2} ${velumEndY - 2}`,
                `C ${velumEndX + 5} ${velumEndY + 3}, ${velumEndX - 1} ${velumEndY + 7}, ${velumEndX - 3} ${velumEndY + 2}`,
                `C ${softPalateControl2X} ${softPalateControl2Y}, ${softPalateControl1X} ${softPalateControl1Y}, 240 190`,
                hardReverse,
                alvReverse,
                `Q 52 246 ${upperLipCornerX} 260`,
                `C ${upperLipC3X} 260, ${upperLipLowX} 255, ${upperLipTipX} 240`,
                `C ${upperLipMidX} 230, 35 225, 40 215 Z`,
            ].join(' ');
            palateTissue.setAttribute('d', palateTissuePath);
        }
        if (uvula) {
            const uvulaPath = `M ${velumEndX - 2.5} ${velumEndY - 1} C ${velumEndX + 3.5} ${velumEndY + 2}, ${velumEndX + 2.5} ${velumEndY + 7.5}, ${velumEndX - 2} ${velumEndY + 6.5} C ${velumEndX - 5.5} ${velumEndY + 5.5}, ${velumEndX - 5} ${velumEndY + 1}, ${velumEndX - 2.5} ${velumEndY - 1} Z`;
            uvula.setAttribute('d', uvulaPath);
        }

        const tip = this._getTonguePoint(ttcl, ttcd, 'tip', roofTrack);
        const body = this._getTonguePoint(tbcl, tbcd, 'body', roofTrack);
        const frPt = transformJawPoint(74, 296, jawTy, jawDeg);
        const frX = frPt.x;
        const frY = frPt.y;
        const brX = 240;
        const brY = 380 + la * 0.5;

        const tipBodyDist = Math.max(1, Math.hypot(body.targetX - tip.targetX, body.targetY - tip.targetY));
        const tipHandleLen = Math.min(30, Math.max(10, 0.38 * tipBodyDist));
        const bodyHandleLen = Math.min(34, Math.max(12, 0.42 * tipBodyDist));

        const v1x = body.targetX - frX;
        const v1y = body.targetY - frY;
        const len1 = Math.max(1, Math.hypot(v1x, v1y));
        const dx1 = (v1x / len1) * tipHandleLen;
        const dy1 = (v1y / len1) * tipHandleLen;

        const v2x = brX - tip.targetX;
        const v2y = brY - tip.targetY;
        const len2 = Math.max(1, Math.hypot(v2x, v2y));
        const chordX = v2x / len2;
        const chordY = v2y / len2;
        let roofTanX = -body.inwardNormalY;
        let roofTanY = body.inwardNormalX;
        if ((roofTanX * chordX) + (roofTanY * chordY) < 0) {
            roofTanX *= -1;
            roofTanY *= -1;
        }
        const blendX = 0.65 * roofTanX + 0.35 * chordX;
        const blendY = 0.65 * roofTanY + 0.35 * chordY;
        const blendLen = Math.max(1e-6, Math.hypot(blendX, blendY));
        const dx2 = (blendX / blendLen) * bodyHandleLen;
        const dy2 = (blendY / blendLen) * bodyHandleLen;

        let tipIn = this._projectInside(
            { x: tip.anchorX, y: tip.anchorY },
            { x: tip.inwardNormalX, y: tip.inwardNormalY },
            { x: tip.targetX - dx1, y: tip.targetY - dy1 },
            2,
        );
        let tipOut = this._projectInside(
            { x: tip.anchorX, y: tip.anchorY },
            { x: tip.inwardNormalX, y: tip.inwardNormalY },
            { x: tip.targetX + dx1, y: tip.targetY + dy1 },
            2,
        );
        let bodyIn = this._projectInside(
            { x: body.anchorX, y: body.anchorY },
            { x: body.inwardNormalX, y: body.inwardNormalY },
            { x: body.targetX - dx2, y: body.targetY - dy2 },
            2,
        );
        let bodyOut = this._projectInside(
            { x: body.anchorX, y: body.anchorY },
            { x: body.inwardNormalX, y: body.inwardNormalY },
            { x: body.targetX + dx2, y: body.targetY + dy2 },
            2,
        );

        if (this._hasTongueSurfaceContact(ttcd)) {
            const patch = this._contactPatchHandles(tip, roofTrack, eff.tipHalfSpan);
            tipIn = patch.before;
            tipOut = patch.after;
        }
        if (this._hasTongueSurfaceContact(tbcd)) {
            const patch = this._contactPatchHandles(body, roofTrack, eff.bodyHalfSpan);
            bodyIn = patch.before;
            bodyOut = patch.after;
        }

        const frHandle0 = { x: frX - 4, y: frY - 26 };
        const brHandle0 = { x: brX, y: brY - 40 };
        let tipPt = { x: tip.targetX, y: tip.targetY };
        const tipSd = this._signedRoofDistance(tipPt, roofTrack);
        if (tipSd.sd < 0) {
            tipPt = { x: tipPt.x + tipSd.nx * (-tipSd.sd + 1e-4), y: tipPt.y + tipSd.ny * (-tipSd.sd + 1e-4) };
        }
        let bodyPt = { x: body.targetX, y: body.targetY };
        const bodySd = this._signedRoofDistance(bodyPt, roofTrack);
        if (bodySd.sd < 0) {
            bodyPt = { x: bodyPt.x + bodySd.nx * (-bodySd.sd + 1e-4), y: bodyPt.y + bodySd.ny * (-bodySd.sd + 1e-4) };
        }
        const frEndpoint = { x: frX, y: frY };
        const brEndpoint = { x: brX, y: brY };
        let frHandle;
        [frHandle, tipIn] = this._constrainSegmentInsideRoof(frEndpoint, frHandle0, tipIn, tipPt, roofTrack, true, true);
        [tipOut, bodyIn] = this._constrainSegmentInsideRoof(tipPt, tipOut, bodyIn, bodyPt, roofTrack, true, true);
        let brHandle;
        [bodyOut, brHandle] = this._constrainSegmentInsideRoof(bodyPt, bodyOut, brHandle0, brEndpoint, roofTrack, true, true);

        const showHighlight = Boolean(this.contactExaggeration?.enabled && this.contactExaggeration?.showContactHighlight);
        if (tipContactArc) {
            if (showHighlight && this._hasTongueSurfaceContact(ttcd)) {
                tipContactArc.setAttribute('d', this._buildRoofArcPath(roofTrack, tip.roofPosition, eff.tipHalfSpan * 1.15));
                tipContactArc.setAttribute('opacity', '0.95');
            } else {
                tipContactArc.setAttribute('opacity', '0');
            }
        }
        if (bodyContactArc) {
            if (showHighlight && this._hasTongueSurfaceContact(tbcd)) {
                bodyContactArc.setAttribute('d', this._buildRoofArcPath(roofTrack, body.roofPosition, eff.bodyHalfSpan * 1.15));
                bodyContactArc.setAttribute('opacity', '0.95');
            } else {
                bodyContactArc.setAttribute('opacity', '0');
            }
        }
        if (lipContactSeal) {
            if (showHighlight && this._isEffectiveLipClosure(la)) {
                lipContactSeal.setAttribute('cx', String(44 - lpOffset * 0.25 + retractX * 0.4));
                lipContactSeal.setAttribute('cy', String(260 - elevateY * 0.4));
                lipContactSeal.setAttribute('opacity', '0.95');
            } else {
                lipContactSeal.setAttribute('opacity', '0');
            }
        }

        const tongueOpacity = 1.0 - (lat / 40) * 0.8;
        if (tongue) {
            tongue.setAttribute('opacity', String(tongueOpacity));
            tongue.setAttribute(
                'd',
                `M ${frX} ${frY} C ${frHandle.x} ${frHandle.y}, ${tipIn.x} ${tipIn.y}, ${tipPt.x} ${tipPt.y} C ${tipOut.x} ${tipOut.y}, ${bodyIn.x} ${bodyIn.y}, ${bodyPt.x} ${bodyPt.y} C ${bodyOut.x} ${bodyOut.y}, ${brHandle.x} ${brHandle.y}, ${brX} ${brY} Z`,
            );
        }

        const windOpacity = lat >= 20 ? (lat - 20) / 20 : 0;
        if (wind) {
            wind.setAttribute('opacity', String(windOpacity));
            wind.setAttribute('transform', `translate(${(tip.targetX + body.targetX) / 2}, ${(tip.targetY + body.targetY) / 2 - 15}) scale(-0.75, 0.75)`);
        }

        const floorCtrlPt = transformJawPoint(67, 296, jawTy, jawDeg);
        const jawCornerPt = transformJawPoint(60, 290, jawTy, jawDeg);
        const lowerToothTipPt = transformJawPoint(50, 265, jawTy, jawDeg);
        const lowerLipG0 = transformJawPoint(lowerLipStartX, lowerLipStartY, jawTy, jawDeg);
        const lowerLipG1 = transformJawPoint(lowerLipC1X, lowerLipC1Y, jawTy, jawDeg);
        const lowerLipG2 = transformJawPoint(lowerLipC2X, lowerLipC2Y, jawTy, jawDeg);
        const lowerLipG3 = transformJawPoint(42, 295, jawTy, jawDeg);
        const lowerLipG4 = transformJawPoint(47, 310, jawTy, jawDeg);
        const lowerLipG5 = transformJawPoint(42, 320, jawTy, jawDeg);
        const lowerLipG6 = transformJawPoint(32, 335, jawTy, jawDeg);
        const lowerLipG7 = transformJawPoint(22, 355, jawTy, jawDeg);
        const lowerLipG8 = transformJawPoint(60, 365, jawTy, jawDeg);
        const lowerLipG9 = transformJawPoint(120, 380, jawTy, jawDeg);

        const nasalD = `M 15 190 C 120 70, 250 70, 280 230 C 290 270, 300 320, 300 350 C ${throatCurveControl2X} ${throatCurveControl2Y}, ${throatCurveControl1X} ${throatCurveControl1Y}, ${velumEndX} ${velumEndY} C ${softPalateControl2X} ${softPalateControl2Y}, ${softPalateControl1X} ${softPalateControl1Y}, 240 190 C 220 140, 100 130, 40 215 Z`;
        const oralD = `${visiblePalatePath} ${throatClosure} L 300 380 L 240 380 L ${brX} ${brY} C ${brHandle.x} ${brHandle.y}, ${bodyOut.x} ${bodyOut.y}, ${bodyPt.x} ${bodyPt.y} C ${bodyIn.x} ${bodyIn.y}, ${tipOut.x} ${tipOut.y}, ${tipPt.x} ${tipPt.y} C ${tipIn.x} ${tipIn.y}, ${frHandle.x} ${frHandle.y}, ${frX} ${frY} Q ${floorCtrlPt.x} ${floorCtrlPt.y} ${jawCornerPt.x} ${jawCornerPt.y} L ${lowerToothTipPt.x} ${lowerToothTipPt.y} L ${lowerLipG0.x} ${lowerLipG0.y} L ${upperLipCornerX} 260 L 50 264 Z`;
        if (nasalTractFill) nasalTractFill.setAttribute('d', nasalD);
        if (oralTractFill) oralTractFill.setAttribute('d', oralD);
        if (nasalVoicing) {
            nasalVoicing.setAttribute('d', nasalD);
            nasalVoicing.setAttribute('opacity', String(vel / 40));
        }
        if (oralVoicing) oralVoicing.setAttribute('d', oralD);

        const clipX = this._getOralVoicingClipX({
            lipAperture: la,
            lipProtrusion: lpOffset,
            lateralDrop: lat,
            ttcd,
            tbcd,
            tip,
            body,
        });
        if (clipRect) {
            clipRect.setAttribute('x', String(clipX));
            clipRect.setAttribute('width', String(400 - clipX));
        }

        const uFacePoints = `90 20 C 75 60, 60 90, 65 110 C 70 120, 65 130, 50 145 C 30 165, 10 170, 15 190 C 20 205, 40 205, 40 215 ${upperFaceLip}`;
        const lFaceGlobal = `${lowerLipG0.x} ${lowerLipG0.y} C ${lowerLipG1.x} ${lowerLipG1.y}, ${lowerLipG2.x} ${lowerLipG2.y}, ${lowerLipG3.x} ${lowerLipG3.y} C ${lowerLipG4.x} ${lowerLipG4.y}, ${lowerLipG5.x} ${lowerLipG5.y}, ${lowerLipG6.x} ${lowerLipG6.y} C ${lowerLipG7.x} ${lowerLipG7.y}, ${lowerLipG8.x} ${lowerLipG8.y}, ${lowerLipG9.x} ${lowerLipG9.y}`;
        if (outsideAir) outsideAir.setAttribute('d', `M 0 0 L 90 0 L ${uFacePoints} L ${lFaceGlobal} L 120 400 L 0 400 Z`);

        const halfGlo = glo * 0.3;
        if (glottisHole) glottisHole.setAttribute('points', `0,-10 ${-halfGlo},10 ${halfGlo},10`);
        if (vfLeft) vfLeft.setAttribute('x2', String(-halfGlo));
        if (vfRight) vfRight.setAttribute('x2', String(halfGlo));

        if (anchor) {
            anchor.setAttribute('cx', String(tip.anchorX));
            anchor.setAttribute('cy', String(tip.anchorY));
        }
        if (normalLine) {
            normalLine.setAttribute('x1', String(tip.anchorX));
            normalLine.setAttribute('y1', String(tip.anchorY));
            normalLine.setAttribute('x2', String(tip.targetX));
            normalLine.setAttribute('y2', String(tip.targetY));
        }

        // --- Trace Mode ---
        this._updateHistory(tip, body);
        this._renderHistory();

        const highlight = this.highlightZone;
        const accent = '#f59e0b';
        if (highlight === 'glottis' && larynxView) {
            larynxView.querySelector('circle')?.setAttribute('stroke', accent);
            glottisHole?.setAttribute('fill', accent);
            vfLeft?.setAttribute('stroke', accent);
            vfRight?.setAttribute('stroke', accent);
        } else {
            larynxView?.querySelector('circle')?.setAttribute('stroke', '#334155');
            glottisHole?.setAttribute('fill', '#0f172a');
            vfLeft?.setAttribute('stroke', '#f8fafc');
            vfRight?.setAttribute('stroke', '#f8fafc');
        }

        if (highlight === 'lips') {
            upperFace?.setAttribute('stroke', accent);
            lowerFace?.setAttribute('stroke', accent);
        } else {
            upperFace?.setAttribute('stroke', '#334155');
            lowerFace?.setAttribute('stroke', '#475569');
        }

        if (highlight === 'tongue_body' || highlight === 'tongue_tip' || highlight === 'tongue_root') {
            tongue?.setAttribute('stroke', accent);
            normalLine?.setAttribute('stroke', accent);
            roofTrackDebug?.setAttribute('opacity', '0.8');
        } else {
            tongue?.setAttribute('stroke', '#e11d48');
            normalLine?.setAttribute('stroke', '#ef4444');
            roofTrackDebug?.setAttribute('opacity', '0');
        }

        if (highlight === 'velum') {
            palate?.setAttribute('stroke', accent);
            this.$('nasal-floor')?.setAttribute('stroke', accent);
            roofTrackDebug?.setAttribute('opacity', '0.8');
        } else {
            palate?.setAttribute('stroke', '#e11d48');
            this.$('nasal-floor')?.setAttribute('stroke', '#e11d48');
        }
    }

    _updateHistory(tip, body) {
        if (!this.showHistory) return;
        this.history.unshift({
            tip: { x: tip.targetX, y: tip.targetY },
            body: { x: body.targetX, y: body.targetY },
        });
        if (this.history.length > this.maxHistory) {
            this.history.pop();
        }
    }

    _renderHistory() {
        const group = this.$('tongue-trail-group');
        if (!group) return;
        if (!this.showHistory || this.history.length < 2) {
            group.innerHTML = '';
            return;
        }

        let html = '';
        for (let i = 0; i < this.history.length; i += 1) {
            const alpha = 1.0 - (i / this.maxHistory);
            if (alpha <= 0) break;
          
            const size = 2 * alpha;
            const h = this.history[i];
          
            // Draw tip point
            html += `<circle cx="${h.tip.x}" cy="${h.tip.y}" r="${size}" fill="#e11d48" opacity="${alpha * 0.5}" />`;
            // Draw body point
            html += `<circle cx="${h.body.x}" cy="${h.body.y}" r="${size}" fill="#e11d48" opacity="${alpha * 0.5}" />`;
        }
        group.innerHTML = html;
    }

    _renderVoicing(timestamp) {
        const line = this.$('voicing-line');
        const pattern = this.$('voicing-pattern');
        const intensity = 1 - this.state.glottal_aperture;
        if (!line || !pattern) return;
        if (intensity > 0) {
            const speed = 0.5 + intensity * 2.5;
            this._voicingOffset = (this._voicingOffset - speed) % 24;
            const wobble = Math.sin(timestamp * 0.005) * 3;
            pattern.setAttribute('patternTransform', `rotate(45) translate(${this._voicingOffset}, ${wobble})`);
            line.setAttribute('stroke-width', String(intensity * 5));
        } else {
            line.setAttribute('stroke-width', '0');
        }
    }
}

if (typeof window !== 'undefined') {
    window.SvgArticulatoryRenderer = SvgArticulatoryRenderer;
    window.SvgArticulatoryDefaultState = DEFAULT_STATE;
    window.SvgArticulatoryLegacyStateToNormalized = legacyStateToNormalized;
}
