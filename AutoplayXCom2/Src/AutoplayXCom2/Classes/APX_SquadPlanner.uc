// Bounded concealed-ambush preparation using stock player-visible previews.
// This planner never transfers units to an AI player or runs an enemy tree.
class APX_SquadPlanner extends Object config(AutoplayXCom2)
    dependson(X2GameRuleset, X2TacticalGameRulesetDataStructures,
        X2GameRulesetVisibilityDataStructures, XGTacticalGameCoreNativeBase);

var config int MaxCandidateTiles;
var config int MaxPreparationActionsPerTurn;

struct AmbushPreparation
{
    var XComGameState_Unit UnitState;
    var AvailableAction Action;
    var int TargetIndex;
    var array<TTile> Path;
    var float Score;
    var bool bMove;
    var bool bFound;
};

static function bool CanPrepare(bool bSquadConcealed, bool bOffensive,
    int PreparationCount, int PreparationLimit)
{
    return bSquadConcealed && bOffensive && PreparationCount < PreparationLimit;
}

static function bool CanStageMove(int StandardAP, int ReactionCost, bool bUsefulShot)
{
    return StandardAP >= 2 && StandardAP > ReactionCost && !bUsefulShot;
}

static function float PreparationScore(bool bMove, bool bUsefulShot, bool bFiringLane)
{
    if (bMove)
        return 30.0;
    if (bUsefulShot || bFiringLane)
        return 25.0;
    return -10000.0;
}

static function float CatchupProgress(float CurrentDistance, float CandidateDistance,
    float CurrentRisk, float CandidateRisk, float SupportDistance)
{
    // A rear soldier may be too far to gain LOS in one blue move. Let them
    // close a material gap before the opener reveals the squad, keeping 1 AP.
    if (CurrentDistance <= FMax(4.0, SupportDistance))
        return -10000.0;
    if (CurrentDistance - CandidateDistance < 2.0 || CandidateRisk > CurrentRisk)
        return -10000.0;
    return FMin(12.0, (CurrentDistance - CandidateDistance) * 2.0);
}

static function bool DetectedOnTile(bool bClearLOS, float DistanceSquared,
    float SightRadius, float DetectionRadius, bool bIgnoresDetectionDistance)
{
    if (!bClearLOS || DistanceSquared > SightRadius * SightRadius)
        return false;
    return bIgnoresDetectionDistance || DistanceSquared <= DetectionRadius * DetectionRadius;
}

static function bool IsLocalSoldier(XComGameState_Unit UnitState, int PlayerID)
{
    return UnitState != none && UnitState.GetAssociatedPlayerID() == PlayerID
        && UnitState.GetTeam() == eTeam_XCom && UnitState.IsAlive()
        && !UnitState.IsIncapacitated() && !UnitState.IsCivilian()
        && !UnitState.GetMyTemplate().bIsCosmetic && !UnitState.bRemovedFromPlay;
}

static function bool SquadIsConcealed(int PlayerID)
{
    local XComGameState_Unit Soldier;
    local int Count;

    foreach `XCOMHISTORY.IterateByClassType(class'XComGameState_Unit', Soldier)
    {
        if (!IsLocalSoldier(Soldier, PlayerID))
            continue;
        ++Count;
        if (!Soldier.IsSquadConcealed())
            return false;
    }
    return Count > 1;
}

static function bool HasUsefulShot(XComGameState_Unit Soldier)
{
    local GameRulesCache_Unit Cache;
    local AvailableAction Candidate;
    local AvailableTarget Target;
    local XComGameState_Ability Ability;
    local XComGameState_Unit Enemy;
    local ShotBreakdown Breakdown;
    local array<StateObjectReference> VisibleEnemies;
    local name AbilityName;

    if (!`TACTICALRULES.GetGameRulesCache_Unit(Soldier.GetReference(), Cache))
        return false;
    class'APX_MissionPlanner'.static.GetVisibleThreats(Soldier, VisibleEnemies);
    foreach Cache.AvailableActions(Candidate)
    {
        if (Candidate.AvailableCode != 'AA_Success' || !Candidate.bInputTriggered || Candidate.bFreeAim)
            continue;
        Ability = XComGameState_Ability(`XCOMHISTORY.GetGameStateForObjectID(Candidate.AbilityObjectRef.ObjectID));
        if (Ability == none)
            continue;
        AbilityName = Ability.GetMyTemplateName();
        if (AbilityName != 'StandardShot' && AbilityName != 'PistolStandardShot' && AbilityName != 'SniperStandardFire')
            continue;
        foreach Candidate.AvailableTargets(Target)
        {
            Enemy = XComGameState_Unit(`XCOMHISTORY.GetGameStateForObjectID(Target.PrimaryTarget.ObjectID));
            if (class'APX_CombatPlanner'.static.IsVisibleHostile(Soldier, Enemy, VisibleEnemies)
                && Ability.GetShotBreakdown(Target, Breakdown) >= 35)
                return true;
        }
    }
    return false;
}

