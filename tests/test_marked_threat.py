"""Public Marked penalties affect the same bounded exposure estimate everywhere.

Numeric tests execute the real UC helpers. SDK/config contracts are optional;
native hit resolution and the resulting action choices still need game testing.
"""
import os
from pathlib import Path
import re
import unittest

from test_ui_gating import CHECKS, function_body
from uc_math import load_uc_function


ROOT = Path(__file__).resolve().parents[1]
CLASSES = ROOT / 'AutoplayXCom2/Src/AutoplayXCom2/Classes'
KNOWLEDGE = CLASSES / 'APX_EnemyKnowledge.uc'
MISSION = CLASSES / 'APX_MissionPlanner.uc'
COMBAT = CLASSES / 'APX_CombatPlanner.uc'
RECORDER = CLASSES / 'APX_MissionRecorder.uc'


class MarkedThreatTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.scale = staticmethod(load_uc_function(KNOWLEDGE, 'MarkedRiskScale'))
        cls.directional = staticmethod(load_uc_function(MISSION, 'DirectionalRisk'))
        cls.melee = staticmethod(load_uc_function(MISSION, 'MeleeReachRisk'))
        cls.combined = staticmethod(load_uc_function(MISSION, 'CombinedExposure'))
        cls.aid = staticmethod(load_uc_function(COMBAT, 'ScoreAidDefense'))

    def test_missing_or_nonpositive_bonus_preserves_unmarked_risk(self):
        for bonus in (-10000, -10, 0):
            self.assertEqual(self.scale(bonus), 1)

    def test_configured_aim_bonus_is_a_bounded_planning_weight(self):
        self.assertAlmostEqual(self.scale(10), 1.1)
        self.assertEqual(self.scale(50), 1.5)
        self.assertEqual(self.scale(10000), 1.5)
        for bonus in (-10000, -10, 0, 1, 10, 50, 10000):
            self.assertGreaterEqual(self.scale(bonus), 1)
            self.assertLessEqual(self.scale(bonus), 1.5)

    def test_marked_increases_cover_and_melee_risk_without_erasing_geometry(self):
        open_risk = self.directional(0, 10, True, False)
        cover_risk = self.directional(2, 10, True, False)
        melee_risk = self.melee(10, 12)
        for risk in (open_risk, cover_risk, melee_risk):
            self.assertAlmostEqual(risk * self.scale(10), risk * 1.1)
            self.assertGreater(risk * self.scale(10), risk * self.scale(0))
        self.assertLess(cover_risk * self.scale(10), open_risk * self.scale(10))
        self.assertEqual(0 * self.scale(10), 0)

    def test_marked_target_gets_more_defensive_value_from_shared_exposure(self):
        raw = self.directional(0, 10, True, False)
        unmarked = self.combined(raw, raw, 1)
        marked = self.combined(raw * self.scale(10), raw * self.scale(10), 1)
        self.assertAlmostEqual(marked, unmarked * 1.1)
        self.assertGreater(self.aid(0.5, marked, 1), self.aid(0.5, unmarked, 1))

    def test_bonus_comes_only_from_target_public_status_and_loaded_effect_config(self):
        source = KNOWLEDGE.read_text()
        bonus = function_body(source, 'KnownMarkedAimBonus')
        self.assertIn('UnitState == none', bonus)
        self.assertIn("UnitState.IsUnitAffectedByEffectName(class'X2StatusEffects'.default.MarkedName)", bonus)
        self.assertIn("return class'X2Effect_Marked'.default.ACCURACY_CHANCE_BONUS", bonus)
        self.assertNotIn('return 10', bonus)
        self.assertNotIn('Enemy', bonus)
        self.assertNotIn('CRIT_', bonus)
        wrapper = function_body(source, 'TargetStatusWeight')
        self.assertIn('MarkedRiskScale(float(KnownMarkedAimBonus(UnitState)))', wrapper)
        for forbidden in ('GetUnitValue(', '.ActionPoints', '.Ammo', 'CanActivateAbility(',
                          'CanAfford(', 'ModifyStateObject(', 'SubmitGameState('):
            self.assertNotIn(forbidden, bonus + wrapper)

    def test_current_and_destination_risk_share_status_weight_for_both_attack_types(self):
        source = MISSION.read_text()
        threat = function_body(source, 'ThreatRiskAtTile')
        read = "TargetWeight = class'APX_EnemyKnowledge'.static.TargetStatusWeight(UnitState)"
        self.assertIn(read, threat)
        self.assertLess(threat.index('return 0.0'), threat.index(read))
        self.assertEqual(threat.count('* Weight * TargetWeight'), 2)
        self.assertLess(threat.index(read), threat.index('if (Enemy.IsMeleeOnly())'))
        # The enemy weapon snapshot remains independent of the target's status.
        self.assertNotIn('TargetStatusWeight', function_body(source, 'GetThreatWeights'))
        exposure = function_body(source, 'ExposureRisk')
        self.assertIn('ThreatRiskAtTile(UnitState, Enemy, Tile, KnownMeleeReach, KnownWeight)', exposure)
        defense = function_body(COMBAT.read_text(), 'DefensiveRisk')
        self.assertIn("class'APX_MissionPlanner'.static.ThreatRiskAtTile(", defense)
        self.assertIn('UnitState, Enemy, UnitState.TileLocation)', defense)
        preview = function_body(RECORDER.read_text(), 'RecordMoveThreatPreviews')
        for tile in ('CurrentTile', 'DestinationTile'):
            self.assertIn('ThreatRiskAtTile(UnitState, Enemy, ' + tile + ', MeleeReach, Weight)', preview)
        self.assertIn('"|marked_aim_bonus=" $ MarkedAimBonus', preview)
        self.assertIn('"|target_status_weight=" $ TargetWeight', preview)
        self.assertLess(preview.index('GetAssociatedPlayerID() != OwnerPlayerID'),
                        preview.index('KnownMarkedAimBonus(UnitState)'))


