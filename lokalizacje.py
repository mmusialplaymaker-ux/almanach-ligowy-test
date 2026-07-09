#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
lokalizacje.py — z kolumny `stadium` wyciąga miejscowość klubu każdego zawodnika,
liczy dystans do Opola i przygotowuje dane do mapy w apce.

Etapy:
  1) python lokalizacje.py --krok miejscowosci
       -> zawodnicy_miejscowosc.csv (player_id, miejscowosc)  [dom = najczęstszy stadion drużyny]
       -> miejscowosci_do_geokodu.csv (unikalne miejscowości do zgeokodowania)
  2) Ty geokodujesz miejscowosci_do_geokodu.csv u siebie (dowolny geokoder / baza miejscowości PL)
       -> zapisujesz miejscowosci_geo.csv z kolumnami: miejscowosc,lat,lon
  3) python lokalizacje.py --krok dystanse
       -> zawodnicy_lokalizacja.csv (player_id, miejscowosc, lat, lon, km_do_opola)  [do apki]

Wymaga: matches z kolumną `stadium` + `team_id` (dodaj `m.stadium` do feedera meczów),
oraz stats_test.csv (player_id -> team_id/zawodnik). Domyślne nazwy plików jak w projekcie.
"""
import argparse, math, os, re, sys
import pandas as pd

OPOLE = (50.6751, 17.9213)     # ul. Leonarda Olejnika 1, Opole (ok.)
ENC = ("utf-8", "cp1250", "latin-1")


def rd(p):
    for e in ENC:
        try:
            return pd.read_csv(p, dtype=str, keep_default_na=False, encoding=e, on_bad_lines="skip")
        except Exception:
            continue
    raise RuntimeError(f"Nie wczytam {p}")


def miasto(stadium):
    """Wyciąga miejscowość z różnych formatów kolumny stadium."""
    s = str(stadium).strip()
    if not s:
        return ""
    m = re.search(r"\(([^,)]+),", s)                      # 'Nazwa (Miasto, ulica)'
    if m:
        return m.group(1).strip()
    m = re.search(r"\d{2}-\d{3}\s+(.+)$", s)              # 'ulica, XX-XXX Miasto'
    if m:
        return re.sub(r"\s+lok\..*", "", m.group(1)).strip()
    if "," in s:                                          # fallback: ostatni człon
        return s.split(",")[-1].strip()
    return s


def haversine(a, b):
    R = 6371.0
    dlat = math.radians(b[0] - a[0])
    dlon = math.radians(b[1] - a[1])
    x = (math.sin(dlat / 2) ** 2
         + math.cos(math.radians(a[0])) * math.cos(math.radians(b[0])) * math.sin(dlon / 2) ** 2)
    return round(2 * R * math.asin(math.sqrt(x)))


def krok_miejscowosci(a):
    m = rd(a.matches)
    for need in ("stadium", "team_id"):
        if need not in m.columns:
            print(f"BLAD: matches nie ma kolumny '{need}'. Dodaj ja do feedera meczow.")
            sys.exit(1)
    m["_miejsc"] = m["stadium"].map(miasto)
    m["_min"] = pd.to_numeric(m.get("minutes"), errors="coerce").fillna(0)
    m = m[m["_miejsc"].str.strip() != ""]

    # miejscowosc druzyny = najczestszy stadion jej meczow (mecze u siebie powtarzaja obiekt)
    dom_team = (m.groupby("team_id")["_miejsc"]
                  .agg(lambda s: s.value_counts().idxmax()).rename("miejscowosc"))

    reg = a.region.strip().lower()
    has_reg = "region_name" in m.columns
    if has_reg:
        m["_reg"] = m["region_name"].astype(str).str.strip().str.lower()

    rows = []
    for pid, g in m.groupby("player_id"):
        # 1) preferuj klub z NAJWIEKSZA liczba minut w regionie docelowym
        gg = g[g["_reg"] == reg] if has_reg else g.iloc[0:0]
        spoza = False
        if not len(gg) or gg["_min"].sum() == 0:
            gg, spoza = g, True          # brak gry w regionie -> klub spoza regionu
        team = gg.groupby("team_id")["_min"].sum().idxmax()
        rows.append({"player_id": pid, "team_id": team,
                     "miejscowosc": dom_team.get(team, ""),
                     "spoza_regionu": spoza})
    zaw = pd.DataFrame(rows)
    zaw = zaw[zaw["miejscowosc"].astype(str).str.strip() != ""]
    zaw.to_csv("zawodnicy_miejscowosc.csv", index=False, encoding="utf-8-sig")
    uniq = pd.DataFrame({"miejscowosc": sorted(zaw["miejscowosc"].dropna().unique())})
    uniq["lat"] = ""; uniq["lon"] = ""
    uniq.to_csv("miejscowosci_do_geokodu.csv", index=False, encoding="utf-8-sig")
    print(f"Zapisano zawodnicy_miejscowosc.csv ({len(zaw)} zawodnikow, "
          f"spoza regionu '{a.region}': {int(zaw['spoza_regionu'].sum())})")
    print(f"Zapisano miejscowosci_do_geokodu.csv ({len(uniq)} miejscowosci)")
    print("-> uzupelnij lat,lon i zapisz jako miejscowosci_geo.csv")


def krok_dystanse(a):
    if not os.path.exists("miejscowosci_geo.csv"):
        print("BLAD: brak miejscowosci_geo.csv (miejscowosc,lat,lon). Najpierw zgeokoduj.")
        sys.exit(1)
    zaw = rd("zawodnicy_miejscowosc.csv")
    geo = rd("miejscowosci_geo.csv")
    geo["lat"] = pd.to_numeric(geo["lat"], errors="coerce")
    geo["lon"] = pd.to_numeric(geo["lon"], errors="coerce")
    d = zaw.merge(geo, on="miejscowosc", how="left")
    ok = d["lat"].notna() & d["lon"].notna()
    d.loc[ok, "km_do_opola"] = d[ok].apply(lambda r: haversine(OPOLE, (r["lat"], r["lon"])), axis=1)
    cols = ["player_id", "miejscowosc", "lat", "lon", "km_do_opola"]
    if "spoza_regionu" in d.columns:
        cols.append("spoza_regionu")
    d[cols].to_csv("zawodnicy_lokalizacja.csv", index=False, encoding="utf-8-sig")
    print(f"Zapisano zawodnicy_lokalizacja.csv | z dystansem: {int(ok.sum())}/{len(d)}")
    if "spoza_regionu" in d.columns:
        print(f"  spoza regionu (inny kolor na mapie): {int(d['spoza_regionu'].astype(str).isin(['True','true']).sum())}")
    if ok.sum():
        print("Najblizej Opola:")
        print(d[ok].sort_values("km_do_opola")[["miejscowosc", "km_do_opola"]]
              .drop_duplicates().head(8).to_string(index=False))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--krok", choices=["miejscowosci", "dystanse"], required=True)
    ap.add_argument("--matches", default="matches_test.csv")
    ap.add_argument("--stats", default="stats_test.csv")
    ap.add_argument("--region", default="opolskie",
                    help="region docelowy: dom = klub z najwieksza liczba minut w tym regionie")
    a = ap.parse_args()
    if a.krok == "miejscowosci":
        krok_miejscowosci(a)
    else:
        krok_dystanse(a)


if __name__ == "__main__":
    main()