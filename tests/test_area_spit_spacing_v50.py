"""#115 — PoisonSpit capability, native move-and-shot and formation regressions.

Pure scores execute the UnrealScript source with uc_math. Source contracts
and a synthetic log E2E are not a compiler or an actual WOTC gameplay test.
"""
from pathlib import Path
import unittest

from uc_math import load_uc_function
from test_ui_gating import function_body
from test_revealed_shooter_tactics_e2e_v45 import run_synthetic_bundle

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "AutoplayXCom2/Src/AutoplayXCom2/Classes"
REPOSITION = SRC / "APX_RepositionPlanner.uc"
MISSION = SRC / "APX_MissionPlanner.uc"
CONTROLLER = SRC / "APX_Controller.uc"


class AreaSpitNumericPolicy(unittest.TestCase):
    """Compare a real-shot plan with the number of potential shared AoE victims."""

    @classmethod
    def setUpClass(cls):
        """Load both anti-Spit scores from production UnrealScript."""
        cls.shot = staticmethod(load_uc_function(REPOSITION, "ScoreAreaShotMove"))
        cls.opening = staticmethod(load_uc_function(REPOSITION, "ScoreOpeningAreaMove"))

    def test_reducing_three_shared_targets_can_beat_moderate_native_shot(self):
        """A native 70-point shot remains plausible after a safe blue step."""
        score = self.shot(70, 68, 71, 69, 3, 2, 25, 22, 3, 2)
        self.assertAlmostEqual(80.4, score)
        self.assertGreater(score, 70)
        self.assertGreater(score, 22)

    def test_strong_legal_immediate_attack_still_wins(self):
        """High-value 82%-chance kill must not be displaced by geometry alone."""
        self.assertLess(self.shot(112, 110, 82, 80, 3, 2, 25, 20, 3, 2), -9999)
        self.assertLess(self.shot(70, 55, 71, 55, 3, 2, 25, 20, 3, 2), -9999)
        self.assertLess(self.shot(70, 68, 71, 69, 3, 3, 25, 20, 3, 2), -9999)
        self.assertLess(self.shot(70, 68, 71, 69, 3, 2, 25, 26, 3, 2), -9999)
        self.assertLess(self.shot(70, 68, 71, 69, 3, 2, 25, 20, 3, 1), -9999)
        self.assertLess(self.shot(70, 68, 51, 49, 3, 2, 25, 20, 3, 2), -9999)

    def test_squad_line_after_move_can_compete_without_invented_now_shot(self):
        """A low capped score cannot claim a predicted future native hit."""
        score = self.opening(3, 2, 28, 25, 5, 2)
        self.assertEqual(30.0, score)
        self.assertLess(score, 50.0)
        self.assertLess(self.opening(3, 3, 28, 25, 5, 2), -9999)
        self.assertLess(self.opening(3, 2, 28, 30, 5, 2), -9999)
        self.assertLess(self.opening(3, 2, 28, 25, 5, 1), -9999)


