// Tactical mission actions use the normal rules cache; never complete objectives by force.
class APX_MissionPlanner extends Object
    config(AutoplayXCom2)
    dependson(X2GameRuleset, X2TacticalGameRulesetDataStructures, XComWorldData,
        X2GameRulesetVisibilityDataStructures, XGTacticalGameCoreNativeBase);

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

// Loot never justifies postponing an owned soldier's bleeding-out emergency.
static function bool HasBleedingSquadmate(XComGameState_Unit UnitState)
{
    local XComGameState_Unit Friendly;

    foreach `XCOMHISTORY.IterateByClassType(class'XComGameState_Unit', Friendly)
    {
        if (Friendly.IsAlive() && !Friendly.bRemovedFromPlay
            && Friendly.GetTeam() == eTeam_XCom && !Friendly.GetMyTemplate().bIsCosmetic
            && Friendly.GetAssociatedPlayerID() == UnitState.GetAssociatedPlayerID()
            && Friendly.IsBleedingOut())
            return true;
    }
    return false;
}

// Read the installed native ability, including its actual configured range.
// Unsupported/modded costs or targeting styles do not grant a free pickup.
static function XComGameState_Ability GetReadyLootAbility(XComGameState_Unit UnitState,
    out float LootRange)
{
    local StateObjectReference AbilityRef;
    local XComGameState_Ability Ability;
    local X2AbilityTemplate Template;
    local X2Condition Condition;
    local X2Condition_Lootable LootCondition;

    LootRange = 0.0;
    if (UnitState == none || !UnitState.IsAbleToAct() || UnitState.bRemovedFromPlay
        || UnitState.GetTeam() != eTeam_XCom || UnitState.IsCivilian()
        || UnitState.GetMyTemplate().bIsCosmetic)
        return none;
    AbilityRef = UnitState.FindAbility('Loot');
    Ability = XComGameState_Ability(`XCOMHISTORY.GetGameStateForObjectID(AbilityRef.ObjectID));
    if (Ability == none || Ability.OwnerStateObject.ObjectID != UnitState.ObjectID)
        return none;
    Template = Ability.GetMyTemplate();
    if (Template == none || Template.Hostility != eHostility_Neutral
        || Template.AbilityCosts.Length != 0 || !Ability.IsAbilityInputTriggered()
        || Ability.IsAbilityFreeAiming() || Template.AbilityTargetStyle == none
        || Template.AbilityTargetStyle.Class != class'X2AbilityTarget_Single'
        || Template.AbilityMultiTargetStyle == none
        || Template.AbilityMultiTargetStyle.Class != class'X2AbilityMultiTarget_Loot'
        || Ability.CanActivateAbility(UnitState) != 'AA_Success')
        return none;
    foreach Template.AbilityTargetConditions(Condition)
    {
        LootCondition = X2Condition_Lootable(Condition);
        if (LootCondition != none && LootCondition.bRestrictRange
            && LootCondition.LootableRange > 0)
        {
            LootRange = LootCondition.LootableRange;
            return Ability;
        }
    }
    return none;
}

// The rules cache supplies the legal target; activating native Loot acquires
// all eligible nearby items. There is no inventory mutation or pickup dialog.
static function bool ChooseLootInteraction(XComGameState_Unit UnitState,
    out AvailableAction Action, out int TargetIndex, out float Score)
{
    local XComGameState_Ability LootAbility;
    local XComGameState_BaseObject TargetObject;
    local Lootable LootObject;
    local GameRulesCache_Unit UnitCache;
    local AvailableAction Candidate;
    local int ActionIndex, Index;
    local float LootRange;

    Score = 0.0;
    TargetIndex = INDEX_NONE;
    LootAbility = GetReadyLootAbility(UnitState, LootRange);
    if (LootAbility == none || HasBleedingSquadmate(UnitState) || ShouldEvacuate(UnitState)
        || !`TACTICALRULES.GetGameRulesCache_Unit(UnitState.GetReference(), UnitCache))
        return false;
    for (ActionIndex = 0; ActionIndex < UnitCache.AvailableActions.Length; ++ActionIndex)
    {
        Candidate = UnitCache.AvailableActions[ActionIndex];
        if (Candidate.AbilityObjectRef.ObjectID != LootAbility.ObjectID
            || Candidate.AvailableCode != 'AA_Success' || !Candidate.bInputTriggered
            || Candidate.bFreeAim)
            continue;
        for (Index = 0; Index < Candidate.AvailableTargets.Length; ++Index)
        {
            TargetObject = `XCOMHISTORY.GetGameStateForObjectID(
                Candidate.AvailableTargets[Index].PrimaryTarget.ObjectID);
            LootObject = Lootable(TargetObject);
            if (TargetObject == none || TargetObject.bRemoved || LootObject == none
                || !LootObject.HasAvailableLoot()
                || !LootObject.HasAvailableLootForLooter(UnitState.GetReference()))
                continue;
            Action = Candidate;
            TargetIndex = Index;
            Score = 245.0;
            return true;
        }
    }
    return false;
}

