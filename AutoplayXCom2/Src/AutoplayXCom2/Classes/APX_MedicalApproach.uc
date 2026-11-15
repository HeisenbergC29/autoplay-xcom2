// #28 — support-only medical eligibility and native single-target geometry.
// Never constructs an ability/target, spends AP/charges or mutates UnitState.
// Any after-move range test is a read-only preview, NOT AA_Success after move.
class APX_MedicalApproach extends Object
    dependson(X2GameRuleset, X2TacticalGameRulesetDataStructures);

static function bool IsLiveSquadPatient(XComGameState_Unit Medic,
    XComGameState_Unit Patient)
{
    return Medic != none && Patient != none
        && Medic.ObjectID != Patient.ObjectID
        && Medic.GetTeam() == eTeam_XCom && Patient.GetTeam() == eTeam_XCom
        && Medic.GetAssociatedPlayerID() == Patient.GetAssociatedPlayerID()
        && Medic.IsFriendlyUnit(Patient)
        && !Patient.bRemoved && !Patient.bRemovedFromPlay
        && Patient.GetMyTemplate() != none
        && !Patient.GetMyTemplate().bIsCosmetic
        && Patient.IsAlive() && !Patient.IsBleedingOut()
        && !Patient.IsBeingCarried()
        && Patient.GetCurrentStat(eStat_HP) > 0.0;
}

// Use the ACTUAL configured damage types installed on THIS ability, not
// IsPoisoned() alone. A modified/different medikit may cure another status,
// and an unrelated poison effect may not be curable by this source.
static function bool HasRemovableEffect(XComGameState_Ability Ability,
    XComGameState_Unit Patient)
{
    local X2Effect Effect;
    local X2Effect_RemoveEffectsByDamageType Removal;
    local name DamageType;

    if (Ability == none || Ability.GetMyTemplate() == none || Patient == none)
        return false;
    foreach Ability.GetMyTemplate().AbilityTargetEffects(Effect)
    {
        Removal = X2Effect_RemoveEffectsByDamageType(Effect);
        if (Removal == none)
            continue;
        foreach Removal.DamageTypesToRemove(DamageType)
        {
            if (Patient.IsUnitAffectedByDamageType(DamageType))
                return true;
        }
    }
    return false;
}

static function bool HasUsefulNeed(XComGameState_Ability Ability,
    XComGameState_Unit Patient)
{
    if (Ability == none || Patient == none || !Patient.IsAlive()
        || Patient.IsBleedingOut() || Patient.bRemovedFromPlay)
        return false;
    return Patient.GetCurrentStat(eStat_HP) < Patient.GetMaxStat(eStat_HP)
        || HasRemovableEffect(Ability, Patient);
}

// Only the 3 source-audited abilities, with stock native single-target
// constraints. CanActivateAbility performs actual shooter AP/cooldown/charge
// checks independently of a currently missing target/out-of-range target.
// TargetConditions test ACTUAL patient state (not fabricated after-move state).
static function bool IsReadyForApproach(XComGameState_Unit Medic,
    XComGameState_Unit Patient, XComGameState_Ability Ability)
{
    local X2AbilityTemplate Template;
    local X2AbilityTarget_Single Single;
    local name AbilityName;

    if (!IsLiveSquadPatient(Medic, Patient) || Ability == none
        || Ability.OwnerStateObject.ObjectID != Medic.ObjectID
        || !Medic.IsAbleToAct() || !HasUsefulNeed(Ability, Patient)
        || !Ability.IsAbilityInputTriggered() || Ability.IsAbilityFreeAiming())
        return false;
    AbilityName = Ability.GetMyTemplateName();
    if (AbilityName != 'MedikitHeal' && AbilityName != 'NanoMedikitHeal'
        && AbilityName != 'GremlinHeal')
        return false;
    Template = Ability.GetMyTemplate();
    if (Template == none || Template.Hostility != eHostility_Defensive
        || Template.AbilityMultiTargetStyle != none)
        return false;
    Single = X2AbilityTarget_Single(Template.AbilityTargetStyle);
    if (Single == none || Single.Class != class'X2AbilityTarget_Single')
        return false;
    // Medikit and Gremlin use separate actual ammo/charge cost templates.
    // The non-targeted CanActivateAbility includes the real cost and cooldown.
    return Ability.CanActivateAbility(Medic) == 'AA_Success'
        && Template.CheckTargetConditions(Ability, Medic, Patient) == 'AA_Success';
}

