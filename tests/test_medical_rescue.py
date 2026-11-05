"""Rescue eligibility and medical values execute the actual UC helpers.

Range, charges and native available-target checks remain SDK/game contracts;
these tests do not grant resources or simulate a successful stabilization.
"""
import os
from pathlib import Path
from types import SimpleNamespace
import unittest

from test_ui_gating import CHECKS, function_body
from uc_math import load_uc_function


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'AutoplayXCom2/Src/AutoplayXCom2/Classes/APX_CombatPlanner.uc'


class Unit:
    def __init__(self, identity, player=1, team='xcom', hp=5, max_hp=5,
                 bleeding=False, alive=True, incapacitated=False,
                 carried=False, removed=False, cosmetic=False):
        self.ObjectID = identity
        self.player = player
        self.team = team
        self.hp = hp
        self.max_hp = max_hp
        self.bleeding = bleeding
        self.alive = alive
        self.incapacitated = incapacitated
        self.carried = carried
        self.bRemoved = removed
        self.bRemovedFromPlay = removed
        self.template = SimpleNamespace(bIsCosmetic=cosmetic)

    def GetAssociatedPlayerID(self):
        return self.player

    def GetTeam(self):
        return self.team

    def IsFriendlyUnit(self, target):
        return self.team == target.team

    def GetMyTemplate(self):
        return self.template

    def IsBleedingOut(self):
        return self.bleeding

    def IsBeingCarried(self):
        return self.carried

    def IsAlive(self):
        return self.alive

    def GetCurrentStat(self, stat):
        return self.hp

    def GetMaxStat(self, stat):
        return self.max_hp


class MedicalRescueTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.patient = staticmethod(load_uc_function(SOURCE, 'IsRescuePatient'))
        cls.medical = staticmethod(load_uc_function(SOURCE, 'ScoreMedical'))
        for helper in (cls.patient, cls.medical):
            helper.__globals__.update(none=None, eTeam_XCom='xcom', eStat_HP='hp',
                                      default=SimpleNamespace(EmergencyHealthFraction=0.45))

    def test_bleeding_incapacitated_squadmate_is_a_rescue_patient(self):
        source = Unit(1)
        patient = Unit(2, hp=1, bleeding=True, incapacitated=True)
        self.assertTrue(self.patient(source, patient))
        self.assertEqual(self.medical(source, patient, True), 400)
        self.assertLess(self.medical(source, patient, False), -1000)

    def test_stabilized_unconscious_dead_and_narrative_knockout_are_not_bleeding_rescue(self):
        source = Unit(1)
        cases = (
            Unit(2, hp=1, incapacitated=True),  # stabilized/unconscious
            Unit(3, hp=0, alive=False, incapacitated=True),
            Unit(4, hp=1, incapacitated=True),  # narrative knockout
        )
        for patient in cases:
            with self.subTest(patient=patient.ObjectID):
                self.assertFalse(self.patient(source, patient))
                self.assertLess(self.medical(source, patient, True), -1000)

    def test_only_owned_present_noncarried_squadmates_become_rescue_goals(self):
        source = Unit(1)
        for patient in (None, source, Unit(2, player=2, bleeding=True),
                        Unit(3, team='alien', bleeding=True),
                        Unit(4, bleeding=True, removed=True),
                        Unit(5, bleeding=True, cosmetic=True),
                        Unit(6, bleeding=True, carried=True)):
            self.assertFalse(self.patient(source, patient))
        self.assertFalse(self.patient(None, Unit(2, bleeding=True)))

    def test_stabilization_priority_beats_ordinary_wound_healing_and_rejects_missing_units(self):
        source = Unit(1)
        bleeding = Unit(2, hp=1, bleeding=True)
        wounded = Unit(3, hp=1)
        self.assertGreater(self.medical(source, bleeding, True),
                           self.medical(source, wounded, False))
        self.assertLess(self.medical(None, wounded, False), -1000)
        self.assertLess(self.medical(source, None, True), -1000)

    def test_approach_requires_existing_ready_single_target_stabilization(self):
        helper = function_body(SOURCE.read_text(), 'GetReadyStabilizeAbility')
        for contract in ('IsRescuePatient(', 'SourceUnit.IsAbleToAct()',
                         'OwnerStateObject.ObjectID != SourceUnit.ObjectID',
                         'default.StabilizeAbilities.Find(',
                         '!Ability.IsAbilityInputTriggered()', 'Ability.IsAbilityFreeAiming()',
                         "Template.AbilityTargetStyle.Class != class'X2AbilityTarget_Single'",
                         'Template.AbilityMultiTargetStyle != none',
                         "Ability.CanActivateAbility(SourceUnit) == 'AA_Success'",
                         "Template.CheckTargetConditions(Ability, SourceUnit, TargetUnit) == 'AA_Success'"):
            self.assertIn(contract, helper)
        self.assertNotIn('AA_NoTargets', helper)
        for forbidden in ('ModifyStateObject', 'SubmitGameState', 'ApplyCost(',
                          'SetCurrentStat', 'ActivateAbility_ReturnContext'):
            self.assertNotIn(forbidden, helper)

    def test_proposed_rescue_range_uses_native_ability_units_and_preserves_final_legality(self):
        helper = function_body(SOURCE.read_text(), 'CanStabilizeFromTile')
        self.assertIn('Template.AbilityTargetStyle.GetHitRange(Ability)', helper)
        self.assertIn('if (HitRange < 0.0)', helper)
        self.assertIn('GetPositionFromTileCoordinates(Tile)', helper)
        self.assertIn('GetPositionFromTileCoordinates(TargetUnit.TileLocation)', helper)
        self.assertIn('VSizeSq(SourceLocation - TargetLocation) <= Square(HitRange)', helper)
        self.assertNotIn('MEDIKIT_RANGE', helper)
        choose = function_body(SOURCE.read_text(), 'ChooseAction')
        self.assertIn("Candidate.AvailableCode != 'AA_Success'", choose)
        self.assertIn('ScoreMedical(UnitState, TargetUnit,', choose)