static function bool FindOverwatch(XComGameState_Unit Soldier,
    out AvailableAction Action, out int TargetIndex, out int PointCost)
{
    local GameRulesCache_Unit Cache;
    local AvailableAction Candidate;
    local XComGameState_Ability Ability;
    local X2AbilityCost Cost;
    local X2AbilityCost_ActionPoints APCost;
    local int SelfIndex, CostPoints;

    PointCost = 100;
    TargetIndex = INDEX_NONE;
    if (!`TACTICALRULES.GetGameRulesCache_Unit(Soldier.GetReference(), Cache))
        return false;
    foreach Cache.AvailableActions(Candidate)
    {
        if (Candidate.AvailableCode != 'AA_Success' || !Candidate.bInputTriggered || Candidate.bFreeAim)
            continue;
        Ability = XComGameState_Ability(`XCOMHISTORY.GetGameStateForObjectID(Candidate.AbilityObjectRef.ObjectID));
        if (Ability == none || Ability.GetMyTemplate() == none
            || class'APX_CombatPlanner'.default.OverwatchAbilities.Find(Ability.GetMyTemplateName()) == INDEX_NONE)
            continue;
        SelfIndex = class'APX_CombatPlanner'.static.FindSelfTarget(Candidate, Soldier.ObjectID);
        if (Candidate.AvailableTargets.Length > 0 && SelfIndex == INDEX_NONE)
            continue;
        CostPoints = 1;
        foreach Ability.GetMyTemplate().AbilityCosts(Cost)
        {
            APCost = X2AbilityCost_ActionPoints(Cost);
            if (APCost != none)
                CostPoints = Max(CostPoints, APCost.GetPointCost(Ability, Soldier));
        }
        if (CostPoints < PointCost)
        {
            Action = Candidate;
            TargetIndex = SelfIndex;
            PointCost = CostPoints;
        }
    }
    return PointCost < 100;
}

static function bool IsDestructiveTraversal(name TraversalName)
{
    return TraversalName == 'eTraversal_BreakWindow' || TraversalName == 'eTraversal_KickDoor'
        || TraversalName == 'eTraversal_BreakWall' || TraversalName == 'eTraversal_Phasing';
}

