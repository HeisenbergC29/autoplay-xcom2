// Source-backed estimates for player-visible hostiles and own public statuses.
// These weights are planner heuristics, not native hit probabilities. Never
// inspect an enemy's current AP, ammo, cooldowns, charges or private AI intent.
class APX_EnemyKnowledge extends Object
    dependson(X2TacticalGameRulesetDataStructures);

const Capability_Control=1;
const Capability_Area=2;
const Capability_Support=4;

// Spread is symmetric around Damage. PlusOne is a percentage chance to add
// one damage, rather than another flat damage term. Crit is deliberately absent.
static function float MeanWeaponDamage(float Damage, int PlusOne)
{
    if (Damage <= 0.0)
        return -1.0;
    return Damage + float(Clamp(PlusOne, 0, 100)) / 100.0;
}

static function float WeaponThreatWeight(float MeanDamage, float Offense)
{
    local float DamageWeight, AimWeight;

    // Missing configuration must preserve the existing geometric risk.
    if (MeanDamage <= 0.0)
        return 1.0;
    DamageWeight = FClamp(MeanDamage / 3.0, 0.75, 1.5);
    AimWeight = 1.0;
    if (Offense > 0.0)
        AimWeight = FClamp(Offense / 65.0, 0.85, 1.15);
    return FClamp(DamageWeight * AimWeight, 0.75, 1.6);
}

// Marked is a displayed penalty on our own unit. Read its installed GameCore
// bonus rather than guessing from the enemy's intent or remaining abilities.
static function int KnownMarkedAimBonus(XComGameState_Unit UnitState)
{
    if (UnitState == none
        || !UnitState.IsUnitAffectedByEffectName(class'X2StatusEffects'.default.MarkedName))
        return 0;
    return class'X2Effect_Marked'.default.ACCURACY_CHANCE_BONUS;
}

static function float MarkedRiskScale(float Bonus)
{
    // A bounded planning weight, not native hit chance or expected damage.
    // Negative or missing bonuses must preserve the unmarked estimate.
    return 1.0 + FClamp(Bonus, 0.0, 50.0) / 100.0;
}

static function float TargetStatusWeight(XComGameState_Unit UnitState)
{
    return MarkedRiskScale(float(KnownMarkedAimBonus(UnitState)));
}

static function float TargetThreatValue(float WeaponWeight, bool bControl,
    bool bArea, bool bSupport, bool bLost)
{
    local float Value;

    if (bLost)
        return 0.6;
    Value = WeaponWeight;
    if (bControl)
        Value += 0.15;
    if (bArea)
        Value += 0.10;
    if (bSupport)
        Value += 0.10;
    // Existing kill-probability weighting remains bounded. A remote or
    // unavailable special attack is not a guarantee of next-turn damage.
    return FClamp(Value, 0.75, 1.5);
}

static function float PrimaryWeaponMeanDamage(XComGameState_Unit Enemy)
{
    local XComGameState_Item Weapon;
    local X2WeaponTemplate WeaponTemplate;
    local WeaponDamageValue Damage;

    if (Enemy == none)
        return -1.0;
    Weapon = Enemy.GetPrimaryWeapon();
    if (Weapon == none)
        return -1.0;
    WeaponTemplate = X2WeaponTemplate(Weapon.GetMyTemplate());
    if (WeaponTemplate == none)
        return -1.0;
    // Read the installed template, including its loaded game configuration.
    // This does not roll damage or inspect current ammunition/upgrades.
    Damage = WeaponTemplate.BaseDamage;
    return MeanWeaponDamage(Damage.Damage, Damage.PlusOne);
}

// Cheap per-contact scalar. Movement searches cache this beside their visible
// enemy list; it intentionally does not scan abilities for every candidate tile.
static function float ThreatWeight(XComGameState_Unit Enemy)
{
    if (Enemy == none)
        return 1.0;
    return WeaponThreatWeight(PrimaryWeaponMeanDamage(Enemy), Enemy.GetCurrentStat(eStat_Offense));
}

