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
        && Patient.IsAlive() && !Patient.IsIncapacitated()
        && !Patient.IsBleedingOut() && !Patient.IsBeingCarried()
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

// An already legal URGENT heal for any own squadmate should not be
// displaced by speculative repositioning. Minor scratches still compete
// fairly with an approach to a dying teammate instead of vetoing it.
// Read only the native actions CombatPlanner can actually dispatch.
static function bool HasUrgentNativeHealNow(XComGameState_Unit Medic)
{
    local GameRulesCache_Unit Cache;
    local AvailableAction Action;
    local AvailableTarget Target;
    local XComGameState_Ability Ability;
    local XComGameState_Unit Patient;
    local name AbilityName;
    local int Scanned, TargetChecks;

    if (Medic == none || `TACTICALRULES == none
        || !`TACTICALRULES.GetGameRulesCache_Unit(Medic.GetReference(), Cache))
        return true; // Incomplete native data cannot justify speculative movement.
    foreach Cache.AvailableActions(Action)
    {
        if (++Scanned > 80)
            return true; // Incomplete scan: do not propose a speculative move.
        if (Action.AvailableCode != 'AA_Success' || !Action.bInputTriggered
            || Action.bFreeAim)
            continue;
        Ability = XComGameState_Ability(`XCOMHISTORY.GetGameStateForObjectID(
            Action.AbilityObjectRef.ObjectID));
        if (Ability == none || Ability.OwnerStateObject.ObjectID != Medic.ObjectID)
            continue;
        AbilityName = Ability.GetMyTemplateName();
        if (AbilityName != 'MedikitHeal' && AbilityName != 'NanoMedikitHeal'
            && AbilityName != 'GremlinHeal')
            continue;
        foreach Action.AvailableTargets(Target)
        {
            if (++TargetChecks > 128)
                return true;
            Patient = XComGameState_Unit(`XCOMHISTORY.GetGameStateForObjectID(
                Target.PrimaryTarget.ObjectID));
            if (Patient != none && Patient.IsAlive()
                && !Patient.IsIncapacitated() && !Patient.IsBleedingOut()
                && !Patient.bRemoved && !Patient.bRemovedFromPlay
                && Patient.GetTeam() == eTeam_XCom
                && Patient.GetAssociatedPlayerID() == Medic.GetAssociatedPlayerID()
                && Medic.IsFriendlyUnit(Patient)
                && HasUsefulNeed(Ability, Patient)
                && (Patient.GetCurrentStat(eStat_HP)
                    <= Patient.GetMaxStat(eStat_HP) * 0.45
                    || (Patient.IsPoisoned()
                        && HasRemovableEffect(Ability, Patient))))
                return true;
        }
    }
    return false;
}

// The budget lives in Controller.MakeDecision and is passed by reference
// through every medic. It is never replenished for another soldier.
static function int RemainingApproachSamples(int RemainingSamples)
{
    return Max(0, RemainingSamples - 1);
}

static function bool CanProposeApproach(bool bUrgentSquadHealAvailable,
    int RemainingSamples)
{
    return !bUrgentSquadHealAvailable && RemainingSamples > 0;
}

// Read the existing local roster once per decision, without updating it.
// Missing/truncated data conservatively keeps normal native action selection.
static function bool HasUrgentSquadHealNow(int PlayerID)
{
    local XComGameState_Player PlayerState;
    local XGPlayer PlayerVisualizer;
    local XGSquad Squad;
    local XGUnit Member;
    local XComGameState_Unit Medic;
    local int Count, Index;

    if (`XCOMHISTORY == none || `TACTICALRULES == none
        || PlayerID != `TACTICALRULES.GetLocalClientPlayerObjectID())
        return true;
    PlayerState = XComGameState_Player(`XCOMHISTORY.GetGameStateForObjectID(PlayerID));
    if (PlayerState == none || PlayerState.GetTeam() != eTeam_XCom)
        return true;
    PlayerVisualizer = XGPlayer(PlayerState.GetVisualizer());
    if (PlayerVisualizer == none || PlayerVisualizer.ObjectID != PlayerID
        || PlayerVisualizer.m_kSquad == none)
        return true;
    Squad = PlayerVisualizer.m_kSquad;
    if (Squad.m_kPlayer != PlayerVisualizer)
        return true;
    Count = Squad.GetNumMembers();
    if (Count <= 0 || Count > 24)
        return true;
    for (Index = 0; Index < Count; ++Index)
    {
        Member = Squad.GetMemberAt(Index);
        if (Member == none || Member.ObjectID <= 0)
            return true;
        Medic = XComGameState_Unit(`XCOMHISTORY.GetGameStateForObjectID(Member.ObjectID));
        if (Medic == none || Medic.GetMyTemplate() == none)
            return true;
        if (Medic.GetAssociatedPlayerID() != PlayerID || Medic.GetTeam() != eTeam_XCom
            || !Medic.IsAlive() || Medic.IsIncapacitated() || Medic.IsBleedingOut()
            || Medic.bRemoved || Medic.bRemovedFromPlay || Medic.GetMyTemplate().bIsCosmetic
            || !Medic.IsAbleToAct())
            continue;
        if (HasUrgentNativeHealNow(Medic))
            return true;
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

    // Caller has already checked real shooter charges/cooldown/AP and
    // patient target conditions once before bounded reachable sampling.
    if (!IsLiveSquadPatient(Medic, Patient) || Ability == none
        || Ability.OwnerStateObject.ObjectID != Medic.ObjectID || `XWORLD == none)
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
    bool bPoisoned, bool bBleeding, optional bool bInvalidPatient)
{
    // Effect removal must never revive ScoreMedical's hard patient vetoes.
    if (bBleeding || bInvalidPatient)
        return -10000.0;
    if (!bRelevantEffect)
        return BaseHealthScore;
    if (BaseHealthScore <= -1000.0)
    {
        if (bPoisoned)
            return 170.0;
        return 105.0;
    }
    if (bPoisoned)
        return BaseHealthScore + 55.0;
    return BaseHealthScore + 25.0;
}

static function float ScoreMedicalApproach(bool bTreatAfterBlue,
    bool bBleeding, float PatientHealthFraction, bool bRemovablePoison,
    float Progress, float CurrentRisk, float DestinationRisk,
    float MedicHealthFraction, float PathCost, float Spacing)
{
    local float Value, Increase;

    // Never treat a guessed second-turn future medical target as legal NOW.
    if (!bTreatAfterBlue || bBleeding || Progress < 0.5)
        return -10000.0;
    if (PatientHealthFraction <= 0.0 || (PatientHealthFraction >= 1.0 && !bRemovablePoison))
        return -10000.0;
    Increase = FMax(0.0, DestinationRisk - CurrentRisk);
    Value = 78.0;
    if (PatientHealthFraction <= 0.45)
        Value = 210.0;
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
