# Copies tools\trap\JWArcherAuto\main.lua into the game's UE4SS mod (enabled.txt / enabled.off untouched).
# The game loads it at its next start. Log: notes\archer_lua.txt
import os, shutil, time
ROOT = os.path.join(os.path.expanduser("~"), "Documents", "Claud OMD")
UE = r"C:\Program Files (x86)\Steam\steamapps\common\Orcs Must Die Deathtrap\OMDD\Binaries\Win64\Mods\JWArcherAuto"
os.makedirs(os.path.join(UE, "Scripts"), exist_ok=True)
shutil.copyfile(os.path.join(ROOT, "tools", "trap", "JWArcherAuto", "main.lua"), os.path.join(UE, "Scripts", "main.lua"))
first = open(os.path.join(UE, "Scripts", "main.lua"), encoding="utf-8").readline().strip()
open(os.path.join(ROOT, "notes", "archer_lua.txt"), "w").write(time.strftime("%H:%M:%S ") + "installed: " + first + "\n")
