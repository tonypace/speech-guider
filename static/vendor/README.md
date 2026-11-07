# Local frontend assets

The app serves these assets directly from `static/`; starting FastAPI or the
desktop backend does not require Node.js or a CDN connection.

- `css/tailwind.min.css` is generated with [Tailwind CSS 3.4.19](https://github.com/tailwindlabs/tailwindcss/releases/tag/v3.4.19).
  Its inputs are `css/tailwind.input.css` and `tailwind.config.cjs`. The config
  scans templates, JavaScript, and Python-generated UI markup; its safelist
  keeps the classes used by runtime status and control updates.
- `vendor/plotly-2.32.0/plotly.min.js` is the unchanged distribution from
  [Plotly.js 2.32.0](https://github.com/plotly/plotly.js/releases/tag/v2.32.0),
  copied from the `plotly.js-dist-min` npm package. The version matches the
  previously used CDN bundle.

Package tarball integrity is pinned in `package-lock.json`. The generated
`manifest.json` records SHA-256 checksums of the served CSS, JavaScript, and
included upstream MIT licenses. After changing UI classes or package versions,
run `npm ci` then `npm run assets:build`; keep the template asset paths and
this provenance note in sync with package upgrades. `npm run assets:check`
rebuilds in a temporary directory and fails if a checked-in artifact is stale.
