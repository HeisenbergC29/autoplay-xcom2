"""#122: execute installed ability reader and real shared classifiers with SDK doubles."""
import os
from pathlib import Path
from types import SimpleNamespace as NS
import unittest
from unittest.mock import Mock

from test_live_unit_stats import SOURCE, UCArray, UnitFixture, HistoryFixture, compile_reader, translate_body
from test_unit_equipment import SLOT, ItemFixture
from test_ui_gating import CHECKS, function_body


class Effect:
    """Supply actual class identity and inheritance, never an ability name."""
    def __init__(self, name, *parents):
        """Record the class and its recognized ancestors."""
        self.Class = NS(Name=name)
        self.classes = (name, *parents)

    def IsA(self, name):
        """Mock native class ancestry."""
        return name in self.classes


class Ability:
    """An installed state object with only authorized metadata."""
    def __init__(self, owner, template, source=0):
        """Record current owner, installed source and loaded template."""
        self.OwnerStateObject = NS(ObjectID=owner)
        self.SourceWeapon = NS(ObjectID=source)
        self.bRemoved = False
        self.GetMyTemplate = Mock(return_value=template)


def template(name="Test", target=(), multi=(), shooter=(), style=None,
             triggers=(), slot="Unknown"):
    """Build a loaded template fixture without readiness or action APIs."""
    return NS(DataName=name, AbilityTargetEffects=UCArray(target),
              AbilityMultiTargetEffects=UCArray(multi),
              AbilityShooterEffects=UCArray(shooter),
              AbilityMultiTargetStyle=style, AbilityTriggers=UCArray(triggers),
              DefaultSourceItemSlot=SLOT[slot])


def classifiers():
    """Execute the actual three production classification methods."""
    source = (SOURCE.parent / "APX_EnemyKnowledge.uc").read_text(encoding="utf-8-sig")
    env = dict(Capability_Control=1, Capability_Area=2, Capability_Support=4,
               X2AbilityTrigger_PlayerInput=lambda x: x if getattr(x, "player", False) else None)
    for name, argument in (("EffectCapabilities", "Effect"),
                           ("AreaStyleCapability", "Style"),
                           ("HasPlayerInputTrigger", "Template")):
        code = f"def {name}({argument}):\n" + translate_body(function_body(source, name))
        exec(compile(code, name, "exec"), env)
    return NS(**{k: env[k] for k in ("EffectCapabilities", "AreaStyleCapability",
                                      "HasPlayerInputTrigger")})


