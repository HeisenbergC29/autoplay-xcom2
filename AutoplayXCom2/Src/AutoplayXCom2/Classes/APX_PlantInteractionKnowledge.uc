// Read-only discovery of actual PlantBomb interaction geometry. A future tile
// is a movement goal, never an injected native ability target or AA_Success.
class APX_PlantInteractionKnowledge extends Object
    dependson(XComWorldData, XGTacticalGameCoreNativeBase);

struct PlantGoalResult
{
    var bool bFound;
    var bool bConsumedObject;
    var TTile Tile;
    var int ObjectID;
    var string Reason;
};

static function bool FiniteCoordinate(float Value)
{
    return Value >= -100000000.0 && Value <= 100000000.0;
}

static function bool HasConsumedPlantInteraction(int CurrentCount,
    int StartingCount, int MaximumCount)
{
    // An unused object disabled by MaxInteractionCount=0 is not a planted bomb.
    return CurrentCount > Max(0, StartingCount) && MaximumCount >= 0
        && CurrentCount >= MaximumCount;
}

static function bool PlantObjectStateEligible(bool bEnabled, bool bBroken,
    bool bRemoved, bool bHacked, int CurrentCount, int MaximumCount)
{
    return bEnabled && !bBroken && !bRemoved && !bHacked
        && (MaximumCount < 0 || CurrentCount < MaximumCount);
}

static function int InteractionAnchorCoordinate(int PointCoordinate,
    int OccupiedCoordinate, int CurrentAnchorCoordinate)
{
    return PointCoordinate - (OccupiedCoordinate - CurrentAnchorCoordinate);
}

static function int PlantQueryProbeZ(int PointTileZ, int Probe)
{
    if (Probe == 1)
        return PointTileZ - 1;
    if (Probe == 2)
        return PointTileZ + 1;
    if (Probe == 3)
        return PointTileZ - 2;
    if (Probe == 4)
        return PointTileZ + 2;
    return PointTileZ;
}

// -1 means unknown, 0 pending, 1 completed. The empty set never means complete.
static function int NativePlantObjectivePhase(XComGameState_BattleData BattleData)
{
    local int Index;

    if (BattleData == none
        || BattleData.MapData.ActiveMission.sType != "SabotageTransmitter")
        return -1;
    for (Index = 0; Index < Min(64,
        BattleData.MapData.ActiveMission.MissionObjectives.Length); ++Index)
    {
        if (BattleData.MapData.ActiveMission.MissionObjectives[Index].ObjectiveName == 'PlantBomb')
            return BattleData.MapData.ActiveMission.MissionObjectives[Index].bCompleted ? 1 : 0;
    }
    return -1;
}

static function bool ContainsTile(const out array<TTile> Tiles, TTile Tile)
{
    local TTile Entry;
    foreach Tiles(Entry)
    {
        if (Entry == Tile)
            return true;
    }
    return false;
}

