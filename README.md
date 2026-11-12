# GREY Development Limited — Website

Static marketing site for **GREY Development Limited** (Realty · Construction · Investment, Abuja, Nigeria).

- Home page: `index.html` — markup, custom CSS and JS all inline
- `developments/<slug>/` — one generated page per development (see below)
- `assets/tailwind.css` — Tailwind, compiled ahead of time (see below)
- `assets/` — brand images, development renders/covers, downloadable brochures
- The published site loads **no third-party scripts and no webfonts**

## Run locally
Open `index.html` in a browser, or serve the folder:

```bash
python3 -m http.server 4599
```

## Development pages

Each development has its own page at `developments/<slug>/index.html`. These
are **generated** by `build_pages.py` - do not edit them by hand. The home page
is the source: the cards in `#projectGrid` supply name, location, status, stage
and brochure; `UNIT_DATA` supplies unit types and room schedules; the styles,
header and footer are copied from `index.html`. Facts for developments without
a `UNIT_DATA` entry live in the `BROCHURE` table in the script, each with the
brochure page it was read from.

After changing `index.html`, run one command to regenerate the pages, the
stylesheet and the sitemap:

```bash
./build.sh
```

## Rebuilding the CSS

`assets/tailwind.css` is generated. Editing it by hand will be overwritten.
`./build.sh` does this for you. To rebuild only the stylesheet:

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

Covers are sized for their render box (~410px CSS, 820px at 2x DPR) and carry
intrinsic `width`/`height` so the browser reserves space before they load.
Re-export at 1000px wide; keep the hero at 1600px.

The gallery band renders two covers at ~615px, so those two also have `-lg`
variants at 1400px, offered through `srcset` (phones still take the 1000px
file). Both sizes are rendered from the brochure PDF, which holds the
full-resolution artwork:

```bash
sips -s format jpeg -s formatOptions 82 --resampleWidth 1400 \
  assets/brochures/<name>-brochure.pdf --out assets/projects/<name>-cover-lg.jpg
```

## Deploy (GitHub Pages)
Publishes from `main`, root folder. `.nojekyll` is included so files are served
as-is. A push is live in roughly a minute.
