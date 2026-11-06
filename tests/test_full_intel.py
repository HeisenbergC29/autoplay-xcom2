"""User-selected omniscience: source-level contracts, not WOTC gameplay.

The player may know all active hostile positions and terrain. Native legal
ability targeting and path validation must not change.
"""
import os
from pathlib import Path
import unittest
from test_ui_gating import CHECKS, function_body

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
            'IsReclaimableControlledSquadmate(', 'Enemies.AddItem(Enemy.GetReference())',
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
        self.assertIn('GetKnownEnemies(SourceUnit, VisibleEnemies)',contacts)
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
        for token in ('ChooseRoutePrefix(UnitState, UnitVisualizer, GoalTile, Path)',
                      'CanSquadSeeLocation(', 'BuildPathToTile(Tile, CandidatePath)',
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

    def test_runtime_records_distinct_v20_revision(self):
        recorder=(CLASSES/'APX_MissionRecorder.uc').read_text()
        dlc=(CLASSES/'X2DownloadableContentInfo_AutoplayXCom2.uc').read_text()
        for source in (recorder,dlc,self.hud):
            self.assertIn('mission-report-v20',source)


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
