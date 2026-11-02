// Conservative stock frag/plasma grenade targeting. Native trajectory and blast
// queries are previews only; this object never builds an ability context or rolls RNG.
class APX_AreaAttackPlanner extends Object config(AutoplayXCom2)
    dependson(X2GameRuleset, X2TacticalGameRulesetDataStructures, WorldInfo);

var config int MinimumTargets;
var config int MaxCandidateCenters;
var config float SafetyBufferTiles;
var private XComPrecomputedPath PreviewPath;

struct GrenadeScanDiagnostics
{
    var int Available;
    var int Supported;
    var int Centers;
    var int EdgeCenters;
    var int Evaluated;
    var int Accepted;
    var int RangeRejected;
    var int VisibilityRejected;
    var int VisualizerRejected;
    var int TrajectoryRejected;
    var int BlastRejected;
    var int TargetsRejected;
    var int ScoreRejected;
    var int Unsupported;
    var int SingleOpportunities;
    var int SingleRejected;
};

var private GrenadeScanDiagnostics Scan;
var private bool bCollectDiagnostics;
var private string LastScanReason;
var private string LastBlastReason;
var private string ScanBlastReason;
var private string ScanRangeReason;
var private int DeepestRejection;
var private float ScanMinRange;
var private float ScanMaxRange;
var private float NearestAimDistance;
var private float LastSingleMin;
var private float LastSingleMax;
var private float LastSingleHealth;
var private float LastOrdinaryScore;

// One summary per unit/decision, not one log line per candidate center. The
// controller attaches it to that decision's recorder session.
function string GetDiagnosticSummary()
{
    return "available=" $ Scan.Available $ " supported=" $ Scan.Supported
        $ " centers=" $ Scan.Centers $ " edge_centers=" $ Scan.EdgeCenters $ " evaluated=" $ Scan.Evaluated
        $ " accepted=" $ Scan.Accepted $ " range=" $ Scan.RangeRejected
        $ " visibility=" $ Scan.VisibilityRejected $ " visualizer=" $ Scan.VisualizerRejected
        $ " trajectory=" $ Scan.TrajectoryRejected $ " blast=" $ Scan.BlastRejected
        $ " targets=" $ Scan.TargetsRejected $ " score=" $ Scan.ScoreRejected
        $ " unsupported=" $ Scan.Unsupported $ " last=" $ LastScanReason
        $ " range_reason=" $ ScanRangeReason $ " blast_reason=" $ ScanBlastReason
        $ " min_range_units=" $ ScanMinRange $ " max_range_units=" $ ScanMaxRange
        $ " nearest_aim_units=" $ NearestAimDistance
        $ " single_opportunities=" $ Scan.SingleOpportunities $ " single_rejected=" $ Scan.SingleRejected
        $ " last_single_min=" $ LastSingleMin $ " last_single_max=" $ LastSingleMax
        $ " last_single_hp=" $ LastSingleHealth $ " last_ordinary_score=" $ LastOrdinaryScore;
}

static function int RejectionPriority(name Stage)
{
    if (Stage == 'score')
        return 7;
    if (Stage == 'targets')
        return 6;
    if (Stage == 'blast')
        return 5;
    if (Stage == 'trajectory')
        return 4;
    if (Stage == 'visualizer')
        return 3;
    if (Stage == 'visibility')
        return 2;
    if (Stage == 'range')
        return 1;
    return 0;
}

function RejectScan(name Stage, string Reason)
{
    if (!bCollectDiagnostics)
        return;
    // A later out-of-range center must not hide why a valid trajectory failed
    // the collateral checks. Keep the most informative reached stage as well
    // as separate range/blast reasons.
    if (RejectionPriority(Stage) >= DeepestRejection)
    {
        LastScanReason = Reason;
        DeepestRejection = RejectionPriority(Stage);
    }
    if (Stage == 'range')
        ScanRangeReason = Reason;
    if (Stage == 'blast')
        ScanBlastReason = Reason;
    switch (Stage)
    {
    case 'range': ++Scan.RangeRejected; break;
    case 'visibility': ++Scan.VisibilityRejected; break;
    case 'visualizer': ++Scan.VisualizerRejected; break;
    case 'trajectory': ++Scan.TrajectoryRejected; break;
    case 'blast': ++Scan.BlastRejected; break;
    case 'targets': ++Scan.TargetsRejected; break;
    case 'score': ++Scan.ScoreRejected; break;
    default: ++Scan.Unsupported; break;
    }
}

function bool EndScan(bool bFound)
{
    bCollectDiagnostics = false;
    return bFound;
}

// The controller must call Cleanup when its tactical HUD is removed.
function Cleanup()
{
    if (PreviewPath != none)
    {
        PreviewPath.Destroy();
        PreviewPath = none;
    }
}

function bool EnsurePreviewPath()
{
    local WorldInfo World;
    if (PreviewPath != none && !PreviewPath.bDeleteMe)
        return true;
    World = class'WorldInfo'.static.GetWorldInfo();
    if (World == none)
        return false;
    PreviewPath = World.Spawn(class'XComPrecomputedPath');
    if (PreviewPath == none)
        return false;
    PreviewPath.SetHidden(true);
    PreviewPath.ClearPathGraphics();
    return true;
}

