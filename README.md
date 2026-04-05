## Facebook Lead Ads Voice AI Agent

This Voice AI Agent calls your facebook leads ads in less than 60 seconds, qualifies them and instantly syncs with your CRM.

## Demo: This Voice AI Agent in Action



## Table of contents
- [Problem Statement](#problem-statement)
- [Traditional Approach used by businesses](#traditional-approach-followed-by-most-businesses)
- [Solution](#solution)
- [Architecture](#architecture)
- [How this Voice AI System works](#how-this-voice-ai-system-works)
- [Tech stack used](#tech-stack-used)
- [Resources](#resources)

## Problem Statement

Facebook/Meta Lead Ads are currently optimized to generate cheap form submissions rather than real prospects, causing businesses to receive a high volume of low‑intent, irrelevant, or even fake leads that don't respond, waste sales time and inflate acquisition metrics.

Businesses report that more than half of their Facebook lead form submissions are low quality: people are not interested and mostly never respond. Many businesses report that when they call, leads insist they never submitted anything, do not remember the ad, or deny any interest.

## Traditional approach followed by most businesses

In my findings I have noticed that business owners follow this traditional approach to running ads;
1. Business owner (Marketer) runs Facebook Lead Ads.
2. User (Lead) clicks.
3. They fill your form.

Then what?

Most businesses just… sit there. Waiting. Hoping someone from your team will call manually.

Meanwhile, your hot high-intent lead turns cold. They have reached to three other competitors. And you still haven’t called them.

That’s not marketing. That’s money bleeding.

## Solution

I have created a Voice AI system that's able to;
- Call your Facebook leads in less than 60 seconds as soon as they fill your form. 
- Qualify your leads.
- Book appointments on your calendars
- Update your CRM

The Voice AI Agent qualifies the lead in real-time, filters out spammy numbers and fake leads, books appointments on your calendar, and sends you the legit leads. It then analyzes the call, categorizes the lead and instantly updates your CRM.

## Architecture


## How this Voice AI System works

The Voice AI Agent takes these actions as soon as a Facebook Lead ad form is filled;
1. Call the lead in less than 60 seconds
2. Have a natural conversation with this user(lead)
3. Understand the needs of this user and qualify them
4. Book an appointment on the business calendar
5. Categorize the lead (whether lead is high/medium/low)
6. Save call summary on a CRM (i.e Google Sheets)

## Benefits
With this Voice AI Agent implemented, business owners & marketers advertising on Facebook;
1. Will never lose a hot lead again.
2. No more leads will go to your competition.
3. No more customer will tell "I didn't fill a form" because you're now able to call them instantly in less than 60 seconds.
4. Filter out spammy numbers, fake leads and bots.
5. Will reduce your Customer Per Acquisition (CAC) cost.
6. Will increase your revenue.
7. Your sales team will now follow-up to actual humans who are interested. 

## Tech stack used
1. Livekit: To build the Voice AI Agent
2. Inngest: As the Agent Orchestrator
3. Twilio: Phone carrier
4. PydanticAI: To summarize the call transcription & provide structured output.
5. Google Apps Script: To upload call analysis/summary to Google Sheets
6. Deployed on GCP (Cloud run) & Livekit Cloud.
7. Used Github Actions to automate deployments

## Resources
Watch the full video of this Voice AI Agent in use.
https://youtu.be/lUZ1KYucq_8

