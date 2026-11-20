// Conservative move-and-shot forecasts for already legal basic ranged targets.
// Remote visibility is native; the projected chance is a bounded heuristic.
// Never move a history object to ask the current-position shot calculator about
// a hypothetical tile. The controller evaluates real actions again after moving.
class APX_RepositionPlanner extends Object config(AutoplayXCom2)
    dependson(X2GameRuleset, X2TacticalGameRulesetDataStructures, XComWorldData,
        X2GameRulesetVisibilityDataStructures);

// An elevated tile is a forecast, not a future native hit preview.
// Keep the historic same-floor candidate search as a reversible fallback.
var config bool EnableElevatedShotForecast;
var config int MaxElevationGainTiles;
var config int HeightForecastDiscount;

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
    var bool bCurrentNativeHeightAdvantage;
};

/** Clamp a current/remote native weapon range-table index; empty tables use index zero. */
static function int RangeBandIndex(int Distance, int Length)
{
    if (Length <= 0)
        return 0;
    return Clamp(Distance, 0, Length - 1);
}

/** Bound a geometric aim projection to 0..95; this is not a native future hit roll. */
static function int ProjectedHitChance(int NativeChance, int RangeDelta, int CoverRecovery)
{
    // Leave uncertainty even when the simple geometric estimate reaches 100%.
    return Clamp(NativeChance + Clamp(RangeDelta + CoverRecovery, -35, 35), 0, 95);
}

// Only add an estimated *new* height benefit. The current native shot
// breakdown already contains any existing bonus and must not be augmented
// a second time. Special-height native state is handled in relative height;
// modded overrides may still differ, hence a configurable discount.
/** Estimate a newly earned native height aim threshold without counting an existing bonus twice. */
static function int ProjectedHeightAimBonus(int CurrentRelativeZ, int CandidateRelativeZ,
    int RequiredZ, int NativeBonus, int UncertaintyDiscount, bool bNativeAlreadyHigh)
{
    if (bNativeAlreadyHigh || RequiredZ <= 0 || NativeBonus <= 0)
        return 0;
    if (CandidateRelativeZ <= CurrentRelativeZ || CurrentRelativeZ >= RequiredZ || CandidateRelativeZ < RequiredZ)
        return 0;
    return Max(0, NativeBonus - Max(0, UncertaintyDiscount));
}

/** Scale only the existing native basic-shot score by estimated hit probability; invalid models return -10000. */
static function float ProjectedShotScore(float NativeScore, int NativeChance, int ProjectedChance)
{
    if (NativeChance <= 0 || NativeScore <= 5.0)
        return -10000.0;
    // For a basic one-target shot, ScoreAttack's damage and kill terms are
    // linear in hit chance, with a constant 5. No crit improvement is invented.
    return 5.0 + (NativeScore - 5.0) * float(ProjectedChance) / float(NativeChance);
}

/** Rank one legal blue move plus an uncertain future basic shot, requiring AP, material gain and no added exposure. */
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

/** Admit only source-audited single-target native StandardShot or PistolStandardShot templates. */
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

/** Check current own revealed shooter readiness, two AP and native move, rejecting terrain/status/aim-sensitive cases. */
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

/** Inspect installed native action-point costs; reject an ability with another legal retained attack after the first. */
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

/** Read only an installed Ruler capability on current visible enemies; never query its current readiness. */
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

/** Enumerate bounded currently legal native basic shots, preserve target safety and projected post-blue AP; empty output means unsupported/unproven. */
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
            Forecast.bCurrentNativeHeightAdvantage = UnitState.HasHeightAdvantageOver(
                TargetUnit, true);
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