function bool GetSupportedGrenade(XComGameState_Unit UnitState,
    AvailableAction Action, out XComGameState_Ability Ability,
    out X2GrenadeTemplate Grenade, out X2AbilityMultiTarget_Radius Radius)
{
    local X2AbilityTemplate Template;
    local XComGameState_Item SourceWeapon, Ammo;
    local name AbilityName;

    Ability = none;
    Grenade = none;
    Radius = none;
    if (!Action.bInputTriggered || Action.AvailableCode != 'AA_Success' || !Action.bFreeAim)
        return false;
    Ability = XComGameState_Ability(`XCOMHISTORY.GetGameStateForObjectID(Action.AbilityObjectRef.ObjectID));
    if (Ability == none || Ability.OwnerStateObject.ObjectID != UnitState.ObjectID)
        return false;
    AbilityName = Ability.GetMyTemplateName();
    if (AbilityName != 'ThrowGrenade' && AbilityName != 'LaunchGrenade')
        return false;
    if (bCollectDiagnostics)
        ++Scan.Available;
    Template = Ability.GetMyTemplate();
    if (Template == none || Template.Hostility != eHostility_Offensive
        || Template.TargetingMethod != class'X2TargetingMethod_Grenade'
        || X2AbilityTarget_Cursor(Template.AbilityTargetStyle) == none)
    {
        RejectScan('unsupported', "targeting_contract");
        return false;
    }
    Radius = X2AbilityMultiTarget_Radius(Template.AbilityMultiTargetStyle);
    // Cone and focus-dependent radius subclasses need their own target solver.
    if (Radius == none || Radius.Class != class'X2AbilityMultiTarget_Radius')
    {
        RejectScan('unsupported', "radius_style");
        return false;
    }
    SourceWeapon = Ability.GetSourceWeapon();
    if (SourceWeapon == none)
    {
        RejectScan('unsupported', "source_weapon");
        return false;
    }
    Ammo = Ability.GetSourceAmmo();
    if (Ammo != none)
        Grenade = X2GrenadeTemplate(Ammo.GetMyTemplate());
    else if (Template.bUseLaunchedGrenadeEffects)
        Grenade = X2GrenadeTemplate(SourceWeapon.GetLoadedAmmoTemplate(Ability));
    else if (Template.bUseThrownGrenadeEffects)
        Grenade = X2GrenadeTemplate(SourceWeapon.GetMyTemplate());
    // These two SDK templates have direct explosive damage and no persistent
    // poison, fire, smoke, EMP immunity exceptions, or delayed proximity trigger.
    if (Grenade == none || (Grenade.DataName != 'FragGrenade' && Grenade.DataName != 'AlienGrenade'))
    {
        RejectScan('unsupported', "grenade_template");
        return false;
    }
    if (bCollectDiagnostics)
        ++Scan.Supported;
    return true;
}

function bool IsLegalLocation(XComGameState_Unit UnitState,
    XComGameState_Ability Ability, vector Location)
{
    local XGUnit Visualizer;
    local float MinRange, MaxRange, Distance;
    local TTile Tile;

    Visualizer = XGUnit(UnitState.GetVisualizer());
    if (Visualizer == none)
    {
        RejectScan('visualizer', "unit_visualizer");
        return false;
    }
    Ability.GetValidWeaponRange(MinRange, MaxRange);
    Distance = VSize(Location - Visualizer.GetGameStateLocation());
    if (bCollectDiagnostics)
    {
        ScanMinRange = MinRange;
        ScanMaxRange = MaxRange;
        if (NearestAimDistance < 0.0 || Distance < NearestAimDistance)
            NearestAimDistance = Distance;
    }
    if (Distance < MinRange || (MaxRange > 0.0 && Distance >= MaxRange))
    {
        RejectScan('range', "outside_weapon_range");
        return false;
    }
    Tile = `XWORLD.GetTileCoordinatesFromPosition(Location);
    // Never choose blind grenade targets, even when a native cursor permits it.
    if (!class'X2TacticalVisibilityHelpers'.static.CanSquadSeeLocation(
        UnitState.ControllingPlayer.ObjectID, Tile))
    {
        RejectScan('visibility', "landing_not_visible");
        return false;
    }
    return true;
}

function bool ComputeImpact(XComGameState_Unit UnitState,
    XComGameState_Ability Ability, vector AimLocation,
    XComPrecomputedPath PathActor, out vector Impact)
{
    local XComGameState_Item SourceWeapon;
    local XGWeapon WeaponVisualizer;
    local XComWeapon WeaponEntity;
    local X2WeaponTemplate WeaponTemplate;
    local XGUnit UnitVisualizer;
    local TTile SnapTile;

    if (PathActor == none)
    {
        RejectScan('trajectory', "preview_path_unavailable");
        return false;
    }
    if (!IsLegalLocation(UnitState, Ability, AimLocation))
        return false;
    SourceWeapon = Ability.GetSourceWeapon();
    if (SourceWeapon == none)
        return false;
    WeaponVisualizer = XGWeapon(SourceWeapon.GetVisualizer());
    WeaponTemplate = X2WeaponTemplate(SourceWeapon.GetMyTemplate());
    if (WeaponTemplate == none)
    {
        RejectScan('unsupported', "weapon_template");
        return false;
    }
    // Stock grenade targeting initializes the stowed item's visualizer/entity
    // on demand. The player need not manually open grenade targeting first.
    UnitVisualizer = XGUnit(UnitState.GetVisualizer());
    if (UnitVisualizer == none)
    {
        RejectScan('visualizer', "unit_visualizer");
        return false;
    }
    if (WeaponVisualizer == none)
    {
        class'XGItem'.static.CreateVisualizer(SourceWeapon);
        WeaponVisualizer = XGWeapon(SourceWeapon.GetVisualizer());
    }
    if (WeaponVisualizer == none)
    {
        RejectScan('visualizer', "grenade_visualizer");
        return false;
    }
    WeaponEntity = WeaponVisualizer.GetEntity();
    if (WeaponEntity == none)
        WeaponEntity = XComWeapon(WeaponVisualizer.CreateEntity(SourceWeapon));
    if (WeaponEntity == none)
    {
        RejectScan('visualizer', "grenade_entity");
        return false;
    }
    if (WeaponEntity.m_kPawn == none)
        WeaponEntity.m_kPawn = UnitVisualizer.GetPawn();
    if (WeaponEntity.m_kPawn == none)
    {
        RejectScan('visualizer', "throwing_pawn");
        return false;
    }

    // Same native pipeline as XGAIBehavior.PrecomputeGrenadePath. Use a private
    // hidden actor while evaluating; only PrepareForActivation touches the global
    // path whose projectile events the normal ability context will consume.
    PathActor.bOverrideSourceTargetFromSocketLocation = false;
    PathActor.bUseOverrideSourceLocation = false;
    PathActor.m_bBlasterBomb = false;
    PathActor.iNumKeyframes = 0;
    PathActor.TouchEvents.Length = 0;
    PathActor.ClearOverrideTargetLocation();
    PathActor.SetWeaponAndTargetLocation(WeaponEntity, UnitState.GetTeam(),
        AimLocation, WeaponTemplate.WeaponPrecomputedPathData);
    PathActor.CalculateTrajectoryToTarget(WeaponTemplate.WeaponPrecomputedPathData);
    if (PathActor.iNumKeyframes <= 0)
    {
        RejectScan('trajectory', "no_trajectory");
        return false;
    }
    if (!TrajectoryIsSafe(PathActor))
    {
        RejectScan('trajectory', "unsafe_trajectory");
        return false;
    }
    Impact = PathActor.GetEndPosition();
    // Match stock X2TargetingMethod_Grenade.GetSplashRadiusCenter's tile snap.
    SnapTile = `XWORLD.GetTileCoordinatesFromPosition(Impact);
    while (SnapTile.Z >= 0 && !`XWORLD.GetFloorPositionForTile(SnapTile, Impact))
        --SnapTile.Z;
    if (SnapTile.Z < 0)
    {
        RejectScan('trajectory', "no_landing_floor");
        return false;
    }
    return IsLegalLocation(UnitState, Ability, Impact);
}

