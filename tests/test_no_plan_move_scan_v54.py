"""#139: execute the actual goal tail, rejection gate and no-plan condition.

Native cache/visibility and the supplied final Overwatch score are fixtures.
These are bounded source-control-flow tests, not a native tactical simulation.
"""
from pathlib import Path
import re
from types import SimpleNamespace as NS
import unittest
from unittest.mock import Mock

from test_live_unit_stats import UCArray, expression, split_condition, translate_body
from test_ui_gating import function_body, braced_body
from uc_math import load_uc_function

ROOT = Path(__file__).resolve().parents[1]
CLASSES = ROOT / "AutoplayXCom2/Src/AutoplayXCom2/Classes"
MISSION = CLASSES / "APX_MissionPlanner.uc"
CONTROLLER = CLASSES / "APX_Controller.uc"


def compile_fragment(name, args, body, env):
    """Compile the selected real UC statements using a narrow fixture adapter."""
    body = body.replace("class'APX_FullIntel'.default.EnableFullIntel", "FullIntel")
    body = body.replace("class'APX_CombatPlanner'.static.", "Combat.")
    body = body.replace("class'XComGameState_BattleData'", "'battle'")
    body = body.replace("++NativePathRejected", "NativePathRejected += 1")
    body = body.replace("for (MoveStopIndex = 0; MoveStopIndex < MoveStopDiagnostics.Length; ++MoveStopIndex)",
                        "for MoveStopIndex in range(MoveStopDiagnostics.Length)")
    # UC string concatenation: @ inserts one space, $ does not.
    def concat(match):
        """Adapt only the diagnostic assignment, retaining real field values."""
        parts = re.split(r"\s*([@$])\s*", match[2])
        result = "str(" + expression(parts[0]) + ")"
        for op, value in zip(parts[1::2], parts[2::2]):
            result += (' + " " + ' if op == "@" else " + ") + "str(" + expression(value) + ")"
        return match[1] + result + ";"
    body = re.sub(r"(MoveDiagnostic\s*=\s*)([^;]*[@$][^;]*);", concat, body)
    namespace = dict(env, string=str, UCArray=UCArray)
    code = "def " + name + "(" + args + "):\n" + translate_body(body)
    exec(compile(code, name, "exec"), namespace)
    return namespace[name]


