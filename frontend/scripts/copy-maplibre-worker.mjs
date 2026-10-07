// MapLibre 6 starts its web worker from `new URL("./maplibre-gl-worker.mjs", import.meta.url)`,
// which Turbopack does not emit, so the worker request 404s and no tiles draw. Serve the
// worker (and the shared chunk it imports) from public/ instead; trip-map.tsx points
// MapLibre at it with setWorkerUrl(). Runs before `dev` and `build` so the copy always
// matches the installed maplibre-gl version.
import { copyFileSync, mkdirSync } from "node:fs";
import { createRequire } from "node:module";
import path from "node:path";

const require = createRequire(import.meta.url);
const dist = path.dirname(require.resolve("maplibre-gl/package.json")) + "/dist";
const target = path.resolve("public/maplibre");

mkdirSync(target, { recursive: true });
for (const file of ["maplibre-gl-worker.mjs", "maplibre-gl-shared.mjs"]) {
  copyFileSync(path.join(dist, file), path.join(target, file));
}
console.log(`Copied the MapLibre worker to ${path.relative(process.cwd(), target)}`);
