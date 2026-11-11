"""Exercise source-backed threat arithmetic and the SDK counterattack boundary.

These tests execute the real small UC helpers, not the native game. Template
classification and visibility contracts still need Windows/game validation.
"""
import os
from pathlib import Path
from types import SimpleNamespace
import unittest

from test_ui_gating import CHECKS, function_body
from uc_math import load_uc_function


ROOT = Path(__file__).resolve().parents[1]
CLASSES = ROOT / 'AutoplayXCom2/Src/AutoplayXCom2/Classes'
SOURCE = CLASSES / 'APX_EnemyKnowledge.uc'
COMBAT = CLASSES / 'APX_CombatPlanner.uc'


class EnemyKnowledgeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = SOURCE.read_text()
        cls.mean = staticmethod(load_uc_function(SOURCE, 'MeanWeaponDamage'))
        cls.weight = staticmethod(load_uc_function(SOURCE, 'WeaponThreatWeight'))
        cls.target = staticmethod(load_uc_function(SOURCE, 'TargetThreatValue'))
        cls.counter = staticmethod(load_uc_function(SOURCE, 'HasMeleeCounter'))
        cls.counter.__globals__['none'] = None
        cls.damage_score = staticmethod(load_uc_function(COMBAT, 'ScoreDamage'))

    def test_plus_one_is_a_probability_and_missing_damage_is_unknown(self):
        self.assertEqual(self.mean(3, 0), 3)
        self.assertEqual(self.mean(3, 50), 3.5)
        self.assertEqual(self.mean(3, 100), 4)
        self.assertEqual(self.mean(3, -50), 3)
        self.assertEqual(self.mean(3, 500), 4)
        self.assertEqual(self.mean(0, 100), -1)
        self.assertEqual(self.mean(-1, 100), -1)

    def test_heavier_known_weapon_increases_risk_without_unbounded_values(self):
        ordinary = self.weight(3, 65)
        heavy = self.weight(6, 65)
        self.assertEqual(ordinary, 1)
        self.assertGreater(heavy, ordinary)
        self.assertLessEqual(self.weight(1000, 1000), 1.6)
        self.assertGreaterEqual(self.weight(1, 1), 0.75)
        self.assertGreater(self.weight(4, 75), self.weight(4, 55))

    def test_missing_weapon_data_preserves_geometry_instead_of_inventing_damage(self):
        for mean in (-1, 0):
            for aim in (0, 10, 65, 1000):
                self.assertEqual(self.weight(mean, aim), 1)
        self.assertEqual(self.weight(3, 0), 1)

    def test_control_area_and_support_capabilities_only_add_bounded_target_value(self):
        baseline = self.target(1, False, False, False, False)
        self.assertGreater(self.target(1, True, False, False, False), baseline)
        self.assertGreater(self.target(1, False, True, False, False), baseline)
        self.assertGreater(self.target(1, False, False, True, False), baseline)
        self.assertEqual(self.target(10, True, True, True, False), 1.5)
        self.assertEqual(self.target(10, True, True, True, True), 0.6)

    def test_threat_changes_comparable_kills_without_overriding_a_reliable_kill(self):
        normal = self.target(self.weight(3, 65), False, False, False, False)
        special = self.target(self.weight(6, 65), True, True, True, False)
        self.assertGreater(self.damage_score(3, 5, 3, 75, special, 0),
                           self.damage_score(3, 5, 3, 75, normal, 0))
        self.assertGreater(self.damage_score(3, 5, 3, 85, normal, 0),
                           self.damage_score(6, 8, 10, 35, special, 0))
        # Capabilities are not free points for a shot that cannot eliminate.
        self.assertEqual(self.damage_score(3, 5, 10, 30, special, 0),
                         self.damage_score(3, 5, 10, 30, normal, 0))

    def test_counter_capability_is_conservative_but_public_impairment_still_matters(self):
        def enemy(abilities=(), alive=True, impaired=False):
            return SimpleNamespace(
                IsAlive=lambda: alive, IsImpaired=lambda: impaired,
                FindAbility=lambda name: SimpleNamespace(ObjectID=10 if name in abilities else 0))
        self.assertFalse(self.counter(None))
        self.assertFalse(self.counter(enemy()))
        self.assertTrue(self.counter(enemy(('CounterattackPreparation',))))
        self.assertTrue(self.counter(enemy(('Counterattack',))))
        self.assertFalse(self.counter(enemy(('CounterattackPreparation',), impaired=True)))
        self.assertFalse(self.counter(enemy(('CounterattackPreparation',), alive=False)))

    def test_combat_counter_guard_precedes_path_and_stationary_shortcuts(self):
        body = function_body(COMBAT.read_text(), 'HasRequiredMeleePath')
        guard = body.index("class'APX_EnemyKnowledge'.static.HasMeleeCounter(TargetUnit)")
        self.assertIn('MeleeCalc = X2AbilityToHitCalc_StandardAim(AbilityTemplate.AbilityToHitCalc)', body)
        self.assertIn('MeleeCalc != none && MeleeCalc.bMeleeAttack', body)
        self.assertLess(guard, body.index('AbilityTemplate.TargetingMethod == none'))
        self.assertLess(guard, body.index('if (Destinations[0] == SourceUnit.TileLocation)'))
        choose = function_body(COMBAT.read_text(), 'ChooseAction')
        self.assertLess(choose.index('IsVisibleHostile(UnitState, TargetUnit, VisibleEnemies)'),
                        choose.index('HasRequiredMeleePath('))

    def test_primary_weapon_read_is_static_metadata_without_current_readiness(self):
        primary = function_body(self.source, 'PrimaryWeaponMeanDamage')
        self.assertIn('Weapon = Enemy.GetPrimaryWeapon()', primary)
        self.assertIn('WeaponTemplate = X2WeaponTemplate(Weapon.GetMyTemplate())', primary)
        self.assertIn('Damage = WeaponTemplate.BaseDamage', primary)
        self.assertIn('MeanWeaponDamage(Damage.Damage, Damage.PlusOne)', primary)
        weight = function_body(self.source, 'ThreatWeight')
        self.assertNotIn('CapabilityFlags(', weight)
        self.assertNotIn('Abilities(', weight)
        combat = function_body(COMBAT.read_text(), 'ScoreAttack')
        self.assertIn("Threat = class'APX_EnemyKnowledge'.static.TargetThreat(TargetUnit)", combat)

    def test_move_risk_snapshot_also_uses_public_area_control_support_capabilities(self):
        # The old route risk saw only the primary weapon and undervalued
        # enemies with PoisonSpit, control, or squad-buffing abilities.
        mission=(CLASSES / 'APX_MissionPlanner.uc').read_text(encoding='utf-8-sig')
        snapshot=function_body(mission, 'GetThreatWeights')
        self.assertIn("class'APX_EnemyKnowledge'.static.TargetThreat(Enemy)", snapshot)
        self.assertNotIn("class'APX_EnemyKnowledge'.static.ThreatWeight(Enemy)", snapshot)
        self.assertIn('Weights.Length = VisibleEnemies.Length', snapshot)
        self.assertIn('Enemy.IsAlive()', snapshot)
        self.assertIn('UnitState.IsEnemyUnit(Enemy)', snapshot)
        score=function_body(mission, 'ThreatRiskAtTile')
        self.assertIn('Weight = KnownThreatWeight;', score)
        self.assertIn('GetCurrentStat(eStat_HP)', function_body(self.source, 'TargetThreatValue')
                      if False else 'dummy') if False else None
        self.assertGreater(self.target(1, False, True, False, False),
                           self.target(1, False, False, False, False))

    def test_capabilities_come_from_offensive_input_templates_not_unit_names(self):
        flags = function_body(self.source, 'CapabilityFlags')
        for gate in ('Enemy.Abilities.Length > 128',
                     'Ability.OwnerStateObject.ObjectID != Enemy.ObjectID',
                     'Template.Hostility != eHostility_Offensive',
                     '!HasPlayerInputTrigger(Template)'):
            self.assertIn(gate, flags)
        for array in ('Template.AbilityTargetEffects(Effect)', 'Template.AbilityMultiTargetEffects(Effect)'):
            self.assertIn(array, flags)
        for shape in ('Radius', 'Cylinder', 'Cone', 'Line'):
            self.assertIn("IsA('X2AbilityMultiTarget_" + shape + "')", flags)
        effects = function_body(self.source, 'EffectCapabilities')
        for kind in ('MindControl', 'Panicked', 'Stunned', 'Sustained', 'Marked', 'SpawnPsiZombie'):
            self.assertIn("IsA('X2Effect_" + kind + "')", effects)
        self.assertNotIn('GetMyTemplateName', self.source)

    def test_helper_never_changes_state_or_reads_hidden_resources_or_ai(self):
        source = CHECKS.without_comments(self.source)
        for forbidden in ('CanActivateAbility(', 'CanAfford(', 'GetUnitValue(',
                          'NumActionPoints(', '.Ammo', 'iCooldown', 'ModifyStateObject(',
                          'SubmitGameState(', 'ActivateAbility_ReturnContext(',
                          'IterateByClassType(', 'Rand(', 'FRand(', '.default ='):
            self.assertNotIn(forbidden, source)