static function bool HasActiveMissionDeadline()
{
    local XComGameState_UITimer TimerState;

    foreach `XCOMHISTORY.IterateByClassType(class'XComGameState_UITimer', TimerState)
    {
        // Do not infer timer semantics from its label or invent remaining turns.
        if (!TimerState.bRemoved && TimerState.IsTimer && TimerState.ShouldShow
            && !TimerState.IsSuspended())
            return true;
    }
    return false;
}

static function bool IsLootRouteAllowed(bool bThreats, bool bBleeding,
    bool bEvacuating, bool bReadyObjective, bool bMissionDeadline, int StandardAP)
{
    return !bThreats && !bBleeding && !bEvacuating && !bReadyObjective
        && !bMissionDeadline && StandardAP >= 2;
}

static function bool LootRouteMakesProgress(bool bHasMissionGoal,
    float CurrentGoalDistance, float DestinationGoalDistance)
{
    return !bHasMissionGoal || DestinationGoalDistance <= CurrentGoalDistance;
}

static function float ScoreLootMove(float PathCost, int ExpirationTurns,
    bool bHasMissionGoal)
{
    local float Value;

    Value = 24.0;
    if (bHasMissionGoal)
        Value = 36.0;
    // Only the drop's real native expiry affects urgency; no synthetic timer.
    return Value + float(Clamp(3 - ExpirationTurns, 0, 2))
        - FMin(3.0, FMax(0.0, PathCost) * 0.1);
}

// Propose a short, known safe approach. EndOfMoveLoot and the refreshed rules
// cache remain authoritative: a proposed tile is never a relocated live unit.
static function bool ChooseLootMove(XComGameState_Unit UnitState,
    out array<TTile> Path, out float Score)
{
    local XComGameState_LootDrop Drop;
    local XComGameState_Ability LootAbility;
    local XGUnit Visualizer;
    local MissionGoal Goal;
    local array<StateObjectReference> VisibleEnemies;
    local array<TTile> Tiles, CandidatePath;
    local AvailableAction Interaction;
    local GameRulesCache_VisibilityInfo Visibility;
    local TTile Tile, LootTile, ClosestTile;
    local vector LootLocation, CandidateLocation;
    local int TargetIndex, StandardAP, Sample, SampleCount, TileIndex, NeighborIndex, Drops;
    local float LootRange, InteractionScore, StartGoalDistance, Cost, Value, StartSupport;
    local bool bReadyObjective;

    Path.Length = 0;
    Score = 0.0;
    LootAbility = GetReadyLootAbility(UnitState, LootRange);
    if (LootAbility == none || !HasLegalMove(UnitState))
        return false;
    StandardAP = UnitState.NumActionPoints(class'X2CharacterTemplateManager'.default.StandardActionPoint);
    bReadyObjective = ChooseInteraction(UnitState, Interaction, TargetIndex, InteractionScore);
    GetVisibleThreats(UnitState, VisibleEnemies);
    if (!IsLootRouteAllowed(VisibleEnemies.Length > 0, HasBleedingSquadmate(UnitState),
        ShouldEvacuate(UnitState), bReadyObjective, HasActiveMissionDeadline(), StandardAP))
        return false;
    FindGoal(UnitState, Goal, VisibleEnemies);
    if (Goal.bCombat)
        return false;
    StartGoalDistance = TileDistance(UnitState.TileLocation, Goal.Tile);
    StartSupport = NearestSupportDistance(UnitState, UnitState.TileLocation);
    Visualizer = XGUnit(UnitState.GetVisualizer());
    if (Visualizer == none || Visualizer.m_kReachableTilesCache == none)
        return false;
    Visualizer.m_kReachableTilesCache.UpdateTileCacheIfNeeded();
    Visualizer.m_kReachableTilesCache.GetAllPathableTiles(Tiles, Visualizer.GetMobility());
    if (Tiles.Length == 0)
        return false;
    foreach `XCOMHISTORY.IterateByClassType(class'XComGameState_LootDrop', Drop)
    {
        LootTile = Drop.GetLootLocation();
        if (Drop.bRemoved || Drop.LootExpirationTurnsRemaining <= 0
            || !class'X2TacticalVisibilityHelpers'.static.CanSquadSeeLocation(
                UnitState.ControllingPlayer.ObjectID, LootTile)
            || !Drop.HasAvailableLoot() || !Drop.HasNonPsiLoot()
            || !Drop.HasAvailableLootForLooter(UnitState.GetReference()))
            continue;
        if (++Drops > 32)
            break;
        LootLocation = `XWORLD.GetPositionFromTileCoordinates(LootTile);
        ClosestTile = Visualizer.m_kReachableTilesCache.GetClosestReachableDestination(LootTile);
        SampleCount = Min(Tiles.Length + 9, Clamp(default.MaxCandidateTiles, 1, 96));
        for (Sample = 0; Sample < SampleCount; ++Sample)
        {
            if (Sample == 0)
                Tile = ClosestTile;
            else if (Sample < 9)
            {
                NeighborIndex = Sample - 1;
                if (NeighborIndex >= 4)
                    ++NeighborIndex;
                Tile = LootTile;
                Tile.X += NeighborIndex % 3 - 1;
                Tile.Y += NeighborIndex / 3 - 1;
            }
            else
            {
                TileIndex = (Sample - 9) * Max(0, Tiles.Length - 1) / Max(1, SampleCount - 10);
                Tile = Tiles[TileIndex];
            }
            Cost = Visualizer.m_kReachableTilesCache.GetPathCostToTile(Tile);
            if (Tile == UnitState.TileLocation || Cost < 0.0 || Cost > Visualizer.GetMobility()
                || !LootRouteMakesProgress(Goal.bFound, StartGoalDistance, TileDistance(Tile, Goal.Tile))
                || !IsSupportedAdvanceDestination(StartSupport, NearestSupportDistance(UnitState, Tile)))
                continue;
            CandidateLocation = `XWORLD.GetPositionFromTileCoordinates(Tile);
            // X2Condition_Lootable rejects Distance >= LootableRange.
            if (VSizeSq(CandidateLocation - LootLocation) >= Square(LootRange)
                || !`XWORLD.CanSeeTileToTile(Tile, LootTile, Visibility))
                continue;
            Value = ScoreLootMove(Cost, Drop.LootExpirationTurnsRemaining, Goal.bFound);
            if (Value <= Score)
                continue;
            CandidatePath.Length = 0;
            if (!Visualizer.m_kReachableTilesCache.BuildPathToTile(Tile, CandidatePath)
                || !class'APX_SquadPlanner'.static.PreparationPathIsSafe(UnitState, CandidatePath))
                continue;
            Path = CandidatePath;
            Score = Value;
        }
    }
    return Path.Length > 1;
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

// Directional cover and tile LOS estimate exposure, not next-turn hit chance.
// Enemy movement and ability conditions can still change the eventual shot.
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

static function float KnownThreatRisk(float Risk, bool bClearLOS, bool bMeleeOnly)
{
    // An enemy behind a solid obstruction is a possible next-turn threat, not
    // an immediate uncovered shot. Melee danger still depends on proximity.
    if (!bClearLOS && !bMeleeOnly)
        return Risk * 0.35;
    return Risk;
}

static function int MeleeMovementActions(int StandardActions, int AttackCost,
    int MovementRangeAdjustment, bool bMovingAttack)
{
    if (bMovingAttack)
        return Max(0, StandardActions - Max(0, MovementRangeAdjustment));
    return Max(0, StandardActions - Max(0, AttackCost));
}

static function float MeleeReachFromBudget(float MoveTilesPerAction,
    int MoveActions, float AttackRangeTiles)
{
    return FMax(0.0, MoveTilesPerAction) * float(Max(0, MoveActions))
        + FMax(0.0, AttackRangeTiles);
}

// A possible next-turn attack envelope, not a legal path or a prediction of
// enemy actions. Use a fresh ordinary turn budget, never the enemy's hidden AP.
// Unsupported melee styles keep the legacy estimate instead of inventing range.
static function float GetMeleeThreatReach(XComGameState_Unit Enemy)
{
    local StateObjectReference AbilityRef;
    local XComGameState_Ability Ability;
    local X2AbilityTemplate Template;
    local X2AbilityCost Cost;
    local X2AbilityCost_ActionPoints APCost;
    local X2AbilityTarget_MovingMelee MovingTarget;
    local X2AbilityTarget_Single SingleTarget;
    local X2AbilityMultiTarget_Cone Cone;
    local XComGameState_Item SourceWeapon;
    local int StandardActions, AttackCost, MoveActions;
    local float MoveTilesPerAction, AttackRangeTiles, BestReach;
    local bool bHasAPCost;

    if (Enemy == none || !Enemy.IsMeleeOnly() || Enemy.Abilities.Length > 64)
        return -1.0;
    StandardActions = class'X2CharacterTemplateManager'.default.StandardActionsPerTurn;
    if (StandardActions <= 0)
        return -1.0;
    MoveTilesPerAction = FMax(0.0, Enemy.GetCurrentStat(eStat_Mobility))
        * class'XComWorldData'.const.WORLD_METERS_TO_UNITS_MULTIPLIER
        / class'XComWorldData'.const.WORLD_StepSize;
    BestReach = -1.0;
    foreach Enemy.Abilities(AbilityRef)
    {
        Ability = XComGameState_Ability(`XCOMHISTORY.GetGameStateForObjectID(AbilityRef.ObjectID));
        if (Ability == none || Ability.OwnerStateObject.ObjectID != Enemy.ObjectID)
            continue;
        Template = Ability.GetMyTemplate();
        if (Template == none || Template.Hostility != eHostility_Offensive
            || Template.AbilityToHitCalc == none
            || !Template.AbilityToHitCalc.IsA('X2AbilityToHitCalc_StandardMelee'))
            continue;
        AttackCost = 0;
        bHasAPCost = false;
        foreach Template.AbilityCosts(Cost)
        {
            APCost = X2AbilityCost_ActionPoints(Cost);
            if (APCost == none)
                continue;
            // Even a bFreeCost ability can require AP to pass CanAfford.
            if (APCost.AllowedTypes.Find(class'X2CharacterTemplateManager'.default.StandardActionPoint) == INDEX_NONE)
                return -1.0;
            if (APCost.bAddWeaponTypicalCost)
            {
                SourceWeapon = Ability.GetSourceWeapon();
                if (SourceWeapon == none || X2WeaponTemplate(SourceWeapon.GetMyTemplate()) == none)
                    return -1.0;
            }
            bHasAPCost = true;
            AttackCost += APCost.GetPointCost(Ability, Enemy);
        }
        if (!bHasAPCost || AttackCost < 0 || AttackCost > StandardActions)
            return -1.0;
        MovingTarget = X2AbilityTarget_MovingMelee(Template.AbilityTargetStyle);
        Cone = X2AbilityMultiTarget_Cone(Template.AbilityMultiTargetStyle);
        if (MovingTarget != none && Template.AbilityMultiTargetStyle == none)
        {
            if (MovingTarget.MovementRangeAdjustment < 0)
                return -1.0;
            MoveActions = MeleeMovementActions(StandardActions, AttackCost,
                MovingTarget.MovementRangeAdjustment, true);
            AttackRangeTiles = class'XComWorldData'.const.WORLD_Melee_Range_Meters
                * class'XComWorldData'.const.WORLD_METERS_TO_UNITS_MULTIPLIER
                / class'XComWorldData'.const.WORLD_StepSize;
        }
        else if (Template.AbilityTargetStyle != none
            && Template.AbilityTargetStyle.Class == class'X2AbilityTarget_Single'
            && Template.AbilityMultiTargetStyle == none)
        {
            SingleTarget = X2AbilityTarget_Single(Template.AbilityTargetStyle);
            if (!SingleTarget.OnlyIncludeTargetsInsideWeaponRange)
                return -1.0;
            // Stock StandardMelee (including psi zombies) uses this stationary
            // style. The native getter resolves weapon range into world units;
            // iRange is not necessarily zero and must not be guessed in tiles.
            AttackRangeTiles = SingleTarget.GetHitRange(Ability) / class'XComWorldData'.const.WORLD_StepSize;
            if (AttackRangeTiles <= 0.0)
                return -1.0;
            MoveActions = MeleeMovementActions(StandardActions, AttackCost, 0, false);
        }
        else if (X2AbilityTarget_Cursor(Template.AbilityTargetStyle) != none && Cone != none)
        {
            // Cone.GetHitRange explicitly returns world units, including its
            // configured geometry. Cursor.GetCursorRangeMeters has a separate
            // contract and must not be interpreted as a tile distance here.
            AttackRangeTiles = Cone.GetHitRange(Ability) / class'XComWorldData'.const.WORLD_StepSize;
            if (AttackRangeTiles <= 0.0)
                return -1.0;
            MoveActions = MeleeMovementActions(StandardActions, AttackCost, 0, false);
        }
        else
            return -1.0;
        BestReach = FMax(BestReach, MeleeReachFromBudget(
            MoveTilesPerAction, MoveActions, AttackRangeTiles));
    }
    return BestReach;
}

