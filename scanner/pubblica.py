"""Pubblica su GitHub il solo file dati."""
import subprocess


def _git(cartella, *argomenti):
    return subprocess.run(["git", *argomenti], cwd=cartella, capture_output=True, text=True, encoding="utf-8")


def motivo_blocco(cartella, percorso):
    """Controlla che pubblicare non trascini altro. Restituisce il problema o None."""
    relativo = percorso.relative_to(cartella).as_posix()
    if _git(cartella, "fetch", "--quiet").returncode != 0:
        return "Non riesco a contattare GitHub: controlla la connessione."
    conta = _git(cartella, "rev-list", "--left-right", "--count", "@{u}...HEAD")
    if conta.returncode != 0:
        return "Il ramo non e' collegato a GitHub."
    indietro, avanti = map(int, conta.stdout.split())
    if indietro:
        return "Su GitHub ci sono modifiche che qui mancano: scaricale prima con 'git pull'."
    if avanti:
        return "Ci sono commit non ancora pubblicati: il push trascinerebbe anche quelli. Pubblicali prima."
    if _git(cartella, "status", "--porcelain", "--", relativo).stdout.strip():
        return f"{relativo} ha modifiche non pubblicate fatte a mano o da una prova: riportalo com'era."
    return None


def pubblica(cartella, percorso, data):
    """Commit e push del solo file dati. Restituisce (riuscito, messaggio)."""
    relativo = percorso.relative_to(cartella).as_posix()
    if _git(cartella, "add", "--", relativo).returncode != 0:
        return False, "git add non riuscito."
    if not _git(cartella, "diff", "--cached", "--name-only", "--", relativo).stdout.strip():
        return True, "Nessuna differenza da pubblicare."
    commit = _git(cartella, "commit", "--quiet", "-m", f"Dati aggiornati al {data}", "--", relativo)
    if commit.returncode != 0:
        return False, f"Commit non riuscito: {commit.stderr.strip()}"
    push = _git(cartella, "push", "--quiet")
    if push.returncode != 0:
        return False, f"Commit fatto ma push non riuscito: {push.stderr.strip()}"
    return True, "Pubblicato."