function bool IsProtectedUnit(XComGameState_Unit SourceUnit, XComGameState_Unit OtherUnit)
{
    if (OtherUnit == none || OtherUnit.bRemoved || OtherUnit.bRemovedFromPlay)
        return false;
    if (OtherUnit.GetMyTemplate() == none)
        return true;
    // A GREMLIN's cosmetic state has no separate gameplay body. Its real owner
    // is checked independently; a missing cosmetic visibility footprint must
    // not reject every grenade on the map.
    if (OtherUnit.GetMyTemplate().bIsCosmetic)
        return false;
    // Also preserve recoverable friendly bodies, not just living soldiers.
    return !SourceUnit.IsEnemyUnit(OtherUnit) || OtherUnit.IsCivilian()
        || OtherUnit.GetMyTemplateName() == 'HostileVIPCivilian'
        || class'Helpers'.static.IsObjectiveTarget(OtherUnit.ObjectID);
}

function bool FootprintNearImpact(X2GameRulesetVisibilityInterface VisibleObject,
    vector Impact, float SafeRadius)
{
    local array<TTile> Tiles;
    local TTile Tile;
    local vector Delta;

    // If a protected mission object has no spatial interface, no safe blast can
    // be established for this candidate. Tactical map objectives normally do.
    if (VisibleObject == none)
        return true;
    VisibleObject.GetVisibilityLocation(Tiles);
    if (Tiles.Length == 0)
        return true;
    foreach Tiles(Tile)
    {
        Delta = `XWORLD.GetPositionFromTileCoordinates(Tile) - Impact;
        // Protect vertical columns too: destroying a floor can injure a unit
        // above the visible blast, even when it is excluded from direct targets.
        Delta.Z = 0.0;
        if (VSizeSq(Delta) <= Square(SafeRadius))
            return true;
    }
    return false;
}

function bool HasDangerousScenery(Actor TargetActor)
{
    local XComDestructibleActor Destructible;
    Destructible = XComDestructibleActor(TargetActor);
    if (Destructible == none)
        return false;
    // Avoid secondary blasts and destruction propagated to unpreviewed child
    // objects. This deliberately rejects some otherwise useful grenade throws.
    return Destructible.HasRadialDamage() || Destructible.bDestroysSurroundingArea
        || Destructible.AffectedChildren.Length > 0;
}

function bool RejectBlast(string Reason)
{
    LastBlastReason = Reason;
    return false;
}

function bool TrajectoryIsSafe(XComPrecomputedPath PathActor)
{
    local int Index;
    local Actor HitActor;
    local XComDestructibleActor Destructible;
    local XComGameState_InteractiveObject Interactive;

    // Projectile entry events can break fragile scenery before the explosion.
    // Check these too; protecting only the blast radius would miss a fuel tank
    // or a marked objective touched while the grenade travels through a window.
    for (Index = 1; Index < PathActor.TouchEvents.Length; ++Index)
    {
        if (!PathActor.TouchEvents[Index].bEntry
            || PathActor.TouchEvents[Index].TraceInfo.HitComponent == none)
            continue;
        HitActor = PathActor.TouchEvents[Index].TraceInfo.HitComponent.Owner;
        if (HasDangerousScenery(HitActor))
            return false;
        Destructible = XComDestructibleActor(HitActor);
        if (Destructible == none)
            continue;
        if (class'Helpers'.static.IsObjectiveTarget(Destructible.ObjectID))
            return false;
        Interactive = XComGameState_InteractiveObject(`XCOMHISTORY.GetGameStateForObjectID(
            Destructible.ObjectID));
        if (Interactive != none && !Interactive.bRemovedFromPlay
            && Interactive.GetRequiresObjectiveGlint())
            return false;
    }
    return true;
}

