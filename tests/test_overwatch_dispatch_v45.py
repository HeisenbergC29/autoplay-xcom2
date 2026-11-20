"""Follow native Overwatch selection from squad visibility to each submission path."""
from pathlib import Path
import re
import unittest

from test_ui_gating import function_body
from uc_math import load_uc_function


CLASSES = Path(__file__).resolve().parents[1] / "AutoplayXCom2/Src/AutoplayXCom2/Classes"


class OverwatchDispatchTests(unittest.TestCase):
    """Check the runtime call chain; native visibility and reaction rolls require the game."""

    @classmethod
    def setUpClass(cls):
        """Read the actual controller, action selectors, and visibility implementation."""
        cls.controller = (CLASSES / "APX_Controller.uc").read_text()
        cls.combat = (CLASSES / "APX_CombatPlanner.uc").read_text()
        cls.squad = (CLASSES / "APX_SquadPlanner.uc").read_text()
        cls.mission = (CLASSES / "APX_MissionPlanner.uc").read_text()
        cls.main = function_body(cls.controller, "MakeDecision")

    def test_one_squad_snapshot_before_any_command(self):
        """Current native squad visibility supplies one answer, refreshed for each decision."""
        refresh = function_body(self.controller, "RefreshContacts")
        self.assertRegex(refresh, r"if \(!bFoundSource\)\s*return false;")
        stages = [refresh.index(token) for token in (
            "bSquadOverwatchSafe = false;", "SourceUnit.GetAssociatedPlayerID() == PlayerID",
            "if (!bFoundSource)", "GetImmediateThreats(SourceUnit, VisibleEnemies)",
            "bSquadOverwatchSafe = !class'APX_CombatPlanner'.static.HasVisibleReclaimableReactionTarget(",
            "foreach VisibleEnemies(EnemyRef)")]
        self.assertEqual(stages, sorted(stages))
        self.assertRegex(refresh, r"HasVisibleReclaimableReactionTarget\(\s*SourceUnit, VisibleEnemies\);")
        native = function_body(self.mission, "GetImmediateThreats")
        self.assertIn("GetAllVisibleEnemiesForPlayer(", native)
        self.assertNotIn("GetKnownEnemies(", native)
        self.assertEqual(1, self.controller.count(".HasVisibleReclaimableReactionTarget("))
        self.assertEqual(1, self.main.count("RefreshContacts("))
        self.assertLess(self.main.index("RefreshContacts("), self.main.index(".ChooseAction("))

    def test_ordinary_selection_keeps_alternatives_and_patrol_preserves_opener(self):
        """Veto normal and patrol OW before spending an AP on the unsafe reaction."""
        choose = function_body(self.combat, "ChooseAction")
        self.assertRegex(self.main, r"static\.ChooseAction\(UnitState, Candidate,\s*TargetIndex, Score, bSquadOverwatchSafe,")
        self.assertRegex(choose, r"ScoreSelfAction\(UnitState, Ability, AbilityName, VisibleEnemies,\s*bSquadOverwatchSafe,")
        score = function_body(self.combat, "ScoreSelfAction")
        self.assertRegex(score, r"(?s)if \(default\.OverwatchAbilities\.Find\(AbilityName\) != INDEX_NONE\)\s*return GuardOverwatchForKnownAlly\(.*?!bSquadOverwatchSafe\);")
        guard = load_uc_function(CLASSES / "APX_CombatPlanner.uc", "GuardOverwatchForKnownAlly")
        self.assertLess(guard(22, True), -1000)
        self.assertEqual(22, guard(22, False))

        patrol = self.main.index("if (bSquadOverwatchSafe && bPatrolActive")
        concealed = self.main.index("if (CoordinateConcealedAmbush")
        self.assertRegex(self.main[patrol:concealed], re.compile(
            r"ChooseReactionSupport\(.*?CanUseAction\(PatrolSupporter, PatrolReaction, PatrolReactionIndex\)\)\s*\{.*?BestAction = PatrolReaction;", re.S))

    def test_concealed_preparation_keeps_legal_move_with_an_unsafe_reaction(self):
        """Rank two supporters using the UC policy; only the actual OW drops out."""
        evaluate = load_uc_function(CLASSES / "APX_SquadPlanner.uc", "PreparationScore")
        self.assertLess(evaluate(False, True, True, True), 0)
        self.assertEqual(evaluate(True, False, False, True), evaluate(True, False, False, False))
        self.assertGreater(evaluate(True, False, False, True), 0)
        self.assertGreater(evaluate(False, True, True, False), 0)
        prepare = function_body(self.squad, "ChoosePreparation")
        self.assertRegex(prepare, re.compile(
            r"PreparationScore\(Candidate.bMove,.*?!bSquadOverwatchSafe\);\s*if \(Candidate.Score < 0.0\)\s*continue;", re.S))
        concealed = self.main.index("if (CoordinateConcealedAmbush")
        submit = self.main.index("ActivateAbility_ReturnContext(")
        self.assertRegex(self.main[concealed:submit], re.compile(
            r"ChoosePreparation\(.*?bSquadOverwatchSafe, RemainingConcealmentChecks\).*?"
            r"CanUseMove\(AmbushUnit, AmbushPath\).*?CanUseAction\(AmbushUnit, AmbushAction, AmbushTargetIndex\)"
            r".*?BestAction = AmbushAction;.*?bMove = AmbushPath.Length > 1;", re.S))

    def test_native_readiness_owner_and_submission_gate(self):
        """A permission to arm cannot create an ability or spend another soldier's AP."""
        select = function_body(self.squad, "FindOverwatch")
        for requirement in ("GetGameRulesCache_Unit(Soldier.GetReference(), Cache)",
                            "Candidate.AvailableCode != 'AA_Success'", "!Candidate.bInputTriggered",
                            "Ability.OwnerStateObject.ObjectID != Soldier.ObjectID", "FindSelfTarget("):
            self.assertIn(requirement, select)
        submit = function_body(self.controller, "CanUseAction")
        stages = [submit.index(token) for token in (
            "Action.AvailableCode != 'AA_Success'", "Ability.OwnerStateObject.ObjectID != UnitState.ObjectID",
            "if (!bSquadOverwatchSafe", "default.OverwatchAbilities.Find(Ability.GetMyTemplateName())",
            "if (TargetIndex != INDEX_NONE)")]
        self.assertEqual(stages, sorted(stages))
        self.assertRegex(submit, r"default\.OverwatchAbilities\.Find\(Ability.GetMyTemplateName\(\)\) != INDEX_NONE\)\s*return false;")
