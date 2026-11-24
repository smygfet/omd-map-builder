# Endless settings update: the new JWEndless script (reads Mods\JWEndless\settings.txt) and the original wave scripts
# kept in tools\endless\originals (the app rebuilds the pak from them when the last wave changes).
# Log: notes\endless_install2.txt
import os, shutil, time
ROOT = os.path.join(os.path.expanduser("~"), "Documents", "Claud OMD")
HERE = os.path.join(ROOT, "tools", "endless")
UE = r"C:\Program Files (x86)\Steam\steamapps\common\Orcs Must Die Deathtrap\OMDD\Binaries\Win64\Mods\JWEndless"
log = open(os.path.join(ROOT, "notes", "endless_install2.txt"), "w", encoding="utf-8")
def p(m): log.write(time.strftime("%H:%M:%S ") + m + "\n"); log.flush()
src = os.path.join(ROOT, "notes", "endless_extract"); dst = os.path.join(HERE, "originals"); os.makedirs(dst, exist_ok=True)
n = 0
for fn in os.listdir(src):
    if fn.endswith((".uasset", ".uexp")): shutil.copyfile(os.path.join(src, fn), os.path.join(dst, fn)); n += 1
p("originals: %d files" % n)
os.makedirs(os.path.join(UE, "Scripts"), exist_ok=True)
shutil.copyfile(os.path.join(HERE, "JWEndless", "Scripts", "main.lua"), os.path.join(UE, "Scripts", "main.lua"))
p("JWEndless script updated (takes effect at the next game start)"); p("DONE")
