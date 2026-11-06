"""Mission coverage documentation contracts: no implied victory from code paths.

Private SDK mission registration is source evidence for the matrix; it is
not copied into the public repo or treated as gameplay verification.
"""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / 'docs/TESTING.pl.md'
CLASSES = ROOT / 'AutoplayXCom2/Src/AutoplayXCom2/Classes'


class CoverageMatrixContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = DOC.read_text(encoding='utf-8-sig')
        cls.matrix = cls.text.split('## Cele i zakończenie misji — macierz obsługi v21', 1)[1].split(
            '## Punktacja każdej symulacji', 1)[0]
        cls.mission = (CLASSES / 'APX_MissionPlanner.uc').read_text(encoding='utf-8-sig')
        cls.evac = (CLASSES / 'APX_EvacPlanner.uc').read_text(encoding='utf-8-sig')
        cls.combat = (CLASSES / 'APX_CombatPlanner.uc').read_text(encoding='utf-8-sig')

    def test_required_mission_families_are_explicit_without_claiming_full_support(self):
        for token in (
            'SabotageCC', 'ChallengeAbductionGasStation', 'SabotageTransmitter',
            'AdventFacilityBLACKSITE', 'ExtractVIP', 'RescueVIP', 'NeutralizeTarget',
            'LostAndAbandonedA/B/C', 'Alien Nest', 'LastGift', 'LastGiftB',
            'LastGiftC', 'ChosenStrongholdShort/Long', 'AvengerDefense',
            'ChosenAvengerDefense', 'AssaultFortressLeadup', 'DestroyAvatarProject',
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.matrix)
        self.assertIn('Brak dedykowanego', self.matrix)
        self.assertIn('Niezweryfikowane', self.matrix)
        self.assertIn('Częściowe', self.matrix)

    def test_reported_scores_are_explicitly_not_confused_with_acceptance(self):
        for token in ('~300', '−12 600', '+700', 'CMPT_TotalScore',
                      'game_score.mission_points', 'outcome=win',
                      'wynik punktowy > 0'):
            with self.subTest(token=token):
                self.assertIn(token, self.matrix)
        self.assertIn('Niepotwierdzony PASS', self.matrix)
        self.assertIn('brak danych', self.matrix)

    def test_named_abilities_have_real_generic_planners(self):
        for ability in ('Interact_PlantBomb', 'Interact_TakeVial',
                        'Interact_MarkSupplyCrate', 'Interact_ActivateAscensionGate',
                        'Hack_Workstation', 'Hack_ObjectiveChest', 'Hack_Scan'):
            with self.subTest(ability=ability):
                self.assertIn("case '" + ability + "':", self.mission)
        self.assertIn('AllStrategyObjectivesCompleted()', self.evac)
        self.assertIn('ChoosePlacement(', self.evac)
        self.assertIn('ScoreObjectiveAttack(', self.combat)

    def test_priority_backlog_does_not_relabel_unverified_gameplay_as_pass(self):
        for topic in ('#29', '#20', '#31', '#28', '#12', '#32'):
            self.assertIn(topic, self.matrix)
        self.assertIn('Żadna kategoria nie jest na dziś potwierdzona', self.matrix)
        self.assertIn('prywatne', self.matrix.lower())


if __name__ == '__main__':
    unittest.main()
