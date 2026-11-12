"""Confirmed transmitter relays can use a native MP melee target.

Numeric cases execute the real UC scoring helpers. Source/SDK checks preserve
the native target/path boundary; they do not replace Windows or game tests.
"""
import os
from pathlib import Path
import re
import unittest

from test_ui_gating import CHECKS, function_body
from uc_math import load_uc_function


ROOT = Path(__file__).resolve().parents[1]
CLASSES = ROOT / 'AutoplayXCom2/Src/AutoplayXCom2/Classes'
COMBAT = CLASSES / 'APX_CombatPlanner.uc'


class RelayActionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = COMBAT.read_text(encoding='utf-8-sig')
        cls.identity = staticmethod(load_uc_function(COMBAT, 'RelayIdentityMatches'))
        cls.score = staticmethod(load_uc_function(COMBAT, 'ScoreRelayOpportunity'))
        cls.events_fit = staticmethod(load_uc_function(COMBAT, 'RelayEventBudgetAllowed'))

    def test_mission_target_and_known_archetype_are_all_required(self):
        self.assertTrue(self.identity(True, True, True))
        for args in ((False, True, True), (True, False, True), (True, True, False)):
            with self.subTest(args=args):
                self.assertFalse(self.identity(*args))
        body = function_body(self.source, 'IsTransmitterRelay')
        for required in ('"SabotageTransmitter"', 'IsObjectiveTarget(TargetObject.ObjectID)',
                         'Visualizer.ObjectID != TargetObject.ObjectID',
                         'Visualizer.ObjectArchetype == none', 'TargetObject.bRemoved',
                         'PathName(Visualizer.ObjectArchetype)',
                         'DestroyTransmitter_TempAssets.Archetypes.ARC_IA_PsionicNode'):
            self.assertIn(required, body)
        self.assertNotIn('Health == 2', body)
        self.assertNotIn('Health <= 2', body)

    def test_destruction_opportunity_is_bounded_below_ready_plant_and_emergency_aid(self):
        # Actual reported target has 2 HP; native preview decides whether the
        # hit is likely to destroy it. No future hit roll is inspected.
        value = self.score(6, 7, 2, 100, 0)
        self.assertEqual(value, 135)
        self.assertLess(value, 200)  # Ready native PlantBomb interaction.
        self.assertLess(value, 140 + 1 * 4)  # Existing emergency-heal minimum.
        self.assertLess(value, 400)  # Existing stabilization.
        self.assertEqual(self.score(6, 7, 2, 100, 35), 100)
        self.assertLess(self.score(6, 7, 2, 50, 0), value)
        self.assertLess(self.score(6, 7, 20, 100, 0), value)
        self.assertLessEqual(self.score(6, 7, 2, 100, 140), 0)
        for args in ((0, 0, 2, 100, 0), (6, 7, 0, 100, 0),
                     (6, 7, 2, 0, 0), (7, 6, 2, 100, 0)):
            with self.subTest(args=args):
                self.assertEqual(self.score(*args), -10000)
        self.assertEqual(self.score(6, 7, 2, 100, -100), value)

    def test_bounded_native_objective_completion_disables_relay_after_plant(self):
        body = function_body(self.source, 'HasUnfinishedTransmitterPlantObjective')
        for required in ('"SabotageTransmitter"', 'Min(32,',
                         "ObjectiveName == 'PlantBomb'", '.bIsStrategyObjective',
                         '!BattleData.MapData.ActiveMission.MissionObjectives[Index].bCompleted'):
            self.assertIn(required, body)
        self.assertNotIn('AllStrategyObjectivesCompleted()', body)
        self.assertNotIn('TimerValue', body)
        score = function_body(self.source, 'ScoreObjectiveAttack')
        self.assertIn('!HasUnfinishedTransmitterPlantObjective()', score)

    def test_known_relay_uses_only_the_legal_mp_punch_and_existing_melee_guards(self):
        choose = function_body(self.source, 'ChooseAction')
        score = function_body(self.source, 'ScoreObjectiveAttack')
        for required in ("Candidate.AvailableCode != 'AA_Success'",
                         'Ability.OwnerStateObject.ObjectID != UnitState.ObjectID',
                         'default.AttackAbilities.Find(AbilityName)',
                         'Candidate.AvailableTargets[Index], VisibleEnemies)'):
            self.assertIn(required, choose)
        for required in ('bRelay = IsTransmitterRelay(Destructible)',
                         "Ability.GetMyTemplateName() != 'DevastatingPunchMP'",
                         '!AbilityTemplate.TargetingMethod.default.ProvidesPath',
                         'HasRequiredMeleePath(SourceUnit, Destructible, AbilityTemplate,',
                         'VisibleEnemies, MeleePenalty)',
                         'Destructible.IsTargetable(SourceUnit.GetTeam())',
                         'SourceUnit.TargetIsEnemy(Destructible.ObjectID)',
                         'IsObjectiveTarget(Destructible.ObjectID)',
                         'CanXComSquadSeeTarget(Destructible.ObjectID)',
                         'Ability.GetShotBreakdown(Target, Breakdown)',
                         'Ability.GetDamagePreview(Target.PrimaryTarget',
                         'Destructible.Health, HitChance, MeleePenalty)'):
            self.assertIn(required, score)
        self.assertLess(score.index('if (bMovingMelee)'), score.index('Ability.GetDamagePreview('))
        path = function_body(self.source, 'HasRequiredMeleePath')
        self.assertIn('TargetUnit = XComGameState_Unit(TargetState)', path)
        self.assertIn('TargetUnit != none && MeleeCalc != none', path)
        self.assertIn('SourceUnit, TargetState, AbilityTemplate, Destinations', path)
        for guard in ('HasMeleeCounter(TargetUnit)', 'HasBlockingHazard(',
                      'IsSupportedCombatDestination(', 'IsSupportedAdvanceDestination(',
                      'IsSupportedAdvanceStep(', 'CanSquadSeeLocation(', 'ExposureRisk('):
            self.assertIn(guard, path)

    def test_relay_exception_does_not_enable_secondary_explosions_or_mutate_history(self):
        blast = function_body(self.source, 'RelayHasNoRadialEvent')
        self.assertLess(blast.index('!RelayEventBudgetAllowed('),
                        blast.index('for (Index = 0;'))
        self.assertIn('XComDestructibleActor_Action_RadialDamage(', blast)
        for events in ('DamagedEvents', 'DestroyedEvents', 'AnnihilatedEvents'):
            self.assertIn('Visualizer.' + events + '[Index].Action', blast)
        self.assertIn('Visualizer.ObjectID != TargetObject.ObjectID', blast)
        score = function_body(self.source, 'ScoreObjectiveAttack')
        self.assertIn('!RelayHasNoRadialEvent(Destructible)', score)
        self.assertIn('Target.AdditionalTargets.Length != 0', score)
        self.assertIn('AbilityTemplate.AbilityMultiTargetStyle != none', score)
        for forbidden in ('ModifyStateObject(', 'SubmitGameState(', 'CreateNewGameState(',
                          'GetRadialDamageTiles(', 'SYNC_RAND', 'GetNextDestination('):
            self.assertNotIn(forbidden, self.source)

    def test_one_event_budget_covers_damage_destruction_and_annihilation(self):
        for counts in ((0, 0, 0), (32, 0, 0), (0, 32, 0), (0, 0, 32), (10, 10, 12)):
            with self.subTest(counts=counts):
                self.assertTrue(self.events_fit(*counts))
        for counts in ((1, 32, 0), (0, 1, 32), (10, 10, 13), (-1, 0, 0), (2147483647, 1, 1)):
            with self.subTest(counts=counts):
                self.assertFalse(self.events_fit(*counts))


