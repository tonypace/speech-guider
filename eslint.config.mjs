import js from '@eslint/js';
import globals from 'globals';
import stylistic from '@stylistic/eslint-plugin';
import { defineConfig } from 'eslint/config';

export default defineConfig([
    {
        ignores: [
            'archive/**',
            'build/**',
            'node_modules/',
            'speech-guider/',
            'AAI/**',
            'Data/**',
            'external/**',
            'omnivoice-tts/**',
            'src-tauri/target/**',
            'static/vendor/**',
            'coverage/**',
            'playwright-report/**',
            'test-results/**'
        ]
    },
    {
        files: ['**/*.{js,mjs,cjs,jsx}'],
        plugins: { js, '@stylistic': stylistic },
        extends: ['js/recommended'],
        languageOptions: {
            globals: globals.browser,
            ecmaVersion: 'latest',
            sourceType: 'module'
        },
        rules: {
            '@stylistic/indent': ['error', 4],
            '@stylistic/linebreak-style': ['error', 'unix'],
            '@stylistic/quotes': ['error', 'single'],
            '@stylistic/semi': ['error', 'always'],
            'no-unused-vars': 'warn',
            'no-console': 'off'
        }
    },
    {
        files: [
            'playwright.config.js',
            'tailwind.config.cjs',
            'vitest.config.js',
            'scripts/**/*.cjs',
            'tests/e2e/**/*.js',
            'tests/js/**/*.js'
        ],
        languageOptions: { globals: { ...globals.node, ...globals.browser } }
    },
    {
        files: ['static/js/*.js', 'tests/js/**/*.test.js'],
        languageOptions: {
            globals: {
                IntercomRecorder: 'readonly'
            }
        }
    },
    {
        files: ['tests/js/**/*.test.js', 'tests/js/setup.js'],
        languageOptions: {
            globals: {
                describe: 'readonly',
                it: 'readonly',
                test: 'readonly',
                expect: 'readonly',
                beforeAll: 'readonly',
                beforeEach: 'readonly',
                afterAll: 'readonly',
                afterEach: 'readonly',
                vi: 'readonly'
            }
        }
    },
    {
        files: ['static/js/*.js'],
        languageOptions: {
            globals: {
                ...globals.browser,
                SvgArticulatoryRenderer: 'readonly'
            }
        }
    }
]);
