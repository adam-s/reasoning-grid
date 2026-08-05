// The server half of the build. Vite builds this with --ssr into dist-ssr/,
// and scripts/prerender.mjs calls it to produce the HTML that ships.
//
// No CSS import here on purpose. Styles come from the client build's <link>,
// which is already in index.html and loads without JavaScript.
import { render } from 'svelte/server';
import App from './App.svelte';

export function renderApp(): { head: string; body: string } {
  return render(App);
}
