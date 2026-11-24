# Take actors of given classes off a cooked level's actor list (entries set to None), so the game never spawns them.
import struct
import ue53pkg

DROP_MAIN = {'BP_ChestSpawner_C', 'BP_RSTGnomeSentinelSpawner_C', 'BP_Sentinel_Archer_Trap_C', 'StaticMeshActor', 'Emitter',
             'InstancedFoliageActor', 'BP_Castle_Plaza_EastTownGate_C', 'BP_Castle_Plaza_EastWaterWheelGate_C',
             'BP_Castle_Plaza_NorthDrawbridgeGate_C', 'BP_Castle_Plaza_WestWatersideGate_C',
             'BP_KeyGrantPickup_EnemyStatue_GnollAssassin_C', 'BP_KeyGrantPickup_Hammer_MorningSkin_C'}
DROP_LIGHTING = {'BP_Lantern_Wall_A_C', 'StaticMeshActor', 'BP_WallTorch_SAND_A_Off_C', 'BP_Lantern_Wall_Wood_C',
                 'BP_Column_Square_Taper_1_4_LightPost_C'}


def hide(umap, uexp, drop):
    p = ue53pkg.Package(umap, uexp)
    L = [e for e in p.exports if p.class_name(e) == 'Level'][0]
    acts = {e['index'] for e in p.exports if e['outer'] == L['index']}
    o, d = p.data(L)
    for k in range(len(d) - 8):
        n = struct.unpack_from('<i', d, k)[0]
        if 10 < n < 20000 and k + 4 + 4 * n <= len(d):
            v = struct.unpack_from('<%di' % n, d, k + 4)
            if all(x in acts or x == 0 for x in v) and sum(1 for x in v if x) > len(acts) * 0.8:
                break
    else:
        raise RuntimeError('actor list not found in ' + umap)
    x = bytearray(p.x); gone = 0
    for i, idx in enumerate(v):
        if idx and p.class_name(p.exports[idx - 1]) in drop:
            struct.pack_into('<i', x, o + k + 4 + 4 * i, 0); gone += 1
    open(uexp, 'wb').write(x)
    return gone