@unittest.skipUnless(os.environ.get('APX_SDK_SOURCE_ROOT'),
                     'SDK sources required for native destructible melee contracts')
class RelayNativeSDKContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sdk = CHECKS.find_sdk_root(Path(os.environ['APX_SDK_SOURCE_ROOT'])) / 'XComGame/Classes'

    def test_mp_punch_supports_non_unit_target_and_native_base_object_attack_tile(self):
        source = (self.sdk / 'X2Ability_Berserker.uc').read_text(encoding='utf-8-sig')
        mp = CHECKS.without_comments(function_body(source, 'CreateDevastatingPunchAbilityMP'))
        self.assertIn('PunchCondition.bFailOnNonUnitTargets = false', mp)
        self.assertIn("new class'X2AbilityTarget_MovingMelee'", mp)
        self.assertNotIn("new class'X2Effect_Knockback'", mp)
        moving = (self.sdk / 'X2AbilityTarget_MovingMelee.uc').read_text(encoding='utf-8-sig')
        self.assertRegex(moving, r'SelectAttackTile\(XComGameState_Unit UnitState,\s*XComGameState_BaseObject TargetState')
        self.assertIn('bAllowDestructibleObjects=true', moving)
        context = (self.sdk / 'XComGameStateContext_Ability.uc').read_text(encoding='utf-8-sig')
        self.assertIn('History.GetGameStateForObjectID(NewContext.InputContext.PrimaryTarget.ObjectID)', context)
        self.assertIn('BuildPathToTile(MeleeDestinations[0], SelectAction.PathTiles)', context)

    @unittest.skipUnless(os.environ.get('APX_GAME_CONFIG_ROOT'),
                         'Game config required to verify exact PlantBomb objective definition')
    def test_transmitter_definition_has_plant_as_strategy_and_sweep_as_tactical(self):
        source = (Path(os.environ['APX_GAME_CONFIG_ROOT']) / 'DefaultMissionDefs.ini').read_text(encoding='utf-8-sig')
        block = source.split('MissionName="SabotageTransmitter"', 1)[1].split('arrMissions=', 1)[0]
        clean = block.replace('\\', ' ')
        self.assertIsNotNone(re.search(
            r'ObjectiveName="PlantBomb",\s*bIsTacticalObjective=false, bIsStrategyObjective=true', clean))
        self.assertIsNotNone(re.search(
            r'ObjectiveName="Sweep",\s*bIsTacticalObjective=true, bIsStrategyObjective=false', clean))


if __name__ == '__main__':
    unittest.main()
