"""Přidá řádek do knihy/<archiv>/<kniha>/vyklad.tsv: chyba písaře v zápisu, doložená jinými zápisy v indexu.

    python tools/vyklad.py <archiv>/<kniha> <snimek> <datum> <udaj> <napsano> <spravne>
        --doklad "<archiv>/<kniha>/<snimek> <datum> (popis)" [--doklad …] --kdo "<kdo a kdy>" [--jistota vysoká]

Vykládaný zápis i každý doklad musí být v precteno.tsv (snímek a datum přesně jako tam). Před zápisem proběhnou
stejné kontroly jako v tools/kontrola.py.
"""
import argparse
import csv
import sys

from kontrola import HLAVICKY, KNIHY, Hlaseni, kontrola_vykladu


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("kniha", help="<archiv>/<kniha>, např. portafontium/maly-bor-15")
    ap.add_argument("snimek")
    ap.add_argument("datum")
    ap.add_argument("udaj", help="který údaj zápisu je chybný, např. „věk zemřelého“, „jméno matky“")
    ap.add_argument("napsano", help="co je v zápisu napsáno")
    ap.add_argument("spravne", help="co je správně")
    ap.add_argument("--doklad", action="append", required=True)
    ap.add_argument("--kdo", required=True, help="např. „Jan Novák + claude-opus-5-5/xhigh 2026-11-05“")
    ap.add_argument("--jistota", default="vysoká")
    a = ap.parse_args()
    p = KNIHY / a.kniha / "vyklad.tsv"
    radek = [a.snimek, a.datum, a.udaj, a.napsano, a.spravne, "; ".join(a.doklad), a.kdo, a.jistota]
    h = Hlaseni()
    kontrola_vykladu(p, radek, "nový řádek", h)
    if h.chyby:
        print("\n".join(h.chyby))
        sys.exit(1)
    novy = not p.exists()
    with open(p, "a", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter="\t", lineterminator="\n")
        if novy:
            w.writerow(HLAVICKY["vyklad.tsv"])
        w.writerow(radek)
    print(f"přidáno do {p.relative_to(KNIHY.parent).as_posix()}")


if __name__ == "__main__":
    main()
