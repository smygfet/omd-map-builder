import os, shutil
ROOT = os.path.join(os.path.expanduser("~"), "Documents", "Claud OMD")
SRC = os.path.join(ROOT, "tools", "trap", "JWArcherGrant")
DST = r"C:\Program Files (x86)\Steam\steamapps\common\Orcs Must Die Deathtrap\OMDD\Binaries\Win64\Mods\JWArcherGrant"
os.makedirs(os.path.join(DST, "Scripts"), exist_ok=True)
shutil.copyfile(os.path.join(SRC, "main.lua"), os.path.join(DST, "Scripts", "main.lua"))
shutil.copyfile(os.path.join(SRC, "enabled.txt"), os.path.join(DST, "enabled.txt"))
open(os.path.join(ROOT, "notes", "grant_install.txt"), "w").write("installed to " + DST)
