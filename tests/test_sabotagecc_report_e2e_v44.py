"""Run the report CLI on synthetic v44 observations of a SabotageCC recovery."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / 'tools' / 'analyze-mission-log.py'


def session(session_id, rows):
    """Encode an ordered sequence of independent APXREC decisions from one mission."""
    return '\n'.join(
        f'AutoplayXCom2: APXREC|v=1|session={session_id}|seq={seq}|decision={decision}|event={fields}'
        for seq, (decision, fields) in enumerate(rows, 1)
    )


class SabotageRecoveryReportEndToEnd(unittest.TestCase):
    """Exercise the installed report format through the CLI and its JSON output."""

    def test_success_and_manual_loss_keep_proposals_distinct_from_accepted_orders(self):
        """A manual plant result in the second run cannot supply the missing chosen order."""
        common = [
            (0, 'start|revision=mission-report-v45|mission=SabotageCC'),
            (97, 'phase|phase=autoplay|turn=22'),
            (97, 'ability|unit=7|ability=Interact_PlantBomb|code=AA_NoTargets|targets=0'),
            (97, 'marker|kind=objective_recovery_scan|details=unit=7 found=True'),
            (97, 'marker|kind=objective_recovery_candidate|details=unit=7 end_x=30 end_y=35 end_z=1'),
        ]
        recovered = session('recovered', common + [
            (97, 'chosen|kind=move|unit=7|x=30|y=35|z=1|accepted=True'),
            (98, 'result|ability=StandardMove|source=7|source_scope=friendly|history=420'),
            (98, 'ability|unit=7|ability=Interact_PlantBomb|code=AA_Success|targets=1'),
            (98, 'chosen|kind=action|unit=7|ability=Interact_PlantBomb|accepted=True'),
            (99, 'result|ability=Interact_PlantBomb|source=7|source_scope=friendly|history=424'),
            (99, 'objective_completed|source=mission_ui_event|objective_name=Plant X4'),
            (99, 'game_score|source=challenge_runtime|mission_points_known=True|mission_final=True'
                 '|mission_points=600|phase=finish|history=425'),
            (99, 'end|outcome=win|history=425|history_pending=0'),
        ])
        assisted = session('assisted', common + [
            (97, 'chosen|kind=move|unit=7|x=30|y=35|z=1|accepted=False'),
            (98, 'phase|phase=manual|turn=22'),
            (98, 'result|ability=StandardMove|source=7|source_scope=friendly|history=401'),
            (98, 'result|ability=Interact_PlantBomb|source=7|source_scope=friendly|history=404'),
            (99, 'objective_failed|source=mission_ui_event|objective_name=Neutralize all enemies'),
            (99, 'end|outcome=loss|history=450|history_pending=0'),
        ])

        with tempfile.TemporaryDirectory() as tmp:
            bundle = Path(tmp) / 'report.zip'
            report = Path(tmp) / 'analysis.json'
            with zipfile.ZipFile(bundle, 'w') as archive:
                archive.writestr('Logs/Launch.log', recovered)
                archive.writestr('Logs/Launch-backup.log', assisted)
            subprocess.run([sys.executable, str(TOOL), str(bundle), '--json', str(report)],
                           cwd=tmp, capture_output=True, text=True, check=True)
            parsed = json.loads(report.read_text(encoding='utf-8'))

        self.assertEqual([], parsed['malformed_records'])
        runs = {run['session']: run for run in parsed['sessions']}
        win, loss = runs['recovered'], runs['assisted']
        self.assertEqual((2, 1, {'Interact_PlantBomb': 1}),
                         (win['accepted_actions'], win['moves'], win['abilities']))
        self.assertEqual('pass', win['attempt_verdict']['status'])
        self.assertTrue(win['mission_points']['confirmed'])
        self.assertEqual(600, win['mission_points']['value'])
        # Both recordings contain plant results. Only the first records a new
        # legal target between the accepted move and the accepted plant order.
        self.assertEqual([(97, 'chosen', 'move'), (98, 'ability', 'Interact_PlantBomb'),
                          (98, 'chosen', 'Interact_PlantBomb')], [
            (row['decision'], row['event'], row.get('ability', row.get('kind')))
            for row in win['records']
            if row['event'] == 'chosen' or (row['event'] == 'ability' and row['code'] == 'AA_Success')
        ])
        self.assertEqual((0, 0, 1, {}), (loss['accepted_actions'], loss['moves'],
                                        loss['rejected_actions'], loss['abilities']))
        self.assertEqual('fail', loss['attempt_verdict']['status'])
        self.assertFalse(loss['mission_points']['confirmed'])
        self.assertTrue(any(row.get('phase') == 'manual' for row in loss['records']))
        self.assertEqual(2, loss['events']['result'])
