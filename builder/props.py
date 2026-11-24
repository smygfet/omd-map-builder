# Props for Map Maker cells ("p" = prop id, "pr" = quarter turns 0-3). A prop stands on a floor cell and blocks it
# (orcs walk around it, no floor traps there). Sizes from the game's cooked meshes (render bounds, cm, relative to
# the pivot), read by tools\prop_bounds.py. Each prop is one or more pieces inside the 3 x 3 m cell.
import math

E = '/Game/Environments/'
AO, PO, LS = E + 'Arch_Order/', E + 'Props_Order/', E + 'LandScapes/'
KD = PO + 'Kitchen_Dining/'
M = {  # key: (path, min, max)
    'barrel':    ('/Game/Environments/Props_Order/Kitchen_Dining/Barrels/Mesh/Barrel_Closed_Barrel_Closed', (-44.0, -44.1, -3.3), (44.1, 44.2, 94.5)),
    'barrelr':   ('/Game/Environments/Props_Order/Kitchen_Dining/Barrels/Mesh/BarrelRopes_Closed_BarrelRopes_Closed', (-47.1, -49.3, -1.8), (47.4, 48.5, 95.0)),
    'barrelo':   ('/Game/Environments/Props_Order/Kitchen_Dining/Barrels/Mesh/Barrel_Open_Barrel_Open', (-44.0, -44.1, -3.3), (44.1, 44.2, 94.5)),
    'keg':       ('/Game/Environments/Props_Order/Kitchen_Dining/Beer/Mesh/BeerKeg_BeerKeg', (-46.2, -45.3, -0.3), (46.7, 66.9, 78.1)),
    'crateL':    ('/Game/Environments/Props_Order/Kitchen_Dining/Crates/Mesh/CrateLarge_Order_CrateLarge', (-64.0, -32.0, 0.0), (64.0, 32.0, 64.0)),
    'crateS':    ('/Game/Environments/Props_Order/Kitchen_Dining/Crates/Mesh/CrateSmall_Order_CrateSmall', (-32.0, -32.0, -1.3), (32.0, 32.0, 64.0)),
    'sack':      ('/Game/Environments/Props_Order/Kitchen_Dining/Sacks/Mesh/Sack', (-30.2, -15.1, 0.0), (30.1, 15.1, 74.1)),
    'mtable':    ('/Game/Environments/Props_Order/Kitchen_Dining/FoodStuffs/Mesh/MerchantTable_SquareTop_SM', (-31.1, -32.0, -0.7), (31.1, 32.0, 32.5)),
    'apples':    ('/Game/Environments/Props_Order/Kitchen_Dining/FoodStuffs/Mesh/Apple_Red_TableSquare_SM', (-31.1, -39.0, -0.6), (31.1, 40.0, 77.6)),
    'bread':     ('/Game/Environments/Props_Order/Kitchen_Dining/FoodStuffs/Mesh/BreadLoafs_TableRound_SM', (-40.0, -51.6, -1.8), (41.8, 38.4, 62.1)),
    'fish':      ('/Game/Environments/Props_Order/Kitchen_Dining/FoodStuffs/Mesh/FishTable_SM', (-40.0, -41.1, -1.8), (41.8, 38.4, 66.7)),
    'ctable':    ('/Game/Environments/Props_Order/Kitchen_Dining/Furniture_Table_Crafting_Wood/Mesh/SM_Furniture_Table_Crafting_Wood', (-156.4, -74.8, -0.2), (154.7, 74.5, 99.6)),
    'king':      ('/Game/Environments/Props_Order/Kitchen_Dining/BanquetChair/Mesh/KingChair_KingChair', (-51.1, -48.4, -0.1), (51.1, 48.6, 213.3)),
    'chest':     (PO + 'Chest/Mesh/Chest_Generic_01', (-46.4, -37.4, -2.5), (46.4, 48.5, 88.6)),
    'anvil':     ('/Game/Environments/Props_Order/Forge/Blacksmith/Mesh/Hub_BlackSmith_Anvil_01', (-49.6, -72.8, 0.3), (51.9, 65.6, 94.8)),
    'bigrack':   ('/Game/Environments/Props_Order/Forge/ToolStorage/Mesh/Wood_LargeRack_01', (-179.7, -125.9, -2.0), (179.7, 125.9, 441.3)),
    'toolrack':  ('/Game/Environments/Props_Order/Forge/ToolStorage/Mesh/Wood_ToolRack_01', (-131.8, -48.4, -3.3), (131.8, 48.4, 210.1)),
    'brazier':   ('/Game/Environments/Props_Order/General_Lighting/Brazier_Large/Mesh/Lighting_Brazier_Large_Stand_SM', (-75.4, -75.4, 0.0), (75.4, 75.4, 113.3)),
    'torch':     ('/Game/Environments/Props_Order/General_Lighting/Torch_Wall/Mesh/Lighting_Torch_Wood_FreeStand', (-28.5, -26.8, -11.1), (28.5, 28.8, 135.1)),
    'glamp':     ('/Game/Environments/Props_Order/General_Lighting/Lampposts/Mesh/Garden_Lamppost_A', (-128.3, -130.3, -0.3), (130.6, 117.8, 593.3)),
    'clamp':     ('/Game/Environments/Props_Order/General_Lighting/Lampposts/Mesh/Castle_Lamppost_A', (-182.3, -39.8, 0.0), (179.4, 40.6, 720.7)),
    'cauldron':  (PO + 'Chemistry/Mesh/ChemistryKit_Cauldron_01', (-180.8, -179.5, -3.4), (180.8, 179.5, 326.6)),
    'fountain':  (AO + 'MetalWork/Fountain/Mesh/Hero_Fountain_A_SM', (-425.5, -428.2, -7.1), (427.3, 424.6, 1091.7)),
    'hogarth':   (PO + 'Library/Statue_Hero_Hogarth/Mesh/Statue_Hero_Hogarth_SM', (-148.6, -89.7, -3.7), (123.6, 121.0, 329.6)),
    'apprentice': (PO + 'Library/Statue_Hero_Apprentice/Mesh/Statue_Hero_Apprentice_SM', (-79.1, -39.0, -1.0), (37.7, 30.1, 236.3)),
    'mermaid':   (AO + 'Resort/Mesh/Statue_Mermaid_SM', (-444.6, -416.1, -0.8), (359.1, 271.8, 825.0)),
    'orcstatue': (PO + 'Library/Statue_CygnusVorwick/Mesh/Statue_Orcs', (-202.5, -239.6, -51.3), (147.4, 338.0, 146.6)),
    'bench':     (AO + 'MetalWork/Mesh/Bench_Gardens_Iron_A', (-153.2, -52.8, 0.3), (153.2, 48.5, 159.0)),
    'planter':   (AO + 'Planters/Castle/Mesh/Planter_Castle_1x1x1_SM', (-150.0, -150.0, 0.0), (150.0, 150.0, 245.0)),
    'pot':       (AO + 'Planters/Garden/Mesh/Planter_Gardens_Stone_A', (-38.9, -38.3, -2.4), (38.9, 38.3, 65.8)),
    'fernbox':   (LS + 'Foliage/Plant/Flowers/Mesh/Plants_FernBox_01_high_SM', (-85.3, -44.3, -1.9), (88.0, 32.6, 50.7)),
    'fern':      (LS + 'Foliage/Plant/Fern/Mesh/Plant_Jungle_Fern_01_High_SM', (-150.7, -163.1, -0.4), (145.3, 127.9, 65.3)),
    'pillar':    (AO + 'Colosseum/Mesh/Colosseum_Arena_Pillar_A_SM', (-121.6, -119.9, -25.0), (123.5, 124.6, 1696.2)),
    'orcpillar': (E + 'Arch_Enemy/Orc_Wood/Mesh/ORC_WoodPillar', (-62.6, -68.0, -159.2), (62.6, 68.0, 159.2)),
    'bookcart':  (AO + 'Hub/Library/Props/Mesh/Hub_Library_BookCart_01', (-49.6, -90.7, -2.2), (49.6, 90.7, 196.0)),
    'anchor':    ('/Game/Environments/Props_Order/Docks/Ship_Fishing/Mesh/Ship_FishingShipA_Anchor_SM', (-39.5, -123.4, -66.2), (119.4, 142.1, 404.1)),
    'rockpile':  (AO + 'Courtyard/Mesh/Courtyard_Rock_Pile_B_SM', (-304.5, -283.4, -1.8), (304.5, 283.4, 201.8)),
    'mtent':     (LS + '3rdParty/Medieval_Village/Meshes/props/SM_market_tent_01', (-225.0, -151.0, 0.0), (225.0, 151.0, 400.0)),
    'otbase':    (E + 'Arch_Enemy/Tents/Mesh/Orc_Tent_Base_02_SM', (-727.1, -636.0, -105.1), (727.1, 652.8, 366.1)),
    'ottop':     (E + 'Arch_Enemy/Tents/Mesh/Orc_Tent_Top_02_SM', (-745.2, -691.8, 208.5), (745.2, 619.4, 817.6)),
    'hay':       (PO + 'TrainingGround/Mesh/TraningGrounds_HayBales_01', (-74.7, -151.3, -9.3), (74.7, 148.7, 143.0)),
    'cart':      (LS + '3rdParty/DreamscapeSeries/DreamscapeMountains/Meshes/props/Objects/SM_Cart', (-96.9, -154.3, 0.4), (96.8, 174.3, 147.9)),
    'fence':     (LS + '3rdParty/DreamscapeSeries/DreamscapeTower/Meshes/Structures/SM_Fence_01', (-170.6, -8.8, -4.7), (170.7, 8.8, 118.5)),
    'boulder':   (LS + 'Geology/rock/Mesh/Rock_G_SM', (-189.3, -160.0, -175.8), (184.5, 160.0, 175.8)),
}
# prop id -> pieces: (mesh key, x, y (cm from the cell middle, before turning), yaw, scale (number or (sx, sy, sz)), z on top of)
PROPS = {
    'barrels':   [('barrel', -55, -45, 0, 1.3), ('barrelr', 60, -35, 40, 1.3), ('barrelo', 0, 65, 15, 1.3)],
    'barrel':    [('barrel', 0, 0, 0, 1.8)],
    'crates':    [('crateL', -40, -50, 0, 1.6), ('crateS', -40, -50, 0, 1.4, 102), ('crateS', 70, 60, 20, 1.6), ('crateL', -30, 70, 90, 1.3)],
    'kegs':      [('keg', -50, 0, 90, 1.5), ('sack', 70, -60, 30, 1.6), ('sack', 70, 60, -20, 1.6)],
    'sacks':     [('sack', -50, -40, 10, 1.7), ('sack', 50, -30, -25, 1.7), ('sack', 0, 50, 80, 1.7)],
    'chest':     [('chest', 0, 0, 0, 1.6)],
    'forge':     [('toolrack', 0, -110, 0, 1.0), ('anvil', 0, 40, 90, 1.5)],
    'rack':      [('bigrack', 0, 0, 0, 0.78)],
    'table':     [('ctable', 0, 0, 0, 0.9)],
    'market':    [('mtable', -70, -60, 0, 2.0), ('apples', 70, -60, 0, 1.5), ('bread', -65, 70, 0, 1.4), ('fish', 70, 70, 0, 1.4)],
    'throne':    [('king', 0, 0, 0, 1.4)],
    'brazier':   [('brazier', 0, 0, 0, 1.6)],
    'torches':   [('torch', -80, 0, 0, 1.6), ('torch', 80, 0, 0, 1.6)],
    'gardenlamp': [('glamp', 0, 0, 0, 1.0)],
    'castlelamp': [('clamp', 0, 0, 0, 0.76)],
    'cauldron':  [('cauldron', 0, 0, 0, 0.78)],
    'fountain':  [('fountain', 0, 0, 0, 0.33)],
    'hogarth':   [('hogarth', 0, 0, 0, 1.0)],
    'apprentice': [('apprentice', 0, 0, 0, 1.5)],
    'mermaid':   [('mermaid', 0, 0, 0, 0.36)],
    'orcstatue': [('orcstatue', 0, 0, 0, 0.5)],
    'bench':     [('bench', 0, 0, 0, 0.92)],
    'planter':   [('planter', 0, 0, 0, 0.98)],
    'pots':      [('pot', -60, -60, 0, 1.4), ('fernbox', 40, 50, 0, 1.3), ('pot', 70, -50, 0, 1.2)],
    'ferns':     [('fern', 0, 0, 0, 0.95)],
    'pillar':    [('pillar', 0, 0, 0, (1.0, 1.0, 600 / 1721.0))],
    'orcpillar': [('orcpillar', 0, 0, 0, 1.8)],
    'bookcart':  [('bookcart', 0, 0, 0, 1.3)],
    'anchor':    [('anchor', 0, 0, 0, 0.9)],
    'rubble':    [('rockpile', 0, 0, 0, 0.47)],
    'tent':      [('mtent', 0, 0, 0, 0.64)],
    # the orc tent's top shares the base's pivot: it sits (its bottom - the base's bottom) above it, at the same scale
    'orctent':   [('otbase', 0, 0, 0, (0.2, 0.2, 0.28)), ('ottop', 0, 0, 0, (0.2, 0.2, 0.28), (208.5 + 105.1) * 0.28)],
    'hay':       [('hay', -72, 0, 0, 0.95), ('hay', 72, 0, 0, 0.95), ('hay', 0, 0, 90, 0.9, 145)],
    'cart':      [('cart', 0, 0, 0, 0.88)],
    'fence':     [('fence', 0, 0, 0, (0.88, 1.0, 1.0))],
    'boulder':   [('boulder', 0, 0, 0, 0.75)],
}
# rough height of each prop (cm) for the navmesh blocker box
def height(pid):
    h = 0
    for pc in PROPS.get(pid, []):
        k, s = pc[0], pc[4]; sz = s[2] if isinstance(s, tuple) else s
        h = max(h, (M[k][2][2] - M[k][1][2]) * sz + (pc[5] if len(pc) > 5 else 0))
    return h


