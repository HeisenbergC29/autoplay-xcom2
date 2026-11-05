"""Cloud escape, forecast diagnostics and terminal score observation boundaries."""
from pathlib import Path
import unittest

from test_ui_gating import function_body
from uc_math import load_uc_function

ROOT = Path(__file__).resolve().parents[1]
CLASSES = ROOT / 'AutoplayXCom2/Src/AutoplayXCom2/Classes'
MISSION = CLASSES / 'APX_MissionPlanner.uc'
RECORDER = CLASSES / 'APX_MissionRecorder.uc'


class V15IntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.escape_score = staticmethod(load_uc_function(MISSION, 'ScorePoisonEscape'))

    def test_cloud_escape_does_not_accept_a_material_increase_in_enemy_exposure(self):
        self.assertLess(self.escape_score(20, 24, 0.1, 0, 1), -1000)
        self.assertGreater(self.escape_score(20, 20, 0.1, 0, 1), 0)

    def test_escape_values_survival_and_short_routes_without_ignoring_lost_attacks(self):
        base = self.escape_score(20, 20, 1, 0, 2)
        self.assertGreater(self.escape_score(20, 20, 0.2, 0, 2), base)
        self.assertGreater(self.escape_score(20, 10, 1, 0, 2), base)
        self.assertLess(self.escape_score(20, 20, 1, 60, 2), base)
        self.assertLess(self.escape_score(20, 20, 1, 0, 6), base)

    def test_poison_escape_keeps_native_blue_move_and_entire_route_guards(self):
        body = function_body(MISSION.read_text(), 'ChoosePoisonEscape')
        for guard in ('NeedsPoisonEscape(UnitState)', 'HasLegalMove(UnitState)',
                      'GetAllPathableTiles(Tiles, Visualizer.GetMobility())',
                      'Cost > Visualizer.GetMobility()', 'HasBlockingHazard(UnitState, Tile)',
                      'IsSupportedCombatDestination(UnitState, Tile)', 'IsSupportedAdvanceStep(',
                      'CanSquadSeeLocation(', 'bSafe && bReachedCleanTile'):
            self.assertIn(guard, body)
        self.assertIn('for (Step = 1;', body)
        self.assertIn('CanCrossStartingPoisonTile(', body)
        self.assertLess(body.index('CanCrossStartingPoisonTile('),
                        body.index('HasBlockingHazard(UnitState, CandidatePath[Step])'))
        self.assertIn('bReachedCleanTile = true', body)

    def test_all_existing_movement_routes_use_the_shared_additional_poison_guard(self):
        for name in ('APX_MissionPlanner', 'APX_CombatPlanner', 'APX_SquadPlanner',
                     'APX_EvacPlanner', 'APX_ExplorationPlanner'):
            source = (CLASSES / (name + '.uc')).read_text()
            self.assertIn("class'APX_HazardKnowledge'.static.HasBlockingHazard(", source)
            self.assertNotIn("class'XComPath'.static.TileContainsHazard(", source)

    def test_cloud_and_offensive_moves_compete_and_use_normal_dispatch(self):
        source = (CLASSES / 'APX_Controller.uc').read_text()
        decision = function_body(source, 'MakeDecision')
        for chooser in ("class'APX_MissionPlanner'.static.ChoosePoisonEscape(",
                        "class'APX_RepositionPlanner'.static.ChooseMove("):
            start = decision.index(chooser)
            following = decision[start:start + 420]
            self.assertIn('Score > BestScore && CanUseMove(', following)
        self.assertIn('PC.GameStateMoveUnitSingle(', decision)

    def test_diagnostics_distinguish_status_cloud_and_hypothetical_hit_chance(self):
        source = RECORDER.read_text()
        unit = function_body(source, 'RecordUnit')
        for field in ('poisoned', 'poison_cloud', 'poison_cloud_harmful'):
            self.assertIn('|' + field + '=', unit)
        move = function_body(source, 'MoveFields')
        for field in ('current_poison_cloud', 'destination_poison_cloud', 'needs_poison_escape',
                      'native_chance_now', 'projected_chance', 'forecast_model=bounded_geometry'):
            self.assertIn('|' + field + ('=' if '=' not in field else ''), move)

    def test_native_numeric_score_is_reset_before_read_and_uses_the_tactical_baseline(self):
        source = (CLASSES / 'APX_MissionScore.uc').read_text()
        text = function_body(source, 'GetText')
        self.assertLess(text.index('bHasNativePoints = false'), text.index('History = `XCOMHISTORY'))
        self.assertIn('CurrentPoints = MissionPoints(Ladder.CumulativeScore, CachedBaseline)', text)
        self.assertLess(text.index('CurrentPoints = MissionPoints('), text.index('bHasNativePoints = true'))
        reader = function_body(source, 'ReadNativeMissionPoints')
        self.assertIn('GetText()', reader)
        self.assertIn('return bHasNativePoints', reader)

    def test_terminal_points_are_observed_again_after_history_catchup(self):
        source = RECORDER.read_text()
        finish = function_body(source, 'Finish')
        self.assertLess(finish.index('Observe("finish")'), finish.index('RecordGameScore("finish")'))
        self.assertLess(finish.index('RecordGameScore("finish")'), finish.index('Emit("end"'))
        score = function_body(source, 'RecordGameScore')
        for guard in ('ReadNativeMissionPoints(MissionPoints)', 'BattleData.VictoriousPlayer.ObjectID != 0',
                      'HistoryCursor == `XCOMHISTORY.GetCurrentHistoryIndex()', '!bLimitReported'):
            self.assertIn(guard, score)
        for field in ('mission_points_known', 'mission_final', 'mission_points'):
            self.assertIn('|' + field + '=', score)

    def test_preparation_combo_is_scored_only_for_medical_and_support_and_recorded_without_queueing(self):
        combat = function_body((CLASSES / 'APX_CombatPlanner.uc').read_text(), 'ChooseAction')
        self.assertEqual(combat.count("class'APX_ActionEconomy'.static.ScoreWithRetainedAttack("), 2)
        self.assertLess(combat.index('CandidateScore = ScoreMedical('),
                        combat.index("class'APX_ActionEconomy'.static.ScoreWithRetainedAttack("))
        action = function_body(RECORDER.read_text(), 'ActionFields')
        self.assertIn("class'APX_ActionEconomy'.static.GetRetainedAttack(", action)
        self.assertNotIn('ScoreWithRetainedAttack(', action)
        for field in ('ap_combo_available', 'ap_combo_followup_ability_id',
                      'ap_combo_followup_target', 'ap_combo_retained_attack_value'):
            self.assertIn('|' + field + '=', action)


if __name__ == '__main__':
    unittest.main()
