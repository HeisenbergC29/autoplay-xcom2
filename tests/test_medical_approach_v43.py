"""#28 native-legal heal/detox approach, no invented future AA target.

The numerical scorer and status policy execute directly from UnrealScript.
All source contracts are read-only; no Windows/game run is claimed.
"""
import os
from pathlib import Path
import unittest
from uc_math import load_uc_function
from test_ui_gating import CHECKS, function_body

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "AutoplayXCom2/Src/AutoplayXCom2/Classes"
MED = SRC / "APX_MedicalApproach.uc"
COMBAT = SRC / "APX_CombatPlanner.uc"
MISSION = SRC / "APX_MissionPlanner.uc"
CONTROLLER = SRC / "APX_Controller.uc"


class MedicalPolicy(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.heal = staticmethod(load_uc_function(MED, "ScoreUsefulHealing"))
        cls.move = staticmethod(load_uc_function(MED, "ScoreMedicalApproach"))

    def test_native_heal_cures_actual_removable_status_at_full_hp(self):
        self.assertEqual(self.heal(-10000, True, True, False), 170)
        self.assertEqual(self.heal(-10000, True, False, False), 105)
        self.assertLess(self.heal(-10000, False, True, False), -1000)
        self.assertLess(self.heal(-10000, True, True, True), -1000)
        self.assertEqual(self.heal(140, True, True, False), 195)
        self.assertEqual(self.heal(100, True, False, False), 125)
        self.assertEqual(self.heal(100, False, True, False), 100)

    def test_urgent_native_approach_beats_wandering_but_danger_defers(self):
        good = self.move(True, False, 0.2, True, 4, 10, 10, 1, 5, 0)
        ordinary = self.move(True, False, 0.8, False, 4, 10, 10, 1, 5, 0)
        risky = self.move(True, False, 0.2, True, 4, 10, 45, 0.4, 5, 5)
        self.assertGreater(good, 240)
        self.assertGreater(good, ordinary)
        self.assertLess(risky, good - 100)
        self.assertLess(self.move(False, False, 0.2, True, 4, 10, 10, 1, 5, 0), -1000)
        self.assertLess(self.move(True, True, 0.2, True, 4, 10, 10, 1, 5, 0), -1000)
        self.assertLess(self.move(True, False, 0.2, True, 0, 10, 10, 1, 5, 0), -1000)
        self.assertLess(self.move(True, False, 1.0, False, 4, 10, 10, 1, 5, 0), -1000)
        self.assertGreater(self.move(True, False, 1.0, True, 4, 10, 10, 1, 5, 0), 50)


class MedicalSource(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.med = MED.read_text(encoding="utf-8-sig")
        cls.combat = COMBAT.read_text(encoding="utf-8-sig")
        cls.mission = MISSION.read_text(encoding="utf-8-sig")
        cls.controller = CONTROLLER.read_text(encoding="utf-8-sig")

    def test_live_patient_is_not_bleeding_dead_or_controlled_enemy(self):
        patient = function_body(self.med, "IsLiveSquadPatient")
        for key in ("Medic.GetTeam() == eTeam_XCom", "Patient.GetTeam() == eTeam_XCom",
                    "Medic.GetAssociatedPlayerID() == Patient.GetAssociatedPlayerID()",
                    "Medic.IsFriendlyUnit(Patient)", "Patient.IsAlive()",
                    "!Patient.IsIncapacitated()", "!Patient.IsBleedingOut()",
                    "!Patient.IsBeingCarried()",
                    "Patient.GetCurrentStat(eStat_HP) > 0.0"):
            self.assertIn(key, patient)

    def test_effect_removal_checks_installed_effect_types_not_poison_label(self):
        status = function_body(self.med, "HasRemovableEffect")
        for key in ("Ability.GetMyTemplate().AbilityTargetEffects(Effect)",
                    "X2Effect_RemoveEffectsByDamageType(Effect)",
                    "Removal.DamageTypesToRemove(DamageType)",
                    "Patient.IsUnitAffectedByDamageType(DamageType)"):
            self.assertIn(key, status)
        self.assertNotIn("IsPoisoned()", status)
        scorer = function_body(self.combat, "ChooseAction")
        self.assertIn("ScoreMedical(UnitState, TargetUnit,", scorer)
        self.assertIn("class'APX_MedicalApproach'.static.ScoreUsefulHealing(", scorer)
        self.assertIn("class'APX_MedicalApproach'.static.HasRemovableEffect(", scorer)
        self.assertIn("TargetUnit.IsPoisoned()", scorer)
        self.assertIn("Candidate.AvailableCode != 'AA_Success'", scorer)

    def test_medikit_gremlin_resources_patient_conditions_and_remote_geometry(self):
        ready = function_body(self.med, "IsReadyForApproach")
        for key in ("'MedikitHeal'", "'NanoMedikitHeal'", "'GremlinHeal'",
                    "Ability.CanActivateAbility(Medic) == 'AA_Success'",
                    "Template.CheckTargetConditions(Ability, Medic, Patient) == 'AA_Success'",
                    "Template.AbilityMultiTargetStyle != none",
                    "Single.Class != class'X2AbilityTarget_Single'",
                    "HasUsefulNeed(Ability, Patient)"):
            self.assertIn(key, ready)
        current = function_body(self.med, "HasNativeTargetNow")
        self.assertIn("Action.AvailableCode != 'AA_Success'", current)
        self.assertIn("Action.AbilityObjectRef.ObjectID != Ability.ObjectID", current)
        self.assertIn("Target.PrimaryTarget.ObjectID == Patient.ObjectID", current)
        any_legal = function_body(self.med, "HasUrgentNativeHealNow")
        self.assertIn("Action.AvailableCode != 'AA_Success'", any_legal)
        self.assertIn("HasUsefulNeed(Ability, Patient)", any_legal)
        self.assertIn("Patient.GetCurrentStat(eStat_HP)", any_legal)
        self.assertIn("Patient.GetMaxStat(eStat_HP) * 0.45", any_legal)
        self.assertIn("HasRemovableEffect(Ability, Patient)", any_legal)
        self.assertIn("Patient.IsPoisoned()", any_legal)
        self.assertIn("if (++Scanned > 80)", any_legal)
        self.assertIn("return true;", any_legal)
        position = function_body(self.med, "CanTreatFromTile")
        self.assertIn("Single.GetHitRange(Ability)", position)
        self.assertIn("HitRange < 0.0", position)
        self.assertIn("ValidatePrimaryTargetOptionFromRemoteLocation(", position)
        self.assertIn("VSizeSq(Proposed - PatientLocation) <= Square(HitRange)", position)
        self.assertNotIn("MEDIKIT_RANGE", position)

    def test_medical_navigation_full_blue_path_risk_spacing_and_budget(self):
        move = function_body(self.mission, "ChooseMedicalMove")
        for key in ("!HasLegalMove(UnitState)", "ActionPointsAfterBlueMove(",
                    "CanAttackWithActionPoints(Heal, UnitState, AfterBluePoints)",
                    "HasActiveMissionDeadline()", "HasBleedingSquadmate(UnitState)",
                    "ShouldEvacuate(UnitState)", "NeedsPoisonEscape(UnitState)",
                    "NeedsPoisonEscape(Patient)", "HasUrgentNativeHealNow(UnitState)",
                    'ActiveMission.sType == "SabotageTransmitter"',
                    "GetAllPathableTiles(", "IsTileReachable(Tile)",
                    "GetPathCostToTile(Tile)", "Cost > Visualizer.GetMobility()",
                    "BuildPathToTile(Tile, CandidatePath)",
                    "CandidatePath[0] != UnitState.TileLocation",
                    "CandidatePath.Length > 48",
                    "HasBlockingHazard(", "IsKnownCombatTile(",
                    "CanSquadSeeLocation(", "IsSupportedCombatDestination(",
                    "IsSupportedAdvanceStep(",
                    "IsSupportedAdvanceDestination(", "ExposureRisk(",
                    "SquadPositionScore(", "InspectPathRisk(",
                    "InspectRiskAtTile(", "RemainingCoverChecks",
                    "RemainingConcealmentChecks", "Patient.IsPoisoned()",
                    "HasNativeTargetNow(", "CanTreatFromTile("):
            self.assertIn(key, move)
        self.assertIn("if (++Scanned > 128)", move)
        self.assertIn("if (++Ready > 64)", move)
        self.assertIn("Heal.GetMyTemplateName() != 'MedikitHeal'", move)
        self.assertIn("Heal.GetMyTemplateName() != 'NanoMedikitHeal'", move)
        self.assertIn("Heal.GetMyTemplateName() != 'GremlinHeal'", move)
        self.assertIn("if (++Patients > 16)", move)
        self.assertIn("RemainingMedicalSamples <= 0", move)
        self.assertIn("RemainingApproachSamples(", move)
        self.assertNotIn("local int EvaluatedCandidates", move)
        self.assertIn("return Path.Length > 1;", move)
        self.assertIn("Count = Min(Tiles.Length + 9, 64)", move)
        for key in ("SubmitGameState(", "ModifyStateObject(", "ApplyCost(",
                    "ActivateAbility_ReturnContext("):
            self.assertNotIn(key, move)

    def test_controller_ranks_medical_move_then_real_ability_next_decision(self):
        decision = function_body(self.controller, "MakeDecision")
        self.assertIn("class'APX_MissionPlanner'.static.ChooseMedicalMove(", decision)
        self.assertIn("CanUseMove(UnitState, CandidatePath, MedicalPatientID > 0)", decision)
        self.assertIn('MissionRecorder.Marker("medical_approach_candidate"', decision)
        self.assertIn("activation=next_decision_native_cache_required", decision)
        self.assertIn("bSelectedRoute = false;", decision)
        self.assertLess(decision.index("ChooseRescueMove("),
                        decision.index("ChooseMedicalMove("))
        self.assertLess(decision.index("ChooseMedicalMove("),
                        decision.index("ActivateAbility_ReturnContext("))
        self.assertIn("mission-report-v55",
                      (SRC / "APX_MissionRecorder.uc").read_text(encoding="utf-8-sig"))


@unittest.skipUnless(os.environ.get("APX_SDK_SOURCE_ROOT"),
                     "Private full WOTC SDK not installed in public CI")
class NativeMedicalSDK(unittest.TestCase):
    def test_stock_ammo_charges_effects_and_native_remote_contract(self):
        root = CHECKS.find_sdk_root(Path(os.environ["APX_SDK_SOURCE_ROOT"]))
        folder = root / "XComGame/Classes"
        read = lambda f: (folder / f).read_text(encoding="utf-8-sig")
        medikit = function_body(read("X2Ability_DefaultAbilitySet.uc"),
                                "AddMedikitHeal")
        specialist = function_body(read("X2Ability_SpecialistAbilitySet.uc"),
                                   "GremlinHeal")
        for key in ("AmmoCost.iAmmo = 1", "ActionPointCost.iNumPoints = 1",
                    "OnlyIncludeTargetsInsideWeaponRange = true",
                    "Template.AddTargetEffect(RemoveEffects)",
                    "default.MedikitHealEffectTypes(HealType)"):
            self.assertIn(key, medikit)
        for key in ("ChargeCost.NumCharges = 1", "ActionPointCost.iNumPoints = 1",
                    "Template.AbilityTargetStyle = default.SingleTargetWithSelf",
                    "Template.AddTargetEffect(RemoveAllEffectsByDamageType())"):
            self.assertIn(key, specialist)
        unit = read("XComGameState_Unit.uc")
        self.assertIn("native function bool IsUnitAffectedByDamageType(", unit)
        single = read("X2AbilityTarget_Single.uc")
        self.assertIn("ValidatePrimaryTargetOptionFromRemoteLocation(", single)


if __name__ == "__main__":
    unittest.main()
