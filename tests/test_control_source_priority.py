"""Source-linked enemies are valued through their known active effects.

Pure score scenarios execute the actual UnrealScript helpers. Visibility,
historical ownership and effect lifecycle remain SDK/native contracts rather
than a replay of the game.
"""
import os
from pathlib import Path
import unittest

from test_ui_gating import CHECKS, function_body
from uc_math import load_uc_function


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'AutoplayXCom2/Src/AutoplayXCom2/Classes/APX_CombatPlanner.uc'


class ControlSourcePriorityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = staticmethod(load_uc_function(SOURCE, 'ScoreDamage'))
        cls.kill = staticmethod(load_uc_function(SOURCE, 'EstimatedKillChance'))
        cls.burst = staticmethod(load_uc_function(SOURCE, 'BurstKillChance'))
        cls.benefit = staticmethod(load_uc_function(SOURCE, 'ScoreSourceBenefits'))

    def source_score(self, low, high, hp, chance, allies=0, zombies=0):
        return (self.base(low, high, hp, chance, 1, 0)
                + self.benefit(self.kill(low, high, hp, chance), allies, zombies))

    def test_reliable_source_kill_can_outweigh_easier_single_zombie_kill(self):
        source = self.source_score(3, 5, 3, 85, zombies=1)
        zombie = self.base(3, 5, 3, 95, 1, 0)
        self.assertGreater(source, zombie)

    def test_rescuing_a_known_player_unit_has_more_value_than_only_removing_zombie(self):
        rescue = self.source_score(3, 5, 3, 85, allies=1)
        remove_zombie = self.source_score(3, 5, 3, 85, zombies=1)
        ordinary = self.source_score(3, 5, 3, 85)
        self.assertGreater(rescue, remove_zombie)
        self.assertGreater(remove_zombie, ordinary)

    def test_poor_source_shot_does_not_automatically_displace_a_reliable_kill(self):
        source = self.source_score(3, 5, 3, 20, allies=1, zombies=1)
        nearby_enemy = self.base(3, 5, 3, 95, 1, 0)
        self.assertLess(source, nearby_enemy)

    def test_unkillable_or_unhittable_source_gets_no_conditional_reward(self):
        self.assertEqual(self.benefit(self.kill(3, 5, 8, 100), 1, 2), 0)
        self.assertEqual(self.benefit(self.kill(3, 5, 3, 0), 1, 2), 0)
        self.assertEqual(self.benefit(1, 0, 0), 0)
        self.assertEqual(self.benefit(1, -1, -2), 0)

    def test_bonus_is_bounded_and_tracks_actual_burst_kill_probability(self):
        self.assertLessEqual(self.benefit(1, 100, 100), 90)
        self.assertEqual(self.benefit(2, 100, 100), self.benefit(1, 100, 100))
        both_required = self.burst(6, 10, 6, 70, 2)
        self.assertAlmostEqual(both_required, 0.49)
        self.assertAlmostEqual(self.benefit(both_required, 1, 1),
                               self.benefit(1, 1, 1) * 0.49)
        self.assertLess(self.benefit(both_required, 1, 1), self.benefit(0.7, 1, 1))

    def test_source_scan_uses_visible_active_effects_and_unique_targets(self):
        source = SOURCE.read_text()
        scan = function_body(source, 'GetKnownSourceBenefits')
        self.assertIn('GetAllVisibleEnemiesForPlayer(PlayerID, VisibleEnemies)', scan)
        self.assertIn('IsVisibleHostile(SourceUnit, Enemy, VisibleEnemies)', scan)
        self.assertNotIn('IterateByClassType', scan)
        self.assertIn('Min(64, VisibleEnemies.Length)', scan)
        for gate in ('EffectState.bRemoved', 'LinkedUnit.IsAlive()',
                     'LinkedUnit.IsIncapacitated()', 'LinkedUnit.bRemovedFromPlay',
                     'SourceStateObjectRef.ObjectID != Enemy.ObjectID',
                     'TargetStateObjectRef.ObjectID != LinkedUnit.ObjectID'):
            self.assertIn(gate, scan)
        self.assertIn("Enemy.FindAbility('KillSiredZombies')", scan)
        self.assertIn("class'X2Ability_Sectoid'.default.SireZombieLinkName", scan)
        self.assertIn('X2Effect_MindControl(EffectTemplate)', scan)
        self.assertIn('EffectTemplate.bRemoveWhenSourceDies', scan)
        self.assertIn('CountedTargets.Find(TargetRef.ObjectID)', scan)
        self.assertIn('CountedTargets.AddItem(TargetRef.ObjectID)', scan)
        self.assertIn('if (bLinked)\n            ++LinkedEnemies;\n        else if (bReleased)', scan)
        self.assertNotIn('GetMyTemplateName()', scan)

    def test_historical_lookup_reads_previous_ownership_without_hidden_position_or_mutation(self):
        history = function_body(SOURCE.read_text(), 'WasControlledByPlayerBeforeEffect')
        self.assertIn('GetOriginalGameStateRevision(EffectState.ObjectID)', history)
        self.assertIn('OriginalState.HistoryIndex - 1', history)
        self.assertIn('PreviousUnit.ControllingPlayer.ObjectID == PlayerID', history)
        for forbidden in ('TileLocation', 'GetCurrentStat', 'ActionPoints',
                          'ModifyStateObject', 'CreateNewGameState', 'SubmitGameState',
                          'SetControllingPlayer', 'RemoveEffect'):
            self.assertNotIn(forbidden, history)

    def test_priority_uses_corrected_burst_probability_and_preserves_target_legality(self):
        source = SOURCE.read_text()
        score = function_body(source, 'ScoreAttack')
        self.assertIn('KillChance = EstimatedKillChance(', score)
        self.assertIn('KillChance = BurstKillChance(', score)
        self.assertLess(score.index('KillChance = BurstKillChance('),
                        score.index('GetKnownSourceBenefits('))
        self.assertIn('if (KillChance > 0.0 && Target.AdditionalTargets.Length == 0)', score)
        self.assertIn('Result += ScoreSourceBenefits(KillChance, ReleasedAllies, LinkedEnemies)', score)
        legal = function_body(source, 'IsVisibleHostile')
        self.assertIn('SourceUnit.IsEnemyUnit(TargetUnit)', legal)
        self.assertIn("VisibleEnemies.Find('ObjectID', TargetUnit.ObjectID)", legal)
        self.assertNotIn('IsMindControlled', legal)


