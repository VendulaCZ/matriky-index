"""Komentář k pull requestu z výpisu tools/kontrola.py (pro workflow kontrola-pr.yml).

    python tools/kontrola_komentar.py <výpis kontroly> <návratový kód kontroly> <commit> > komentar.md

Výpis obsahuje text z dat pull requestu, proto jde do <pre> escapovaný a @ a # dostanou neviditelnou mezeru, aby
komentář nikoho neoznačil ani neodkazoval na jiné issues.
"""
import html
import sys

ZNACKA = "<!-- kontrola-pr -->"
# Komentář na GitHubu má limit 65 536 znaků; celý výpis zůstává v logu běhu.
MAX_RADKU = 150
ZWSP = "​"


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    vypis, kod, commit = sys.argv[1], sys.argv[2], sys.argv[3]
    with open(vypis, encoding="utf-8", errors="replace") as f:
        radky = [r for r in f.read().splitlines() if r.strip()]
    souhrn = next((r for r in reversed(radky) if r.startswith("chyb: ")), None)
    hlaseni = [r for r in radky if r.startswith("CHYBA")] + [r for r in radky if not r.startswith(("CHYBA", "chyb: "))]
    out = [ZNACKA]
    if kod == "0":
        out.append(f"**Kontrola dat** (commit {commit[:7]}): bez chyb – {souhrn}.")
    elif souhrn:
        out += [f"**Kontrola dat** (commit {commit[:7]}): {souhrn}.", "",
                "Opravte prosím řádky níže a pošlete změny do téže větve, kontrola proběhne znovu sama. Formát sloupců "
                "je v README (precteno.tsv – zápisy přečtené očima)."]
    else:
        out.append(f"**Kontrola dat** (commit {commit[:7]}) nedoběhla, podrobnosti jsou v logu běhu.")
    if hlaseni:
        ukazka = hlaseni[:MAX_RADKU]
        nadpis = ("Výpis kontroly" if len(hlaseni) <= MAX_RADKU
                  else f"Výpis kontroly (prvních {MAX_RADKU} z {len(hlaseni)} řádků, celý je v logu běhu)")
        text = html.escape("\n".join(ukazka)).replace("@", "@" + ZWSP).replace("#", "#" + ZWSP)
        out += ["", f"<details{'' if kod == '0' else ' open'}><summary>{nadpis}</summary>", "", f"<pre>{text}</pre>",
                "</details>"]
    print("\n".join(out))


if __name__ == "__main__":
    main()
