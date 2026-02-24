import logging

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
        instructions="Read @social_copilot.md",
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


async def join_call(agent: Agent, call_type: str, call_id: str) -> None:
    """Join or create a Stream call for the agent."""
    call = agent.edge.client.video.call(call_type, call_id)
    await call.get_or_create(data={"created_by_id": agent.agent_user.id})

    async with await agent.join(call):
        await agent.finish()

if __name__ == "__main__":
    launcher = AgentLauncher(
        create_agent=create_agent,
        join_call=join_call,
    )
    Runner(launcher).cli()
