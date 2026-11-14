"""Bounded and verified current-control source targeting after native X4.

One source already exists in APX_CombatPlanner for active mind-control
links: do not infer it from Priest templates or previous hit logs.
"""
from pathlib import Path
import unittest

from uc_math import load_uc_function
from test_ui_gating import function_body

ROOT = Path(__file__).resolve().parents[1]
C = ROOT / "AutoplayXCom2/Src/AutoplayXCom2/Classes"
MISSION = C / "APX_MissionPlanner.uc"
COMBAT = C / "APX_CombatPlanner.uc"
CONTROLLER = C / "APX_Controller.uc"
PLANT = C / "APX_PlantInteractionKnowledge.uc"


class SweepSourceGoalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mission = MISSION.read_text(encoding="utf-8-sig")
        cls.combat = COMBAT.read_text(encoding="utf-8-sig")
        cls.controller = CONTROLLER.read_text(encoding="utf-8-sig")
        cls.plant = PLANT.read_text(encoding="utf-8-sig")
        cls.policy = staticmethod(load_uc_function(MISSION,
                           "ShouldPreferVerifiedSweepControlSource"))

    def test_source_priority_requires_real_sweep_known_link_and_health(self):
        self.assertTrue(self.policy(True, 1, 0.40))
        self.assertTrue(self.policy(True, 2, 0.99))
        for case in [(False, 1, 0.90), (False, 3, 1.0),
                     (True, 0, 0.90), (True, -1, 0.90),
                     (True, 1, 0.39), (True, 5, 0.00)]:
            with self.subTest(case=case):
                self.assertFalse(self.policy(*case))

    def test_native_plant_only_activates_sweep_for_blood_killer(self):
        goal = function_body(self.mission, "FindGoal")
        self.assertIn("class'APX_PlantInteractionKnowledge'.static.NativePlantObjectivePhase(BattleData)", goal)
        self.assertIn('PlantObjectivePhase == 1', goal)
        self.assertIn("UnitState.GetMyTemplateName() == 'BerserkerMP'", goal)
        self.assertIn('BattleData.MapData.ActiveMission.sType == "SabotageTransmitter"', goal)
        self.assertIn('if (bBerserkerSweep && HealthFraction >= 0.40)', goal)
        self.assertLess(goal.index('if (bBerserkerSweep && HealthFraction >= 0.40)'),
                        goal.index('if ((bBerserkerSweep || bBerserkerFocusGoal)'))
        self.assertLess(goal.index('if (EvacZone != none && ShouldEvacuate(UnitState))'),
                        goal.index('if (bBerserkerSweep && HealthFraction >= 0.40)'))
        self.assertIn('ShouldPrioritizeBerserkerSabotage(', goal)

    def test_only_real_current_visible_source_effect_can_redirect(self):
        goal = function_body(self.mission, "FindGoal")
        self.assertIn("class'APX_CombatPlanner'.static.GetKnownSourceBenefits(", goal)
        self.assertIn('ReleasedAllies, LinkedEnemies)', goal)
        self.assertIn('ShouldPreferVerifiedSweepControlSource(bBerserkerSweep,', goal)
        self.assertIn('Min(24, VisibleEnemies.Length)', goal)
        self.assertIn('BestSourceID = OtherUnit.ObjectID', goal)
        self.assertIn('Goal.Tile = BestSourceTile', goal)
        self.assertIn('Goal.bCombat = true', goal)
        self.assertIn('Berserker sweep control source|unit=', goal)
        for token in ("OtherUnit.IsAlive()", "OtherUnit.IsIncapacitated()",
                      "OtherUnit.bRemovedFromPlay",
                      "UnitState.IsEnemyUnit(OtherUnit)",
                      "IsReclaimableControlledSquadmate("):
            self.assertIn(token, goal)
        self.assertNotIn("GetCurrentActionPoints(", goal)
        self.assertNotIn("IsEngaged(", goal)
        self.assertNotIn("HasAbsoluteKnowledge(", goal)
        self.assertNotIn('AdvPriestM3', goal)

    def test_existing_stock_effect_source_verification_is_reused(self):
        code = function_body(self.combat, 'GetKnownSourceBenefits')
        self.assertIn('GetAllVisibleEnemiesForPlayer(PlayerID, VisibleEnemies)', code)
        self.assertIn('IsVisibleHostile(SourceUnit, Enemy, VisibleEnemies)', code)
        self.assertIn("EffectState.ApplyEffectParameters.SourceStateObjectRef.ObjectID != Enemy.ObjectID", code)
        self.assertIn("EffectState.ApplyEffectParameters.TargetStateObjectRef.ObjectID != LinkedUnit.ObjectID", code)
        self.assertIn("X2Effect_MindControl(EffectTemplate) != none", code)
        self.assertIn("EffectTemplate.bRemoveWhenSourceDies", code)
        self.assertIn('WasControlledByPlayerBeforeEffect(LinkedUnit, EffectState, PlayerID)', code)
        self.assertIn('LinkedUnit.IsMindControlled()', code)
        self.assertIn('CountedTargets.AddItem(TargetRef.ObjectID)', code)
        self.assertIn('Min(64, VisibleEnemies.Length)', code)
        target_guard = function_body(self.combat, 'IsReclaimableControlledSquadmate')
        self.assertIn('WasControlledByPlayerBeforeEffect(', target_guard)
        self.assertIn('EffectTemplate.bRemoveWhenSourceDies', target_guard)

    def test_it_changes_movement_goal_not_native_actions_or_score(self):
        goal = function_body(self.mission, "FindGoal")
        move = function_body(self.mission, "ChooseMove")
        self.assertIn('FullPath', self.mission)
        self.assertIn("class'APX_HazardKnowledge'.static.HasBlockingHazard(", self.mission)
        self.assertIn('IsSupportedAdvanceStep(', self.mission)
        self.assertIn('ExposureRisk(', move)
        self.assertIn('CandidateRisk', move)
        self.assertIn('HasLegalMove(UnitState)', move)
        self.assertNotIn('ActivateAbility_ReturnContext(', goal)
        self.assertNotIn('ModifyStateObject(', goal)
        self.assertNotIn('ScoreSourceBenefits(', goal)
        self.assertIn("class'APX_CombatPlanner'.static.ChooseAction(", self.controller)
        self.assertIn('if (IsReclaimableControlledSquadmate(SourceUnit, TargetUnit))',
                      function_body(self.combat, 'ScoreAttack'))
        self.assertIn('ScoreSourceBenefits(KillChance, ReleasedAllies, LinkedEnemies)',
                      function_body(self.combat, 'ScoreAttack'))


if __name__ == "__main__":
    unittest.main()
