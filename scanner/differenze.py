"""Riepilogo: cosa cambia rispetto al file precedente."""
from collections import Counter

MAX_ESEMPI = 15


def _firma(rotta):
    return sorted(str((c["iata"], c.get("nome"), c.get("voli_sett"), c.get("giorni"))) for c in rotta["compagnie"])


def confronta(precedente, nuovi):
    """Elenca le rotte nuove, sparite, tornate e cambiate. Senza file precedente non c'e' confronto."""
    vecchie = {(r["da"], r["a"]): r for r in precedente["rotte"]} if precedente else {}
    risultato = {"nuove": [], "sparite": [], "tornate": [], "cambiate": []}
    for rotta in nuovi["rotte"]:
        chiave = (rotta["da"], rotta["a"])
        vecchia = vecchie.get(chiave)
        if vecchia is None:
            risultato["nuove"].append(chiave)
        elif vecchia["stato"] == "attiva" and rotta["stato"] != "attiva":
            risultato["sparite"].append(chiave)
        elif vecchia["stato"] != "attiva" and rotta["stato"] == "attiva":
            risultato["tornate"].append(chiave)
        elif _firma(vecchia) != _firma(rotta):
            risultato["cambiate"].append(chiave)
    nuove_chiavi = {(r["da"], r["a"]) for r in nuovi["rotte"]}
    risultato["sparite"] += [k for k in vecchie if k not in nuove_chiavi]
    return risultato


def riepilogo(precedente, nuovi, avvisi):
    """Il testo da mostrare a Davide prima della domanda."""
    stati = Counter(r["stato"] for r in nuovi["rotte"])
    aeroporti = nuovi["aeroporti"]
    completi = sum(1 for a in aeroporti.values() if a["settimana_completa"])
    con_voli = sum(1 for r in nuovi["rotte"] for c in r["compagnie"] if c["voli_sett"])
    righe = [
        f"Aeroporti: {len(aeroporti)} (settimana completa: {completi})",
        f"Rotte: {len(nuovi['rotte'])} = attive {stati['attiva']}, stagionali {stati['stagionale']}, "
        f"annunciate {stati['annunciata']}, nascoste {stati['nascosta']}",
    ]
    if not con_voli:
        righe.append("ATTENZIONE: questo file non ha frequenze, il sito mostrera' solo le compagnie.")
    if precedente is None:
        righe.append("Prima esecuzione: non c'e' un file precedente da confrontare.")
    else:
        d = confronta(precedente, nuovi)
        righe.append(f"Rispetto al {precedente['aggiornato']}: {len(d['nuove'])} nuove, "
                     f"{len(d['sparite'])} sparite, {len(d['tornate'])} tornate, {len(d['cambiate'])} cambiate")
        for nome in ("nuove", "sparite", "tornate", "cambiate"):
            if d[nome]:
                esempi = ", ".join(f"{a}>{b}" for a, b in sorted(d[nome])[:MAX_ESEMPI])
                altre = len(d[nome]) - MAX_ESEMPI
                righe.append(f"  {nome}: {esempi}" + (f" e altre {altre}" if altre > 0 else ""))
        prima = sum(1 for r in precedente["rotte"] if r["stato"] == "attiva")
        if prima and con_voli and stati["attiva"] < prima * 0.7:
            righe.append(f"ATTENZIONE: le rotte attive scendono da {prima} a {stati['attiva']}. "
                         "Controlla prima di pubblicare, soprattutto se non e' un cambio di stagione.")
    righe += [f"AVVISO: {a}" for a in avvisi]
    return "\n".join(righe)
