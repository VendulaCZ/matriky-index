"""Converts a PERO OCR export into the index layout: knihy/<archiv>/<kniha>/ocr-pero.tsv, stranky.tsv and kniha.yaml.

    python tools/pero_import.py <export.zip> [--only BOOK]

The export is either PERO's own ZIP (`/document/download_document_pages/<id>`: PAGE XML + TXT per page) or a
`*.pagexml.zip` bundle assembled in the browser ("### PAGE <id>" followed by the page's PAGE XML). Only the text of
each line, its bounding box and confidence are kept; polygons, baselines and PERO's internal ids are dropped.
Book metadata comes from BOOKS below; a book is written only when its pages are found in the export.
"""
import argparse
import csv
import json
import re
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree

REPO = Path(__file__).resolve().parent.parent
PF = "https://www.portafontium.eu/register/soap-pn/"

# prefix: the part of the image file name before "_<number>"; delitel: file number // delitel = snímek on the portal.
BOOKS = {
    "dnesice-01": dict(archiv="portafontium", nazev="Dnešice 01", farnost="Dnešice", roky="1685–1735",
                       obsah="N 1685–1735 (snímky 3–151), O 1685–1735 (152–192), Z 1685–1735 (193–247, neOCRováno)",
                       url=PF + "dnesice-01", prefix="dnesice-01"),
    "dnesice-02": dict(archiv="portafontium", nazev="Dnešice 02", farnost="Dnešice", roky="1735–1770",
                       obsah="OCR jen snímky 55–75 (N 1746–1752) a 162–173 (O 1735–1744) – test přesnosti",
                       url=PF + "dnesice-02", prefix="dnesice-02"),
    "dolni-lukavice-01": dict(archiv="portafontium", nazev="Dolní Lukavice 01", farnost="Dolní Lukavice", roky="1682–1765",
                              obsah="N 1682–1765 (snímky 3–370); soubor = snímek×10+1 (354–358: +2)",
                              url=PF + "dolni-lukavice-01", prefix="dolni-lukavice-01"),
    "velky-bor-01": dict(archiv="portafontium", nazev="Velký Bor 01", farnost="Velký Bor", roky="1707–1754",
                         obsah="N 1707–1753 (snímky 2–180), O 1708–1754 (181–228); snímek 135 na serveru prázdný",
                         url=PF + "velky-bor-01", prefix="velky-bor-01"),
    "velky-bor-02": dict(archiv="portafontium", nazev="Velký Bor 02", farnost="Velký Bor", roky="1746–1771",
                         obsah="N 1746–1771 (snímky 4–163); snímek 134 na serveru prázdný",
                         url=PF + "velky-bor-02", prefix="velky-bor-02"),
    "velky-bor-08": dict(archiv="portafontium", nazev="Velký Bor 08", farnost="Velký Bor", roky="1746–1771",
                         obsah="O 1746–1771 (snímky 2–67), řazeno podle obce nevěsty", url=PF + "velky-bor-08",
                         prefix="velky-bor-08"),
    "velky-bor-11": dict(archiv="portafontium", nazev="Velký Bor 11", farnost="Velký Bor", roky="1746–1771",
                         obsah="Z 1746–1771 (snímky 3–89)", url=PF + "velky-bor-11", prefix="velky-bor-11"),
    "maly-bor-05": dict(archiv="portafontium", nazev="Malý Bor 05", farnost="Malý Bor", roky="1745–1763",
                        obsah="N 1745–1763 (snímky 3–99), O (100–141), Z (142–176); navíc soubor 1205-o",
                        url=PF + "maly-bor-05", prefix="maly-bor-05"),
    "maly-bor-03": dict(archiv="portafontium", nazev="Malý Bor 03", farnost="Malý Bor", roky="1704–1726",
                        obsah="N 1704–1726 (snímky 3–69), O (70–85), Z (86–100)", url=PF + "maly-bor-03",
                        prefix="maly-bor-03"),
    "horazdovice-05": dict(archiv="portafontium", nazev="Horažďovice 05", farnost="Horažďovice", roky="1699–1747",
                           obsah="OCR jen N 1699–1747 (snímky 4–184 a 254–267); Z (185–252) a O (269–322) bez OCR",
                           url=PF + "horazdovice-05", prefix="horazdovice-05"),
    "horazdovice-05-zo": dict(archiv="portafontium", nazev="Horažďovice 05 – zemřelí a oddaní", farnost="Horažďovice",
                              roky="1699–1747", obsah="Z (snímky 185–252) a O (269–322); oddíl N je v horazdovice-05",
                              url=PF + "horazdovice-05", prefix="horazdovice-05"),
    "kasejovice-03": dict(archiv="portafontium", nazev="Kasejovice 03",
                          farnost="Kasejovice (Kasejovice, Hradiště, Řesanice, Předmíř, Mětly, Újezd, Chlumek …)",
                          roky="1667–1689",
                          obsah="N 1667–1676 (snímky 3–44), O 1667–1676 (45–57), N 1677–1689 (58–108), O 1677–1689 (109–126), "
                                "Z 1677–1689 (128–142); OCR jen N 1667–1676 a Z 1677–1689",
                          url=PF + "kasejovice-03", prefix="kasejovice-03",
                          poznamka="zápisy přečtené očima: N 0030–0440 (1667–1676) a 0580–1080 (1677–1689), O 0450–0570 a 1090–1260 "
                                   "(1667–1689); "
                                   "příjmení většinou čtena ze snímků 1600 px, proto nízká jistota"),
    "kasejovice-05": dict(archiv="portafontium", nazev="Kasejovice 05", farnost="Kasejovice", roky="1690–1747",
                          obsah="O 1690–1747 (snímky 3–210); snímek 3 = str. 54–55 (1704–1705)",
                          url=PF + "kasejovice-05", prefix="kasejovice-05"),
    "kasejovice-07": dict(archiv="portafontium", nazev="Kasejovice 07", farnost="Kasejovice", roky="1690–1744",
                          obsah="Z 1690–1744 (snímky 3–219); snímek 3 = str. 52–53",
                          url=PF + "kasejovice-07", prefix="kasejovice-07"),
    "horazdovice-05-kurrent": dict(archiv="portafontium", nazev="Horažďovice 05 (druhé OCR modelem Kurrent)",
                                   farnost="Horažďovice", roky="1737–1747",
                                   obsah="N 1737–1747 (snímky 133–184 a 254–267) znovu modelem Kurrent – česká kurzíva; "
                                         "celá kniha modelem Czech Handwritten je v horazdovice-05",
                                   url=PF + "horazdovice-05", prefix="horazdovice-05"),
    "vs-horazdovice-k1563": dict(archiv="portafontium", nazev="Vs Horažďovice K 1563 – kniha purkrechtní rychty Pačejovické",
                                 farnost="Malý Bor, Kvasňovice (Olšany, Pačejov, Týřovice, Velešice)", roky="1726–1817",
                                 obsah="pozemková kniha; OCR celé knihy kromě souboru 3740; soubor vs-horazdovice-k1563_NNNN, "
                                       "snímek = NNNN/10", url="https://www.portafontium.eu/amtsbuch/soap-pn/vs-horazdovice/k1563",
                                 prefix="vs-horazdovice-k1563", druh="pozemková kniha"),
    "maly-bor-06": dict(archiv="portafontium", nazev="Malý Bor 06", farnost="Malý Bor", roky="1764–1784",
                        obsah="N (snímky 5–95), O od 1764 (96–129), Z (130–187); latinsky", url=PF + "maly-bor-06",
                        prefix="maly-bor-06"),
    "maly-bor-04": dict(archiv="portafontium", nazev="Malý Bor 04", farnost="Malý Bor", roky="1727–1744",
                        obsah="N 1727–1744 (snímky 3–78, mezi nimi listy x; na snímku 72 i oddaní 1728), O (79–93, od 9/1735), Z (94–118)",
                        url=PF + "maly-bor-04", prefix="maly-bor-04"),
    "kvasnovice-01": dict(archiv="portafontium", nazev="Kvasňovice 01", farnost="Kvasňovice", roky="1738–1765",
                          obsah="N 1738–1765 (snímky 3–62), Z (62–105), O 1738–1765 (106–127); česky, od asi 1763 latinsky",
                          url=PF + "kvasnovice-01", prefix="kvasnovice-01"),
    "kvasnovice-05": dict(archiv="portafontium", nazev="Kvasňovice 05", farnost="Kvasňovice", roky="1784–",
                          obsah="Z od 1784 (snímky 3–128, 37 a 52 chybí); česky, tabulky", url=PF + "kvasnovice-05",
                          prefix="kvasnovice-05"),
    "kvasnovice-02": dict(archiv="portafontium", nazev="Kvasňovice 02", farnost="Kvasňovice", roky="1766–1793",
                          obsah="N 1766–1793 (snímky 3–138, 240–244), Z (139–203, snímek 177 chybí), O (204–239); latinsky",
                          url=PF + "kvasnovice-02", prefix="kvasnovice-02"),
    "6568": dict(archiv="soapraha", nazev="Kněževes 03 (eBadatelna 6568)", farnost="Kněževes", roky="1735–1810",
                 obsah="OCR snímky 84–125 (O 1761–1810); soubor = číslo snímku v eBadatelně",
                 url="https://ebadatelna.soapraha.cz/d/6568/", prefix="", delitel=1),
    "o-235": dict(archiv="zayt", nazev="Hrochův Týnec, židovská kontrolní matrika O (NA HBMa inv. 235)",
                  farnost="Hrochův Týnec", roky="1839–1889",
                  obsah="OCR snímky 24–38 (O asi 1846–1856); soubor = snímek; zápisy jsou psané svisle, OCR je z obrázků "
                        "otočených o 90° po směru hodinových ručiček (soubor -r)",
                  url="https://zayt.org/collections/jewish-control-registers-1780-1911/o-235", prefix="o235", delitel=1),
    "o-2434": dict(archiv="zayt", nazev="Zájezdec, židovská matrika O (NA HBMa inv. 2434)", farnost="Zájezdec",
                   roky="1839, 1841–1868",
                   obsah="OCR snímky 22–34; soubor = snímek; zápisy jsou psané svisle, OCR je z obrázků otočených o 90° "
                         "po směru hodinových ručiček (soubor -r)",
                   url="https://zayt.org/collections/jewish-registers-1784-1949/o-2434", prefix="o2434", delitel=1),
    "noz-372": dict(archiv="zayt", nazev="Kostelec nad Černými lesy, židovská kontrolní matrika NOZ (NA HBMa inv. 372)",
                    farnost="Kostelec nad Černými lesy", roky="1840–1862",
                    obsah="N 1840–1862 fol. 1–10 (fol. 9 = sn. 11, fol. 10 = sn. 12), O 1840–1862 fol. 17–19 = sn. 13–15 "
                          "(posty 1–19), Z 1840–1862 fol. 24–30 = sn. 16–22, společný rejstřík N+O+Z (folio/post) pag. "
                          "40–46 = sn. 23–29, sn. 30 závěrečná doložka; OCR snímky 15–31; soubor = snímek",
                    url="https://zayt.org/collections/jewish-control-registers-1780-1911/noz-372", prefix="noz372",
                    delitel=1),
    "o-406": dict(archiv="zayt", nazev="Heřmanův Městec, židovská matrika O (NA inv. 406), duplikát 1839–1850",
                  farnost="Heřmanův Městec", roky="1839–1850",
                  obsah="OCR snímky 4–34 (O 1839–1850; snímek 11 se nestáhl); soubor = snímek; zápisy svisle, OCR z obrázků "
                        "oříznutých na knihu a otočených o 90° po směru hodinových ručiček (soubor -r)",
                  url="https://zayt.org/collections/jewish-registers-1784-1949/o-406", prefix="o406", delitel=1),
    "sign-26-1": dict(archiv="vca", nazev="Dobruška N 1799–1806 a Z 1799–1806, sign. 26-1 (kód RRGJJKAQ)",
                      farnost="Dobruška (Pulice, Pohoří …)", roky="1799–1806",
                      obsah="fol. = snímek + 2 (sn. 45 = fol. 47, XI–XII 1799); OCR snímky 115–189 (úmrtní oddíl, bez rejstříku); "
                            "soubor = snímek; šedotónové JPEG 4078 px",
                      url="https://storage.vychodoceskearchivy.cz/matriky/R/CZ_215000010_00190_RRGJJKAQ_sign-26-1.zip", prefix="dob261", delitel=1),
    "sign-26-12": dict(archiv="vca", nazev="Dobruška Z vesnice 1806–1843, sign. 26-12 (kód 3CF3NFID)",
                       farnost="Dobruška (vesnice)", roky="1806–1843",
                       obsah="po obcích; OCR snímky 74–87 (oddíl Pulice sn. 76–85, pag. 198–217); soubor = snímek; "
                             "šedotónové JPEG 4078 px",
                       url="https://storage.vychodoceskearchivy.cz/matriky/3/CZ_215000010_00190_3CF3NFID_sign-26-12.zip", prefix="dob2612", delitel=1),
    "sign-1309": dict(archiv="vca", nazev="Litomyšl N 1850–1857, sign. 1309 (kód WRH6GG3Q)",
                      farnost="Litomyšl", roky="10/1850–1857",
                      obsah="N Litomyšl město a předměstí (Dolní a Horní předměstí, Lány, Zahájí, Záhradí); snímky 1–395; "
                            "soubor = snímek; OCR ze šedotónových JPEG 2400 px",
                      url="https://aron.vychodoceskearchivy.cz/apu/9340aa8e-bfe5-4c80-af51-9adf97017290", prefix="lit1309",
                      delitel=1),
    "sign-7492": dict(archiv="vca", nazev="Litomyšl, index Z 1864–1906, sign. 7492 (kód LRIQXP2E)", farnost="Litomyšl",
                      roky="1864–1906",
                      obsah="rejstřík zemřelých celé farnosti (město, předměstí i vesnice); snímky 1–229; soubor = snímek; "
                            "OCR ze šedotónových JPEG 2400 px",
                      url="https://aron.vychodoceskearchivy.cz/apu/06a51ee1-4891-4871-b054-cd9370536c0b", prefix="lit7492",
                      delitel=1),
    "o-2741": dict(archiv="zayt", nazev="Praha-Karlín, židovská matrika O 1848–1856 (NA HBMa inv. 2741)",
                   farnost="Karlín (krajský rabín Kouřimska; snoubenci z celého kraje)", roky="1848–1856",
                   obsah="„Trauungs-Matrik“, tištěný formulář přes dvojstranu, 4 posty na stranu (sn. 20 = pag. 18, 1854); "
                         "OCR snímky 3–35; soubor = snímek, obrázek oříznutý na knihu, šedotónový",
                   url="https://zayt.org/collections/jewish-registers-1784-1949/o-2741", prefix="o2741", delitel=1),
    "o-2745": dict(archiv="zayt", nazev="Praha-Libeň, židovská matrika O 1833–1849 (NA HBMa inv. 2745)",
                   farnost="Libeň (snoubenci i z venkova – Přistoupim, Poříčany, Cerhenice aj.)", roky="1833–1849",
                   obsah="ručně linkovaná tabulka přes dvojstranu (sn. 10 = pag. 12–13, rok 1837); OCR snímky 4–17; soubor = "
                         "snímek, obrázek oříznutý na knihu, šedotónový",
                   url="https://zayt.org/collections/jewish-registers-1784-1949/o-2745", prefix="o2745", delitel=1),
    "z-481": dict(archiv="zayt", nazev="Hroubovice (FÚ Luže), židovská kontrolní matrika Z (NA inv. 481)", farnost="Luže",
                  roky="1840–1873", obsah="Z Hroubovice 1840–1873; OCR snímky 3–52; soubor = snímek; oříznuté, šedotónové; "
                                          "sn. 3–11 neotočené, 12–52 otočené o 90° (soubor -r)",
                  url="https://zayt.org/collections/jewish-control-registers-1780-1911/z-481", prefix="z481", delitel=1),
    "su-xiv-5": dict(archiv="zaopava", nazev="Ruda nad Moravou N 1779–1825, ZA Opava, NAD 165, sign. Šu XIV 5 (inv. 7909)",
                     farnost="Ruda nad Moravou (Bartoňov, Bohdíkov, Bušín/Buschin, Hostice, Jakubovice, Olšany, Raškov, Ruda n. M. …)",
                     roky="1779–1825", obsah="OCR snímky 30–95 (asi 1782–1788; str. 1–181 = všechny obce 1779–1788); latinsky; "
                                             "soubor = snímek; obrázky v polovičním rozlišení (1800 px), šedotónové",
                     url="https://digi.archives.cz/da/permalink?xid=be93172a-f13c-102f-8255-0050568c0263",
                     prefix="bohdikov5", delitel=1),
    "su-xiv-4": dict(archiv="zaopava", nazev="Ruda nad Moravou N, O, Z 1772–1778, ZA Opava, NAD 165, sign. Šu XIV 4 (inv. 7908)",
                     farnost="Ruda nad Moravou (Bartoňov, Bohdíkov, Bušín, Hartíkov, Hostice, Jakubovice, Olšany, Raškov …)",
                     roky="1772–1778", obsah="po obcích, u každé N, O, Z (Bušín str. 1–72); OCR snímky 1–177; soubor = snímek; "
                                             "obrázky v polovičním rozlišení, šedotónové",
                     url="https://digi.archives.cz/da/permalink?xid=be9317b6-f13c-102f-8255-0050568c0263", prefix="ruda4", delitel=1),
    "be97d562": dict(archiv="zaopava", nazev="Ruda nad Moravou N, O, Z 1757–1771 s rejstříky N a O (1757–1792), ZA Opava, NAD 165",
                     farnost="Ruda nad Moravou (Bušín, Hostice, Olšany, Dolní Bohdíkov, Klášterec, Vyšehoří, Hartíkov …)",
                     roky="1757–1771", obsah="N str. 1–107, O str. 123–162, Z str. 184–239, rejstříky N a O (do 1792); OCR "
                                             "snímky 1–131 bez sn. 45 (portál nevydal); soubor = snímek; poloviční rozlišení, "
                                             "šedotónové",
                     url="https://digi.archives.cz/da/permalink?xid=be97d562-f13c-102f-8255-0050568c0263", prefix="ruda1757",
                     delitel=1),
    "be9318d8": dict(archiv="zaopava", nazev="Ruda nad Moravou N, Z, O 1701–1757, ZA Opava, NAD 165, sign. Šu XIV 2 (inv. 7906)",
                     farnost="Ruda nad Moravou (Bohdíkov, Bušín, Hartíkov, Hostice, Jakubovice, Janoušov, Klášterec, "
                             "Komňátka, Olšany, Raškov, Štědrákova Lhota, Vyšehoří)",
                     roky="1701–1757", obsah="N 1701–1757 asi sn. 1–249 (sn. 200 = I 1749), O asi sn. 250–363 (sn. 360 = I 1747), Z dál; "
                                             "OCR snímky 1–80 (N 1701–1720), 160–228 (N X 1738 – asi 1757), 250–372 (O 1701–1757) a 373–540 "
                                             "(Z 1701 – asi 1740); soubor = snímek; "
                                             "poloviční rozlišení, šedotónové",
                     url="https://digi.archives.cz/da/permalink?xid=be9318d8-f13c-102f-8255-0050568c0263", prefix="ruda1701",
                     delitel=1),
    "su-xiv-14": dict(archiv="zaopava", nazev="Ruda nad Moravou O 1779–1825, ZA Opava, NAD 165, sign. Šu XIV 14 (inv. 7918)",
                      farnost="Ruda nad Moravou (Bartoňov, Bohdíkov, Bušín, Hostice, Jakubovice, Olšany, Raškov …)",
                      roky="1779–1825", obsah="str. 1–47 = všechny obce 1779–1788, od 1789 po obcích; OCR snímky 1–35 "
                                              "(1779–1788); soubor = snímek; obrázky v polovičním rozlišení, šedotónové",
                      url="https://digi.archives.cz/da/permalink?xid=be9312c0-f13c-102f-8255-0050568c0263", prefix="ruda14", delitel=1),
    "su-xiv-19": dict(archiv="zaopava", nazev="Ruda nad Moravou Z 1779–1825, ZA Opava, NAD 165, sign. Šu XIV 19 (inv. 7923)",
                      farnost="Ruda nad Moravou (Bartoňov, Bohdíkov, Bušín, Hostice, Jakubovice, Olšany, Raškov …)",
                      roky="1779–1825", obsah="str. 1–86 = všechny obce 1779–1788, od 1789 po obcích; OCR snímky 1–302; "
                                              "soubor = snímek; obrázky v polovičním rozlišení, šedotónové",
                      url="https://digi.archives.cz/da/permalink?xid=be930f8c-f13c-102f-8255-0050568c0263", prefix="ruda19", delitel=1),
    "o-830": dict(archiv="zayt", nazev="Kolín, židovská matrika O 1850–1895 s rejstříkem (NA inv. 830)", farnost="Kolín",
                  roky="1850–1895", obsah="OCR snímky 2–78; soubor = snímek; oříznuté, šedotónové, poloviční rozlišení",
                  url="https://zayt.org/collections/jewish-registers-1784-1949/o-830", prefix="o830", delitel=1),
    "noz-530": dict(archiv="zayt", nazev="Hroubovice, židovská matrika N 1874–1895, O 1875–1891, Z 1875–1895 (NA inv. 530)",
                    farnost="Hroubovice", roky="1874–1895",
                    obsah="OCR snímky 2–73; soubor = snímek; oříznuté, šedotónové, poloviční rozlišení",
                    url="https://zayt.org/collections/jewish-registers-1784-1949/noz-530", prefix="noz530", delitel=1),
    "z-236": dict(archiv="zayt", nazev="Hrochův Týnec, židovská kontrolní matrika Z (NA inv. 236)", farnost="Hrochův Týnec",
                  roky="1839–1882", obsah="OCR snímky 41–46 a 51–58 (asi 1855–1857 a 1861–1866); soubor = snímek; zápisy svisle, "
                                          "OCR z oříznutých a otočených obrázků (soubor -r)",
                  url="https://zayt.org/collections/jewish-control-registers-1780-1911/z-236", prefix="z236", delitel=1),
    "noz-726": dict(archiv="zayt", nazev="Přistoupim, židovská kontrolní matrika NOZ (NA inv. 726)", farnost="Přistoupim",
                    roky="1803–1840",
                    obsah="N 1816–1840 s opisy N 1803, 1805, 1808, O 1826–1838, Z 1819–1839, rejstříky; OCR snímky 2–20 "
                          "(1 a 21 desky); soubor = snímek, obrázek oříznutý na knihu",
                    url="https://zayt.org/collections/jewish-control-registers-1780-1911/noz-726", prefix="noz726",
                    delitel=1),
    "noz-727": dict(archiv="zayt", nazev="Přistoupim, židovská kontrolní matrika NOZ (NA inv. 727)", farnost="Přistoupim",
                    roky="1840–1858", obsah="N 1841–1858 s rejstříkem, O 1840–1853, Z 1843–1853; OCR snímky 2–13 (1 a 14 "
                                            "desky); soubor = snímek, obrázek oříznutý na knihu",
                    url="https://zayt.org/collections/jewish-control-registers-1780-1911/noz-727", prefix="noz727",
                    delitel=1),
    "familianti-83": dict(archiv="zayt", nazev="Familiantská kniha Kouřimský kraj HBF IX/IX (Řimovice, Sázava, Kostelec "
                                                "nad Černými lesy)", farnost="panství Kostelec nad Černými lesy",
                          roky="1811–1848", obsah="OCR snímky 21–70 = panství Kostelec nad Černými lesy od fol. 43 (snímek "
                                                  "30 = fol. 60); soubor = snímek",
                          url="https://zayt.org/collections/jewish-familiant-books-1811-1848-redux/83", prefix="fam83",
                          delitel=1),
    "kramerius-1804": dict(archiv="ndk", nazev="Kraméryusowy Cýs. k. Pražské Posstowské Nowiny, ročník 16 (1804)",
                           farnost="celé Čechy (týdeník, Praha)", roky="1804", druh="noviny",
                           obsah="OCR č. 47–52 (24. 11.–29. 12. 1804), str. 185–208; soubor = strana ročníku; IMG_FULL z NDK",
                           url="https://ndk.cz/view/uuid:b1942b3d-435d-11dd-b505-00145e5790ea", prefix="kram1804",
                           delitel=1),
    "kramerius-1805": dict(archiv="ndk", nazev="Kraméryusowy Cýs. k. Pražské Posstowské Nowiny, ročník 17 (1805)",
                           farnost="celé Čechy (týdeník, Praha)", roky="1805", druh="noviny",
                           obsah="OCR č. 1–13 (5. 1.–30. 3. 1805), str. 1–52; soubor = strana ročníku; IMG_FULL z NDK",
                           url="https://ndk.cz/view/uuid:b1942b3e-435d-11dd-b505-00145e5790ea", prefix="kram1805",
                           delitel=1),
}
EXPORTS = {  # export file stem -> books it contains, PERO document, model, date
    "dnesice-01": (["dnesice-01"], "c1785e53-4a1c-40f7-a924-7d219217bf15", "Kurrent (German, Czech)", "2026-10-19"),
    "dnesice-02-test": (["dnesice-02"], "103bd7f2-529f-455d-b84e-285b8807397a", "Kurrent (German, Czech)", "2026-10-19"),
    "dolni-lukavice-01": (["dolni-lukavice-01"], "f576fcb5-bc48-406e-b75a-5a0a3b1e2d2c", "Kurrent (German, Czech)",
                          "2026-10-19"),
    "velky-bor-01": (["velky-bor-01"], "658b2c64-93b8-43a8-a478-3cfd30f232fa", "Kurrent (German, Czech)", "2026-10-19"),
    "velky-bor-02": (["velky-bor-02"], "ea0f5d04-f694-4607-a7b3-030028813dbf", "Czech Handwritten", "2026-10-21"),
    "velky-bor-08-11": (["velky-bor-08", "velky-bor-11"], "f61096eb-8434-4bf0-8567-7e488a5ad40a", "Czech Handwritten",
                        "2026-10-21"),
    "maly-bor-05": (["maly-bor-05"], "414ba723-3991-4f8a-b1a5-5c2b4e63bf4a", "Czech Handwritten", "2026-10-21"),
    "maly-bor-03": (["maly-bor-03"], "d6e5e828-1460-4523-8ec1-891a6cad4f26", "Czech Handwritten", "2026-10-21"),
    "maly-bor-04": (["maly-bor-04"], "949bb837-fa4e-4144-a503-65ae049bcf1f", "Czech Handwritten", "2026-10-21"),
    "knezeves-03": (["6568"], "fda952f8-d802-487f-b70a-c278de37df0a", "Czech Handwritten", "2026-10-21"),
    "zidovske-o235-o2434-noz372": (["noz-372"], "17f0a0e2-56cb-476e-beb1-667191362e2a",
                                   "Kurrent (German, Czech)", "2026-10-21"),
    "zidovske-o235-o2434-otocene": (["o-235", "o-2434"], "00b4fec1-aa87-4774-92ec-bd38077992e2", "Kurrent (German, Czech)",
                                    "2026-10-21"),
    "pristoupim-noz726-noz727": (["noz-726", "noz-727"], "3ffd9a97-1756-472a-bc3f-84333d8b10fc", "Kurrent (German, Czech)",
                                 "2026-10-21"),
    "hermanuv-mestec-o406-otocene": (["o-406"], "59d2c47d-c079-4cbe-af77-4f405ae9982a", "Kurrent (German, Czech)",
                                     "2026-10-22"),
    "hrochuv-tynec-z236-otocene": (["z-236"], "ac372e5b-9763-46d4-9c58-9d48def1d0cf", "Kurrent (German, Czech)",
                                   "2026-10-22"),
    "familianti-83-kostelec": (["familianti-83"], "8c28db92-6852-49c1-8a02-d9dcb650a12b", "Kurrent (German, Czech)",
                               "2026-10-21"),
    "kvasnovice-02": (["kvasnovice-02"], "039c275f-e042-487c-af86-180ece6ab7e1", "Czech Handwritten", "2026-10-21"),
    "kvasnovice-01": (["kvasnovice-01"], "5c1a99a8-9ce5-4a29-b55e-e421741e0f61", "Kurrent (German, Czech)", "2026-10-21"),
    "kvasnovice-05": (["kvasnovice-05"], "eb1b5565-a613-4f43-9054-284e334056b0", "Kurrent (German, Czech)", "2026-10-22"),
    "maly-bor-06": (["maly-bor-06"], "c118aa96-dcf1-4ad3-97b9-21d1454f0e54", "Czech Handwritten", "2026-10-22"),
    "litomysl-z-index-7492": (["sign-7492"], "7c8f80c2-117d-4ead-bb24-519ac40c2005", "Czech Handwritten", "2026-11-02"),
    "dobruska-26-1-26-12": (["sign-26-1", "sign-26-12"], "6543ac92-3886-4503-b2f3-e973817b2f34", "Kurrent (German, Czech)",
                            "2026-11-02"),
    "litomysl-n-1309": (["sign-1309"], "9cf4c19e-3582-41cf-82c8-c4cb45510542", "Kurrent (German, Czech)", "2026-11-02"),
    "kurrent-2741-2745-481": (["o-2741", "o-2745", "z-481"], "8b22ff4d-4bfb-48ce-a789-7644f374dc32",
                              "Kurrent (German, Czech)", "2026-11-02"),
    "bohdikov-su-xiv-5": (["su-xiv-5"], "161c8c33-983b-4c9a-87cd-36473e311b18", "Czech Handwritten", "2026-11-02"),
    "ruda-1757-1771": (["be97d562"], "61da916d-56f4-46e5-b358-2f9080289d2c", "Czech Handwritten", "2026-11-02"),
    "ruda-1701-1757": (["be9318d8"], "59dc2bb6-c7b9-4457-a9a1-4dd2d84eba46, 6e04fb07-1adc-4450-ac97-c3c0d7f458c1, "
                                     "5b1e5314-fc04-48ac-a7d5-fe111c9e8cef, 6323e93c-6924-47eb-9a8a-7ec850109f68",
                       "Czech Handwritten", "2026-11-03"),
    "kasejovice-03-n1667-z1677": (["kasejovice-03"], "9345001a-cea4-433e-a3c7-4e68d4313678", "Kurrent (German, Czech)",
                                  "2026-11-04"),
    "kasejovice-05-o1690-1747": (["kasejovice-05"], "bf7b354b-05a6-45de-b54a-a033d5b780c0", "Kurrent (German, Czech)",
                                 "2026-11-04"),
    "kasejovice-07-z1690-1744": (["kasejovice-07"], "36f52f6b-4218-4534-bc8e-81fd5f392349", "Kurrent (German, Czech)",
                                 "2026-11-04"),
    "kramerius-1804-1805": (["kramerius-1804", "kramerius-1805"], "9fa4607b-77db-46dc-930f-d34910174fc0",
                            "Czech Fraktur Printed", "2026-11-02"),
    "ruda-su-xiv-19": (["su-xiv-19"], "1a7cf0e9-622f-4314-8b7a-2a4027591f52", "Czech Handwritten", "2026-11-02"),
    "ruda-su-xiv-4-14": (["su-xiv-4", "su-xiv-14"], "2d56f6dc-b89c-49a9-9e93-099de7a9306b", "Czech Handwritten", "2026-11-02"),
    "zayt-o830-noz530": (["o-830", "noz-530"], "e9d24973-74c9-4448-a926-a8bbf814d218", "Kurrent (German, Czech)", "2026-11-02"),
    "horazdovice-05": (["horazdovice-05"], "fd143024-c5a7-4f8e-808b-be33654abe80", "Czech Handwritten", "2026-10-22"),
    "vs-horazdovice-k1563": (["vs-horazdovice-k1563"], "d93b37ec-4ffb-4ad6-a2a6-e3d4846c54da", "Czech Handwritten",
                             "2026-10-22"),
    "horazdovice-05-zo": (["horazdovice-05-zo"], "61f588be-d923-4111-85d4-63af9d9c9101", "Czech Handwritten", "2026-10-22"),
    "horazdovice-05-kurrent": (["horazdovice-05-kurrent"], "8862a4c4-aeee-4093-9fc2-cf199db556de", "Kurrent (German, Czech)",
                               "2026-10-22"),
}


