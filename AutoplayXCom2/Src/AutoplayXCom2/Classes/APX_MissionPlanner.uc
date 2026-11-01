// Tactical mission actions use the normal rules cache; never complete objectives by force.
class APX_MissionPlanner extends Object
    config(AutoplayXCom2)
    dependson(X2GameRuleset, X2TacticalGameRulesetDataStructures, XComWorldData);

var config int MaxCandidateTiles;
var config float PreferredCombatRangeTiles;
var config float MinimumPositionGain;
var config float SquadSupportDistance;
var config float SquadSeparationTiles;

// UnrealScript cannot pass a bit-packed bool as an out parameter. Carry the
// related result fields in one value whose structure can be passed by reference.
struct MissionGoal
{
    var TTile Tile;
    var float Value;
    var bool bCombat;
    var bool bFound;
};

// A component marks an actual mission unit (VIP/captive), rather than every civilian.
static function bool HasObjectiveInfo(XComGameState_BaseObject StateObject)
{
    local array<XComGameState_BaseObject> Components;
    local int Index;

    if (StateObject == none)
        return false;
    StateObject.GetAllComponentObjects(Components);
    for (Index = 0; Index < Components.Length; ++Index)
    {
        if (XComGameState_ObjectiveInfo(Components[Index]) != none)
            return true;
    }
    return false;
}

static function bool IsUnfinishedObject(XComGameState_InteractiveObject ObjectState)
{
    return ObjectState != none && ObjectState.IsEnabled && !ObjectState.bBroken
        && !ObjectState.bRemovedFromPlay && !ObjectState.bHasBeenHacked
        && (ObjectState.MaxInteractionCount < 0
            || ObjectState.InteractionCount < ObjectState.MaxInteractionCount);
}

// Do not evacuate the combat squad merely because a flare exists. The mission's
// strategy objective must be complete; controlled civilians and carried VIPs go first.
static function bool ShouldEvacuate(XComGameState_Unit UnitState)
{
    local XComGameState_BattleData BattleData;
    local XComGameState_Unit CarriedUnit;
    local XComGameState_Effect CarryEffect;
    local int ObjectiveIndex;
    local bool bHasStrategyObjective;

    if (UnitState.IsCivilian() && UnitState.GetTeam() == eTeam_XCom)
        return true;

    if (UnitState.IsUnitAffectedByEffectName(class'X2Ability_CarryUnit'.default.CarryUnitEffectName))
    {
        foreach `XCOMHISTORY.IterateByClassType(class'XComGameState_Unit', CarriedUnit)
        {
            CarryEffect = CarriedUnit.GetUnitAffectedByEffectState(class'X2AbilityTemplateManager'.default.BeingCarriedEffectName);
            if (CarryEffect != none
                && CarryEffect.ApplyEffectParameters.SourceStateObjectRef.ObjectID == UnitState.ObjectID
                && HasObjectiveInfo(CarriedUnit))
                return true;
        }
    }

    BattleData = XComGameState_BattleData(`XCOMHISTORY.GetSingleGameStateObjectForClass(class'XComGameState_BattleData', true));
    if (BattleData == none)
        return false;
    for (ObjectiveIndex = 0;
        ObjectiveIndex < BattleData.MapData.ActiveMission.MissionObjectives.Length;
        ++ObjectiveIndex)
    {
        if (BattleData.MapData.ActiveMission.MissionObjectives[ObjectiveIndex].bIsStrategyObjective)
        {
            bHasStrategyObjective = true;
            break;
        }
    }
    // The game's helper returns true for an empty strategy-objective set.
    // That must not tell a defense squad to abandon an active mission.
    return bHasStrategyObjective && BattleData.AllStrategyObjectivesCompleted();
}

