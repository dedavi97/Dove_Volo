"""Scanner di Dove_Volo: raccoglie i dati e produce il file JSON del sito."""
from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent


def versione():
    """L'unico punto in cui e' scritta la versione e' il file VERSIONE."""
    return (RADICE / "VERSIONE").read_text(encoding="utf-8").strip()