@unittest.skipUnless(os.environ.get('APX_SDK_SOURCE_ROOT'), 'Marked contracts need SDK sources')
class MarkedSDKContracts(unittest.TestCase):
    def test_native_effect_uses_public_effect_name_and_actual_accuracy_config(self):
        sdk = CHECKS.find_sdk_root(Path(os.environ['APX_SDK_SOURCE_ROOT'])) / 'XComGame/Classes'
        effect = (sdk / 'X2Effect_Marked.uc').read_text(encoding='utf-8-sig')
        self.assertIn('config(GameCore)', effect)
        self.assertIn('var config int ACCURACY_CHANCE_BONUS;', effect)
        modifier = function_body(effect, 'GetToHitAsTargetModifiers')
        self.assertIn('AccuracyInfo.Value = default.ACCURACY_CHANCE_BONUS', modifier)
        self.assertIn('ShotModifiers.AddItem(AccuracyInfo)', modifier)
        # The stock target modifier has no melee or attacker-team exception.
        self.assertNotIn('if (', modifier)
        statuses = (sdk / 'X2StatusEffects.uc').read_text(encoding='utf-8-sig')
        marked = function_body(statuses, 'CreateMarkedEffect')
        self.assertIn("PersistentEffect = new class 'X2Effect_Marked'", marked)
        self.assertIn('PersistentEffect.EffectName = default.MarkedName', marked)
        self.assertIn('SetDisplayInfo(ePerkBuff_Penalty', marked)
        unit = (sdk / 'XComGameState_Unit.uc').read_text(encoding='utf-8-sig')
        self.assertIn('IsUnitAffectedByEffectName(name EffectName) const', unit)


@unittest.skipUnless(os.environ.get('APX_GAME_CONFIG_ROOT'), 'Marked evidence needs provided game config')
class MarkedGameConfigContracts(unittest.TestCase):
    def test_provided_game_config_has_accuracy_penalty_without_assumed_crit_bonus(self):
        config_root = Path(os.environ['APX_GAME_CONFIG_ROOT'])
        data = (config_root / 'DefaultGameCore.ini').read_bytes()
        encoding = 'utf-16' if data[:2] in (b'\xff\xfe', b'\xfe\xff') else 'utf-8-sig'
        text = data.decode(encoding)
        section = re.search(r'^\[XComGame\.X2Effect_Marked\]\s*$(.*?)(?=^\[|\Z)',
                            text, flags=re.M | re.S)
        self.assertIsNotNone(section)
        values = dict(re.findall(r'^(\w+)\s*=\s*(-?\d+)\s*$', section[1], re.M))
        self.assertEqual(int(values['ACCURACY_CHANCE_BONUS']), 10)
        self.assertEqual(int(values['CRIT_CHANCE_BONUS']), 0)
        self.assertEqual(int(values['CRIT_DAMAGE_BONUS']), 0)


if __name__ == '__main__':
    unittest.main()
