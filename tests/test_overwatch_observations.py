"""Exercise stock Overwatch observations in the report and its CLI."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from test_mission_log import LOG, TOOL, record


class OverwatchObservationTests(unittest.TestCase):
    """Orders, friendly arming results and resolved shots have distinct provenance."""

    def test_explicit_sources_and_exact_stock_ability_names(self):
        """Count manual or automatic friendly results even when no autoplay order exists."""
        results = [
            {'ability': 'sNiPeRrIfLeOvErWaTcH', 'source_scope': 'friendly'},
            {'ability': 'LongWatch', 'source_scope': 'friendly'},
            {'ability': 'LONGWATCHSHOT', 'source_scope': 'friendly', 'hit': 'eHit_Graze'},
            {'ability': 'PistolOverwatchShot', 'source_scope': 'friendly'},
            {'ability': 'OverwatchShot', 'source_scope': 'visible_enemy', 'hit': 'eHit_Miss'},
            {'ability': 'unseen_attack', 'source_scope': 'unseen_other'},
            {'ability': 'OverwatchShot', 'source': 5},
            {'ability': 'Overwatch', 'source_scope': 'unknown'},
            {'ability': 'KillZoneShot', 'source_scope': 'friendly', 'hit': 'eHit_Success'},
            {'ability': 'ReturnFire', 'source_scope': 'friendly'},
        ]
        self.assertEqual({
            'accepted_autoplay_orders': 0,
            'observed_friendly_arm_results': 2,
            'observed_friendly_shot_results': 2,
            'friendly_shot_outcomes': {'eHit_Graze': 1, 'unknown': 1},
            'unknown_scope_results': 2,
        }, LOG.summarize_overwatch(0, results))

    def test_partial_recording_with_orders_and_no_observed_results(self):
        """An accepted stance can be the last observation before a log is cut."""
        self.assertEqual({
            'accepted_autoplay_orders': 1,
            'observed_friendly_arm_results': 0,
            'observed_friendly_shot_results': 0,
            'friendly_shot_outcomes': {},
            'unknown_scope_results': 0,
        }, LOG.summarize_overwatch(1, []))

    def test_cli_reports_orders_manual_reserves_and_only_resolved_shots(self):
        """Run the installed CLI on a partial mission, including interrupt and manual frames."""
        rows = [
            record(1, 'start', 'mission=ChallengeAbductionGasStation'),
            record(2, 'chosen', 'kind=action|unit=5|ability=OvErWaTcH|accepted=true'),
            record(3, 'result', 'ability=overwatch|source=5|source_scope=friendly'),
            record(4, 'chosen', 'kind=action|unit=7|ability=longwatch|accepted=false'),
            record(5, 'phase', 'phase=manual|turn=2'),
            record(6, 'result', 'ability=pistoloverwatch|source=7|source_scope=friendly'),
            record(7, 'interrupted', 'ability=OverwatchShot|source=5|source_scope=friendly'),
            record(8, 'result', 'ability=OverwatchShot|source=5|source_scope=friendly'
                   '|hit=eHit_Success|interruption=eInterruptionStatus_Interrupt'),
            record(9, 'result', 'ability=overwatchshot|source=5|source_scope=friendly'
                   '|hit=eHit_Miss|interruption=eInterruptionStatus_Resume'),
            record(10, 'result', 'ability=pistoloverwatchshot|source=7|source_scope=friendly'
                   '|hit=eHit_Graze|interruption=eInterruptionStatus_None'),
            record(11, 'result', 'ability=OverwatchShot|source=99|source_scope=visible_enemy'
                   '|hit=eHit_Success|interruption=eInterruptionStatus_None'),
            record(12, 'result', 'ability=OverwatchShot|source=7|hit=eHit_Miss'),
        ]
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'Launch.log'
            output = Path(directory) / 'report.json'
            source.write_text('\n'.join(rows), encoding='utf-8')
            proc = subprocess.run([sys.executable, str(TOOL), str(source), '--json', str(output)],
                                  check=True, capture_output=True, text=True)
            mission, = json.loads(output.read_text(encoding='utf-8'))['sessions']
        self.assertEqual({
            'accepted_autoplay_orders': 1,
            'observed_friendly_arm_results': 2,
            'observed_friendly_shot_results': 2,
            'friendly_shot_outcomes': {'eHit_Graze': 1, 'eHit_Miss': 1},
            'unknown_scope_results': 1,
        }, mission['overwatch_observations'])
        self.assertIn('autoplay orders=1, friendly arm results=2, friendly shot results=2', proc.stdout)
        self.assertIn('eHit_Graze=1, eHit_Miss=1', proc.stdout)
        self.assertEqual('unknown', mission['outcome'])