@unittest.skipUnless(os.environ.get('APX_SDK_SOURCE_ROOT'), 'Control lifecycle requires stock SDK sources')
class ControlSourceSDKContracts(unittest.TestCase):
    def test_native_mind_control_removal_restores_ownership_and_conditionally_grants_ap(self):
        sdk = CHECKS.find_sdk_root(Path(os.environ['APX_SDK_SOURCE_ROOT'])) / 'XComGame/Classes'
        control = (sdk / 'X2Effect_MindControl.uc').read_text(encoding='utf-8-sig')
        self.assertRegex(control, r'bRemoveWhenSourceDies\s*=\s*true')
        removal = function_body(control, 'OnEffectRemoved')
        self.assertIn('GetOriginalGameStateRevision(RemovedEffectState.ObjectID)', removal)
        self.assertIn('HistoryIndex - 1', removal)
        self.assertIn('SetControllingPlayer(OriginalControllingPlayer)', removal)
        self.assertIn('UnitState.ActionPoints.Length = 0', removal)
        self.assertIn('GetCachedUnitActionPlayerRef().ObjectID == UnitState.ControllingPlayer.ObjectID', removal)
        self.assertIn('UnitState.ActionPoints.AddItem(', removal)
        self.assertLess(removal.index('UnitState.ActionPoints.Length = 0'),
                        removal.index('GetCachedUnitActionPlayerRef()'))

    def test_native_zombie_death_link_matches_actual_source_of_linked_effect(self):
        sdk = CHECKS.find_sdk_root(Path(os.environ['APX_SDK_SOURCE_ROOT'])) / 'XComGame/Classes'
        spawn = (sdk / 'X2Effect_SpawnPsiZombie.uc').read_text(encoding='utf-8-sig')
        complete = function_body(spawn, 'OnSpawnComplete')
        self.assertIn('NewEffectParams = ApplyEffectParameters', complete)
        self.assertIn('NewEffectParams.TargetStateObjectRef = ZombieGameState.GetReference()', complete)
        self.assertIn("class'X2Ability_Sectoid'.default.SireZombieLinkName", complete)
        sectoid = (sdk / 'X2Ability_Sectoid.uc').read_text(encoding='utf-8-sig')
        self.assertIn("AddKillLinkedUnits('KillSiredZombies', default.SireZombieLinkName",
                      function_body(sectoid, 'AddKillSiredZombies'))
        kill = function_body(sectoid, 'AddKillLinkedUnits')
        self.assertIn("EventID = 'UnitDied'", kill)
        self.assertIn("new class'X2Condition_UnitEffectsWithAbilitySource'", kill)
        self.assertIn('AddRequireEffect(LinkEffectName,', kill)
        self.assertIn("new class'X2Effect_KillUnit'", kill)


if __name__ == '__main__':
    unittest.main()