function bool BlastIsSafe(XComGameState_Unit UnitState,
    XComGameState_Ability Ability, X2AbilityMultiTarget_Radius Radius, vector Impact)
{
    local array<XComGameState_BaseObject> RawTargets;
    local XComGameState_BaseObject TargetObject, ObjectiveOwner;
    local XComGameState_Unit OtherUnit;
    local XComGameState_ObjectiveInfo Objective;
    local XComGameState_InteractiveObject Interactive;
    local array<TTile> BlastTiles;
    local array<Actor> TileActors;
    local TTile Tile;
    local Actor TileActor;
    local float SafeRadius;

    LastBlastReason = "none";
    Radius.GetTargetedStateObjects(Ability, Impact, RawTargets);
    foreach RawTargets(TargetObject)
    {
        if (TargetObject == none)
            return RejectBlast("missing_target_object");
        if (class'Helpers'.static.IsObjectiveTarget(TargetObject.ObjectID))
            return RejectBlast("objective_in_blast");
        OtherUnit = XComGameState_Unit(TargetObject);
        if (IsProtectedUnit(UnitState, OtherUnit))
            return RejectBlast("protected_unit_in_blast");
        Interactive = XComGameState_InteractiveObject(TargetObject);
        if (Interactive != none && Interactive.GetRequiresObjectiveGlint())
            return RejectBlast("interactive_objective_in_blast");
        if (HasDangerousScenery(TargetObject.GetVisualizer()))
            return RejectBlast("dangerous_scenery_in_blast");
    }

    SafeRadius = Radius.GetTargetRadius(Ability) + `TILESTOUNITS(FMax(0.0, SafetyBufferTiles));
    // Independent protection catches units omitted by filtered damage conditions
    // and protects floors/nearby civilians. Enemy locations are never harvested
    // here for candidate generation or score; only protected objects matter.
    foreach `XCOMHISTORY.IterateByClassType(class'XComGameState_Unit', OtherUnit)
    {
        if (IsProtectedUnit(UnitState, OtherUnit)
            && FootprintNearImpact(X2GameRulesetVisibilityInterface(OtherUnit), Impact, SafeRadius))
            return RejectBlast("protected_unit_near_blast");
    }
    foreach `XCOMHISTORY.IterateByClassType(class'XComGameState_ObjectiveInfo', Objective)
    {
        ObjectiveOwner = `XCOMHISTORY.GetGameStateForObjectID(Objective.OwningObjectId);
        if (ObjectiveOwner == none || ObjectiveOwner.bRemoved)
            continue;
        OtherUnit = XComGameState_Unit(ObjectiveOwner);
        if (OtherUnit != none && !IsProtectedUnit(UnitState, OtherUnit))
            continue;
        Interactive = XComGameState_InteractiveObject(ObjectiveOwner);
        if (Interactive != none && (Interactive.bRemovedFromPlay || Interactive.bBroken))
            continue;
        if (FootprintNearImpact(X2GameRulesetVisibilityInterface(ObjectiveOwner), Impact, SafeRadius))
            return RejectBlast("objective_near_blast");
    }
    foreach `XCOMHISTORY.IterateByClassType(class'XComGameState_InteractiveObject', Interactive)
    {
        if (Interactive.IsEnabled && !Interactive.bRemovedFromPlay && !Interactive.bBroken
            && Interactive.GetRequiresObjectiveGlint()
            && FootprintNearImpact(X2GameRulesetVisibilityInterface(Interactive), Impact, SafeRadius))
            return RejectBlast("interactive_objective_near_blast");
    }

    Radius.GetValidTilesForLocation(Ability, Impact, BlastTiles);
    if (BlastTiles.Length == 0)
        return RejectBlast("no_blast_tiles");
    foreach BlastTiles(Tile)
    {
        TileActors = `XWORLD.GetActorsOnTile(Tile, true);
        foreach TileActors(TileActor)
        {
            if (HasDangerousScenery(TileActor))
                return RejectBlast("dangerous_scenery_on_blast_tile");
        }
    }
    return true;
}

