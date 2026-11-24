# Base levels a map can be built on. Castle Plaza: crystal rift (orcs attack it). Castle Colosseum: normal rift (orcs walk in).
# Everything the builder needs to know about a base: its files, actor names, what to copy for VS and what to hide.
import hideactors

PLAZA = dict(
    key='plaza', dir='/Game/Levels/BaseGame/Castle/CastlePlaza/', level='Level_Castle_CastlePlaza',
    actors='castleplaza_actors.json',
    rift='BP_Rift_Crystal_C_0', rift_dz=95, platform='BP_Rift_Platform_FishMarket_C_0', rift_pp='RSTPathPoint_1',
    onslaught='BP_Onslaught_Castle_CastlePlaza_C_1',
    spawners=['BP_AISpawner_C_%d' % i for i in range(14)],
    # VS copies: (actor, new number) -> name = base name + '_' + (number - 1)
    vs_copies=[('BP_Rift_Crystal_C_0', 2), ('BP_Rift_Platform_FishMarket_C_0', 2), ('RSTPathPoint_1', 17)]
              + [('BP_AISpawner_C_%d' % i, 15 + i) for i in range(14)],
    drop=set(hideactors.DROP_MAIN), empty_subs={'Geo': 'Geo', 'Props': 'Props', 'Perf': 'Perf'})

COLOSSEUM = dict(
    key='colosseum', dir='/Game/Levels/BaseGame/Castle/Colosseum/', level='Level_Castle_Colosseum',
    actors='colosseum_actors.json',
    rift='BP_Rift_C_2', rift_dz=227, platform=None, rift_pp='RSTPathPoint_1',
    onslaught='BP_Onslaught_Castle_Colosseum_C_1',
    spawners=['BP_AISpawner_C_%d' % i for i in range(10)],
    vs_copies=[('BP_Rift_C_2', 10), ('RSTPathPoint_1', 31)] + [('BP_AISpawner_C_%d' % i, 31 + i) for i in range(10)],
    # the rift's dais (RiftBase_1_BP_C) stores no location, so it cannot be moved: hidden
    drop={'BP_ChestSpawner_C', 'BP_RSTGnomeSentinelSpawner_C', 'BP_Sentinel_Archer_Trap_C', 'StaticMeshActor', 'Emitter',
          'InstancedFoliageActor', 'BP_Colosseum_BathsEastGate_C', 'BP_Colosseum_BlacksmithNorthGate_C',
          'BP_Colosseum_JailsSouthGate_C', 'BP_Colosseum_UpperPitsWestGate_C',
          'BP_KeyGrantPickup_EnemyStatue_OrcUnstable_C', 'RiftBase_1_BP_C'},
    empty_subs={'Geo': 'Geo', 'Props': 'Props', 'Perf': 'Perf'})

# Order Arboretum: a mission with two normal rifts in separate lanes - the game itself handles two rifts here.
# VS: nothing is copied; rift 3 (+ its dais) goes to side A, rift 5 to side B, and the 24 spawners split 12/12.
_ARB_SP = ['BP_AISpawner_C_%d' % i for i in range(24)]
ARBORETUM = dict(
    key='arboretum', dir='/Game/Levels/BaseGame/Gardens/Arboretum/', level='Level_Gardens_Arboretum',
    actors='arboretum_actors.json',
    rift='BP_Rift_C_3', rift_dz=127, platform='RiftBase_1_BP_C_2', rift_pp='RSTPathPoint_1',
    rift2=dict(rift='BP_Rift_C_5', platform='RiftBase_1_BP_C_4', pp='RSTPathPoint_0', dz=127),
    onslaught='BP_Onslaught_Gardens_Arboretum_C_1',
    # endless VS: the wave script, copied per map with every wave running wave 1 (builder/onslaughtloop.py)
    loop_script=dict(path='/Game/Levels/BaseGame/Gardens/Onslaughts/', name='BP_Onslaught_Gardens_Arboretum'),
    spawners=_ARB_SP,
    # test (2026-11-11): spawners swapped - odd ones on side A, even ones on side B (swapping the rifts changed nothing:
    # blocked orcs broke barricades only on side B)
    vs_pairs=[[_ARB_SP[2 * i], _ARB_SP[2 * i + 1]] for i in range(12)],
    vs_copies=[],
    drop={'BP_ChestSpawner_C', 'BP_RSTGnomeSentinelSpawner_C', 'BP_Warhero_Priestess_Trap_C', 'StaticMeshActor',
          'InstancedFoliageActor', 'NiagaraActor', 'StairPlatform_Small_C', 'BP_Gardens_Arboretum_1Gate_A_C',
          'BP_Gardens_Arboretum_LowerNorthGate_C', 'BP_Gardens_Arboretum_UpperEastGate_C',
          'BP_Gardens_Arboretum_UpperNorthGate_C', 'BP_KeyGrantPickup_Gabriella_MorningSkin_C', 'KillZVolume'},
    # four scenery sublevels but three shared empty levels: Perf (culling volumes only) stays as it is
    empty_subs={'LowerGeo': 'Geo', 'UpperGeo': 'Props', 'Props': 'Perf'})

BASES = {'plaza': PLAZA, 'colosseum': COLOSSEUM, 'arboretum': ARBORETUM}


def patch_config(b, renamed=None, vs=False):
    """What patch_plaza2 needs: per side the rift, its platform and the rift path point; spawner pairs (side A, side B)."""
    r = renamed or {}
    side = lambda n: n and r.get(n)
    rifts = [dict(rift=b['rift'], platform=b['platform'], pp=b['rift_pp'], dz=b['rift_dz'])]
    if vs and b.get('rift2'):                    # a base with two rifts of its own
        return dict(key=b['key'], rifts=rifts + [dict(b['rift2'])], onslaught=b['onslaught'], spawners=b['vs_pairs'])
    if renamed:
        rifts.append(dict(rift=side(b['rift']), platform=side(b['platform']), pp=side(b['rift_pp']), dz=b['rift_dz']))
    return dict(key=b['key'], rifts=rifts, onslaught=b['onslaught'],
                spawners=[[s, r.get(s)] for s in b['spawners']])