static function bool IsObjectiveAbility(name AbilityName)
{
    switch (AbilityName)
    {
    case 'Interact_PlantBomb':
    case 'Interact_TakeVial':
    case 'Interact_StasisTube':
    case 'Interact_SweaterTube':
    case 'Interact_MarkSupplyCrate':
    case 'Interact_ActivateAscensionGate':
    case 'Hack_Workstation':
    case 'Hack_ObjectiveChest':
    case 'Hack_Scan':
    case 'GatherEvidence':
    case 'PlantExplosiveMissionDevice':
        return true;
    }
    return false;
}

static function bool ChooseInteraction(XComGameState_Unit UnitState,
    out AvailableAction Action, out int TargetIndex, out float Score)
{
    local GameRulesCache_Unit UnitCache;
    local AvailableAction Candidate;
    local XComGameState_Ability AbilityState;
    local XComGameState_InteractiveObject ObjectState;
    local XComGameState_Unit TargetUnit;
    local name AbilityName;
    local int ActionIndex, Index;
    local float CandidateScore;

    Score = 0;
    TargetIndex = INDEX_NONE;
    if (!`TACTICALRULES.GetGameRulesCache_Unit(UnitState.GetReference(), UnitCache))
        return false;

    for (ActionIndex = 0; ActionIndex < UnitCache.AvailableActions.Length; ++ActionIndex)
    {
        Candidate = UnitCache.AvailableActions[ActionIndex];
        if (Candidate.AvailableCode != 'AA_Success' || !Candidate.bInputTriggered
            || Candidate.bFreeAim)
            continue;
        AbilityState = XComGameState_Ability(`XCOMHISTORY.GetGameStateForObjectID(Candidate.AbilityObjectRef.ObjectID));
        if (AbilityState == none)
            continue;
        AbilityName = AbilityState.GetMyTemplateName();

        if (AbilityName == 'Evac' && ShouldEvacuate(UnitState))
        {
            Action = Candidate;
            TargetIndex = Candidate.AvailableTargets.Length > 0 ? 0 : INDEX_NONE;
            Score = 300;
            return true;
        }

        for (Index = 0; Index < Candidate.AvailableTargets.Length; ++Index)
        {
            CandidateScore = 0;
            ObjectState = XComGameState_InteractiveObject(`XCOMHISTORY.GetGameStateForObjectID(Candidate.AvailableTargets[Index].PrimaryTarget.ObjectID));
            TargetUnit = XComGameState_Unit(`XCOMHISTORY.GetGameStateForObjectID(Candidate.AvailableTargets[Index].PrimaryTarget.ObjectID));

            if (IsObjectiveAbility(AbilityName))
                CandidateScore = 200;
            else if ((AbilityName == 'Interact' || AbilityName == 'Interact_OpenChest'
                || AbilityName == 'Hack' || AbilityName == 'Hack_Chest')
                && IsUnfinishedObject(ObjectState) && ObjectState.GetRequiresObjectiveGlint())
                CandidateScore = 190;
            // The SDK's Knockout condition permits civilians generally; an
            // objective component alone does not distinguish a captive from a
            // friendly/neutral rescue VIP. Capture only the hostile VIP type.
            else if (AbilityName == 'Knockout' && TargetUnit != none
                && TargetUnit.GetMyTemplateName() == 'HostileVIPCivilian'
                && HasObjectiveInfo(TargetUnit))
                CandidateScore = 230;
            else if (AbilityName == 'CarryUnit' && TargetUnit != none
                && !TargetUnit.bRemovedFromPlay && HasObjectiveInfo(TargetUnit))
                CandidateScore = 240;
            else if (AbilityName == 'CarryUnit' && TargetUnit != none
                && UnitState.IsFriendlyUnit(TargetUnit) && TargetUnit.IsBleedingOut()
                && class'XComGameState_EvacZone'.static.GetEvacZone(eTeam_XCom) != none)
                CandidateScore = 220;

            if (CandidateScore > Score)
            {
                Score = CandidateScore;
                Action = Candidate;
                TargetIndex = Index;
            }
        }
    }
    return Score > 0;
}