// A caller-owned snapshot aligned with its unchanged visible-contact list.
// Build once per movement search; neither enemy templates nor class defaults
// are cached across decisions or mutated by this optimization.
static function GetMeleeThreatReaches(XComGameState_Unit UnitState,
    const out array<StateObjectReference> VisibleEnemies, out array<float> Reaches)
{
    local XComGameState_Unit Enemy;
    local int Index;

    Reaches.Length = VisibleEnemies.Length;
    for (Index = 0; Index < VisibleEnemies.Length; ++Index)
    {
        Reaches[Index] = -1.0;
        Enemy = XComGameState_Unit(`XCOMHISTORY.GetGameStateForObjectID(VisibleEnemies[Index].ObjectID));
        if (UnitState != none && Enemy != none && Enemy.IsAlive()
            && !Enemy.IsIncapacitated() && !Enemy.bRemovedFromPlay
            && UnitState.IsEnemyUnit(Enemy) && Enemy.IsMeleeOnly())
            Reaches[Index] = GetMeleeThreatReach(Enemy);
    }
}

static function float MeleeReachRisk(float Distance, float Reach)
{
    local float LegacyRisk;

    LegacyRisk = DirectionalRisk(0, Distance, false, true);
    if (Reach >= 0.0 && Distance <= Reach)
        return FMax(30.0, LegacyRisk);
    // Preserve residual legacy risk outside the recognized envelope. Crossing
    // its edge is not a guarantee of safety against all paths or abilities.
    return LegacyRisk;
}

// Caller-owned weights share the same visible-contact order as reach values.
// Snapshot once per search so weapon metadata is not re-read for every tile.
static function GetThreatWeights(XComGameState_Unit UnitState,
    const out array<StateObjectReference> VisibleEnemies, out array<float> Weights)
{
    local XComGameState_Unit Enemy;
    local int Index;

    Weights.Length = VisibleEnemies.Length;
    for (Index = 0; Index < VisibleEnemies.Length; ++Index)
    {
        Weights[Index] = 1.0;
        Enemy = XComGameState_Unit(`XCOMHISTORY.GetGameStateForObjectID(VisibleEnemies[Index].ObjectID));
        if (Enemy != none && Enemy.IsAlive() && !Enemy.bRemovedFromPlay
            && UnitState != none && UnitState.IsEnemyUnit(Enemy))
            Weights[Index] = class'APX_EnemyKnowledge'.static.ThreatWeight(Enemy);
    }
}

