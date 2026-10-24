import { build } from 'esbuild'
import { fileURLToPath } from 'node:url'
import { resolve } from 'node:path'
const project = fileURLToPath(new URL('../', import.meta.url))
// MapLibre supports .cjs classic workers. Bundle its official worker locally so
// development and production use the same worker format and origin.
await build({
  entryPoints: [resolve(project, 'node_modules/maplibre-gl/dist/maplibre-gl-worker.mjs')],
  outfile: resolve(project, 'public/maplibre-worker.cjs'),
  bundle: true, format: 'iife', platform: 'browser', target: 'es2022',
  minify: true, legalComments: 'eof',
})
