"""Kontrola dat v knihy/: formát souborů, povinná pole a ochrana žijících lidí.

    python tools/kontrola.py                 # celý index
    python tools/kontrola.py --zmeny main    # jen knihy změněné proti větvi main a navíc zákaz mazání řádků

Chyby (ukončí s kódem 1) zastaví pull request, varování jen upozorňují. Spouští ji GitHub Action u každého pull requestu.
"""
import argparse
import csv
import datetime
import re
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
KNIHY = ROOT / "knihy"
HLAVICKY = {
    "precteno.tsv": ["snimek", "datum", "typ", "obec", "osoby", "ostatni", "jistota", "cetl", "odkaz"],
    "ocr-pero.tsv": ["snimek", "soubor", "strana", "radek", "x", "y", "sirka", "vyska", "jistota", "text"],
    "stranky.tsv": ["snimek", "soubor", "sirka_obrazku", "vyska_obrazku", "radku"],
    "opravy.tsv": ["snimek", "soubor", "strana", "x", "y", "sirka", "vyska", "puvodne", "spravne", "kdo", "jistota"],
}
TYPY = {"N", "O", "Z", "P", "S", "K", "J"}
JISTOTA = ("vysoká", "střední", "nízká")
# Jazykový model se v cetl píše jako id/effort (claude-sonnet-5-5/xhigh), aby šlo zápisy přečtené slabším modelem
# najít a přečíst znovu; samotné „Claude“ nebo „agent“ nestačí.
MODEL_EFFORT = re.compile(r"\b[a-z][a-z0-9.]*(?:-[a-z0-9.]+)+/[a-z]+\b")
JAZYKOVY_MODEL = re.compile(r"\b(claude|agent|opus|sonnet|haiku|gpt|chatgpt|gemini|llm|copilot)\b", re.I)
# Matriky narozených jsou veřejně přístupné po 100 letech, oddaných a zemřelých po 75 letech (zákon o matrikách
# 301/2000 Sb., § 5a); soupisy obyvatel držíme stejně jako narozené. Mladší zápisy mohou týkat žijících lidí.
LHUTA = {"N": 100, "S": 100, "O": 75, "Z": 75}
# Soubory, ve kterých se cizí řádky nesmí mazat ani měnit (ocr-pero.tsv se při lepším OCR vyměňuje celý).
NEPREPISOVAT = ("precteno.tsv", "opravy.tsv")


class Hlaseni:
    def __init__(self):
        self.chyby, self.varovani = [], []

    def chyba(self, kde, co):
        self.chyby.append(f"{kde}: {co}")

    def varuj(self, kde, co):
        self.varovani.append(f"{kde}: {co}")


def rel(p):
    return p.relative_to(ROOT).as_posix()


