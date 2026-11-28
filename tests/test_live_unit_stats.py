"""#125: exercise the actual UC read flow against controlled SDK test doubles.

The tiny adapter supports only statements used in APX_UnitStats, not general
UnrealScript. All control flow, authorization, field mapping and status logic
come from production source. Native history, visibility and stat values are
fixtures; neither this test nor the private SDK checks execute the game.
"""
import os
from pathlib import Path
import re
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

from test_ui_gating import CHECKS, function_body

ROOT = Path(__file__).resolve().parents[1]
CLASSES = ROOT / "AutoplayXCom2/Src/AutoplayXCom2/Classes"
SOURCE = CLASSES / "APX_UnitStats.uc"


class UCArray(list):
    """Provide only the stock dynamic-array operations used by this reader."""

    @property
    def Length(self):
        """Return the number of entries."""
        return len(self)

    @Length.setter
    def Length(self, length):
        """Resize while preserving existing entries; zero-initialize new ones."""
        del self[length:]
        self.extend([0] * (length - len(self)))

    def AddItem(self, value):
        """Append a scalar or reference, like the stock dynamic array."""
        self.append(value)

    def Find(self, field, value=None):
        """Return the matching scalar or struct-field index, or INDEX_NONE."""
        if value is None:
            return next((i for i, item in enumerate(self) if item == field), -1)
        return next((i for i, item in enumerate(self)
                     if getattr(item, field) == value), -1)


def expression(source):
    """Translate the limited expression syntax, preserving actual operators."""
    source = " ".join(source.split()).replace(chr(96), "")
    source = source.replace("class'APX_FullIntel'.static.", "FullIntel.")
    source = source.replace("class'APX_EnemyKnowledge'.static.", "EnemyKnowledge.")
    source = source.replace("class'X2ItemTemplateManager'.static.GetItemTemplateManager()",
                            "ItemTemplateManager()")
    for uc, python in (("none", "None"), ("true", "True"), ("false", "False")):
        source = re.sub(r"\b" + uc + r"\b", python, source, flags=re.I)
    return re.sub(r"!(?!=)", "not ", source.replace("&&", " and ").replace("||", " or "))


def split_condition(token):
    """Return a balanced if condition and its optional inline statement."""
    start = token.index("(")
    depth = 1
    for end in range(start + 1, len(token)):
        depth += (token[end] == "(") - (token[end] == ")")
        if depth == 0:
            return token[start + 1:end], token[end + 1:].strip()
    raise AssertionError("Unbalanced condition: " + token)


def translate_body(body):
    """Translate this class's statements; unfamiliar syntax fails compilation."""
    body = body.replace("for (Index = 0; Index < FactCount; ++Index)",
                        "for Index in range(FactCount)")
    body = body.replace("for (MarkupIndex = 0; MarkupIndex < Armor.UIStatMarkups.Length; ++MarkupIndex)",
                        "for MarkupIndex in range(Armor.UIStatMarkups.Length)")
    tokens = [s.strip() for s in re.split(r"([{};])", body)
              if s.strip() and s != ";"]
    lines = []
    indent = 1
    pending_block = False
    for token in tokens:
        if token == "{":
            if not pending_block:
                raise AssertionError("Unexpected block")
            pending_block = False
            indent += 1
            continue
        if pending_block:
            raise AssertionError("Missing block: " + token)
        if token == "}":
            indent -= 1
            continue
        prefix = "    " * indent
        if token.startswith("local "):
            if token.startswith("local array<"):
                lines.append(prefix + token.split()[-1] + " = UCArray()")
        elif token.startswith("if "):
            condition, inline = split_condition(token)
            lines.append(prefix + "if " + expression(condition) + ":")
            if inline:
                lines.append(prefix + "    " + expression(inline))
            else:
                pending_block = True
        elif token.startswith("foreach "):
            match = re.fullmatch(r"foreach\s+([\w.]+)\((\w+)\)", token)
            if not match:
                raise AssertionError("Unsupported foreach: " + token)
            lines.append(prefix + f"for {match[2]} in {match[1]}:")
            pending_block = True
        elif token.startswith("for "):
            lines.append(prefix + token + ":")
            pending_block = True
        else:
            lines.append(prefix + expression(token))
    if indent != 1 or pending_block:
        raise AssertionError("Incomplete source block")
    return "\n".join(lines)


