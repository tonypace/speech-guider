// Test environment setup for Vitest
import { vi } from 'vitest';
import { JSDOM } from 'jsdom';

// Node's optional Web Storage must not override the browser test environment.
const storage = new JSDOM('', { url: 'https://localhost/' }).window.localStorage;
Object.defineProperty(globalThis, 'localStorage', { configurable: true, value: storage });

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
    storage.clear();
    document.body.innerHTML = '';
});

console.log('Test environment setup complete');
