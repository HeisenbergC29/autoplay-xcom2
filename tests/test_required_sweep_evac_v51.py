"""#130: exercise the production evacuation policy on mocked native snapshots.

The limited UC adapter runs the real policy and evacuation branches, not
UnrealScript bytecode or pathfinding. The ZIP/CLI test exercises the analyzer
on synthetic observations. Actual Kismet execution and EVAC require WOTC.
"""
import os
from pathlib import Path
import re
from types import SimpleNamespace as NS
import unittest

from test_live_unit_stats import UCArray, translate_body
from test_revealed_shooter_tactics_e2e_v45 import run_synthetic_bundle
from test_ui_gating import CHECKS, function_body, braced_body

ROOT = Path(__file__).resolve().parents[1]
CLASSES = ROOT / "AutoplayXCom2/Src/AutoplayXCom2/Classes"
MISSION = CLASSES / "APX_MissionPlanner.uc"
CONTROLLER = CLASSES / "APX_Controller.uc"


def compile_gate(source, environment):
    """Adapt only the SDK-dependent syntax of the actual five policy methods."""
    namespace = dict(environment)
    specs = (
        ("HasPendingRequiredCommanderSweep", "BattleData"),
        ("SquadEvacuationReason", "BattleData"),
        ("IsRescueEvacuation", "UnitState"),
        ("IsRequiredSweepEvacuationBlocked", "UnitState"),
        ("ShouldEvacuate", "UnitState"),
    )
    for name, args in specs:
        body = function_body(source, name)
        body = body.replace(
            "for (Index = 0; Index < BattleData.MapData.ActiveMission.MissionObjectives.Length; ++Index)",
            "for Index in range(BattleData.MapData.ActiveMission.MissionObjectives.Length)")
        body = body.replace(
            "foreach " + chr(96) + "XCOMHISTORY.IterateByClassType(class'XComGameState_Unit', CarriedUnit)",
            "foreach CarriedUnits(CarriedUnit)")
        body = body.replace("class'X2Ability_CarryUnit'.default.CarryUnitEffectName", "CarryName")
        body = body.replace("class'X2AbilityTemplateManager'.default.BeingCarriedEffectName", "CarriedName")
        body = body.replace("class'XComGameState_BattleData'", "'XComGameState_BattleData'")
        code = f"def {name}({args}):\n" + translate_body(body)
        exec(compile(code, f"{MISSION.name}:{name}", "exec"), namespace)
    return namespace


def compile_evac_branches(source, namespace):
    """Execute the actual FindGoal and ChooseInteraction evacuation branches.

    The surrounding native goal search, rules cache and candidate scoring
    are outside this adapter. A false result means this branch did not select
    evacuation; it does not simulate the fallback chosen by WOTC.
    """
    goal = function_body(source, "FindGoal")
    goal_match = re.search(r"if\s*\(EvacZone != none && ShouldEvacuate\(UnitState\)\)\s*\{", goal)
    if goal_match is None:
        raise AssertionError("Missing real evacuation movement branch")
    goal_branch = goal[goal_match.start():goal_match.end()] + braced_body(
        goal, goal_match.end() - 1) + "}\nreturn false;"
    code = "def EvacGoalBranch(UnitState, EvacZone, Goal):\n" + translate_body(goal_branch)
    exec(compile(code, f"{MISSION.name}:FindGoal.Evac", "exec"), namespace)

    interaction = function_body(source, "ChooseInteraction")
    match = re.search(r"if\s*\(AbilityName == 'Evac'\)\s*\{", interaction)
    if match is None:
        raise AssertionError("Missing real evacuation interaction branch")
    branch = interaction[match.start():match.end()] + braced_body(
        interaction, match.end() - 1) + "}"
    branch = branch.replace("Candidate.AvailableTargets.Length > 0 ? 0 : INDEX_NONE",
                            "0 if Candidate.AvailableTargets.Length > 0 else INDEX_NONE")
    body = "for Candidate in Candidates {\n" + branch + "\n}\nreturn false;"
    code = "def EvacActionBranch(UnitState, AbilityName, Candidates):\n" + translate_body(body)
    exec(compile(code, f"{MISSION.name}:ChooseInteraction.Evac", "exec"), namespace)


