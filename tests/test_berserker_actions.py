"""Stock Berserker player-input melee is supported by the existing melee planner.

Source checks only; SDK is optional and the game remains the runtime oracle.
"""
import os
from pathlib import Path
import unittest

from test_ui_gating import CHECKS, function_body

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / 'AutoplayXCom2/Config/XComAutoplayXCom2.ini'
COMBAT = ROOT / 'AutoplayXCom2/Src/AutoplayXCom2/Classes/APX_CombatPlanner.uc'


class BerserkerMeleeTests(unittest.TestCase):
    def test_supported_player_input_attacks_are_in_the_config(self):
        lines = CONFIG.read_text(encoding='utf-8-sig').splitlines()
        attacks = [line.split('=', 1)[1].strip() for line in lines
                   if line.startswith('+AttackAbilities=')]
        for name in ('DevastatingPunch', 'DevastatingPunchMP'):
            with self.subTest(ability=name):
                self.assertEqual(attacks.count(name), 1)

    def test_stock_melee_path_and_visibility_guards_apply_to_berserkers(self):
        source = COMBAT.read_text(encoding='utf-8-sig')
        chooser = function_body(source, 'ChooseAction')
        for required in ('default.AttackAbilities.Find(AbilityName)',
                         'IsVisibleHostile(', 'AdditionalTargetsAreSafe(',
                         'HasRequiredMeleePath(', 'ScoreAttack('):
            self.assertIn(required, chooser)
        path = function_body(source, 'HasRequiredMeleePath')
        for required in ('X2AbilityTarget_MovingMelee',
                         'SelectAttackTile(', 'BuildPathToTile(',
                         'IsSupportedCombatDestination(', 'IsSupportedAdvanceStep(',
                         'CanSquadSeeLocation(', 'ExposureRisk('):
            self.assertIn(required, path)


@unittest.skipUnless(os.environ.get('APX_SDK_SOURCE_ROOT'),
                     'SDK source needed to validate the stock Berserker abilities')
class BerserkerSDKContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sdk = CHECKS.find_sdk_root(Path(os.environ['APX_SDK_SOURCE_ROOT'])) / 'XComGame/Classes'
        cls.source = (cls.sdk / 'X2Ability_Berserker.uc').read_text(encoding='utf-8-sig')

    def test_both_attacks_use_standard_melee_and_native_target_path(self):
        for function in ('CreateDevastatingPunchAbility', 'CreateDevastatingPunchAbilityMP'):
            with self.subTest(function=function):
                body = function_body(self.source, function)
                for required in ('X2AbilityToHitCalc_StandardMelee',
                                 'X2AbilityTarget_MovingMelee',
                                 "class'X2TargetingMethod_MeleePath'",
                                 'X2AbilityTrigger_PlayerInput',
                                 'X2AbilityCost_ActionPoints',
                                 'eHostility_Offensive'):
                    self.assertIn(required, body)

    def test_mp_berserker_character_equips_the_mp_attack(self):
        source = (self.sdk / 'X2Character_DefaultMPCharacters.uc').read_text(encoding='utf-8-sig')
        self.assertIn("CharTemplate.Abilities.AddItem('DevastatingPunchMP')", source)


if __name__ == '__main__':
    unittest.main()
