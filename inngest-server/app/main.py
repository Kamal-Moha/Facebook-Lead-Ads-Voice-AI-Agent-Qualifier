import logging
from fastapi import FastAPI, Request, Response
import inngest
import inngest.fast_api
import os
import requests
import json

from dotenv import load_dotenv

from livekit import api
from livekit.protocol.sip import CreateSIPParticipantRequest

from utils import remove_underscores
from pydantic import BaseModel, EmailStr
from pydantic_ai import Agent, DocumentUrl

from typing import List, Optional, Literal
from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.lead import Lead

load_dotenv()

logger = logging.getLogger(__name__)
headers = {"content-type": "application/json"}

# Below are the questions asked on the Meta Lead Ad Form. And in order
questions = {
    "qn_1": "when_are_you_looking_to_buy_a_home?",
    "qn_2": "do_you_need_financing_(a_mortgage)_to_buy?",
    "qn_3": "are_you_interested_in_this_specific_house_or_just_any_similar_house?",
    "qn_4": "what_is_your_approximate_budget_for_buying_a_home?",
    "qn_5": "when_would_you_like_to_view_the_property?",
    "qn_6": "email",
    "qn_7": "full_name",
    "qn_8": "phone_number",
    "qn_9": "city",
}

app = FastAPI()


class LeadFormData(BaseModel):
    when_are_you_looking_to_buy: str
    do_you_need_financing: str
    interested_in_specific_house: str
    approximate_budget: str
    when_to_view_property: str
    email: EmailStr
    full_name: str
    phone_number: str
    city: str


class JsonFileOutput(BaseModel):
    tool_calls: list[str]
    tool_call_results: list[str]
    lead_intent: Literal["High", "Medium", "Low"]
    summary: str


class Transcript(BaseModel):
    url: str


# Meta Lead Ad Form
class ValueModel(BaseModel):
    created_time: int
    leadgen_id: str
    page_id: str
    form_id: Optional[str]


class ChangeModel(BaseModel):
    value: ValueModel
    field: str


class EntryModel(BaseModel):
    id: str
    time: int
    changes: List[ChangeModel]


class WebhookData(BaseModel):
    entry: List[EntryModel]
    object: str


# Configuration
room_name = "my-room"
agent_name = "meta-lead-ads-agent"
outbound_trunk_id = os.getenv("SIP_OUTBOUND_TRUNK_ID")


async def make_call(data: LeadFormData) -> None:
    """Create a dispatch and add a SIP participant to call the phone number"""
    lkapi = api.LiveKitAPI()

    # Create agent dispatch
    logger.info(f"Creating dispatch for agent {agent_name} in room {room_name}")
    dispatch = await lkapi.agent_dispatch.create_dispatch(
        api.CreateAgentDispatchRequest(
            agent_name=agent_name, room=room_name, metadata=data.phone_number
        )
    )
    logger.info(f"Created dispatch: {dispatch}")
    print(f"Created dispatch: {dispatch}")

    dispatches = await lkapi.agent_dispatch.list_dispatch(room_name=room_name)
    print(f"there are {len(dispatches)} dispatches in {room_name}")

    # Create SIP participant to make the call
    if not outbound_trunk_id or not outbound_trunk_id.startswith("ST_"):
        logger.error("SIP_OUTBOUND_TRUNK_ID is not set or invalid")
        return

    logger.info(f"Dialing {data.phone_number} to room {room_name}")

    try:
        # Create SIP participant to initiate the call
        sip_participant = await lkapi.sip.create_sip_participant(
            CreateSIPParticipantRequest(
                room_name=room_name,
                sip_trunk_id=outbound_trunk_id,
                sip_call_to=data.phone_number,
                participant_identity="phone_user",
                participant_name=data.full_name,
                krisp_enabled=True,
                wait_until_answered=True,
                play_dialtone=True,
                participant_attributes=data.model_dump(),
            )
        )
        logger.info(f"Created SIP participant: {sip_participant}")
        return f"Created SIP participant: {sip_participant}"
    except Exception as e:
        logger.error(f"Error creating SIP participant: {e}")
        return f"Error creating SIP participant: {e}"

    # Close API connection
    await lkapi.aclose()


# FUNCTION 2 - Analyze transcript
async def analyze_transcript(transcript: Transcript):
    agent: Agent[None, str] = Agent(
        "github:openai/gpt-4.1",
        system_prompt="You are a helpful agent tasked to interpret documents. The document is a call transcripton between an interested lead(user) and a Voice AI Agent",
        output_type=JsonFileOutput,
        instructions="""
      Analyze the document and provide a detailed action oriented summary.

      Output:
        lead_intent:
          Use the tool calls made by the agent and the summary to determine the lead intent.
          For example, if an appointment has been scheduled for the user, then this user is a high intent lead.

        summary:
          Provide a detailed summary of the document and highlight the keys ACTIONS taken by the Voice Agent as highlighted in the document.

        tool_calls:
          List the tool calls made by the Voice Agent as highlighted in the document.

        tool_call_results:
          List the results of the tool calls made by the Voice Agent as highlighted in the document.
      """,
    )
    print(f"Transcript: {transcript}")
    result = await agent.run(
        [
            "Summarize this document. Tell me what are the main actions taken and what are the tool calls that have been made",
            DocumentUrl(url=transcript),
        ]
    )

    print(f"Result: {result}")
    return result.output.model_dump()