def objective(name, completed=False, strategy=False, tactical=False):
    """Represent the native mission definition fields, not a UI objective row."""
    return NS(ObjectiveName=name, bCompleted=completed,
              bIsStrategyObjective=strategy, bIsTacticalObjective=tactical)


def soldier(object_id=410, civilian=False, team="XCom", carrying=False,
            carrier_id=None, objective_unit=False):
    """Supply only the native rescue API used by this policy."""
    effect = None if carrier_id is None else NS(
        ApplyEffectParameters=NS(SourceStateObjectRef=NS(ObjectID=carrier_id)))
    return NS(ObjectID=object_id, objective=objective_unit,
              IsCivilian=lambda: civilian, GetTeam=lambda: team,
              IsUnitAffectedByEffectName=lambda name: carrying and name == "carry",
              GetUnitAffectedByEffectState=lambda name: effect if name == "carried" else None)


class RequiredSweepEvacTests(unittest.TestCase):
    """Reproduce the v50 failure sequence through the actual policy code."""

    def setUp(self):
        """Install stock-shaped battle/units and compile source, not a policy copy."""
        self.source = MISSION.read_text(encoding="utf-8-sig")
        self.commander = objective("KillCommander", strategy=True)
        self.sweep = objective("Sweep", tactical=True)
        self.goals = UCArray([self.commander, self.sweep])
        self.battle = NS(bMissionAborted=False, MapData=NS(
            ActiveMission=NS(sType="NeutralizeFieldCommander", MissionObjectives=self.goals)))
        self.battle.AllStrategyObjectivesCompleted = lambda: all(
            g.bCompleted for g in self.goals if g.bIsStrategyObjective)
        self.carried = []
        self.unit = soldier()
        self.history = NS(GetSingleGameStateObjectForClass=lambda *_: self.battle)
        self.uc = compile_gate(self.source, dict(
            XCOMHISTORY=self.history, XComGameState_BattleData=lambda obj: obj,
            eTeam_XCom="XCom", CarryName="carry", CarriedName="carried",
            CarriedUnits=self.carried, HasObjectiveInfo=lambda unit: unit.objective,
            INDEX_NONE=-1))
        compile_evac_branches(self.source, self.uc)

    def test_verified_sweep_veto_only_for_current_required_commander_sweep(self):
        """Identical native flags in different missions do not mean identical victory rules."""
        pending = self.uc["HasPendingRequiredCommanderSweep"]
        dispatch = self.uc["IsRequiredSweepEvacuationBlocked"]
        self.assertTrue(pending(self.battle))
        self.assertTrue(dispatch(self.unit))
        self.assertFalse(dispatch(soldier(civilian=True)))
        self.carried[:] = [soldier(420, carrier_id=410, objective_unit=True)]
        self.assertFalse(dispatch(soldier(carrying=True)))
        for mission_type in ("Sabotage", "SabotageTransmitter", "OtherModMission", ""):
            self.battle.MapData.ActiveMission.sType = mission_type
            self.assertFalse(pending(self.battle))
            self.assertFalse(dispatch(self.unit))
        self.battle.MapData.ActiveMission.sType = "NeutralizeFieldCommander"
        self.sweep.bIsTacticalObjective = False
        self.assertFalse(pending(self.battle))
        self.sweep.bIsTacticalObjective = True
        self.sweep.bCompleted = True
        self.assertFalse(pending(self.battle))
        self.sweep.bCompleted = False
        self.battle.bMissionAborted = True
        self.assertFalse(pending(self.battle))
        self.assertFalse(dispatch(self.unit))
        self.battle.bMissionAborted = False
        self.goals[:] = [self.commander, objective("UnknownRequired", tactical=True)]
        self.assertFalse(pending(self.battle))
        self.assertFalse(pending(None))

    def test_real_report_order_keeps_soldiers_until_native_sweep(self):
        """A commander kill and flare cannot authorize D34/D36 evacuation."""
        read = self.uc["SquadEvacuationReason"]
        should = self.uc["ShouldEvacuate"]
        self.assertEqual("strategy_objective_pending", read(self.battle))
        self.assertFalse(should(self.unit))
        self.commander.bCompleted = True
        self.assertEqual("required_tactical_objective_pending", read(self.battle))
        self.assertFalse(should(self.unit))
        self.sweep.bCompleted = True
        self.assertEqual("allowed", read(self.battle))
        self.assertTrue(should(self.unit))

    def test_other_objectives_keep_original_strategy_only_gate(self):
        """Do not introduce a new extraction exception or an unverified tactical veto."""
        self.commander.bCompleted = self.sweep.bCompleted = True
        self.goals.extend([objective("ExtractAll", strategy=True), objective("Bonus")])
        self.assertFalse(self.uc["ShouldEvacuate"](self.unit))
        self.goals[-2].bCompleted = True
        self.goals.append(objective("OtherRequired", tactical=True))
        self.assertTrue(self.uc["ShouldEvacuate"](self.unit))
        self.goals[:] = [objective("ExtractAll", strategy=True)]
        self.battle.MapData.ActiveMission.sType = "CovertEscape"
        self.assertFalse(self.uc["ShouldEvacuate"](self.unit))
        self.goals[0].bCompleted = True
        self.assertTrue(self.uc["ShouldEvacuate"](self.unit))

    def test_alien_facility_can_extract_after_destroy_without_sweep(self):
        """Regression: real stock Sabotage flags permit evacuation before Sweep."""
        self.battle.MapData.ActiveMission.sType = "Sabotage"
        destroy = objective("DestroyFacility", strategy=True)
        self.goals[:] = [self.sweep, destroy]  # installed definition's order
        reason = self.uc["SquadEvacuationReason"]
        should = self.uc["ShouldEvacuate"]
        dispatch = self.uc["IsRequiredSweepEvacuationBlocked"]
        zone = NS(CenterLocation=(12, 16, 1))
        candidate = NS(AvailableTargets=UCArray([self.unit]))
        self.assertEqual("strategy_objective_pending", reason(self.battle))
        self.assertFalse(should(self.unit))
        self.assertFalse(self.uc["EvacGoalBranch"](self.unit, zone, NS(bFound=False, Tile=None)))
        self.assertFalse(self.uc["EvacActionBranch"](self.unit, "Evac", [candidate]))
        destroy.bCompleted = True
        self.assertFalse(self.sweep.bCompleted)
        self.assertEqual("allowed", reason(self.battle))
        self.assertTrue(should(self.unit))
        self.assertFalse(dispatch(self.unit))
        goal = NS(bFound=False, Tile=None)
        self.assertTrue(self.uc["EvacGoalBranch"](self.unit, zone, goal))
        self.assertEqual(zone.CenterLocation, goal.Tile)
        self.assertTrue(self.uc["EvacActionBranch"](self.unit, "Evac", [candidate]))
        self.sweep.bCompleted = True
        self.assertTrue(should(self.unit))

    def test_missing_and_empty_non_extraction_missions_fail_closed(self):
        """A completed defense objective alone does not grant evacuation."""
        self.goals.clear()
        reason = self.uc["SquadEvacuationReason"]
        should = self.uc["ShouldEvacuate"]
        self.assertEqual("no_strategy_objective", reason(self.battle))
        self.goals.append(objective("Defense", completed=True, tactical=True))
        self.assertFalse(should(self.unit))
        self.battle = None
        self.assertEqual("missing_battle_data", reason(None))
        self.assertFalse(should(self.unit))
        self.assertFalse(should(None))
        self.uc["XCOMHISTORY"] = None
        self.assertFalse(should(self.unit))

    def test_controlled_civilian_exception(self):
        """A locally controlled civilian may leave; a neutral is not the exception."""
        own_vip = soldier(civilian=True)
        neutral = soldier(civilian=True, team="Neutral")
        self.assertTrue(self.uc["IsRescueEvacuation"](own_vip))
        self.assertTrue(self.uc["ShouldEvacuate"](own_vip))
        self.assertFalse(self.uc["IsRescueEvacuation"](neutral))
        self.assertFalse(self.uc["ShouldEvacuate"](neutral))

    def test_carrier_requires_current_matching_objective_effect(self):
        """Only the existing objective-carrier exception bypasses open Sweep."""
        carrier = soldier(carrying=True)
        rescue = self.uc["IsRescueEvacuation"]
        should = self.uc["ShouldEvacuate"]
        for unit in (soldier(420, carrier_id=411, objective_unit=True),
                     soldier(420, carrier_id=410, objective_unit=False),
                     soldier(420, objective_unit=True)):
            self.carried[:] = [unit]
            self.assertFalse(rescue(carrier))
            self.assertFalse(should(carrier))
        self.carried[:] = [soldier(420, carrier_id=410, objective_unit=True)]
        self.assertTrue(rescue(carrier))
        self.assertTrue(should(carrier))
        self.assertFalse(rescue(self.unit))
        self.assertFalse(should(self.unit))

    def test_native_abort_preserves_preexisting_strategy_only_behavior(self):
        """The policy never initiates abort, nor grants a new abort exception."""
        self.battle.bMissionAborted = True
        should = self.uc["ShouldEvacuate"]
        self.assertFalse(should(self.unit))
        self.commander.bCompleted = True
        self.assertTrue(should(self.unit))
        self.goals[:] = [self.sweep]
        self.assertFalse(should(self.unit))

    def test_actual_movement_and_action_selection_branches_share_gate(self):
        """Run production branches before and after Sweep with a valid flare."""
        self.commander.bCompleted = True
        zone = NS(CenterLocation=(12, 16, 1))
        candidate = NS(AvailableTargets=UCArray([self.unit]))
        goal_branch = self.uc["EvacGoalBranch"]
        action_branch = self.uc["EvacActionBranch"]
        for unit, expected in ((self.unit, False), (soldier(civilian=True), True)):
            goal = NS(bFound=False, Tile=None)
            self.assertEqual(expected, goal_branch(unit, zone, goal))
            self.assertEqual(expected, goal.bFound)
            self.assertEqual(expected, action_branch(unit, "Evac", [candidate]))
        self.sweep.bCompleted = True
        goal = NS(bFound=False, Tile=None)
        self.assertTrue(goal_branch(self.unit, zone, goal))
        self.assertEqual(zone.CenterLocation, goal.Tile)
        self.assertTrue(action_branch(self.unit, "Evac", [candidate]))
        self.assertFalse(goal_branch(self.unit, None, NS(bFound=False)))
        self.assertFalse(action_branch(self.unit, "StandardShot", [candidate]))

    def test_synthetic_zip_reports_block_then_native_evac_and_old_loss(self):
        """Execute policy, then preserve synthetic observations in real CLI output."""
        start = "start|mission=NeutralizeFieldCommander|revision=mission-report-v53"
        rows = [(0, start),
                (32, "chosen|kind=action|unit=410|ability=PlaceEvacZone|score=280|accepted=True")]
        self.commander.bCompleted = True
        reason = self.uc["SquadEvacuationReason"](self.battle)
        self.assertFalse(self.uc["ShouldEvacuate"](self.unit))
        rows.append((34, "marker|kind=evacuation_blocked|details=scope=ordinary_squad reason=" + reason))
        rows.append((34, "chosen|kind=action|unit=410|ability=StandardShot|target=42|score=45|accepted=True"))
        self.sweep.bCompleted = True
        self.assertTrue(self.uc["ShouldEvacuate"](self.unit))
        rows.extend([
            (36, "chosen|kind=action|unit=410|ability=Evac|target=410|score=300|accepted=True"),
            (37, "game_score|source=legacy_runtime|mission_points_known=True|mission_final=True"
                 "|mission_points=120|phase=finish|history=3370"),
            (37, "end|reason=tactical_game_ended|outcome=win|history=3370|history_pending=0")])
        old = [(0, start.replace("v53", "v50")), rows[1], rows[4],
               (37, "end|reason=tactical_game_ended|outcome=loss|history=3370|history_pending=0")]
        report = run_synthetic_bundle(("guarded", rows), ("old_loss", old))
        self.assertEqual([], report["malformed_records"])
        sessions = {run["session"]: run for run in report["sessions"]}
        guarded = sessions["guarded"]
        marker, = [r for r in guarded["records"] if r["event"] == "marker"]
        evac, = [r for r in guarded["records"] if r["event"] == "chosen" and r["ability"] == "Evac"]
        self.assertLess(marker["seq"], evac["seq"])
        self.assertIn("required_tactical_objective_pending", marker["details"])
        self.assertEqual("win", guarded["outcome"])
        self.assertEqual("fail", sessions["old_loss"]["attempt_verdict"]["status"])


