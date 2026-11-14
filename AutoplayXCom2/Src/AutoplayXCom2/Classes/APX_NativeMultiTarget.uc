// #38b: currently native-legal single-click multi-target actions.
// Unlike grenades, these cannot be sent through X2TargetingMethod_Grenade,
// a precomputed projectile actor, or the AreaAttackPlanner free-aim contract.
// Only stock Faceoff is admitted: real self-primary, native enemy list,
// individually checked current visibility and a conservative shot preview.
class APX_NativeMultiTarget extends Object
    dependson(X2GameRuleset, X2TacticalGameRulesetDataStructures);

static function bool SupportedFaceoff(XComGameState_Unit Shooter,
    XComGameState_Ability Ability)
{
    local X2AbilityTemplate Template;
    local X2AbilityMultiTarget_AllUnits Multi;
    local XComGameState_Item Weapon;
    local X2Effect_ApplyWeaponDamage DamageEffect;

    if (Shooter == none || Ability == none
        || Ability.OwnerStateObject.ObjectID != Shooter.ObjectID
        || Ability.GetMyTemplateName() != 'Faceoff')
        return false;
    Template = Ability.GetMyTemplate();
    if (Template == none || Template.Hostility != eHostility_Offensive
        || Template.TargetingMethod != none
        || Template.AbilityToHitCalc == none
        || Template.AbilityMultiTargetEffects.Length != 1)
        return false;
    Multi = X2AbilityMultiTarget_AllUnits(Template.AbilityMultiTargetStyle);
    if (Multi == none || Multi.Class != class'X2AbilityMultiTarget_AllUnits'
        || !Multi.bUseAbilitySourceAsPrimaryTarget || !Multi.bAcceptEnemyUnits
        || Multi.bAcceptFriendlyUnits || !Multi.bDontAcceptNeutralUnits
        || Multi.bRandomlySelectOne || Multi.RandomChance > 0)
        return false;
    DamageEffect = X2Effect_ApplyWeaponDamage(Template.AbilityMultiTargetEffects[0]);
    if (DamageEffect == none || DamageEffect.bExplosiveDamage)
        return false;
    Weapon = Ability.GetSourceWeapon();
    // Unknown ammo splash/delayed effects are not silently modeled as bullets.
    if (Weapon == none || Weapon.GetLoadedAmmoTemplate(Ability) != none)
        return false;
    return true;
}

// One real source-executed scoring rule, not an asserted certain kill.
// Min-damage finish only counts as "strong" when the native hit preview is
// >=70%, still strictly NOT a guaranteed future hit or a native score.
static function float ScoreFaceoffOutcome(int TargetCount, int StrongFinishes,
    float DamageValue)
{
    if (TargetCount < 2 || TargetCount > 16 || DamageValue <= 0.0)
        return -10000.0;
    return DamageValue - 12.0 + FMin(12.0, float(Max(0, StrongFinishes)) * 5.0);
}

// The list comes directly from current AA_Success AvailableTargets. No
// predicted next target / hidden foe / future RNG is added. Fail the WHOLE
// ability if any native additional target is unsafe or not independently
// current-visible, including civilians, allies and controlled squadmates.
static function float ScoreFaceoff(XComGameState_Unit Shooter,
    XComGameState_Ability Ability, AvailableTarget NativeTarget,
    const out array<StateObjectReference> VisibleEnemies)
{
    local X2AbilityTemplate Template;
    local X2Effect_ApplyWeaponDamage DamageEffect;
    local StateObjectReference TargetRef;
    local XComGameState_Unit Enemy;
    local AvailableTarget Preview;
    local ShotBreakdown Breakdown;
    local WeaponDamageValue MinDamage, MaxDamage, EmptyDamage;
    local array<int> Seen;
    local float Armor, MinAfterArmor, MaxAfterArmor, Health, Value;
    local int Index, Chance, AllowsShield, StrongFinishes;

    if (!SupportedFaceoff(Shooter, Ability)
        || NativeTarget.PrimaryTarget.ObjectID != Shooter.ObjectID
        || NativeTarget.AdditionalTargets.Length < 2
        || NativeTarget.AdditionalTargets.Length > 16)
        return -10000.0;
    Template = Ability.GetMyTemplate();
    DamageEffect = X2Effect_ApplyWeaponDamage(Template.AbilityMultiTargetEffects[0]);

    for (Index = 0; Index < NativeTarget.AdditionalTargets.Length; ++Index)
    {
        TargetRef = NativeTarget.AdditionalTargets[Index];
        if (TargetRef.ObjectID <= 0 || Seen.Find(TargetRef.ObjectID) != INDEX_NONE)
            return -10000.0;
        Seen.AddItem(TargetRef.ObjectID);
        Enemy = XComGameState_Unit(`XCOMHISTORY.GetGameStateForObjectID(TargetRef.ObjectID));
        if (!class'APX_CombatPlanner'.static.IsVisibleHostile(
                Shooter, Enemy, VisibleEnemies)
            || class'APX_CombatPlanner'.static.IsReclaimableControlledSquadmate(
                Shooter, Enemy))
            return -10000.0;

        // Read-only COPY for a per-enemy shot estimate. Never substitute this
        // into the actual native Ability.AvailableTargets / action dispatch.
        Preview = NativeTarget;
        Preview.PrimaryTarget = TargetRef;
        Preview.AdditionalTargets.Length = 0;
        Chance = Ability.GetShotBreakdown(Preview, Breakdown);
        if (Chance < 0 || Chance > 100)
            return -10000.0;
        MinDamage = EmptyDamage;
        MaxDamage = EmptyDamage;
        AllowsShield = 0;
        DamageEffect.GetDamagePreview(TargetRef, Ability, false,
            MinDamage, MaxDamage, AllowsShield);
        Armor = Enemy.GetArmorMitigationForUnitFlag();
        if (DamageEffect.bIgnoreArmor)
            Armor = 0.0;
        MinAfterArmor = class'APX_CombatPlanner'.static.PreviewDamageAfterArmor(
            MinDamage.Damage, Armor, MinDamage.Pierce, 1);
        MaxAfterArmor = class'APX_CombatPlanner'.static.PreviewDamageAfterArmor(
            MaxDamage.Damage, Armor, MaxDamage.Pierce, 1);
        Health = Enemy.GetCurrentStat(eStat_HP) + Enemy.GetCurrentStat(eStat_ShieldHP);
        // This ability rolls separately per native additional target. The
        // breakdown is a current preview, not a guaranteed future hit.
        if (Health <= 0.0 || MinDamage.Damage < 0.0
            || MaxDamage.Damage < MinDamage.Damage)
            return -10000.0;
        if (Chance >= 70 && MinAfterArmor >= Health)
            ++StrongFinishes;
        Value += class'APX_CombatPlanner'.static.ScoreDamage(
            MinAfterArmor, MaxAfterArmor, Health, float(Chance), 1.0,
            1.0 - Enemy.GetCurrentStat(eStat_HP)
                / FMax(1.0, Enemy.GetMaxStat(eStat_HP)));
    }
    return ScoreFaceoffOutcome(Seen.Length, StrongFinishes, Value);
}
