// Conservative move-and-shot forecasts for already legal basic ranged targets.
// Remote visibility is native; the projected chance is a bounded heuristic.
// Never move a history object to ask the current-position shot calculator about
// a hypothetical tile. The controller evaluates real actions again after moving.
class APX_RepositionPlanner extends Object
    dependson(X2GameRuleset, X2TacticalGameRulesetDataStructures, XComWorldData,
        X2GameRulesetVisibilityDataStructures);

struct AttackForecast
{
    var XComGameState_Ability Ability;
    var XComGameState_Unit TargetUnit;
    var X2WeaponTemplate Weapon;
    var int NativeChance;
    var int CurrentRangeModifier;
    var int CoverRecovery;
    var float NativeScore;
    var bool bIgnoreCover;
};

static function int RangeBandIndex(int Distance, int Length)
{
    if (Length <= 0)
        return 0;
    return Clamp(Distance, 0, Length - 1);
}

static function int ProjectedHitChance(int NativeChance, int RangeDelta, int CoverRecovery)
{
    // Leave uncertainty even when the simple geometric estimate reaches 100%.
    return Clamp(NativeChance + Clamp(RangeDelta + CoverRecovery, -35, 35), 0, 95);
}

static function float ProjectedShotScore(float NativeScore, int NativeChance, int ProjectedChance)
{
    if (NativeChance <= 0 || NativeScore <= 5.0)
        return -10000.0;
    // For a basic one-target shot, ScoreAttack's damage and kill terms are
    // linear in hit chance, with a constant 5. No crit improvement is invented.
    return 5.0 + (NativeScore - 5.0) * float(ProjectedChance) / float(NativeChance);
}

static function float MoveAndShotScore(float NativeScore, float ProjectedScore,
    int NativeChance, int ProjectedChance, float CurrentRisk, float CandidateRisk,
    float PathCost, int ActionPoints)
{
    if (ActionPoints < 2 || PathCost < 0.0)
        return -10000.0;
    if (ProjectedChance - NativeChance < 12 || ProjectedScore - NativeScore < 8.0)
        return -10000.0;
    if (CandidateRisk > CurrentRisk)
        return -10000.0;
    // Pay for an extra action and its imperfect forecast. Ordinary defensive
    // moves keep their existing score; this value represents the retained shot.
    return ProjectedScore - 6.0 - FMin(8.0, PathCost * 0.2);
}

static function bool SupportsForecast(XComGameState_Ability Ability)
{
    local X2AbilityTemplate Template;
    local X2AbilityToHitCalc_StandardAim Aim;

    if (Ability == none || (Ability.GetMyTemplateName() != 'StandardShot'
        && Ability.GetMyTemplateName() != 'PistolStandardShot'))
        return false;
    Template = Ability.GetMyTemplate();
    if (Template == none || Template.AbilityToHitCalc == none
        || Template.AbilityToHitCalc.Class != class'X2AbilityToHitCalc_StandardAim'
        || X2AbilityTarget_Single(Template.AbilityTargetStyle) == none
        || Template.AbilityMultiTargetStyle != none
        || (Template.TargetingMethod != none && Template.TargetingMethod.default.ProvidesPath))
        return false;
    Aim = X2AbilityToHitCalc_StandardAim(Template.AbilityToHitCalc);
    return !Aim.bMeleeAttack && !Aim.bIndirectFire && !Aim.bReactionFire
        && !Aim.bGuaranteedHit && Aim.FinalMultiplier == 1.0;
}

static function bool CanForecastUnit(XComGameState_Unit UnitState)
{
    if (UnitState == none || `XCOMHISTORY == none || `XWORLD == none
        || !UnitState.IsAbleToAct() || UnitState.IsConcealed()
        || UnitState.NumActionPoints() < 2
        || !class'APX_MissionPlanner'.static.HasLegalMove(UnitState)
        || class'APX_MissionPlanner'.static.ShouldEvacuate(UnitState)
        || class'APX_HazardKnowledge'.static.HasBlockingHazard(UnitState, UnitState.TileLocation))
        return false;
    // These own passives can lose a to-hit bonus after movement. Do not carry
    // the current native bonus into a speculative shot, even if inactive now.
    return UnitState.FindAbility('SteadyHands').ObjectID <= 0
        && UnitState.FindAbility('Aim').ObjectID <= 0;
}