// Shared per-contact estimate for movement, defensive actions and diagnostics.
// Callers must first restrict Enemy to their player-visible hostile contacts.
static function float ThreatRiskAtTile(XComGameState_Unit UnitState,
    XComGameState_Unit Enemy, TTile Tile, optional float KnownMeleeReach=-2.0,
    optional float KnownThreatWeight=-1.0)
{
    local vector TargetLocation, EnemyLocation;
    local float Angle, Risk, MeleeReach, Weight, TargetWeight;
    local ECoverType Cover;
    local int CoverLevel;
    local GameRulesCache_VisibilityInfo Visibility;
    local TTile EnemyTile;
    local bool bClearLOS;

    if (UnitState == none || Enemy == none || !Enemy.IsAlive()
        || Enemy.IsIncapacitated() || Enemy.bRemovedFromPlay || !UnitState.IsEnemyUnit(Enemy))
        return 0.0;
    TargetWeight = class'APX_EnemyKnowledge'.static.TargetStatusWeight(UnitState);
    Weight = KnownThreatWeight;
    if (Weight < 0.0)
        Weight = class'APX_EnemyKnowledge'.static.ThreatWeight(Enemy);
    if (Enemy.IsMeleeOnly())
    {
        MeleeReach = KnownMeleeReach;
        if (MeleeReach == -2.0)
            MeleeReach = GetMeleeThreatReach(Enemy);
        // Legacy melee also ignores cover and LOS. A recognized -1 fallback
        // need not repeat the template scan or those unrelated native queries.
        return MeleeReachRisk(TileDistance(Tile, Enemy.TileLocation), MeleeReach) * Weight * TargetWeight;
    }
    TargetLocation = `XWORLD.GetPositionFromTileCoordinates(Tile);
    EnemyLocation = `XWORLD.GetPositionFromTileCoordinates(Enemy.TileLocation);
    Cover = `XWORLD.GetCoverTypeForTarget(EnemyLocation, TargetLocation, Angle);
    CoverLevel = 0;
    if (Cover == CT_Standing)
        CoverLevel = 2;
    else if (Cover == CT_MidLevel)
        CoverLevel = 1;
    Risk = DirectionalRisk(CoverLevel, TileDistance(Tile, Enemy.TileLocation),
        UnitState.GetMyTemplate().bCanTakeCover, Enemy.IsMeleeOnly());
    EnemyTile = Enemy.TileLocation;
    bClearLOS = `XWORLD.CanSeeTileToTile(EnemyTile, Tile, Visibility);
    return KnownThreatRisk(Risk, bClearLOS, Enemy.IsMeleeOnly()) * Weight * TargetWeight;
}

