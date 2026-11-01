// Evaluates legal, player-visible actions. Never changes unit state or grants AP.
class APX_CombatPlanner extends Object config(AutoplayXCom2)
    dependson(X2GameRuleset, XComGameState_Ability, X2TacticalGameRulesetDataStructures);

var config array<name> AttackAbilities;
var config array<name> HealAbilities;
var config array<name> StabilizeAbilities;
var config array<name> ReloadAbilities;
var config array<name> OverwatchAbilities;
var config array<name> HunkerAbilities;
var config int MinimumHitChance;
var config float EmergencyHealthFraction;

static function bool ChooseAction(XComGameState_Unit UnitState,
    out AvailableAction Action, out int TargetIndex, out float Score)
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
    local float CandidateScore;
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
                    if (!HasRequiredMeleePath(UnitState, TargetUnit, AbilityTemplate))
                        continue;
                    CandidateScore = ScoreAttack(Ability, Candidate.AvailableTargets[Index], TargetUnit);
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
        else
        {
            SelfIndex = FindSelfTarget(Candidate, UnitState.ObjectID);
            if (Candidate.AvailableTargets.Length > 0 && SelfIndex == INDEX_NONE)
                continue;
            CandidateScore = ScoreSelfAction(UnitState, Ability, AbilityName, VisibleEnemies.Length > 0);
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
    XComGameState_Unit TargetUnit, X2AbilityTemplate AbilityTemplate)
{
    local array<TTile> Destinations, Path;
    local XGUnit UnitVisualizer;

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
    return UnitVisualizer.m_kReachableTilesCache.BuildPathToTile(Destinations[0], Path)
        && Path.Length > 1;
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

static function float ScoreAttack(XComGameState_Ability Ability,
    AvailableTarget Target, XComGameState_Unit TargetUnit)
{
    local ShotBreakdown Breakdown;
    local WeaponDamageValue MinDamage, MaxDamage;
    local int HitChance, AllowsShield;
    local float ExpectedDamage, Result;

    if (Ability.GetMyTemplate().AbilityToHitCalc == none)
        return -10000.0;
    HitChance = Clamp(Ability.GetShotBreakdown(Target, Breakdown), 0, 100);
    if (HitChance < default.MinimumHitChance)
        return -10000.0;

    Ability.GetDamagePreview(Target.PrimaryTarget, MinDamage, MaxDamage, AllowsShield);
    // Use the game's effects/weapon-tech preview. This is a heuristic: armour
    // mitigation and multi-shot outcomes can make actual HP damage differ.
    ExpectedDamage = float(MinDamage.Damage + MaxDamage.Damage) * 0.5 * float(HitChance) / 100.0;
    if (ExpectedDamage <= 0.0)
        return -10000.0;
    Result = 40.0 + ExpectedDamage * 8.0 + float(HitChance) * 0.12;
    if (float(MinDamage.Damage) >= TargetUnit.GetCurrentStat(eStat_HP)
        + TargetUnit.GetCurrentStat(eStat_ShieldHP))
        Result += 35.0 * float(HitChance) / 100.0;
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
    XComGameState_Ability Ability, name AbilityName, bool bEnemiesVisible)
{
    local XComGameState_Item Weapon;

    if (default.ReloadAbilities.Find(AbilityName) != INDEX_NONE)
    {
        Weapon = XComGameState_Item(`XCOMHISTORY.GetGameStateForObjectID(Ability.SourceWeapon.ObjectID));
        if (Weapon == none)
            Weapon = UnitState.GetItemInSlot(eInvSlot_PrimaryWeapon);
        if (Weapon == none || Weapon.Ammo >= Weapon.GetClipSize())
            return -10000.0;
        if (Weapon.Ammo == 0)
            return 85.0;
        return bEnemiesVisible ? 3.0 : 12.0;
    }
    if (default.OverwatchAbilities.Find(AbilityName) != INDEX_NONE)
        return 2.0;
    if (default.HunkerAbilities.Find(AbilityName) != INDEX_NONE)
    {
        if (bEnemiesVisible && UnitState.GetCurrentStat(eStat_HP)
            / FMax(1.0, UnitState.GetMaxStat(eStat_HP)) <= default.EmergencyHealthFraction)
            return 65.0;
        return 1.0;
    }
    return -10000.0;
}