class InstalledAbilityTests(unittest.TestCase):
    """Run the public reader end to end using controlled current history."""

    def setUp(self):
        """Install only native metadata APIs, with no readiness interfaces."""
        self.own = UnitFixture(11, "Soldier")
        self.enemy = UnitFixture(21, "Enemy", 2, "Alien")
        self.other = UnitFixture(99, "Renamed", 2, "Alien")
        for unit in (self.own, self.enemy, self.other):
            unit.Abilities = UCArray()
            unit.InventoryItems = UCArray()
        self.history = HistoryFixture({11: self.own, 21: self.enemy, 99: self.other})
        self.allowed = [21, 99]
        self.classifiers = classifiers()
        env = dict(XCOMHISTORY=self.history, XWORLD=object(),
                   TACTICALRULES=NS(GetLocalClientPlayerObjectID=lambda: 1),
                   FullIntel=NS(GetKnownEnemies=self.known_enemies),
                   EnemyKnowledge=self.classifiers, eTeam_XCom="XCom",
                   X2AbilityTrigger_PlayerInput=lambda x: x if getattr(x, "player", False) else None,
                   INDEX_NONE=-1, eReturnType_Reference="reference",
                   XComGameState_Unit=lambda x: x if isinstance(x, UnitFixture) else None,
                   XComGameState_Item=lambda x: x if isinstance(x, ItemFixture) else None,
                   XComGameState_Ability=lambda x: x if isinstance(x, Ability) else None)
        env.update({"eInvSlot_" + name: slot for name, slot in SLOT.items()})
        self.uc = compile_reader(SOURCE.read_text(encoding="utf-8-sig"), env)

    def known_enemies(self, observer, output):
        """Reuse the existing visibility policy fixture."""
        output[:] = [NS(ObjectID=i) for i in self.allowed]

    def install(self, unit, object_id, loaded, source=0):
        """Insert a current installed reference; no template-added inference."""
        ability = Ability(unit.ObjectID, loaded, source)
        self.history.objects[object_id] = ability
        unit.Abilities.append(NS(ObjectID=object_id))
        return ability

    def equip(self, unit, object_id, slot="Utility"):
        """Install a native inventory reference."""
        item = ItemFixture(unit.ObjectID, slot, NS())
        self.history.objects[object_id] = item
        unit.InventoryItems.append(NS(ObjectID=object_id))
        return item

    def read(self, subject=21, observer=11, index=None, arrays=None):
        """Execute public API and verify parallel row/ledger dimensions."""
        arrays = [UCArray() for _ in range(8)] if arrays is None else arrays
        ok = self.uc["ReadUnitAbilities"](self.history,
                self.history.index if index is None else index, observer, subject, *arrays)
        ids, names, items, styles, facts, unknown_ids, scopes, classes = arrays
        width = self.uc["AbilityFactCount"]
        self.assertEqual(len(ids), len(names))
        self.assertEqual(len(ids), len(items))
        self.assertEqual(len(ids), len(styles))
        self.assertEqual(len(ids)*width, len(facts))
        self.assertEqual(len(unknown_ids), len(scopes))
        self.assertEqual(len(scopes), len(classes))
        rows = [NS(id=i, name=names[n], source=items[n], style=styles[n],
                   facts=list(facts[n*width:(n+1)*width])) for n, i in enumerate(ids)]
        return ok, rows, list(zip(unknown_ids, scopes, classes))

    def test_classifiers_recognize_subclasses_not_names(self):
        """All supported classes, unknown classes and absent trigger/style."""
        for suffix, expected in (("MindControl", 1), ("Panicked", 1), ("Stunned", 1),
                                 ("Sustained", 1), ("Marked", 4), ("SpawnPsiZombie", 4)):
            self.assertEqual(expected, self.classifiers.EffectCapabilities(
                Effect("ModSubclass", "X2Effect_" + suffix)))
        for suffix in ("Radius", "Cylinder", "Cone", "Line"):
            self.assertEqual(2, self.classifiers.AreaStyleCapability(
                Effect("CustomShape", "X2AbilityMultiTarget_" + suffix)))
        for value in (None, Effect("Unknown")):
            self.assertEqual(0, self.classifiers.EffectCapabilities(value))
            self.assertEqual(0, self.classifiers.AreaStyleCapability(value))
        self.assertTrue(self.classifiers.HasPlayerInputTrigger(template(triggers=[NS(player=True)])))
        self.assertFalse(self.classifiers.HasPlayerInputTrigger(template(triggers=[NS(player=True)]*17)))
        self.assertFalse(self.classifiers.HasPlayerInputTrigger(None))

    def test_renamed_ability_and_unknown_effect_scope(self):
        """Actual loaded classes give same facts despite different names and IDs."""
        for unit, aid, iid, name in ((self.enemy, 101, 201, "Original"),
                                    (self.other, 102, 202, "Renamed"),
                                    (self.own, 103, 203, "Own")):
            self.equip(unit, iid)
            self.install(unit, aid, template(name,
                target=[Effect("CustomControl", "X2Effect_MindControl"), Effect("Unrecognized")],
                multi=[Effect("X2Effect_Panicked")], shooter=[Effect("X2Effect_Marked")],
                style=Effect("CustomRadius", "X2AbilityMultiTarget_Radius"),
                triggers=[NS(player=True)]), iid)
            ok, rows, ledger = self.read(unit.ObjectID)
            self.assertTrue(ok)
            self.assertEqual([1, 1, 3, 4, 1, 1, 1, 1, 1], rows[0].facts)
            self.assertEqual((aid, name, iid, "CustomRadius"),
                             (rows[0].id, rows[0].name, rows[0].source, rows[0].style))
            self.assertEqual([(aid, "target", "Unrecognized")], ledger)

    def test_missing_and_unrecognized_are_distinct_from_absence(self):
        """An empty installed list differs from unresolved rows and unknown shapes."""
        self.assertEqual((True, [], []), self.read())
        self.install(self.enemy, 101, template())
        self.install(self.enemy, 102, template(style=Effect("OtherShape"),
                     multi=[None], shooter=[Effect("UnknownShooter")],
                     triggers=[NS(player=True)]*17, slot="PrimaryWeapon"))
        missing = self.install(self.enemy, 103, None)
        wrong = self.install(self.enemy, 104, template())
        wrong.OwnerStateObject.ObjectID = 99
        removed = self.install(self.enemy, 105, template())
        removed.bRemoved = True
        self.enemy.Abilities.append(NS(ObjectID=106))
        ok, rows, ledger = self.read()
        self.assertTrue(ok)
        self.assertEqual([1, 2, 0, 0, 1, 2, 2, 0, 1], rows[0].facts)
        self.assertEqual([1, 0, 0, 0, 0, 0, 0, 2, 1], rows[1].facts)
        self.assertEqual("OtherShape", rows[1].style)
        self.assertEqual([(102, "multi", ""), (102, "shooter", "UnknownShooter")], ledger)
        self.assertEqual([1]+[0]*8, rows[2].facts)
        for row in rows[3:]:
            self.assertEqual([0]*9, row.facts)
        wrong.GetMyTemplate.assert_not_called()
        removed.GetMyTemplate.assert_not_called()
        missing.GetMyTemplate.assert_called_once()

    def test_input_status_distinguishes_partial_trigger_lists(self):
        """Actual reader preserves positive proof and distinguishes unknown from absence."""
        player = NS(player=True)
        other = NS(player=False)
        cases = [
            ([], 2), ([other], 2), ([other]*16, 2),
            ([None], 0), ([None, other], 0), ([other, None], 0),
            ([None, player], 1), ([player, None], 1),
            ([other, player], 1), ([player]*17, 0), ([other]*17, 0),
            ([other]*16+[player], 0),
        ]
        for n, (triggers, expected) in enumerate(cases):
            self.install(self.enemy, 100+n, template(triggers=triggers))
        ok, rows, ledger = self.read()
        self.assertTrue(ok)
        self.assertEqual([], ledger)
        for row, (triggers, expected) in zip(rows, cases):
            with self.subTest(triggers=triggers):
                self.assertEqual(expected, row.facts[self.uc["AbilityInputStatus"]])
                self.assertEqual(1, row.facts[self.uc["AbilityTemplateStatus"]])
                # The older boolean consumer must retain its original semantics.
                self.assertEqual(expected == 1, self.classifiers.HasPlayerInputTrigger(
                    template(triggers=triggers)))

    def test_installed_source_survives_missing_template(self):
        """Validate explicit source independently, but never invent template facts."""
        item = self.equip(self.enemy, 201)
        ability = self.install(self.enemy, 101, None, 201)
        self.install(self.enemy, 102, None, 0)
        self.install(self.enemy, 103, None, 999)
        ok, rows, ledger = self.read()
        self.assertTrue(ok)
        self.assertEqual([], ledger)
        self.assertEqual((201, [1, 1]+[0]*7), (rows[0].source, rows[0].facts))
        for row in rows[1:]:
            self.assertEqual((0, [1]+[0]*8), (row.source, row.facts))
        for row in rows:
            self.assertEqual(("", ""), (row.name, row.style))
        for field, rejected in (("bRemoved", True), ("InventorySlot", SLOT["Mission"])):
            with self.subTest(field=field):
                original = getattr(item, field)
                setattr(item, field, rejected)
                self.assertEqual((0, [1]+[0]*8),
                                 (self.read()[1][0].source, self.read()[1][0].facts))
                setattr(item, field, original)
        item.OwnerStateObject.ObjectID = 99
        self.assertEqual(0, self.read()[1][0].facts[1])
        item.OwnerStateObject.ObjectID = 21
        self.enemy.InventoryItems.Length = 0
        self.assertEqual(0, self.read()[1][0].facts[1])
        self.enemy.InventoryItems.AddItem(NS(ObjectID=201))
        ability.GetMyTemplate.return_value = template()
        self.history.index += 1
        row = self.read()[1][0]
        self.assertEqual((201, [1, 1, 0, 0, 1, 2, 2, 0, 1]),
                         (row.source, row.facts))

    def test_equipment_reference_revalidated_on_current_history(self):
        """No source guessing after swap, wrong owner, removal or non-equipped slot."""
        item = self.equip(self.enemy, 201)
        ability = self.install(self.enemy, 101, template(slot="Utility"), 201)
        self.assertEqual(201, self.read()[1][0].source)
        for field, value in (("bRemoved", True), ("InventorySlot", SLOT["Mission"])):
            original = getattr(item, field)
            setattr(item, field, value)
            self.assertEqual(0, self.read()[1][0].facts[1])
            setattr(item, field, original)
        item.OwnerStateObject.ObjectID = 99
        self.assertEqual(0, self.read()[1][0].source)
        self.enemy.InventoryItems.Length = 0
        self.history.index += 1
        self.equip(self.enemy, 202, "SecondaryWeapon")
        self.assertEqual(0, self.read()[1][0].facts[1])
        ability.SourceWeapon.ObjectID = 202
        self.assertEqual(202, self.read()[1][0].source)
        ability.SourceWeapon.ObjectID = 0
        self.assertEqual(0, self.read()[1][0].facts[1])

    def test_limits_and_partial_effect_scan(self):
        """Keep recognized effects but never certify a truncated ledger or scan."""
        self.install(self.enemy, 101, template(target=[Effect("Unknown")]*33,
                     multi=[Effect("X2Effect_Stunned")]))
        ok, rows, ledger = self.read()
        self.assertTrue(ok)
        self.assertEqual((1, 0, 0), (rows[0].facts[2], rows[0].facts[4], len(ledger)))
        self.enemy.Abilities.Length = 0
        for n in range(9):
            self.install(self.enemy, 110+n, template(target=[Effect("Unknown")]*32))
        ok, rows, ledger = self.read()
        self.assertTrue(ok)
        self.assertEqual(256, len(ledger))
        self.assertEqual(1, rows[7].facts[4])
        self.assertEqual(0, rows[8].facts[4])
        self.assertEqual(32, rows[8].facts[7])
        self.enemy.Abilities.append(self.enemy.Abilities[0])
        self.assertEqual((False, [], []), self.read())
        self.enemy.Abilities = UCArray([NS(ObjectID=n) for n in range(129)])
        self.assertEqual((False, [], []), self.read())

    def test_authorization_and_snapshot_invalidation_clear_all_outputs(self):
        """Denied, stale and changing state must not leak previous results."""
        first = self.install(self.enemy, 101, template(target=[Effect("Unknown")]))
        second = self.install(self.enemy, 102, template())
        arrays = [UCArray() for _ in range(8)]
        self.assertTrue(self.read(arrays=arrays)[0])
        self.allowed = []
        first.GetMyTemplate.reset_mock()
        self.assertEqual((False, [], []), self.read(arrays=arrays))
        first.GetMyTemplate.assert_not_called()
        self.allowed = [21]
        self.assertEqual((False, [], []), self.read(index=41, arrays=arrays))
        second.GetMyTemplate.reset_mock()

        def advance():
            """Simulate a history change while retrieving native metadata."""
            self.history.index += 1
            return template()

        first.GetMyTemplate.side_effect = advance
        self.assertEqual((False, [], []), self.read(arrays=arrays))
        self.assertTrue(all(not a for a in arrays))
        second.GetMyTemplate.assert_not_called()

    def test_reader_has_no_readiness_or_mutation_calls(self):
        """Preserve the observational boundary in the actual production source."""
        source = CHECKS.without_comments(SOURCE.read_text(encoding="utf-8-sig"))
        source = source[source.index("function ResetAbilityFacts("):]
        for forbidden in ("SourceAmmo", "CanActivateAbility(", "CanAfford(", "NumActionPoints(",
                          ".Ammo", "iCooldown", "GetUnitValue(", "SubmitGameState(",
                          "ModifyStateObject(", "AdditionalAbilities", "Rand("):
            self.assertNotIn(forbidden, source)


