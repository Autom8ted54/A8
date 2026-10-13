"""Build the design-refresh preview variants from site/index.html (content stays identical).

Run: python3 design-varianten/build.py  -> design-varianten/variant-{a,b,c}.html
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = (ROOT / "site" / "index.html").read_text(encoding="utf-8")
INTER = '<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">'

VARIANTS = {
    "a": {
        "fonts": "family=Literata:ital,opsz,wght@0,7..72,400;0,7..72,600;0,7..72,700;1,7..72,400",
        "hero": '''
            <div class="kr-stamp" aria-hidden="true">
                <svg viewBox="0 0 200 200"><defs><path id="kr-c" d="M100,100 m-70,0 a70,70 0 1,1 140,0 a70,70 0 1,1 -140,0"/></defs>
                <circle cx="100" cy="100" r="92" fill="none" stroke="currentColor" stroke-width="3"/>
                <circle cx="100" cy="100" r="52" fill="none" stroke="currentColor" stroke-width="2"/>
                <text font-size="15" letter-spacing="2.4" fill="currentColor"><textPath href="#kr-c">KANSENRADAR · ELKE MAANDAG · VLAANDEREN ·</textPath></text>
                <text x="100" y="102" text-anchor="middle" font-size="26" font-weight="700" fill="currentColor">07:00</text>
                </svg>
            </div>''',
    },
    "b": {
        "fonts": "family=Bricolage+Grotesque:opsz,wght@12..96,500;12..96,700;12..96,800&family=Instrument+Sans:wght@400;500;600",
        "hero": '''
            <div class="kr-radar" aria-hidden="true">
                <div class="kr-rings"></div>
                <div class="kr-sweep"></div>
                <span class="kr-blip" style="--x:68%;--y:30%;--d:0.9s">Stad Gent</span>
                <span class="kr-blip" style="--x:28%;--y:62%;--d:2.4s">VDAB</span>
                <span class="kr-blip" style="--x:74%;--y:70%;--d:3.6s">Provincie Limburg</span>
                <span class="kr-blip" style="--x:38%;--y:24%;--d:5.1s">Stad Brugge</span>
            </div>''',
    },
    "c": {
        "fonts": "family=Young+Serif&family=Figtree:wght@400;500;600;700",
        "hero": '''
            <div class="kr-sky" aria-hidden="true">
                <span class="kr-cloud kr-cloud--1"></span><span class="kr-cloud kr-cloud--2"></span>
                <span class="kr-cloud kr-cloud--3"></span><span class="kr-sun"></span>
            </div>''',
        "after_h1": '''
                <div class="kr-forecast" aria-hidden="true">
                    <div class="kr-day kr-day--on"><b>ma</b><span class="kr-ico kr-ico--sun"></span><em>07:00</em></div>
                    <div class="kr-day"><b>di</b><span class="kr-ico"></span><em>&nbsp;</em></div>
                    <div class="kr-day"><b>wo</b><span class="kr-ico"></span><em>&nbsp;</em></div>
                    <div class="kr-day"><b>do</b><span class="kr-ico"></span><em>&nbsp;</em></div>
                    <div class="kr-day"><b>vr</b><span class="kr-ico"></span><em>&nbsp;</em></div>
                </div>''',
    },
}

for key, v in VARIANTS.items():
    html = SRC.replace(INTER, f'<link href="https://fonts.googleapis.com/css2?{v["fonts"]}&display=swap" rel="stylesheet">')
    html = html.replace('href="css/style.css"', f'href="../site/css/style.css">\n    <link rel="stylesheet" href="variant-{key}.css"')
    html = html.replace('href="assets/', 'href="../site/assets/').replace('src="js/', 'src="../site/js/')
    html = html.replace("<body>", f'<body class="variant-{key}">', 1)
    html = html.replace('<section class="section-problem">\n            <div class="container">',
                        '<section class="section-problem">' + v["hero"] + '\n            <div class="container">', 1)
    if "after_h1" in v:
        html = html.replace("</h1>", "</h1>" + v["after_h1"], 1)
    (ROOT / "design-varianten" / f"variant-{key}.html").write_text(html, encoding="utf-8")
    print("built", key)
