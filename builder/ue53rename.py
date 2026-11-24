# Rename entries in the name map of a UE5.3 legacy cooked package (.umap/.uasset + .uexp) and fix every
# header offset that moves. Optionally replace raw byte spans inside one export (resizing it).
import struct


class Summary:
    """Walks FPackageFileSummary (UE5.3, FileVersionUE5 1009 or unversioned) recording offset-field positions."""
    def __init__(self, h):
        self.h = h; o = 0
        rd = lambda f: struct.unpack_from(f, h, o)
        self.fields = {}            # name -> (pos, fmt)
        def take(name, fmt):
            nonlocal o
            v = struct.unpack_from(fmt, h, o)[0]
            self.fields[name] = (o, fmt); o += struct.calcsize(fmt); return v
        def fstr(name):
            nonlocal o
            p = o; n = struct.unpack_from('<i', h, o)[0]; o += 4
            if n > 0: s = h[o:o + n - 1].decode('latin-1'); o += n
            elif n < 0: s = h[o:o - 2 * n - 2].decode('utf-16-le'); o += -2 * n
            else: s = ''
            self.fields[name] = (p, 'fstr'); return s
        assert take('tag', '<I') == 0x9E2A83C1
        legacy = take('legacy', '<i')
        if legacy != -4: take('ue3', '<i')
        take('ue4', '<i')
        ue5 = take('ue5', '<i') if legacy <= -8 else 0
        take('licensee', '<i')
        ncv = take('ncv', '<i'); o += 20 * ncv
        take('TotalHeaderSize', '<i')
        self.package_name = fstr('PackageName')
        self.flags = take('PackageFlags', '<I')
        self.name_count = take('NameCount', '<i'); self.name_off = take('NameOffset', '<i')
        if ue5 == 0 or ue5 >= 1008:
            take('SoftObjectPathsCount', '<i'); take('SoftObjectPathsOffset', '<i')
        if not (self.flags & 0x80000000): fstr('LocalizationId')
        take('GatherableTextDataCount', '<i'); take('GatherableTextDataOffset', '<i')
        take('ExportCount', '<i'); take('ExportOffset', '<i')
        take('ImportCount', '<i'); take('ImportOffset', '<i')
        take('DependsOffset', '<i')
        take('SoftPackageReferencesCount', '<i'); take('SoftPackageReferencesOffset', '<i')
        take('SearchableNamesOffset', '<i')
        take('ThumbnailTableOffset', '<i')
        o += 16                                                    # package guid
        if not (self.flags & 0x80000000): o += 16                  # persistent guid
        ng = take('GenerationCount', '<i'); o += 8 * ng
        for nm in ('Saved', 'Compat'):
            o += 10; fstr(nm + 'Branch')
        take('CompressionFlags', '<I')
        assert take('CompressedChunks', '<i') == 0
        take('PackageSource', '<I')
        na = take('AdditionalPackagesToCook', '<i')
        for i in range(na): fstr('APTC%d' % i)
        take('AssetRegistryDataOffset', '<i')
        take('BulkDataStartOffset', '<q')
        take('WorldTileInfoDataOffset', '<i')
        nc = take('ChunkIDCount', '<i'); o += 4 * nc
        take('PreloadDependencyCount', '<i'); take('PreloadDependencyOffset', '<i')
        take('NamesReferencedFromExportDataCount', '<i')
        take('PayloadTocOffset', '<q')
        take('DataResourceOffset', '<i')
        self.end = o


OFFSET_FIELDS = ['TotalHeaderSize', 'SoftObjectPathsOffset', 'GatherableTextDataOffset', 'ExportOffset', 'ImportOffset',
                 'DependsOffset', 'SoftPackageReferencesOffset', 'SearchableNamesOffset', 'ThumbnailTableOffset',
                 'AssetRegistryDataOffset', 'BulkDataStartOffset', 'WorldTileInfoDataOffset', 'PreloadDependencyOffset',
                 'PayloadTocOffset', 'DataResourceOffset']


