#!/usr/bin/env python3
"""Generate one page per development at developments/<slug>/index.html.

index.html stays the single source of truth: the cards in #projectGrid supply
name, location, status, stage, target, cover and brochure; UNIT_DATA supplies
the unit types and room schedules; the <style> block, header and footer are
lifted from it verbatim so the pages cannot drift from the home page.

A development without a UNIT_DATA entry (Grey Altura, whose brochure is image-only)
gets a short page with only what its card says. Nothing here is estimated.

Run ./build.sh rather than this file directly - the Tailwind stylesheet has to
be rebuilt afterwards, because it only contains classes it finds in the HTML.
"""
import html, json, re, struct, subprocess, sys
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent
SITE = 'https://greydevelopmentng.com'
STAGES = ['Slab', 'Superstructure', 'Roofing', 'Finishing', 'Handover']
STATUS = {'selling': 'Now selling', 'completed': 'Completed', 'coming': 'Coming soon'}
SLUGS = {
    "Shafa's Residences": 'shafas-residences', "Amrah's Villas": 'amrahs-villas',
    'Eden I': 'eden-i', 'The Eden II': 'eden-ii',
    'Grey Oasis': 'grey-oasis', 'Grey Altura': 'grey-altura',
}
# The enquiry form's <option> text, where it differs from the card name.
FORM_OPTION = {'The Eden II': 'EDEN II'}

# Brochure pages shown on each development page, as (page, caption). `./build.sh render`
# re-exports them from the PDFs into assets/projects/<slug>/; a normal build only reads them.
MEDIA = {
    'shafas-residences': {
        'views': [(13, 'view-shafas'), (12, 'hero-shafas'), (14, 'interior-shafas')],
        'map': [(4, 'Location')],
        'pdf': 'shafas-residences-brochure.pdf',
        'plans': [(6, 'Site plan'), (8, 'Terrace \u2014 ground floor'), (9, 'Terrace \u2014 first floor'),
                  (10, 'Terrace \u2014 second floor'), (11, 'Flats \u2014 ground to second floor')],
        'gallery': [(12, 'The estate'), (13, 'The terraces'), (14, 'Living room'), (15, 'Living room'),
                    (16, 'Lounge and kitchen'), (17, 'Bedroom'), (18, 'Living room')]},
    'amrahs-villas': {
        'views': [(10, 'view-amrahs-villas')],
        'map': [(4, 'Location')],
        'pdf': 'amrahs-villas-brochure.pdf',
        'plans': [(7, 'Ground floor'), (8, 'First floor'), (9, 'Pent floor')],
        'gallery': [(10, 'Front elevation'), (11, 'The villas'), (12, 'Corner view'), (13, 'The balconies')]},
    'eden-ii': {
        'views': [(12, 'view-eden-ii'), (13, 'hero-eden-ii'), (15, 'interior-eden-ii')],
        'map': [(4, 'Location')],
        'pdf': 'eden-ii-brochure.pdf',
        'plans': [(8, 'Terrace \u2014 ground floor'), (9, 'Terrace \u2014 first floor'),
                  (10, 'Terrace \u2014 second floor'), (11, 'Block of flats')],
        'gallery': [(12, 'The terraces'), (13, 'The courtyard'), (14, 'Block of flats'), (15, 'Living room'),
                    (16, 'Kitchen and dining area'), (17, 'Bedroom')]},
    'eden-i': {
        'views': [(11, 'view-eden-i')],
        'map': [(4, 'Location')],
        'pdf': 'eden-i-brochure.pdf',
        'plans': [(8, 'Ground floor'), (9, 'First floor'), (10, 'Second floor')],
        'gallery': [(11, 'The terraces'), (12, 'The estate'), (13, 'Front elevation'), (14, 'Living room'),
                    (15, 'Kitchen'), (16, 'Dining area'), (17, 'Bedroom')]},
    'grey-oasis': {
        'views': [(1, 'hero-grey-oasis', (0.18, 0.742))],
        'map': [(3, 'Location')],
        'pdf': 'grey-oasis-brochure.pdf',
        'plans': [(7, 'Ground floor'), (8, 'First floor')],
        'gallery': [(5, 'Exterior'), (6, 'Exterior'), (9, 'Living room'), (10, 'Family living room'),
                    (11, 'Kitchen'), (12, 'Master bedroom'), (13, 'Master bathroom')]},
}

