// Tactical mission actions use the normal rules cache; never complete objectives by force.
class APX_MissionPlanner extends Object
    config(AutoplayXCom2)
    dependson(X2GameRuleset, X2TacticalGameRulesetDataStructures, XComWorldData);

var config int MaxCandidateTiles;
var config float PreferredCombatRangeTiles;

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

    class'X2TacticalVisibilityHelpers'.static.GetAllVisibleEnemyUnitsForUnit(UnitState.ObjectID, VisibleEnemies);
    EvacZone = class'XComGameState_EvacZone'.static.GetEvacZone(eTeam_XCom);
    if (EvacZone != none && ShouldEvacuate(UnitState))
    {
        Goal.Tile = EvacZone.CenterLocation;
        Goal.bFound = true;
        return true;
    }

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

    foreach VisibleEnemies(EnemyRef)
    {
        OtherUnit = XComGameState_Unit(`XCOMHISTORY.GetGameStateForObjectID(EnemyRef.ObjectID));
        if (OtherUnit != none && OtherUnit.IsAlive() && !OtherUnit.bRemovedFromPlay
            && UnitState.IsEnemyUnit(OtherUnit))
            ConsiderGoal(UnitState, OtherUnit.TileLocation, 40, true,
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

// Evaluate cover against the enemies the soldier can actually see. Hidden units
// never contribute to target selection or movement scoring.
static function float CoverScore(XComGameState_Unit UnitState, TTile Tile,
    array<StateObjectReference> VisibleEnemies)
{
    local StateObjectReference EnemyRef;
    local XComGameState_Unit Enemy;
    local vector TargetLocation, EnemyLocation;
    local float Angle, Result;
    local ECoverType Cover;

    if (!UnitState.GetMyTemplate().bCanTakeCover)
        return 0;
    TargetLocation = `XWORLD.GetPositionFromTileCoordinates(Tile);
    foreach VisibleEnemies(EnemyRef)
    {
        Enemy = XComGameState_Unit(`XCOMHISTORY.GetGameStateForObjectID(EnemyRef.ObjectID));
        if (Enemy == none || !Enemy.IsAlive() || Enemy.GetTeam() == eTeam_TheLost
            || !UnitState.IsEnemyUnit(Enemy))
            continue;
        EnemyLocation = `XWORLD.GetPositionFromTileCoordinates(Enemy.TileLocation);
        Cover = `XWORLD.GetCoverTypeForTarget(EnemyLocation, TargetLocation, Angle);
        if (Cover == CT_Standing)
            Result += 6;
        else if (Cover == CT_MidLevel)
            Result += 3;
        else
            Result -= 8;
    }
    return Result;
}

static function float PositionScore(XComGameState_Unit UnitState, TTile Tile,
    TTile GoalTile, bool bCombatGoal, array<StateObjectReference> VisibleEnemies)
{
    local float Distance, Result;
    Distance = TileDistance(Tile, GoalTile);
    if (bCombatGoal)
        Result = -Abs(Distance - default.PreferredCombatRangeTiles) * 2;
    else
        Result = -Distance * 3;
    Result += CoverScore(UnitState, Tile, VisibleEnemies);
    return Result;
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
    local bool bSafe;

    Path.Length = 0;
    if (!class'X2PathSolver'.static.BuildPath(UnitState,
        UnitState.TileLocation, GoalTile, FullPath, false))
        return false;
    for (Index = FullPath.Length - 1; Index > 0; --Index)
    {
        if (TileDistance(FullPath[Index], UnitState.TileLocation) < 1
            || !UnitVisualizer.m_kReachableTilesCache.IsTileReachable(FullPath[Index])
            || UnitVisualizer.m_kReachableTilesCache.GetPathCostToTile(FullPath[Index]) > UnitVisualizer.GetMobility())
            continue;
        CandidatePath.Length = 0;
        if (!UnitVisualizer.m_kReachableTilesCache.BuildPathToTile(FullPath[Index], CandidatePath)
            || CandidatePath.Length < 2)
            continue;
        bSafe = true;
        for (PathIndex = 1; PathIndex < CandidatePath.Length; ++PathIndex)
        {
            if (class'XComPath'.static.TileContainsHazard(UnitState, CandidatePath[PathIndex]))
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
    local bool bCombatGoal, bSafe;
    local int Index, PathIndex, Stride;
    local float CurrentScore, CandidateScore, BestScore;

    Path.Length = 0;
    Score = 0;
    if (!HasLegalMove(UnitState)
        || !FindGoal(UnitState, Goal, VisibleEnemies))
        return false;
    GoalTile = Goal.Tile;
    bCombatGoal = Goal.bCombat;
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
        Score = 25;
        return true;
    }
    // Blue moves preserve an action for combat, interactions or overwatch.
    UnitVisualizer.m_kReachableTilesCache.GetAllPathableTiles(Tiles, UnitVisualizer.GetMobility());
    ClosestTile = UnitVisualizer.m_kReachableTilesCache.GetClosestReachableDestination(GoalTile);
    // Make sure the closest destination participates even with bounded sampling.
    Tiles.InsertItem(0, ClosestTile);
    Stride = Max(1, (Tiles.Length + Max(1, default.MaxCandidateTiles) - 1)
        / Max(1, default.MaxCandidateTiles));
    CurrentScore = PositionScore(UnitState, UnitState.TileLocation, GoalTile, bCombatGoal, VisibleEnemies);
    BestScore = CurrentScore + 1.0;

    for (Index = 0; Index < Tiles.Length; Index += Stride)
    {
        Tile = Tiles[Index];
        if (TileDistance(Tile, UnitState.TileLocation) < 1
            || class'XComPath'.static.TileContainsHazard(UnitState, Tile)
            || UnitVisualizer.m_kReachableTilesCache.GetPathCostToTile(Tile) > UnitVisualizer.GetMobility())
            continue;
        CandidateScore = PositionScore(UnitState, Tile, GoalTile, bCombatGoal, VisibleEnemies);
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
            if (class'XComPath'.static.TileContainsHazard(UnitState, CandidatePath[PathIndex]))
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

defaultproperties
{
    MaxCandidateTiles=96
    PreferredCombatRangeTiles=9
}
