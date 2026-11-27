/**
 * Read current, authorized tactical unit facts for program #120.
 * No weighting, ability readiness, targeting, game-state mutation or caching.
 * All outputs are stock scalar arrays; no cross-class custom struct dependency.
 */
class APX_UnitStats extends Object;

/** Stable positions in both output arrays. Keep in order for future consumers. */
const FactHP = 0;
const FactMaxHP = 1;
const FactShieldHP = 2;
const FactArmor = 3;
const FactOffense = 4;
const FactDefense = 5;
const FactMobility = 6;
const FactCount = 7;

const FactUnknown = 0;
const FactKnown = 1;

/**
 * Classify a scalar independently of the unit's name or ID. Zero is known.
 * Negative offense/defense modifiers are legitimate; negative HP/shield/
 * armor/mobility are not usable. Unavailable or NaN values are unknown.
 */
static function int FactStatus(float Value, bool bAvailable, bool bSigned)
{
    if (!bAvailable || Value != Value)
        return 0;
    if (!bSigned && Value < 0.0)
        return 0;
    return 1;
}

/** Clear both arrays on entry and on a rejected or superseded snapshot. */
static function ResetFacts(out array<float> Values, out array<int> Status)
{
    local int Index;

    Values.Length = FactCount;
    Status.Length = FactCount;
    for (Index = 0; Index < FactCount; ++Index)
    {
        Values[Index] = 0.0;
        Status[Index] = FactUnknown;
    }
}

/** Record a known scalar or an explicit unknown; do not use zero as a sentinel. */
static function StoreFact(out array<float> Values, out array<int> Status,
    int Index, float Value, bool bAvailable, bool bSigned)
{
    Status[Index] = FactStatus(Value, bAvailable, bSigned);
    Values[Index] = 0.0;
    if (Status[Index] == FactKnown)
        Values[Index] = Value;
}

