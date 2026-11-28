/**
 * Read current, authorized tactical unit facts for program #120.
 * No weighting, ability readiness, targeting, game-state mutation or caching.
 * All outputs are stock scalar arrays; no cross-class custom struct dependency.
 */
class APX_UnitStats extends Object
    dependson(X2TacticalGameRulesetDataStructures);

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

/** Row status distinguishes unresolved, loaded, and verified empty slots. */
const EquipmentUnknown = 0;
const EquipmentPresent = 1;
const EquipmentAbsent = 2;

/** Stable per-row numeric fields; nominal template values, not effective unit stats. */
const EquipmentDamage = 0;
const EquipmentSpread = 1;
const EquipmentPlusOne = 2;
const EquipmentCritDamage = 3;
const EquipmentPierce = 4;
const EquipmentShred = 5;
const EquipmentRupture = 6;
const EquipmentAim = 7;
const EquipmentCritChance = 8;
const EquipmentRange = 9;
const EquipmentRadius = 10;
const EquipmentUpgradeCount = 11;
const EquipmentUpgradeAim = 12;
const EquipmentUpgradeCrit = 13;
const EquipmentUpgradeDamage = 14;
const EquipmentArmorHP = 15;
const EquipmentArmorMitigation = 16;
const EquipmentArmorDefense = 17;
const EquipmentArmorMobility = 18;
const EquipmentFactCount = 19;

/**
 * Classify a scalar independently of the unit's name or ID. Zero is known.
 * Negative offense/defense modifiers are legitimate; negative HP/shield/
 * armor/mobility are not usable. Unavailable or NaN values are unknown.
 */
private static function int FactStatus(float Value, bool bAvailable, bool bSigned)
{
    if (!bAvailable || Value != Value)
        return 0;
    if (!bSigned && Value < 0.0)
        return 0;
    return 1;
}

/** Clear both arrays on entry and on a rejected or superseded snapshot. */
private static function ResetFacts(out array<float> Values, out array<int> Status)
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
private static function StoreFact(out array<float> Values, out array<int> Status,
    int Index, float Value, bool bAvailable, bool bSigned)
{
    Status[Index] = FactStatus(Value, bAvailable, bSigned);
    Values[Index] = 0.0;
    if (Status[Index] == FactKnown)
        Values[Index] = Value;
}

