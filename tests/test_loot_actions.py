"""Exercise loot priorities and audit the native pickup/navigation boundary.

The numeric cases execute the real UnrealScript helpers. Source/SDK contracts
check that navigation only proposes a safe tile; native Loot still owns range,
eligibility, item acquisition and the final post-movement target list.
"""
import os
from pathlib import Path
import unittest

from test_ui_gating import CHECKS, function_body
from uc_math import load_uc_function


ROOT = Path(__file__).resolve().parents[1]
CLASSES = ROOT / 'AutoplayXCom2/Src/AutoplayXCom2/Classes'
SOURCE = CLASSES / 'APX_MissionPlanner.uc'


class LootActionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.route_allowed = staticmethod(load_uc_function(SOURCE, 'IsLootRouteAllowed'))
        cls.progress = staticmethod(load_uc_function(SOURCE, 'LootRouteMakesProgress'))
        cls.score = staticmethod(load_uc_function(SOURCE, 'ScoreLootMove'))
        cls.source = SOURCE.read_text()

    def test_combat_bleeding_evac_objective_and_deadline_each_block_loot_travel(self):
        self.assertTrue(self.route_allowed(False, False, False, False, False, 2))
        for blocker in range(5):
            state = [False] * 5
            state[blocker] = True
            with self.subTest(blocker=blocker):
                self.assertFalse(self.route_allowed(*state, 2))
        for ap in (0, 1):
            self.assertFalse(self.route_allowed(False, False, False, False, False, ap))

    def test_loot_endpoint_cannot_take_soldier_farther_from_mission_goal(self):
        self.assertTrue(self.progress(True, 12.0, 8.0))
        self.assertTrue(self.progress(True, 12.0, 12.0))
        self.assertFalse(self.progress(True, 12.0, 12.01))
        self.assertFalse(self.progress(True, 1.0, 9.0))
        self.assertTrue(self.progress(False, 0.0, 8.0))

    def test_expiry_only_breaks_short_safe_route_preferences(self):
        self.assertGreater(self.score(3, 1, True), self.score(3, 3, True))
        self.assertGreater(self.score(1, 2, True), self.score(9, 2, True))
        self.assertGreater(self.score(3, 3, True), self.score(3, 1, False))
        self.assertLess(self.score(0, 1, True), 100)
        # Very large costs and an unexpected timer cannot create huge utility.
        self.assertEqual(self.score(1000, -1000, False), 23)

    def test_actual_free_native_ability_and_ready_cache_target_are_required(self):
        ready = function_body(self.source, 'GetReadyLootAbility')
        for contract in ("UnitState.FindAbility('Loot')",
                         'Ability.OwnerStateObject.ObjectID != UnitState.ObjectID',
                         'Template.AbilityCosts.Length != 0',
                         "Template.AbilityTargetStyle.Class != class'X2AbilityTarget_Single'",
                         "Template.AbilityMultiTargetStyle.Class != class'X2AbilityMultiTarget_Loot'",
                         "Ability.CanActivateAbility(UnitState) != 'AA_Success'",
                         'LootCondition.bRestrictRange', 'LootCondition.LootableRange > 0'):
            self.assertIn(contract, ready)
        pickup = function_body(self.source, 'ChooseLootInteraction')
        for contract in ("Candidate.AvailableCode != 'AA_Success'",
                         '!Candidate.bInputTriggered', 'Candidate.bFreeAim',
                         'Candidate.AvailableTargets[Index].PrimaryTarget.ObjectID',
                         'HasAvailableLootForLooter(UnitState.GetReference())',
                         'HasBleedingSquadmate(UnitState)', 'ShouldEvacuate(UnitState)'):
            self.assertIn(contract, pickup)

    def test_whole_native_blue_path_has_current_visibility_hazard_and_support_guards(self):
        move = function_body(self.source, 'ChooseLootMove')
        for contract in ('UnitState.NumActionPoints(', 'Cost > Visualizer.GetMobility()',
                         'BuildPathToTile(Tile, CandidatePath)',
                         'PreparationPathIsSafe(UnitState, CandidatePath)',
                         'IsSupportedAdvanceDestination(', 'LootRouteMakesProgress(',
                         'GetVisibleThreats(UnitState, VisibleEnemies)',
                         'IsLootRouteAllowed(VisibleEnemies.Length > 0'):
            self.assertIn(contract, move)
        path = function_body((CLASSES / 'APX_SquadPlanner.uc').read_text(), 'PreparationPathIsSafe')
        for contract in ('IsKnownCombatTile(Tile)', 'CanSquadSeeLocation(',
                         'HasBlockingHazard(Soldier, Tile)',
                         'IsSupportedAdvanceStep(', 'IsDestructiveTraversal('):
            self.assertIn(contract, path)

    def test_only_visible_unexpired_eligible_drops_and_actual_deadlines_are_read(self):
        move = function_body(self.source, 'ChooseLootMove')
        for contract in ("IterateByClassType(class'XComGameState_LootDrop', Drop)",
                         'Drop.LootExpirationTurnsRemaining <= 0', 'Drop.HasNonPsiLoot()',
                         'Drop.HasAvailableLootForLooter(UnitState.GetReference())',
                         'CanSquadSeeLocation(', 'HasActiveMissionDeadline()'):
            self.assertIn(contract, move)
        self.assertNotIn("IterateByClassType(class'XComGameState_Unit'", move)
        deadline = function_body(self.source, 'HasActiveMissionDeadline')
        for contract in ('TimerState.IsTimer', 'TimerState.ShouldShow', '!TimerState.IsSuspended()'):
            self.assertIn(contract, deadline)
        self.assertNotIn('TimerValue', deadline)

    def test_proposed_pickup_uses_strict_native_world_range_without_relocating_unit(self):
        move = function_body(self.source, 'ChooseLootMove')
        self.assertIn('VSizeSq(CandidateLocation - LootLocation) >= Square(LootRange)', move)
        self.assertIn('CanSeeTileToTile(Tile, LootTile, Visibility)', move)
        self.assertNotIn('MeetsConditionWithSource(', move)
        for name in ('GetReadyLootAbility', 'ChooseLootInteraction', 'ChooseLootMove'):
            helper = function_body(self.source, name)
            for forbidden in ('ModifyStateObject', 'SubmitGameState', 'MakeAvailableLoot(',
                              'AcquireAllLoot(', 'SetCurrentStat', 'CloseScreen(',
                              'PopScreen(', 'ActivateAbility_ReturnContext'):
                self.assertNotIn(forbidden, helper)
        self.assertNotRegex(move, r'UnitState\.TileLocation\s*=')


