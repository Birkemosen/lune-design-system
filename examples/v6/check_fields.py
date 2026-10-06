#!/usr/bin/env python3
"""
Tjek V6-siden efter flytningen til Hjem / ark / System (DESIGN.md 15).

    python examples/v6/check_fields.py [dist/da/index.html]

1. Hvert felt og hver handling i conf_fields.txt (den gamle Konfiguration og
   hverdagsfelterne på det gamle Dashboard) findes i den nye markup.
2. Ingen grupperet liste har mere end 6 rækker; ingen fane, System-kategori
   eller underside har mere end 5 grupper.
3. Tekstfelter i grupperede lister har en bredde fra 15.6 (.w-*).
4. De gamle visninger og tilstande (v-dash-*, v-conf-*, m-dash, m-conf) er væk.
Afslutter med kode 1 ved fejl.
"""
import pathlib, re, sys
from html.parser import HTMLParser

ROOT = pathlib.Path(__file__).resolve().parent
MAX_ROWS, MAX_GROUPS = 6, 5


class Walk(HTMLParser):
    """Tæller rækker pr. .setting-list og grupper pr. fane/kategori/underside."""
    VOID = {"input", "br", "img", "meta", "link", "hr", "source", "use", "path", "circle", "rect", "line", "polyline", "polygon"}

    def __init__(self):
        super().__init__()
        self.stack = []          # (tag, classes, info)
        self.errors = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        cls = set((a.get("class") or "").split())
        parent = self.stack[-1] if self.stack else None
        # række i en liste: direkte barn af .setting-list eller .gated-body
        if parent and parent[1] & {"setting-list", "gated-body"} and (cls & {"setting"} or tag == "details"):
            lst = next(s for s in reversed(self.stack) if "setting-list" in s[1])
            lst[2]["rows"] += 1
        if "setting-group" in cls:
            host = next((s for s in reversed(self.stack) if s[1] & {"tab-panel", "sys-cat", "subpage-body"}), None)
            if host:
                host[2]["groups"] += 1
        if tag == "input" and "input" in cls and not any(c.startswith("w-") for c in cls):
            if any("setting-control" in s[1] for s in self.stack):
                self.errors.append(f'tekstfelt uden .w-* i grupperet liste: id="{a.get("id")}"')
        info = {"rows": 0, "groups": 0, "label": a.get("id") or a.get("data-cat") or a.get("data-tab") or ""}
        if tag not in self.VOID:
            self.stack.append((tag, cls, info))

    def handle_startendtag(self, tag, attrs):
        # <path …/> o.l.: tæl, men læg ikke på stakken (ellers popper endtag for meget).
        self.VOID = self.VOID | {tag}
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag):
        if tag in self.VOID or not any(t == tag for t, _, _ in self.stack):
            return
        while self.stack:
            t, cls, info = self.stack.pop()
            if "setting-list" in cls and info["rows"] > MAX_ROWS:
                self.errors.append(f"gruppe med {info['rows']} rækker (maks. {MAX_ROWS}) nær {self.where()}")
            if cls & {"tab-panel", "sys-cat", "subpage-body"} and info["groups"] > MAX_GROUPS:
                self.errors.append(f"{info['label'] or t} har {info['groups']} grupper (maks. {MAX_GROUPS})")
            if t == tag:
                break

    def where(self):
        for t, cls, info in reversed(self.stack):
            if cls & {"sheet", "sys-cat"}:
                return info["label"]
        return "?"


def main():
    page = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT.parent.parent / "dist" / "da" / "index.html"
    html = page.read_text(encoding="utf-8")
    want = [l.strip() for l in (ROOT / "conf_fields.txt").read_text(encoding="utf-8").splitlines() if l.strip() and not l.startswith("#")]
    errors = []

    names = set(re.findall(r'\bname="([^"]+)"', html))
    actions = set(re.findall(r'name="action" value="([^"]+)"', html))
    data_actions = set(re.findall(r'data-action="([^"]+)"', html))
    for w in want:
        kind, _, v = w.rpartition(":")
        ok = (v in actions) if kind == "action" else (v in data_actions) if kind == "data-action" else (w in names)
        if not ok:
            errors.append(f"mangler: {w}")

    for old in ('id="v-dash-', 'id="v-conf-', 'id="m-dash"', 'id="m-conf"'):
        if old in html:
            errors.append(f"gammel markup findes stadig: {old}")

    walk = Walk()
    walk.feed(html)
    errors += walk.errors

    for e in errors:
        print("FEJL ", e)
    print(f"{page}: {len(want)} felter/handlinger tjekket, {len(errors)} fejl")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