/** Reject an old index, another history instance, or missing tactical services. */
private static function bool IsCurrentSnapshot(XComGameStateHistory History, int HistoryIndex)
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
private static function bool IsAuthorizedSubject(XComGameState_Unit Observer,
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
private static function float ReadArmor(XComGameStateHistory History, int HistoryIndex,
    XComGameState_Unit Subject)
{
    local StateObjectReference EffectRef;
    local XComGameState_Effect EffectState;
    local float Armor;
    if (!IsCurrentSnapshot(History, HistoryIndex) || Subject == none
        || Subject.AffectedByEffects.Length > 128)
        return -1.0;
    foreach Subject.AffectedByEffects(EffectRef)
    {
        if (EffectRef.ObjectID <= 0)
            return -1.0;
        EffectState = XComGameState_Effect(History.GetGameStateForObjectID(
            EffectRef.ObjectID, eReturnType_Reference, HistoryIndex));
        if (EffectState == none || EffectState.bRemoved || EffectState.GetX2Effect() == none)
            return -1.0;
    }
    Armor = Subject.GetArmorMitigationForUnitFlag();
    if (FactStatus(Armor, IsCurrentSnapshot(History, HistoryIndex), false) != FactKnown)
        return -1.0;
    return Armor;
}

/**
 * Populate one already authorized snapshot. Use native current values (not
 * template base stats); MaxHP uses the native calculated maximum. Offense
 * and defense are stat points, not a complete shot probability. Mobility is
 * the native movement stat, not a count of remaining AP or reachable tiles.
 */
private static function PopulateFacts(XComGameStateHistory History, int HistoryIndex,
    XComGameState_Unit Subject, out array<float> Values, out array<int> Status)
{
    local float Armor;
    // Negative is an internal armor-only failure sentinel; public output
    // always uses an independent status, including a real known zero.
    Armor = ReadArmor(History, HistoryIndex, Subject);
    if (!IsCurrentSnapshot(History, HistoryIndex))
        return;
    StoreFact(Values, Status, FactHP, Subject.GetCurrentStat(eStat_HP), true, false);
    StoreFact(Values, Status, FactMaxHP, Subject.GetMaxStat(eStat_HP), true, false);
    StoreFact(Values, Status, FactShieldHP, Subject.GetCurrentStat(eStat_ShieldHP), true, false);
    StoreFact(Values, Status, FactArmor, Armor, Armor >= 0.0, false);
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
    local XComGameState_Unit Subject;

    ResetFacts(Values, Status);
    Subject = ResolveAuthorizedSubject(History, HistoryIndex, ObserverID, SubjectID);
    if (Subject == none)
        return false;

    PopulateFacts(History, HistoryIndex, Subject, Values, Status);
    if (!IsCurrentSnapshot(History, HistoryIndex))
    {
        ResetFacts(Values, Status);
        return false;
    }
    return true;
}


/** Resolve and authorize both readers using the same current reference snapshot. */
private static function XComGameState_Unit ResolveAuthorizedSubject(
    XComGameStateHistory History, int HistoryIndex, int ObserverID, int SubjectID)
{
    local XComGameState_Unit Observer, Subject;

    if (!IsCurrentSnapshot(History, HistoryIndex) || ObserverID <= 0 || SubjectID <= 0)
        return none;
    Observer = XComGameState_Unit(History.GetGameStateForObjectID(
        ObserverID, eReturnType_Reference, HistoryIndex));
    Subject = XComGameState_Unit(History.GetGameStateForObjectID(
        SubjectID, eReturnType_Reference, HistoryIndex));
    if (!IsAuthorizedSubject(Observer, Subject) || !IsCurrentSnapshot(History, HistoryIndex))
        return none;
    return Subject;
}

/** Clear all parallel row arrays and flattened numeric arrays. */
private static function ResetEquipment(out array<int> ItemIDs, out array<EInventorySlot> Slots,
    out array<int> Presence, out array<name> Categories,
    out array<float> Values, out array<int> Status)
{
    ItemIDs.Length = 0;
    Slots.Length = 0;
    Presence.Length = 0;
    Categories.Length = 0;
    Values.Length = 0;
    Status.Length = 0;
}

/** Append one row with unknown numeric fields; return its flattened start index. */
private static function int AppendEquipmentRow(int ItemID, EInventorySlot Slot, int RowStatus,
    name Category, out array<int> ItemIDs, out array<EInventorySlot> Slots,
    out array<int> Presence, out array<name> Categories,
    out array<float> Values, out array<int> Status)
{
    local int Start;

    Start = Values.Length;
    ItemIDs.AddItem(ItemID);
    Slots.AddItem(Slot);
    Presence.AddItem(RowStatus);
    Categories.AddItem(Category);
    Values.Length = Start + EquipmentFactCount;
    Status.Length = Start + EquipmentFactCount;
    return Start;
}

/** Classify actual inventory slots: 0 unknown, 1 equipped, 2 excluded cargo. */
private static function int EquipmentSlotKind(EInventorySlot Slot)
{
    if (Slot == eInvSlot_Unknown)
        return 0;
    if (Slot == eInvSlot_Mission || Slot == eInvSlot_Backpack || Slot == eInvSlot_Loot)
        return 2;
    if (Slot == eInvSlot_Armor || Slot == eInvSlot_PrimaryWeapon
        || Slot == eInvSlot_SecondaryWeapon || Slot == eInvSlot_HeavyWeapon
        || Slot == eInvSlot_Utility || Slot == eInvSlot_GrenadePocket
        || Slot == eInvSlot_CombatSim || Slot == eInvSlot_AmmoPocket
        || Slot == eInvSlot_TertiaryWeapon || Slot == eInvSlot_QuaternaryWeapon
        || Slot == eInvSlot_QuinaryWeapon || Slot == eInvSlot_SenaryWeapon
        || Slot == eInvSlot_SeptenaryWeapon)
        return 1;
    return 0;
}

/**
 * Read names of installed upgrades, without the native item cache-populating
 * GetMyWeaponUpgradeTemplates or upgrade callbacks. Raw sums are nominal
 * metadata (BonusDamage can be miss damage), never effective shot damage.
 * An unresolved installed name leaves the entire aggregate unknown.
 */
private static function ReadUpgradeFacts(XComGameState_Item Item, int Start,
    out array<float> Values, out array<int> Status)
{
    local array<name> UpgradeNames;
    local name UpgradeName;
    local X2ItemTemplateManager Manager;
    local X2WeaponUpgradeTemplate Upgrade;
    local int Count, Aim, Crit, Damage;

    UpgradeNames = Item.GetMyWeaponUpgradeTemplateNames();
    if (UpgradeNames.Length > 32)
        return;
    Manager = class'X2ItemTemplateManager'.static.GetItemTemplateManager();
    Count = 0;
    Aim = 0;
    Crit = 0;
    Damage = 0;
    foreach UpgradeNames(UpgradeName)
    {
        if (UpgradeName == '')
            continue;
        if (Manager == none)
            return;
        Upgrade = X2WeaponUpgradeTemplate(Manager.FindItemTemplate(UpgradeName));
        if (Upgrade == none)
            return;
        Count += 1;
        Aim += Upgrade.AimBonus;
        Crit += Upgrade.CritBonus;
        Damage += Upgrade.BonusDamage.Damage;
    }
    StoreFact(Values, Status, Start + EquipmentUpgradeCount, float(Count), true, false);
    StoreFact(Values, Status, Start + EquipmentUpgradeAim, float(Aim), true, true);
    StoreFact(Values, Status, Start + EquipmentUpgradeCrit, float(Crit), true, true);
    StoreFact(Values, Status, Start + EquipmentUpgradeDamage, float(Damage), true, true);
}

/** Loaded base weapon metadata, including grenade templates; no target or roll. */
private static function ReadWeaponFacts(XComGameState_Item Item, X2WeaponTemplate Weapon,
    int Start, out array<float> Values, out array<int> Status)
{
    StoreFact(Values, Status, Start + EquipmentDamage, float(Weapon.BaseDamage.Damage), true, false);
    StoreFact(Values, Status, Start + EquipmentSpread, float(Weapon.BaseDamage.Spread), true, false);
    StoreFact(Values, Status, Start + EquipmentPlusOne, float(Weapon.BaseDamage.PlusOne),
        Weapon.BaseDamage.PlusOne >= 0 && Weapon.BaseDamage.PlusOne <= 100, false);
    StoreFact(Values, Status, Start + EquipmentCritDamage, float(Weapon.BaseDamage.Crit), true, false);
    StoreFact(Values, Status, Start + EquipmentPierce, float(Weapon.BaseDamage.Pierce), true, false);
    StoreFact(Values, Status, Start + EquipmentShred, float(Weapon.BaseDamage.Shred), true, false);
    StoreFact(Values, Status, Start + EquipmentRupture, float(Weapon.BaseDamage.Rupture), true, false);
    StoreFact(Values, Status, Start + EquipmentAim, float(Weapon.Aim), true, true);
    StoreFact(Values, Status, Start + EquipmentCritChance, float(Weapon.CritChance), true, true);
    StoreFact(Values, Status, Start + EquipmentRange, float(Weapon.iRange), Weapon.iRange >= -1, true);
    StoreFact(Values, Status, Start + EquipmentRadius, float(Weapon.iRadius), true, false);
    ReadUpgradeFacts(Item, Start, Values, Status);
}

/**
 * Sum only unconditional declared armor UI markups for one stat. Do not
 * execute display delegates or infer a missing declaration as zero.
 * These are item metadata, NOT additional effective armor or HP.
 */
private static function ReadDeclaredArmorMarkup(X2ArmorTemplate Armor, ECharStatType Stat,
    int Index, out array<float> Values, out array<int> Status)
{
    local int MarkupIndex;
    local float Total;
    local bool bFound;
    local delegate<X2StrategyGameRulesetDataStructures.SpecialRequirementsDelegate> DisplayFn;

    if (Armor.UIStatMarkups.Length > 64)
        return;
    Total = 0.0;
    bFound = false;
    for (MarkupIndex = 0; MarkupIndex < Armor.UIStatMarkups.Length; ++MarkupIndex)
    {
        if (Armor.UIStatMarkups[MarkupIndex].StatType != Stat)
            continue;
        DisplayFn = Armor.UIStatMarkups[MarkupIndex].ShouldStatDisplayFn;
        if (DisplayFn != none)
            return;
        Total += float(Armor.UIStatMarkups[MarkupIndex].StatModifier);
        bFound = true;
    }
    StoreFact(Values, Status, Index, Total, bFound, true);
}

/** Read one actual inventory reference. False means slot completeness is unknown. */
private static function bool ReadEquipmentItem(XComGameStateHistory History, int HistoryIndex,
    int SubjectID, int ItemID, out array<int> ItemIDs, out array<EInventorySlot> Slots,
    out array<int> Presence, out array<name> Categories,
    out array<float> Values, out array<int> Status)
{
    local XComGameState_Item Item;
    local X2ItemTemplate Template;
    local X2WeaponTemplate Weapon;
    local X2ArmorTemplate Armor;
    local int Kind, Start;

    Item = none;
    if (ItemID > 0)
        Item = XComGameState_Item(History.GetGameStateForObjectID(
            ItemID, eReturnType_Reference, HistoryIndex));
    if (Item == none || Item.bRemoved || Item.OwnerStateObject.ObjectID != SubjectID)
    {
        AppendEquipmentRow(ItemID, eInvSlot_Unknown, EquipmentUnknown, '',
            ItemIDs, Slots, Presence, Categories, Values, Status);
        return false;
    }
    Kind = EquipmentSlotKind(Item.InventorySlot);
    if (Kind == 2)
        return true;
    if (Kind == 0)
    {
        AppendEquipmentRow(ItemID, eInvSlot_Unknown, EquipmentUnknown, '',
            ItemIDs, Slots, Presence, Categories, Values, Status);
        return false;
    }
    Template = Item.GetMyTemplate();
    if (!IsCurrentSnapshot(History, HistoryIndex))
        return false;
    if (Template == none)
    {
        AppendEquipmentRow(ItemID, Item.InventorySlot, EquipmentUnknown, '',
            ItemIDs, Slots, Presence, Categories, Values, Status);
        return true;
    }
    Start = AppendEquipmentRow(ItemID, Item.InventorySlot, EquipmentPresent, Template.ItemCat,
        ItemIDs, Slots, Presence, Categories, Values, Status);
    Weapon = X2WeaponTemplate(Template);
    if (Weapon != none)
        ReadWeaponFacts(Item, Weapon, Start, Values, Status);
    Armor = X2ArmorTemplate(Template);
    if (Armor != none)
    {
        ReadDeclaredArmorMarkup(Armor, eStat_HP, Start + EquipmentArmorHP, Values, Status);
        ReadDeclaredArmorMarkup(Armor, eStat_ArmorMitigation, Start + EquipmentArmorMitigation, Values, Status);
        ReadDeclaredArmorMarkup(Armor, eStat_Defense, Start + EquipmentArmorDefense, Values, Status);
        ReadDeclaredArmorMarkup(Armor, eStat_Mobility, Start + EquipmentArmorMobility, Values, Status);
    }
    return true;
}

/** Emit an explicit empty core slot only after every inventory slot was resolved. */
private static function EnsureEquipmentSlot(EInventorySlot Slot, bool bComplete,
    out array<int> ItemIDs, out array<EInventorySlot> Slots, out array<int> Presence,
    out array<name> Categories, out array<float> Values, out array<int> Status)
{
    local int RowStatus;

    if (Slots.Find(Slot) != INDEX_NONE)
        return;
    RowStatus = EquipmentUnknown;
    if (bComplete)
        RowStatus = EquipmentAbsent;
    AppendEquipmentRow(0, Slot, RowStatus, '', ItemIDs, Slots, Presence, Categories, Values, Status);
}

/**
 * Read equipped item facts for the same authorized snapshot as ReadUnitStats.
 * Slots carries the native EInventorySlot enum, not cast integers.
 * Four row arrays share an index; Values/Status contain EquipmentFactCount
 * scalars per row. Unknown=0, present=1, absent=2 for Presence; numeric
 * Status retains FactKnown/FactUnknown. Identity is solely for locating items.
 * No capacity/remaining ammo, charges, readiness or ranking is read.
 * Bounds: at most 64 inventory refs plus four explicit core-slot placeholders.
 * False clears every output; true may contain unknown rows or numeric fields.
 */
static function bool ReadUnitEquipment(XComGameStateHistory History, int HistoryIndex,
    int ObserverID, int SubjectID, out array<int> ItemIDs, out array<EInventorySlot> Slots,
    out array<int> Presence, out array<name> Categories,
    out array<float> Values, out array<int> Status)
{
    local XComGameState_Unit Subject;
    local StateObjectReference ItemRef;
    local array<int> Seen;
    local bool bComplete;

    ResetEquipment(ItemIDs, Slots, Presence, Categories, Values, Status);
    Subject = ResolveAuthorizedSubject(History, HistoryIndex, ObserverID, SubjectID);
    if (Subject == none || Subject.InventoryItems.Length > 64)
        return false;
    bComplete = true;
    foreach Subject.InventoryItems(ItemRef)
    {
        if (!IsCurrentSnapshot(History, HistoryIndex))
        {
            ResetEquipment(ItemIDs, Slots, Presence, Categories, Values, Status);
            return false;
        }
        if (Seen.Find(ItemRef.ObjectID) != INDEX_NONE)
        {
            bComplete = false;
            continue;
        }
        Seen.AddItem(ItemRef.ObjectID);
        if (!ReadEquipmentItem(History, HistoryIndex, SubjectID, ItemRef.ObjectID,
            ItemIDs, Slots, Presence, Categories, Values, Status))
            bComplete = false;
    }
    if (!IsCurrentSnapshot(History, HistoryIndex))
    {
        ResetEquipment(ItemIDs, Slots, Presence, Categories, Values, Status);
        return false;
    }
    EnsureEquipmentSlot(eInvSlot_PrimaryWeapon, bComplete, ItemIDs, Slots, Presence, Categories, Values, Status);
    EnsureEquipmentSlot(eInvSlot_SecondaryWeapon, bComplete, ItemIDs, Slots, Presence, Categories, Values, Status);
    EnsureEquipmentSlot(eInvSlot_Armor, bComplete, ItemIDs, Slots, Presence, Categories, Values, Status);
    EnsureEquipmentSlot(eInvSlot_Utility, bComplete, ItemIDs, Slots, Presence, Categories, Values, Status);
    return true;
}
