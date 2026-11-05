// Bounded preparation + currently legal attack estimates. Never grants points,
// changes ammunition or commits a second action. The controller rescans after
// the preparation resolves, so the retained attack is an estimate, not a queue.
class APX_ActionEconomy extends Object
    dependson(X2GameRuleset, XComGameState_Ability);

static function float PreparationSequenceScore(float PreparationValue, float RetainedAttackValue)
{
    if (PreparationValue <= 0.0 || RetainedAttackValue <= 0.0)
        return PreparationValue;
    // Keep urgent medical priorities. Count one retained attack plus only a
    // bounded fraction of the preparation's benefit, rather than two full shots.
    return FMax(PreparationValue, RetainedAttackValue + FMin(20.0, PreparationValue * 0.5));
}

static function bool MeetsPointRequirement(int AllowedPoints, int RequiredPoints)
{
    return AllowedPoints >= Max(0, RequiredPoints);
}

static function bool IsSupportedPreparation(name AbilityName)
{
    // These stock actions do not consume the firearm's ammunition or move its
    // owner. Reload forecasts and damaging first actions need resource/target
    // projection beyond this local AP model and remain outside its scope.
    return AbilityName == 'AidProtocol' || AbilityName == 'MedikitHeal'
        || AbilityName == 'NanoMedikitHeal' || AbilityName == 'GremlinHeal'
        || AbilityName == 'MedikitStabilize' || AbilityName == 'GremlinStabilize';
}

static function bool ProjectAfterAction(XComGameState_Ability Ability,
    XComGameState_Unit UnitState, out array<name> RemainingPoints)
{
    local X2AbilityCost Cost;
    local X2AbilityCost_ActionPoints APCost;
    local int TypeIndex, PointIndex, Required, Allowed, Consumed;

    RemainingPoints.Length = 0;
    if (Ability == none || Ability.GetMyTemplate() == none || UnitState == none
        || Ability.OwnerStateObject.ObjectID != UnitState.ObjectID)
        return false;
    RemainingPoints = UnitState.ActionPoints;
    foreach Ability.GetMyTemplate().AbilityCosts(Cost)
    {
        APCost = X2AbilityCost_ActionPoints(Cost);
        if (APCost == none)
            continue;
        // Movement costs require a particular native path, and custom AP cost
        // subclasses may have additional semantics not represented by this copy.
        if (APCost.Class != class'X2AbilityCost_ActionPoints' || APCost.bMoveCost)
            return false;
        Required = APCost.GetPointCost(Ability, UnitState);
        Allowed = 0;
        for (TypeIndex = 0; TypeIndex < APCost.AllowedTypes.Length; ++TypeIndex)
        {
            for (PointIndex = 0; PointIndex < RemainingPoints.Length; ++PointIndex)
            {
                if (RemainingPoints[PointIndex] == APCost.AllowedTypes[TypeIndex])
                    ++Allowed;
            }
        }
        // Native CanAfford checks required AP even when ApplyCost is free.
        if (!MeetsPointRequirement(Allowed, Required))
            return false;
        if (APCost.bFreeCost)
            continue;
        if (APCost.ConsumeAllPoints(Ability, UnitState))
        {
            RemainingPoints.Length = 0;
            continue;
        }
        Consumed = 0;
        // Match native ApplyCost: specific AP types are spent before standard.
        for (TypeIndex = APCost.AllowedTypes.Length - 1;
            TypeIndex >= 0 && Consumed < Required; --TypeIndex)
        {
            for (PointIndex = RemainingPoints.Length - 1;
                PointIndex >= 0 && Consumed < Required; --PointIndex)
            {
                if (RemainingPoints[PointIndex] == APCost.AllowedTypes[TypeIndex])
                {
                    RemainingPoints.Remove(PointIndex, 1);
                    ++Consumed;
                }
            }
        }
        if (Consumed < Required)
            return false;
    }
    return true;
}

