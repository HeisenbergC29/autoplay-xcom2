"""#139: execute the actual goal tail, rejection gate and no-plan condition.

Native cache/visibility and the competing Overwatch score are fixtures. The
actual scan, path rejection, stop guard and recorder budget are linked.
These are bounded source-control-flow tests, not a native tactical simulation.
"""
from pathlib import Path
import re
from types import SimpleNamespace as NS
import unittest
from unittest.mock import Mock

from test_live_unit_stats import UCArray, expression, split_condition, translate_body
from test_ui_gating import function_body, braced_body
from test_recorder_terminal_limit_v52 import compile_lifecycle, History, uc_concat
from uc_math import load_uc_function

ROOT = Path(__file__).resolve().parents[1]
CLASSES = ROOT / "AutoplayXCom2/Src/AutoplayXCom2/Classes"
MISSION = CLASSES / "APX_MissionPlanner.uc"
CONTROLLER = CLASSES / "APX_Controller.uc"
REPOSITION = CLASSES / "APX_RepositionPlanner.uc"
RECORDER = CLASSES / "APX_MissionRecorder.uc"


def compile_fragment(name, args, body, env):
    """Compile the selected real UC statements using a narrow fixture adapter."""
    body = body.replace("class'APX_FullIntel'.default.EnableFullIntel", "FullIntel")
    body = body.replace("class'APX_CombatPlanner'.static.", "Combat.")
    body = body.replace("class'XComGameState_BattleData'", "'battle'")
    body = body.replace("class'APX_MissionPlanner'.static.", "Mission.")
    body = body.replace("class'APX_MissionPlanner'.default.", "MissionDefaults.")
    body = body.replace("++MoveStopOmitted", "MoveStopOmitted += 1")
    body = body.replace("class'APX_PlantInteractionKnowledge'.static.", "Plant.")
    body = body.replace("for (ActionIndex = 0; ActionIndex < Min(64, Cache.AvailableActions.Length); ++ActionIndex)",
                        "for ActionIndex in range(min(64, Cache.AvailableActions.Length))")
    body = re.sub(r"\belse\s+(?!if\b)", "if (__ELSE__) ", body)
    body = body.replace("++NativePathRejected", "NativePathRejected += 1")
    body = body.replace("for (MoveStopIndex = 0; MoveStopIndex < MoveStopDiagnostics.Length; ++MoveStopIndex)",
                        "for MoveStopIndex in range(MoveStopDiagnostics.Length)")
    # UC string concatenation: @ inserts one space, $ does not.
    def concat_expression(value):
        """Convert the exact emitted field order, not a reconstructed marker."""
        parts = re.split(r"\s*([@$])\s*", value)
        result = "str(" + expression(parts[0]) + ")"
        for op, part in zip(parts[1::2], parts[2::2]):
            result += (' + " " + ' if op == "@" else " + ") + "str(" + expression(part) + ")"
        return result

    body = re.sub(r'MoveStopDiagnostics.AddItem\((.*?)\);',
                  lambda m: 'MoveStopDiagnostics.AddItem(' + concat_expression(m[1]) + ');',
                  body, flags=re.S)
    body = re.sub(r'MissionRecorder.Marker\("no_plan_move_scan",\s*(.*?)\);',
                  lambda m: 'MissionRecorder.Marker("no_plan_move_scan",'
                  + concat_expression(m[1]) + ');', body, flags=re.S)
    def concat(match):
        """Adapt only the diagnostic assignment, retaining real field values."""
        return match[1] + concat_expression(match[2]) + ";"
    body = re.sub(r"(MoveDiagnostic\s*=\s*)([^;]*[@$][^;]*);", concat, body)
    namespace = dict(env, string=str, UCArray=UCArray)
    code = "def " + name + "(" + args + "):\n" + translate_body(body).replace("if __ELSE__:", "else:")
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
        self.reposition = REPOSITION.read_text(encoding="utf-8-sig")
        self.unit_reference = NS(ObjectID=1)
        self.unit = NS(ObjectID=1, TileLocation=0, NumActionPoints=lambda: 2,
                       GetReference=lambda: self.unit_reference)
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

    def x4_goal(self, status):
        """Run native/fallback resolution and the real successful FindGoal body."""
        body = function_body(self.mission, "FindBerserkerSabotageGoal")
        body = body.replace("class'APX_PlantInteractionKnowledge'.static.FindInteractionGoal(\n        UnitState, NativeGoalTile, NativeGoalReason, VerifiedPath)",
                            "ReadNative(UnitState, VerifiedPath)")
        body = body.replace("NativeGoalStatus = ReadNative(UnitState, VerifiedPath);",
                            "NativeGoalStatus, NativeGoalTile, NativeGoalReason = ReadNative(UnitState, VerifiedPath);")
        body = body.replace('GoalSource = "mission_marker_unverified:" $ NativeGoalReason;',
                            'GoalSource = "mission_marker_unverified:" + NativeGoalReason;')
        body = body.replace("return true;", "return (true, GoalTile, GoalSource, NativeGoalStatus);")
        body = body.replace("return false;", "return (false, GoalTile, GoalSource, NativeGoalStatus);")
        env = dict(self.env, ReadNative=lambda *_: (status, 45, "native_fixture"),
                   XWORLD=NS(GetTileCoordinatesFromPosition=lambda x:x, IsTileOutOfRange=lambda _:False))
        native = compile_fragment("X4Resolve", "UnitState,BattleData,GoalTile,GoalSource,NativeGoalStatus,VerifiedPath",
                                  body, env)
        found, tile, source, actual_status = native(self.unit, self.battle, 0, "", 0, UCArray())
        self.assertTrue(found)
        # Extract the selected branch after its real native resolver succeeded.
        start = self.goal_body.index('GoalSource = "x4_map_marker_unverified";')
        end = self.goal_body.index("return true;", start)+len("return true;")
        branch = self.goal_body[start:end].replace("return true;", "return GoalSource;")
        goal = NS()
        label = compile_fragment("X4Label", "SabotageNativeGoalStatus,SabotageGoalTile,SabotageGoalSource,Goal",
                                 branch, env)(actual_status, tile, source, goal)
        return label, goal

    def test_x4_native_and_unverified_fallback_labels(self):
        """A usable map marker is not a verified native plant anchor."""
        for status, expected, tile in ((1, "native_objective", 45),
                                       (0, "x4_map_marker_unverified", 12)):
            with self.subTest(status=status):
                label, goal = self.x4_goal(status)
                self.assertEqual(expected, label)
                self.assertEqual(tile, goal.Tile)
                self.assertTrue(goal.bBerserkerSabotageGoal)

    def rejected_forecast(self, actions):
        """Feed actual cache to GatherForecasts guards and the no-shot branch."""
        cache = NS(AvailableActions=UCArray(actions))
        def get_cache(reference, output):
            """Supply the native cache via its out parameter."""
            self.assertIs(reference, self.unit_reference)
            output.AvailableActions = cache.AvailableActions
            return True

        def blue_points(unit, points):
            """Supply native remaining AP after a blue move."""
            points.AddItem("standard")
            return True

        rules = NS(VisibilityMgr=object(), GetGameRulesCache_Unit=Mock(side_effect=get_cache))
        supports = Mock(return_value=False)
        env = dict(self.env, TACTICALRULES=rules, Min=min,
                   CanForecastUnit=lambda _:True, HasVisibleRuler=lambda _:False,
                   Mission=NS(ActionPointsAfterBlueMove=blue_points),
                   SupportsForecast=supports, XComGameState_Ability=lambda x:x)
        body = function_body(self.reposition, "GatherForecasts")
        # Run through the real unsupported-ability gate. The fixture has no
        # supported entry; reaching the later native-shot body is an error.
        body = body[body.index("Forecasts.Length = 0;"):body.index("WeaponState = Ability.GetSourceWeapon();")]
        body = body.replace("return;", "return OpeningShot;")
        body = body.replace("Forecasts.Length = 0;", "Cache = MakeCache();\nRemainingPoints = UCArray();\nForecasts.Length = 0;")
        env["MakeCache"] = NS
        env["XCOMHISTORY"] = NS(GetGameStateForObjectID=lambda _:NS())
        body += "\nReachedSupportedShot();\n}\nreturn OpeningShot;"
        env["ReachedSupportedShot"] = Mock(side_effect=AssertionError("Fixture reached supported shot"))
        gather = compile_fragment("Gather", "UnitState,VisibleEnemies,Forecasts", body, env)
        forecasts = UCArray()
        opening = gather(self.unit, self.known, forecasts)
        rules.GetGameRulesCache_Unit.assert_called_once()
        supports.assert_called_once()
        self.assertEqual(0, forecasts.Length)
        self.assertIsNone(opening)
        move = function_body(self.reposition, "ChooseMove")
        # Execute real zero-shot predicate and reason, with the outputs of
        # GatherForecasts rather than a separately invented no-shot flag.
        start = move.index("SupportedShots = Forecasts.Length;")
        end = move.index("Visualizer = XGUnit", start)
        fragment = move[start:end].replace("return false;", "return (false, ScanReason);")
        env["HasNearbySpitCapability"] = Mock(side_effect=AssertionError("No current or opening shot"))
        env["ReadNearbyFriendlyTiles"] = env["HasNearbySpitCapability"]
        env["ForecastScanStage"] = load_uc_function(REPOSITION, "ForecastScanStage")
        env["ForecastScanReason"] = compile_fragment("ScanReason", "SupportedShots,Endpoints,ImprovedShots,SafeRoutes,bSelected",
            function_body(self.reposition, "ForecastScanReason"), env)
        result = compile_fragment("NoShot", "UnitState,VisibleEnemies,Forecasts,OpeningShot,FriendTiles,SquadEnemies",
                                  fragment, env)(self.unit,self.known,forecasts,opening,UCArray(),UCArray())
        self.assertEqual((False, "no_supported_current_shot"), result)
        return result[0]

    def recorder(self, remaining):
        """Use actual recorder Emit, epoch gate and Marker at the real clamped cap."""
        history = History()
        logs = []
        uc = compile_lifecycle(dict(
            bStarted=True,bFinished=False,bLimitReported=False,bRecordingEpochInvalid=False,
            bEndPending=False,LastEndHistory=0,Sequence=100-remaining,MaxRecords=100,
            Decision=56,SessionID="fixture",HistoryCursor=10,RecordingStartHistory=10,
            LastObservedMissionHistory=10,RecordedHistory=history,XCOMHISTORY=history,
            RecordedStartStateIndex=2,RecordedBattleID=8,RecordedMissionType="Test",
            Clamp=lambda v,lo,hi:max(lo,min(hi,v)),Max=max,Safe=str,
            XComGameState_BattleData=lambda x:x,Join=lambda *xs:"".join(map(str,xs)),
            Log=logs.append,TurnAtHistory=lambda _:16))
        marker = function_body(RECORDER.read_text(encoding="utf-8-sig"),"Marker")
        marker = marker.replace("local int CurrentHistory;", "local int CurrentHistory;\nClock = \"\";")
        marker = re.sub(r"(Clock = )(.*?);",lambda m:m[1]+uc_concat(m[2])+";",marker,flags=re.S)
        marker = re.sub(r'Emit\("marker",\s*(.*?)\);',lambda m:'Emit("marker",'+uc_concat(m[1])+');',marker,flags=re.S)
        exec(compile("def Marker(Kind,Details):\n"+translate_body(marker),"Marker","exec"),uc)
        return NS(Marker=uc["Marker"]), logs, uc

    def emit_stop(self, recorder, diagnostic, best, have, visible=False):
        """Execute stop condition, actual stop body and real stop-marker call."""
        if not self.stop_gate(visible=visible,best=best,have=have):
            return False
        start = self.decision.index("if (MeaningfulActionsThisTurn == 0)", self.decision.index("if ((!bHavePlan"))
        end = self.decision.index("return;",start)+len("return;")
        body = self.decision[start:end]+"\n}"
        stop_body = function_body(self.controller,"StopAutoplay")
        i = stop_body.index("if (MissionRecorder != none)")
        j = stop_body.index(";",i)+1
        # All unrelated UI/reset side effects are outside this fixture.
        stop = compile_fragment("StopAutoplay","Reason",stop_body[i:j],dict(MissionRecorder=recorder))
        status = function_body(self.controller,"StopWithStatus")
        with_status = compile_fragment("StopWithStatus","Reason,DisplayStatus",status,dict(StopAutoplay=stop))
        env = dict(self.env, StopWithStatus=with_status, StatusNoPlan="NoPlan", MissionRecorder=recorder)
        run = compile_fragment("EmitStop","MeaningfulActionsThisTurn,FocusBattle,MoveStopDiagnostics,MoveStopOmitted,bVisibleThreats,RecentContacts,bCombatThreats,BestScore",
                               body,env)
        run(0,None,UCArray([diagnostic]),0,visible,UCArray(),False,best)
        return True

    def route_failure(self):
        """Execute actual native path failure gate and the final diagnostic."""
        found, source, _ = self.goal_tail(0)
        self.assertTrue(found)
        self.assertEqual("known_enemy_pursuit", source)
        start = self.move_body.index("if (!UnitVisualizer.m_kReachableTilesCache.BuildPathToTile(Tile, CandidatePath)")
        end = self.move_body.index("bSafe = true;", start)
        gate = self.move_body[start:end]
        start = self.move_body.index('if (Path.Length < 2)\n    {\n        LaterRejected =')
        end = self.move_body.index("if (bInspectContact)", start)
        tail = self.move_body[start:end].replace("return false;", "return (false, MoveDiagnostic);")
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
        return ok,summary

    def selected_stop_inputs(self, recorder, proposed, moved, summary):
        """Pass both real rejection results through the controller's existing gates."""
        start = self.decision.index("if (ChooseCompetitiveReposition(UnitState, BestScore,")
        end = self.decision.index("CandidatePath.Length = 0;", start)
        attack = self.decision[start:end]
        start = self.decision.index("if (bCandidateMove\n            && TraceCandidateMove",end)
        end = self.decision.index("bCompareTimedObjective =",start)
        move = self.decision[start:end]
        env = dict(self.env, MissionRecorder=recorder,
                   ChooseCompetitiveReposition=Mock(return_value=proposed),
                   TraceCandidateMove=Mock(side_effect=AssertionError("Rejected candidate traced")),
                   CanUseMove=Mock(side_effect=AssertionError("Rejected candidate accepted")))
        body = ("BestScore = 2.0; bHavePlan = true; Score = -10000.0;"
                "CandidatePath = UCArray(); RemainingTempoCoverChecks = 1;"
                "MoveStopDiagnostics = UCArray(); MoveStopOmitted = 0;"
                'MissionMovePlanner = "mission"; MissionMoveOutcome = "not_proposed";'
                + attack + move
                + "return (BestScore,bHavePlan,MoveStopDiagnostics);")
        best, have, diagnostics = compile_fragment("Selection",
            "UnitState,bCandidateMove,MissionMoveDiagnostic",body,env)(self.unit,moved,summary)
        env["ChooseCompetitiveReposition"].assert_called_once()
        env["TraceCandidateMove"].assert_not_called()
        env["CanUseMove"].assert_not_called()
        self.assertEqual(1,len(diagnostics))
        return best,have,diagnostics[0]

    def test_native_path_failure_is_counted_and_stop_remains_justified(self):
        """Join real forecast and path rejection to stop and actual recorder output."""
        self.assertEqual(2,self.unit.NumActionPoints())
        actions = [NS(bInputTriggered=True,bFreeAim=False,AvailableCode="AA_Success",
                      AbilityObjectRef=NS(ObjectID=99))]
        proposed = self.rejected_forecast(actions)
        moved, summary = self.route_failure()
        # The supplied existing Overwatch is the only competing plan.
        recorder,logs,_ = self.recorder(5)
        best,have,diagnostic = self.selected_stop_inputs(recorder,proposed,moved,summary)
        self.assertEqual((2.0,True),(best,have))
        self.assertTrue(self.emit_stop(recorder,diagnostic,best,have))
        self.assertIn("|kind=autoplay_stop|",logs[0])
        self.assertIn("|kind=no_plan_move_scan|",logs[1])
        self.assertIn("unit=1 ap=2 branch=mission outcome=not_proposed",logs[1])
        self.assertIn("goal=known_enemy_pursuit",logs[1])
        self.assertIn("native_path_rejected=1",logs[1])
        self.assertFalse(self.emit_stop(recorder,summary,20,True))
        self.assertEqual(2,len(logs))

    def test_one_remaining_record_preserves_stop_boundary(self):
        """Actual Emit clamp grants the last ordinary slot to autoplay_stop."""
        recorder,logs,uc = self.recorder(1)
        self.assertTrue(self.emit_stop(recorder,"reason=no_goal",2,True))
        self.assertIn("|seq=100|event=marker|",logs[0])
        self.assertIn("|kind=autoplay_stop|",logs[0])
        self.assertIn("|history=10|turn=16",logs[0])
        self.assertIn("|event=limit|",logs[1])
        self.assertTrue(uc["bLimitReported"])
        self.assertFalse(any("no_plan_move_scan" in x for x in logs))

    def test_diagnostic_locals_declared_and_early_reason_initialized(self):
        """Guard declarations not exercised by the limited fragment adapter."""
        declarations = self.move_body[:self.move_body.index("Path.Length = 0;")]
        for name in ("GoalSource", "EndpointRejected", "GainRejected",
                     "NativePathRejected", "UnsafePathRejected", "LaterRejected",
                     "bPrefixFound"):
            self.assertRegex(declarations, r"\blocal\s+\w+\s+[^;]*\b" + name + r"\b[^;]*;")
        self.assertLess(self.move_body.index('MoveDiagnostic = "reason=no_legal_move";'),
                        self.move_body.index("if (!HasLegalMove(UnitState))"))

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
        self.assertLess(decision.index('StopWithStatus("No constructive action', stop), marker)
        self.assertEqual(1, decision.count('Marker("no_plan_move_scan"'))
        self.assertIn('return false;', self.move_body[self.move_body.index("reason=no_qualified_route"):])
        self.assertNotIn("SubmitGameState(", self.move_body)


if __name__ == "__main__":
    unittest.main()