def local(element):
    return element.tag.rsplit("}", 1)[-1]


def child(element, name):
    return next((c for c in element if local(c) == name), None)


def parse_page(xml):
    root = ElementTree.fromstring(xml)
    page = root if local(root) == "Page" else next((e for e in root.iter() if local(e) == "Page"), None)
    if page is None:
        return None
    width, height = int(page.get("imageWidth")), int(page.get("imageHeight"))
    lines = []
    for line in (e for e in page.iter() if local(e) == "TextLine"):
        points = [tuple(map(int, p.split(","))) for p in child(line, "Coords").get("points").split()]
        xs, ys = [p[0] for p in points], [p[1] for p in points]
        equiv = child(line, "TextEquiv")
        unicode = child(equiv, "Unicode") if equiv is not None else None
        text = (unicode.text or "") if unicode is not None else ""
        conf = equiv.get("conf", "") if equiv is not None else ""
        lines.append((min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys), conf, " ".join(text.split())))
    return page.get("imageFilename").rsplit(".", 1)[0], width, height, lines


def pages(path):
    with zipfile.ZipFile(path) as archive:
        if path.name.endswith(".pagexml.zip"):
            for name in archive.namelist():
                for chunk in archive.read(name).decode("utf-8").split("### PAGE ")[1:]:
                    yield chunk.split("\n", 1)[1].encode("utf-8")
        else:
            for name in sorted(n for n in archive.namelist() if n.endswith(".xml")):
                yield archive.read(name)