function float ScoreBlast(XComGameState_Unit UnitState, XComGameState_Ability Ability,
    X2GrenadeTemplate Grenade, AvailableTarget Target,
    const out array<StateObjectReference> VisibleEnemies)
{
    local array<X2Effect> Effects;
    local StateObjectReference TargetRef;
    local XComGameState_Unit Enemy;
    local X2Effect Effect;
    local WeaponDamageValue MinDamage, MaxDamage, EmptyDamage;
    local int AllowsShield, Count, LethalCount;
    local float MinTotal, MaxTotal, Health, Armor, Result;
    local float SingleMin, SingleMax, SingleHealth, OrdinaryScore;
    local XComGameState_Unit SingleEnemy;
    local bool bSingleFollowup, bSingleOpportunity;

    if (Ability.GetMyTemplate().bUseLaunchedGrenadeEffects)
        Effects = Grenade.LaunchedGrenadeEffects;
    else
        Effects = Grenade.ThrownGrenadeEffects;
    foreach Target.AdditionalTargets(TargetRef)
    {
        Enemy = XComGameState_Unit(`XCOMHISTORY.GetGameStateForObjectID(TargetRef.ObjectID));
        if (!class'APX_CombatPlanner'.static.IsVisibleHostile(UnitState, Enemy, VisibleEnemies))
            continue;
        MinTotal = 0.0;
        MaxTotal = 0.0;
        Armor = Enemy.GetArmorMitigationForUnitFlag();
        Health = Enemy.GetCurrentStat(eStat_HP) + Enemy.GetCurrentStat(eStat_ShieldHP);
        foreach Effects(Effect)
        {
            if (Effect == none)
                continue;
            // Native ability preview uses bAsPrimaryTarget=false for grenade
            // effects. Calling Ability.GetDamagePreview(enemy-ref) would instead
            // inspect the empty primary effects and incorrectly report zero.
            MinDamage = EmptyDamage;
            MaxDamage = EmptyDamage;
            AllowsShield = 0;
            Effect.GetDamagePreview(TargetRef, Ability, false, MinDamage, MaxDamage, AllowsShield);
            // The stock preview reports raw damage; armor is applied per hit.
            // Do not subtract Shred before this grenade's own damage lands.
            if (X2Effect_ApplyWeaponDamage(Effect) != none
                && X2Effect_ApplyWeaponDamage(Effect).bIgnoreArmor)
            {
                MinTotal += MinDamage.Damage;
                MaxTotal += MaxDamage.Damage;
            }
            else
            {
                MinTotal += class'APX_CombatPlanner'.static.PreviewDamageAfterArmor(
                    MinDamage.Damage, Armor, MinDamage.Pierce, 1);
                MaxTotal += class'APX_CombatPlanner'.static.PreviewDamageAfterArmor(
                    MaxDamage.Damage, Armor, MaxDamage.Pierce, 1);
            }
        }
        if (MaxTotal <= 0.0)
            continue;
        // Stock previews omit the advanced explosive falloff adjustment.
        // Without its native result, do not promise a minimum or a sure kill.
        if (`SecondWaveEnabled('ExplosiveFalloff'))
            MinTotal = 0.0;
        ++Count;
        SingleMin = MinTotal;
        SingleMax = MaxTotal;
        SingleHealth = Health;
        SingleEnemy = Enemy;
        if (MinTotal >= Health)
            ++LethalCount;
        Result += class'APX_CombatPlanner'.static.ScoreDamage(MinTotal, MaxTotal,
            Health, 100.0, 1.0, 1.0 - Enemy.GetCurrentStat(eStat_HP)
                / FMax(1.0, Enemy.GetMaxStat(eStat_HP)));
        // Modest setup value only if an ally can actually follow up now.
        // This is a cover-opening opportunity, not a promise that terrain breaks.
        if (MinTotal < Health)
            Result += CoverOpeningValue(UnitState, Enemy);
    }
    if (Count == 1 && LethalCount == 0 && MinimumTargets > 1)
    {
        OrdinaryScore = BestOrdinaryAttackScore(UnitState, VisibleEnemies);
        bSingleFollowup = HasQualifiedFollowup(UnitState, SingleEnemy,
            FMax(0.0, SingleHealth - SingleMin));
        bSingleOpportunity = IsUsefulSingleGrenade(SingleMin, SingleMax, SingleHealth,
            bSingleFollowup, Result - 18.0, OrdinaryScore);
        if (bCollectDiagnostics)
        {
            LastSingleMin = SingleMin;
            LastSingleMax = SingleMax;
            LastSingleHealth = SingleHealth;
            LastOrdinaryScore = OrdinaryScore;
            if (bSingleOpportunity)
                ++Scan.SingleOpportunities;
            else
                ++Scan.SingleRejected;
        }
    }
    return ScoreGrenadeOutcome(Count, LethalCount, Max(1, MinimumTargets), Result, bSingleOpportunity);
}

// A reliable finisher or a substantial singleton advantage may justify the
// limited grenade. Rifle kills win ties by saving the item.
static function float ScoreGrenadeOutcome(int Count, int LethalCount,
    int RequiredTargets, float DamageValue, optional bool bSingleOpportunity)
{
    if (Count == 0 || (Count < RequiredTargets && LethalCount == 0 && !bSingleOpportunity))
        return -10000.0;
    return DamageValue - 18.0;
}

static function bool IsUsefulSingleGrenade(float MinDamage, float MaxDamage,
    float Health, bool bQualifiedFollowup, float GrenadeScore, float OrdinaryScore)
{
    if (Health <= 0.0 || MinDamage <= 0.0 || GrenadeScore < OrdinaryScore + 12.0)
        return false;
    // The report's safe 3-4 damage frag against 4 HP is much more reliable
    // than a 30% rifle shot. Do not require a guaranteed minimum-damage kill.
    if (MinDamage >= Health * 0.75 && MaxDamage >= Health)
        return true;
    return bQualifiedFollowup;
}

