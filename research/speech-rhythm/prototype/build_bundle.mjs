import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const indexPath = path.join(__dirname, 'index.html');
const distDir = path.join(__dirname, 'dist');
const outputPath = path.join(distDir, 'speech-rhythm-standalone.html');

const SCRIPT_MODULES = [
    {
        src: './js/data_and_audio.js',
        filePath: path.join(__dirname, 'js', 'data_and_audio.js')
    },
    {
        src: './js/goal2_live_modes.js',
        filePath: path.join(__dirname, 'js', 'goal2_live_modes.js')
    },
    {
        src: './js/goal1_post_modes.js',
        filePath: path.join(__dirname, 'js', 'goal1_post_modes.js')
    }
];

const FALLBACK_THEME_CSS = `  <style>
    :root {
      --background: #020617;
      --foreground: #f8fafc;
      --card: #0f172a;
      --border: #1e293b;
      --muted-foreground: #94a3b8;
      --primary: #6366f1;
      --primary-foreground: #ffffff;
    }
    body {
      font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }
  </style>
`;

export function buildStandaloneHtml() {
    let html = fs.readFileSync(indexPath, 'utf8');

    if (!html.includes(':root')) {
        if (!html.includes('</head>')) {
            throw new Error('Expected </head> closing tag in index.html');
        }
        html = html.replace('</head>', () => `${FALLBACK_THEME_CSS}</head>`);
    }

    for (const mod of SCRIPT_MODULES) {
        const escapedSrc = mod.src.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        const tagRegex = new RegExp(`<script src="${escapedSrc}(?:\\?[^"]*)?"><\\/script>`);
        if (!tagRegex.test(html)) {
            throw new Error(`Expected script tag not found in index.html for: ${mod.src}`);
        }
        const source = fs.readFileSync(mod.filePath, 'utf8');
        if (source.toLowerCase().includes('</script>')) {
            throw new Error(`Unsafe </script> sequence found in ${mod.filePath}`);
        }
        // Use a replacer function so `$` sequences inside JS code are never treated as replacement patterns.
        html = html.replace(tagRegex, () => `<script>\n${source}\n  </script>`);
    }

    return html;
}

function main() {
    const checkMode = process.argv.includes('--check');
    const html = buildStandaloneHtml();
    const expectedBytes = Buffer.from(html, 'utf8');

    if (checkMode) {
        if (!fs.existsSync(outputPath)) {
            console.error(`Missing bundle: ${outputPath}. Run node build_bundle.mjs.`);
            process.exitCode = 1;
            return;
        }
        const actualBytes = fs.readFileSync(outputPath);
        if (!expectedBytes.equals(actualBytes)) {
            console.error(`Stale bundle: ${outputPath}. Run node build_bundle.mjs.`);
            process.exitCode = 1;
            return;
        }
        console.log(`Bundle up to date: ${outputPath} (${expectedBytes.length} bytes)`);
        return;
    }

    fs.mkdirSync(distDir, { recursive: true });
    fs.writeFileSync(outputPath, expectedBytes);
    console.log(`Built standalone bundle: ${outputPath} (${expectedBytes.length} bytes)`);
}

main();
