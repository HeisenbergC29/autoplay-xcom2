// Evaluates legal, player-visible actions. Never changes unit state or grants AP.
class APX_CombatPlanner extends Object config(AutoplayXCom2)
    dependson(X2GameRuleset, XComGameState_Ability, X2TacticalGameRulesetDataStructures);

var config array<name> AttackAbilities;
var config array<name> HealAbilities;
var config array<name> StabilizeAbilities;
var config array<name> ReloadAbilities;
var config array<name> OverwatchAbilities;
var config array<name> HunkerAbilities;
var config array<name> SupportAbilities;
var config int MinimumHitChance;
var config float EmergencyHealthFraction;

static function bool ChooseAction(XComGameState_Unit UnitState,
    out AvailableAction Action, out int TargetIndex, out float Score,
    optional bool bRecentContact)
{
    local XComGameStateHistory History;
    local GameRulesCache_Unit UnitCache;
    local AvailableAction Candidate, EmptyAction;
    local XComGameState_Ability Ability;
    local XComGameState_Unit TargetUnit;
    local X2AbilityTemplate AbilityTemplate;
    local array<StateObjectReference> VisibleEnemies;
    local name AbilityName;
    local int Index, SelfIndex;
    local float CandidateScore, MeleePenalty;
    local bool bFound;

    Action = EmptyAction;
    TargetIndex = INDEX_NONE;
    Score = -10000.0;
    if (UnitState == none || !UnitState.IsAbleToAct() || `TACTICALRULES == none)
        return false;

    History = `XCOMHISTORY;
    if (!`TACTICALRULES.GetGameRulesCache_Unit(UnitState.GetReference(), UnitCache))
        return false;

    // Player visibility includes a squadmate spotting a valid squadsight target.
    // Do not enumerate all hostile units in history to find hidden targets.
    class'X2TacticalVisibilityHelpers'.static.GetAllVisibleEnemiesForPlayer(
        UnitState.ControllingPlayer.ObjectID, VisibleEnemies);

    foreach UnitCache.AvailableActions(Candidate)
    {
        if (!Candidate.bInputTriggered || Candidate.AvailableCode != 'AA_Success'
            || Candidate.bFreeAim)
            continue;

        Ability = XComGameState_Ability(History.GetGameStateForObjectID(Candidate.AbilityObjectRef.ObjectID));
        if (Ability == none)
            continue;
        AbilityTemplate = Ability.GetMyTemplate();
        if (AbilityTemplate == none)
            continue;
        AbilityName = Ability.GetMyTemplateName();

        // Free-aim/radius/cone attacks need a separate collateral-damage solver.
        if (AbilityTemplate.AbilityMultiTargetStyle != none
            && !AbilityTemplate.AbilityMultiTargetStyle.IsA('X2AbilityMultiTarget_Volt')
            && !AbilityTemplate.AbilityMultiTargetStyle.IsA('X2AbilityMultiTarget_BurstFire'))
            continue;

        if (default.AttackAbilities.Find(AbilityName) != INDEX_NONE)
        {
            for (Index = 0; Index < Candidate.AvailableTargets.Length; ++Index)
            {
                TargetUnit = XComGameState_Unit(History.GetGameStateForObjectID(
                    Candidate.AvailableTargets[Index].PrimaryTarget.ObjectID));
                if (TargetUnit != none)
                {
                    if (!IsVisibleHostile(UnitState, TargetUnit, VisibleEnemies)
                        || !AdditionalTargetsAreSafe(UnitState, Candidate.AvailableTargets[Index], VisibleEnemies))
                        continue;
                    if (!HasRequiredMeleePath(UnitState, TargetUnit, AbilityTemplate,
                        VisibleEnemies, MeleePenalty))
                        continue;
                    CandidateScore = ScoreAttack(Ability, Candidate.AvailableTargets[Index], TargetUnit);
                    CandidateScore -= MeleePenalty;
                }
                else
                {
                    CandidateScore = ScoreObjectiveAttack(UnitState, Ability,
                        Candidate.AvailableTargets[Index]);
                }
                if (CandidateScore > Score)
                {
                    Action = Candidate;
                    TargetIndex = Index;
                    Score = CandidateScore;
                    bFound = CandidateScore > -1000.0;
                }
            }
        }
        else if (default.HealAbilities.Find(AbilityName) != INDEX_NONE
            || default.StabilizeAbilities.Find(AbilityName) != INDEX_NONE)
        {
            for (Index = 0; Index < Candidate.AvailableTargets.Length; ++Index)
            {
                TargetUnit = XComGameState_Unit(History.GetGameStateForObjectID(
                    Candidate.AvailableTargets[Index].PrimaryTarget.ObjectID));
                CandidateScore = ScoreMedical(UnitState, TargetUnit,
                    default.StabilizeAbilities.Find(AbilityName) != INDEX_NONE);
                if (CandidateScore > Score)
                {
                    Action = Candidate;
                    TargetIndex = Index;
                    Score = CandidateScore;
                    bFound = CandidateScore > -1000.0;
                }
            }
        }
        else if (default.SupportAbilities.Find(AbilityName) != INDEX_NONE)
        {
            for (Index = 0; Index < Candidate.AvailableTargets.Length; ++Index)
            {
                TargetUnit = XComGameState_Unit(History.GetGameStateForObjectID(
                    Candidate.AvailableTargets[Index].PrimaryTarget.ObjectID));
                CandidateScore = ScoreSupport(UnitState, TargetUnit, AbilityName, VisibleEnemies);
                if (CandidateScore > Score)
                {
                    Action = Candidate;
                    TargetIndex = Index;
                    Score = CandidateScore;
                    bFound = CandidateScore > -1000.0;
                }
            }
        }
        else
        {
            SelfIndex = FindSelfTarget(Candidate, UnitState.ObjectID);
            if (Candidate.AvailableTargets.Length > 0 && SelfIndex == INDEX_NONE)
                continue;
            CandidateScore = ScoreSelfAction(UnitState, Ability, AbilityName, VisibleEnemies, bRecentContact);
            if (CandidateScore > Score)
            {
                Action = Candidate;
                TargetIndex = SelfIndex;
                Score = CandidateScore;
                bFound = CandidateScore > -1000.0;
            }
        }
    }
    return bFound;
}

static function bool HasRequiredMeleePath(XComGameState_Unit SourceUnit,
    XComGameState_Unit TargetUnit, X2AbilityTemplate AbilityTemplate,
    array<StateObjectReference> VisibleEnemies, out float RiskPenalty)
{
    local array<TTile> Destinations, Path;
    local XGUnit UnitVisualizer;
    local int Index;

    RiskPenalty = 0.0;
    if (AbilityTemplate.TargetingMethod == none || !AbilityTemplate.TargetingMethod.default.ProvidesPath)
        return true;
    if (AbilityTemplate.AbilityTargetStyle == none
        || !AbilityTemplate.AbilityTargetStyle.IsA('X2AbilityTarget_MovingMelee'))
        return false;

    UnitVisualizer = XGUnit(SourceUnit.GetVisualizer());
    if (UnitVisualizer == none || UnitVisualizer.m_kReachableTilesCache == none)
        return false;
    UnitVisualizer.m_kReachableTilesCache.UpdateTileCacheIfNeeded();
    if (!class'X2AbilityTarget_MovingMelee'.static.SelectAttackTile(
        SourceUnit, TargetUnit, AbilityTemplate, Destinations) || Destinations.Length == 0)
        return false;
    if (Destinations[0] == SourceUnit.TileLocation)
        return true;

    // This is the same destination/path selection used by ActivateAbility_Internal
    // when an AI activates a moving-melee ability without a supplied path.
    if (!UnitVisualizer.m_kReachableTilesCache.BuildPathToTile(Destinations[0], Path)
        || Path.Length < 2)
        return false;
    for (Index = 1; Index < Path.Length; ++Index)
    {
        if (class'XComPath'.static.TileContainsHazard(SourceUnit, Path[Index]))
            return false;
    }
    // Melee spends its own AP and can strand the attacker beside other aliens.
    // Account for all squad-visible threats at the actual native attack tile.
    RiskPenalty = class'APX_MissionPlanner'.static.ExposureRisk(
        SourceUnit, Destinations[0], VisibleEnemies) * 0.65;
    return true;
}

static function bool IsVisibleHostile(XComGameState_Unit SourceUnit,
    XComGameState_Unit TargetUnit, const out array<StateObjectReference> VisibleEnemies)
{
    return TargetUnit != none && TargetUnit.IsAlive() && !TargetUnit.IsIncapacitated()
        && !TargetUnit.GetMyTemplate().bIsCosmetic && !TargetUnit.IsCivilian()
        && TargetUnit.GetMyTemplateName() != 'HostileVIPCivilian'
        && SourceUnit.IsEnemyUnit(TargetUnit)
        && VisibleEnemies.Find('ObjectID', TargetUnit.ObjectID) != INDEX_NONE;
}

static function bool AdditionalTargetsAreSafe(XComGameState_Unit SourceUnit,
    AvailableTarget Target, const out array<StateObjectReference> VisibleEnemies)
{
    local StateObjectReference TargetRef;
    local XComGameState_Unit TargetUnit;

    foreach Target.AdditionalTargets(TargetRef)
    {
        TargetUnit = XComGameState_Unit(`XCOMHISTORY.GetGameStateForObjectID(TargetRef.ObjectID));
        if (!IsVisibleHostile(SourceUnit, TargetUnit, VisibleEnemies))
            return false;
    }
    return true;
}

