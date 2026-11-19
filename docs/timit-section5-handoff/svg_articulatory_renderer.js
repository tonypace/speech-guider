// --- USER PROVIDED RENDERER CODE ---
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
    // This fraction is the hard palate endpoint on the original fixed track.
    const SOFT_PALATE_START = 0.5628632913010034;
    const PHARYNX_START = 0.86;
    const TEETH = [[50, 265], [53, 256], [56, 247], [60, 239]];
    const ALVEOLAR_RIDGE = [[60, 239], [75, 225], [95, 205], [122, 192]];
    const HARD_PALATE = [[122, 192], [155, 172], [205, 172], [240, 190]];
    const TONGUE_TIP_REST_DISTANCE = 32;
    const TONGUE_BODY_REST_DISTANCE = 36;
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

    function cubicPath([, first, second, end]) {
      return `C ${first.join(' ')}, ${second.join(' ')}, ${end.join(' ')}`;
    }

    function sampleRoofSection(curves, steps, start, end) {
      const samples = [];
      let length = 0;
      for (const curve of curves) {
        const [p0, p1, p2, p3] = curve.map(([x, y]) => ({x, y}));
        for (let index = 0; index <= steps; index += 1) {
          const point = cubicPoint(p0, p1, p2, p3, index / steps);
          if (samples.length) length += distance(samples[samples.length - 1], point);
          samples.push({...point, length});
        }
      }
      return samples.map(point => ({...point, position: lerp(start, end, point.length / length)}));
    }

    const ANTERIOR_ROOF = sampleRoofSection([TEETH, ALVEOLAR_RIDGE, HARD_PALATE], 70, 0, SOFT_PALATE_START);

    function distance(a, b) {
      return Math.hypot(b.x - a.x, b.y - a.y);
    }

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

        <g>
          <g stroke="#334155" stroke-width="6" fill="none" stroke-linecap="round" stroke-linejoin="round">
            <path id="${prefix}-upper-face" d=""></path>
            <path d="M 15 190 C 120 70, 250 70, 280 230 C 290 270, 300 320, 300 350" stroke="#e11d48"></path>
            <path id="${prefix}-nasal-floor" d="M 40 215 C 100 130, 220 140, 240 190" stroke="#e11d48"></path>
            <path id="${prefix}-palate" d="" stroke="#e11d48"></path>
          </g>
        </g>

        <g id="${prefix}-jaw-group">
          <path d="M 60 290 Q 80 300 100 300" fill="none" stroke="#e11d48" stroke-width="6" stroke-linecap="round"></path>
          <path id="${prefix}-lower-face" d="" stroke="#475569" stroke-width="6" fill="none" stroke-linecap="round" stroke-linejoin="round"></path>
        </g>

        <g id="${prefix}-tongue-trail-group" pointer-events="none"></g>
        <path id="${prefix}-tongue" d="" fill="#fb7185" stroke="#e11d48" stroke-width="3" opacity="1.0"></path>
        <path id="${prefix}-tip-contact-arc" d="" fill="none" stroke="#f59e0b" stroke-width="5" stroke-linecap="round" opacity="0" pointer-events="none"></path>
        <path id="${prefix}-body-contact-arc" d="" fill="none" stroke="#f59e0b" stroke-width="5" stroke-linecap="round" opacity="0" pointer-events="none"></path>
        <circle id="${prefix}-lip-contact-seal" cx="46" cy="260" r="5" fill="#f59e0b" stroke="#ffffff" stroke-width="1.5" opacity="0" pointer-events="none"></circle>
        <path id="${prefix}-upper-teeth" d="M 52 239 C 48 254, 48 259, 50 264 L 60 239 Z" fill="#ffffff" stroke="#000000" stroke-width="1.5" stroke-linejoin="round"></path>
        <g id="${prefix}-lower-teeth-group">
          <path id="${prefix}-lower-teeth" d="M 52 290 C 48 275, 48 270, 50 265 L 60 290 Z" fill="#ffffff" stroke="#000000" stroke-width="1.5" stroke-linejoin="round"></path>
        </g>
        <path id="${prefix}-roof-track-debug" fill="none" stroke="#10b981" stroke-width="2" stroke-dasharray="4" opacity="0" pointer-events="none"></path>
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

    class SvgArticulatoryRenderer {
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
          'oral-voicing', 'oral-voicing-clip-rect', 'upper-face', 'nasal-floor', 'palate',
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
          // NOTE: I added _renderFrame here so sliders update in real time while animating
          this._renderFrame(); 
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

      _buildRoofTrack(geometry = this._buildVisiblePalateGeometry(this.state.velic_aperture * VELIC_APERTURE_MAX)) {
        const softPalate = sampleRoofSection([geometry.softPalate], 128, SOFT_PALATE_START, PHARYNX_START);
        const throat = sampleRoofSection([geometry.throat], 128, PHARYNX_START, 1);
        return {
          path: `M ${TEETH[0].join(' ')} ${cubicPath(TEETH)} ${geometry.palateCurves} ${geometry.throatClosure}`,
          samples: [...ANTERIOR_ROOF, ...softPalate.slice(1), ...throat.slice(1)],
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
          HARD_PALATE[3], [softPalateControl1X, softPalateControl1Y],
          [softPalateControl2X, softPalateControl2Y], [velumEndX, velumEndY],
        ];
        const throat = [
          softPalate[3], [throatCurveControl1X, throatCurveControl1Y],
          [throatCurveControl2X, throatCurveControl2Y], [300, 350],
        ];
        const palateCurves = [ALVEOLAR_RIDGE, HARD_PALATE, softPalate].map(cubicPath).join(' ');
        return {
          path: `M ${ALVEOLAR_RIDGE[0].join(' ')} ${palateCurves}`,
          palateCurves,
          throatClosure: cubicPath(throat),
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
        const index = samples.findIndex(sample => sample.position >= position);
        const upper = samples[index];
        const lower = samples[Math.max(0, index - 1)];
        const next = samples[Math.min(samples.length - 1, index + 1)];
        const interpolate = position > TIP_DOMAIN_END && upper.position > lower.position;
        const weight = interpolate ? (position - lower.position) / (upper.position - lower.position) : 1;
        const current = {x: lerp(lower.x, upper.x, weight), y: lerp(lower.y, upper.y, weight)};
        const previous = samples[Math.max(0, index - 2)];
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
        if (domain === 'tip') return lerp(0, TIP_DOMAIN_END, clamp(location, 0, 1));
        return lerp(BODY_DOMAIN_START, 1, clamp(location, 0, 1));
      }

      _surfaceForRoofPosition(position) {
        const value = clamp(position, 0, 1);
        if (value < 0.035) return 'upper_teeth';
        if (value < 0.25) return 'alveolar_ridge';
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
        const lp = s.lip_protrusion * LIP_PROTRUSION_MAX;
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

        if (jaw) jaw.setAttribute('transform', `translate(0, ${la})`);
        if (lowerTeeth) lowerTeeth.setAttribute('transform', `translate(0, ${la})`);
        if (roofTrackDebug) roofTrackDebug.setAttribute('d', roofTrack.path);

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
            lipContactSeal.setAttribute('cx', String(44 - lp * 0.25));
            lipContactSeal.setAttribute('cy', '260');
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
            `M ${frX} ${frY} C ${frX} ${frY - 30}, ${tipIn.x} ${tipIn.y}, ${tip.targetX} ${tip.targetY} C ${tipOut.x} ${tipOut.y}, ${bodyIn.x} ${bodyIn.y}, ${body.targetX} ${body.targetY} C ${bodyOut.x} ${bodyOut.y}, ${brX} ${brY - 40}, ${brX} ${brY} Z`,
          );
        }

        const windOpacity = lat >= 20 ? (lat - 20) / 20 : 0;
        if (wind) {
          wind.setAttribute('opacity', String(windOpacity));
          wind.setAttribute('transform', `translate(${(tip.targetX + body.targetX) / 2}, ${(tip.targetY + body.targetY) / 2 - 15}) scale(-0.75, 0.75)`);
        }

        const nasalD = `M 15 190 C 120 70, 250 70, 280 230 C 290 270, 300 320, 300 350 C ${throatCurveControl2X} ${throatCurveControl2Y}, ${throatCurveControl1X} ${throatCurveControl1Y}, ${velumEndX} ${velumEndY} C ${softPalateControl2X} ${softPalateControl2Y}, ${softPalateControl1X} ${softPalateControl1Y}, 240 190 C 220 140, 100 130, 40 215 Z`;
        const oralD = `${visiblePalatePath} ${throatClosure} L 300 380 L 240 380 L ${brX} ${brY} C ${brX} ${brY - 40}, ${bodyOut.x} ${bodyOut.y}, ${body.targetX} ${body.targetY} C ${bodyIn.x} ${bodyIn.y}, ${tipOut.x} ${tipOut.y}, ${tip.targetX} ${tip.targetY} C ${tipIn.x} ${tipIn.y}, ${frX} ${frY - 30}, ${frX} ${frY} Q 80 ${300 + la} 60 ${290 + la} L 50 ${265 + la} L 46 ${260 + la} L 46 260 L 50 264 Z`;
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
