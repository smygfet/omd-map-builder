# Fingerprint of the app's source files on the PC: the exe stores the value it was built from, and rebuilds itself
# when the files on disk no longer match (see app.py: self update).
import hashlib, os

ROOT = os.path.join(os.path.expanduser("~"), "Documents", "Claud OMD")
SRC = os.path.join(ROOT, "tools", "exe_src")
MB = os.path.join(ROOT, "tools", "mapbuild")
FILES = [os.path.join(SRC, f) for f in ("app.py", "builder.py", "srchash.py", "build_exe.py", "mapmaker.html")] + \
        [os.path.join(MB, f) for f in ("mapv2.py", "tilepng.py", "geowriter.py", "hideactors.py", "ue53pkg.py", "ue53rename.py",
                                        "arpatch.py", "cityhash64.py", "boxes2tris.py", "prune.py", "deathtrapify.py",
                                        "patch_plaza2.py", "castleplaza_actors.json", "colosseum_actors.json", "arboretum_actors.json", "bases.py", "findloc.py", "dupactors.py", "JWVersus_main.lua", "envdeco.py", "props.py", "onslaughtloop.py", "friendpack.py", "JWBarricades_main.lua")]


def source_hash():
    h = hashlib.sha1()
    for f in FILES:
        h.update(os.path.basename(f).encode())
        try: h.update(open(f, "rb").read().replace(b"\r\n", b"\n"))
        except OSError: h.update(b"-")
    return h.hexdigest()[:16]