class AreaSpitSourceContracts(unittest.TestCase):
    """Only bounded current native state may back a defensive move."""

    @classmethod
    def setUpClass(cls):
        """Read actual planner/controller code for path and target provenance."""
        cls.source = REPOSITION.read_text(encoding="utf-8-sig")
        cls.controller = CONTROLLER.read_text(encoding="utf-8-sig")
        cls.mission = MISSION.read_text(encoding="utf-8-sig")

    def test_installed_spit_capability_and_squad_geometry_not_enemy_intent(self):
        """Four-tile diameter-aware geometry counts current living squadmates."""
        spit = function_body(self.source, "HasNearbySpitCapability")
        friends = function_body(self.source, "ReadNearbyFriendlyTiles")
        choose = function_body(self.source, "ChooseMove")
        for token in ("Enemy.FindAbility('PoisonSpit')", "Enemy.IsAlive()",
                      "KnownEnemies.Length > 64", "TileDistance("):
            self.assertIn(token, spit)
        for token in ("Count > 24", "FriendTiles.Length >= 12", "Friend.IsAlive()",
                      "Friend.IsFriendlyUnit("):
            if token == "Friend.IsFriendlyUnit(":
                self.assertIn("Soldier.IsFriendlyUnit(Friend)", friends)
            else:
                self.assertIn(token, friends)
        self.assertIn("FMax(4.0, class'APX_MissionPlanner'.default.SquadAreaRiskRadiusTiles)", choose)
        self.assertIn("WorstSharedAreaTargets(", choose)
        self.assertIn("SharedAfter < SharedBefore", choose)
        for forbidden in ("GetEnemyActionPoints(", "SYNC_RAND(", "GetNextDestination("):
            self.assertNotIn(forbidden, self.source)

    def test_current_shot_and_future_opened_line_both_preserve_native_ap(self):
        """Remote LOS is a hypothesis; actual attack remains native in controller."""
        retained = function_body(self.source, "ProjectSafeAreaShotAtTile")
        opening = function_body(self.source, "OpensSquadContactLane")
        choose = function_body(self.source, "ChooseMove")
        for part in (retained, opening):
            self.assertIn("GetVisibilityInfoFromRemoteLocation(", part)
            self.assertIn("ValidatePrimaryTargetOptionFromRemoteLocation(", part)
            self.assertIn("EvaluateConditions(", part)
        self.assertIn("OpeningShot == none", choose)
        self.assertIn("Enemy.IsMindControlled()", opening)
        self.assertIn("GetImmediateThreats(UnitState, SquadEnemies)", choose)
        self.assertIn("ScoreOpeningAreaMove(", choose)
        self.assertIn("ScoreAreaShotMove(", choose)
        self.assertIn("AreaProbes < 12", choose)
        self.assertIn("ForecastBluePathSafe(", choose)
        self.assertIn("++SafeRoutes", choose)
        self.assertIn('"area_spit_reposition_retains_shot"', choose)
        self.assertIn('"area_spit_reposition_opens_squad_lane"', choose)
        self.assertIn("if (ChooseCompetitiveReposition(", function_body(self.controller, "MakeDecision"))
        self.assertIn("GameStateMoveUnitSingle(", function_body(self.controller, "MakeDecision"))

    def test_opened_lane_requires_a_real_no_targets_action(self):
        """Rulers, missing caches and blocked abilities cannot appear to be usable shots."""
        gather = function_body(self.source, "GatherForecasts")
        gates = ('OpeningShot = none;', 'HasVisibleRuler(VisibleEnemies)',
                 'ActionPointsAfterBlueMove(UnitState, RemainingPoints)',
                 'GetGameRulesCache_Unit(', "Candidate.AvailableCode != 'AA_NoTargets'",
                 'Ability.OwnerStateObject.ObjectID != UnitState.ObjectID',
                 'CanAttackWithActionPoints(Ability, UnitState, RemainingPoints)',
                 "if (Candidate.AvailableCode == 'AA_NoTargets')",
                 'WeaponState.Ammo > 0', 'OpeningShot = Ability;')
        offsets = [gather.index(gate) for gate in gates]
        self.assertEqual(sorted(offsets), offsets)
        self.assertIn("Candidate.AvailableCode != 'AA_Success'", gather)
        choose = function_body(self.source, "ChooseMove")
        self.assertIn("GatherForecasts(UnitState, VisibleEnemies, Forecasts, OpeningShot)", choose)
        self.assertIn("OpensSquadContactLane(UnitState, Tile, OpeningShot, SquadEnemies)", choose)

    def test_guard_against_unknown_path_and_do_not_force_movement(self):
        """Every scored proposed route is checked by the original complete-path gate."""
        choose = function_body(self.source, "ChooseMove")
        self.assertLess(choose.index("if (Value <= -1000.0)"),
                        choose.index("BuildPathToTile("))
        self.assertLess(choose.index("BuildPathToTile("),
                        choose.index("ForecastBluePathSafe("))
        self.assertLess(choose.index("ForecastBluePathSafe("),
                        choose.index("++SafeRoutes;"))
        self.assertIn("bSelected = Path.Length >= 2 && Score > 0.0", choose)
        self.assertIn("if (CandidateRisk > CurrentRisk)", choose)
        self.assertIn("if (!CanForecastUnit(UnitState))", choose)
        self.assertIn("if (Forecasts.Length == 0 && (!bAreaThreat", choose)


class AreaSpitLogEndToEnd(unittest.TestCase):
    """Verify source/destination and post-move shot provenance in synthetic CLI."""

    def test_formation_reposition_and_existing_shot_can_win_different_decisions(self):
        """Synthetic chosen actions do not prove that poison was actually avoided."""
        rows = [
            (0, "start|mission=ChallengeAbductionGasStation|revision=mission-report-v50"),
            (1, "unit|id=63468|scope=friendly|ap=2|x=20|y=15|z=1"),
            (1, "marker|kind=offensive_reposition_scan|details=unit=63468"
             " reason=area_spit_reposition_retains_shot supported_native_shots=1"
             " material_previews=2 safe_native_paths=1 proposed=True"
             " score=80.4 current_best=70 future_native_shot=unverified"),
            (1, "chosen|kind=move|unit=63468|score=80.4|ap_before=2"
             "|path_tiles=4|x=24|y=18|z=1|accepted=True"
             "|move_planner=offensive_reposition"),
            (2, "unit|id=63468|scope=friendly|ap=1|x=24|y=18|z=1"),
            (2, "chosen|kind=action|unit=63468|ability=StandardShot|target=63501"
             "|score=65|accepted=True|chance=69"),
            (3, "marker|kind=offensive_reposition_scan|details=unit=63474"
             " reason=outscored_by_current_squad_action proposed=True"
             " score=90 current_best=112 future_native_shot=unverified"),
            (3, "chosen|kind=action|unit=63474|ability=StandardShot|target=63501"
             "|score=112|accepted=True|chance=82"),
            (4, "end|reason=tactical_game_ended|outcome=loss|history=99|history_pending=0"),
        ]
        data = run_synthetic_bundle(("formation", rows))
        self.assertEqual([], data["malformed_records"])
        session, = data["sessions"]
        chosen = [r for r in session["records"] if r["event"] == "chosen"]
        self.assertEqual(["move", "action", "action"], [r["kind"] for r in chosen])
        self.assertEqual((63468, 2), (chosen[0]["unit"], chosen[0]["ap_before"]))
        self.assertEqual(63468, chosen[1]["unit"])
        self.assertEqual("offensive_reposition", chosen[0]["move_planner"])
        reasons = [r.get("details", "") for r in session["records"]
                   if r["event"] == "marker"]
        self.assertTrue(any("area_spit_reposition_retains_shot" in x for x in reasons))
        self.assertTrue(any("outscored_by_current_squad_action" in x for x in reasons))


if __name__ == "__main__":
    unittest.main()