@unittest.skipUnless(os.environ.get("APX_SDK_SOURCE_ROOT"), "Private SDK required")
class AbilitySDKContracts(unittest.TestCase):
    """Native declarations are checked separately from simulated read flow."""

    def test_installed_references_and_template_fields(self):
        """Check the exact stock types and installed source assignment."""
        root = CHECKS.find_sdk_root(Path(os.environ["APX_SDK_SOURCE_ROOT"])) / "XComGame/Classes"

        def read(name):
            """Read the private SDK source, not a copied fixture."""
            return CHECKS.without_comments((root / (name + ".uc")).read_text(encoding="utf-8-sig"))

        ability = read("XComGameState_Ability")
        for field in ("OwnerStateObject", "SourceWeapon"):
            self.assertRegex(ability, r"\bStateObjectReference\s+" + field + r"\b")
        self.assertRegex(ability, r"\bX2AbilityTemplate\s+GetMyTemplate\(")
        unit = read("XComGameState_Unit")
        for field in ("Abilities", "InventoryItems"):
            self.assertRegex(unit, r"\barray<StateObjectReference>\s+" + field + r"\b")
        native = read("X2TacticalGameRuleset")
        self.assertIn("kAbility.SourceWeapon = ItemRef;", native)
        self.assertIn("Unit.Abilities.AddItem(kAbility.GetReference());", native)
        loaded = read("X2AbilityTemplate")
        for field in ("AbilityTargetEffects", "AbilityMultiTargetEffects", "AbilityShooterEffects"):
            self.assertRegex(loaded, r"\barray<X2Effect>\s+" + field + r"\b")
        self.assertRegex(loaded, r"(?i)\bEInventorySlot\s+DefaultSourceItemSlot\b")
        self.assertRegex(loaded, r"\bX2AbilityMultiTargetStyle\s+AbilityMultiTargetStyle\b")
        self.assertRegex(read("X2DataTemplate"), r"\bname\s+DataName\b")


if __name__ == "__main__":
    unittest.main()