static function bool HasVisibleRulerReaction(XComGameState_Unit UnitState,
    const out array<StateObjectReference> VisibleEnemies)
{
    local StateObjectReference EnemyRef, ReactionRef;
    local XComGameState_Unit Enemy;
    local int Count;

    foreach VisibleEnemies(EnemyRef)
    {
        ++Count;
        if (Count > 128)
            break;
        Enemy = XComGameState_Unit(`XCOMHISTORY.GetGameStateForObjectID(EnemyRef.ObjectID));
        if (!class'APX_CombatPlanner'.static.IsVisibleHostile(UnitState, Enemy, VisibleEnemies))
            continue;
        // Installed public capability, never current AP, cooldown or intent.
        ReactionRef = Enemy.FindAbility('AlienRulerActionSystem');
        if (ReactionRef.ObjectID != 0)
            return true;
    }
    return false;
}

static function bool GetRetainedAttack(XComGameState_Unit UnitState,
    XComGameState_Ability Preparation, const out array<StateObjectReference> VisibleEnemies,
    out int FollowUpAbilityID, out int FollowUpTargetID, out float FollowUpValue)
{
    local GameRulesCache_Unit Cache;
    local AvailableAction Candidate;
    local AvailableTarget Target;
    local XComGameState_Ability Ability;
    local X2AbilityTemplate Template;
    local XComGameState_Unit TargetUnit;
    local array<name> RemainingPoints;
    local float Value;
    local int ActionCount, TargetCount;

    FollowUpAbilityID = 0;
    FollowUpTargetID = 0;
    FollowUpValue = 0.0;
    if (UnitState == none || !UnitState.IsAbleToAct() || UnitState.IsConcealed()
        || Preparation == none || Preparation.GetMyTemplate() == none
        || !IsSupportedPreparation(Preparation.GetMyTemplateName())
        || Preparation.CanActivateAbility(UnitState) != 'AA_Success'
        || VisibleEnemies.Length == 0 || `TACTICALRULES == none
        || HasVisibleRulerReaction(UnitState, VisibleEnemies)
        || !ProjectAfterAction(Preparation, UnitState, RemainingPoints)
        || !`TACTICALRULES.GetGameRulesCache_Unit(UnitState.GetReference(), Cache))
        return false;
    foreach Cache.AvailableActions(Candidate)
    {
        ++ActionCount;
        if (ActionCount > 128 || TargetCount >= 32)
            break;
        if (!Candidate.bInputTriggered || Candidate.AvailableCode != 'AA_Success'
            || Candidate.bFreeAim)
            continue;
        Ability = XComGameState_Ability(`XCOMHISTORY.GetGameStateForObjectID(Candidate.AbilityObjectRef.ObjectID));
        if (Ability == none || Ability.ObjectID == Preparation.ObjectID
            || Ability.OwnerStateObject.ObjectID != UnitState.ObjectID
            || class'APX_CombatPlanner'.default.AttackAbilities.Find(Ability.GetMyTemplateName()) == INDEX_NONE)
            continue;
        Template = Ability.GetMyTemplate();
        if (Template == none || Template.AbilityToHitCalc == none
            || Template.AbilityToHitCalc.IsA('X2AbilityToHitCalc_StandardMelee')
            || (Template.TargetingMethod != none && Template.TargetingMethod.default.ProvidesPath)
            || (Template.AbilityTargetStyle != none && Template.AbilityTargetStyle.IsA('X2AbilityTarget_MovingMelee'))
            || !class'APX_MissionPlanner'.static.CanAttackWithActionPoints(Ability, UnitState, RemainingPoints))
            continue;
        if (Template.AbilityMultiTargetStyle != none
            && !Template.AbilityMultiTargetStyle.IsA('X2AbilityMultiTarget_Volt')
            && !Template.AbilityMultiTargetStyle.IsA('X2AbilityMultiTarget_BurstFire'))
            continue;
        foreach Candidate.AvailableTargets(Target)
        {
            ++TargetCount;
            if (TargetCount > 32)
                break;
            TargetUnit = XComGameState_Unit(`XCOMHISTORY.GetGameStateForObjectID(Target.PrimaryTarget.ObjectID));
            if (!class'APX_CombatPlanner'.static.IsVisibleHostile(UnitState, TargetUnit, VisibleEnemies)
                || !class'APX_CombatPlanner'.static.AdditionalTargetsAreSafe(UnitState, Target, VisibleEnemies))
                continue;
            Value = class'APX_CombatPlanner'.static.ScoreAttack(Ability, Target, TargetUnit);
            if (Value > FollowUpValue)
            {
                FollowUpAbilityID = Ability.ObjectID;
                FollowUpTargetID = TargetUnit.ObjectID;
                FollowUpValue = Value;
            }
        }
    }
    return FollowUpAbilityID != 0 && FollowUpValue > 0.0;
}

static function float ScoreWithRetainedAttack(XComGameState_Unit UnitState,
    XComGameState_Ability Preparation, float PreparationValue,
    const out array<StateObjectReference> VisibleEnemies,
    out int FollowUpAbilityID, out int FollowUpTargetID, out float FollowUpValue)
{
    FollowUpAbilityID = 0;
    FollowUpTargetID = 0;
    FollowUpValue = 0.0;
    if (PreparationValue <= 0.0 || !GetRetainedAttack(UnitState, Preparation, VisibleEnemies,
        FollowUpAbilityID, FollowUpTargetID, FollowUpValue))
        return PreparationValue;
    return PreparationSequenceScore(PreparationValue, FollowUpValue);
}
