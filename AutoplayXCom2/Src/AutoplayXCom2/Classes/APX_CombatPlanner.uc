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
    local float CandidateScore, MeleePenalty, RetainedAttackValue;
    local int FollowUpAbilityID, FollowUpTargetID;
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
                CandidateScore = class'APX_ActionEconomy'.static.ScoreWithRetainedAttack(
                    UnitState, Ability, CandidateScore, VisibleEnemies,
                    FollowUpAbilityID, FollowUpTargetID, RetainedAttackValue);
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
                CandidateScore = class'APX_ActionEconomy'.static.ScoreWithRetainedAttack(
                    UnitState, Ability, CandidateScore, VisibleEnemies,
                    FollowUpAbilityID, FollowUpTargetID, RetainedAttackValue);
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
    local X2AbilityToHitCalc_StandardAim MeleeCalc;
    local int Index;
    local float StartSupport;
    local bool bRequireSupport;

    RiskPenalty = 0.0;
    // The native counterattack conversion can also defeat a guaranteed melee
    // preview. Check the visible capability before stationary/path shortcuts;
    // never inspect the enemy's private once-per-turn counter value.
    MeleeCalc = X2AbilityToHitCalc_StandardAim(AbilityTemplate.AbilityToHitCalc);
    if (MeleeCalc != none && MeleeCalc.bMeleeAttack
        && class'APX_EnemyKnowledge'.static.HasMeleeCounter(TargetUnit))
        return false;
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

    // A moving attack must obey the same formation and visible-terrain
    // limits as a normal combat move, even when the target is a likely kill.
    bRequireSupport = !class'APX_MissionPlanner'.static.ShouldEvacuate(SourceUnit);
    StartSupport = class'APX_MissionPlanner'.static.NearestSupportDistance(
        SourceUnit, SourceUnit.TileLocation);
    if (!class'APX_MissionPlanner'.static.IsKnownCombatTile(Destinations[0])
        || !class'APX_MissionPlanner'.static.IsSupportedCombatDestination(SourceUnit, Destinations[0])
        || (bRequireSupport && !class'APX_MissionPlanner'.static.IsSupportedAdvanceDestination(
            StartSupport, class'APX_MissionPlanner'.static.NearestSupportDistance(SourceUnit, Destinations[0]))))
        return false;

    // This is the same destination/path selection used by ActivateAbility_Internal
    // when an AI activates a moving-melee ability without a supplied path.
    if (!UnitVisualizer.m_kReachableTilesCache.BuildPathToTile(Destinations[0], Path)
        || Path.Length < 2)
        return false;
    for (Index = 1; Index < Path.Length; ++Index)
    {
        if (class'APX_HazardKnowledge'.static.HasBlockingHazard(SourceUnit, Path[Index])
            || !class'APX_MissionPlanner'.static.IsKnownCombatTile(Path[Index])
            || !class'X2TacticalVisibilityHelpers'.static.CanSquadSeeLocation(
                SourceUnit.ControllingPlayer.ObjectID, Path[Index])
            || (bRequireSupport && !class'APX_MissionPlanner'.static.IsSupportedAdvanceStep(
                StartSupport, class'APX_MissionPlanner'.static.NearestSupportDistance(SourceUnit, Path[Index]))))
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
        if (!IsVisibleHostile(SourceUnit, TargetUnit, VisibleEnemies)
            || IsReclaimableControlledSquadmate(SourceUnit, TargetUnit))
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

// This is the same historical ownership lookup used by the stock mind-control
// removal effect. Read only ownership of a currently visible affected unit,
// never its old position or other hidden contacts.
static function bool WasControlledByPlayerBeforeEffect(XComGameState_Unit UnitState,
    XComGameState_Effect EffectState, int PlayerID)
{
    local XComGameState_Effect OriginalEffect;
    local XComGameState OriginalState;
    local XComGameState_Unit PreviousUnit;

    if (UnitState == none || EffectState == none || PlayerID <= 0)
        return false;
    OriginalEffect = XComGameState_Effect(`XCOMHISTORY.GetOriginalGameStateRevision(EffectState.ObjectID));
    if (OriginalEffect == none)
        return false;
    OriginalState = OriginalEffect.GetParentGameState();
    if (OriginalState == none || OriginalState.HistoryIndex <= 0)
        return false;
    PreviousUnit = XComGameState_Unit(`XCOMHISTORY.GetGameStateForObjectID(
        UnitState.ObjectID,, OriginalState.HistoryIndex - 1));
    return PreviousUnit != none && PreviousUnit.ControllingPlayer.ObjectID == PlayerID;
}

// Prevent friendly fire against temporarily hostile squadmates who can be
// recovered by removing their active mind-control source. Only the visible
// target's current effect links and its earlier ownership are examined; no
// hidden source position, readiness, AI intent or resource is inspected.
static function bool IsReclaimableControlledSquadmate(XComGameState_Unit SourceUnit,
    XComGameState_Unit TargetUnit)
{
    local StateObjectReference EffectRef;
    local XComGameState_Effect EffectState;
    local X2Effect_Persistent EffectTemplate;

    if (SourceUnit == none || TargetUnit == none
        || SourceUnit.ControllingPlayer.ObjectID <= 0
        || !SourceUnit.IsEnemyUnit(TargetUnit) || !TargetUnit.IsMindControlled())
        return false;
    foreach TargetUnit.AffectedByEffects(EffectRef)
    {
        EffectState = XComGameState_Effect(`XCOMHISTORY.GetGameStateForObjectID(EffectRef.ObjectID));
        if (EffectState == none || EffectState.bRemoved
            || EffectState.ApplyEffectParameters.TargetStateObjectRef.ObjectID != TargetUnit.ObjectID)
            continue;
        EffectTemplate = EffectState.GetX2Effect();
        if (X2Effect_MindControl(EffectTemplate) != none
            && EffectTemplate.bRemoveWhenSourceDies
            && WasControlledByPlayerBeforeEffect(TargetUnit, EffectState,
                SourceUnit.ControllingPlayer.ObjectID))
            return true;
    }
    return false;
}

// Count actual active links on visible contacts, rather than valuing an enemy
// merely because its character template can create zombies or mind control.
// A death-linked zombie is not also counted as a rescued ally if both effects
// exist on it. No source effect is removed here; the game resolves every result.
static function GetKnownSourceBenefits(XComGameState_Unit SourceUnit,
    XComGameState_Unit Enemy, out int ReleasedAllies, out int LinkedEnemies)
{
    local array<StateObjectReference> VisibleEnemies;
    local array<int> CountedTargets;
    local StateObjectReference TargetRef, EffectRef, KillLinkedRef;
    local XComGameState_Unit LinkedUnit;
    local XComGameState_Effect EffectState;
    local X2Effect_Persistent EffectTemplate;
    local bool bCanEndZombie, bReleased, bLinked;
    local int Index, PlayerID;

    ReleasedAllies = 0;
    LinkedEnemies = 0;
    if (SourceUnit == none || Enemy == none)
        return;
    PlayerID = SourceUnit.ControllingPlayer.ObjectID;
    class'X2TacticalVisibilityHelpers'.static.GetAllVisibleEnemiesForPlayer(PlayerID, VisibleEnemies);
    if (!IsVisibleHostile(SourceUnit, Enemy, VisibleEnemies))
        return;
    KillLinkedRef = Enemy.FindAbility('KillSiredZombies');
    bCanEndZombie = KillLinkedRef.ObjectID > 0;
    for (Index = 0; Index < Min(64, VisibleEnemies.Length); ++Index)
    {
        TargetRef = VisibleEnemies[Index];
        if (TargetRef.ObjectID == Enemy.ObjectID || CountedTargets.Find(TargetRef.ObjectID) != INDEX_NONE)
            continue;
        LinkedUnit = XComGameState_Unit(`XCOMHISTORY.GetGameStateForObjectID(TargetRef.ObjectID));
        if (LinkedUnit == none || !LinkedUnit.IsAlive() || LinkedUnit.IsIncapacitated()
            || LinkedUnit.bRemovedFromPlay || LinkedUnit.GetMyTemplate().bIsCosmetic
            || !SourceUnit.IsEnemyUnit(LinkedUnit))
            continue;
        bReleased = false;
        bLinked = false;
        foreach LinkedUnit.AffectedByEffects(EffectRef)
        {
            EffectState = XComGameState_Effect(`XCOMHISTORY.GetGameStateForObjectID(EffectRef.ObjectID));
            if (EffectState == none || EffectState.bRemoved
                || EffectState.ApplyEffectParameters.SourceStateObjectRef.ObjectID != Enemy.ObjectID
                || EffectState.ApplyEffectParameters.TargetStateObjectRef.ObjectID != LinkedUnit.ObjectID)
                continue;
            EffectTemplate = EffectState.GetX2Effect();
            if (EffectTemplate == none)
                continue;
            if (bCanEndZombie && EffectTemplate.EffectName == class'X2Ability_Sectoid'.default.SireZombieLinkName)
                bLinked = true;
            if (X2Effect_MindControl(EffectTemplate) != none && EffectTemplate.bRemoveWhenSourceDies
                && LinkedUnit.IsMindControlled()
                && WasControlledByPlayerBeforeEffect(LinkedUnit, EffectState, PlayerID))
                bReleased = true;
        }
        if (bLinked)
            ++LinkedEnemies;
        else if (bReleased)
            ++ReleasedAllies;
        if (bLinked || bReleased)
            CountedTargets.AddItem(TargetRef.ObjectID);
    }
}

// A source kill can remove further enemies or restore a controlled squadmate.
// This bounded benefit is conditional on the actual attack's kill estimate;
// restoration does not promise immediate AP: the stock effect clears the old
// budget, then grants a fresh one only when the restored owner is on turn.
static function float ScoreSourceBenefits(float KillChance, int ReleasedAllies, int LinkedEnemies)
{
    return FClamp(KillChance, 0.0, 1.0)
        * FMin(90.0, float(Max(0, ReleasedAllies)) * 45.0 + float(Max(0, LinkedEnemies)) * 25.0);
}

static function float ScoreAttack(XComGameState_Ability Ability,
    AvailableTarget Target, XComGameState_Unit TargetUnit)
{
    local ShotBreakdown Breakdown;
    local WeaponDamageValue MinDamage, MaxDamage;
    local X2AbilityMultiTarget_BurstFire BurstFire;
    local XComGameState_Unit SourceUnit;
    local int HitChance, AllowsShield, Shots, ReleasedAllies, LinkedEnemies;
    local float Armor, Health, MinHPDamage, MaxHPDamage, Threat, Result, KillChance;

    if (Ability.GetMyTemplate().AbilityToHitCalc == none)
        return -10000.0;
    SourceUnit = XComGameState_Unit(`XCOMHISTORY.GetGameStateForObjectID(Ability.OwnerStateObject.ObjectID));
    // Prefer disabling/killing the controller and recovering this soldier.
    if (IsReclaimableControlledSquadmate(SourceUnit, TargetUnit))
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
    Threat = class'APX_EnemyKnowledge'.static.TargetThreat(TargetUnit);
    Result = ScoreDamage(MinHPDamage, MaxHPDamage, Health, HitChance, Threat,
        1.0 - TargetUnit.GetCurrentStat(eStat_HP) / FMax(1.0, TargetUnit.GetMaxStat(eStat_HP)));
    KillChance = EstimatedKillChance(MinHPDamage, MaxHPDamage, Health, HitChance);
    if (Shots > 1)
    {
        Result += (BurstKillChance(MinHPDamage, MaxHPDamage, Health, HitChance, Shots)
            - KillChance) * 65.0 * FClamp(Threat, 0.6, 1.5);
        KillChance = BurstKillChance(MinHPDamage, MaxHPDamage, Health, HitChance, Shots);
    }
    // Multi-target actions need their own accounting so an affected linked
    // unit is not valued again as a consequence of the primary source kill.
    if (KillChance > 0.0 && Target.AdditionalTargets.Length == 0)
    {
        GetKnownSourceBenefits(SourceUnit, TargetUnit, ReleasedAllies, LinkedEnemies);
        Result += ScoreSourceBenefits(KillChance, ReleasedAllies, LinkedEnemies);
    }
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

// Bleeding is a distinct rescue state. Unconscious/stabilized soldiers need
// revival or evacuation instead; dead bodies must never become healing goals.
// Do not require IsAbleToAct/!IsIncapacitated on the patient being rescued.
static function bool IsRescuePatient(XComGameState_Unit SourceUnit,
    XComGameState_Unit TargetUnit)
{
    return SourceUnit != none && TargetUnit != none
        && SourceUnit.ObjectID != TargetUnit.ObjectID
        && SourceUnit.GetAssociatedPlayerID() == TargetUnit.GetAssociatedPlayerID()
        && SourceUnit.GetTeam() == eTeam_XCom && TargetUnit.GetTeam() == eTeam_XCom
        && SourceUnit.IsFriendlyUnit(TargetUnit)
        && !TargetUnit.bRemoved && !TargetUnit.bRemovedFromPlay
        && TargetUnit.GetMyTemplate() != none && !TargetUnit.GetMyTemplate().bIsCosmetic
        && TargetUnit.IsBleedingOut() && !TargetUnit.IsBeingCarried();
}

// CanActivateAbility checks the real shooter, cooldown, ammo/charges and AP,
// independently of whether a target currently lies in the medikit's range.
// This lets navigation propose a rescue without inventing an extra medikit.
static function XComGameState_Ability GetReadyStabilizeAbility(
    XComGameState_Unit SourceUnit, XComGameState_Unit TargetUnit)
{
    local StateObjectReference AbilityRef;
    local XComGameState_Ability Ability;
    local X2AbilityTemplate Template;

    if (!IsRescuePatient(SourceUnit, TargetUnit) || !SourceUnit.IsAbleToAct())
        return none;
    foreach SourceUnit.Abilities(AbilityRef)
    {
        Ability = XComGameState_Ability(`XCOMHISTORY.GetGameStateForObjectID(AbilityRef.ObjectID));
        if (Ability == none || Ability.OwnerStateObject.ObjectID != SourceUnit.ObjectID
            || default.StabilizeAbilities.Find(Ability.GetMyTemplateName()) == INDEX_NONE
            || !Ability.IsAbilityInputTriggered() || Ability.IsAbilityFreeAiming())
            continue;
        Template = Ability.GetMyTemplate();
        // Only the configured single-target stabilization contract is known.
        // Radius/revival abilities need an explicit planner of their own.
        if (Template == none || Template.Hostility != eHostility_Defensive
            || Template.AbilityTargetStyle == none
            || Template.AbilityTargetStyle.Class != class'X2AbilityTarget_Single'
            || Template.AbilityMultiTargetStyle != none)
            continue;
        if (Ability.CanActivateAbility(SourceUnit) == 'AA_Success'
            && Template.CheckTargetConditions(Ability, SourceUnit, TargetUnit) == 'AA_Success')
            return Ability;
    }
    return none;
}

// A position proposal, not an activation. The next decision still needs the
// native available-target cache to authorize the actual stabilization order.
static function bool CanStabilizeFromTile(XComGameState_Unit SourceUnit,
    XComGameState_Unit TargetUnit, XComGameState_Ability Ability, TTile Tile)
{
    local X2AbilityTemplate Template;
    local vector SourceLocation, TargetLocation;
    local float HitRange;

    if (!IsRescuePatient(SourceUnit, TargetUnit) || Ability == none
        || Ability.OwnerStateObject.ObjectID != SourceUnit.ObjectID)
        return false;
    Template = Ability.GetMyTemplate();
    if (Template == none || Template.AbilityTargetStyle == none
        || Template.AbilityTargetStyle.Class != class'X2AbilityTarget_Single'
        || Template.AbilityMultiTargetStyle != none
        || default.StabilizeAbilities.Find(Ability.GetMyTemplateName()) == INDEX_NONE)
        return false;
    HitRange = Template.AbilityTargetStyle.GetHitRange(Ability);
    if (HitRange < 0.0)
        return true;
    SourceLocation = `XWORLD.GetPositionFromTileCoordinates(Tile);
    TargetLocation = `XWORLD.GetPositionFromTileCoordinates(TargetUnit.TileLocation);
    return VSizeSq(SourceLocation - TargetLocation) <= Square(HitRange);
}

static function float ScoreMedical(XComGameState_Unit SourceUnit,
    XComGameState_Unit TargetUnit, bool bStabilize)
{
    local float Health, MaxHealth, MissingHealth;

    if (SourceUnit == none || TargetUnit == none)
        return -10000.0;
    if (TargetUnit.bRemoved || TargetUnit.bRemovedFromPlay || !SourceUnit.IsFriendlyUnit(TargetUnit))
        return -10000.0;
    if (bStabilize)
    {
        if (TargetUnit.IsBleedingOut())
            return 400.0;
        return -10000.0;
    }
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
    local float Distance, Risk, TotalRisk, WorstRisk;

    RangedThreats = 0;
    NearbyMelee = 0;
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
        // The same obstruction discount as movement: otherwise Aid Protocol
        // can displace an escape by valuing an obstructed shot as fully open.
        Risk = class'APX_MissionPlanner'.static.ThreatRiskAtTile(
            UnitState, Enemy, UnitState.TileLocation);
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
