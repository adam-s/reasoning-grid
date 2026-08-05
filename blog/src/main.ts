import './app.css';
import './lib/viz/figure-heights.css';
import App from './App.svelte';
import { hydrate } from 'svelte';

// `hydrate`, not `mount`: scripts/prerender.mjs writes the rendered page into
// index.html at build time, so there is already markup here to attach to.
// `mount` would throw it away and rebuild the DOM, which loses the whole point
// and flashes the page.
export default hydrate(App, { target: document.getElementById('app')! });