e = html.escape
ARROW = ('<svg class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
         'stroke-linecap="square" aria-hidden="true"><path d="M5 12h14M13 6l6 6-6 6"/></svg>')


def jpeg_size(path):
    """Width and height of a JPEG, read from its frame header."""
    with open(path, 'rb') as f:
        f.read(2)
        while True:
            marker, = struct.unpack('>H', f.read(2))
            size, = struct.unpack('>H', f.read(2))
            if 0xFFC0 <= marker <= 0xFFCF and marker not in (0xFFC4, 0xFFC8, 0xFFCC):
                f.read(1)
                h, w = struct.unpack('>HH', f.read(4))
                return w, h
            f.read(size - 2)


def render():
    """Re-export clean renders, floor plans, gallery pages and maps from the brochure PDFs."""
    import tempfile
    tool = Path(tempfile.gettempdir()) / 'grey-pdfpage'
    subprocess.run(['swiftc', '-O', str(ROOT / 'tools/pdfpage.swift'), '-o', str(tool)], check=True)
    for slug, m in MEDIA.items():
        pdf = ROOT / 'assets/brochures' / m['pdf']
        # Clean renders for the hero, cards and galleries: a gallery page with its caption
        # strip cut off (or, for a cover, just the band holding the render), at two widths.
        for view in m.get('views', []):
            page_no, name = view[0], view[1]
            top, bottom = view[2] if len(view) > 2 else (0.0, 0.855)
            tmp = Path(tempfile.gettempdir()) / 'grey-view.jpg'
            subprocess.run([str(tool), str(pdf), str(page_no), '2400', str(tmp), '0.92'], check=True)
            # sips centres the crop when the offset is 0, so the top edge is asked for as row 1.
            _, ph = jpeg_size(tmp)   # fractions are of the page height, which is not the width
            subprocess.run(['sips', '-c', str(round(ph * (bottom - top))), '2400', '--cropOffset',
                            str(max(1, round(ph * top))), '0', str(tmp)], check=True, capture_output=True)
            for w, q in ((2000, '78'), (1100, '76')):
                subprocess.run(['sips', '-s', 'format', 'jpeg', '-s', 'formatOptions', q, '--resampleWidth', str(w),
                                str(tmp), '--out', str(ROOT / 'assets/projects' / f'{name}-{w}.jpg')],
                               check=True, capture_output=True)
        out = ROOT / 'assets/projects' / slug
        out.mkdir(exist_ok=True)
        for kind in ('plans', 'gallery', 'map'):
            for page_no, _ in m[kind]:
                subprocess.run([str(tool), str(pdf), str(page_no), '1600',
                                str(out / f'{kind[:4]}-p{page_no:02d}.jpg'), '0.8'], check=True)
        print('rendered', slug)


def media_figs(slug, kind, name):
    figs = ''
    for n, (page_no, cap) in enumerate(MEDIA.get(slug, {}).get(kind, [])):
        rel = f'assets/projects/{slug}/{kind[:4]}-p{page_no:02d}.jpg'
        if not (ROOT / rel).exists():
            continue
        w, h = jpeg_size(ROOT / rel)
        what = {'plans': 'floor plan', 'map': 'location map from the brochure'}.get(kind, 'artist\u2019s impression')
        figs += (f'<figure class="reveal"{" data-delay=1" if n % 2 else ""}>'
                 f'<a href="/{rel}" target="_blank" rel="noopener" class="gal block border border-line" data-lb data-cap="{e(cap)}" aria-label="{e(cap)} \u2014 view larger">'
                 f'<img src="/{rel}" width="{w}" height="{h}" alt="{e(name)} \u2014 {e(cap)}, {what}" loading="lazy" decoding="async" class="w-full h-auto block" /></a>'
                 f'<figcaption class="mono text-[10px] uppercase tracking-[0.18em] text-muted mt-3">{e(cap)}</figcaption></figure>')
    return figs


