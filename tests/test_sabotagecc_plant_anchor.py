"""SabotageCC post-clear native plant-goal, never a fake PlantBomb activation.

Source tests and the actual pure UnrealScript policy; stock Windows WOTC
compile and a fully autonomous game remain required for acceptance.
"""
from pathlib import Path
import unittest

from uc_math import load_uc_function
from test_ui_gating import function_body

ROOT=Path(__file__).resolve().parents[1]
CLASSES=ROOT/"AutoplayXCom2/Src/AutoplayXCom2/Classes"
MISSION=CLASSES/"APX_MissionPlanner.uc"
PLANT=CLASSES/"APX_PlantInteractionKnowledge.uc"
CONTROLLER=CLASSES/"APX_Controller.uc"

class SabotageCCPlantAnchorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source=MISSION.read_text(encoding="utf-8-sig")
        cls.native=PLANT.read_text(encoding="utf-8-sig")
        cls.controller=CONTROLLER.read_text(encoding="utf-8-sig")
        cls.eligible=staticmethod(load_uc_function(MISSION,'ShouldSeekMonumentPlantAnchor'))

    def test_only_post_clear_sabotagecc_is_eligible(self):
        self.assertTrue(self.eligible(True,0,False,False,True))
        for args in (
            (False,0,False,False,True),
            (True,1,False,False,True),
            (True,10,False,False,True),
            (True,0,True,False,True),
            (True,0,False,True,True),
            (True,0,False,False,False),
        ):
            with self.subTest(args=args):
                self.assertFalse(self.eligible(*args))

    def test_real_actor_socket_is_consulted_before_marker_and_combat_fallback(self):
        goal=function_body(self.source,'FindGoal')
        self.assertIn('BattleData.MapData.ActiveMission.sType == "SabotageCC"',goal)
        self.assertIn('ShouldSeekMonumentPlantAnchor(true, VisibleEnemies.Length,',goal)
        self.assertIn("UnitState.FindAbility('Interact_PlantBomb').ObjectID > 0",goal)
        self.assertIn("class'APX_PlantInteractionKnowledge'.static.FindInteractionGoal(",goal)
        self.assertIn('if (MonumentNativeGoalStatus > 0)',goal)
        self.assertIn('Goal.Tile = SabotageGoalTile;',goal)
        self.assertIn('Goal.bCombat = false;',goal)
        self.assertIn('return true;',goal)
        self.assertIn('Native monument plant approach|unit=',goal)
        # Must be before generic glint and the ObjectiveLocation marker that
        # previously returned bFound=false at <=3 (even with wrong Z).
        self.assertLess(goal.index('ShouldSeekMonumentPlantAnchor(true,'),
                        goal.index('IsUnfinishedObject(ObjectState)'))
        self.assertLess(goal.index('ShouldSeekMonumentPlantAnchor(true,'),
                        goal.index('BattleData.MapData.ObjectiveLocation'))
        self.assertIn('TileDistance(UnitState.TileLocation, Goal.Tile) > 3',goal)
        self.assertNotIn('MonumentNativeGoalStatus >= 0',goal)

    def test_no_native_goal_never_grants_interaction_or_sets_objective_completed(self):
        goal=function_body(self.source,'FindGoal')
        interact=function_body(self.source,'ChooseInteraction')
        self.assertIn("Candidate.AvailableCode != 'AA_Success'",interact)
        self.assertIn('Candidate.bInputTriggered',interact)
        self.assertIn('IsObjectiveAbility(AbilityName)',interact)
        self.assertNotIn('AA_Success',goal)  # Selecting a tile is not native legality.
        for forbidden in ('ActivateAbility_ReturnContext(', 'ModifyStateObject(',
                          'CreateNewGameState(', 'SubmitGameState(', 'ForceInteract('):
            self.assertNotIn(forbidden,goal)
        self.assertIn('class\'X2PathSolver\'.static.BuildPath(',self.native)
        self.assertIn("NativePlantObjectivePhase(BattleData)",self.source)

    def test_plant_discovery_is_bounded_and_fails_closed(self):
        query=function_body(self.native,'FindInteractionGoalResult')
        for token in (
            "UnitState.FindAbility('Interact_PlantBomb')",
            "Ability.OwnerStateObject.ObjectID != UnitState.ObjectID",
            "Visualizer.InteractionAbilityTemplateName != 'Interact_PlantBomb'",
            "ObjectState.CanInteractNormally(UnitState)",
            "NativePlantPointOnTile(",
            "ContainsTile(FutureFootprint, QueryTile)",
            "FullPath[FullPath.Length - 1] == Candidate",
            "ObjectsChecked > 128",
            "RemainingQueries = 32",
            "PointsChecked > 32",
            "AnchorsChecked < 64",
            "PathChecks < 4",
        ):
            with self.subTest(token=token):
                self.assertIn(token,query)
        self.assertNotIn('UnitState.TileLocation =',query)

    def test_existing_sabotage_transmitter_and_controller_native_actions_unmodified(self):
        goal=function_body(self.source,'FindGoal')
        self.assertIn('FindBerserkerSabotageGoal(UnitState, BattleData,',goal)
        self.assertIn('Goal.bBerserkerSabotageGoal = true;',goal)
        self.assertIn('ShouldEvacuate(UnitState)',goal)
        self.assertIn('GetImmediateThreats(UnitState, ImmediateEnemies)',goal)
        self.assertIn('ChooseInteraction(UnitState, Candidate, TargetIndex, Score)',self.controller)
        self.assertIn('ActivateAbility_ReturnContext(',self.controller)
        self.assertNotIn('Native monument plant approach|unit=',self.controller)

if __name__=='__main__':
    unittest.main()
