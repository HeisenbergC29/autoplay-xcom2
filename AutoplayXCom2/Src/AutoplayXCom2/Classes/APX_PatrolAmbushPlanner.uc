// Bounded, source-backed patrol setup. Current waypoint is an observation,
// next-turn paths are VARIANTS (uncertain), not predicted native AI choices.
// State stays runtime-local and is reset at OFF, rewind and battle changes.
class APX_PatrolAmbushPlanner extends Object config(AutoplayXCom2)
    dependson(X2GameRulesetVisibilityDataStructures);

var config bool EnablePatrolAmbush;
var config int MaxSetupTurns;
var config int MaxSetupActions;
var config int MaxReactionSupport;
var config int MaxPositionSamples;
var config int MaxGroupChecks;
var config float MaxPatrolDistanceTiles;
var config float MinimumApproachGainTiles;
var config float WeakRevealedOpenerThreshold;

var private XComGameStateHistory OwnedHistory;
var private int OwnedStartIndex, OwnedBattleID, OwnedPlayerID;
var private int LastHistory, GroupID, StartTurn, LastTurn;
var private TTile Waypoint;
var private int PreparedMoves, OrderedReactions;
var private name Phase;
var private bool bExpired;

// Single-turn progression and future target hypotheses do not grant a
// movement trigger, future LOS or a shot against a hidden group.
static function bool CanStage(bool bEnabled, bool bUrgent, bool bCombatContact,
    bool bNativePath, int StandardAP, int Actions, int Limit, int Elapsed, int MaxTurns)
{
    return bEnabled && !bUrgent && !bCombatContact && bNativePath
        && StandardAP >= 2 && Actions < Limit && Elapsed < MaxTurns;
}

static function bool CanDeferOpener(bool bNativeOpener, bool bUrgent,
    bool bRevealed, float DirectShotScore, int ReadySupport,
    int Ordered, int MaxSupport, float WeakRevealedThreshold)
{
    if (!bNativeOpener || bUrgent || ReadySupport < 2 || Ordered >= MaxSupport)
        return false;
    return !bRevealed || DirectShotScore <= WeakRevealedThreshold;
}

static function float VariantPositionScore(float Progress, int CoveredLanes,
    bool bDirectionalCover, float PositionBenefit, float ExposureIncrease,
    int ContactStatus, float UnknownPenalty)
{
    if (Progress <= 0.0 || CoveredLanes <= 0 || ContactStatus == 1)
        return -10000.0;
    return 30.0 + FMin(14.0, Progress * 3.0)
        + float(Clamp(CoveredLanes, 0, 3)) * 8.0
        + (bDirectionalCover ? 8.0 : 0.0)
        + FClamp(PositionBenefit, -16.0, 12.0)
        - FMax(0.0, ExposureIncrease) * 1.5
        - (ContactStatus < 0 ? FClamp(UnknownPenalty, 0.0, 30.0) : 0.0);
}

function Reset()
{
    OwnedHistory = none;
    OwnedStartIndex = INDEX_NONE;
    OwnedBattleID = 0;
    OwnedPlayerID = 0;
    LastHistory = INDEX_NONE;
    GroupID = 0;
    StartTurn = INDEX_NONE;
    LastTurn = INDEX_NONE;
    PreparedMoves = 0;
    OrderedReactions = 0;
    Phase = 'none';
    bExpired = false;
}

