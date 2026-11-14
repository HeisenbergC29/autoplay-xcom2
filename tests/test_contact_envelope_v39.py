"""Contact-envelope v39: bounded read-only native-state policy.

Pure numeric helpers are executed from UnrealScript source via uc_math.
Other tests are source/API contracts, not a Windows WOTC compilation or
an in-game proof of visibility/ambush prediction.
"""
from pathlib import Path
import os
import re
import unittest

from uc_math import load_uc_function
from test_ui_gating import CHECKS, function_body

ROOT = Path(__file__).resolve().parents[1]
CLASSES = ROOT / "AutoplayXCom2/Src/AutoplayXCom2/Classes"
CONTACT = CLASSES / "APX_ContactEnvelope.uc"
PATROL = CLASSES / "APX_PatrolKnowledge.uc"
CONTROLLER = CLASSES / "APX_Controller.uc"
MISSION = CLASSES / "APX_MissionPlanner.uc"
CONCEALMENT = CLASSES / "APX_ConcealmentPlanner.uc"
INI = ROOT / "AutoplayXCom2/Config/XComAutoplayXCom2.ini"


class ContactEnvelopeNumericContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.clock = staticmethod(load_uc_function(PATROL, "StoredWaypointAge"))
        cls.detect = staticmethod(load_uc_function(CONTACT, "ConcealedContactPossible"))
        cls.budget = staticmethod(load_uc_function(CONTACT, "SnapshotBudgetsValid"))
        cls.combine = staticmethod(load_uc_function(CONTACT, "CombineRouteStatus"))

    def test_native_ai_clock_not_local_xcom_turn(self):
        self.assertEqual(self.clock(8, 8), 0)
        self.assertEqual(self.clock(8, 7), 1)
        self.assertEqual(self.clock(8, 6), 2)
        for ai, last in ((8, 5), (8, -100), (8, 9), (0, 0), (-1, -1)):
            with self.subTest(ai=ai, last=last):
                self.assertEqual(self.clock(ai, last), -1)

    def test_stationary_cover_is_not_assigned_to_traversing_soldier(self):
        # Native unit-concealment rule: a moving detector requires a clear
        # directional cover angle; a moving concealed soldier does not.
        self.assertFalse(self.detect(True, True, True, 100.0, 50.0, False))
        self.assertTrue(self.detect(True, False, True, 100.0, 50.0, False))
        self.assertTrue(self.detect(True, False, False, 5000.0, 50.0, True))
        self.assertFalse(self.detect(False, False, False, 100.0, 50.0, True))
        self.assertFalse(self.detect(True, False, False, 5000.0, 50.0, False))

    def test_threat_or_uncertainty_in_middle_is_not_erased_by_clear_endpoint(self):
        status = 0
        for sample in (0, 1, 0):
            status = self.combine(status, sample)
        self.assertEqual(status, 1)
        status = 0
        for sample in (0, -1, 0):
            status = self.combine(status, sample)
        self.assertEqual(status, -1)
        self.assertEqual(self.combine(0, 0), 0)
        self.assertEqual(self.combine(-1, 1), 1)

    def test_empty_budget_cannot_be_complete(self):
        self.assertTrue(self.budget(32, 128, 64, 128, 512))
        for values in ((0, 128, 64, 128, 512),
                       (32, 0, 64, 128, 512),
                       (32, 128, 0, 128, 512),
                       (32, 128, 64, 0, 512),
                       (32, 128, 64, 128, 0)):
            self.assertFalse(self.budget(*values))


class ContactEnvelopeSourceContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contact = CONTACT.read_text(encoding="utf-8-sig")
        cls.patrol = PATROL.read_text(encoding="utf-8-sig")
        cls.controller = CONTROLLER.read_text(encoding="utf-8-sig")
        cls.mission = MISSION.read_text(encoding="utf-8-sig")

    def test_one_snapshot_and_shared_budgets_across_units(self):
        make = function_body(self.controller, "MakeDecision")
        self.assertIn("if (!bContactSnapshotReady)", make)
        self.assertIn("bContactSnapshotReady = true;", make)
        self.assertIn("BuildSnapshot(", make)
        for field in ("RemainingContactGroups", "RemainingContactMembers",
                      "RemainingContactDetectors", "RemainingContactTiles",
                      "RemainingContactLOS", "ContactSnapshotUnits",
                      "ContactSnapshotInteractives"):
            self.assertIn(field, make)
        self.assertIn("RemainingContactDetectors, RemainingContactTiles, RemainingContactLOS", make)
        for field in ("MaxGroups=32", "MaxMembers=128", "MaxDetectors=64",
                      "MaxTiles=128", "MaxLOS=512"):
            self.assertIn(field, INI.read_text(encoding="utf-8-sig"))

    def test_stock_patrol_clock_and_freshness_not_guessing_next_ai_choice(self):
        evidence = function_body(self.patrol, "StoredPatrolEvidence")
        for key in ("PatrolGroupList.Find('ObjectID', Group.ObjectID)",
                    "AIData.StatsData.TurnCount",
                    "Group.TurnCountForLastDestination",
                    "GetCurrentPatrolWaypoint(",
                    "Group.CurrentTargetLocation",
                    "patrol_waypoint_reached",
                    "patrol_ai_clock_stale_or_unknown"):
            self.assertIn(key, evidence)
        self.assertNotIn("PlayerTurnCount", evidence)
        for forbidden in ("ComputeGroupPath(", "GetGroupMovePaths(",
                          "ShouldMoveToIntercept(", "GetAllConnectedNodes(",
                          "GetGroupInfo("):
            self.assertNotIn(forbidden, CHECKS.without_comments(self.patrol))

    def test_route_uses_current_observed_native_los_and_native_detection(self):
        route = function_body(self.contact, "AssessRoute")
        for term in ("HorizonAITurns > 0", "future_patrol_route_unselected",
                     "if (!bSnapshotComplete", "for (Step = 0; Step < Path.Length",
                     "--RemainingTiles;", "--RemainingDetectors;", "--RemainingLOS;",
                     "UnitBreaksConcealment(Detector)", "GetConcealmentDetectionDistance(Detector)",
                     "DoesUnitBreaksConcealmentIgnoringDistance",
                     "CanSeeTileToTile(Detector.TileLocation, Tile, Visibility)",
                     "native_peek_unverified", "GetPathPointsFromPath",
                     "destructive_traversal", "interactive_detector"):
            self.assertIn(term, route)
        self.assertIn("GetAllVisibleObjectsForPlayer(", self.contact)
        self.assertIn("GetKnownEnemies(", self.contact)
        for forbidden in ("ModifyStateObject(", "SubmitGameState(",
                          "CreateNewGameState(", "GetTotalScore(", "Rand(", "FRand(",
                          "SetCurrentHistoryIndex("):
            self.assertNotIn(forbidden, CHECKS.without_comments(self.contact))

    def test_real_mission_planner_consumer_not_only_recorder(self):
        choose = function_body(self.mission, "ChooseMove")
        self.assertIn("bInspectContact = !bCoverUrgent", choose)
        self.assertIn("!bCombatGoal && !Goal.bBerserkerSabotageGoal", choose)
        self.assertGreaterEqual(choose.count("APX_ContactEnvelope'.static.AssessRoute("), 2)
        self.assertIn("PathStatusPenalty(ContactStatus)", choose)
        self.assertIn("RiskyRoute = Path;", choose)
        self.assertIn("CandidateScore -= class'APX_ContactEnvelope'.static.PathStatusPenalty(", choose)
        self.assertIn("BuildPathToTile(Tile, CandidatePath)", choose)
        self.assertIn("HasBlockingHazard(", choose)
        self.assertIn("IsSupportedAdvanceStep(", choose)
        self.assertIn("MoveOpportunityPenalty(", choose)

    def test_fullintel_false_is_not_upgraded_and_unknown_is_not_clear(self):
        build = function_body(self.contact, "BuildSnapshot")
        self.assertIn("!class'APX_FullIntel'.default.EnableFullIntel", build)
        self.assertIn('Reason = "limited_visibility";', build)
        self.assertIn('Reason = "group_budget";', build)
        self.assertIn('Reason = "detector_snapshot_truncated";', build)
        route = function_body(self.contact, "AssessRoute")
        self.assertIn('Reason = "decision_budget";', route)
        self.assertIn("return -1;", route)
        self.assertIn('Reason = "clear_current_snapshot_only";', route)
        self.assertIn("if (Status == 0)", route)


@unittest.skipUnless(os.environ.get("APX_SDK_SOURCE_ROOT"),
                     "Private WOTC SDK sources not available")
class ContactEnvelopeSDKContracts(unittest.TestCase):
    def test_stock_nonmutating_fields_and_native_detection(self):
        root = CHECKS.find_sdk_root(Path(os.environ["APX_SDK_SOURCE_ROOT"]))
        group = (root / "XComGame/Classes/XComGameState_AIGroup.uc").read_text(encoding="utf-8-sig")
        ai = (root / "XComGame/Classes/XComGameState_AIPlayerData.uc").read_text(encoding="utf-8-sig")
        unit = (root / "XComGame/Classes/XComGameState_Unit.uc").read_text(encoding="utf-8-sig")
        for term in ("CurrentTargetLocation", "TurnCountForLastDestination",
                     "m_arrMembers", "DESTINATION_REACHED_SIZE_SQ"):
            self.assertIn(term, group)
        for term in ("var int TurnCount;", "var array<StateObjectReference> GroupList, PatrolGroupList",
                     "m_iPlayerObjectID", "StatsData"):
            self.assertIn(term, ai)
        for term in ("GetConcealmentDetectionDistance(",
                     "UnitBreaksConcealment(", "DoesUnitBreaksConcealmentIgnoringDistance("):
            self.assertIn(term, unit)


if __name__ == "__main__":
    unittest.main()
