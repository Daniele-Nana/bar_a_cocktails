import pytest
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from borabora_async import Pic, Bar, Clients

# ==========================================
# TESTS DU PIC (ASYNCHRONE)
# ==========================================
@pytest.mark.asyncio
async def test_pic_async_fifo():
    """Vérifie que la file asyncio.Queue du Pic respecte le FIFO."""
    p = Pic(name="test", verbose=False)
    await p.embrocher(["A"])
    await p.embrocher(["B"])
    assert await p.liberer() == ["A"]
    assert await p.liberer() == ["B"]

# ==========================================
# TESTS DU BAR (ASYNCHRONE)
# ==========================================
@pytest.mark.asyncio
async def test_bar_async_fifo():
    """Vérifie que la file asyncio.Queue du Bar respecte le FIFO."""
    b = Bar(name="test", verbose=False)
    await b.recevoir(["X"])
    await b.recevoir(["Y"])
    assert await b.evacuer() == ["X"]
    assert await b.evacuer() == ["Y"]

# ==========================================
# TESTS DES CLIENTS (ASYNCHRONE)
# ==========================================
@pytest.mark.asyncio
async def test_clients_async_lecture(tmp_path):
    """Vérifie la lecture asynchrone du fichier."""
    fichier = tmp_path / "test_async.txt"
    fichier.write_text("0 mojito\n")
    c = Clients(str(fichier))
    assert await c.commande() == ["mojito"]
    assert await c.commande() is None