static function float TileDistance(TTile First, TTile Second)
{
    local vector Delta;
    Delta.X = First.X - Second.X;
    Delta.Y = First.Y - Second.Y;
    Delta.Z = (First.Z - Second.Z) * 0.5;
    return VSize(Delta);
}

static function ConsiderGoal(XComGameState_Unit UnitState, TTile CandidateTile,
    float Priority, bool bCombat, out MissionGoal Goal)
{
    local float Value;
    Value = Priority - TileDistance(UnitState.TileLocation, CandidateTile) * 0.25;
    if (!Goal.bFound || Value > Goal.Value)
    {
        Goal.Tile = CandidateTile;
        Goal.Value = Value;
        Goal.bCombat = bCombat;
        Goal.bFound = true;
    }
}

static function bool FindGoal(XComGameState_Unit UnitState, out MissionGoal Goal,
    out array<StateObjectReference> VisibleEnemies)
{
    local XComGameState_InteractiveObject ObjectState;
    local XComGameState_Unit OtherUnit;
    local XComGameState_EvacZone EvacZone;
    local XComGameState_BattleData BattleData;
    local StateObjectReference EnemyRef;
    local MissionGoal EmptyGoal;

    Goal = EmptyGoal;

    GetVisibleThreats(UnitState, VisibleEnemies);
    EvacZone = class'XComGameState_EvacZone'.static.GetEvacZone(eTeam_XCom);
    if (EvacZone != none && ShouldEvacuate(UnitState))
    {
        Goal.Tile = EvacZone.CenterLocation;
        Goal.bFound = true;
        return true;
    }

    // A squadmate's contact still threatens this soldier. Deal with known
    // enemies before walking toward the much higher-scored mission marker.
    // Evacuation above remains an explicit exception.
    foreach VisibleEnemies(EnemyRef)
    {
        OtherUnit = XComGameState_Unit(`XCOMHISTORY.GetGameStateForObjectID(EnemyRef.ObjectID));
        ConsiderGoal(UnitState, OtherUnit.TileLocation, 40, true, Goal);
    }
    if (Goal.bFound)
        return true;

    foreach `XCOMHISTORY.IterateByClassType(class'XComGameState_InteractiveObject', ObjectState)
    {
        if (IsUnfinishedObject(ObjectState) && ObjectState.GetRequiresObjectiveGlint())
            ConsiderGoal(UnitState, ObjectState.TileLocation, 100, false,
                Goal);
    }

    foreach `XCOMHISTORY.IterateByClassType(class'XComGameState_Unit', OtherUnit)
    {
        if (OtherUnit.ObjectID == UnitState.ObjectID || OtherUnit.bRemovedFromPlay
            || OtherUnit.IsUnitAffectedByEffectName(class'X2AbilityTemplateManager'.default.BeingCarriedEffectName))
            continue;
        // ObjectiveInfo also marks combat objectives. Do not rush into melee
        // range of a hostile boss as though it were a civilian to rescue.
        if (HasObjectiveInfo(OtherUnit) && !OtherUnit.IsPlayerControlled()
            && (!UnitState.IsEnemyUnit(OtherUnit)
                || OtherUnit.GetMyTemplateName() == 'HostileVIPCivilian')
            && class'X2TacticalVisibilityHelpers'.static.IsUnitVisibleToLocalPlayer(OtherUnit.ObjectID, -1))
            ConsiderGoal(UnitState, OtherUnit.TileLocation, 95, false,
                Goal);
        else if (OtherUnit.IsAlive() && OtherUnit.GetTeam() == eTeam_Neutral
            && OtherUnit.RescueRingRadius > 0
            && class'X2TacticalVisibilityHelpers'.static.IsUnitVisibleToLocalPlayer(OtherUnit.ObjectID, -1))
            ConsiderGoal(UnitState, OtherUnit.TileLocation, 80, false,
                Goal);
    }

    if (!Goal.bFound)
    {
        BattleData = XComGameState_BattleData(`XCOMHISTORY.GetSingleGameStateObjectForClass(class'XComGameState_BattleData', true));
        if (BattleData != none && VSizeSq(BattleData.MapData.ObjectiveLocation) > 1)
        {
            Goal.Tile = `XWORLD.GetTileCoordinatesFromPosition(BattleData.MapData.ObjectiveLocation);
            Goal.bCombat = false;
            Goal.bFound = TileDistance(UnitState.TileLocation, Goal.Tile) > 3;
        }
    }
    return Goal.bFound;
}

// Only the player's known contacts participate, never hidden unit positions.
// The same contact list is shared by movement, attacks and exploration guards.
static function GetVisibleThreats(XComGameState_Unit UnitState,
    out array<StateObjectReference> VisibleEnemies)
{
    local int Index;
    local XComGameState_Unit Enemy;

    VisibleEnemies.Length = 0;
    class'X2TacticalVisibilityHelpers'.static.GetAllVisibleEnemiesForPlayer(
        UnitState.ControllingPlayer.ObjectID, VisibleEnemies);
    for (Index = VisibleEnemies.Length - 1; Index >= 0; --Index)
    {
        Enemy = XComGameState_Unit(`XCOMHISTORY.GetGameStateForObjectID(VisibleEnemies[Index].ObjectID));
        if (Enemy == none || !Enemy.IsAlive() || Enemy.IsIncapacitated()
            || Enemy.bRemovedFromPlay || Enemy.IsCivilian()
            || Enemy.GetMyTemplate().bIsCosmetic || !UnitState.IsEnemyUnit(Enemy)
            || Enemy.GetMyTemplateName() == 'HostileVIPCivilian')
            VisibleEnemies.Remove(Index, 1);
    }
}