def place(pid, turns, cx, cy, z, put):
    """Put prop pid in the cell whose middle is (cx, cy) (world), floor height z. turns: quarter turns clockwise."""
    yaw0 = 90.0 * (turns % 4); a = math.radians(yaw0); ca, sa = math.cos(a), math.sin(a)
    n = 0
    for pc in PROPS.get(pid, []):
        k, ox, oy, yaw, s = pc[:5]; on = pc[5] if len(pc) > 5 else 0.0
        sx, sy, sz = s if isinstance(s, tuple) else (s, s, s)
        path, mn, mx = M[k]
        # the mesh's own middle (x, y) and bottom (z), scaled and turned by the piece's yaw
        b = math.radians(yaw); cb, sb = math.cos(b), math.sin(b)
        mx_, my_ = (mn[0] + mx[0]) / 2 * sx, (mn[1] + mx[1]) / 2 * sy
        offx, offy = mx_ * cb - my_ * sb, mx_ * sb + my_ * cb
        px, py = ox - offx, oy - offy                         # pivot so that the mesh's middle lands on (ox, oy)
        wx, wy = cx + px * ca - py * sa, cy + px * sa + py * ca
        put(path, (wx, wy, z + on - mn[2] * sz), (0.0, yaw0 + yaw, 0.0), (sx, sy, sz), 'Prop'); n += 1
    return n
