# Read-only: copy the barricade icons (with their image data) out of the game paks into notes\tbicon_extract.
import os, shutil, subprocess
ROOT = os.path.join(os.path.expanduser("~"), "Documents", "Claud OMD")
PAKS = r"C:\Program Files (x86)\Steam\steamapps\common\Orcs Must Die Deathtrap\OMDD\Content\Paks"
RETOC = os.path.join(ROOT, "tools", "retoc.exe")
OUT = os.path.join(ROOT, "extracted_tbicon"); FLAT = os.path.join(ROOT, "notes", "tbicon_extract")
shutil.rmtree(OUT, ignore_errors=True); shutil.rmtree(FLAT, ignore_errors=True); os.makedirs(FLAT)
args = [RETOC, "to-legacy", "--no-shaders", "--version", "UE5_3", "--filter", "Content/Traps/Barricade/UI/", PAKS, OUT]
with open(os.path.join(FLAT, "retoc.txt"), "w", encoding="utf-8", errors="replace") as f:
    p = subprocess.run(args, stdout=f, stderr=subprocess.STDOUT)
names = []
for root, _, files in os.walk(OUT):
    for fn in files:
        full = os.path.join(root, fn); rel = os.path.relpath(full, OUT).replace(os.sep, "~")
        shutil.copyfile(full, os.path.join(FLAT, rel)); names.append("%s %d" % (rel, os.path.getsize(full)))
open(os.path.join(FLAT, "done.txt"), "w").write("exit %d\n%s" % (p.returncode, "\n".join(sorted(names))))