function float BestOrdinaryAttackScore(XComGameState_Unit UnitState,
    const out array<StateObjectReference> VisibleEnemies)
{
    local GameRulesCache_Unit Cache;
    local AvailableAction Candidate;
    local AvailableTarget Target;
    local XComGameState_Ability Ability;
    local XComGameState_Unit Enemy;
    local name AbilityName;
    local float BestScore;

    BestScore = 0.0;
    if (!`TACTICALRULES.GetGameRulesCache_Unit(UnitState.GetReference(), Cache))
        return BestScore;
    foreach Cache.AvailableActions(Candidate)
    {
        if (Candidate.AvailableCode != 'AA_Success' || !Candidate.bInputTriggered || Candidate.bFreeAim)
            continue;
        Ability = XComGameState_Ability(`XCOMHISTORY.GetGameStateForObjectID(Candidate.AbilityObjectRef.ObjectID));
        if (Ability == none)
            continue;
        AbilityName = Ability.GetMyTemplateName();
        if (AbilityName != 'StandardShot' && AbilityName != 'SniperStandardFire' && AbilityName != 'PistolStandardShot')
            continue;
        foreach Candidate.AvailableTargets(Target)
        {
            Enemy = XComGameState_Unit(`XCOMHISTORY.GetGameStateForObjectID(Target.PrimaryTarget.ObjectID));
            if (class'APX_CombatPlanner'.static.IsVisibleHostile(UnitState, Enemy, VisibleEnemies))
                BestScore = FMax(BestScore, class'APX_CombatPlanner'.static.ScoreAttack(Ability, Target, Enemy));
        }
    }
    return BestScore;
}

function bool HasQualifiedFollowup(XComGameState_Unit SourceUnit, XComGameState_Unit Enemy,
    float RemainingHealth)
{
    local XComGameState_Unit Ally;
    local XComGameState_Ability Shot;
    local GameRulesCache_Unit Cache;
    local AvailableAction Candidate;
    local AvailableTarget Target;
    local ShotBreakdown Breakdown;
    local WeaponDamageValue MinDamage, MaxDamage;
    local int Chance, AllowsShield;
    local float Armor, MinHPDamage;
    local name AbilityName;

    if (RemainingHealth <= 0.0)
        return false;
    foreach `XCOMHISTORY.IterateByClassType(class'XComGameState_Unit', Ally)
    {
        if (Ally.ObjectID == SourceUnit.ObjectID || !Ally.IsAbleToAct()
            || Ally.GetAssociatedPlayerID() != SourceUnit.GetAssociatedPlayerID()
            || Ally.GetTeam() != eTeam_XCom || Ally.GetMyTemplate().bIsCosmetic
            || !`TACTICALRULES.GetGameRulesCache_Unit(Ally.GetReference(), Cache))
            continue;
        foreach Cache.AvailableActions(Candidate)
        {
            if (Candidate.AvailableCode != 'AA_Success' || !Candidate.bInputTriggered || Candidate.bFreeAim)
                continue;
            Shot = XComGameState_Ability(`XCOMHISTORY.GetGameStateForObjectID(Candidate.AbilityObjectRef.ObjectID));
            if (Shot == none)
                continue;
            AbilityName = Shot.GetMyTemplateName();
            if (AbilityName != 'StandardShot' && AbilityName != 'SniperStandardFire' && AbilityName != 'PistolStandardShot')
                continue;
            foreach Candidate.AvailableTargets(Target)
            {
                if (Target.PrimaryTarget.ObjectID != Enemy.ObjectID)
                    continue;
                Chance = Shot.GetShotBreakdown(Target, Breakdown);
                if (Chance < 50)
                    continue;
                Shot.GetDamagePreview(Target.PrimaryTarget, MinDamage, MaxDamage, AllowsShield);
                Armor = Enemy.GetArmorMitigationForUnitFlag();
                if (class'APX_CombatPlanner'.static.AbilityIgnoresArmor(Shot.GetMyTemplate()))
                    Armor = 0.0;
                MinHPDamage = class'APX_CombatPlanner'.static.PreviewDamageAfterArmor(
                    MinDamage.Damage, Armor, MinDamage.Pierce, 1);
                if (MinHPDamage >= RemainingHealth)
                    return true;
            }
        }
    }
    return false;
}

function float CoverOpeningValue(XComGameState_Unit SourceUnit, XComGameState_Unit Enemy)
{
    local XComGameState_Unit Ally;
    local XComGameState_Ability Shot;
    local GameRulesCache_Unit UnitCache;
    local AvailableAction Candidate;
    local AvailableTarget Target;
    local float Angle, Result;
    local vector EnemyLocation, AllyLocation;
    local bool bFollowUp;

    EnemyLocation = `XWORLD.GetPositionFromTileCoordinates(Enemy.TileLocation);
    foreach `XCOMHISTORY.IterateByClassType(class'XComGameState_Unit', Ally)
    {
        if (Ally.ObjectID == SourceUnit.ObjectID || !Ally.IsAbleToAct()
            || Ally.GetAssociatedPlayerID() != SourceUnit.GetAssociatedPlayerID()
            || Ally.GetTeam() != eTeam_XCom || Ally.GetMyTemplate().bIsCosmetic)
            continue;
        // Native const out vector inputs still require addressable variables.
        AllyLocation = `XWORLD.GetPositionFromTileCoordinates(Ally.TileLocation);
        if (`XWORLD.GetCoverTypeForTarget(AllyLocation, EnemyLocation, Angle) == CT_None
            || !`TACTICALRULES.GetGameRulesCache_Unit(Ally.GetReference(), UnitCache))
            continue;
        bFollowUp = false;
        foreach UnitCache.AvailableActions(Candidate)
        {
            if (Candidate.AvailableCode != 'AA_Success' || !Candidate.bInputTriggered
                || Candidate.bFreeAim)
                continue;
            Shot = XComGameState_Ability(`XCOMHISTORY.GetGameStateForObjectID(
                Candidate.AbilityObjectRef.ObjectID));
            if (Shot == none || (Shot.GetMyTemplateName() != 'StandardShot'
                && Shot.GetMyTemplateName() != 'SniperStandardFire'
                && Shot.GetMyTemplateName() != 'PistolStandardShot'))
                continue;
            foreach Candidate.AvailableTargets(Target)
            {
                if (Target.PrimaryTarget.ObjectID == Enemy.ObjectID)
                {
                    Result += 4.0;
                    bFollowUp = true;
                    break;
                }
            }
            // Count one opportunity per ally, even with several loaded weapons.
            if (Result >= 12.0)
                return 12.0;
            if (bFollowUp)
                break;
        }
    }
    return Result;
}

