// Search the player's unexplored floor grid, never hidden unit positions.
class APX_ExplorationPlanner extends Object config(AutoplayXCom2)
    dependson(X2GameRulesetVisibilityDataStructures, XGTacticalGameCoreNativeBase);

var config int GridSpacing;
var config int MaxMapSamples;
var config int MaxSamplesPerDecision;
var config int MaxFrontiers;
var config int MaxPathAttempts;
var config int MaxPathLength;
var config int MaxRememberedFailures;
var config int MaxTrackedUnits;

struct ExplorationGoal
{
    var int UnitID;
    var TTile Tile;
    var bool bActive;
};

struct FailedExplorationGoal
{
    var int UnitID;
    var TTile Tile;
};

var private array<TTile> Frontiers;
var private array<ExplorationGoal> Goals;
var private array<FailedExplorationGoal> Failures;
var private array<int> EligibleUnitIDs;
var private int OwnerPlayerID;
var private bool bInitialized;
var private TTile MinimumTile;
var private int MapNumX;
var private int MapNumY;
var private int MapNumZ;
var private int ScanSpacing;
var private int ScanSizeX;
var private int ScanSizeY;
var private int ScanCount;
var private int ScanCursor;
var private int LastWorldRebuild;
var private int LastPlayerTurn;

// A blue-range path can still consume the LAST action. Reserve another normal
// AP before entering fog, so a newly revealed patrol can be answered this turn.
static function bool CanSpendExplorationAP(int ActionPoints, bool bThreats)
{
    return ActionPoints >= 2 && !bThreats;
}

static function bool CanExplore(XComGameState_Unit UnitState)
{
    if (UnitState == none || !UnitState.IsAbleToAct() || UnitState.IsCivilian()
        || UnitState.GetMyTemplate().bIsCosmetic
        || !CanSpendExplorationAP(UnitState.NumActionPoints(),
            class'APX_MissionPlanner'.static.HasCombatThreats(UnitState)))
        return false;
    return class'APX_MissionPlanner'.static.HasLegalMove(UnitState);
}

static function float ScoreExplorationMove(float CurrentCohesion, float CandidateCohesion)
{
    // Catching up acts before stretching the formation. Keep all exploration
    // below the 25-point mission-route priority and above idle overwatch.
    return 15.0 + FClamp(CandidateCohesion - CurrentCohesion, -6.0, 8.0);
}

// The controller must wait for another decision while a bounded scan is still
// running, rather than report no plan after examining only the first map slice.
function bool HasPendingSearch()
{
    if (!bInitialized)
        return false;
    RefreshRoster(OwnerPlayerID);
    if (EligibleUnitIDs.Length == 0)
        return false;
    PruneFrontiers();
    return ScanCursor < ScanCount || Frontiers.Length > 0;
}