/** Reject an old index, another history instance, or missing tactical services. */
static function bool IsCurrentSnapshot(XComGameStateHistory History, int HistoryIndex)
{
    return History != none && History == `XCOMHISTORY && HistoryIndex >= 0
        && History.GetCurrentHistoryIndex() == HistoryIndex
        && `TACTICALRULES != none && `XWORLD != none;
}

/**
 * The observer must be controlled by the local XCOM player. Own units need
 * the same controller; hostile units must pass the existing full-intel or
 * normal player-visibility policy. Never authorize a unit by its template name.
 */
static function bool IsAuthorizedSubject(XComGameState_Unit Observer,
    XComGameState_Unit Subject)
{
    local array<StateObjectReference> KnownEnemies;
    local int LocalPlayerID;

    if (`TACTICALRULES == none || Observer == none || Subject == none
        || Observer.GetMyTemplate() == none || Subject.GetMyTemplate() == none
        || Observer.GetMyTemplate().bIsCosmetic || Subject.GetMyTemplate().bIsCosmetic
        || Observer.bRemoved || Observer.bRemovedFromPlay
        || Subject.bRemoved || Subject.bRemovedFromPlay
        || Observer.IsCivilian() || Subject.IsCivilian()
        || Observer.GetTeam() != eTeam_XCom)
        return false;
    LocalPlayerID = `TACTICALRULES.GetLocalClientPlayerObjectID();
    if (LocalPlayerID <= 0 || Observer.GetAssociatedPlayerID() != LocalPlayerID)
        return false;
    if (Subject.GetAssociatedPlayerID() == LocalPlayerID
        && Subject.GetTeam() == eTeam_XCom)
        return true;
    if (!Observer.IsEnemyUnit(Subject) || !Subject.IsAlive()
        || Subject.IsIncapacitated())
        return false;

    // Reuse the existing policy rather than creating another visibility bypass.
    class'APX_FullIntel'.static.GetKnownEnemies(Observer, KnownEnemies);
    return KnownEnemies.Find('ObjectID', Subject.ObjectID) != INDEX_NONE;
}

/**
 * Read the native UI/UnitFlag armor total in damage points. Stock WOTC
 * adds installed bonus-armor effects to current ArmorMitigation and subtracts
 * Shredded. Preflight every effect reference because the stock getter assumes
 * it can resolve them. Incomplete evidence leaves armor unknown, not zero.
 * No damage roll or hypothetical target is needed.
 */
static function bool ReadArmor(XComGameStateHistory History, int HistoryIndex,
    XComGameState_Unit Subject, out float Armor)
{
    local StateObjectReference EffectRef;
    local XComGameState_Effect EffectState;

    Armor = 0.0;
    if (!IsCurrentSnapshot(History, HistoryIndex) || Subject == none
        || Subject.AffectedByEffects.Length > 128)
        return false;
    foreach Subject.AffectedByEffects(EffectRef)
    {
        if (EffectRef.ObjectID <= 0)
            return false;
        EffectState = XComGameState_Effect(History.GetGameStateForObjectID(
            EffectRef.ObjectID, eReturnType_Reference, HistoryIndex));
        if (EffectState == none || EffectState.bRemoved || EffectState.GetX2Effect() == none)
            return false;
    }
    Armor = Subject.GetArmorMitigationForUnitFlag();
    return FactStatus(Armor, IsCurrentSnapshot(History, HistoryIndex), false) == FactKnown;
}

/**
 * Populate one already authorized snapshot. Use native current values (not
 * template base stats); MaxHP uses the native calculated maximum. Offense
 * and defense are stat points, not a complete shot probability. Mobility is
 * the native movement stat, not a count of remaining AP or reachable tiles.
 */
static function PopulateFacts(XComGameStateHistory History, int HistoryIndex,
    XComGameState_Unit Subject, out array<float> Values, out array<int> Status)
{
    local float Armor;
    local bool bArmorKnown;

    bArmorKnown = ReadArmor(History, HistoryIndex, Subject, Armor);
    StoreFact(Values, Status, FactHP, Subject.GetCurrentStat(eStat_HP), true, false);
    StoreFact(Values, Status, FactMaxHP, Subject.GetMaxStat(eStat_HP), true, false);
    StoreFact(Values, Status, FactShieldHP, Subject.GetCurrentStat(eStat_ShieldHP), true, false);
    StoreFact(Values, Status, FactArmor, Armor, bArmorKnown, false);
    StoreFact(Values, Status, FactOffense, Subject.GetCurrentStat(eStat_Offense), true, true);
    StoreFact(Values, Status, FactDefense, Subject.GetCurrentStat(eStat_Defense), true, true);
    StoreFact(Values, Status, FactMobility, Subject.GetCurrentStat(eStat_Mobility), true, false);
}

/**
 * Public entry: resolve observer/subject IDs as references at one CURRENT
 * history index, authorize before reading stats and verify the same snapshot
 * afterwards. A true return means the snapshot was authorized/current; each
 * slot may still be unknown. False always returns seven unknown slots.
 * IDs only locate objects; no values are keyed by identity or template.
 * Call once per subject per decision; do not reuse across a history change.
 */
static function bool ReadUnitStats(XComGameStateHistory History, int HistoryIndex,
    int ObserverID, int SubjectID, out array<float> Values, out array<int> Status)
{
    local XComGameState_Unit Observer, Subject;

    ResetFacts(Values, Status);
    if (!IsCurrentSnapshot(History, HistoryIndex) || ObserverID <= 0 || SubjectID <= 0)
        return false;
    Observer = XComGameState_Unit(History.GetGameStateForObjectID(
        ObserverID, eReturnType_Reference, HistoryIndex));
    Subject = XComGameState_Unit(History.GetGameStateForObjectID(
        SubjectID, eReturnType_Reference, HistoryIndex));
    if (!IsAuthorizedSubject(Observer, Subject))
        return false;
    if (!IsCurrentSnapshot(History, HistoryIndex))
        return false;

    PopulateFacts(History, HistoryIndex, Subject, Values, Status);
    if (!IsCurrentSnapshot(History, HistoryIndex))
    {
        ResetFacts(Values, Status);
        return false;
    }
    return true;
}
