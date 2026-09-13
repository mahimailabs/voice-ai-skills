"""Server-side timing estimates, not caller-device or PSTN latency.

See README.md for definitions. Snapshot updates share a turn ID; merge before
computing percentiles. No transcript, tool arguments, or audio is logged.
"""
import logging
import uuid
from collections import deque

from pipecat.frames.frames import (
    BotStartedSpeakingFrame, LLMContextFrame, MetricsFrame, TranscriptionFrame,
    VADUserStartedSpeakingFrame, VADUserStoppedSpeakingFrame,
)
from pipecat.metrics.metrics import TTFBMetricsData
from pipecat.observers.base_observer import BaseObserver
from clinic import log_metrics


class VoiceMetricsObserver(BaseObserver):
    def __init__(self, llm_name, tts_name):
        super().__init__()
        self.llm_name, self.tts_name = llm_name, tts_name
        self.seen, self.order = set(), deque()
        self.session_id = uuid.uuid4().hex
        self.turn = 0
        self.responding = False
        self.end = self.transcript = None
        self.values = {}

    async def on_push_frame(self, data):
        frame = data.frame
        if frame.id in self.seen:
            return
        self.seen.add(frame.id)
        self.order.append(frame.id)
        if len(self.order) > 4096:
            self.seen.discard(self.order.popleft())
        now = data.timestamp / 1_000_000_000
        if isinstance(frame, VADUserStartedSpeakingFrame):
            if not self.turn or self.responding:
                self.turn += 1
                self.values = {}
                self.transcript = None
            self.end = None
            self.responding = False
        elif isinstance(frame, VADUserStoppedSpeakingFrame):
            self.end = now - frame.stop_secs  # Remove the configured VAD silence window.
        elif isinstance(frame, TranscriptionFrame):
            self.transcript = now
        elif isinstance(frame, LLMContextFrame) and self.turn and not self.responding:
            self.responding = True
            if self.end is not None:
                self.values['end_of_turn_delay'] = max(0, now - self.end)
        elif isinstance(frame, MetricsFrame) and self.responding:
            for metric in frame.data:
                if isinstance(metric, TTFBMetricsData):
                    name = {self.llm_name: 'llm_node_ttft', self.tts_name: 'tts_node_ttfb'}.get(metric.processor)
                    if name:
                        self.values.setdefault(name, metric.value)
        elif isinstance(frame, BotStartedSpeakingFrame) and self.responding and self.end is not None:
            self.values.setdefault('e2e_latency', max(0, now - self.end))
        else:
            return
        if self.end is not None and self.transcript is not None:
            self.values['transcription_delay'] = max(0, self.transcript - self.end)
        if self.responding:
            log_metrics(logging.getLogger('clinic-agent'), turn_id=f'{self.session_id}:{self.turn}',
                        role='turn', metrics=self.values, scope='pipecat_server_estimate_seconds')
