"""#123: exercise actual UC equipment-reader control flow with SDK doubles.

The fixtures supply current history, loaded templates and raw installed upgrade
names. They do not simulate game action resolution or native equipment effects.
"""
import os
from pathlib import Path
from types import SimpleNamespace as NS
import unittest
from unittest.mock import Mock, call

from test_live_unit_stats import SOURCE, UCArray, UnitFixture, HistoryFixture, compile_reader
from test_ui_gating import CHECKS

SLOTS = ("Unknown", "Armor", "PrimaryWeapon", "SecondaryWeapon", "HeavyWeapon",
         "Utility", "Mission", "Backpack", "Loot", "GrenadePocket", "CombatSim",
         "AmmoPocket", "TertiaryWeapon", "QuaternaryWeapon", "QuinaryWeapon",
         "SenaryWeapon", "SeptenaryWeapon")
SLOT = {name: index for index, name in enumerate(SLOTS)}


class ItemFixture:
    """A real inventory reference's mock, with no readiness interfaces."""

    def __init__(self, owner, slot, template, upgrades=()):
        """Install only the fields read by the equipment reader."""
        self.OwnerStateObject = NS(ObjectID=owner)
        self.InventorySlot = SLOT[slot]
        self.bRemoved = False
        self.GetMyTemplate = Mock(return_value=template)
        self.GetMyWeaponUpgradeTemplateNames = Mock(return_value=UCArray(upgrades))


def weapon(damage=4, category="weapon", aim=0):
    """Provide loaded weapon facts, including actual zero and sight range."""
    return NS(kind="weapon", ItemCat=category, Aim=aim, CritChance=0,
              iRange=-1, iRadius=0,
              BaseDamage=NS(Damage=damage, Spread=1, PlusOne=25, Crit=2,
                            Pierce=0, Shred=1, Rupture=0))


def markup(stat, value, condition=None):
    """Declare one armor UI metadata row, with optional uncalled delegate."""
    return NS(StatType="eStat_" + stat, StatModifier=value, ShouldStatDisplayFn=condition)


def armor(amount=2):
    """Provide loaded armor declarations, distinct from effective unit stats."""
    return NS(kind="armor", ItemCat="armor", UIStatMarkups=UCArray([
        markup("HP", 3), markup("ArmorMitigation", amount), markup("Defense", 0)]))


def upgrade(aim=5, crit=10, damage=1):
    """Nominal upgrade fields; no effective damage callback."""
    return NS(kind="upgrade", AimBonus=aim, CritBonus=crit, BonusDamage=NS(Damage=damage))


