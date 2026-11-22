"""Exercise the combat Overwatch target predicate, ranking and matching SDK contracts."""

import os
from pathlib import Path
import unittest
from unittest.mock import Mock

from test_ui_gating import CHECKS, function_body
from uc_math import load_uc_function


CLASSES = Path(__file__).resolve().parents[1] / 'AutoplayXCom2/Src/AutoplayXCom2/Classes'
COMBAT = CLASSES / 'APX_CombatPlanner.uc'


class CombatReactionTargetTests(unittest.TestCase):
    """Follow a stock arming action from a validated owner to its reaction score."""

    def test_resolve_own_granted_reaction_for_the_selected_weapon(self):
        """Pistol, long watch and ordinary rifle use their actual same-weapon shot."""
        resolver = function_body(COMBAT.read_text(), 'ResolveStockReactionShot')
        self.assertRegex(resolver, r"case 'Overwatch':\s*case 'SniperRifleOverwatch':\s*ShotName = 'OverwatchShot';")
        for ability in ('PistolOverwatch', 'LongWatch'):
            self.assertRegex(resolver, rf"case '{ability}':\s*ShotName = '{ability}Shot';")
        self.assertRegex(resolver, r'default:\s*return none;')
        for gate in ('ArmAbility.OwnerStateObject.ObjectID != Soldier.ObjectID',
                     'ArmAbility.SourceWeapon.ObjectID <= 0',
                     'Soldier.FindAbility(ShotName, ArmAbility.SourceWeapon)',
                     'Shot.OwnerStateObject.ObjectID != Soldier.ObjectID'):
            self.assertIn(gate, resolver)

    def test_native_range_and_visibility_drive_ranking_before_arming(self):
        """Run the UC predicate and ranking with controlled native target replies."""
        qualifies = load_uc_function(COMBAT, 'IsCurrentReactionTarget')
        score = load_uc_function(COMBAT, 'ScoreOverwatchDefense')
        guard = load_uc_function(COMBAT, 'GuardOverwatchForKnownAlly')
        shot, soldier, enemy = object(), object(), object()
        for in_range, target_result, expected in (
            (False, 'AA_Success', 5), (True, 'AA_NotVisible', 5),
            (True, 'AA_UnitIsImmune', 5), (True, 'AA_Success', 17),
        ):
            with self.subTest(in_range=in_range, target=target_result):
                template = Mock()
                validate = template.AbilityTargetStyle.ValidatePrimaryTargetOption
                validate.return_value = in_range
                template.CheckTargetConditions.return_value = target_result
                lane = qualifies(template, shot, soldier, enemy)
                reserve = score(lane, False, 1.0, 0.0, 0, True)
                self.assertEqual(expected, guard(reserve, False))
                self.assertLess(guard(reserve, True), -1000)
                validate.assert_called_once_with(shot, soldier, enemy)
                if in_range:
                    template.CheckTargetConditions.assert_called_once_with(shot, soldier, enemy)
                else:
                    template.CheckTargetConditions.assert_not_called()

    def test_combat_entry_uses_current_known_targets_and_never_activates_a_reaction(self):
        """Inspect entry-point wiring and bound the native calls before ranking."""
        combat = COMBAT.read_text()
        chooser = function_body(combat, 'ChooseAction')
        self.assertIn('GetAllVisibleEnemiesForPlayer(', chooser)
        self.assertIn("Candidate.AvailableCode != 'AA_Success'", chooser)
        self.assertIn('ScoreSelfAction(UnitState, Ability, AbilityName, VisibleEnemies,', chooser)
        lane = function_body(combat, 'HasPlausibleLocalReactionLane')
        requirements = ('SquadVisibleEnemies.Length == 0 || SquadVisibleEnemies.Length > 64',
                        'ResolveStockReactionShot(Soldier, ArmAbility)', 'if (Shot == none)',
                        "Template.AbilityTargetStyle.Class != class'X2AbilityTarget_Single'",
                        'foreach SquadVisibleEnemies(Ref)', 'IsVisibleHostile(Soldier, Enemy,',
                        'IsCurrentReactionTarget(Template, Shot, Soldier, Enemy)')
        offsets = [lane.index(requirement) for requirement in requirements]
        self.assertEqual(offsets, sorted(offsets))
        inspection = lane + function_body(combat, 'IsCurrentReactionTarget')
        for forbidden in ('CanActivateAbility', 'AbilityTrigger', 'SubmitGameState',
                          'GetNextDestination', 'ActionPoints', 'CanSeeTileToTile'):
            self.assertNotIn(forbidden, inspection)