/** Read-only remote LOS, cover and target-condition preview; outputs the strongest material basic-shot estimate or false. */
static function bool ProjectAtTile(XComGameState_Unit UnitState, TTile Tile,
    const out array<AttackForecast> Forecasts, out int TargetID, out int NativeChance,
    out int ProjectedChance, out float NativeScore, out float ProjectedScore)
{
    local GameRulesCache_VisibilityInfo Visibility, EmptyVisibility;
    local AttackForecast Forecast;
    local vector SourceLocation, TargetLocation;
    local int Distance, RangeModifier, Chance, HeightBonus;
    local float Value;

    TargetID = 0;
    NativeChance = 0;
    ProjectedChance = 0;
    NativeScore = 0.0;
    ProjectedScore = -10000.0;
    // No downward moves or unsupported rooftop leaps in the speculative
    // forecast. All candidates still need native LOS/target/AP/path/risk checks.
    if (UnitState == none || `TACTICALRULES == none
        || `TACTICALRULES.VisibilityMgr == none || `XCOMHISTORY == none || `XWORLD == none)
        return false;
    if (Tile.Z < UnitState.TileLocation.Z
        || (Tile.Z > UnitState.TileLocation.Z
            && (!default.EnableElevatedShotForecast
                || Tile.Z - UnitState.TileLocation.Z >
                    Clamp(default.MaxElevationGainTiles, 1, 8))))
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
        HeightBonus = ProjectedHeightAimBonus(
            UnitState.TileLocation.Z + UnitState.GetHeightAdvantageBonusZ()
                - Forecast.TargetUnit.TileLocation.Z,
            Tile.Z + UnitState.GetHeightAdvantageBonusZ()
                - Forecast.TargetUnit.TileLocation.Z,
            Max(1, class'X2TacticalGameRuleset'.default.UnitHeightAdvantage),
            class'X2TacticalGameRuleset'.default.UnitHeightAdvantageBonus,
            Clamp(default.HeightForecastDiscount, 0, 20),
            Forecast.bCurrentNativeHeightAdvantage);
        Chance = ProjectedHitChance(Forecast.NativeChance,
            RangeModifier - Forecast.CurrentRangeModifier + HeightBonus,
            Forecast.CoverRecovery);
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

/**
 * Rejects a speculative flank crossing a tile with greater CURRENT exposure
 * than the origin. This is not a prediction of future movement or reaction.
 * @param OriginRisk Same-unit risk in native current tactical snapshot.
 * @param StepRisk Risk at a proposed native path step (same score units).
 * @return True only if the step does not increase recorded exposure.
 */
static function bool ForecastPathRiskAllowed(float OriginRisk, float StepRisk)
{
    return OriginRisk >= 0.0 && StepRisk >= 0.0 && StepRisk <= OriginRisk;
}

/**
 * Validates every actual native blue-path tile, not just the endpoint.
 * Shares the controller's bounded explosive-cover budget; when exhausted,
 * fail closed. Does not move units, preview hidden AI actions or grant LOS.
 * @param UnitState Current own unit, not a fabricated future state.
 * @param CandidatePath Actual native cache path, starting at current tile.
 * @param VisibleEnemies Current authorized enemy references.
 * @param Reaches Native current melee estimates aligned to VisibleEnemies.
 * @param Weights Current bounded threat weights.
 * @param OriginRisk Already computed risk of this unit's current tile.
 * @param OriginSupport Initial nearest active squadmate distance, in tiles.
 * @param RemainingTempoCoverChecks Shared read-only cover inspection budget.
 * @return False if any tile is unknown, hazardous, unsupported, risky or
 *         lacks a complete explosive-cover inspection.
 */
static function bool ForecastBluePathSafe(XComGameState_Unit UnitState,
    const out array<TTile> CandidatePath,
    const out array<StateObjectReference> VisibleEnemies,
    const out array<float> Reaches, const out array<float> Weights,
    float OriginRisk, float OriginSupport,
    out int RemainingTempoCoverChecks)
{
    local int Step;
    local TTile Destination;

    if (UnitState == none || CandidatePath.Length < 2
        || CandidatePath.Length > 64
        || CandidatePath[0] != UnitState.TileLocation
        || RemainingTempoCoverChecks < CandidatePath.Length - 1)
        return false;
    Destination = CandidatePath[CandidatePath.Length - 1];
    if (!class'APX_MissionPlanner'.static.IsSupportedCombatDestination(
            UnitState, Destination))
        return false;
    for (Step = 1; Step < CandidatePath.Length; ++Step)
    {
        if (class'APX_HazardKnowledge'.static.HasBlockingHazard(
                UnitState, CandidatePath[Step])
            || !class'APX_MissionPlanner'.static.IsKnownCombatTile(
                CandidatePath[Step])
            || (!class'APX_FullIntel'.default.EnableFullIntel
                && !class'X2TacticalVisibilityHelpers'.static.CanSquadSeeLocation(
                    UnitState.ControllingPlayer.ObjectID, CandidatePath[Step]))
            || !class'APX_MissionPlanner'.static.IsSupportedAdvanceStep(
                OriginSupport, class'APX_MissionPlanner'.static.NearestSupportDistance(
                    UnitState, CandidatePath[Step]))
            || !ForecastPathRiskAllowed(OriginRisk,
                class'APX_MissionPlanner'.static.ExposureRisk(
                    UnitState, CandidatePath[Step],
                    VisibleEnemies, Reaches, Weights)))
            return false;
    }
    // Use the exact native current-state cover estimate already employed by
    // the second-blue route; its method consumes a shared per-tile budget.
    return class'APX_MissionPlanner'.static.BlueRouteExplosiveSafe(
        UnitState, CandidatePath, VisibleEnemies, RemainingTempoCoverChecks);
}

/**
 * Compresses mutually exclusive scan outcomes into one bounded log label.
 * No label claims that a rejected tile would have been native legal.
 * @param SupportedShots Current AA_Success shots meeting stock forecast rules.
 * @param Endpoints Checked native reachable endpoint count.
 * @param ImprovedShots Hypothetical candidates surviving hit/value gates.
 * @param SafeRoutes Whole-path approved native blue moves.
 * @param Selected True only if caller selected a scored movement proposal.
 * @return Diagnostic stage, not an ability result or win prediction.
 */
static function string ForecastScanReason(int SupportedShots,
    int Endpoints, int ImprovedShots, int SafeRoutes, bool bSelected)
{
    if (SupportedShots <= 0)
        return "no_supported_current_shot";
    if (Endpoints <= 0)
        return "no_native_blue_endpoints";
    if (ImprovedShots <= 0)
        return "no_material_projected_shot";
    if (SafeRoutes <= 0)
        return "unsafe_or_unverified_blue_path";
    if (!bSelected)
        return "outscored_by_other_local_route";
    return "safe_move_and_shot_candidate";
}

// Selected-move telemetry reuses the same bounded projection, never a fake state.
/** Record optional selected movement's estimate from current native actions; never grants a future shot. */
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

/**
 * Scans native first-blue movement endpoints for a future basic shot.
 * No shot is granted: Controller must re-read legal native actions after
 * the actual movement. Shared cover budget is consumed for full paths;
 * diagnostics are advisory and cannot certify native gameplay.
 * @param UnitState Own current revealed 2AP shooter.
 * @param Path Best currently native-reachable blue path or empty.
 * @param Score Heuristic score, -10000 on failure.
 * @param RemainingTempoCoverChecks Shared per-decision cover budget.
 * @param ScanReason Aggregated rejection stage for recorder.
 * @param SupportedShots Current legal basic target models inspected.
 * @param ImprovedShots Future previews clearing material gain gates.
 * @param SafeRoutes Native complete paths passing all safety checks.
 */
static function bool ChooseMove(XComGameState_Unit UnitState,
    out array<TTile> Path, out float Score,
    optional out int RemainingTempoCoverChecks,
    optional out string ScanReason, optional out int SupportedShots,
    optional out int ImprovedShots, optional out int SafeRoutes)
{
    local XGUnit Visualizer;
    local array<TTile> Tiles, CandidatePath;
    local array<StateObjectReference> VisibleEnemies;
    local array<AttackForecast> Forecasts;
    local array<float> Reaches, Weights;
    local TTile Tile;
    local float CurrentRisk, CandidateRisk, CurrentSupport, PathCost, Value;
    local float NativeScore, ProjectedScore;
    local int SampleIndex, Index, Samples, TargetID, NativeChance, ProjectedChance;
    local int InspectedEndpoints;
    local bool bSelected;

    Path.Length = 0;
    Score = -10000.0;
    SupportedShots = 0;
    ImprovedShots = 0;
    SafeRoutes = 0;
    ScanReason = "not_ready_for_forecast";
    if (!CanForecastUnit(UnitState))
        return false;
    class'APX_MissionPlanner'.static.GetVisibleThreats(UnitState, VisibleEnemies);
    GatherForecasts(UnitState, VisibleEnemies, Forecasts);
    SupportedShots = Forecasts.Length;
    if (Forecasts.Length == 0)
    {
        ScanReason = ForecastScanReason(0, 0, 0, 0, false);
        return false;
    }
    Visualizer = XGUnit(UnitState.GetVisualizer());
    if (Visualizer == none || Visualizer.m_kReachableTilesCache == none)
    {
        ScanReason = "native_reachable_cache_missing";
        return false;
    }
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
        ++InspectedEndpoints;
        PathCost = Visualizer.m_kReachableTilesCache.GetPathCostToTile(Tile);
        if (Tile.Z < UnitState.TileLocation.Z
            || (Tile.Z > UnitState.TileLocation.Z
                && (!default.EnableElevatedShotForecast
                    || Tile.Z - UnitState.TileLocation.Z >
                        Clamp(default.MaxElevationGainTiles, 1, 8)))
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
        if (Value <= -1000.0)
            continue;
        ++ImprovedShots;
        if (Value <= Score)
            continue;
        CandidatePath.Length = 0;
        if (!Visualizer.m_kReachableTilesCache.BuildPathToTile(Tile, CandidatePath)
            || CandidatePath.Length < 2)
            continue;
        if (!ForecastBluePathSafe(UnitState, CandidatePath, VisibleEnemies,
            Reaches, Weights, CurrentRisk, CurrentSupport,
            RemainingTempoCoverChecks))
            continue;
        ++SafeRoutes;
        Path = CandidatePath;
        Score = Value;
    }
    bSelected = Path.Length >= 2 && Score > 0.0;
    ScanReason = ForecastScanReason(SupportedShots, InspectedEndpoints,
        ImprovedShots, SafeRoutes, bSelected);
    return bSelected;
}
