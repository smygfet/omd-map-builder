-- JWArcherAuto v13: makes the Guardian Archer trap (BP_Sentinel_Archer_Trap, a map sentinel) work as a player trap.
--  * placed by a player -> marked paid and summoned right away (no extra sentinel payment)
--  * can be sold (sentinels have bPreventSell); selling removes its archer
--  * exactly one archer per trap: a new archer is moved onto its trap's spawn point (the game spawns summons like
--    enemies, sometimes at an orc spawner); extra copies from the same summon are removed
--  * archers stand still but can turn: walking speed and acceleration 0 instead of DisableMovement (v2), which left them
--    hovering where they were put and unable to turn towards what they shoot (they aimed ~45 degrees off)
--  * selling: the game's sell button never offers sentinel traps, so Delete sells the archer trap you stand next to
--    (within 4 m): Sell() on the trap, or if that refuses, the trap's price back as coins and the trap removed
--  * v5: selling only in the build phase (a break is active, or no enemy alive); during a wave Delete does nothing
--    and the traps keep bPreventSell, so no other way of selling works either
--  * v6: the second player's Delete is sent to the host as a private chat message ("!jwsell"); the host sells
--  * v7: selling the normal way (look at it, hold the sell key). The archer trap's parts get the collision setup of a
--    normal trap's parts (copied from the first other trap you place), its coin-contribution interaction is switched
--    off, and each trap kind's parts are logged once, plus what the game's sell ability does. Delete still works.
--  * v8: v7's log showed the archer trap's collision is already the same as a normal trap's, and the game's sell never
--    even reaches the server for it (its client-side check refuses sentinel traps). So the mod listens to the game's own
--    sell button (the sell ability's input): when you press it while looking at your archer trap (it's the trap closest
--    to where you aim, within 15 m), the mod sells it (on the host directly, the second player's through the host).
--  * v9: a sold trap stays in the game (bIsSold) for a while, so its archer stayed: the archer is now removed as soon
--    as its trap is sold. While you aim at your archer trap in the build phase, it shows the game's sell highlight
--    (the trap's own BP_SellableBegin/End).
--  * v10: a sold trap is never taken up again (v9 dropped it from its list, then saw it as a newly placed trap and
--    summoned a new archer onto it every half second, which kept the plate too). Sold traps are remembered and hidden
--    and removed if the game leaves them. The highlight also calls the trap's own "Update Sell Visuals".
--  * v11: a much bigger sell target: the line of sight counts if it passes within 1.6 m of the plate or anywhere on the
--    archer (feet to head), up to 25 m away, and an archer trap wins over a normal trap that is about as close.
--  * v12: normal traps couldn't be sold any more. Hooks on the game's sell ability (Server_SellTrap, OnInputReleased,
--    K2_ActivateAbility, BP_SellableBegin) are removed; only the sell button's press (OnInputPressed) is listened to.
--  * v13: selling paid nothing back (Sell() says yes but the game pays no refund for a sentinel trap): a second after
--    the sale the mod checks the player's coins and pays the refund itself if it didn't come. Less lag when placing:
--    v7's part dumps and collision copying are gone (they walked every collision part in the level three times per
--    archer); the coin-contribution volume is switched off directly.
-- Map-placed sentinels (not owned by a player) are left alone. Log: Binaries/Win64/JW_ArcherAuto.txt
local BIN = "C:/Program Files (x86)/Steam/steamapps/common/Orcs Must Die Deathtrap/OMDD/Binaries/Win64/"
local LOG = BIN .. "JW_ArcherAuto.txt"
local f = io.open(LOG, "w"); if f then f:write(os.date("%H:%M:%S ") .. "v13 loaded\n"); f:close() end
local function w(s) local f = io.open(LOG, "a"); if f then f:write(os.date("%H:%M:%S ") .. s .. "\n"); f:close() end end
local function get(o, k) local ok, v = pcall(function() return o[k] end); if ok then return v end end
local function valid(o) return o ~= nil and pcall(function() return o:IsValid() end) and o:IsValid() end

local traps = {}      -- trap address -> {trap=, archer=, summoned_at=}
local sold = {}       -- trap address -> clock when sold (never taken up again)
local refunds = {}    -- {ps, coin0, price, at}: refunds to check a second after a sale
local known = {}      -- archer addresses already handled (ours or map sentinels)
local clock = 0

local function owned(t)
    local ok, v = pcall(function() local p = t.TrapOwner:Get(); return p and p:IsValid() end)
    if ok and v then return true end
    if get(t, "bIsOwnedByLocalPlayer") == true then return true end
    local i = get(t, "TrapOwnerPlayerIndex")
    return type(i) == "number" and i >= 0 and valid(get(t, "TrapDefinition"))
end
local function spawn_loc(t)
    local ok, v = pcall(function() return t.SpawnPoint:K2_GetComponentLocation() end)
    if ok and v then return v end
    return t:K2_GetActorLocation()
end
local function dist2(a, b) local dx, dy, dz = a.X - b.X, a.Y - b.Y, a.Z - b.Z; return dx * dx + dy * dy + dz * dz end
-- keep an archer in place without freezing it: no walking, but gravity (stands on the floor) and turning still work
local function hold(archer)
    local cm = get(archer, "CharacterMovement")
    if not cm then return end
    pcall(function() cm.MaxWalkSpeed = 0.0 end)
    pcall(function() cm.MaxAcceleration = 0.0 end)
    pcall(function() cm.bUseControllerDesiredRotation = true end)
    pcall(function() cm.RotationRate = {Pitch = 0.0, Yaw = 540.0, Roll = 0.0} end)
    if get(cm, "MovementMode") == 0 then pcall(function() cm:SetMovementMode(1, 0) end) end   -- undo v2's DisableMovement
end
local function pin(archer, rec)
    local loc = spawn_loc(rec.trap)
    if dist2(archer:K2_GetActorLocation(), loc) > 150 * 150 then
        local rot = rec.trap:K2_GetActorRotation()
        pcall(function() archer:K2_TeleportTo(loc, rot) end)
        w("  moved archer onto its trap")
    end
    hold(archer)
    rec.archer = archer
end

-- build phase: the game state says a break is active (the go break before wave 1, timed breaks between waves);
-- if that can't be read, no living enemy counts as build phase
local function enemies_alive()
    for _, c in ipairs(FindAllOf("RSTAICharacter") or {}) do
        local ok, alive = pcall(function()
            if not c:IsValid() then return false end
            if string.find(c:GetFullName(), "Sentinel", 1, true) then return false end
            return not c.HealthComponent:IsDeadOrDying()
        end)
        if ok and alive then return true end
    end
    return false
end
local function build_phase()
    local gs = FindFirstOf("RSTGameStateBase")
    if gs and valid(gs) then
        local ok, b = pcall(function() return gs:IsAnyBreakActive() end)
        if ok and type(b) == "boolean" then
            if b then return true end
            return false   -- a break can be read and none is active: a wave is running
        end
    end
    return not enemies_alive()
end
local building = true


-- ---------- v7: make the archer trap sellable like any trap ----------
local function cname(c) local ok, n = pcall(function() return c:GetFName():ToString() end); return ok and n or "?" end
local function addr(o) local ok, a = pcall(function() return o:GetAddress() end); return ok and a or nil end
local function parts_of(actor)
    local out, me = {}, addr(actor)
    for _, c in ipairs(FindAllOf("PrimitiveComponent") or {}) do
        local o = nil; pcall(function() o = c:GetOwner() end)
        if o and addr(o) == me then out[#out + 1] = c end
    end
    return out
end
local function coll(c)
    local i = {resp = {}}
    pcall(function() i.profile = c:GetCollisionProfileName():ToString() end)
    pcall(function() i.enabled = c:GetCollisionEnabled() end)
    pcall(function() i.objtype = c:GetCollisionObjectType() end)
    for ch = 0, 31 do pcall(function() i.resp[ch] = c:GetCollisionResponseToChannel(ch) end) end
    return i
end
local function coll_str(i)
    local r = {}
    for ch = 0, 31 do r[#r + 1] = tostring(i.resp[ch] or "?") end
    return string.format("profile %s, collision %s, type %s, responses %s", tostring(i.profile), tostring(i.enabled), tostring(i.objtype), table.concat(r, ""))
end
local function cls_name(a) local ok, n = pcall(function() return a:GetClass():GetFName():ToString() end); return ok and n or "?" end
local dumped = {}          -- trap class -> true (parts logged once per kind)
local donor = nil          -- part name -> collision info, from a normal (non-sentinel) trap
local function dump_trap(t, why)
    local cn = cls_name(t)
    if dumped[cn .. why] then return end
    dumped[cn .. why] = true
    w("parts of " .. cn .. " (" .. why .. "):")
    for _, c in ipairs(parts_of(t)) do
        local ccls = "?"; pcall(function() ccls = c:GetClass():GetFName():ToString() end)
        w("  " .. cname(c) .. " [" .. ccls .. "] " .. coll_str(coll(c)))
    end
end
local function take_donor(t)
    local d, n = {}, 0
    for _, c in ipairs(parts_of(t)) do d[cname(c)] = coll(c); n = n + 1 end
    if n > 0 then donor = d; w("sell setup taken from " .. cls_name(t) .. " (" .. n .. " parts)") end
end
local function copy_coll(c, i)
    pcall(function() c:SetCollisionProfileName(FName(i.profile), true) end)
    if i.objtype then pcall(function() c:SetCollisionObjectType(i.objtype) end) end
    for ch = 0, 31 do if i.resp[ch] then pcall(function() c:SetCollisionResponseToChannel(ch, i.resp[ch]) end) end end
    if i.enabled then pcall(function() c:SetCollisionEnabled(i.enabled) end) end
end
local function make_sellable(rec)
    local t = rec.trap
    pcall(function() t.bAllowInteraction = false end)
    local ic = get(t, "IteractCollision")
    if ic then pcall(function() ic:SetCollisionEnabled(0) end) end
    rec.sellfix = true; rec.fixed_with = donor
end
-- diagnostics: what the game's sell ability does
local hooked = {}
local function try_hook(key, path, fn)
    if hooked[key] then return end
    local ok = pcall(function() RegisterHook(path, fn) end)
    if ok then hooked[key] = true; w("hooked " .. key) end
end
local function hooks()
    -- (v12: no hooks on the game's own sell calls; they stopped normal traps from selling)
end

local sellreq = false
pcall(function() RegisterKeyBind(Key.DEL, function() sellreq = true end) end)
local function is_host()
    for _, gm in ipairs(FindAllOf("GameModeBase") or {}) do if valid(gm) then return true end end
    return false
end
-- sell the archer trap nearest to this player (within 4 m); host only (selling and coins are the server's)
local function sell_for(pc, ps, target)
    if not building then w("sell: not in the build phase, no selling during a wave"); return end
    local t = target
    if not t then
        local ok0, ploc = pcall(function() return pc.Pawn:K2_GetActorLocation() end)
        if not ok0 or not ploc then w("sell: player has no hero"); return end
        local bd = 400 * 400
        for _, a in ipairs(FindAllOf("BP_Sentinel_Archer_Trap_C") or {}) do
            if valid(a) and owned(a) then
                local d = dist2(a:K2_GetActorLocation(), ploc)
                if d < bd then t, bd = a, d end
            end
        end
    end
    if not t then w("sell: no archer trap within 4 m"); return end
    local refund = get(t, "RefundValue") or 0
    local rec = traps[t:GetAddress()]
    local coin0 = ps and get(ps, "Coin")
    local ok, r = pcall(function() return t:Sell() end)
    w("sell: Sell() -> " .. tostring(ok and r or ("error " .. tostring(r))) .. ", refund value " .. tostring(refund))
    if ok and r == true and ps and type(coin0) == "number" then
        local price = (refund and refund > 0) and refund or (get(get(t, "TrapDefinition") or {}, "PlacementCost") or 0)
        if price > 0 then table.insert(refunds, {ps = ps, coin0 = coin0, price = price, at = clock}) end
    end
    if not (ok and r == true) then
        -- fallback: pay back what the trap cost and remove it (and its archer, see the trap loop)
        local price = (refund and refund > 0) and refund or (get(get(t, "TrapDefinition") or {}, "PlacementCost") or 0)
        if ps and price > 0 then pcall(function() ps:GrantCoin(price, 0) end) end
        pcall(function() t:K2_DestroyActor() end)
        w("sell: removed the trap, paid back " .. tostring(price))
    end
    sold[t:GetAddress()] = clock
    if rec then
        rec.sold = true
        if valid(rec.archer) then pcall(function() rec.archer:K2_DestroyActor() end); w("sell: removed its archer") end
    end
end
-- Delete pressed here. On the host: sell at once. On the other player's PC: ask the host with a private chat message
-- ("!jwsell", RSTPlayerState:Server_AddPlayerChatMessage); the host's copy of this mod hooks that call.
local SELLTAG = "!jwsell"
local function sell_near()
    for _, pc in ipairs(FindAllOf("PlayerController") or {}) do
        local ok, lc = pcall(function() return pc:IsLocalController() end)
        if ok and lc then
            local ps = get(pc, "PlayerState")
            if is_host() then sell_for(pc, ps)
            else
                if not building then w("sell: not in the build phase, no selling during a wave"); return end
                local ok2, e = pcall(function() ps:Server_AddPlayerChatMessage(SELLTAG, 0, false, true) end)
                w("sell: asked the host" .. (ok2 and "" or (": failed " .. tostring(e))))
            end
            return
        end
    end
    w("sell: no local player")
end

-- v8: the trap you aim at (closest to the camera's line of sight, within 15 m in front, 2.5 m off the line)
local function local_pc()
    for _, pc in ipairs(FindAllOf("PlayerController") or {}) do
        local ok, lc = pcall(function() return pc:IsLocalController() end)
        if ok and lc then return pc end
    end
end
local function aimed_trap(pc)
    local cm = get(pc, "PlayerCameraManager")
    if not cm then return nil end
    local ok, loc = pcall(function() return cm:GetCameraLocation() end)
    local ok2, rot = pcall(function() return cm:GetCameraRotation() end)
    if not (ok and ok2 and loc and rot) then return nil end
    local p, y = math.rad(rot.Pitch), math.rad(rot.Yaw)
    local fx, fy, fz = math.cos(p) * math.cos(y), math.cos(p) * math.sin(y), math.sin(p)
    -- squared distance from the line of sight to a point (nil if behind or too far)
    local function off(pt)
        local dx, dy, dz = pt.X - loc.X, pt.Y - loc.Y, pt.Z - loc.Z
        local along = dx * fx + dy * fy + dz * fz
        if along <= 0 or along > 2500 then return nil end
        return dx * dx + dy * dy + dz * dz - along * along
    end
    local best, bs = nil, nil
    for _, t in ipairs(FindAllOf("RSTTrap") or {}) do
        if valid(t) and get(t, "bIsBeingPlaced") == false and get(t, "bIsSold") ~= true then
            local okl, o = pcall(function() return t:K2_GetActorLocation() end)
            if okl and o then
                local d = nil
                local function try(pt) local v = off(pt); if v and (not d or v < d) then d = v end end
                if string.find(cls_name(t), "Sentinel_Archer_Trap", 1, true) then
                    -- the plate and a column up to head height, at the trap and at its archer
                    for _, h in ipairs({0, 60, 120, 180, 240}) do try({X = o.X, Y = o.Y, Z = o.Z + h}) end
                    local rec = traps[t:GetAddress()]
                    if rec and valid(rec.archer) then
                        local oka, al = pcall(function() return rec.archer:K2_GetActorLocation() end)
                        if oka and al then for _, h in ipairs({-90, -30, 30, 90}) do try({X = al.X, Y = al.Y, Z = al.Z + h}) end end
                    end
                    if d and d < 160 * 160 then d = d * 0.25 else d = nil end      -- archer traps win ties
                else
                    try(o)
                    if d and d >= 200 * 200 then d = nil end
                end
                if d and (not bs or d < bs) then best, bs = t, d end
            end
        end
    end
    return best
end
local aimreq = false
local function sell_aimed()
    local pc = local_pc()
    if not pc then return end
    local t = aimed_trap(pc)
    if not t then w("sell button: not aiming at a trap"); return end
    local cn = cls_name(t)
    if not string.find(cn, "Sentinel_Archer_Trap", 1, true) then return end   -- another trap: the game sells it itself
    if not owned(t) then w("sell button: that archer trap isn't a player's"); return end
    w("sell button: aiming at an archer trap")
    if is_host() then sell_for(pc, get(pc, "PlayerState"), t)
    else
        if not building then w("sell: not in the build phase, no selling during a wave"); return end
        local ok2, e = pcall(function() get(pc, "PlayerState"):Server_AddPlayerChatMessage("!jwsell", 0, false, true) end)
        w("sell: asked the host" .. (ok2 and "" or (": failed " .. tostring(e))))
    end
end
local function sell_hooks()
    try_hook("SellPressed", "/Script/OMD4.RSTGameplayAbility_SellTrap:OnInputPressed", function(self, dur)
        w("game sell button pressed"); aimreq = true
    end)
end

local sellq = {}
do
    local ok, e = pcall(function()
        RegisterHook("/Script/OMD4.RSTPlayerState:Server_AddPlayerChatMessage", function(self, msg)
            pcall(function()
                if msg:get():ToString() ~= SELLTAG then return end
                local ps = self:get()
                local pc = ps:GetOwner()
                if pc:IsLocalController() then return end      -- the host's own Delete is handled directly
                if is_host() then table.insert(sellq, {pc = pc, ps = ps}) end
            end)
        end)
    end)
    w("hook Server_AddPlayerChatMessage (the other player's selling): " .. (ok and "ok" or tostring(e)))
end
local function every(ms, fn)
    -- on the game thread when this UE4SS has it (no Lua on the async thread: that crashed the referee)
    if LoopInGameThreadWithDelay then LoopInGameThreadWithDelay(ms, fn)
    else LoopAsync(ms, function() ExecuteInGameThread(fn); return false end) end
end

-- v9: the sell highlight while aiming at your archer trap in the build phase
local lit = nil
local hl_broken = false
local hl_said = false
local function unlight()
    if lit then
        if valid(lit) then pcall(function() lit:BP_SellableEnd() end); pcall(function() lit["Update Sell Visuals"](lit, false) end) end
        lit = nil
    end
end
every(200, function()
    local ok, err = pcall(function()
        local t = nil
        if building then
            local pc = local_pc()
            if pc then
                local a = aimed_trap(pc)
                if a and string.find(cls_name(a), "Sentinel_Archer_Trap", 1, true) and owned(a) then t = a end
            end
        end
        if t and lit and t:GetAddress() == lit:GetAddress() then return end
        unlight()
        if t and not hl_broken then
            local ok2, e = pcall(function() t:BP_SellableBegin() end)
            local ok3, e3 = pcall(function() t["Update Sell Visuals"](t, true) end)
            if ok2 or ok3 then
                lit = t
                if not hl_said then hl_said = true; w("sell highlight on (BP_SellableBegin " .. (ok2 and "ok" or tostring(e)) .. ", Update Sell Visuals " .. (ok3 and "ok" or tostring(e3)) .. ")") end
            else hl_broken = true; w("sell highlight failed (stopped trying): " .. tostring(e) .. " / " .. tostring(e3)) end
        end
    end)
    if not ok then w("highlight error: " .. tostring(err)) end
    return false
end)
every(500, function()
    clock = clock + 0.5
    do local ok, b = pcall(build_phase); if ok and b ~= building then building = b; w("build phase: " .. tostring(b)) end end
    if sellreq then sellreq = false; local ok, e = pcall(sell_near); if not ok then w("sell error: " .. tostring(e)) end end
    pcall(sell_hooks)
    for i = #refunds, 1, -1 do
        local q = refunds[i]
        if clock - q.at >= 1 then
            table.remove(refunds, i)
            local c = get(q.ps, "Coin")
            if type(c) == "number" and c < q.coin0 + q.price / 2 then
                local okg, e = pcall(function() q.ps:GrantCoin(q.price, 0) end)
                w("sell: the game paid nothing back, paid " .. q.price .. (okg and "" or (" FAILED " .. tostring(e))))
            else
                w("sell: the game paid the refund itself (coins " .. tostring(q.coin0) .. " -> " .. tostring(c) .. ")")
            end
        end
    end
    if aimreq then aimreq = false; local ok, e = pcall(sell_aimed); if not ok then w("sell error: " .. tostring(e)) end end
    while #sellq > 0 do local q = table.remove(sellq, 1); w("sell request from the other player"); local ok, e = pcall(sell_for, q.pc, q.ps); if not ok then w("sell error: " .. tostring(e)) end end
    do
        local ok, err = pcall(function()
            hooks()
            -- new player-placed traps
            for _, t in ipairs(FindAllOf("BP_Sentinel_Archer_Trap_C") or {}) do
                local id = t:GetAddress()
                if valid(t) and not traps[id] and not sold[id] and get(t, "bIsSold") ~= true and get(t, "bIsBeingPlaced") == false and owned(t) then
                    local rec = {trap = t, summoned_at = clock}; traps[id] = rec
                    w("placed archer trap (cost " .. tostring(get(t, "SummonCost")) .. ")")
                    if get(t, "HasCompletedSummon") ~= true then
                        pcall(function() t.CoinSpent = get(t, "SummonCost") or 0 end)
                        pcall(function() t.HasCompletedSummon = true end)
                        pcall(function() t:OnRep_HasCompletedSummon() end)
                        local ok2, e2 = pcall(function() t:ResummonSentinel() end)
                        w("  summoned: " .. (ok2 and "ok" or ("error " .. tostring(e2))))
                    end
                end
            end
            -- traps: keep sellable; sold/destroyed -> remove its archer
            for id, rec in pairs(traps) do
                if not valid(rec.trap) or rec.sold or get(rec.trap, "bIsSold") == true then
                    if valid(rec.trap) and not sold[id] then sold[id] = clock end
                    if valid(rec.archer) then pcall(function() rec.archer:K2_DestroyActor() end); w("trap gone, removed its archer") end
                    traps[id] = nil
                else
                    local want = not building
                    if get(rec.trap, "bPreventSell") ~= want then pcall(function() rec.trap.bPreventSell = want end) end
                    if not rec.sellfix and get(rec.trap, "HasCompletedSummon") == true then make_sellable(rec) end
                    if rec.archer and not valid(rec.archer) then rec.archer = nil; rec.summoned_at = clock end   -- died: wait for the respawn
                end
            end
            -- sold traps the game leaves standing: hide them at once, remove them after 3 s
            for id, at in pairs(sold) do
                local t = nil
                for _, a in ipairs(FindAllOf("BP_Sentinel_Archer_Trap_C") or {}) do if a:GetAddress() == id then t = a end end
                if not t or not valid(t) then sold[id] = nil
                else
                    pcall(function() t:SetActorHiddenInGame(true) end)
                    pcall(function() t:SetActorEnableCollision(false) end)
                    if clock - at >= 3 then pcall(function() t:K2_DestroyActor() end); w("removed a sold archer trap the game left standing"); sold[id] = nil end
                end
            end
            -- new archers: give each to the nearest of our traps that has none; extra copies of a fresh summon go
            for _, a in ipairs(FindAllOf("BP_Sentinel_Archer_C") or {}) do
                local aid = a:GetAddress()
                if valid(a) and not known[aid] then
                    known[aid] = true
                    local best, bd = nil, nil
                    for _, rec in pairs(traps) do
                        if valid(rec.trap) and not valid(rec.archer) then
                            local d = dist2(a:K2_GetActorLocation(), spawn_loc(rec.trap))
                            if not bd or d < bd then best, bd = rec, d end
                        end
                    end
                    if best then
                        w("archer -> trap (was " .. math.floor(math.sqrt(bd)) .. " away)"); pin(a, best)
                    else
                        local fresh = false
                        for _, rec in pairs(traps) do if clock - (rec.summoned_at or -99) < 4 then fresh = true end end
                        if fresh then pcall(function() a:K2_DestroyActor() end); w("removed an extra archer copy") end
                    end
                end
            end
            -- our archers stay put (and fall onto the floor, and turn to their targets)
            for _, rec in pairs(traps) do
                if valid(rec.archer) then hold(rec.archer) end
            end
        end)
        if not ok then w("error: " .. tostring(err)) end
    end
    return false
end)
