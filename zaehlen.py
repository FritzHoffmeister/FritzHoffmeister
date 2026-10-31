"""Zählt die Python-Zeilen in allen eigenen Repos und schreibt die Summe ins README.

Das Profil-Repo ist öffentlich: Repo-Namen tauchen deshalb weder im Code noch in der
Ausgabe auf. Es wird nur die Summe und die Zahl der Projekte gedruckt und geschrieben.

Umgebung:
  LOC_TOKEN    Token mit Lesezugriff auf die privaten Repos
  LOC_EXCLUDE  optional, kommagetrennte Repo-Namen, die nicht mitzählen (als Secret)
"""
import base64
import json
import os
import re
import subprocess
import tempfile
import urllib.request
from pathlib import Path

OWNER = "FritzHoffmeister"
README = Path(__file__).with_name("README.md")
MARKE = re.compile(r"(<!--zeilen-->).*?(<!--/zeilen-->)", re.S)


def api(pfad, token):
    req = urllib.request.Request(
        f"https://api.github.com{pfad}",
        headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"},
    )
    with urllib.request.urlopen(req) as r:
        return json.load(r)


def eigene_repos(token):
    repos, seite = [], 1
    while True:
        teil = api(f"/user/repos?affiliation=owner&per_page=100&page={seite}", token)
        if not teil:
            return repos
        repos += [r for r in teil if r["owner"]["login"] == OWNER and not r["fork"]]
        seite += 1


def python_zeilen(repo, token, ziel):
    kopf = "http.extraHeader=Authorization: Basic " + base64.b64encode(
        f"x-access-token:{token}".encode()).decode()
    ok = subprocess.run(
        ["git", "-c", kopf, "clone", "--depth", "1", "--quiet", repo["clone_url"], ziel],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    ).returncode == 0
    if not ok:
        return None
    dateien = subprocess.run(["git", "-C", ziel, "ls-files", "-z", "*.py"],
                             capture_output=True).stdout.split(b"\0")
    n = 0
    for d in filter(None, dateien):
        try:
            n += (Path(ziel) / d.decode()).read_bytes().count(b"\n")
        except (OSError, UnicodeDecodeError):
            pass
    return n


def main():
    token = os.environ["LOC_TOKEN"]
    aus = {s.strip().lower() for s in os.environ.get("LOC_EXCLUDE", "").split(",") if s.strip()}
    summe, projekte, fehler = 0, 0, 0
    for repo in eigene_repos(token):
        if repo["name"].lower() in aus or repo["name"] == OWNER:
            continue
        with tempfile.TemporaryDirectory() as tmp:
            n = python_zeilen(repo, token, str(Path(tmp) / "r"))
        if n is None:
            fehler += 1
        elif n > 0:
            summe += n
            projekte += 1
    if projekte == 0:
        raise SystemExit("Keine Zeilen gezählt, README bleibt unverändert.")
    gerundet = f"{round(summe, -3):,}".replace(",", ".")
    zeile = f"≈ {gerundet} Zeilen Python in {projekte} privaten Projekten"
    README.write_text(MARKE.sub(rf"\g<1>{zeile}\g<2>", README.read_text()))
    print(zeile, f"(nicht lesbar: {fehler})" if fehler else "")


if __name__ == "__main__":
    main()
