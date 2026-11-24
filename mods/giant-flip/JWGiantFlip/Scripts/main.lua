-- JWGiantFlip v3: the Giant Flip Trap throws big enemies too (as in OMD3, where it flips even very heavy ones).
-- The game's Giant Flip ability (GA_FlipTrap_Big_Fire) has a MaxWeightClass (0 Light, 1 Heavy, 2 VeryHeavy,
-- 3 Immovable); enemies above it are not launched. This sets it to MAX_WEIGHT on the ability's class default and on
-- every live copy, and logs what the game had (also its launch multipliers per weight class).
-- Log: Binaries\Win64\JW_GiantFlip_log.txt
local BIN = "C:/Program Files (x86)/Steam/steamapps/common/Orcs Must Die Deathtrap/OMDD/Binaries/Win64/"
local MAX_WEIGHT = 2        -- VeryHeavy: ogres, trolls ... (3 would also throw bosses)
-- v2: big enemies are thrown less far (user: "a bit too easy, large orcs should be thrown less"). OMD3's Giant Flip
-- throws light 42 / heavy 12 / very heavy 4 squares; distance grows with the square of the launch speed, so the
-- speed multipliers are about sqrt(12/42) and sqrt(4/42) for heavy and very heavy.
local MULT = {[0] = 1.0, [1] = 0.55, [2] = 0.35, [3] = 0.2}
-- v3: settings file Mods\JWGiantFlip\settings.txt (the OMD Map Builder's Mods page can write it), read every 10 s:
--   max_weight = 0..3 (0 light only, 1 heavy, 2 very heavy, 3 also immovable/bosses)
--   light, heavy, veryheavy, immovable = launch speed in % per weight class (100 = the trap's full throw)
local SETTINGS = BIN .. "Mods/JWGiantFlip/settings.txt"
local last_settings = nil
local function read_settings()
    local f = io.open(SETTINGS, "r")
    local txt = f and f:read("*a") or ""
    if f then f:close() end
    if txt == last_settings then return false end
    last_settings = txt
    local t = {}
    for k, v in txt:gmatch("([%w_]+)%s*=%s*([%d%.]+)") do t[k] = tonumber(v) end
    if t.max_weight then MAX_WEIGHT = math.max(0, math.min(3, math.floor(t.max_weight))) end
    if t.light then MULT[0] = t.light / 100 end
    if t.heavy then MULT[1] = t.heavy / 100 end
    if t.veryheavy then MULT[2] = t.veryheavy / 100 end
    if t.immovable then MULT[3] = t.immovable / 100 end
    return true
end
local CDO = "/Game/Traps/FlipTrap/Abilities/GA_FlipTrap_Big_Fire.Default__GA_FlipTrap_Big_Fire_C"
local logfile = io.open(BIN .. "JW_GiantFlip_log.txt", "w")
local function log(s) if logfile then logfile:write(os.date("%H:%M:%S ") .. s .. "\n"); logfile:flush() end end
local function valid(o) return o ~= nil and pcall(function() return o:IsValid() end) and o:IsValid() end
local function str(f) local ok, v = pcall(f); if not ok then return "?" end; return tostring(v) end
log("JWGiantFlip v3 loaded: Giant Flip max weight class -> " .. MAX_WEIGHT)

local reported, done = false, {}
local function fix(o, what)
    local ok, cur = pcall(function() return o.MaxWeightClass end)
    if not ok then if not reported then log(what .. ": no MaxWeightClass (" .. tostring(cur) .. ")") end; return end
    local mults_ok = true
    pcall(function() o.WeightClassLaunchMultipliers:ForEach(function(k, v)
        local kk = k:get(); local want = MULT[kk]
        if want and math.abs(v:get() - want) > 0.001 then mults_ok = false; v:set(want) end
    end) end)
    if cur ~= MAX_WEIGHT or not mults_ok then
        local okw = pcall(function() o.MaxWeightClass = MAX_WEIGHT end)
        local a = str(function() return o:GetAddress() end)
        if not done[a] then
            done[a] = true
            local mult = {}
            pcall(function() o.WeightClassLaunchMultipliers:ForEach(function(k, v) mult[#mult + 1] = tostring(k:get()) .. "=" .. tostring(v:get()) end) end)
            log(string.format("%s: max weight class %s -> %s%s; launch velocity %s; multipliers now {%s}", what, tostring(cur), tostring(MAX_WEIGHT),
                okw and "" or " (FAILED)", str(function() return o.CharacterLaunchVelocity end), table.concat(mult, ", ")))
        end
    end
end

local tick = 0
local function step()
    tick = tick + 1
    if tick % 5 == 1 and read_settings() then
        done = {}
        log(string.format("settings%s: max weight class %d, launch %%: light %d, heavy %d, very heavy %d, immovable %d",
            last_settings == "" and " (none, defaults)" or "", MAX_WEIGHT, math.floor(MULT[0] * 100 + 0.5), math.floor(MULT[1] * 100 + 0.5),
            math.floor(MULT[2] * 100 + 0.5), math.floor(MULT[3] * 100 + 0.5)))
    end
    local c = StaticFindObject(CDO)
    if valid(c) then fix(c, "class default") ; reported = true end
    for _, a in ipairs(FindAllOf("GA_FlipTrap_Big_Fire_C") or {}) do
        if valid(a) and not a:GetFullName():find("Default__", 1, true) then fix(a, "placed Giant Flip") end
    end
end
LoopInGameThreadWithDelay(2000, function() local ok, e = pcall(step); if not ok then log("error " .. tostring(e)) end; return false end)
