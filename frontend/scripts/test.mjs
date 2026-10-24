import { mkdirSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { resolve } from 'node:path'
import { spawnSync } from 'node:child_process'
const project = fileURLToPath(new URL('../', import.meta.url))
const temp = resolve(project, '.cache', 'test-temp')
mkdirSync(temp, { recursive: true })
const result = spawnSync(process.execPath, [resolve(project, 'node_modules/vitest/vitest.mjs'), 'run', ...process.argv.slice(2)], {
  cwd: project, stdio: 'inherit', env: { ...process.env, TEMP: temp, TMP: temp },
})
if (result.error) { console.error(result.error.message); process.exit(1) }
process.exit(result.status ?? 1)
