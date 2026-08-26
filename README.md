# GREY Development Limited — Website

Static marketing site for **GREY Development Limited** (Realty · Construction · Investment, Abuja, Nigeria).

- Single self-contained page: `index.html` (HTML + Tailwind via CDN)
- Assets in `assets/` — brand images, development renders/covers, and downloadable brochures
- No build step required — it's plain static files

## Run locally
Just open `index.html` in a browser, or serve the folder:

```bash
python3 -m http.server 4599
# then visit http://localhost:4599
```

## Deploy (GitHub Pages)
This repo is set up to publish with GitHub Pages from the `main` branch, root folder.
`.nojekyll` is included so the files are served exactly as-is.
