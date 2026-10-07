#!/usr/bin/env python3
"""
Indholdsfortegnelse i Markdown, i Lune-stil: ## som fede grupper, ### som punkter
med afsnitsnummeret som kode-chip.

    python tools/md_toc.py FIL.md [FIL.md …]          → skriv/opdatér fortegnelsen
    python tools/md_toc.py --check FIL.md [FIL.md …]  → fejl, hvis den er forældet

Fortegnelsen står mellem <!-- toc --> og <!-- /toc -->. Mangler markørerne, indsættes
den efter dokumentets første afsnit (under # titlen). Ankrene følger GitHubs regler
(små bogstaver, tegnsætning væk, mellemrum → -, dubletter får -1, -2 …), så linkene
virker både på github.com og i GitHub Pages.

    **[3. Komponenter](#3-komponenter)**
    - `3.1` [Navbar](#31-navbar-svævende-pille)
    - [Uden nummer](#uden-nummer)
"""
from __future__ import annotations

import pathlib, re, sys

START, END = "<!-- toc -->", "<!-- /toc -->"
NUM = re.compile(r"^(\d+(?:\.\d+)*[a-z]?\.?)\s+(.*)$")


def slug(text: str, seen: dict[str, int]) -> str:
    s = re.sub(r"`|\*\*|__|\[([^\]]*)\]\([^)]*\)", lambda m: m.group(1) or "", text).strip().lower()
    s = re.sub(r"[^\w\- ]", "", s, flags=re.UNICODE).replace(" ", "-")
    n = seen.get(s, 0)
    seen[s] = n + 1
    return s if n == 0 else f"{s}-{n}"


def plain(text: str) -> str:
    """Overskriftens tekst uden links/fremhævning (koden bevares)."""
    return re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text).replace("**", "").strip()


def build(md: str) -> str:
    seen: dict[str, int] = {}
    out, fence = [], False
    for line in md.split("\n"):
        if line.lstrip().startswith("```"):
            fence = not fence
            continue
        if fence:
            continue
        m = re.match(r"^(#{1,3})\s+(.*?)\s*#*\s*$", line)
        if not m:
            continue
        level, text = len(m.group(1)), m.group(2)
        anchor = slug(text, seen)
        if level == 1:
            continue
        label = plain(text)
        if level == 2:
            out += ([""] if out else []) + [f"**[{label}](#{anchor})**", ""]
        else:
            n = NUM.match(label)
            out.append(f"- `{n.group(1).rstrip('.')}` [{n.group(2)}](#{anchor})" if n else f"- [{label}](#{anchor})")
    # En gruppe uden punkter slutter ikke med en tom linje foran den næste.
    text = re.sub(r"\n{3,}", "\n\n", "\n".join(out)).strip("\n")
    return START + "\n" + text + "\n" + END


def apply(md: str) -> str:
    toc = build(md)
    if START in md and END in md:
        a, b = md.index(START), md.index(END) + len(END)
        return md[:a] + toc + md[b:]
    # Efter titlen og første afsnit.
    lines = md.split("\n")
    i = next((k for k, l in enumerate(lines) if l.startswith("# ")), -1) + 1
    while i < len(lines) and not lines[i].strip():
        i += 1
    while i < len(lines) and lines[i].strip() and not lines[i].startswith("#"):
        i += 1
    return "\n".join(lines[:i] + ["", toc] + lines[i:])


def main(argv: list[str]) -> int:
    check = "--check" in argv
    files = [a for a in argv if a != "--check"]
    if not files:
        print(__doc__)
        return 2
    stale = 0
    for f in files:
        p = pathlib.Path(f)
        md = p.read_text(encoding="utf-8")
        new = apply(md)
        if new == md:
            continue
        if check:
            print(f"forældet indholdsfortegnelse: {f}")
            stale += 1
        else:
            p.write_text(new, encoding="utf-8")
            print(f"opdateret: {f}")
    return 1 if stale else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