@unittest.skipUnless(os.environ.get('APX_SDK_SOURCE_ROOT'), 'Requires stock WOTC SDK sources')
class StockReactionContracts(unittest.TestCase):
    """Check the exact stock conditions that the combat forecast may invoke."""

    def test_native_weapons_grant_the_matched_shot_and_long_watch_replaces_it(self):
        """Each supported arming action resolves the reaction the stock weapon grants."""
        sdk = CHECKS.find_sdk_root(Path(os.environ['APX_SDK_SOURCE_ROOT'])) / 'XComGame/Classes'
        weapons = (sdk / 'X2Item_DefaultWeapons.uc').read_text(encoding='cp1252')
        for weapon, arm, shot in (('AssaultRifle', 'Overwatch', 'OverwatchShot'),
                                  ('Pistol', 'PistolOverwatch', 'PistolOverwatchShot'),
                                  ('SniperRifle', 'SniperRifleOverwatch', 'OverwatchShot')):
            with self.subTest(weapon=weapon):
                grants = function_body(weapons, f'CreateTemplate_{weapon}_Conventional')
                for ability in (arm, shot):
                    self.assertIn(f"Template.Abilities.AddItem('{ability}')", grants)
        sniper = (sdk / 'X2Ability_SharpshooterAbilitySet.uc').read_text(encoding='utf-8-sig')
        long_watch = function_body(sniper, 'LongWatch')
        self.assertIn("Template.OverrideAbilities.AddItem('SniperRifleOverwatch')", long_watch)
        self.assertIn("Template.AdditionalAbilities.AddItem('LongWatchShot')", long_watch)
        self.assertIn("Template.OverrideAbilities.AddItem('OverwatchShot')",
                      function_body(sniper, 'LongWatchShot'))

    def test_stock_trigger_range_target_filters_and_long_watch_exception(self):
        """The stock event revalidates range and target conditions when enemies move."""
        sdk = CHECKS.find_sdk_root(Path(os.environ['APX_SDK_SOURCE_ROOT'])) / 'XComGame/Classes'
        ability = (sdk / 'XComGameState_Ability.uc').read_text(encoding='utf-8-sig')
        observer = function_body(ability, 'CanActivateAbilityForObserverEvent')
        self.assertIn('ValidatePrimaryTargetOption(self, ShootingUnit, TargetObject)', observer)
        self.assertIn('CheckTargetConditions(self, ShootingUnit, TargetUnit)', observer)
        standard = (sdk / 'X2Ability_DefaultAbilitySet.uc').read_text(encoding='utf-8-sig')
        sniper = (sdk / 'X2Ability_SharpshooterAbilitySet.uc').read_text(encoding='utf-8-sig')
        for source, name in ((standard, 'AddOverwatchShotAbility'), (standard, 'PistolOverwatchShotHelper'),
                             (sniper, 'LongWatchShot')):
            with self.subTest(reaction=name):
                body = function_body(source, name)
                self.assertIn('SingleTarget.OnlyIncludeTargetsInsideWeaponRange = true', body)
                self.assertIn('TargetVisibilityCondition.bRequireGameplayVisible = true', body)
                self.assertIn('TargetVisibilityCondition.bDisablePeeksOnMovement = true', body)
                self.assertEqual(name == 'LongWatchShot', 'bAllowSquadsight = true' in body)
                self.assertEqual(name != 'LongWatchShot', 'bRequireBasicVisibility = true' in body)
                target_conditions = [line for line in body.splitlines()
                                     if 'AbilityTargetConditions.AddItem(' in line]
                self.assertEqual(4, len(target_conditions))
                for condition in ('LivingHostileUnitDisallowMindControlProperty', 'TargetVisibilityCondition',
                                  'X2Condition_EverVigilant', 'OverwatchTargetEffectsCondition()'):
                    self.assertTrue(any(condition in line for line in target_conditions), condition)
