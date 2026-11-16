"""
Partie 1 : Simulation synchrone d'un bar à cocktails.
Ce module gère séquentiellement les interactions entre un serveur et un bariste.
"""
import sys
import time
import re
import os
import tempfile
import argparse
import logging
import json
from typing import List, Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

# --- Configuration ---
FICHIER_LOG = os.path.join(tempfile.gettempdir(), "borabora_sync.log")
logging.basicConfig(
    filename=FICHIER_LOG,
    level=logging.INFO,
    format='%(message)s',
    filemode='w'
)
console = Console()

# ==========================================
# CLASSES DE BASE ET ACCESSOIRES
# ==========================================
class Logable:
    def __init__(self, name: str, verbose: bool) -> None:
        self.name = name
        self.verbose = verbose

    def log(self, msg: str) -> None:
        message = f"[{self.name}] {msg}"
        logging.info(message)
        if self.verbose:
            print(message, flush=True)

class Accessoire(list, Logable):
    def __init__(self, name: str = "accessoire", verbose: bool = True) -> None:
        list.__init__(self)
        Logable.__init__(self, name, verbose)

class Pic(Accessoire):
    def embrocher(self, postit: List[str]) -> None:
        self.insert(0, postit)  
        self.log(f"post-it '{postit}' embroché, {len(self)} post-it(s) à traiter")

    def liberer(self) -> Optional[List[str]]:
        if len(self) > 0:
            postit = self.pop()
            self.log(f"post-it '{postit}' libéré, {len(self)} post-it(s) à traiter")
            return postit
        return None

class Bar(Accessoire):
    def recevoir(self, commande: List[str]) -> None:
        self.insert(0, commande)
        self.log(f"'{commande}' posée, {len(self)} commande(s) à servir")

    def evacuer(self) -> Optional[List[str]]:
        if len(self) > 0:
            commande = self.pop()
            self.log(f"'{commande}' évacuée, {len(self)} commande(s) à servir")
            return commande
        return None

class Employe(Logable):
    def __init__(self, pic: Pic, bar: Bar, clients: "Clients", name: str, verbose: bool) -> None:
        Logable.__init__(self, name, verbose)
        self.pic = pic
        self.bar = bar
        self.clients = clients
        self.step = 0
        # Statistiques
        self.cocktails_traites = 0
        self.commandes_traitees = 0
        self.log("prêt pour le service")

class Serveur(Employe):
    def prendre_commande(self) -> None:
        while True:
            commande = self.clients.commande()
            if commande is None: break
            self.log(f"prêt pour prendre une nouvelle commande...")
            self.log(f"j'ai la commande '{commande}'")
            self.pic.embrocher(commande)

    def servir(self) -> None:
        while True:
            commande = self.bar.evacuer()
            if commande is None: break
            self.log(f"j'apporte la commande '{commande}'")
            for conso in commande:
                self.log(f"je sers '{conso}'")
                self.cocktails_traites += 1
            self.commandes_traitees += 1

    def run(self) -> None:
        if self.step == 0:
            self.step += 1
            self.prendre_commande()
        elif self.step == 1:
            self.step += 1
            self.servir()

class Bariste(Employe):
    def preparer(self) -> None:
        while True:
            commande = self.pic.liberer()
            if commande is None: break
            self.log(f"je commence la fabrication de '{commande}'")
            for conso in commande:
                self.log(f"je prépare '{conso}'")
                self.cocktails_traites += 1
            self.bar.recevoir(commande)
            self.log(f"la commande '{commande}' est prête")
            self.commandes_traitees += 1

    def run(self) -> None:
        self.preparer()

class Clients:
    def __init__(self, fname: str) -> None:
        self.commandes: List[tuple[float, List[str]]] = []
        start = time.time()
        fmt = re.compile(r"(\d+)\s+(.*)")
        try:
            with open(fname, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line: continue
                    found = fmt.search(line)
                    if found:
                        when = int(found.group(1))
                        what = found.group(2)
                        self.commandes.append((start + when, what.split(",")))
                    else:
                        # C'EST CETTE LIGNE QUI MANQUAIT
                        print(f"⚠️ Ligne ignorée (format incorrect) : {line}")
        except FileNotFoundError:
            print(f"❌ Erreur : Le fichier '{fname}' est introuvable.")
            sys.exit(1)
        self.commandes = self.commandes[::-1]

    def commande(self) -> Optional[List[str]]:
        if len(self.commandes) > 0:
            while True:
                if time.time() > self.commandes[-1][0]:
                    return self.commandes.pop()[1]
                time.sleep(0.01)
        return None

# ==========================================
# PROGRAMME PRINCIPAL
# ==========================================
def main() -> None:
    parser = argparse.ArgumentParser(description="Simulation synchrone d'un bar à cocktails.")
    parser.add_argument("fichier", help="Le fichier contenant les commandes (ex: commandes/lundi)")
    args = parser.parse_args()

    try:
        with open("config.json", "r", encoding="utf-8") as f:
            config = json.load(f)
    except FileNotFoundError:
        config = {"bob": {"verbose": False}, "alice": {"verbose": True}}

    print(f"Écriture des logs dans {FICHIER_LOG}")
    debut = time.time()
    
    le_pic = Pic(name="le_pic", verbose=False)
    le_bar = Bar(name="le_bar", verbose=False)
    les_clients = Clients(args.fichier)
    
    bob = Bariste(le_pic, le_bar, les_clients, name="bob", verbose=config["bob"]["verbose"])
    alice = Serveur(le_pic, le_bar, les_clients, name="alice", verbose=config["alice"]["verbose"])

    alice.run()
    bob.run()
    alice.run()

    fin = time.time()
    
    # --- RAPPORT AVEC RICH ---
    table = Table(title="🏁 RAPPORT DE FIN DE SERVICE (SYNCHRONE)")
    table.add_column("Employé", style="cyan")
    table.add_column("Cocktails Traités", style="magenta")
    table.add_column("Commandes Traitées", style="green")

    table.add_row("Bob (Bariste)", str(bob.cocktails_traites), str(bob.commandes_traitees))
    table.add_row("Alice (Serveur)", str(alice.cocktails_traites), str(alice.commandes_traitees))

    console.print(table)
    console.print(Panel(f"⏱️ Temps total d'exécution : {fin - debut:.2f} secondes", style="bold yellow"))

if __name__ == "__main__":
    main()