class EvacuationIntegrationContracts(unittest.TestCase):
    """Keep normal cache, native dispatch and preparation separate."""

    def test_action_veto_after_native_cache_and_before_dispatch(self):
        """The same gate protects selection and final dispatch."""
        mission = MISSION.read_text(encoding="utf-8-sig")
        controller = CONTROLLER.read_text(encoding="utf-8-sig")
        choose = function_body(mission, "ChooseInteraction")
        self.assertLess(choose.index("Candidate.AvailableCode != 'AA_Success'"),
                        choose.index("if (AbilityName == 'Evac')"))
        self.assertIn("if (!ShouldEvacuate(UnitState))", choose)
        use = function_body(controller, "CanUseAction")
        self.assertLess(use.index("Ability.OwnerStateObject.ObjectID != UnitState.ObjectID"),
                        use.index("IsRequiredSweepEvacuationBlocked(UnitState)"))
        decide = function_body(controller, "MakeDecision")
        self.assertIn('Marker("evacuation_blocked"', decide)
        self.assertLess(decide.index("IsRequiredSweepEvacuationBlocked(BestUnit)"),
                        decide.index("MissionRecorder.PrepareChosenAction("))
        self.assertLess(decide.index("IsRequiredSweepEvacuationBlocked(BestUnit)"),
                        decide.index("ActivateAbility_ReturnContext("))
        self.assertIn("ChoosePlacement(", decide)
        self.assertIn("ChooseMove(", decide)
        self.assertIn("ChooseInteraction(", decide)
        self.assertNotIn("bMissionAborted = true", mission)