class NoPlanMoveScanTests(unittest.TestCase):
    """Test the actual relevant control flow on the LEAD-supplied scenario."""

    def setUp(self):
        """Load current source and a last able soldier with two known enemies."""
        self.mission = MISSION.read_text(encoding="utf-8-sig")
        self.controller = CONTROLLER.read_text(encoding="utf-8-sig")
        self.goal_body = function_body(self.mission, "FindGoal")
        self.move_body = function_body(self.mission, "ChooseMove")
        self.decision = function_body(self.controller, "MakeDecision")
        self.unit = NS(ObjectID=1, TileLocation=0, NumActionPoints=lambda: 2)
        self.known = UCArray([NS(ObjectID=2), NS(ObjectID=3)])
        self.enemies = {2: NS(TileLocation=20), 3: NS(TileLocation=25)}
        self.battle = NS(MapData=NS(ObjectiveLocation=12))
        self.env = dict(FullIntel=True,
                        XComGameState_BattleData=lambda x: x,
                        XComGameState_Unit=lambda x: x,
                        XCOMHISTORY=NS(GetSingleGameStateObjectForClass=lambda *_: self.battle,
                                       GetGameStateForObjectID=self.enemies.get),
                        XWORLD=NS(GetTileCoordinatesFromPosition=lambda x: x),
                        VSizeSq=lambda x: x*x, TileDistance=lambda a,b: abs(a-b),
                        Combat=NS(IsReclaimableControlledSquadmate=lambda *_: False),
                        ShouldPursueKnownEnemies=load_uc_function(MISSION, "ShouldPursueKnownEnemies"))
        self.env["ConsiderGoal"] = compile_fragment(
            "ConsiderGoal", "UnitState,CandidateTile,Priority,bCombat,Goal",
            function_body(self.mission, "ConsiderGoal"), self.env)

    def goal_tail(self, map_location):
        """Execute actual generic map-objective and pursuit branches."""
        self.battle.MapData.ObjectiveLocation = map_location
        body = self.goal_body[self.goal_body.index('if (Goal.bFound)\n        GoalSource = "mission_object";'):]
        body = body.replace("return Goal.bFound;", "return (Goal.bFound, GoalSource);")
        run = compile_fragment("GoalTail", "UnitState,VisibleEnemies,Goal,bSkipUnverifiedPlantMarker,GoalSource",
                               body, self.env)
        goal = NS(bFound=False, bCombat=False, Tile=None, Value=0)
        found, source = run(self.unit, self.known, goal, False, "none")
        return found, source, goal

    def stop_gate(self, visible=False, contacts=(), immediate=False, best=2.0, have=True, meaningful=0):
        """Run actual contact assignments and the real no-plan guard."""
        flags = self.decision[self.decision.index("bContactSearch = !bVisibleThreats"):
                              self.decision.index(";", self.decision.index("bCombatThreats = bVisibleThreats"))+1]
        update = re.search(r"bCombatThreats = bCombatThreats\s*\|\|\s*[^;]+;", self.decision)[0]
        update = update.replace("class'APX_MissionPlanner'.static.HasCombatThreats(UnitState)", "immediate")
        start = self.decision.index("if ((!bHavePlan || (BestScore <= 2.0")
        condition, _ = split_condition(self.decision[start:self.decision.index("{", start)])
        run = compile_fragment("StopGate",
            "bVisibleThreats,RecentContacts,immediate,BestScore,bHavePlan,MeaningfulActionsThisTurn",
            flags + update + "\nreturn " + condition + ";", self.env)
        return run(visible, UCArray(contacts), immediate, best, have, meaningful)

    def test_map_goal_precedes_known_enemy_but_pursuit_available_without_map_goal(self):
        """Two known live contacts need not be the destination selected by FindGoal."""
        found, source, goal = self.goal_tail(12)
        self.assertTrue(found)
        self.assertEqual(("map_objective", 12, False), (source, goal.Tile, goal.bCombat))
        found, source, goal = self.goal_tail(0)
        self.assertTrue(found)
        self.assertEqual(("known_enemy_pursuit", 20, True), (source, goal.Tile, goal.bCombat))
        found, source, goal = self.goal_tail(2)
        self.assertTrue(found)
        self.assertEqual(("known_enemy_pursuit", 20), (source, goal.Tile))

    def test_active_contact_cannot_reach_reported_stop(self):
        """Full intel alone is not immediate combat; remembered/visible contact is."""
        self.assertTrue(self.stop_gate())
        self.assertFalse(self.stop_gate(contacts=[NS(UnitID=2)]))
        self.assertFalse(self.stop_gate(visible=True))
        self.assertFalse(self.stop_gate(immediate=True))
        self.assertFalse(self.stop_gate(best=20))
        self.assertFalse(self.stop_gate(meaningful=1))

    def test_native_path_failure_is_counted_and_stop_remains_justified(self):
        """Scenario: last soldier, two AP, empty shot cache, no buildable route.

        Execute the actual chosen goal tail, native path failure gate and final
        no-route diagnostic, then the unchanged controller stop predicate.
        """
        available_shots = UCArray()
        self.assertEqual(0, available_shots.Length)
        self.assertEqual(2, self.unit.NumActionPoints())
        found, source, _ = self.goal_tail(0)
        self.assertTrue(found)
        self.assertEqual("known_enemy_pursuit", source)
        start = self.move_body.index("if (!UnitVisualizer.m_kReachableTilesCache.BuildPathToTile(Tile, CandidatePath)")
        end = self.move_body.index("bSafe = true;", start)
        gate = self.move_body[start:end]
        start = self.move_body.index('if (Path.Length < 2)\n    {\n        LaterRejected =')
        end = self.move_body.index("if (bInspectContact)", start)
        tail = self.move_body[start:end]
        tail = tail.replace("return false;", "return (false, MoveDiagnostic);")
        body = ("NativePathRejected = 0; EndpointRejected = 0; GainRejected = 0;"
                "UnsafePathRejected = 0; SampleCount = 1; bPrefixFound = false;"
                "for Tile in Tiles {\n" + gate + "\n}\n" + tail)
        native = Mock(return_value=False)
        visualizer = NS(m_kReachableTilesCache=NS(BuildPathToTile=native))
        run = compile_fragment("RouteFailure",
            "UnitVisualizer,Tiles,CandidatePath,Path,MoveDiagnostic", body, self.env)
        ok, summary = run(visualizer, [7], UCArray(), UCArray(),
                          "goal=" + source + " known=2 immediate=False")
        self.assertFalse(ok)
        native.assert_called_once()
        self.assertIn("reason=no_qualified_route", summary)
        self.assertIn("native_path_rejected=1", summary)
        self.assertIn("later_rejected=0", summary)
        self.assertTrue(self.stop_gate(best=2.0))

    def test_diagnostics_follow_actual_selection_and_only_emit_on_stop(self):
        """Source contract: no alternate query, no extra movement or fallback."""
        decision = self.decision
        start = decision.index("MissionMoveDiagnostic = ")
        end = decision.index("bCompareTimedObjective =", start)
        selection = decision[start:end]
        self.assertEqual(1, selection.count("ChooseContactSearchMove("))
        self.assertEqual(1, selection.count(".static.ChooseMove("))
        self.assertEqual(1, selection.count("CanUseMove("))
        self.assertIn('MissionMoveOutcome = "outscored";', selection)
        self.assertIn('MissionMoveOutcome = "controller_rejected";', selection)
        self.assertIn("MoveStopDiagnostics.Length < 16", selection)
        self.assertIn("++MoveStopOmitted", selection)
        stop = decision.index("if ((!bHavePlan || (BestScore <= 2.0")
        marker = decision.index('Marker("no_plan_move_scan"')
        self.assertLess(stop, marker)
        self.assertLess(marker, decision.index('StopWithStatus("No constructive action', marker))
        self.assertEqual(1, decision.count('Marker("no_plan_move_scan"'))
        self.assertIn('return false;', self.move_body[self.move_body.index("reason=no_qualified_route"):])
        self.assertNotIn("SubmitGameState(", self.move_body)


if __name__ == "__main__":
    unittest.main()
