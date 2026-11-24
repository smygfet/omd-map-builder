# Minimal reader for UE5.3 legacy cooked packages (.umap/.uasset + .uexp) - names, imports, exports.
import struct

class R:
    def __init__(s, b, o=0): s.b, s.o = b, o
    def i32(s): v = struct.unpack_from('<i', s.b, s.o)[0]; s.o += 4; return v
    def u32(s): v = struct.unpack_from('<I', s.b, s.o)[0]; s.o += 4; return v
    def i64(s): v = struct.unpack_from('<q', s.b, s.o)[0]; s.o += 8; return v
    def fstr(s):
        n = s.i32()
        if n == 0: return ""
        if n > 0: v = s.b[s.o:s.o + n - 1].decode('latin-1'); s.o += n; return v
        n = -n; v = s.b[s.o:s.o + 2 * n - 2].decode('utf-16-le'); s.o += 2 * n; return v

class Package:
    def __init__(self, umap_path, uexp_path):
        self.h = open(umap_path, 'rb').read()
        self.x = open(uexp_path, 'rb').read()
        r = R(self.h)
        assert r.u32() == 0x9E2A83C1
        self.legacy = r.i32(); r.i32(); self.ue4 = r.i32(); self.ue5 = r.i32(); r.i32()
        if self.ue5 == 0: self.ue5 = 1009   # unversioned cooked package: UE5.3 layout
        ncv = r.i32(); r.o += ncv * 20
        self.total_header = r.i32()
        self.package_name = r.fstr()
        self.flags = r.u32()
        self.name_count = r.i32(); self.name_off = r.i32()
        if self.ue5 >= 1008: r.i32(); r.i32()
        if not (self.flags & 0x80000000): r.fstr()          # LocalizationId when not FilterEditorOnly
        r.i32(); r.i32()                                     # gatherable text
        self.export_count = r.i32(); self.export_off = r.i32()
        self.import_count = r.i32(); self.import_off = r.i32()
        # names
        r.o = self.name_off; self.names = []
        for _ in range(self.name_count):
            self.names.append(r.fstr()); r.o += 4
        # imports (32 bytes each for UE5.3 cooked)
        self.imports = []
        isz = (self.export_off - self.import_off) // self.import_count if self.import_off < self.export_off else 32
        for i in range(self.import_count):
            r.o = self.import_off + i * isz
            cp = self.fname(r); cn = self.fname(r); outer = r.i32(); on = self.fname(r)
            self.imports.append(dict(class_package=cp, class_name=cn, outer=outer, name=on))
        # exports (96 bytes each for UE5.3)
        self.exports = []
        r.o = self.export_off
        for i in range(self.export_count):
            st = r.o
            cls = r.i32(); sup = r.i32(); tmpl = r.i32(); outer = r.i32(); name = self.fname(r)
            oflags = r.u32(); size = r.i64(); off = r.i64()
            self.exports.append(dict(index=i + 1, cls=cls, outer=outer, name=name, size=size, off=off, table_pos=st))
            r.o = st + 96
    def fname(self, r):
        i = r.i32(); n = r.i32()
        s = self.names[i] if 0 <= i < len(self.names) else "?%d" % i
        return s if n == 0 else "%s_%d" % (s, n - 1)
    def obj_name(self, idx):
        if idx > 0: return self.exports[idx - 1]['name']
        if idx < 0: return self.imports[-idx - 1]['name']
        return None
    def class_name(self, e): return self.obj_name(e['cls'])
    def path(self, e):
        parts = [e['name']]; o = e['outer']
        while o > 0: parts.append(self.exports[o - 1]['name']); o = self.exports[o - 1]['outer']
        return ".".join(reversed(parts))
    def data(self, e):
        s = e['off'] - self.total_header
        return s, self.x[s:s + e['size']]