static function bool HasCombatThreats(XComGameState_Unit UnitState)
{
    local array<StateObjectReference> VisibleEnemies;
    GetVisibleThreats(UnitState, VisibleEnemies);
    return VisibleEnemies.Length > 0;
}

// This is a conservative directional-cover heuristic, not a hypothetical shot
// preview. Solid walls/peek tiles and enemy movement can change actual LOS.
static function float DirectionalRisk(int CoverLevel, float Distance,
    bool bCanTakeCover, bool bMeleeOnly)
{
    local float Risk;

    if (bMeleeOnly)
        return FMax(0.0, 12.0 - Distance) * 4.0;
    Risk = 30.0;
    if (!bCanTakeCover)
        Risk = 12.0;
    if (bCanTakeCover && CoverLevel == 2)
        Risk = 3.0;
    if (bCanTakeCover && CoverLevel == 1)
        Risk = 10.0;
    return Risk * FClamp(18.0 / FMax(1.0, Distance), 0.2, 1.0) + FMax(0.0, 4.0 - Distance) * 5.0;
}

static function float CombinedExposure(float SumRisk, float WorstRisk, float HealthFraction)
{
    // One open flank cannot be cancelled out by several full-cover directions.
    return (SumRisk * 0.65 + WorstRisk * 0.75) * (1.0 + (1.0 - FClamp(HealthFraction, 0.0, 1.0)) * 0.6);
}