// Stock damage previews report raw damage separately from armour and piercing.
// Burst-fire previews aggregate shots, so apply mitigation per shot. Ignoring
// later shred is conservative and avoids claiming a kill that armour prevents.
static function float PreviewDamageAfterArmor(float Damage, float Armor,
    float Pierce, int Shots)
{
    Shots = Max(1, Shots);
    if (Damage <= 0.0)
        return 0.0;
    return FMax(1.0, Damage / float(Shots)
        - FMax(0.0, Armor - Pierce / float(Shots))) * float(Shots);
}

static function bool AbilityIgnoresArmor(X2AbilityTemplate AbilityTemplate)
{
    local X2Effect Effect;
    local X2Effect_ApplyWeaponDamage DamageEffect;

    foreach AbilityTemplate.AbilityTargetEffects(Effect)
    {
        DamageEffect = X2Effect_ApplyWeaponDamage(Effect);
        if (DamageEffect != none && DamageEffect.bIgnoreArmor)
            return true;
    }
    return false;
}

// A range-based estimate, not a prediction of the hidden damage roll. The
// guaranteed case is exact for the supplied preview; intermediate rolls use a
// uniform approximation and intentionally omit critical-hit luck.
static function float EstimatedKillChance(float MinDamage, float MaxDamage,
    float Health, float HitChance)
{
    if (Health <= 0.0 || MaxDamage <= 0.0)
        return 0.0;
    if (MinDamage >= Health)
        return FClamp(HitChance, 0.0, 100.0) / 100.0;
    if (MaxDamage < Health)
        return 0.0;
    return FClamp(HitChance, 0.0, 100.0) / 100.0
        * FClamp((MaxDamage - Health + 1.0) / (MaxDamage - MinDamage + 1.0), 0.0, 1.0);
}

