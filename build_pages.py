#!/usr/bin/env python3
"""Generate one page per development at developments/<slug>/index.html.

index.html stays the single source of truth: the cards in #projectGrid supply
name, location, status, stage, target, cover and brochure; UNIT_DATA supplies
the unit types and room schedules; the <style> block, header and footer are
lifted from it verbatim so the pages cannot drift from the home page.

BROCHURE below holds facts read from the brochure PDFs for developments that
have no UNIT_DATA entry. Each value carries the brochure page it came from.
Nothing here is estimated: where a brochure is silent, the page is too.

Run ./build.sh rather than this file directly - the Tailwind stylesheet has to
be rebuilt afterwards, because it only contains classes it finds in the HTML.
"""
import html, json, re, subprocess, sys
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

BROCHURE = {
    "Amrah's Villas": {
        'features': ['Standby generator', 'CCTV & security', 'Central gas system', 'Home automation',
                     'Intercom', 'Fibre-optic internet', 'Central power', 'Central water'],      # p.7
        'travel': [('Maitama District', '3 min'), ('Central Business District', '5 min')],      # p.6
        'plan': ('12-month payment plan',                                                       # p.16
                 [('Upon subscription', '40%'), ('After 6 months', '30%'), ('After 9 months', '30%')]),
        'types': [{
            'name': '4-Bed Semi-Detached Duplex', 'size': '4 bedrooms, all en-suite',           # p.9
            'summary': 'A semi-detached duplex with every bedroom en-suite.',
            'highlights': ['2 master suites with walk-in closets', '2 further en-suite bedrooms',
                           'Living room, ante-room & kitchen', 'Servant’s quarters & double carport'],
            'floors': [                                                                         # pp.10-12
                {'name': 'Ground Floor', 'note': 'Approx. 82 m²', 'rooms': [
                    ['Living Room', '44 m²'], ['Kitchen', '17 m²'], ['Ante-room', '11 m²'],
                    ['BQ', '8 m²'], ['Store', '2 m²']]},
                {'name': 'First Floor', 'note': 'Approx. 112 m²', 'rooms': [
                    ['Master Bedroom, en-suite', '34 m²'], ['Madam’s Bedroom, en-suite', '22 m²'],
                    ['Walk-in Closet', '19 m²'], ['Master Balcony', '16 m²'],
                    ['Bath / WC (master)', '10 m²'], ['Bath / WC', '6 m²'], ['Balcony', '5 m²']]},
                {'name': 'Pent Floor', 'note': 'Approx. 112 m²', 'rooms': [
                    ['Master Bedroom, en-suite', '34 m²'], ['Madam’s Bedroom, en-suite', '22 m²'],
                    ['Walk-in Closet', '19 m²'], ['Master Balcony', '16 m²'],
                    ['Bath / WC (master)', '10 m²'], ['Bath / WC', '6 m²'], ['Balcony', '5 m²']]},
            ]}],
    },
    'Eden I': {
        'features': ['Standby generator', 'CCTV & security', 'Central gas system', 'Home automation',
                     'Intercom', 'Fibre-optic internet', 'Landscaped greens', 'Fitness area'],   # p.6
        'travel': [('Minister’s Hill', '3 min'), ('Maitama District', '5 min')],            # p.5
        'types': [{
            'name': '4-Bed Townhome', 'size': '360 m²',                                     # p.8
            'summary': 'A four-bedroom townhome over three floors, with every bedroom en-suite.',
            'highlights': ['4 bedrooms, all en-suite', '2 living rooms & a mini lounge',
                           'Master’s suite with walk-in closet', 'Servant’s quarters & double carport'],
            'floors': [                                                                         # pp.9-11
                {'name': 'Ground Floor', 'note': 'Approx. 80 m²', 'rooms': [
                    ['Living Room', '47 m²'], ['Kitchen', '12 m²'], ['BQ', '8 m²'],
                    ['Courtyard', '6 m²'], ['Visitors’ Toilet', '3 m²'],
                    ['Store', '2 m²'], ['Bath / WC', '2 m²']]},
                {'name': 'First Floor', 'note': 'Approx. 89 m²', 'rooms': [
                    ['Family Living Room', '24 m²'], ['Mini Lounge', '24 m²'],
                    ['Master Bedroom, en-suite', '20 m²'], ['Bedroom, en-suite', '19 m²'],
                    ['Bath / WC (×2)', '10 m²'], ['Courtyard', '6 m²'], ['Balcony', '6 m²']]},
                {'name': 'Second Floor', 'note': 'Approx. 108 m²', 'rooms': [
                    ['Master’s Suite', '37 m²'], ['Bedroom, en-suite', '19 m²'],
                    ['Stairhall', '14 m²'], ['Bath / WC (×2)', '14 m²'],
                    ['Walk-in Closet', '11 m²'], ['Courtyard', '6 m²'],
                    ['Balcony', '6 m²'], ['Safe Room', '1 m²']]},
            ]}],
    },
    'Grey Oasis': {
        'address': 'Gobir Road, Unguwan Rimi GRA, Kaduna',                                       # p.3
        'features': ['Gated estate', 'Secure environment', 'Landscaped greens', 'Ample parking'],  # pp.2, 4
        'travel': [('Kaduna Polo Club', '8 min · 3.1 km'), ('Murtala Square', '10 min · 5.3 km'),
                   ('Ahmadu Bello Way', '6 min · 6.5 km'), ('Train station', '12 min · 7.6 km'),
                   ('Kaduna Airport', '20 min · 23.8 km')],                                 # p.3
        'plan': ('Staged payment plan',                                                          # p.13
                 [('Upon subscription', '50%'), ('After 6 months', '20%'),
                  ('After 12 months', '20%'), ('After 18 months', '10%')]),
        'types': [],
    },
}

e = html.escape
ARROW = ('<svg class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
         'stroke-linecap="square" aria-hidden="true"><path d="M5 12h14M13 6l6 6-6 6"/></svg>')


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
            note = f.get('note') or ('Sheet ' + f['sheet'] if f.get('sheet') else '')
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
    data = units.get(card['unit']) or BROCHURE.get(name) or {}
    types = data.get('types', [])
    features = data.get('features', [])
    travel = data.get('travel', [])
    plan = data.get('plan')
    address = data.get('meta') or data.get('address') or card['loc']
    url = f'{SITE}/developments/{slug}/'
    cover = '/' + card['cover']
    lg = card['cover'].replace('.jpg', '-lg.jpg')
    if (ROOT / lg).exists():
        img = (f'<img src="/{lg}" width="1400" height="989" srcset="{cover} 1000w, /{lg} 1400w" '
               f'sizes="(min-width:1024px) 46vw, 92vw" alt="{e(card["alt"])}" fetchpriority="high" decoding="async" class="w-full h-auto block" />')
    else:
        img = (f'<img src="{cover}" width="1000" height="707" alt="{e(card["alt"])}" fetchpriority="high" '
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
    if cols:
        sections += f'''
    <section class="relative py-20 sm:py-28 bg-panel border-t border-line">
      <div class="mx-auto max-w-[1440px] px-5 sm:px-8 lg:px-20">
        <p class="reveal eyebrow text-[11px] mb-4">{num('The estate')}</p>
        <h2 class="reveal display text-3xl sm:text-5xl text-porcelain mb-12">What comes <span class="gradword">with the address.</span></h2>
        <div class="grid md:grid-cols-2 lg:grid-cols-3 gap-x-12 gap-y-12">{''.join(cols)}</div>
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
    sys.exit(main())
