"""Defensive ranking scenarios execute the actual scalar UnrealScript helpers.

Native availability, cover validity, reserve AP and reaction shots still require
the stock SDK compiler/game; these tests guard comparisons rather than simulate AI.
"""
from pathlib import Path
import unittest

from uc_math import load_uc_function
from test_ui_gating import function_body


SOURCE = Path(__file__).resolve().parents[1] / 'AutoplayXCom2/Src/AutoplayXCom2/Classes/APX_CombatPlanner.uc'


class TacticalDefenseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.overwatch = staticmethod(load_uc_function(SOURCE, 'ScoreOverwatchDefense'))
        cls.hunker = staticmethod(load_uc_function(SOURCE, 'ScoreHunkerDefense'))
        cls.aid = staticmethod(load_uc_function(SOURCE, 'ScoreAidDefense'))
        cls.shot = staticmethod(load_uc_function(SOURCE, 'ScoreDamage'))

    def test_out_of_contact_overwatch_does_not_preempt_advancing(self):
        self.assertEqual(self.overwatch(False, False, 1, 0, 0), 2)
        self.assertLess(self.overwatch(False, True, 1, 0, 0), 9)

    def test_low_probability_shot_can_lose_to_overwatch(self):
        poor_shot = self.shot(3, 5, 6, 25, 1, 0)
        self.assertGreater(self.overwatch(True, False, 1, 4.2, 0), poor_shot)

    def test_healthy_full_cover_prefers_reaction_over_hunker(self):
        self.assertGreater(self.overwatch(True, False, 1, 4.2, 0),
                           self.hunker(1, 4.2, 1, 0, False, False))

    def test_wounded_exposed_soldier_prefers_hunker_over_bad_shot(self):
        defensive = self.hunker(0.25, 42, 1, 0, False, False)
        self.assertGreater(defensive, self.shot(3, 5, 6, 35, 1, 0))
        self.assertGreater(defensive, self.overwatch(True, False, 0.25, 42, 0))

    def test_hunker_scales_with_current_personal_exposure(self):
        """Wounds alone have no defensive utility; risk is continuous up to a fully open lane."""
        for health in (1.0, 0.25):
            with self.subTest(health=health):
                risks = (0.0, 0.1, 4.2, 14.0, 41.99, 42.0, 42.01)
                scores = [self.hunker(health, risk, 1, 0, False, False) for risk in risks]
                self.assertEqual(scores[0], 1.0)
                self.assertEqual(scores, sorted(scores))
                self.assertLess(scores[5] - scores[4], 0.02)
                self.assertLess(scores[6] - scores[5], 0.02)

    def test_personal_cover_and_los_feed_the_hunker_vs_overwatch_ranking(self):
        """Exercise the scalar chain from native geometry inputs through competition with Overwatch."""
        movement = SOURCE.with_name('APX_MissionPlanner.uc')
        direction = load_uc_function(movement, 'DirectionalRisk')
        known = load_uc_function(movement, 'KnownThreatRisk')
        combined = load_uc_function(movement, 'CombinedExposure')

        blocked = known(direction(2, 16, True, False), False, False)
        blocked_tile = combined(blocked, blocked, 1.0)
        squad_contact = self.overwatch(False, False, 1.0, blocked_tile, 0, True)
        self.assertLess(self.hunker(1.0, blocked_tile, 1, 0, False, False), squad_contact)
        self.assertLess(self.hunker(0.25, blocked_tile, 1, 0, False, False), squad_contact)

        open_lane = known(direction(0, 16, True, False), True, False)
        open_tile = combined(open_lane, open_lane, 1.0)
        self.assertAlmostEqual(42.0, open_tile)
        self.assertAlmostEqual(47.8, self.hunker(0.25, open_tile, 1, 0, False, False))
        self.assertGreater(self.hunker(0.25, combined(2 * open_lane, open_lane, 1.0), 2, 0,
                                       False, False), self.overwatch(True, False, 0.25, open_tile, 0))

    def test_gas_station_hunker_yields_to_recorded_move_at_d15(self):
        """The 3/5 HP shooter's v48 stance no longer outranks the same decision's move candidate."""
        # With this recorded HP and no melee penalty, v48's uncapped score
        # 31.1867 identifies ranged risk up to the log's rounding precision.
        stance = self.hunker(3 / 5, 21.46675, 1, 0, False, False)
        self.assertAlmostEqual(16.4288, stance, places=4)
        self.assertLess(stance, 17.6989)

    def test_live_chooser_uses_the_scoring_chain_only_for_native_legal_actions(self):
        """Follow the chooser entries linking observed geometry and HP to squad competition."""
        source = SOURCE.read_text()
        choose = function_body(source, 'ChooseAction')
        score = function_body(source, 'ScoreSelfAction')
        controller = function_body(SOURCE.with_name('APX_Controller.uc').read_text(), 'MakeDecision')
        self.assertLess(choose.index("Candidate.AvailableCode != 'AA_Success'"),
                        choose.index('CandidateScore = ScoreSelfAction('))
        score_branch = choose[choose.index('CandidateScore = ScoreSelfAction('):]
        self.assertIn('if (CandidateScore > Score)', score_branch)
        self.assertIn('RangedRisk = DefensiveRisk(UnitState, VisibleEnemies,', score)
        self.assertIn('return ScoreHunkerDefense(HealthFraction, RangedRisk, RangedThreats,', score)
        self.assertIn("class'APX_CombatPlanner'.static.ChooseAction(", controller)
        self.assertIn('Score > BestScore && CanUseAction(', controller)
        self.assertIn('Score > BestScore && CanUseMove(', controller)

    def test_reliable_kill_still_beats_nonemergency_hunker(self):
        reliable_kill = self.shot(3, 5, 3, 85, 1, 0)
        self.assertGreater(reliable_kill, self.hunker(0.25, 42, 1, 0, False, False))

    def test_hunker_does_not_pretend_to_stop_melee(self):
        self.assertEqual(self.hunker(0.25, 0, 0, 1, False, False), 1)
        self.assertLess(self.hunker(0.25, 42, 1, 1, False, False),
                        self.hunker(0.25, 42, 1, 0, False, False))
        self.assertGreater(self.overwatch(True, False, 1, 0, 1),
                           self.overwatch(True, False, 1, 0, 0))

    def test_hunker_extinguishes_fire_even_without_contact(self):
        self.assertEqual(self.hunker(0.5, 0, 0, 0, True, False), 130)
        self.assertGreater(self.hunker(0.5, 0, 0, 0, True, False),
                           self.shot(3, 5, 6, 85, 1, 0))

    def test_concealed_soldier_preserves_reaction_option(self):
        self.assertEqual(self.hunker(1, 42, 1, 0, False, True), 1)
        self.assertGreater(self.overwatch(True, True, 1, 4.2, 0),
                           self.overwatch(True, False, 1, 4.2, 0))

    def test_aid_protocol_is_saved_without_meaningful_ranged_risk(self):
        self.assertLess(self.aid(1, 0, 0), -1000)
        self.assertLess(self.aid(1, 4.2, 1), -1000)
        self.assertGreater(self.aid(0.25, 42, 1), self.aid(1, 42, 1))

    def test_legacy_obstructed_viper_aid_no_longer_displaces_recorded_escape(self):
        movement = SOURCE.with_name('APX_MissionPlanner.uc')
        directional = load_uc_function(movement, 'DirectionalRisk')
        known = load_uc_function(movement, 'KnownThreatRisk')
        combined = load_uc_function(movement, 'CombinedExposure')
        # Legacy D5: the only ranged contact was a Viper without tile LOS.
        # Native visibility/pathfinding remain an in-game check. The log's
        # retreat26 must beat Aid21.88, previously inflated to32.8.
        contact_risk = known(directional(0, 11.4, True, False), False, False)
        ranged_risk = combined(contact_risk, contact_risk, 1)
        self.assertAlmostEqual(self.aid(1, ranged_risk, 1), 21.88)
        self.assertLess(self.aid(1, ranged_risk, 1), 26)
        self.assertGreater(self.aid(1, combined(30, 30, 1), 1), 26)

    def test_movement_and_defense_share_the_visible_contact_risk_contract(self):
        defense = function_body(SOURCE.read_text(), 'DefensiveRisk')
        movement = SOURCE.with_name('APX_MissionPlanner.uc').read_text()
        exposure = function_body(movement, 'ExposureRisk')
        contact = function_body(movement, 'ThreatRiskAtTile')
        self.assertIn('ThreatRiskAtTile(', exposure)
        self.assertIn('ThreatRiskAtTile(', defense)
        self.assertLess(defense.index('IsVisibleHostile('), defense.index('ThreatRiskAtTile('))
        self.assertLess(defense.index('if (Enemy.IsMeleeOnly())'), defense.index('ThreatRiskAtTile('))
        self.assertIn('KnownThreatRisk(Risk, bClearLOS, Enemy.IsMeleeOnly())', contact)
        self.assertIn('CombinedExposure(TotalRisk, WorstRisk, 1.0)', defense)


if __name__ == '__main__':
    unittest.main()
