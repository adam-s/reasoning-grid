import { defineConfig } from 'vite';
import { svelte } from '@sveltejs/vite-plugin-svelte';

// base: './' is required by the deploy path -- scripts/sync-app.sh in the blog
// repo copies dist/ to an arbitrary subpath, and relative asset URLs mean the
// same build works at /reasoning-grid/ or anywhere else without a rebuild.
export default defineConfig({
  plugins: [svelte()],
  base: './',
  // strictPort so the sweep has a deterministic target. measure-figures.mjs
  // defaults to 5175, and when Vite silently fell through to 5177 the default
  // pointed at whatever project happened to hold that port.
  server: { port: 5175, strictPort: true },
});