# FUNCTION 3 - Sending info to Google Sheets. This function sends data to your Google Apps Script Web App
async def send_to_google_sheet(
    data: JsonFileOutput, name: str, phone_number: str, call_recording: str
):
    # !!! PASTE YOUR WEB APP URL HERE !!!
    apps_script_url = os.getenv("APPS_SCRIPT_WEB_APP")

    try:
        # Convert the Pydantic model to a dictionary, then to a JSON string
        # payload = json.dumps(data.model_dump())

        # Adding 'name', 'phone_number' and 'call_recording' into the dictionary
        data["name"] = name
        data["phone_number"] = phone_number
        data["call_recording"] = call_recording
        payload = json.dumps(data)

        print(f"PAYLOAD: {payload}")

        # Make the POST request
        response = requests.post(apps_script_url, data=payload, headers=headers)
        response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)

        return f"✅Successfully sent data to Google Sheet {response.json()}"

    except requests.exceptions.RequestException as e:
        return f"❌ Failed to send data to Google Sheet: {e}"


async def getting_lead_data(lead_gen_id: str):
    FacebookAdsApi.init(access_token=os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN"))
    lead_node = Lead(lead_gen_id).api_get(fields=["field_data"])
    field_data = lead_node.get("field_data", [])

    # Create the flat dictionary from Meta
    lead_dict = {
        item["name"]: remove_underscores(item["values"][0]) for item in field_data
    }
    print(f"LEAD INFO: {lead_dict}")
    # return lead_dict

    # Modifying the lead_dict from Meta
    modified_lead_dict = {
        "when_are_you_looking_to_buy": lead_dict.get(questions.get("qn_1")),
        "do_you_need_financing": lead_dict.get(questions.get("qn_2")),
        "interested_in_specific_house": lead_dict.get(questions.get("qn_3")),
        "approximate_budget": lead_dict.get(questions.get("qn_4")),
        "when_to_view_property": lead_dict.get(questions.get("qn_5")),
        "email": lead_dict.get(questions.get("qn_6")),
        "full_name": lead_dict.get(questions.get("qn_7")),
        "phone_number": lead_dict.get(questions.get("qn_8")),
        "city": lead_dict.get(questions.get("qn_9")),
    }
    return modified_lead_dict

signing_key = os.getenv("INNGEST_SIGNING_KEY")
if signing_key:
    logging.info(f"Inngest key found. Length: {len(signing_key)}")
    print(f"Inngest key found. Length: {len(signing_key)}")
else:
    logging.error("Inngest signing key is MISSING at runtime")

# Create an Inngest client
inngest_client = inngest.Inngest(
    app_id="Lead Qualification - Voice AI Agent",
    logger=logging.getLogger("uvicorn"),
    is_production=os.environ.get("ENV") == "production",
)


# Creating the Inngest function to handle what should happen when the calls is completed
@inngest_client.create_function(
    fn_id="livekit_call_completed",
    # Event that triggers this function
    trigger=inngest.TriggerEvent(event="livekit/call.completed"),
)
async def livekit_call_completed(ctx: inngest.Context) -> str:
    print(f"Event: {ctx.event}")

    transcript_url = ctx.event.data["transcript_url"]

    # Step 1 - Transcribe the call
    call_analysis = await ctx.step.run(
        "Transcribing the call", analyze_transcript, transcript_url
    )

    # Step 2 - Sending info to Google Sheets
    await ctx.step.run(
        "Sending to Google Sheets",
        send_to_google_sheet,
        call_analysis,
        ctx.event.data["user"]["name"],
        ctx.event.data["user"]["phone"],
        ctx.event.data["recording_url"],
    )


@inngest_client.create_function(
    fn_id="meta_lead_ad_form_submitted",
    # Event that triggers this function
    trigger=inngest.TriggerEvent(event="meta/lead_ad_form.submitted"),
)
async def meta_lead_ad_form_submitted(ctx: inngest.Context) -> str:

    parsed_data = WebhookData(**ctx.event.data)
    lead_gen_id = parsed_data.entry[0].changes[0].value.leadgen_id
    print(f"LEADGEN ID: {lead_gen_id}")

    # Step 1 - Getting Lead data
    lead_data = await ctx.step.run("Getting lead data", getting_lead_data, lead_gen_id)

    # Step 2 - Calling the user
    await ctx.step.run("calling_the_user", make_call, LeadFormData(**lead_data))


@app.get("/api/webhook", tags=["meta"])
async def meta_leads_webhook(request: Request):
    verify_token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")
    if verify_token == os.getenv("WEBHOOK_VERIFY_TOKEN"):
        print(f"----{challenge}----")
        return Response(content=challenge, media_type="text/plain")
    return Response(content="Invalid verify token", media_type="text/plain")


@app.post("/api/webhook", tags=["meta"])
async def process_webhook(request: Request):
    print("STARTING !")
    data = await request.json()
    print(f"DATA: {data}")

    # Sending event to inngest
    await inngest_client.send(
        inngest.Event(name="meta/lead_ad_form.submitted", data=data)
    )


# Serve the Inngest endpoint
inngest.fast_api.serve(
    app, inngest_client, [meta_lead_ad_form_submitted, livekit_call_completed]
)