class EquipmentTests(unittest.TestCase):
    """Cover every helper through the real public equipment snapshot flow."""

    def setUp(self):
        """Create own and hostile fixtures and compile real UC methods."""
        self.own = UnitFixture(11, "Soldier")
        self.enemy = UnitFixture(21, "Enemy", 2, "Alien")
        self.other = UnitFixture(99, "Renamed", 2, "Alien")
        for unit in (self.own, self.enemy, self.other):
            unit.InventoryItems = UCArray()
        self.history = HistoryFixture({11: self.own, 21: self.enemy, 99: self.other})
        self.allowed = [21, 99]
        self.upgrades = {"scope": upgrade()}
        self.manager = NS(FindItemTemplate=Mock(side_effect=self.upgrades.get))
        self.manager_getter = Mock(return_value=self.manager)
        env = dict(XCOMHISTORY=self.history, XWORLD=object(),
                   TACTICALRULES=NS(GetLocalClientPlayerObjectID=lambda: 1),
                   FullIntel=NS(GetKnownEnemies=self.known_enemies),
                   eTeam_XCom="XCom", INDEX_NONE=-1, eReturnType_Reference="reference",
                   XComGameState_Unit=lambda x: x if isinstance(x, UnitFixture) else None,
                   XComGameState_Item=lambda x: x if isinstance(x, ItemFixture) else None,
                   X2WeaponTemplate=lambda x: x if getattr(x, "kind", None) == "weapon" else None,
                   X2ArmorTemplate=lambda x: x if getattr(x, "kind", None) == "armor" else None,
                   X2WeaponUpgradeTemplate=lambda x: x if getattr(x, "kind", None) == "upgrade" else None,
                   ItemTemplateManager=self.manager_getter)
        env.update({"eInvSlot_" + name: slot for name, slot in SLOT.items()})
        env.update({name: name for name in (*self.own.stats, "eStat_ArmorMitigation")})
        self.uc = compile_reader(SOURCE.read_text(encoding="utf-8-sig"), env)

    def known_enemies(self, observer, output):
        """Stand in for existing full-intel/visibility policy."""
        output[:] = [NS(ObjectID=i) for i in self.allowed]

    def equip(self, unit, item_id, slot, template, upgrades=()):
        """Attach one referenced item in the fixture's current snapshot."""
        item = ItemFixture(unit.ObjectID, slot, template, upgrades)
        self.history.objects[item_id] = item
        unit.InventoryItems.append(NS(ObjectID=item_id))
        return item

    def read(self, subject=21, observer=11, index=None, history=None, outputs=None):
        """Run actual public reader and validate the shape of all parallel outputs."""
        arrays = [UCArray() for _ in range(6)] if outputs is None else outputs
        ok = self.uc["ReadUnitEquipment"](self.history if history is None else history,
                                        self.history.index if index is None else index,
                                        observer, subject, *arrays)
        ids, slots, presence, categories, values, status = arrays
        width = self.uc["EquipmentFactCount"]
        self.assertEqual(len(ids), len(slots))
        self.assertEqual(len(ids), len(presence))
        self.assertEqual(len(ids), len(categories))
        self.assertEqual(len(ids) * width, len(values))
        self.assertEqual(len(values), len(status))
        rows = [NS(id=item_id, slot=slots[i], presence=presence[i],
                   category=categories[i], values=values[i*width:(i+1)*width],
                   status=status[i*width:(i+1)*width]) for i, item_id in enumerate(ids)]
        return ok, rows

    def row(self, rows, slot):
        """Return the unique requested core-slot row in this fixture."""
        matches = [r for r in rows if r.slot == SLOT[slot]]
        self.assertEqual(1, len(matches))
        return matches[0]

    def fact(self, row, name):
        """Return the numeric value together with independent availability."""
        i = self.uc["Equipment" + name]
        return row.values[i], row.status[i]

    def test_equipment_swap_changes_same_unit_in_current_history(self):
        """E2E reader: a weapon and armor swap changes facts, not identity weights."""
        old_weapon = self.equip(self.enemy, 201, "PrimaryWeapon", weapon(4), ["scope", ""])
        self.equip(self.enemy, 202, "Armor", armor(2))
        self.equip(self.enemy, 203, "SecondaryWeapon", weapon(2))
        self.equip(self.enemy, 204, "Utility", weapon(3, "grenade"))
        self.equip(self.enemy, 205, "Utility", NS(kind="other", ItemCat="medikit"))
        self.equip(self.enemy, 206, "Mission", NS(kind="other", ItemCat="objective"))
        ok, before = self.read()
        self.assertTrue(ok)
        primary = self.row(before, "PrimaryWeapon")
        self.assertEqual((4, 1), self.fact(primary, "Damage"))
        self.assertEqual((5, 1), self.fact(primary, "UpgradeAim"))
        self.assertEqual((1, 1), self.fact(primary, "UpgradeCount"))
        self.assertEqual((-1, 1), self.fact(primary, "Range"))
        self.assertEqual((2, 1), self.fact(self.row(before, "Armor"), "ArmorMitigation"))
        self.assertEqual(2, sum(r.slot == SLOT["Utility"] for r in before))
        self.assertNotIn(206, [r.id for r in before])
        old_weapon.GetMyWeaponUpgradeTemplateNames.assert_called_once()
        self.enemy.InventoryItems[:] = [r for r in self.enemy.InventoryItems if r.ObjectID not in (201, 202)]
        self.history.index += 1
        self.equip(self.enemy, 211, "PrimaryWeapon", weapon(8, aim=12))
        self.equip(self.enemy, 212, "Armor", armor(4))
        ok, after = self.read()
        self.assertTrue(ok)
        self.assertEqual((8, 1), self.fact(self.row(after, "PrimaryWeapon"), "Damage"))
        self.assertEqual((0, 1), self.fact(self.row(after, "PrimaryWeapon"), "UpgradeCount"))
        self.assertEqual((4, 1), self.fact(self.row(after, "Armor"), "ArmorMitigation"))
        self.assertNotIn(201, [r.id for r in after])
        self.assertNotIn(202, [r.id for r in after])

    def test_same_facts_across_ids_names_and_own_enemy(self):
        """Names/IDs are locator metadata only; equal equipment yields equal facts."""
        for unit, item_id in ((self.enemy, 201), (self.other, 301), (self.own, 401)):
            self.equip(unit, item_id, "PrimaryWeapon", weapon(), ["scope"])
            self.equip(unit, item_id+1, "Armor", armor())
        profiles = []
        for subject in (21, 99, 11):
            ok, rows = self.read(subject=subject)
            self.assertTrue(ok)
            profiles.append([(r.slot, r.presence, r.category, r.values, r.status) for r in rows])
        self.assertEqual(profiles[0], profiles[1])
        self.assertEqual(profiles[0], profiles[2])

    def test_absence_unknown_template_and_missing_reference(self):
        """Empty, unresolved slot, unresolved template and zero never collapse."""
        self.equip(self.enemy, 201, "PrimaryWeapon", None)
        ok, rows = self.read()
        self.assertTrue(ok)
        self.assertEqual(0, self.row(rows, "PrimaryWeapon").presence)
        self.assertEqual(201, self.row(rows, "PrimaryWeapon").id)
        self.assertEqual(2, self.row(rows, "SecondaryWeapon").presence)
        self.enemy.InventoryItems.append(NS(ObjectID=404))
        ok, rows = self.read()
        self.assertTrue(ok)
        self.assertEqual(0, self.row(rows, "Unknown").presence)
        self.assertEqual(0, self.row(rows, "SecondaryWeapon").presence)
        self.assertEqual((0, 0), self.fact(self.row(rows, "PrimaryWeapon"), "Damage"))

    def test_actual_slot_and_incomplete_owner_removed_duplicate(self):
        """Use actual slot, not template default; invalid refs cannot certify absence."""
        gun = weapon()
        gun.InventorySlot = SLOT["PrimaryWeapon"]
        item = self.equip(self.enemy, 201, "SecondaryWeapon", gun)
        self.assertEqual(1, self.row(self.read()[1], "SecondaryWeapon").presence)
        self.assertEqual(2, self.row(self.read()[1], "PrimaryWeapon").presence)
        for owner, removed in ((11, False), (21, True)):
            item.OwnerStateObject.ObjectID = owner
            item.bRemoved = removed
            rows = self.read()[1]
            self.assertEqual(0, self.row(rows, "Unknown").presence)
            self.assertEqual(0, self.row(rows, "PrimaryWeapon").presence)
        item.OwnerStateObject.ObjectID = 21
        item.bRemoved = False
        self.enemy.InventoryItems.append(NS(ObjectID=201))
        rows = self.read()[1]
        self.assertEqual(1, self.row(rows, "SecondaryWeapon").presence)
        self.assertEqual(0, self.row(rows, "PrimaryWeapon").presence)

    def test_upgrade_aggregate_unknown_and_known_zero(self):
        """An unknown installed upgrade cannot look like no upgrades."""
        item = self.equip(self.enemy, 201, "PrimaryWeapon", weapon(4), ["scope", "missing"])
        row = self.row(self.read()[1], "PrimaryWeapon")
        self.assertEqual((4, 1), self.fact(row, "Damage"))
        for name in ("UpgradeCount", "UpgradeAim", "UpgradeCrit", "UpgradeDamage"):
            self.assertEqual((0, 0), self.fact(row, name))
        item.GetMyWeaponUpgradeTemplateNames.return_value = UCArray([""] * 2)
        row = self.row(self.read()[1], "PrimaryWeapon")
        self.assertEqual((0, 1), self.fact(row, "UpgradeCount"))
        item.GetMyWeaponUpgradeTemplateNames.return_value = UCArray(["scope"] * 33)
        self.assertEqual((0, 0), self.fact(self.row(self.read()[1], "PrimaryWeapon"), "UpgradeCount"))
        item.GetMyWeaponUpgradeTemplateNames.return_value = UCArray(["scope"])
        self.manager_getter.return_value = None
        self.assertEqual((0, 0), self.fact(self.row(self.read()[1], "PrimaryWeapon"), "UpgradeAim"))

    def test_armor_markups_are_nominal_not_effective_or_conditional(self):
        """A conditional declaration is unknown and never executes its callback."""
        declared = armor(2)
        callback = Mock(return_value=True)
        declared.UIStatMarkups.extend([markup("ArmorMitigation", 1),
                                      markup("HP", 5, callback)])
        self.equip(self.enemy, 201, "Armor", declared)
        row = self.row(self.read()[1], "Armor")
        self.assertEqual((3, 1), self.fact(row, "ArmorMitigation"))
        self.assertEqual((0, 1), self.fact(row, "ArmorDefense"))
        self.assertEqual((0, 0), self.fact(row, "ArmorHP"))
        self.assertEqual((0, 0), self.fact(row, "ArmorMobility"))
        callback.assert_not_called()
        self.enemy.GetArmorMitigationForUnitFlag.return_value = 1.0
        values, status = UCArray(), UCArray()
        self.assertTrue(self.uc["ReadUnitStats"](self.history, 42, 11, 21, values, status))
        self.assertEqual((1.0, 1), (values[3], status[3]))

    def test_snapshot_and_authorization_fail_closed(self):
        """Reject foreign/stale contexts and clear all previous arrays."""
        item = self.equip(self.enemy, 201, "PrimaryWeapon", weapon())
        for kwargs in ({"index": 41}, {"history": HistoryFixture({}, 42)},
                       {"observer": 21}, {"subject": 999}):
            arrays = [UCArray([99]) for _ in range(6)]
            self.assertEqual((False, []), self.read(outputs=arrays, **kwargs))
            self.assertTrue(all(not a for a in arrays))
        self.allowed = []
        self.assertEqual((False, []), self.read())
        item.GetMyTemplate.assert_not_called()
        self.allowed = [21]
        self.enemy.InventoryItems[:] = [NS(ObjectID=201)] * 65
        self.assertEqual((False, []), self.read())
        item.GetMyTemplate.assert_not_called()

    def test_mid_read_invalidation_never_publishes_mixed_snapshot(self):
        """A re-entrant native lookup invalidates all results and skips later items."""
        first = self.equip(self.enemy, 201, "PrimaryWeapon", weapon())
        second = self.equip(self.enemy, 202, "Armor", armor())
        def advance():
            """Simulate history advancement during a native template lookup."""
            self.history.index += 1
            return weapon()
        first.GetMyTemplate.side_effect = advance
        self.assertEqual((False, []), self.read())
        second.GetMyTemplate.assert_not_called()

    def test_slot_classifier_and_source_read_only(self):
        """Recognize stock slots explicitly and avoid readiness and cache mutation."""
        f = self.uc["EquipmentSlotKind"]
        self.assertEqual([0,1,1,1,1,1,2,2,2,1,1,1,1,1,1,1,1],
                         [f(i) for i in range(len(SLOTS))])
        self.assertEqual(0, f(255))
        source = CHECKS.without_comments(SOURCE.read_text(encoding="utf-8-sig"))
        for forbidden in ("GetAllInventoryItems(", "GetMyWeaponUpgradeTemplates(",
                          "GetUIStatMarkup(", "CanActivateAbility(", "GetAvailableActions(",
                          ".Ammo", ".Charges", "Cooldown", "SubmitGameState("):
            self.assertNotIn(forbidden, source)


