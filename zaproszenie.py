#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
zaproszenie.py - generator PDF "Zaproszenie na testy" z logo klubu.
Funkcja generuj(...) wolana z apki po kliknieciu zawodnika; jest tez CLI do testow.
"""
import os, glob, datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

KLUB = "OKS Odra Opole"
ADRES = "ul. Leonarda Olejnika 1, 45-839 Opole"
KONTAKT = ""  # np. "tel. ..., e-mail: ..."

def _logo():
    for name in ("logo.jpg", "logo.png", "logo.jpeg"):
        if os.path.exists(name):
            return name
    g = glob.glob("*logo*.*") + glob.glob("*.jpg") + glob.glob("*.png")
    return g[0] if g else None

def generuj(zawodnik, rocznik="", klub_zawodnika="", out_path="zaproszenie.pdf",
            klub=KLUB, adres=ADRES, kontakt=KONTAKT, logo=None,
            data_testow="", miejsce_testow=""):
    logo = logo or _logo()
    c = canvas.Canvas(out_path, pagesize=A4)
    W, H = A4
    y = H - 30 * mm
    if logo and os.path.exists(logo):
        try:
            img = ImageReader(logo)
            iw, ih = img.getSize()
            w = 38 * mm; h = w * ih / iw
            c.drawImage(img, (W - w) / 2, y - h + 10 * mm, width=w, height=h,
                        preserveAspectRatio=True, mask="auto")
            y -= h
        except Exception:
            pass
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(W / 2, y, klub)
    y -= 7 * mm
    c.setFont("Helvetica", 9)
    c.drawCentredString(W / 2, y, adres + ("  |  " + kontakt if kontakt else ""))
    y -= 6 * mm
    c.setStrokeColor(colors.HexColor("#c0392b")); c.setLineWidth(1.2)
    c.line(25 * mm, y, W - 25 * mm, y)
    y -= 18 * mm

    c.setFont("Helvetica", 10)
    c.drawRightString(W - 25 * mm, y, "Opole, dnia " + datetime.date.today().strftime("%d.%m.%Y") + " r.")
    y -= 16 * mm
    c.setFont("Helvetica-Bold", 15)
    c.drawCentredString(W / 2, y, "ZAPROSZENIE NA TESTY")
    y -= 14 * mm

    c.setFont("Helvetica", 11)
    txt = c.beginText(25 * mm, y); txt.setLeading(16)
    naglowek = f"Szanowni Państwo,"
    txt.textLine(naglowek); txt.textLine("")
    linia = (f"{klub} ma przyjemność zaprosić zawodnika "
             f"{zawodnik}" + (f" (rocznik {rocznik})" if rocznik else "") +
             (f", {klub_zawodnika}," if klub_zawodnika else "") +
             " na testy do drużyny młodzieżowej naszego klubu.")
    # zawijanie
    import textwrap
    for w in textwrap.wrap(linia, 92):
        txt.textLine(w)
    txt.textLine("")
    if data_testow:
        txt.textLine(f"Termin testów: {data_testow}")
    if miejsce_testow:
        txt.textLine(f"Miejsce: {miejsce_testow}")
    if data_testow or miejsce_testow:
        txt.textLine("")
    for w in textwrap.wrap("Prosimy o potwierdzenie obecności oraz zabranie stroju treningowego, "
                           "obuwia na nawierzchnię naturalną i sztuczną oraz ochraniaczy. "
                           "W przypadku pytań pozostajemy do dyspozycji.", 92):
        txt.textLine(w)
    c.drawText(txt)

    c.setFont("Helvetica", 11)
    c.drawRightString(W - 25 * mm, 45 * mm, "Z wyrazami szacunku,")
    c.drawRightString(W - 25 * mm, 38 * mm, klub)
    c.showPage(); c.save()
    return out_path

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--zawodnik", required=True)
    ap.add_argument("--rocznik", default="")
    ap.add_argument("--klub-zawodnika", dest="kz", default="")
    ap.add_argument("--data", default=""); ap.add_argument("--miejsce", default="")
    ap.add_argument("--out", default="zaproszenie.pdf")
    a = ap.parse_args()
    p = generuj(a.zawodnik, a.rocznik, a.kz, a.out, data_testow=a.data, miejsce_testow=a.miejsce)
    print("Zapisano", p)