function bool EvaluateImpact(XComGameState_Unit UnitState,
    XComGameState_Ability Ability, X2GrenadeTemplate Grenade,
    X2AbilityMultiTarget_Radius Radius, vector Impact,
    const out array<StateObjectReference> VisibleEnemies,
    out AvailableTarget Target, out array<vector> Locations, out float Score)
{
    local AvailableTarget EmptyTarget;
    Target = EmptyTarget;
    Locations.Length = 0;
    Score = -10000.0;
    if (!BlastIsSafe(UnitState, Ability, Radius, Impact))
    {
        RejectScan('blast', LastBlastReason);
        return false;
    }
    Ability.GatherAdditionalAbilityTargetsForLocation(Impact, Target);
    if (Target.PrimaryTarget.ObjectID != 0 || Target.AdditionalTargets.Length == 0
        || Radius.CheckFilteredMultiTargets(Ability, Target) != 'AA_Success')
    {
        RejectScan('targets', "native_target_filter");
        return false;
    }
    Score = ScoreBlast(UnitState, Ability, Grenade, Target, VisibleEnemies);
    if (Score <= -1000.0)
    {
        RejectScan('score', "not_worth_limited_grenade");
        return false;
    }
    Ability.GatherAbilityTargetLocationsForLocation(Impact, Target, Locations);
    if (Locations.Length != 1)
    {
        RejectScan('targets', "target_location_contract");
        return false;
    }
    return true;
}

function AddCenter(vector Center, out array<vector> Centers)
{
    local TTile Tile;
    local vector FloorCenter, Existing;
    if (Centers.Length >= Clamp(MaxCandidateCenters, 1, 64)
        || !`XWORLD.GetFloorTileForPosition(Center, Tile))
        return;
    if (!`XWORLD.GetFloorPositionForTile(Tile, FloorCenter))
        return;
    foreach Centers(Existing)
    {
        if (VSizeSq(Existing - FloorCenter) < 1.0)
            return;
    }
    Centers.AddItem(FloorCenter);
}

// Aim inside the throw range while keeping the visible target inside the
// prospective blast. This only proposes a point: floor snapping, real landing,
// cover blocking and protected-object checks still decide whether it is legal.
static function float EdgeAimDistance(float EnemyDistance, float MaxRange,
    float BlastRadius, float Margin)
{
    local float LegalRange;

    if (MaxRange <= 0.0 || BlastRadius <= 0.0 || EnemyDistance <= 0.0)
        return -1.0;
    LegalRange = FMax(0.0, MaxRange - FMax(0.0, Margin));
    if (EnemyDistance > LegalRange + BlastRadius)
        return -1.0;
    return FMin(LegalRange, FMax(0.0, EnemyDistance - BlastRadius * 0.75));
}