static function bool EndsTurnForForecast(XComGameState_Ability Ability,
    XComGameState_Unit UnitState)
{
    local X2AbilityCost Cost;
    local X2AbilityCost_ActionPoints APCost;

    if (Ability == none || Ability.GetMyTemplate() == none || UnitState == none)
        return false;
    // This forecast values one retained shot. A repeatable shot may instead
    // permit two attacks now (SkirmisherStrike, Quickdraw, LightEmUp, etc.).
    // Leave those sequences to action-chain planning rather than losing one
    // of the shots merely because the remaining one would be more accurate.
    foreach Ability.GetMyTemplate().AbilityCosts(Cost)
    {
        APCost = X2AbilityCost_ActionPoints(Cost);
        if (APCost != none && !APCost.bFreeCost && APCost.ConsumeAllPoints(Ability, UnitState))
            return true;
    }
    return false;
}

static function bool HasVisibleRuler(const out array<StateObjectReference> VisibleEnemies)
{
    local StateObjectReference EnemyRef;
    local XComGameState_Unit Enemy;
    foreach VisibleEnemies(EnemyRef)
    {
        Enemy = XComGameState_Unit(`XCOMHISTORY.GetGameStateForObjectID(EnemyRef.ObjectID));
        // A possible reaction to the extra action is not a next-turn threat.
        // Installed capability is enough to decline; never read its readiness.
        if (Enemy != none && Enemy.FindAbility('AlienRulerActionSystem').ObjectID > 0)
            return true;
    }
    return false;
}

static function GatherForecasts(XComGameState_Unit UnitState,
    const out array<StateObjectReference> VisibleEnemies, out array<AttackForecast> Forecasts)
{
    local GameRulesCache_Unit Cache;
    local GameRulesCache_VisibilityInfo Visibility;
    local AvailableAction Candidate;
    local AvailableTarget Target;
    local XComGameState_Ability Ability;
    local XComGameState_Item WeaponState;
    local XComGameState_Unit TargetUnit;
    local X2AbilityToHitCalc_StandardAim Aim;
    local ShotBreakdown Breakdown;
    local array<name> RemainingPoints;
    local AttackForecast Forecast;
    local int ActionIndex, TargetIndex, ModifierIndex, Distance;

    Forecasts.Length = 0;
    if (`TACTICALRULES == none || `TACTICALRULES.VisibilityMgr == none || !CanForecastUnit(UnitState)
        || VisibleEnemies.Length == 0 || VisibleEnemies.Length > 64
        || HasVisibleRuler(VisibleEnemies)
        || !class'APX_MissionPlanner'.static.ActionPointsAfterBlueMove(UnitState, RemainingPoints)
        || RemainingPoints.Length == 0
        || !`TACTICALRULES.GetGameRulesCache_Unit(UnitState.GetReference(), Cache))
        return;
    for (ActionIndex = 0; ActionIndex < Min(64, Cache.AvailableActions.Length); ++ActionIndex)
    {
        Candidate = Cache.AvailableActions[ActionIndex];
        if (!Candidate.bInputTriggered || Candidate.AvailableCode != 'AA_Success' || Candidate.bFreeAim)
            continue;
        Ability = XComGameState_Ability(`XCOMHISTORY.GetGameStateForObjectID(Candidate.AbilityObjectRef.ObjectID));
        if (!SupportsForecast(Ability) || Ability.OwnerStateObject.ObjectID != UnitState.ObjectID
            || !EndsTurnForForecast(Ability, UnitState)
            || !class'APX_MissionPlanner'.static.CanAttackWithActionPoints(Ability, UnitState, RemainingPoints))
            continue;
        WeaponState = Ability.GetSourceWeapon();
        if (WeaponState == none || X2WeaponTemplate(WeaponState.GetMyTemplate()) == none)
            continue;
        Aim = X2AbilityToHitCalc_StandardAim(Ability.GetMyTemplate().AbilityToHitCalc);
        for (TargetIndex = 0; TargetIndex < Min(8, Candidate.AvailableTargets.Length); ++TargetIndex)
        {
            Target = Candidate.AvailableTargets[TargetIndex];
            TargetUnit = XComGameState_Unit(`XCOMHISTORY.GetGameStateForObjectID(Target.PrimaryTarget.ObjectID));
            if (Target.AdditionalTargets.Length > 0
                || !class'APX_CombatPlanner'.static.IsVisibleHostile(UnitState, TargetUnit, VisibleEnemies)
                || !`TACTICALRULES.VisibilityMgr.GetVisibilityInfo(UnitState.ObjectID,
                    TargetUnit.ObjectID, Visibility) || !Visibility.bVisibleGameplay)
                continue;
            Forecast.NativeChance = Clamp(Ability.GetShotBreakdown(Target, Breakdown), 0, 100);
            if (Forecast.NativeChance < class'APX_CombatPlanner'.default.MinimumHitChance
                || Forecast.NativeChance > 83 || Breakdown.SpecialGuaranteedHit != ''
                || Breakdown.Modifiers.Length > 64)
                continue;
            Forecast.NativeScore = class'APX_CombatPlanner'.static.ScoreAttack(Ability, Target, TargetUnit);
            if (Forecast.NativeScore <= 5.0)
                continue;
            Forecast.Ability = Ability;
            Forecast.TargetUnit = TargetUnit;
            Forecast.Weapon = X2WeaponTemplate(WeaponState.GetMyTemplate());
            Forecast.bIgnoreCover = Aim.bIgnoreCoverBonus || !TargetUnit.CanTakeCover();
            Forecast.CoverRecovery = 0;
            // A destination with no cover removes these CURRENT native terms.
            // No positive future angle/flanking/crit bonus is manufactured.
            if (!Forecast.bIgnoreCover)
            {
                for (ModifierIndex = 0; ModifierIndex < Breakdown.Modifiers.Length; ++ModifierIndex)
                {
                    if (Breakdown.Modifiers[ModifierIndex].Reason == class'XLocalizedData'.default.TargetLowCover
                        || Breakdown.Modifiers[ModifierIndex].Reason == class'XLocalizedData'.default.TargetHighCover
                        || Breakdown.Modifiers[ModifierIndex].Reason == class'XLocalizedData'.default.BadAngleToTargetCover
                        || Breakdown.Modifiers[ModifierIndex].Reason == class'XLocalizedData'.default.AngleToTargetCover)
                        Forecast.CoverRecovery -= Breakdown.Modifiers[ModifierIndex].Value;
                }
            }
            Distance = UnitState.TileDistanceBetween(TargetUnit);
            Forecast.CurrentRangeModifier = 0;
            if (Forecast.Weapon.RangeAccuracy.Length > 0)
                Forecast.CurrentRangeModifier = Forecast.Weapon.RangeAccuracy[
                    RangeBandIndex(Distance, Forecast.Weapon.RangeAccuracy.Length)];
            Forecasts.AddItem(Forecast);
            if (Forecasts.Length >= 16)
                return;
        }
    }
}

static function bool ProjectAtTile(XComGameState_Unit UnitState, TTile Tile,
    const out array<AttackForecast> Forecasts, out int TargetID, out int NativeChance,
    out int ProjectedChance, out float NativeScore, out float ProjectedScore)
{
    local GameRulesCache_VisibilityInfo Visibility, EmptyVisibility;
    local AttackForecast Forecast;
    local vector SourceLocation, TargetLocation;
    local int Distance, RangeModifier, Chance;
    local float Value;

    TargetID = 0;
    NativeChance = 0;
    ProjectedChance = 0;
    NativeScore = 0.0;
    ProjectedScore = -10000.0;
    // Keep the native height bonuses unchanged; rooftop forecasts need a more
    // complete model than raw Z comparisons, including special unit height.
    if (UnitState == none || Tile.Z != UnitState.TileLocation.Z || `TACTICALRULES == none
        || `TACTICALRULES.VisibilityMgr == none || `XCOMHISTORY == none || `XWORLD == none)
        return false;
    SourceLocation = `XWORLD.GetPositionFromTileCoordinates(Tile);
    foreach Forecasts(Forecast)
    {
        Visibility = EmptyVisibility;
        Visibility.SourceID = UnitState.ObjectID;
        Visibility.TargetID = Forecast.TargetUnit.ObjectID;
        if (!`TACTICALRULES.VisibilityMgr.GetVisibilityInfoFromRemoteLocation(
            UnitState.ObjectID, Tile, Forecast.TargetUnit.ObjectID, Visibility)
            || !Visibility.bClearLOS
            || !`TACTICALRULES.VisibilityMgr.EvaluateConditions(Visibility,
                `XCOMHISTORY.GetCurrentHistoryIndex(),
                class'UITacticalHUD_EnemyPreview'.default.LivingHostileGameplayVisibleFilter)
            || (!Forecast.bIgnoreCover && Visibility.TargetCover != CT_None)
            || !X2AbilityTarget_Single(Forecast.Ability.GetMyTemplate().AbilityTargetStyle).
                ValidatePrimaryTargetOptionFromRemoteLocation(UnitState, Tile, Forecast.TargetUnit))
            continue;
        TargetLocation = `XWORLD.GetPositionFromTileCoordinates(Forecast.TargetUnit.TileLocation);
        // Match Unit.TileDistanceBetween: world-space length, integer truncation.
        Distance = int(VSize(SourceLocation - TargetLocation) / class'XComWorldData'.const.WORLD_StepSize);
        RangeModifier = 0;
        if (Forecast.Weapon.RangeAccuracy.Length > 0)
            RangeModifier = Forecast.Weapon.RangeAccuracy[RangeBandIndex(Distance, Forecast.Weapon.RangeAccuracy.Length)];
        Chance = ProjectedHitChance(Forecast.NativeChance,
            RangeModifier - Forecast.CurrentRangeModifier, Forecast.CoverRecovery);
        Value = ProjectedShotScore(Forecast.NativeScore, Forecast.NativeChance, Chance);
        if (Chance - Forecast.NativeChance >= 12 && Value - Forecast.NativeScore >= 8.0
            && Value > ProjectedScore)
        {
            TargetID = Forecast.TargetUnit.ObjectID;
            NativeChance = Forecast.NativeChance;
            ProjectedChance = Chance;
            NativeScore = Forecast.NativeScore;
            ProjectedScore = Value;
        }
    }
    return TargetID > 0;
}

// Selected-move telemetry reuses the same bounded projection, never a fake state.
static function bool EvaluateDestination(XComGameState_Unit UnitState, TTile Tile,
    out int TargetID, out int NativeChance, out int ProjectedChance,
    out float NativeAttackScore, out float ProjectedAttackScore)
{
    local array<StateObjectReference> VisibleEnemies;
    local array<AttackForecast> Forecasts;
    class'APX_MissionPlanner'.static.GetVisibleThreats(UnitState, VisibleEnemies);
    GatherForecasts(UnitState, VisibleEnemies, Forecasts);
    return ProjectAtTile(UnitState, Tile, Forecasts, TargetID, NativeChance,
        ProjectedChance, NativeAttackScore, ProjectedAttackScore);
}

static function bool ChooseMove(XComGameState_Unit UnitState,
    out array<TTile> Path, out float Score)
{
    local XGUnit Visualizer;
    local array<TTile> Tiles, CandidatePath;
    local array<StateObjectReference> VisibleEnemies;
    local array<AttackForecast> Forecasts;
    local array<float> Reaches, Weights;
    local TTile Tile;
    local float CurrentRisk, CandidateRisk, CurrentSupport, PathCost, Value;
    local float NativeScore, ProjectedScore;
    local int SampleIndex, Index, Samples, PathIndex, TargetID, NativeChance, ProjectedChance;
    local bool bSafe;

    Path.Length = 0;
    Score = -10000.0;
    if (!CanForecastUnit(UnitState))
        return false;
    class'APX_MissionPlanner'.static.GetVisibleThreats(UnitState, VisibleEnemies);
    GatherForecasts(UnitState, VisibleEnemies, Forecasts);
    if (Forecasts.Length == 0)
        return false;
    Visualizer = XGUnit(UnitState.GetVisualizer());
    if (Visualizer == none || Visualizer.m_kReachableTilesCache == none)
        return false;
    Visualizer.m_kReachableTilesCache.UpdateTileCacheIfNeeded();
    Visualizer.m_kReachableTilesCache.GetAllPathableTiles(Tiles, Visualizer.GetMobility());
    Tiles.InsertItem(0, Visualizer.m_kReachableTilesCache.GetClosestReachableDestination(Forecasts[0].TargetUnit.TileLocation));
    Samples = Min(64, Tiles.Length);
    class'APX_MissionPlanner'.static.GetMeleeThreatReaches(UnitState, VisibleEnemies, Reaches);
    class'APX_MissionPlanner'.static.GetThreatWeights(UnitState, VisibleEnemies, Weights);
    CurrentRisk = class'APX_MissionPlanner'.static.ExposureRisk(UnitState, UnitState.TileLocation,
        VisibleEnemies, Reaches, Weights);
    CurrentSupport = class'APX_MissionPlanner'.static.NearestSupportDistance(UnitState, UnitState.TileLocation);
    for (SampleIndex = 0; SampleIndex < Samples; ++SampleIndex)
    {
        Index = 0;
        if (SampleIndex > 0 && Samples > 1)
            Index = 1 + ((SampleIndex - 1) * (Tiles.Length - 2)) / Max(1, Samples - 2);
        Tile = Tiles[Index];
        PathCost = Visualizer.m_kReachableTilesCache.GetPathCostToTile(Tile);
        if (Tile.Z != UnitState.TileLocation.Z
            || class'APX_MissionPlanner'.static.TileDistance(Tile, UnitState.TileLocation) < 1.0
            || PathCost < 0.0 || PathCost > Visualizer.GetMobility()
            || class'APX_HazardKnowledge'.static.HasBlockingHazard(UnitState, Tile)
            || !class'APX_MissionPlanner'.static.IsKnownCombatTile(Tile)
            || !class'APX_MissionPlanner'.static.IsSupportedCombatDestination(UnitState, Tile)
            || !class'APX_MissionPlanner'.static.IsSupportedAdvanceDestination(CurrentSupport,
                class'APX_MissionPlanner'.static.NearestSupportDistance(UnitState, Tile)))
            continue;
        CandidateRisk = class'APX_MissionPlanner'.static.ExposureRisk(UnitState, Tile,
            VisibleEnemies, Reaches, Weights);
        if (CandidateRisk > CurrentRisk
            || !ProjectAtTile(UnitState, Tile, Forecasts, TargetID, NativeChance,
                ProjectedChance, NativeScore, ProjectedScore))
            continue;
        Value = MoveAndShotScore(NativeScore, ProjectedScore, NativeChance, ProjectedChance,
            CurrentRisk, CandidateRisk, PathCost, UnitState.NumActionPoints());
        if (Value <= Score)
            continue;
        CandidatePath.Length = 0;
        if (!Visualizer.m_kReachableTilesCache.BuildPathToTile(Tile, CandidatePath) || CandidatePath.Length < 2)
            continue;
        bSafe = true;
        // The current tile may be dangerous; every step after it must be safe.
        for (PathIndex = 1; PathIndex < CandidatePath.Length; ++PathIndex)
        {
            if (class'APX_HazardKnowledge'.static.HasBlockingHazard(UnitState, CandidatePath[PathIndex])
                || !class'APX_MissionPlanner'.static.IsKnownCombatTile(CandidatePath[PathIndex])
                || (!class'APX_FullIntel'.default.EnableFullIntel
                    && !class'X2TacticalVisibilityHelpers'.static.CanSquadSeeLocation(
                        UnitState.ControllingPlayer.ObjectID, CandidatePath[PathIndex]))
                || !class'APX_MissionPlanner'.static.IsSupportedAdvanceStep(CurrentSupport,
                    class'APX_MissionPlanner'.static.NearestSupportDistance(UnitState, CandidatePath[PathIndex])))
            {
                bSafe = false;
                break;
            }
        }
        if (bSafe)
        {
            Path = CandidatePath;
            Score = Value;
        }
    }
    return Path.Length >= 2 && Score > 0.0;
}
