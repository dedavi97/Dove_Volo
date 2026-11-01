"""Quali aeroporti fanno parte di Dove_Volo: Europa larga, senza eliporti."""

UE27 = "AT BE BG HR CY CZ DK EE FI FR DE GR HU IE IT LV LT LU MT NL PL PT RO SK SI ES SE".split()
PAESI_AREA = set(UE27) | set(
    "GB NO IS CH LI AL BA ME RS MK XK MD UA BY TR GE AM AZ FO GI IM JE GG SJ".split()
)
LON_MAX_RUSSIA = 60.0

# Secondo codice dello stesso aeroporto: Basilea-Mulhouse ha sia BSL sia MLH.
ALIAS = {"MLH": "BSL"}
# Eliporti che OurAirports non conosce, quindi non riconoscibili dal tipo.
ELIPORTI_EXTRA = {"AEI", "VIF"}


def codice_unico(codice):
    return ALIAS.get(codice, codice)


def nell_area(paese, lon):
    if paese == "RU":
        return lon < LON_MAX_RUSSIA
    return paese in PAESI_AREA


def _numero(valore):
    try:
        return float(valore)
    except (TypeError, ValueError):
        return None


def leggi_aeroporti(righe):
    """Dalle righe di OurAirports ricava gli aeroporti dell'area e tutti i codici conosciuti.

    Restituisce (area, conosciuti). `area` e' {iata: {nome, citta, paese, lat, lon}}.
    """
    scelte = {}
    for riga in righe:
        codice = (riga.get("iata_code") or "").strip()
        if not codice or riga.get("type") == "closed":
            continue
        if codice not in scelte or riga.get("scheduled_service") == "yes":
            scelte[codice] = riga

    area = {}
    for codice, riga in scelte.items():
        lat, lon = _numero(riga.get("latitude_deg")), _numero(riga.get("longitude_deg"))
        if lat is None or lon is None:
            continue
        if riga.get("type") == "heliport" or codice in ELIPORTI_EXTRA:
            continue
        if nell_area(riga.get("iso_country"), lon):
            area[codice] = {
                "nome": riga.get("name") or codice,
                "citta": riga.get("municipality") or "",
                "paese": riga["iso_country"],
                "lat": round(lat, 4),
                "lon": round(lon, 4),
            }
    return area, set(scelte) | set(ALIAS) | ELIPORTI_EXTRA
