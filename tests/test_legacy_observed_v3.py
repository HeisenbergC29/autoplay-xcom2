"""Observed_v3 uses actual installed Legacy config tables, not v2 defaults.

Source contracts are not Windows compiler/game evidence. The native C++
award bodies and complete late-load coverage are not available here.
"""
from pathlib import Path
import os
import re
import unittest

from test_ui_gating import function_body, CHECKS
from uc_math import load_uc_function

ROOT = Path(__file__).resolve().parents[1]
CLASSES = ROOT / "AutoplayXCom2/Src/AutoplayXCom2/Classes"
V2 = CLASSES / "APX_ComparisonScore.uc"
V3 = CLASSES / "APX_LegacyObservedV3.uc"
HUD = CLASSES / "APX_MissionScore.uc"
REC = CLASSES / "APX_MissionRecorder.uc"


class LegacyObservedV3Contracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.v2 = V2.read_text(encoding="utf-8-sig")
        cls.v3 = V3.read_text(encoding="utf-8-sig")
        cls.hud = HUD.read_text(encoding="utf-8-sig")
        cls.rec = REC.read_text(encoding="utf-8-sig")
        cls.decay = staticmethod(load_uc_function(V3, "DecayedPoints"))
        cls.classify = staticmethod(load_uc_function(V3, "ClassifyEnemyOrigin"))
        cls.penalty = staticmethod(load_uc_function(V3, "SoldierPenaltyPoints"))
        cls.supported = staticmethod(load_uc_function(V3, "InstalledRateCountsSupported"))

    def test_historical_v2_preserved_and_new_v3_has_distinct_identity(self):
        self.assertIn('return "wotc_legacy_observed_v2";', self.v2)
        self.assertIn("DecayedPoints(500, 100, 100, 1, Turn)", self.v2)
        self.assertIn('return "wotc_legacy_config_observed_v3_partial";', self.v3)
        self.assertNotIn("class APX_ComparisonScore extends Object", self.v3)
        self.assertIn("class APX_LegacyObservedV3 extends Object", self.v3)
        self.assertIn("APX_LegacyObservedV3 ComparisonCounter", self.hud)
        self.assertIn("ComparisonCounter = new(self) class'APX_LegacyObservedV3'", self.hud)

    def test_actual_config_overrides_and_defaults_not_hard_coded_rates(self):
        self.assertIn("class'XComGameState_LadderProgress'.default.DefaultEnemyScoringTable", self.v3)
        self.assertIn("class'XComGameState_LadderProgress'.default.DefaultObjectiveScoringTable", self.v3)
        self.assertIn("class'XComGameState_LadderProgress'.default.DefaultSoldierScoring", self.v3)
        self.assertIn('if (Turn < 0 || !HasInstalledRates())', self.v3)
        rules = function_body(self.v3, "FindEnemyRule")
        self.assertIn('Rate = class\'XComGameState_LadderProgress\'.default.DefaultEnemyScoring;', rules)
        self.assertIn('CharacterTemplateName', rules)
        self.assertIn('!= TemplateName', rules)
        self.assertIn('Min(512,', rules)
        enemy = function_body(self.v3, "EnemyPoints")
        self.assertIn('Rate.SpawnedPoints', enemy)
        for f in ("Rate.StartingPoints", "Rate.MinPoints",
                  "Rate.DecreasePerTurn", "Rate.TurnOffset"):
            self.assertIn(f, enemy)
        self.assertNotIn("TemplateName == 'Muton'", enemy)
        self.assertNotIn("DecayedPoints(500, 100", enemy)

    def test_legacy_rate_decay_formula_is_still_only_observation_convention(self):
        self.assertEqual(self.decay(1500, 1000, 100, 1, 10), 1000)
        self.assertEqual(self.decay(3000, 2000, 200, 1, 10), 2000)
        self.assertEqual(self.decay(15000, 10000, 1000, 1, 10), 10000)
        self.assertEqual(self.decay(1000, 1000, 0, 1, 10), 1000)
        self.assertEqual(self.decay(1500, 1000, 100, 1, 1), 1500)
        self.assertEqual(self.decay(1500, 1000, 100, 1, 2), 1400)

    def test_objectives_identified_by_all_native_fields(self):
        body = function_body(self.v3, "CompletedObjectivePoints")
        for token in (".MissionType != MissionName",
                      ".TextPoolIndex != TextPoolIndex",
                      ".GroupID != GroupID", ".LineIndex != LineIndex",
                      "DefaultObjectiveScoringTable[Index]"):
            self.assertIn(token, body)
        event = function_body(self.v3, "OnObjectiveCompleted")
        self.assertIn('CompletedObjectivePoints(Turn,', event)
        self.assertIn('name(MissionType), DisplayAction.TextPoolIndex', event)
        self.assertIn('DisplayAction.GroupID, DisplayAction.LineIndex', event)
        self.assertIn('CompletedObjectives.Find(ObjectiveID) == INDEX_NONE', event)

    def test_only_verified_origin_gets_kill_credit(self):
        body = function_body(self.v3, "ObserveUnit")
        self.assertIn("GetUnitValue('NewSpawnedUnit', SpawnedValue)", body)
        self.assertIn('eReturnType_Reference, StartIndex', body)
        self.assertIn('if (bVerifiedTacticalStart)', body)
        self.assertIn('StartingEnemy.IsEnemyTeam(eTeam_XCom)', body)
        self.assertIn('Origin = ClassifyEnemyOrigin(', body)
        self.assertIn('UnitState.GetPreviousTeam() == eTeam_XCom', body)
        self.assertIn('if (Origin < 0)', body)
        self.assertIn('bUnresolvedEnemyOrigins = true', body)
        self.assertIn('++UnresolvedOriginCount', body)
        self.assertIn('Units[Index].TemplateName, Turn, Origin == 1)', body)
        self.assertLess(body.index('if (Origin < 0)'),
                        body.index('EnemyPoints('))
        self.assertNotIn('ReinforcementPoints', body)
        # Born after tactical start but without explicit spawn marker is UNKNOWN,
        # not evidence of normal/native reinforcement scoring.
        self.assertNotIn('Score += Rate.StartingPoints', self.v3)

    def test_archive_presence_does_not_establish_ordinary_enemy_origin(self):
        # (spawned, verified tactical start, start unit exists,
        #  started XCOM, started enemy, native previous team XCOM)
        self.assertEqual(self.classify(False, True, True, False, True, False), 0)
        for facts in (
                (False, False, True, False, True, False),  # arbitrary archive
                (False, True, False, False, False, False),  # late unknown origin
                (False, True, True, False, False, False),  # start neutral/ally
                (False, False, False, False, False, False)):
            with self.subTest(facts=facts):
                self.assertEqual(self.classify(*facts), -1)

    def test_dead_controlled_former_xcom_never_becomes_an_enemy_award(self):
        for facts in (
                (False, True, True, True, False, False),  # verified own at start
                (False, False, True, False, True, True),  # archive, known previous XCOM
                (True, False, False, False, False, True),  # own spawned unit
                (True, True, True, True, False, False)):
            with self.subTest(facts=facts):
                self.assertEqual(self.classify(*facts), -1)
        # Explicit native spawn classification does not require a start snapshot.
        self.assertEqual(self.classify(True, False, False, False, False, False), 1)

    def test_initial_owner_and_archive_guard_are_bound_to_the_observer(self):
        ensure = function_body(self.v3, "EnsureMission")
        self.assertIn('StartState = History.GetGameStateFromHistory(CurrentStart)', ensure)
        self.assertIn('XComGameStateContext_TacticalGameRule(StartState.GetContext())', ensure)
        self.assertIn('StartContext.GameRuleType == eGameRule_TacticalGameStart', ensure)
        index = function_body(self.v3, "UnitIndex")
        self.assertIn('if (bVerifiedTacticalStart)', index)
        self.assertIn('StartingUnit.GetAssociatedPlayerID() == OwnerPlayerID', index)
        self.assertIn('StartingUnit.GetTeam() == eTeam_XCom', index)
        self.assertNotIn('Entry.bOriginalFriendly = bFriendly', index)
        self.assertIn('if (Units[Index].bEligible)', function_body(self.v3, 'GetObservedScore'))
        cleanup = function_body(self.v3, 'Cleanup')
        self.assertIn('bVerifiedTacticalStart = false;', cleanup)

    def test_missing_or_oversized_installed_tables_cannot_use_truncated_fallback(self):
        for counts in ((1, 1), (134, 116), (512, 512)):
            with self.subTest(counts=counts):
                self.assertTrue(self.supported(*counts))
        for counts in ((0, 116), (134, 0), (513, 116), (134, 513), (-1, 116)):
            with self.subTest(counts=counts):
                self.assertFalse(self.supported(*counts))
        self.assertIn('return InstalledRateCountsSupported(', function_body(self.v3, 'HasInstalledRates'))

    def test_first_wound_and_loss_are_stock_negative_rates(self):
        soldier = function_body(self.v3, "SoldierPoints")
        self.assertIn('return SoldierPenaltyPoints(bEligible, bWounded, bLost,', soldier)
        self.assertIn('Rate.UninjuredBonus, Rate.WoundedBonus', soldier)
        observed = function_body(self.v3, "ObserveUnit")
        self.assertIn('!UnitState.bMissionProvided', observed)
        self.assertIn('UnitState.GetPreviousTeam() == eTeam_XCom', observed)
        self.assertIn("GetUnitValue('LadderKilledScored', KilledValue)", observed)
        self.assertIn('HighestHP > UnitState.LowestHP', observed)
        rescued = function_body(self.v3, "GetObservedScore")
        self.assertIn('DefaultSoldierScoring.RescuedCivilianBonus', rescued)

    def test_zero_or_negative_native_bonus_never_awards_points_for_a_wound_or_loss(self):
        cases = (
            ((True, True, True, 1000, 5000), -6000),
            ((True, True, False, 1000, 5000), -1000),
            ((True, False, True, 1000, 5000), -5000),
            ((True, False, False, 1000, 5000), 0),
            ((False, True, True, 1000, 5000), 0),
            ((True, True, True, 0, 0), 0),
            ((True, True, True, -1000, -5000), 0),
            ((True, True, True, -1000, 5000), -5000),
            ((True, True, True, 1000, -5000), -1000),
        )
        for facts, expected in cases:
            with self.subTest(facts=facts):
                self.assertEqual(self.penalty(*facts), expected)

    def test_partial_coverage_is_permanent_until_native_parity_is_proven(self):
        self.assertIn("partial_unknown_enemy_origin", self.v3)
        self.assertIn("partial_objective_civilian_listener_started_late", self.v3)
        self.assertIn("partial_native_disabled_restart_bonus_unverified", self.v3)
        self.assertIn('bEarlyEventCoverage = bVerifiedTacticalStart && CurrentIndex <= CurrentStart + 1;', self.v3)
        self.assertIn('partial_unverified_tactical_start', self.v3)
        self.assertIn('bUnresolvedEnemyOrigins = false;', self.v3)
        self.assertIn('if (!EnsureMission() || !HasInstalledRates())', self.v3)
        self.assertIn('return "~" $ string(ComparisonPoints) $ "/" $ UnavailableText()', self.hud)
        self.assertIn('comparison_status=partial', self.rec)
        self.assertIn('native_parity_proven=false', self.rec)
        self.assertIn('event_coverage_proven=false', self.rec)
        self.assertIn('rate_source=installed_ladder_config', self.rec)
        self.assertIn("class'APX_LegacyObservedV3'.static.GetProfileID()", self.rec)

    def test_v3_is_pure_observation_and_native_score_precedence_preserved(self):
        clean = CHECKS.without_comments(self.v3)
        forbidden = r"\b(?:AddKillMail|GetTotalScore|ModifyStateObject|CreateNewGameState|CreateStateObject|SubmitGameState|SetCurrentHistoryIndex|Rand|FRand)\s*\("
        self.assertIsNone(re.search(forbidden, clean))
        self.assertIn('UnitState.GetAssociatedPlayerID() == OwnerPlayerID', self.v3)
        self.assertIn("GetAllVisibleEnemiesForPlayer(", self.v3)
        self.assertIn('EndIndex = Min(ObservedHistory.GetCurrentHistoryIndex(), HistoryCursor + 256)', self.v3)
        get_text = function_body(self.hud, "GetText")
        self.assertLess(get_text.index("if (Ladder == none && ChallengeData == none)"),
                        get_text.index('ReadChallengePoints(History, CurrentPoints)'))
        self.assertIn('!CanReadScoreNow()', self.hud)
        self.assertNotIn('Manager.GetTotalScore(', self.hud)


