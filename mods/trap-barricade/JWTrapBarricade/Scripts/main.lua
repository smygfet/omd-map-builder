-- JWTrapBarricade v28: the Trap Barricade (a new trap in the trap book that places the Rift Barricade, recoloured fire red).
-- A placed trap takes its data (health, price) from its actor class, i.e. the Rift Barricade's. So the mod recognises a
-- Trap Barricade by the hotbar item it was placed from (DA_TrapBarricade_InventoryItem selected), and while that item is
-- selected the Rift Barricade's placement cost is set to the Trap Barricade's (put back when another item is selected).
-- After placement its health is set to 100. Every other barricade is left alone.
-- Each placed Trap Barricade:
--   * is stretched to 3 m and gets an invisible solid body (trap grids only work with something solid behind them)
--   * gets five trap grids made from the game's Gnome Sentinel (the grid the game itself spawns mid-mission): one on
--     top for floor traps, one on each side for wall traps
--   * when enemies break it: its traps are removed with Sell and the money that refund pays is taken back (you lose
--     the traps and what they cost), then the grids, the body and the barricade go too
--   * when you sell it yourself: its traps are sold normally (money kept)
--   * looks like the normal wooden barricade: once, when placed, its two mesh components get the normal barricade's
--     materials (Barricade_Wood_INST / Barricade_Metal_INST) and its blue idle sparkles are switched off.
--     It also does not buff the barricades next to it (the Rift Barricade's blue neighbour buff, QueryBox1/2, is
--     switched off on it). Ordinary Rift Barricades stay blue. (v18-v19 painted every second by searching the whole level: that lagged.)
--   * v24: shots and aim go through its invisible body and its stretched model (they blocked shooting at orcs near it);
--     orcs are still blocked
--   * v25: the player can walk up to it: its invisible body and every part of its five trap-spot actors ignore the
--     player (RSTPlayerCharacter, channel 22); only the visible model blocks the player, as on a normal barricade
--     (v26: the trap-spot actors' parts are found by owner among all PrimitiveComponents, once per barricade;
--     K2_GetComponentsByClass gave nothing in v25). v27: the barricade's own parts other than its visible model
--     (StaticMeshComponent, MeshComponent) ignore the player too (2 of 4 sides still blocked in v26), and every part of
--     the barricade, its body and trap spots is logged with its collision and size. v28: the culprit was the model's
--     MeshComponent (skeletal physics shapes can't stretch in Z only, so they grow 2.7x wider too); it now ignores the
--     player, and the invisible body (exactly the barricade's size) blocks the player instead
-- History of the tests (v1-v14): see the project note claude/trap-barricade.md. Log: Binaries\Win64\JW_TrapBarricade_log.txt
local BIN = "C:/Program Files (x86)/Steam/steamapps/common/Orcs Must Die Deathtrap/OMDD/Binaries/Win64/"
local CLASSES = {"BP_Rift_Barricade_C"}
local OUR_ITEM = "DA_TrapBarricade_InventoryItem"   -- the Trap Barricade's item (trap book / hotbar)
local TB_COST = 1500                                -- its placement cost (the Rift Barricade's own is 4000)
local TB_HEALTH = 100.0                             -- its health
local RIFT_DEF = "/Game/Traps/Barricade/BP/DA_Rift_Barricade_Definition.DA_Rift_Barricade_Definition"
local GRID_CLASS = "/Game/Environments/Shared/BP_OMDTrapGrid_Blank.BP_OMDTrapGrid_Blank_C"
local STEP_MS = 200
local OUT = 2.0               -- grids sit this far outside the barricade's faces (cm)
local MESH_H = 111.0          -- the barricade mesh's height (SM_Barricade_100_Health bounds: 310 x 310 x 111 cm)
local TALL = 300.0            -- the trap barricade's height: room for one row of wall traps

local logfile = io.open(BIN .. "JW_TrapBarricade_log.txt", "w")
local function log(s) if logfile then logfile:write(os.date("%H:%M:%S ") .. s .. "\n"); logfile:flush() end end
log("JWTrapBarricade v28 loaded")

local function get(o, k) local ok, v = pcall(function() return o[k] end); if ok then return v end end
local function valid(o) return o ~= nil and pcall(function() return o:IsValid() end) and o:IsValid() end
local function name_of(o) local ok, n = pcall(function() return o:GetFullName() end); return ok and n or "?" end
local function addr(o) local ok, a = pcall(function() return o:GetAddress() end); return ok and a or nil end
local function vec(v) return v and string.format("(%.0f, %.0f, %.0f)", v.X, v.Y, v.Z) or "?" end

local function is_host()
    for _, gm in ipairs(FindAllOf("GameModeBase") or {}) do
        if valid(gm) and not name_of(gm):find("Default__", 1, true) then return true end
    end
    return false
end
local function owned(t)
    local ok, v = pcall(function() local p = t.TrapOwner:Get(); return p and p:IsValid() end)
    if ok and v then return true end
    if get(t, "bIsOwnedByLocalPlayer") == true then return true end
    local i = get(t, "TrapOwnerPlayerIndex")
    return type(i) == "number" and i >= 0 and valid(get(t, "TrapDefinition"))
end
-- broken by enemies (dead / no health) is checked BEFORE sold: a broken barricade is also flagged bIsSold by the game
-- a barricade's health component: its HealthComponent property, else the RSTHealthComponent whose owner it is
-- (the same lookup as the barricade-walls mod JWBarricades; BP_Barricade has no HealthComponent property)
local function health_of(t)
    local ok, hc = pcall(function() return t.HealthComponent end)
    if ok and valid(hc) then return hc end
    local ta = addr(t)
    for _, h in ipairs(FindAllOf("RSTHealthComponent") or {}) do
        local okk, o = pcall(function() return h:GetOwner() end)
        if okk and valid(o) and addr(o) == ta then return h end
    end
end
local function broken(t, rec)
    if not valid(t) then return true, "gone" end
    if rec and not (rec.hc and valid(rec.hc)) then rec.hc = health_of(t) end
    local hc = rec and rec.hc or health_of(t)
    if rec and valid(hc) then
        local okh, hp = pcall(function() return hc:GetHealth() end)
        if okh and type(hp) == "number" and hp ~= rec.hp then
            if rec.hp == nil then
                local okm, mh = pcall(function() return hc:GetMaxHealth() end)
                log(string.format("barricade health found: %.0f of %s", hp, okm and string.format("%.0f", mh) or "?"))
            elseif hp < rec.hp then
                log(string.format("barricade hit: health %.0f", hp))
            end
            rec.hp = hp
        end
    elseif rec and not rec.nohc then
        rec.nohc = true; log("barricade: NO health component found")
    end
    if valid(hc) then
        local okd, dead = pcall(function() return hc:IsDeadOrDying() end)
        if okd and dead then return true, "broken" end
        local okh, hp = pcall(function() return hc:GetHealth() end)
        if okh and type(hp) == "number" and hp <= 0 then return true, "broken" end
    end
    if get(t, "bIsSold") == true then return true, "sold" end
    if get(t, "bActorIsBeingDestroyed") == true then return true, "gone" end
    return false
end

-- refunds to take back: {ps, last = coins last seen, left = coins still to take, untill = os.clock() deadline}
CLAW = {}
local function clawback()
    for i = #CLAW, 1, -1 do
        local c = CLAW[i]
        local coins = valid(c.ps) and get(c.ps, "Coin") or nil
        if coins then
            local up = coins - c.last
            if up > 0 then
                local take = math.min(up, c.left)
                local okt = pcall(function() c.ps:SpendCoin(take) end)
                if not okt then pcall(function() c.ps.Coin = math.max(0, coins - take) end) end
                c.left = c.left - take
                log(string.format("  %s: refund of %d arrived, taken back (%d left to take)", c.what, take, c.left))
            end
            c.last = valid(c.ps) and get(c.ps, "Coin") or coins
        end
        if c.left <= 0 or os.clock() > c.untill or not coins then
            if c.left > 0 then log(string.format("  %s: %d of the refund never arrived (nothing more taken)", c.what, c.left)) end
            table.remove(CLAW, i)
        end
    end
end

-- remove a trap the game's own way (Sell: also removes its visible copy); keep_money = false takes the refund back
local function remove_trap(t, keep_money)
    local refund = 0
    pcall(function() refund = t:GetRefundValue() end)
    local ps = nil
    pcall(function() ps = t.TrapOwner:Get() end)
    local before = valid(ps) and get(ps, "Coin") or nil
    local oks, sold = pcall(function() return t:Sell() end)
    local after = valid(ps) and get(ps, "Coin") or nil
    local how
    if oks and sold then
        how = "sold"
        if not keep_money and valid(ps) and refund > 0 and before then
            -- the refund can arrive a moment after Sell: watch this player's coins for 3 s and take back what arrives
            CLAW[#CLAW + 1] = {ps = ps, last = before, left = refund, untill = os.clock() + 3.0, what = name_of(t):match("BP_[%w_]+") or "trap"}
            how = how .. ", refund " .. refund .. " will be taken back"
        end
    else
        how = "Sell refused (" .. tostring(oks and sold or sold) .. "): destroyed and hidden"
        pcall(function() t:SetActorHiddenInGame(true) end)
        pcall(function() t:K2_DestroyActor() end)
    end
    return string.format("%s (refund value %d, coins %s -> %s)", how, refund, tostring(before), tostring(valid(ps) and get(ps, "Coin") or "?"))
end

local grid_cls = nil
local function grid_class()
    if valid(grid_cls) then return grid_cls end
    grid_cls = StaticFindObject(GRID_CLASS)
    if not valid(grid_cls) then pcall(function() LoadAsset("/Game/Environments/Shared/BP_OMDTrapGrid_Blank") end); grid_cls = StaticFindObject(GRID_CLASS) end
    return valid(grid_cls) and grid_cls or nil
end

-- one grid: centre (world), rotation, box extent (local: X = outward normal, Y and Z = the face), placement type
-- (1 floor, 2 wall, 4 ceiling), same layout as the map builder's grids
local used = {}       -- spare grids already borrowed (address -> true)
local function coll(box)
    local okc, ce = pcall(function() return box:GetCollisionEnabled() end)
    local okp, pn = pcall(function() return box:GetCollisionProfileName():ToString() end)
    local okm, mob = pcall(function() return box.Mobility end)
    return string.format("collision %s profile %s mobility %s", okc and tostring(ce) or "?", okp and tostring(pn) or "?", okm and tostring(mob) or "?")
end
local function plane_info(box)
    local p = get(box, "TrapGridRevealPlane")
    if not valid(p) then return "reveal plane: none" end
    local okl, pl = pcall(function() return p:K2_GetComponentLocation() end)
    local oks, ps = pcall(function() return p:K2_GetComponentScale() end)
    local okm, mesh = pcall(function() return name_of(p.StaticMesh) end)
    local okc, ce = pcall(function() return p:GetCollisionEnabled() end)
    local okp, pn = pcall(function() return p:GetCollisionProfileName():ToString() end)
    local okv, vis = pcall(function() return p:IsVisible() end)
    return string.format("reveal plane at %s scale %s mesh %s collision %s profile %s visible %s", okl and vec(pl) or "?",
        oks and string.format("(%.2f, %.2f, %.2f)", ps.X, ps.Y, ps.Z) or "?", okm and (mesh:match("[^%.]+$") or mesh) or "?",
        okc and tostring(ce) or "?", okp and tostring(pn) or "?", okv and tostring(vis) or "?")
end
local function spare_grid()
    for _, gr in ipairs(FindAllOf("BP_OMDTrapGrid_Blank_C") or {}) do
        local a = addr(gr)
        if a and not used[a] and valid(gr) and not name_of(gr):find("Default__", 1, true) then
            local l = gr:K2_GetActorLocation()
            if math.abs(l.X) < 1 and math.abs(l.Y) < 1 and math.abs(l.Z) < 1 then used[a] = true; return gr end
        end
    end
end
-- v8: plain map grids (BP_OMDTrapGrid_Blank) only work when they come with the level. The Gnome Sentinel
-- (BP_RSTGnomeSentinel, a C++ RSTGnomeSentinel grid) is made to be spawned mid-mission, and traps go on it.
-- So each face is a Gnome Sentinel: its box template gets our size, type and an identity transform before
-- spawning (put back afterwards), the actor is spawned at the face, and its balloon, gnome, sound and FX are removed.
local GNOME = "/PostContent1/Traps/Sentinel_Gnome/BP/BP_RSTGnomeSentinel"
local GNOME_CLASS = GNOME .. ".BP_RSTGnomeSentinel_C"
local GNOME_BOX = GNOME_CLASS .. ":RSTTrapGridBox_GEN_VARIABLE"
local gnome_cls = nil
local gnome_tries = 0
local function gnome_class()
    gnome_cls = StaticFindObject(GNOME_CLASS)
    if valid(gnome_cls) then return gnome_cls end
    gnome_tries = gnome_tries + 1
    local steps = {}
    -- the gnome lives in the PostContent1 game feature: load its package (several ways; one is enough)
    for _, p in ipairs({GNOME, GNOME_CLASS, GNOME .. "_C"}) do
        local ok, err = pcall(function() LoadAsset(p) end)
        steps[#steps + 1] = p:match("[^/]+$") .. (ok and " ok" or (" failed: " .. tostring(err)))
        gnome_cls = StaticFindObject(GNOME_CLASS)
        if valid(gnome_cls) then break end
    end
    if not valid(gnome_cls) then
        pcall(function()
            local ksl = StaticFindObject("/Script/Engine.Default__KismetSystemLibrary")
            local soft = ksl:MakeSoftClassPath(GNOME_CLASS)
            steps[#steps + 1] = "soft class path made"
        end)
        gnome_cls = StaticFindObject(GNOME_CLASS)
    end
    if gnome_tries <= 3 then log("  loading the gnome sentinel class: " .. table.concat(steps, "; ") .. " -> " .. (valid(gnome_cls) and "FOUND" or "not found")) end
    return valid(gnome_cls) and gnome_cls or nil
end
local VISUALS = {"SkeletalMesh", "StaticMesh", "NS_Gnome_Balloon", "Audio_Crystal_LP", "Audio_Flame_LP"}
local PLAYER_CH = 22        -- RSTPlayerCharacter (GameTraceChannel9)
local function let_player_through_all(actors)
    local own, n, names = {}, 0, {}
    for _, a in ipairs(actors) do local ad = valid(a) and addr(a); if ad then own[ad] = true end end
    for _, c in ipairs(FindAllOf("PrimitiveComponent") or {}) do
        local o = nil; pcall(function() o = c:GetOwner() end)
        local oa = valid(o) and addr(o)
        if oa and own[oa] then
            if pcall(function() c:SetCollisionResponseToChannel(PLAYER_CH, 0) end) then
                n = n + 1
                local cn = name_of(c):match("[^%.:]+$") or "?"; names[cn] = true
            end
        end
    end
    local list = {}; for k in pairs(names) do list[#list + 1] = k end
    return n, table.concat(list, ", ")
end

local function describe_parts(actors, keep_mesh_of)
    local own = {}
    for k, a in pairs(actors) do local ad = valid(a) and addr(a); if ad then own[ad] = k end end
    local lines, changed = {}, 0
    for _, c in ipairs(FindAllOf("PrimitiveComponent") or {}) do
        local o = nil; pcall(function() o = c:GetOwner() end)
        local oa = valid(o) and addr(o)
        local who = oa and own[oa]
        if who then
            local cn = name_of(c):match("[^%.:]+$") or "?"
            local visible_model = (who == "barricade") and (cn == "StaticMeshComponent")   -- MeshComponent: too wide, see v28
            if who == "body" then visible_model = true end                                   -- the body blocks the player
            if not visible_model then
                if pcall(function() c:SetCollisionResponseToChannel(PLAYER_CH, 0) end) then changed = changed + 1 end
            end
            local ce = "?"; pcall(function() ce = tostring(c:GetCollisionEnabled()) end)
            local rp = "?"; pcall(function() rp = tostring(c:GetCollisionResponseToChannel(PLAYER_CH)) end)
            local rpn = "?"; pcall(function() rpn = tostring(c:GetCollisionResponseToChannel(3 - 1)) end)
            local bo = "?"
            pcall(function() local b = c.Bounds; bo = vec(b.Origin) .. " half " .. vec(b.BoxExtent) end)
            lines[#lines + 1] = string.format("    %s.%s: collision %s, player %s, bounds %s%s", who, cn, ce, rp, bo, visible_model and " (visible model, kept)" or "")
        end
    end
    return changed, lines
end

local function let_player_through(actor)
    local n = 0
    local cls = StaticFindObject("/Script/Engine.PrimitiveComponent")
    if not valid(cls) then return 0 end
    local ok, arr = pcall(function() return actor:K2_GetComponentsByClass(cls) end)
    if ok and arr then
        pcall(function() arr:ForEach(function(_, e)
            local c = e:get()
            if valid(c) and pcall(function() c:SetCollisionResponseToChannel(PLAYER_CH, 0) end) then n = n + 1 end
        end) end)
    end
    return n
end

local function spawn_grid(world, c, rot, ext, ptype, tag)
    local cls = gnome_class(); if not cls then log("  " .. tag .. ": gnome sentinel class not found"); return nil end
    local t = StaticFindObject(GNOME_BOX)
    local saved = nil
    if valid(t) then
        saved = {e = get(t, "BoxExtent"), ty = get(t, "TrapPlacementTypes"), l = get(t, "RelativeLocation"), r = get(t, "RelativeRotation")}
        pcall(function() t.BoxExtent = ext end)
        pcall(function() t.TrapPlacementTypes = ptype end)
        pcall(function() t.RelativeLocation = {X = 0.0, Y = 0.0, Z = 0.0} end)
        pcall(function() t.RelativeRotation = {Pitch = 0.0, Yaw = 0.0, Roll = 0.0} end)
    else
        log("  " .. tag .. ": gnome box template not found")
    end
    local g = world:SpawnActor(cls, c, rot)
    if valid(t) and saved then
        pcall(function() t.BoxExtent = {X = saved.e.X, Y = saved.e.Y, Z = saved.e.Z} end)
        pcall(function() t.TrapPlacementTypes = saved.ty end)
        pcall(function() t.RelativeLocation = {X = saved.l.X, Y = saved.l.Y, Z = saved.l.Z} end)
        pcall(function() t.RelativeRotation = {Pitch = saved.r.Pitch, Yaw = saved.r.Yaw, Roll = saved.r.Roll} end)
    end
    if not valid(g) then log("  " .. tag .. ": spawn failed"); return nil end
    local removed = 0
    for _, cn in ipairs(VISUALS) do
        local comp = get(g, cn)
        if valid(comp) then
            pcall(function() comp:SetVisibility(false, true) end)
            pcall(function() comp:SetCollisionEnabled(0) end)
            if pcall(function() comp:K2_DestroyComponent(comp) end) then removed = removed + 1 end
        end
    end
    local box = get(g, "RSTTrapGridBox")
    if valid(box) then
        local oke, e2 = pcall(function() return box:GetScaledBoxExtent() end)
        local okl, l2 = pcall(function() return box:K2_GetComponentLocation() end)
        local okr, r2 = pcall(function() return box:K2_GetComponentRotation() end)
        log(string.format("  %s: gnome grid, box at %s rot (%.0f, %.0f, %.0f) extent %s type %s (template %s), %d visual part(s) removed",
            tag, okl and vec(l2) or "?", okr and r2.Pitch or 0, okr and r2.Yaw or 0, okr and r2.Roll or 0, oke and vec(e2) or "?",
            tostring(get(box, "TrapPlacementTypes")), saved and "set" or "MISSING", removed))
    else
        log("  " .. tag .. ": gnome has no grid box")
    end
    return g
end


-- every trap grid the game accepts sits on something solid (floor, wall, the gnome's balloon deck); the barricade
-- only has a thin collision plate at its foot. So the trap barricade gets an invisible solid body: a blocking cube.
-- collision channels (DefaultEngine.ini): Visibility 2, Camera 3, RSTProjectile 24 (GameTraceChannel11),
-- RSTAimAssist 27 (GameTraceChannel14), RSTAimTrace 30 (GameTraceChannel17)
local SHOT_CHANNELS = {2, 3, 24, 27, 30}
local function let_shots_through(comp)
    local n = 0
    for _, ch in ipairs(SHOT_CHANNELS) do
        if pcall(function() comp:SetCollisionResponseToChannel(ch, 0) end) then n = n + 1 end
    end
    return n
end

local function spawn_body(world, c, yaw, size_xy, h)
    local cls = StaticFindObject("/Script/Engine.StaticMeshActor")
    local cube = StaticFindObject("/Engine/BasicShapes/Cube.Cube")
    if not valid(cube) then pcall(function() LoadAsset("/Engine/BasicShapes/Cube") end); cube = StaticFindObject("/Engine/BasicShapes/Cube.Cube") end
    if not (valid(cls) and valid(cube)) then log("  body: cube or StaticMeshActor not found"); return nil end
    local a = world:SpawnActor(cls, c, {Pitch = 0.0, Yaw = yaw, Roll = 0.0})
    if not valid(a) then log("  body: spawn failed"); return nil end
    local m = get(a, "StaticMeshComponent")
    local steps = {}
    local function try(name, f) local ok, e = pcall(f); steps[#steps + 1] = name .. (ok and "" or ("(failed: " .. tostring(e) .. ")")) end
    try("movable", function() m:SetMobility(2) end)
    try("mesh", function() m:SetStaticMesh(cube) end)
    try("scale", function() a:SetActorScale3D({X = size_xy / 100.0, Y = size_xy / 100.0, Z = h / 100.0}) end)
    try("blocking", function() m:SetCollisionProfileName(FName("BlockAll"), true) end)
    try("collision on", function() m:SetCollisionEnabled(3) end)
    try("hidden", function() a:SetActorHiddenInGame(true) end)
    try("shots pass", function() assert(let_shots_through(m) == #SHOT_CHANNELS) end)
    try("blocks the player", function() m:SetCollisionResponseToChannel(22, 2) end)
    local okc, ce = pcall(function() return m:GetCollisionEnabled() end)
    local okp, pn = pcall(function() return m:GetCollisionProfileName():ToString() end)
    log(string.format("  body: invisible solid cube %.0f x %.0f x %.0f cm at %s (%s), collision %s profile %s", size_xy, size_xy, h, vec(c),
        table.concat(steps, ", "), okc and tostring(ce) or "?", okp and tostring(pn) or "?"))
    return a
end

-- ===== wooden look (v21): once per placed Trap Barricade, only its own components =====
local WOOD = {wood = "/Game/Traps/Barricade/Mat/Barricade_Wood_INST.Barricade_Wood_INST",
              metal = "/Game/Traps/Barricade/Mat/Barricade_Metal_INST.Barricade_Metal_INST"}
local function wood_mat(kind)
    local m = StaticFindObject(WOOD[kind])
    if not valid(m) then pcall(function() LoadAsset(WOOD[kind]:match("^[^%.]+")) end); m = StaticFindObject(WOOD[kind]) end
    return valid(m) and m or nil
end

-- the blue fire on top: the blueprint's component NS_Rift_Barricade_Idle (a property of the barricade, so no searching)
local function hide_fire(bar)
    local fx = get(bar, "NS_Rift_Barricade_Idle")
    if not valid(fx) then return false end
    pcall(function() fx:Deactivate() end)
    pcall(function() fx:SetVisibility(false, false) end)
    pcall(function() fx:SetHiddenInGame(true, false) end)
    return true
end

local function make_wooden(bar)
    local done, notes = 0, {}
    for _, cname in ipairs({"StaticMeshComponent", "MeshComponent"}) do
        local m = get(bar, cname)
        if valid(m) then
            local n = 0; pcall(function() n = m:GetNumMaterials() end)
            for i = 0, n - 1 do
                local mat = nil; pcall(function() mat = m:GetMaterial(i) end)
                local mn = valid(mat) and name_of(mat) or ""
                if mn:find("Rift_Barricade", 1, true) then
                    local kind = mn:find("Metal", 1, true) and "metal" or "wood"
                    local w = wood_mat(kind)
                    if w and pcall(function() m:SetMaterial(i, w) end) then done = done + 1
                    else notes[#notes + 1] = cname .. " slot " .. i .. " failed" end
                end
            end
        else notes[#notes + 1] = cname .. " not found" end
    end
    if hide_fire(bar) then notes[#notes + 1] = "blue fire off" else notes[#notes + 1] = "blue fire not found" end
    for _, cname in ipairs({"StaticMeshComponent", "MeshComponent"}) do
        local m = get(bar, cname)
        if valid(m) then notes[#notes + 1] = cname .. " lets shots through (" .. let_shots_through(m) .. " channels)" end
    end
    -- the Rift Barricade's neighbour buff (blue glow on the barricades next to it): its two query boxes stop overlapping,
    -- which makes the blueprint remove the buff it gave
    for _, qn in ipairs({"QueryBox1", "QueryBox2"}) do
        local q = get(bar, qn)
        if valid(q) and pcall(function() q:SetCollisionEnabled(0) end) then notes[#notes + 1] = qn .. " off"
        else notes[#notes + 1] = qn .. " not found" end
    end
    return done, notes
end

local B = {}          -- barricade address -> {bar=, grids={}, at=}
local seen = {}       -- barricade addresses already looked at
local reported = false

local function setup(bar)
    local world = bar:GetWorld()
    local loc = bar:K2_GetActorLocation(); local rot = bar:K2_GetActorRotation()
    local box = get(bar, "GeneratedBoxCollision")
    local ext, bc = nil, nil
    if valid(box) then
        pcall(function() ext = box:GetScaledBoxExtent() end)
        pcall(function() bc = box:K2_GetComponentLocation() end)
    end
    log(string.format("barricade %s at %s yaw %.0f, box centre %s half size %s", name_of(bar):match("[^%.]+$") or "?", vec(loc), rot.Yaw,
        vec(bc), vec(ext)))
    if not (ext and bc) then log("  no collision box: skipped"); return nil end
    -- make it TALL cm high (stretch the actor up); the collision box is only the 10 cm footprint plate
    local sz = TALL / MESH_H
    local oks = pcall(function() bar:SetActorScale3D({X = 1.0, Y = 1.0, Z = sz}) end)
    log(string.format("  stretched to %.0f cm (scale Z %.2f): %s", TALL, sz, oks and "ok" or "failed"))
    local h = oks and TALL or MESH_H
    local yaw = rot.Yaw; local r = math.rad(yaw)
    local fx, fy = math.cos(r), math.sin(r)          -- the barricade's forward (its local X) on the ground
    local rx, ry = -fy, fx                            -- its right (local Y)
    local base = loc.Z
    local top = base + h
    local g = {}
    -- the solid body first (2 cm smaller than the grids' faces, so the grids sit just outside it)
    g[#g + 1] = spawn_body(world, {X = bc.X, Y = bc.Y, Z = base + h / 2}, yaw, 2 * ext.X, h)
    -- top: floor traps (rotated like the builder's floor grids: pitch 90)
    -- pitch exactly 90 came out as -90 (facing down = a ceiling grid): use 89.9
    -- v11: Pitch 89.9 still came out as -90 (facing down). v12: ask for -89.9
    g[#g + 1] = spawn_grid(world, {X = bc.X, Y = bc.Y, Z = top + 5}, {Pitch = -89.9, Yaw = yaw, Roll = 0.0},
        {X = 10.0, Y = ext.Y, Z = ext.X}, 1, "top")
    -- the four sides: wall traps (local X of the grid = outward normal)
    local sides = {
        {fx, fy, ext.X, ext.Y, yaw, "front"}, {-fx, -fy, ext.X, ext.Y, yaw + 180, "back"},
        {rx, ry, ext.Y, ext.X, yaw + 90, "right"}, {-rx, -ry, ext.Y, ext.X, yaw - 90, "left"},
    }
    for _, s in ipairs(sides) do
        local nx, ny, dist, half, gyaw, tag = s[1], s[2], s[3], s[4], s[5], s[6]
        g[#g + 1] = spawn_grid(world, {X = bc.X + nx * (dist + OUT), Y = bc.Y + ny * (dist + OUT), Z = base + h / 2},
            {Pitch = 0.0, Yaw = gyaw, Roll = 0.0}, {X = 10.0, Y = half, Z = h / 2}, 2, tag)
    end
    local grids = {}; for i = 2, #g do grids[#grids + 1] = g[i] end
    local okp, np, pn = pcall(let_player_through_all, grids)
    log("  trap spots: " .. (okp and (tostring(np) .. " part(s) let the player through (" .. tostring(pn) .. ")") or ("error " .. tostring(np))))
    local who = {barricade = bar, body = g[1]}
    for i = 2, #g do who["spot" .. (i - 1)] = g[i] end
    local okd, nd, lines = pcall(describe_parts, who)
    if okd then
        log("  parts (player channel response 0 = ignore, 2 = block): " .. nd .. " set to ignore the player")
        for _, l in ipairs(lines) do log(l) end
    else log("  parts: error " .. tostring(nd)) end
    return g
end

-- traps built on our grids: their MainTrapGrid is one of them
local function traps_on(grids)
    local set = {}
    for _, gr in ipairs(grids) do local a = addr(gr); if a then set[a] = true end end
    local out = {}
    for _, t in ipairs(FindAllOf("RSTTrap") or {}) do
        if valid(t) and get(t, "bIsBeingPlaced") ~= true then
            local ok, mg = pcall(function() return t.MainTrapGrid:Get() end)
            if ok and valid(mg) and set[addr(mg)] then out[#out + 1] = t end
        end
    end
    return out
end


-- ---------- the trap being placed: why can't it go on our grids? ----------
local REASON = {[0] = "Unknown", "NoTrapGrid", "InvalidPlacement", "WrongPlacementType", "TrapLimitReached", "NotEnoughCoin", "Encroaching"}
local ours = {}       -- grid address -> "barricade <n> <side>"
local last_line = nil
local function watch_pending()
    for _, t in ipairs(FindAllOf("RSTTrap") or {}) do
        if valid(t) and get(t, "bIsBeingPlaced") == true and not name_of(t):find("Default__", 1, true) then
            local l = t:K2_GetActorLocation()
            local r = get(t, "LastPlacementFailureReason")
            local okv = get(t, "bIsPlacementValid")
            local gname, mine = "none", ""
            local okg, mg = pcall(function() return t.MainTrapGrid:Get() end)
            if okg and valid(mg) then
                gname = (name_of(mg):match("[^%.:]+$") or "?")
                mine = ours[addr(mg)] and (" = OUR " .. ours[addr(mg)]) or " (map grid)"
            end
            local near, nd = nil, 1e18
            for a, rec in pairs(B) do
                if valid(rec.bar) then
                    local bl = rec.bar:K2_GetActorLocation()
                    local d = math.sqrt((bl.X - l.X) ^ 2 + (bl.Y - l.Y) ^ 2)
                    if d < nd then nd, near = d, rec end
                end
            end
            if nd > 1000 or (l.X == 0 and l.Y == 0) then goto continue end
            local line = string.format("holding %s at %s: valid %s, reason %s, grid %s%s, nearest barricade %s",
                (name_of(t):match("BP_[%w_]+") or "trap"), vec({X = math.floor(l.X / 10) * 10, Y = math.floor(l.Y / 10) * 10, Z = math.floor(l.Z / 10) * 10}),
                tostring(okv), REASON[r] or tostring(r), gname, mine, near and string.format("%.0f cm away", nd) or "none")
            if line ~= last_line then log(line); last_line = line end
        end
        ::continue::
    end
end

-- ---------- which item is selected: is the Trap Barricade in hand? ----------
local rift_cost = nil          -- the Rift Barricade definition's own cost (restored when the Trap Barricade isn't in hand)
local last_hand = nil
local function hotbar_item_for(ps)
    local best, n = nil, 0
    for _, hb in ipairs(FindAllOf("RSTHotbarComponent") or {}) do
        if valid(hb) and not name_of(hb):find("Default__", 1, true) then
            n = n + 1
            local item = nil
            pcall(function() local inst = hb:GetActiveSlotItem(); if valid(inst) then item = inst.ItemDef end end)
            local own = nil; pcall(function() own = hb:GetOwner() end)
            if ps and valid(own) then
                local ops = nil
                pcall(function() if own:IsA(StaticFindObject("/Script/Engine.PlayerState")) then ops = own end end)
                if not ops then pcall(function() ops = own.PlayerState end) end
                if not valid(ops) then pcall(function() ops = own:GetPlayerState() end) end
                if valid(ops) and addr(ops) == addr(ps) then return item end
            end
            best = item
        end
    end
    if n == 1 then return best end
    return nil
end
local function in_hand(ps)
    local item = hotbar_item_for(ps)
    return valid(item) and name_of(item):find(OUR_ITEM, 1, true) ~= nil
end
local function update_cost()
    local def = StaticFindObject(RIFT_DEF)
    if not valid(def) then return end
    if rift_cost == nil then rift_cost = get(def, "PlacementCost") end
    local hand = in_hand(nil)
    if hand ~= last_hand then
        pcall(function() def.PlacementCost = hand and TB_COST or rift_cost end)
        log(string.format("Trap Barricade %s: Rift Barricade cost set to %s", hand and "in hand" or "not in hand", tostring(get(def, "PlacementCost"))))
        last_hand = hand
    end
end
-- the barricade's health: its RSTHealthSet attributes (Health, MaxHealth)
local function set_health(bar, hp)
    local done = 0
    for _, hs in ipairs(FindAllOf("RSTHealthSet") or {}) do
        local ok, o = pcall(function() return hs:GetOuter() end)
        if ok and valid(o) and addr(o) == addr(bar) then
            for _, k in ipairs({"MaxHealth", "Health"}) do
                pcall(function() hs[k].BaseValue = hp; hs[k].CurrentValue = hp end)
            end
            done = done + 1
        end
    end
    return done
end

local logged_traps = {}
local function log_new_traps()
    for _, t in ipairs(FindAllOf("RSTTrap") or {}) do
        local a = addr(t)
        if a and not logged_traps[a] and valid(t) and get(t, "bIsBeingPlaced") ~= true and not name_of(t):find("Default__", 1, true) then
            local okd, def = pcall(function() return t.TrapDefinition end)
            if okd and valid(def) then
                logged_traps[a] = true
                local cls = name_of(t):match("^(%S+)") or "?"
                local l = t:K2_GetActorLocation()
                log(string.format("placed trap: %s %s, definition %s, owned %s, at %s", cls, name_of(t):match("[^%.:]+$") or "?",
                    name_of(def), tostring(owned(t)), vec(l)))
            end
        end
    end
end

local tick = 0
local function step()
    if not is_host() then return end
    pcall(clawback)
    pcall(update_cost)
    pcall(log_new_traps)
    pcall(watch_pending)
    if gnome_tries < 3 and not valid(StaticFindObject(GNOME_CLASS)) then pcall(gnome_class) end
    for _, cn in ipairs(CLASSES) do
        for _, bar in ipairs(FindAllOf(cn) or {}) do
            local a = addr(bar)
            if a and valid(bar) and not seen[a] and get(bar, "bIsBeingPlaced") ~= true and not name_of(bar):find("Default__", 1, true) then
                seen[a] = true
                local ps = nil; pcall(function() ps = bar.TrapOwner:Get() end)
                local is_ours = in_hand(valid(ps) and ps or nil)
                log("new Rift Barricade placed: " .. (is_ours and "a TRAP BARRICADE (placed with it in hand)" or "an ordinary one"))
                if owned(bar) and is_ours then
                    local n = set_health(bar, TB_HEALTH)
                    log(string.format("  health set to %.0f (%d health set(s))", TB_HEALTH, n))
                    local okw, nw, wn = pcall(make_wooden, bar)
                    log("  wooden look: " .. (okw and (nw .. " material(s) swapped" .. (#wn > 0 and (", " .. table.concat(wn, ", ")) or "")) or ("error " .. tostring(nw))))
                    local ok, g = pcall(setup, bar)
                    if ok and g then
                        B[a] = {bar = bar, grids = g, n = 0}
                        local sides = {"body", "top", "front", "back", "right", "left"}
                        local nb = 0; for _ in pairs(B) do nb = nb + 1 end
                        for i, gr in ipairs(g) do local ga = addr(gr); if ga then ours[ga] = "barricade " .. nb .. " " .. (sides[i] or "?") end end
                    elseif not ok then log("setup error: " .. tostring(g)) end
                end
            end
        end
    end
    tick = tick + 1
    for a, rec in pairs(B) do
        if tick % 5 == 0 and valid(rec.bar) then pcall(hide_fire, rec.bar) end   -- in case the game switches it back on
        local br, why = broken(rec.bar, rec)
        local on = traps_on(rec.grids)
        if #on ~= rec.n then log(string.format("barricade %s: %d trap(s) built on it", tostring(a), #on)); rec.n = #on end
        if br then
            local keep = (why == "sold")              -- the player sold it: its traps are sold normally, money kept
            log("barricade " .. tostring(a) .. " " .. why .. ": removing " .. #on .. " trap(s)" .. (keep and " (money kept)" or " (money lost)") ..
                ", its grids and the barricade")
            for _, t in ipairs(on) do
                local ok, r = pcall(remove_trap, t, keep)
                log("  trap " .. (name_of(t):match("BP_[%w_]+") or "?") .. ": " .. (ok and r or ("error " .. tostring(r))))
            end
            for _, gr in ipairs(rec.grids) do if valid(gr) then pcall(function() gr:K2_DestroyActor() end) end end
            if valid(rec.bar) and why ~= "sold" then          -- the broken barricade itself: gone too (the game would leave it)
                local ok, r = pcall(remove_trap, rec.bar, false)
                log("  the barricade: " .. (ok and r or ("error " .. tostring(r))))
            end
            B[a] = nil
        end
    end
    -- once: what an ordinary trap grid in this level looks like (for comparison), and how many spares there are
    if not reported then
        local n = 0
        for _, gr in ipairs(FindAllOf("BP_OMDTrapGrid_Blank_C") or {}) do
            local l = valid(gr) and gr:K2_GetActorLocation()
            if l and math.abs(l.X) < 1 and math.abs(l.Y) < 1 and not name_of(gr):find("Default__", 1, true) then n = n + 1 end
        end
        if n > 0 then log("spare map grids (parked at the centre): " .. n) end
        for _, gr in ipairs(FindAllOf("BP_OMDTrapGrid_Blank_C") or {}) do
            local l0 = valid(gr) and gr:K2_GetActorLocation()
            if valid(gr) and not name_of(gr):find("Default__", 1, true) and l0 and (math.abs(l0.X) > 1 or math.abs(l0.Y) > 1) then
                local box = get(gr, "OMDTrapGridBox")
                log("level grid in use: " .. coll(box) .. ", tile origin " .. vec(get(gr, "GridStartBottomLeft")))
                log("level grid in use: " .. plane_info(box))
                local oke, e = pcall(function() return box:GetUnscaledBoxExtent() end)
                log(string.format("level grid example: at %s rot yaw %.0f pitch %.0f, extent %s, type %s, grid scale %s",
                    vec(gr:K2_GetActorLocation()), gr:K2_GetActorRotation().Yaw, gr:K2_GetActorRotation().Pitch,
                    oke and vec(e) or "?", tostring(get(box, "TrapPlacementTypes")), tostring(get(gr, "GridScale"))))
                reported = true; break
            end
        end
    end
end

local function run_step() local ok, err = pcall(step); if not ok then log("step error " .. tostring(err)) end end
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
