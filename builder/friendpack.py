# Friend pack: everything a friend WITHOUT OMD Map Builder needs to play our maps (and VS with us), in one zip with an
# installer. Contents: our paks (Paks\Mods\zz_JW*: maps, registry, archer trap) as installed in the game right now,
# UE4SS (UE4SS*.*, dwmapi.dll, the Mods folder with the VS referee and the archer mods, minus our test tools) and
# install.bat, install.ps1 and READ ME.txt. Used by the app's "Share: no Map Builder" button (tools\vs_friendpack.py
# is the older job version of the same thing).
import fnmatch, os, time, zipfile

INSTALL_PS1 = r'''# Installs the OMD VS mods into Orcs Must Die! Deathtrap (close the game first).
$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$cands = @("C:\Program Files (x86)\Steam", "C:\Program Files\Steam")
$libs = @()
foreach ($s in $cands) {
  $libs += $s
  $vdf = Join-Path $s "steamapps\libraryfolders.vdf"
  if (Test-Path $vdf) {
    foreach ($line in Get-Content $vdf) {
      if ($line -match '"path"\s+"(.+)"') { $libs += ($Matches[1] -replace '\\\\', '\') }
    }
  }
}
$game = $null
foreach ($l in $libs) {
  $g = Join-Path $l "steamapps\common\Orcs Must Die Deathtrap"
  if (Test-Path (Join-Path $g "OMDD\Content\Paks")) { $game = $g; break }
}
if (-not $game) { Write-Host "Orcs Must Die! Deathtrap was not found in any Steam library." -ForegroundColor Red; exit 1 }
Write-Host "Game folder: $game"
if (Get-Process -Name "OMDDSteam-Win64-Shipping" -ErrorAction SilentlyContinue) {
  Write-Host "Close the game first, then run install.bat again." -ForegroundColor Red; exit 1
}
$mods = Join-Path $game "OMDD\Content\Paks\Mods"
New-Item -ItemType Directory -Force -Path $mods | Out-Null
Get-ChildItem $mods -Filter "zz_JW*" -ErrorAction SilentlyContinue | Remove-Item -Force   # old versions of our paks
$src = Join-Path $here "game"
Get-ChildItem $src -Recurse -File | ForEach-Object {
  $rel = $_.FullName.Substring($src.Length + 1)
  $dst = Join-Path $game $rel
  New-Item -ItemType Directory -Force -Path (Split-Path -Parent $dst) | Out-Null
  Copy-Item $_.FullName $dst -Force
}
# mods the host switched off in OMD Map Builder come as enabled.off: switch them off here too
Get-ChildItem (Join-Path $game "OMDD\Binaries\Win64\Mods") -Directory | ForEach-Object {
  if ((Test-Path (Join-Path $_.FullName "enabled.off")) -and (Test-Path (Join-Path $_.FullName "enabled.txt"))) { Remove-Item (Join-Path $_.FullName "enabled.txt") -Force }
}
# the Lua mods write their logs and read their rules in the game folder: point them at this PC's game folder
$bin = (Join-Path $game "OMDD\Binaries\Win64\") -replace '\\', '/'
$def = "C:/Program Files (x86)/Steam/steamapps/common/Orcs Must Die Deathtrap/OMDD/Binaries/Win64/"
Get-ChildItem (Join-Path $game "OMDD\Binaries\Win64\Mods") -Recurse -Filter "main.lua" | ForEach-Object {
  $t = [IO.File]::ReadAllText($_.FullName)
  if ($t.Contains($def) -and $bin -ne $def) { [IO.File]::WriteAllText($_.FullName, $t.Replace($def, $bin)) }
}
Write-Host "Done. Start the game and join the host's game from the Steam invite." -ForegroundColor Green
'''
INSTALL_BAT = '@echo off\r\npowershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1"\r\npause\r\n'
# Takes out exactly what install.bat put in: every file in this pack's game folder, plus any zz_JW* paks (older versions).
UNINSTALL_PS1 = r'''# Removes the OMD custom maps and mods from Orcs Must Die! Deathtrap (close the game first).
param([string]$GameDir = "")        # optional: the game folder (otherwise it is looked up in the Steam libraries)
$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$cands = @("C:\Program Files (x86)\Steam", "C:\Program Files\Steam")
$libs = @()
foreach ($s in $cands) {
  $libs += $s
  $vdf = Join-Path $s "steamapps\libraryfolders.vdf"
  if (Test-Path $vdf) {
    foreach ($line in Get-Content $vdf) {
      if ($line -match '"path"\s+"(.+)"') { $libs += ($Matches[1] -replace '\\\\', '\') }
    }
  }
}
$game = $null
if ($GameDir) { $game = $GameDir } else {
  foreach ($l in $libs) {
    $g = Join-Path $l "steamapps\common\Orcs Must Die Deathtrap"
    if (Test-Path (Join-Path $g "OMDD\Content\Paks")) { $game = $g; break }
  }
}
if (-not $game) { Write-Host "Orcs Must Die! Deathtrap was not found in any Steam library." -ForegroundColor Red; exit 1 }
Write-Host "Game folder: $game"
if (Get-Process -Name "OMDDSteam-Win64-Shipping" -ErrorAction SilentlyContinue) {
  Write-Host "Close the game first, then run uninstall.bat again." -ForegroundColor Red; exit 1
}
$n = 0
Get-ChildItem (Join-Path $game "OMDD\Content\Paks\Mods") -Filter "zz_JW*" -ErrorAction SilentlyContinue | ForEach-Object { Remove-Item $_.FullName -Force; $n++ }
$src = Join-Path $here "game"
$dirs = @()
Get-ChildItem $src -Recurse -File | ForEach-Object {
  $rel = $_.FullName.Substring($src.Length + 1)
  $dst = Join-Path $game $rel
  if (Test-Path $dst) { Remove-Item $dst -Force; $n++ }
  $dirs += (Split-Path -Parent $dst)
}
# the logs UE4SS wrote
$win = Join-Path $game "OMDD\Binaries\Win64"
Get-ChildItem $win -Filter "UE4SS*.log" -ErrorAction SilentlyContinue | Remove-Item -Force
# empty folders left behind, deepest first (only folders the pack made files in)
$dirs | Sort-Object -Unique | Sort-Object Length -Descending | ForEach-Object {
  $d = $_
  while ($d -and $d.StartsWith($win + "\") -and (Test-Path $d)) {
    if ((Get-ChildItem $d -Force -Recurse -File -ErrorAction SilentlyContinue | Where-Object { $_.Name -notlike "*.log" }).Count -eq 0) { Remove-Item $d -Recurse -Force } else { break }
    $d = Split-Path -Parent $d
  }
}
Write-Host "Removed $n files. The game is back to normal (no custom maps, no mods)." -ForegroundColor Green
'''
UNINSTALL_BAT = '@echo off\r\npowershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0uninstall.ps1"\r\npause\r\n'

