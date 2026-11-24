# Installs the JWTrapBarricade test mod (UE4SS). Separate from the OMD Map Builder app and its mods.
# Log: notes\trapbarr_install.txt. Remove: delete Binaries\Win64\Mods\JWTrapBarricade
import os, shutil, time
ROOT = os.path.join(os.path.expanduser("~"), "Documents", "Claud OMD")
SRC = os.path.join(ROOT, "tools", "trapbarricade", "JWTrapBarricade")
DST = r"C:\Program Files (x86)\Steam\steamapps\common\Orcs Must Die Deathtrap\OMDD\Binaries\Win64\Mods\JWTrapBarricade"
os.makedirs(os.path.join(DST, "Scripts"), exist_ok=True)
shutil.copyfile(os.path.join(SRC, "Scripts", "main.lua"), os.path.join(DST, "Scripts", "main.lua"))
shutil.copyfile(os.path.join(SRC, "enabled.txt"), os.path.join(DST, "enabled.txt"))
open(os.path.join(ROOT, "notes", "trapbarr_install.txt"), "w").write(time.strftime("%H:%M:%S ") + "installed to " + DST + "\nDONE\n")