static function bool HasPlayerInputTrigger(X2AbilityTemplate Template)
{
    local X2AbilityTrigger Trigger;

    if (Template == none || Template.AbilityTriggers.Length > 16)
        return false;
    foreach Template.AbilityTriggers(Trigger)
    {
        if (X2AbilityTrigger_PlayerInput(Trigger) != none)
            return true;
    }
    return false;
}

static function int EffectCapabilities(X2Effect Effect)
{
    if (Effect == none)
        return 0;
    // Mindspin, panic/stun and sustained hostile binds can remove an action or
    // a squad member. This classifies the effect, not the enemy's species.
    if (Effect.IsA('X2Effect_MindControl') || Effect.IsA('X2Effect_Panicked')
        || Effect.IsA('X2Effect_Stunned') || Effect.IsA('X2Effect_Sustained'))
        return Capability_Control;
    // MarkTarget helps other shooters; PsiReanimation creates another actor.
    // Actual active-link release bonuses remain CombatPlanner's separate work.
    if (Effect.IsA('X2Effect_Marked') || Effect.IsA('X2Effect_SpawnPsiZombie'))
        return Capability_Support;
    return 0;
}

// Potential capabilities only. Do not call CanActivateAbility/CanAfford or
// read charges/cooldowns to determine the enemy's hidden current availability.
static function int CapabilityFlags(XComGameState_Unit Enemy)
{
    local StateObjectReference AbilityRef;
    local XComGameState_Ability Ability;
    local X2AbilityTemplate Template;
    local X2Effect Effect;
    local int Flags;

    if (Enemy == none || Enemy.Abilities.Length > 128)
        return 0;
    foreach Enemy.Abilities(AbilityRef)
    {
        Ability = XComGameState_Ability(`XCOMHISTORY.GetGameStateForObjectID(AbilityRef.ObjectID));
        if (Ability == none || Ability.OwnerStateObject.ObjectID != Enemy.ObjectID)
            continue;
        Template = Ability.GetMyTemplate();
        if (Template == none || Template.Hostility != eHostility_Offensive
            || !HasPlayerInputTrigger(Template))
            continue;
        if (Template.AbilityMultiTargetStyle != none
            && (Template.AbilityMultiTargetStyle.IsA('X2AbilityMultiTarget_Radius')
                || Template.AbilityMultiTargetStyle.IsA('X2AbilityMultiTarget_Cylinder')
                || Template.AbilityMultiTargetStyle.IsA('X2AbilityMultiTarget_Cone')
                || Template.AbilityMultiTargetStyle.IsA('X2AbilityMultiTarget_Line')))
            Flags = Flags | Capability_Area;
        foreach Template.AbilityTargetEffects(Effect)
            Flags = Flags | EffectCapabilities(Effect);
        foreach Template.AbilityMultiTargetEffects(Effect)
            Flags = Flags | EffectCapabilities(Effect);
    }
    return Flags;
}

static function float TargetThreat(XComGameState_Unit Enemy)
{
    local int Flags;

    if (Enemy == none)
        return 1.0;
    Flags = CapabilityFlags(Enemy);
    return TargetThreatValue(ThreatWeight(Enemy), (Flags & Capability_Control) != 0,
        (Flags & Capability_Area) != 0, (Flags & Capability_Support) != 0,
        Enemy.GetTeam() == eTeam_TheLost);
}

// CounterattackPreparation installs Counterattack and a once-per-turn private
// value. Knowing the capability is safe; reading whether it was spent is not.
// SDK counterattack resolution explicitly excludes publicly impaired targets.
static function bool HasMeleeCounter(XComGameState_Unit Enemy)
{
    local StateObjectReference AbilityRef;

    if (Enemy == none || !Enemy.IsAlive() || Enemy.IsImpaired())
        return false;
    AbilityRef = Enemy.FindAbility('CounterattackPreparation');
    if (AbilityRef.ObjectID != 0)
        return true;
    AbilityRef = Enemy.FindAbility('Counterattack');
    return AbilityRef.ObjectID != 0;
}