static function float ScoreDamage(float MinDamage, float MaxDamage,
    float Health, float HitChance, float Threat, float WoundFraction)
{
    local float Chance, ExpectedDamage, KillChance;

    if (MaxDamage <= 0.0 || Health <= 0.0)
        return -10000.0;
    Chance = FClamp(HitChance, 0.0, 100.0) / 100.0;
    // Cap each endpoint separately: a pistol that finishes a wounded alien
    // should not lose to a high-damage attack wasting most of its damage.
    ExpectedDamage = (FMin(Health, MinDamage) + FMin(Health, MaxDamage)) * 0.5 * Chance;
    KillChance = EstimatedKillChance(MinDamage, MaxDamage, Health, HitChance);
    return 5.0 + ExpectedDamage * 8.0 + KillChance * 65.0 * FClamp(Threat, 0.6, 1.5)
        + Chance * (4.0 + FClamp(WoundFraction, 0.0, 1.0) * 8.0);
}

// The preview aggregates Rapid Fire / Fan Fire damage, but their hit rolls
// remain independent. Do not value two required hits like one guaranteed hit.
// When partial-hit damage might suffice, use a conservative all-hits estimate;
// when every individual hit is lethal, use the chance of at least one hit.
static function float BurstKillChance(float MinDamage, float MaxDamage,
    float Health, float HitChance, int Shots)
{
    local float Chance, AllHit, AllMiss;

    Chance = FClamp(HitChance, 0.0, 100.0) / 100.0;
    AllHit = Chance;
    AllMiss = 1.0 - Chance;
    if (Shots >= 2)
    {
        AllHit *= Chance;
        AllMiss *= 1.0 - Chance;
    }
    if (Shots >= 3)
    {
        AllHit *= Chance;
        AllMiss *= 1.0 - Chance;
    }
    if (Shots > 3)
        return 0.0;
    if (MinDamage / float(Max(1, Shots)) >= Health)
        return 1.0 - AllMiss;
    return EstimatedKillChance(MinDamage, MaxDamage, Health, 100.0) * AllHit;
}