# Same exact body contract as test_native_multitarget_38b; array<name> is
# not accepted by the generic function_body helper's scalar return-type regex.
UPGRADE_NAMES_GETTER = (r"function\s+array<name>\s+GetMyWeaponUpgradeTemplateNames\(\)"
                        r"\s*\{\s*return m_arrWeaponUpgradeNames;\s*\}")


class EquipmentGetterContract(unittest.TestCase):
    """Regression for the native array-returning getter signature."""

    def test_exact_array_getter_requires_uncached_names(self):
        """Accept the actual declaration, reject wrong return or a caching body."""
        source = ("function array<name> GetMyWeaponUpgradeTemplateNames()\n"
                  "{\n    // Installed names, not templates.\n"
                  "    return m_arrWeaponUpgradeNames;\n}")
        self.assertRegex(CHECKS.without_comments(source), UPGRADE_NAMES_GETTER)
        for changed in (
                source.replace("array<name>", "name"),
                source.replace("m_arrWeaponUpgradeNames;", "m_arrWeaponUpgradeTemplates;"),
                source.replace("return m_arrWeaponUpgradeNames;",
                               "UpdateCache(); return m_arrWeaponUpgradeNames;")):
            self.assertNotRegex(CHECKS.without_comments(changed), UPGRADE_NAMES_GETTER)


