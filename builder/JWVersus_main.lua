-- JWVersus: referee for VS maps (two rifts, side A = west rift, side B = east rift).
-- Installed by OMD Map Builder into Binaries\Win64\Mods\JWVersus. Only wakes up on our custom levels (Level_JW_*)
-- that have exactly two rifts.
--
-- How it keeps score: the game has ONE shared rift point pool. Every time it drops, the loss goes to the side whose
-- rift an orc just walked into (RiftEnterBeginOverlap hook; fallback: the rift with the nearest enemy). Each side
-- starts with the mission's rift points. The host keeps the shared pool at the lower of the two, so the game's own
-- defeat happens exactly when one side runs out; the winner is shown on screen first.
-- Log: Binaries\Win64\JW_Versus_log.txt

local BIN = "C:/Program Files (x86)/Steam/steamapps/common/Orcs Must Die Deathtrap/OMDD/Binaries/Win64/"
local HARDER = 0.5          -- extra copies per wave orc added each mission wave (endless)
local TOUGHER = 0.15        -- enemy health +15 % per mission wave (endless)
-- (both are defaults: the map's VS rules from the Map Maker, Mods/JWVersus/rules.txt, can change them per map)
local RULES = BIN .. "Mods/JWVersus/rules.txt"
local LOGF = BIN .. "JW_Versus_log.txt"
local logfile = io.open(LOGF, "w")
local function log(s)
    local line = os.date("%H:%M:%S ") .. tostring(s)
    if logfile then logfile:write(line .. "\n"); logfile:flush() end
    print("[JWVersus] " .. tostring(s) .. "\n")
end
log("loaded v127 (sends on F1-F6: curse F6, curse test Ctrl+F6, PvP test Ctrl+F9)")
local HC = {}
local function hk(n) HC[n] = (HC[n] or 0) + 1; if HC[n] <= 3 then log("hook fired: " .. n .. " #" .. HC[n]) end end

local SIDE = {"A", "B"}
local V = nil            -- state of the current VS match (nil = not a VS level)
local function growth_orcs() return (V and V.harder) or HARDER end
local function growth_health() return (V and V.tougher) or TOUGHER end
local entries = {}       -- recent rift entries {side, t}
local seen = {}          -- enemy actor address -> true (count each orc once)
local tick = 0
-- curses (the 6th send; defined after tick: before it, tick was a nil global here and the check failed): V.curse[side] = {id, name, from, t0, till, wave} while a side is cursed
local function curse_on(side, id)
    local c = V and V.curse and V.curse[side]
    return c and c.id == id and tick < c.till
end

local function valid(o) return o ~= nil and o:IsValid() end
local function inst(o)                    -- a real object in the level, not a class default object
    if not valid(o) then return false end
    local ok, n = pcall(function() return o:GetFullName() end)
    return ok and not n:find("Default__", 1, true)
end
local function loc(a) local ok, v = pcall(function() return a:K2_GetActorLocation() end); if ok and v then return v end end
local function name_of(o) local ok, n = pcall(function() return o:GetFullName() end); return ok and n or "?" end

local function local_pc()
    local pcs = FindAllOf("PlayerController") or {}
    for _, pc in ipairs(pcs) do
        if inst(pc) then
            local ok, l = pcall(function() return pc:IsLocalController() end)
            if ok and l then return pc end
        end
    end
    return pcs[1]
end

local function console(cmd)
    local pc = local_pc(); local ksl = StaticFindObject("/Script/Engine.Default__KismetSystemLibrary")
    if valid(pc) and valid(ksl) then ksl:ExecuteConsoleCommand(pc, cmd, pc); log("cmd " .. cmd); return true end
    return false
end

local function game_state()
    for _, gs in ipairs(FindAllOf("RSTGameStateBase") or {}) do if inst(gs) then return gs end end
end
local function rift_points()
    local gs = game_state(); if not gs then return nil end
    local ok, v = pcall(function() return gs:GetRiftPoints() end)
    if ok and type(v) == "number" then return v end
    return nil
end
local host_cache, host_tick = nil, -100
local function is_host()
    -- the game mode only exists on the server (or in a solo game)
    if tick - host_tick < 10 and host_cache ~= nil then return host_cache end
    host_tick = tick; host_cache = false
    for _, gm in ipairs(FindAllOf("GameModeBase") or {}) do if inst(gm) then host_cache = true; break end end
    return host_cache
end

-- ---------- on-screen scoreboard (a UMG widget built at runtime) ----------
local hud, hud_fail = nil, -1000
local function hud_text(txt)
    if hud and valid(hud.w) and valid(hud.t) then
        pcall(function() hud.t:SetText(FText(txt)) end); return
    end
    hud = nil
    if tick - hud_fail < 20 then                -- widget failed lately: only the chat line, retry every 10 s
        local pc = local_pc()
        if valid(pc) then pcall(function() pc:ClientMessage(txt, FName("None"), 5.0) end) end
        return
    end
    local ok, err = pcall(function()
        local gi = FindFirstOf("GameInstance")
        local w = StaticConstructObject(StaticFindObject("/Script/UMG.UserWidget"), gi, FName("JWVersusHUD"))
        w.WidgetTree = StaticConstructObject(StaticFindObject("/Script/UMG.WidgetTree"), w, FName("JWVersusTree"))
        local canvas = StaticConstructObject(StaticFindObject("/Script/UMG.CanvasPanel"), w.WidgetTree, FName("JWVersusCanvas"))
        w.WidgetTree.RootWidget = canvas
        local t = StaticConstructObject(StaticFindObject("/Script/UMG.TextBlock"), w.WidgetTree, FName("JWVersusText"))
        local slot = canvas:AddChildToCanvas(t)
        local function try(what, f) local okf, e = pcall(f); if not okf then log("  layout " .. what .. " failed: " .. tostring(e)) end end
        try("autosize", function() slot:SetAutoSize(true) end)
        try("anchors", function() slot:SetAnchors({Minimum = {X = 0.5, Y = 0.0}, Maximum = {X = 0.5, Y = 0.0}}) end)
        try("alignment", function() slot:SetAlignment({X = 0.5, Y = 0.0}) end)
        try("position", function() slot:SetPosition({X = 0.0, Y = 132.0}) end)
        try("layoutdata", function()
            slot.LayoutData.Anchors.Minimum.X = 0.5; slot.LayoutData.Anchors.Maximum.X = 0.5
            slot.LayoutData.Alignment.X = 0.5; slot.LayoutData.Offsets.Left = 0.0; slot.LayoutData.Offsets.Top = 132.0
            slot.bAutoSize = true
        end)
        pcall(function() t.Font.Size = 22 end)
        pcall(function() t:SetJustification(1) end)
        pcall(function() t:SetShadowOffset({X = 2.0, Y = 2.0}) end)
        t:SetText(FText(txt))
        pcall(function() w:SetOwningPlayer(local_pc()) end)
        w:AddToViewport(500)
        hud = {w = w, t = t}
        log("scoreboard widget created")
    end)
    if not ok then
        hud_fail = tick
        log("scoreboard widget failed: " .. tostring(err))
        local pc = local_pc()
        if valid(pc) then pcall(function() pc:ClientMessage(txt, FName("None"), 5.0) end) end
    end
end

-- messages (sends, curses): their own line at the top left, under the hero's portrait and health bar
local msgw = nil
local MSG_X, MSG_Y = 20.0, 168.0          -- UI units: just under the health bar (from a screenshot)
local function msg_text(txt)
    if msgw and valid(msgw.w) and valid(msgw.t) then
        if msgw.last ~= txt then msgw.last = txt; pcall(function() msgw.t:SetText(FText(txt)) end) end
        return
    end
    if txt == "" then return end
    local ok, err = pcall(function()
        local gi = FindFirstOf("GameInstance")
        local w = StaticConstructObject(StaticFindObject("/Script/UMG.UserWidget"), gi, FName("JWVersusMsg"))
        w.WidgetTree = StaticConstructObject(StaticFindObject("/Script/UMG.WidgetTree"), w, FName("JWVersusMsgTree"))
        local canvas = StaticConstructObject(StaticFindObject("/Script/UMG.CanvasPanel"), w.WidgetTree, FName("JWVersusMsgCanvas"))
        w.WidgetTree.RootWidget = canvas
        local t = StaticConstructObject(StaticFindObject("/Script/UMG.TextBlock"), w.WidgetTree, FName("JWVersusMsgText"))
        local slot = canvas:AddChildToCanvas(t)
        pcall(function() slot:SetAutoSize(true) end)
        pcall(function() slot:SetAnchors({Minimum = {X = 0.0, Y = 0.0}, Maximum = {X = 0.0, Y = 0.0}}) end)
        pcall(function() slot:SetAlignment({X = 0.0, Y = 0.0}) end)
        pcall(function() slot:SetPosition({X = MSG_X, Y = MSG_Y}) end)
        pcall(function() t.Font.Size = 16 end)
        pcall(function() t.Font.OutlineSettings.OutlineSize = 1 end)
        pcall(function() t:SetShadowOffset({X = 1.5, Y = 1.5}) end)
        t:SetText(FText(txt))
        pcall(function() w:SetOwningPlayer(local_pc()) end)
        w:AddToViewport(500)
        msgw = {w = w, t = t, last = txt}
    end)
    if not ok then log("message widget failed: " .. tostring(err)) end
end

-- ---------- which side am I: a coloured line on screen, and a big coloured SIDE A / SIDE B above each rift ----------
-- (made on every PC for its own player; nothing here is sent over the network)
local SIDECOL = {{R = 0.25, G = 0.6, B = 1.0}, {R = 1.0, G = 0.3, B = 0.3}}       -- A blue, B red
local SIDEWORD = {"BLUE", "RED"}
local mark = nil
local function my_side()
    if V and V.myside then return V.myside end
    local pc = local_pc()
    local ok, l = pcall(function() return pc.Pawn:K2_GetActorLocation() end)
    if ok and l and V then
        local sd = (l.X < V.mid) and 1 or 2                          -- (side_of_x is defined further down)
        if V.started then V.myside = sd; log("this player is side " .. SIDE[sd]) end   -- kept for the whole match
        return sd
    end
end
local function side_line(txt, col)
    if mark and valid(mark.w) and valid(mark.t) then
        pcall(function() mark.t:SetText(FText(txt)) end)
    else
        mark = nil
        local ok, err = pcall(function()
            local gi = FindFirstOf("GameInstance")
            local w = StaticConstructObject(StaticFindObject("/Script/UMG.UserWidget"), gi, FName("JWVersusSide"))
            w.WidgetTree = StaticConstructObject(StaticFindObject("/Script/UMG.WidgetTree"), w, FName("JWVersusSideTree"))
            local canvas = StaticConstructObject(StaticFindObject("/Script/UMG.CanvasPanel"), w.WidgetTree, FName("JWVersusSideCanvas"))
            w.WidgetTree.RootWidget = canvas
            local t = StaticConstructObject(StaticFindObject("/Script/UMG.TextBlock"), w.WidgetTree, FName("JWVersusSideText"))
            local slot = canvas:AddChildToCanvas(t)
            pcall(function() slot:SetAutoSize(true) end)
            pcall(function() slot:SetAnchors({Minimum = {X = 0.5, Y = 0.0}, Maximum = {X = 0.5, Y = 0.0}}) end)
            pcall(function() slot:SetAlignment({X = 0.5, Y = 0.0}) end)
            pcall(function() slot:SetPosition({X = 0.0, Y = 94.0}) end)
            pcall(function() t.Font.Size = 18 end)
            pcall(function() t:SetJustification(1) end)
            pcall(function() t:SetShadowOffset({X = 2.0, Y = 2.0}) end)
            t:SetText(FText(txt))
            pcall(function() w:SetOwningPlayer(local_pc()) end)
            w:AddToViewport(501)
            mark = {w = w, t = t}
        end)
        if not ok then log("side line failed: " .. tostring(err)); return end
    end
    if mark.col ~= col then
        local c = SIDECOL[col]
        local okc, e = pcall(function() mark.t:SetColorAndOpacity({SpecifiedColor = {R = c.R, G = c.G, B = c.B, A = 1.0}, ColorUseRule = 0}) end)
        if not okc and not mark.colfail then mark.colfail = true; log("side line colour failed: " .. tostring(e)) end
        mark.col = col
    end
end
local rift_labels = nil       -- the rift pins (set further down)
local board_update = nil      -- the scoreboard (set further down, where its helpers are)
local function show()
    if not V then return end
    -- the scoreboard shows the score and the wave; this text below it only the winner, the round and messages
    local lines = {}
    if V.winner then lines[#lines + 1] = (V.winner == 0 and "DRAW" or ("SIDE " .. (V.winner == 1 and "A" or "B") .. " WINS!")) end
    if V.round and V.round > 1 then lines[#lines + 1] = "ROUND " .. V.round end
    pcall(msg_text, (V.msg and tick - V.msg.t < 10) and V.msg.text or "")   -- (under the health bar, not here)
    for sd = 1, 2 do
        local c = V.curse and V.curse[sd]
        if c and tick < c.till then lines[#lines + 1] = string.format("SIDE %s CURSED: %s  %d s", SIDE[sd], c.name, (c.till - tick) // 2) end
    end
    local okb = board_update and pcall(board_update)
    if not okb then                                    -- no scoreboard: the old one-line score
        table.insert(lines, 1, string.format("SIDE A  %d   |   %d  SIDE B", math.max(V.lives[1], 0), math.max(V.lives[2], 0)))
    end
    hud_text(table.concat(lines, "\n"))
end

-- ---------- which side ----------
local function side_of_x(x)
    if not V then return nil end
    return (x < V.mid) and 1 or 2
end

local function find_rifts()
    local out = {}
    for _, r in ipairs(FindAllOf("RSTRift") or {}) do
        if inst(r) then local l = loc(r); if l then table.insert(out, {r = r, x = l.X, y = l.Y, z = l.Z}) end end
    end
    table.sort(out, function(a, b) return a.x < b.x end)
    return out
end

local function is_enemy(a)
    if not inst(a) then return false end
    local n = name_of(a)
    if n:find("Hero") or n:find("PlayerController") or n:find("Wisp") then return false end
    -- guardian archers placed on the map (the archer trap): not wave enemies, never twinned, never a keeper
    if n:find("Sentinel") then return false end
    local okd, dying = pcall(function() return a.bActorIsBeingDestroyed end)
    if okd and dying then return false end
    local ok, c = pcall(function() return a:GetController() end)
    if ok and valid(c) and name_of(c):find("PlayerController") then return false end
    return true
end

-- rift crystal health: damage on a crystal tells which side lost the point
local function crystal_hp(i)
    local ok, h = pcall(function() return V.rifts[i].r.HealthComponent:GetHealth() end)
    if ok and type(h) == "number" then return h end
end
local function track_damage()
    for i = 1, 2 do
        local h = crystal_hp(i)
        if h then
            if V.hp[i] and h < V.hp[i] then V.dmg[i] = V.dmg[i] + (V.hp[i] - h) end
            V.hp[i] = h
        end
    end
end

-- heroes that die cost the pool rift points: note each death with the dead hero's side, so the loss is charged there
-- (before this, a loss with no orc seen entering a rift went to the side with an enemy nearest a rift)
local function track_hero_deaths()
    V.hdeaths = V.hdeaths or {}; V.hseen = V.hseen or {}
    local list = {}
    if V.pcs then for _, e in ipairs(V.pcs) do list[#list + 1] = {pc = e.pc, side = e.side} end
    else for _, pc in ipairs(FindAllOf("PlayerController") or {}) do if inst(pc) then list[#list + 1] = {pc = pc} end end end
    for i, e in ipairs(list) do
        local okp, pawn = pcall(function() return e.pc.Pawn end)
        local alive_pawn = okp and valid(pawn) and name_of(pawn):find("Hero")
        local dead = false
        if alive_pawn then
            local okd, d = pcall(function() return pawn.HealthComponent:IsDeadOrDying() end)
            dead = okd and d == true
            local key = pawn:GetAddress()
            if dead and not V.hseen[key] then
                V.hseen[key] = true
                local sd = e.side
                if not sd then local l = loc(pawn); sd = l and side_of_x(l.X) or 1 end
                table.insert(V.hdeaths, {side = sd, t = tick})
                log(string.format("hero %d (side %s) died", i, SIDE[sd]))
            end
        end
    end
    while #V.hdeaths > 0 and tick - V.hdeaths[1].t > 20 do table.remove(V.hdeaths, 1) end   -- 10 s: a death that cost nothing
end

local function nearest_side()
    -- fallback when no rift entry was seen: the rift with an enemy closest to it
    local best, bd = nil, 1e18
    for _, p in ipairs(FindAllOf("Character") or {}) do
        if is_enemy(p) then
            local l = loc(p)
            if l then
                for i, r in ipairs(V.rifts) do
                    local d = (l.X - r.x) ^ 2 + (l.Y - r.y) ^ 2
                    if d < bd then bd, best = d, i end
                end
            end
        end
    end
    return best
end

-- ---------- hooks ----------
local function on_rift_entry(rift, actor, why)
    if not V then return end
    local ok, err = pcall(function()
        local r = rift and rift:get() or nil
        local a = actor and actor:get() or nil
        if not is_enemy(a) then return end
        local key = a:GetAddress()
        if seen[key] then return end
        seen[key] = true
        local s
        if valid(r) then local l = loc(r); if l then s = side_of_x(l.X) end end
        if not s then local l = loc(a); if l then s = side_of_x(l.X) end end
        if s then table.insert(entries, {side = s, t = tick}); log(why .. ": enemy " .. name_of(a):match("[^%.]+$") .. " -> side " .. (s == 1 and "A" or "B")) end
    end)
    if not ok then log("hook error " .. tostring(err)) end
end

local hooked = false
local function try_hooks()
    if hooked then return end
    hooked = true
    local ok1, e1 = pcall(function()
        RegisterHook("/Script/OMD4.RSTRift:RiftEnterBeginOverlap", function(self, comp, other)
            hk("RiftEnterBeginOverlap")
            on_rift_entry(self, other, "rift overlap")
        end)
    end)
    log("hook RiftEnterBeginOverlap: " .. (ok1 and "ok" or tostring(e1)))
    local ok2, e2 = pcall(function()
        RegisterHook("/Script/OMD4.RSTOnslaughtComponentRiftDefense:OnRiftEntered", function(self, a1, a2)
            hk("OnRiftEntered")
            -- parameter layout unknown: log what we get, use whichever is an actor
            local ok, err = pcall(function()
                local p1 = a1 and a1:get() or nil; local p2 = a2 and a2:get() or nil
                log("OnRiftEntered(" .. (p1 and name_of(p1) or "nil") .. ", " .. (p2 and name_of(p2) or "nil") .. ")")
                local rift, enemy = nil, nil
                for _, p in ipairs({p1, p2}) do
                    if valid(p) then if name_of(p):find("Rift") then rift = p else enemy = p end end
                end
                if enemy then on_rift_entry(rift and {get = function() return rift end}, {get = function() return enemy end}, "OnRiftEntered") end
            end)
            if not ok then log("OnRiftEntered parse: " .. tostring(err)) end
        end)
    end)
    log("hook OnRiftEntered: " .. (ok2 and "ok" or tostring(e2)))
    local ok3, e3 = pcall(function()
        RegisterHook("/Script/OMD4.RSTRiftCrystal:OnDamageTaken", function(self, hc, dmg)
            hk("crystal OnDamageTaken")
            if not V then return end
            pcall(function()
                local c = self:get()
                local l = valid(c) and loc(c)
                if not l then return end
                local okd, d = pcall(function() return dmg:get() end)
                d = (okd and type(d) == "number" and d > 0) and d or 1
                local sd = side_of_x(l.X)
                V.hdmg[sd] = V.hdmg[sd] + d
            end)
        end)
    end)
    log("hook crystal OnDamageTaken: " .. (ok3 and "ok" or tostring(e3)))
    -- coins: each enemy's death handler (OnDeathStarted / OnDeathFinished, bound to its health component, so hookable)
    -- is wrapped: the players' coins are read before and after, the difference is that kill's coins per player
    for _, fn in ipairs({"OnDeathStarted", "OnDeathFinished"}) do
        local ok4, e4 = pcall(function()
            RegisterHook("/Script/OMD4.RSTCharacter:" .. fn, function(self)
                hk(fn .. " pre")
                if not V or not V.econ then return end
                pcall(function()
                    local c = self:get()
                    if not is_enemy(c) then return end
                    local snap = {}
                    for i, e in ipairs(V.econ) do snap[i] = e.ps.Coin end
                    V.snap[fn .. c:GetAddress()] = snap
                end)
            end, function(self)
                hk(fn .. " post")
                if not V or not V.econ then return end
                pcall(function()
                    local c = self:get()
                    local key = fn .. c:GetAddress()
                    local snap = V.snap[key]; if not snap then return end
                    V.snap[key] = nil
                    local d, any = {}, false
                    for i, e in ipairs(V.econ) do d[i] = e.ps.Coin - snap[i]; if d[i] ~= 0 then any = true end end
                    local l = loc(c)
                    local sd = l and side_of_x(l.X)
                    V.deathseen = (V.deathseen or 0) + 1
                    if V.deathseen <= 8 or (any and (V.coinseen or 0) < 8) then
                        if any then V.coinseen = (V.coinseen or 0) + 1 end
                        log(string.format("%s %s on side %s: coins %s", fn, name_of(c):match("[^%.]+$") or "?", sd and SIDE[sd] or "?",
                            table.concat(d, " / ")))
                    end
                    if any and sd then table.insert(V.kgrants, {side = sd, d = d}) end
                end)
            end)
        end)
        log("hook " .. fn .. ": " .. (ok4 and "ok" or tostring(e4)))
    end
end

-- ---------- players: host puts the first player on side A, the second on side B ----------
local function place_players()
    if not is_host() then return end
    local starts = {}
    for _, ps in ipairs(FindAllOf("PlayerStart") or {}) do
        local l = inst(ps) and loc(ps); if l then table.insert(starts, l) end
    end
    local pcs = {}
    for _, pc in ipairs(FindAllOf("PlayerController") or {}) do
        if inst(pc) then
            local okp, pawn = pcall(function() return pc.Pawn end)
            if okp and valid(pawn) and name_of(pawn):find("Hero") then table.insert(pcs, pc) end
        end
    end
    if #pcs < 2 then return end                -- one player: stays where the game put them
    V.pcs = {}
    for i, pc in ipairs(pcs) do V.pcs[i] = {pc = pc, side = ((i - 1) % 2) + 1} end
    for i, pc in ipairs(pcs) do
        local ok, pawn = pcall(function() return pc.Pawn end)
        if ok and valid(pawn) then
            local key = pawn:GetAddress()
            local want = ((i - 1) % 2) + 1
            V.player_side[i] = want
            local l = loc(pawn)
            if l and not V.placed[key] then
                V.placed[key] = true
                if side_of_x(l.X) ~= want then
                    for _, s in ipairs(starts) do
                        if side_of_x(s.X) == want then
                            pcall(function() pawn:K2_SetActorLocation({X = s.X, Y = s.Y, Z = s.Z + 20}, false, {}, true) end)
                            log("player " .. i .. " moved to side " .. (want == 1 and "A" or "B")); break
                        end
                    end
                else
                    log("player " .. i .. " is on side " .. (want == 1 and "A" or "B"))
                end
            end
        end
    end
end

-- ---------- fair waves: every orc the mission spawns gets a twin on the other side ----------
-- Works in both directions (the mission may use spawners on either side). A twin = the spawner on the other side
-- closest to the mirrored spot is set to that orc type and fired (OnDelayedSpawnTimer). A new enemy that shows up next
-- to a spawner we just fired is a twin; any other new enemy is a wave orc and gets a twin queued for the other side.
-- Per side: twins made + twins on the way never pass the other side's wave orcs. Host only.
-- Twins are on by default; a file named JW_NOTWINS next to the game exe switches them off.
local COORD = nil
local function coordinator()
    if COORD and inst(COORD) then return COORD end
    COORD = nil
    for _, c in ipairs(FindAllOf("RSTOnslaughtCoordinator") or {}) do if inst(c) then COORD = c; break end end
    return COORD
end


-- ---------- looking inside the mission's wave script (for looping wave 1) ----------
-- Lists the Blueprint variables of every onslaught coordinator (the map's wave script is a Blueprint child of
-- RSTOnslaughtCoordinator) with their values; later calls log only the values that changed.
local SIMPLE = {IntProperty = true, FloatProperty = true, DoubleProperty = true, BoolProperty = true, ByteProperty = true,
    EnumProperty = true, NameProperty = true, Int64Property = true, StrProperty = true}
local function dump_waves(tag)
    if not V then return end
    V.wsnap = V.wsnap or {}
    for _, c in ipairs(FindAllOf("RSTOnslaughtCoordinator") or {}) do
        if inst(c) then
            local cname = name_of(c):match("[^%.]+$") or "?"
            local okc, cls = pcall(function() return c:GetClass() end)
            local n, lines = 0, {}
            while okc and cls and cls:IsValid() and n < 8 do
                n = n + 1
                local clsname = cls:GetFName():ToString()
                if clsname == "RSTOnslaughtCoordinator" then break end     -- native part: in the SDK already
                pcall(function()
                    cls:ForEachProperty(function(prop)
                        local pn = prop:GetFName():ToString()
                        local pt = prop:GetClass():GetFName():ToString()
                        local v = "(" .. pt .. ")"
                        if SIMPLE[pt] then
                            local okv, val = pcall(function() return c[pn] end)
                            if okv then
                                if type(val) == "userdata" then pcall(function() val = val:ToString() end) end
                                v = tostring(val)
                            end
                        elseif pt == "ArrayProperty" then
                            local okv, val = pcall(function() return c[pn]:GetArrayNum() end)
                            v = "array[" .. (okv and tostring(val) or "?") .. "]"
                        end
                        local key = cname .. "." .. pn
                        if V.wsnap[key] ~= v then
                            table.insert(lines, string.format("%s.%s %s = %s%s", clsname, pn, pt, v,
                                V.wsnap[key] and ("  (was " .. V.wsnap[key] .. ")") or ""))
                            V.wsnap[key] = v
                        end
                    end)
                end)
                local oks, sup = pcall(function() return cls:GetSuperStruct() end)
                if not oks then break end
                cls = sup
            end
            log(string.format("wave script %s [%s]: %d variables %s", cname, tag, #lines, (#lines > 0) and "changed/new:" or "unchanged"))
            for i = 1, math.min(#lines, 120) do log("    " .. lines[i]) end
        end
    end
end

local function spawn_twin(def, l, side, mirror)
    local tx = mirror and (2 * V.mid - l.X) or l.X
    local best, bd, bl = nil, 1e18, nil
    for _, sp in ipairs(FindAllOf("BP_AISpawner_C") or {}) do
        if inst(sp) then
            local sl = loc(sp)
            if sl and side_of_x(sl.X) == side then
                local d = (sl.X - tx) ^ 2 + (sl.Y - l.Y) ^ 2
                if d < bd then bd, best, bl = d, sp, sl end
            end
        end
    end
    if not best then return nil end
    V.spn = (V.spn or 0) + 1
    local tr = V.spn <= 2
    local function t(m) if tr then log("spawn_twin " .. V.spn .. ": " .. m) end end
    t("spawner " .. (name_of(best):match("[^%.]+$") or "?") .. ", def " .. (name_of(def):match("[^%.]+$") or "?"))
    best.PawnDefinition = def; t("PawnDefinition set")
    best.MinSpawnCount = 1; best.MaxSpawnCount = 1; t("counts set")
    best.bAllowRespawn = false; best.bIsActive = true; best.MaxAliveCount = 1000; t("flags 1 set")
    best.bActivateAtStart = true; best.NumInitiallySpawned = 0; best.MinRespawnDelay = 0.0; t("flags 2 set")
    best:OnDelayedSpawnTimer(); t("OnDelayedSpawnTimer called")
    return bl
end

-- queue n orcs of this type for a side (mirror = at the mirrored spot of l, else at l itself)
-- enemy health grows with the mission wave: every enemy type seen gets MaxHealth = its own value x (1 + 0.15 per
-- wave after the first), set on its pawn definition, so it applies to every enemy of that type spawned afterwards
-- and doubles with every referee round after the mission's own waves (round 2 x2, round 3 x4 ...)
local function health_scale()
    local r = math.max((V.round or 1) - 1, 0)
    return (1 + math.max((V.cwave or 1) - 1, 0) * growth_health()) * (V.endless and 2 ^ r or 1)
end
local PDES = {}             -- kept across matches: the true original health of every enemy type
local function note_def(def)
    if not V then return end
    local n = name_of(def)
    if PDES[n] then
        if PDES[n].def ~= def then PDES[n].def = def end
        if not PDES[n].set then PDES[n].set = true; pcall(function() def.MaxHealth = PDES[n].orig * health_scale() end) end
        return
    end
    local ok, h = pcall(function() return def.MaxHealth end)
    if ok and type(h) == "number" and h > 0 then
        PDES[n] = {def = def, orig = h, set = true}
        pcall(function() def.MaxHealth = h * health_scale() end)
    end
end
local function scale_health()
    local sc = health_scale()
    local c = 0
    for _, e in pairs(PDES) do
        c = c + 1
        if valid(e.def) then pcall(function() e.def.MaxHealth = e.orig * sc end) end
    end
    log(string.format("enemy health x%.2f (%d enemy types)", sc, c))
end
local function want(def, l, side, mirror, n)
    local dn = name_of(def)
    for _ = 1, n do table.insert(V.queue, {def = def, dn = dn, l = l, side = side, mirror = mirror, t = tick}) end
    V.need[side] = V.need[side] + n
end

-- ---------- the door tag ----------
-- Orcs only put barricades on their threat list when they carry the loose gameplay tag Status.PassedThreshold.Door
-- (found in the game's code: the AI's sensing skips barricades without it). Normally a door (ARSTDoor) gives the tag
-- when an orc walks through its ThresholdBox; our maps have no working doors, so the referee gives it to every orc.
local DOORTAG = nil
local function give_door_tag(p)
    local ok, e = pcall(function()
        -- one tag on the orc's own ability system component (AddTimedLooseTag takes a single tag, a simple struct;
        -- the container versions crashed the newer UE4SS)
        local tr = (V.doortags or 0) < 2
        local asc = p:GetRSTAbilitySystemComponent()
        if tr then log("door tag: component " .. (valid(asc) and "found" or "missing")) end
        if not valid(asc) then return false end
        asc:AddTimedLooseTag({TagName = FName("Status.PassedThreshold.Door")}, true, 100000.0)
        if tr then log("door tag: added") end
        return true
    end)
    V.doortags = (V.doortags or 0) + 1
    if not ok then V.doorfail = (V.doorfail or 0) + 1 end
    if V.doortags <= 3 or (not ok and V.doorfail <= 5) then log("door tag -> " .. name_of(p):match("[^%.]+$") .. ": " .. (ok and tostring(e) or ("failed: " .. tostring(e)))) end
end

local MAX_ALIVE = 220                 -- no more referee spawns while this many enemies are alive
local function twins()
    if not V or not V.twins or not V.started or V.winner or not is_host() then return end
    for i = #V.pending, 1, -1 do                                     -- requests older than 5 s that gave nothing
        if tick - V.pending[i].t > 10 then table.remove(V.pending, i) end
    end
    local alive = 0
    for _, p in ipairs(FindAllOf("Character") or {}) do
        local okk, key = pcall(function() return p:GetAddress() end)
        if okk and key then
            local known = V.seen_enemy[key]
            if known == nil then                                     -- first look at this actor (names are slow: once each)
                known = is_enemy(p)
                V.seen_enemy[key] = known
                if known then
                    local l = loc(p)
                    if not l or (l.X == 0 and l.Y == 0) then V.seen_enemy[key] = nil end   -- not placed yet: look again
                    if l and (l.X ~= 0 or l.Y ~= 0) then
                        local sd = side_of_x(l.X)
                        local twin, td = nil, 1e18                   -- the closest open request on this side
                        for i, q in ipairs(V.pending) do
                            local d = (q.x - l.X) ^ 2 + (q.y - l.Y) ^ 2
                            if q.side == sd and d < td then twin, td = i, d end
                        end
                        V.eside[key] = sd
                        if not V.notag then give_door_tag(p) end
                        -- an enemy a player sent: its type AND near the spawner the send used (by type alone, a
                        -- wave orc of that type was taken for the sent one, and the sent one got a twin on the
                        -- sender's own side)
                        local sentone = false
                        local w = V.sentwait[sd]
                        if w and w.n > 0 and w.list then
                            local okd, def = pcall(function() return p.PawnDefinition end)
                            local dn = okd and valid(def) and name_of(def)
                            local best, bd = nil, 900 * 900
                            for i, e in ipairs(w.list) do
                                local d = (e.x - l.X) ^ 2 + (e.y - l.Y) ^ 2
                                if e.dn == dn and d < bd then best, bd = i, d end
                            end
                            if best then
                                table.remove(w.list, best); w.n = w.n - 1
                                sentone = true; V.sentin = (V.sentin or 0) + 1
                            end
                        end
                        if sentone then
                            -- not a wave orc and not a twin
                        elseif twin then                             -- one we asked for
                            table.remove(V.pending, twin)
                            V.made[sd] = V.made[sd] + 1
                        else                                         -- a wave orc
                            local okd, def = pcall(function() return p.PawnDefinition end)
                            if okd and valid(def) then
                                note_def(def)
                                V.wave[sd] = V.wave[sd] + 1; V.round_waves = V.round_waves + 1
                                V.lastwave = {p = p, key = key, t = tick}            -- newest mission enemy (keeper candidate)
                                if V.wave[sd] == 1 then log("wave orcs seen on side " .. SIDE[sd]) end
                                local pos = {X = l.X, Y = l.Y}
                                if V.round == 1 then table.insert(V.history, {def = def, l = pos, side = sd, t = tick - V.t0}) end
                                -- harder over time: the mission repeats wave 1 (looping wave script), so from wave 2 on
                                -- each wave orc brings 0.5 more extra copies per wave (wave 3: 1, wave 5: 2 ...), on both
                                -- sides; plus the old referee rounds if those ever run
                                local mult = (V.round - 1) + ((V.cwave or 1) > 1 and ((V.cwave - 1) * growth_orcs()) or 0)
                                V.acc = V.acc or {0, 0}
                                V.acc[sd] = V.acc[sd] + mult
                                local extra = math.floor(V.acc[sd]); V.acc[sd] = V.acc[sd] - extra
                                local paired = false
                                local dn = name_of(def)
                                for qi, q in ipairs(V.queue) do              -- the mission sent this one's twin itself
                                    if q.side == sd and q.mirror and q.dn == dn then
                                        table.remove(V.queue, qi); V.need[sd] = V.need[sd] - 1
                                        V.paired = (V.paired or 0) + 1; paired = true; break
                                    end
                                end
                                if paired then
                                    if extra > 0 then want(def, pos, sd, false, extra); want(def, pos, 3 - sd, true, extra) end
                                else
                                    want(def, pos, 3 - sd, true, 1 + extra)
                                    if extra > 0 then want(def, pos, sd, false, extra) end
                                end
                            end
                        end
                    end
                end
            elseif known then
                local okd, dying = pcall(function() return p.bActorIsBeingDestroyed end)
                if not (okd and dying) and valid(p) then alive = alive + 1 end
                if false and V.eside[key] and not V.dead[key] then          -- (kills are now seen by the death hooks)
                    local okh, dd = pcall(function() return p.HealthComponent:IsDeadOrDying() end)
                    if (okh and dd) or (okd and dying) then
                        V.dead[key] = true
                        table.insert(V.deaths, {side = V.eside[key], t = tick})
                    end
                end
            end
        end
    end
    V.alive = alive
    -- referee-run rounds (when the mission's own waves cannot be restarted): replay round 1, harder each round
    if V.replay then
        local r = V.replay
        local first = V.history[1].t                                 -- no break: the first orcs come at once
        while r.i <= #V.history and V.history[r.i].t - first <= (tick - r.t0) * r.speed do
            local h = V.history[r.i]; r.i = r.i + 1
            local n = V.round - 1                                    -- round 2: 1 extra per orc, round 3: 2 extra ...
            want(h.def, h.l, h.side, false, 1 + n)
            want(h.def, h.l, 3 - h.side, true, 1 + n)
        end
        -- the next round starts while the last orcs of this one are still alive: with the mission's waves over, the
        -- game declares victory as soon as no enemy is left
        if r.i > #V.history and #V.queue <= 4 and alive <= 12 and not r.done then
            r.done = tick; log("round " .. V.round .. " nearly cleared (" .. alive .. " left)")
        end
        if r.done then
            V.round = V.round + 1; pcall(scale_health)
            V.replay = {i = 1, t0 = tick, speed = 1.0}
            log("round " .. V.round .. " (run by the referee): " .. #V.history .. " wave orcs x" .. V.round .. " per side")
            show()
        end
    end
    local sent, i = 0, 1
    while i <= #V.queue and sent < 4 and V.tries < 20000 and alive < MAX_ALIVE do
        local q = V.queue[i]
        local t = q.side
        local onway = 0
        for _, r in ipairs(V.pending) do if r.side == t then onway = onway + 1 end end
        local mine, other = V.wave[t] + V.made[t] + onway, V.wave[3 - t] + V.made[3 - t]
        for _, r in ipairs(V.pending) do if r.side == 3 - t then other = other + 1 end end
        if tick - (q.t or 0) < 4 then                                -- 2 s to see whether the mission sends this twin itself
            i = i + 1
        elseif q.mirror and mine >= other then                       -- this side is not behind: no twin needed
            if tick - (q.t or 0) > 20 then table.remove(V.queue, i); V.skipped = (V.skipped or 0) + 1 else i = i + 1 end
        elseif q.mirror or V.made[t] + onway < V.need[t] then
            table.remove(V.queue, i)
            V.tries = V.tries + 1
            local ok, r = pcall(spawn_twin, q.def, q.l, t, q.mirror)
            if not ok then log("twin error: " .. tostring(r))
            elseif not r then log("twin: no spawner on side " .. SIDE[t])
            else table.insert(V.pending, {side = t, x = r.X, y = r.Y, t = tick}) end
            sent = sent + 1
        else
            i = i + 1
        end
    end
    if tick % 20 == 7 then
        log(string.format("balance: side A orcs %d (wave %d + ours %d), side B orcs %d (wave %d + ours %d), queued %d, alive %d, paired %d, not needed %d, sent in %d",
            V.wave[1] + V.made[1], V.wave[1], V.made[1], V.wave[2] + V.made[2], V.wave[2], V.made[2], #V.queue, alive, V.paired or 0, V.skipped or 0, V.sentin or 0))
    end
end

-- ---------- separate economy: kill coins go to the player whose side the orc died on ----------
-- The game splits every kill's coins evenly between all players (GrantCoinToPlayers: amount / players, the rest to
-- the host). The death hooks read every player's coins before and after each enemy's death handler, so each kill's
-- coins per player are known exactly. With 2 players the share of the player on the other side is moved to the
-- player on the orc's side. Solo test (file JW_ECONSOLO): the single player counts as side A, and coins from
-- side B kills are taken away. Host only.
local function econ_players()
    local list = {}
    for _, pc in ipairs(FindAllOf("PlayerController") or {}) do
        if inst(pc) then
            local okp, pawn = pcall(function() return pc.Pawn end)
            local oks, ps = pcall(function() return pc.PlayerState end)
            if okp and valid(pawn) and name_of(pawn):find("Hero") and oks and valid(ps) then
                local okh, h = pcall(function() return ps.bIsHost end)
                table.insert(list, {pc = pc, ps = ps, host = okh and (h == true or h == 1)})
            end
        end
    end
    -- same order as place_players(): first found = side A; one player (a solo test) stays where the game put them, so
    -- their side is where they stand
    for i, e in ipairs(list) do e.side = ((i - 1) % 2) + 1 end
    if #list == 1 and V and V.mid then
        local l = loc(list[1].pc.Pawn)
        if l then list[1].side = (l.X < V.mid) and 1 or 2 end
    end
    return list
end

local function coins()
    if not V or not V.started or V.winner or not is_host() then return end
    if not V.econ then
        if tick % 4 ~= 0 then return end
        local pl = econ_players()
        if #pl >= 2 or (#pl == 1 and V.econsolo) then
            V.econ = pl; V.kgrants = {}; V.snap = {}; V.moved = {0, 0}; V.kills = {0, 0}
            local who = {}
            for i, e in ipairs(pl) do who[#who + 1] = string.format("player %d side %s%s", i, SIDE[e.side], e.host and " (host)" or "") end
            log("economy on: " .. table.concat(who, ", ") .. (#pl == 1 and " (solo test: side B kills pay nothing)" or ""))
        end
        return
    end
    local host
    for _, e in ipairs(V.econ) do if e.host then host = e end end
    if not host then host = V.econ[1] end
    -- each kill's coins (seen by the death hooks): what players on the other side got goes to the orc's side
    local fix = {}                                     -- per player: + gets coins, - gives coins
    for i = 1, #V.econ do fix[i] = 0 end
    while #V.kgrants > 0 do
        local g = table.remove(V.kgrants, 1)
        local sd = g.side
        V.kills[sd] = V.kills[sd] + 1
        -- curses on the orc's side: "no money" = the kill pays nobody; "steal" = the kill pays the side that sent it
        local dest = sd
        if curse_on(sd, "steal") then dest = 3 - sd elseif curse_on(sd, "nomoney") then dest = nil end
        local n = 0
        for _, f in ipairs(V.econ) do if f.side == dest then n = n + 1 end end
        local function give(amount)
            if dest and n > 0 then for j, f in ipairs(V.econ) do if f.side == dest then fix[j] = fix[j] + amount / n end end end
        end
        for i, e in ipairs(V.econ) do
            if e.side ~= sd and g.d[i] > 0 then
                fix[i] = fix[i] - g.d[i]; give(g.d[i])
            elseif e.side == sd and dest ~= sd and g.d[i] > 0 then
                fix[i] = fix[i] - g.d[i]; give(g.d[i])                      -- the cursed side's own kill coins
                V.cursed_coins = (V.cursed_coins or 0) + g.d[i]
            end
        end
    end
    for i, e in ipairs(V.econ) do
        local m = math.floor(math.abs(fix[i]) + 0.5)
        if m > 0 then
            local ok, r = pcall(function()
                if fix[i] < 0 then
                    local have = e.ps.Coin
                    local take = math.min(m, have)
                    if take > 0 then e.ps:SpendCoin(take, 2) end              -- Correction
                    return take
                else
                    e.ps:GrantCoin(m, 0)                                    -- reason None: not seen as a kill grant
                    return m
                end
            end)
            V.moved[e.side] = V.moved[e.side] + ((fix[i] < 0) and -(ok and r or 0) or (ok and r or 0))
            if (V.coinlog or 0) < 15 or not ok then
                V.coinlog = (V.coinlog or 0) + 1
                log(string.format("coins: player %d (side %s) %s%d (%s)", i, SIDE[e.side], fix[i] < 0 and "-" or "+", m,
                    ok and "ok" or tostring(r)))
            end
        end
    end
    if tick % 40 == 13 then
        local c = {}
        for i, e in ipairs(V.econ) do local ok, v = pcall(function() return e.ps.Coin end); c[#c + 1] = string.format("player %d: %s", i, ok and tostring(v) or "?") end
        log(string.format("economy: kills A %d B %d, moved A %+d B %+d | %s", V.kills[1], V.kills[2], V.moved[1], V.moved[2], table.concat(c, ", ")))
    end
end

-- ---------- sending enemies to the other side (hotkeys F1-F6, paid with coins) ----------
-- The host's player presses a key: the price is taken from their coins and the group spawns on the opponent's
-- spawners (not counted for the twins' balance). A second player's keys are not seen yet (needs a way from the
-- client to the host).
local SEND = {
    {key = "F1", name = "5 light orcs",    pde = "Orcs/Orc_Light/Data/PDE_Orc_Light",           n = 5, cost = 1000},
    {key = "F2", name = "8 kobold runners", pde = "Kobolds/Kobold_Runner/Data/PDE_Kobold_Runner", n = 8, cost = 1200},
    {key = "F3", name = "2 heavy orcs",    pde = "Orcs/Orc_Heavy/Data/PDE_Orc_Heavy",           n = 2, cost = 1500},
    {key = "F4", name = "1 ogre",          pde = "Ogres/Ogre_Light/Data/PDE_Ogre_Light",        n = 1, cost = 2500},
    -- the game's unstable rift (the enemy that opens a small rift and lets enemies out until it is destroyed)
    {key = "F5", name = "1 unstable rift", pde = "UnstableRifts/Data/PDE_UnstableRift",         n = 1, cost = 5000, rift = true},
    -- a random curse on the other side (see CURSES further down)
    {key = "F6", name = "a curse",        n = 0, cost = 6000, curse = true},
}
local RISE = 5             -- each send of a type makes that player's next one of that type 5 % (of the base price) dearer
-- this player's price for this group now: base x (1 + rise x sends so far), counted per player and type, whole match
local function send_price(k, ps)
    local g = SEND[k]
    local key = ps and ps:GetAddress() or 0
    local c = (V.sends and V.sends[key] and V.sends[key][k]) or 0
    local tax = 1
    if ps and V.econ then
        for _, e in ipairs(V.econ) do if e.ps:GetAddress() == key then if curse_on(e.side, "tax") then tax = 2 end end end
    end
    return math.floor(g.cost * (1 + (V.rise or RISE) / 100 * c) * tax + 0.5), key
end
-- ---------- send strip: one slim row of buttons above the game's trap bar (key, what, price now, times sent) ----------
-- Built from plain UMG widgets on every PC for its own player. The price is red when this player's coins don't cover it.
local SHORT = {"5 orcs", "8 kobolds", "2 heavies", "1 ogre", "1 rift", "curse"}
-- the tiles' pictures: the game's own distortion / status icons (first one found), and the count shown on them
local ICONS = {
    {"/Game/UI/Icons/Distortions/Distortion_Light_Orc"},
    {"/Game/UI/Icons/Distortions/Distortion_Kobold"},
    {"/Game/UI/Icons/Distortions/Distortion_HeavyHitters", "/Game/UI/Icons/Distortions/Distortion_Medium_Orc"},
    {"/Game/UI/Icons/Distortions/Distortion_Ogre"},
    {"/Game/UI/Icons/Distortions/Distortion_Unstable_Rift_Every_Wave", "/Game/UI/Icons/Distortions/Distortion_UnstableOrc"},
    {"/Game/UI/Icons/StatusEffects/Icon_StatusEffect_Curse"},
}
local ICON_N = {"x5", "x8", "x2", "", "", ""}
local ICON_SIZE = 34                      -- (fallback icons only)
-- our own picture sheet (written by the map builder into every build): the game's icons with their backgrounds cut
-- out; each send's part of the 1000 x 564 sheet as U/V from-to
local ICON_SHEET = "/Game/Levels/Custom/JW_Shared/JWSendIcons.JWSendIcons"
local ICON_UV = {{0.01, 0.01773, 0.19, 0.33688}, {0.206, 0.01773, 0.386, 0.33688}, {0.402, 0.01773, 0.582, 0.33688},
                 {0.598, 0.01773, 0.778, 0.33688}, {0.794, 0.01773, 0.974, 0.33688}, {0.01, 0.36525, 0.19, 0.6844}}
local function icon_sheet()
    local t = StaticFindObject(ICON_SHEET)
    if not (t and t:IsValid()) and LoadAsset then pcall(function() LoadAsset(ICON_SHEET) end); t = StaticFindObject(ICON_SHEET) end
    if t and t:IsValid() then return t end
end
local function icon_tex(list)
    for _, path in ipairs(list or {}) do
        local short = path:match("[^/]+$")
        local full = path .. "." .. short
        local t = StaticFindObject(full)
        if not (t and t:IsValid()) and LoadAsset then pcall(function() LoadAsset(full) end); t = StaticFindObject(full) end
        if t and t:IsValid() then return t, short end
    end
end
local strip = nil
local STRIP_X, STRIP_Y = 294, -141  -- left edge and bottom, in UI units: on the game's hotbar, from its 4th slot (measured from screenshots)
local function rgba(r, g, b, a) return {R = r, G = g, B = b, A = a or 1.0} end
local function new(cls, outer, name) return StaticConstructObject(StaticFindObject("/Script/UMG." .. cls), outer, FName(name)) end
local function text_col(t, c) pcall(function() t:SetColorAndOpacity({SpecifiedColor = c, ColorUseRule = 0}) end) end
local function round_brush(b, col, radius, outline)
    pcall(function() b:SetBrushColor(col) end)
    pcall(function()
        local br = b.Background
        br.DrawAs = 4                                  -- RoundedBox
        local r = type(radius) == "table" and radius or {radius, radius, radius, radius}   -- top-left, top-right, bottom-right, bottom-left
        br.OutlineSettings.CornerRadii = {X = r[1], Y = r[2], Z = r[3], W = r[4]}
        br.OutlineSettings.RoundingType = 0            -- fixed radius
        if outline then br.OutlineSettings.Color = {SpecifiedColor = outline, ColorUseRule = 0}; br.OutlineSettings.Width = 2.0 end
        b:SetBrush(br)
    end)
end
-- the game's own hotbar font (the trap prices): copied from one of its text blocks, so the strip matches it
local game_font = nil
local function find_game_font()
    if game_font then return game_font end
    for _, t in ipairs(FindAllOf("TextBlock") or {}) do
        local ok, f = pcall(function()
            if t:GetFName():ToString():find("^JW") then return nil end
            local txt = t:GetText():ToString()
            if not txt:match("^%d[%d%s]*%d$") then return nil end       -- a price like "1 000"
            if (t.Font.Size or 0) < 14 then return nil end
            return t.Font
        end)
        if ok and f then game_font = f; log("send strip: using the hotbar's font from " .. name_of(t)); return f end
    end
end
local function style_text(t, size, col, outline)
    local f = find_game_font()
    if f then
        pcall(function() t.Font.FontObject = f.FontObject end)
        pcall(function() t.Font.TypefaceFontName = f.TypefaceFontName end)
    end
    pcall(function() t.Font.Size = size end)
    if outline then pcall(function() t.Font.OutlineSettings.OutlineSize = outline; t.Font.OutlineSettings.OutlineColor = rgba(0, 0, 0, 0.9) end) end
    pcall(function() t:SetShadowOffset({X = 1.0, Y = 1.0}) end)
    text_col(t, col)
end
local GOLD, GOLDDIM = rgba(0.79, 0.62, 0.30, 1), rgba(0.45, 0.42, 0.36, 1)
local TILE_W, TILE_H, TILE_GAP = 84, 80, 1   -- the game's hotbar slots: 84 x 80 UI units, 85 apart
local SEL_LIFT = 8                           -- how far the game lifts a selected hotbar slot (UI units, from a screenshot)
local FOG_DENSITY, FOG_FALLOFF = 3.0, 10.0    -- pit fog: thickness at its base (10 m down) and how fast it thins upward
local function make_strip()
    local gi = FindFirstOf("GameInstance")
    local w = new("UserWidget", gi, "JWSendStrip")
    w.WidgetTree = new("WidgetTree", w, "JWSendStripTree")
    local canvas = new("CanvasPanel", w.WidgetTree, "JWSendStripCanvas")
    w.WidgetTree.RootWidget = canvas
    local row = new("HorizontalBox", w.WidgetTree, "JWSendRow")
    local slot = canvas:AddChildToCanvas(row)
    pcall(function() slot:SetAutoSize(true) end)
    pcall(function() slot:SetAnchors({Minimum = {X = 0.0, Y = 1.0}, Maximum = {X = 0.0, Y = 1.0}}) end)
    pcall(function() slot:SetAlignment({X = 0.0, Y = 1.0}) end)
    pcall(function() slot:SetPosition({X = STRIP_X, Y = STRIP_Y}) end)
    -- (for tuning: where the game's own hotbar sits)
    pcall(function()
        local hb = FindFirstOf("W_HUD_Hotbar_C")
        local hs = hb.Slot
        log(string.format("hotbar widget %s in %s", name_of(hb), name_of(hs)))
        local p, z, al = hs:GetPosition(), hs:GetSize(), hs:GetAlignment()
        log(string.format("  hotbar slot position %.0f, %.0f size %.0f x %.0f alignment %.2f, %.2f", p.X, p.Y, z.X, z.Y, al.X, al.Y))
    end)
    local function txt(name, size, col, outline)
        local t = new("TextBlock", w.WidgetTree, name)
        style_text(t, size, col, outline)
        pcall(function() t:SetJustification(1) end)
        return t
    end
    local function add_h(parent, child, pad)
        local s2 = parent:AddChildToHorizontalBox(child)
        pcall(function() s2:SetVerticalAlignment(3) end)            -- bottom
        if pad then pcall(function() s2:SetPadding({Left = pad, Top = 0, Right = 0, Bottom = 0}) end) end
        return s2
    end
    local function add_v(parent, child)
        local s2 = parent:AddChildToVerticalBox(child)
        pcall(function() s2:SetHorizontalAlignment(2) end)          -- centre
        return s2
    end
    -- the game's own trap slot (4th slot of the HUD's hotbar): every visible picture layer of it (background, fill,
    -- gold edge ...) with its own colour, and its price font, so our tiles look exactly like it
    local look = nil
    local SKIP = {"Icon", "Select", "Highlight", "Hover", "Glow", "Cooldown", "Lock", "Flash", "New", "Count", "Key", "Number", "Pulse", "Disabled", "Equipped", "Charge", "Item"}   -- (Image_FullyUpgraded is the gold edge: kept)
    local function skip_name(n) for _, k in ipairs(SKIP) do if n:find(k, 1, true) then return true end end return false end
    local function col_s(c) return c and string.format("%.2f %.2f %.2f %.2f", c.R or 0, c.G or 0, c.B or 0, c.A or 0) or "-" end
    local function walk(wd, depth, out)
        if not wd or depth > 12 then return end
        local cls, nm = "?", "?"
        pcall(function() cls = wd:GetClass():GetFName():ToString() end)
        pcall(function() nm = wd:GetFName():ToString() end)
        local vis = 0; pcall(function() vis = wd:GetVisibility() end)
        local op = 1; pcall(function() op = wd:GetRenderOpacity() end)
        local shown = vis ~= 1 and vis ~= 2 and op > 0.01
        local info = ""
        if cls == "Image" then
            local res, tint, coa = "-", nil, nil
            pcall(function() res = wd.Brush.ResourceObject:GetFName():ToString() end)
            pcall(function() tint = wd.Brush.TintColor.SpecifiedColor end)
            pcall(function() coa = wd.ColorAndOpacity end)
            info = string.format(" res=%s tint=%s col=%s", res, col_s(tint), col_s(coa))
            local edge = nm == "Image_FullyUpgraded"                  -- the gold edge: always ours, whatever the slot's upgrades
            if (shown or edge) and not skip_name(nm) then out[#out + 1] = {kind = "img", brush = wd.Brush, col = coa, op = edge and 1 or op, name = nm} end
        elseif cls == "Border" then
            local bc = nil; pcall(function() bc = wd.BrushColor end)
            info = " brushcol=" .. col_s(bc)
            if shown and not skip_name(nm) then out[#out + 1] = {kind = "border", brush = wd.Background, col = bc, op = op, name = nm} end
        end
        log(string.format("  slot %s%s %s vis=%d op=%.2f%s", string.rep(" ", depth), cls, nm, vis, op, info))
        local n = 0; pcall(function() n = wd:GetChildrenCount() end)
        for i = 0, n - 1 do local ch; pcall(function() ch = wd:GetChildAt(i) end); walk(ch, depth + 1, out) end
        if n == 0 then local ct; pcall(function() ct = wd:GetContent() end); if ct then walk(ct, depth + 1, out) end end
    end
    pcall(function()
        for _, sl in ipairs(FindAllOf("W_HotbarSlot_C") or {}) do
            local n = name_of(sl)
            if not n:find("Default__", 1, true) and not n:find("ThreadSelect", 1, true) then
                local num = -1
                pcall(function() num = sl["Slot Number"] end)
                if num >= 4 then                                           -- a trap slot (key 4 and on; 3 is the barricades)
                    local layers = {}
                    log("send strip: layers of hotbar slot #" .. num)
                    walk(sl.WidgetTree.RootWidget, 0, layers)
                    local f = nil; pcall(function() f = sl.Text_CoinCost.Font end)
                    look = {layers = layers, font = f, from = n .. " #" .. num}
                    -- the key under the slot: the game's input action widget (a diamond with the key in it)
                    pcall(function()
                        local act = sl.Action
                        local kl, kf = {}, nil
                        local function kwalk(wd, depth)
                            if not wd or depth > 10 then return end
                            local cls, nm = "?", "?"
                            pcall(function() cls = wd:GetClass():GetFName():ToString() end)
                            pcall(function() nm = wd:GetFName():ToString() end)
                            local vis = 0; pcall(function() vis = wd:GetVisibility() end)
                            local res = "-"; pcall(function() res = wd.Brush.ResourceObject:GetFName():ToString() end)
                            log(string.format("  key %s%s %s vis=%d res=%s", string.rep(" ", depth), cls, nm, vis, res))
                            if cls == "Image" and vis ~= 1 and vis ~= 2 and res ~= "-" then
                                local coa; pcall(function() coa = wd.ColorAndOpacity end)
                                kl[#kl + 1] = {brush = wd.Brush, col = coa}
                            end
                            if (cls:find("TextBlock")) and not kf then pcall(function() kf = {font = wd.Font, col = wd.ColorAndOpacity} end) end
                            local n2 = 0; pcall(function() n2 = wd:GetChildrenCount() end)
                            for i = 0, n2 - 1 do local ch; pcall(function() ch = wd:GetChildAt(i) end); kwalk(ch, depth + 1) end
                            if n2 == 0 then
                                local ct; pcall(function() ct = wd:GetContent() end)
                                if ct then kwalk(ct, depth + 1) end
                                local wt; pcall(function() wt = wd.WidgetTree.RootWidget end)
                                if wt then kwalk(wt, depth + 1) end
                            end
                        end
                        kwalk(act.WidgetTree.RootWidget, 0)
                        local kw, kh = 30, 30
                        pcall(function() local b = sl.ActionSizeBox; if b.WidthOverride > 0 then kw = b.WidthOverride end; if b.HeightOverride > 0 then kh = b.HeightOverride end end)
                        look.key = {layers = kl, font = kf, w = kw, h = kh}
                        log(string.format("send strip: key look %d layer(s), %s font, %d x %d", #kl, kf and "with" or "no", kw, kh))
                    end)
                    if #layers == 0 then look.layers = {{kind = "img", brush = sl.Image_Background.Brush}} end
                    break
                end
            end
        end
    end)
    if not look then
        local names = {}
        for i, sl in ipairs(FindAllOf("W_HotbarSlot_C") or {}) do if i <= 4 then names[#names + 1] = name_of(sl) end end
        log("send strip: no hotbar slot found; slots: " .. table.concat(names, " | "))
    else
        local ns = {}; for _, L in ipairs(look.layers) do ns[#ns + 1] = L.name or "?" end
        log("send strip: copying layers " .. table.concat(ns, ", "))
    end
    log("send strip: hotbar slot look " .. (look and ("from " .. look.from) or "not found, own frame"))
    local function price_text(t, size)
        if look and look.font then
            pcall(function() t.Font.FontObject = look.font.FontObject end)
            pcall(function() t.Font.TypefaceFontName = look.font.TypefaceFontName end)
            pcall(function() t.Font.OutlineSettings.OutlineSize = look.font.OutlineSettings.OutlineSize; t.Font.OutlineSettings.OutlineColor = look.font.OutlineSettings.OutlineColor end)
            pcall(function() t.Font.Size = size end)
        end
    end
    -- one tile like the game's hotbar slots (its own background image when found, else a gold frame)
    local function tile(name)
        local col = new("VerticalBox", w.WidgetTree, name .. "Col")
        local size = new("SizeBox", w.WidgetTree, name .. "Size")
        pcall(function() size:SetWidthOverride(TILE_W) end); pcall(function() size:SetHeightOverride(TILE_H) end)
        local inner = new("VerticalBox", w.WidgetTree, name .. "In")      -- (filled top to bottom, spread out)
        if look then
            local ov = new("Overlay", w.WidgetTree, name .. "Ov")
            for li, L in ipairs(look.layers) do                       -- the slot's layers, bottom to top, each in its own colour
                local lw
                if L.kind == "border" then
                    lw = new("Border", w.WidgetTree, name .. "Bg" .. li)
                    pcall(function() lw:SetBrush(L.brush) end)
                    if L.col then pcall(function() lw:SetBrushColor(L.col) end) end
                else
                    lw = new("Image", w.WidgetTree, name .. "Bg" .. li)
                    pcall(function() lw:SetBrush(L.brush) end)
                    if L.col then pcall(function() lw:SetColorAndOpacity(L.col) end) end
                end
                if L.op and L.op < 1 then pcall(function() lw:SetRenderOpacity(L.op) end) end
                local o1 = ov:AddChildToOverlay(lw)
                pcall(function() o1:SetHorizontalAlignment(0) end); pcall(function() o1:SetVerticalAlignment(0) end)
            end
            local o2 = ov:AddChildToOverlay(inner)
            pcall(function() o2:SetHorizontalAlignment(0) end); pcall(function() o2:SetVerticalAlignment(0) end)
            pcall(function() o2:SetPadding({Left = 3, Top = 5, Right = 3, Bottom = 4}) end)
            size:SetContent(ov)
            add_v(col, size)
            return col, ov, inner, true
        end
        local b = new("Border", w.WidgetTree, name .. "Frame")
        round_brush(b, rgba(0.09, 0.075, 0.06, 0.88), 6, GOLD)
        pcall(function() b:SetPadding({Left = 2, Top = 4, Right = 2, Bottom = 3}) end)
        pcall(function() b:SetHorizontalAlignment(2) end); pcall(function() b:SetVerticalAlignment(2) end)
        size:SetContent(b)
        add_v(col, size)
        b:SetContent(inner)
        return col, b, inner
    end
    -- the key above each tile, like the game's number keys under its slots (the same diamond when found)
    local KEY_GAP = 3
    local function keybox(name, text)
        local kk = look and look.key
        local sz = new("SizeBox", w.WidgetTree, name .. "KSz")
        local kw, kh = 30, 30
        pcall(function() sz:SetWidthOverride(kw) end); pcall(function() sz:SetHeightOverride(kh) end)
        local ov = new("Overlay", w.WidgetTree, name .. "KOv")
        if true then                                                        -- the game's number keys: a dark diamond, no edge
            local dsz = new("SizeBox", w.WidgetTree, name .. "KDs")
            local side = math.floor(math.min(kw, kh) * 0.70)
            pcall(function() dsz:SetWidthOverride(side) end); pcall(function() dsz:SetHeightOverride(side) end)
            local d = new("Border", w.WidgetTree, name .. "KD")
            round_brush(d, rgba(0.035, 0.04, 0.06, 0.92), 2)
            dsz:SetContent(d)
            pcall(function() dsz:SetRenderTransformAngle(45.0) end)
            local o1 = ov:AddChildToOverlay(dsz)
            pcall(function() o1:SetHorizontalAlignment(2) end); pcall(function() o1:SetVerticalAlignment(2) end)
        elseif kk and #kk.layers > 0 then
            for li, L in ipairs(kk.layers) do
                local im = new("Image", w.WidgetTree, name .. "KBg" .. li)
                pcall(function() im:SetBrush(L.brush) end)
                if L.col then pcall(function() im:SetColorAndOpacity(L.col) end) end
                local o1 = ov:AddChildToOverlay(im)
                pcall(function() o1:SetHorizontalAlignment(0) end); pcall(function() o1:SetVerticalAlignment(0) end)
            end
        else
            local b = new("Border", w.WidgetTree, name .. "KBg")
            round_brush(b, rgba(0.07, 0.06, 0.05, 0.9), 4, GOLD)
            local o1 = ov:AddChildToOverlay(b)
            pcall(function() o1:SetHorizontalAlignment(0) end); pcall(function() o1:SetVerticalAlignment(0) end)
        end
        local t = txt(name .. "KT", 11, rgba(0.95, 0.95, 0.95), 0)
        price_text(t, 11)                                                   -- the game's font
        t:SetText(FText(text))
        local o2 = ov:AddChildToOverlay(t)
        pcall(function() o2:SetHorizontalAlignment(2) end); pcall(function() o2:SetVerticalAlignment(2) end)
        sz:SetContent(ov)
        return sz, t, kh
    end
    local function top_space(colw, nm, hgt)                                   -- room for the key above the head tile
        local sp = new("Spacer", w.WidgetTree, nm)
        pcall(function() sp:SetSize({X = 1, Y = hgt}) end)
        colw:InsertChildAt(0, sp)
    end
    local hcol, hb_, hin = tile("JWSendHead")
    local fill_sp = function(nm)                                              -- a spacer that takes the free height
        local sp = new("Spacer", w.WidgetTree, nm)
        local ss = hin:AddChildToVerticalBox(sp)
        pcall(function() ss:SetSize({SizeRule = 1, Value = 1.0}) end)
    end
    fill_sp("JWSendHeadSp1")
    local head = txt("JWSendHeadT", 12, rgba(0.95, 0.82, 0.48), 1); add_v(hin, head)
    fill_sp("JWSendHeadSp2")                                                -- (centred top to bottom)
    local coins = nil                                                       -- (the game shows the coins already)
    local _, _, khh = keybox("JWSendProbe", "")                             -- (the key's height, for the head's spacer)
    pcall(function() top_space(hcol, "JWSendHeadTop", khh + KEY_GAP) end)
    add_h(row, hcol)
    local sheet = icon_sheet()
    log("send strip: picture sheet " .. (sheet and "found" or "not found (old build: the game's icons)"))
    local chips = {}
    for k, g in ipairs(SEND) do
        local col = new("VerticalBox", w.WidgetTree, "JWSend" .. k .. "Col")
        local kb, kt = keybox("JWSend" .. k, g.key)
        add_v(col, kb)
        local gap = new("Spacer", w.WidgetTree, "JWSend" .. k .. "Gap"); pcall(function() gap:SetSize({X = 1, Y = KEY_GAP}) end); add_v(col, gap)
        local size = new("SizeBox", w.WidgetTree, "JWSend" .. k .. "Size")
        pcall(function() size:SetWidthOverride(TILE_W) end); pcall(function() size:SetHeightOverride(TILE_H) end)
        local ov = new("Overlay", w.WidgetTree, "JWSend" .. k .. "Ov")
        local b = ov
        if look then                                                         -- the slot's own layers (frame, fill, gold edge)
            for li, L in ipairs(look.layers) do
                local lw
                if L.kind == "border" then
                    lw = new("Border", w.WidgetTree, "JWSend" .. k .. "Bg" .. li)
                    pcall(function() lw:SetBrush(L.brush) end)
                    if L.col then pcall(function() lw:SetBrushColor(L.col) end) end
                else
                    lw = new("Image", w.WidgetTree, "JWSend" .. k .. "Bg" .. li)
                    pcall(function() lw:SetBrush(L.brush) end)
                    if L.col then pcall(function() lw:SetColorAndOpacity(L.col) end) end
                end
                if L.op and L.op < 1 then pcall(function() lw:SetRenderOpacity(L.op) end) end
                local o1 = ov:AddChildToOverlay(lw)
                pcall(function() o1:SetHorizontalAlignment(0) end); pcall(function() o1:SetVerticalAlignment(0) end)
            end
        else
            local fr = new("Border", w.WidgetTree, "JWSend" .. k .. "Frame")
            round_brush(fr, rgba(0.09, 0.075, 0.06, 0.88), 6, GOLD)
            local o1 = ov:AddChildToOverlay(fr)
            pcall(function() o1:SetHorizontalAlignment(0) end); pcall(function() o1:SetVerticalAlignment(0) end)
            b = fr
        end
        -- the picture fills the tile (like the trap pictures), the price sits over its bottom edge
        local pic_ok = false
        local pw, ph = TILE_W - 10, TILE_H - 10
        pcall(function()
            local im = new("Image", w.WidgetTree, "JWSendPic" .. k)
            if sheet then
                im:SetBrushFromTexture(sheet, false)
                local uv = ICON_UV[k]
                local br = im.Brush
                br.ImageSize = {X = 180.0, Y = 180.0}
                br.UVRegion = {Min = {X = uv[1], Y = uv[2]}, Max = {X = uv[3], Y = uv[4]}, bIsValid = true}
                im:SetBrush(br)
                if k == 1 then
                    local m = "?"; pcall(function() m = string.format("%.3f-%.3f valid %s", im.Brush.UVRegion.Min.X, im.Brush.UVRegion.Max.X, tostring(im.Brush.UVRegion.bIsValid)) end)
                    log("send strip: picture part " .. m)
                end
            else
                local tex = icon_tex(ICONS[k]); if not tex then error("no icon") end
                im:SetBrushFromTexture(tex, false)
            end
            local psz = new("SizeBox", w.WidgetTree, "JWSendPicSz" .. k)
            psz:SetWidthOverride(pw); psz:SetHeightOverride(ph)
            psz:SetContent(im)
            local a = ov:AddChildToOverlay(psz)
            pcall(function() a:SetHorizontalAlignment(2) end); pcall(function() a:SetVerticalAlignment(1) end)
            pcall(function() a:SetPadding({Left = 0, Top = 3, Right = 0, Bottom = 0}) end)
            pic_ok = true
        end)
        if not pic_ok then
            local nt = txt("JWSendName" .. k, 10, rgba(0.92, 0.88, 0.80), 1); nt:SetText(FText(SHORT[k]))
            local a = ov:AddChildToOverlay(nt)
            pcall(function() a:SetHorizontalAlignment(2) end); pcall(function() a:SetVerticalAlignment(2) end)
        end
        if ICON_N[k] ~= "" then                                              -- how many: top right
            local ct = txt("JWSendCnt" .. k, 14, rgba(1, 0.95, 0.8), 2); ct:SetText(FText(ICON_N[k]))
            local a = ov:AddChildToOverlay(ct)
            pcall(function() a:SetHorizontalAlignment(3) end); pcall(function() a:SetVerticalAlignment(1) end)
            pcall(function() a:SetPadding({Left = 0, Top = 3, Right = 6, Bottom = 0}) end)
        end
        local sent = txt("JWSendSent" .. k, 11, rgba(0.95, 0.82, 0.48), 2)   -- sent so far: top left
        local a2 = ov:AddChildToOverlay(sent)
        pcall(function() a2:SetHorizontalAlignment(1) end); pcall(function() a2:SetVerticalAlignment(1) end)
        pcall(function() a2:SetPadding({Left = 6, Top = 4, Right = 0, Bottom = 0}) end)
        local psize = 15                                                    -- (the hotbar's own 28 is in another scale: far too big)
        local pt = txt("JWSendPrice" .. k, psize, rgba(1, 1, 1), 1); price_text(pt, psize)
        local a3 = ov:AddChildToOverlay(pt)
        pcall(function() a3:SetHorizontalAlignment(2) end); pcall(function() a3:SetVerticalAlignment(3) end)
        pcall(function() a3:SetPadding({Left = 0, Top = 0, Right = 0, Bottom = 1}) end)
        size:SetContent(ov)
        add_v(col, size)
        add_h(row, col, TILE_GAP)
        chips[k] = {b = b, price = pt, key = kt, sent = sent, kname = g.key, img = look ~= nil, col = col}
    end
    pcall(function() w:SetOwningPlayer(local_pc()) end)
    w:AddToViewport(499)
    return {w = w, head = head, coins = coins, chips = chips, hcol = hcol}
end
local function fmt(n) local s0 = tostring(math.floor(n)); return (s0:reverse():gsub("(%d%d%d)", "%1 "):reverse():gsub("^ ", "")) end
local function update_strip()
    if V then pcall(msg_text, (V.msg and tick - V.msg.t < 10) and V.msg.text or "") end    -- (the message's 5 s run out)
    if not V or not V.started or V.send_on == false then
        if strip and valid(strip.w) then pcall(function() strip.w:SetVisibility(1) end) end   -- Collapsed
        return
    end
    if not (strip and valid(strip.w)) then
        if (V.strip_fail or 0) >= 3 then return end
        if not icon_sheet() and (V.sheet_wait or 0) < 10 then V.sheet_wait = (V.sheet_wait or 0) + 1; return end   -- (5 s for the pictures)
        local ok, r = pcall(make_strip)
        if not ok then V.strip_fail = (V.strip_fail or 0) + 1; log("send strip failed: " .. tostring(r)); return end
        strip = r; log("send strip created")
    end
    pcall(function() strip.w:SetVisibility(4) end)                    -- SelfHitTestInvisible: shown, never takes the mouse
    local pc = local_pc()
    local ps; pcall(function() ps = pc.PlayerState end)
    local have = 0; pcall(function() have = ps.Coin end)
    local sd = my_side() or 1
    pcall(function() strip.head:SetText(FText("SEND\nTO\nSIDE " .. SIDE[3 - sd])) end)

    -- a tile rises with the trap slot under it when that slot is selected (the game lifts the selected slot)
    if tick % 2 == 0 then
        local cols = {strip.hcol}
        for k, c in ipairs(strip.chips) do cols[k + 1] = c.col end
        local slots = {}
        for _, sl in ipairs(FindAllOf("W_HotbarSlot_C") or {}) do
            pcall(function()
                local n = name_of(sl)
                if n:find("Default__", 1, true) or n:find("ThreadSelect", 1, true) then return end
                local num = sl["Slot Number"]
                if num and num >= 4 and num <= 4 + #SEND and not slots[num] then slots[num] = sl end
            end)
        end
        for i, col in ipairs(cols) do
            local sl = slots[3 + i]
            local lift = 0
            if sl then
                pcall(function()
                    local t = sl.RenderTransform.Translation.Y
                    if math.abs(t) > 0.5 then lift = -t; return end
                    local v = sl.Image_Selected:GetVisibility()
                    if v ~= 1 and v ~= 2 then lift = SEL_LIFT end
                end)
            end
            if col.__lift ~= lift then
                col.__lift = lift
                pcall(function() col:SetRenderTranslation({X = 0.0, Y = -lift}) end)
            end
        end
    end
    for k, c in ipairs(strip.chips) do
        local n
        if is_host() then
            local key = ps and ps:GetAddress()
            n = (V.sends and key and V.sends[key] and V.sends[key][k]) or 0
        else n = (V.mysends and V.mysends[k]) or 0 end
        local price = math.floor(SEND[k].cost * (1 + (V.rise or RISE) / 100 * n) + 0.5)
        local broke = have < price
        pcall(function() c.price:SetText(FText(fmt(price))) end)

        if c.broke ~= broke then
            c.broke = broke
            text_col(c.price, broke and rgba(1.0, 0.45, 0.4) or rgba(1, 1, 1))
            if not c.img then round_brush(c.b, rgba(0.09, 0.075, 0.06, 0.88), 6, broke and GOLDDIM or GOLD) end
            pcall(function() c.col:SetRenderOpacity(broke and 0.65 or 1.0) end)
        end
    end
end

-- ---------- scoreboard at the top: SIDE A | wave | SIDE B, like a sports score bug ----------
local board = nil
local BOARD_COL = {rgba(0.10, 0.35, 0.85, 0.92), rgba(0.80, 0.12, 0.12, 0.92)}
local function make_board()
    local gi = FindFirstOf("GameInstance")
    local w = new("UserWidget", gi, "JWBoard")
    w.WidgetTree = new("WidgetTree", w, "JWBoardTree")
    local canvas = new("CanvasPanel", w.WidgetTree, "JWBoardCanvas")
    w.WidgetTree.RootWidget = canvas
    local colm = new("VerticalBox", w.WidgetTree, "JWBoardCol")
    local slot = canvas:AddChildToCanvas(colm)
    pcall(function() slot:SetAutoSize(true) end)
    pcall(function() slot:SetAnchors({Minimum = {X = 0.5, Y = 0.0}, Maximum = {X = 0.5, Y = 0.0}}) end)
    pcall(function() slot:SetAlignment({X = 0.5, Y = 0.0}) end)
    pcall(function() slot:SetPosition({X = 0.0, Y = 18.0}) end)
    local row = new("HorizontalBox", w.WidgetTree, "JWBoardRow")
    local rs = colm:AddChildToVerticalBox(row); pcall(function() rs:SetHorizontalAlignment(2) end)
    local function txt(name, size, col, outline)
        local t = new("TextBlock", w.WidgetTree, name)
        style_text(t, size, col, outline)
        pcall(function() t:SetJustification(1) end)
        return t
    end
    local function block(name, width, col, radii)
        local sb = new("SizeBox", w.WidgetTree, name .. "Size")
        pcall(function() sb:SetWidthOverride(width) end); pcall(function() sb:SetHeightOverride(64) end)
        local b = new("Border", w.WidgetTree, name)
        round_brush(b, col, radii)
        pcall(function() b:SetPadding({Left = 10, Top = 0, Right = 10, Bottom = 0}) end)
        pcall(function() b:SetHorizontalAlignment(2) end); pcall(function() b:SetVerticalAlignment(2) end)
        sb:SetContent(b)
        local s2 = row:AddChildToHorizontalBox(sb)
        pcall(function() s2:SetVerticalAlignment(2) end)
        return b
    end
    local function side(i)
        local b = block("JWBoardSide" .. i, 190, BOARD_COL[i], i == 1 and {10, 0, 0, 10} or {0, 10, 10, 0})
        local hb = new("HorizontalBox", w.WidgetTree, "JWBoardSideRow" .. i)
        b:SetContent(hb)
        local lab = new("VerticalBox", w.WidgetTree, "JWBoardLab" .. i)
        local name = txt("JWBoardName" .. i, 16, rgba(1, 1, 1), 1); name:SetText(FText("SIDE " .. SIDE[i]))
        local you = txt("JWBoardYou" .. i, 10, rgba(1, 1, 1, 0.85), 1)
        local s1 = lab:AddChildToVerticalBox(name); pcall(function() s1:SetHorizontalAlignment(2) end)
        local s2 = lab:AddChildToVerticalBox(you); pcall(function() s2:SetHorizontalAlignment(2) end)
        local score = txt("JWBoardScore" .. i, 28, rgba(1, 1, 1), 2)
        local first, second = lab, score
        if i == 2 then first, second = score, lab end
        local a = hb:AddChildToHorizontalBox(first); pcall(function() a:SetVerticalAlignment(2) end)
        local c = hb:AddChildToHorizontalBox(second); pcall(function() c:SetVerticalAlignment(2) end)
        pcall(function() (i == 1 and c or a):SetPadding(i == 1 and {Left = 16, Top = 0, Right = 0, Bottom = 0} or {Left = 0, Top = 0, Right = 16, Bottom = 0}) end)
        return {score = score, you = you, border = b}
    end
    local A = side(1)
    local mid = block("JWBoardMid", 170, rgba(0.05, 0.045, 0.04, 0.9), 0)
    local vb = new("VerticalBox", w.WidgetTree, "JWBoardMidCol")
    mid:SetContent(vb)
    local wave = txt("JWBoardWave", 18, rgba(0.95, 0.82, 0.48), 1)
    local info = txt("JWBoardInfo", 10, rgba(0.85, 0.82, 0.76), 1)
    local s1 = vb:AddChildToVerticalBox(wave); pcall(function() s1:SetHorizontalAlignment(2) end)
    local s2 = vb:AddChildToVerticalBox(info); pcall(function() s2:SetHorizontalAlignment(2) end)
    local Bside = side(2)
    -- under the board: a tinted black band saying which side you are, in your side's colour
    local bsz = new("SizeBox", w.WidgetTree, "JWBoardBandSize")
    pcall(function() bsz:SetWidthOverride(190 + 170 + 190) end)
    local band = new("Border", w.WidgetTree, "JWBoardBand")
    round_brush(band, rgba(0, 0, 0, 0.6), {0, 0, 10, 10})
    pcall(function() band:SetPadding({Left = 8, Top = 2, Right = 8, Bottom = 3}) end)
    pcall(function() band:SetHorizontalAlignment(2) end)
    bsz:SetContent(band)
    local bs = colm:AddChildToVerticalBox(bsz); pcall(function() bs:SetHorizontalAlignment(2) end)
    local you = txt("JWBoardBandText", 14, rgba(1, 1, 1), 1)
    band:SetContent(you)
    pcall(function() w:SetOwningPlayer(local_pc()) end)
    w:AddToViewport(500)
    pcall(function() w:SetVisibility(4) end)                          -- shown, never takes the mouse
    return {w = w, sides = {A, Bside}, wave = wave, info = info, you = you}
end
board_update = function()
    if not V then return end
    if not (board and valid(board.w)) then
        if (V.board_fail or 0) >= 3 then error("no scoreboard") end
        local ok, r = pcall(make_board)
        if not ok then V.board_fail = (V.board_fail or 0) + 1; log("scoreboard failed: " .. tostring(r)); error(r) end
        board = r; log("scoreboard created")
    end
    local mine = my_side()
    if mine and board.youside ~= mine then
        board.youside = mine
        pcall(function() board.you:SetText(FText(string.format("YOU ARE SIDE %s  -  defend the %s pin", SIDE[mine], SIDEWORD[mine]))) end)
        text_col(board.you, SIDECOL[mine] and rgba(SIDECOL[mine].R, SIDECOL[mine].G, SIDECOL[mine].B) or rgba(1, 1, 1))
    end
    for i = 1, 2 do
        local sd = board.sides[i]
        pcall(function() sd.score:SetText(FText(tostring(math.max(V.lives[i], 0)))) end)
        pcall(function() sd.you:SetText(FText(mine == i and "YOU" or (V.winner == i and "WINS" or " "))) end)
    end
    local cw = V.cwave or 1
    pcall(function() board.wave:SetText(FText(V.winner and (V.winner == 0 and "DRAW" or "FINAL") or ("WAVE " .. cw))) end)
    local info = " "
    if not V.winner and cw > 1 then info = string.format("x%.1f orcs  x%.2f health", 1 + (cw - 1) * growth_orcs(), 1 + (cw - 1) * growth_health()) end
    pcall(function() board.info:SetText(FText(info)) end)
end
-- the game's own rift point counter (the shared pool, A + B) only confuses in VS: hidden while a match runs
-- ---------- map pins over the rifts and a team dot over every enemy ----------
-- Both are small UMG widgets in a WidgetComponent in screen space: drawn flat on the screen at a point in the world,
-- always facing the camera, the same size at any distance. Made on every PC for itself (nothing is sent).
local WC = nil
local function widget_comp(actor, z, wd, size, pivot, world)
    WC = WC or StaticFindObject("/Script/UMG.WidgetComponent")
    local c = actor:AddComponentByClass(WC, false, {Rotation = {X = 0, Y = 0, Z = 0, W = 1}, Translation = {X = 0, Y = 0, Z = z}, Scale3D = {X = 1, Y = 1, Z = 1}}, false)
    pcall(function() c:SetWidgetSpace(world and 0 or 1) end)            -- World (hidden behind walls) or Screen
    if world then
        pcall(function() c:SetTwoSided(true) end)
        pcall(function() c:SetBlendMode(1) end)                             -- Masked: solid colours, no see-through
        pcall(function() c:SetRelativeScale3D({X = world, Y = world, Z = world}) end)
    end
    pcall(function() c:SetDrawSize(size) end)
    pcall(function() c:SetPivot(pivot) end)
    pcall(function() c:SetCollisionEnabled(0) end)
    c:SetWidget(wd)
    return c
end
local function circle_widget(name, d, col, letter, needle)
    local gi = FindFirstOf("GameInstance")
    local w = new("UserWidget", gi, name)
    w.WidgetTree = new("WidgetTree", w, name .. "T")
    local vb = new("VerticalBox", w.WidgetTree, name .. "V")
    w.WidgetTree.RootWidget = vb
    local sb = new("SizeBox", w.WidgetTree, name .. "S")
    pcall(function() sb:SetWidthOverride(d) end); pcall(function() sb:SetHeightOverride(d) end)
    -- the head: a ball in the side's colour with a gold rim (the game's UI gold), a shine at the top left, and the
    -- letter in the middle
    local ov = new("Overlay", w.WidgetTree, name .. "O")
    sb:SetContent(ov)
    local b = new("Border", w.WidgetTree, name .. "B")
    round_brush(b, col, d / 2, letter and GOLD or rgba(1, 1, 1, 1))
    pcall(function() local br = b.Background; br.OutlineSettings.Width = letter and 4.0 or 2.0; b:SetBrush(br) end)
    local os1 = ov:AddChildToOverlay(b)
    pcall(function() os1:SetHorizontalAlignment(0) end); pcall(function() os1:SetVerticalAlignment(0) end)   -- fill
    if letter then
        local hs = new("SizeBox", w.WidgetTree, name .. "HS")
        pcall(function() hs:SetWidthOverride(d * 0.28) end); pcall(function() hs:SetHeightOverride(d * 0.2) end)
        local hl = new("Border", w.WidgetTree, name .. "H")
        round_brush(hl, rgba(1, 1, 1, 0.45), d * 0.1)
        hs:SetContent(hl)
        local os2 = ov:AddChildToOverlay(hs)
        pcall(function() os2:SetHorizontalAlignment(1) end); pcall(function() os2:SetVerticalAlignment(1) end)  -- left, top
        pcall(function() os2:SetPadding({Left = d * 0.2, Top = d * 0.14, Right = 0, Bottom = 0}) end)
        local t = new("TextBlock", w.WidgetTree, name .. "L")
        style_text(t, math.floor(d * 0.46), rgba(1, 1, 1), 2)
        pcall(function() t:SetJustification(1) end)
        t:SetText(FText(letter))
        local os3 = ov:AddChildToOverlay(t)
        pcall(function() os3:SetHorizontalAlignment(2) end); pcall(function() os3:SetVerticalAlignment(2) end)  -- centre
    end
    local s1 = vb:AddChildToVerticalBox(sb); pcall(function() s1:SetHorizontalAlignment(2) end)
    if needle then
        local ns = new("SizeBox", w.WidgetTree, name .. "NS")
        pcall(function() ns:SetWidthOverride(4) end); pcall(function() ns:SetHeightOverride(needle) end)
        local nb = new("Border", w.WidgetTree, name .. "N")
        round_brush(nb, rgba(0.72, 0.72, 0.76, 1), {0, 0, 2, 2}, rgba(0.25, 0.25, 0.28, 1))
        ns:SetContent(nb)
        local s2 = vb:AddChildToVerticalBox(ns); pcall(function() s2:SetHorizontalAlignment(2) end)
    end
    return w
end
local PIN_D, PIN_NEEDLE = 70, 54
local PIN_Z = 1500.0          -- the needle's tip 15 m above the rift, against the sky
rift_labels = function()
    if V and V.labels then                     -- drawn on the screen (solid), but only while nothing is in the way
        local pc = local_pc()
        for i, a in ipairs(V.labels) do
            pcall(function()
                local see = pc:LineOfSightTo(a, {X = 0, Y = 0, Z = 0}, false)
                local wc = V.pinwc and V.pinwc[i]
                if wc and wc.__seen ~= see then wc:SetVisibility(see, false); wc.__seen = see end
            end)
        end
        return
    end
    if not V or (V.labels_tries or 0) >= 3 then return end
    V.labels_tries = (V.labels_tries or 0) + 1
    local ok, err = pcall(function()
        local cls = StaticFindObject("/Script/Engine.TextRenderActor")
        local out = {}
        for i, r in ipairs(V.rifts) do
            local world = r.r:GetWorld()
            -- an invisible actor to hold the pin (a TextRenderActor with no text), its point high above the rift, so
            -- it shows against the sky. In the world (walls hide it), turned to the camera all the time.
            local a = world:SpawnActor(cls, {X = r.x, Y = r.y, Z = r.z + PIN_Z}, {Pitch = 0.0, Yaw = 0.0, Roll = 0.0})
            pcall(function() a.TextRender:SetText(FText("")) end)
            local c = SIDECOL[i]
            local wd = circle_widget("JWPin" .. i, PIN_D, rgba(c.R * 0.9, c.G * 0.9, c.B * 0.9, 1), SIDE[i], PIN_NEEDLE)
            local wc = widget_comp(a, 0, wd, {X = PIN_D + 8, Y = PIN_D + PIN_NEEDLE + 8}, {X = 0.5, Y = 1.0})
            V.pinwc = V.pinwc or {}; V.pinwc[#V.pinwc + 1] = wc
            table.insert(out, a)
        end
        V.labels = out
    end)
    log("rift pins: " .. (ok and "ok" or tostring(err)))
end

-- a small dot in the side's colour over every enemy (off; a file JW_DOTS switches it on)
local DOTS = false
do local f = io.open(BIN .. "JW_DOTS", "r"); if f then f:close(); DOTS = true end end
local function team_dots()
    if not V or not DOTS or (V.dots_fail or 0) >= 3 then return end
    V.dotted = V.dotted or {}
    for _, p in ipairs(FindAllOf("RSTAICharacter") or {}) do
        pcall(function()
            if not p:IsValid() then return end
            local key = p:GetAddress()
            if V.dotted[key] then return end
            local n = name_of(p)
            if n:find("Sentinel", 1, true) or n:find("Default__", 1, true) then V.dotted[key] = true; return end
            local l = p:K2_GetActorLocation()
            local sd = (l.X < V.mid) and 1 or 2
            V.dotted[key] = true
            local c = SIDECOL[sd]
            local hh = 100
            pcall(function() hh = p.CapsuleComponent:GetScaledCapsuleHalfHeight() end)
            local ok, e = pcall(function()
                V.dotn = (V.dotn or 0) + 1
                local wd = circle_widget("JWDot" .. V.dotn, 14, rgba(c.R, c.G, c.B, 1))
                widget_comp(p, hh + 45, wd, {X = 18, Y = 18}, {X = 0.5, Y = 0.5})
            end)
            if not ok then V.dots_fail = (V.dots_fail or 0) + 1; log("team dot failed: " .. tostring(e)) end
        end)
    end
end

-- what an enemy is made of (meshes, materials and their colour settings), once per enemy class, to JW_Looks.txt:
-- for team colours on the orcs' own clothes
local LOOKF = BIN .. "JW_Looks.txt"
local looked = {}
local function look_probe()
    if not V or tick % 6 ~= 3 then return end
    for _, p in ipairs(FindAllOf("RSTAICharacter") or {}) do
        pcall(function()
            if not p:IsValid() then return end
            local cls = name_of(p:GetClass())
            if looked[cls] or cls:find("Sentinel", 1, true) then return end
            looked[cls] = true
            local f = io.open(LOOKF, "a"); if not f then return end
            local function w(s0) f:write(s0 .. "\n") end
            w("=== " .. os.date("%H:%M:%S") .. " " .. cls)
            local function mats(comp, ind)
                local n = 0; pcall(function() n = comp:GetNumMaterials() end)
                for i = 0, n - 1 do
                    local m; pcall(function() m = comp:GetMaterial(i) end)
                    local depth = 0
                    while m and m:IsValid() and depth < 4 do
                        w(ind .. "  mat " .. i .. (depth > 0 and (" parent" .. depth) or "") .. ": " .. name_of(m))
                        pcall(function()
                            m.VectorParameterValues:ForEach(function(_, e)
                                local v = e:get()
                                local pv = v.ParameterValue
                                w(string.format("%s      vector %s = %.2f %.2f %.2f %.2f", ind, v.ParameterInfo.Name:ToString(), pv.R, pv.G, pv.B, pv.A))
                            end)
                        end)
                        pcall(function()
                            m.ScalarParameterValues:ForEach(function(_, e)
                                local v = e:get()
                                w(string.format("%s      scalar %s = %.2f", ind, v.ParameterInfo.Name:ToString(), v.ParameterValue))
                            end)
                        end)
                        pcall(function()
                            m.TextureParameterValues:ForEach(function(_, e)
                                local v = e:get()
                                w(string.format("%s      texture %s = %s", ind, v.ParameterInfo.Name:ToString(), name_of(v.ParameterValue)))
                            end)
                        end)
                        local par; pcall(function() par = m.Parent end)
                        m = par; depth = depth + 1
                    end
                end
            end
            local function walk(comp, ind, depth)
                if not comp or not comp:IsValid() or depth > 4 then return end
                local cn = name_of(comp)
                local mesh = ""
                pcall(function() mesh = " mesh=" .. name_of(comp.SkeletalMesh or comp.SkinnedAsset) end)
                pcall(function() if mesh == "" then mesh = " mesh=" .. name_of(comp.StaticMesh) end end)
                w(ind .. cn:match("[^%.:]+$") .. "  (" .. (cn:match("^%S+") or "?") .. ")" .. mesh)
                if cn:find("MeshComponent") then mats(comp, ind) end
                local k = 0; pcall(function() k = comp:GetNumChildrenComponents() end)
                for i = 0, k - 1 do
                    local ch; pcall(function() ch = comp:GetChildComponent(i) end)
                    walk(ch, ind .. "  ", depth + 1)
                end
            end
            walk(p.RootComponent, "", 0)
            f:close()
            log("look probe: " .. cls)
        end)
    end
end

-- ---------- team banners along the routes (positions from the map builder: Mods/JWVersus/banners.txt) ----------
-- The game's large banner with the arena flag material, its colour (BC_ColorTint) set to the side's colour. Spawned
-- on every PC for itself, no collision (traps go over them).
local BANNERS = BIN .. "Mods/JWVersus/banners.txt"
local BANNER_MESHES = {"Banner_Coastal_OrderCrest_Small_SM", "BannerLargeA"}   -- side A (blue), side B (red)
local BANNER_MAT = "/Game/Environments/Props_Order/General_Decor/Banner_Order/Mat/ArenaFlags_INST.ArenaFlags_INST"
local function load_obj(path)
    local o = StaticFindObject(path)
    if not (o and o:IsValid()) then pcall(function() LoadAsset(path:match("^[^%.]+")) end); o = StaticFindObject(path) end
    if o and o:IsValid() then return o end
end
local function team_banners()
    if not V or V.banners_done or not V.rifts or not V.rifts[1] then return end
    V.banners_done = true
    local list = {}
    local f = io.open(BANNERS, "r")
    if f then
        for line in f:lines() do
            local lv, sd, x, y, z, nx, ny = line:match("^(%S+)%s+(%d)%s+(%S+)%s+(%S+)%s+(%S+)%s+(%S+)%s+(%S+)")
            if lv == V.level then list[#list + 1] = {sd = tonumber(sd) + 1, x = tonumber(x), y = tonumber(y), z = tonumber(z), nx = tonumber(nx), ny = tonumber(ny)} end
        end
        f:close()
    end
    -- the banners the map builder put in the level (one StaticMeshActor each, mesh BannerLargeA)
    local found = {}
    for _, c in ipairs(FindAllOf("StaticMeshComponent") or {}) do
        pcall(function()
            if not c:IsValid() then return end
            local mn = name_of(c.StaticMesh)
            for _, m in ipairs(BANNER_MESHES) do if mn:find(m, 1, true) then found[#found + 1] = c end end
        end)
    end
    log(string.format("team banners: %d in the level, %d in banners.txt", #found, #list))
    if #found == 0 then return end
    local ok, err = pcall(function()
        for _, c in ipairs(found) do
            pcall(function()
                local bb = c.StaticMesh:GetBoundingBox()
                local mn, mx = bb.Min, bb.Max
                local thinY = (mx.Y - mn.Y) <= (mx.X - mn.X)               -- the cloth's thin side faces the room
                local height = mx.Z - mn.Z
                local wide = thinY and (mx.X - mn.X) or (mx.Y - mn.Y)
                local sc = math.min(1.3, 420.0 / math.max(height, 1), 260.0 / math.max(wide, 1))
                local back = thinY and mn.Y or mn.X                           -- the side that goes against the wall
                local cmid = thinY and (mn.X + mx.X) / 2 or (mn.Y + mx.Y) / 2 -- the cloth's middle across
                local a = c:GetOwner()
                local l = a:K2_GetActorLocation()
                local q, bd = nil, 1e12                                       -- its entry: the nearest one
                for _, e in ipairs(list) do
                    local d = (e.x - l.X) ^ 2 + (e.y - l.Y) ^ 2
                    if d < bd then q, bd = e, d end
                end
                local sd = q and q.sd or ((l.X < V.mid) and 1 or 2)
                pcall(function() c:SetMobility(2) end)
                pcall(function() c:SetCollisionEnabled(0) end)
                if q then
                    local yaw = math.deg(math.atan(q.ny, q.nx)) - (thinY and 90 or 0)
                    local off = (-back) * sc + 22                            -- the back of the cloth 22 cm off the wall (the stones bulge, the cloth sways)
                    -- across the wall the cloth's middle on the entry (the local across axis, turned by yaw)
                    local r = math.rad(yaw)
                    local ax, ay = math.cos(r), math.sin(r)                  -- local +X in the world
                    if not thinY then ax, ay = -math.sin(r), math.cos(r) end -- (then the across axis is local +Y)
                    local loc = {X = q.x + q.nx * off - ax * cmid * sc, Y = q.y + q.ny * off - ay * cmid * sc,
                                 Z = q.z + 560.0 - mx.Z * sc}               -- the top 5.6 m above the floor
                    a:K2_TeleportTo(loc, {Pitch = 0.0, Yaw = yaw, Roll = 0.0})
                    pcall(function() a:SetActorScale3D({X = sc, Y = sc, Z = sc}) end)
                end
                if not V.bannerlog then V.bannerlog = true; log(string.format("banner %s bounds %.0f %.0f %.0f .. %.0f %.0f %.0f scale %.2f", name_of(c.StaticMesh), mn.X, mn.Y, mn.Z, mx.X, mx.Y, mx.Z, sc)) end
            end)
        end
    end)
    if not ok then log("team banners failed: " .. tostring(err)) end
end

-- the middle between the sides kills (rule): any enemy or hero inside the middle strip dies at once, as if it
-- fell out of the world (heroes come back like after a fall). Host only.
local function middle_kill()
    if not V or not V.midkill or not V.started or (V.midhalf or 0) <= 0 or not is_host() then return end
    for _, cls in ipairs({"RSTAICharacter", "RSTPlayerCharacter"}) do
        for _, p in ipairs(FindAllOf(cls) or {}) do
            pcall(function()
                if not p:IsValid() then return end
                local n = name_of(p)
                if n:find("Default__", 1, true) or n:find("Sentinel", 1, true) then return end
                local l = p:K2_GetActorLocation()
                if math.abs(l.X - V.mid) > V.midhalf then return end
                if V.bridge1 > V.bridge0 and l.Y > V.bridge0 and l.Y < V.bridge1 and l.Z > (V.killz or -400) then return end   -- on the bridge
                local hc = p.HealthComponent
                if hc:IsDeadOrDying() then return end
                hc:DamageSelfDestruct(true, nil)
                V.midkills = (V.midkills or 0) + 1
                if V.midkills <= 5 then log("middle kill: " .. n:match("[^%.]+$")) end
            end)
        end
    end
end

-- death pits and the ravine: anyone who falls below the map's lowest floor (V.killz) dies at once
local function pit_kill()
    if not V or not V.started or (V.pits or 0) <= 0 or not is_host() or tick % 2 ~= 0 then return end
    for _, cls in ipairs({"RSTAICharacter", "RSTPlayerCharacter"}) do
        for _, p in ipairs(FindAllOf(cls) or {}) do
            pcall(function()
                if not p:IsValid() then return end
                local n = name_of(p)
                if n:find("Default__", 1, true) then return end
                local l = p:K2_GetActorLocation()
                if l.Z > V.killz then return end
                local hc = p.HealthComponent
                if hc:IsDeadOrDying() then return end
                hc:DamageSelfDestruct(true, nil)
                V.pitkills = (V.pitkills or 0) + 1
                if V.pitkills <= 5 then log(string.format("pit kill: %s at z %.0f", n:match("[^%.]+$"), l.Z)) end
            end)
        end
    end
end

-- (diagnostics, once per match) what the minimap shows: its MapData objects and the HUD minimap's pictures
local function minimap_dump()
    if not V or V.mmdumped or not V.started or tick < 40 then return end
    V.mmdumped = true
    local function props(st, pre, depth)
        pcall(function()
            st:ForEachProperty(function(pr)
                local pn, pc = "?", "?"
                pcall(function() pn = pr:GetFName():ToString() end)
                pcall(function() pc = pr:GetClass():GetFName():ToString() end)
                log(string.format("  minimap prop %s%s : %s", pre, pn, pc))
                if depth < 3 then
                    pcall(function() props(pr:GetStruct(), pre .. pn .. ".", depth + 1) end)
                    pcall(function() props(pr:GetInner():GetStruct(), pre .. pn .. "[].", depth + 1) end)
                end
            end)
        end)
    end
    for i, md in ipairs(FindAllOf("RSTMapData") or {}) do
        log("minimap data: " .. name_of(md))
        if i == 1 then props(md:GetClass(), "", 0) end
    end
    local function walk(wd, depth)
        if not wd or depth > 14 then return end
        local cls, nm = "?", "?"
        pcall(function() cls = wd:GetClass():GetFName():ToString() end)
        pcall(function() nm = wd:GetFName():ToString() end)
        local vis = -1; pcall(function() vis = wd:GetVisibility() end)
        local info = ""
        pcall(function()
            local r = wd.Brush.ResourceObject
            if r and r:IsValid() then info = " res=" .. r:GetFullName() end
        end)
        log(string.format("  minimap %s%s %s vis=%d%s", string.rep(" ", depth), cls, nm, vis, info))
        local n = 0; pcall(function() n = wd:GetChildrenCount() end)
        for i = 0, n - 1 do local ch; pcall(function() ch = wd:GetChildAt(i) end); walk(ch, depth + 1) end
        if n == 0 then local ct; pcall(function() ct = wd:GetContent() end); if ct then walk(ct, depth + 1) end end
        if cls:find("^W_") then pcall(function() walk(wd.WidgetTree.RootWidget, depth + 1) end) end
    end
    pcall(function()
        local n = 0
        for _, t in ipairs(FindAllOf("Texture2D") or {}) do
            local nm = name_of(t)
            if nm:find("JW", 1, true) or nm:find("Whitebox", 1, true) or nm:find("/Minimaps/", 1, true) then
                n = n + 1; if n <= 20 then log("  minimap texture in memory: " .. nm) end
            end
        end
        log("  minimap textures found: " .. n)
    end)
    -- the volume's numbers and whether our picture is loaded
    pcall(function()
        for _, md in ipairs(FindAllOf("RSTMapData") or {}) do
            local vols = md.MapVolumes
            local n = 0; pcall(function() n = #vols end)
            for i = 1, n do
                local v = vols[i]
                local t, e = v.Transform, v.Extent
                log(string.format("  minimap volume %d: rot %.3f %.3f %.3f %.3f pos %.0f %.0f %.0f scale %.3f %.3f %.3f extent %.0f %.0f %.0f", i,
                    t.Rotation.X, t.Rotation.Y, t.Rotation.Z, t.Rotation.W, t.Translation.X, t.Translation.Y, t.Translation.Z,
                    t.Scale3D.X, t.Scale3D.Y, t.Scale3D.Z, e.X, e.Y, e.Z))
                pcall(function() log("  minimap texture: " .. tostring(v.MapTexture:ToString())) end)
                pcall(function() local o = v.MapTexture:Get(); log("  minimap texture loaded: " .. (o and o:IsValid() and o:GetFullName() or "no")) end)
            end
        end
    end)
    for _, cn in ipairs({"RSTMapWidget"}) do
        for _, mw in ipairs(FindAllOf(cn) or {}) do
            local n = name_of(mw)
            if not n:find("Default__", 1, true) then
                log("minimap map widget " .. n)
                pcall(function()
                    mw:GetClass():ForEachProperty(function(pr)
                        local pn = pr:GetFName():ToString()
                        local val = "?"
                        pcall(function()
                            local v = mw[pn]
                            if type(v) == "number" or type(v) == "boolean" then val = tostring(v)
                            elseif type(v) == "userdata" then
                                local ok, fn = pcall(function() return v:GetFullName() end)
                                if ok and fn then val = fn else
                                    local ok2, xy = pcall(function() return string.format("(%.1f, %.1f)", v.X, v.Y) end)
                                    val = ok2 and xy or "struct" end
                            end
                        end)
                        log("  map widget prop " .. pn .. " = " .. val)
                    end)
                end)
            end
        end
    end
    for _, w in ipairs(FindAllOf("W_HUD_Minimap_C") or {}) do
        local n = name_of(w)
        if not n:find("Default__", 1, true) then log("minimap widget " .. n); pcall(function() walk(w.WidgetTree.RootWidget, 1) end) end
    end
end

-- fog in the death pits / ravine: the level's height fog gets a second, thick layer low down that thins out fast
-- above, so the pit bottoms are hazy and the map itself stays clear
local function pit_fog()
    if not V or V.fogdone or not V.started or (V.pits or 0) <= 0 then return end
    V.fogdone = true
    local done = 0
    for _, f in ipairs(FindAllOf("ExponentialHeightFogComponent") or {}) do
        pcall(function()
            local n = name_of(f)
            if n:find("Default__", 1, true) then return end
            local z = f:K2_GetComponentLocation().Z
            log(string.format("fog %s at z %.0f: density %.4f falloff %.4f, 2nd %.4f %.4f %.0f", n:match("[^%.]+$"), z,
                f.FogDensity, f.FogHeightFalloff, f.SecondFogData.FogDensity, f.SecondFogData.FogHeightFalloff, f.SecondFogData.FogHeightOffset))
            pcall(function() log(string.format("  fog start %.0f, max opacity %.2f, cutoff %.0f", f.StartDistance, f.FogMaxOpacity, f.FogCutoffDistance)) end)
            f.StartDistance = 0                  -- the fog started far away, so only the far edges looked foggy
            f.SecondFogData.FogDensity = FOG_DENSITY
            f.SecondFogData.FogHeightFalloff = FOG_FALLOFF
            f.SecondFogData.FogHeightOffset = (V.killz or -400) - 600 - z
            pcall(function() f:MarkRenderStateDirty() end)
            pcall(function() f:SetFogDensity(f.FogDensity) end)
            done = done + 1
        end)
    end
    log("pit fog: " .. done .. " fog component(s) changed")
end

-- a fog floor in the pits: the builder lays thin flat blocks 9 m down (only there). They take a cloud material that is
-- already in memory (the game has no real fog plane loaded on our maps); F9 tries the next one (the last choice is
-- "hidden"). They never collide.
local function fog_apply()
    local F = V.fog
    local mat = F.cands[F.idx]
    for _, c in ipairs(F.pieces) do
        pcall(function()
            if mat then c:SetMaterial(0, mat); c:SetVisibility(true, false) else c:SetVisibility(false, false) end
        end)
    end
    local nm = mat and (name_of(mat):match("([^%.]+)$") or "?") or "hidden"
    log(string.format("fog floor: %d pieces, %d/%d %s", #F.pieces, F.idx, #F.cands, nm))
    return nm
end
local function fog_floor()
    if not V or not V.started or (V.pits or 0) <= 0 then return end
    if V.fog then
        if V.fogcycle then
            V.fogcycle = false
            V.fog.idx = V.fog.idx % (#V.fog.cands + 1) + 1
            local nm = fog_apply()
            if JW_SAY then JW_SAY("Pit fog " .. V.fog.idx .. ": " .. nm .. "  (Ctrl+F9: next)") end
        end
        return
    end
    local cands = {}
    for _, m in ipairs(FindAllOf("MaterialInstanceConstant") or {}) do
        local n = name_of(m)
        if (n:find("Fog", 1, true) or n:find("Mist", 1, true) or n:find("Cloud", 1, true) or n:find("Haze", 1, true))
           and not n:find("Default__", 1, true) and not n:find("Volumetric", 1, true) then
            local pri = n:find("FogPlane", 1, true) and 0 or n:find("StormCloud", 1, true) and 1 or n:find("PoisonGas", 1, true) and 2 or 5
            cands[#cands + 1] = {m = m, p = pri, n = n}
        end
    end
    table.sort(cands, function(a, b) if a.p ~= b.p then return a.p < b.p end return a.n < b.n end)
    for i, c in ipairs(cands) do if i <= 20 then log("fog material " .. i .. ": " .. c.n) end; cands[i] = c.m end
    local pieces = {}
    for _, c in ipairs(FindAllOf("StaticMeshComponent") or {}) do
        pcall(function()
            local sm = c.StaticMesh
            if not (sm and sm:IsValid() and sm:GetFName():ToString() == "Column_Square_1_1_Stone_House_SM") then return end
            if c.RelativeScale3D.Z > 0.01 then return end
            pcall(function() c:SetCollisionEnabled(0) end)
            pieces[#pieces + 1] = c
        end)
    end
    V.fog = {cands = cands, pieces = pieces, idx = (#cands > 0) and 1 or 1}
    fog_apply()
end
-- (F9 used to cycle the pit fog test; it is the PvP test key now)

-- player dots on the minimap: our own small markers laid over the game's map (the game drew none on our maps).
-- The map widget gets an overlay with a canvas over it; a dot sits at the player's place in the map's volume.
local mm = nil
local function minimap_dots()
    if not V or not V.started then return end
    if not (mm and mm.canvas and valid(mm.canvas)) then
        if (V.mmfail or 0) >= 3 then return end
        local ok, err = pcall(function()
            local vol = nil
            for _, md in ipairs(FindAllOf("RSTMapData") or {}) do
                local v = md.MapVolumes[1]
                local t, e = v.Transform, v.Extent
                local yaw = 2 * math.atan(t.Rotation.Z, t.Rotation.W)
                vol = {cx = t.Translation.X, cy = t.Translation.Y, c = math.cos(yaw), s = math.sin(yaw), ex = e.X, ey = e.Y}
            end
            if not vol then error("no map volume") end
            local mw = nil
            for _, w in ipairs(FindAllOf("W_MapWidget_C") or {}) do
                local n = name_of(w)
                if n:find("W_HUD_Minimap", 1, true) and not n:find("Default__", 1, true) then mw = w end
            end
            if not mw then error("no HUD minimap") end
            local sb = mw:GetParent()                      -- SizeBox_0: give it an overlay with the map + our canvas
            local gi = FindFirstOf("GameInstance")
            local ov = StaticConstructObject(StaticFindObject("/Script/UMG.Overlay"), sb:GetOuter(), FName("JWMiniOv"))
            sb:SetContent(ov)
            local s1 = ov:AddChildToOverlay(mw)
            pcall(function() s1:SetHorizontalAlignment(0) end); pcall(function() s1:SetVerticalAlignment(0) end)
            local cv = StaticConstructObject(StaticFindObject("/Script/UMG.CanvasPanel"), sb:GetOuter(), FName("JWMiniCanvas"))
            local s2 = ov:AddChildToOverlay(cv)
            pcall(function() s2:SetHorizontalAlignment(0) end); pcall(function() s2:SetVerticalAlignment(0) end)
            pcall(function() cv:SetVisibility(4) end)
            mm = {canvas = cv, vol = vol, dots = {}, outer = sb:GetOuter()}
            log(string.format("minimap dots: on (volume centre %.0f %.0f, half %.0f x %.0f)", vol.cx, vol.cy, vol.ex, vol.ey))
        end)
        if not ok then V.mmfail = (V.mmfail or 0) + 1; log("minimap dots failed: " .. tostring(err)); return end
    end
    local me = nil; pcall(function() me = local_pc().Pawn end)
    local seen = {}
    for _, p in ipairs(FindAllOf("RSTPlayerCharacter") or {}) do
        pcall(function()
            local n = name_of(p)
            if n:find("Default__", 1, true) or not p:IsValid() then return end
            local key = p:GetAddress(); seen[key] = true
            local d = mm.dots[key]
            if not (d and valid(d.b)) then
                local mine = me and me:GetAddress() == key
                local sz = mine and 15 or 11
                local b = StaticConstructObject(StaticFindObject("/Script/UMG.Border"), mm.outer, FName("JWMiniDot" .. tostring(key)))
                local l = p:K2_GetActorLocation()
                local side = (V.mid and l.X > V.mid) and 2 or 1
                if mine then side = my_side() or side end           -- my own dot: my team's colour, with a gold rim
                local col = rgba(SIDECOL[side].R, SIDECOL[side].G, SIDECOL[side].B, 1)
                round_brush(b, col, sz / 2, mine and GOLD or rgba(0, 0, 0, 0.8))
                local cs = mm.canvas:AddChildToCanvas(b)
                pcall(function() cs:SetSize({X = sz, Y = sz}) end)
                pcall(function() cs:SetAlignment({X = 0.5, Y = 0.5}) end)
                d = {b = b, slot = cs}; mm.dots[key] = d
            end
            local l = p:K2_GetActorLocation()
            local v = mm.vol
            local dx, dy = l.X - v.cx, l.Y - v.cy
            local lx, ly = dx * v.c + dy * v.s, -dx * v.s + dy * v.c
            local u, w = (lx / v.ex + 1) / 2, (ly / v.ey + 1) / 2
            u = math.max(0, math.min(1, u)); w = math.max(0, math.min(1, w))
            pcall(function() d.slot:SetAnchors({Minimum = {X = u, Y = w}, Maximum = {X = u, Y = w}}) end)
            pcall(function() d.slot:SetPosition({X = 0, Y = 0}) end)
        end)
    end
    for key, d in pairs(mm.dots) do
        if not seen[key] then pcall(function() d.b:RemoveFromParent() end); mm.dots[key] = nil end
    end
end

-- ===== PvP test (host, Ctrl+F9 cycles) =====
-- 0 off; 1 the game's own friendly fire (its cheat ToggleFriendlyFire); 2 side B's heroes on team 3 (the game's
-- "player-damageable traps" team); 3 side B's heroes on team 2 (the enemies' team). Every hero hit is logged.
local PVP_NAMES = {[0] = "off", "the game's friendly fire", "side B heroes on team 3", "side B heroes on team 2 (enemy team)",
    "side B heroes on team 1 (NPC team)", "side B heroes on team 3, their controllers on team 0 (traps stay on team 0?)"}
local PVP_N = 6
local pvp = {mode = 0, want = 0, ff = false}
local function heroes()
    local out = {}
    for _, p in ipairs(FindAllOf("RSTPlayerCharacter") or {}) do
        if p:IsValid() and not name_of(p):find("Default__", 1, true) then out[#out + 1] = p end
    end
    return out
end
local function set_team(p, id)
    pcall(function() if p.MyTeamID.TeamID ~= id then p.MyTeamID = {TeamID = id} end end)
end
local function friendly_fire(on)
    if pvp.ff == on then return end
    local ok, err = pcall(function()
        local pc = local_pc()
        local cm = pc.CheatManager
        if not (cm and cm:IsValid()) then
            cm = StaticConstructObject(StaticFindObject("/Script/OMD4.RSTCheatManager"), pc, FName("JWCheatManager"))
            pc.CheatManager = cm
        end
        cm:ToggleFriendlyFire()
    end)
    pvp.ff = on
    log("pvp: ToggleFriendlyFire " .. (ok and "called" or ("failed: " .. tostring(err))))
end
local function pvp_tick()
    if not V or not V.started or not is_host() then return end
    if not V.pvp_set then
        -- the map's PvP rule (Map Maker): heroes on side B join team 3 for the whole match, so heroes can shoot each
        -- other (traps may hit the other side's hero, but do no damage); without the rule PvP starts off
        V.pvp_set = true
        pvp.want = V.pvp_rule and 2 or 0
        if V.pvp_rule then log("PvP on (map rule): heroes can hit each other") end
    end
    if pvp.want ~= pvp.mode then
        pvp.mode = pvp.want
        friendly_fire(pvp.mode == 1)
        if pvp.mode < 2 then for _, p in ipairs(heroes()) do set_team(p, 0) end end
        local msg = (V.pvp_rule and pvp.mode == 2) and "PvP ON: heroes can hit each other"
            or ("PvP test " .. pvp.mode .. ": " .. PVP_NAMES[pvp.mode] .. "  (Ctrl+F9: next)")
        if JW_SAY then JW_SAY(msg) else log(msg) end
    end
    if pvp.mode >= 2 then
        -- 2: team 3, 3: team 2, 4: team 1, 5: team 3 with the hero's controller kept on team 0 (a trap takes its owner's
        -- team: on team 3 side B's traps aimed at every hero; test 5 tries to keep the traps on the players' team)
        local tb = ({[2] = 3, [3] = 2, [4] = 1, [5] = 3})[pvp.mode]
        if tick % 20 == 0 then                       -- every 10 s: which team each side's traps are on (their GetTeam)
            local cnt = {{}, {}}
            for _, t in ipairs(JW_TRAPS and JW_TRAPS() or {}) do
                pcall(function()
                    if name_of(t):find("Default__", 1, true) then return end
                    local l = t:K2_GetActorLocation(); local sd = (V.mid and l.X > V.mid) and 2 or 1
                    local tm = tostring(t:GetTeam()); cnt[sd][tm] = (cnt[sd][tm] or 0) + 1
                end)
            end
            local function f(c) local o = {} for k, v in pairs(c) do o[#o + 1] = "team " .. k .. " x" .. v end return #o > 0 and table.concat(o, ", ") or "none" end
            log(string.format("pvp %d: traps side A: %s | side B: %s", pvp.mode, f(cnt[1]), f(cnt[2])))
        end
        for _, p in ipairs(heroes()) do
            local l = p:K2_GetActorLocation()
            set_team(p, (V.mid and l.X > V.mid) and tb or 0)
            if pvp.mode == 5 then
                pcall(function()
                    local c = p:GetController()
                    if c and c:IsValid() and c.MyTeamID.TeamID ~= 0 then c.MyTeamID = {TeamID = 0} end
                end)
            end
        end
    end
end
pcall(function() RegisterKeyBind(Key.F9, {ModifierKey.CONTROL}, function() pvp.want = (pvp.want + 1) % PVP_N; JW_PVPKEY = os.clock() end) end)   -- Ctrl+F9 (F10 opened the console, F9 sends a rift)
-- (a hook on RSTCharacter:OnDamageTaken crashed the game at start: removed; hero hits are not logged)

local function hide_game_rift_counter()
    if tick % 4 ~= 0 then return end
    for _, wd in ipairs(FindAllOf("UserWidget") or {}) do
        pcall(function()
            local n = name_of(wd)
            if not n:find("RiftPoints") then return end
            if not V.riftseen then V.riftseen = {} end
            if not V.riftseen[n] then V.riftseen[n] = true; log("game rift counter widget: " .. n) end
            if wd:GetVisibility() ~= 1 then wd:SetVisibility(1) end              -- Collapsed
        end)
    end
end

local function say(text) if V then V.msg = {text = text, t = tick}; log(text); show() end end
JW_SAY = say
-- a line in the game's message feed (bottom left, where "Unstable Rift Opening" shows). The game posts those with
-- RSTPlayerCommunicationSubsystem:AddSystemCommunication(definition); we borrow the unstable rift's definition for a
-- moment: our text as its chat text, no ping, no map ping, no sound or voice line, then put it back.
-- (Tried before: Client_AddPlayerChatMessage on each player state and the host's Server_AddPlayerChatMessage: the
-- calls went through but nothing showed.)
local COMM_DEF = "/Game/UI/Data/CommunicationOptions/System/DA_Communication_Spawn_UnstableRift.DA_Communication_Spawn_UnstableRift"
local CHAT_FEED = false     -- the feed call crashed the game when a send was made (v124): off until made safe
function JW_CHAT(text, sender)
    if not V then return end
    if not CHAT_FEED then return end
    local def = StaticFindObject(COMM_DEF)
    if not (def and def:IsValid()) and LoadAsset then pcall(function() LoadAsset(COMM_DEF) end); def = StaticFindObject(COMM_DEF) end
    local sub = FindFirstOf("RSTPlayerCommunicationSubsystem")
    if not (def and def:IsValid()) or not (sub and sub:IsValid()) then
        if not V.chat_logged then V.chat_logged = true; log("chat: no " .. (def and def:IsValid() and "communication subsystem" or "communication definition")) end
        return
    end
    local keep = {}
    local fields = {"bCreatesPing", "bCreateWorldPing", "bCreateMinimapPing", "bMinimapDopplerPing", "bAttachCue", "bRequiresAttachedActorForText"}
    pcall(function() keep.text = def.ChatText:ToString() end)
    for _, f in ipairs(fields) do pcall(function() keep[f] = def[f] end) end
    pcall(function() keep.cue = def.GameplayCueTag.TagName end)
    pcall(function() keep.dlg = def.DialogueIdentifier.TagName end)
    local ok, err = pcall(function()
        def.ChatText = FText(text)
        for _, f in ipairs(fields) do def[f] = false end
        pcall(function() def.GameplayCueTag = {TagName = FName("None")} end)
        pcall(function() def.DialogueIdentifier = {TagName = FName("None")} end)
        local pawn; pcall(function() pawn = local_pc().Pawn end)
        local l = pawn and loc(pawn) or {X = 0, Y = 0, Z = 0}
        sub:AddSystemCommunication(def, pawn, {X = l.X, Y = l.Y, Z = l.Z}, {})
    end)
    local function restore()
        pcall(function() if keep.text then def.ChatText = FText(keep.text) end end)
        for _, f in ipairs(fields) do pcall(function() if keep[f] ~= nil then def[f] = keep[f] end end) end
        pcall(function() if keep.cue then def.GameplayCueTag = {TagName = keep.cue} end end)
        pcall(function() if keep.dlg then def.DialogueIdentifier = {TagName = keep.dlg} end end)
    end
    if not pcall(ExecuteWithDelay, 3000, function() pcall(restore) end) then restore() end
    if not V.chat_logged or not ok then V.chat_logged = true; log("chat" .. (ok and "" or (" failed: " .. tostring(err))) .. ": " .. text) end
end
local function send_def(g)
    if g.def and valid(g.def) then return g.def end
    local short = g.pde:match("[^/]+$")
    local path = "/Game/Characters/Minions/" .. g.pde .. "." .. short
    local d = StaticFindObject(path)
    if not valid(d) and LoadAsset then pcall(function() LoadAsset(path) end); d = StaticFindObject(path) end
    if valid(d) then g.def = d; return d end
    return nil
end
local function do_send(k, sender)
    if not V or not V.started or V.winner or not is_host() then return end
    local g = SEND[k]
    if not g then return end
    if V.send_on == false then say("sending enemies is off on this map"); return end
    local pl = V.econ or econ_players()
    local me
    if sender then                       -- a request from another player (chat message, see below)
        local sa = sender:GetAddress()
        for _, e in ipairs(pl) do if e.ps:GetAddress() == sa then me = e end end
        if not me then log("send: request from a player who is not in the game"); return end
    else
        for _, e in ipairs(pl) do if e.host then me = e end end
        me = me or pl[1]
    end
    if not me then return end
    if #pl == 1 and V.mid then                 -- alone: the side is where the player stands now
        local l = loc(me.pc and me.pc.Pawn)
        if l then me.side = (l.X < V.mid) and 1 or 2 end
    end
    local from = me.side or 1
    local to = 3 - from
    local def
    if g.curse then
        local c = V.curse and V.curse[to]
        if c and tick < c.till then say(string.format("SIDE %s is already cursed (%s, %d s left)", SIDE[to], c.name, (c.till - tick) // 2)); return end
    else
        def = send_def(g)
        if not def then say("cannot send " .. g.name .. ": enemy type not found"); return end
    end
    local price, pkey = send_price(k, me.ps)
    local ok, have = pcall(function() return me.ps.Coin end)
    if not ok or have < price then say(string.format("SIDE %s: not enough coins for %s (%d needed)", SIDE[from], g.name, price)); return end
    local okp = pcall(function() me.ps:SpendCoin(price, 1) end)            -- NormalSpend
    if not okp then say("paying failed"); return end
    V.sends = V.sends or {}; V.sends[pkey] = V.sends[pkey] or {}; V.sends[pkey][k] = (V.sends[pkey][k] or 0) + 1
    if g.curse then JW_CURSE(from, to, price, nil, me.ps); return end
    for _ = 1, g.n do table.insert(V.sendq, {def = def, side = to}) end
    V.sentn = V.sentn or {0, 0}; V.sentn[from] = V.sentn[from] + g.n
    say(string.format("SIDE %s SENT %s TO SIDE %s", SIDE[from], g.name:upper(), SIDE[to]))
    log(string.format("  (%d coins, next %d)", price, (send_price(k, me.ps))))
    if not g.curse then pcall(JW_CHAT, string.format("[SIDE %s] sent %s to SIDE %s", SIDE[from], g.name, SIDE[to]), me.ps) end
end
-- ---------- curses: the 6th send puts a random curse on the other side ----------
-- "wave" curses last until the mission's next wave begins (at least 60 s, at most 3 min); the others a fixed time.
-- Effects on enemies and heroes are set on each actor of the cursed side (found every second while it lasts).
local CURSES = {
    {id = "steal",   name = "COINS STOLEN",  secs = 60,  text = "every coin side %s earns for 1 min goes to side %s"},
    {id = "traps",   name = "TRAPS OFF",     secs = 60,  text = "side %s's traps stop working for 1 min (sent by side %s)"},
    {id = "double",  name = "DOUBLE LIFE",   wave = true, text = "orcs on side %s have double life this wave (sent by side %s)"},
    {id = "nomoney", name = "NO MONEY",      wave = true, text = "side %s earns no coins this wave (sent by side %s)"},
    -- haste is out until a way is found: NavPower moves the orcs at its own speed (speed fraction, walk speed, the
    -- speed attribute, time dilation and the Orc Drummer's buff effect all left it at 423, tested 2026-11-14)
    -- {id = "haste", name = "HASTE", wave = true, text = "orcs on side %s run 50 %% faster this wave (sent by side %s)"},
    {id = "fragile", name = "FRAGILE RIFT",  wave = true, text = "every orc in side %s's rift costs double this wave (sent by side %s)"},
    {id = "tax",     name = "TAX",           secs = 120, text = "side %s's sends cost double for 2 min (sent by side %s)"},
    {id = "armour",  name = "ARMOURED",      wave = true, text = "orcs on side %s get a shield as big as their life this wave (sent by side %s)"},
    {id = "boots",   name = "HEAVY BOOTS",   secs = 60,  text = "side %s's heroes move 40 %% slower for 1 min (sent by side %s)"},
}
-- an actor's health, shield and speed, read back for the log
function JW_STATS(p)
    local o = {}
    pcall(function() local hc = p.HealthComponent; o[#o + 1] = string.format("health %.0f/%.0f shield %.0f/%.0f", hc:GetHealth(), hc:GetMaxHealth(), hc:GetShield(), hc:GetMaxShield()) end)
    pcall(function() local hs = p.HealthComponent.HealthSet; o[#o + 1] = string.format("(set: shield base %.0f cur %.0f, max shield base %.0f cur %.0f)", hs.Shield.BaseValue, hs.Shield.CurrentValue, hs.MaxShield.BaseValue, hs.MaxShield.CurrentValue) end)
    pcall(function() o[#o + 1] = string.format("walk %.0f", p.CharacterMovement.MaxWalkSpeed) end)
    pcall(function() local c = p:GetController(); o[#o + 1] = string.format("mover speed %.0f", c:GetMoverSpeed()) end)
    pcall(function() local v = p:GetVelocity(); o[#o + 1] = string.format("velocity %.0f", math.sqrt(v.X * v.X + v.Y * v.Y)) end)
    pcall(function() o[#o + 1] = string.format("time %.2f", p.CustomTimeDilation) end)
    return table.concat(o, " ")
end
local BPLIB = nil
local function bplib()
    if not (BPLIB and valid(BPLIB)) then BPLIB = StaticFindObject("/Script/OMD4.Default__RSTBlueprintLibrary") end
    return BPLIB
end
-- an attribute (FGameplayAttributeData: BaseValue, CurrentValue) times f
local function attr_mul(set, name, f)
    local a = set[name]
    local b, c = a.BaseValue, a.CurrentValue
    set[name] = {BaseValue = b * f, CurrentValue = c * f}
    return c
end
local function move_set(p)
    local found
    pcall(function()
        local asc = p.HealthComponent.AbilitySystemComponent
        local arr = asc.SpawnedAttributes
        for i = 1, #arr do
            local a = arr[i]
            if a and a:IsValid() and name_of(a):find("MovementAttributeSet") then found = a end
        end
    end)
    return found
end
-- speed x f: the movement attribute set when found, and the character movement's walk speed; enemies are moved by
-- NavPower (their AI controller's mover keeps its own speed: walk speed alone did nothing), so for them the mover's
-- speed fraction too
local function speed_mul(p, f)
    local how = {}
    local okc, c = pcall(function() return p:GetController() end)
    if okc and c and c:IsValid() and not name_of(c):find("PlayerController") then
        V.npfrac = V.npfrac or {}
        local key = c:GetAddress()
        local fr = (V.npfrac[key] or 1.0) * f
        local ok, r = pcall(function() return c:SetMaxSpeedFraction(fr) end)
        if ok then V.npfrac[key] = fr; how[#how + 1] = "navpower fraction " .. string.format("%.2f", fr) .. " (" .. tostring(r) .. ")" end
    end
    local ms = move_set(p)
    if ms then if pcall(attr_mul, ms, "MovementSpeed", f) then how[#how + 1] = "attribute" end end
    local ok = pcall(function() local cm = p.CharacterMovement; cm.MaxWalkSpeed = cm.MaxWalkSpeed * f end)
    if ok then how[#how + 1] = "walk speed" end
    return table.concat(how, "+")
end
local HASTE_GE = {"/Game/Characters/Minions/Orcs/Orc_Drummer/Abilities/GE_Drummer_Buffs",
                  "/Game/Characters/Minions/Ogres/Ogre_Light/Abilities/GE_ChargeMovement_Ogre"}
local GECLS = {}
local function ge_class(path)
    if GECLS[path] and valid(GECLS[path]) then return GECLS[path] end
    local short = path:match("[^/]+$")
    local full = path .. "." .. short .. "_C"
    local c = StaticFindObject(full)
    if not valid(c) and LoadAsset then
        -- load the blueprint by its object path (package.asset), as the sends load enemy types, then find its class
        local okl, e = pcall(function() LoadAsset(path .. "." .. short) end)
        c = StaticFindObject(full)
        if not valid(c) then log("haste: " .. short .. " not loaded (" .. (okl and "LoadAsset ok, no class" or tostring(e)) .. ")") end
    end
    if valid(c) then GECLS[path] = c; return c end
end
-- apply the first gameplay effect of the list that is found to the actor (its ability system)
function apply_ge(p, list)
    local asc = p.HealthComponent.AbilitySystemComponent
    for _, path in ipairs(list) do
        local cls = ge_class(path)
        if cls then
            local ctx = asc:MakeEffectContext()
            asc:BP_ApplyGameplayEffectToSelf(cls, 1.0, ctx)
            return "effect " .. path:match("[^/]+$")
        end
    end
    return "no effect class found"
end
local function curse_enemy(p, c)
    local hs = p.HealthComponent.HealthSet
    if c.id == "double" then
        attr_mul(hs, "MaxHealth", 2); attr_mul(hs, "Health", 2)
    elseif c.id == "armour" then
        local mh = hs.MaxHealth.CurrentValue
        local sh = math.max(hs.MaxShield.CurrentValue, 0) + mh
        hs.MaxShield = {BaseValue = sh, CurrentValue = sh}; hs.Shield = {BaseValue = sh, CurrentValue = sh}
    elseif c.id == "haste" then
        -- tried: the mover's speed fraction (only slows down), walk speed and the speed attribute (the mover ignored
        -- both), time dilation (fast legs, same speed). Now the game's own buff: the Orc Drummer's effect, applied
        -- through the orc's ability system
        return apply_ge(p, HASTE_GE)
    end
    return "health set"
end
-- every placed trap: FindAllOf("RSTTrap") finds none (the traps are blueprint classes made from it), so every actor
-- is checked with IsA
function JW_TRAPS()
    local out = {}
    local cls = StaticFindObject("/Script/OMD4.RSTTrap")
    for _, a in ipairs(FindAllOf("Actor") or {}) do
        local ok, is = pcall(function() return a:IsA(cls) end)
        if ok and is and inst(a) then out[#out + 1] = a end
    end
    return out
end
local function curse_traps(sd, secs)
    local lib = bplib()
    local n, bad, err = 0, 0, nil
    for _, t in ipairs(JW_TRAPS()) do
        if inst(t) then
            local l = loc(t)
            if l and side_of_x(l.X) == sd then
                local ok, r = pcall(function() return lib:DisableTrap(t, secs) end)
                if ok and r ~= false then n = n + 1 else bad = bad + 1; err = err or tostring(r) end
            end
        end
    end
    return n, bad, err
end
function JW_CURSE(from, to, price, force, sender)
    local c = CURSES[force or math.random(#CURSES)]
    local secs = c.secs or 180
    V.curse = V.curse or {}
    V.curse[to] = {id = c.id, name = c.name, from = from, t0 = tick, till = tick + secs * 2, wave = V.cwave, isw = c.wave,
                   seen = {}, heroes = {}}
    say(string.format("SIDE %s CURSED SIDE %s: %s - " .. c.text, SIDE[from], SIDE[to], c.name, SIDE[to], SIDE[from]))
    log(string.format("curse %s on side %s (%d coins)", c.id, SIDE[to], price or 0))
    pcall(JW_CHAT, string.format("[SIDE %s] cursed SIDE %s: %s - " .. c.text, SIDE[from], SIDE[to], c.name, SIDE[to], SIDE[from]), sender)
    if c.id == "traps" then
        local n, bad, err = curse_traps(to, secs)
        log(string.format("curse traps: %d traps disabled for %d s on side %s%s", n, secs, SIDE[to], bad > 0 and (", " .. bad .. " failed: " .. tostring(err)) or ""))
    end
end
-- test (host): Ctrl+F6 puts the next curse in the list on your own side, free (one player is enough)
local curse_test = 0
pcall(function() RegisterKeyBind(Key.F6, {ModifierKey.CONTROL}, function() JW_CURSETEST = os.clock(); JW_CURSEPEND = true end) end)
local function curse_test_tick()
    if not JW_CURSEPEND or not V or not V.started or not is_host() then return end
    JW_CURSEPEND = nil
    curse_test = curse_test % #CURSES + 1
    local sd = my_side() or 1
    if V.curse then V.curse[sd] = nil end                -- on your own side, so you can see it when testing alone
    log("curse test " .. curse_test .. " (Ctrl+F6)")
    JW_CURSE(3 - sd, sd, 0, curse_test)
end
local function curse_tick()
    pcall(curse_test_tick)
    if not V or not V.curse or not is_host() then return end
    for sd = 1, 2 do
        local c = V.curse[sd]
        if c then
            -- a wave curse ends with the wave (but runs at least 60 s)
            if c.isw and V.cwave ~= c.wave and tick - c.t0 >= 120 and tick < c.till then c.till = tick end
            local live = tick < c.till
            if live and tick % 2 == 0 then show() end              -- the countdown under the score
            if live and (c.id == "double" or c.id == "armour" or c.id == "haste") and tick % 2 == 0 then
                for _, p in ipairs(FindAllOf("Character") or {}) do
                    if is_enemy(p) then
                        local key = p:GetAddress()
                        if not c.seen[key] then
                            local l = loc(p)
                            if l and side_of_x(l.X) == sd then
                                c.seen[key] = true
                                local ok, how = pcall(curse_enemy, p, c)
                                c.n = (c.n or 0) + 1
                                if (c.logged or 0) < 3 then
                                    c.logged = (c.logged or 0) + 1
                                    log("curse " .. c.id .. ": " .. (ok and ("set (" .. tostring(how) .. ")") or ("failed: " .. tostring(how))) .. " " .. JW_STATS(p))
                                    c.check = c.check or {}; table.insert(c.check, {p = p, t = tick + 4})
                                end
                            end
                        end
                    end
                end
            end
            if live and c.id == "haste" and (c.base or 0) < 3 and tick % 4 == 0 then
                for _, p in ipairs(FindAllOf("Character") or {}) do
                    if (c.base or 0) < 3 and is_enemy(p) then
                        local l = loc(p)
                        if l and side_of_x(l.X) ~= sd then c.base = (c.base or 0) + 1; log("haste: an orc on the other side for comparison: " .. JW_STATS(p)) end
                    end
                end
            end
            while c.check and #c.check > 0 and tick >= c.check[1].t do
                local e = table.remove(c.check, 1)
                if valid(e.p) then log("curse " .. c.id .. " 2 s later: " .. JW_STATS(e.p)) end
            end
            if c.id == "boots" and tick % 2 == 0 then
                for _, p in ipairs(heroes()) do
                    local key = p:GetAddress()
                    local l = loc(p)
                    if live and not c.heroes[key] and l and side_of_x(l.X) == sd then
                        local ok, how = pcall(speed_mul, p, 0.6)
                        c.heroes[key] = p
                        log("curse boots: hero slowed (" .. (ok and tostring(how) or ("failed: " .. tostring(how))) .. ")")
                    end
                end
                if not live then
                    for _, p in pairs(c.heroes) do if valid(p) then pcall(speed_mul, p, 1 / 0.6) end end
                    c.heroes = {}
                end
            end
            if not live and not c.done then
                c.done = true
                log(string.format("curse %s on side %s is over%s", c.id, SIDE[sd], c.n and (" (" .. c.n .. " enemies)") or ""))
                pcall(JW_CHAT, string.format("The curse on SIDE %s (%s) is over", SIDE[sd], c.name))
                show()
            end
        end
    end
end
local function sending()
    if not V or not V.sendq or V.winner or not is_host() then return end
    for sd = 1, 2 do                                       -- sent enemies that never showed up: forget after 15 s
        local w = V.sentwait[sd]
        if w and w.n > 0 and tick - w.t > 30 then log(string.format("send: %d sent enemies never seen on side %s", w.n, SIDE[sd])); V.sentwait[sd] = nil end
    end
    if #V.sendq == 0 then return end
    local made = 0
    while #V.sendq > 0 and made < 2 and (V.alive or 0) < MAX_ALIVE do
        local q = table.remove(V.sendq, 1)
        local sps = {}
        for _, sp in ipairs(FindAllOf("BP_AISpawner_C") or {}) do
            if inst(sp) then local l = loc(sp); if l and side_of_x(l.X) == q.side then table.insert(sps, l) end end
        end
        if #sps == 0 then log("send: no spawner on side " .. SIDE[q.side]); return end
        local l = sps[math.random(#sps)]
        local ok, r = pcall(spawn_twin, q.def, l, q.side, false)
        if ok and r then
            local w = V.sentwait[q.side] or {n = 0, list = {}}; V.sentwait[q.side] = w
            w.list = w.list or {}
            table.insert(w.list, {x = l.X, y = l.Y, dn = name_of(q.def)}); w.n = w.n + 1; w.t = tick
        else log("send error: " .. tostring(r)) end
        made = made + 1
    end
end
-- A second player's keys: their own referee (on their PC) sends the request to the host as a private chat message
-- ("!jwsend <n>", RSTPlayerState:Server_AddPlayerChatMessage, a server call any player may make). The host's referee
-- hooks that call, and pays and sends for the player it came from.
local SENDTAG = "!jwsend "
local function client_send(k)
    for _, pc in ipairs(FindAllOf("PlayerController") or {}) do
        local ok, done = pcall(function()
            if not pc:IsLocalController() then return false end
            local ps = pc.PlayerState
            ps:Server_AddPlayerChatMessage(SENDTAG .. k, 0, false, true)
            return true
        end)
        if ok and done then
            log("send request to the host: " .. SEND[k].name)
            V.mysends = V.mysends or {}; V.mysends[k] = (V.mysends[k] or 0) + 1       -- for this PC's send strip
            return
        end
        if not ok then log("send request failed: " .. tostring(done)) end
    end
end
for k, g in ipairs(SEND) do
    pcall(function() RegisterKeyBind(Key[g.key], function()
        if not V then return end
        -- Ctrl+F9 is the PvP test: the plain F9 bind may fire with it, so wait a moment and drop the send then
        if g.curse then                       -- Ctrl+F6 is the curse test: the plain F6 bind may fire with it
            local okd = pcall(ExecuteWithDelay, 150, function()
                if JW_CURSETEST and os.clock() - JW_CURSETEST < 0.5 then return end
                if not V then return end
                if is_host() then V.sendreq = k else V.clientreq = k end
            end)
            if okd then return end
        end
        if is_host() then V.sendreq = k else V.clientreq = k end
    end) end)
end
local chat_hooked = false
local function hook_chat()
    if chat_hooked then return end
    chat_hooked = true
    local ok, e = pcall(function()
        RegisterHook("/Script/OMD4.RSTPlayerState:Server_AddPlayerChatMessage", function(self, msg)
            pcall(function()
                if not V or not is_host() then return end
                local m = msg:get():ToString()
                local n = tonumber(m:match("^" .. SENDTAG .. "(%d+)$") or "")
                if not n then return end
                local ps = self:get()
                local lc = false
                pcall(function() lc = ps:GetOwner():IsLocalController() end)
                if lc then return end                 -- the host's own key press is handled directly
                V.remote = V.remote or {}
                table.insert(V.remote, {k = n, ps = ps})
                log("send request from the other player: " .. ((SEND[n] or {}).name or tostring(n)))
            end)
        end)
    end)
    log("hook Server_AddPlayerChatMessage (second player's sending): " .. (ok and "ok" or tostring(e)))
end

-- ---------- the map's VS rules (Map Maker -> rules.txt, one line per level) ----------
local function read_rules(level)
    local r = {}
    local f = io.open(RULES, "r")
    if not f then return r, "no rules file" end
    for line in f:lines() do
        local lv, rest = line:match("^(%S+)%s+(.*)$")
        if lv == level then
            for k, v in rest:gmatch("(%w+)=(%S*)") do r[k] = v end
            f:close(); return r, "found"
        end
    end
    f:close(); return r, "no line for this level"
end
local function apply_rules(level)
    local r, how = read_rules(level)
    local num = function(k, d) local n = tonumber(r[k] or ""); if n == nil then return d end; return n end
    if r.endless ~= nil then V.endless = num("endless", 1) ~= 0 end
    V.harder = num("orcs", HARDER * 100) / 100
    V.tougher = num("health", TOUGHER * 100) / 100
    if not V.endless then V.harder, V.tougher = 0, 0 end
    V.send_on = num("send", 1) ~= 0
    if r.prices then
        local i = 0
        for p in r.prices:gmatch("%d+") do i = i + 1; if SEND[i] then SEND[i].cost = tonumber(p) end end
    end
    V.rise = num("rise", RISE)
    V.archers_on = num("archers", 1) ~= 0
    V.midkill = num("midkill", 0) ~= 0
    V.midhalf = num("midhalf", 0)
    V.bridge0, V.bridge1 = num("bridge0", 0), num("bridge1", 0)          -- the VS bridge (world Y range): no middle kill on it
    V.pits = num("pits", 0)                             -- death pits / ravine cells in this map: a fall kills
    V.killz = num("killz", -400)
    V.start_coins = num("coins", 0)
    V.rift_rule = num("rift", 0)
    V.pvp_rule = num("pvp", 0) ~= 0                     -- PvP: heroes can hit each other
    log(string.format("middle kills: %s (%.0f cm each side of the middle)", V.midkill and "on" or "off", V.midhalf))
    log(string.format("death pits: %d cells, a fall below z %.0f kills", V.pits, V.killz))
    local pr = {}
    for _, g in ipairs(SEND) do pr[#pr + 1] = tostring(g.cost) end
    log(string.format("VS rules (%s): endless %s, orcs +%d%%, health +%d%% per wave, sending %s (%s, +%d%% per send), archer trap %s, coins %s, rift points %s, PvP %s",
        how, V.endless and "on" or "off", math.floor(V.harder * 100 + 0.5), math.floor(V.tougher * 100 + 0.5),
        V.send_on and "on" or "off", table.concat(pr, "/"), V.rise, V.archers_on and "allowed" or "not allowed",
        V.start_coins > 0 and tostring(V.start_coins) or "mission's", V.rift_rule > 0 and tostring(V.rift_rule) or "mission's", V.pvp_rule and "on" or "off"))
end

-- starting coins (rule): each player's coins set to the rule's number a few seconds into the match (the game hands
-- out its own starting coins when the match begins)
local function start_coins()
    if not V or not V.coins_at or tick < V.coins_at or not is_host() then return end
    V.coins_at = nil
    for i, e in ipairs(econ_players()) do
        local ok, r = pcall(function()
            local have = e.ps.Coin
            local d = V.start_coins - have
            if d > 0 then e.ps:GrantCoin(d, 0) elseif d < 0 then e.ps:SpendCoin(-d, 2) end
            return string.format("%d -> %d", have, V.start_coins)
        end)
        log(string.format("starting coins, player %d: %s", i, ok and r or tostring(r)))
    end
end

-- archer trap not allowed (rule): placed ones are sold again (coins back)
local function no_archers()
    if not V or V.archers_on ~= false or tick % 4 ~= 1 or not is_host() then return end
    for _, t in ipairs(FindAllOf("BP_Sentinel_Archer_Trap_C") or {}) do
        pcall(function()
            if not t:IsValid() or t.bIsBeingPlaced then return end
            local own = false
            pcall(function() local p = t.TrapOwner:Get(); own = p and p:IsValid() end)
            if not own then return end                -- a sentinel of the map itself
            local ok, r = pcall(function() return t:Sell() end)
            if not (ok and r == true) then pcall(function() t.bPreventSell = false end); ok, r = pcall(function() return t:Sell() end) end
            if not (ok and r == true) then pcall(function() t:K2_DestroyActor() end) end
            say("the guardian archer trap is not allowed on this map")
        end)
    end
end

-- the mission's waves restarted? if no wave orc shows up 15 s after the restart, the referee runs the rounds itself
local function check_restart()
    if not V or not V.restart_check or tick < V.restart_check then return end
    V.restart_check = nil
    if V.round_waves > 0 then log("round " .. V.round .. ": the mission's waves are running again")
    elseif #V.history == 0 then log("round " .. V.round .. ": no waves to replay")
    else
        log("round " .. V.round .. ": the mission did not restart; the referee runs the waves (" .. #V.history .. " orcs, x" .. V.round .. " per side)")
        V.replay = {i = 1, t0 = tick, speed = 1.0}
    end
end

-- ---------- main loop ----------
local function start_match(level, rifts)
    V = {level = level, rifts = rifts, mid = (rifts[1].x + rifts[2].x) / 2, lives = {0, 0}, started = false,
         last = nil, placed = {}, player_side = {}, winner = nil,
         twins = true, seen_enemy = {}, queue = {}, pending = {}, wave = {0, 0}, made = {0, 0}, need = {0, 0}, tries = 0,
         history = {}, eside = {}, dead = {}, deaths = {}, kgrants = {}, snap = {}, sendq = {}, sentwait = {}, t0 = tick, round_waves = 0, replay = nil, restart_check = nil, alive = 0,
         hp = {nil, nil}, dmg = {0, 0}, hdmg = {0, 0}, owe = {0, 0}, test = false, reinit = nil,
         endless = true, round = 1, active = nil, was_active = false, restart_at = nil}
    entries = {}; seen = {}
    log(string.format("VS level %s: rift A at x=%.0f, rift B at x=%.0f, middle x=%.0f", level, rifts[1].x, rifts[2].x, V.mid))
    local f = io.open(BIN .. "JW_NOTWINS", "r"); if f then f:close(); V.twins = false end
    log("twins: " .. (V.twins and "on" or "off (JW_NOTWINS found)"))
    f = io.open(BIN .. "JW_NOENDLESS", "r"); if f then f:close(); V.endless = false end
    f = io.open(BIN .. "JW_TEST", "r"); if f then f:close(); V.test = true end
    f = io.open(BIN .. "JW_ECONSOLO", "r"); if f then f:close(); V.econsolo = true end
    log("economy solo test: " .. (V.econsolo and "on (JW_ECONSOLO found)" or "off"))
    f = io.open(BIN .. "JW_NODOORTAG", "r"); if f then f:close(); V.notag = true end
    f = io.open(BIN .. "JW_FASTWAVES", "r"); if f then f:close(); V.fast = true; log("KEEPER TEST: a keeper is picked in wave 1 (JW_FASTWAVES found)") end
    log("door tag: " .. (V.notag and "off (JW_NODOORTAG found)" or "on"))
    V.nofix = true
    f = io.open(BIN .. "JW_FIX", "r"); if f then f:close(); V.nofix = false end
    log("old orc workarounds (unstick, forced barricade attack): " .. (V.nofix and "off" or "on (JW_FIX found)"))
    if V.test then log("TEST MODE (JW_TEST found): a side at 0 is refilled, the match never ends") end
    local noend = not V.endless
    apply_rules(level)
    if noend then V.endless = false end           -- JW_NOENDLESS still wins
    log("endless waves: " .. (V.endless and "on" or "off"))
    try_hooks()
    hook_chat()
end

local function finish(w)
    if V.winner then return end
    V.winner = w
    log("result: " .. (w == 0 and "draw" or ("side " .. (w == 1 and "A" or "B") .. " wins")) ..
        string.format(" (A %d, B %d)", V.lives[1], V.lives[2]))
    show()
end

local function step()
    tick = tick + 1
    -- which level: taken from the rift actors' own path (FindFirstOf("World") can return a streamed sublevel)
    if V then
        if tick % 4 == 0 and #find_rifts() ~= 2 then log("left VS level"); V = nil; hud = nil; mark = nil; strip = nil; board = nil end
    end
    if not V then
        if tick % 2 ~= 0 then return end
        local rifts = find_rifts()
        if #rifts ~= 2 or math.abs(rifts[1].x - rifts[2].x) < 100 then return end
        local lv = name_of(rifts[1].r):match("(Level_JW_[^%.:]+)[%.:]")
        if not lv then return end
        start_match(lv, rifts)
    end
    local pts = rift_points()
    if pts == nil then return end
    if not V.started then
        local gs = game_state()
        local ok, st = pcall(function() return gs:IsGameStarted() end)
        if (ok and st) or tick % 4 == 0 then
            if pts > 0 then
                V.started = true; V.lives = {pts, pts}; V.last = pts; V.t0 = tick; V.start = pts; V.lost = {0, 0}
                if (V.rift_rule or 0) > 0 then V.lives = {V.rift_rule, V.rift_rule} end
                if (V.start_coins or 0) > 0 then V.coins_at = tick + 8 end
                log("match on: each side starts with " .. V.lives[1] .. " rift points")
                pcall(scale_health)                     -- back to normal health (it stays raised from a last match)
                -- one shared pool for both sides = A + B: every point an orc takes belongs to exactly one side, the pool
                -- never runs dry before a side does, and the referee does not have to touch it while orcs walk in
                -- (the cheat SetRiftPoints raises the pool through AddRiftPoints when the number is higher)
                -- (raised a few seconds later: the game sets its starting points again when the waves begin)
                V.raise_from = tick + 6; V.raise_tries = 0
                show()
            end
        end
        place_players()
        return
    end
    if tick % 2 == 0 then place_players() end
    if V.winner then
        if is_host() and pts > 0 and tick % 4 == 0 and (V.endtries or 0) < 6 then
            V.endtries = (V.endtries or 0) + 1
            local gs = game_state()
            local ok, e = pcall(function() gs:SubtractRiftPoints(3, pts) end)       -- reason Cheat
            log(string.format("ending the game: SubtractRiftPoints(%d) %s, pool now %s", pts, ok and "ok" or tostring(e), tostring(rift_points())))
            if (V.endtries % 2) == 0 then console("SetRiftPoints 0") end
        end
        if tick % 8 == 0 then show() end
        return
    end
    if pts > V.last then
        if V.raise_from and pts >= V.lives[1] + V.lives[2] then
            log("pool raised to " .. pts .. " (side A + side B) by " .. tostring(V.raise_method)); V.raise_from = nil
        end
        V.last = pts                      -- our raise (or a heal): not a loss
    end
    if V.raise_from and tick >= V.raise_from and is_host() then
        local want = V.lives[1] + V.lives[2]
        if pts >= want then
            log("pool holds " .. pts .. " (side A + side B)"); V.raise_from = nil
        elseif V.lost[1] + V.lost[2] > 0 or V.raise_tries >= 9 then
            -- the raise did not work (or orcs got in first): split what the pool holds between the sides
            V.raise_from = nil
            local t = V.lives[1] + V.lives[2]
            V.lives[1] = math.floor(V.lives[1] * pts / t); V.lives[2] = pts - V.lives[1]
            log(string.format("pool could not be raised after %d tries (holds %d, wanted %d): sides now A %d, B %d",
                V.raise_tries, pts, want, V.lives[1], V.lives[2]))
            show()
        elseif (tick - V.raise_from) % 4 == 0 then
            -- three ways in turn: the game state's own AddRiftPoints, writing the property, the cheat command
            V.raise_tries = V.raise_tries + 1
            local m = ({"AddRiftPoints", "write RiftPoints", "cheat SetRiftPoints"})[(V.raise_tries - 1) % 3 + 1]
            V.raise_method = m
            local gs = game_state()
            local ok, e = pcall(function()
                if m == "AddRiftPoints" then gs:AddRiftPoints(want - pts)
                elseif m == "write RiftPoints" then gs.RiftPoints = want
                else console("SetRiftPoints " .. want) end
            end)
            log(string.format("raise try %d (%s): %s, pool now %s", V.raise_tries, m, ok and "ok" or tostring(e), tostring(rift_points())))
        end
    end
    track_damage()
    pcall(track_hero_deaths)
    if pts < V.last and pts == V.start and V.lost[1] + V.lost[2] == 0 and #entries == 0 and (V.reraise or 0) < 3 then
        -- the game set its starting points again (e.g. when the waves begin): raise once more, nothing was lost
        V.reraise = (V.reraise or 0) + 1; V.last = pts
        log("the game reset the pool to " .. pts .. ": raising it again")
        V.raise_from = tick; V.raise_tries = 0
    end
    if pts < V.last then
        local d = V.last - pts
        V.last = pts
        -- 1) orcs seen walking into a rift, oldest first (one point each; entries without a point yet are kept for the
        --    next drop), 2) the rest by crystal damage, 3) the side of the orcs that just walked in, 4) the nearest enemy
        local sa, sb, last = 0, 0, nil
        while d > 0 and #entries > 0 do
            local e = table.remove(entries, 1)
            if e.side == 1 then sa = sa + 1 else sb = sb + 1 end
            last = e.side; d = d - 1
        end
        local how = string.format("entries A %d B %d, %d waiting", sa, sb, #entries)
        local rest = d
        if rest > 0 and V.hdeaths and #V.hdeaths > 0 then
            -- 2) a hero died just now: the whole rest is the death's cost, on the dead hero's side
            local h = table.remove(V.hdeaths, 1)
            if h.side == 1 then sa = sa + rest else sb = sb + rest end
            how = how .. ", hero died on side " .. SIDE[h.side]; rest = 0
        end
        if rest > 0 then
            local da, db = V.hdmg[1], V.hdmg[2]                  -- damage seen by the crystal hook
            local src = "crystal hits"
            if da + db == 0 then da, db = V.dmg[1], V.dmg[2]; src = "crystal health" end
            if da + db > 0 then
                V.owe[1] = V.owe[1] + rest * da / (da + db); V.owe[2] = V.owe[2] + rest * db / (da + db)
                local ra = math.floor(V.owe[1] + 1e-6); local rb = math.floor(V.owe[2] + 1e-6)
                if ra + rb < rest then
                    if V.owe[1] - ra >= V.owe[2] - rb then ra = ra + 1 else rb = rb + 1 end
                end
                V.owe[1] = V.owe[1] - ra; V.owe[2] = V.owe[2] - rb
                sa, sb = sa + ra, sb + rb
                how = how .. string.format(", %s A %.0f B %.0f", src, da, db)
            else
                local s = last or nearest_side() or 1                -- an orc that costs more than one point
                if s == 1 then sa = sa + rest else sb = sb + rest end
                how = how .. (last and ", extra cost side " or ", nearest enemy side ") .. SIDE[s]
            end
        end
        if curse_on(1, "fragile") and sa > 0 then how = how .. ", fragile rift A x2"; sa = sa * 2 end
        if curse_on(2, "fragile") and sb > 0 then how = how .. ", fragile rift B x2"; sb = sb * 2 end
        log(string.format("rift points -%d -> A -%d, B -%d (%s)", sa + sb, sa, sb, how))
        V.dmg = {0, 0}; V.hdmg = {0, 0}
        V.lost[1] = V.lost[1] + sa; V.lost[2] = V.lost[2] + sb
        V.lives[1] = V.lives[1] - sa; V.lives[2] = V.lives[2] - sb
        show()
        if V.lives[1] <= 0 or V.lives[2] <= 0 then
            finish((V.lives[1] <= 0 and V.lives[2] <= 0) and 0 or (V.lives[1] <= 0 and 2 or 1))
        end
    end
    if #entries > 0 and tick - entries[1].t > 8 then table.remove(entries, 1) end   -- an entry that never cost a point
    -- endless waves: when the mission's onslaught stops (polled, no hooks: hooks on the coordinator crashed the game),
    -- start it again 3 s later
    local co = coordinator()
    if co and V.endless and is_host() then
        local oka, active = pcall(function() return co:IsOnslaughtActive() end)
        if oka and type(active) == "boolean" then
            if active ~= V.active then log("onslaught active: " .. tostring(active)); V.active = active end
            if active == false and V.was_active and not V.restart_at then
                -- restart at once: the game declares victory as soon as the last wave orc dies after this
                V.restart_at = tick; log("the mission's waves are over: restarting now")
            end
            if active then V.was_active = true end
        end
    end
    if V.restart_at and tick >= V.restart_at and is_host() then
        V.restart_at = nil; V.was_active = false
        -- Onslaught_Start(1, 0) did not restart the mission's waves (tested 2026-11-11), and the game declared victory
        -- 4 s later: the referee runs the rounds itself, starting at once (replay of round 1, more orcs each round)
        if #V.history > 0 then
            V.mission_over = true
            V.round = V.round + 1; V.round_waves = 0; pcall(scale_health)
            V.replay = {i = 1, t0 = tick, speed = 1.0}
            log("round " .. V.round .. " (run by the referee, at once): " .. #V.history .. " wave orcs x" .. V.round .. " per side")
            show()
        else log("no recorded waves: cannot run more rounds") end
    end
    local function mission_alive(c0)
        local okm, m = pcall(function() return c0 and c0:GetNumPawnsAlive() end)
        return (okm and type(m) == "number") and m or 0
    end
    local function is_dying(c) local okd, d = pcall(function() return c.HealthComponent:IsDeadOrDying() end); return okd and d == true end
    -- the mission's waves (game state CurrentWave / MaxWave), logged when they change
    local gsw = game_state()
    local okw, cw, mw = pcall(function() return gsw.CurrentWave, gsw.MaxWave end)
    if okw and type(cw) == "number" and cw ~= V.cwave then
        V.cwave = cw; log(string.format("mission wave %d of %s", cw, tostring(mw)))
        pcall(scale_health)
        pcall(dump_waves, "wave " .. cw)
    end
    -- fast test (file JW_FASTWAVES): skip the mission's waves with the cheat NextWave until the last one
    -- (the cheat NextWave did nothing: no fast skipping)
    if V.started and tick % 40 == 20 and (V.dumps or 0) < 40 then V.dumps = (V.dumps or 0) + 1; pcall(dump_waves, "t" .. tick) end
    -- keeper: after its last wave (picked in the second-to-last: CurrentWave may count from 0) the game declares victory as soon as none of ITS OWN enemies is alive (ours from
    -- the spawners do not count). So in the last wave one mission enemy is put aside: moved high above the map,
    -- frozen, hidden and made undamageable. It stays alive, so the game never sees zero, and endless can go on.
    -- test (JW_FASTWAVES): the keeper is picked already in wave 1, so a short test shows whether the game still counts it
    local pick_now = V.fast and okw and type(cw) == "number" and cw >= 1
    local last_waves = okw and type(cw) == "number" and type(mw) == "number" and mw > 0 and cw >= mw - 1
    -- (no keeper needed any more: the VS maps' wave script runs wave 1 for every wave and never ends the mission;
    --  only the JW_FASTWAVES test still picks one)
    if V.endless and V.fast and is_host() and not V.keeper and (pick_now or last_waves)
       and V.lastwave and valid(V.lastwave.p) and not is_dying(V.lastwave.p) and tick - V.lastwave.t < 20
       and mission_alive(co) > 0 then
        local k = V.lastwave.p
        local n0 = co and select(2, pcall(function() return co:GetNumPawnsAlive() end))
        -- it walks as normal (frozen or moved off the navmesh, the game's stuck timer removed it after ~35 s), cannot be
        -- damaged, and is put back where it was picked every 8 s, so it never reaches the rift
        local ok, e = pcall(function() k.bCanBeDamaged = false end)
        V.keeper = k; V.keeper_key = V.lastwave.key; V.keeper_t = tick; V.keeper_home = loc(k)
        local n1 = co and select(2, pcall(function() return co:GetNumPawnsAlive() end))
        log(string.format("keeper: %s picked, cannot be damaged (%s); mission enemies alive before %s, after %s",
            name_of(k):match("[^%.]+$") or "?", ok and "ok" or tostring(e), tostring(n0), tostring(n1)))
    end
    if V.keeper and V.keeper_home and tick % 16 == 0 and valid(V.keeper) then
        local h = V.keeper_home
        pcall(function() V.keeper:K2_SetActorLocation({X = h.X, Y = h.Y, Z = h.Z}, false, {}, true) end)
    end
    if V.keeper and tick % 10 == 0 then
        local okn, n = pcall(function() return co and co:GetNumPawnsAlive() end)
        if not valid(V.keeper) or is_dying(V.keeper) then
            log(string.format("keeper gone after %d s!", (tick - (V.keeper_t or tick)) // 2)); V.keeper = nil
        elseif (V.keeplog or 0) < 40 then
            local l = loc(V.keeper)
            V.keeplog = (V.keeplog or 0) + 1
            log(string.format("keeper alive (%d s) at (%.0f, %.0f, %.0f), mission enemies alive %s, wave %s",
                (tick - V.keeper_t) // 2, l and l.X or 0, l and l.Y or 0, l and l.Z or 0, tostring(okn and n), tostring(V.cwave)))
        end
    end
    local gs = game_state()
    local ok, ended = pcall(function() return gs:IsGameEnded() end)
    if ok and ended and not V.winner then
        log("the game says it has ended (round " .. V.round .. ")")
        finish(V.lives[1] == V.lives[2] and 0 or (V.lives[1] > V.lives[2] and 1 or 2))
    end
    if tick % 8 == 0 then show() end
end

-- every 5 s while a match runs: how many enemies are on each side (diagnostics for the log)
-- ---------- stuck orcs (barricade test): log what an orc that stands still thinks, then try to unstick it ----------
local STATE = {[0] = "NotSet", "Spawn", "Reset", "MoveToNode", "Combat", "WaitForDoor", "SearchForPlayer", "Launched",
               "InAbility", "Guard", "ReturnToGuard", "Recover", "FollowMaster", "Interacting"}
local function bb_describe(c)
    local out = {}
    pcall(function()
        local bb = c.Blackboard
        local kr, kp = c.BlackboardRiftPointKey, c.BlackboardCurrentPathPointKey
        local okv, v = pcall(function() return bb:GetValueAsVector(kr) end)
        out[#out + 1] = "rift point " .. (okv and v and string.format("(%.0f, %.0f)", v.X, v.Y) or "?")
        local oko, o = pcall(function() return bb:GetValueAsObject(kr) end)
        if oko and valid(o) then out[#out + 1] = "= " .. (name_of(o):match("[^%.]+$") or "?") end
        local okp, q = pcall(function() return bb:GetValueAsObject(kp) end)
        local okq, w = pcall(function() return bb:GetValueAsVector(kp) end)
        out[#out + 1] = "| path point " .. ((okp and valid(q)) and (name_of(q):match("[^%.]+$") or "?") or "none") ..
            (okq and w and string.format(" (%.0f, %.0f)", w.X, w.Y) or "")
    end)
    return table.concat(out, " ")
end

local function ai_info(p)
    local c = p:GetController()
    if not valid(c) then return "no controller" end
    local st, bl, stuck = "?", "?", "?"
    pcall(function() local v = c.CurrentState; st = STATE[v] or tostring(v) end)
    pcall(function() bl = tostring(c:IsBlockedToNode()) end)
    pcall(function() stuck = tostring(c:GetIsRunning()) end)
    return string.format("state %s, blocked to node %s, running %s | %s", st, bl, stuck, bb_describe(c))
end

-- barricades on the game state's list (GameState:UpdateBarricadesArray) are what blocked orcs attack; add ours
local function list_barricades()
    if not V or V.nofix or not V.started or V.winner or tick % 10 ~= 3 or not is_host() then return end
    local gs = game_state(); if not gs then return end
    V.barr = V.barr or {}
    local n, new = 0, 0
    for _, t in ipairs(FindAllOf("RSTTrap") or {}) do
        if inst(t) then
            local nm = name_of(t)
            V.trapnames = V.trapnames or {}
            local short = nm:match("^(%S+)") .. " " .. (nm:match("([^%.]+)$") or "")
            local cls = nm:match("^(%S+)") or "?"
            if not V.trapnames[cls] then V.trapnames[cls] = true; log("trap placed: " .. short) end
            if nm:find("Barricade") or nm:find("barricade") then
                n = n + 1
                local okk, key = pcall(function() return t:GetAddress() end)
                local bl = loc(t)
                if bl then V.barrpos = V.barrpos or {}; V.barrpos[key] = {t = t, x = bl.X, y = bl.Y, seen = tick} end
                if okk and not V.barr[key] then
                    V.barr[key] = true; new = new + 1
                    local ok, e = pcall(function() gs:UpdateBarricadesArray(t, true) end)
                    if (V.barrlog or 0) < 5 then
                        V.barrlog = (V.barrlog or 0) + 1
                        log("barricade " .. nm:match("[^%.]+$") .. " side " .. SIDE[side_of_x((loc(t) or {X = 0}).X)] ..
                            " -> UpdateBarricadesArray: " .. (ok and "ok" or tostring(e)))
                    end
                end
            end
        end
    end
    for bk, b in pairs(V.barrpos or {}) do if tick - b.seen > 20 then V.barrpos[bk] = nil end end
    if new > 0 then log("barricades: " .. n .. " placed, " .. new .. " new") end
end

local function stuck_check()
    if V and V.nofix then return end
    -- Orcs blocked by barricades stand still on our maps: the game does not plan their route through the barricades.
    -- Every 5 s: an orc that is blocked to its next path point and has not moved gets its routes recomputed including
    -- routes through obstructions; it then walks to the barricade and attacks it.
    if not V or not V.started or V.winner or tick % 10 ~= 5 or not is_host() then return end
    V.still = V.still or {}; V.stucklog = V.stucklog or 0
    local fixed = 0
    for _, p in ipairs(FindAllOf("Character") or {}) do
        local okk, key = pcall(function() return p:GetAddress() end)
        if okk and V.seen_enemy[key] and valid(p) then
            local l = loc(p)
            if l and (math.abs(l.X) > 1 or math.abs(l.Y) > 1) then
                local s0 = V.still[key]
                if s0 and (s0.x - l.X) ^ 2 + (s0.y - l.Y) ^ 2 < 60 * 60 then
                    s0.n = s0.n + 1
                    if V.nudged_n == nil then V.nudged_n = 0 end
                    if V.nudged_n < 400 then                                -- ask it to look for barricades to break
                        local c = p:GetController()
                        local oks, st = pcall(function() return c.CurrentState end)
                        if not (oks and st == 8) then
                            V.nudged_n = V.nudged_n + 1
                            local ok1 = pcall(function() p.NextEvaluateNearbyBreakablesTime = 0.0; p:BP_EvaluateNearbyBreakables() end)
                            local ok2 = pcall(function() c:HandleThreatEvaluation() end)
                            if V.nudged_n <= 12 then
                                local ok, info = pcall(ai_info, p)
                                log(string.format("breakables check side %s at (%.0f, %.0f): evaluate %s, threats %s -> %s",
                                    SIDE[side_of_x(l.X)], l.X, l.Y, ok1 and "ok" or "failed", ok2 and "ok" or "failed", ok and info or "?"))
                            end
                        end
                    end
                    if fixed < 25 then
                        local c = p:GetController()
                        local okb, blocked = pcall(function() return c:IsBlockedToNode() end)
                        local oks, st = pcall(function() return c.CurrentState end)
                        V.fixedat = V.fixedat or {}
                        -- nearest barricade on this orc's side, up to 6 m away (only for orcs the game marks as blocked)
                        local sdo = side_of_x(l.X)
                        local nb, nbd = nil, 600 * 600
                        for bk, b in pairs(V.barrpos or {}) do
                            if tick - b.seen <= 20 and side_of_x(b.x) == sdo then
                                local dd = (b.x - l.X) ^ 2 + (b.y - l.Y) ^ 2
                                if dd < nbd then nbd, nb = dd, b end
                            end
                        end
                        if okb and blocked and not (oks and st == 8) and tick - (V.fixedat[key] or -1000) > 20 then
                            V.fixedat[key] = tick
                            fixed = fixed + 1
                            -- a barricade within 6 m: make it the orc's target and go to combat (the game itself never does this
                            -- on our two-rift maps); otherwise recompute the routes so it walks up to the barricade first
                            local bt = nb and inst(nb.t) and nb.t or nil
                            local okc
                            if bt then
                                okc = pcall(function()
                                    pcall(function() c.Blackboard:SetValueAsObject(c.BlackboardCurrentTargetKey, bt) end)
                                    c:SetCurrentState(4, bt)
                                end)
                                V.attacks = (V.attacks or 0) + 1
                            else
                                okc = pcall(function() c:UpdatePathNodeCosts(true); c:UpdateNodeNetwork(); c:ResumeAI(true) end)
                            end
                            if V.stucklog < 25 then
                                V.stucklog = V.stucklog + 1
                                local ok, info = pcall(ai_info, p)
                                log(string.format("unstick orc side %s at (%.0f, %.0f): %s -> %s", SIDE[side_of_x(l.X)], l.X, l.Y,
                                    ok and info or "?", bt and (okc and "ATTACK the barricade" or "attack failed") or (okc and "routes recomputed" or "failed")))
                            end
                        end
                    end
                else
                    V.still[key] = {x = l.X, y = l.Y, n = 0}
                end
            end
        end
    end
    if fixed > 0 then V.unstuck = (V.unstuck or 0) + fixed end
    if tick % 40 == 5 and (V.unstuck or 0) > 0 then log("unstuck so far: " .. V.unstuck .. ", sent to attack a barricade: " .. (V.attacks or 0)) end
end

local function census()
    if not V or tick % 10 ~= 0 then return end
    local a, b = 0, 0
    for _, p in ipairs(FindAllOf("Character") or {}) do
        local okk, key = pcall(function() return p:GetAddress() end)
        local e = okk and V.seen_enemy[key]
        if e == nil then e = is_enemy(p) end
        if e and valid(p) then local l = loc(p); if l and (l.X ~= 0 or l.Y ~= 0) then if l.X < V.mid then a = a + 1 else b = b + 1 end end end
    end
    local co, w, al = coordinator(), "?", "?"
    if co then
        pcall(function() w = tostring(co:GetNumPawnsWaitingForSpawn()) end)
        pcall(function() al = tostring(co:GetNumPawnsAlive()) end)
    end
    log(string.format("enemies: side A %d, side B %d | pool %s | lives A %d, B %d | onslaught alive %s, waiting %s | crystal hp A %s, B %s",
        a, b, tostring(rift_points()), V.lives[1], V.lives[2], al, w, tostring((crystal_hp(1))), tostring((crystal_hp(2)))))
end

-- Start slowly and stay light: nothing for the first 40 s after the game started (calling into the engine during
-- startup hung / crashed the game), then two steps a second, on the game thread, never queued twice.
local queued, wait, STEP_MS = false, 80, 500
local function run_step()
    local ok, err = pcall(function() step(); if V and V.sendreq then local k = V.sendreq; V.sendreq = nil; do_send(k) end
        if V and V.clientreq then local k = V.clientreq; V.clientreq = nil; client_send(k) end
        while V and V.remote and #V.remote > 0 do local q = table.remove(V.remote, 1); do_send(q.k, q.ps) end
        start_coins(); no_archers()
        if V then
            if rift_labels then pcall(rift_labels) end
            pcall(team_dots); pcall(middle_kill); pcall(pit_kill); pcall(team_banners); pcall(minimap_dots); pcall(pvp_tick); pcall(curse_tick)   -- (minimap_dump, a diagnostic walk of the minimap widgets, crashed the game ~20 s into a match: off)
            if tick % 2 == 0 then
                local sd = my_side()
                if sd and not (board and valid(board.w)) then pcall(side_line, string.format("YOU ARE SIDE %s  -  defend the %s sign", SIDE[sd], SIDEWORD[sd]), sd)
                elseif mark and valid(mark.w) then pcall(function() mark.w:RemoveFromParent() end); mark = nil end
                pcall(update_strip)
                if board_update then pcall(board_update) end
                pcall(hide_game_rift_counter)
            end
        end
 twins(); sending(); coins(); check_restart(); list_barricades(); stuck_check(); census() end)
    if not ok then log("step error " .. tostring(err)) end
end
if type(LoopInGameThreadWithDelay) == "function" then
    log("using LoopInGameThreadWithDelay")
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