static function float ScoreAttack(XComGameState_Ability Ability,
    AvailableTarget Target, XComGameState_Unit TargetUnit)
{
    local ShotBreakdown Breakdown;
    local WeaponDamageValue MinDamage, MaxDamage;
    local X2AbilityMultiTarget_BurstFire BurstFire;
    local int HitChance, AllowsShield, Shots;
    local float Armor, Health, MinHPDamage, MaxHPDamage, Threat, Result;

    if (Ability.GetMyTemplate().AbilityToHitCalc == none)
        return -10000.0;
    HitChance = Clamp(Ability.GetShotBreakdown(Target, Breakdown), 0, 100);
    if (HitChance < default.MinimumHitChance)
        return -10000.0;

    Ability.GetDamagePreview(Target.PrimaryTarget, MinDamage, MaxDamage, AllowsShield);
    Armor = TargetUnit.GetArmorMitigationForUnitFlag();
    if (AbilityIgnoresArmor(Ability.GetMyTemplate()))
        Armor = 0.0;
    Shots = 1;
    BurstFire = X2AbilityMultiTarget_BurstFire(Ability.GetMyTemplate().AbilityMultiTargetStyle);
    if (BurstFire != none)
        Shots += BurstFire.NumExtraShots;
    MinHPDamage = PreviewDamageAfterArmor(MinDamage.Damage, Armor, MinDamage.Pierce, Shots);
    MaxHPDamage = PreviewDamageAfterArmor(MaxDamage.Damage, Armor, MaxDamage.Pierce, Shots);
    Health = TargetUnit.GetCurrentStat(eStat_HP);
    if (AllowsShield > 0)
        Health += TargetUnit.GetCurrentStat(eStat_ShieldHP);
    // Remove dangerous weapons first when kill probabilities are comparable.
    // Do not reserve a target optimistically: the controller recomputes after
    // every actual result, so a missed kill naturally leaves a follow-up shot.
    Threat = FClamp(TargetUnit.GetCurrentStat(eStat_Offense) / 65.0, 0.75, 1.35);
    if (TargetUnit.GetTeam() == eTeam_TheLost)
        Threat = 0.6;
    Result = ScoreDamage(MinHPDamage, MaxHPDamage, Health, HitChance, Threat,
        1.0 - TargetUnit.GetCurrentStat(eStat_HP) / FMax(1.0, TargetUnit.GetMaxStat(eStat_HP)));
    if (Shots > 1)
        Result += (BurstKillChance(MinHPDamage, MaxHPDamage, Health, HitChance, Shots)
            - EstimatedKillChance(MinHPDamage, MaxHPDamage, Health, HitChance))
            * 65.0 * FClamp(Threat, 0.6, 1.5);
    // Spend free attacks before turn-ending shots and conserve scarce attacks
    // when an ordinary shot gives essentially the same outcome.
    if (Ability.GetMyTemplateName() == 'LightningHands'
        || Ability.GetMyTemplateName() == 'Whiplash')
        Result += 12.0;
    if (Ability.GetMyTemplateName() == 'CombatProtocol'
        || Ability.GetMyTemplateName() == 'HailOfBullets'
        || Ability.GetMyTemplateName() == 'Soulfire')
        Result -= 8.0;
    return Result;
}

