import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Optional

import aiortc
from vision_agents.core.processors import VideoProcessor
from vision_agents.core.utils.video_forwarder import VideoForwarder

logger = logging.getLogger(__name__)


@dataclass
class PersonState:
    """Tracks the state of a detected person across frames."""

    person_id: int
    first_seen: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)
    position: str = "center"      
    facing_camera: bool = True
    pose_description: str = ""
    consecutive_away_frames: int = 0


class SocialCueProcessor(VideoProcessor):
    """
    Processes video frames to extract social context.

    Works alongside YOLO — YOLO provides raw detections (bounding boxes,
    pose keypoints), and this processor maintains state and generates
    human-readable scene summaries fed to the LLM.
    """

    @property
    def name(self) -> str:
        return "social_cue_processor"

    def __init__(self, fps: int = 3):
        """
        Args:
            fps: Frames per second to process. 3–5 is ideal for social cues
                 since faces don't change that fast.
        """
        self.fps = fps
        self.frame_count = 0
        self.tracked_people: dict[int, PersonState] = {}
        self.previous_person_count = 0
        self.scene_context: str = ""
        self.last_significant_change: float = 0.0
        self._lock = asyncio.Lock()
        self._running = False

    async def process_video(
        self,
        track: aiortc.VideoStreamTrack,
        participant_id: Optional[str],
        shared_forwarder: Optional[VideoForwarder] = None,
    ) -> None:
        """Register frame handler with the shared video forwarder."""
        self._running = True
        if shared_forwarder:
            shared_forwarder.add_frame_handler(
                self._analyze_frame,
                fps=float(self.fps),
                name="social_cue_analyzer",
            )

    async def _analyze_frame(self, frame) -> None:
        """
        Analyze a video frame for social cues.

        Runs on every Nth frame (based on fps setting). Updates tracked
        person state and generates context summaries for the LLM.
        """
        async with self._lock:
            self.frame_count += 1

            # Every 15 frames (~5 seconds at 3 fps), refresh the scene summary
            if self.frame_count % 15 == 0:
                self._generate_scene_summary()

    def _generate_scene_summary(self) -> None:
        """Generate a human-readable scene summary for the LLM context."""
        now = time.time()
        active_people = {
            pid: state
            for pid, state in self.tracked_people.items()
            if now - state.last_seen < 5  # Active in the last 5 seconds
        }
        person_count = len(active_people)

        if person_count != self.previous_person_count:
            diff = person_count - self.previous_person_count
            if diff > 0:
                self.scene_context = (
                    f"SCENE UPDATE: {diff} new person(s) appeared. "
                    f"Total people visible: {person_count}."
                )
            else:
                self.scene_context = (
                    f"SCENE UPDATE: {abs(diff)} person(s) left the frame. "
                    f"Total people visible: {person_count}."
                )
            self.last_significant_change = now
            self.previous_person_count = person_count
            logger.debug("Scene context updated: %s", self.scene_context)

    def get_context(self) -> str:
        """Return the latest social context string for the LLM."""
        return self.scene_context

    async def stop_processing(self) -> None:
        """Stop frame processing."""
        self._running = False

    async def close(self) -> None:
        """Clean up resources."""
        self._running = False
        self.tracked_people.clear()
        self.scene_context = ""
        logger.info("SocialCueProcessor closed")
