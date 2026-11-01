"""Prepara lo sfondo della mappa: i confini dei paesi di Natural Earth (pubblico dominio).

Si lancia una volta sola, o se si vuole cambiare la zona disegnata: il risultato sito/europa.json
sta nel repo. Tiene i paesi dell'area, con quelli vicini per dare contesto, e solo le coordinate.
"""
import json
import urllib.request
from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent
USCITA = RADICE / "sito" / "europa.json"
URL = ("https://raw.githubusercontent.com/nvkelso/natural-earth-vector/v5.1.2/"
       "geojson/ne_50m_admin_0_countries.geojson")
# Lat e lon della zona disegnata: sud, ovest, nord, est.
SUD, OVEST, NORD, EST = 20, -40, 82, 80
DECIMALI = 2


def tocca_la_zona(anello):
    lon = [p[0] for p in anello]
    lat = [p[1] for p in anello]
    return max(lon) >= OVEST and min(lon) <= EST and max(lat) >= SUD and min(lat) <= NORD


def semplifica(anello):
    """Arrotonda le coordinate e toglie i punti ripetuti."""
    punti = []
    for lon, lat, *_ in anello:
        punto = [round(lon, DECIMALI), round(lat, DECIMALI)]
        if not punti or punti[-1] != punto:
            punti.append(punto)
    return punti


def riduci(geojson):
    poligoni = []
    for paese in geojson["features"]:
        geometria = paese["geometry"]
        gruppi = geometria["coordinates"] if geometria["type"] == "MultiPolygon" else [geometria["coordinates"]]
        for gruppo in gruppi:
            if tocca_la_zona(gruppo[0]):
                anelli = [semplifica(anello) for anello in gruppo]
                poligoni.append([a for a in anelli if len(a) >= 4])
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
