"""Swim Scout crew — orchestrates Data Fetcher, Safety Officer, and Coach in parallel then in sequence."""
import asyncio
import anthropic
from agents import data_fetcher, safety_officer, coach


class SwimCrew:
    def __init__(self) -> None:
        self.client = anthropic.AsyncAnthropic()

    async def evaluate(self, location: str) -> dict:
        """Run the full crew evaluation for a location and return a structured report."""
        print(f"[SwimCrew] Evaluating: {location}")

        # Data Fetcher and Safety Officer run in parallel — they're independent
        print("[SwimCrew] Data Fetcher + Safety Officer running in parallel...")
        conditions, safety = await asyncio.gather(
            data_fetcher.run(location, self.client),
            safety_officer.run(location, self.client),
        )

        # Coach needs both reports before running
        print("[SwimCrew] Coach synthesizing recommendations...")
        coaching = await coach.run(location, conditions, safety, self.client)

        return {
            "location": location,
            "conditions": {
                "summary": conditions["summary"],
                "raw_data": conditions["raw_data"],
            },
            "safety": {
                "summary": safety["summary"],
                "raw_data": safety["raw_data"],
            },
            "coaching": coaching["recommendation"],
        }
