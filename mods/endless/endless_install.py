# Installs Endless mode for the game's own missions: zz_JWEndless_P (looped wave scripts) into Paks\Mods and the
# UE4SS helper JWEndless (harder every wave). Waits while the game is running. Log: notes\endless_install.txt
import os, shutil, subprocess, time
ROOT = os.path.join(os.path.expanduser("~"), "Documents", "Claud OMD")
HERE = os.path.join(ROOT, "tools", "endless")
GAME = r"C:\Program Files (x86)\Steam\steamapps\common\Orcs Must Die Deathtrap\OMDD"
MODS = os.path.join(GAME, "Content", "Paks", "Mods")
UE = os.path.join(GAME, "Binaries", "Win64", "Mods", "JWEndless")
log = open(os.path.join(ROOT, "notes", "endless_install.txt"), "w", encoding="utf-8")
def p(m): log.write(time.strftime("%H:%M:%S ") + m + "\n"); log.flush()
def game_running():
    out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq OMDDSteam-Win64-Shipping.exe"], capture_output=True, text=True,
                         creationflags=0x08000000).stdout
    return "OMDDSteam-Win64-Shipping.exe" in out
t0 = time.time()
while game_running():
    if time.time() - t0 < 5: p("game is running: waiting until it is closed")
    time.sleep(5)
for e in (".pak", ".utoc", ".ucas"):
    shutil.copyfile(os.path.join(HERE, "zz_JWEndless_P" + e), os.path.join(MODS, "zz_JWEndless_P" + e)); p("installed zz_JWEndless_P" + e)
os.makedirs(os.path.join(UE, "Scripts"), exist_ok=True)
shutil.copyfile(os.path.join(HERE, "JWEndless", "Scripts", "main.lua"), os.path.join(UE, "Scripts", "main.lua"))
if not os.path.exists(os.path.join(UE, "enabled.off")):
    open(os.path.join(UE, "enabled.txt"), "w").close()
p("installed UE4SS mod JWEndless"); p("DONE")
