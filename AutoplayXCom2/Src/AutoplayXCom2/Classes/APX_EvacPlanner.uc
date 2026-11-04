// Plans the ordinary commander ability. Never creates an evac zone game state.
class APX_EvacPlanner extends Object
    config(AutoplayXCom2)
    dependson(X2GameRuleset, XComWorldData);

var config int MaxCandidateTiles;

static function bool PrimaryObjectivesCompleted()
{
    local XComGameState_BattleData BattleData;
    local int Index;
    local bool bHasStrategyObjective;

    BattleData = XComGameState_BattleData(`XCOMHISTORY.GetSingleGameStateObjectForClass(
        class'XComGameState_BattleData', true));
    if (BattleData == none || BattleData.bMissionAborted)
        return false;
    for (Index = 0; Index < BattleData.MapData.ActiveMission.MissionObjectives.Length; ++Index)
    {
        if (BattleData.MapData.ActiveMission.MissionObjectives[Index].bIsStrategyObjective)
        {
            bHasStrategyObjective = true;
            break;
        }
    }
    // The game's AllStrategyObjectivesCompleted returns true for an empty set.
    return bHasStrategyObjective && BattleData.AllStrategyObjectivesCompleted();
}

static function bool FindPlacementAction(XComGameState_Unit UnitState,
    out AvailableAction Action, out XComGameState_Ability Ability)
{
    local GameRulesCache_Unit UnitCache;
    local AvailableAction Candidate;

    if (!`TACTICALRULES.GetGameRulesCache_Unit(UnitState.GetReference(), UnitCache))
        return false;
    foreach UnitCache.AvailableActions(Candidate)
    {
        if (Candidate.AvailableCode != 'AA_Success' || !Candidate.bInputTriggered)
            continue;
        Ability = XComGameState_Ability(`XCOMHISTORY.GetGameStateForObjectID(
            Candidate.AbilityObjectRef.ObjectID));
        if (Ability == none || Ability.OwnerStateObject.ObjectID != UnitState.ObjectID
            || Ability.GetMyTemplateName() != 'PlaceEvacZone')
            continue;
        // This implementation supplies a cursor location, not an object target.
        // Reject an altered template whose targeting contract we do not know.
        if (!Candidate.bFreeAim || Candidate.AvailableTargets.Length > 1
            || (Candidate.AvailableTargets.Length == 1
                && (Candidate.AvailableTargets[0].PrimaryTarget.ObjectID != UnitState.ObjectID
                    || Candidate.AvailableTargets[0].AdditionalTargets.Length != 0))
            || X2AbilityTarget_Cursor(Ability.GetMyTemplate().AbilityTargetStyle) == none
            || Ability.GetMyTemplate().TargetingMethod != class'X2TargetingMethod_EvacZone')
            continue;
        Action = Candidate;
        return true;
    }
    return false;
}

static function bool AreaIsSafe(XComGameState_Unit UnitState, TTile Center)
{
    local TTile Minimum, Maximum, Tile;

    // The stock targeting method includes soldier occupancy and vertical
    // clearance. IncludeSoldiers=true rejects placement over squad members.
    if (!class'X2TargetingMethod_EvacZone'.static.ValidateEvacArea(Center, true))
        return false;
    class'XComGameState_EvacZone'.static.GetEvacMinMax2D(Center, Minimum, Maximum);
    Tile = Minimum;
    for (Tile.X = Minimum.X; Tile.X <= Maximum.X; ++Tile.X)
    {
        for (Tile.Y = Minimum.Y; Tile.Y <= Maximum.Y; ++Tile.Y)
        {
            if (class'APX_HazardKnowledge'.static.HasBlockingHazard(UnitState, Tile))
                return false;
        }
    }
    return true;
}

static function bool HasSafeBlueRoute(XComGameState_Unit UnitState,
    XGUnit UnitVisualizer, TTile Destination)
{
    local array<TTile> Path;
    local int Index;

    if (!UnitVisualizer.m_kReachableTilesCache.IsTileReachable(Destination)
        || UnitVisualizer.m_kReachableTilesCache.GetPathCostToTile(Destination)
            > UnitVisualizer.GetMobility()
        || !UnitVisualizer.m_kReachableTilesCache.BuildPathToTile(Destination, Path)
        || Path.Length < 2)
        return false;
    for (Index = 1; Index < Path.Length; ++Index)
    {
        if (class'APX_HazardKnowledge'.static.HasBlockingHazard(UnitState, Path[Index]))
            return false;
    }
    return true;
}

static function float SquadDistanceScore(XComGameState_Unit UnitState, TTile Destination)
{
    local XComGameState_Unit SquadUnit;
    local float Result;

    foreach `XCOMHISTORY.IterateByClassType(class'XComGameState_Unit', SquadUnit)
    {
        if (SquadUnit.GetTeam() == eTeam_XCom && SquadUnit.IsAlive()
            && !SquadUnit.bRemovedFromPlay && !SquadUnit.GetMyTemplate().bIsCosmetic
            && SquadUnit.GetAssociatedPlayerID() == UnitState.GetAssociatedPlayerID())
            Result -= class'APX_MissionPlanner'.static.TileDistance(
                SquadUnit.TileLocation, Destination);
    }
    return Result;
}

static function bool ChoosePlacement(XComGameState_Unit UnitState,
    out AvailableAction Action, out array<vector> Locations, out float Score)
{
    local XComGameState_Ability Ability;
    local XGUnit UnitVisualizer;
    local array<TTile> Tiles;
    local TTile CandidateTile, FloorTile;
    local vector CandidateLocation, SourceLocation, BestLocation;
    local float MaxRange, CandidateScore, BestScore;
    local int Index, Stride;
    local bool bFound;

    Locations.Length = 0;
    Score = 0.0;
    if (UnitState == none || `TACTICALRULES == none || !UnitState.IsAbleToAct()
        || UnitState.GetTeam() != eTeam_XCom
        || class'XComGameState_EvacZone'.static.GetEvacZone(eTeam_XCom) != none
        || !PrimaryObjectivesCompleted()
        || !FindPlacementAction(UnitState, Action, Ability))
        return false;

    UnitVisualizer = XGUnit(UnitState.GetVisualizer());
    if (UnitVisualizer == none || UnitVisualizer.m_kReachableTilesCache == none)
        return false;
    UnitVisualizer.m_kReachableTilesCache.UpdateTileCacheIfNeeded();
    UnitVisualizer.m_kReachableTilesCache.GetAllPathableTiles(Tiles, UnitVisualizer.GetMobility());
    MaxRange = Ability.GetAbilityCursorRangeMeters();
    SourceLocation = `XWORLD.GetPositionFromTileCoordinates(UnitState.TileLocation);
    Stride = Max(1, (Tiles.Length + Max(1, default.MaxCandidateTiles) - 1)
        / Max(1, default.MaxCandidateTiles));
    BestScore = -1000000.0;

    for (Index = 0; Index < Tiles.Length; Index += Stride)
    {
        CandidateTile = Tiles[Index];
        CandidateLocation = `XWORLD.GetPositionFromTileCoordinates(CandidateTile);
        if (!`XWORLD.GetFloorTileForPosition(CandidateLocation, FloorTile)
            || FloorTile != CandidateTile)
            continue;
        CandidateLocation.Z = `XWORLD.GetFloorZForPosition(CandidateLocation);
        if (MaxRange >= 0.0 && VSize(CandidateLocation - SourceLocation) > `METERSTOUNITS(MaxRange))
            continue;
        // Choose a known, currently visible area even when an altered cursor
        // template does not require squadsight. Never scout through this call.
        if (!class'X2TacticalVisibilityHelpers'.static.CanSquadSeeLocation(
            UnitState.ControllingPlayer.ObjectID, CandidateTile))
            continue;
        if (!AreaIsSafe(UnitState, CandidateTile)
            || !HasSafeBlueRoute(UnitState, UnitVisualizer, CandidateTile))
            continue;
        CandidateScore = SquadDistanceScore(UnitState, CandidateTile);
        if (!bFound || CandidateScore > BestScore)
        {
            bFound = true;
            BestScore = CandidateScore;
            BestLocation = CandidateLocation;
        }
    }

    if (!bFound)
        return false;
    Locations.AddItem(BestLocation);
    Score = 280.0;
    return true;
}
