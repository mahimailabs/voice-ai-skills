import json
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from metrics_report import summarize


class ReportTests(unittest.TestCase):
    def test_snapshots_merge_without_double_counting_or_zero_filling(self):
        def row(turn, **values):
            return 'voice_metrics '+json.dumps({'scope':'test','role':'turn','turn_id':turn,**values})
        report = summarize([row('1',e2e_latency=1), row('1',tts_node_ttfb=.2),
                            row('2',e2e_latency=2), row('3',e2e_latency=0)])
        self.assertEqual(report[0]['turns'], 3)
        metrics = report[0]['metrics']
        self.assertEqual(metrics['e2e_latency'], {'samples':3,'missing':0,'p50':1,'p95':2})
        self.assertEqual(metrics['tts_node_ttfb']['missing'], 2)
        self.assertIsNone(metrics['transcription_delay']['p95'])

    def test_scopes_and_roles_do_not_mix(self):
        rows = [{'scope':scope,'role':role,'turn_id':'same','e2e_latency':1}
                for scope, role in [('livekit','user'),('livekit','assistant'),('pipecat','turn')]]
        report = summarize(['voice_metrics '+json.dumps(row) for row in rows])
        self.assertEqual(len(report), 3)
