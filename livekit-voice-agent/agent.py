from dotenv import load_dotenv

from livekit import api
from livekit import agents, rtc
from livekit.agents import AgentServer, AgentSession, Agent, room_io, mcp
from livekit.plugins import (
    aws,
    noise_cancellation,
)

# import packages
import os
from datetime import datetime
import json
import logging
import inngest
import random
import string

from utils import load_prompt, upload_cs_file, get_cs_file_url

load_dotenv()

agent_name = "meta-lead-ads-agent"
transcription_bucket = "call-transcriptions-meta-leads"
call_recording_bucket = "voice-ai-call-recordings-meta-lead-ads"

# Create an Inngest client
inngest_client = inngest.Inngest(
    app_id="Lead Qualification - Voice AI Agent",
    logger=logging.getLogger("uvicorn")
)


class ContextAgent(Agent):
    def __init__(self, context_vars=None) -> None:
        instructions = load_prompt("agent_instructions.yaml")

        if context_vars:
            instructions = instructions.format(**context_vars)

        super().__init__(instructions=instructions)

    async def on_enter(self):
        self.session.generate_reply(
            instructions="""
        Greet the customer by saying;
        For example;
        Hi {full_name}, I'm Linda from Dalabey Real Estate. I have seen you have recently filled our form on Meta/Facebook.
        Offer your assistance. You should start by speaking in English.

        """
        )


server = AgentServer()


@server.rtc_session(agent_name=agent_name)
async def my_agent(ctx: agents.JobContext):
    # ------RECORDING THE CALL (EGRESS)-------

    random_string = "".join(random.choices(string.ascii_letters + string.digits, k=12))
    unique_time = datetime.now().strftime("%Y-%m-%dT%H%M%S") + f"-{random_string}"
    # Set up recording
    req = api.RoomCompositeEgressRequest(
        room_name=ctx.room.name,
        layout="speaker",
        audio_only=True,
        file=api.EncodedFileOutput(
            filepath=f"{ctx.room.name}/agent-{unique_time}.ogg",
            s3=api.S3Upload(
                bucket=call_recording_bucket,
                region="eu-north-1",
                access_key=os.getenv("AWS_ACCESS_KEY_ID"),
                secret=os.getenv("AWS_SECRET_ACCESS_KEY"),
                force_path_style=True,
            ),
        ),
    )

    res = await ctx.api.egress.start_room_composite_egress(req)

    # --------------
    await ctx.connect()
    participant = await ctx.wait_for_participant()

    print(participant)
    print(f"Participant Attributes: {participant.attributes}")
    # print(f"Participant Name: {participant.attributes['name']}")
    print(f"Participant Name: {participant.attributes['full_name']}")

    async def write_transcript():
        current_date = datetime.now().strftime("%Y%m%d_%H%M%S")
        print(f"Curent Date: {current_date}")
        # This example writes to the temporary directory, but you can save to any location
        filename = f"transcript_{ctx.room.name}_{current_date}.json"
        with open(filename, "w") as f:
            json.dump(session.history.to_dict(), f, indent=2)

        # Saving to Google Cloud
        upload_cs_file(transcription_bucket, filename, filename)

        public_url = get_cs_file_url(transcription_bucket, filename)
        print(f"Transcript for {ctx.room.name} saved to {public_url}")

        # print(f"Transcript for {ctx.room.name} saved to {filename}")
        recording_url = get_cs_file_url(
            call_recording_bucket, f"{ctx.room.name}/agent-{unique_time}.ogg"
        )
        print(f"Call recording for {ctx.room.name} saved to {public_url}")

        # Prepare data to trigger event in inngest
        payload = {
            "transcript_url": public_url,
            "recording_url": recording_url,
            "user": {
                "name": participant.attributes["full_name"],
                "phone": participant.attributes["sip.phoneNumber"],
            },
        }
        print(f"PAYLOAD: {payload}")

        # Sending event to inngest
        await inngest_client.send(
            inngest.Event(name="livekit/call.completed", data=payload)
        )

        return f"Call transcript {public_url} sent and inngest event triggered"

    ctx.add_shutdown_callback(write_transcript)

    # # Amazon Nova Sonic
    session = AgentSession(
        llm=aws.realtime.RealtimeModel(voice="tiffany"),
        mcp_servers=[
            mcp.MCPServerHTTP("https://c054-102-203-209-86.ngrok-free.app/mcp")
        ],
    )

    await session.start(
        room=ctx.room,
        agent=ContextAgent(participant.attributes),
        room_options=room_io.RoomOptions(
            audio_input=room_io.AudioInputOptions(
                noise_cancellation=lambda params: noise_cancellation.BVCTelephony() if params.participant.kind == rtc.ParticipantKind.PARTICIPANT_KIND_SIP else noise_cancellation.BVC(),
            ),
        ),
    )

if __name__ == "__main__":
    agents.cli.run_app(server)
