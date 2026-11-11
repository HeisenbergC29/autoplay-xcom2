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
                       'Destructible.HasRadialDamage()', 'GetDestroyedDamagePreview()',
                       'Destructible.GetRadialDamageTiles(BlastTiles)',
                       'BlastTiles.Length > 96', 'Seen.Find(Destructible)',
                       '++Sampled > 16', 'Probe < 5', 'BlastTile == Tile'):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase,risk)
        for prohibited in ('CreateNewGameState','SubmitGameState',
                           'ApplyDamage','GetUnitValue(','.Ammo','GetCurrentActionPoints('):
            self.assertNotIn(prohibited,self.source)

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
                       'Goal.bBerserkerSabotageGoal', 'CoverChecks <= 6',
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
        self.assertEqual(move.count('GetThreatWeights(UnitState, VisibleEnemies, ThreatWeights);'),1)
        self.assertEqual(move.count('GetMeleeThreatReaches(UnitState, VisibleEnemies, MeleeThreatReaches);'),1)


if __name__=='__main__':
    unittest.main()