def compile_reader(source, environment):
    """Compile the real methods into a sandbox of explicit test-double APIs."""
    clean = CHECKS.without_comments(source)
    namespace = dict(environment, UCArray=UCArray)
    for name, value in re.findall(r"\bconst\s+(\w+)\s*=\s*(\d+)\s*;", clean):
        namespace[name] = int(value)
    definitions = re.findall(r"\bfunction\s+(?:\w+\s+)?(\w+)\s*\(([^)]*)\)\s*\{",
                             clean, flags=re.S)
    for name, params in definitions:
        arguments = ", ".join(part.strip().split()[-1] for part in params.split(","))
        code = f"def {name}({arguments}):\n" + translate_body(function_body(clean, name))
        exec(compile(code, f"{SOURCE.name}:{name}", "exec"), namespace)
    return namespace


class UnitFixture:
    """A controlled stock-unit test double with independently supplied native facts."""

    def __init__(self, object_id, template_name, owner=1, team="XCom"):
        """Install the native API responses; no scoring or unit-name mapping."""
        self.ObjectID = object_id
        self.bRemoved = self.bRemovedFromPlay = False
        self.AffectedByEffects = UCArray()
        self.stats = {"eStat_HP": 8.0, "eStat_ShieldHP": 0.0,
                      "eStat_Offense": 75.0, "eStat_Defense": -5.0,
                      "eStat_Mobility": 12.0, "eStat_ArmorMitigation": 99.0}
        self.GetMyTemplate = Mock(return_value=SimpleNamespace(
            name=template_name, bIsCosmetic=False))
        self.GetAssociatedPlayerID = Mock(return_value=owner)
        self.GetTeam = Mock(return_value=team)
        self.IsCivilian = Mock(return_value=False)
        self.IsAlive = Mock(return_value=True)
        self.IsIncapacitated = Mock(return_value=False)
        self.IsEnemyUnit = Mock(side_effect=lambda other: team != other.GetTeam())
        self.GetCurrentStat = Mock(side_effect=self.stats.__getitem__)
        self.GetMaxStat = Mock(return_value=10.0)
        self.GetArmorMitigationForUnitFlag = Mock(return_value=3.0)


class EffectFixture:
    """A resolved effect reference; native armor remains an opaque response."""

    def __init__(self, removed=False, template=True):
        """Configure whether the effect is complete in the current snapshot."""
        self.bRemoved = removed
        self.GetX2Effect = Mock(return_value=object() if template else None)


class HistoryFixture:
    """Explicit history identity/index and reference lookup, not a game simulator."""

    def __init__(self, objects, index=42):
        """Record all object resolutions for same-snapshot assertions."""
        self.objects = objects
        self.index = index
        self.GetCurrentHistoryIndex = Mock(side_effect=lambda: self.index)
        self.GetGameStateForObjectID = Mock(side_effect=self.lookup)

    def lookup(self, object_id, return_type, history_index):
        """Reject a wrong lookup mode/index and return the configured object."""
        if return_type != "reference" or history_index != self.index:
            raise AssertionError("Lookup outside the current fixture snapshot")
        return self.objects.get(object_id)