def kontrola_knihy(d, h, prisne):
    """d = knihy/<archiv>/<kniha>; prisne = kniha je v pull requestu, chybějící popis je chyba."""
    archiv, kniha = d.parent.name, d.name
    ky = d / "kniha.yaml"
    if not ky.exists():
        (h.chyba if prisne else h.varuj)(rel(d), "chybí kniha.yaml (archiv, kniha, nazev, url)")
    else:
        try:
            meta = yaml.safe_load(ky.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError as e:
            h.chyba(rel(ky), f"neplatný YAML: {e}")
            meta = {}
        if meta.get("archiv") not in (None, archiv):
            h.chyba(rel(ky), f"archiv „{meta.get('archiv')}“ nesouhlasí se složkou „{archiv}“")
        if meta.get("kniha") not in (None, kniha):
            h.chyba(rel(ky), f"kniha „{meta.get('kniha')}“ nesouhlasí se složkou „{kniha}“")
        for pole in ("nazev", "url"):
            if not meta.get(pole):
                (h.chyba if prisne else h.varuj)(rel(ky), f"chybí pole {pole}")
    for jmeno, hlavicka in HLAVICKY.items():
        p = d / jmeno
        if p.exists():
            kontrola_tsv(p, hlavicka, h)


def rok_udalosti(datum):
    roky = [int(r) for r in re.findall(r"(?<!\d)(1[0-9]{3}|20[0-9]{2})(?!\d)", datum)]
    return max(roky) if roky else None


def kontrola_tsv(p, hlavicka, h):
    with open(p, encoding="utf-8", newline="") as f:
        radky = list(csv.reader(f, delimiter="\t"))
    if not radky:
        h.chyba(rel(p), "prázdný soubor")
        return
    if radky[0] != hlavicka:
        h.chyba(rel(p), "hlavička musí být: " + "\t".join(hlavicka))
        return
    letos = datetime.date.today().year
    for i, r in enumerate(radky[1:], start=2):
        kde = f"{rel(p)}:{i}"
        if not any(r):
            continue
        # Prázdný poslední sloupec (odkaz) smí chybět.
        if len(r) not in (len(hlavicka), len(hlavicka) - 1):
            h.chyba(kde, f"{len(r)} sloupců místo {len(hlavicka)} (oddělovač je tabulátor)")
            continue
        if p.name != "precteno.tsv":
            continue
        snimek, datum, typ, _, osoby, _, jistota, cetl = r[:8]
        if not snimek.strip():
            h.chyba(kde, "chybí snímek")
        if typ not in TYPY:
            h.chyba(kde, f"typ „{typ}“ není z {', '.join(sorted(TYPY))}")
        if not cetl.strip():
            h.chyba(kde, "chybí cetl (kdo a kdy četl)")
        elif JAZYKOVY_MODEL.search(MODEL_EFFORT.sub("", cetl)):
            h.chyba(kde, f"cetl „{cetl}“: u jazykového modelu uveďte jeho id a effort, např. claude-sonnet-5-5/xhigh")
        if not osoby.strip():
            h.varuj(kde, "prázdné osoby")
        if jistota and not jistota.startswith(JISTOTA):
            h.varuj(kde, f"jistota „{jistota}“ nezačíná vysoká/střední/nízká")
        rok = rok_udalosti(datum)
        if rok is None:
            h.varuj(kde, f"datum „{datum}“ bez roku")
        elif typ in LHUTA and rok > letos - LHUTA[typ]:
            h.chyba(kde, f"zápis typu {typ} z roku {rok} je mladší než {LHUTA[typ]} let – může se týkat žijících "
                         f"lidí, do veřejného indexu nepatří")


def zmenene_knihy(zaklad):
    out = subprocess.run(["git", "diff", "--name-only", f"{zaklad}...HEAD", "--", "knihy"], cwd=ROOT,
                         capture_output=True, text=True, check=True).stdout.split()
    knihy = set()
    for f in out:
        casti = Path(f).parts
        if len(casti) >= 3:
            knihy.add(ROOT.joinpath(*casti[:3]))
    return knihy


def smazane_radky(zaklad, h):
    """Odebrané nebo přepsané řádky v precteno.tsv a opravy.tsv (změna se v diffu ukáže jako - a +)."""
    diff = subprocess.run(["git", "diff", "--unified=0", f"{zaklad}...HEAD", "--", "knihy"], cwd=ROOT,
                          capture_output=True, text=True, encoding="utf-8", check=True).stdout
    soubor = None
    for radek in diff.splitlines():
        if radek.startswith("--- "):
            continue
        if radek.startswith("+++ "):
            soubor = radek[6:] if radek.startswith("+++ b/") else None
            continue
        if soubor and Path(soubor).name in NEPREPISOVAT and radek.startswith("-"):
            h.chyba(soubor, f"odebraný nebo změněný řádek: {radek[1:80]}… – cizí řádky se nemění, oprava patří do "
                            f"opravy.tsv nebo jako nový řádek")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--zmeny", metavar="ZAKLAD", help="kontrolovat jen knihy změněné proti této větvi")
    a = ap.parse_args()
    h = Hlaseni()
    if a.zmeny:
        for d in sorted(zmenene_knihy(a.zmeny)):
            if d.exists():
                kontrola_knihy(d, h, prisne=True)
        smazane_radky(a.zmeny, h)
    else:
        for d in sorted(p for p in KNIHY.glob("*/*") if p.is_dir() and p.parent.name != "testy"):
            kontrola_knihy(d, h, prisne=False)
    for v in h.varovani:
        print("varování:", v)
    for c in h.chyby:
        print("CHYBA:", c)
    print(f"chyb: {len(h.chyby)}, varování: {len(h.varovani)}")
    sys.exit(1 if h.chyby else 0)


if __name__ == "__main__":
    main()