def between(s, a, b, start=0):
    i = s.index(a, start)
    j = s.index(b, i) + len(b)
    return s[i:j]


def rebase(fragment):
    """Point a fragment lifted from the home page at the site root."""
    fragment = re.sub(r'(href|src)="assets/', r'\1="/assets/', fragment)
    return re.sub(r'href="#([a-z]+)"', r'href="/#\1"', fragment)


def parse_cards(src):
    grid = src[src.index('id="projectGrid"'):src.index('id="projEmpty"') if 'id="projEmpty"' in src else None]
    cards = []
    for m in re.finditer(r'<article class="reveal group[^>]*>.*?</article>', grid, re.S):
        a = m.group(0)
        g = lambda pat: (re.search(pat, a, re.S) or [None, ''])[1].strip()
        name = html.unescape(re.sub(r'<[^>]+>', '', g(r'<h3[^>]*>(.*?)</h3>')))
        cards.append({
            'name': name, 'slug': SLUGS[name],
            'status': g(r'data-status="([^"]*)"'), 'stage': int(g(r'data-stage="([^"]*)"') or 0),
            'updated': g(r'data-updated="([^"]*)"'),
            'cover': g(r'<img src="([^"]*)"'), 'alt': html.unescape(g(r'alt="([^"]*)"')),
            'loc': html.unescape(g(r'text-slate mt-2">(.*?)</p>')),
            'desc': html.unescape(g(r'<p class="text-body text-sm mt-3[^>]*>(.*?)</p>')),
            'brochure': g(r'href="(assets/brochures/[^"]*)"'),
            'unit': html.unescape(g(r'data-unit="([^"]*)"')),
        })
    assert len(cards) == len(SLUGS), f'expected {len(SLUGS)} cards, found {len(cards)}'
    return cards


def parse_units(src):
    i = src.index('const UNIT_DATA = ') + len('const UNIT_DATA = ')
    literal = src[i:src.index('\n    };', i) + len('\n    }')]
    out = subprocess.run(['node', '-e', 'process.stdout.write(JSON.stringify((' + literal + ')))'],
                         capture_output=True, text=True, check=True).stdout
    return json.loads(out)


def stage_label(st):
    return 'In planning' if st == 0 else ('Delivered' if st >= 5 else STAGES[st])


def type_block(t):
    hl = ''.join(f'<li class="flex gap-3 text-sm text-body"><span class="mt-[11px] w-3 h-px bg-gold shrink-0"></span>{e(x)}</li>'
                 for x in t['highlights'])
    if t['floors']:
        floors = ''
        for f in t['floors']:
            note = f.get('note', '')
            rows = ''.join(f'<div class="uspec text-sm"><dt>{e(r[0])}</dt><dd>{e(r[1])}</dd></div>' for r in f['rooms'])
            floors += (f'<div class="mb-8 last:mb-0"><div class="flex items-baseline justify-between mb-2 border-b border-line pb-2">'
                       f'<h4 class="h3">{e(f["name"])}</h4>'
                       f'<span class="mono text-[10px] uppercase text-muted tracking-[0.14em]">{e(note)}</span></div><dl>{rows}</dl></div>')
        right = f'<p class="eyebrow text-[10px] mb-4">Room schedule</p>{floors}'
    else:
        right = ('<p class="eyebrow text-[10px] mb-4">Floor plans</p>'
                 '<p class="text-body text-sm leading-relaxed">Dimensioned floor plans for this unit type are published in the brochure.</p>')
    return f'''
        <div class="reveal grid lg:grid-cols-[minmax(0,24rem)_minmax(0,1fr)] gap-10 lg:gap-20 py-12 border-t border-line first:border-t-0 first:pt-0">
          <div>
            <h3 class="display text-2xl sm:text-3xl text-porcelain">{e(t['name'])}</h3>
            <p class="mono text-sm text-porcelain mt-2">{e(t['size'])}</p>
            <p class="text-body text-sm leading-relaxed mt-4">{e(t['summary'])}</p>
            <ul class="space-y-2 mt-5">{hl}</ul>
          </div>
          <div>{right}</div>
        </div>'''