static function float ExposureRisk(XComGameState_Unit UnitState, TTile Tile,
    array<StateObjectReference> VisibleEnemies)
{
    local StateObjectReference EnemyRef;
    local XComGameState_Unit Enemy;
    local vector TargetLocation, EnemyLocation;
    local float Angle, Risk, SumRisk, WorstRisk;
    local ECoverType Cover;
    local int CoverLevel;

    TargetLocation = `XWORLD.GetPositionFromTileCoordinates(Tile);
    foreach VisibleEnemies(EnemyRef)
    {
        Enemy = XComGameState_Unit(`XCOMHISTORY.GetGameStateForObjectID(EnemyRef.ObjectID));
        if (Enemy == none || !Enemy.IsAlive() || Enemy.IsIncapacitated()
            || Enemy.bRemovedFromPlay || !UnitState.IsEnemyUnit(Enemy))
            continue;
        EnemyLocation = `XWORLD.GetPositionFromTileCoordinates(Enemy.TileLocation);
        Cover = `XWORLD.GetCoverTypeForTarget(EnemyLocation, TargetLocation, Angle);
        CoverLevel = 0;
        if (Cover == CT_Standing)
            CoverLevel = 2;
        else if (Cover == CT_MidLevel)
            CoverLevel = 1;
        Risk = DirectionalRisk(CoverLevel, TileDistance(Tile, Enemy.TileLocation),
            UnitState.GetMyTemplate().bCanTakeCover, Enemy.IsMeleeOnly());
        SumRisk += Risk;
        WorstRisk = FMax(WorstRisk, Risk);
    }
    return CombinedExposure(SumRisk, WorstRisk, UnitState.GetCurrentStat(eStat_HP)
        / FMax(1.0, UnitState.GetMaxStat(eStat_HP)));
}

// Smooth support and blast-spacing preferences, not tile reservations. The
// controller submits one action and recomputes from the resulting live state.
static function float SquadPositionScore(XComGameState_Unit UnitState, TTile Tile)
{
    local XComGameState_Unit Friend;
    local float Distance, NearestDistance, Result;
    local bool bHasSupport;

    NearestDistance = 100000.0;
    foreach `XCOMHISTORY.IterateByClassType(class'XComGameState_Unit', Friend)
    {
        if (Friend.ObjectID == UnitState.ObjectID || !Friend.IsAlive()
            || Friend.IsIncapacitated() || Friend.bRemovedFromPlay || Friend.IsCivilian()
            || Friend.GetMyTemplate().bIsCosmetic
            || Friend.GetAssociatedPlayerID() != UnitState.GetAssociatedPlayerID()
            || !UnitState.IsFriendlyUnit(Friend))
            continue;
        Distance = TileDistance(Tile, Friend.TileLocation);
        NearestDistance = FMin(NearestDistance, Distance);
        Result -= FMax(0.0, default.SquadSeparationTiles - Distance) * 5.0;
        bHasSupport = true;
    }
    if (bHasSupport)
        Result -= FMin(30.0, FMax(0.0, NearestDistance - default.SquadSupportDistance) * 4.0);
    return Result;
}

// A soldier with spent AP still anchors the formation. Use only known friendly
// positions; no hidden enemy state participates in this support envelope.
static function float NearestSupportDistance(XComGameState_Unit UnitState, TTile Tile)
{
    local XComGameState_Unit Friendly;
    local float Distance, Nearest;
    local bool bFound;

    Nearest = 1000000.0;
    foreach `XCOMHISTORY.IterateByClassType(class'XComGameState_Unit', Friendly)
    {
        if (Friendly.ObjectID == UnitState.ObjectID || !Friendly.IsAlive()
            || Friendly.IsIncapacitated() || Friendly.bRemovedFromPlay
            || Friendly.GetAssociatedPlayerID() != UnitState.GetAssociatedPlayerID()
            || Friendly.GetTeam() != eTeam_XCom || Friendly.IsCivilian()
            || Friendly.GetMyTemplate().bIsCosmetic)
            continue;
        Distance = TileDistance(Tile, Friendly.TileLocation);
        Nearest = FMin(Nearest, Distance);
        bFound = true;
    }
    // A lone survivor must remain able to advance.
    return bFound ? Nearest : 0.0;
}

static function bool IsSupportedAdvanceStep(float StartDistance, float Distance)
{
    return Distance <= FMax(10.0, StartDistance);
}

static function bool IsSupportedAdvanceDestination(float StartDistance, float Distance)
{
    return Distance <= 10.0 || Distance < StartDistance - 0.5;
}