static function float ExposureRisk(XComGameState_Unit UnitState, TTile Tile,
    array<StateObjectReference> VisibleEnemies,
    optional const out array<float> MeleeThreatReaches,
    optional const out array<float> ThreatWeights)
{
    local XComGameState_Unit Enemy;
    local float Risk, SumRisk, WorstRisk, KnownMeleeReach, KnownWeight;
    local int Index;

    for (Index = 0; Index < VisibleEnemies.Length; ++Index)
    {
        Enemy = XComGameState_Unit(`XCOMHISTORY.GetGameStateForObjectID(VisibleEnemies[Index].ObjectID));
        KnownMeleeReach = -2.0;
        if (MeleeThreatReaches.Length == VisibleEnemies.Length)
            KnownMeleeReach = MeleeThreatReaches[Index];
        KnownWeight = -1.0;
        if (ThreatWeights.Length == VisibleEnemies.Length)
            KnownWeight = ThreatWeights[Index];
        Risk = ThreatRiskAtTile(UnitState, Enemy, Tile, KnownMeleeReach, KnownWeight);
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

static function int AdvanceCoverLevel(XComGameState_Unit UnitState, TTile Tile, TTile GoalTile)
{
    local vector GoalLocation, TargetLocation;
    local float Angle;
    local ECoverType Cover;

    if (!UnitState.GetMyTemplate().bCanTakeCover)
        return 0;
    GoalLocation = `XWORLD.GetPositionFromTileCoordinates(GoalTile);
    TargetLocation = `XWORLD.GetPositionFromTileCoordinates(Tile);
    Cover = `XWORLD.GetCoverTypeForTarget(GoalLocation, TargetLocation, Angle);
    if (Cover == CT_Standing)
        return 2;
    if (Cover == CT_MidLevel)
        return 1;
    return 0;
}

static function float AdvanceEndpointScore(float RouteProgress, int CoverLevel)
{
    // Prefer cover when it costs only a little progress. Progress is measured
    // along the actual A* route, so a necessary detour remains useful.
    return RouteProgress * 2.0 + float(Clamp(CoverLevel, 0, 2)) * 2.5;
}

static function float FiringPositionValue(float Distance, float PreferredRange,
    bool bClearLOS, bool bFlanking, bool bHighGround)
{
    local float Value;

    // Geometry through a wall cannot justify a move to "flank" a visible unit.
    if (!bClearLOS)
        return -20.0;
    Value = -Abs(Distance - PreferredRange);
    if (bFlanking && Distance <= 15.0)
        Value += 14.0;
    if (bHighGround && Distance <= 18.0)
        Value += 5.0;
    return Value;
}

static function bool IsKnownCombatTile(TTile Tile)
{
    local FOWTileStatus FogStatus;
    local byte GameplayFlags;
    local CachedCoverAndPeekData CoverData;
    local TTile VisibilityTile;

    if (`XWORLD.IsTileOutOfRange(Tile))
        return false;
    CoverData = `XWORLD.GetCachedCoverAndPeekData(Tile);
    VisibilityTile = Tile;
    if (CoverData.bDefaultTileValid != 0)
        VisibilityTile = CoverData.DefaultVisibilityCheckTile;
    `XWORLD.GetTileFOWValue(VisibilityTile, FogStatus, GameplayFlags);
    return FogStatus != eFOWTileStatus_NeverSeen;
}

static function bool IsSafeCombatExpansion(bool bCurrentlyVisible,
    float VerticalRise, bool bHasElevatedSupport)
{
    if (!bCurrentlyVisible)
        return false;
    // Do not establish a new rooftop firing position during an active fight.
    // A squadmate already holding that level provides a known support anchor.
    return VerticalRise <= 1.0 || bHasElevatedSupport;
}

static function bool IsSupportedCombatDestination(XComGameState_Unit UnitState, TTile Tile)
{
    local XComGameState_Unit Friendly;
    local bool bVisible, bElevatedSupport;

    bVisible = class'X2TacticalVisibilityHelpers'.static.CanSquadSeeLocation(
        UnitState.ControllingPlayer.ObjectID, Tile);
    if (Tile.Z > UnitState.TileLocation.Z + 1)
    {
        foreach `XCOMHISTORY.IterateByClassType(class'XComGameState_Unit', Friendly)
        {
            if (Friendly.ObjectID == UnitState.ObjectID || !Friendly.IsAlive()
                || Friendly.IsIncapacitated() || Friendly.bRemovedFromPlay
                || Friendly.GetAssociatedPlayerID() != UnitState.GetAssociatedPlayerID()
                || Friendly.GetTeam() != eTeam_XCom || Friendly.IsCivilian()
                || Friendly.GetMyTemplate().bIsCosmetic)
                continue;
            if (Abs(Friendly.TileLocation.Z - Tile.Z) <= 1
                && TileDistance(Friendly.TileLocation, Tile) <= 8.0)
            {
                bElevatedSupport = true;
                break;
            }
        }
    }
    return IsSafeCombatExpansion(bVisible, float(Tile.Z - UnitState.TileLocation.Z),
        bElevatedSupport);
}

static function float OffensivePositionScore(XComGameState_Unit UnitState, TTile Tile,
    array<StateObjectReference> VisibleEnemies)
{
    local XComGameState_Unit Enemy;
    local StateObjectReference EnemyRef;
    local vector SourceLocation, EnemyLocation;
    local ECoverType Cover;
    local float Distance, Angle, Value, BestValue;
    local GameRulesCache_VisibilityInfo Visibility;
    local TTile EnemyTile;
    local bool bClearLOS;

    BestValue = -10000.0;
    SourceLocation = `XWORLD.GetPositionFromTileCoordinates(Tile);
    foreach VisibleEnemies(EnemyRef)
    {
        Enemy = XComGameState_Unit(`XCOMHISTORY.GetGameStateForObjectID(EnemyRef.ObjectID));
        if (Enemy == none || !Enemy.IsAlive() || Enemy.IsIncapacitated()
            || !UnitState.IsEnemyUnit(Enemy))
            continue;
        Distance = TileDistance(Tile, Enemy.TileLocation);
        EnemyLocation = `XWORLD.GetPositionFromTileCoordinates(Enemy.TileLocation);
        Cover = `XWORLD.GetCoverTypeForTarget(SourceLocation, EnemyLocation, Angle);
        EnemyTile = Enemy.TileLocation;
        bClearLOS = `XWORLD.CanSeeTileToTile(Tile, EnemyTile, Visibility);
        Value = FiringPositionValue(Distance, default.PreferredCombatRangeTiles,
            bClearLOS, Enemy.GetMyTemplate().bCanTakeCover && Cover == CT_None,
            Tile.Z > EnemyTile.Z);
        BestValue = FMax(BestValue, Value);
    }
    if (BestValue == -10000.0)
        return 0.0;
    return BestValue;
}

static function float PositionScore(XComGameState_Unit UnitState, TTile Tile,
    TTile GoalTile, bool bCombatGoal, array<StateObjectReference> VisibleEnemies,
    optional const out array<float> MeleeThreatReaches,
    optional const out array<float> ThreatWeights)
{
    local float Result;
    if (bCombatGoal)
        Result = OffensivePositionScore(UnitState, Tile, VisibleEnemies);
    else
        Result = -TileDistance(Tile, GoalTile) * 3.0;
    return Result - ExposureRisk(UnitState, Tile, VisibleEnemies, MeleeThreatReaches, ThreatWeights)
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

static function float ScoreCombatReposition(float PositionGain, float CurrentRisk,
    float CandidateRisk, float HealthFraction, int StandardAP)
{
    local float RiskReduction, Result;

    // The old unbounded-delta scale repeatedly scored moves at 80, even above
    // an ally's 96% kill. Position utility is a heuristic, not damage removed.
    RiskReduction = FMax(0.0, CurrentRisk - CandidateRisk);
    Result = 16.0 + FMin(14.0, FMax(0.0, PositionGain) * 0.35)
        + FMin(16.0, RiskReduction * 0.3);
    if (HealthFraction < 0.5 && RiskReduction >= 8.0)
        Result += 16.0;
    // A last-AP retreat gives up this turn's shot or reaction. In the second
    // report two healthy retreats scored 46 and displaced 46% attacks. Keep
    // ordinary escapes useful when no attack exists, while reserving the high
    // retreat priority for a wounded soldier materially reducing exposure.
    if (StandardAP < 2 && !(HealthFraction < 0.5 && RiskReduction >= 8.0))
        return FMin(26.0, Result);
    return Result;
}

// Project only the blue move's AP cost into a local copy. The stock movement
// builder applies this ordinary cost; path-cost increases are outside blue range.
// Match the native preference for specific AP types before standard points.
static function bool ActionPointsAfterBlueMove(XComGameState_Unit UnitState,
    out array<name> RemainingPoints)
{
    local XComGameState_Ability MoveAbility;
    local StateObjectReference MoveRef;
    local X2AbilityCost Cost;
    local X2AbilityCost_ActionPoints APCost;
    local int TypeIndex, PointIndex, PointCost, Consumed;

    RemainingPoints.Length = 0;
    if (UnitState == none)
        return false;
    RemainingPoints = UnitState.ActionPoints;
    MoveRef = UnitState.FindAbility('StandardMove');
    MoveAbility = XComGameState_Ability(`XCOMHISTORY.GetGameStateForObjectID(
        MoveRef.ObjectID));
    if (MoveAbility == none || MoveAbility.GetMyTemplate() == none)
        return false;
    foreach MoveAbility.GetMyTemplate().AbilityCosts(Cost)
    {
        APCost = X2AbilityCost_ActionPoints(Cost);
        if (APCost == none || APCost.bFreeCost)
            continue;
        if (APCost.ConsumeAllPoints(MoveAbility, UnitState))
        {
            RemainingPoints.Length = 0;
            continue;
        }
        PointCost = APCost.GetPointCost(MoveAbility, UnitState);
        Consumed = 0;
        for (TypeIndex = APCost.AllowedTypes.Length - 1;
            TypeIndex >= 0 && Consumed < PointCost; --TypeIndex)
        {
            for (PointIndex = RemainingPoints.Length - 1;
                PointIndex >= 0 && Consumed < PointCost; --PointIndex)
            {
                if (RemainingPoints[PointIndex] == APCost.AllowedTypes[TypeIndex])
                {
                    RemainingPoints.Remove(PointIndex, 1);
                    ++Consumed;
                }
            }
        }
        if (Consumed < PointCost)
            return false;
    }
    return true;
}

