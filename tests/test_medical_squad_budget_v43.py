"""Current native urgent care and one shared medical sample budget.

Math policies execute from the production UC helpers; source/API contracts do
not execute the native WOTC engine or certify that a proposed heal will succeed.
"""
from pathlib import Path
from types import SimpleNamespace
import unittest

from uc_math import load_uc_function
from test_ui_gating import function_body

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "AutoplayXCom2/Src/AutoplayXCom2/Classes"
MED = SRC / "APX_MedicalApproach.uc"
MISSION = SRC / "APX_MissionPlanner.uc"
CONTROLLER = SRC / "APX_Controller.uc"


class MedicalSquadPolicy(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.allow = staticmethod(load_uc_function(MED, "CanProposeApproach"))
        cls.consume = staticmethod(load_uc_function(MED, "RemainingApproachSamples"))
        cls.approach = staticmethod(load_uc_function(MED, "ScoreMedicalApproach"))

    def test_other_medics_urgent_native_heal_preempts_a_higher_move_score(self):
        native = load_uc_function(SRC / "APX_CombatPlanner.uc", "ScoreMedical")
        native.__globals__.update(none=None, eStat_HP="HP",
                                 default=SimpleNamespace(EmergencyHealthFraction=0.45))
        medic_a = SimpleNamespace(IsFriendlyUnit=lambda target: True)
        patient = SimpleNamespace(
            bRemoved=False, bRemovedFromPlay=False, IsAlive=lambda: True,
            IsBleedingOut=lambda: False, GetCurrentStat=lambda stat: 2.0,
            GetMaxStat=lambda stat: 10.0)
        ready_score = native(medic_a, patient, False)
        medic_b_move = self.approach(True, False, 0.2, False, 4, 0, 0, 1, 4, 0)
        self.assertEqual(ready_score, 172.0)
        self.assertAlmostEqual(medic_b_move, 244.6)
        self.assertGreater(medic_b_move, ready_score)
        self.assertFalse(self.allow(True, 128))
        self.assertTrue(self.allow(False, 128))

    def test_medics_share_remaining_samples_instead_of_restarting_the_cap(self):
        remaining = 128
        counts = []
        for requested in (90, 90, 90):
            sampled = 0
            for _ in range(requested):
                if not self.allow(False, remaining):
                    break
                remaining = self.consume(remaining)
                sampled += 1
            counts.append(sampled)
        self.assertEqual(counts, [90, 38, 0])
        self.assertEqual(remaining, 0)
        self.assertEqual(self.consume(0), 0)
        self.assertEqual(self.consume(-5), 0)
        self.assertFalse(self.allow(False, 0))


class MedicalSquadSource(unittest.TestCase):
    def test_controller_owns_one_snapshot_and_one_medical_budget(self):
        make = function_body(CONTROLLER.read_text(encoding="utf-8-sig"), "MakeDecision")
        self.assertEqual(make.count("RemainingMedicalSamples = 128;"), 1)
        self.assertEqual(make.count("HasUrgentSquadHealNow("), 1)
        self.assertLess(make.index("HasUrgentSquadHealNow("),
                        make.index("foreach `XCOMHISTORY.IterateByClassType(class'XComGameState_Unit'"))
        self.assertIn("bSquadUrgentHealAvailable, RemainingMedicalSamples", make)
        self.assertIn("RemainingCoverChecks, RemainingConcealmentChecks, RemainingMedicalSamples", make)
        move = function_body(MISSION.read_text(encoding="utf-8-sig"), "ChooseMedicalMove")
        self.assertIn("if (RemainingMedicalSamples <= 0)", move)
        self.assertIn("return Path.Length > 1;", move)
        self.assertIn("RemainingMedicalSamples = class'APX_MedicalApproach'.static.RemainingApproachSamples(", move)
        self.assertNotIn("EvaluatedCandidates", move)

    def test_roster_and_native_readiness_are_bounded_observational_reads(self):
        source = MED.read_text(encoding="utf-8-sig")
        squad = function_body(source, "HasUrgentSquadHealNow")
        for token in ("GetLocalClientPlayerObjectID()", "PlayerState.GetTeam() != eTeam_XCom",
                      "PlayerVisualizer.ObjectID != PlayerID", "Squad.m_kPlayer != PlayerVisualizer",
                      "Count > 24", "Squad.GetMemberAt(Index)", "Member.ObjectID",
                      "Medic.GetAssociatedPlayerID() != PlayerID", "HasUrgentNativeHealNow(Medic)"):
            self.assertIn(token, squad)
        self.assertNotIn("IterateByClassType", squad)
        self.assertNotIn("GetUnits(", squad)
        self.assertNotIn("RefreshMembers(", squad)
        native = function_body(source, "HasUrgentNativeHealNow")
        self.assertIn("++Scanned > 80", native)
        self.assertIn("++TargetChecks > 128", native)
        self.assertIn("return true;", native)


if __name__ == "__main__":
    unittest.main()
