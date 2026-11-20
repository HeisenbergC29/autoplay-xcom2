"""#104: ranged shot vs speculative blue flank vs non-guaranteed Overwatch.

Numeric tests execute the actual pure UnrealScript methods. Path, target and
Controller tests are source contracts; they do not execute native WOTC.
"""
from pathlib import Path
import unittest

from test_ui_gating import CHECKS, function_body
from uc_math import load_uc_function

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "AutoplayXCom2/Src/AutoplayXCom2/Classes"
REPOSITION = SRC / "APX_RepositionPlanner.uc"
COMBAT = SRC / "APX_CombatPlanner.uc"
CONTROLLER = SRC / "APX_Controller.uc"


class RevealedShooterPolicyTests(unittest.TestCase):
    """Exercise every introduced pure policy and the unchanged action scorers."""

    @classmethod
    def setUpClass(cls):
        """Read actual installed UC source so tests fail on unreviewed policy drift."""
        cls.path_risk = staticmethod(load_uc_function(REPOSITION, "ForecastPathRiskAllowed"))
        cls.stage = staticmethod(load_uc_function(REPOSITION, "ForecastScanStage"))
        cls.move_score = staticmethod(load_uc_function(REPOSITION, "MoveAndShotScore"))
        cls.ow_score = staticmethod(load_uc_function(COMBAT, "ScoreOverwatchDefense"))
        cls.ow_guard = staticmethod(load_uc_function(COMBAT, "GuardOverwatchForKnownAlly"))
        cls.chance = staticmethod(load_uc_function(REPOSITION, "ProjectedHitChance"))
        cls.projected = staticmethod(load_uc_function(REPOSITION, "ProjectedShotScore"))

    def test_all_risky_middle_tiles_block_forecast_even_when_endpoint_safe(self):
        """A safe endpoint cannot excuse exposing an intermediate blue path tile."""
        self.assertTrue(self.path_risk(20, 20))
        self.assertTrue(self.path_risk(20, 0))
        self.assertFalse(self.path_risk(20, 20.01))
        self.assertFalse(self.path_risk(0, 1))
        self.assertFalse(self.path_risk(-1, 0))
        self.assertFalse(self.path_risk(20, -1))
        self.assertFalse(all(self.path_risk(20, n) for n in (11, 26, 7)))
        self.assertTrue(all(self.path_risk(20, n) for n in (11, 20, 7)))

    def test_each_diagnostic_stage_is_explicit_and_not_a_native_legality_claim(self):
        """No supported shot is distinct from no reachable safe movement."""
        expected = [
            ((0, 0, 0, 0, False), 0),
            ((2, 0, 0, 0, False), 1),
            ((2, 48, 0, 0, False), 2),
            ((2, 48, 3, 0, False), 3),
            ((2, 48, 3, 1, False), 4),
            ((2, 48, 3, 1, True), 5),
        ]
        for args, stage in expected:
            with self.subTest(args=args):
                self.assertEqual(self.stage(*args), stage)

    def test_string_labels_are_stable_and_tied_to_tested_numeric_stages(self):
        """Each diagnostic reason is mapped from one numeric policy branch."""
        source = REPOSITION.read_text(encoding="utf-8-sig")
        mapping = function_body(source, "ForecastScanReason")
        self.assertIn("Stage = ForecastScanStage(", mapping)
        for label in ("no_supported_current_shot", "no_native_blue_endpoints",
                      "no_material_projected_shot", "unsafe_or_unverified_blue_path",
                      "outscored_by_other_local_route", "safe_move_and_shot_candidate"):
            self.assertIn(f'return "{label}";', mapping)

    def test_good_immediate_shot_and_overwatch_must_not_be_downgraded(self):
        """Observed GasStation good 70-85% legal shots should remain competitive."""
        strong = 55.08  # GasStation decision 2, confirmed native sniper action.
        self.assertLess(self.move_score(strong, 59, 82, 87, 22, 12, 4, 2), -1000)
        self.assertGreater(strong, self.ow_score(True, False, 1, 0, 0))
        self.assertEqual(self.ow_score(False, False, 1, 0, 0), 2)

    def test_weak_shot_can_justify_separately_legal_blue_move_but_not_last_ap(self):
        """A material +hit chance and +damage only proposes movement; no auto shot."""
        chance = self.chance(35, 15, 20)
        projected = self.projected(30, 35, chance)
        self.assertEqual(chance, 70)
        self.assertGreater(projected, 30)
        self.assertGreater(self.move_score(30, projected, 35, chance, 20, 14, 4, 2), 30)
        self.assertLess(self.move_score(30, projected, 35, chance, 20, 14, 4, 1), -1000)
        self.assertLess(self.move_score(30, projected, 35, chance, 20, 21, 4, 2), -1000)

    def test_known_mind_controlled_squadmate_vetoes_speculative_overwatch(self):
        """Only current verified original-owner evidence warrants an OW veto."""
        self.assertEqual(self.ow_guard(17, True), -10000)
        self.assertEqual(self.ow_guard(22, True), -10000)
        self.assertEqual(self.ow_guard(17, False), 17)
        self.assertEqual(self.ow_guard(2, False), 2)
        # A mind-control event not yet observed at arming cannot be predicted;
        # the False case leaves the stock reaction heuristic unchanged.

    def test_overwatch_reaction_is_not_projected_as_a_certain_future_hit(self):
        """Native engine, not the planner, selects reaction target and roll."""
        self.assertLess(self.ow_score(True, False, 1, 0, 0), 20)
        self.assertLess(self.ow_score(True, False, 1, 0, 1), 25)
        self.assertEqual(self.ow_score(False, False, 1, 0, 0), 2)


