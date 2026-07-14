#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
powolania.py - parsuje PDF-y powolan OZPN (pilkaopolska) i dopasowuje do naszych
zawodnikow -> powolania_kadra.csv (player_id, kadra_woj, liczba_powolan, akcje, rocznik_pdf).
Pliki: "Lista-powolanych*.pdf" + stats_test.csv w tym samym folderze.
Uzycie: python powolania.py
Wymaga: pip install pdfplumber pandas
"""
import glob, os, re, sys, unicodedata
import pandas as pd
import pdfplumber

ENC = ("utf-8", "cp1250", "latin-1")

def _norm(s):
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z]", "", s.lower())

def _rd(p):
    for e in ENC:
        try: return pd.read_csv(p, dtype=str, keep_default_na=False, encoding=e, on_bad_lines="skip")
        except Exception: continue
    raise RuntimeError(f"Nie wczytam {p}")

def parse_pdf(path):
    with pdfplumber.open(path) as pdf:
        txt = "\n".join((p.extract_text() or "") for p in pdf.pages)
    m = re.search(r"rocznik[a]?\s+(20\d\d)", txt, re.I)
    rocznik = int(m.group(1)) if m else None
    md = re.search(r"dnia\s+([\d.]+)", txt)
    data = md.group(1).strip(".") if md else ""
    lastname_first = bool(re.search(r"NAZWISKO\s+I\s+IMI", txt, re.I))
    out = []
    for line in txt.splitlines():
        mm = re.match(r"^\s*(\d{1,2})\s+([A-ZĄĆĘŁŃÓŚŹŻ].+)", line)
        if not mm: continue
        rest = re.sub(r"\(BR\)", " ", mm.group(2)).strip()
        tk = rest.split()
        if len(tk) < 3: continue
        fn, ln = (tk[1], tk[0]) if lastname_first else (tk[0], tk[1])
        out.append((fn, ln, " ".join(tk[2:])))
    return rocznik, data, out

def main():
    pdfs = sorted(glob.glob("Lista-powolanych*.pdf"))
    if not pdfs:
        print("Brak plikow Lista-powolanych*.pdf w folderze."); sys.exit(1)
    rows = []
    for p in pdfs:
        rocznik, data, zaw = parse_pdf(p)
        akcja = os.path.basename(p).replace("Lista-powolanych-zawodnikow-na-", "").replace(".pdf", "")
        akcja = re.sub(r"[-_]+", " ", akcja)[:50].strip()
        for fn, ln, klub in zaw:
            rows.append({"_key": _norm(fn) + "|" + _norm(ln), "fn": fn, "ln": ln,
                         "rocznik_pdf": rocznik, "data": data, "akcja": akcja, "klub_pdf": klub})
        print(f"  {os.path.basename(p)[:48]:48} rocznik={rocznik} osob={len(zaw)}")
    pw = pd.DataFrame(rows)

    if not os.path.exists("stats_test.csv"):
        print("Brak stats_test.csv - zapisuje sama liste powolan (bez player_id).")
        pw.drop(columns=["_key"]).to_csv("powolania_kadra.csv", index=False, encoding="utf-8-sig")
        return
    s = _rd("stats_test.csv").drop_duplicates("player_id").copy()
    s["_key"] = s["firstname"].map(_norm) + "|" + s["lastname"].map(_norm)
    key2pid = s.drop_duplicates("_key").set_index("_key")["player_id"]
    pw["player_id"] = pw["_key"].map(key2pid)
    hit = pw[pw["player_id"].notna()].copy()

    def _nm(g): return f"{g['fn'].iloc[0]} {g['ln'].iloc[0]}"
    agg = (hit.groupby("player_id")
              .apply(lambda g: pd.Series({
                  "zawodnik": _nm(g),
                  "rocznik_pdf": g["rocznik_pdf"].max(),
                  "liczba_powolan": g["akcja"].nunique(),
                  "akcje": "; ".join(sorted(set(g["akcja"]))[:4]),
              }))
              .reset_index())
    agg["kadra_woj"] = True
    nasz = s.drop_duplicates("player_id").set_index("player_id")["est_birth_year"].str[:4]
    agg["nasz_rocznik"] = agg["player_id"].map(nasz)
    agg["rocznik_zgodny"] = agg["nasz_rocznik"].astype(str) == agg["rocznik_pdf"].astype(str)
    agg.to_csv("powolania_kadra.csv", index=False, encoding="utf-8-sig")

    print(f"\nPowolanych ogolem (unikalnych): {pw['_key'].nunique()}")
    print(f"Dopasowanych do naszej bazy: {len(agg)}")
    print(f"  rocznik zgodny z PDF: {int(agg['rocznik_zgodny'].sum())} "
          f"| niezgodny (kandydat na korekte z oficjalnego dokumentu): {int((~agg['rocznik_zgodny']).sum())}")
    print("Zapisano powolania_kadra.csv")

if __name__ == "__main__":
    main()