import asyncio
import logging
import os
import ssl

import aiohttp
import certifi
import httpx
from dotenv import load_dotenv
from vision_agents.core import Agent, AgentLauncher, Runner, User
from vision_agents.plugins import gemini, getstream, ultralytics
from vision_agents.plugins.getstream import (
    CallSessionParticipantJoinedEvent,
    CallSessionParticipantLeftEvent,
)

from processors.social_processor import SocialCueProcessor

logger = logging.getLogger(__name__)
load_dotenv()

os.environ['SSL_CERT_FILE'] = certifi.where()
os.environ['REQUESTS_CA_BUNDLE'] = certifi.where()

ssl_context = ssl.create_default_context(cafile=certifi.where())

original_aiohttp_init = aiohttp.TCPConnector.__init__

def patched_aiohttp_init(self, *args, **kwargs):
    if 'ssl' not in kwargs or kwargs['ssl'] is None:
        kwargs['ssl'] = ssl_context
    original_aiohttp_init(self, *args, **kwargs)

aiohttp.TCPConnector.__init__ = patched_aiohttp_init

original_httpx_init = httpx.AsyncHTTPTransport.__init__

def patched_httpx_init(self, *args, **kwargs):
    if 'verify' not in kwargs:
        kwargs['verify'] = ssl_context
    original_httpx_init(self, *args, **kwargs)

httpx.AsyncHTTPTransport.__init__ = patched_httpx_init


async def create_agent(**kwargs) -> Agent:
    """Create the EchoSight social intelligence agent."""
    yolo_processor = ultralytics.YOLOPoseProcessor(
        model_path="yolo11n-pose.pt",  
        device="cpu",                  
    )
    social_processor = SocialCueProcessor(fps=3)
    agent = Agent(
        edge=getstream.Edge(),
        agent_user=User(
            name="EchoSight",
            id="echosight-agent",
        ),
        instructions="Read @instructions/social_copilot.md",
        llm=gemini.Realtime(
            model="gemini-2.5-flash-native-audio-preview-12-2025",
            fps=5,  
            config={
                "response_modalities": ["AUDIO"],
                "speech_config": {
                    "voice_config": {
                        "prebuilt_voice_config": {
                            "voice_name": "Leda", 
                        }
                    },
                    "language_code": "en-US",
                },
                "enable_affective_dialog": True,  
            },
        ),
        processors=[yolo_processor, social_processor],
    )

    @agent.events.subscribe
    async def on_participant_joined(event: CallSessionParticipantJoinedEvent):
        """Notify the user when someone joins the call."""
        user = event.participant.user
        if user.id != "echosight-agent":
            name = user.name or user.id
            await agent.simple_response(f"A new person has joined: {name}.")

    @agent.events.subscribe
    async def on_participant_left(event: CallSessionParticipantLeftEvent):
        """Notify the user when someone leaves the call."""
        user = event.participant.user
        if user.id != "echosight-agent":
            name = user.name or user.id
            await agent.simple_response(f"{name} has left the conversation.")

    return agent


async def _proactive_monitor(agent: Agent, interval: int = 8) -> None:
    """Periodically prompt Gemini to scan the scene and deliver cues proactively."""
    await asyncio.sleep(10)  
    while True:
        await asyncio.sleep(interval)
        await agent.simple_response(
            "Scan the current video frame right now. "
            "If something notable has changed — such as a person looking at their phone, "
            "someone new entering the frame, someone leaving, or a significant change in "
            "attention or body language — deliver a brief cue per your instructions. "
            "If nothing significant has changed, stay completely silent."
        )


async def join_call(agent: Agent, call_type: str, call_id: str) -> None:
    """Join or create a Stream call for the agent."""
    call = agent.edge.client.video.call(call_type, call_id)
    await call.get_or_create(data={"created_by_id": agent.agent_user.id})

    async with agent.join(call):
        monitor_task = asyncio.create_task(_proactive_monitor(agent))
        try:
            await agent.finish()
        finally:
            monitor_task.cancel()
            try:
                await monitor_task
            except asyncio.CancelledError:
                pass

if __name__ == "__main__":
    launcher = AgentLauncher(
        create_agent=create_agent,
        join_call=join_call,
    )
    Runner(launcher).cli()
