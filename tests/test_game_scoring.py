"""Native observations stay separate from incomplete game-derived comparisons."""
import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('game_scoring', ROOT / 'tools/game_scoring.py')
SCORING = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SCORING)
LOG_SPEC = importlib.util.spec_from_file_location('mission_log_scoring', ROOT / 'tools/analyze-mission-log.py')
LOG = importlib.util.module_from_spec(LOG_SPEC)
LOG_SPEC.loader.exec_module(LOG)


def events(*items):
    return [{'seq': index, 'session': 's', **item} for index, item in enumerate(items, 1)]


def friendly(**fields):
    return {'event': 'unit', 'id': 1, 'scope': 'friendly', 'hp': 6, 'max_hp': 6,
            'alive': True, 'score_eligible': True, **fields}


def enemy(**fields):
    return {'event': 'unit', 'id': 9, 'scope': 'visible_enemy', 'template': 'Sectoid',
            'hp': 4, 'alive': True, 'spawned': False, 'reinforcement': False, 'turn': 1, **fields}


def comparison(*items):
    return SCORING.comparison_score(events({'event': 'start'}, {'event': 'phase', 'turn': 1},
                                          *items, {'event': 'end', 'outcome': 'win'}),
                                    SCORING.load_profile())


def component_points(score, kind):
    return [item['points'] for item in score['components'] if item['kind'] == kind]