function BuildCandidateCenters(XComGameState_Unit UnitState,
    XComGameState_Ability Ability, X2AbilityMultiTarget_Radius Radius,
    const out array<vector> EnemyCenters, out array<vector> Centers)
{
    local array<vector> DirectCenters, EdgeCenters, MidpointCenters;
    local XGUnit UnitVisualizer;
    local vector SourceLocation, EnemyCenter, Delta, EdgeCenter;
    local float MinRange, MaxRange, BlastRadius, Distance, AimDistance;
    local int First, Second, Index, MarginIndex, Budget;

    Centers.Length = 0;
    UnitVisualizer = XGUnit(UnitState.GetVisualizer());
    if (UnitVisualizer == none)
        return;
    SourceLocation = UnitVisualizer.GetGameStateLocation();
    Ability.GetValidWeaponRange(MinRange, MaxRange);
    BlastRadius = Radius.GetTargetRadius(Ability);
    Budget = Clamp(MaxCandidateCenters, 1, 64);
    foreach EnemyCenters(EnemyCenter)
    {
        AddCenter(EnemyCenter, DirectCenters);
        Delta = EnemyCenter - SourceLocation;
        Distance = VSize(Delta);
        // Two interior margins tolerate different floor-grid snaps near the
        // range boundary. Neither changes the ability's actual maximum range.
        for (MarginIndex = 0; MarginIndex < 2; ++MarginIndex)
        {
            AimDistance = EdgeAimDistance(Distance, MaxRange, BlastRadius,
                `TILESTOUNITS(0.25 + float(MarginIndex) * 0.5));
            if (AimDistance < 0.0)
                continue;
            EdgeCenter = SourceLocation + Normal(Delta) * AimDistance;
            AddCenter(EdgeCenter, EdgeCenters);
        }
    }
    for (First = 0; First < EnemyCenters.Length; ++First)
    {
        for (Second = First + 1; Second < EnemyCenters.Length; ++Second)
            AddCenter((EnemyCenters[First] + EnemyCenters[Second]) * 0.5, MidpointCenters);
    }
    // Round-robin the three pools. Filling the budget with distant enemy
    // centers first would silently exclude every useful range-edge proposal.
    for (Index = 0; Index < Budget && Centers.Length < Budget; ++Index)
    {
        if (Index < DirectCenters.Length)
            AddCenter(DirectCenters[Index], Centers);
        if (Index < EdgeCenters.Length)
        {
            First = Centers.Length;
            AddCenter(EdgeCenters[Index], Centers);
            if (Centers.Length > First)
                ++Scan.EdgeCenters;
        }
        if (Index < MidpointCenters.Length)
            AddCenter(MidpointCenters[Index], Centers);
    }
}

function bool ChooseAction(XComGameState_Unit UnitState,
    out AvailableAction Action, out int TargetIndex, out array<vector> Locations,
    out vector AimLocation, out float Score)
{
    local GameRulesCache_Unit UnitCache;
    local AvailableAction Candidate, EmptyAction;
    local AvailableTarget Target;
    local XComGameState_Ability Ability;
    local X2GrenadeTemplate Grenade;
    local X2AbilityMultiTarget_Radius Radius;
    local array<StateObjectReference> VisibleEnemies;
    local StateObjectReference EnemyRef;
    local XComGameState_Unit Enemy;
    local array<vector> Centers, EnemyCenters, CandidateLocations;
    local vector Center, Impact, EnemyCenter;
    local float CandidateScore;
    local bool bFound;
    local GrenadeScanDiagnostics EmptyScan;

    Scan = EmptyScan;
    LastScanReason = "none";
    ScanRangeReason = "none";
    ScanBlastReason = "none";
    DeepestRejection = 0;
    ScanMinRange = -1.0;
    ScanMaxRange = -1.0;
    NearestAimDistance = -1.0;
    LastSingleMin = -1.0;
    LastSingleMax = -1.0;
    LastSingleHealth = -1.0;
    LastOrdinaryScore = -1.0;
    bCollectDiagnostics = true;
    Action = EmptyAction;
    TargetIndex = INDEX_NONE;
    Locations.Length = 0;
    Score = -10000.0;
    if (UnitState == none || !UnitState.IsAbleToAct() || `TACTICALRULES == none
        || !`TACTICALRULES.GetGameRulesCache_Unit(UnitState.GetReference(), UnitCache))
    {
        RejectScan('unsupported', "unit_or_cache_unavailable");
        return EndScan(false);
    }
    class'X2TacticalVisibilityHelpers'.static.GetAllVisibleEnemiesForPlayer(
        UnitState.ControllingPlayer.ObjectID, VisibleEnemies);
    foreach VisibleEnemies(EnemyRef)
    {
        Enemy = XComGameState_Unit(`XCOMHISTORY.GetGameStateForObjectID(EnemyRef.ObjectID));
        if (!class'APX_CombatPlanner'.static.IsVisibleHostile(UnitState, Enemy, VisibleEnemies))
            continue;
        EnemyCenter = `XWORLD.GetPositionFromTileCoordinates(Enemy.TileLocation);
        EnemyCenters.AddItem(EnemyCenter);
        if (EnemyCenters.Length >= Clamp(MaxCandidateCenters, 1, 64))
            break;
    }
    if (EnemyCenters.Length == 0)
    {
        LastScanReason = "no_visible_centers";
        return EndScan(false);
    }
    if (!EnsurePreviewPath())
    {
        RejectScan('trajectory', "preview_path_unavailable");
        return EndScan(false);
    }
    foreach UnitCache.AvailableActions(Candidate)
    {
        if (!GetSupportedGrenade(UnitState, Candidate, Ability, Grenade, Radius))
            continue;
        BuildCandidateCenters(UnitState, Ability, Radius, EnemyCenters, Centers);
        Scan.Centers += Centers.Length;
        foreach Centers(Center)
        {
            ++Scan.Evaluated;
            if (!ComputeImpact(UnitState, Ability, Center, PreviewPath, Impact)
                || !EvaluateImpact(UnitState, Ability, Grenade, Radius, Impact,
                    VisibleEnemies, Target, CandidateLocations, CandidateScore))
                continue;
            ++Scan.Accepted;
            if (CandidateScore <= Score)
                continue;
            Action = Candidate;
            Action.AvailableTargets.Length = 0;
            Action.AvailableTargets.AddItem(Target);
            TargetIndex = 0;
            Locations = CandidateLocations;
            AimLocation = Center;
            Score = CandidateScore;
            bFound = true;
        }
    }
    return EndScan(bFound);
}

function bool PrepareForActivation(XComGameState_Unit UnitState,
    AvailableAction Action, vector AimLocation, const out array<vector> Locations)
{
    local GameRulesCache_Unit UnitCache;
    local AvailableAction CurrentAction;
    local XComGameState_Ability Ability;
    local X2GrenadeTemplate Grenade;
    local X2AbilityMultiTarget_Radius Radius;
    local array<StateObjectReference> VisibleEnemies;
    local AvailableTarget FreshTarget;
    local StateObjectReference TargetRef;
    local array<vector> FreshLocations;
    local vector Impact;
    local float Score;
    local bool bAvailable;

    if (UnitState == none || Locations.Length != 1 || Action.AvailableTargets.Length != 1
        || `PRECOMPUTEDPATH == none
        || !`TACTICALRULES.GetGameRulesCache_Unit(UnitState.GetReference(), UnitCache))
        return false;
    foreach UnitCache.AvailableActions(CurrentAction)
    {
        if (CurrentAction.AbilityObjectRef.ObjectID == Action.AbilityObjectRef.ObjectID)
        {
            bAvailable = GetSupportedGrenade(UnitState, CurrentAction, Ability, Grenade, Radius);
            break;
        }
    }
    if (!bAvailable || !ComputeImpact(UnitState, Ability, AimLocation, `PRECOMPUTEDPATH, Impact)
        || VSizeSq(Impact - Locations[0]) > 1.0)
        return false;
    class'X2TacticalVisibilityHelpers'.static.GetAllVisibleEnemiesForPlayer(
        UnitState.ControllingPlayer.ObjectID, VisibleEnemies);
    if (!EvaluateImpact(UnitState, Ability, Grenade, Radius, Impact,
        VisibleEnemies, FreshTarget, FreshLocations, Score)
        || FreshLocations.Length != 1 || VSizeSq(FreshLocations[0] - Locations[0]) > 1.0
        || FreshTarget.PrimaryTarget != Action.AvailableTargets[0].PrimaryTarget
        || FreshTarget.AdditionalTargets.Length != Action.AvailableTargets[0].AdditionalTargets.Length)
        return false;
    foreach FreshTarget.AdditionalTargets(TargetRef)
    {
        if (Action.AvailableTargets[0].AdditionalTargets.Find('ObjectID', TargetRef.ObjectID) == INDEX_NONE)
            return false;
    }
    return true;
}
