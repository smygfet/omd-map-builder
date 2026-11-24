-- JWTrapBarricadeGrant v3: once, gives the profile 1 gold skull so the Trap Barricade can be bought in the hub
-- (v1 bug: the "done" check ran only at start, so it granted a skull every 3 s), and logs what the game sees of the
-- new trap: is the item loaded, is its identifier tag valid, does the asset manager know it (the trap book lists
-- purchasable items from the asset manager). Compared with the Guardian Archer, which works.
-- Log: Binaries\Win64\JW_TrapBarricadeGrant.txt
local BIN = "C:/Program Files (x86)/Steam/steamapps/common/Orcs Must Die Deathtrap/OMDD/Binaries/Win64/"
local DONE, LOG = BIN .. "JW_TRAPBARRICADE_GRANTED", BIN .. "JW_TrapBarricadeGrant.txt"
local ITEMS = {
    {"Trap Barricade", "/Game/Traps/TrapBarricade/DA_TrapBarricade_InventoryItem", "DA_TrapBarricade_InventoryItem"},
    {"Guardian Archer", "/Game/Traps/GuardianArcher/DA_GuardianArcher_InventoryItem", "DA_GuardianArcher_InventoryItem"},
    {"Rift Barricade", "/Game/Traps/Barricade/BP/DA_Rift_Barricade_InventoryItem", "DA_Rift_Barricade_InventoryItem"},
}
local function w(s) local f = io.open(LOG, "a"); if f then f:write(os.date("%H:%M:%S ") .. s .. "\n"); f:close() end; print("[JWTrapBarricadeGrant] " .. s .. "\n") end
local function done() local f = io.open(DONE, "r"); if f then f:close(); return true end; return false end
local function valid(o) return o ~= nil and pcall(function() return o:IsValid() end) and o:IsValid() end
local function str(f) local ok, v = pcall(f); if not ok then return "error: " .. tostring(v) end; return tostring(v) end

local function report(profile)
    w("---- what the game sees (v3) ----")
    local ksl = StaticFindObject("/Script/Engine.Default__KismetSystemLibrary")
    local gtl = StaticFindObject("/Script/GameplayTags.Default__BlueprintGameplayTagLibrary")
    -- every package of the Trap Barricade: does it load?
    for _, n in ipairs({"DA_TrapBarricade_Definition", "DA_TrapBarricade_AbilitySet", "DT_TrapBarricade_Attributes", "DA_TrapBarricade_InventoryItem"}) do
        local pkg = "/Game/Traps/TrapBarricade/" .. n
        local o = StaticFindObject(pkg .. "." .. n)
        if not valid(o) then pcall(function() LoadAsset(pkg) end); o = StaticFindObject(pkg .. "." .. n) end
        local extra = ""
        if valid(o) and n == "DA_TrapBarricade_Definition" then extra = ", cost " .. str(function() return o.PlacementCost end) end
        w(string.format("package %s: %s%s", n, valid(o) and "LOADS" or "does NOT load", extra))
    end
    for _, it in ipairs(ITEMS) do
        local name, pkg, obj = it[1], it[2], it[3]
        local full = pkg .. "." .. obj
        local item = StaticFindObject(full)
        local loaded_now = false
        if not valid(item) then pcall(function() LoadAsset(pkg) end); item = StaticFindObject(full); loaded_now = true end
        if not valid(item) then w(name .. ": item NOT FOUND (" .. full .. ")")
        else
            local tag = str(function() return item.Identifier.TagName:ToString() end)
            local tagok = str(function() return gtl:IsGameplayTagValid(item.Identifier) end)
            local purch = str(function() return item.bPurchasable end)
            local owned = str(function() return profile:IsInventoryItemOwned(item) end)
            local pid = str(function()
                local id = ksl:GetPrimaryAssetIdFromObject(item)
                return id.PrimaryAssetType.Name:ToString() .. ":" .. id.PrimaryAssetName:ToString()
            end)
            local inst = str(function() return item.InstanceClass:GetFullName() end)
            w(string.format("%s: found%s, identifier tag '%s' valid %s, purchasable %s, owned %s, primary asset id %s, instance class %s",
                name, loaded_now and " (loaded by me)" or " (already loaded)", tag, tagok, purch, owned, pid, inst))
        end
    end
end

if done() then w("skull already granted earlier; only reporting") end
local tries, reported = 0, false
LoopAsync(3000, function()
    tries = tries + 1
    if tries > 400 then w("gave up (no profile found)"); return true end
    if reported and done() then return true end
    ExecuteInGameThread(function()
        local ok, err = pcall(function()
            local profile
            for _, p in ipairs(FindAllOf("RSTPlayerProfile") or {}) do
                if p:IsValid() and not p:GetFullName():find("Default__") then profile = p; break end
            end
            if not profile then return end
            if not reported then reported = true; report(profile) end
            if done() then return end
            local f = io.open(DONE, "w"); if f then f:write("1"); f:close() end      -- marked BEFORE granting: never twice
            local item = StaticFindObject(ITEMS[1][2] .. "." .. ITEMS[1][3])
            if valid(item) and profile:IsInventoryItemOwned(item) then w("Trap Barricade already owned, no skull"); return end
            local before = profile:GetGoldSkulls()
            profile:GrantGoldSkulls(1)
            w("granted 1 gold skull (" .. tostring(before) .. " -> " .. tostring(profile:GetGoldSkulls()) .. ")")
            pcall(function() profile:AsyncSaveGameToSlotForLocalPlayer() end)
        end)
        if not ok then w("error: " .. tostring(err)) end
    end)
    return false
end)