// Only locally controlled friendlies are considered. No enemy location/state
// is inspected; the roster prevents one unit from discarding another's route.
function RefreshRoster(int PlayerID)
{
    local XComGameState_Unit UnitState;
    EligibleUnitIDs.Length = 0;
    foreach `XCOMHISTORY.IterateByClassType(class'XComGameState_Unit', UnitState)
    {
        if (UnitState.GetAssociatedPlayerID() == PlayerID
            && UnitState.GetTeam() == eTeam_XCom && CanExplore(UnitState))
        {
            EligibleUnitIDs.AddItem(UnitState.ObjectID);
            if (EligibleUnitIDs.Length >= Clamp(MaxTrackedUnits, 1, 128))
                return;
        }
    }
}

function bool InitializeIfNeeded()
{
    local XComWorldData World;
    local XComGameState_Player PlayerState;
    local int SampleLimit, PlayerTurn;

    World = `XWORLD;
    if (World == none || World.NumX <= 0 || World.NumY <= 0 || World.NumZ <= 0)
        return false;
    PlayerState = XComGameState_Player(`XCOMHISTORY.GetGameStateForObjectID(OwnerPlayerID));
    PlayerTurn = PlayerState != none ? PlayerState.PlayerTurnCount : INDEX_NONE;
    if (bInitialized && MapNumX == World.NumX && MapNumY == World.NumY
        && MapNumZ == World.NumZ)
    {
        // A new turn can make another soldier available; destruction can open
        // a route. Re-sample previously rejected cells in either case instead
        // of permanently discarding a cell rejected by just this turn's roster.
        if (LastWorldRebuild != World.NumRebuilds || LastPlayerTurn != PlayerTurn)
        {
            ScanCursor = 0;
            Frontiers.Length = 0;
            Failures.Length = 0;
            LastWorldRebuild = World.NumRebuilds;
            LastPlayerTurn = PlayerTurn;
        }
        return true;
    }

    MapNumX = World.NumX;
    MapNumY = World.NumY;
    MapNumZ = World.NumZ;
    MinimumTile = World.GetTileCoordinatesFromPosition(World.WorldBounds.Min);
    World.ClampTile(MinimumTile);
    ScanSpacing = Clamp(GridSpacing, 1, 32);
    SampleLimit = Max(MapNumZ, Clamp(MaxMapSamples, 64, 65536));
    // All height slices participate. Increase only XY spacing on large maps.
    do
    {
        ScanSizeX = (MapNumX + ScanSpacing - 1) / ScanSpacing;
        ScanSizeY = (MapNumY + ScanSpacing - 1) / ScanSpacing;
        ScanCount = ScanSizeX * ScanSizeY * MapNumZ;
        if (ScanCount > SampleLimit)
            ++ScanSpacing;
    }
    until (ScanCount <= SampleLimit);

    ScanCursor = 0;
    Frontiers.Length = 0;
    Goals.Length = 0;
    Failures.Length = 0;
    LastWorldRebuild = World.NumRebuilds;
    LastPlayerTurn = PlayerTurn;
    bInitialized = true;
    return true;
}

function bool IsUnexploredFloor(TTile Tile)
{
    local FOWTileStatus FogStatus;
    local byte GameplayFlags;
    local CachedCoverAndPeekData CoverData;
    local TTile VisibilityTile;

    if (`XWORLD.IsTileOutOfRange(Tile)
        || !`XWORLD.IsFloorTileAndValidDestination(Tile))
        return false;
    // Match the stock pawn's visibility check height instead of assuming that
    // the floor voxel is also the unit's eye/peek visibility voxel.
    CoverData = `XWORLD.GetCachedCoverAndPeekData(Tile);
    VisibilityTile = Tile;
    if (CoverData.bDefaultTileValid != 0)
        VisibilityTile = CoverData.DefaultVisibilityCheckTile;
    `XWORLD.GetTileFOWValue(VisibilityTile, FogStatus, GameplayFlags);
    return FogStatus == eFOWTileStatus_NeverSeen;
}

function bool IsReserved(TTile Tile)
{
    local int Index;
    for (Index = 0; Index < Goals.Length; ++Index)
    {
        if (Goals[Index].bActive && Goals[Index].Tile == Tile)
            return true;
    }
    return false;
}

function SampleFrontiers()
{
    local TTile Tile;
    local int FlatIndex, Samples;

    PruneFrontiers();
    Samples = Clamp(MaxSamplesPerDecision, 1, 2048);
    // Do not advance beyond a full queue: doing so would silently skip the
    // unsampled remainder of the map. Failed goals are pruned after the roster
    // has tried them, so an unreachable queue cannot block the scan forever.
    while (Samples > 0 && ScanCursor < ScanCount
        && Frontiers.Length < Clamp(MaxFrontiers, 1, 256))
    {
        FlatIndex = ScanCursor;
        ++ScanCursor;
        --Samples;
        Tile.X = MinimumTile.X + (FlatIndex % ScanSizeX) * ScanSpacing;
        FlatIndex = FlatIndex / ScanSizeX;
        Tile.Y = MinimumTile.Y + (FlatIndex % ScanSizeY) * ScanSpacing;
        Tile.Z = MinimumTile.Z + FlatIndex / ScanSizeY;
        if (IsUnexploredFloor(Tile) && !IsReserved(Tile))
            Frontiers.AddItem(Tile);
    }
}

function bool AllEligibleUnitsRejected(TTile Tile)
{
    local int Index;
    if (EligibleUnitIDs.Length == 0)
        return false;
    for (Index = 0; Index < EligibleUnitIDs.Length; ++Index)
    {
        if (!WasRejected(EligibleUnitIDs[Index], Tile))
            return false;
    }
    return true;
}

function PruneFrontiers()
{
    local int Index, FrontierIndex, OtherIndex;
    local bool bKeepFailure;
    // A soldier who spent their AP, became incapacitated or left the mission
    // must not reserve the only route for all remaining soldiers. Return a
    // dormant reservation to the shared queue when space is available. When
    // full, retaining it until a later pass is preferable to losing the cell.
    for (Index = 0; Index < Goals.Length; ++Index)
    {
        if (Goals[Index].bActive && EligibleUnitIDs.Find(Goals[Index].UnitID) == INDEX_NONE
            && Frontiers.Length < Clamp(MaxFrontiers, 1, 256))
        {
            Goals[Index].bActive = false;
            bKeepFailure = false;
            for (OtherIndex = 0; OtherIndex < Frontiers.Length; ++OtherIndex)
                bKeepFailure = bKeepFailure || Frontiers[OtherIndex] == Goals[Index].Tile;
            if (!bKeepFailure && IsUnexploredFloor(Goals[Index].Tile))
                Frontiers.AddItem(Goals[Index].Tile);
        }
    }
    for (Index = Frontiers.Length - 1; Index >= 0; --Index)
    {
        if (!IsUnexploredFloor(Frontiers[Index]) || IsReserved(Frontiers[Index])
            || AllEligibleUnitsRejected(Frontiers[Index]))
            Frontiers.Remove(Index, 1);
    }
    // Historical failures for discarded/finished cells no longer need space.
    // Keep only queued or assigned cells so a bounded history retains every
    // queued goal's rejection set until the last eligible unit has tried it.
    for (Index = Failures.Length - 1; Index >= 0; --Index)
    {
        bKeepFailure = IsReserved(Failures[Index].Tile);
        for (FrontierIndex = 0; FrontierIndex < Frontiers.Length && !bKeepFailure; ++FrontierIndex)
            bKeepFailure = Frontiers[FrontierIndex] == Failures[Index].Tile;
        if (!bKeepFailure || EligibleUnitIDs.Find(Failures[Index].UnitID) == INDEX_NONE)
            Failures.Remove(Index, 1);
    }
}

function int GetUnitGoalIndex(int UnitID)
{
    local ExplorationGoal Goal;
    local int Index;
    for (Index = 0; Index < Goals.Length; ++Index)
    {
        if (Goals[Index].UnitID == UnitID)
            return Index;
    }
    if (Goals.Length >= Clamp(MaxTrackedUnits, 1, 128))
        Goals.Remove(0, 1);
    Goal.UnitID = UnitID;
    Goals.AddItem(Goal);
    return Goals.Length - 1;
}

function bool WasRejected(int UnitID, TTile Tile)
{
    local int Index;
    for (Index = 0; Index < Failures.Length; ++Index)
    {
        if (Failures[Index].UnitID == UnitID && Failures[Index].Tile == Tile)
            return true;
    }
    return false;
}

function RejectGoal(int UnitID, TTile Tile)
{
    local FailedExplorationGoal Failure;
    local int Index, FailureLimit;
    if (WasRejected(UnitID, Tile))
        return;
    // Retain at least one failure per queued frontier/roster pair. A smaller
    // ring could forget early attempts before every friendly gets a chance,
    // allowing an unreachable full queue to retry forever.
    FailureLimit = Max(Clamp(MaxRememberedFailures, 1, 65536),
        (Clamp(MaxFrontiers, 1, 256) + Clamp(MaxTrackedUnits, 1, 128))
        * Clamp(MaxTrackedUnits, 1, 128));
    if (Failures.Length >= FailureLimit)
        Failures.Remove(0, 1);
    Failure.UnitID = UnitID;
    Failure.Tile = Tile;
    Failures.AddItem(Failure);
    // A SPARK's size or a temporary obstruction can make a goal unreachable
    // for one soldier while another can reach it. Preserve the shared candidate.
    if (Frontiers.Length < Clamp(MaxFrontiers, 1, 256))
    {
        for (Index = 0; Index < Frontiers.Length; ++Index)
        {
            if (Frontiers[Index] == Tile)
                return;
        }
        Frontiers.AddItem(Tile);
    }
}

function bool AssignNextGoal(XComGameState_Unit UnitState, int GoalIndex)
{
    local int Index, BestIndex;
    local float Distance, BestDistance, Value;

    BestIndex = INDEX_NONE;
    BestDistance = 1000000.0;
    for (Index = 0; Index < Frontiers.Length; ++Index)
    {
        if (WasRejected(UnitState.ObjectID, Frontiers[Index]))
            continue;
        Distance = class'APX_MissionPlanner'.static.TileDistance(
            UnitState.TileLocation, Frontiers[Index]);
        // A stale fog voxel at the current floor cannot yield a movement path.
        // Record the rejection so it cannot keep a full frontier queue pending
        // forever. Adjacent cells remain valid exploration destinations.
        if (Distance <= 0.1)
        {
            RejectGoal(UnitState.ObjectID, Frontiers[Index]);
            continue;
        }
        // Among similarly close frontiers, prefer the squad's direction over
        // a private unexplored corner on the opposite side of the map.
        Value = Distance - 0.5 * class'APX_MissionPlanner'.static.SquadPositionScore(
            UnitState, Frontiers[Index]);
        if (Value < BestDistance)
        {
            BestIndex = Index;
            BestDistance = Value;
        }
    }
    if (BestIndex == INDEX_NONE)
        return false;
    Goals[GoalIndex].Tile = Frontiers[BestIndex];
    Goals[GoalIndex].bActive = true;
    Frontiers.Remove(BestIndex, 1);
    return true;
}

function bool BuildSafeBluePrefix(XComGameState_Unit UnitState,
    TTile GoalTile, out array<TTile> Path)
{
    local XGUnit UnitVisualizer;
    local array<TTile> FullPath, CandidatePath;
    local int Index, PathIndex;
    local float Cost, StartSupport, CandidateValue, BestValue;
    local bool bSafe;

    Path.Length = 0;
    StartSupport = class'APX_MissionPlanner'.static.NearestSupportDistance(UnitState, UnitState.TileLocation);
    BestValue = -1000000.0;
    UnitVisualizer = XGUnit(UnitState.GetVisualizer());
    if (UnitVisualizer == none || UnitVisualizer.m_kReachableTilesCache == none)
        return false;
    UnitVisualizer.m_kReachableTilesCache.UpdateTileCacheIfNeeded();
    if (!class'X2PathSolver'.static.BuildPath(UnitState,
        UnitState.TileLocation, GoalTile, FullPath, false)
        || FullPath.Length > Clamp(MaxPathLength, 16, 8192))
        return false;
    for (Index = FullPath.Length - 1; Index > 0; --Index)
    {
        if (!UnitVisualizer.m_kReachableTilesCache.IsTileReachable(FullPath[Index]))
            continue;
        Cost = UnitVisualizer.m_kReachableTilesCache.GetPathCostToTile(FullPath[Index]);
        if (Cost < 0.0 || Cost > UnitVisualizer.GetMobility())
            continue;
        if (!class'APX_MissionPlanner'.static.IsSupportedAdvanceDestination(StartSupport,
            class'APX_MissionPlanner'.static.NearestSupportDistance(UnitState, FullPath[Index])))
            continue;
        CandidatePath.Length = 0;
        if (!UnitVisualizer.m_kReachableTilesCache.BuildPathToTile(FullPath[Index], CandidatePath)
            || CandidatePath.Length < 2)
            continue;
        bSafe = true;
        // Leaving a hazardous starting tile is allowed; entering hazards is not.
        for (PathIndex = 1; PathIndex < CandidatePath.Length; ++PathIndex)
        {
            if (class'APX_HazardKnowledge'.static.HasBlockingHazard(UnitState, CandidatePath[PathIndex])
                || !class'APX_MissionPlanner'.static.IsSupportedAdvanceStep(StartSupport,
                    class'APX_MissionPlanner'.static.NearestSupportDistance(UnitState, CandidatePath[PathIndex])))
            {
                bSafe = false;
                break;
            }
        }
        if (bSafe)
        {
            CandidateValue = class'APX_MissionPlanner'.static.AdvanceEndpointScore(float(Index),
                class'APX_MissionPlanner'.static.AdvanceCoverLevel(UnitState, FullPath[Index], GoalTile));
            CandidateValue += class'APX_MissionPlanner'.static.SquadPositionScore(UnitState, FullPath[Index]);
            if (CandidateValue > BestValue)
            {
                BestValue = CandidateValue;
                Path = CandidatePath;
            }
        }
    }
    return Path.Length > 1;
}

function bool ChooseMove(XComGameState_Unit UnitState,
    out array<TTile> Path, out float Score)
{
    local int GoalIndex, Attempt;

    Path.Length = 0;
    Score = 0.0;
    if (!CanExplore(UnitState))
        return false;
    OwnerPlayerID = UnitState.GetAssociatedPlayerID();
    if (!InitializeIfNeeded())
        return false;
    RefreshRoster(OwnerPlayerID);
    // The tracking bound must also bound assignments; otherwise a unit beyond
    // the roster cap could keep evicting another soldier's active reservation.
    if (EligibleUnitIDs.Find(UnitState.ObjectID) == INDEX_NONE)
        return false;
    SampleFrontiers();
    GoalIndex = GetUnitGoalIndex(UnitState.ObjectID);
    if (Goals[GoalIndex].bActive && !IsUnexploredFloor(Goals[GoalIndex].Tile))
        Goals[GoalIndex].bActive = false;

    for (Attempt = 0; Attempt < Clamp(MaxPathAttempts, 1, 16); ++Attempt)
    {
        if (!Goals[GoalIndex].bActive && !AssignNextGoal(UnitState, GoalIndex))
            return false;
        if (BuildSafeBluePrefix(UnitState, Goals[GoalIndex].Tile, Path))
        {
            Score = ScoreExplorationMove(
                class'APX_MissionPlanner'.static.SquadPositionScore(UnitState, UnitState.TileLocation),
                class'APX_MissionPlanner'.static.SquadPositionScore(UnitState, Path[Path.Length - 1]));
            return true;
        }
        RejectGoal(UnitState.ObjectID, Goals[GoalIndex].Tile);
        Goals[GoalIndex].bActive = false;
    }
    return false;
}