@unittest.skipUnless(os.environ.get("APX_SDK_SOURCE_ROOT"), "Private stock SDK UC required")
class LegacyObservedV3SDKContracts(unittest.TestCase):
    def test_stock_ladder_public_config_structs_and_penalty_semantics(self):
        root = CHECKS.find_sdk_root(Path(os.environ["APX_SDK_SOURCE_ROOT"]))
        ladder = (root / "XComGame/Classes/XComGameState_LadderProgress.uc").read_text(encoding="utf-8-sig")
        structures = (root / "XComGame/Classes/X2ChallengeModeDataStructures.uc").read_text(encoding="utf-8-sig")
        for declaration in (
            'config( Ladder )', 'var config ChallengeEnemyScoring DefaultEnemyScoring;',
            'var config array<ChallengeEnemyScoring> DefaultEnemyScoringTable;',
            'var config ChallengeObjectiveScoring DefaultObjectiveScoring;',
            'var config array<ChallengeObjectiveScoring> DefaultObjectiveScoringTable;',
            'var config ChallengeSoldierScoring DefaultSoldierScoring;'
        ):
            self.assertIn(declaration, ladder)
        for native_fact in (
            'LadderData.CumulativeScore -= SoldierScoring.UninjuredBonus',
            'LadderData.CumulativeScore -= SoldierScoring.WoundedBonus',
            'if (SoldierScoring.UninjuredBonus > 0)',
            'if (SoldierScoring.WoundedBonus > 0)',
            "'NewSpawnedUnit'", "'LadderKilledScored'"
        ):
            self.assertIn(native_fact, ladder)
        for field in ("SpawnedPoints", "ReinforcementPoints",
                      "DisabledPoints", "MinDisabledPoints"):
            self.assertIn(field, structures)


if __name__ == "__main__":
    unittest.main()