static function float ScoreRouteAdvance(float CurrentCohesion, float CandidateCohesion)
{
    // Mission-marker routes need the same catch-up ordering as exploration;
    // a fixed route score otherwise lets the first soldier repeatedly lead.
    return 25.0 + FClamp(CandidateCohesion - CurrentCohesion, -6.0, 8.0);
}

static function float OffensivePositionScore(XComGameState_Unit UnitState, TTile Tile,
    array<StateObjectReference> VisibleEnemies)
{
    local XComGameState_Unit Enemy;
    local StateObjectReference EnemyRef;
    local vector SourceLocation, EnemyLocation;
    local ECoverType Cover;
    local float Distance, Angle, Value, BestValue;

    BestValue = -10000.0;
    SourceLocation = `XWORLD.GetPositionFromTileCoordinates(Tile);
    foreach VisibleEnemies(EnemyRef)
    {
        Enemy = XComGameState_Unit(`XCOMHISTORY.GetGameStateForObjectID(EnemyRef.ObjectID));
        if (Enemy == none || !Enemy.IsAlive() || Enemy.IsIncapacitated()
            || !UnitState.IsEnemyUnit(Enemy))
            continue;
        Distance = TileDistance(Tile, Enemy.TileLocation);
        Value = -Abs(Distance - default.PreferredCombatRangeTiles);
        EnemyLocation = `XWORLD.GetPositionFromTileCoordinates(Enemy.TileLocation);
        Cover = `XWORLD.GetCoverTypeForTarget(SourceLocation, EnemyLocation, Angle);
        // Flanking is useful only against cover users within practical range.
        // Keep this bounded: geometry alone does not establish a legal shot.
        if (Enemy.GetMyTemplate().bCanTakeCover && Cover == CT_None && Distance <= 15.0)
            Value += 14.0;
        if (Tile.Z > Enemy.TileLocation.Z && Distance <= 18.0)
            Value += 5.0;
        BestValue = FMax(BestValue, Value);
    }
    if (BestValue == -10000.0)
        return 0.0;
    return BestValue;
}

static function float PositionScore(XComGameState_Unit UnitState, TTile Tile,
    TTile GoalTile, bool bCombatGoal, array<StateObjectReference> VisibleEnemies)
{
    local float Result;
    if (bCombatGoal)
        Result = OffensivePositionScore(UnitState, Tile, VisibleEnemies);
    else
        Result = -TileDistance(Tile, GoalTile) * 3.0;
    return Result - ExposureRisk(UnitState, Tile, VisibleEnemies)
        + SquadPositionScore(UnitState, Tile);
}

// Last-AP movement must remove a material threat, not chase a flank with no
// action left to exploit it. A blue move with two AP still leaves a response.
static function bool IsUsefulReposition(float PositionGain, float CurrentRisk,
    float CandidateRisk, int StandardAP, float MinimumGain)
{
    if (PositionGain < MinimumGain)
        return false;
    if (StandardAP < 2 && CurrentRisk - CandidateRisk < 8.0)
        return false;
    // Do not trade a safe firing position for a speculative flank.
    return CandidateRisk <= CurrentRisk + 3.0;
}

