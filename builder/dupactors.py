# Copy actors (with all their components) inside a UE5.3 legacy cooked level (.umap/.uexp).
# Used to make the VS base level: Castle Plaza with a second rift crystal + rift platform.
#
# What a copy needs:
#  - new export table entries (same class/template, outer remapped, name = same base name with a new number)
#  - the export data, with every reference into the copied set pointed at the new exports
#  - preload dependencies (copied + remapped), an empty DependsMap entry
#  - the new actor added to the level's Actors array, and to the level's preload list
#  - all header offsets and export serial offsets moved
import struct
import ue53pkg

EXP = 96
# VS level: second rift crystal + platform, a second copy of the path point that sits at the rift
VS_COPIES = [('BP_Rift_Crystal_C_0', 2), ('BP_Rift_Platform_FishMarket_C_0', 2), ('RSTPathPoint_1', 17)]
# and a copy of every orc spawner (C_0..13 -> C_14..27): the copy keeps the spawner's settings, so a wave that uses
# spawner X spawns at X on side A and at its mirror image on side B
VS_COPIES += [('BP_AISpawner_C_%d' % i, 15 + i) for i in range(14)]
SPAWNER_ID_OFFSET = 100


def _summary(h):
    """Offsets of the summary fields we need (UE5.3 cooked, legacy version -8)."""
    o = 32
    o += 4 + struct.unpack_from('<i', h, o)[0]            # folder FString
    F = {'flags': o}; o += 4
    for n in ['name_count', 'name_off', 'soft_count', 'soft_off', 'gtext_count', 'gtext_off', 'export_count', 'export_off',
              'import_count', 'import_off', 'depends_off', 'softpkg_count', 'softpkg_off', 'searchable_off', 'thumb_off']:
        F[n] = o; o += 4
    o += 16
    g = struct.unpack_from('<i', h, o)[0]; o += 4 + 8 * g
    for _ in range(2):
        o += 10; o += 4 + struct.unpack_from('<i', h, o)[0]
    o += 16
    F['ar_off'] = o; o += 4
    F['bulk_off'] = o; o += 8
    F['worldtile_off'] = o; o += 4
    c = struct.unpack_from('<i', h, o)[0]; o += 4 + 4 * c
    F['preload_count'] = o; o += 4
    F['preload_off'] = o; o += 4
    F['names_ref_count'] = o; o += 4
    F['payloadtoc_off'] = o; o += 8
    F['dataresource_off'] = o; o += 4
    return F


def _location_bytes(p, e, d):
    """Byte ranges of the RelativeLocation/Rotation values in a component's data (empty if unknown)."""
    import findloc
    cn = p.class_name(e) or ''
    if not cn.endswith('Component'): return []
    L = 5 if cn == 'SceneComponent' else 120
    try:
        o = findloc.loc_offset(bytes(d), L)
        he, fr = findloc.header(bytes(d))
    except Exception:
        return []
    if o is None or o < 0 or o + 24 > len(d): return []
    v = struct.unpack_from('<3d', d, o)
    if not findloc.plausible(v): return []
    return [(o, min(len(d), o + 48))]