static function bool CanAttackWithActionPoints(XComGameState_Ability Ability,
    XComGameState_Unit UnitState, const out array<name> Points)
{
    local X2AbilityCost Cost;
    local X2AbilityCost_ActionPoints APCost;
    local int TypeIndex, PointIndex, AllowedPoints;

    if (Ability == none || Ability.GetMyTemplate() == none || UnitState == none)
        return false;
    foreach Ability.GetMyTemplate().AbilityCosts(Cost)
    {
        APCost = X2AbilityCost_ActionPoints(Cost);
        if (APCost == none)
            continue;
        // bFreeCost skips consumption, but native CanAfford still checks the
        // required points. Do not grant free abilities unavailable at zero AP.
        AllowedPoints = 0;
        for (TypeIndex = 0; TypeIndex < APCost.AllowedTypes.Length; ++TypeIndex)
        {
            for (PointIndex = 0; PointIndex < Points.Length; ++PointIndex)
            {
                if (Points[PointIndex] == APCost.AllowedTypes[TypeIndex])
                    ++AllowedPoints;
            }
        }
        if (AllowedPoints < APCost.GetPointCost(Ability, UnitState))
            return false;
    }
    return true;
}

// Compare AP eligibility on the current legal target list, not future LOS,
// range, ammo changes or a speculative flank at the destination. No AP or
// game-state objects are changed. Moving melee is handled by its own planner.
static function GetMoveAttackOptions(XComGameState_Unit UnitState,
    const out array<StateObjectReference> VisibleEnemies,
    out float BestNow, out float BestAfterMove)
{
    local GameRulesCache_Unit Cache;
    local AvailableAction Candidate;
    local AvailableTarget Target;
    local XComGameState_Ability Ability;
    local X2AbilityTemplate Template;
    local XComGameState_Unit TargetUnit;
    local array<name> RemainingPoints;
    local float Value;
    local bool bAffordableAfterMove;

    BestNow = 0.0;
    BestAfterMove = 0.0;
    if (UnitState == none || `TACTICALRULES == none || VisibleEnemies.Length == 0
        || !ActionPointsAfterBlueMove(UnitState, RemainingPoints)
        || !`TACTICALRULES.GetGameRulesCache_Unit(UnitState.GetReference(), Cache))
        return;
    foreach Cache.AvailableActions(Candidate)
    {
        if (!Candidate.bInputTriggered || Candidate.AvailableCode != 'AA_Success'
            || Candidate.bFreeAim)
            continue;
        Ability = XComGameState_Ability(`XCOMHISTORY.GetGameStateForObjectID(Candidate.AbilityObjectRef.ObjectID));
        if (Ability == none || Ability.OwnerStateObject.ObjectID != UnitState.ObjectID
            || class'APX_CombatPlanner'.default.AttackAbilities.Find(Ability.GetMyTemplateName()) == INDEX_NONE)
            continue;
        Template = Ability.GetMyTemplate();
        if (Template == none || Template.AbilityToHitCalc == none
            || Template.AbilityToHitCalc.IsA('X2AbilityToHitCalc_StandardMelee')
            || (Template.TargetingMethod != none && Template.TargetingMethod.default.ProvidesPath)
            || (Template.AbilityTargetStyle != none && Template.AbilityTargetStyle.IsA('X2AbilityTarget_MovingMelee')))
            continue;
        if (Template.AbilityMultiTargetStyle != none
            && !Template.AbilityMultiTargetStyle.IsA('X2AbilityMultiTarget_Volt')
            && !Template.AbilityMultiTargetStyle.IsA('X2AbilityMultiTarget_BurstFire'))
            continue;
        bAffordableAfterMove = CanAttackWithActionPoints(Ability, UnitState, RemainingPoints);
        foreach Candidate.AvailableTargets(Target)
        {
            TargetUnit = XComGameState_Unit(`XCOMHISTORY.GetGameStateForObjectID(Target.PrimaryTarget.ObjectID));
            if (!class'APX_CombatPlanner'.static.IsVisibleHostile(UnitState, TargetUnit, VisibleEnemies)
                || !class'APX_CombatPlanner'.static.AdditionalTargetsAreSafe(UnitState, Target, VisibleEnemies))
                continue;
            Value = class'APX_CombatPlanner'.static.ScoreAttack(Ability, Target, TargetUnit);
            BestNow = FMax(BestNow, Value);
            if (bAffordableAfterMove)
                BestAfterMove = FMax(BestAfterMove, Value);
        }
    }
}