// A mission relay/transmitter is a destructible state rather than a unit. Only
// consider it when the normal rules cache supplied a legal ranged attack and
// the game marks it as a hostile, visible mission objective. Ordinary cover,
// explosive scenery, and friendly defense devices are never attack goals.
static function float ScoreObjectiveAttack(XComGameState_Unit SourceUnit,
    XComGameState_Ability Ability, AvailableTarget Target)
{
    local XComGameState_Destructible Destructible;
    local X2AbilityTemplate AbilityTemplate;
    local ShotBreakdown Breakdown;
    local WeaponDamageValue MinDamage, MaxDamage;
    local int HitChance, AllowsShield;
    local float ExpectedDamage, Result;

    AbilityTemplate = Ability.GetMyTemplate();
    if (Target.AdditionalTargets.Length != 0
        || AbilityTemplate.AbilityTargetStyle == none
        || !AbilityTemplate.AbilityTargetStyle.IsA('X2AbilityTarget_Single')
        || AbilityTemplate.AbilityTargetStyle.IsA('X2AbilityTarget_MovingMelee')
        || AbilityTemplate.AbilityMultiTargetStyle != none
        || AbilityTemplate.AbilityToHitCalc == none)
        return -10000.0;
    if (AbilityTemplate.TargetingMethod != none
        && AbilityTemplate.TargetingMethod.default.ProvidesPath)
        return -10000.0;

    Destructible = XComGameState_Destructible(`XCOMHISTORY.GetGameStateForObjectID(Target.PrimaryTarget.ObjectID));
    if (Destructible == none || Destructible.Health <= 0
        || !Destructible.IsTargetable(SourceUnit.GetTeam())
        || !SourceUnit.TargetIsEnemy(Destructible.ObjectID)
        || !class'Helpers'.static.IsObjectiveTarget(Destructible.ObjectID)
        || !class'X2TacticalVisibilityHelpers'.static.CanXComSquadSeeTarget(Destructible.ObjectID))
        return -10000.0;

    HitChance = Clamp(Ability.GetShotBreakdown(Target, Breakdown), 0, 100);
    if (HitChance < default.MinimumHitChance)
        return -10000.0;
    Ability.GetDamagePreview(Target.PrimaryTarget, MinDamage, MaxDamage, AllowsShield);
    ExpectedDamage = float(MinDamage.Damage + MaxDamage.Damage) * 0.5 * float(HitChance) / 100.0;
    if (ExpectedDamage <= 0.0)
        return -10000.0;
    Result = 160.0 + ExpectedDamage * 8.0;
    if (MinDamage.Damage >= Destructible.Health)
        Result += 25.0 * float(HitChance) / 100.0;
    return Result;
}

static function float ScoreMedical(XComGameState_Unit SourceUnit,
    XComGameState_Unit TargetUnit, bool bStabilize)
{
    local float Health, MaxHealth, MissingHealth;

    if (TargetUnit == none || !SourceUnit.IsFriendlyUnit(TargetUnit))
        return -10000.0;
    if (bStabilize)
        return TargetUnit.IsBleedingOut() ? 400.0 : -10000.0;
    if (!TargetUnit.IsAlive() || TargetUnit.IsBleedingOut())
        return -10000.0;

    Health = TargetUnit.GetCurrentStat(eStat_HP);
    MaxHealth = FMax(1.0, TargetUnit.GetMaxStat(eStat_HP));
    MissingHealth = MaxHealth - Health;
    if (MissingHealth <= 0.0)
        return -10000.0;
    if (Health / MaxHealth <= default.EmergencyHealthFraction)
        return 140.0 + MissingHealth * 4.0;
    return 20.0 + MissingHealth * 4.0;
}

static function int FindSelfTarget(AvailableAction Action, int UnitID)
{
    local int Index;
    for (Index = 0; Index < Action.AvailableTargets.Length; ++Index)
    {
        if (Action.AvailableTargets[Index].PrimaryTarget.ObjectID == UnitID)
            return Index;
    }
    return INDEX_NONE;
}

static function float ScoreSelfAction(XComGameState_Unit UnitState,
    XComGameState_Ability Ability, name AbilityName,
    array<StateObjectReference> VisibleEnemies, optional bool bRecentContact)
{
    local XComGameState_Item Weapon;
    local int RangedThreats, NearbyMelee;
    local float RangedRisk, HealthFraction;

    if (default.ReloadAbilities.Find(AbilityName) != INDEX_NONE)
    {
        Weapon = XComGameState_Item(`XCOMHISTORY.GetGameStateForObjectID(Ability.SourceWeapon.ObjectID));
        if (Weapon == none)
            Weapon = UnitState.GetItemInSlot(eInvSlot_PrimaryWeapon);
        if (Weapon == none || Weapon.Ammo >= Weapon.GetClipSize())
            return -10000.0;
        if (Weapon.Ammo == 0)
            return ScoreEmptyReload(VisibleEnemies.Length > 0, bRecentContact);
        return ScorePartialReload(VisibleEnemies.Length > 0, bRecentContact);
    }
    if (default.OverwatchAbilities.Find(AbilityName) == INDEX_NONE
        && default.HunkerAbilities.Find(AbilityName) == INDEX_NONE)
        return -10000.0;

    RangedRisk = DefensiveRisk(UnitState, VisibleEnemies, RangedThreats, NearbyMelee);
    HealthFraction = UnitState.GetCurrentStat(eStat_HP)
        / FMax(1.0, UnitState.GetMaxStat(eStat_HP));
    if (default.OverwatchAbilities.Find(AbilityName) != INDEX_NONE)
        return ScoreOverwatchDefense(VisibleEnemies.Length > 0 || bRecentContact,
            UnitState.IsConcealed(), HealthFraction, RangedRisk, NearbyMelee);
    return ScoreHunkerDefense(HealthFraction, RangedRisk, RangedThreats,
        NearbyMelee, UnitState.IsBurning(), UnitState.IsConcealed());
}