function bool Refresh(XComGameState_Unit Scout, int Turn,
    StateObjectReference PatrolGroup, TTile CurrentWaypoint,
    bool bSnapshotComplete, bool bUrgent, out string Reason)
{
    local XComGameState_BattleData Battle;
    local int HistoryIndex, StartIndex;
    local XComGameState_AIGroup Group;
    local bool bNewEpoch;

    Reason = "unavailable";
    if (!EnablePatrolAmbush || Scout == none || `XCOMHISTORY == none
        || !class'APX_FullIntel'.default.EnableFullIntel)
    {
        Reset();
        return false;
    }
    HistoryIndex = `XCOMHISTORY.GetCurrentHistoryIndex();
    StartIndex = `XCOMHISTORY.FindStartStateIndex();
    Battle = XComGameState_BattleData(`XCOMHISTORY.GetSingleGameStateObjectForClass(
        class'XComGameState_BattleData', true));
    if (Battle == none)
    {
        Reset();
        return false;
    }
    bNewEpoch = OwnedHistory != `XCOMHISTORY
        || OwnedStartIndex != StartIndex
        || OwnedBattleID != Battle.ObjectID
        || OwnedPlayerID != Scout.GetAssociatedPlayerID()
        || HistoryIndex < LastHistory || Turn < LastTurn;
    if (bNewEpoch)
        Reset();
    OwnedHistory = `XCOMHISTORY;
    OwnedStartIndex = StartIndex;
    OwnedBattleID = Battle.ObjectID;
    OwnedPlayerID = Scout.GetAssociatedPlayerID();
    LastHistory = HistoryIndex;
    LastTurn = Turn;

    if (bUrgent || !bSnapshotComplete || PatrolGroup.ObjectID <= 0)
    {
        if (GroupID > 0)
        {
            Phase = 'abort';
            bExpired = true; // Do not spin on the same uncertain waypoint.
        }
        Reason = bUrgent ? "urgent_mission_preempts" : "patrol_evidence_unknown";
        return false;
    }
    Group = XComGameState_AIGroup(
        `XCOMHISTORY.GetGameStateForObjectID(PatrolGroup.ObjectID));
    if (Group == none || Group.bRemoved)
    {
        Reason = "patrol_missing";
        Phase = 'abort';
        bExpired = true;
        return false;
    }
    if (GroupID != Group.ObjectID || CurrentWaypoint != Waypoint)
    {
        GroupID = Group.ObjectID;
        Waypoint = CurrentWaypoint;
        StartTurn = Turn;
        PreparedMoves = 0;
        OrderedReactions = 0;
        Phase = 'approach';
        bExpired = false;
    }
    if (bExpired || Turn - StartTurn >= Clamp(MaxSetupTurns, 1, 3))
    {
        Phase = 'abort';
        bExpired = true;
        Reason = "setup_wait_limit";
        return false;
    }
    Reason = string(Phase);
    return Phase != 'open' && Phase != 'abort';
}

function name CurrentPhase()
{
    return Phase;
}

function int CurrentGroupID()
{
    return GroupID;
}

function TTile CurrentWaypoint()
{
    return Waypoint;
}

function void NoteSubmitted(bool bMove, bool bReaction, bool bOpener)
{
    if (bOpener)
    {
        Phase = 'open';
        bExpired = true;
    }
    else if (bReaction)
    {
        ++OrderedReactions;
        Phase = 'armed';
    }
    else if (bMove)
    {
        ++PreparedMoves;
        Phase = 'setup';
    }
}

// A directional LOS check to one possible approach tile gives one geometric
// lane, not a selected enemy path, native reaction trigger or legal attack.
// Shared budget is depleted for ALL candidate locations and all own soldiers.
static function int CountVariantLanes(TTile Position, TTile Target,
    out int RemainingLOS)
{
    local TTile Variant;
    local GameRulesCache_VisibilityInfo Visibility;
    local int Index, Lanes;
    local float SightSq;

    SightSq = Square(`METERSTOUNITS(15.0));
    for (Index = 0; Index < 3; ++Index)
    {
        Variant = Target;
        if (Index == 1)
            Variant.X += 2;
        if (Index == 2)
            Variant.Y += 2;
        if (`XWORLD.IsTileOutOfRange(Variant))
            continue;
        if (RemainingLOS <= 0)
            return 0; // The entire confidence estimate is now unknown.
        --RemainingLOS;
        if (`XWORLD.CanSeeTileToTile(Position, Variant, Visibility)
            && Visibility.DefaultTargetDist <= SightSq)
            ++Lanes;
    }
    return Lanes;
}

