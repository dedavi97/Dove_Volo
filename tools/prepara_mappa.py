"""Prepara lo sfondo della mappa: i confini di tutti i paesi del mondo, da Natural Earth (pubblico dominio).

Si lancia di rado: il risultato sito/mondo.json sta nel repo. Dettaglio pieno nella zona delle rotte,
coordinate piu' grezze nel resto del mondo per tenere leggero il file.
"""
import json
import urllib.request
from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent
USCITA = RADICE / "sito" / "mondo.json"
URL = ("https://raw.githubusercontent.com/nvkelso/natural-earth-vector/v5.1.2/"
       "geojson/ne_50m_admin_0_countries.geojson")
# Lat e lon della zona delle rotte, con un po' di margine: sud, ovest, nord, est.
SUD, OVEST, NORD, EST = 20, -40, 82, 80
DECIMALI_ZONA = 2
DECIMALI_RESTO = 1


def tocca_la_zona(anello):
    lon = [p[0] for p in anello]
    lat = [p[1] for p in anello]
    return max(lon) >= OVEST and min(lon) <= EST and max(lat) >= SUD and min(lat) <= NORD


def semplifica(anello, decimali):
    """Arrotonda le coordinate e toglie i punti ripetuti."""
    punti = []
    for lon, lat, *_ in anello:
        punto = [round(lon, decimali), round(lat, decimali)]
        if not punti or punti[-1] != punto:
            punti.append(punto)
    return punti


def riduci(geojson):
    poligoni = []
    for paese in geojson["features"]:
        geometria = paese["geometry"]
        gruppi = geometria["coordinates"] if geometria["type"] == "MultiPolygon" else [geometria["coordinates"]]
        for gruppo in gruppi:
            decimali = DECIMALI_ZONA if tocca_la_zona(gruppo[0]) else DECIMALI_RESTO
            anelli = [a for a in (semplifica(anello, decimali) for anello in gruppo) if len(a) >= 4]
            if anelli:
                poligoni.append(anelli)
    return {"type": "Feature", "properties": {}, "geometry": {"type": "MultiPolygon", "coordinates": poligoni}}


def main():
    richiesta = urllib.request.Request(URL, headers={"User-Agent": "Dove_Volo (https://github.com/dedavi97/Dove_Volo)"})
    with urllib.request.urlopen(richiesta, timeout=120) as risposta:
        geojson = json.load(risposta)
    risultato = riduci(geojson)
    USCITA.write_text(json.dumps(risultato, separators=(",", ":")), encoding="utf-8", newline="\n")
    print(f"Scritto {USCITA}: {len(risultato['geometry']['coordinates'])} poligoni, "
          f"{USCITA.stat().st_size / 1000:.0f} KB")


if __name__ == "__main__":
    main()
