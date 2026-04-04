// DOM utility mocks and helpers
import { vi } from 'vitest';

/**
 * Create a mock DOM element with common properties and methods
 */
export function createMockElement(tag = 'div', attributes = {}) {
  const element = document.createElement(tag);
  
  // Set attributes
  Object.entries(attributes).forEach(([key, value]) => {
    if (key === 'className') {
      element.className = value;
    } else if (key === 'innerHTML') {
      element.innerHTML = value;
    } else if (key === 'textContent') {
      element.textContent = value;
    } else {
      element.setAttribute(key, value);
    }
  });
  
  // Add mock methods that might be called
  element.getBoundingClientRect = vi.fn(() => ({
    top: 0,
    left: 0,
    bottom: 100,
    right: 100,
    width: 100,
    height: 100,
    x: 0,
    y: 0,
    toJSON: () => ({}),
  }));
  
  element.scrollIntoView = vi.fn();
  element.focus = vi.fn();
  element.blur = vi.fn();
  element.click = vi.fn();
  
  return element;
}

/**
 * Simulate a DOM event
 */
export function simulateEvent(element, eventType, eventData = {}) {
  const event = new Event(eventType, {
    bubbles: true,
    cancelable: true,
    ...eventData,
  });
  
  Object.assign(event, eventData);
  
  element.dispatchEvent(event);
  return event;
}

/**
 * Simulate a keyboard event
 */
export function simulateKeyEvent(element, key, type = 'keydown', modifiers = {}) {
  const event = new KeyboardEvent(type, {
    key,
    code: `Key${key.toUpperCase()}`,
    bubbles: true,
    cancelable: true,
    ...modifiers,
  });
  
  element.dispatchEvent(event);
  return event;
}

/**
 * Simulate a mouse event
 */
export function simulateMouseEvent(element, type, coordinates = {}) {
  const event = new MouseEvent(type, {
    bubbles: true,
    cancelable: true,
    clientX: coordinates.x || 0,
    clientY: coordinates.y || 0,
    ...coordinates,
  });
  
  element.dispatchEvent(event);
  return event;
}

/**
 * Wait for a specified time (for async tests)
 */
export function wait(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

/**
 * Wait for the next animation frame
 */
export function waitForAnimationFrame() {
  return new Promise(resolve => {
    requestAnimationFrame(resolve);
  });
}

/**
 * Create a complete mock recorder UI
 */
export function createMockRecorderUI() {
  const container = createMockElement('div', { id: 'recorder' });
  const recordBtn = createMockElement('button', { id: 'record-btn' });
  const timer = createMockElement('span', { id: 'rec-timer', textContent: '0:00' });
  const waveformCanvas = createMockElement('canvas', { id: 'waveform' });
  const fileUploadSection = createMockElement('div', { id: 'file-upload-section' });
  
  container.appendChild(recordBtn);
  container.appendChild(timer);
  container.appendChild(waveformCanvas);
  container.appendChild(fileUploadSection);
  
  document.body.appendChild(container);
  
  return {
    container,
    recordBtn,
    timer,
    waveformCanvas,
    fileUploadSection,
  };
}

/**
 * Cleanup all mock elements
 */
export function cleanupMocks() {
  document.body.innerHTML = '';
  vi.clearAllMocks();
}
