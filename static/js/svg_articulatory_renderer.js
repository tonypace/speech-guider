const DEFAULT_STATE = {
  lip_aperture: 0.25,
  lip_protrusion: 0.71,
  tongue_tip_constriction_location: 0.2,
  tongue_tip_constriction_degree: 1,
  lateral_tongue_drop: 0,
  velic_aperture: 0,
  tongue_body_constriction_location: 0.7,
  tongue_body_constriction_degree: 1,
  glottal_aperture: 0,
};

const TIP_DOMAIN_END = 0.25;
const BODY_DOMAIN_START = 0.35;
const TONGUE_TIP_REST_DISTANCE = 32;
const TONGUE_BODY_REST_DISTANCE = 24;
const LIP_APERTURE_MAX = 40;
const LIP_PROTRUSION_MAX = 14;
const VELIC_APERTURE_MAX = 40;
const ORAL_REFERENCE_POINT = { x: 190, y: 300 };

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

function lerp(start, end, t) {
  return start + (end - start) * t;
}

function normalizeScalar(value, legacyMax, fallback) {
  const numericValue = Number(value);
  if (!Number.isFinite(numericValue)) return fallback;
  if (numericValue <= 1) return clamp(numericValue, 0, 1);
  return clamp(numericValue / legacyMax, 0, 1);
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

function createSvgMarkup(prefix) {
  return `
  <svg id="${prefix}-mouth-svg" width="400" height="400" class="border rounded bg-gray-50 w-full" viewBox="0 0 400 400">
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

    <g>
      <path d="M 52 239 C 48 254, 48 259, 50 264 L 60 239 Z" fill="#ffffff" stroke="#000000" stroke-width="1.5" stroke-linejoin="round"></path>
      <g stroke="#334155" stroke-width="6" fill="none" stroke-linecap="round" stroke-linejoin="round">
        <path id="${prefix}-upper-face" d=""></path>
        <path d="M 15 190 C 120 70, 250 70, 280 230 C 290 270, 300 320, 300 350" stroke="#e11d48"></path>
        <path id="${prefix}-nasal-floor" d="M 40 215 C 100 130, 220 140, 240 190" stroke="#e11d48"></path>
        <path id="${prefix}-palate" d="" stroke="#e11d48"></path>
      </g>
    </g>

    <g id="${prefix}-jaw-group">
      <path d="M 60 290 Q 80 300 100 300" fill="none" stroke="#e11d48" stroke-width="6" stroke-linecap="round"></path>
      <path d="M 52 290 C 48 275, 48 270, 50 265 L 60 290 Z" fill="#ffffff" stroke="#000000" stroke-width="1.5" stroke-linejoin="round"></path>
      <path id="${prefix}-lower-face" d="" stroke="#475569" stroke-width="6" fill="none" stroke-linecap="round" stroke-linejoin="round"></path>
    </g>

    <path id="${prefix}-tongue" d="" fill="#fb7185" stroke="#e11d48" stroke-width="3" opacity="1.0"></path>
    <line id="${prefix}-normal-line" x1="0" y1="0" x2="0" y2="0" stroke="#ef4444" stroke-width="1.5" stroke-dasharray="4" marker-end="url(#${prefix}-arrow)"></line>
    <circle id="${prefix}-anchor-point" cx="0" cy="0" r="3" fill="#3b82f6"></circle>
    <g id="${prefix}-wind-icon" stroke="#0f172a" stroke-width="2.5" stroke-linecap="round" fill="none" opacity="0">
      <path d="M 8 -8 H -12 M 8 -8 C 10.2 -8 12 -9.8 12 -12 C 12 -14.2 10.2 -16 8 -16 C 5.8 -16 4 -14.2 4 -12" />
      <path d="M 12 0 H -16 M 12 0 C 14.2 0 16 1.8 16 4 C 16 6.2 14.2 8 12 8 C 9.8 8 8 6.2 8 4" />
      <path d="M 4 8 H -8 M 4 8 C 6.2 8 8 9.8 8 12 C 8 14.2 6.2 16 4 16 C 1.8 16 0 14.2 0 12" />
    </g>
    <g id="${prefix}-larynx-view" transform="translate(260, 385)">
      <text x="0" y="-18" font-size="10" font-weight="bold" text-anchor="middle" fill="#64748b">GLO</text>
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
    this._mounted = false;
    this._elements = {};
    this._roofTrackCache = null;
    this._palateGeometryCache = null;
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
      'oral-voicing', 'oral-voicing-clip-rect', 'upper-face', 'nasal-floor', 'palate',
      'jaw-group', 'lower-face', 'tongue', 'normal-line', 'anchor-point', 'wind-icon',
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
    this.state = this._normalizeState({ ...this.state, ...nextState });
    if (!this._mounted) this.mount();
    this.render();
  }

  setParameters(nextState) {
    this.setState(nextState);
  }

  updateFromSchema(nextState) {
    this.setState(nextState);
  }

  setHighlightZone(zone) {
    this.highlightZone = zone;
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
    this._renderVoicing(performance.now());
  }

  _buildRoofTrack(vel) {
    const roofEnd = { x: 300, y: 350 };
    const segments = [
      {
        type: 'cubic',
        p0: { x: 54, y: 264 },
        p1: { x: 61, y: 252 },
        p2: { x: 84, y: 223 },
        p3: { x: 122, y: 192 },
      },
      {
        type: 'cubic',
        p0: { x: 122, y: 192 },
        p1: { x: 155, y: 172 },
        p2: { x: 205, y: 172 },
        p3: { x: 240, y: 190 },
      },
      {
        type: 'cubic',
        p0: { x: 240, y: 190 },
        p1: { x: 264 - vel * 0.12, y: 206 + vel * 0.18 },
        p2: { x: 282 - vel * 0.18, y: 236 + vel * 0.4 },
        p3: { x: 292 - vel * 0.08, y: 272 + vel * 0.8 },
      },
      {
        type: 'quadratic',
        p0: { x: 292 - vel * 0.08, y: 272 + vel * 0.8 },
        p1: { x: 300, y: 310 + vel * 0.35 },
        p2: roofEnd,
      },
    ];

    const samples = [];
    let totalLength = 0;
    let previous = null;
    segments.forEach((segment) => {
      const steps = segment.type === 'quadratic' ? 50 : 70;
      for (let i = 0; i <= steps; i += 1) {
        const t = i / steps;
        const point = segment.type === 'quadratic'
          ? quadraticPoint(segment.p0, segment.p1, segment.p2, t)
          : cubicPoint(segment.p0, segment.p1, segment.p2, segment.p3, t);
        if (previous) totalLength += distance(previous, point);
        samples.push({ ...point, length: totalLength });
        previous = point;
      }
    });

    const path = [
      'M 54 264',
      'C 61 252, 84 223, 122 192',
      'C 155 172, 205 172, 240 190',
      `C ${264 - vel * 0.12} ${206 + vel * 0.18}, ${282 - vel * 0.18} ${236 + vel * 0.4}, ${292 - vel * 0.08} ${272 + vel * 0.8}`,
      `Q 300 ${310 + vel * 0.35} 300 350`,
    ].join(' ');

    return { path, samples, totalLength, end: roofEnd };
  }

  _buildVisiblePalateGeometry(vel) {
    const velFactor = clamp(vel / 40, 0, 1);
    const velumEndX = lerp(300, 274, velFactor);
    const velumEndY = lerp(350, 288, velFactor);
    const softPalateControl1X = lerp(264, 260, velFactor);
    const softPalateControl1Y = lerp(206, 212, velFactor);
    const softPalateControl2X = lerp(280, 274, velFactor);
    const softPalateControl2Y = lerp(236, 242, velFactor);
    const throatCurveControl1X = Math.min(296, velumEndX + 18);
    const throatCurveControl1Y = velumEndY + 10;
    const throatCurveControl2X = 294;
    const throatCurveControl2Y = 314;

    const path = [
      'M 54 264',
      'C 61 252, 84 223, 122 192',
      'C 155 172, 205 172, 240 190',
      `C ${softPalateControl1X} ${softPalateControl1Y}, ${softPalateControl2X} ${softPalateControl2Y}, ${velumEndX} ${velumEndY}`,
    ].join(' ');

    const throatClosure = `C ${throatCurveControl1X} ${throatCurveControl1Y}, ${throatCurveControl2X} ${throatCurveControl2Y}, 300 350`;

    return {
      path,
      throatClosure,
      velumEndX,
      velumEndY,
    };
  }

  _buildVisiblePalatePath(vel) {
    return this._buildVisiblePalateGeometry(vel).path;
  }

  _normalizeState(state) {
    return {
      ...DEFAULT_STATE,
      ...state,
      lip_aperture: normalizeScalar(state.lip_aperture, LIP_APERTURE_MAX, DEFAULT_STATE.lip_aperture),
      lip_protrusion: normalizeScalar(state.lip_protrusion, LIP_PROTRUSION_MAX, DEFAULT_STATE.lip_protrusion),
      tongue_tip_constriction_location: clamp(Number(state.tongue_tip_constriction_location ?? DEFAULT_STATE.tongue_tip_constriction_location), 0, 1),
      tongue_tip_constriction_degree: this._normalizeDegree(
        state.tongue_tip_constriction_degree ?? DEFAULT_STATE.tongue_tip_constriction_degree,
        40,
      ),
      lateral_tongue_drop: clamp(Number(state.lateral_tongue_drop ?? DEFAULT_STATE.lateral_tongue_drop), 0, 40),
      velic_aperture: normalizeScalar(state.velic_aperture, VELIC_APERTURE_MAX, DEFAULT_STATE.velic_aperture),
      tongue_body_constriction_location: clamp(Number(state.tongue_body_constriction_location ?? DEFAULT_STATE.tongue_body_constriction_location), 0, 1),
      tongue_body_constriction_degree: this._normalizeDegree(
        state.tongue_body_constriction_degree ?? DEFAULT_STATE.tongue_body_constriction_degree,
        30,
      ),
      glottal_aperture: clamp(Number(state.glottal_aperture ?? DEFAULT_STATE.glottal_aperture), 0, 30),
    };
  }

  _sampleRoofTrack(roofTrack, s) {
    const targetLength = clamp(s, 0, 1) * roofTrack.totalLength;
    const samples = roofTrack.samples;
    if (!samples.length) {
      return {
        anchorX: 0,
        anchorY: 0,
        inwardNormalX: 0,
        inwardNormalY: 1,
      };
    }
    let index = samples.findIndex((sample) => sample.length >= targetLength);
    if (index < 0) index = samples.length - 1;
    const current = samples[index];
    const prev = samples[Math.max(0, index - 1)];
    const next = samples[Math.min(samples.length - 1, index + 1)];
    const tangentX = next.x - prev.x;
    const tangentY = next.y - prev.y;
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
    if (domain === 'tip') return lerp(0, TIP_DOMAIN_END, clamp(location, 0, 1));
    return lerp(BODY_DOMAIN_START, 1, clamp(location, 0, 1));
  }

  _normalizeDegree(value, legacyRestDistance) {
    const numericValue = Number(value);
    if (numericValue <= 1) return clamp(numericValue, 0, 1);
    return clamp(numericValue / legacyRestDistance, 0, 1);
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

  _getTonguePoint(location, degree, domain, roofTrack) {
    const roofPosition = this._mapLocation(location, domain);
    const anchor = this._sampleRoofTrack(roofTrack, roofPosition);
    const restDistance = domain === 'tip' ? TONGUE_TIP_REST_DISTANCE : TONGUE_BODY_REST_DISTANCE;
    const legacyRest = domain === 'tip' ? 40 : 30;
    const normalizedDegree = this._normalizeDegree(degree, legacyRest);
    const distanceFromRoof = normalizedDegree * restDistance;

    return {
      ...anchor,
      roofPosition,
      distanceFromRoof,
      targetX: anchor.anchorX + anchor.inwardNormalX * distanceFromRoof,
      targetY: anchor.anchorY + anchor.inwardNormalY * distanceFromRoof,
    };
  }

  _isEffectiveTongueClosure(normalizedDegree, lateralDrop) {
    return normalizedDegree <= 0.03 && lateralDrop < 8;
  }

  _isEffectiveLipClosure(lipAperture) {
    return lipAperture <= 2;
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
    const upperFace = this.$('upper-face');
    const lowerFace = this.$('lower-face');
    const palate = this.$('palate');
    const tongue = this.$('tongue');
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

    const la = normalizeScalar(s.lip_aperture, LIP_APERTURE_MAX, DEFAULT_STATE.lip_aperture) * LIP_APERTURE_MAX;
    const lp = normalizeScalar(s.lip_protrusion, LIP_PROTRUSION_MAX, DEFAULT_STATE.lip_protrusion) * LIP_PROTRUSION_MAX;
    const ttcl = clamp(s.tongue_tip_constriction_location, 0, 1);
    const ttcd = this._normalizeDegree(s.tongue_tip_constriction_degree, 40);
    const lat = clamp(s.lateral_tongue_drop, 0, 40);
    const vel = normalizeScalar(s.velic_aperture, VELIC_APERTURE_MAX, DEFAULT_STATE.velic_aperture) * VELIC_APERTURE_MAX;
    const tbcl = clamp(s.tongue_body_constriction_location, 0, 1);
    const tbcd = this._normalizeDegree(s.tongue_body_constriction_degree, 30);
    const glo = clamp(s.glottal_aperture, 0, 30);
    const velRounded = Math.round(vel);
    if (!this._roofTrackCache || this._roofTrackCache.vel !== velRounded) {
      this._roofTrackCache = { vel: velRounded, ...this._buildRoofTrack(vel) };
    }
    const roofTrack = this._roofTrackCache;
    if (!this._palateGeometryCache || this._palateGeometryCache.vel !== velRounded) {
      this._palateGeometryCache = { vel: velRounded, ...this._buildVisiblePalateGeometry(vel) };
    }
    const visiblePalateGeometry = this._palateGeometryCache;
    const visiblePalatePath = visiblePalateGeometry.path;

    if (jaw) jaw.setAttribute('transform', `translate(0, ${la})`);

    const upperFacePath = `M 90 20 C 75 60, 60 90, 65 110 C 70 120, 65 130, 50 145 C 30 165, 10 170, 15 190 C 20 205, 40 205, 40 215 C 35 225, 22 230, ${27 - lp} 240 C 32 255, 43 260, 46 260`;
    const lowerFacePath = `M 46 260 C ${27 - lp} 265, 27 280, 42 295 C 47 310, 42 320, 32 335 C 22 355, 60 365, 120 380`;
    if (upperFace) upperFace.setAttribute('d', upperFacePath);
    if (lowerFace) lowerFace.setAttribute('d', lowerFacePath);
    if (palate) palate.setAttribute('d', visiblePalatePath);

    const tip = this._getTonguePoint(ttcl, ttcd, 'tip', roofTrack);
    const body = this._getTonguePoint(tbcl, tbcd, 'body', roofTrack);
    const frX = 100;
    const frY = 300 + la;
    const brX = 240;
    const brY = 380 + la * 0.5;

    const v1x = body.targetX - frX;
    const v1y = body.targetY - frY;
    const len1 = Math.max(1, Math.hypot(v1x, v1y));
    const dx1 = (v1x / len1) * 30;
    const dy1 = (v1y / len1) * 30;
    const v2x = brX - tip.targetX;
    const v2y = brY - tip.targetY;
    const len2 = Math.max(1, Math.hypot(v2x, v2y));
    const dx2 = (v2x / len2) * 40;
    const dy2 = (v2y / len2) * 40;

    const tipIn = this._projectInside(
      { x: tip.anchorX, y: tip.anchorY },
      { x: tip.inwardNormalX, y: tip.inwardNormalY },
      { x: tip.targetX - dx1, y: tip.targetY - dy1 },
      2,
    );
    const tipOut = this._projectInside(
      { x: tip.anchorX, y: tip.anchorY },
      { x: tip.inwardNormalX, y: tip.inwardNormalY },
      { x: tip.targetX + dx1, y: tip.targetY + dy1 },
      2,
    );
    const bodyIn = this._projectInside(
      { x: body.anchorX, y: body.anchorY },
      { x: body.inwardNormalX, y: body.inwardNormalY },
      { x: body.targetX - dx2, y: body.targetY - dy2 },
      2,
    );
    const bodyOut = this._projectInside(
      { x: body.anchorX, y: body.anchorY },
      { x: body.inwardNormalX, y: body.inwardNormalY },
      { x: body.targetX + dx2, y: body.targetY + dy2 },
      2,
    );

    const tongueOpacity = 1.0 - (lat / 40) * 0.8;
    if (tongue) {
      tongue.setAttribute('opacity', String(tongueOpacity));
      tongue.setAttribute(
        'd',
        `M ${frX} ${frY} C ${frX} ${frY - 30}, ${tipIn.x} ${tipIn.y}, ${tip.targetX} ${tip.targetY} C ${tipOut.x} ${tipOut.y}, ${bodyIn.x} ${bodyIn.y}, ${body.targetX} ${body.targetY} C ${bodyOut.x} ${bodyOut.y}, ${brX} ${brY - 40}, ${brX} ${brY} Z`,
      );
    }

    const windOpacity = lat >= 20 ? (lat - 20) / 20 : 0;
    if (wind) {
      wind.setAttribute('opacity', String(windOpacity));
      wind.setAttribute('transform', `translate(${(tip.targetX + body.targetX) / 2}, ${(tip.targetY + body.targetY) / 2 - 15}) scale(-0.75, 0.75)`);
    }

    const nasalD = 'M 15 190 C 120 70, 250 70, 280 230 C 286 236, 290 241, 294 246 L 240 190 C 220 140, 100 130, 40 215 Z';
    const oralD = `${visiblePalatePath} ${visiblePalateGeometry.throatClosure} L 300 380 L 240 380 L ${brX} ${brY} C ${brX} ${brY - 40}, ${bodyOut.x} ${bodyOut.y}, ${body.targetX} ${body.targetY} C ${bodyIn.x} ${bodyIn.y}, ${tipOut.x} ${tipOut.y}, ${tip.targetX} ${tip.targetY} C ${tipIn.x} ${tipIn.y}, ${frX} ${frY - 30}, ${frX} ${frY} Q 80 ${300 + la} 60 ${290 + la} L 50 ${265 + la} L 46 ${260 + la} L 46 260 L 50 264 Z`;
    if (nasalTractFill) nasalTractFill.setAttribute('d', nasalD);
    if (oralTractFill) oralTractFill.setAttribute('d', oralD);
    if (nasalVoicing) {
      nasalVoicing.setAttribute('d', nasalD);
      nasalVoicing.setAttribute('opacity', String(vel / 40));
    }
    if (oralVoicing) oralVoicing.setAttribute('d', oralD);

    const clipX = this._getOralVoicingClipX({
      lipAperture: la,
      lipProtrusion: lp,
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

    const uFacePoints = `90 20 C 75 60, 60 90, 65 110 C 70 120, 65 130, 50 145 C 30 165, 10 170, 15 190 C 20 205, 40 205, 40 215 C 35 225, 22 230, ${27 - lp} 240 C 32 255, 43 260, 46 260`;
    const lFaceGlobal = `46 ${260 + la} C ${27 - lp} ${265 + la}, ${27 + la * 0.4} ${280 + la}, 42 ${295 + la} C 47 ${310 + la}, 42 ${320 + la}, 32 ${335 + la} C 22 ${355 + la}, 60 ${365 + la}, 120 ${380 + la}`;
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
    } else {
      tongue?.setAttribute('stroke', '#e11d48');
      normalLine?.setAttribute('stroke', '#ef4444');
    }

    if (highlight === 'velum') {
      palate?.setAttribute('stroke', accent);
      this.$('nasal-floor')?.setAttribute('stroke', accent);
    } else {
      palate?.setAttribute('stroke', '#e11d48');
      this.$('nasal-floor')?.setAttribute('stroke', '#e11d48');
    }
  }

  _renderVoicing(timestamp) {
    const line = this.$('voicing-line');
    const pattern = this.$('voicing-pattern');
    const intensity = 1 - clamp(this.state.glottal_aperture, 0, 30) / 30;
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
}