static function float ScorePartialReload(bool bVisibleEnemy, bool bRecentContact)
{
    if (bRecentContact)
        return 1.0;
    if (bVisibleEnemy)
        return 3.0;
    return 12.0;
}

static function float ScoreEmptyReload(bool bVisibleEnemy, bool bRecentContact)
{
    if (bVisibleEnemy || bRecentContact)
        return 35.0;
    return 18.0;
}

// Evaluate ranged exposure separately: hunker does not turn an approaching
// melee attacker into a safe threat. Contacts are limited to the player's view.
static function float DefensiveRisk(XComGameState_Unit UnitState,
    array<StateObjectReference> VisibleEnemies, out int RangedThreats, out int NearbyMelee)
{
    local XComGameState_Unit Enemy;
    local StateObjectReference EnemyRef;
    local vector UnitLocation, EnemyLocation;
    local float Distance, Angle, Risk, TotalRisk, WorstRisk;
    local ECoverType Cover;
    local int CoverLevel;

    RangedThreats = 0;
    NearbyMelee = 0;
    UnitLocation = `XWORLD.GetPositionFromTileCoordinates(UnitState.TileLocation);
    foreach VisibleEnemies(EnemyRef)
    {
        Enemy = XComGameState_Unit(`XCOMHISTORY.GetGameStateForObjectID(EnemyRef.ObjectID));
        if (!IsVisibleHostile(UnitState, Enemy, VisibleEnemies))
            continue;
        Distance = class'APX_MissionPlanner'.static.TileDistance(UnitState.TileLocation, Enemy.TileLocation);
        if (Enemy.IsMeleeOnly())
        {
            if (Distance <= 8.0)
                ++NearbyMelee;
            continue;
        }
        ++RangedThreats;
        EnemyLocation = `XWORLD.GetPositionFromTileCoordinates(Enemy.TileLocation);
        Cover = `XWORLD.GetCoverTypeForTarget(EnemyLocation, UnitLocation, Angle);
        CoverLevel = 0;
        if (Cover == CT_MidLevel)
            CoverLevel = 1;
        if (Cover == CT_Standing)
            CoverLevel = 2;
        Risk = class'APX_MissionPlanner'.static.DirectionalRisk(CoverLevel, Distance,
            UnitState.GetMyTemplate().bCanTakeCover, false);
        TotalRisk += Risk;
        WorstRisk = FMax(WorstRisk, Risk);
    }
    return class'APX_MissionPlanner'.static.CombinedExposure(TotalRisk, WorstRisk, 1.0);
}