@unittest.skipUnless(os.environ.get('APX_SDK_SOURCE_ROOT'), 'SDK medical contracts need APX_SDK_SOURCE_ROOT')
class MedicalRescueSDKContracts(unittest.TestCase):
    def test_standard_stabilization_is_single_target_and_stops_bleeding_without_revival(self):
        sdk = CHECKS.find_sdk_root(Path(os.environ['APX_SDK_SOURCE_ROOT'])) / 'XComGame/Classes'
        defaults = (sdk / 'X2Ability_DefaultAbilitySet.uc').read_text(encoding='utf-8-sig')
        stabilize = function_body(defaults, 'AddMedikitStabilize')
        self.assertIn("new class'X2AbilityTarget_Single'", stabilize)
        self.assertIn('OnlyIncludeTargetsInsideWeaponRange = true', stabilize)
        self.assertIn('IsBleedingOut = true', stabilize)
        self.assertIn('MEDIKIT_STABILIZE_AMMO', stabilize)
        self.assertIn('ActionPointCost.iNumPoints = 1', stabilize)
        self.assertIn('BleedingOutName', stabilize)
        self.assertIn('CreateUnconsciousStatusEffect(', stabilize)
        self.assertNotIn('AbilityMultiTargetStyle', stabilize)
        specialist = (sdk / 'X2Ability_SpecialistAbilitySet.uc').read_text(encoding='utf-8-sig')
        gremlin = function_body(specialist, 'GremlinStabilize')
        self.assertIn('Template.AbilityTargetStyle = default.SingleTargetWithSelf', gremlin)
        self.assertIn('ChargeCost.NumCharges = 1', gremlin)
        self.assertIn('IsBleedingOut = true', gremlin)

    def test_ready_shooter_check_includes_real_resource_cost_and_cooldown(self):
        sdk = CHECKS.find_sdk_root(Path(os.environ['APX_SDK_SOURCE_ROOT'])) / 'XComGame/Classes'
        ability = (sdk / 'XComGameState_Ability.uc').read_text(encoding='utf-8-sig')
        ready = function_body(ability, 'CanActivateAbility')
        for contract in ('IsCoolingDown()', 'm_Template.CanAfford(self, kUnit)',
                         'm_Template.CheckShooterConditions(self, kUnit, Revalidation)'):
            self.assertIn(contract, ready)
        target = (sdk / 'X2AbilityTargetStyle.uc').read_text(encoding='utf-8-sig')
        self.assertIn('Returns distance in Units', target)
        self.assertIn('-1 if unlimited range', target)


if __name__ == '__main__':
    unittest.main()
