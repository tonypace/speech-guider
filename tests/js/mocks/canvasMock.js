// Mock for Canvas 2D Context
import { vi } from 'vitest';

export const createMockCanvasContext = () => {
  return {
    // Properties
    fillStyle: '',
    strokeStyle: '',
    lineWidth: 1,
    lineCap: 'butt',
    lineJoin: 'miter',
    miterLimit: 10,
    globalAlpha: 1,
    globalCompositeOperation: 'source-over',
    font: '10px sans-serif',
    textAlign: 'start',
    textBaseline: 'alphabetic',
    
    // Path methods
    beginPath: vi.fn(),
    moveTo: vi.fn(),
    lineTo: vi.fn(),
    arc: vi.fn(),
    arcTo: vi.fn(),
    bezierCurveTo: vi.fn(),
    quadraticCurveTo: vi.fn(),
    rect: vi.fn(),
    closePath: vi.fn(),
    
    // Drawing methods
    fill: vi.fn(),
    stroke: vi.fn(),
    fillRect: vi.fn(),
    strokeRect: vi.fn(),
    clearRect: vi.fn(),
    
    // Style methods
    createLinearGradient: vi.fn(() => ({
      addColorStop: vi.fn(),
    })),
    createRadialGradient: vi.fn(() => ({
      addColorStop: vi.fn(),
    })),
    createPattern: vi.fn(() => ({})),
    
    // Image methods
    drawImage: vi.fn(),
    getImageData: vi.fn((x, y, width, height) => ({
      data: new Uint8ClampedArray(width * height * 4),
      width,
      height,
    })),
    putImageData: vi.fn(),
    
    // Text methods
    fillText: vi.fn(),
    strokeText: vi.fn(),
    measureText: vi.fn((text) => ({
      width: text.length * 8,
      actualBoundingBoxAscent: 10,
      actualBoundingBoxDescent: 2,
    })),
    
    // State methods
    save: vi.fn(),
    restore: vi.fn(),
    
    // Transform methods
    scale: vi.fn(),
    rotate: vi.fn(),
    translate: vi.fn(),
    transform: vi.fn(),
    setTransform: vi.fn(),
    resetTransform: vi.fn(),
    
    // Clipping
    clip: vi.fn(),
    
    // Canvas reference
    canvas: null,
  };
};

export const createMockCanvas = (width = 300, height = 150) => {
  const mockContext = createMockCanvasContext();
  
  const canvas = {
    width,
    height,
    getContext: vi.fn((type) => {
      if (type === '2d') {
        mockContext.canvas = canvas;
        return mockContext;
      }
      return null;
    }),
    toDataURL: vi.fn((type = 'image/png') => `data:${type};base64,mockdata`),
    toBlob: vi.fn((callback) => {
      callback(new Blob(['mock'], { type: 'image/png' }));
    }),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  };
  
  return { canvas, context: mockContext };
};

// Helper to mock canvas in DOM
export function mockCanvasInDocument(canvasId, width = 300, height = 150) {
  const { canvas, context } = createMockCanvas(width, height);
  canvas.id = canvasId;
  
  // Add to document
  document.body.appendChild(canvas);
  
  return { canvas, context };
}
