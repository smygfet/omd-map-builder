# Builds the Giant Flip Trap as its own trap in the trap book (v2). The game already has the whole trap
# (BP_FlipTrap_Big: 2x2 model, animations, flip ability); normally you only get it from the "Bigger Stronger Flippers"
# Thread.
#   DA_GiantFlip_InventoryItem  <- DA_TarTrap_InventoryItem: the Tar Trap's item is PURCHASABLE (the Flip Trap's is not,
#                                  so v1, built on it, never showed in the trap book). Places BP_FlipTrap_Big, own
#                                  name/text, own identifier tag, Giant Flip icon, no Tar Trap upgrades.
#   DA_GiantFlip_Definition     <- DA_FlipTrap_Big_Definition, with its OWN identifier Gameplay.Property.Trap.JWGiantFlip
#                                  (a trap definition's primary asset id is its identifier; the Big one shares the
#                                  Flip Trap's), price 1600
#   DA_FlipTrap_Big_Definition  <- the game's own, price 800 -> 1600 (the placed BP_FlipTrap_Big uses it)
# plus Config/Tags/JWGiantFlip.ini (registers both tags).
# Usage: make_giantflip.py <out zen_in dir> <out ini dir>
import os, struct, sys, hashlib
sys.path.insert(0, "/home/claude/endless/lib")
import ue53rename as RN
X = "/mnt/user-data/uploads/Claud OMD/notes/giantflip_extract/OMDD~Content~Traps~FlipTrap~BP~"
T = "/mnt/user-data/uploads/Claud OMD/notes/trap_extract2/OMDD~Content~Traps~TarTrap~BP~"
ZEN = sys.argv[1]; INI = sys.argv[2]
DIR = "/Game/Traps/GiantFlip"; ITEM = "DA_GiantFlip_InventoryItem"; DEF = "DA_GiantFlip_Definition"
TAG = "Item.Identifier.Trap.JWGiantFlip"; DEFTAG = "Gameplay.Property.Trap.JWGiantFlip"
COST = 1600
NAME = "Giant Flip Trap"
DESC = "A huge 2x2 Flip Trap from the war machines. Launches enemies much farther than the normal Flip Trap. (Physics Trap)"
rd = lambda p: (open(p + ".uasset", "rb").read(), open(p + ".uexp", "rb").read())
key = lambda s: hashlib.md5(s.encode()).hexdigest().upper().encode()
def wr(sub, n, hx):
    d = os.path.join(ZEN, "OMDD/Content", sub); os.makedirs(d, exist_ok=True)
    open(os.path.join(d, n + ".uasset"), "wb").write(hx[0]); open(os.path.join(d, n + ".uexp"), "wb").write(hx[1]); print("wrote", sub, n)
old_cost = struct.pack("<i", 800) + b"\x01"; new_cost = struct.pack("<i", COST) + b"\x01"

# item: the Tar Trap's (purchasable) item, as the working Trap Barricade and Guardian Archer
h, x = rd(T + "DA_TarTrap_InventoryItem")
edits = {3: [(b"8C375F5A45AAFB51E09BF28148DF244B", key("JWGiantFlip:name")), (RN.fstring("Tar Trap"), RN.fstring(NAME)),
             (b"346713A64F7C7F38991FA2B753493D99", key("JWGiantFlip:desc")),
             (RN.fstring("Enemies are slowed while on it."), RN.fstring(DESC)),
             (struct.pack("<i", 3) + struct.pack("<3i", -18, -19, -17), struct.pack("<i", 0))]}          # no Tar Trap upgrades
wr("Traps/GiantFlip", ITEM, RN.rewrite(h, x, renames={
        "/Game/Traps/TarTrap/BP/BP_TarTrap": "/Game/Traps/FlipTrap/BP/BP_FlipTrap_Big", "BP_TarTrap_C": "BP_FlipTrap_Big_C",
        "/Game/Traps/TarTrap/BP/DA_TarTrap_Definition": DIR + "/" + DEF, "DA_TarTrap_Definition": DEF,
        "Item.Identifier.Trap.TarTrap": TAG,
        "/Game/Traps/TarTrap/UI/ICON_TarTrap": "/Game/Traps/FlipTrap/UI/ICON_FlipTrap_Big", "ICON_TarTrap": "ICON_FlipTrap_Big",
        "/Game/Traps/TarTrap/BP/DA_TarTrap_InventoryItem": DIR + "/" + ITEM, "DA_TarTrap_InventoryItem": ITEM},
    package_name=DIR + "/" + ITEM, export_edits=edits))

# our own definition: the Big one with its own identifier and price
h, x = rd(X + "DA_FlipTrap_Big_Definition")
assert x.count(old_cost) == 1
wr("Traps/GiantFlip", DEF, RN.rewrite(h, x, renames={
        "Gameplay.Property.Trap.FlipTrap": DEFTAG,
        "/Game/Traps/FlipTrap/BP/DA_FlipTrap_Big_Definition": DIR + "/" + DEF, "DA_FlipTrap_Big_Definition": DEF},
    package_name=DIR + "/" + DEF, export_edits={1: [(old_cost, new_cost)]}))

# the game's Big definition (used by the placed trap): price
h, x = rd(X + "DA_FlipTrap_Big_Definition")
wr("Traps/FlipTrap/BP", "DA_FlipTrap_Big_Definition", RN.rewrite(h, x, export_edits={1: [(old_cost, new_cost)]}))

d = os.path.join(INI, "OMDD", "Config", "Tags"); os.makedirs(d, exist_ok=True)
open(os.path.join(d, "JWGiantFlip.ini"), "w", newline="\r\n").write(
    "[/Script/GameplayTags.GameplayTagsList]\n"
    "GameplayTagList=(Tag=\"%s\",DevComment=\"Giant Flip Trap mod\")\n"
    "GameplayTagList=(Tag=\"%s\",DevComment=\"Giant Flip Trap mod\")\n" % (TAG, DEFTAG))
print("ok")