def book_of(image, books):
    for key in books:
        prefix = BOOKS[key]["prefix"]
        if not prefix or image.startswith(prefix + "_"):
            return key
    return None


def file_number(image):
    m = re.search(r"(\d{4})(?:-[a-z]+)?$", image)
    return int(m.group(1)) if m else None


def snimek(key, image):
    n = file_number(image)
    if n is None:
        return ""
    return str(n // BOOKS[key].get("delitel", 10))


def write_book(key, export_stem, rows, page_rows, pero_doc, model, date):
    meta = BOOKS[key]
    out = REPO / "knihy" / meta["archiv"] / key
    out.mkdir(parents=True, exist_ok=True)
    rows.sort(key=lambda r: (file_number(r[1]) or 0, r[1], r[2], r[4]))
    with open(out / "ocr-pero.tsv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter="\t", lineterminator="\n")
        w.writerow(["snimek", "soubor", "strana", "radek", "x", "y", "sirka", "vyska", "jistota", "text"])
        line_no = {}
        for snim, image, side, x, y, wd, ht, conf, text in rows:
            line_no[(image, side)] = line_no.get((image, side), 0) + 1
            w.writerow([snim, image, side, line_no[(image, side)], x, y, wd, ht, conf, text])
    page_rows.sort(key=lambda r: (file_number(r[1]) or 0, r[1]))
    with open(out / "stranky.tsv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter="\t", lineterminator="\n")
        w.writerow(["snimek", "soubor", "sirka_obrazku", "vyska_obrazku", "radku"])
        w.writerows(page_rows)
    q = lambda value: json.dumps(value, ensure_ascii=False)  # a JSON string is a valid YAML scalar, colons included
    yaml = [f"archiv: {q(meta['archiv'])}", f"kniha: {q(key)}", f"nazev: {q(meta['nazev'])}",
            f"druh: {q(meta.get('druh', 'matrika'))}", f"farnost: {q(meta['farnost'])}",
            f"roky: {q(meta['roky'])}", f"obsah: {q(meta['obsah'])}", f"url: {q(meta['url'])}"]
    if meta.get("poznamka"):
        yaml.append(f"poznamka: {q(meta['poznamka'])}")
    yaml += ["ocr:", f"- nastroj: {q('PERO OCR (pero-ocr.fit.vutbr.cz)')}", f"  dokument: {q(pero_doc)}", f"  model: {q(model)}",
            f"  datum: {q(date)}",
            f"  export: {q(export_stem)}",
            f"  stranek: {len(page_rows)}", f"  radku: {len(rows)}",
            f"  poznamka: {q('souřadnice v pixelech nahraného obrázku (viz stranky.tsv); text je strojový, nekontrolovaný')}"]
    (out / "kniha.yaml").write_text("\n".join(yaml) + "\n", encoding="utf-8")
    print(f"{meta['archiv']}/{key}: {len(page_rows)} stran, {len(rows)} řádků")


def main():
    sys.stdout.reconfigure(encoding="utf-8")  # the Windows console defaults to cp1252
    parser = argparse.ArgumentParser()
    parser.add_argument("export", type=Path)
    args = parser.parse_args()
    stem = args.export.name.removesuffix(".zip").removesuffix(".pagexml")
    if stem not in EXPORTS:
        sys.exit(f"unknown export {stem}; add it to EXPORTS")
    keys, pero_doc, model, date = EXPORTS[stem]
    rows = {k: [] for k in keys}
    page_rows = {k: [] for k in keys}
    for xml in pages(args.export):
        parsed = parse_page(xml)
        if parsed is None:
            continue
        image, width, height, lines = parsed
        key = book_of(image, keys)
        if key is None:
            print(f"skipping page {image}", file=sys.stderr)
            continue
        snim = snimek(key, image)
        page_rows[key].append([snim, image, width, height, len(lines)])
        for x, y, wd, ht, conf, text in lines:
            rows[key].append((snim, image, "L" if x < width / 2 else "R", x, y, wd, ht, conf, text))
    for key in keys:
        write_book(key, args.export.name, rows[key], page_rows[key], pero_doc, model, date)


if __name__ == "__main__":
    main()