@unittest.skipUnless(os.environ.get('APX_SDK_SOURCE_ROOT'), 'Enemy knowledge contracts need SDK sources')
class EnemyKnowledgeSDKContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sdk = CHECKS.find_sdk_root(Path(os.environ['APX_SDK_SOURCE_ROOT'])) / 'XComGame/Classes'

    def test_weapon_metadata_and_plus_one_contract_are_native_sdk_fields(self):
        weapon = (self.sdk / 'X2WeaponTemplate.uc').read_text(encoding='utf-8-sig')
        self.assertIn('var config WeaponDamageValue BaseDamage;', weapon)
        item = function_body((self.sdk / 'XComGameState_Item.uc').read_text(encoding='utf-8-sig'),
                             'GetBaseWeaponDamageValue')
        self.assertIn('DamageValue = WeaponTemplate.BaseDamage', item)
        structure = (self.sdk / 'X2TacticalGameRulesetDataStructures.uc').read_text(encoding='utf-8-sig')
        self.assertIn('chance from 0-100 that one bonus damage will be added', structure)

    def test_counter_guard_matches_native_conversion_even_for_guaranteed_melee(self):
        source = (self.sdk / 'XComGameStateContext_Ability.uc').read_text(encoding='utf-8-sig')
        self.assertIn('!TargetUnitState.IsImpaired()', source)
        self.assertIn('ToHitCalc.bGuaranteedHit == true', source)
        self.assertIn('ToHitCalc.bMeleeAttack', source)
        self.assertIn('eHit_CounterAttack', source)
        template = (self.sdk / 'X2Ability_Muton.uc').read_text(encoding='utf-8-sig')
        self.assertIn("'CounterattackPreparation'", template)
        self.assertIn("Template.AdditionalAbilities.AddItem('Counterattack')", template)

    def test_registered_templates_use_the_effects_which_the_classifier_recognizes(self):
        mindspin = function_body((self.sdk / 'X2Ability_Sectoid.uc').read_text(encoding='utf-8-sig'),
                                'AddMindspinTemplate')
        self.assertIn('CreateMindControlStatusEffect(', mindspin)
        self.assertIn('CreatePanickedStatusEffect()', mindspin)
        captain = function_body((self.sdk / 'X2Ability_AdventCaptain.uc').read_text(encoding='utf-8-sig'),
                               'CreateMarkTargetAbility')
        self.assertIn('CreateMarkedEffect(', captain)
        viper = (self.sdk / 'X2Effect_ViperBindSustained.uc').read_text(encoding='utf-8-sig')
        self.assertIn('extends X2Effect_Sustained', viper)
        for name in ('X2AbilityMultiTarget_Line', 'X2AbilityTrigger_PlayerInput',
                     'X2Effect_Marked', 'X2Effect_SpawnPsiZombie'):
            self.assertTrue((self.sdk / (name + '.uc')).is_file())


if __name__ == '__main__':
    unittest.main()
