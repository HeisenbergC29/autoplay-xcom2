// Explicit user-authorized omniscience for locally controlled XCOM.
// Do not bypass native targeting, AP consumption, hit rolls, or path legality.
class APX_FullIntel extends Object config(AutoplayXCom2);

var config bool EnableFullIntel;

// Visual FOW is not the same as tactical state visibility. The planner
// receives live enemy positions from read-only history when mode is enabled.
static function GetKnownEnemies(XComGameState_Unit SourceUnit,
    out array<StateObjectReference> Enemies)
{
    local XComGameState_Unit Enemy;

    Enemies.Length = 0;
    if (SourceUnit == none || `XCOMHISTORY == none || `XWORLD == none
        || `TACTICALRULES == none)
        return;

    if (!default.EnableFullIntel)
    {
        class'X2TacticalVisibilityHelpers'.static.GetAllVisibleEnemiesForPlayer(
            SourceUnit.ControllingPlayer.ObjectID, Enemies);
        return;
    }

    if (SourceUnit.GetTeam() != eTeam_XCom
        || SourceUnit.GetAssociatedPlayerID() != `TACTICALRULES.GetLocalClientPlayerObjectID())
        return;

    foreach `XCOMHISTORY.IterateByClassType(class'XComGameState_Unit', Enemy)
    {
        if (Enemy == none || Enemy.ObjectID == SourceUnit.ObjectID
            || !Enemy.IsAlive() || Enemy.IsIncapacitated()
            || Enemy.bRemovedFromPlay || Enemy.IsCivilian()
            || Enemy.GetMyTemplate() == none || Enemy.GetMyTemplate().bIsCosmetic
            || Enemy.GetMyTemplateName() == 'HostileVIPCivilian'
            || !SourceUnit.IsEnemyUnit(Enemy)
            || `XWORLD.IsTileOutOfRange(Enemy.TileLocation)
            || class'APX_CombatPlanner'.static.IsReclaimableControlledSquadmate(
                SourceUnit, Enemy))
            continue;
        Enemies.AddItem(Enemy.GetReference());
    }
}

// Only planning uses fog-independent tile knowledge. Actual movement/attack
// submission still uses native path caches and available action target lists.
static function bool CanPlanAtTile(XComGameState_Unit UnitState, TTile Tile)
{
    if (UnitState == none || `XWORLD == none || `XWORLD.IsTileOutOfRange(Tile))
        return false;
    if (default.EnableFullIntel)
        return true;
    return class'X2TacticalVisibilityHelpers'.static.CanSquadSeeLocation(
        UnitState.ControllingPlayer.ObjectID, Tile);
}

// These are stock visual-FOW APIs; they do not grant native attack targeting.
static function bool RevealMapForPlayer()
{
    if (!default.EnableFullIntel || `XWORLD == none || `BATTLE == none
        || `BATTLE.GetALocalPlayerController() == none)
        return false;
    `XWORLD.InitializeAllViewersToHaveSeenFog(true);
    if (`XWORLD.bEnableFOW)
        `BATTLE.SetFOW(false);
    return true;
}
