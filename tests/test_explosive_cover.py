"""Exploding environmental cover: cheap, bounded and read-only move risk.

The SDK's radial-damage tiles are a potential effect. This is NOT evidence
that the enemy can shoot now or that a car will detonate this turn.
"""
from pathlib import Path
import unittest

from test_ui_gating import function_body
from uc_math import load_uc_function

ROOT=Path(__file__).resolve().parents[1]
CLASSES=ROOT/'AutoplayXCom2/Src/AutoplayXCom2/Classes'
COVER=CLASSES/'APX_ExplosiveCoverKnowledge.uc'
MISSION=CLASSES/'APX_MissionPlanner.uc'


class ExplosiveCoverContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source=COVER.read_text(encoding='utf-8-sig')
        cls.mission=MISSION.read_text(encoding='utf-8-sig')
        cls.penalty=staticmethod(load_uc_function(COVER,'ExplosiveCoverPenalty'))
        cls.contains=staticmethod(load_uc_function(COVER,'BlastExtentsContain'))
        cls.live_cover=staticmethod(load_uc_function(COVER,'FutureBlastStillPossible'))
        cls.consume=staticmethod(load_uc_function(COVER,'RemainingInspectionBudget'))

    def test_risk_depends_on_real_native_damage_and_enemy_capability(self):
        self.assertEqual(self.penalty(5,False,1.0),0)
        self.assertEqual(self.penalty(0,True,1.0),0)
        self.assertGreater(self.penalty(5,True,1.0),0)
        self.assertGreater(self.penalty(5,True,0.25),self.penalty(5,True,1.0))
        self.assertLessEqual(self.penalty(999,True,0),42.0)
        self.assertGreaterEqual(self.penalty(1,True,1.0),12)

    def test_scans_actual_world_destructibles_not_names_or_fake_explosions(self):
        risk=function_body(self.source,'RiskAtTile')
        for phrase in ('GetActorsOnTile(ProbeTile, true)', 'XComDestructibleActor(Candidate)',
                       'RadialEvent.GetBlastExtents(MinTile, MaxTile)',
                       'Destructible.DestroyedEvents[Index].Action',
                       'RadialEvent.UnitDamage', 'Seen.Find(Candidate)',
                       'SampledActors >= 16', 'Probe < 5', 'BlastExtentsContain('):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase,risk)
        self.assertNotIn('GetRadialDamageTiles(', self.source)
        self.assertNotIn('GetDestroyedDamagePreview(', self.source)
        self.assertNotIn('array<TTile>', risk)
        for prohibited in ('CreateNewGameState','SubmitGameState',
                           'ApplyDamage','GetUnitValue(','.Ammo','GetCurrentActionPoints('):
            self.assertNotIn(prohibited,self.source)

    def test_inclusive_bounds_do_not_require_allocating_a_blast_volume(self):
        # Match stock inclusive min/max tile enumeration at boundaries.
        self.assertTrue(self.contains(3,4,1,3,4,1,7,9,3))
        self.assertTrue(self.contains(7,9,3,3,4,1,7,9,3))
        self.assertTrue(self.contains(5,6,2,3,4,1,7,9,3))
        for point in ((2,6,2),(8,6,2),(5,3,2),(5,10,2),(5,6,0),(5,6,4)):
            with self.subTest(point=point):
                self.assertFalse(self.contains(*point,3,4,1,7,9,3))
        self.assertFalse(self.contains(5,6,2,7,4,1,3,9,3))
        # An enormous event stays a constant-size point test, rather than
        # allocating every voxel before discovering the old 96-tile cap.
        self.assertTrue(self.contains(1,2,3,-100000,-100000,-100000,
                                      100000,100000,100000))

    def test_wrecks_are_excluded_but_live_damaged_cover_remains_possible(self):
        self.assertTrue(self.live_cover(1,False,False,False))
        self.assertTrue(self.live_cover(10,False,False,False))
        self.assertFalse(self.live_cover(0,False,False,False))
        for states in ((True,False,False),(False,True,False),(False,False,True)):
            self.assertFalse(self.live_cover(10,*states))
        risk=function_body(self.source,'RiskAtTile')
        gate=risk.index('FutureBlastStillPossible(')
        self.assertLess(gate,risk.index('DestroyedEvents.Length'))
        for state in ("'_Destroyed'","'Dead'","'_DestructionStarted'"):
            self.assertIn('Destructible.IsInState('+state+')',risk)
        self.assertNotIn("IsInState('_Damaged')",risk)

    def test_native_work_caps_are_checked_before_event_inspection(self):
        risk=function_body(self.source,'RiskAtTile')
        self.assertLess(risk.index('SampledActors >= 16'),
                        risk.index('XComDestructibleActor(Candidate)'))
        self.assertLess(risk.index('DestroyedEvents.Length > 32 - SampledEvents'),
                        risk.index('for (Index = 0;'))
        self.assertLess(risk.index('if (SampledEvents >= 32)'),
                        risk.index('RadialEvent.GetBlastExtents('))
        for guard in ('if (SampledActors >= 16)',
                      'if (Destructible.DestroyedEvents.Length > 32 - SampledEvents)',
                      'if (SampledEvents >= 32)'):
            after=risk.split(guard,1)[1].lstrip()
            self.assertTrue(after.startswith('return 42.0;'),guard)

    def test_exhausted_shared_budget_is_uncertain_not_zero_or_eight(self):
        remaining=6
        calls=0
        for _ in range(10):
            if remaining>0:
                remaining=self.consume(remaining)
                calls+=1
        self.assertEqual(calls,6)
        self.assertEqual(remaining,0)
        self.assertEqual(self.consume(0),0)
        self.assertEqual(self.consume(-1),0)
        inspect=function_body(self.source,'InspectRiskAtTile')
        self.assertLess(inspect.index('if (RemainingCoverChecks <= 0)'),
                        inspect.index('RiskAtTile('))
        self.assertIn('return 42.0;',inspect)
        self.assertNotIn('return 8.0;',inspect)
        self.assertIn('RemainingInspectionBudget(RemainingCoverChecks)',inspect)

    def test_threats_use_only_installed_ability_capabilities_and_enemy_positions(self):
        threats=function_body(self.source,'HasRelevantRangedThreat')
        self.assertIn("class'APX_EnemyKnowledge'.static.PrimaryWeaponMeanDamage",threats)
        self.assertIn("class'APX_EnemyKnowledge'.static.CapabilityFlags",threats)
        self.assertIn('Enemy.IsMeleeOnly()',threats)
        self.assertIn('!UnitState.IsEnemyUnit(Enemy)',threats)
        self.assertIn('Checked > 32',threats)
        risk=function_body(self.source,'RiskAtTile')
        self.assertIn("class'APX_FullIntel'.default.EnableFullIntel",risk)
        self.assertIn('GetKnownEnemies(UnitState, ThreatRefs)',risk)

    def test_routine_move_reassesses_early_route_and_bounded_local_endpoints(self):
        move=function_body(self.mission,'ChooseMove')
        for phrase in ('bCoverUrgent = ShouldEvacuate(UnitState)',
                       'Goal.bBerserkerSabotageGoal', 'RemainingCoverChecks',
                       'APX_ExplosiveCoverKnowledge', 'RiskyRouteCoverRisk',
                       'LocalFallbackCoverRisk', 'Path = RiskyRoute',
                       'Path = LocalFallbackPath'):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase,move)
        # Crucially, soldiers in revealed missions such as GasStation still
        # evaluate explosive cover, unlike a concealment-only guard.
        self.assertNotIn('if (!bConcealmentUrgent && UnitState.GetMyTemplate().bCanTakeCover)',move)
        self.assertIn('if (!bCoverUrgent && UnitState.GetMyTemplate().bCanTakeCover)',move)
        self.assertIn('LocalFallbackPath = CandidatePath;',move)
        self.assertIn('|| (!bCoverUrgent && UnitState.GetMyTemplate().bCanTakeCover)',move)
        self.assertIn('LocalFallbackCoverRisk = 0.0;',move)
        self.assertIn('UnitState.IsConcealed(), true, true,',move)
        self.assertNotIn('.static.RiskAtTile(',move)
        self.assertNotIn('CoverRisk = 8.0;',move)
        self.assertNotIn('RemainingCoverChecks =',move)
        controller=(CLASSES/'APX_Controller.uc').read_text()
        decision=function_body(controller,'MakeDecision')
        self.assertEqual(decision.count('RemainingCoverChecks = 6;'),1)
        self.assertLess(decision.index('RemainingCoverChecks = 6;'),
                        decision.index('foreach `XCOMHISTORY.IterateByClassType('))
        statement=decision.split("class'APX_MissionPlanner'.static.ChooseMove(",1)[1].split(';',1)[0]
        self.assertIn('RemainingCoverChecks',statement)
        self.assertEqual(move.count('GetThreatWeights(UnitState, VisibleEnemies, ThreatWeights);'),1)
        self.assertEqual(move.count('GetMeleeThreatReaches(UnitState, VisibleEnemies, MeleeThreatReaches);'),1)


if __name__=='__main__':
    unittest.main()
