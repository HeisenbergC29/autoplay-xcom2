// Presentation-only fix for the stock DevastatingPunchMP template.
// Ordinary DevastatingPunch hides failed damage-effect visual results on
// both hit and miss effects, but the MP template omits those flags.
class X2DownloadableContentInfo_AutoplayXCom2 extends X2DownloadableContentInfo;

static event OnPostTemplatesCreated()
{
    local X2AbilityTemplateManager Manager;
    local array<X2AbilityTemplate> Templates;
    local int Index;

    Manager = class'X2AbilityTemplateManager'.static.GetAbilityTemplateManager();
    if (Manager == none)
        return;
    Manager.FindAbilityTemplateAllDifficulties('DevastatingPunchMP', Templates);
    for (Index = 0; Index < Templates.Length; ++Index)
        PatchMPFailureVisualization(Templates[Index]);
}

// No game-state mutations, damage changes, roll changes or action-cost changes.
// Validate the exact template shape before mutating either visualization flag.
static function bool PatchMPFailureVisualization(X2AbilityTemplate Template)
{
    local X2Effect Effect;
    local X2Effect_ApplyWeaponDamage DamageEffect, HitEffect, MissEffect;
    local X2Effect_ImmediateAbilityActivation ImpairingEffect;
    local int DamageCount, ImpairingCount;

    if (Template == none || Template.DataName != 'DevastatingPunchMP')
        return false;

    foreach Template.AbilityTargetEffects(Effect)
    {
        DamageEffect = X2Effect_ApplyWeaponDamage(Effect);
        if (DamageEffect != none)
        {
            ++DamageCount;
            if (DamageEffect.bApplyOnHit && !DamageEffect.bApplyOnMiss)
                HitEffect = DamageEffect;
            else if (!DamageEffect.bApplyOnHit && DamageEffect.bApplyOnMiss
                && DamageEffect.bIgnoreBaseDamage)
                MissEffect = DamageEffect;
        }
        ImpairingEffect = X2Effect_ImmediateAbilityActivation(Effect);
        if (ImpairingEffect != none
            && ImpairingEffect.AbilityName == class'X2Ability_Impairing'.default.ImpairingAbilityName)
            ++ImpairingCount;
    }
    if (DamageCount != 2 || HitEffect == none || MissEffect == none
        || ImpairingCount != 1)
        return false;

    // This stock effect property is used only in BuildVisualization. Do not
    // change application of the hit, miss or Impairing effects themselves.
    if (HitEffect.HideVisualizationOfResultsAdditional.Find('AA_HitResultFailure') == INDEX_NONE)
        HitEffect.HideVisualizationOfResultsAdditional.AddItem('AA_HitResultFailure');
    if (MissEffect.HideVisualizationOfResultsAdditional.Find('AA_HitResultFailure') == INDEX_NONE)
        MissEffect.HideVisualizationOfResultsAdditional.AddItem('AA_HitResultFailure');
    return true;
}