@unittest.skipUnless(os.environ.get("APX_SDK_SOURCE_ROOT"), "Private WOTC SDK needed")
class EvacuationSDKContracts(unittest.TestCase):
    """Verify stock flags and actual native Kismet completion/abort semantics."""

    @classmethod
    def setUpClass(cls):
        """Locate the original private SDK using the standard checker."""
        cls.sdk = CHECKS.find_sdk_root(Path(os.environ["APX_SDK_SOURCE_ROOT"])) / "XComGame/Classes"

    def test_separate_native_required_flags_and_completion(self):
        """The strategic helper omits Sweep; Kismet writes the native bit."""
        battle = (self.sdk / "XComGameState_BattleData.uc").read_text(encoding="utf-8-sig")
        tactical = function_body(battle, "AllTacticalObjectivesCompleted")
        strategy = function_body(battle, "AllStrategyObjectivesCompleted")
        self.assertIn(".bIsTacticalObjective", tactical)
        self.assertIn(".bCompleted", tactical)
        self.assertIn(".bIsStrategyObjective", strategy)
        self.assertNotIn(".bIsTacticalObjective", strategy)
        self.assertRegex(function_body(battle, "CompleteObjective"), r"\.bCompleted\s*=\s*true")
        sequence = (self.sdk / "SeqAct_CompleteMissionObjective.uc").read_text(encoding="utf-8-sig")
        self.assertIn("BattleData.CompleteObjective(ObjectiveName)", sequence)
        self.assertIn("SubmitGameState(NewGameState)", sequence)

    def test_alien_network_success_is_not_all_tactical_objectives(self):
        """Native Alien Facility strategic success does not require Sweep."""
        sources = (self.sdk / "X2StrategyElement_DefaultMissionSources.uc").read_text(
            encoding="utf-8-sig")
        alien = function_body(sources, "CreateAlienNetworkTemplate")
        self.assertIn("'MissionSource_AlienNetwork'", alien)
        self.assertIn("Template.WasMissionSuccessfulFn = OneStrategyObjectiveCompleted;", alien)
        self.assertIn("BattleDataState.OneStrategyObjectiveCompleted()",
                      function_body(sources, "OneStrategyObjectiveCompleted"))
        battle = (self.sdk / "XComGameState_BattleData.uc").read_text(encoding="utf-8-sig")
        one = function_body(battle, "OneStrategyObjectiveCompleted")
        self.assertIn(".bIsStrategyObjective", one)
        self.assertIn(".bCompleted", one)
        self.assertNotIn(".bIsTacticalObjective", one)

    def test_native_abort_sets_flag_not_planner(self):
        """The exception is keyed to the actual existing native abort state."""
        abort = (self.sdk / "X2Ability_AbortMission.uc").read_text(encoding="utf-8-sig")
        self.assertRegex(abort, r"\.bMissionAborted\s*=\s*true")
        self.assertNotIn("AbortMission(", function_body(MISSION.read_text(), "ShouldEvacuate"))


if __name__ == "__main__":
    unittest.main()
