-- JWArcherGrant: one time, gives the profile 1 gold skull so the Guardian Archer can be bought in the hub.
-- Skips if the trap is already owned. Writes Binaries/Win64/JW_ARCHER_GRANTED when done, then never runs again.
local BIN = "C:/Program Files (x86)/Steam/steamapps/common/Orcs Must Die Deathtrap/OMDD/Binaries/Win64/"
local DONE, LOG = BIN .. "JW_ARCHER_GRANTED", BIN .. "JW_ArcherGrant.txt"
local ITEM = "/Game/Traps/GuardianArcher/DA_GuardianArcher_InventoryItem.DA_GuardianArcher_InventoryItem"
local f0 = io.open(DONE, "r"); if f0 then f0:close(); print("[JWArcherGrant] already done\n"); return end
local function w(s) local f = io.open(LOG, "a"); if f then f:write(os.date("%H:%M:%S ") .. s .. "\n"); f:close() end; print("[JWArcherGrant] " .. s .. "\n") end
local tries = 0
LoopAsync(3000, function()
    tries = tries + 1
    if tries > 400 then w("gave up (no profile found)"); return true end
    local finished = false
    ExecuteInGameThread(function()
        local ok, err = pcall(function()
            local profile
            for _, p in ipairs(FindAllOf("RSTPlayerProfile") or {}) do
                if p:IsValid() and not p:GetFullName():find("Default__") then profile = p; break end
            end
            if not profile then return end
            local item = StaticFindObject(ITEM)
            if item and item:IsValid() and profile:IsInventoryItemOwned(item) then
                w("Guardian Archer already owned, nothing to do"); finished = true; return
            end
            local before = profile:GetGoldSkulls()
            profile:GrantGoldSkulls(1)
            w("granted 1 gold skull (" .. tostring(before) .. " -> " .. tostring(profile:GetGoldSkulls()) .. ")")
            pcall(function() profile:AsyncSaveGameToSlotForLocalPlayer() end)
            finished = true
        end)
        if not ok then w("error: " .. tostring(err)) end
        if finished then local f = io.open(DONE, "w"); if f then f:write("1"); f:close() end end
    end)
    return finished
end)