class LiveUnitStatsTests(unittest.TestCase):
    """Execute every production method through the real public reader flow."""

    def setUp(self):
        """Configure native SDK stubs and compile the actual UC functions."""
        self.source = SOURCE.read_text(encoding="utf-8-sig")
        self.own = UnitFixture(11, "Soldier")
        self.enemy = UnitFixture(21, "Viper", 2, "Alien")
        self.renamed = UnitFixture(99, "OtherModTemplate", 2, "Alien")
        self.effect = EffectFixture()
        self.history = HistoryFixture({11: self.own, 21: self.enemy,
                                       99: self.renamed, 44: self.effect})
        self.permitted = [21, 99]
        self.intel = Mock(side_effect=self.known_enemies)
        self.rules = SimpleNamespace(GetLocalClientPlayerObjectID=Mock(return_value=1))
        environment = dict(
            XCOMHISTORY=self.history, TACTICALRULES=self.rules, XWORLD=object(),
            eTeam_XCom="XCom", INDEX_NONE=-1, eReturnType_Reference="reference",
            FullIntel=SimpleNamespace(GetKnownEnemies=self.intel),
            XComGameState_Unit=lambda obj: obj if isinstance(obj, UnitFixture) else None,
            XComGameState_Effect=lambda obj: obj if isinstance(obj, EffectFixture) else None,
        )
        environment.update({name: name for name in self.own.stats})
        self.uc = compile_reader(self.source, environment)

    def known_enemies(self, observer, output):
        """Stand in for the existing policy; visibility mode is not reimplemented."""
        output[:] = [SimpleNamespace(ObjectID=i) for i in self.permitted]

    def read(self, subject=21, observer=11, history=None, index=None, values=None, status=None):
        """Call the translated public entry, retaining output-array identity."""
        if history is None:
            history = self.history
        if index is None:
            index = self.history.index
        values = UCArray() if values is None else values
        status = UCArray() if status is None else status
        ok = self.uc["ReadUnitStats"](history, index, observer, subject, values, status)
        return ok, list(values), list(status)

    def test_numeric_status_distinguishes_zero_signed_and_unknown(self):
        """The production scalar classifier never treats a known zero as absent."""
        classify = self.uc["FactStatus"]
        for value, available, signed, expected in (
                (0.0, True, False, 1), (0.0, False, False, 0),
                (-1.0, True, False, 0), (-5.0, True, True, 1),
                (float("nan"), True, True, 0), (12.5, True, False, 1)):
            with self.subTest(value=value, available=available, signed=signed):
                self.assertEqual(expected, classify(value, available, signed))

    def test_full_reader_same_stats_regardless_of_identity(self):
        """Different template names and IDs yield identical facts, including own units."""
        expected = (True, [8, 10, 0, 3, 75, -5, 12], [1] * 7)
        self.assertEqual(expected, self.read(subject=21))
        self.assertEqual(expected, self.read(subject=99))
        self.assertEqual(expected, self.read(subject=11))
        self.assertEqual(2, self.intel.call_count)
        self.assertEqual(7, self.uc["FactCount"])

    def test_current_stats_and_armor_change_with_same_unit_and_new_frame(self):
        """Read the native effective armor, not base 99 or a stale cached value."""
        self.enemy.AffectedByEffects.append(SimpleNamespace(ObjectID=44))
        self.assertEqual(3.0, self.read()[1][3])
        self.history.index += 1
        self.enemy.GetArmorMitigationForUnitFlag.return_value = 1.0
        self.enemy.stats.update(eStat_HP=4, eStat_Offense=55, eStat_Mobility=7)
        self.enemy.GetMaxStat.return_value = 9.0
        self.assertEqual((True, [4, 9, 0, 1, 55, -5, 7], [1] * 7), self.read())
        self.history.index += 1
        self.enemy.GetArmorMitigationForUnitFlag.return_value = 0.0
        self.assertEqual((0.0, 1), (self.read()[1][3], self.read()[2][3]))
        self.assertNotIn(unittest.mock.call("eStat_ArmorMitigation"),
                         self.enemy.GetCurrentStat.call_args_list)

    def test_missing_effect_does_not_turn_unknown_armor_into_known_zero(self):
        """Incomplete effect evidence invalidates only armor, before native getter."""
        self.enemy.AffectedByEffects.append(SimpleNamespace(ObjectID=404))
        ok, values, status = self.read()
        self.assertTrue(ok)
        self.assertEqual(0.0, values[3])
        self.assertEqual([1, 1, 1, 0, 1, 1, 1], status)
        self.enemy.GetArmorMitigationForUnitFlag.assert_not_called()
        for invalid in (EffectFixture(removed=True), EffectFixture(template=False)):
            self.history.objects[404] = invalid
            self.assertEqual(0, self.read()[2][3])

    def test_armor_budget_and_invalid_native_values_are_explicit_unknown(self):
        """Excess effect references, negative armor and unavailable fields stay unknown."""
        self.enemy.AffectedByEffects[:] = [SimpleNamespace(ObjectID=44)] * 129
        self.assertEqual(0, self.read()[2][3])
        self.enemy.GetArmorMitigationForUnitFlag.assert_not_called()
        self.enemy.AffectedByEffects.clear()
        self.enemy.GetArmorMitigationForUnitFlag.return_value = -2.0
        self.enemy.stats["eStat_ShieldHP"] = -1.0
        self.assertEqual([1, 1, 0, 0, 1, 1, 1], self.read()[2])
        self.enemy.stats["eStat_ShieldHP"] = 0.0
        self.enemy.GetArmorMitigationForUnitFlag.return_value = 0.0
        self.assertEqual([1] * 7, self.read()[2])

    def test_unavailable_or_outdated_snapshot_clears_previous_result(self):
        """Even a matching numeric index from a different history is rejected."""
        values, status = UCArray([77] * 9), UCArray([1] * 9)
        unknown = (False, [0] * 7, [0] * 7)
        self.assertEqual(unknown, self.read(index=41, values=values, status=status))
        self.assertEqual([0] * 7, values)
        self.assertEqual([0] * 7, status)
        self.assertEqual(unknown, self.read(history=HistoryFixture({}, 42)))
        self.assertEqual(unknown, self.read(subject=555))
        self.assertEqual(unknown, self.read(subject=0))
        self.uc["XWORLD"] = None
        self.assertEqual(unknown, self.read())
        self.enemy.GetCurrentStat.assert_not_called()

    def test_visibility_and_ownership_precede_any_stat_read(self):
        """Nonlocal observer, hidden unauthorized target or cosmetic never yields stats."""
        unknown = (False, [0] * 7, [0] * 7)
        self.permitted = []
        self.assertEqual(unknown, self.read())
        self.assertEqual(unknown, self.read(observer=21, subject=99))
        self.permitted = [21]
        self.own.GetAssociatedPlayerID.return_value = 3
        self.assertEqual(unknown, self.read())
        self.own.GetAssociatedPlayerID.return_value = 1
        self.enemy.GetMyTemplate.return_value.bIsCosmetic = True
        self.assertEqual(unknown, self.read())
        self.enemy.GetMyTemplate.return_value = None
        self.assertEqual(unknown, self.read())
        self.enemy.GetCurrentStat.assert_not_called()
        self.enemy.GetArmorMitigationForUnitFlag.assert_not_called()

    def test_same_history_index_for_unit_and_effect_lookups(self):
        """No copied, future or historical snapshot is used in the read."""
        self.enemy.AffectedByEffects.append(SimpleNamespace(ObjectID=44))
        self.assertTrue(self.read()[0])
        self.assertEqual([unittest.mock.call(i, "reference", 42) for i in (11, 21, 44)],
                         self.history.GetGameStateForObjectID.call_args_list)

    def test_history_change_mid_read_discards_entire_snapshot(self):
        """A re-entrant or superseded read must not publish mixed-frame values."""
        def advance(stat):
            """Simulate a native service invalidating the snapshot during a read."""
            self.history.index += 1
            return self.enemy.stats[stat]

        self.enemy.GetCurrentStat.side_effect = advance
        self.assertEqual((False, [0] * 7, [0] * 7), self.read())

    def test_armor_read_invalidating_snapshot_does_not_read_other_stats(self):
        """Do not publish or continue another stat read after the native armor callback."""
        def invalidated_armor():
            """Simulate a re-entrant mod effect changing the history index."""
            self.history.index += 1
            return 3.0

        self.enemy.GetArmorMitigationForUnitFlag.side_effect = invalidated_armor
        self.assertEqual((False, [0] * 7, [0] * 7), self.read())
        self.enemy.GetCurrentStat.assert_not_called()

    def test_reader_has_no_ranking_or_dispatch(self):
        """This class must remain observational even after future consumers arrive."""
        for forbidden in ("GetAvailableActions(", "CanActivateAbility(", "NumActionPoints(",
                          ".Ammo", "Cooldown", "Charges", "GetMyTemplateName(",
                          "GetBaseStat(", "ModifyStateObject(", "SubmitGameState(",
                          "RollArmorMitigation(", "GetArmorMitigation("):
            self.assertNotIn(forbidden, CHECKS.without_comments(self.source))
        self.assertIn("private static function float ReadArmor(", self.source)
        self.assertIn("private static function PopulateFacts(", self.source)