@unittest.skipUnless(os.environ.get("APX_SDK_SOURCE_ROOT"), "Private WOTC SDK needed")
class EquipmentSDKContracts(unittest.TestCase):
    """Check selected SDK declarations against private, unredistributed sources."""

    def test_inventory_and_upgrade_apis(self):
        """Actual inventory slot/owner, non-caching upgrade name API and loaded manager."""
        root = CHECKS.find_sdk_root(Path(os.environ["APX_SDK_SOURCE_ROOT"])) / "XComGame/Classes"
        def read(name):
            """Read the exact SDK class, never include it in the repository."""
            return (root / (name + ".uc")).read_text(encoding="utf-8-sig")
        unit, item = read("XComGameState_Unit"), read("XComGameState_Item")
        self.assertIn("protectedwrite array<StateObjectReference> InventoryItems", unit)
        self.assertIn("EInventorySlot InventorySlot", item)
        self.assertIn("OwnerStateObject", item)
        self.assertRegex(CHECKS.without_comments(item), UPGRADE_NAMES_GETTER)
        self.assertIn("FindItemTemplate(name DataName)", read("X2ItemTemplateManager"))
        equipment = read("X2EquipmentTemplate")
        self.assertIn("UIStatMarkups", equipment)
        self.assertIn("ShouldStatDisplayFn", equipment)
        self.assertIn("class X2ArmorTemplate extends X2EquipmentTemplate", read("X2ArmorTemplate"))
        self.assertIn("class X2GrenadeTemplate extends X2WeaponTemplate", read("X2GrenadeTemplate"))


if __name__ == "__main__":
    unittest.main()
