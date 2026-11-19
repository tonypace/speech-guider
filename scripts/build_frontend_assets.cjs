const { execFileSync } = require('node:child_process');
const { createHash } = require('node:crypto');
const { existsSync, mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } = require('node:fs');
const { tmpdir } = require('node:os');
const { dirname, join, resolve } = require('node:path');

const root = resolve(__dirname, '..');
const scratch = mkdtempSync(join(tmpdir(), 'speech-guider-css-'));
const check = process.argv.includes('--check');

function packageInfo(name) {
    const manifestPath = require.resolve(`${name}/package.json`);
    return {
        directory: dirname(manifestPath),
        manifest: JSON.parse(readFileSync(manifestPath, 'utf8')),
    };
}

function artifact(path, bytes) {
    const destination = join(root, 'static', path);
    if (!check) {
        mkdirSync(dirname(destination), { recursive: true });
        writeFileSync(destination, bytes);
    } else if (!existsSync(destination) || !bytes.equals(readFileSync(destination))) {
        console.error(`Stale frontend asset: static/${path}. Run npm run assets:build.`);
        process.exitCode = 1;
    }
    return createHash('sha256').update(bytes).digest('hex');
}

try {
    const tailwind = packageInfo('tailwindcss');
    const cssPath = join(scratch, 'tailwind.min.css');
    execFileSync(process.execPath, [
        join(tailwind.directory, tailwind.manifest.bin.tailwindcss),
        '--config', join(root, 'tailwind.config.cjs'),
        '--input', join(root, 'static/css/tailwind.input.css'),
        '--output', cssPath,
        '--minify',
    ], { cwd: root, stdio: 'inherit' });

    const css = 'css/tailwind.min.css';
    const tailwindLicense = 'vendor/Tailwind-LICENSE.txt';
    const manifest = {
        packages: {
            tailwindcss: tailwind.manifest.version,
        },
        sha256: {
            [css]: artifact(css, readFileSync(cssPath)),
            [tailwindLicense]: artifact(tailwindLicense, readFileSync(join(tailwind.directory, 'LICENSE'))),
        },
    };
    artifact('vendor/manifest.json', Buffer.from(`${JSON.stringify(manifest, null, 2)}\n`));

    const template = readFileSync(join(root, 'app/templates/index.html'), 'utf8');
    if (!template.includes(`"/static/${css}"`)) {
        console.error(`App template must load /static/${css}.`);
        process.exitCode = 1;
    }
} finally {
    rmSync(scratch, { recursive: true, force: true });
}
