-- JWGiantFlipGrant v2 (logs when the game itself loads the item, e.g. when the trap book opens; LoadAsset of a
-- mod package doesn't work from here, so v1's "NOT FOUND" meant nothing): once, gives the profile 1 gold skull so the Giant Flip Trap can be bought in the hub,
-- and logs whether the game sees the new item. Log: Binaries\Win64\JW_GiantFlipGrant.txt
local BIN = "C:/Program Files (x86)/Steam/steamapps/common/Orcs Must Die Deathtrap/OMDD/Binaries/Win64/"
local DONE, LOG = BIN .. "JW_GIANTFLIP_GRANTED", BIN .. "JW_GiantFlipGrant.txt"
local PKG, OBJ = "/Game/Traps/GiantFlip/DA_GiantFlip_InventoryItem", "DA_GiantFlip_InventoryItem"
local function w(s) local f = io.open(LOG, "a"); if f then f:write(os.date("%H:%M:%S ") .. s .. "\n"); f:close() end; print("[JWGiantFlipGrant] " .. s .. "\n") end
local function done() local f = io.open(DONE, "r"); if f then f:close(); return true end; return false end
local function valid(o) return o ~= nil and pcall(function() return o:IsValid() end) and o:IsValid() end
local function str(f) local ok, v = pcall(f); if not ok then return "error: " .. tostring(v) end; return tostring(v) end

local function item()
    local it = StaticFindObject(PKG .. "." .. OBJ)
    if not valid(it) then pcall(function() LoadAsset(PKG) end); it = StaticFindObject(PKG .. "." .. OBJ) end
    return valid(it) and it or nil
end

local function report(profile)
    local it = item()
    if not it then w("Giant Flip Trap item NOT FOUND"); return end
    local gtl = StaticFindObject("/Script/GameplayTags.Default__BlueprintGameplayTagLibrary")
    local def = StaticFindObject("/Game/Traps/FlipTrap/BP/DA_FlipTrap_Big_Definition.DA_FlipTrap_Big_Definition")
    w(string.format("Giant Flip Trap item: found, tag '%s' valid %s, purchasable %s, owned %s, price %s",
        str(function() return it.Identifier.TagName:ToString() end), str(function() return gtl:IsGameplayTagValid(it.Identifier) end),
        str(function() return it.bPurchasable end), str(function() return profile:IsInventoryItemOwned(it) end),
        valid(def) and str(function() return def.PlacementCost end) or "?"))
end

local tries, reported, seen = 0, false, false
local function watch()
    if seen then return end
    for _, o in ipairs(FindAllOf("RSTInventoryItemDefinition") or {}) do
        if valid(o) and o:GetFullName():find(OBJ, 1, true) and not o:GetFullName():find("Default__", 1, true) then
            seen = true
            w("the game loaded the Giant Flip Trap item: purchasable " .. str(function() return o.bPurchasable end) ..
              ", name '" .. str(function() return o.DisplayName:ToString() end) .. "'")
        end
    end
end
LoopAsync(3000, function()
    tries = tries + 1
    if tries > 400 then w("gave up"); return true end
    if reported and done() and seen then return true end
    ExecuteInGameThread(function()
        local ok, err = pcall(function()
            local profile
            for _, p in ipairs(FindAllOf("RSTPlayerProfile") or {}) do
                if p:IsValid() and not p:GetFullName():find("Default__") then profile = p; break end
            end
            if not profile then return end
            pcall(watch)
            if not reported then reported = true; report(profile) end
            if done() then return end
            local f = io.open(DONE, "w"); if f then f:write("1"); f:close() end      -- marked BEFORE granting: never twice
            local it = item()
            if it and profile:IsInventoryItemOwned(it) then w("Giant Flip Trap already owned, no skull"); return end
            local before = profile:GetGoldSkulls()
            profile:GrantGoldSkulls(1)
            w("granted 1 gold skull (" .. tostring(before) .. " -> " .. tostring(profile:GetGoldSkulls()) .. ")")
            pcall(function() profile:AsyncSaveGameToSlotForLocalPlayer() end)
        end)
        if not ok then w("error: " .. tostring(err)) end
    end)
    return false
end)
