import sys
import os
import pytest
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from borabora_sync import Pic, Bar, Clients

# ==========================================
# TESTS DU PIC (SYNCHRONE)
# ==========================================
def test_pic_est_vide_au_depart():
    p = Pic()
    assert p.liberer() is None

def test_pic_fifo():
    """Vérifie que le Pic respecte le FIFO."""
    p = Pic()
    p.embrocher(["A"])
    p.embrocher(["B"])
    p.embrocher(["C"])
    assert p.liberer() == ["A"]
    assert p.liberer() == ["B"]
    assert p.liberer() == ["C"]

# ==========================================
# TESTS DU BAR (SYNCHRONE)
# ==========================================
def test_bar_fifo():
    """Vérifie que le Bar respecte le FIFO."""
    b = Bar()
    b.recevoir(["X"])
    b.recevoir(["Y"])
    assert b.evacuer() == ["X"]
    assert b.evacuer() == ["Y"]
    assert b.evacuer() is None

# ==========================================
# TESTS DES CLIENTS (SYNCHRONE)
# ==========================================
def test_clients_lecture_valide(tmp_path):
    """Vérifie la lecture correcte d'un fichier."""
    fichier = tmp_path / "test_commandes.txt"
    fichier.write_text("0 mojito,margarita\n0 daiquiri\n")
    c = Clients(str(fichier))
    assert c.commande() == ["mojito", "margarita"]
    assert c.commande() == ["daiquiri"]
    assert c.commande() is None

def test_clients_fichier_introuvable():
    """Vérifie que le programme quitte proprement si le fichier n'existe pas."""
    with pytest.raises(SystemExit) as excinfo:
        Clients("fichier_inexistant.txt")
    assert excinfo.value.code == 1

def test_clients_ligne_incorrecte(tmp_path, capsys):
    """Vérifie que les lignes mal formatées sont ignorées avec un avertissement."""
    fichier = tmp_path / "test_erreur.txt"
    fichier.write_text("0 bon_format\nmauvais_format_sans_delai\n")
    c = Clients(str(fichier))
    # On vérifie que le message d'avertissement a bien été affiché
    captured = capsys.readouterr()
    assert "⚠️ Ligne ignorée" in captured.out
    # On vérifie que seule la bonne commande a été gardée
    assert c.commande() == ["bon_format"]