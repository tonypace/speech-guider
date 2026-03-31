const DEFAULT_STATE = {
  lip_aperture: 10,
  lip_protrusion: 10,
  tongue_tip_constriction_location: 0.2,
  tongue_tip_constriction_degree: 40,
  lateral_tongue_drop: 0,
  velic_aperture: 0,
  tongue_body_constriction_location: 0.7,
  tongue_body_constriction_degree: 30,
  glottal_aperture: 0,
};

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
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
      <path d="M 52 230 C 48 245, 48 250, 50 255 L 60 230 Z" fill="#ffffff" stroke="#000000" stroke-width="1.5" stroke-linejoin="round"></path>
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
    this.state = { ...DEFAULT_STATE, ...(options.state || {}) };
    this.highlightZone = options.highlightZone || null;
    this.isRunning = false;
    this.animationId = null;
    this._voicingOffset = 0;
    this._mounted = false;
    this._elements = {};
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
    this.state = { ...this.state, ...nextState };
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

  _getPoint(t, d) {
    const p0 = { x: 52, y: 230 };
    const p1 = { x: 130, y: 140 };
    const hinge = { x: 240, y: 190 };
    const velumCtrl = { x: 260, y: 220 - this.state.velic_aperture * 0.1 };
    const p2 = { x: 280, y: 270 + this.state.velic_aperture };
    const useOral = t <= 0.85;
    const localT = useOral ? t / 0.85 : (t - 0.85) / 0.15;
    const a = useOral ? p0 : hinge;
    const b = useOral ? p1 : velumCtrl;
    const c = useOral ? hinge : p2;
    const anchorX = Math.pow(1 - localT, 2) * a.x + 2 * (1 - localT) * localT * b.x + Math.pow(localT, 2) * c.x;
    const anchorY = Math.pow(1 - localT, 2) * a.y + 2 * (1 - localT) * localT * b.y + Math.pow(localT, 2) * c.y;
    const tangentX = 2 * (1 - localT) * (b.x - a.x) + 2 * localT * (c.x - b.x);
    const tangentY = 2 * (1 - localT) * (b.y - a.y) + 2 * localT * (c.y - b.y);
    let normalX = -tangentY;
    let normalY = tangentX;
    const length = Math.sqrt(normalX * normalX + normalY * normalY) || 1;
    normalX /= length;
    normalY /= length;
    return {
      anchorX,
      anchorY,
      targetX: anchorX + normalX * d,
      targetY: anchorY + normalY * d,
      normalX,
      normalY,
    };
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

    const la = clamp(s.lip_aperture, 0, 40);
    const lp = clamp(s.lip_protrusion, 0, 14);
    const ttcl = clamp(s.tongue_tip_constriction_location, 0, 1);
    const ttcd = clamp(s.tongue_tip_constriction_degree, 0, 150);
    const lat = clamp(s.lateral_tongue_drop, 0, 40);
    const vel = clamp(s.velic_aperture, 0, 40);
    const tbcl = clamp(s.tongue_body_constriction_location, 0, 1);
    const tbcd = clamp(s.tongue_body_constriction_degree, 0, 150);
    const glo = clamp(s.glottal_aperture, 0, 30);

    if (jaw) jaw.setAttribute('transform', `translate(0, ${la})`);

    const upperFacePath = `M 90 20 C 75 60, 60 90, 65 110 C 70 120, 65 130, 50 145 C 30 165, 10 170, 15 190 C 20 205, 40 205, 40 215 C 35 225, 22 230, ${27 - lp} 240 C 32 255, 43 260, 46 260`;
    const lowerFacePath = `M 46 260 C ${27 - lp} 265, 27 280, 42 295 C 47 310, 42 320, 32 335 C 22 355, 60 365, 120 380`;
    if (upperFace) upperFace.setAttribute('d', upperFacePath);
    if (lowerFace) lowerFace.setAttribute('d', lowerFacePath);
    if (palate) {
      palate.setAttribute('d', `M 52 230 Q 130 140 240 190 Q ${260 - vel * 0.1} ${220 + vel * 0.3} ${280 - vel * 0.4} ${270 + vel}`);
    }

    const tip = this._getPoint(ttcl, ttcd);
    const body = this._getPoint(tbcl, tbcd);
    const frX = 100;
    const frY = 300 + la;
    const brX = 240;
    const brY = 380 + la * 0.5;
    const v1x = body.targetX - frX;
    const v1y = body.targetY - frY;
    const len1 = Math.max(1, Math.sqrt(v1x * v1x + v1y * v1y));
    const dx1 = (v1x / len1) * 30;
    const dy1 = (v1y / len1) * 30;
    const v2x = brX - tip.targetX;
    const v2y = brY - tip.targetY;
    const len2 = Math.max(1, Math.sqrt(v2x * v2x + v2y * v2y));
    const dx2 = (v2x / len2) * 40;
    const dy2 = (v2y / len2) * 40;

    const tongueOpacity = 1.0 - (lat / 40) * 0.8;
    if (tongue) {
      tongue.setAttribute(
        'opacity',
        String(tongueOpacity),
      );
      tongue.setAttribute(
        'd',
        `M ${frX} ${frY} C ${frX} ${frY - 30}, ${tip.targetX - dx1} ${tip.targetY - dy1}, ${tip.targetX} ${tip.targetY} C ${tip.targetX + dx1} ${tip.targetY + dy1}, ${body.targetX - dx2} ${body.targetY - dy2}, ${body.targetX} ${body.targetY} C ${body.targetX + dx2} ${body.targetY + dy2}, ${brX} ${brY - 40}, ${brX} ${brY} Z`,
      );
    }

    const windOpacity = lat >= 20 ? (lat - 20) / 20 : 0;
    if (wind) {
      wind.setAttribute('opacity', String(windOpacity));
      wind.setAttribute('transform', `translate(${(tip.targetX + body.targetX) / 2}, ${(tip.targetY + body.targetY) / 2 - 15}) scale(-0.75, 0.75)`);
    }

    const nasalD = `M 15 190 C 120 70, 250 70, 280 230 C 290 270, 300 320, 300 350 L ${280 - vel * 0.4} ${270 + vel} Q ${260 - vel * 0.1} ${220 + vel * 0.3} 240 190 C 220 140, 100 130, 40 215 Z`;
    const oralD = `M 52 230 Q 130 140 240 190 Q ${260 - vel * 0.1} ${220 + vel * 0.3} ${280 - vel * 0.4} ${270 + vel} L 300 350 L 300 380 L 240 380 L ${brX} ${brY} C ${brX} ${brY - 40}, ${body.targetX + dx2} ${body.targetY + dy2}, ${body.targetX} ${body.targetY} C ${body.targetX - dx2} ${body.targetY - dy2}, ${tip.targetX + dx1} ${tip.targetY + dy1}, ${tip.targetX} ${tip.targetY} C ${tip.targetX - dx1} ${tip.targetY - dy1}, ${frX} ${frY - 30}, ${frX} ${frY} Q 80 ${300 + la} 60 ${290 + la} L 50 ${265 + la} L 46 ${260 + la} L 46 260 L 50 255 Z`;
    const oralVoicingD = `M 52 230 Q 130 140 240 190 Q ${260 - vel * 0.1} ${220 + vel * 0.3} ${280 - vel * 0.4} ${270 + vel} L 300 350 L 300 380 L 240 380 L ${brX} ${brY} C ${brX} ${brY - 40}, ${body.targetX + dx2} ${body.targetY + dy2}, ${body.targetX} ${body.targetY} C ${body.targetX - dx2} ${body.targetY - dy2}, ${tip.targetX + dx1} ${tip.targetY + dy1}, ${tip.targetX} ${tip.targetY} C ${tip.targetX - dx1} ${tip.targetY - dy1}, ${frX} ${frY - 30}, ${frX} ${frY} Q 80 ${300 + la} 60 ${290 + la} L 50 ${265 + la} L 46 ${260 + la} L 46 260 L 50 255 Z`;
    if (nasalTractFill) nasalTractFill.setAttribute('d', nasalD);
    if (oralTractFill) oralTractFill.setAttribute('d', oralD);
    if (nasalVoicing) {
      nasalVoicing.setAttribute('d', nasalD);
      nasalVoicing.setAttribute('opacity', String(s.velic_aperture / 40));
    }
    if (oralVoicing) oralVoicing.setAttribute('d', oralVoicingD);

    let clipX = 0;
    if (lat === 0) {
      if (ttcd === 0) clipX = Math.max(clipX, tip.targetX);
      if (tbcd === 0) clipX = Math.max(clipX, body.targetX);
    }
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