// Probe only the occupied tile that must contain this particular interaction.
// Native UnitInteractions performs the same query for each occupied cell.
static function bool NativePlantPointOnTile(XComGameState_InteractiveObject ObjectState,
    XComInteractiveLevelActor Visualizer, TTile QueryTile, out int RemainingQueries)
{
    local array<XComInteractPoint> Points;
    local XComInteractPoint Point;
    local vector Position;

    if (RemainingQueries <= 0 || `XWORLD == none)
        return false;
    --RemainingQueries;
    Position = `XWORLD.GetPositionFromTileCoordinates(QueryTile);
    `XWORLD.GetInteractionPoints(Position, 8.0, 90.0, Points);
    // Unknown crowded geometry is not accepted after an incomplete iteration.
    if (Points.Length > 32)
        return false;
    foreach Points(Point)
    {
        if (Point.InteractiveActor == Visualizer
            && ObjectState.IsLocationValidForInteraction(Point.Location))
            return true;
    }
    return false;
}

static function float GoalDistance(TTile Start, TTile Destination)
{
    local vector Delta;
    Delta.X = Start.X - Destination.X;
    Delta.Y = Start.Y - Destination.Y;
    Delta.Z = Start.Z - Destination.Z;
    return VSizeSq(Delta);
}

// These describe the last proven discovery stage, not a guessed game failure.
static function string PlantDiscoveryFailureReason(int PlantActors,
    int EligibleActors, int ReadyActors, int CachedPoints,
    int RegisteredPoints, int CandidateCount)
{
    if (PlantActors <= 0)
        return "no_native_plant_actor";
    if (EligibleActors <= 0)
        return "plant_actor_state_unavailable";
    if (ReadyActors <= 0)
        return "plant_interaction_blocked";
    if (CachedPoints <= 0)
        return "plant_actor_has_no_cached_points";
    if (RegisteredPoints <= 0)
        return "no_registered_plant_point";
    if (CandidateCount <= 0)
        return "no_compatible_plant_anchor";
    return "no_path_to_plant_anchor";
}

static function FindInteractionGoal(XComGameState_Unit UnitState,
    out PlantGoalResult Result)
{
    local PlantGoalResult EmptyResult;
    local XComGameState_InteractiveObject ObjectState;
    local XComInteractiveLevelActor Visualizer;
    local XComGameState_Ability Ability;
    local StateObjectReference AbilityRef;
    local array<TTile> Footprint, FutureFootprint, Candidates, FullPath;
    local array<int> CandidateObjectIDs, Tried;
    local XComInteractPoint Point;
    local TTile OccupiedTile, PointTile, QueryTile, Candidate;
    local int ObjectsChecked, PointsChecked, AnchorsChecked, RemainingQueries;
    local int PlantActors, EligibleActors, ReadyActors, RegisteredPoints;
    local int Cell, Index, BestIndex, PathChecks, Probe;
    local float Distance, BestDistance;

    Result = EmptyResult;
    Result.Reason = "no_native_plant_goal";
    if (UnitState == none || `XCOMHISTORY == none || `XWORLD == none)
        return;
    AbilityRef = UnitState.FindAbility('Interact_PlantBomb');
    Ability = XComGameState_Ability(`XCOMHISTORY.GetGameStateForObjectID(AbilityRef.ObjectID));
    if (Ability == none || Ability.OwnerStateObject.ObjectID != UnitState.ObjectID)
    {
        Result.Reason = "no_owned_plant_ability";
        return;
    }
    if (UnitState.UnitSize > 1)
        UnitState.GetVisibilityForLocation(UnitState.TileLocation, Footprint);
    else
        Footprint.AddItem(UnitState.TileLocation);
    if (Footprint.Length == 0 || Footprint.Length > 16)
    {
        Result.Reason = "unknown_unit_footprint";
        return;
    }
    RemainingQueries = 32;
    foreach `XCOMHISTORY.IterateByClassType(class'XComGameState_InteractiveObject', ObjectState)
    {
        // Bound inspected entries, including those rejected before matching.
        if (++ObjectsChecked > 128)
            break;
        if (ObjectState == none || ObjectState.bRemoved || ObjectState.bRemovedFromPlay)
            continue;
        // The ordinary-visibility mode may still use the mission's public
        // marker, but must not discover hidden actor sockets through history.
        if (!class'APX_FullIntel'.default.EnableFullIntel
            && !class'X2TacticalVisibilityHelpers'.static.CanXComSquadSeeTarget(ObjectState.ObjectID))
            continue;
        Visualizer = XComInteractiveLevelActor(ObjectState.GetVisualizer());
        if (Visualizer == none || Visualizer.bDeleteMe
            || Visualizer.ObjectID != ObjectState.ObjectID
            || Visualizer.InteractionAbilityTemplateName != 'Interact_PlantBomb')
            continue;
        ++PlantActors;
        if (HasConsumedPlantInteraction(ObjectState.InteractionCount,
            Visualizer.StartingInteractionCount, ObjectState.MaxInteractionCount))
        {
            Result.bConsumedObject = true;
            continue;
        }
        if (!PlantObjectStateEligible(ObjectState.IsEnabled, ObjectState.bBroken,
            ObjectState.bRemoved || ObjectState.bRemovedFromPlay, ObjectState.bHasBeenHacked,
            ObjectState.InteractionCount, ObjectState.MaxInteractionCount))
            continue;
        ++EligibleActors;
        if (!ObjectState.CanInteractNormally(UnitState))
            continue;
        ++ReadyActors;
        // This public native cache is discovery only. Confirm its point is
        // still registered in XWORLD before accepting any future anchor.
        foreach Visualizer.InteractPoints(Point)
        {
            if (++PointsChecked > 32 || RemainingQueries <= 0 || AnchorsChecked >= 64)
                break;
            if (Point.InteractiveActor != Visualizer
                || !FiniteCoordinate(Point.Location.X) || !FiniteCoordinate(Point.Location.Y)
                || !FiniteCoordinate(Point.Location.Z))
                continue;
            PointTile = `XWORLD.GetTileCoordinatesFromPosition(Point.Location);
            // Stock queries accept points within 90 world units vertically.
            // A socket's own tile may therefore be above/below the occupied
            // tile that supplies the real interaction query (64-unit floors).
            // Every nearby level must independently pass that native query.
            for (Probe = 0; Probe < 5 && RemainingQueries > 0 && AnchorsChecked < 64; ++Probe)
            {
                QueryTile = PointTile;
                QueryTile.Z = PlantQueryProbeZ(PointTile.Z, Probe);
                if (`XWORLD.IsTileOutOfRange(QueryTile)
                    || !NativePlantPointOnTile(ObjectState, Visualizer, QueryTile, RemainingQueries))
                    continue;
                ++RegisteredPoints;
                for (Cell = 0; Cell < Footprint.Length && AnchorsChecked < 64; ++Cell)
                {
                    ++AnchorsChecked;
                    // Reverse offsets from the verified QUERY tile. Using
                    // the socket's tile here would invent an airborne goal.
                    OccupiedTile = Footprint[Cell];
                    Candidate.X = InteractionAnchorCoordinate(QueryTile.X, OccupiedTile.X, UnitState.TileLocation.X);
                    Candidate.Y = InteractionAnchorCoordinate(QueryTile.Y, OccupiedTile.Y, UnitState.TileLocation.Y);
                    Candidate.Z = InteractionAnchorCoordinate(QueryTile.Z, OccupiedTile.Z, UnitState.TileLocation.Z);
                    if (`XWORLD.IsTileOutOfRange(Candidate) || ContainsTile(Candidates, Candidate))
                        continue;
                    FutureFootprint.Length = 0;
                    if (UnitState.UnitSize > 1)
                        UnitState.GetVisibilityForLocation(Candidate, FutureFootprint);
                    else
                        FutureFootprint.AddItem(Candidate);
                    if (FutureFootprint.Length == 0 || FutureFootprint.Length > 16
                        || !ContainsTile(FutureFootprint, QueryTile))
                        continue;
                    Candidates.AddItem(Candidate);
                    CandidateObjectIDs.AddItem(ObjectState.ObjectID);
                }
            }
        }
    }
    // A geometry-compatible anchor still needs a real path for this unit's
    // size. At most four full native paths are requested; later movement uses
    // the existing blue-path, hazard, support and exposure guards unchanged.
    while (PathChecks < 4 && Tried.Length < Candidates.Length)
    {
        BestIndex = INDEX_NONE;
        BestDistance = 1000000000.0;
        for (Index = 0; Index < Candidates.Length; ++Index)
        {
            if (Tried.Find(Index) != INDEX_NONE)
                continue;
            Distance = GoalDistance(UnitState.TileLocation, Candidates[Index]);
            if (BestIndex == INDEX_NONE || Distance < BestDistance)
            {
                BestIndex = Index;
                BestDistance = Distance;
            }
        }
        if (BestIndex == INDEX_NONE)
            break;
        Tried.AddItem(BestIndex);
        Candidate = Candidates[BestIndex];
        FullPath.Length = 0;
        ++PathChecks;
        if (Candidate == UnitState.TileLocation
            || (class'X2PathSolver'.static.BuildPath(UnitState, UnitState.TileLocation,
                Candidate, FullPath, false) && FullPath.Length > 1
                && FullPath[FullPath.Length - 1] == Candidate))
        {
            Result.bFound = true;
            Result.Tile = Candidate;
            Result.ObjectID = CandidateObjectIDs[BestIndex];
            Result.Reason = "native_plant_interaction_point";
            break;
        }
    }
    if (!Result.bFound)
    {
        Result.Reason = PlantDiscoveryFailureReason(PlantActors, EligibleActors,
            ReadyActors, PointsChecked, RegisteredPoints, Candidates.Length);
        if (ObjectsChecked > 128 && PlantActors == 0)
            Result.Reason = "plant_object_scan_limit";
        else if (PointsChecked > 32 && RegisteredPoints == 0)
            Result.Reason = "plant_cached_point_limit";
        else if (RemainingQueries <= 0 && RegisteredPoints == 0)
            Result.Reason = "plant_world_query_limit";
        else if (AnchorsChecked >= 64 && Candidates.Length == 0)
            Result.Reason = "plant_anchor_limit";
        else if (PathChecks >= 4 && Tried.Length < Candidates.Length)
            Result.Reason = "plant_path_limit";
        if (Result.bConsumedObject)
            Result.Reason = "plant_interaction_already_used";
    }
    `log("Native plant approach|unit=" $ UnitState.ObjectID
        $ "|objects_checked=" $ Min(ObjectsChecked, 128)
        $ "|point_entries=" $ Min(PointsChecked, 32)
        $ "|plant_actors=" $ PlantActors $ "|eligible_actors=" $ EligibleActors
        $ "|ready_actors=" $ ReadyActors $ "|registered_points=" $ RegisteredPoints
        $ "|world_queries=" $ (32 - RemainingQueries)
        $ "|anchors_checked=" $ AnchorsChecked $ "|path_checks=" $ PathChecks
        $ "|goal_found=" $ Result.bFound $ "|object=" $ Result.ObjectID
        $ "|reason=" $ Result.Reason, true, 'AutoplayXCom2');
}
