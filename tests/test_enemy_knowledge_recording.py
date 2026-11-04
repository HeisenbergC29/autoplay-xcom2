"""The report exposes visible knowledge used by the new threat estimates."""
import os
from pathlib import Path
import unittest

from test_ui_gating import CHECKS, function_body


ROOT = Path(__file__).resolve().parents[1]
CLASSES = ROOT / 'AutoplayXCom2/Src/AutoplayXCom2/Classes'
SOURCE = CLASSES / 'APX_MissionRecorder.uc'


class EnemyKnowledgeRecordingTests(unittest.TestCase):
    def test_enemy_knowledge_follows_current_visibility_and_is_deduplicated(self):
        source = SOURCE.read_text()
        observe = function_body(source, 'Observe')
        visible = observe[observe.index('foreach VisibleEnemies(EnemyRef)'):]
        self.assertIn('RecordEnemyKnowledge(UnitState)', visible)
        self.assertNotIn('RecordEnemyKnowledge', observe[:observe.index('foreach VisibleEnemies(EnemyRef)')])
        record = function_body(source, 'RecordEnemyKnowledge')
        for field in ('source=visible_template', 'primary_weapon=', 'weapon_mean_damage=',
                      'aim=', 'mobility=', 'armor=', 'base_hp=', 'base_aim=', 'base_defense=',
                      'base_will=', 'base_dodge=', 'base_armor=', 'base_psi=',
                      'base_hack_defense=', 'base_detection=', 'base_crit=',
                      'threat_weight=', 'target_threat=',
                      'capabilities=', 'melee_counter_possible=', 'immune_types='):
            self.assertIn(field, record)
        self.assertLess(record.index('Units[Index].Knowledge != Fields'), record.index('Emit('))
        for forbidden in ('CanActivateAbility', 'NumActionPoints', 'GetAbilityCooldown',
                          'ApplyCost', 'ModifyStateObject', 'SubmitGameState'):
            self.assertNotIn(forbidden, record)

    def test_selected_move_trace_uses_the_same_profile_for_both_positions(self):
        trace = function_body(SOURCE.read_text(), 'RecordMoveThreatPreviews')
        self.assertIn('Weight = class\'APX_EnemyKnowledge\'.static.ThreatWeight(Enemy)', trace)
        self.assertIn('ThreatRiskAtTile(UnitState, Enemy, CurrentTile, MeleeReach, Weight)', trace)
        self.assertIn('ThreatRiskAtTile(UnitState, Enemy, DestinationTile, MeleeReach, Weight)', trace)
        self.assertIn('"|threat_weight=" $ Weight', trace)


@unittest.skipUnless(os.environ.get('APX_SDK_SOURCE_ROOT'), 'Visible template contracts need SDK')
class EnemyKnowledgeRecordingSDKContracts(unittest.TestCase):
    def test_tech_weakness_and_immunity_fields_are_native_character_metadata(self):
        sdk = CHECKS.find_sdk_root(Path(os.environ['APX_SDK_SOURCE_ROOT'])) / 'XComGame/Classes'
        character = (sdk / 'X2CharacterTemplate.uc').read_text(encoding='utf-8-sig')
        self.assertIn('native function float GetCharacterBaseStat(ECharStatType StatType) const;', character)
        for field in ('bWeakAgainstTechLikeRobot', 'bIsRobotic', 'ImmuneTypes'):
            self.assertIn(field, character)
        # Spectre demonstrates why robotic and tech-vulnerable are separate.
        defaults = (sdk / 'X2Character_DefaultCharacters.uc').read_text(encoding='utf-8-sig')
        spectre = function_body(defaults, 'CreateTemplate_SpectreM1')
        self.assertIn('bIsRobotic = false', spectre)
        self.assertIn('bWeakAgainstTechLikeRobot = true', spectre)


if __name__ == '__main__':
    unittest.main()
