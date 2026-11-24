-- JWBarricades: barricade walls for OMD Map Builder maps.
-- Installed by OMD Map Builder into Binaries\Win64\Mods\JWBarricades, next to barricades.txt (written at every build):
--   L <level> <vs>              one line per custom level (Level_JW_<id>); vs = 1 on VS levels
--   B <level> x y z yaw [g]     one line per barricade wall or gate cell: the cell centre and its floor top; g = the
--                               gate it belongs to (0 or missing: a barricade wall cell)
--   G <level> g x y z yaw w     one line per gate: its middle, floor top, yaw and width (the portcullis is built into
--                               the level there)
-- What a barricade wall is: a 3 m wooden block built into the level (the wall kit's wood column) with the game's own
-- barricade (BP_Barricade, 3.1 x 3.1 m = one cell) inside it, hidden.
-- On the host (or in a solo game), when one of our levels has loaded:
--   1. the barricade is placed at every B line of that level, given the barricade's trap definition and put on the
--      game state's barricade list, so blocked orcs walk up to it and smash it, like a barricade a player placed;
--   2. on non-VS levels, every new enemy gets the loose tag Status.PassedThreshold.Door. Orcs only take barricades as
--      targets when they carry it, and the game gives it when an orc walks through a door, which our maps don't
--      have. (On VS levels the JWVersus referee does this.)
-- On every PC (host and clients): when the barricade in a wooden block is broken (dead / no health left; the game
-- keeps broken barricades in the level), the block is hidden and loses its collision, so the way is open. If the
-- barricade gets its health back, the block comes back.
-- Gates: a portcullis (built into the level) over a run of cells, each with a hidden barricade. On every PC: when
-- any barricade of a gate breaks, the portcullis is hidden and loses its collision, and (on the host) the gate's other
-- barricades are removed, so the whole gate opens. A gate stays open for the rest of the level.
-- Log: Binaries\Win64\JW_Barricades_log.txt

local BIN = "C:/Program Files (x86)/Steam/steamapps/common/Orcs Must Die Deathtrap/OMDD/Binaries/Win64/"
local VERSION = 4
-- this mod's own folder (from where UE4SS loaded this file); BIN is only the fallback
local function mod_dir()
    local ok, src = pcall(function() return debug.getinfo(1, "S").source end)
    if not ok or type(src) ~= "string" then return nil end
    src = src:gsub("^@", ""):gsub("\\", "/")
    return src:match("^(.*)/[Ss]cripts/[^/]*$")
end
local MOD = mod_dir() or (BIN .. "Mods/JWBarricades")
local WIN64 = MOD:match("^(.*/)Mods/[^/]+$") or BIN
local LIST = MOD .. "/barricades.txt"
local logfile = io.open(WIN64 .. "JW_Barricades_log.txt", "w")
local function log(s)
    local line = os.date("%H:%M:%S ") .. tostring(s)
    if logfile then logfile:write(line .. "\n"); logfile:flush() end
    print("[JWBarricades] " .. tostring(s) .. "\n")
end
log("loaded v" .. VERSION .. ", list " .. LIST)

local BAR_PKG = "/Game/Traps/Barricade/BP/BP_Barricade"
local BAR_CLASS = BAR_PKG .. ".BP_Barricade_C"
local DEF_PKG = "/Game/Traps/Barricade/BP/DA_Barricade_Definition"
local DEF_OBJ = DEF_PKG .. ".DA_Barricade_Definition"
local DOOR_TAG = "Status.PassedThreshold.Door"
local WOOD_MESH = "Column_Square_1_1_Wood_SM"     -- the wooden block of a barricade wall (builder: mapv2 WOOD_BLOCK)
local GATE_MESH = "Portcullis_CastlePlaza_D_SM"   -- a gate's portcullis (builder: mapv2 PORTCULLIS)

local function valid(o) return o ~= nil and o:IsValid() end
local function name_of(o) local ok, n = pcall(function() return o:GetFullName() end); return ok and n or "?" end
local function inst(o)                      -- a real object in the level, not a class default object
    return valid(o) and not name_of(o):find("Default__", 1, true)
end
local function loc(a) local ok, v = pcall(function() return a:K2_GetActorLocation() end); if ok and v then return v end end

-- ---------- the list (re-read for every level, so a rebuild shows up after the next level load) ----------
local function read_list()
    local levels, bars, gates = {}, {}, {}
    local f = io.open(LIST, "r")
    if not f then return levels, bars, false, gates end
    for line in f:lines() do
        local k, lv, rest = line:match("^(%u)%s+(%S+)%s*(.*)$")
        if k == "L" then
            local vs, kz, np = rest:match("^(%S+)%s*(%S*)%s*(%S*)")
            levels[lv] = {vs = tonumber(vs) == 1, killz = tonumber(kz) or -400, pits = tonumber(np) or 0}
        elseif k == "B" then
            local x, y, z, yaw, g = rest:match("^(%S+)%s+(%S+)%s+(%S+)%s+(%S+)%s*(%S*)")
            if x then
                bars[lv] = bars[lv] or {}
                table.insert(bars[lv], {x = tonumber(x), y = tonumber(y), z = tonumber(z), yaw = tonumber(yaw) or 0, g = tonumber(g) or 0})
            end
        elseif k == "G" then
            local g, x, y, z, yaw, w = rest:match("^(%S+)%s+(%S+)%s+(%S+)%s+(%S+)%s+(%S+)%s*(%S*)")
            if g then
                gates[lv] = gates[lv] or {}
                table.insert(gates[lv], {g = tonumber(g), x = tonumber(x), y = tonumber(y), z = tonumber(z), yaw = tonumber(yaw) or 0, w = tonumber(w) or 0})
            end
        end
    end
    f:close()
    return levels, bars, true, gates
end

-- ---------- host / level ----------
local function is_host()                    -- the game mode only exists on the server (or in a solo game)
    for _, gm in ipairs(FindAllOf("GameModeBase") or {}) do if inst(gm) then return true end end
    return false
end
local function game_state()
    for _, gs in ipairs(FindAllOf("RSTGameStateBase") or {}) do if inst(gs) then return gs end end
end
-- which of our levels is loaded: from a rift actor's path (FindFirstOf("World") can return a streamed sublevel)
local function current_level()
    for _, r in ipairs(FindAllOf("RSTRift") or {}) do
        if inst(r) then
            local lv = name_of(r):match("(Level_JW_[^%.:]+)[%.:]")
            if lv then
                local ok, key = pcall(function() return r:GetAddress() end)
                return lv, r, ok and key or 0
            end
        end
    end
end

local LV = nil               -- state of the loaded level: {name, key, t, vs, bars, placed, tries, seen, blocks, ...}

-- ---------- what a barricade looks like to the engine (diagnostics, to compare ours with a player's) ----------
local function describe(a)
    local out = {}
    local function q(label, f) local ok, v = pcall(f); out[#out + 1] = label .. "=" .. (ok and tostring(v) or "?") end
    q("hidden", function() return a.bHidden end)
    q("beingPlaced", function() return a.bIsBeingPlaced end)
    q("sold", function() return a.bIsSold end)
    q("team", function() return a:GetTeam() end)
    q("owner", function() local o = a.TrapOwner; return o and o:IsValid() and "yes" or "none" end)
    q("meshVisible", function() return a.MeshComponent:IsVisible() end)
    q("meshScale", function() local v = a.MeshComponent.RelativeScale3D; return string.format("%.2f", v.X) end)
    q("targetScale", function() local v = a.TargetMeshScale; return string.format("%.2f", v.X) end)
    q("boxCollision", function() return a.GeneratedBoxCollision:GetCollisionEnabled() end)
    q("actorCollision", function() return a:GetActorEnableCollision() end)
    q("grid", function() local g = a.MainTrapGrid; return g and g:IsValid() and "yes" or "none" end)
    return table.concat(out, " ")
end

-- ---------- wooden blocks (on every PC): hidden when their barricade is gone ----------
local function find_blocks()
    local out = {}
    for _, m in ipairs(FindAllOf("StaticMeshActor") or {}) do
        if inst(m) then
            local ok, mesh = pcall(function() return m.StaticMeshComponent.StaticMesh:GetFullName() end)
            if ok and mesh and mesh:find(WOOD_MESH, 1, true) then
                local l = loc(m)
                if l then
                    for _, b in ipairs(LV.bars) do
                        if (b.g or 0) == 0 and math.abs(l.X - b.x) < 60 and math.abs(l.Y - b.y) < 60 and math.abs(l.Z - b.z) < 120 then
                            table.insert(out, {m = m, x = l.X, y = l.Y, z = l.Z, had = false, gone = false}); break
                        end
                    end
                end
            end
        end
    end
    return out
end
local function all_barricades()
    local out = {}
    for _, t in ipairs(FindAllOf("RSTTrap") or {}) do
        if inst(t) and name_of(t):find("BP_Barricade", 1, true) then
            local okd, dying = pcall(function() return t.bActorIsBeingDestroyed end)
            local oks, sold = pcall(function() return t.bIsSold end)
            if not (okd and dying) and not (oks and sold) then local l = loc(t); if l then table.insert(out, {t = t, x = l.X, y = l.Y, z = l.Z}) end end
        end
    end
    return out
end
-- a barricade's health component: its HealthComponent property, else the RSTHealthComponent whose owner it is
local function health_of(t)
    local ok, hc = pcall(function() return t.HealthComponent end)
    if ok and valid(hc) then return hc end
    for _, h in ipairs(FindAllOf("RSTHealthComponent") or {}) do
        local okk, o = pcall(function() return h:GetOwner() end)
        if okk and valid(o) and o:GetAddress() == t:GetAddress() then return h end
    end
end
-- broken: dead or dying, or no health left. A broken barricade stays in the level (the game doesn't remove it).
local function broken(k)
    if not valid(k.bar) then return true, "gone" end
    if not (k.hc and valid(k.hc)) then k.hc = health_of(k.bar) end
    if not k.hc then return false, "no health component" end
    local okd, dead = pcall(function() return k.hc:IsDeadOrDying() end)
    local okh, hp = pcall(function() return k.hc:GetHealth() end)
    k.hp = okh and hp or k.hp
    if okd and dead then return true, "dead" end
    if okh and hp and hp <= 0 then return true, "no health" end
    return false, okh and string.format("health %.0f", hp) or "health ?"
end
local function show_block(k, on)
    local ok, e = pcall(function()
        k.m:SetActorHiddenInGame(not on)
        k.m:SetActorEnableCollision(on)
    end)
    return ok, e
end
local function update_blocks()
    if not LV.blocks then
        LV.blocks = find_blocks()
        log(string.format("wooden blocks found: %d of %d", #LV.blocks, #LV.bars))
    end
    if #LV.blocks == 0 then return end
    local list = nil
    for _, k in ipairs(LV.blocks) do
        if not k.bar then                                       -- find the barricade inside this block (once)
            list = list or all_barricades()
            for _, b in ipairs(list) do
                if math.abs(b.x - k.x) < 120 and math.abs(b.y - k.y) < 120 and math.abs(b.z - k.z) < 200 then
                    k.bar = b.t; k.hc = health_of(b.t)
                    LV.linked = (LV.linked or 0) + 1
                    if LV.linked <= 2 then
                        local okm, mh = pcall(function() return k.hc:GetMaxHealth() end)
                        log(string.format("block at %.0f %.0f has its barricade, health component %s, max health %s", k.x, k.y,
                            k.hc and "found" or "NOT found", okm and string.format("%.0f", mh) or "?"))
                    end
                    break
                end
            end
        end
        if k.bar then
            local br, why = broken(k)
            if br ~= (k.down or false) then                     -- changed: broken -> hide the block, repaired -> show it again
                k.down = br
                local ok, e = show_block(k, not br)
                LV.broken = (LV.broken or 0) + (br and 1 or -1)
                log(string.format("barricade wall at %.0f %.0f %s (%s): wooden block %s; broken now: %d", k.x, k.y,
                    br and "BROKE" or "is back", why, ok and (br and "hidden" or "shown") or ("FAILED: " .. tostring(e)), LV.broken))
            end
        end
    end
end
-- ---------- gates (on every PC): the portcullis goes when any of the gate's barricades breaks ----------
local function find_portcullises()
    local found = 0
    for _, m in ipairs(FindAllOf("StaticMeshActor") or {}) do
        if inst(m) then
            local ok, mesh = pcall(function() return m.StaticMeshComponent.StaticMesh:GetFullName() end)
            if ok and mesh and mesh:find(GATE_MESH, 1, true) then
                local l = loc(m)
                if l then
                    for _, G in ipairs(LV.gates) do
                        if not G.m and math.abs(l.X - G.x) < 80 and math.abs(l.Y - G.y) < 80 and math.abs(l.Z - G.z) < 150 then
                            G.m = m; found = found + 1; break
                        end
                    end
                end
            end
        end
    end
    return found
end
local function update_gates()
    if not LV.gcells then
        LV.gcells = {}
        for _, b in ipairs(LV.bars) do
            if (b.g or 0) > 0 then table.insert(LV.gcells, {x = b.x, y = b.y, z = b.z, g = b.g}) end
        end
        local n = find_portcullises()
        log(string.format("gates: %d, gate cells %d, portcullises found %d", #LV.gates, #LV.gcells, n))
    end
    if #LV.gcells == 0 then return end
    local list = nil
    local byg = {}
    for _, G in ipairs(LV.gates) do byg[G.g] = G end
    for _, k in ipairs(LV.gcells) do
        if not k.bar then
            list = list or all_barricades()
            for _, b in ipairs(list) do
                if math.abs(b.x - k.x) < 120 and math.abs(b.y - k.y) < 120 and math.abs(b.z - k.z) < 200 then
                    k.bar = b.t; k.hc = health_of(b.t); k.linked = true; break
                end
            end
        end
        local G = byg[k.g]
        if G and not G.open and k.linked then
            local br, why = broken(k)
            if br then
                G.open = true
                local ok, e = true, nil
                if G.m and valid(G.m) then
                    ok, e = pcall(function() G.m:SetActorHiddenInGame(true); G.m:SetActorEnableCollision(false) end)
                end
                log(string.format("gate %d BROKE (%s at %.0f %.0f): portcullis %s", k.g, why, k.x, k.y,
                    G.m and (ok and "hidden" or ("FAILED: " .. tostring(e))) or "not found"))
                if is_host() then                                   -- the gate's other barricades go too: the whole gate opens
                    local gs, n = game_state(), 0
                    for _, q in ipairs(LV.gcells) do
                        if q.g == k.g and q ~= k and q.bar and valid(q.bar) then
                            pcall(function() if gs then gs:UpdateBarricadesArray(q.bar, false) end end)
                            local okd = pcall(function() q.bar:K2_DestroyActor() end)
                            if okd then n = n + 1 end
                        end
                    end
                    log(string.format("gate %d: removed %d more barricade(s)", k.g, n))
                end
            end
        end
    end
end

-- player-placed barricades: logged once each with the same details as ours (to see what ours are missing)
local function note_players_barricades()
    for _, b in ipairs(all_barricades()) do
        local ok, key = pcall(function() return b.t:GetAddress() end)
        if ok and not LV.mine[key] and not LV.noted[key] then
            LV.noted[key] = true
            log("a player's barricade: " .. describe(b.t))
        end
    end
end

-- ---------- placing barricades ----------
local function find_or_load(obj, pkg)
    local o = StaticFindObject(obj)
    if not valid(o) and LoadAsset then pcall(function() LoadAsset(pkg) end); o = StaticFindObject(obj) end
    return valid(o) and o or nil
end
local function transform(b)
    local h = math.rad(b.yaw or 0) / 2
    return {Rotation = {X = 0.0, Y = 0.0, Z = math.sin(h), W = math.cos(h)},
            Translation = {X = b.x, Y = b.y, Z = b.z}, Scale3D = {X = 1.0, Y = 1.0, Z = 1.0}}
end

local function place_all()
    local cls = find_or_load(BAR_CLASS, BAR_PKG)
    local def = find_or_load(DEF_OBJ, DEF_PKG)
    log(string.format("barricade class %s, definition %s", cls and "found" or "MISSING", def and "found" or "MISSING"))
    if not cls then return false end
    local world = LV.rift:GetWorld()
    local gsl = StaticFindObject("/Script/Engine.Default__GameplayStatics")
    local gs = game_state()
    local made, listed, how = 0, 0, {}
    for i, b in ipairs(LV.bars) do
        local a, mode = nil, nil
        -- 1) deferred spawn: the trap definition is set before the barricade starts (its health and abilities come
        --    from the definition when it begins play)
        local ok, err = pcall(function()
            local t = transform(b)
            a = gsl:BeginDeferredActorSpawnFromClass(world, cls, t, 1, nil, 0)
            if valid(a) then
                if def then a.TrapDefinition = def end
                gsl:FinishSpawningActor(a, t, 0)
                mode = "deferred"
            end
        end)
        -- 2) plain spawn, definition set afterwards
        if not valid(a) then
            if i <= 2 then log("deferred spawn failed: " .. tostring(err)) end
            local ok2, err2 = pcall(function()
                a = world:SpawnActor(cls, {X = b.x, Y = b.y, Z = b.z}, {Pitch = 0.0, Yaw = b.yaw or 0.0, Roll = 0.0})
                if valid(a) and def then a.TrapDefinition = def end
                mode = "spawn"
            end)
            if not ok2 and i <= 2 then log("spawn failed: " .. tostring(err2)) end
        end
        if valid(a) then
            made = made + 1; how[mode] = (how[mode] or 0) + 1
            local okk, key = pcall(function() return a:GetAddress() end); if okk then LV.mine[key] = true end
            if i == 1 then log("our barricade as spawned: " .. describe(a)) end
            -- the wooden block is what players see: the barricade's own mesh stays hidden
            pcall(function() a.MeshComponent:SetVisibility(false, true) end)
            -- the game state's barricade list: what blocked orcs look for
            if gs then
                local okl, el = pcall(function() gs:UpdateBarricadesArray(a, true) end)
                if okl then listed = listed + 1 elseif i <= 2 then log("UpdateBarricadesArray failed: " .. tostring(el)) end
            end
            if i <= 2 then
                local l = loc(a)
                local okd, d = pcall(function() return a.TrapDefinition end)
                log(string.format("barricade %d: %s at %.0f %.0f %.0f (wanted %.0f %.0f %.0f), definition %s", i,
                    name_of(a):match("[^%.:]+$") or "?", l and l.X or 0, l and l.Y or 0, l and l.Z or 0, b.x, b.y, b.z,
                    okd and valid(d) and (name_of(d):match("[^%.]+$") or "?") or "none"))
            end
            table.insert(LV.actors, a)
        end
    end
    local hs = {}
    for k, v in pairs(how) do hs[#hs + 1] = k .. " " .. v end
    log(string.format("placed %d of %d barricades (%s), %d on the game's barricade list", made, #LV.bars, table.concat(hs, ", "), listed))
    return made > 0
end

-- ---------- door tag for enemies (non-VS levels) ----------
local function is_enemy(a)
    local n = name_of(a)
    if n:find("Hero") or n:find("PlayerController") or n:find("Wisp") or n:find("Sentinel") then return false end
    local ok, c = pcall(function() return a:GetController() end)
    if ok and valid(c) and name_of(c):find("PlayerController") then return false end
    return true
end
local function door_tags()
    local n = 0
    for _, p in ipairs(FindAllOf("Character") or {}) do
        local ok, key = pcall(function() return p:GetAddress() end)
        if ok and key and LV.seen[key] == nil and inst(p) then
            local l = loc(p)
            if l and (l.X ~= 0 or l.Y ~= 0) then                 -- placed in the level (not still spawning)
                LV.seen[key] = false
                if is_enemy(p) then
                    local okt, e = pcall(function()
                        local asc = p:GetRSTAbilitySystemComponent()
                        if not valid(asc) then return "no ability component" end
                        asc:AddTimedLooseTag({TagName = FName(DOOR_TAG)}, true, 100000.0)
                        return "ok"
                    end)
                    LV.seen[key] = true; n = n + 1
                    LV.tagged = (LV.tagged or 0) + 1
                    if LV.tagged <= 3 or not okt then log("door tag -> " .. (name_of(p):match("[^%.]+$") or "?") .. ": " .. (okt and tostring(e) or ("failed: " .. tostring(e)))) end
                end
            end
        end
    end
    if n > 0 and LV.tagged % 50 < n then log("door tags given: " .. LV.tagged) end
end

-- ---------- death pits (normal custom maps; on VS maps the referee does it) ----------
-- anyone (hero or enemy) below the map's lowest floor (killz, from the builder) dies at once; heroes respawn as after
-- any fall. Host only, once a second.
local function pit_kill()
    for _, cls in ipairs({"RSTAICharacter", "RSTPlayerCharacter"}) do
        for _, p in ipairs(FindAllOf(cls) or {}) do
            pcall(function()
                if not inst(p) then return end
                local l = p:K2_GetActorLocation()
                if l.Z > LV.killz then return end
                local hc = p.HealthComponent
                if hc:IsDeadOrDying() then return end
                hc:DamageSelfDestruct(true, nil)
                LV.pitkills = (LV.pitkills or 0) + 1
                if LV.pitkills <= 5 then log(string.format("pit kill: %s at z %.0f", name_of(p):match("[^%.]+$"), l.Z)) end
            end)
        end
    end
end

-- ---------- main loop ----------
local tick = 0
local function step()
    tick = tick + 1
    local lv, rift, key = current_level()
    if not lv then
        if LV then log("left " .. LV.name); LV = nil end
        return
    end
    if not LV or LV.name ~= lv or LV.key ~= key then
        local levels, bars, found, gates = read_list()
        LV = {name = lv, key = key, rift = rift, t = tick, vs = levels[lv] and levels[lv].vs or false,
              killz = levels[lv] and levels[lv].killz or -400, pits = levels[lv] and levels[lv].pits or 0,
              bars = bars[lv] or {}, gates = gates[lv] or {}, placed = false, tries = 0, seen = {}, actors = {}, mine = {}, noted = {}}
        log(string.format("level %s: %d barricade(s), %d gate(s), %d pit cell(s)%s%s", lv, #LV.bars, #LV.gates, LV.pits, LV.vs and ", VS level" or "",
            found and "" or " (no barricades.txt)"))
    end
    if #LV.bars > 0 and tick - LV.t >= 5 then
        local ok, e = pcall(update_blocks); if not ok then log("blocks error " .. tostring(e)) end
        if #LV.gates > 0 then local ok2, e2 = pcall(update_gates); if not ok2 then log("gates error " .. tostring(e2)) end end
    end
    if not is_host() then return end                          -- clients get the barricades from the host
    if tick % 5 == 0 then pcall(note_players_barricades) end
    if LV.placed and tick % 30 == 0 and #LV.actors > 0 then             -- now and then: how ours are doing
        local alive = 0
        for _, a in ipairs(LV.actors) do if inst(a) then alive = alive + 1 end end
        if alive ~= LV.last_alive then
            LV.last_alive = alive
            log(string.format("our barricades in the level: %d of %d; first: %s", alive, #LV.actors, valid(LV.actors[1]) and describe(LV.actors[1]) or "gone"))
        end
    end
    if not LV.placed and #LV.bars > 0 and tick - LV.t >= 3 and LV.tries < 3 then
        LV.tries = LV.tries + 1
        local ok, res = pcall(place_all)
        if not ok then log("placing failed: " .. tostring(res)) end
        LV.placed = ok and res or false
        if not LV.placed and LV.tries >= 3 then log("giving up on barricades for this level") end
    end
    if not LV.vs then door_tags() end
    if not LV.vs and LV.pits > 0 then pit_kill() end          -- VS levels: the referee does this
end

-- start slowly: nothing in the first 40 s (calling into the engine during startup hung the game for the referee),
-- then one step a second on the game thread
local wait, STEP_MS, queued = 40, 1000, false
local function run_step()
    local ok, err = pcall(step)
    if not ok then log("step error " .. tostring(err)) end
end
if type(LoopInGameThreadWithDelay) == "function" then
    LoopInGameThreadWithDelay(STEP_MS, function()
        if wait > 0 then wait = wait - 1; return false end
        run_step(); return false
    end)
else
    LoopAsync(STEP_MS, function()
        if wait > 0 then wait = wait - 1; return false end
        if queued then return false end
        queued = true
        ExecuteInGameThread(function() run_step(); queued = false end)
        return false
    end)
end