class GameScoringTests(unittest.TestCase):
    def test_actual_profile_values_and_provenance_replace_manual_user_numbers(self):
        profile = SCORING.load_profile()
        self.assertEqual(profile['enemies']['Sectoid']['starting_points'], 1500)
        self.assertEqual(profile['enemies']['Muton']['starting_points'], 3000)
        self.assertEqual(profile['objective']['min_points'], 5000)
        self.assertFalse(profile['is_official_game_score'])
        self.assertFalse(profile['comparison_conventions']['turn_decay_is_native_reconstruction'])
        self.assertTrue(profile['provenance'][0]['log_sha256'])

    def test_zero_base_starts_at_zero_and_never_grants_automatic_end_bonuses(self):
        soldiers = [friendly(id=identity, highest_hp=6, lowest_hp=6) for identity in range(1, 5)]
        for outcome in ('win', 'loss'):
            with self.subTest(outcome=outcome):
                result = SCORING.comparison_score(events(
                    {'event': 'start'}, {'event': 'phase', 'turn': 1},
                    *soldiers, {'event': 'end', 'outcome': outcome}), SCORING.load_profile())
                self.assertEqual(result['observed_subtotal'], 0)
                self.assertEqual(result['components'], [])
                self.assertEqual(component_points(result, 'soldier_allowance'), [])
        empty = SCORING.comparison_score(events({'event': 'start'}, {'event': 'end'}),
                                         SCORING.load_profile())
        self.assertIsNone(empty['observed_subtotal'])

    def test_human_summary_keeps_a_legitimate_zero_visible(self):
        lines = '\n'.join((
            'APXREC|v=1|session=zero|seq=1|event=start|mission=SabotageCC',
            'APXREC|v=1|session=zero|seq=2|event=unit|scope=friendly|id=1|score_eligible=True|hp=6|max_hp=6|highest_hp=6|lowest_hp=6|alive=True',
            'APXREC|v=1|session=zero|seq=3|event=end|outcome=win',
        ))
        report = LOG.analyze_logs([('Launch.log', lines)])
        self.assertEqual(report['sessions'][0]['game_scoring']['comparison']['observed_subtotal'], 0)
        self.assertIn('observed subtotal=0', LOG.human_summary(report))
        self.assertNotIn('no award components could be reconstructed', LOG.human_summary(report))

    def test_archived_v1_retains_old_allowance_only_when_explicitly_selected(self):
        old_profile = SCORING.load_profile(ROOT / 'tools/legacy-score-rules-v1.json')
        self.assertEqual(old_profile['profile_id'], 'wotc_legacy_observed_v1')
        self.assertTrue(old_profile['initial_soldier_allowance'])
        records = events({'event': 'start'}, {'event': 'phase', 'turn': 1},
                         friendly(highest_hp=6, lowest_hp=6), {'event': 'end', 'outcome': 'win'})
        legacy = SCORING.comparison_score(records, old_profile)
        current = SCORING.comparison_score(records, SCORING.load_profile())
        self.assertEqual(component_points(legacy, 'soldier_allowance'), [6000])
        self.assertEqual(legacy['observed_subtotal'], 6000)
        self.assertEqual(current['observed_subtotal'], 0)
        self.assertEqual(component_points(current, 'soldier_allowance'), [])

    def test_zero_base_report_components_preserve_negative_result(self):
        initial = [friendly(id=identity, highest_hp=6, lowest_hp=6) for identity in range(1, 5)]
        injured = [friendly(id=identity, hp=3, highest_hp=6, lowest_hp=3)
                   for identity in range(1, 5)]
        dead = [friendly(id=identity, hp=0, alive=False, highest_hp=6, lowest_hp=0)
                for identity in range(1, 4)]
        result = comparison(*initial, *injured, *dead,
                            enemy(template='AdvTrooperM1', id=9),
                            enemy(template='AdvTrooperM1', id=9, hp=0, alive=False, turn=7),
                            enemy(template='AdvTrooperM1', id=10),
                            enemy(template='AdvTrooperM1', id=10, hp=0, alive=False, turn=12))
        self.assertEqual(result['observed_subtotal'], -18800)
        self.assertEqual(component_points(result, 'soldier_allowance'), [])
        self.assertEqual(component_points(result, 'first_injury_penalty'), [-1000] * 4)
        self.assertEqual(component_points(result, 'soldier_loss_penalty'), [-5000] * 3)

    def test_injury_once_healing_no_refund_and_bleeding_not_death(self):
        result = comparison(friendly(), friendly(hp=4, highest_hp=6, lowest_hp=4),
                            friendly(hp=2, highest_hp=6, lowest_hp=2),
                            friendly(hp=6, highest_hp=6, lowest_hp=2),
                            friendly(hp=0, bleeding_out=True, incapacitated=True))
        self.assertEqual(component_points(result, 'soldier_allowance'), [])
        self.assertEqual(component_points(result, 'first_injury_penalty'), [-1000])
        self.assertEqual(component_points(result, 'soldier_loss_penalty'), [])

    def test_ladder_narrative_knockout_and_later_death_are_one_loss(self):
        result = comparison(friendly(), friendly(hp=0, unconscious=True, ladder_killed_scored=True),
                            friendly(hp=0, alive=False, ladder_killed_scored=True))
        self.assertEqual(component_points(result, 'first_injury_penalty'), [-1000])
        self.assertEqual(component_points(result, 'soldier_loss_penalty'), [-5000])
        self.assertEqual(result['observed_friendly_losses'], 1)

    def test_native_mission_hp_history_distinguishes_preexisting_wounds(self):
        start_injured = friendly(hp=4, max_hp=6, highest_hp=4, lowest_hp=4)
        result = comparison(start_injured)
        self.assertEqual(component_points(result, 'first_injury_penalty'), [])
        self.assertEqual(result['observed_friendly_wounded'], 0)
        result = comparison(start_injured, friendly(hp=2, highest_hp=4, lowest_hp=2))
        self.assertEqual(component_points(result, 'first_injury_penalty'), [-1000])
        # A witnessed damage result is also valid evidence before the next
        # native HP-history snapshot is available.
        result = comparison(start_injured, {'event': 'result', 'target': 1,
                                            'target_hp_before': 4, 'target_hp_after': 2})
        self.assertEqual(component_points(result, 'first_injury_penalty'), [-1000])

    def test_missing_native_injury_history_is_explicit_and_can_be_resolved(self):
        result = comparison(friendly(hp=4, max_hp=6))
        self.assertEqual(component_points(result, 'first_injury_penalty'), [-1000])
        self.assertIn('soldier_injury_history', result['missing_components'])
        self.assertTrue(any('pre-existing injury' in note for note in result['assumptions']))
        result = comparison(friendly(hp=4, max_hp=6),
                            friendly(hp=4, max_hp=6, highest_hp=4, lowest_hp=4))
        self.assertEqual(component_points(result, 'first_injury_penalty'), [])
        self.assertNotIn('soldier_injury_history', result['missing_components'])

    def test_mission_provided_units_do_not_receive_soldier_points(self):
        result = comparison(friendly(score_eligible=False, hp=0, alive=False))
        self.assertEqual(result['components'], [])
        self.assertIsNone(result['observed_subtotal'])
        old = comparison(friendly(score_eligible=None))
        self.assertIn('soldier_score_eligibility', old['missing_components'])

    def test_results_and_dead_snapshot_count_one_confirmed_enemy(self):
        result = comparison(enemy(), {'event': 'result', 'target': 9, 'target_hp_before': 4,
                                       'target_hp_after': 0, 'target_alive_after': False, 'turn': 3},
                            {'event': 'result_target', 'target': 9, 'target_hp_before': 4,
                             'target_hp_after': 0, 'target_alive_after': False, 'turn': 3},
                            enemy(hp=0, alive=False, turn=3))
        self.assertEqual(component_points(result, 'enemy_eliminated'), [1300])

    def test_later_history_result_supplies_turn_missing_from_dead_snapshot(self):
        dead = enemy(hp=0, alive=False)
        dead.pop('turn')
        result = comparison(enemy(), dead,
                            {'event': 'result', 'target': 9, 'target_hp_before': 4,
                             'target_hp_after': 0, 'target_alive_after': False, 'turn': 3})
        self.assertEqual(component_points(result, 'enemy_eliminated'), [1300])
        self.assertNotIn('enemy_kill_turn', result['missing_components'])

    def test_hp_zero_without_death_confirmation_or_unknown_target_is_not_a_kill(self):
        result = comparison(enemy(), {'event': 'result', 'target': 9, 'target_hp_before': 4,
                                       'target_hp_after': 0, 'turn': 3},
                            {'event': 'result', 'target': 99, 'target_hp_before': 4,
                             'target_hp_after': 0, 'target_alive_after': False, 'turn': 3})
        self.assertEqual(component_points(result, 'enemy_eliminated'), [])
        self.assertIn('enemy_death_confirmation', result['missing_components'])

    def test_original_friendly_mind_control_casualty_is_not_an_enemy_award(self):
        result = comparison(friendly(), enemy(id=1), enemy(id=1, hp=0, alive=False))
        self.assertEqual(component_points(result, 'enemy_eliminated'), [])

    def test_original_enemy_mind_control_does_not_make_it_a_soldier(self):
        result = comparison(enemy(), friendly(id=9, score_eligible=False),
                            enemy(hp=0, alive=False, turn=3))
        self.assertEqual(component_points(result, 'soldier_allowance'), [])
        self.assertEqual(component_points(result, 'enemy_eliminated'), [1300])

    def test_negative_or_missing_objective_and_enemy_turn_never_awards_max_points(self):
        result = comparison({'event': 'objective_completed', 'objective_id': 'goal', 'completion_turn': -1},
                            enemy(), {'event': 'result', 'target': 9, 'target_hp_before': 4,
                                      'target_hp_after': 0, 'target_alive_after': False, 'turn': -1})
        self.assertEqual(component_points(result, 'objective_completed'), [])
        self.assertEqual(component_points(result, 'enemy_eliminated'), [])
        self.assertIn('objective_completion_turn', result['missing_components'])
        self.assertIn('enemy_kill_turn', result['missing_components'])

    def test_comparison_can_be_complete_for_its_declared_public_observation_scope(self):
        result = comparison(friendly(), enemy(), enemy(hp=0, alive=False),
                            {'event': 'scoring_coverage', 'complete': True})
        self.assertEqual(result['status'], 'complete_for_comparison_convention')
        self.assertEqual(result['total'], 1500)
        self.assertIn('restart_penalties', result['excluded_native_components'])
        self.assertFalse(result['is_official_game_score'])

    def test_spawned_and_unknown_origin_are_distinguished(self):
        result = comparison(enemy(spawned=True), enemy(spawned=True, hp=0, alive=False))
        self.assertEqual(component_points(result, 'enemy_eliminated'), [0])
        result = comparison(enemy(spawned=None, reinforcement=None),
                            enemy(spawned=None, reinforcement=None, hp=0, alive=False))
        self.assertEqual(component_points(result, 'enemy_eliminated'), [1500])
        self.assertIn('enemy_spawn_reinforcement_origin', result['missing_components'])

    def test_unknown_enemy_uses_labelled_sdk_default_and_is_incomplete(self):
        result = comparison(enemy(template='UnobservedModEnemy'),
                            enemy(template='UnobservedModEnemy', hp=0, alive=False))
        awarded = next(c for c in result['components'] if c['kind'] == 'enemy_eliminated')
        self.assertEqual(awarded['points'], 500)
        self.assertEqual(awarded['rule_source'], 'sdk_structure_default')
        self.assertIn('enemy_runtime_override_not_observed', result['missing_components'])
        self.assertIsNone(result['total'])

    def test_victory_does_not_invent_objectives_and_explicit_side_goals_are_deduplicated(self):
        result = comparison(friendly())
        self.assertEqual(component_points(result, 'objective_completed'), [])
        goal = {'event': 'objective_completed', 'objective_id': 'side:1', 'completion_turn': 3}
        result = comparison(friendly(), goal, goal,
                            {'event': 'objective_completed', 'objective_id': 'main:1', 'completion_turn': 10})
        self.assertEqual(component_points(result, 'objective_completed'), [8000, 5000])

    def test_public_rescue_event_can_count_without_hidden_civilian_id(self):
        result = comparison({'event': 'civilian_rescued', 'civilian_id': 0, 'source': 'mission_event'},
                            {'event': 'civilian_rescued', 'civilian_id': 33},
                            {'event': 'civilian_rescued', 'civilian_id': 33})
        self.assertEqual(component_points(result, 'civilian_rescued'), [1000, 1000])

    def test_same_fixed_profile_is_applied_to_ordinary_and_legacy_missions(self):
        for mission in ('SabotageCC', 'ChallengeAbductionGasStation'):
            result = SCORING.score_session(events({'event': 'start', 'mission': mission}, friendly(),
                                                  {'event': 'end', 'outcome': 'win'}),
                                           {'mission': mission, 'initial_max_score': 999999})
            self.assertEqual(result['comparison']['profile_id'], 'wotc_legacy_observed_v2')
            self.assertIsNone(result['official']['cumulative_score'])
            self.assertIsNone(result['comparison']['total'])
            self.assertEqual(result['comparison']['observed_subtotal'], 0)

    def test_native_snapshots_and_delta_are_used_without_summing_opaque_ledger_fields(self):
        records = events({'event': 'game_score', 'source': 'legacy_runtime', 'phase': 'start',
                          'ladder_index': 1, 'ladder_rung': 2, 'cumulative_score': 8000, 'history': 200},
                         {'event': 'score_delta', 'score_id': 77, 'history': 201, 'added_points': 1500, 'ladder_bonus': 9000},
                         {'event': 'score_delta', 'score_id': 77, 'history': 201, 'added_points': 1500, 'ladder_bonus': 9000},
                         {'event': 'score_delta', 'score_id': 77, 'history': 202, 'added_points': 1600, 'ladder_bonus': 9000},
                         {'event': 'game_score', 'source': 'legacy_runtime', 'phase': 'finish',
                          'ladder_index': 1, 'ladder_rung': 2, 'cumulative_score': 6000, 'history': 203},
                         {'event': 'game_score', 'source': 'legacy_runtime', 'phase': 'finish',
                          'ladder_index': 1, 'ladder_rung': 3, 'cumulative_score': 30000})
        result = SCORING.official_observations(records)
        self.assertEqual(result['cumulative_score'], 6000)
        self.assertEqual(result['recording_delta'], -2000)
        self.assertEqual((result['from_history'], result['to_history']), (200, 203))
        self.assertEqual(len(result['score_events']), 2)
        self.assertEqual(result['other_stage_snapshots_ignored'], 1)

    def test_mid_session_native_score_does_not_claim_whole_mission_delta(self):
        result = SCORING.official_observations(events(
            {'event': 'game_score', 'source': 'legacy_runtime', 'phase': 'observe', 'cumulative_score': 10000}))
        self.assertEqual(result['cumulative_score'], 10000)
        self.assertIsNone(result['recording_delta'])

    def test_real_format_native_tables_scope_to_session_and_never_become_earned_score(self):
        table = '\n'.join([
            'XCom_Challenge: ScoreType(0): CMPT_None',
            'XCom_Challenge: MissionTypeObjectiveScoringValues[MissionType: GasStation StartingPoints: 10000 MinPoints: 5000 DecreasePerTurn: 1000 TurnOffset: 1]',
            'XCom_Challenge: ScoreType(1): NumObjectives: 1 MaxScore: 10000',
            "XCom_Challenge: ScoreType(2): Unit: 'Sectoid' EnemyScoring[StartingPoints: 1500 MinPoints: 1000 DecreasePerTurn: 100 TurnOffset: 1 SpawnedPoints: 0 ReinforcementPoints: 0 DisabledPoints: 1000 MinDisabledPoints: 1000] MaxScore: 11500",
            'XCom_Challenge: SoldierScoring[UninjuredBonus: 1000 NumSoldiers: 4] MaxScore: 15500',
            'XCom_Challenge: SoldierScoring[WoundedBonus: 5000 NumSoldiers: 4] MaxScore: 35500',
            'XCom_Challenge: TimeScoring[PointsPerInterval: 250 IntervalInSeconds: 60] TimeLimit: 0 MaxScore: 35500',
            'APXREC|v=1|session=gas|seq=1|event=start|mission=GasStation',
            'APXREC|v=1|session=gas|seq=2|event=end|outcome=win',
            'XCom_Challenge: ScoreType(0): CMPT_None',
            'XCom_Challenge: MissionTypeObjectiveScoringValues[MissionType: Cemetery StartingPoints: 10000 MinPoints: 5000 DecreasePerTurn: 1000 TurnOffset: 1]',
            'XCom_Challenge: ScoreType(1): NumObjectives: 1 MaxScore: 64000',
        ])
        report = LOG.analyze_logs([('Launch.log', table)])
        self.assertEqual(len(report['native_scoring_profiles']), 2)
        scoring = report['sessions'][0]['game_scoring']
        observed = scoring['native_rules_observed']
        self.assertEqual(observed['mission'], 'GasStation')
        self.assertEqual(observed['initial_max_score'], 35500)
        self.assertEqual(observed['soldier']['survival_bonus'], 5000)
        self.assertEqual(observed['time']['time_limit'], 0)
        self.assertEqual(scoring['official']['status'], 'not_recorded')
        self.assertIsNone(scoring['official']['cumulative_score'])
        self.assertIn('Native earned score was not recorded.', LOG.human_summary(report))
        self.assertIn('Comparison (wotc_legacy_observed_v2): partial', LOG.human_summary(report))

    def test_native_runtime_getters_augment_table_without_changing_comparison_profile(self):
        baseline = {'mission': 'GasStation', 'log_file': 'Launch.log', 'log_line': 3,
                    'objectives': [{'text_pool_index': 0, 'group_id': 0, 'line_index': 1,
                                    'starting_points': 10000}],
                    'enemies': {'Sectoid': {'starting_points': 1500}},
                    'soldier': {}, 'time': {}, 'initial_max_score': 46000}
        records = events(
            {'event': 'start', 'mission': 'GasStation', 'log_file': 'Launch.log', 'log_line': 20},
            {'event': 'score_rule', 'source': 'legacy_runtime', 'kind': 'soldier',
             'uninjured_bonus': 1000, 'survival_bonus': 5000, 'rescued_bonus': 1000, 'history': 30},
            {'event': 'score_rule', 'source': 'legacy_runtime', 'kind': 'enemy',
             'template': 'Sectopod', 'starting_points': 7500, 'min_points': 5000,
             'decrease_per_turn': 500, 'turn_offset': 1, 'history': 31},
            {'event': 'score_rule', 'source': 'legacy_runtime', 'kind': 'objective',
             'mission': 'GasStation', 'objective_id': 'GasStation:0:1:0',
             'text_pool_index': 0, 'group_id': 0, 'line_index': 1,
             'starting_points': 9000, 'min_points': 5000, 'history': 32},
            {'event': 'score_rule', 'source': 'legacy_runtime', 'kind': 'enemy',
             'template': 'Sectopod', 'starting_points': 8000, 'history': 33},
            {'event': 'score_rule', 'source': 'legacy_runtime', 'kind': 'time',
             'points_per_interval': 250, 'interval_seconds': 60, 'history': 34})
        rules = SCORING.native_rules_for_session(records, [baseline])
        self.assertEqual(rules['observed_sources'], ['engine_initialization_table', 'legacy_runtime_getters'])
        self.assertEqual(rules['initial_max_score'], 46000)
        self.assertEqual(rules['soldier']['survival_bonus'], 5000)
        self.assertEqual(rules['enemies']['Sectopod']['starting_points'], 8000)
        self.assertEqual(len(rules['objectives']), 1)
        self.assertEqual(rules['objectives'][0]['starting_points'], 9000)
        self.assertEqual(rules['time']['interval_seconds'], 60)
        self.assertEqual([r['starting_points'] for r in rules['runtime_observations']
                          if r.get('template') == 'Sectopod'], [7500, 8000])
        self.assertNotIn('Sectopod', baseline['enemies'])
        self.assertEqual(baseline['objectives'][0]['starting_points'], 10000)
        self.assertEqual(SCORING.score_session(records, rules)['comparison']['profile_id'],
                         'wotc_legacy_observed_v2')
        self.assertNotIn('Sectopod', SCORING.load_profile()['enemies'])

    def test_runtime_rules_work_without_startup_log_and_reject_other_mission_or_source(self):
        records = events(
            {'event': 'start', 'mission': 'GasStation'},
            {'event': 'score_rule', 'source': 'legacy_runtime', 'kind': 'enemy',
             'template': 'Viper', 'starting_points': 1500, 'history': 1},
            {'event': 'score_rule', 'source': 'legacy_runtime', 'kind': 'objective',
             'mission': 'Cemetery', 'starting_points': 90000},
            {'event': 'score_rule', 'source': 'planner', 'kind': 'soldier',
             'survival_bonus': 999999})
        rules = SCORING.native_rules_for_session(records, [])
        self.assertEqual(rules['observed_sources'], ['legacy_runtime_getters'])
        self.assertEqual(rules['enemies']['Viper']['starting_points'], 1500)
        self.assertEqual(rules['objectives'], [])
        self.assertEqual(rules['soldier'], {})
        self.assertIsNone(rules['initial_max_score'])
        self.assertIsNone(SCORING.official_observations(records)['cumulative_score'])
        self.assertIsNone(SCORING.native_rules_for_session(events({'event': 'start'}), []))

    def test_missing_records_and_pending_history_prevent_total(self):
        result = SCORING.comparison_score([
            {'seq': 1, 'event': 'start'}, {'seq': 3, 'event': 'phase', 'turn': 4},
            {'seq': 4, 'event': 'end', 'history_pending': 2}], SCORING.load_profile())
        self.assertIsNone(result['total'])
        self.assertIn('recording_sequence_gaps', result['missing_components'])
        self.assertIn('recording_started_after_first_turn', result['missing_components'])
        self.assertIn('pending_history_frames', result['missing_components'])


if __name__ == '__main__':
    unittest.main()
