# GREY Development Limited — Website

Static marketing site for **GREY Development Limited** (Realty · Construction · Investment, Abuja, Nigeria).

- Single page: `index.html` — markup, custom CSS and JS all inline
- `assets/tailwind.css` — Tailwind, compiled ahead of time (see below)
- `assets/` — brand images, development renders/covers, downloadable brochures
- The published site loads **no third-party scripts and no webfonts**

## Run locally
Open `index.html` in a browser, or serve the folder:

```bash
python3 -m http.server 4599
```

## Rebuilding the CSS

`assets/tailwind.css` is generated. Editing it by hand will be overwritten.
Rebuild it after adding or changing any Tailwind utility class in `index.html`:

```bash
npx tailwindcss@3.4.17 -c tailwind.config.js -i in.css -o assets/tailwind.css --minify
```

The theme (the four brand colours, the aliases and the font stacks) lives in
`tailwind.config.js`. Tailwind only emits classes it can find in `index.html`,
so a class that only ever appears inside a JS string must also appear somewhere
in the markup, or it will not be generated.

**The `<link>` to `assets/tailwind.css` must stay *after* the inline `<style>`
blocks.** The utilities are expected to win ties against the component classes
above them (`text-offwhite` over `.display`, `text-[9px]` over `.eyebrow`).
Moving the link earlier turns the hero headline Charcoal on a Charcoal ground.

## Images

Covers are sized for their render box (~410px CSS, 820px at 2× DPR) and carry
intrinsic `width`/`height` so the browser reserves space before they load.
Re-export at 1000px wide; keep the hero at 1600px.

## Deploy (GitHub Pages)
Publishes from `main`, root folder. `.nojekyll` is included so files are served
as-is. A push is live in roughly a minute.