static function bool HasLegalMove(XComGameState_Unit UnitState)
{
    local GameRulesCache_Unit UnitCache;
    local StateObjectReference MoveRef;
    local int Index;

    MoveRef = UnitState.FindAbility('StandardMove');
    if (MoveRef.ObjectID == 0
        || !`TACTICALRULES.GetGameRulesCache_Unit(UnitState.GetReference(), UnitCache))
        return false;
    for (Index = 0; Index < UnitCache.AvailableActions.Length; ++Index)
    {
        if (UnitCache.AvailableActions[Index].AbilityObjectRef.ObjectID == MoveRef.ObjectID
            && UnitCache.AvailableActions[Index].bInputTriggered
            && UnitCache.AvailableActions[Index].AvailableCode == 'AA_Success')
            return true;
    }
    return false;
}

// The distance heuristic can get stuck behind a wall: a real route may first
// move away from its goal. Use the game's unrestricted A* only for planning,
// then rebuild a blue-range prefix from the actual reachable cache for dispatch.
static function bool ChooseRoutePrefix(XComGameState_Unit UnitState,
    XGUnit UnitVisualizer, TTile GoalTile, out array<TTile> Path)
{
    local array<TTile> FullPath, CandidatePath;
    local int Index, PathIndex;
    local bool bSafe, bRequireSupport;
    local float StartSupport, PathCost;

    Path.Length = 0;
    bRequireSupport = !ShouldEvacuate(UnitState);
    StartSupport = NearestSupportDistance(UnitState, UnitState.TileLocation);
    if (!class'X2PathSolver'.static.BuildPath(UnitState,
        UnitState.TileLocation, GoalTile, FullPath, false))
        return false;
    for (Index = FullPath.Length - 1; Index > 0; --Index)
    {
        if (TileDistance(FullPath[Index], UnitState.TileLocation) < 1
            || !UnitVisualizer.m_kReachableTilesCache.IsTileReachable(FullPath[Index]))
            continue;
        PathCost = UnitVisualizer.m_kReachableTilesCache.GetPathCostToTile(FullPath[Index]);
        if (PathCost < 0.0 || PathCost > UnitVisualizer.GetMobility()
            || (bRequireSupport && !IsSupportedAdvanceDestination(StartSupport,
                NearestSupportDistance(UnitState, FullPath[Index]))))
            continue;
        CandidatePath.Length = 0;
        if (!UnitVisualizer.m_kReachableTilesCache.BuildPathToTile(FullPath[Index], CandidatePath)
            || CandidatePath.Length < 2)
            continue;
        bSafe = true;
        for (PathIndex = 1; PathIndex < CandidatePath.Length; ++PathIndex)
        {
            if (class'XComPath'.static.TileContainsHazard(UnitState, CandidatePath[PathIndex])
                || (bRequireSupport && !IsSupportedAdvanceStep(StartSupport,
                    NearestSupportDistance(UnitState, CandidatePath[PathIndex]))))
            {
                bSafe = false;
                break;
            }
        }
        if (bSafe)
        {
            Path = CandidatePath;
            return true;
        }
    }
    return false;
}

static function bool ChooseMove(XComGameState_Unit UnitState,
    out array<TTile> Path, out float Score)
{
    local XGUnit UnitVisualizer;
    local array<TTile> Tiles, CandidatePath;
    local array<StateObjectReference> VisibleEnemies;
    local TTile GoalTile, Tile, ClosestTile;
    local MissionGoal Goal;
    local bool bCombatGoal, bSafe, bRequireSupport;
    local int Index, PathIndex, SampleIndex, SampleCount;
    local float CurrentScore, CandidateScore, BestScore, CurrentRisk, CandidateRisk, PathCost, StartSupport;

    Path.Length = 0;
    Score = 0;
    if (!HasLegalMove(UnitState)
        || !FindGoal(UnitState, Goal, VisibleEnemies))
        return false;
    GoalTile = Goal.Tile;
    bCombatGoal = Goal.bCombat;
    bRequireSupport = !bCombatGoal && !ShouldEvacuate(UnitState);
    StartSupport = NearestSupportDistance(UnitState, UnitState.TileLocation);
    // Preserve the last action for overwatch while advancing into fog. Valid
    // evacuation is allowed because it may be this soldier's final chance.
    if (!bCombatGoal && VisibleEnemies.Length == 0 && UnitState.NumActionPoints() < 2
        && !ShouldEvacuate(UnitState))
        return false;
    UnitVisualizer = XGUnit(UnitState.GetVisualizer());
    if (UnitVisualizer == none || UnitVisualizer.m_kReachableTilesCache == none)
        return false;

    UnitVisualizer.m_kReachableTilesCache.UpdateTileCacheIfNeeded();
    // Prefer the same native route on successive objective moves. A fallback
    // only after greedy failure would oscillate back toward a wall on the next
    // action whenever the necessary detour initially increases direct distance.
    if (!bCombatGoal && VisibleEnemies.Length == 0
        && ChooseRoutePrefix(UnitState, UnitVisualizer, GoalTile, Path))
    {
        Score = ScoreRouteAdvance(SquadPositionScore(UnitState, UnitState.TileLocation),
            SquadPositionScore(UnitState, Path[Path.Length - 1]));
        return true;
    }
    // Blue moves preserve an action for combat, interactions or overwatch.
    UnitVisualizer.m_kReachableTilesCache.GetAllPathableTiles(Tiles, UnitVisualizer.GetMobility());
    ClosestTile = UnitVisualizer.m_kReachableTilesCache.GetClosestReachableDestination(GoalTile);
    // Make sure the closest destination participates even with bounded sampling.
    Tiles.InsertItem(0, ClosestTile);
    SampleCount = Min(Tiles.Length, Clamp(default.MaxCandidateTiles, 1, 512));
    CurrentScore = PositionScore(UnitState, UnitState.TileLocation, GoalTile, bCombatGoal, VisibleEnemies);
    BestScore = CurrentScore + FMax(1.0, default.MinimumPositionGain);
    CurrentRisk = ExposureRisk(UnitState, UnitState.TileLocation, VisibleEnemies);

    // Include the closest goal tile and distribute the remaining samples over
    // the entire native list, even when tile count is just above the budget.
    for (SampleIndex = 0; SampleIndex < SampleCount; ++SampleIndex)
    {
        Index = 0;
        if (SampleIndex > 0 && SampleCount > 1)
            Index = 1 + ((SampleIndex - 1) * (Tiles.Length - 2)) / Max(1, SampleCount - 2);
        Tile = Tiles[Index];
        PathCost = UnitVisualizer.m_kReachableTilesCache.GetPathCostToTile(Tile);
        if (TileDistance(Tile, UnitState.TileLocation) < 1
            || class'XComPath'.static.TileContainsHazard(UnitState, Tile)
            || PathCost < 0.0 || PathCost > UnitVisualizer.GetMobility()
            || (bRequireSupport && !IsSupportedAdvanceDestination(StartSupport,
                NearestSupportDistance(UnitState, Tile))))
            continue;
        CandidateRisk = ExposureRisk(UnitState, Tile, VisibleEnemies);
        CandidateScore = PositionScore(UnitState, Tile, GoalTile, bCombatGoal, VisibleEnemies);
        // Small travel cost breaks equivalent-position ties and reduces churn.
        CandidateScore -= PathCost * 0.25;
        if (bCombatGoal && !IsUsefulReposition(CandidateScore - CurrentScore,
            CurrentRisk, CandidateRisk, UnitState.NumActionPoints(), default.MinimumPositionGain))
            continue;
        if (CandidateScore <= BestScore)
            continue;

        CandidatePath.Length = 0;
        if (!UnitVisualizer.m_kReachableTilesCache.BuildPathToTile(Tile, CandidatePath)
            || CandidatePath.Length < 2)
            continue;
        bSafe = true;
        // Check the entire route, not just its endpoint; allow leaving a burning start tile.
        for (PathIndex = 1; PathIndex < CandidatePath.Length; ++PathIndex)
        {
            if (class'XComPath'.static.TileContainsHazard(UnitState, CandidatePath[PathIndex])
                || (bRequireSupport && !IsSupportedAdvanceStep(StartSupport,
                    NearestSupportDistance(UnitState, CandidatePath[PathIndex]))))
            {
                bSafe = false;
                break;
            }
        }
        if (bSafe)
        {
            BestScore = CandidateScore;
            Path = CandidatePath;
        }
    }
    if (Path.Length < 2)
        return false;
    Score = 20 + FMin(60, BestScore - CurrentScore);
    return true;
}