def page(card, cards, units, head, header, footer):
    name, slug = card['name'], card['slug']
    data = units.get(card['unit']) or {}
    types = data.get('types', [])
    features = data.get('features', [])
    travel = data.get('travel', [])
    plan = data.get('plan')
    address = data.get('meta') or data.get('address') or card['loc']
    url = f'{SITE}/developments/{slug}/'
    cover = '/' + card['cover']
    lg = card['cover'].replace('-1100.jpg', '-2000.jpg') if card['cover'].endswith('-1100.jpg') else ''
    cw, ch = jpeg_size(ROOT / card['cover'])
    if lg and (ROOT / lg).exists():
        lw, lh = jpeg_size(ROOT / lg)
        img = (f'<img src="/{lg}" width="{lw}" height="{lh}" srcset="{cover} {cw}w, /{lg} {lw}w" '
               f'sizes="(min-width:1024px) 46vw, 92vw" alt="{e(card["alt"])}" fetchpriority="high" decoding="async" class="w-full h-auto block" />')
    else:
        img = (f'<img src="{cover}" width="{cw}" height="{ch}" alt="{e(card["alt"])}" fetchpriority="high" '
               f'decoding="async" class="w-full h-auto block" />')
    st = max(0, min(5, card['stage']))
    # Segment i is STAGES[i]; the stage label is STAGES[st], so st is the active segment.
    track = ''.join(f'<span class="tl-seg{" is-done" if st >= 5 or 0 < st > i else (" is-active" if 0 < st == i else "")}"></span>'
                    for i in range(5))
    enquire = f'/?interest={quote(FORM_OPTION.get(name, name))}#contact'
    wa = 'https://wa.me/2348078963703?text=' + quote(f"Hello GREY Development, I'd like to enquire about {name}.")
    brochure = '/' + card['brochure'] if card['brochure'] else ''
    title = f'{name} — {card["loc"]} | GREY Development Limited'
    desc = card['desc']
    n = [0]
    def num(label):
        n[0] += 1
        return f'{n[0]:02d} | {label}'

    glance = num('At a glance')   # numbered first: it is the first section on the page
    sections = ''
    if types:
        sections += f'''
    <section class="relative py-20 sm:py-28 bg-ink2 border-t border-line">
      <div class="mx-auto max-w-[1440px] px-5 sm:px-8 lg:px-20">
        <p class="reveal eyebrow text-[11px] mb-4">{num('The homes')}</p>
        <h2 class="reveal display text-3xl sm:text-5xl text-porcelain mb-12">Unit types <span class="gradword">and room schedule.</span></h2>
        {''.join(type_block(t) for t in types)}
        <p class="reveal text-muted text-xs mt-8 max-w-2xl">{e(data.get('price', 'Price on request'))}. Areas are from the brochure room schedule; final built-up area is slightly higher once wall thickness and circulation are included.</p>
      </div>
    </section>'''

    plans = media_figs(slug, 'plans', name)
    if plans:
        sections += f'''
    <section class="relative py-20 sm:py-28 bg-panel border-t border-line">
      <div class="mx-auto max-w-[1440px] px-5 sm:px-8 lg:px-20">
        <p class="reveal eyebrow text-[11px] mb-4">{num('Floor plans')}</p>
        <h2 class="reveal display text-3xl sm:text-5xl text-porcelain mb-12">Drawn before <span class="gradword">it is built.</span></h2>
        <div class="grid md:grid-cols-2 gap-x-8 gap-y-10">{plans}</div>
        <p class="reveal text-muted text-xs mt-8 max-w-2xl">Room areas as stated on the architect\u2019s drawings. Plans are for illustration and are not to scale. Select a plan to view it larger.</p>
      </div>
    </section>'''
    gallery = media_figs(slug, 'gallery', name)
    if gallery:
        sections += f'''
    <section class="on-void relative py-20 sm:py-28 bg-void border-t border-line">
      <div class="mx-auto max-w-[1440px] px-5 sm:px-8 lg:px-20">
        <p class="reveal eyebrow text-[11px] mb-4">{num('Gallery')}</p>
        <h2 class="reveal display text-3xl sm:text-5xl mb-12">Inside <span class="gradword">and out.</span></h2>
        <div class="grid md:grid-cols-2 gap-x-8 gap-y-10">{gallery}</div>
        <p class="reveal text-muted text-xs mt-8 max-w-2xl">All images are artist\u2019s impressions from the brochure.</p>
      </div>
    </section>'''

    cols = []
    if features:
        items = ''.join(f'<li class="flex gap-3 text-sm text-body py-2.5 border-b border-line"><span class="mt-[11px] w-3 h-px bg-gold shrink-0"></span>{e(x)}</li>' for x in features)
        cols.append(f'<div class="reveal"><h3 class="h3 mb-4">Estate features</h3><ul>{items}</ul></div>')
    if travel:
        rows = ''.join(f'<div class="uspec text-sm"><dt>{e(a)}</dt><dd>{e(b)}</dd></div>' for a, b in travel)
        cols.append(f'<div class="reveal" data-delay="1"><h3 class="h3 mb-4">Getting around</h3><dl>{rows}</dl>'
                    f'<p class="text-muted text-xs mt-4">Drive times by car, as given in the brochure.</p></div>')
    if plan and card['status'] != 'completed':
        rows = ''.join(f'<div class="uspec text-sm"><dt>{e(a)}</dt><dd>{e(b)}</dd></div>' for a, b in plan[1])
        cols.append(f'<div class="reveal" data-delay="2"><h3 class="h3 mb-4">{e(plan[0])}</h3><dl>{rows}</dl>'
                    f'<p class="text-muted text-xs mt-4">As published in the brochure. Terms are confirmed in writing at subscription.</p></div>')
    loc_map = media_figs(slug, 'map', name)
    if cols:
        sections += f'''
    <section class="relative py-20 sm:py-28 bg-ink border-t border-line">
      <div class="mx-auto max-w-[1440px] px-5 sm:px-8 lg:px-20">
        <p class="reveal eyebrow text-[11px] mb-4">{num('The estate')}</p>
        <h2 class="reveal display text-3xl sm:text-5xl text-porcelain mb-12">What comes <span class="gradword">with the address.</span></h2>
        <div class="grid md:grid-cols-2 lg:grid-cols-3 gap-x-12 gap-y-12">{''.join(cols)}</div>
        {f'<div class="max-w-4xl mt-14">{loc_map}</div>' if loc_map else ''}
      </div>
    </section>'''

    others = ''.join(
        f'<a href="/developments/{c["slug"]}/" class="group flex flex-col sm:flex-row sm:items-baseline sm:justify-between gap-1 sm:gap-6 py-5 border-b border-line t-std">'
        f'<span class="display text-xl sm:text-2xl text-porcelain group-hover:text-gold t-std">{e(c["name"])}</span>'
        f'<span class="mono text-[10px] uppercase tracking-[0.18em] text-muted sm:shrink-0">{e(c["loc"])} &middot; {e(STATUS[c["status"]])}</span></a>'
        for c in cards if c['slug'] != slug)

    brochure_btn = (f'<a href="{brochure}" target="_blank" rel="noopener" class="btn btn-invert-secondary inline-flex items-center gap-2 px-6 py-3 text-sm">Brochure (PDF) {ARROW}</a>'
                    if brochure else '')
    ld = json.dumps({
        '@context': 'https://schema.org',
        '@graph': [
            {'@type': 'WebPage', '@id': url, 'url': url, 'name': title, 'description': desc,
             'primaryImageOfPage': SITE + cover, 'isPartOf': {'@id': SITE + '/#org'}},
            {'@type': 'BreadcrumbList', 'itemListElement': [
                {'@type': 'ListItem', 'position': 1, 'name': 'Home', 'item': SITE + '/'},
                {'@type': 'ListItem', 'position': 2, 'name': 'Developments', 'item': SITE + '/#projects'},
                {'@type': 'ListItem', 'position': 3, 'name': name, 'item': url}]},
        ]}, ensure_ascii=False, indent=2)

    return f'''<!DOCTYPE html>
<html lang="en" class="scroll-smooth">
<head>
  <!-- GENERATED by build_pages.py from index.html - edit that, then run ./build.sh -->
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{e(title)}</title>
  <meta name="description" content="{e(desc)}" />
  <meta property="og:title" content="{e(name)} — {e(card['loc'])}" />
  <meta property="og:description" content="{e(desc)}" />
  <meta property="og:image" content="{SITE}{cover}" />
  <meta property="og:url" content="{url}" />
  <meta property="og:type" content="website" />
  <meta property="og:site_name" content="GREY Development Limited" />
  <meta name="twitter:card" content="summary_large_image" />
  <meta name="theme-color" content="#18191B" />
  <link rel="canonical" href="{url}" />
  <script type="application/ld+json">
{ld}
  </script>
{head}
</head>

<body class="bg-ink text-body">
  <a href="#main" class="sr-only focus:not-sr-only focus:fixed focus:z-[100] focus:top-4 focus:left-4 focus:bg-void focus:text-offwhite focus:px-4 focus:py-2 focus:rounded-full">Skip to content</a>

{header}

  <main id="main">
    <section class="on-void bg-void pt-28 sm:pt-36 pb-16 sm:pb-24">
      <div class="mx-auto max-w-[1440px] px-5 sm:px-8 lg:px-20">
        <nav aria-label="Breadcrumb" class="hero-in mono text-[10px] uppercase tracking-[0.18em] text-muted mb-10">
          <a href="/#projects" class="hover:text-gold t-micro">Developments</a> <span aria-hidden="true">/</span> <span class="text-offwhite">{e(name)}</span>
        </nav>
        <div class="grid lg:grid-cols-2 gap-10 lg:gap-16 items-end">
          <div>
            <span class="hero-in inline-block eyebrow text-[10px] px-3 py-1.5 rounded-full border border-gold/40 text-gold" style="animation-delay:.08s">{e(STATUS[card['status']])}</span>
            <h1 class="hero-in display display--hero text-offwhite mt-6" style="animation-delay:.16s">{e(name)}</h1>
            <p class="hero-in mono text-[11px] uppercase tracking-[0.18em] text-muted mt-5" style="animation-delay:.24s">{e(address)}</p>
            <p class="hero-in text-offwhite/80 mt-6 max-w-xl leading-relaxed" style="animation-delay:.32s">{e(desc)}</p>
            <div class="hero-in flex flex-wrap items-center gap-3 mt-9" style="animation-delay:.4s">
              <a href="{enquire}" class="btn btn-invert inline-flex items-center gap-2 px-6 py-3 text-sm">Enquire {ARROW}</a>
              <a href="{wa}" target="_blank" rel="noopener" class="btn btn-invert-secondary inline-flex items-center gap-2 px-6 py-3 text-sm">WhatsApp</a>
              {brochure_btn}
            </div>
          </div>
          <figure class="hero-in" style="animation-delay:.3s">
            <div class="gal">{img}</div>
            <figcaption class="mono text-[10px] uppercase tracking-[0.18em] text-muted mt-4">Artist&rsquo;s impression</figcaption>
          </figure>
        </div>
      </div>
    </section>

    <section class="relative py-20 sm:py-28 bg-ink">
      <div class="mx-auto max-w-[1440px] px-5 sm:px-8 lg:px-20">
        <p class="reveal eyebrow text-[11px] mb-4">{glance}</p>
        <dl class="reveal grid grid-cols-2 lg:grid-cols-4 gap-x-8 gap-y-10 border-t border-line pt-10" data-delay="1">
          <div><dt class="eyebrow text-[10px] mb-2">Status</dt><dd class="display text-xl text-porcelain">{e(STATUS[card['status']])}</dd></div>
          <div><dt class="eyebrow text-[10px] mb-2">Location</dt><dd class="display text-xl text-porcelain">{e(card['loc'])}</dd></div>
          <div><dt class="eyebrow text-[10px] mb-2">Delivery stage</dt><dd class="display text-xl text-porcelain">{e(stage_label(st))}</dd></div>
          <div><dt class="eyebrow text-[10px] mb-2">Target</dt><dd class="display text-xl text-porcelain" id="target" data-raw="{e(card['updated'])}" data-stage="{st}">{e(card['updated'].title() if st in (0, 5) else 'Schedule on request')}</dd></div>
        </dl>
        <div class="reveal max-w-xl mt-12" data-delay="2">
          <div class="flex items-center gap-1.5" role="img" aria-label="Delivery progress: {e(stage_label(st))}">{track}</div>
          <div class="hidden sm:flex justify-between mono text-[9px] uppercase tracking-[0.14em] text-muted mt-3" aria-hidden="true">{''.join(f'<span>{s}</span>' for s in STAGES)}</div>
        </div>
      </div>
    </section>
{sections}

    <section class="on-void bg-void py-20 sm:py-28 border-t border-line">
      <div class="mx-auto max-w-[1440px] px-5 sm:px-8 lg:px-20">
        <div class="grid lg:grid-cols-[minmax(0,24rem)_minmax(0,1fr)] gap-12 lg:gap-20">
          <div class="reveal">
            <p class="eyebrow text-[11px] mb-4">{num('Next step')}</p>
            <h2 class="display text-3xl sm:text-5xl">Ask about <span class="gradword">{e(name)}.</span></h2>
            <p class="text-body mt-5 leading-relaxed">Tell us what you are weighing. Our team responds within one business day.</p>
            <div class="flex flex-wrap gap-3 mt-8">
              <a href="{enquire}" class="btn btn-invert inline-flex items-center gap-2 px-6 py-3 text-sm">Start an enquiry {ARROW}</a>
              <a href="tel:+2348078963703" class="btn btn-invert-secondary inline-flex items-center gap-2 px-6 py-3 text-sm">Call 0807 896 3703</a>
            </div>
          </div>
          <div class="reveal" data-delay="1">
            <p class="eyebrow text-[10px] mb-2">Other developments</p>
            <div class="border-t border-line">{others}</div>
          </div>
        </div>
      </div>
    </section>
  </main>

{footer}

  <dialog id="lb" class="lb" aria-label="Image viewer">
    <button type="button" class="x" data-lb-close aria-label="Close viewer"><svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M5 5l14 14M19 5L5 19"/></svg></button>
    <button type="button" class="prev" data-lb-step="-1" aria-label="Previous image"><svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M19 12H5M11 6l-6 6 6 6"/></svg></button>
    <button type="button" class="next" data-lb-step="1" aria-label="Next image"><svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M5 12h14M13 6l6 6-6 6"/></svg></button>
    <figure><img id="lbImg" alt="" /><figcaption><span id="lbCap"></span><span class="n" id="lbN"></span></figcaption></figure>
  </dialog>

  <script>
    (() => {{
      const header = document.getElementById('siteHeader');
      const menuBtn = document.getElementById('menuBtn'), menu = document.getElementById('mobileMenu');
      const setMenu = (open) => {{
        menu.classList.toggle('hidden', !open);
        menuBtn.setAttribute('aria-expanded', String(open));
        menuBtn.setAttribute('aria-label', open ? 'Close menu' : 'Open menu');
      }};
      menuBtn.addEventListener('click', () => setMenu(menu.classList.contains('hidden')));
      document.addEventListener('keydown', (ev) => {{ if (ev.key === 'Escape') setMenu(false); }});

      // Delivery target: never show a date that has already passed (same rule as the home page)
      const MONTHS = ['JAN','FEB','MAR','APR','MAY','JUN','JUL','AUG','SEP','OCT','NOV','DEC'];
      const t = document.getElementById('target');
      const m = /^([A-Z]{{3}})\\s+(\\d{{4}})$/i.exec((t.dataset.raw || '').trim());
      if (m && +t.dataset.stage < 5) {{
        const now = new Date(), mi = MONTHS.indexOf(m[1].toUpperCase());
        const past = mi >= 0 && new Date(+m[2], mi, 1) < new Date(now.getFullYear(), now.getMonth(), 1);
        t.textContent = past ? 'Schedule on request' : m[1].charAt(0) + m[1].slice(1).toLowerCase() + ' ' + m[2];
      }}

      // Image viewer: plans, gallery and map open in a dialog with previous / next.
      const lb = document.getElementById('lb'), links = [...document.querySelectorAll('a[data-lb]')];
      if (lb && lb.showModal && links.length) {{
        const img = document.getElementById('lbImg'), cap = document.getElementById('lbCap'), cnt = document.getElementById('lbN');
        let at = 0;
        const go = (n) => {{
          at = (n + links.length) % links.length; const a = links[at];
          img.src = a.href; img.alt = a.querySelector('img').alt;
          cap.textContent = a.dataset.cap; cnt.textContent = (at + 1) + ' / ' + links.length;
        }};
        links.forEach((a, n) => a.addEventListener('click', (ev) => {{
          if (ev.metaKey || ev.ctrlKey || ev.shiftKey) return;   // let "open in new tab" through
          ev.preventDefault(); go(n); lb.showModal();
        }}));
        lb.querySelectorAll('[data-lb-step]').forEach(b => b.addEventListener('click', () => go(at + (+b.dataset.lbStep))));
        lb.querySelector('[data-lb-close]').addEventListener('click', () => lb.close());
        lb.addEventListener('click', (ev) => {{ if (ev.target === lb || ev.target.tagName === 'FIGURE') lb.close(); }});
        lb.addEventListener('keydown', (ev) => {{ if (ev.key === 'ArrowRight') go(at + 1); if (ev.key === 'ArrowLeft') go(at - 1); }});
        let x0 = null;
        lb.addEventListener('touchstart', (ev) => {{ x0 = ev.touches[0].clientX; }}, {{ passive: true }});
        lb.addEventListener('touchend', (ev) => {{
          if (x0 === null) return; const dx = ev.changedTouches[0].clientX - x0; x0 = null;
          if (Math.abs(dx) > 50) go(at + (dx < 0 ? 1 : -1));
        }});
        lb.addEventListener('close', () => {{ img.removeAttribute('src'); links[at].focus(); }});
      }}

      const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
      const els = document.querySelectorAll('.reveal');
      if (!reduce && 'IntersectionObserver' in window) {{
        const io = new IntersectionObserver((entries) => {{
          entries.forEach(en => {{ if (en.isIntersecting) {{ en.target.classList.add('is-visible'); io.unobserve(en.target); }} }});
        }}, {{ threshold: 0.12 }});
        els.forEach(el => io.observe(el));
      }} else {{
        els.forEach(el => el.classList.add('is-visible'));
      }}
    }})();
  </script>
</body>
</html>
'''