// Check the native cache NOW. An already available heal is an action to
// compare in CombatPlanner, not a reason to waste an AP repositioning.
static function bool HasNativeTargetNow(XComGameState_Unit Medic,
    XComGameState_Unit Patient, XComGameState_Ability Ability)
{
    local GameRulesCache_Unit Cache;
    local AvailableAction Action;
    local AvailableTarget Target;

    if (Medic == none || Patient == none || Ability == none || `TACTICALRULES == none
        || !`TACTICALRULES.GetGameRulesCache_Unit(Medic.GetReference(), Cache))
        return false;
    foreach Cache.AvailableActions(Action)
    {
        if (Action.AvailableCode != 'AA_Success'
            || Action.AbilityObjectRef.ObjectID != Ability.ObjectID)
            continue;
        foreach Action.AvailableTargets(Target)
        {
            if (Target.PrimaryTarget.ObjectID == Patient.ObjectID)
                return true;
        }
    }
    return false;
}

// Gremlin's remote/global target style may have -1 unlimited range.
// Without a finite range, moving towards the patient has no proven benefit:
// reject an invented geometric goal. The game's native RemoteTile validator
// remains the final read-only geometry check for finite-range variants.
static function bool CanTreatFromTile(XComGameState_Unit Medic,
    XComGameState_Unit Patient, XComGameState_Ability Ability, TTile Tile)
{
    local X2AbilityTarget_Single Single;
    local float HitRange;
    local vector Proposed, PatientLocation;

    if (!IsReadyForApproach(Medic, Patient, Ability) || `XWORLD == none)
        return false;
    Single = X2AbilityTarget_Single(Ability.GetMyTemplate().AbilityTargetStyle);
    if (Single == none)
        return false;
    HitRange = Single.GetHitRange(Ability);
    if (HitRange < 0.0)
        return false; // unlimited native remote heal: no finite-range approach.
    Proposed = `XWORLD.GetPositionFromTileCoordinates(Tile);
    PatientLocation = `XWORLD.GetPositionFromTileCoordinates(Patient.TileLocation);
    return VSizeSq(Proposed - PatientLocation) <= Square(HitRange)
        && Single.ValidatePrimaryTargetOptionFromRemoteLocation(
            Medic, Tile, Patient);
}

// Already-legal patient status is beneficial even at max HP IF (and only if)
// an actual removal effect installed on this ability matches the actual
// persistent damage type. Native AA_Success was checked by CombatPlanner.
static function float ScoreUsefulHealing(float BaseHealthScore, bool bRelevantEffect,
    bool bPoisoned, bool bBleeding)
{
    if (bBleeding)
        return -10000.0;
    if (!bRelevantEffect)
        return BaseHealthScore;
    if (BaseHealthScore <= -1000.0)
        return bPoisoned ? 170.0 : 105.0;
    return BaseHealthScore + (bPoisoned ? 55.0 : 25.0);
}

static function float ScoreMedicalApproach(bool bTreatAfterBlue,
    bool bBleeding, float PatientHealthFraction, bool bRemovablePoison,
    float Progress, float CurrentRisk, float DestinationRisk,
    float MedicHealthFraction, float PathCost, float Spacing)
{
    local float Value, Increase;

    // Never treat a guessed second-turn future medical target as legal NOW.
    if (!bTreatAfterBlue || bBleeding || Progress < 0.5
        || PatientHealthFraction <= 0.0 || PatientHealthFraction >= 1.0
            && !bRemovablePoison)
        return -10000.0;
    Increase = FMax(0.0, DestinationRisk - CurrentRisk);
    Value = (PatientHealthFraction <= 0.45 ? 210.0 : 78.0);
    if (bRemovablePoison)
        Value += 48.0;
    Value += FMin(18.0, FMax(0.0, Progress) * 3.0)
        + (1.0 - FClamp(PatientHealthFraction, 0.0, 1.0)) * 30.0;
    Value -= DestinationRisk * 0.35 + Increase * 2.0
        + FMax(0.0, PathCost) * 0.35
        + FMax(0.0, Spacing) * 1.2;
    if (MedicHealthFraction < 0.5 && Increase > 0.0)
        Value -= 80.0;
    return Value;
}