README = """OMD custom maps (the host's maps, the VS referee, the guardian archer trap)

1. Close Orcs Must Die! Deathtrap.
2. Unzip this whole folder somewhere (e.g. the desktop).
3. Double-click install.bat. It finds the game, copies the files in and replaces older versions.
4. Start the game. The custom maps are in the run's mission choice. For VS, join the host from the Steam invite.

Both players need the same version: when the host builds new maps, install the new zip again.
To remove everything again: close the game and double-click uninstall.bat (keep this folder, or unzip the pack again).
It takes out the custom maps and the mods; the game then runs like before.

In a VS match: F5-F8 send enemies to the other side (paid with your coins). Delete next to a guardian archer trap sells it
(build phase only).
"""

DEV_MODS = {"JWAutoTest", "JWMapLoader"}          # our test tools (JWMapLoader uses F6/F8/F9, the send keys)
SKIP = ["*.log", "*.txt.bak", "JW_*"]


def make(game, out, log=print):
    """Zips the friend pack to out (replaced only when complete). Returns (files, MB unpacked, MB zip)."""
    win64 = os.path.join(game, "OMDD", "Binaries", "Win64")
    paks = os.path.join(game, "OMDD", "Content", "Paks", "Mods")
    if not any(f.startswith("zz_JWMaps") for f in (os.listdir(paks) if os.path.isdir(paks) else [])):
        raise RuntimeError("no custom maps in the game yet - press Build & install first")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    tmp = out + ".tmp"; n = 0; size = 0
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z:
        def add(path, arc):
            nonlocal n, size
            z.write(path, arc); n += 1; size += os.path.getsize(path)
        for f in sorted(os.listdir(paks)):
            if f.startswith("zz_JW"): add(os.path.join(paks, f), "game/OMDD/Content/Paks/Mods/" + f)
        for f in sorted(os.listdir(win64)):
            fp = os.path.join(win64, f)
            if os.path.isfile(fp) and (f.lower().startswith("ue4ss") or f.lower() == "dwmapi.dll") and not f.lower().endswith(".log"):
                add(fp, "game/OMDD/Binaries/Win64/" + f)
        for top in ("Mods", "UE4SS_Signatures"):
            base = os.path.join(win64, top)
            if not os.path.isdir(base): continue
            for dp, dn, fn in os.walk(base):
                dn[:] = [d for d in dn if d not in DEV_MODS]
                for f in fn:
                    if any(fnmatch.fnmatch(f, s) for s in SKIP): continue
                    fp = os.path.join(dp, f)
                    add(fp, "game/OMDD/Binaries/Win64/" + os.path.relpath(fp, win64).replace("\\", "/"))
        z.writestr("install.ps1", INSTALL_PS1)
        z.writestr("install.bat", INSTALL_BAT)
        z.writestr("uninstall.ps1", UNINSTALL_PS1)
        z.writestr("uninstall.bat", UNINSTALL_BAT)
        z.writestr("READ ME.txt", README)
    if os.path.exists(out): os.remove(out)
    os.rename(tmp, out)
    mb = (n, size / 1e6, os.path.getsize(out) / 1e6)
    log("friend pack: %s (%d files, %.1f MB unpacked, %.1f MB zip) %s" % (out, mb[0], mb[1], mb[2], time.strftime("%H:%M:%S")))
    return mb