static function bool PreparationPathIsSafe(XComGameState_Unit Soldier,
    const out array<TTile> Path)
{
    local array<PathPoint> Points;
    local PathPoint Point;
    local array<StateObjectReference> VisibleObjects;
    local StateObjectReference DetectorRef;
    local XComGameState_Unit Detector;
    local XComGameState_InteractiveObject DetectionObject;
    local GameRulesCache_VisibilityInfo Visibility;
    local TTile Tile, DetectorTile;
    local vector TilePosition, DetectorPosition;
    local int Index;
    local float DetectionDistance, SightDistance, StartSupport;
    local string ConcealmentReason;

    if (Soldier == none || Path.Length < 2)
        return false;
    StartSupport = class'APX_MissionPlanner'.static.NearestSupportDistance(Soldier, Soldier.TileLocation);
    class'X2PathSolver'.static.GetPathPointsFromPath(Soldier, Path, Points);
    if (Points.Length < 2)
        return false;
    foreach Points(Point)
    {
        if (Soldier.IsConcealed()
            && `XCOMHISTORY.GetSingleGameStateObjectForClass(
                class'XComGameState_ChallengeData', true) == none
            && IsDestructiveTraversal(name(string(Point.Traversal))))
            return false;
    }
    // Only currently visible objects can contribute detection positions. This
    // also includes visible civilians and security devices which can reveal a
    // concealed soldier. Do not enumerate hidden objects to get their ranges.
    if (Soldier.IsConcealed())
        class'X2TacticalVisibilityHelpers'.static.GetAllVisibleObjectsForPlayer(
            Soldier.GetAssociatedPlayerID(), VisibleObjects, , -1, true);
    for (Index = 1; Index < Path.Length; ++Index)
    {
        Tile = Path[Index];
        if (!class'APX_MissionPlanner'.static.IsKnownCombatTile(Tile)
            || !class'X2TacticalVisibilityHelpers'.static.CanSquadSeeLocation(Soldier.GetAssociatedPlayerID(), Tile)
            || class'APX_HazardKnowledge'.static.HasBlockingHazard(Soldier, Tile)
            || Tile.Z > Soldier.TileLocation.Z + 1
            || !class'APX_MissionPlanner'.static.IsSupportedAdvanceStep(StartSupport,
                class'APX_MissionPlanner'.static.NearestSupportDistance(Soldier, Tile)))
            return false;
        foreach VisibleObjects(DetectorRef)
        {
            DetectionObject = XComGameState_InteractiveObject(`XCOMHISTORY.GetGameStateForObjectID(DetectorRef.ObjectID));
            if (DetectionObject != none && !DetectionObject.bRemovedFromPlay
                && !DetectionObject.bHasBeenHacked && DetectionObject.DetectionRange > 0.0)
            {
                TilePosition = `XWORLD.GetPositionFromTileCoordinates(Tile);
                DetectorTile = DetectionObject.TileLocation;
                DetectorPosition = `XWORLD.GetPositionFromTileCoordinates(DetectorTile);
                if (VSizeSq(TilePosition - DetectorPosition) <= Square(DetectionObject.DetectionRange))
                    return false;
            }
            Detector = XComGameState_Unit(`XCOMHISTORY.GetGameStateForObjectID(DetectorRef.ObjectID));
            if (Detector == none || !Detector.IsAlive() || Detector.GetMyTemplate().bIsCosmetic
                || !Soldier.UnitBreaksConcealment(Detector))
                continue;
            DetectorTile = Detector.TileLocation;
            if (!`XWORLD.CanSeeTileToTile(DetectorTile, Tile, Visibility))
                continue;
            SightDistance = `METERSTOUNITS(Detector.GetVisibilityRadius());
            DetectionDistance = Soldier.GetConcealmentDetectionDistance(Detector);
            if (DetectedOnTile(true, Visibility.DefaultTargetDist, SightDistance,
                DetectionDistance, Detector.DoesUnitBreaksConcealmentIgnoringDistance()))
                return false;
        }
    }
    // Shared estimator adds full-intel hostile positions and SDK exceptions
    // (e.g. Infiltration vs interactive detectors). This is an ambush/loot
    // preparation guard, not a force-reveal or history manipulation.
    if (Soldier.IsConcealed()
        && class'APX_ConcealmentPlanner'.static.PathRisksRevealing(
            Soldier, Path, ConcealmentReason))
        return false;
    return true;
}

static function bool HasFiringLane(XComGameState_Unit Soldier, TTile Tile,
    const out array<StateObjectReference> VisibleEnemies)
{
    local XComGameState_Unit Enemy;
    local StateObjectReference EnemyRef;
    local GameRulesCache_VisibilityInfo Visibility;
    local TTile EnemyTile;
    local float SightDistance;

    SightDistance = `METERSTOUNITS(Soldier.GetVisibilityRadius());
    foreach VisibleEnemies(EnemyRef)
    {
        Enemy = XComGameState_Unit(`XCOMHISTORY.GetGameStateForObjectID(EnemyRef.ObjectID));
        if (!class'APX_CombatPlanner'.static.IsVisibleHostile(Soldier, Enemy, VisibleEnemies))
            continue;
        EnemyTile = Enemy.TileLocation;
        if (`XWORLD.CanSeeTileToTile(Tile, EnemyTile, Visibility)
            && Visibility.DefaultTargetDist <= Square(SightDistance))
            return true;
    }
    return false;
}

// Preparing a shot while concealed must still leave a reasonable position
// after the opener reveals the squad. This is a bounded planner allowance,
// not a claim about native hit probability or unseen enemy intentions.
static function bool PreparationRiskAllowed(float CurrentRisk, float CandidateRisk)
{
    return CandidateRisk <= FMax(0.0, CurrentRisk) + FMax(6.0, CurrentRisk * 0.25);
}

static function bool ChoosePreparationMove(XComGameState_Unit Soldier, XComGameState_Unit Opener,
    const out array<StateObjectReference> VisibleEnemies, out array<TTile> Path)
{
    local XGUnit Visualizer;
    local array<TTile> Tiles, CandidatePath, RoutePath;
    local array<float> MeleeThreatReaches, ThreatWeights;
    local TTile Tile, OpenerTile;
    local int Index, Sample, SampleCount;
    local float Cost, Value, BestValue, CurrentSupport;
    local float CurrentDistance, CandidateDistance, CurrentRisk, CandidateRisk, CatchupValue;
    local bool bFiringLane, bBestFiringLane;

    Path.Length = 0;
    if (Soldier.NumActionPoints() < 2 || !class'APX_MissionPlanner'.static.HasLegalMove(Soldier))
        return false;
    Visualizer = XGUnit(Soldier.GetVisualizer());
    if (Visualizer == none || Visualizer.m_kReachableTilesCache == none)
        return false;
    Visualizer.m_kReachableTilesCache.UpdateTileCacheIfNeeded();
    Visualizer.m_kReachableTilesCache.GetAllPathableTiles(Tiles, Visualizer.GetMobility());
    OpenerTile = Opener.TileLocation;
    // Include a route prefix toward the known friendly opener so bounded
    // sampling cannot omit every catch-up point behind a corner. The ordinary
    // route is only a proposal: concealment/path checks below still apply.
    if (class'APX_MissionPlanner'.static.ChooseRoutePrefix(Soldier, Visualizer, OpenerTile, RoutePath))
        Tiles.InsertItem(0, RoutePath[RoutePath.Length - 1]);
    SampleCount = Min(Tiles.Length, Clamp(default.MaxCandidateTiles, 1, 128));
    BestValue = -100000.0;
    CurrentSupport = class'APX_MissionPlanner'.static.NearestSupportDistance(Soldier, Soldier.TileLocation);
    CurrentDistance = class'APX_MissionPlanner'.static.TileDistance(Soldier.TileLocation, OpenerTile);
    class'APX_MissionPlanner'.static.GetMeleeThreatReaches(Soldier, VisibleEnemies, MeleeThreatReaches);
    class'APX_MissionPlanner'.static.GetThreatWeights(Soldier, VisibleEnemies, ThreatWeights);
    CurrentRisk = class'APX_MissionPlanner'.static.ExposureRisk(
        Soldier, Soldier.TileLocation, VisibleEnemies, MeleeThreatReaches, ThreatWeights);
    for (Sample = 0; Sample < SampleCount; ++Sample)
    {
        Index = Sample * Max(0, Tiles.Length - 1) / Max(1, SampleCount - 1);
        Tile = Tiles[Index];
        Cost = Visualizer.m_kReachableTilesCache.GetPathCostToTile(Tile);
        if (Tile == Soldier.TileLocation || Cost < 0.0 || Cost > Visualizer.GetMobility()
            || Tile.Z > Soldier.TileLocation.Z + 1
            || !class'APX_MissionPlanner'.static.IsSupportedAdvanceDestination(CurrentSupport,
                class'APX_MissionPlanner'.static.NearestSupportDistance(Soldier, Tile)))
            continue;
        CandidateRisk = class'APX_MissionPlanner'.static.ExposureRisk(
            Soldier, Tile, VisibleEnemies, MeleeThreatReaches, ThreatWeights);
        if (!PreparationRiskAllowed(CurrentRisk, CandidateRisk))
            continue;
        bFiringLane = HasFiringLane(Soldier, Tile, VisibleEnemies);
        if (!bFiringLane && bBestFiringLane)
            continue;
        CatchupValue = 0.0;
        if (!bFiringLane)
        {
            CandidateDistance = class'APX_MissionPlanner'.static.TileDistance(Tile, OpenerTile);
            CatchupValue = CatchupProgress(CurrentDistance, CandidateDistance, CurrentRisk,
                CandidateRisk, class'APX_MissionPlanner'.default.SquadSupportDistance);
            if (CatchupValue < 0.0)
                continue;
        }
        Value = class'APX_MissionPlanner'.static.PositionScore(Soldier, Tile, Tile, true, VisibleEnemies, MeleeThreatReaches, ThreatWeights) - Cost * 0.25;
        Value += CatchupValue;
        // Prefer an established line whenever both kinds of safe move exist.
        if (bFiringLane == bBestFiringLane && Value <= BestValue)
            continue;
        CandidatePath.Length = 0;
        if (!Visualizer.m_kReachableTilesCache.BuildPathToTile(Tile, CandidatePath)
            || !PreparationPathIsSafe(Soldier, CandidatePath))
            continue;
        BestValue = Value;
        bBestFiringLane = bFiringLane;
        Path = CandidatePath;
    }
    return Path.Length > 1;
}

// Keep the result struct private to this class's compilation boundary. The
// controller uses stock types, as the other planners do, so it does not need
// a DependsOn edge to another mod class just to parse a local declaration.
static function bool ChoosePreparation(int PlayerID, XComGameState_Unit Opener,
    out XComGameState_Unit PreparedUnit, out AvailableAction PreparedAction,
    out int PreparedTargetIndex, out array<TTile> PreparedPath, out float PreparedScore)
{
    local XComGameState_Unit Soldier;
    local array<StateObjectReference> VisibleEnemies;
    local AmbushPreparation Preparation, Candidate, EmptyPreparation;
    local AvailableAction OverwatchAction, EmptyAction;
    local array<TTile> PreparationPath;
    local int PointCost, SelfIndex;
    local bool bUsefulShot;

    PreparedUnit = none;
    PreparedAction = EmptyAction;
    PreparedTargetIndex = INDEX_NONE;
    PreparedPath.Length = 0;
    PreparedScore = -10000.0;
    Preparation = EmptyPreparation;
    if (Opener == none || !SquadIsConcealed(PlayerID))
        return false;
    class'APX_MissionPlanner'.static.GetVisibleThreats(Opener, VisibleEnemies);
    if (VisibleEnemies.Length == 0)
        return false;
    foreach `XCOMHISTORY.IterateByClassType(class'XComGameState_Unit', Soldier)
    {
        if (!IsLocalSoldier(Soldier, PlayerID) || Soldier.ObjectID == Opener.ObjectID
            || !Soldier.IsAbleToAct() || Soldier.NumAllReserveActionPoints() > 0
            || Soldier.NumActionPoints() == 0)
            continue;
        Candidate = EmptyPreparation;
        if (!FindOverwatch(Soldier, OverwatchAction, SelfIndex, PointCost))
            continue;
        Candidate.Action = OverwatchAction;
        Candidate.TargetIndex = SelfIndex;
        Candidate.UnitState = Soldier;
        bUsefulShot = HasUsefulShot(Soldier);
        if (CanStageMove(Soldier.NumActionPoints(), PointCost, bUsefulShot)
            && ChoosePreparationMove(Soldier, Opener, VisibleEnemies, PreparationPath))
        {
            Candidate.Path = PreparationPath;
            Candidate.bMove = true;
        }
        Candidate.Score = PreparationScore(Candidate.bMove, bUsefulShot,
            HasFiringLane(Soldier, Soldier.TileLocation, VisibleEnemies));
        if (Candidate.Score < 0.0)
            continue;
        Candidate.bFound = true;
        if (!Preparation.bFound || Candidate.Score > Preparation.Score)
            Preparation = Candidate;
    }
    if (!Preparation.bFound)
        return false;
    PreparedUnit = Preparation.UnitState;
    PreparedAction = Preparation.Action;
    PreparedTargetIndex = Preparation.TargetIndex;
    PreparedPath = Preparation.Path;
    PreparedScore = Preparation.Score;
    return true;
}
