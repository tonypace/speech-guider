/**
 * Tests for the SVG articulatory renderer
 */

import { describe, it, expect, beforeEach } from 'vitest';

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
    renderer.setState({ lip_aperture: 20, glottal_aperture: 10 });
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
});