@unittest.skipUnless(os.environ.get("APX_SDK_SOURCE_ROOT"), "Private WOTC SDK needed")
class LiveUnitStatsSDKContracts(unittest.TestCase):
    """Confirm real SDK declarations and armor semantics without redistributing SDK."""

    @classmethod
    def setUpClass(cls):
        """Resolve the same stock SDK root used by the repository audit."""
        cls.sdk = CHECKS.find_sdk_root(Path(os.environ["APX_SDK_SOURCE_ROOT"])) / "XComGame/Classes"
        cls.unit = (cls.sdk / "XComGameState_Unit.uc").read_text(encoding="utf-8-sig")

    def test_stock_stat_api_and_unit_flag_match_the_selected_read(self):
        """Native current values and calculated max are the SDK UI's basis."""
        self.assertRegex(self.unit, r"native function float GetCurrentStat\(\s*ECharStatType Stat\s*\) const")
        self.assertRegex(self.unit, r"native function float GetMaxStat\(\s*ECharStatType Stat\s*\)")
        summary = function_body(self.unit, "GetUISummary_UnitStats")
        for stat in ("eStat_HP", "eStat_Offense", "eStat_Defense", "eStat_Mobility"):
            self.assertIn(f"GetCurrentStat({stat})", summary)
        flag = (self.sdk / "UIUnitFlag.uc").read_text(encoding="utf-8-sig")
        self.assertIn("SetShieldPoints(NewUnitState.GetCurrentStat(eStat_ShieldHP)", flag)
        self.assertIn("SetArmorPoints(NewUnitState.GetArmorMitigationForUnitFlag())", flag)

    def test_stock_armor_includes_bonus_effects_and_subtracts_shred(self):
        """Native UI armor is the same stock current+bonus-shred total used here."""
        armor = function_body(self.unit, "GetArmorMitigationForUnitFlag")
        for token in ("GetCurrentStat(eStat_ArmorMitigation)", "X2Effect_BonusArmor(",
                      "ArmorEffect.GetArmorMitigation(EffectState, self)", "Total -= Shredded",
                      "max(0, Total)"):
            self.assertIn(token, armor)
        self.assertNotIn("RollArmorMitigation(", armor)
        self.assertNotIn("SYNC_RAND", armor)
        self.assertLess(armor.index("ArmorEffect.GetArmorMitigation("), armor.index("Total -= Shredded"))

    def test_mobility_and_defense_are_native_stats_not_reach_or_hit_probability(self):
        """Source consumers distinguish movement/aim stats from action-specific legality."""
        movement = (self.sdk / "XGUnit.uc").read_text(encoding="utf-8-sig")
        aim = (self.sdk / "X2AbilityToHitCalc_StandardAim.uc").read_text(encoding="utf-8-sig")
        self.assertIn("GetCurrentStat(eStat_Mobility)", function_body(movement, "GetMaxPathDistance"))
        self.assertIn("TargetState.GetCurrentStat(eStat_Defense)", aim)
        self.assertIn("UnitState.GetStatModifiers(eStat_Offense", aim)
        history = (self.sdk / "XComGameStateHistory.uc").read_text(encoding="utf-8-sig")
        self.assertIn("optional int HistoryIndex=-1", history)
        self.assertIn("optional EGameStateReturnType DesiredReturnType=eReturnType_Reference", history)


if __name__ == "__main__":
    unittest.main()
