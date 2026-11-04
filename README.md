# Index matrik

Co už bylo z matričních knih přečteno – strojově (PERO OCR) i očima – bez vazby na konkrétní rodokmen. Slouží k tomu,
aby se stejná stránka nemusela znovu stahovat, OCRkovat ani číst. Index je veřejný a společný: kdo něco
nového přečte, pošle to sem (viz [Přispějte](#přispějte)).

Kromě matrik sem patří i další knihy se jmény: pozemkové (gruntovní) knihy, soupisy poddaných, familiantské knihy. Mají
stejnou strukturu; druh knihy říká pole `druh` v `kniha.yaml` (`matrika`, `pozemková kniha`, `urbář`,
`soupis poddaných`, `sčítání lidu`, `policejní přihlášky`, `familianti`; chybí-li, jde o matriku). Zápisy přečtené dřív
při práci na rodokmenu jsou přenesené se `cetl` = „Claude (z rodokmenu …)“.

Skeny se neukládají (lze je kdykoli stáhnout z archivu). Plné exporty z PERO (PAGE XML s obrysy řádků) jsou mimo git.

Co v indexu je (knihy, rozsah OCR, počty přečtených zápisů): [PREHLED.md](PREHLED.md), generuje `python tools/prehled.py`.

Licence: nástroje MIT ([LICENSE](LICENSE)), data v `knihy/` CC BY 4.0 ([LICENSE-DATA.md](LICENSE-DATA.md)).

## Kdo četl

Sloupec `cetl` v `precteno.tsv` uvádí u jazykového modelu jeho identifikátor v hranatých závorkách, aby šlo zápisy
přečtené slabším modelem najít a přečíst znovu lepším. `agent` je pomocný agent, který četl skeny, `Claude` hlavní
model, který zápis ověřil nebo četl sám.

Starší řádky model neuvádějí. Podle záznamů sezení četly:

| `cetl` | model |
|---|---|
| `agent` do 2026-10-31 | `claude-opus-5-5` |
| `agent 2026-11-01` | `claude-opus-5-5` nebo `claude-sonnet-5-5` (ten den pracovali oba) |
| `agent` od 2026-11-02 | `claude-sonnet-5-5` |
| `Claude …` (i „z rodokmenu“) | `claude-opus-5-5`, jen 2026-10-05 `claude-sonnet-5-5` |

## Přispějte

Přečetli jste si matriku nebo jiný pramen – očima, přes PERO OCR nebo s Claudem? Pošlete to sem, ať to nemusí číst
nikdo další. Stačí pull request s novými řádky v `knihy/<archiv>/<kniha>/precteno.tsv` (Claude Code ho podle
[AGENTS.md](AGENTS.md) připraví sám), nebo formulář „Nové čtení“ v Issues. Pravidla, kontrola a licence:
[CONTRIBUTING.md](CONTRIBUTING.md). Než začnete číst celou knihu, založte Issue „Čtu knihu“.

## Struktura

```
knihy/<archiv>/<kniha>/
  kniha.yaml      popis knihy: archiv, název, farnost, roky, obsah (které snímky jsou N/O/Z), odkaz na portál,
                  jak se z čísla souboru dostat na snímek, a pro každé OCR: nástroj, dokument v PERO, model, datum
  stranky.tsv     zpracované stránky: snímek, soubor, rozměry obrázku, počet řádků
  ocr-pero.tsv    strojový text: snímek, soubor, strana (L/R), řádek, obdélník x/y/šířka/výška v pixelech obrázku,
                  jistota (0–1), text – nekontrolovaný, s chybami
  precteno.tsv    zápisy přečtené očima (formát níže)
knihy/testy/      pokusná OCR (výřezy)
tools/
  kontrola.py     kontrola dat (formát, povinná pole, lhůty pro žijící lidi); běží u každého pull requestu
  hledej.py       volné hledání slova ve všech knihách (precteno, OCR s opravami; Levenshtein na začátku slova)
  opravy.py       přidání opravy strojového čtení do opravy.tsv
  pero_import.py  převod exportu z PERO do knihy/…
  prehled.py      vygeneruje PREHLED.md
  pero/           balik.py (skeny do balíků ≤ 9,4 MB), pero.js (nahrávání a export ve stránce PERO) – viz PERO.md
  scan/           stahování skenů: pfl.py, pf64.py (Porta fontium), ebget.py (eBadatelna SOA Praha), da2.py,
                  dasearch.py (DigiArchiv SOA Třeboň), zget.py + rzip.py (VČA Zámrsk; vcakniha.py = celá kniha pro PERO),
                  zayt.py, books.py, bfilter.py (zayt.org), mza.py (Acta Publica, MZA Brno), zaopava.py (ZA Opava, cesty
                  ke snímkům zjistí tools/pero/zaopava.js v prohlížeči), cr.py (výřez skenu);
                  slusne.py = společný limit dotazů
```

Archivy: `portafontium` (SOA Plzeň), `soapraha` (eBadatelna, kniha = id matriky), `soatrebon`, `vca`, `zayt`, `nacr`,
`mza` (Acta Publica, kniha = id z adresy matrika/detail/<id>), `ahmp`, `familysearch` (kniha = číslo DGS),
`zaopava`, `konskripce` (policejní přihlášky NA), `cuzk` (indikační skici stabilního katastru, kniha = id rastru
z adresy ags.cuzk.gov.cz/archiv/openmap.html?typ=skicic&idrastru=<id>; čtou se v prohlížeči archivu map ČÚZK),
`ndk` (Národní digitální knihovna, noviny; kniha = titul a ročník, snímek = strana ročníku).

## Ohleduplnost k archivům

Digitální badatelny jsou veřejná služba pro všechny badatele, ne zdroj dat pro hromadné stahování. Když po nich začne
skeny tahat víc lidí s automatickými nástroji najednou, archiv přestane stíhat a odnesou to všichni, i ti, kdo listují
ručně. Na přelomu října a listopadu 2026 přestala Acta Publica (MZA Brno) odpovídat řadě badatelů a některé IP adresy
zablokovala.

- Stahujte jen knihy, které opravdu potřebujete, a jen jejich potřebnou část (rejstřík, roky, obec). Celou knihu do
  PERO teprve tehdy, když hledané jméno nejde najít jinak.
- Každé stahování jde přes `tools/scan/slusne.py`. Výchozí limit: stránky a hledání 1 dotaz za 2 s, obrázky 5 za 1 s.
  Přetížené archivy mají přísnější limit (`POMALE`, Acta Publica 1 snímek za 2 s). Po 429/503 je server půl hodiny
  zablokovaný pro všechny procesy (`python -I tools/scan/slusne.py stav`). Vlastní jednorázové skripty volají
  `slusne.urlopen()` / `slusne.get()`, ne přímo `urllib`, `requests` ani `curl`. Souběžné procesy limit nezrychlí, jen
  se o něj dělí.
- Když archiv odpovídá pomalu, píše o přetížení nebo vás zablokuje, dejte mu pauzu: `python -I tools/scan/slusne.py
  zablokuj <server> <hodin>`. Blokaci neobcházejte jinou sítí ani jinou IP adresou.
- Než knihu stáhnete, podívejte se do `knihy/`, jestli ji tu už někdo nepřečetl. Proto index existuje: jednou přečtená
  kniha se nemusí stahovat znovu.

## Hledání

    python tools/hledej.py plozar --maxd 2 [--kniha dnesice-01] [--skip '^(ploze|plota)'] [--kontext 1]

PERO komolí vzácná příjmení (Plocar → „Klozara“, „Plogar“), proto volné hledání; prázdný výsledek nedokazuje, že jméno
v knize není. Zásah se ověřuje na skenu (snímek a strana jsou ve výpisu).

## Přidání knihy

Celý postup (skeny podle archivu, nahrání do PERO, rozbor rozložení, volba modelu, export a import) je v
[PERO.md](PERO.md). Zkráceně: skeny do PERO (Porta fontium a Acta Publica přímo z prohlížeče, ostatní z disku),
„Handwritten layout“, OCR „Kurrent (German, Czech)“ pro kurent, „Czech Handwritten“ pro latinku, export, doplnit
`BOOKS` a `EXPORTS` v `tools/pero_import.py` a spustit `python tools/pero_import.py <export.zip>`.

## Vrstvy a opravy

Původní data se nepřepisují, opravy a výklady se přidávají zvlášť:

1. `ocr-pero.tsv` – strojový text, nemění se (při lepším OCR se vymění celý).
2. `opravy.tsv` – opravy strojového čtení: co je na skenu opravdu napsáno (PERO „Plohar“, napsáno „Ploczar“). Oprava je
   ukotvená obdélníkem řádku na skenu, ne jeho číslem, takže přežije nové OCR. Přidává se nástrojem:

       python tools/opravy.py <kniha> <snímek+strana> <řádek> "<jak četl PERO>" "<co je napsáno>" --kdo "agent 2026-10-21"

   Sloupce: snimek, soubor, strana, x, y, sirka, vyska (obdélník řádku), puvodne (prázdné = celý řádek), spravne, kdo,
   jistota.
3. `precteno.tsv` – celé zápisy přečtené očima, doslovně, i s chybami písaře.
4. Výklad (kdo osoba ve skutečnosti je, např. v zápisu „Františka Červená“, ve skutečnosti Barbora Jímalová) do indexu
   nepatří – index drží, co je napsáno; výklad je v rodokmenu (ve sloupci `odkaz` se na něj dá odkázat).

`tools/hledej.py` prohledává `precteno.tsv` (zásah označen „[očima]“) a strojový text s použitými opravami („[opraveno]“;
hledá se i v původním znění).

## precteno.tsv – zápisy přečtené očima

Každý zápis, který člověk nebo agent při práci přečetl, i když se netýká hledané rodiny. Sloupce oddělené tabulátorem,
první řádek hlavička:

| sloupec | obsah |
|---|---|
| snimek | číslo snímku na portálu a strana, např. `124R` |
| datum | datum události, jak je čitelné (`1756-01-14`, `1757-04`, `~1723`) |
| typ | `N` narození/křest, `O` sňatek, `Z` úmrtí/pohřeb, `P` převod gruntu v pozemkové knize (koupě, dědictví, přiženění, odhad), `S` řádek soupisu poddaných nebo sčítání lidu, `K` katastrální mapa (indikační skica: číslo domu, majitel), `J` jiné (ohlášky, atestát, rejstřík, familiant, prázdná strana) |
| obec | obec a číslo domu (`Jetenovice 7`); u pozemkové knihy i jméno gruntu (`Velké Hydčice 3, grunt Němcovský`) |
| osoby | hlavní osoby s rolí: `dítě: Ambrož; otec: Matěj Píhr; matka: Ludmila` (u O ženich, nevěsta a jejich rodiče; u P `prodávající: …; kupující: …; výměnkář: …`; u S `hospodář: …; manželka: …; děti: …`) |
| ostatni | kmotři, svědci, povolání, věk, příčina smrti – stručně; u P cena, splátky, výminek, svědci |
| jistota | `vysoká`, `střední`, `nízká`; nejisté čtení v textu značit `[?]` |
| cetl | kdo, kdy a jakým modelem: `agent 2026-11-04 [claude-sonnet-5-5]`, `Claude 2026-11-04 [claude-opus-5-5]`, u člověka jméno a datum; model v hranatých závorkách (viz [Kdo četl](#kdo-četl)) |
| odkaz | volitelně odkaz na zpracovaný záznam jinde (např. v rodokmenu) |
