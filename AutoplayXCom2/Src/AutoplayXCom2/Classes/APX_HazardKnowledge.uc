// Public world-tile hazards are distinct from statuses already on a soldier.
// These helpers never query poison in fog or inspect an unseen enemy source.
class APX_HazardKnowledge extends Object;

static function bool PoisonCloudIsHarmful(bool bContainsPoison, bool bRobotic,
    bool bImmuneToPoison)
{
    return bContainsPoison && !bRobotic && !bImmuneToPoison;
}

static function bool MayCrossStartingPoison(bool bStartedInPoison,
    bool bAlreadyReachedCleanTile, bool bStepInPoison, bool bOtherHazard)
{
    // Only a continuous prefix of the starting cloud may be crossed to leave
    // it. The caller must separately require a clean final destination.
    return bStartedInPoison && !bAlreadyReachedCleanTile
        && bStepInPoison && !bOtherHazard;
}

static function bool IsKnownPoisonCloudAtTile(XComGameState_Unit UnitState, TTile Tile)
{
    local XComWorldData WorldData;

    if (UnitState == none)
        return false;
    // Our current tile is public even during temporary visibility changes.
    // Query other tiles only after confirming current squad visibility.
    if (Tile != UnitState.TileLocation
        && !class'X2TacticalVisibilityHelpers'.static.CanSquadSeeLocation(
            UnitState.GetAssociatedPlayerID(), Tile))
        return false;
    WorldData = `XWORLD;
    if (WorldData == none)
        return false;
    return WorldData.TileContainsPoison(Tile);
}

static function bool IsHarmfulPoisonCloudAtTile(XComGameState_Unit UnitState, TTile Tile)
{
    if (!IsKnownPoisonCloudAtTile(UnitState, Tile))
        return false;
    // CreatePoisonedStatusEffect excludes robots and tags its damage Poison.
    // Existing Poisoned is not immunity: its duplicate response is Refresh.
    return PoisonCloudIsHarmful(true, UnitState.IsRobotic(),
        UnitState.IsImmuneToDamage('Poison'));
}

static function bool NeedsPoisonEscape(XComGameState_Unit UnitState)
{
    if (UnitState == none)
        return false;
    return IsHarmfulPoisonCloudAtTile(UnitState, UnitState.TileLocation);
}

static function bool HasBlockingHazard(XComGameState_Unit UnitState, TTile Tile)
{
    if (UnitState == none)
        return true;
    // Keep the native guard for all other hazard types. The explicit public
    // cloud check also applies when this soldier is already poisoned.
    return class'XComPath'.static.TileContainsHazard(UnitState, Tile)
        || IsHarmfulPoisonCloudAtTile(UnitState, Tile);
}

static function bool CanCrossStartingPoisonTile(XComGameState_Unit UnitState,
    TTile Tile, bool bAlreadyReachedCleanTile)
{
    local XComWorldData WorldData;

    if (bAlreadyReachedCleanTile || !NeedsPoisonEscape(UnitState)
        || !IsHarmfulPoisonCloudAtTile(UnitState, Tile))
        return false;
    // The harmful-poison check has already gated this tile on squad visibility.
    // Never waive a fire/acid check just because poison also covers the tile.
    WorldData = `XWORLD;
    if (WorldData == none)
        return false;
    return MayCrossStartingPoison(true, bAlreadyReachedCleanTile, true,
        WorldData.TileContainsFire(Tile) || WorldData.TileContainsAcid(Tile));
}
