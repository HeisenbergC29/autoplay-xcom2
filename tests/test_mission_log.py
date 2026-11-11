"""Recording summaries are based on observations, including incomplete logs."""
import importlib.util
import json
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest
import zipfile


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / 'tools/analyze-mission-log.py'
SPEC = importlib.util.spec_from_file_location('mission_log', TOOL)
LOG = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(LOG)


def record(seq, event, fields='', session='s1'):
    return f'[0003.11] AutoplayXCom2: APXREC|v=1|session={session}|seq={seq}|event={event}|decision=1' + ('|' + fields if fields else '')


class MissionLogTests(unittest.TestCase):
    def test_unclassified_ui_failure_does_not_override_final_native_victory(self):
        for marker in ('', '|critical=false', '|critical=unknown', '|critical=1'):
            with self.subTest(marker=marker):
                report = LOG.analyze_logs([('Launch.log', '\n'.join([
                    record(1, 'start', 'mission=SabotageCC'),
                    record(2, 'objective_failed',
                           'source=mission_ui_event|objective_id=ui:1' + marker),
                    record(3, 'game_score', 'source=challenge_runtime|mission_points_known=true'
                           '|mission_final=true|mission_points=700|phase=finish|history=20'),
                    record(4, 'end', 'outcome=win|history=20|history_pending=0'),
                ]))])
                session = report['sessions'][0]
                self.assertFalse(session['critical_objective_failed'])
                self.assertEqual(session['failed_objective_ids'], ['ui:1'])
                self.assertEqual(session['unclassified_failed_objective_ids'], ['ui:1'])
                self.assertEqual(session['attempt_verdict']['status'], 'pass')
                self.assertIn('criticality unverified', LOG.human_summary(report))
                self.assertNotIn('CRITICAL OBJECTIVE FAILURE', LOG.human_summary(report))

    def test_mixed_failures_separate_proven_critical_from_unclassified_ids(self):
        report = LOG.analyze_logs([('Launch.log', '\n'.join([
            record(1, 'start'),
            record(2, 'objective_failed', 'objective_id=ui:1|critical=false'),
            record(3, 'objective_failed', 'objective_id=required:2|critical=true'),
            record(4, 'objective_failed', 'objective_id=required:2|critical=true'),
        ]))])
        session = report['sessions'][0]
        self.assertEqual(session['failed_objective_ids'], ['required:2', 'ui:1'])
        self.assertEqual(session['critical_failed_objective_ids'], ['required:2'])
        self.assertEqual(session['unclassified_failed_objective_ids'], ['ui:1'])
        self.assertEqual(session['attempt_verdict']['status'], 'fail')
        critical_line = next(line for line in LOG.human_summary(report).splitlines()
                             if 'CRITICAL OBJECTIVE FAILURE' in line)
        self.assertNotIn('ui:1', critical_line)

    def test_conflicting_failure_records_cannot_certify_a_critical_verdict(self):
        lines = '\n'.join([
            record(1, 'start'),
            record(2, 'objective_failed', 'objective_id=x|critical=true'),
            record(2, 'objective_failed', 'objective_id=x|critical=false'),
        ])
        session = LOG.analyze_logs([('Launch.log', lines)])['sessions'][0]
        self.assertEqual(session['attempt_verdict']['status'], 'unknown')
        self.assertEqual(session['attempt_verdict']['reason'], 'conflicting_records')

    def test_failed_objective_is_critical_even_with_positive_native_score(self):
        session = LOG.analyze_logs([('Launch.log', '\n'.join([
            record(1, 'start', 'mission=SabotageTransmitter|difficulty=2'),
            record(2, 'objective_failed',
                   'source=mission_ui_event|critical=true|objective_id=SabotageTransmitter:3:1:0|objective_name=PlantBomb|turn=4'),
            record(3, 'game_score',
                   'source=legacy_runtime|ladder_index=1|ladder_rung=1|mission_points_known=true|mission_final=true|mission_points=700|phase=finish|history=20'),
            record(4, 'end', 'outcome=win|history=20|history_pending=0'),
        ]))])['sessions'][0]
        self.assertEqual(session['outcome'], 'win')
        self.assertTrue(session['critical_objective_failed'])
        self.assertEqual(len(session['failed_objective_ids']), 1)
        self.assertEqual(session['mission_points']['value'], 700)
        self.assertTrue(session['mission_points']['confirmed'])
        self.assertEqual(session['attempt_verdict']['status'], 'fail')
        self.assertEqual(session['attempt_verdict']['reason'], 'critical_objective_failed')
        report = LOG.analyze_logs([('Launch.log', '\n'.join([
            record(1, 'start', 'mission=SabotageTransmitter'),
            record(2, 'objective_failed', 'critical=true|objective_id=Transmitter:1'),
        ]))])
        self.assertIn('CRITICAL OBJECTIVE FAILURE', LOG.human_summary(report))

    def test_failed_objective_without_terminal_record_is_already_critical(self):
        session = LOG.analyze_logs([('Launch.log', '\n'.join([
            record(1, 'start', 'mission=SabotageTransmitter'),
            record(2, 'objective_failed', 'critical=true|objective_id=Transmitter:1'),
            record(3, 'hud_score', 'display=500/32950'),
        ]))])['sessions'][0]
        self.assertEqual(session['outcome'], 'unknown')
        self.assertTrue(session['critical_objective_failed'])
        self.assertEqual(session['attempt_verdict']['status'], 'fail')
        self.assertEqual(session['attempt_verdict']['reason'], 'critical_objective_failed')
        self.assertFalse(session['mission_points']['confirmed'])

    def test_no_failed_objective_does_not_falsely_make_a_loss_or_unknown(self):
        session = LOG.analyze_logs([('Launch.log', '\n'.join([
            record(1, 'start', 'mission=SabotageTransmitter'),
            record(2, 'objective_completed', 'objective_id=Transmitter:1'),
            record(3, 'end', 'outcome=unknown'),
        ]))])['sessions'][0]
        self.assertFalse(session['critical_objective_failed'])
        self.assertEqual(session['failed_objective_ids'], [])
        self.assertEqual(session['attempt_verdict']['status'], 'unknown')

    def test_grenade_scan_diagnostics_distinguish_range_from_blast_rejections(self):
        report = LOG.analyze_logs([('Launch.log', '\n'.join([
            record(1, 'start'),
            record(2, 'marker', 'kind=grenade_scan|details=unit=410 available=1 supported=1 evaluated=3 accepted=0 range=2 blast=1 last=outside_weapon_range'),
            record(3, 'marker', 'kind=grenade_scan|details=unit=428 available=1 supported=1 evaluated=4 accepted=0 range=3 blast=1 edge_centers=2 single_opportunities=1 single_rejected=2 last_single_min=3.0 last_single_max=4.0 last_single_hp=4.0 last_ordinary_score=27.6 range_reason=outside_weapon_range blast_reason=protected_unit_near_blast'),
        ]))])
        diagnostic = report['sessions'][0]['grenade_diagnostics']
        self.assertEqual(diagnostic['scans'], 2)
        self.assertEqual(diagnostic['totals']['range'], 5)
        self.assertEqual(diagnostic['totals']['blast'], 2)
        self.assertEqual(diagnostic['totals']['accepted'], 0)
        self.assertEqual(diagnostic['totals']['single_opportunities'], 1)
        self.assertEqual(diagnostic['totals']['single_rejected'], 2)
        self.assertNotIn('last_single_hp', diagnostic['totals'])
        self.assertEqual(diagnostic['reason_observations'],
                         {'outside_weapon_range': 1, 'protected_unit_near_blast': 1})
        self.assertIn('range=5', LOG.human_summary(report))

    def test_preflight_grenade_rejection_does_not_invent_a_dispatched_grenade(self):
        lines = [
            record(1, 'start', 'mission=Gatecrasher|difficulty=2'),
            record(2, 'marker', 'kind=area_revalidation_rejected|details=unit=1 reason=landing_changed evaluation_reason=none'),
            record(3, 'marker', 'kind=area_revalidation_rejected|details=unit=1 reason=fresh_impact_rejected evaluation_reason=protected_unit'),
            record(4, 'chosen', 'kind=action|unit=1|ability=Overwatch|accepted=true'),
            record(5, 'end', 'outcome=loss'),
        ]
        report = LOG.analyze_logs([('backup.log', '\n'.join(lines)),
                                   ('Launch.log', '\n'.join(lines))])
        session = report['sessions'][0]
        self.assertEqual(report['duplicate_records'], len(lines))
        self.assertEqual(session['grenade_preparation'], {
            'preview_rejections': 2,
            'reasons': {'fresh_impact_rejected': 1, 'landing_changed': 1},
        })
        self.assertEqual(session['accepted_actions'], 1)
        self.assertEqual(session['rejected_actions'], 0)
        self.assertNotIn('grenade', session['abilities'])
        self.assertIn('rejected before dispatch=2', LOG.human_summary(report))

    def test_native_false_followed_by_matching_turn_confirmation_is_not_failure(self):
        report = LOG.analyze_logs([('Launch.log', '\n'.join([
            record(1, 'start'),
            record(2, 'marker', 'kind=end_turn_requested|details=player=2 turn=3 history=50 native_return=False'),
            record(3, 'marker', 'kind=end_turn_confirmed|details=player=2 turn=3 history=51 evidence=skip_turn_history'),
            record(4, 'end', 'outcome=win'),
        ]))])
        turn = report['sessions'][0]['end_turn_diagnostics']
        self.assertEqual(turn['requested'], 1)
        self.assertEqual(turn['confirmed'], 1)
        self.assertEqual(turn['native_false_confirmed'], 1)
        self.assertEqual(turn['unresolved_after_timeout'], 0)
        self.assertEqual(turn['pending_without_confirmation'], 0)
        self.assertEqual(turn['evidence'], {'skip_turn_history': 1})
        self.assertFalse(any('timed out' in warning for warning in report['sessions'][0]['warnings']))
        self.assertIn('native false but confirmed=1', LOG.human_summary(report))

    def test_timeout_then_late_confirmation_is_recorded_as_recovered_ticket(self):
        session = LOG.analyze_logs([('Launch.log', '\n'.join([
            record(1, 'start'),
            record(2, 'marker', 'kind=end_turn_requested|details=player=2 turn=8 history=54 native_return=False'),
            record(3, 'marker', 'kind=end_turn_unconfirmed|details=player=2 turn=8 history=54 request_history=54'),
            record(4, 'marker', 'kind=end_turn_confirmed|details=player=2 turn=8 history=55 evidence=turn_transition'),
            record(5, 'end', 'outcome=loss'),
        ]))])['sessions'][0]
        turn = session['end_turn_diagnostics']
        self.assertEqual(turn['unconfirmed_markers'], 1)
        self.assertEqual(turn['confirmed_after_timeout'], 1)
        self.assertEqual(turn['native_false_confirmed'], 1)
        self.assertEqual(turn['unresolved_after_timeout'], 0)
        self.assertFalse(any('timed out without later' in w for w in session['warnings']))

    def test_expired_turn_without_confirmation_remains_unresolved_not_native_rejected(self):
        session = LOG.analyze_logs([('Launch.log', '\n'.join([
            record(1, 'start'),
            record(2, 'marker', 'kind=end_turn_requested|details=player=2 turn=4 history=97 native_return=False'),
            record(3, 'marker', 'kind=end_turn_unconfirmed|details=player=2 turn=4 history=97 request_history=97'),
            record(4, 'end', 'outcome=unknown'),
        ]))])['sessions'][0]
        turn = session['end_turn_diagnostics']
        self.assertEqual(turn['requested'], 1)
        self.assertEqual(turn['unresolved_after_timeout'], 1)
        self.assertEqual(turn['confirmed'], 0)
        self.assertEqual(turn['native_false_confirmed'], 0)
        self.assertTrue(any('not proof of a native rejection' in w for w in session['warnings']))

    def test_points_are_always_explicitly_labeled_by_certainty_per_mission(self):
        first = '\n'.join([
            record(1, 'start', 'mission=GasStation|difficulty=2|history=1'),
            record(2, 'game_score', 'source=legacy_runtime|ladder_index=1|ladder_rung=1|mission_points_known=true|mission_final=true|mission_points=-12600|phase=finish|history=20'),
            record(3, 'end', 'outcome=loss|history=20|history_pending=0'),
        ])
        second = '\n'.join([
            record(1, 'start', 'mission=BloodKiller|difficulty=2', session='s2'),
            record(2, 'hud_score', 'display=700/32950', session='s2'),
            record(3, 'score_delta', 'scoring_type=CMPT_TotalScore|added_points=700', session='s2'),
            record(4, 'end', 'outcome=loss', session='s2'),
        ])
        report = LOG.analyze_logs([('Launch.log', first + '\n' + second)])
        by_mission = {s['mission']: s for s in report['sessions']}
        self.assertEqual(by_mission['GasStation']['mission_points'],
                         {'value': -12600, 'confirmed': True, 'source': 'native_mission_points',
                          'status': 'final_native_observation'})
        self.assertEqual(by_mission['BloodKiller']['mission_points']['value'], 700)
        self.assertFalse(by_mission['BloodKiller']['mission_points']['confirmed'])
        self.assertIn('mission=GasStation, difficulty=2, outcome=loss, mission points=-12600 (confirmed',
                      LOG.human_summary(report))
        self.assertIn('mission=BloodKiller, difficulty=2, outcome=loss, mission points=+700 (provisional',
                      LOG.human_summary(report))
        self.assertEqual(by_mission['BloodKiller']['attempt_verdict']['status'], 'fail')

    def test_result_health_proves_elimination_without_a_dead_visibility_snapshot(self):
        report = LOG.analyze_logs([('Launch.log', '\n'.join([
            record(1, 'start'),
            record(2, 'unit', 'id=9|scope=visible_enemy|hp=4|alive=true'),
            record(3, 'result', 'source=1|target=9|hit=eHit_Success|target_hp_before=4|target_hp_after=0'),
            record(4, 'result_target', 'source=1|target=9|hit=eHit_Success|target_hp_before=4|target_hp_after=0'),
            record(5, 'visibility_lost', 'id=9'),
        ]))])
        session = report['sessions'][0]
        self.assertEqual(session['observed_deaths'], {})
        self.assertEqual(session['confirmed_target_eliminations'], {'visible_enemy': 1})

    def test_real_fname_casing_does_not_hide_five_overwatch_orders(self):
        lines = [record(1, 'start', 'mission=SabotageCC|difficulty=3')]
        for sequence, spelling in enumerate(['overwatch', 'Overwatch', 'OVERWATCH', 'overwatch', 'overwatch'], 2):
            lines.append(record(sequence, 'chosen', f'kind=action|unit=1|ability={spelling}|accepted=True'))
        lines.append(record(7, 'end', 'reason=tactical_game_ended|outcome=unknown'))
        session = LOG.analyze_logs([('Launch.log', '\n'.join(lines))])['sessions'][0]
        self.assertEqual(session['action_families'], {'overwatch': 5})
        self.assertEqual(session['abilities']['overwatch'], 3)
        self.assertEqual(session['abilities']['OVERWATCH'], 1)
        self.assertTrue(any('confirmed native mission result' in warning for warning in session['warnings']))
        for spelling, family in [('hunkerDOWN', 'hunker'), ('THROWGRENADE', 'grenade'),
                                 ('placeevaczone', 'evacuation'), ('reload', 'reload'),
                                 ('aidprotocol', 'support'), ('LONGWATCH', 'overwatch')]:
            with self.subTest(spelling=spelling):
                self.assertEqual(LOG.action_family(spelling), family)

    def test_autoplay_orders_and_friendly_or_incoming_results_are_distinct(self):
        session = LOG.analyze_logs([('Launch.log', '\n'.join([
            record(1, 'start'),
            record(2, 'unit', 'id=1|scope=friendly|hp=4|alive=true'),
            record(3, 'unit', 'id=9|scope=visible_enemy|hp=4|alive=true'),
            record(4, 'chosen', 'kind=action|unit=1|ability=overwatch|accepted=true'),
            record(5, 'result', 'source=1|target=9|ability=OverwatchShot|hit=eHit_Miss'),
            record(6, 'result', 'source=9|target=1|ability=StandardShot|hit=eHit_Miss'),
            record(7, 'result', 'source=0|target=1|ability=unseen_attack|hit=eHit_Success|source_scope=unseen_other'),
            record(8, 'visibility_lost', 'id=9'),
        ]))])['sessions'][0]
        self.assertEqual(session['accepted_actions'], 1)
        self.assertEqual(session['recorded_misses'], 2)
        self.assertEqual(session['recorded_misses_by_source'],
                         {'friendly': 1, 'unseen_other': 0, 'visible_enemy': 1})
        self.assertEqual(session['visibility_loss_events'], 1)

    def test_dedicated_interrupted_event_counts_without_counting_a_miss(self):
        session = LOG.analyze_logs([('Launch.log', '\n'.join([
            record(1, 'start'),
            record(2, 'interrupted', 'source=1|target=9|ability=StandardShot'),
            record(3, 'result', 'source=1|target=9|ability=StandardShot|hit=eHit_Success|interruption=eInterruptionStatus_Resume'),
        ]))])['sessions'][0]
        self.assertEqual(session['interrupted_result_frames'], 1)
        self.assertEqual(session['recorded_misses'], 0)
        self.assertEqual(session['hit_results'], {'eHit_Success': 1})

    def test_known_outcome_can_still_have_incomplete_action_history(self):
        report = LOG.analyze_logs([('Launch.log', '\n'.join([
            record(1, 'start'),
            record(2, 'end', 'outcome=loss|history_pending=12'),
        ]))])
        session = report['sessions'][0]
        self.assertEqual(session['outcome'], 'loss')
        self.assertTrue(any('12 history frames' in warning for warning in session['warnings']))

    def test_available_unhandled_commands_are_distinct_from_passive_abilities(self):
        report = LOG.analyze_logs([('Launch.log', '\n'.join([
            record(1, 'start'),
            record(2, 'ability', 'unit=1|ability=Inspire|code=AA_Success|input=true|handler=unhandled'),
            record(3, 'ability', 'unit=1|ability=PassiveBuff|code=AA_Success|input=false|handler=unhandled'),
            record(4, 'ability', 'unit=1|ability=UnavailableSkill|code=AA_CannotAfford_ActionPoints|input=true|handler=unhandled'),
            record(5, 'chosen', 'kind=action|unit=1|ability=LongWatch|accepted=true'),
            record(6, 'chosen', 'kind=action|unit=2|ability=AidProtocol|accepted=true'),
        ]))])
        session = report['sessions'][0]
        self.assertEqual(session['unsupported_abilities'], {'Inspire': 1})
        self.assertEqual(session['action_families'], {'overwatch': 1, 'support': 1})

    def test_realistic_decisions_defense_results_and_own_health_changes(self):
        lines = [
            record(1, 'start', 'player=1|mission=Gatecrasher|difficulty=2|history=7'),
            record(2, 'unit', 'id=1|scope=friendly|hp=5|max_hp=5|alive=true|ap=2|ammo=3'),
            record(3, 'candidate', 'kind=action|unit=1|ability=StandardShot|target=9|score=12.5|chance=20'),
            record(4, 'chosen', 'kind=action|unit=1|ability=Overwatch|target=1|score=24|accepted=true'),
            record(5, 'result', 'source=1|target=9|ability=OverwatchShot|hit=eHit_Miss|history=10'),
            record(6, 'unit', 'id=1|scope=friendly|hp=2|max_hp=5|alive=true|ap=0|ammo=2'),
            record(7, 'chosen', 'kind=action|unit=1|ability=HunkerDown|accepted=true'),
            record(8, 'chosen', 'kind=area|unit=1|ability=ThrowGrenade|accepted=true'),
            record(9, 'end', 'reason=MissionComplete|outcome=loss'),
        ]
        report = LOG.analyze_logs([('Launch.log', '\n'.join(lines))])
        session = report['sessions'][0]
        self.assertEqual((report['record_count'], session['outcome']), (9, 'loss'))
        self.assertEqual(session['action_families'], {'overwatch': 1, 'hunker': 1, 'grenade': 1})
        self.assertEqual(session['recorded_misses'], 1)
        self.assertEqual(session['observed_hp_loss'], {'friendly': 3})
        self.assertEqual(session['events']['candidate'], 1)
        self.assertEqual(session['warnings'], [])

    def test_interruption_frames_are_not_missed_shots_or_duplicate_rolls(self):
        report = LOG.analyze_logs([('Launch.log', '\n'.join([
            record(1, 'start'),
            record(2, 'result', 'source=1|target=9|ability=StandardShot|hit=eHit_Miss|interruption=eInterruptionStatus_Interrupt'),
            record(3, 'result', 'source=1|target=9|ability=StandardShot|hit=eHit_Success|interruption=eInterruptionStatus_Resume'),
        ]))])
        session = report['sessions'][0]
        self.assertEqual(session['hit_results'], {'eHit_Success': 1})
        self.assertEqual(session['recorded_misses'], 0)
        self.assertEqual(session['interrupted_result_frames'], 1)

    def test_visibility_loss_is_not_a_kill(self):
        report = LOG.analyze_logs([('Launch.log', '\n'.join([
            record(1, 'start'),
            record(2, 'unit', 'id=9|scope=visible_enemy|hp=4|alive=true|ap=-1|ammo=-1'),
            record(3, 'visibility_lost', 'id=9'),
        ]))])
        session = report['sessions'][0]
        self.assertEqual(session['observed_deaths'], {})
        self.assertEqual(session['outcome'], 'unknown')
        self.assertTrue(any('No end record' in text for text in session['warnings']))

    def test_multiple_sessions_and_overlap_logs_are_deduplicated(self):
        first = record(1, 'start')
        report = LOG.analyze_logs([
            ('Launch-backup.log', first),
            ('Launch.log', first + '\n' + record(2, 'end', 'outcome=win') + '\n' + record(1, 'start', session='s2')),
        ])
        self.assertEqual(report['record_count'], 3)
        self.assertEqual(report['duplicate_records'], 1)
        self.assertEqual([entry['session'] for entry in report['sessions']], ['s1', 's2'])
        self.assertEqual(report['sessions'][0]['outcome'], 'win')

    def test_gap_truncation_unknown_versions_and_conflicts_are_visible(self):
        text = '\n'.join([
            record(3, 'unit', 'id=1|scope=friendly|hp=2|alive=true'),
            record(5, 'limit'),
            record(5, 'end', 'outcome=win'),
            'APXREC|v=1|session=s1|seq=',
            'APXREC|v=2|session=s1|seq=9|event=start',
        ])
        report = LOG.analyze_logs([('Launch.log', text)])
        self.assertEqual(len(report['malformed_records']), 3)
        session = report['sessions'][0]
        self.assertEqual(session['outcome'], 'unknown')
        self.assertTrue(any('sequence numbers' in text for text in session['warnings']))
        self.assertTrue(any('record limit' in text for text in session['warnings']))
        self.assertTrue(any('start record' in text for text in session['warnings']))

    def test_rejected_actions_are_not_reported_as_used(self):
        report = LOG.analyze_logs([('Launch.log', '\n'.join([
            record(1, 'start'),
            record(2, 'chosen', 'kind=action|unit=1|ability=Evac|accepted=false'),
        ]))])
        session = report['sessions'][0]
        self.assertEqual(session['abilities'], {})
        self.assertEqual((session['accepted_actions'], session['rejected_actions']), (0, 1))

    def test_explicit_unsupported_abilities_are_reported_separately(self):
        report = LOG.analyze_logs([('Launch.log', '\n'.join([
            record(1, 'start'),
            record(2, 'candidate', 'kind=unsupported|unit=1|ability=SmokeGrenade'),
            record(3, 'candidate', 'kind=action|unit=1|ability=StandardShot|score=40'),
        ]))])
        self.assertEqual(report['sessions'][0]['unsupported_abilities'], {'SmokeGrenade': 1})
        self.assertIn('SmokeGrenade', LOG.human_summary(report))

    def test_utf16_logs_and_report_zip_without_extraction(self):
        with tempfile.TemporaryDirectory() as temporary:
            archive = Path(temporary) / 'report.zip'
            with zipfile.ZipFile(archive, 'w') as output:
                output.writestr('Logs/Launch.log', (record(1, 'start') + '\n').encode('utf-16'))
                output.writestr('manifest.json', '{}')
                output.writestr('Save/fixture.XComSave', b'not read by analyzer')
            logs = LOG.read_logs(archive)
            self.assertEqual(LOG.analyze_logs(logs)['record_count'], 1)
            self.assertEqual(list(Path(temporary).iterdir()), [archive])

    def test_unsafe_zip_paths_and_links_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            archive = Path(temporary) / 'report.zip'
            for filename in ['../Launch.log', '/Launch.log', 'C:/Launch.log']:
                with self.subTest(filename=filename):
                    with zipfile.ZipFile(archive, 'w') as output:
                        output.writestr(filename, record(1, 'start'))
                    with self.assertRaisesRegex(ValueError, 'Unsafe'):
                        LOG.read_logs(archive)
            with zipfile.ZipFile(archive, 'w') as output:
                link = zipfile.ZipInfo('Logs/Launch.log')
                link.external_attr = (stat.S_IFLNK | 0o777) << 16
                output.writestr(link, 'target')
            with self.assertRaisesRegex(ValueError, 'symbolic links'):
                LOG.read_logs(archive)

    def test_duplicate_or_invalid_fields_do_not_silently_override(self):
        with self.assertRaises(ValueError):
            LOG.parse_record(record(1, 'start', 'seq=8'))
        with self.assertRaises(ValueError):
            LOG.parse_record(record(1, 'start', 'BAD FIELD=value'))

    def test_cli_outputs_json_and_refuses_existing_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'Launch.log'
            output = Path(temporary) / 'mission.json'
            path.write_text(record(1, 'start') + '\n' + record(2, 'end', 'outcome=win'))
            command = [sys.executable, str(TOOL), str(path), '--json', str(output)]
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('outcome=win', result.stdout)
            before = output.read_bytes()
            self.assertEqual(json.loads(before)['sessions'][0]['outcome'], 'win')
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(output.read_bytes(), before)

    def test_no_recording_is_not_a_successful_analysis(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'Launch.log'
            path.write_text('Log: ordinary engine message\n')
            result = subprocess.run([sys.executable, str(TOOL), str(path)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 1)
            self.assertIn('No APXREC', result.stdout)


if __name__ == '__main__':
    unittest.main()