class RevealedShooterSourceContracts(unittest.TestCase):
    """Verify complex native call boundaries, path guards and recorder wiring."""

    @classmethod
    def setUpClass(cls):
        """Load runtime owners for the per-method contract suite."""
        cls.reposition = REPOSITION.read_text(encoding="utf-8-sig")
        cls.combat = COMBAT.read_text(encoding="utf-8-sig")
        cls.controller = CONTROLLER.read_text(encoding="utf-8-sig")

    def test_full_path_helper_applies_native_checks_to_every_step_and_shared_budget(self):
        """No cheap forecast may cross unexamined explosive/midpoint danger."""
        f = function_body(self.reposition, "ForecastBluePathSafe")
        for token in (
            "CandidatePath.Length > 64", "CandidatePath[0] != UnitState.TileLocation",
            "RemainingTempoCoverChecks < CandidatePath.Length - 1",
            "for (Step = 1; Step < CandidatePath.Length; ++Step)",
            "IsKnownCombatTile(", "HasBlockingHazard(", "CanSquadSeeLocation(",
            "IsSupportedAdvanceStep(", "ForecastPathRiskAllowed(OriginRisk,",
            "ExposureRisk(", "IsSupportedCombatDestination(",
            "BlueRouteExplosiveSafe(", "RemainingTempoCoverChecks",
        ):
            self.assertIn(token, f)
        self.assertLess(f.index("for (Step = 1;"),
                        f.index("BlueRouteExplosiveSafe("))
        for forbidden in ("ModifyStateObject(", "SubmitGameState(", "SYNC_RAND(",
                          "ActivateAbility_ReturnContext(", "GameStateMoveUnitSingle("):
            self.assertNotIn(forbidden, CHECKS.without_comments(f))

    def test_actual_future_shot_remains_unconfirmed_and_fresh_after_native_blue(self):
        """The forecast uses current legal native targets but never fabricates them."""
        gather = function_body(self.reposition, "GatherForecasts")
        choose = function_body(self.reposition, "ChooseMove")
        project = function_body(self.reposition, "ProjectAtTile")
        for key in ("Candidate.AvailableCode != 'AA_Success'",
                    "CanAttackWithActionPoints(Ability, UnitState, RemainingPoints)",
                    "IsVisibleHostile(UnitState, TargetUnit, VisibleEnemies)",
                    "Target.AdditionalTargets.Length > 0",
                    "EndsTurnForForecast(Ability, UnitState)"):
            self.assertIn(key, gather)
        for key in ("ValidatePrimaryTargetOptionFromRemoteLocation(",
                    "GetVisibilityInfoFromRemoteLocation(", "EvaluateConditions(",
                    "LivingHostileGameplayVisibleFilter"):
            self.assertIn(key, project)
        for key in ("GatherForecasts(", "ForecastBluePathSafe(", "SafeRoutes",
                    "ImprovedShots", "ForecastScanReason(",
                    "Score = Value;", "Score = -10000.0;"):
            self.assertIn(key, choose)
        self.assertNotIn("UnitState.TileLocation =", self.reposition)
        self.assertNotIn("GetAllUnits(", self.reposition)

    def test_controller_logs_bounded_diagnostic_and_keeps_actual_native_dispatch(self):
        """Only accepted native move is submitted, all other abilities still compete."""
        main = function_body(self.controller, "MakeDecision")
        for key in ("RepositionScanReason", "RepositionSupportedShots",
                    "RepositionImprovedShots", "RepositionSafeRoutes",
                    "RemainingTempoCoverChecks", "ChooseMove(",
                    'MissionRecorder.Marker("offensive_reposition_scan"',
                    "safe_native_paths=", "current_best=", "future_native_shot=unverified",
                    "TraceCandidateMove(UnitState, CandidatePath, Score)",
                    "Score > BestScore && CanUseMove(UnitState, CandidatePath)",
                    "GameStateMoveUnitSingle("):
            self.assertIn(key, main)
        self.assertLess(main.index("class'APX_CombatPlanner'.static.ChooseAction("),
                        main.index("class'APX_RepositionPlanner'.static.ChooseMove("))
        self.assertLess(main.index("class'APX_RepositionPlanner'.static.ChooseMove("),
                        main.index("class'APX_MissionPlanner'.static.ChooseMove("))
        self.assertIn("StopAutoplay", self.controller)
        self.assertNotIn("GetEnemyActionPoints(", self.reposition)

    def test_visible_mind_control_ow_veto_uses_original_ownership_evidence(self):
        """The native future reaction target cannot be selected by our score."""
        finder = function_body(self.combat, "HasVisibleReclaimableReactionTarget")
        score = function_body(self.combat, "ScoreSelfAction")
        for token in ("VisibleEnemies.Length > 64", "if (++Checked > 64)",
                      "IsVisibleHostile(", "IsReclaimableControlledSquadmate(",
                      "return true;"):
            self.assertIn(token, finder)
        self.assertIn("GuardOverwatchForKnownAlly(", score)
        self.assertIn("HasVisibleReclaimableReactionTarget(", score)
        self.assertIn("ScoreOverwatchDefense(", score)
        self.assertNotIn("GetEnemyActionPoints(", finder)
        self.assertNotIn("GetGroupMovePaths(", finder)

    def test_guarded_own_ap_and_ally_protection_do_not_depend_on_reaction_guess(self):
        """No unsupported rifle target, no converted ally, no special AP grant."""
        gather = function_body(self.reposition, "GatherForecasts")
        self.assertIn("Ability.OwnerStateObject.ObjectID != UnitState.ObjectID", gather)
        self.assertIn("IsVisibleHostile(", gather)
        self.assertNotIn("GetGroupMovePaths(", self.reposition)
        self.assertNotIn("GetAllUnits(", self.reposition)
        self.assertIn("IsReclaimableControlledSquadmate(", self.combat)
        self.assertIn("!UnitState.IsAbleToAct()", function_body(
            self.reposition, "CanForecastUnit"))
        self.assertIn("UnitState.NumActionPoints() < 2", function_body(
            self.reposition, "CanForecastUnit"))
        self.assertIn("RemainingPoints.Length == 0", gather)


if __name__ == "__main__":
    unittest.main()
