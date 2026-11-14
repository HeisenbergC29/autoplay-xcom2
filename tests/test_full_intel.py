"""User-selected omniscience: source-level contracts, not WOTC gameplay.

The player may know all active hostile positions and terrain. Native legal
ability targeting and path validation must not change.
"""
import os
from pathlib import Path
import unittest
from test_ui_gating import CHECKS, braced_body, function_body
from uc_math import load_uc_function

ROOT=Path(__file__).resolve().parents[1]
CLASSES=ROOT/'AutoplayXCom2/Src/AutoplayXCom2/Classes'


class FullIntelContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.intel=(CLASSES/'APX_FullIntel.uc').read_text(encoding='utf-8-sig')
        cls.controller=(CLASSES/'APX_Controller.uc').read_text(encoding='utf-8-sig')
        cls.mission=(CLASSES/'APX_MissionPlanner.uc').read_text(encoding='utf-8-sig')
        cls.explore=(CLASSES/'APX_ExplorationPlanner.uc').read_text(encoding='utf-8-sig')
        cls.hud=(CLASSES/'APX_UITacticalControl.uc').read_text(encoding='utf-8-sig')

    def test_config_explicitly_enables_full_intel_with_reversible_switch(self):
        cfg=(ROOT/'AutoplayXCom2/Config/XComAutoplayXCom2.ini').read_text()
        self.assertIn('[AutoplayXCom2.APX_FullIntel]', cfg)
        self.assertIn('EnableFullIntel=true', cfg)
        self.assertIn('var config bool EnableFullIntel',self.intel)

    def test_live_hostiles_filtered_and_original_visibility_mode_preserved(self):
        body=function_body(self.intel,'GetKnownEnemies')
        for token in (
            '!default.EnableFullIntel', 'GetAllVisibleEnemiesForPlayer(',
            'SourceUnit.GetTeam() != eTeam_XCom', 'GetLocalClientPlayerObjectID()',
            "IterateByClassType(class'XComGameState_Unit', Enemy)",
            'Enemy.IsAlive()', 'Enemy.IsIncapacitated()',
            'Enemy.bRemovedFromPlay', 'Enemy.IsCivilian()',
            'Enemy.GetMyTemplate().bIsCosmetic', 'SourceUnit.IsEnemyUnit(Enemy)',
            'IsTileOutOfRange(Enemy.TileLocation)',
            'Enemies.AddItem(Enemy.GetReference())',
        ):
            with self.subTest(token=token):
                self.assertIn(token, body)
        for forbidden in ('ModifyStateObject', 'SubmitGameState', 'CreateNewGameState',
                          'Rand(', 'FRand(', 'Enemy.ActionPoints', 'Enemy.Ammo',
                          'Enemy.GetAvailable'):
            self.assertNotIn(forbidden, body)

    def test_sdk_visual_fog_api_and_hud_reapply(self):
        reveal=function_body(self.intel,'RevealMapForPlayer')
        self.assertIn('InitializeAllViewersToHaveSeenFog(true)',reveal)
        self.assertIn('SetFOW(false)',reveal)
        self.assertIn('GetALocalPlayerController()',reveal)
        init=function_body(self.hud,'InitAutoplayControl')
        self.assertIn('RevealMapForPlayer()',init)
        tick=function_body(self.hud,'Tick')
        self.assertIn('RevealMapForPlayer()',tick)
        self.assertIn('bIsRemoved',tick)

    def test_controller_uses_full_contacts_and_no_fog_frontier(self):
        contacts=function_body(self.controller,'RefreshContacts')
        self.assertIn('GetImmediateThreats(SourceUnit, VisibleEnemies)',contacts)
        self.assertNotIn('GetKnownEnemies(',contacts)
        decision=function_body(self.controller,'MakeDecision')
        self.assertIn("!class'APX_FullIntel'.default.EnableFullIntel",decision)
        self.assertIn('EndTurnTicketIsCurrent()',decision)
        self.assertIn('RefreshAreaRejectionScope(',decision)

    def test_combat_goal_and_safe_route_uses_known_map(self):
        threats=function_body(self.mission,'GetVisibleThreats')
        self.assertIn('GetKnownEnemies(UnitState, VisibleEnemies)',threats)
        known=function_body(self.mission,'IsKnownCombatTile')
        self.assertIn("class'APX_FullIntel'.default.EnableFullIntel",known)
        self.assertIn('GetTileFOWValue(',known)
        chooser=function_body(self.mission,'ChooseMove')
        for token in ('ChooseRoutePrefix(UnitState, UnitVisualizer, GoalTile, Path, bCombatGoal)',
                      'CanUseRoutineRoute(Goal.bImmediateThreats,', 'BuildPathToTile(Tile, CandidatePath)',
                      'HasBlockingHazard(', 'IsSupportedAdvanceStep(', 'CanPlanAtTile('):
            with self.subTest(token=token):
                self.assertIn(token,chooser)
        self.assertIn("class'APX_FullIntel'.default.EnableFullIntel",
                      function_body(self.explore,'IsUnexploredFloor'))

    def test_native_target_legal_action_and_path_guards_still_present(self):
        combat=(CLASSES/'APX_CombatPlanner.uc').read_text()
        chooser=function_body(combat,'ChooseAction')
        for token in ("Candidate.AvailableCode != 'AA_Success'",
                      'Candidate.bInputTriggered', 'Candidate.AvailableTargets',
                      'HasRequiredMeleePath(', 'AdditionalTargetsAreSafe(',
                      "GetAllVisibleEnemiesForPlayer("):
            self.assertIn(token,chooser)

    def test_runtime_records_current_revision(self):
        recorder=(CLASSES/'APX_MissionRecorder.uc').read_text()
        dlc=(CLASSES/'X2DownloadableContentInfo_AutoplayXCom2.uc').read_text()
        for source in (recorder,dlc,self.hud):
            self.assertIn('mission-report-v39',source)


