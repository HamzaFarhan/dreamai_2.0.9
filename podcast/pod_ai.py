import anthropic
import instructor
from dotenv import load_dotenv
from pydantic import BaseModel, Field, field_validator

from dreamai.utils import deindent

load_dotenv()

ask_cld = instructor.from_anthropic(anthropic.Anthropic())


class Info(BaseModel):
    answer: str = Field(
        ..., description="The answer to the user's question about the podcast."
    )
    timestamps: list[float] = Field(
        ..., description="The timestamps in the transcript where the answer was found."
    )

    @field_validator("timestamps")
    @classmethod
    def sort_timestamps(cls, timestamps) -> list[float]:
        return sorted(timestamps)


def merge_same_role_messages(messages: list[dict]) -> list[dict]:
    if not messages:
        return []
    new_messages = []
    last_message = None
    for message in messages:
        if last_message is None:
            last_message = message
        elif last_message["role"] == message["role"]:
            last_message["content"] += "\n\n" + message["content"]
        else:
            new_messages.append(last_message)
            last_message = message
    if last_message is not None:
        new_messages.append(last_message)
    return new_messages


def get_segments_between(
    segments: list[dict], start: float = 0, end: float = float("inf")
) -> list[dict]:
    return [
        segment
        for segment in segments
        if segment["start"] >= start and segment["start"] <= end
    ]


def merge_consecutive_segments(segments: list[dict]) -> list[dict]:
    merged_segments = []
    for segment in segments:
        if not merged_segments:
            merged_segments.append(segment)
        else:
            last_segment = merged_segments[-1]
            if last_segment["end"] == segment["start"]:
                last_segment["end"] = segment["end"]
            else:
                merged_segments.append(segment)
    return merged_segments


sys_message = deindent(
    """
You are an avid listener of podcasts and you have world class information retention.
You will be a given a part of a transcript from a podcast episode and you will be asked to answer questions based on the information in the transcript.
Also return the timestamp of the segment in the podcast where the answer was found.
"""
)
