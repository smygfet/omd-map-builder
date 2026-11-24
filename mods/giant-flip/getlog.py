# Read-only: copy the game's log lines about the Giant Flip Trap (and package load errors) to notes\giantflip_gamelog.txt
import os, glob
ROOT = os.path.join(os.path.expanduser("~"), "Documents", "Claud OMD")
out = []
for p in glob.glob(os.path.join(os.environ.get("LOCALAPPDATA", ""), "OMDD", "Saved", "Logs", "*.log")):
    out.append("==== %s (%d bytes)" % (p, os.path.getsize(p)))
    try:
        for i, line in enumerate(open(p, encoding="utf-8", errors="replace")):
            l = line.lower()
            if any(k in l for k in ("giantflip", "jwgiant", "fliptrap_big", "zz_jw", "failed to load", "can't find file", "couldn't find", "loadpackage", "mount", "skippackage", "error:")):
                out.append("%d: %s" % (i, line.rstrip()[:400]))
    except Exception as e: out.append("read error %r" % e)
open(os.path.join(ROOT, "notes", "giantflip_gamelog.txt"), "w", encoding="utf-8").write("\n".join(out[-3000:]))