@unittest.skipUnless(os.environ.get('APX_SDK_SOURCE_ROOT'), 'SDK loot contracts need APX_SDK_SOURCE_ROOT')
class LootSDKContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sdk = CHECKS.find_sdk_root(Path(os.environ['APX_SDK_SOURCE_ROOT'])) / 'XComGame/Classes'

    def test_native_pickup_is_free_and_collects_items_without_a_choice_screen(self):
        source = (self.sdk / 'X2Ability_DefaultAbilitySet.uc').read_text(encoding='utf-8-sig')
        ability = function_body(source, 'AddLootAbility')
        self.assertIn("'Loot'", ability)
        self.assertNotIn('AbilityCosts.AddItem', ability)
        self.assertIn('LootableCondition.LootableRange = default.LOOT_RANGE', ability)
        self.assertIn('LootableCondition.bRestrictRange = true', ability)
        self.assertIn('VisibilityCondition.bRequireLOS = true', ability)
        self.assertIn('AbilityTriggerEventListener_EndOfMoveLoot', ability)
        self.assertIn("EventTrigger.ListenerData.EventID = 'UnitMoveFinished'", ability)
        self.assertIn("new class'X2AbilityMultiTarget_Loot'", ability)
        build = function_body(source, 'LootAbility_BuildGameState')
        self.assertIn('MakeAvailableLoot(NewGameState)', build)
        self.assertIn('AcquireAllLoot(', build)
        visual = function_body(source, 'LootAbility_BuildVisualization')
        self.assertIn("class'X2Action_Loot'.static.AddToVisualizationTreeIfLooted", visual)
        self.assertNotIn('PushScreen', visual)

    def test_end_of_move_uses_refreshed_native_targets_and_native_range_is_strict(self):
        source = (self.sdk / 'XComGameState_Ability.uc').read_text(encoding='utf-8-sig')
        pickup = function_body(source, 'AbilityTriggerEventListener_EndOfMoveLoot')
        self.assertIn('GetGameRulesCache_Unit(MovingUnitState.GetReference(), UnitCache)', pickup)
        self.assertIn('AvailableTargets.Length', pickup)
        self.assertIn('ActivateAbility(UnitCache.AvailableActions[ActionIndex], LootTargetIndex', pickup)
        source = (self.sdk / 'X2Condition_Lootable.uc').read_text(encoding='utf-8-sig')
        condition = function_body(source, 'CallMeetsConditionWithSource')
        self.assertIn('SourceUnitState.TileLocation', condition)
        self.assertIn('Distance >= LootableRange', condition)
        self.assertIn('HasAvailableLootForLooter(SourceUnitState.GetReference())', condition)


if __name__ == '__main__':
    unittest.main()