static function float MoveOpportunityPenalty(float BestNow, float BestAfterMove,
    float HealthFraction, float RiskReduction)
{
    // Preserve the existing emergency escape for a wounded, exposed soldier.
    if (HealthFraction < 0.5 && RiskReduction >= 8.0)
        return 0.0;
    return FMax(0.0, BestNow - BestAfterMove);
}

// Rescue is distinct from an ordinary firing-position move. The downed own
// squadmate is the destination anchor; live-squad spacing must not exclude
// every approach to a casualty who fell behind. Risk still reduces its value.
static function float ScoreRescueApproach(bool bCanTreatNow, float Progress,
    float CurrentRisk, float DestinationRisk, float HealthFraction, int BleedingTurns)
{
    local float Value, Increase;

    if (!bCanTreatNow && (Progress < 2.0 || BleedingTurns <= 1))
        return -10000.0;
    Value = 180.0;
    if (bCanTreatNow)
        Value = 260.0;
    Value += FMin(12.0, FMax(0.0, Progress) * 2.0);
    Value += float(Clamp(3 - BleedingTurns, 0, 2)) * 8.0;
    Increase = FMax(0.0, DestinationRisk - CurrentRisk);
    Value -= DestinationRisk * 0.15 + Increase * (2.0 - FClamp(HealthFraction, 0.0, 1.0));
    if (HealthFraction <= 0.45 && Increase > 0.0)
        Value -= 60.0;
    return Value;
}