def fstring(s):
    try:
        e = s.encode('ascii'); return struct.pack('<i', len(e) + 1) + e + b'\0'
    except UnicodeEncodeError:
        e = s.encode('utf-16-le'); return struct.pack('<i', -(len(e) // 2 + 1)) + e + b'\0\0'


def rewrite(h, x, renames=None, package_name=None, export_edits=None):
    """renames: {old_name: new_name}. export_edits: {export_index(1-based): [(old_bytes, new_bytes), ...]}.
    Returns (new_header, new_uexp)."""
    S = Summary(h)
    renames = renames or {}
    # --- rebuild the name map ---
    o = S.name_off; entries = []
    for i in range(S.name_count):
        n = struct.unpack_from('<i', h, o)[0]; st = o; o += 4
        if n > 0: s = h[o:o + n - 1].decode('latin-1'); o += n
        elif n < 0: s = h[o:o - 2 * n - 2].decode('utf-16-le'); o += -2 * n
        else: s = ''
        hashes = h[o:o + 4]; o += 4
        entries.append((s, hashes))
    names_end = o
    used = set()
    blob = b''
    for s, hs in entries:
        if s in renames: s = renames[s]; used.add(s)
        blob += fstring(s) + hs
    missing = [k for k, v in renames.items() if v not in used]
    assert not missing, "names not found: %s" % missing
    # --- summary package name ---
    pre = bytearray(h[:S.name_off])
    d1 = 0
    if package_name is not None:
        p, _ = S.fields['PackageName']
        old_len = len(fstring(S.package_name)) if S.package_name else 4
        new = fstring(package_name)
        pre[p:p + old_len] = new; d1 = len(new) - old_len
    d2 = len(blob) - (names_end - S.name_off)
    new_h = bytearray(bytes(pre) + blob + h[names_end:])
    delta_total = d1 + d2
    # re-walk the summary at its new positions and patch offsets
    S2 = Summary(bytes(new_h))
    def patch(name, shift_if_after):
        pos, fmt = S2.fields[name]
        v = struct.unpack_from(fmt, new_h, pos)[0]
        if v > 0 and v >= shift_if_after: struct.pack_into(fmt, new_h, pos, v + delta_total)
    for f in OFFSET_FIELDS:
        if f in S2.fields: patch(f, S.name_off)
    pos, fmt = S2.fields['NameOffset']; struct.pack_into(fmt, new_h, pos, S.name_off + d1)
    # exports: SerialOffset (+delta), and optional in-export edits
    S3 = Summary(bytes(new_h))
    exp_off = struct.unpack_from('<i', new_h, S3.fields['ExportOffset'][0])[0]
    exp_cnt = struct.unpack_from('<i', new_h, S3.fields['ExportCount'][0])[0]
    old_total = S.__dict__.get('total', None)
    old_hdr_size = struct.unpack_from('<i', h, S.fields['TotalHeaderSize'][0])[0]
    new_hdr_size = old_hdr_size + delta_total
    x = bytearray(x)
    export_edits = export_edits or {}
    # gather exports (old offsets relative to uexp)
    ex = []
    for i in range(exp_cnt):
        tp = exp_off + 96 * i
        size, off = struct.unpack_from('<qq', new_h, tp + 28)
        ex.append([tp, size, off - old_hdr_size])
    order = sorted(range(exp_cnt), key=lambda k: ex[k][2])
    new_x = bytearray(); cursor = 0; shifts = []
    for k in order:
        tp, size, rel = ex[k]
        new_x += x[cursor:rel]
        data = bytes(x[rel:rel + size])
        for old, new in export_edits.get(k + 1, []):
            assert data.count(old) == 1, ("edit not unique in export %d" % (k + 1), old)
            data = data.replace(old, new)
        struct.pack_into('<qq', new_h, tp + 28, len(data), len(new_x) + new_hdr_size)
        new_x += data; cursor = rel + size
    new_x += x[cursor:]
    grow = len(new_x) - len(x)
    if grow:
        pos, fmt = S3.fields['BulkDataStartOffset']
        v = struct.unpack_from(fmt, new_h, pos)[0]
        struct.pack_into(fmt, new_h, pos, v + grow)
    return bytes(new_h), bytes(new_x)