class FullIntelPolicyScenarios(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mission = CLASSES / 'APX_MissionPlanner.uc'
        cls.pursue = staticmethod(load_uc_function(cls.mission, 'ShouldPursueKnownEnemies'))
        cls.routine = staticmethod(load_uc_function(cls.mission, 'CanUseRoutineRoute'))
        cls.combat_movement = staticmethod(load_uc_function(cls.mission, 'RequiresCombatMovement'))
        cls.mission_goal = staticmethod(load_uc_function(cls.mission, 'IsMissionTravelGoal'))
        cls.loot = staticmethod(load_uc_function(cls.mission, 'IsLootRouteAllowed'))
        cls.loot_progress = staticmethod(load_uc_function(cls.mission, 'LootRouteMakesProgress'))
        cls.source = cls.mission.read_text(encoding='utf-8-sig')

    def test_remote_enemy_does_not_replace_an_urgent_mission_goal(self):
        self.assertFalse(self.pursue(True, True, 1))
        self.assertTrue(self.pursue(True, False, 1))
        self.assertFalse(self.pursue(True, False, 0))
        self.assertFalse(self.pursue(False, False, 1))
        goal = function_body(self.source, 'FindGoal')
        self.assertLess(goal.index('foreach ImmediateEnemies('),
                        goal.index("IterateByClassType(class'XComGameState_InteractiveObject'"))
        self.assertLess(goal.index('BattleData.MapData.ObjectiveLocation'),
                        goal.index('ShouldPursueKnownEnemies('))

    def test_remote_only_enemy_does_not_veto_safe_nearby_loot(self):
        # No immediate contact, bleeding, evacuation, ready objective or timer.
        self.assertTrue(self.loot(False, False, False, False, False, 2))
        # A distant combat-pursuit goal cannot forbid a short loot detour.
        self.assertFalse(self.mission_goal(True, True))
        self.assertTrue(self.loot_progress(self.mission_goal(True, True), 5, 7))
        self.assertFalse(self.loot(True, False, False, False, False, 2))
        self.assertFalse(self.loot(False, True, False, False, False, 2))
        loot = function_body(self.source, 'ChooseLootMove')
        self.assertIn('GetImmediateThreats(UnitState, VisibleEnemies)', loot)
        self.assertIn('bHasMissionGoal = IsMissionTravelGoal(Goal.bFound, Goal.bCombat)', loot)

    def test_hidden_nearer_enemy_cannot_bypass_visible_fight_scoring(self):
        # The immediate shooter still sets this flag even if a hidden enemy
        # would be closer. Known-enemy distance is not an input to this gate.
        self.assertFalse(self.routine(True, False, 2))
        self.assertFalse(self.routine(True, False, 1))
        immediate = function_body(self.source, 'GetImmediateThreats')
        self.assertIn('GetAllVisibleEnemiesForPlayer(', immediate)
        self.assertNotIn('GetKnownEnemies(', immediate)
        move = function_body(self.source, 'ChooseMove')
        self.assertIn('if (bRoutineRoute &&', move)
        for guard in ('IsUsefulReposition(', 'ScoreCombatReposition(',
                      'MoveOpportunityPenalty(', 'IsSupportedCombatDestination('):
            self.assertIn(guard, move)

    def test_last_ap_is_reserved_on_a_distant_pursuit(self):
        self.assertTrue(self.routine(False, False, 2))
        self.assertFalse(self.routine(False, False, 1))
        self.assertFalse(self.routine(False, False, 0))
        self.assertTrue(self.routine(False, True, 1))
        move = function_body(self.source, 'ChooseMove')
        self.assertIn('if (!Goal.bImmediateThreats && !bRoutineRoute)', move)
        prefix = function_body(self.source, 'ChooseRoutePrefix')
        self.assertIn('bCombatRoute && !IsSupportedCombatDestination(', prefix)
        self.assertIn('HasBlockingHazard(', prefix)
        self.assertIn('IsSupportedAdvanceStep(', prefix)

    def test_controlled_squadmate_is_known_danger_but_not_a_pursuit_target(self):
        intel = function_body((CLASSES / 'APX_FullIntel.uc').read_text(), 'GetKnownEnemies')
        self.assertNotIn('IsReclaimableControlledSquadmate(', intel)
        goal = function_body(self.source, 'FindGoal')
        # Each pursuit branch must retain the protection, including the new
        # post-PlantBomb Sweep. A fixed count of two sites hid that distinction.
        for marker in ('foreach ImmediateEnemies(EnemyRef)', 'if (bBerserkerSweep)',
                       'if (ShouldPursueKnownEnemies('):
            with self.subTest(branch=marker):
                body = braced_body(goal, goal.index('{', goal.index(marker)))
                guard = body.index('IsReclaimableControlledSquadmate(UnitState, OtherUnit)')
                self.assertLess(guard, body.index('ConsiderGoal(UnitState, OtherUnit.TileLocation'))
                self.assertIn('continue;', body[guard:body.index('ConsiderGoal(')])
        native = function_body(self.source, 'GetImmediateThreats')
        self.assertIn('GetAllVisibleEnemiesForPlayer(', native)
        # The existing attack/grenade protection is verified in its dedicated tests.

    def test_protected_visible_hostile_still_requires_combat_movement(self):
        self.assertTrue(self.combat_movement(False, True, False))
        self.assertTrue(self.combat_movement(True, True, False))
        self.assertFalse(self.combat_movement(False, False, False))
        self.assertFalse(self.combat_movement(False, True, True))
        move = function_body(self.source, 'ChooseMove')
        self.assertIn('bCombatGoal = RequiresCombatMovement(Goal.bCombat, Goal.bImmediateThreats,', move)


@unittest.skipUnless(os.environ.get('APX_SDK_SOURCE_ROOT'),
                     'Stock SDK needed to verify native FOW helper signatures')
class FullIntelSDKContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sdk=CHECKS.find_sdk_root(Path(os.environ['APX_SDK_SOURCE_ROOT']))/'XComGame/Classes'

    def test_stock_battle_hides_visual_fog(self):
        s=(self.sdk/'XGBattle.uc').read_text()
        body=function_body(s,'SetFOW')
        self.assertIn('bEnableFOW = bNewFOW',body)
        self.assertIn('FOWEffect.bShowFOW',body)

    def test_stock_map_reveal(self):
        s=(self.sdk/'XComWorldData.uc').read_text()
        self.assertIn('InitializeAllViewersToHaveSeenFog(bool bSetting)',s)


if __name__ == '__main__':
    unittest.main()
