// Test environment setup for Vitest
import { afterEach, vi } from 'vitest';
import { JSDOM } from 'jsdom';
import { createMockCanvasContext } from './mocks/canvasMock.js';

// Node's optional Web Storage must not override the browser test environment.
const storage = new JSDOM('', { url: 'https://localhost/' }).window.localStorage;
Object.defineProperty(globalThis, 'localStorage', { configurable: true, value: storage });

const installCanvasContextMock = () => {
    if (typeof HTMLCanvasElement === 'undefined') return;
    HTMLCanvasElement.prototype.getContext = vi.fn(function getContext(type) {
        if (type !== '2d') return null;
        return createMockCanvasContext(this);
    });
};

installCanvasContextMock();

// Mock window.matchMedia
Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: vi.fn().mockImplementation((query) => ({
        matches: false,
        media: query,
        onchange: null,
        addListener: vi.fn(),
        removeListener: vi.fn(),
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn(),
    })),
});

// Mock ResizeObserver
global.ResizeObserver = vi.fn().mockImplementation(() => ({
    observe: vi.fn(),
    unobserve: vi.fn(),
    disconnect: vi.fn(),
}));

// Mock requestAnimationFrame
global.requestAnimationFrame = vi.fn((callback) => {
    return setTimeout(callback, 16);
});

global.cancelAnimationFrame = vi.fn((id) => {
    clearTimeout(id);
});

// Mock performance.now
global.performance = {
    now: vi.fn(() => Date.now()),
};

// Cleanup after each test
afterEach(() => {
    vi.clearAllMocks();
    installCanvasContextMock();
    storage.clear();
    document.body.innerHTML = '';
});
