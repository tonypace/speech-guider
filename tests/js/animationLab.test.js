/**
 * Tests for the SVG articulatory renderer
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';

describe('SvgArticulatoryRenderer', () => {
    let renderer;
    let container;

    beforeEach(async () => {
        document.body.innerHTML = '<div id="svg-articulatory-animation"></div>';
        container = document.getElementById('svg-articulatory-animation');
        const mod = await import('../../static/js/svg_articulatory_renderer.js');
        renderer = new mod.SvgArticulatoryRenderer(container, { prefix: 'test' });
    });

    it('mounts an SVG surface', () => {
        renderer.mount();
        expect(container.querySelector('svg')).toBeTruthy();
        expect(container.querySelector('#test-mouth-svg')).toBeTruthy();
    });

    it('renders state updates', () => {
        renderer.mount();
        renderer.setState({ lip_aperture: 0.5, glottal_aperture: 1 });
        expect(container.querySelector('#test-jaw-group')).toBeTruthy();
        expect(container.querySelector('#test-tongue').getAttribute('d')).toContain('C');
    });

    it('starts and stops animation loops', () => {
        renderer.mount();
        renderer.startAnimation();
        expect(renderer.isRunning).toBe(true);
        renderer.stopAnimation();
        expect(renderer.isRunning).toBe(false);
    });

    it('starts animation idempotently (no double-start)', () => {
        renderer.mount();
        renderer.startAnimation();
        renderer.startAnimation();
        expect(renderer.isRunning).toBe(true);
        renderer.stopAnimation();
    });

    it('stopAnimation clears animationId', () => {
        renderer.mount();
        renderer.startAnimation();
        renderer.stopAnimation();
        expect(renderer.animationId).toBeNull();
    });

    it('accepts highlight zones', () => {
        renderer.mount();
        renderer.setHighlightZone('tongue_body');
        expect(renderer.highlightZone).toBe('tongue_body');
    });

    it('handles missing containers gracefully', async () => {
        const mod = await import('../../static/js/svg_articulatory_renderer.js');
        const missing = new mod.SvgArticulatoryRenderer(null);
        expect(() => missing.mount()).not.toThrow();
    });

    it('setState merges with existing state', () => {
        renderer.mount();
        renderer.setState({ lip_aperture: 0.2 });
        expect(renderer.state.lip_aperture).toBe(0.2);
        expect(renderer.state.lip_protrusion).toBe(0.71);
    });

    it('setState auto-mounts if not mounted', () => {
        renderer.setState({ lip_aperture: 0.12 });
        expect(renderer._mounted).toBe(true);
    });

    it('destroy clears container and stops animation', () => {
        renderer.mount();
        renderer.startAnimation();
        renderer.destroy();
        expect(renderer.isRunning).toBe(false);
        expect(renderer._mounted).toBe(false);
        expect(container.innerHTML).toBe('');
    });

    it('render calls _renderFrame and _renderVoicing', () => {
        renderer.mount();
        const frameSpy = vi.spyOn(renderer, '_renderFrame');
        const voicingSpy = vi.spyOn(renderer, '_renderVoicing');
        renderer.render();
        expect(frameSpy).toHaveBeenCalled();
        expect(voicingSpy).toHaveBeenCalled();
    });

    it('setHighlightZone(null) clears highlight and re-renders', () => {
        renderer.mount();
        renderer.setHighlightZone('tongue_body');
        renderer.setHighlightZone(null);
        expect(renderer.highlightZone).toBeNull();
    });

    it('highlightZone glottis updates SVG elements', () => {
        renderer.mount();
        renderer.setHighlightZone('glottis');
        const glottisHole = container.querySelector('#test-glottis-hole');
        expect(glottisHole).toBeTruthy();
    });

    it('highlightZone lips updates upper-face and lower-face stroke', () => {
        renderer.mount();
        renderer.setHighlightZone('lips');
        const upperFace = container.querySelector('#test-upper-face');
        const lowerFace = container.querySelector('#test-lower-face');
        expect(upperFace).toBeTruthy();
        expect(lowerFace).toBeTruthy();
        expect(upperFace.getAttribute('stroke')).toBe('#f59e0b');
    });

    it('highlightZone tongue_body sets tongue stroke to accent color', () => {
        renderer.mount();
        renderer.setHighlightZone('tongue_body');
        const tongue = container.querySelector('#test-tongue');
        expect(tongue.getAttribute('stroke')).toBe('#f59e0b');
    });

    it('highlightZone tongue_tip sets tongue stroke to accent color', () => {
        renderer.mount();
        renderer.setHighlightZone('tongue_tip');
        const tongue = container.querySelector('#test-tongue');
        expect(tongue.getAttribute('stroke')).toBe('#f59e0b');
    });

    it('highlightZone velum sets palate stroke to accent color', () => {
        renderer.mount();
        renderer.setHighlightZone('velum');
        const palate = container.querySelector('#test-palate');
        expect(palate.getAttribute('stroke')).toBe('#f59e0b');
    });

    it('highlightZone tongue_root sets tongue stroke to accent color', () => {
        renderer.mount();
        renderer.setHighlightZone('tongue_root');
        const tongue = container.querySelector('#test-tongue');
        expect(tongue.getAttribute('stroke')).toBe('#f59e0b');
    });

    it('jaw-group transform updates with lip_aperture', () => {
        renderer.mount();
        renderer.setState({ lip_aperture: 0.5 });
        const jawGroup = container.querySelector('#test-jaw-group');
        expect(jawGroup.getAttribute('transform')).toContain('translate(0, 14.00)');
        expect(jawGroup.getAttribute('transform')).toContain('rotate(-2.40, 225, 290)');
    });

    it('glottal_aperture updates glottis-hole points', () => {
        renderer.mount();
        renderer.setState({ glottal_aperture: 2 / 3 });
        const glottisHole = container.querySelector('#test-glottis-hole');
        const pts = glottisHole.getAttribute('points');
        expect(pts).toContain('0,-10');
    });

    it('nasal voicing opacity responds to velic_aperture', () => {
        renderer.mount();
        renderer.setState({ velic_aperture: 0.5 });
        const nasalVoicing = container.querySelector('#test-nasal-voicing');
        expect(nasalVoicing).toBeTruthy();
        expect(parseFloat(nasalVoicing.getAttribute('opacity'))).toBeGreaterThan(0);
    });

    it('tongue opacity decreases as lateral_tongue_drop increases', () => {
        renderer.mount();
        renderer.setState({ lateral_tongue_drop: 1 });
        const tongue = container.querySelector('#test-tongue');
        const opacity = parseFloat(tongue.getAttribute('opacity'));
        expect(opacity).toBeLessThan(1.0);
    });

    it('wind-icon appears when lateral_tongue_drop >= 20', () => {
        renderer.mount();
        renderer.setState({ lateral_tongue_drop: 0.625 });
        const wind = container.querySelector('#test-wind-icon');
        expect(parseFloat(wind.getAttribute('opacity'))).toBeGreaterThan(0);
    });

    it('constructor merges options.state with DEFAULT_STATE', async () => {
        const mod = await import('../../static/js/svg_articulatory_renderer.js');
        const r = new mod.SvgArticulatoryRenderer(document.body, {
            state: { lip_aperture: 0.99 },
        });
        expect(r.state.lip_aperture).toBe(0.99);
        expect(r.state.lip_protrusion).toBe(0.71);
    });

    it('constructor uses prefix from options', async () => {
        const mod = await import('../../static/js/svg_articulatory_renderer.js');
        const r = new mod.SvgArticulatoryRenderer(document.body, { prefix: 'myprefix' });
        expect(r.prefix).toBe('myprefix');
    });

    it('state is initialized with default values', async () => {
        const mod = await import('../../static/js/svg_articulatory_renderer.js');
        const r = new mod.SvgArticulatoryRenderer(document.body);
        expect(r.state.lip_aperture).toBe(0.25);
        expect(r.state.lip_protrusion).toBe(0.71);
        expect(r.state.tongue_tip_constriction_location).toBe(0.2);
        expect(r.state.tongue_tip_constriction_degree).toBe(1);
        expect(r.state.lateral_tongue_drop).toBe(0);
        expect(r.state.velic_aperture).toBe(0);
        expect(r.state.tongue_body_constriction_location).toBe(0.7);
        expect(r.state.tongue_body_constriction_degree).toBe(1);
        expect(r.state.glottal_aperture).toBe(0);
    });

    it('maps tongue tip and tongue body to separate roof domains', async () => {
        const mod = await import('../../static/js/svg_articulatory_renderer.js');
        const r = new mod.SvgArticulatoryRenderer(document.body);
        expect(r._mapLocation(0, 'tip')).toBeCloseTo(0.0, 4);
        expect(r._mapLocation(0.5, 'tip')).toBeCloseTo(0.135, 4);
        expect(r._mapLocation(1, 'tip')).toBeCloseTo(0.34, 4);
        expect(r._mapLocation(0, 'body')).toBeCloseTo(0.22, 4);
        expect(r._mapLocation(0.5, 'body')).toBeCloseTo(0.48, 4);
        expect(r._mapLocation(1, 'body')).toBeCloseTo(0.88, 4);
    });

    it('clamps tongue degree and labiodental_retraction to normalized range', async () => {
        const mod = await import('../../static/js/svg_articulatory_renderer.js');
        const r = new mod.SvgArticulatoryRenderer(document.body);
        r.mount();
        r.setState({ tongue_tip_constriction_degree: 1.4, labiodental_retraction: 0.8 });
        expect(r.state.tongue_tip_constriction_degree).toBeCloseTo(1, 4);
        expect(r.state.labiodental_retraction).toBeCloseTo(0.8, 4);
        r.setState({ tongue_tip_constriction_degree: -0.2, labiodental_retraction: 1.5 });
        expect(r.state.tongue_tip_constriction_degree).toBeCloseTo(0, 4);
        expect(r.state.labiodental_retraction).toBeCloseTo(1, 4);
    });

    it('clips oral voicing at effective tongue closure anchors', async () => {
        const mod = await import('../../static/js/svg_articulatory_renderer.js');
        const r = new mod.SvgArticulatoryRenderer(document.body);
        const clipX = r._getOralVoicingClipX({
            lipAperture: 10,
            lipProtrusion: 10,
            lateralDrop: 0,
            ttcd: 0,
            tbcd: 1,
            tip: { anchorX: 54 },
            body: { anchorX: 180 },
        });
        expect(clipX).toBe(54);
    });

    it('does not clip oral voicing for open tongue constrictions', async () => {
        const mod = await import('../../static/js/svg_articulatory_renderer.js');
        const r = new mod.SvgArticulatoryRenderer(document.body);
        const clipX = r._getOralVoicingClipX({
            lipAperture: 10,
            lipProtrusion: 10,
            lateralDrop: 0,
            ttcd: 0.12,
            tbcd: 0.2,
            tip: { anchorX: 54 },
            body: { anchorX: 180 },
        });
        expect(clipX).toBe(0);
    });
});

describe('clamp (via renderer behavior)', () => {
    it('accepts out-of-range lip_aperture without throwing', async () => {
        document.body.innerHTML = '<div id="c"></div>';
        const mod = await import('../../static/js/svg_articulatory_renderer.js');
        const r = new mod.SvgArticulatoryRenderer(document.getElementById('c'));
        r.mount();
        expect(() => r.setState({ lip_aperture: 200 })).not.toThrow();
        expect(r.state.lip_aperture).toBe(1);
    });

    it('accepts negative glottal_aperture without throwing', async () => {
        document.body.innerHTML = '<div id="c"></div>';
        const mod = await import('../../static/js/svg_articulatory_renderer.js');
        const r = new mod.SvgArticulatoryRenderer(document.getElementById('c'));
        r.mount();
        expect(() => r.setState({ glottal_aperture: -50 })).not.toThrow();
        expect(r.state.glottal_aperture).toBe(0);
    });
});
