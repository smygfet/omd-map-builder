# Builds the Guardian Archer trap packages (legacy cooked) from the Tar Trap's definition and inventory item, plus
# (v2, 2026-11-17) its own icon /Game/Traps/GuardianArcher/ICON_GuardianArcher: OMD3's Guardian Archer (picture from
# the user: icon_src.png, transparent background), in the same texture format as a
# trap icon (512x512 DXT5; mips 512/256/128 in the .ubulk, 64..1 inline), built on ICON_Barricade's package.
import hashlib, os, struct, sys
import etcpak
from PIL import Image
sys.path.insert(0, "/home/claude/omd/builder")
import ue53rename as RN
HERE = os.path.dirname(os.path.abspath(__file__))
SRC = "/mnt/user-data/uploads/Claud OMD/notes/trap_extract2/OMDD~Content~Traps~TarTrap~BP~"
ICO = "/mnt/user-data/uploads/Claud OMD/notes/tbicon_extract/OMDD~Content~Traps~Barricade~UI~ICON_Barricade"
ZEN = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "zen_in")
OUT = os.path.join(ZEN, "OMDD/Content/Traps/GuardianArcher")
DIR = "/Game/Traps/GuardianArcher"
DEF, ITEM, ICON = "DA_GuardianArcher_Definition", "DA_GuardianArcher_InventoryItem", "ICON_GuardianArcher"
TAG = "Item.Identifier.Trap.GravityPillar"       # registered but unused (OMD3's cut Gravity Pillar)
COST = 1800       # shows as 1400 in game
os.makedirs(OUT, exist_ok=True)
rd = lambda n: (open(SRC + n + ".uasset", "rb").read(), open(SRC + n + ".uexp", "rb").read())
def key(s): return hashlib.md5(s.encode()).hexdigest().upper()

# --- definition ---
h, x = rd("DA_TarTrap_Definition")
e0 = bytes.fromhex("00000000 00000000 03000000 00000000 00000000".replace(" ", ""))   # DA_TrapBase_AbilitySet
e1 = bytes.fromhex("01000000 00000000 02000000 00000000 00000000".replace(" ", ""))   # DA_TarTrap_AbilitySet
edits = {1: [(struct.pack("<i", 2) + e0 + e1, struct.pack("<i", 1) + e0),
             (struct.pack("<i", 800) + b"\x01", struct.pack("<i", COST) + b"\x01")]}
h2, x2 = RN.rewrite(h, x, renames={"Gameplay.Property.Trap.TarTrap": "Gameplay.Property.Trap.Sentinel",
                                   "/Game/Traps/TarTrap/BP/DA_TarTrap_Definition": DIR + "/" + DEF, "DA_TarTrap_Definition": DEF},
                    package_name=DIR + "/" + DEF, export_edits=edits)
open(os.path.join(OUT, DEF + ".uasset"), "wb").write(h2); open(os.path.join(OUT, DEF + ".uexp"), "wb").write(x2)

# --- inventory item (icon: our own) ---
h, x = rd("DA_TarTrap_InventoryItem")
name, desc = "Guardian Archer", "Summons an elf archer who shoots enemies from afar, flyers too."
edits = {3: [(b"8C375F5A45AAFB51E09BF28148DF244B", key("GuardianArcher:name").encode()),
             (RN.fstring("Tar Trap"), RN.fstring(name)),
             (b"346713A64F7C7F38991FA2B753493D99", key("GuardianArcher:desc").encode()),
             (RN.fstring("Enemies are slowed while on it."), RN.fstring(desc)),
             (struct.pack("<i", 3) + struct.pack("<3i", -18, -19, -17), struct.pack("<i", 0))]}     # no Tar Trap upgrades
ren = {"/Game/Traps/TarTrap/BP/BP_TarTrap": "/Game/Traps/Sentinel_Archer/BP/BP_Sentinel_Archer_Trap", "BP_TarTrap_C": "BP_Sentinel_Archer_Trap_C",
       "/Game/Traps/TarTrap/BP/DA_TarTrap_Definition": DIR + "/" + DEF, "DA_TarTrap_Definition": DEF,
       "Item.Identifier.Trap.TarTrap": TAG,
       "/Game/Traps/TarTrap/UI/ICON_TarTrap": DIR + "/" + ICON, "ICON_TarTrap": ICON,
       "/Game/Traps/TarTrap/BP/DA_TarTrap_InventoryItem": DIR + "/" + ITEM, "DA_TarTrap_InventoryItem": ITEM}
h2, x2 = RN.rewrite(h, x, renames=ren, package_name=DIR + "/" + ITEM, export_edits=edits)
open(os.path.join(OUT, ITEM + ".uasset"), "wb").write(h2); open(os.path.join(OUT, ITEM + ".uexp"), "wb").write(x2)

# --- icon ---
cut = Image.open(os.path.join(HERE, "icon_src.png")).convert("RGBA")
cut = cut.crop(cut.split()[3].getbbox())
sc = 500 / max(cut.size); cut = cut.resize((round(cut.width * sc), round(cut.height * sc)), Image.LANCZOS)
src = Image.new("RGBA", (512, 512), (0, 0, 0, 0)); src.paste(cut, ((512 - cut.width) // 2, (512 - cut.height) // 2), cut)
src.save(os.path.join(HERE, "ICON_GuardianArcher.png"))
ih = open(ICO + ".uasset", "rb").read(); ix = bytearray(open(ICO + ".uexp", "rb").read()); ib = open(ICO + ".ubulk", "rb").read()
def enc(w):
    im = src.resize((max(w, 4), max(w, 4)), Image.LANCZOS)
    return etcpak.compress_bc3(im.tobytes("raw", "RGBA"), im.width, im.height)
nb = enc(512) + enc(256) + enc(128); assert len(nb) == len(ib)
pos = {}
for k in range(150, len(ix) - 12):
    w, hh, d = struct.unpack_from("<3i", ix, k)
    if w in (64, 32, 16, 8, 4, 2, 1) and w == hh and d == 1 and w not in pos: pos[w] = k
assert sorted(pos) == [1, 2, 4, 8, 16, 32, 64], pos
for w, k in pos.items():
    n = max(w // 4, 1) ** 2 * 16
    ix[k - n:k] = enc(w)[:n]
nh, nx = RN.rewrite(ih, bytes(ix), renames={"/Game/Traps/Barricade/UI/ICON_Barricade": DIR + "/" + ICON, "ICON_Barricade": ICON},
                    package_name=DIR + "/" + ICON)
for ext, data in ((".uasset", nh), (".uexp", nx), (".ubulk", nb)):
    open(os.path.join(OUT, ICON + ext), "wb").write(data)
print("ok")
