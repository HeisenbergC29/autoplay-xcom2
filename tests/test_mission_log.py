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
