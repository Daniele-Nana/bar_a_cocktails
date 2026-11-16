"""
Partie 2 & 3 : Simulation asynchrone.
Intègre asyncio, asyncio.Queue, asyncio.Lock, argparse, config.json, logging et rich.
"""
import asyncio
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
FICHIER_LOG = os.path.join(tempfile.gettempdir(), "borabora_async.log")
logging.basicConfig(
    filename=FICHIER_LOG,
    level=logging.INFO,
    format='%(message)s',
    filemode='w'
)
console = Console()

class Logable:
    def __init__(self, name: str, verbose: bool):
        self.name = name
        self.verbose = verbose

    def log(self, msg: str) -> None:
        message = f"[{self.name}] {msg}"
        logging.info(message)
        if self.verbose:
            print(message, flush=True)

class Accessoire(Logable):
    pass

class Pic(Accessoire):
    def __init__(self, name, verbose):
        super().__init__(name, verbose)
        self.file = asyncio.Queue()

    async def embrocher(self, postit):
        await self.file.put(postit)
        self.log(f"post-it '{postit}' embroché, {self.file.qsize()} en attente")

    async def liberer(self):
        postit = await self.file.get()
        self.log(f"post-it '{postit}' libéré, {self.file.qsize()} en attente")
        return postit

class Bar(Accessoire):
    def __init__(self, name, verbose):
        super().__init__(name, verbose)
        self.file = asyncio.Queue()

    async def recevoir(self, commande):
        await self.file.put(commande)
        self.log(f"commande '{commande}' posée, {self.file.qsize()} à servir")

    async def evacuer(self):
        commande = await self.file.get()
        self.log(f"commande '{commande}' évacuée, {self.file.qsize()} à servir")
        return commande

class Employe(Logable):
    def __init__(self, pic: Pic, bar: Bar, clients: "Clients", name: str, verbose: bool, delai: float = 0):
        super().__init__(name, verbose)
        self.pic = pic
        self.bar = bar
        self.clients = clients
        self.delai = delai
        self.cocktails_traites = 0
        self.commandes_traitees = 0

class Serveur(Employe):
    def __init__(self, pic, bar, clients, name, verbose, delai=0):
        super().__init__(pic, bar, clients, name, verbose, delai)
        self.verrou = asyncio.Lock() 

    async def prendre_commandes(self):
        while True:
            commande = await self.clients.commande()
            if commande is None:
                async with self.verrou:
                    await self.pic.embrocher(None) # Sentinelle
                break
            
            async with self.verrou:
                self.log("prêt pour prendre une nouvelle commande...")
                self.log(f"j'ai la commande '{commande}'")
                self.log(f"j'écris sur le post-it '{commande}'")
                await self.pic.embrocher(commande)
                await asyncio.sleep(self.delai)
            await asyncio.sleep(0)

    async def servir(self):
        while True:
            commande = await self.bar.evacuer()
            if commande is None:
                break 
            
            async with self.verrou:
                self.log(f"j'apporte la commande '{commande}'")
                for conso in commande:
                    self.log(f"je sers '{conso}'")
                    self.cocktails_traites += 1
                    await asyncio.sleep(self.delai)
                self.commandes_traitees += 1
            await asyncio.sleep(0)

