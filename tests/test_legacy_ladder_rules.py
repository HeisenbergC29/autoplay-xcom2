"""No private SDK or game config files are committed or needed in public CI."""
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
AUDITOR = ROOT / "tools/audit-legacy-ladder-rules.py"
SPEC = importlib.util.spec_from_file_location("legacy_rate_auditor", AUDITOR)
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)

BASE = """[Other.Section]
DefaultEnemyScoringTable=(CharacterTemplateName="Fake", StartingPoints=100, MinPoints=1, DecreasePerTurn=0, TurnOffset=1, SpawnedPoints=0, ReinforcementPoints=0, DisabledPoints=1, MinDisabledPoints=1)
[XComGame.XComGameState_LadderProgress]
DefaultEnemyScoring=(CharacterTemplateName="", StartingPoints=1000, MinPoints=1000, DecreasePerTurn=0, TurnOffset=1, SpawnedPoints=0, ReinforcementPoints=0, DisabledPoints=1000, MinDisabledPoints=1000)
DefaultEnemyScoringTable=(CharacterTemplateName="AdvTrooperM1", StartingPoints=1500, MinPoints=1000, DecreasePerTurn=100, TurnOffset=1, SpawnedPoints=0, ReinforcementPoints=0, DisabledPoints=1000, MinDisabledPoints=1000)
DefaultEnemyScoringTable=(CharacterTemplateName="AdvPriestM3", StartingPoints=3000, MinPoints=2000, DecreasePerTurn=200, TurnOffset=1, SpawnedPoints=0, ReinforcementPoints=0, DisabledPoints=2000, MinDisabledPoints=2000)
DefaultObjectiveScoring=(MissionType="", TextPoolIndex=-1, GroupID=-1, LineIndex=-1, StartingPoints=0, MinPoints=0, DecreasePerTurn=0, TurnOffset=1)
DefaultObjectiveScoringTable=(MissionType="SabotageTransmitter", TextPoolIndex=0, GroupID=1, LineIndex=1, StartingPoints=15000, MinPoints=10000, DecreasePerTurn=1000, TurnOffset=1)
DefaultMissionScoring=(MissionType="", StartingPoints=15000, MinPoints=10000, DecreasePerTurn=1000, TurnOffset=1)
DefaultSoldierScoring=(UninjuredBonus=1000, WoundedBonus=5000, RescuedCivilianBonus=1000)
"""
TLE = """[XComGame.XComGameState_LadderProgress]
+DefaultObjectiveScoringTable=(MissionType="ChallengeTerrorBar", TextPoolIndex=0, GroupID=1, LineIndex=0, StartingPoints=15000, MinPoints=10000, DecreasePerTurn=1000, TurnOffset=1)
+DefaultEnemyScoringTable=(CharacterTemplateName="Muton", StartingPoints=3000, MinPoints=2000, DecreasePerTurn=200, TurnOffset=1, SpawnedPoints=0, ReinforcementPoints=0, DisabledPoints=2000, MinDisabledPoints=2000)
RestartScorePenalty=5000
"""


class LegacyRateAuditTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        folder = Path(self.temp.name)
        self.base = folder / "DefaultLadder.ini"
        self.tle = folder / "XComLadder.ini"
        self.base.write_text(BASE, encoding="utf-8")
        self.tle.write_text(TLE, encoding="utf-8")

    def test_enemy_override_and_native_default_are_not_v2_sdk_fallback(self):
        rules = mod.load_rules([self.base, self.tle])
        self.assertEqual(mod.decayed(mod.rate_for_enemy(rules, "AdvTrooperM1"), 10), 1000)
        self.assertEqual(mod.decayed(mod.rate_for_enemy(rules, "AdvPriestM3"), 10), 2000)
        self.assertEqual(mod.decayed(mod.rate_for_enemy(rules, "UnknownEnemy"), 10), 1000)
        self.assertEqual(mod.decayed(mod.rate_for_enemy(rules, "Muton"), 10), 2000)
        self.assertEqual(mod.rate_for_enemy(rules, "AdvTrooperM1")["ReinforcementPoints"], 0)

    def test_objective_key_includes_line_and_group_not_only_mission(self):
        rules = mod.load_rules([self.base, self.tle])
        self.assertEqual(mod.decayed(mod.rate_for_objective(rules, "ChallengeTerrorBar", 0, 1, 0), 10), 10000)
        self.assertEqual(mod.decayed(mod.rate_for_objective(rules, "ChallengeTerrorBar", 0, 1, 1), 10), 0)
        self.assertEqual(mod.decayed(mod.rate_for_objective(rules, "SabotageTransmitter", 0, 1, 1), 10), 10000)
        self.assertEqual(rules["defaults"]["RestartScorePenalty"]["Value"], 5000)

    def test_report_is_only_derived_and_not_official(self):
        rules = mod.load_rules([self.base, self.tle])
        previous = json.loads((ROOT / "tools/legacy-score-rules.json").read_text())
        r = mod.audit(rules, previous)
        self.assertEqual(r["counts"], {"enemy": 3, "objective": 2, "mission": 0})
        self.assertEqual(r["comparison_differences_at_turn10"]["AdvTrooperM1"],
                         {"previous": 100, "configured": 1000, "difference": 900})
        self.assertEqual(r["comparison_differences_at_turn10"]["AdvPriestM3"],
                         {"previous": 100, "configured": 2000, "difference": 1900})
        self.assertFalse(r["is_official_game_score"])
        self.assertFalse(r["native_award_parity_proven"])
        self.assertFalse(r["event_coverage_proven"])
        self.assertNotIn(self.temp.name, json.dumps(r))
        self.assertEqual(len(r["sources"][0]["sha256"]), 64)

    def test_conflicting_same_key_is_not_silently_overridden(self):
        text = TLE + ('+DefaultEnemyScoringTable=(CharacterTemplateName="AdvTrooperM1", '
                      'StartingPoints=3000, MinPoints=2000, DecreasePerTurn=200, TurnOffset=1, '
                      'SpawnedPoints=0, ReinforcementPoints=0, DisabledPoints=2000, MinDisabledPoints=2000)\n')
        self.tle.write_text(text)
        with self.assertRaisesRegex(ValueError, "ambiguous.*override"):
            mod.load_rules([self.base, self.tle])

    def test_bad_entries_and_removal_require_manual_review(self):
        self.tle.write_text("[XComGame.XComGameState_LadderProgress]\n"
                            "-DefaultEnemyScoringTable=(CharacterTemplateName=\"Muton\", "
                            "StartingPoints=3000, MinPoints=2000, DecreasePerTurn=200, TurnOffset=1, "
                            "SpawnedPoints=0, ReinforcementPoints=0, DisabledPoints=2000, MinDisabledPoints=2000)\n")
        with self.assertRaisesRegex(ValueError, "removal"):
            mod.load_rules([self.base, self.tle])
        self.tle.write_text("[XComGame.XComGameState_LadderProgress]\n"
                            "+DefaultEnemyScoringTable=(CharacterTemplateName=\"Muton\", StartingPoints=3)\n")
        with self.assertRaisesRegex(ValueError, "incomplete scoring values"):
            mod.load_rules([self.base, self.tle])

    def test_negative_unknown_turn_and_no_borrowed_initial_score(self):
        with self.assertRaisesRegex(ValueError, "turn unknown"):
            mod.decayed({"StartingPoints": 100, "MinPoints": 0,
                         "TurnOffset": 1, "DecreasePerTurn": 10}, -1)
        self.assertNotIn("initial_soldier_allowance", mod.audit(mod.load_rules([self.base])))

    @unittest.skipUnless(os.environ.get("APX_GAME_LADDER_INI") and
                         os.environ.get("APX_TLE_LADDER_INI"), "Private installed INI required")
    def test_optional_private_real_config_counts(self):
        r = mod.load_rules([Path(os.environ["APX_GAME_LADDER_INI"]),
                            Path(os.environ["APX_TLE_LADDER_INI"])])
        self.assertEqual({k: len(v) for k,v in r["categories"].items()},
                         {"enemy": 134, "objective": 116, "mission": 20})


if __name__ == "__main__":
    unittest.main()