def main():
    src = (ROOT / 'index.html').read_text()
    cards, units = parse_cards(src), parse_units(src)

    icon = re.search(r'  <link rel="icon"[^\n]*\n', src).group(0)
    style = between(src, '  <style>', '</style>')
    assert 'url(assets' not in style
    css = re.search(r'<link rel="stylesheet" href="assets/tailwind\.css[^"]*" />', src).group(0)
    head = (icon + "  <script>document.documentElement.classList.add('js');</script>\n" + style + '\n  ' + rebase(css))

    header = rebase(between(src, '  <header id="siteHeader"', '</header>'))
    # No hero to sit over here, so the bar starts in its scrolled (glass) state.
    header = header.replace('class="fixed top-0 inset-x-0 z-50 t-std"', 'class="scrolled fixed top-0 inset-x-0 z-50 t-std"', 1)
    header = header.replace('href="/#home"', 'href="/"')
    footer = rebase(between(src, '  <footer class="on-void', '</footer>'))

    for c in cards:
        out = ROOT / 'developments' / c['slug'] / 'index.html'
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(page(c, cards, units, head, header, footer))
        print('wrote', out.relative_to(ROOT))

    urls = [(SITE + '/', '1.0')] + [(f'{SITE}/developments/{c["slug"]}/', '0.8') for c in cards]
    from datetime import date
    today = date.today().isoformat()
    (ROOT / 'sitemap.xml').write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' +
        ''.join(f'  <url>\n    <loc>{u}</loc>\n    <lastmod>{today}</lastmod>\n    <changefreq>monthly</changefreq>\n'
                f'    <priority>{p}</priority>\n  </url>\n' for u, p in urls) + '</urlset>\n')
    print('wrote sitemap.xml')


if __name__ == '__main__':
    if 'render' in sys.argv[1:]:
        render()
    sys.exit(main())