class Bariste(Employe):
    def __init__(self, pic, bar, clients, name, verbose, delai=0, nb_serveurs=1):
        super().__init__(pic, bar, clients, name, verbose, delai)
        self.nb_serveurs = nb_serveurs
        self.est_fini = False # <-- NOUVEAU : Indique si Bob a fini son travail

    async def preparer(self):
        while True:
            commande = await self.pic.liberer()
            if commande is None:
                # 1. On prévient tous les serveurs
                for _ in range(self.nb_serveurs):
                    await self.bar.recevoir(None)
                
                # 2. On vide le Pic des autres sentinelles laissées par les serveurs
                while not self.pic.file.empty():
                    await self.pic.liberer()
                
                self.est_fini = True # 3. On signale qu'on a fini
                break
            
            self.log(f"je commence la fabrication de '{commande}'")
            for conso in commande:
                self.log(f"je prépare '{conso}'")
                self.cocktails_traites += 1
                await asyncio.sleep(self.delai)
            await self.bar.recevoir(commande)
            self.log(f"la commande '{commande}' est prête")
            self.commandes_traitees += 1
            await asyncio.sleep(0)

    async def servir_si_possible(self):
        while True:
            if self.est_fini:
                break # <-- Si Bob a fini, la tâche s'arrête proprement

            if self.pic.file.empty() and not self.bar.file.empty():
                commande = await self.bar.evacuer()
                
                if commande is None:
                    await self.bar.recevoir(None)
                    break
                    
                self.log(f"j'aide à servir '{commande}'")
                for conso in commande:
                    self.log(f"je sers '{conso}'")
                    self.cocktails_traites += 1
                    await asyncio.sleep(self.delai)
                self.commandes_traitees += 1
            else:
                await asyncio.sleep(0.05)

class Clients:
    def __init__(self, fname: str):
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
                        self.commandes.append((start + int(found.group(1)), found.group(2).split(",")))
                    else:
                        # C'EST CETTE LIGNE QUI MANQUAIT
                        print(f"⚠️ Ligne ignorée (format incorrect) : {line}")
        except FileNotFoundError:
            print(f"❌ Erreur : Fichier '{fname}' introuvable.")
            sys.exit(1)
        self.commandes = self.commandes[::-1]

    async def commande(self) -> Optional[List[str]]:
        if self.commandes:
            while True:
                if time.time() > self.commandes[-1][0]:
                    return self.commandes.pop()[1]
                await asyncio.sleep(0.01)
        return None

async def main_async(fcommands: str) -> None:
    print(f"Écriture des logs dans {FICHIER_LOG}")
    debut = time.time()
    
    try:
        with open("config.json", "r", encoding="utf-8") as f:
            config = json.load(f)
    except FileNotFoundError:
        config = {"bob": {"delai": 0.2, "verbose": False}, "alice": {"delai": 0.5, "verbose": True}, "clara": {"delai": 0.1, "verbose": True}}

    le_pic = Pic(name="le_pic", verbose=False)
    le_bar = Bar(name="le_bar", verbose=False)
    les_clients = Clients(fcommands)
    
    bob = Bariste(le_pic, le_bar, les_clients, name="bob", verbose=config["bob"]["verbose"], delai=config["bob"]["delai"], nb_serveurs=2)
    alice = Serveur(le_pic, le_bar, les_clients, name="alice", verbose=config["alice"]["verbose"], delai=config["alice"]["delai"])
    clara = Serveur(le_pic, le_bar, les_clients, name="clara", verbose=config["clara"]["verbose"], delai=config["clara"]["delai"])

    await asyncio.gather(
        alice.prendre_commandes(),
        clara.prendre_commandes(),
        bob.preparer(),
        bob.servir_si_possible(),
        alice.servir(),
        clara.servir()
    )
        
    fin = time.time()
    
    # --- RAPPORT AVEC RICH ---
    table = Table(title="🏁 RAPPORT DE FIN DE SERVICE (ASYNCHRONE)")
    table.add_column("Employé", style="cyan")
    table.add_column("Cocktails Traités", style="magenta")
    table.add_column("Commandes Traitées", style="green")

    table.add_row("Bob (Bariste)", str(bob.cocktails_traites), str(bob.commandes_traitees))
    table.add_row("Alice (Serveur)", str(alice.cocktails_traites), str(alice.commandes_traitees))
    table.add_row("Clara (Serveur)", str(clara.cocktails_traites), str(clara.commandes_traitees))

    console.print(table)
    console.print(Panel(f"⏱️ Temps total d'exécution : {fin - debut:.2f} secondes", style="bold yellow"))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Simulation asynchrone d'un bar à cocktails.")
    parser.add_argument("fichier", help="Le fichier contenant les commandes (ex: commandes/mardi)")
    args = parser.parse_args()
    
    asyncio.run(main_async(args.fichier))