static function bool ChooseRescueMove(XComGameState_Unit UnitState,
    out array<TTile> Path, out float Score, out int PatientID)
{
    local XComGameState_Unit Patient;
    local XComGameState_Ability Stabilize;
    local XGUnit Visualizer;
    local array<TTile> Tiles, CandidatePath;
    local array<name> RemainingPoints;
    local array<StateObjectReference> VisibleEnemies;
    local array<float> MeleeThreatReaches;
    local array<float> ThreatWeights;
    local TTile Tile, ClosestTile;
    local int Sample, SampleCount, TileIndex, NeighborIndex, PathIndex, Turns;
    local float Cost, Distance, CandidateDistance, CurrentRisk, Risk, Value, HealthFraction;
    local bool bCanTreatNow, bSafe;

    Path.Length = 0;
    Score = 0.0;
    PatientID = 0;
    if (UnitState == none || !UnitState.IsAbleToAct() || !HasLegalMove(UnitState)
        || !ActionPointsAfterBlueMove(UnitState, RemainingPoints))
        return false;
    Visualizer = XGUnit(UnitState.GetVisualizer());
    if (Visualizer == none || Visualizer.m_kReachableTilesCache == none)
        return false;
    Visualizer.m_kReachableTilesCache.UpdateTileCacheIfNeeded();
    Visualizer.m_kReachableTilesCache.GetAllPathableTiles(Tiles, Visualizer.GetMobility());
    if (Tiles.Length == 0)
        return false;
    GetVisibleThreats(UnitState, VisibleEnemies);
    GetMeleeThreatReaches(UnitState, VisibleEnemies, MeleeThreatReaches);
    GetThreatWeights(UnitState, VisibleEnemies, ThreatWeights);
    CurrentRisk = ExposureRisk(UnitState, UnitState.TileLocation, VisibleEnemies, MeleeThreatReaches, ThreatWeights);
    HealthFraction = UnitState.GetCurrentStat(eStat_HP) / FMax(1.0, UnitState.GetMaxStat(eStat_HP));
    foreach `XCOMHISTORY.IterateByClassType(class'XComGameState_Unit', Patient)
    {
        Stabilize = class'APX_CombatPlanner'.static.GetReadyStabilizeAbility(UnitState, Patient);
        if (Stabilize == none || !CanAttackWithActionPoints(Stabilize, UnitState, RemainingPoints))
            continue;
        Turns = Patient.GetBleedingOutTurnsRemaining();
        Distance = TileDistance(UnitState.TileLocation, Patient.TileLocation);
        ClosestTile = Visualizer.m_kReachableTilesCache.GetClosestReachableDestination(Patient.TileLocation);
        SampleCount = Min(Tiles.Length + 9, Clamp(default.MaxCandidateTiles, 1, 96));
        for (Sample = 0; Sample < SampleCount; ++Sample)
        {
            // Include native closest and adjacent treatment positions before
            // sampling the larger tile set. Do not use an occupied body tile
            // as though it were automatically a legal movement destination.
            if (Sample == 0)
                Tile = ClosestTile;
            else if (Sample < 9)
            {
                NeighborIndex = Sample - 1;
                if (NeighborIndex >= 4)
                    ++NeighborIndex;
                Tile = Patient.TileLocation;
                Tile.X += NeighborIndex % 3 - 1;
                Tile.Y += NeighborIndex / 3 - 1;
            }
            else
            {
                TileIndex = (Sample - 9) * Max(0, Tiles.Length - 1) / Max(1, SampleCount - 10);
                Tile = Tiles[TileIndex];
            }
            Cost = Visualizer.m_kReachableTilesCache.GetPathCostToTile(Tile);
            if (Tile == UnitState.TileLocation || Cost < 0.0 || Cost > Visualizer.GetMobility()
                || !IsKnownCombatTile(Tile)
                || !class'X2TacticalVisibilityHelpers'.static.CanSquadSeeLocation(
                    UnitState.ControllingPlayer.ObjectID, Tile))
                continue;
            bCanTreatNow = class'APX_CombatPlanner'.static.CanStabilizeFromTile(
                UnitState, Patient, Stabilize, Tile);
            CandidateDistance = TileDistance(Tile, Patient.TileLocation);
            Risk = ExposureRisk(UnitState, Tile, VisibleEnemies, MeleeThreatReaches, ThreatWeights);
            Value = ScoreRescueApproach(bCanTreatNow, Distance - CandidateDistance,
                CurrentRisk, Risk, HealthFraction, Turns) - Cost * 0.25;
            if (Value <= Score)
                continue;
            CandidatePath.Length = 0;
            if (!Visualizer.m_kReachableTilesCache.BuildPathToTile(Tile, CandidatePath)
                || CandidatePath.Length < 2)
                continue;
            bSafe = true;
            for (PathIndex = 1; PathIndex < CandidatePath.Length; ++PathIndex)
            {
                if (class'XComPath'.static.TileContainsHazard(UnitState, CandidatePath[PathIndex])
                    || !IsKnownCombatTile(CandidatePath[PathIndex])
                    || !class'X2TacticalVisibilityHelpers'.static.CanSquadSeeLocation(
                        UnitState.ControllingPlayer.ObjectID, CandidatePath[PathIndex]))
                {
                    bSafe = false;
                    break;
                }
            }
            if (bSafe)
            {
                Path = CandidatePath;
                Score = Value;
                PatientID = Patient.ObjectID;
            }
        }
    }
    return Path.Length > 1;
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
    local float StartSupport, PathCost, CandidateValue, BestValue;

    Path.Length = 0;
    bRequireSupport = !ShouldEvacuate(UnitState);
    StartSupport = NearestSupportDistance(UnitState, UnitState.TileLocation);
    BestValue = -1000000.0;
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
            CandidateValue = AdvanceEndpointScore(float(Index),
                AdvanceCoverLevel(UnitState, FullPath[Index], GoalTile));
            CandidateValue += SquadPositionScore(UnitState, FullPath[Index]);
            if (CandidateValue > BestValue)
            {
                BestValue = CandidateValue;
                Path = CandidatePath;
            }
        }
    }
    return Path.Length > 1;
}

static function bool ChooseMove(XComGameState_Unit UnitState,
    out array<TTile> Path, out float Score)
{
    local XGUnit UnitVisualizer;
    local array<TTile> Tiles, CandidatePath;
    local array<StateObjectReference> VisibleEnemies;
    local array<float> MeleeThreatReaches;
    local array<float> ThreatWeights;
    local TTile GoalTile, Tile, ClosestTile;
    local MissionGoal Goal;
    local bool bCombatGoal, bSafe, bRequireSupport;
    local int Index, PathIndex, SampleIndex, SampleCount;
    local float CurrentScore, CandidateScore, BestScore, CurrentRisk, CandidateRisk, PathCost, StartSupport, BestRisk;
    local float BestAttackNow, BestAttackAfterMove, HealthFraction;

    Path.Length = 0;
    Score = 0;
    if (!HasLegalMove(UnitState)
        || !FindGoal(UnitState, Goal, VisibleEnemies))
        return false;
    GoalTile = Goal.Tile;
    bCombatGoal = Goal.bCombat;
    bRequireSupport = !ShouldEvacuate(UnitState);
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
    GetMeleeThreatReaches(UnitState, VisibleEnemies, MeleeThreatReaches);
    GetThreatWeights(UnitState, VisibleEnemies, ThreatWeights);
    CurrentScore = PositionScore(UnitState, UnitState.TileLocation, GoalTile,
        bCombatGoal, VisibleEnemies, MeleeThreatReaches, ThreatWeights);
    BestScore = CurrentScore + FMax(1.0, default.MinimumPositionGain);
    CurrentRisk = ExposureRisk(UnitState, UnitState.TileLocation, VisibleEnemies, MeleeThreatReaches, ThreatWeights);
    BestRisk = CurrentRisk;

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
            || (bCombatGoal && !IsKnownCombatTile(Tile))
            || (bCombatGoal && !IsSupportedCombatDestination(UnitState, Tile))
            || PathCost < 0.0 || PathCost > UnitVisualizer.GetMobility()
            || (bRequireSupport && !IsSupportedAdvanceDestination(StartSupport,
                NearestSupportDistance(UnitState, Tile))))
            continue;
        CandidateRisk = ExposureRisk(UnitState, Tile, VisibleEnemies, MeleeThreatReaches, ThreatWeights);
        CandidateScore = PositionScore(UnitState, Tile, GoalTile, bCombatGoal,
            VisibleEnemies, MeleeThreatReaches, ThreatWeights);
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
                || (bCombatGoal && !IsKnownCombatTile(CandidatePath[PathIndex]))
                || (bCombatGoal && !class'X2TacticalVisibilityHelpers'.static.CanSquadSeeLocation(
                    UnitState.ControllingPlayer.ObjectID, CandidatePath[PathIndex]))
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
            BestRisk = CandidateRisk;
            Path = CandidatePath;
        }
    }
    if (Path.Length < 2)
        return false;
    if (bCombatGoal)
    {
        HealthFraction = UnitState.GetCurrentStat(eStat_HP) / FMax(1.0, UnitState.GetMaxStat(eStat_HP));
        Score = ScoreCombatReposition(BestScore - CurrentScore, CurrentRisk, BestRisk,
            HealthFraction, UnitState.NumActionPoints());
        GetMoveAttackOptions(UnitState, VisibleEnemies, BestAttackNow, BestAttackAfterMove);
        Score -= MoveOpportunityPenalty(BestAttackNow, BestAttackAfterMove,
            HealthFraction, CurrentRisk - BestRisk);
    }
    else
        Score = 20 + FMin(60, BestScore - CurrentScore);
    return true;
}