def duplicate(umap, uexp, copies, actors=None, log=print):
    """copies: list of (actor export name, new number) e.g. [('BP_Rift_Crystal_C_0', 2)] -> BP_Rift_Crystal_C_1.
    actors: optional castleplaza_actors.json dict ({actor: {'off': uexp offset, ...}}); it comes back with every
    offset moved to the new file, plus entries for the copies.
    Returns (new umap bytes, new uexp bytes, {old actor name: new actor name}, new actors dict)."""
    p = ue53pkg.Package(umap, uexp)
    h = p.h; F = _summary(h)
    g = lambda k: struct.unpack_from('<i', h, F[k])[0]
    total = p.total_header
    assert g('export_off') == p.export_off and g('depends_off') == p.export_off + EXP * len(p.exports)
    pre_off, pre_cnt = g('preload_off'), g('preload_count')
    preload = list(struct.unpack_from('<%di' % pre_cnt, h, pre_off))
    entries = [bytearray(h[e['table_pos']:e['table_pos'] + EXP]) for e in p.exports]
    datas = [bytearray(p.data(e)[1]) for e in p.exports]
    # per export preload groups
    deps = []
    for ent in entries:
        first, *cnt = struct.unpack_from('<5i', ent, 76)
        groups, pos = [], first
        for c in cnt:
            groups.append(preload[pos:pos + c] if c else []); pos += c
        deps.append(groups)

    def under(e, root):
        o = e['outer']
        while o > 0:
            if o == root: return True
            o = p.exports[o - 1]['outer']
        return False

    level = [e for e in p.exports if e['name'] == 'PersistentLevel'][0]
    renamed = {}; copied = {}
    for actor_name, number in copies:
        root = [e for e in p.exports if e['name'] == actor_name][0]
        assert root['outer'] == level['index'], actor_name
        S = [root] + [e for e in p.exports if under(e, root['index'])]
        base = len(entries)
        remap = {e['index']: base + k + 1 for k, e in enumerate(S)}
        name_idx = struct.unpack_from('<i', h, root['table_pos'] + 16)[0]
        new_name = "%s_%d" % (p.names[name_idx], number - 1)
        assert all(e['name'] != new_name for e in p.exports), new_name + " already exists"
        for e in S:
            ent = bytearray(entries[e['index'] - 1]); d = bytearray(datas[e['index'] - 1])
            for fld in (0, 4, 8, 12):                       # class, super, template, outer
                v = struct.unpack_from('<i', ent, fld)[0]
                if v in remap: struct.pack_into('<i', ent, fld, remap[v])
            if e is root: struct.pack_into('<i', ent, 20, number)
            hits = 0
            prot = _location_bytes(p, e, d)         # never "fix" bytes inside a location/rotation (false matches)
            for j in range(len(d) - 3):
                if any(a - 3 <= j < b for a, b in prot): continue
                v = struct.unpack_from('<i', d, j)[0]
                if v in remap:
                    struct.pack_into('<i', d, j, remap[v]); hits += 1
            if e is root and p.class_name(root) == 'BP_AISpawner_C':
                # spawner ID (indexInLevel) = the int right after the spawner's SpawnVolume reference. The game keeps
                # one spawner per ID, so the copy gets its own ID (+100): then it is registered and gets a path network.
                vol = [x for x in S if x['outer'] == root['index'] and x['name'] == 'SpawnVolume'][0]
                j = d.find(struct.pack('<i', remap[vol['index']]))
                assert j >= 0, "spawner ID not found in " + actor_name
                old_id = struct.unpack_from('<i', d, j + 4)[0]
                assert 0 <= old_id < 100, (actor_name, old_id)
                struct.pack_into('<i', d, j + 4, old_id + SPAWNER_ID_OFFSET)
            entries.append(ent); datas.append(d)
            deps.append([[remap.get(x, x) for x in grp] for grp in deps[e['index'] - 1]])
        log("  copied %s -> %s (%d exports)" % (actor_name, new_name, len(S)))
        renamed[actor_name] = new_name; copied.update(remap)
        new_actor = remap[root['index']]
        # level: Actors array (count followed by export indices, contains the original actor)
        ld = datas[level['index'] - 1]
        for o in range(len(ld) - 4):
            n = struct.unpack_from('<i', ld, o)[0]
            if 100 < n < 100000 and o + 4 + 4 * n <= len(ld):
                arr = struct.unpack_from('<%di' % n, ld, o + 4)
                if root["index"] in arr and all(0 <= a <= len(entries) for a in arr):
                    break
        else:
            raise RuntimeError("level Actors array not found")
        struct.pack_into('<i', ld, o, n + 1)
        ld[o + 4 + 4 * n:o + 4 + 4 * n] = struct.pack('<i', new_actor)
        for grp in deps[level['index'] - 1]:
            if root['index'] in grp: grp.append(new_actor)

    # ----- write -----
    n_old = len(p.exports); n_new = len(entries); grow = n_new - n_old
    new_pre = []
    for ent, groups in zip(entries, deps):
        cnt = [len(x) for x in groups]
        old_first = struct.unpack_from('<i', ent, 76)[0]
        first = len(new_pre) if sum(cnt) or old_first != -1 else -1
        struct.pack_into('<5i', ent, 76, first, *cnt)
        for grp in groups: new_pre += grp
    head = bytearray(h[:p.export_off])
    exports_blob = b''.join(entries)
    old_dep_end = g('ar_off')                                 # DependsMap ends where the AR data starts
    depends = h[g('depends_off'):old_dep_end] + b'\0\0\0\0' * grow
    ar = h[g('ar_off'):pre_off]
    pre_blob = struct.pack('<%di' % len(new_pre), *new_pre)
    rest = h[pre_off + 4 * pre_cnt:]                         # data resources etc. up to the end of the header
    assert g('dataresource_off') == pre_off + 4 * pre_cnt
    nh = bytearray(head + exports_blob + depends + ar + pre_blob + rest)
    S2 = lambda k, v: struct.pack_into('<i', nh, F[k], v)
    S2('export_count', n_new)
    dep_off = p.export_off + len(exports_blob); S2('depends_off', dep_off)
    ar_off = dep_off + len(depends); S2('ar_off', ar_off)
    po = ar_off + len(ar); S2('preload_off', po); S2('preload_count', len(new_pre))
    S2('dataresource_off', po + len(pre_blob))
    new_total = len(nh); struct.pack_into('<i', nh, 28, new_total)
    # export data in the old order, new exports appended before the trailing package tag
    out = bytearray(); offs = []
    for d in datas: offs.append(new_total + len(out)); out += d
    tail = p.x[sum(e['size'] for e in p.exports):]
    assert tail == b'\xc1\x83\x2a\x9e', "unexpected bytes after the export data"
    out += tail
    for k, ent in enumerate(entries):
        pos = p.export_off + EXP * k
        struct.pack_into('<qq', nh, pos + 28, len(datas[k]), offs[k])
    struct.pack_into('<q', nh, F['bulk_off'], new_total + len(out) - 4)
    new_actors = None
    if actors is not None:
        starts = [e['off'] - total for e in p.exports]
        def move(off, idx=None):
            for e in p.exports:
                s0 = e['off'] - total
                if s0 <= off < s0 + e['size']:
                    k = copied[e['index']] if idx == 'copy' else e['index']
                    return offs[k - 1] - new_total + (off - s0)
            raise RuntimeError("offset %d is not inside any export" % off)
        new_actors = {}
        for name, a in actors.items():
            new_actors[name] = dict(a, off=move(a['off']))
            if name in renamed: new_actors[renamed[name]] = dict(a, off=move(a['off'], 'copy'))
    return bytes(nh), bytes(out), renamed, new_actors


if __name__ == '__main__':
    import sys
    src, dst = sys.argv[1], sys.argv[2]
    import json
    hh, xx, ren, act = duplicate(src + '.umap', src + '.uexp', VS_COPIES, json.load(open(sys.argv[3])))
    open(dst + '.umap', 'wb').write(hh); open(dst + '.uexp', 'wb').write(xx)
    json.dump(act, open(sys.argv[4], 'w'), indent=1)
    print(ren)
