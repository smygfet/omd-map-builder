-- JWEndless v4: endless mode helper for the game's own missions (separate from the VS referee JWVersus).
-- The pak zz_JWEndless_P makes every base-game mission repeat its wave 1 (waves 1-39, wave 40 ends).
-- This mod makes each wave harder, from wave 2 on (all numbers can be changed on the app's Mods page):
--   * enemy health +15 % per wave (MaxHealth on the enemy types' pawn definitions; originals restored on every new level)
--   * more enemies: each wave enemy brings 0.5 extra copies per wave (wave 3: 1 extra, wave 5: 2 extra ...),
--     spawned from the spawner nearest to it
--   * v3: NEW ENEMY TYPES, from wave 1: the first START_TYPES types of a ladder (heavy orcs, archers, a light ogre)
--     come with wave 1, and every wave unlocks PER_WAVE more, bigger ones (trolls -> ogres -> cyclopses -> earth
--     elemental). The newest types come NEW_COUNT each, earlier ones OLD_COUNT each, +1 every GROW waves.
--     Types that fail to load are logged and skipped. They walk in from the spawners the mission's own enemies use.
--     v4: the order is RANDOM for every mission: the ladder is three tiers (small/medium/big) shuffled within each
--     tier, so every run starts with different types but still grows bigger. (random=0 keeps the fixed order)
--     Settings file keys: newtypes (0/1), newcount, oldcount, starttypes, perwave, random (0/1).
--   * nothing extra spawns in the build phase: the wave number goes up when the build phase starts, so extra and new
--     enemies wait until that wave's own enemies have appeared, and leftovers of the last wave are dropped
-- Only active on levels under /Game/Levels/BaseGame/ (never on custom or VS maps). Host only.
-- Log: Binaries\Win64\JW_Endless_log.txt
local BIN = "C:/Program Files (x86)/Steam/steamapps/common/Orcs Must Die Deathtrap/OMDD/Binaries/Win64/"
-- defaults; the OMD Map Builder's Mods page writes Mods\JWEndless\settings.txt, read at every mission start
local MORE = 0.5            -- extra copies per wave enemy, added each wave
local TOUGHER = 0.15        -- enemy health per wave
local MAX_ALIVE = 200       -- no extra spawns while this many enemies are alive
local FROM = 2              -- the first wave that is harder
local NEWTYPES = 1          -- 1: new enemy types on
local START_TYPES = 3       -- ladder types that come from wave 1
local PER_WAVE = 2          -- ladder types unlocked per wave after that
local NEW_COUNT = 4         -- how many of each newly unlocked type come each wave
local OLD_COUNT = 2         -- how many of each earlier ladder type come each wave
local GROW = 3              -- every GROW waves each type sends one more
local RANDOM = 1            -- 1: shuffle the ladder within its tiers for every mission
-- the ladder: bigger and bigger, in tiers (shuffled within each tier when RANDOM is 1) (only walking enemies; flyers, bosses and special ones left out)
local LADDER = {
    {"Orc_Heavy", tier = 1,        "/Game/Characters/Minions/Orcs/Orc_Heavy/Data/PDE_Orc_Heavy"},
    {"Orc_Archer", tier = 1,       "/Game/Characters/Minions/Orcs/Orc_Archer/Data/PDE_Orc_Archer"},
    {"Ogre_Light", tier = 1,       "/Game/Characters/Minions/Ogres/Ogre_Light/Data/PDE_Ogre_Light"},
    {"Gnoll_Grenadier", tier = 1,  "/Game/Characters/Minions/Gnolls/Gnoll_Grenadier/Data/PDE_Gnoll_Grenadier"},
    {"Troll_Light", tier = 1,      "/Game/Characters/Minions/Trolls/Troll_Light/Data/PDE_Troll_Light"},
    {"Gnoll_Assassin", tier = 1,   "/Game/Characters/Minions/Gnolls/Gnoll_Assassin/Data/PDE_Gnoll_Assassin"},
    {"Ogre_Heavy", tier = 2,       "/Game/Characters/Minions/Ogres/Ogre_Heavy/Data/PDE_Ogre_Heavy"},
    {"Troll_Archer", tier = 2,     "/Game/Characters/Minions/Trolls/Troll_Archer/Data/PDE_Troll_Archer"},
    {"Cyclops_Mage", tier = 2,     "/Game/Characters/Minions/Cyclops/Cyclops_Mage/Data/PDE_Cyclops_Mage"},
    {"Ogre_Shield", tier = 2,      "/Game/Characters/Minions/Ogres/Ogre_Shield/Data/PDE_Ogre_Shield"},
    {"Troll_Mountain", tier = 3,   "/Game/Characters/Minions/Trolls/Troll_Mountain/Data/PDE_Troll_Mountain"},
    {"Ogre_Fire", tier = 3,        "/Game/Characters/Minions/Ogres/Ogre_Fire/Data/PDE_Ogre_Fire"},
    {"Cyclops_Guardian", tier = 3, "/Game/Characters/Minions/Cyclops/Cyclops_Guardian/Data/PDE_Cyclops_Guardian"},
    {"Cyclops_Druid", tier = 3,    "/Game/Characters/Minions/Cyclops/Cyclops_Druid/Data/PDE_Cyclops_Druid"},
    {"Elemental_Earth", tier = 3,  "/Game/Characters/Minions/Elementals/Earth/Elemental_Earth/Data/PDE_Elemental_Earth"},
    {"Elemental_Fire", tier = 3,   "/Game/Characters/Minions/Elementals/Fire/Elemental_Fire/Data/PDE_Elemental_Fire"},
}
local SETTINGS = BIN .. "Mods/JWEndless/settings.txt"
local STEP_MS = 500

local logfile = io.open(BIN .. "JW_Endless_log.txt", "w")
local function log(s)
    if logfile then logfile:write(os.date("%H:%M:%S ") .. s .. "\n"); logfile:flush() end
end
log("JWEndless v4 loaded (random new enemy types from wave 1)")

local function read_settings()
    local f = io.open(SETTINGS, "r")
    if not f then return "defaults (no settings file)" end
    local t = {}
    for line in f:lines() do
        local k, v = line:match("^%s*([%w_]+)%s*=%s*([%d%.]+)")
        if k then t[k] = tonumber(v) end
    end
    f:close()
    if t.health then TOUGHER = t.health / 100 end
    if t.extra then MORE = t.extra end
    if t.max_alive then MAX_ALIVE = t.max_alive end
    if t.from_wave then FROM = math.max(t.from_wave, 2) end
    if t.newtypes then NEWTYPES = t.newtypes end
    if t.newcount then NEW_COUNT = math.max(math.floor(t.newcount), 0) end
    if t.oldcount then OLD_COUNT = math.max(math.floor(t.oldcount), 0) end
    if t.starttypes then START_TYPES = math.max(math.floor(t.starttypes), 1) end
    if t.perwave then PER_WAVE = math.max(math.floor(t.perwave), 1) end
    if t.random then RANDOM = t.random end
    return "settings file"
end
local function steps(w) return math.max(w - FROM + 1, 0) end      -- how many times harder wave w is

local function valid(o) return o ~= nil and o:IsValid() end
local function name_of(o) local ok, n = pcall(function() return o:GetFullName() end); return ok and n or "?" end
local function inst(o) return valid(o) and not name_of(o):find("Default__", 1, true) end
local function loc(a) local ok, v = pcall(function() return a:K2_GetActorLocation() end); if ok and v then return v end end

local function game_state()
    for _, gs in ipairs(FindAllOf("RSTGameStateBase") or {}) do if inst(gs) then return gs end end
end
local function is_host()
    for _, gm in ipairs(FindAllOf("GameModeBase") or {}) do if inst(gm) then return true end end
    return false
end
local function is_enemy(a)
    if not inst(a) then return false end
    local n = name_of(a)
    if n:find("Hero") or n:find("PlayerController") or n:find("Wisp") or n:find("Sentinel") then return false end
    local okd, dying = pcall(function() return a.bActorIsBeingDestroyed end)
    if okd and dying then return false end
    local ok, c = pcall(function() return a:GetController() end)
    if ok and valid(c) and name_of(c):find("PlayerController") then return false end
    local okp, def = pcall(function() return a.PawnDefinition end)
    return okp and valid(def)
end

-- ---------- enemy health ----------
local PDES = {}             -- pawn definition name -> {def, orig}; kept across levels so originals are never lost
local scale = 1.0
local function set_health(sc)
    scale = sc
    for _, e in pairs(PDES) do
        if valid(e.def) then pcall(function() e.def.MaxHealth = e.orig * sc end) end
    end
end
local function note_def(def)
    local n = name_of(def)
    local e = PDES[n]
    if e then
        if e.def ~= def then e.def = def end
        if e.sc ~= scale then e.sc = scale; pcall(function() def.MaxHealth = e.orig * scale end) end
        return
    end
    local ok, h = pcall(function() return def.MaxHealth end)
    if ok and type(h) == "number" and h > 0 then
        PDES[n] = {def = def, orig = h, sc = scale}
        pcall(function() def.MaxHealth = h * scale end)
    end
end

-- ---------- extra enemies ----------
local S = nil               -- state of the current level
local function spawn_near(def, l)
    local best, bd = nil, 1e18
    for _, sp in ipairs(FindAllOf("BP_AISpawner_C") or {}) do
        if inst(sp) then
            local sl = loc(sp)
            if sl then
                local d = (sl.X - l.X) ^ 2 + (sl.Y - l.Y) ^ 2
                if d < bd then bd, best = d, sp end
            end
        end
    end
    if not best then return false end
    best.PawnDefinition = def
    best.MinSpawnCount = 1; best.MaxSpawnCount = 1
    best.bAllowRespawn = false; best.bIsActive = true; best.MaxAliveCount = 1000
    best.bActivateAtStart = true; best.NumInitiallySpawned = 0; best.MinRespawnDelay = 0.0
    best:OnDelayedSpawnTimer()
    return true
end

-- ---------- the ladder of new enemy types ----------
local LDEF = {}             -- ladder index -> loaded pawn definition (looked up fresh on every level)
local function ladder_def(i)
    local d = LDEF[i]
    if valid(d) then return d end
    local path = LADDER[i][2]; local full = path .. "." .. path:match("[^/]+$")
    d = StaticFindObject(full)
    if not valid(d) then pcall(function() LoadAsset(path) end); d = StaticFindObject(full) end
    if valid(d) then LDEF[i] = d; return d end
    return nil
end

local AVAIL = {}            -- ladder indexes that loaded on this level
local function queue_ladder(w)
    if NEWTYPES == 0 or w < 1 or #AVAIL == 0 then return end
    local top = math.min(START_TYPES + (w - 1) * PER_WAVE, #AVAIL)
    local newest = math.max(top - (w == 1 and START_TYPES or PER_WAVE) + 1, 1)
    if START_TYPES + (w - 2) * PER_WAVE >= #AVAIL and w > 1 then newest = top + 1 end   -- ladder done: no "new" ones
    local more = math.floor((w - 1) / GROW)
    local parts = {}
    for j = 1, top do
        local i = AVAIL[j]
        local n = ((j >= newest) and NEW_COUNT or OLD_COUNT) + more
        local def = ladder_def(i)
        if def and n > 0 then
            local dn = name_of(def)
            for _ = 1, n do table.insert(S.queue, {def = def, dn = dn, l = nil}) end
            parts[#parts + 1] = n .. " " .. LADDER[i][1]
        end
    end
    log("  new enemy types this wave: " .. table.concat(parts, ", "))
end

local function step()
    local gs = game_state()
    if not gs then S = nil; return end
    local lvl = name_of(gs)
    if not S or S.gs ~= gs then                      -- a new level: restore health, decide whether we run here
        set_health(1.0)
        local on = lvl:find("/Game/Levels/BaseGame/", 1, true) ~= nil and lvl:find("BossOnslaughts", 1, true) == nil and lvl:find("/Hub/", 1, true) == nil
        S = {gs = gs, on = on, wave = 0, seen = {}, mine = {}, queue = {}, acc = 0, extra = 0, waves_seen = 0}
        log("level " .. (lvl:match("/Game/[^%.]+") or lvl) .. ": " .. (on and "endless helper ON" or "not a base-game mission, idle"))
        LDEF = {}
        if on then
            local src = read_settings()
            log(string.format("  %s: health +%d%% per wave, %.2f extra per enemy per wave, max %d alive, harder from wave %d",
                src, math.floor(TOUGHER * 100 + 0.5), MORE, MAX_ALIVE, FROM))
            if NEWTYPES ~= 0 then
                AVAIL = {}
                local missing = {}
                for i = 1, #LADDER do                                                     -- load them now (loading screen)
                    if ladder_def(i) then AVAIL[#AVAIL + 1] = i else missing[#missing + 1] = LADDER[i][1] end
                end
                if RANDOM ~= 0 then
                    math.randomseed(os.time() + math.floor(os.clock() * 1000))
                    local order = {}
                    for _, i in ipairs(AVAIL) do order[#order + 1] = {i = i, t = LADDER[i].tier or 9, r = math.random()} end
                    table.sort(order, function(a, b) if a.t ~= b.t then return a.t < b.t end; return a.r < b.r end)
                    AVAIL = {}; for _, o in ipairs(order) do AVAIL[#AVAIL + 1] = o.i end
                end
                local names = {}; for _, i in ipairs(AVAIL) do names[#names + 1] = LADDER[i][1] end
                log("  ladder" .. (RANDOM ~= 0 and " (random)" or "") .. ": " .. table.concat(names, ", "))
                log(string.format("  new enemy types: ON, %d of %d types loaded%s; %d from wave 1, +%d per wave, new x%d, earlier x%d, +1 each every %d waves",
                    #AVAIL, #LADDER, #missing > 0 and (" (not loaded: " .. table.concat(missing, ", ") .. ")") or "",
                    START_TYPES, PER_WAVE, NEW_COUNT, OLD_COUNT, GROW))
            else log("  new enemy types: off") end
        end
    end
    if not S.on or not is_host() then return end
    -- the mission's wave
    local okw, cw, mw = pcall(function() return gs.CurrentWave, gs.MaxWave end)
    if okw and type(cw) == "number" and cw ~= S.wave then
        S.wave = cw
        set_health(1 + steps(cw) * TOUGHER)
        log(string.format("wave %d of %s: health x%.2f, %.2f extra per enemy (%d enemy types)",
            cw, tostring(mw), scale, steps(cw) * MORE, (function() local c = 0; for _ in pairs(PDES) do c = c + 1 end; return c end)()))
        if #S.queue > 0 then log("  dropped " .. #S.queue .. " queued extra enemies of the last wave") end
        S.queue = {}; S.live = false; S.acc = 0
        pcall(queue_ladder, cw)
    end
    -- new enemies
    local alive = 0
    for _, p in ipairs(FindAllOf("Character") or {}) do
        local okk, key = pcall(function() return p:GetAddress() end)
        if okk and key then
            local known = S.seen[key]
            if known == nil then
                known = is_enemy(p)
                S.seen[key] = known
                if known then
                    local l = loc(p)
                    if not l or (l.X == 0 and l.Y == 0) then S.seen[key] = nil   -- not placed yet: look again
                    else
                        local def = p.PawnDefinition
                        note_def(def)
                        local dn = name_of(def)
                        if (S.mine[dn] or 0) > 0 then          -- one of our extra copies
                            S.mine[dn] = S.mine[dn] - 1
                        else                                    -- a wave enemy
                            S.waves_seen = S.waves_seen + 1
                            if not S.live then S.live = true; log("  wave " .. tostring(S.wave) .. " has started (its enemies appear)") end
                            if #(S.starts or {}) < 40 then S.starts = S.starts or {}; table.insert(S.starts, {X = l.X, Y = l.Y}) end
                            if steps(S.wave) > 0 then
                                S.acc = S.acc + steps(S.wave) * MORE
                                local n = math.floor(S.acc); S.acc = S.acc - n
                                for _ = 1, n do table.insert(S.queue, {def = def, dn = dn, l = {X = l.X, Y = l.Y}}) end
                            end
                        end
                    end
                end
            elseif known then
                local okd, dying = pcall(function() return p.bActorIsBeingDestroyed end)
                if not (okd and dying) and valid(p) then alive = alive + 1 end
            end
        end
    end
    -- send a few queued copies per step
    local sent = 0
    while S.live and #S.queue > 0 and sent < 3 and alive + sent < MAX_ALIVE do
        local q = S.queue[1]
        if q.l == nil then
            if not S.starts or #S.starts == 0 then break end              -- no wave enemy seen yet: wait
            q.l = S.starts[math.random(#S.starts)]
        end
        table.remove(S.queue, 1)
        if valid(q.def) then
            local ok, r = pcall(spawn_near, q.def, q.l)
            if ok and r then
                S.mine[q.dn] = (S.mine[q.dn] or 0) + 1; S.extra = S.extra + 1; sent = sent + 1
                if S.extra <= 3 or S.extra % 50 == 0 then log("extra enemies spawned: " .. S.extra) end
            elseif not ok then log("spawn error: " .. tostring(r)) end
        end
    end
end

local function run_step()
    local ok, err = pcall(step)
    if not ok then log("step error " .. tostring(err)) end
end
if type(LoopInGameThreadWithDelay) == "function" then
    LoopInGameThreadWithDelay(STEP_MS, function() run_step(); return false end)
else
    local queued = false
    LoopAsync(STEP_MS, function()
        if queued then return false end
        queued = true
        ExecuteInGameThread(function() run_step(); queued = false end)
        return false
    end)
end