// Only a blue-range, native-reachable setup that improves at least one
// corridor. No target is generated by hypotheses, and no blind overwatch.
// Normal objective, deadline, evac, bleeding, combat still have priority.
function bool ChooseApproach(XComGameState_Unit Soldier,
    const out array<StateObjectReference> KnownUnits,
    const out array<StateObjectReference> KnownInteractives,
    bool bSnapshotComplete, string SnapshotReason,
    out int RemainingDetectors, out int RemainingTiles, out int RemainingLOS,
    out array<TTile> Path, out float Score, out string Reason,
    optional out int RemainingConcealmentChecks)
{
    local XGUnit Visualizer;
    local array<TTile> Tiles, CandidatePath;
    local array<StateObjectReference> VisibleEnemies;
    local array<float> MeleeThreatReaches, ThreatWeights;
    local AvailableAction OW;
    local TTile Tile;
    local vector Source, Destination;
    local float Cost, Progress, NowDistance, NextDistance;
    local float PositionGain, RiskNow, RiskThere, CandidateScore, Angle;
    local int Sample, Index, ContactStatus, Lanes, OWTargetIndex, OWCost;
    local bool bCovered;
    local string ContactReason;

    Path.Length = 0;
    Score = -10000.0;
    Reason = "inactive";
    if (Phase != 'approach' && Phase != 'setup')
        return false;
    if (Soldier == none || !class'APX_SquadPlanner'.static.IsLocalSoldier(
        Soldier, OwnedPlayerID) || !Soldier.IsAbleToAct()
        || Soldier.NumAllReserveActionPoints() > 0
        || !class'APX_MissionPlanner'.static.HasLegalMove(Soldier)
        || !class'APX_SquadPlanner'.static.FindOverwatch(
            Soldier, OW, OWTargetIndex, OWCost))
        return false;
    if (!CanStage(EnablePatrolAmbush, false, false, true,
        Soldier.NumActionPoints(), PreparedMoves,
        Clamp(MaxSetupActions, 1, 8), LastTurn - StartTurn,
        Clamp(MaxSetupTurns, 1, 3)))
        return false;

    Visualizer = XGUnit(Soldier.GetVisualizer());
    if (Visualizer == none || Visualizer.m_kReachableTilesCache == none)
        return false;
    Visualizer.m_kReachableTilesCache.UpdateTileCacheIfNeeded();
    Visualizer.m_kReachableTilesCache.GetAllPathableTiles(Tiles, Visualizer.GetMobility());
    NowDistance = class'APX_MissionPlanner'.static.TileDistance(Soldier.TileLocation, Waypoint);
    if (NowDistance < 4.0 || NowDistance > FMax(8.0, MaxPatrolDistanceTiles))
        return false;
    class'APX_MissionPlanner'.static.GetVisibleThreats(Soldier, VisibleEnemies);
    if (VisibleEnemies.Length > 0)
        return false;
    class'APX_MissionPlanner'.static.GetMeleeThreatReaches(
        Soldier, VisibleEnemies, MeleeThreatReaches);
    class'APX_MissionPlanner'.static.GetThreatWeights(
        Soldier, VisibleEnemies, ThreatWeights);
    RiskNow = class'APX_MissionPlanner'.static.ExposureRisk(
        Soldier, Soldier.TileLocation, VisibleEnemies, MeleeThreatReaches, ThreatWeights);
    Source = `XWORLD.GetPositionFromTileCoordinates(Waypoint);
    Sample = Min(Tiles.Length, Clamp(MaxPositionSamples, 1, 48));
    for (Index = 0; Index < Sample; ++Index)
    {
        Tile = Tiles[Index * Max(0, Tiles.Length - 1) / Max(1, Sample - 1)];
        if (Tile == Soldier.TileLocation
            || Tile.Z > Soldier.TileLocation.Z + 1)
            continue;
        Cost = Visualizer.m_kReachableTilesCache.GetPathCostToTile(Tile);
        if (Cost < 0.0 || Cost > Visualizer.GetMobility())
            continue;
        NextDistance = class'APX_MissionPlanner'.static.TileDistance(Tile, Waypoint);
        Progress = NowDistance - NextDistance;
        if (Progress < FMax(1.0, MinimumApproachGainTiles) || NextDistance < 4.0)
            continue;
        Destination = `XWORLD.GetPositionFromTileCoordinates(Tile);
        bCovered = `XWORLD.GetCoverTypeForTarget(Source, Destination, Angle) != CT_None;
        RiskThere = class'APX_MissionPlanner'.static.ExposureRisk(
            Soldier, Tile, VisibleEnemies, MeleeThreatReaches, ThreatWeights);
        if (!class'APX_SquadPlanner'.static.PreparationRiskAllowed(RiskNow, RiskThere))
            continue;
        CandidatePath.Length = 0;
        if (!Visualizer.m_kReachableTilesCache.BuildPathToTile(Tile, CandidatePath)
            || !class'APX_SquadPlanner'.static.PreparationPathIsSafe(
                Soldier, CandidatePath, RemainingConcealmentChecks))
            continue;
        ContactStatus = class'APX_ContactEnvelope'.static.AssessRoute(
            Soldier, CandidatePath, KnownUnits, KnownInteractives,
            bSnapshotComplete, SnapshotReason, 0, RemainingDetectors,
            RemainingTiles, RemainingLOS, ContactReason);
        if (ContactStatus == 1)
            continue;
        Lanes = CountVariantLanes(Tile, Waypoint, RemainingLOS);
        PositionGain = class'APX_MissionPlanner'.static.SquadPositionScore(Soldier, Tile)
            - class'APX_MissionPlanner'.static.SquadPositionScore(
                Soldier, Soldier.TileLocation);
        CandidateScore = VariantPositionScore(Progress, Lanes, bCovered,
            PositionGain, RiskThere - RiskNow, ContactStatus,
            class'APX_ContactEnvelope'.static.PathStatusPenalty(-1));
        CandidateScore -= Cost * 0.25;
        if (CandidateScore <= Score)
            continue;
        Path = CandidatePath;
        Score = CandidateScore;
        Reason = ContactStatus < 0 ? "setup_variant_unknown" : "setup_current_clear";
    }
    return Path.Length > 1;
}

// An opener MUST be the native legal shot against a member of this stored
// current group, never merely an estimated corridor or a fake target.
function bool IsActualOpener(AvailableAction Candidate, int TargetIndex,
    XComGameState_Unit Soldier)
{
    local XComGameState_Ability Ability;
    local XComGameState_AIGroup Group;
    local int EnemyID;

    if (GroupID <= 0 || Soldier == none
        || Candidate.AvailableCode != 'AA_Success'
        || TargetIndex < 0 || TargetIndex >= Candidate.AvailableTargets.Length)
        return false;
    Ability = XComGameState_Ability(`XCOMHISTORY.GetGameStateForObjectID(
        Candidate.AbilityObjectRef.ObjectID));
    Group = XComGameState_AIGroup(`XCOMHISTORY.GetGameStateForObjectID(GroupID));
    if (Ability == none || Group == none
        || Ability.OwnerStateObject.ObjectID != Soldier.ObjectID
        || Ability.GetMyTemplate() == none
        || Ability.GetMyTemplate().Hostility != eHostility_Offensive
        || (Ability.GetMyTemplateName() != 'StandardShot'
            && Ability.GetMyTemplateName() != 'PistolStandardShot'
            && Ability.GetMyTemplateName() != 'SniperStandardFire'))
        return false;
    EnemyID = Candidate.AvailableTargets[TargetIndex].PrimaryTarget.ObjectID;
    return Group.m_arrMembers.Find('ObjectID', EnemyID) != INDEX_NONE;
}

// Readiness is a current real native action; projected lanes are only hints.
// This method cannot create an enemy target or bypass available-action checks.
function bool ChooseReactionSupport(int PlayerID, XComGameState_Unit Opener,
    AvailableAction NativeOpener, int OpenerTarget, float DirectScore,
    out XComGameState_Unit Supporter, out AvailableAction Reaction,
    out int ReactionTarget, out float ReactionScore)
{
    local XComGameState_Unit Soldier, Enemy;
    local XComGameState_AIGroup Group;
    local XComGameState_Ability Ability;
    local AvailableAction Candidate;
    local array<StateObjectReference> VisibleEnemies;
    local int Cost, TargetIndex, Checked, Eligible, AlreadyArmed;
    local bool bRevealed;

    Supporter = none;
    ReactionTarget = INDEX_NONE;
    ReactionScore = -10000.0;
    if (Phase == 'abort' || Phase == 'open' || GroupID <= 0 || Opener == none
        || OpenerTarget < 0 || OpenerTarget >= NativeOpener.AvailableTargets.Length)
        return false;
    Ability = XComGameState_Ability(`XCOMHISTORY.GetGameStateForObjectID(
        NativeOpener.AbilityObjectRef.ObjectID));
    if (Ability == none || Ability.OwnerStateObject.ObjectID != Opener.ObjectID
        || Ability.GetMyTemplate() == none
        || Ability.GetMyTemplate().Hostility != eHostility_Offensive
        || (Ability.GetMyTemplateName() != 'StandardShot'
            && Ability.GetMyTemplateName() != 'PistolStandardShot'
            && Ability.GetMyTemplateName() != 'SniperStandardFire'))
        return false;
    Enemy = XComGameState_Unit(`XCOMHISTORY.GetGameStateForObjectID(
        NativeOpener.AvailableTargets[OpenerTarget].PrimaryTarget.ObjectID));
    Group = XComGameState_AIGroup(`XCOMHISTORY.GetGameStateForObjectID(GroupID));
    if (Enemy == none || Group == none
        || Group.m_arrMembers.Find('ObjectID', Enemy.ObjectID) == INDEX_NONE)
        return false;
    bRevealed = !class'APX_SquadPlanner'.static.SquadIsConcealed(PlayerID);
    class'APX_MissionPlanner'.static.GetVisibleThreats(Opener, VisibleEnemies);
    if (!class'APX_CombatPlanner'.static.IsVisibleHostile(
        Opener, Enemy, VisibleEnemies))
        return false;
    // Native action cache on real, currently visible target, never a future
    // activation assumption. Two useful lanes required before spending OW AP.
    foreach `XCOMHISTORY.IterateByClassType(class'XComGameState_Unit', Soldier)
    {
        if (++Checked > 24)
            return false;
        if (!class'APX_SquadPlanner'.static.IsLocalSoldier(Soldier, PlayerID)
            || Soldier.ObjectID == Opener.ObjectID || !Soldier.IsAbleToAct())
            continue;
        if (class'APX_SquadPlanner'.static.HasReadyOpeningOverwatch(Soldier))
        {
            ++Eligible;
            ++AlreadyArmed;
            continue;
        }
        if (!class'APX_SquadPlanner'.static.HasFiringLane(
            Soldier, Soldier.TileLocation, VisibleEnemies)
            || !class'APX_SquadPlanner'.static.FindOverwatch(
                Soldier, Candidate, TargetIndex, Cost))
            continue;
        ++Eligible;
        if (Supporter == none)
        {
            Supporter = Soldier;
            Reaction = Candidate;
            ReactionTarget = TargetIndex;
        }
    }
    if (!CanDeferOpener(true, class'APX_MissionPlanner'.static.HasActiveMissionDeadline()
        || class'APX_MissionPlanner'.static.HasBleedingSquadmate(Opener)
        || class'APX_MissionPlanner'.static.ShouldEvacuate(Opener),
        bRevealed, DirectScore, Eligible, OrderedReactions + AlreadyArmed,
        Clamp(MaxReactionSupport, 1, 3), WeakRevealedOpenerThreshold)
        || Supporter == none)
        return false;
    ReactionScore = DirectScore + 1.0;
    return true;
}