// Defensive values deliberately compete with poor shots, not reliable kills.
// Out of contact overwatch stays below every useful advance/exploration score.
static function float ScoreOverwatchDefense(bool bEnemiesVisible, bool bConcealed,
    float HealthFraction, float RangedRisk, int NearbyMelee)
{
    local float Result;

    if (!bEnemiesVisible)
        return 2.0;
    Result = 17.0;
    if (bConcealed)
        Result = 22.0;
    Result -= FMin(7.0, RangedRisk * 0.12) * (1.0 - FClamp(HealthFraction, 0.0, 1.0));
    // A nearby melee attacker is likely to move; an available reaction can be
    // preferable to hunkering, while a legal immediate kill still scores higher.
    if (NearbyMelee > 0)
        Result += 5.0;
    return Result;
}

static function float ScoreHunkerDefense(float HealthFraction, float RangedRisk,
    int RangedThreats, int NearbyMelee, bool bBurning, bool bConcealed)
{
    local float Result;

    // Stock HunkerDown removes Burning, even without a visible enemy.
    if (bBurning)
        return 130.0;
    if (RangedThreats == 0 || bConcealed)
        return 1.0;
    Result = 13.0 + (1.0 - FClamp(HealthFraction, 0.0, 1.0)) * 24.0
        + FMin(18.0, RangedRisk * 0.4);
    if (NearbyMelee > 0)
        Result -= 12.0;
    return FMax(1.0, Result);
}

static function float ScoreSupport(XComGameState_Unit SourceUnit,
    XComGameState_Unit TargetUnit, name AbilityName,
    array<StateObjectReference> VisibleEnemies)
{
    local int RangedThreats, NearbyMelee;
    local float Risk, HealthFraction;

    if (AbilityName != 'AidProtocol' || TargetUnit == none || !TargetUnit.IsAlive()
        || TargetUnit.IsIncapacitated() || !SourceUnit.IsFriendlyUnit(TargetUnit)
        || TargetUnit.IsCivilian() || TargetUnit.GetMyTemplate().bIsCosmetic
        || TargetUnit.IsUnitAffectedByEffectName('AidProtocol'))
        return -10000.0;
    Risk = DefensiveRisk(TargetUnit, VisibleEnemies, RangedThreats, NearbyMelee);
    HealthFraction = TargetUnit.GetCurrentStat(eStat_HP)
        / FMax(1.0, TargetUnit.GetMaxStat(eStat_HP));
    return ScoreAidDefense(HealthFraction, Risk, RangedThreats);
}

static function float ScoreAidDefense(float HealthFraction, float RangedRisk, int RangedThreats)
{
    if (RangedThreats == 0 || RangedRisk < 6.0)
        return -10000.0;
    return 16.0 + FMin(20.0, RangedRisk * 0.4)
        + (1.0 - FClamp(HealthFraction, 0.0, 1.0)) * 24.0;
}

// Stable labels for the mission recorder; action availability and numeric
// scores are logged separately and remain the evidence for the final choice.
static function string GetActionReason(XComGameState_Unit UnitState, name AbilityName)
{
    if (default.OverwatchAbilities.Find(AbilityName) != INDEX_NONE)
        return "reserve_reaction_shot";
    if (default.HunkerAbilities.Find(AbilityName) != INDEX_NONE)
    {
        if (UnitState != none && UnitState.IsBurning())
            return "extinguish_burning";
        return "reduce_ranged_risk";
    }
    if (default.SupportAbilities.Find(AbilityName) != INDEX_NONE)
        return "protect_exposed_ally";
    if (default.HealAbilities.Find(AbilityName) != INDEX_NONE)
        return "heal_wounded_ally";
    if (default.StabilizeAbilities.Find(AbilityName) != INDEX_NONE)
        return "stabilize_bleeding_ally";
    if (default.ReloadAbilities.Find(AbilityName) != INDEX_NONE)
        return "restore_ammunition";
    if (default.AttackAbilities.Find(AbilityName) != INDEX_NONE)
        return "damage_and_elimination_chance";
    return "outside_combat_allowlist";
}
