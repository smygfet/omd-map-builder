# Copies the archer mod's log (and the UE4SS log tail) to notes\archer_log.txt. Read-only.
import os
ROOT = os.path.join(os.path.expanduser("~"), "Documents", "Claud OMD")
BIN = r"C:\Program Files (x86)\Steam\steamapps\common\Orcs Must Die Deathtrap\OMDD\Binaries\Win64"
out = []
for n, tail in (("JW_ArcherAuto.txt", 0), (os.path.join("ue4ss", "UE4SS.log"), 300), ("UE4SS.log", 300)):
    p = os.path.join(BIN, n)
    if not os.path.exists(p): out.append("== %s: missing" % n); continue
    t = open(p, encoding="utf-8", errors="replace").read().splitlines()
    if tail:
        t = [l for l in t if "ArcherAuto" in l or "JWArcher" in l or "error" in l.lower()][-tail:]
    out.append("== %s (%d lines)" % (n, len(t))); out += t
open(os.path.join(ROOT, "notes", "archer_log.txt"), "w", encoding="utf-8").write("\n".join(out))
