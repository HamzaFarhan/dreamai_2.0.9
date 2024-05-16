import json
import os
from collections import defaultdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional, Protocol, Sequence
from uuid import uuid4

import anthropic
import instructor
import openai
import pandas as pd
from chromadb import Collection as ChromaCollection
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from pypdf import PdfReader
from streamlit.runtime.uploaded_file_manager import UploadedFile

from dreamai.ai import (
    ModelName,
    assistant_message,
    claude_response,
    merge_same_role_messages,
    oai_response,
    system_message,
    user_message,
)
from dreamai.chroma import chroma_collection

load_dotenv()

ask_oai = instructor.from_openai(openai.OpenAI())
ask_cld = instructor.from_anthropic(anthropic.Anthropic())

GPT_MODEL = ModelName.GPT_4
MODEL = ModelName.GPT_4
TEMPERATURE = 0.3
MAX_TOKENS = 3_000
ATTEMPTS = 3
CLAUDE_MAX_TEXT_LEN = 400_000
GPT_MAX_TEXT_LEN = 100_000
PROFILES_DIR = Path("user_profiles")
PROFILES_COLLECTION_NAME = "user_profiles"
JOBS_DIR = Path("job_posts")
JOBS_COLLECTION_NAME = "job_posts"


def extract_text(data: str | Path | UploadedFile) -> str:
    if isinstance(data, Path):
        if data.exists():
            if data.suffix == ".txt":
                return data.read_text()
        else:
            return ""
    elif isinstance(data, str):
        try:
            if Path(data).exists():
                if Path(data).suffix == ".txt":
                    return Path(data).read_text()
                else:
                    data = Path(data)
            else:
                return data
        except Exception:
            return data
    try:
        reader = PdfReader(data)
        text = ""
        for page in reader.pages:
            text += page.extract_text()
        return text.strip()
    except Exception as e:
        print(e)
        return ""


class EducationLevel(int, Enum):
    HIGH_SCHOOL = 1
    BACHELOR = 2
    MASTER = 3
    DOCTORATE = 4

    def __str__(self) -> str:
        return self.name.replace("_", " ").title()


class Level(str, Enum):
    NONE = "None"
    BEGINNER = "Beginner"
    INTERMEDIATE = "Intermediate"
    ADVANCED = "Advanced"

    def __str__(self) -> str:
        return self.value


def model_to_str(model: BaseModel, keys: list[str] | None = None) -> str:
    doc = ""
    for k, v in model.model_dump(include=keys).items():  # type: ignore
        if v:
            doc += f"\n<{k}>\n{v}\n</{k}>\n"
    return doc.strip()


def model_to_df(model: BaseModel, keys: list[str] | None = None) -> pd.DataFrame:
    data = defaultdict(list)
    for k, v in model.model_dump(include=keys).items():  # type: ignore
        k = k.replace("_", " ").title()
        if v and isinstance(v, (CustomDate, EducationLevel)):
            data[k].append(str(v))
        else:
            data[k].append(v)
    return pd.DataFrame(data)


class JobModel(BaseModel):
    def __str__(self) -> str:
        return model_to_str(self)

    def to_df(self, keys: list[str] | None = None) -> pd.DataFrame:
        return model_to_df(self, keys=keys)


class CustomDate(JobModel):
    year: int = Field(default_factory=lambda: datetime.now().year)
    month: int = 1
    day: int = 1

    @classmethod
    def today(cls) -> "CustomDate":
        today = datetime.now().strftime("%Y-%m-%d").split("-")
        return cls(year=int(today[0]), month=int(today[1]), day=int(today[2]))

    @property
    def date(self) -> datetime:
        return datetime(self.year, self.month, self.day)

    def __str__(self) -> str:
        return str(self.date.date())


class Skill(JobModel):
    name: str
    proficiency_level: Level = Field(
        Level.BEGINNER,
        description="Proficiency level in the skill.",
        examples=["NONE", "BEGINNER", "INTERMEDIATE", "ADVANCED"],
    )


class Certification(JobModel):
    name: str
    institution: str | None = None
    issue_date: CustomDate | None = None
    expiration_date: CustomDate | None = None

    @property
    def is_expired(self) -> bool:
        if self.expiration_date is None:
            return False
        return self.expiration_date.date < datetime.now()


class JobDescription(JobModel):
    title: str
    company: str | None = None
    description: str = Field(
        ...,
        description="A brief summary of the job, including the main responsibilities and technical skills required.",
    )


class Experience(JobModel):
    job_description: JobDescription
    start_date: CustomDate | None = None
    end_date: CustomDate | None = None

    def to_df(self, keys: list[str] | None = None) -> pd.DataFrame:
        df = self.job_description.to_df(keys=keys)
        df["Start Date"] = None
        df["End Date"] = None
        if self.start_date is not None:
            df["Start Date"] = str(self.start_date)
        if self.end_date is not None:
            df["End Date"] = str(self.end_date)
        return df


class Education(JobModel):
    degree: EducationLevel = EducationLevel.HIGH_SCHOOL
    institution: str | None = None
    field_of_study: str | None = None
    graduation_year: int | None = None


class UserProfile(JobModel):
    name: str
    email: str
    title: str = Field(
        description="Current/Preferred job title. Be as specific as possible."
    )
    summary: str = Field(
        description="A brief summary of the candidate's profile. Include technical proficiencies and education."
    )
    experiences: list[Experience]
    skills: list[Skill]
    certifications: list[Certification] = Field(default_factory=list)
    education: list[Education]
    interested_job_titles: list[str] = Field(
        description="Job titles of interest", default_factory=list
    )
    years_of_experience: int = Field(
        1, description="Total years of professional experience"
    )

    @property
    def max_education(self) -> EducationLevel:
        return sorted(edu.degree for edu in self.education)[-1]

    def create_dfs(self):
        dfs = {}
        if len(self.experiences) > 0:
            dfs["experiences"] = pd.concat(exp.to_df() for exp in self.experiences)
        if len(self.skills) > 0:
            dfs["skills"] = pd.concat(skill.to_df() for skill in self.skills)
        if len(self.certifications) > 0:
            dfs["certifications"] = pd.concat(
                cert.to_df() for cert in self.certifications
            )
        if len(self.education) > 0:
            dfs["education"] = pd.concat(edu.to_df() for edu in self.education)
        return dfs

    def to_doc(self) -> str:
        return model_to_str(
            self,
            keys=[
                "summary",
                "title",
                "experiences",
                "skills",
                "certifications",
                "interested_job_titles",
            ],
        )


class JobPost(JobModel):
    job_description: JobDescription
    skills: list[Skill]
    education: list[Education] = Field(
        description="The education requirements for the job", default_factory=list
    )
    years_of_experience: int = Field(
        0, description="Minimum years of experience required"
    )
    # posted_date: CustomDate = Field(
    #     description="Date the job was posted", default_factory=CustomDate.today
    # )

    @property
    def min_education(self) -> EducationLevel:
        if not self.education:
            return EducationLevel.HIGH_SCHOOL
        return sorted(edu.degree for edu in self.education)[0]

    def create_dfs(self):
        dfs = {}
        dfs["skills"] = pd.concat(skill.to_df() for skill in self.skills)
        if len(self.education) > 0:
            dfs["education"] = pd.concat(edu.to_df() for edu in self.education)
        return dfs

    def to_doc(self) -> str:
        return model_to_str(
            self,
            keys=["job_description", "skills", "education"],
        )


class Creator(Protocol):
    def __call__(
        self,
        data: str | Path | UploadedFile,
        model: ModelName,
        attempts: int,
        max_tokens: int,
    ) -> UserProfile | JobPost | str | None: ...


def ask_cld_or_oai(
    messages: list[dict[str, str]],
    system: str = "",
    model: ModelName = MODEL,
    response_model: Optional[type] = None,
    attempts: int = ATTEMPTS,
    max_tokens: int = MAX_TOKENS,
    temperature: float = TEMPERATURE,
    stop: list[str] | str | None = None,
):
    ask_kwargs = {
        "model": model,
        "response_model": response_model,
        "max_retries": attempts,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    # try:
    if "gpt" in ask_kwargs["model"].lower():
        if system:
            messages.insert(0, system_message(system))
        res = ask_oai.create(
            messages=messages,  # type: ignore
            stop=stop,
            **ask_kwargs,
        )
        return oai_response(res) if response_model is None else res
    else:
        res = ask_cld.create(
            system=system,
            messages=merge_same_role_messages(messages),  # type: ignore
            stop_sequences=stop,
            **ask_kwargs,
        )
        return claude_response(res) if response_model is None else res
    # except Exception as e:
    #     print(f"Error in ask_cld_or_oai. User messages: {messages}")
    #     print(e)
    #     return None


def create_reasoning(
    user_profile: UserProfile,
    job_post: JobPost,
    model: ModelName = MODEL,
    attempts: int = ATTEMPTS,
    max_tokens: int = MAX_TOKENS,
    temperature: float = TEMPERATURE,
):
    system = """
You are a world class recruiter.
You'll be given a job post and a candidate that has been shortlisted for the job.
Give a brief reasoning for why the candidate is a good fit for the job.
Try to also mention which specific sections of the candidate's profile make them a good fit and why.
Make it brief but detailed with bullet points.
"""
    messages = [
        user_message(
            f"<Job Post>\n{job_post}\n</Job Post>\n\n<Candidate>\n{user_profile}\n</Candidate>"[
                :GPT_MAX_TEXT_LEN
            ]
        ),
        assistant_message("<Reasoning>"),
    ]

    try:
        if "gpt" not in model.lower():
            messages[0] = user_message(
                f"<Job Post>\n{job_post}\n</Job Post>\n\n<Candidate>\n{user_profile}\n</Candidate>"[
                    :CLAUDE_MAX_TEXT_LEN
                ]
            )
        res = ask_cld_or_oai(
            messages=messages,
            system=system,
            model=model,
            attempts=attempts,
            max_tokens=max_tokens,
            temperature=temperature,
            stop="</Reasoning>",
        )
        return res.split("</Reasoning>")[0].split("<Reasoning>")[-1].strip()
    except Exception as e:
        print(f"Error in create_reasoning: {e}")
        try:
            res = ask_cld_or_oai(
                messages=messages,
                system=system,
                model=GPT_MODEL,
                attempts=attempts,
                max_tokens=max_tokens,
                temperature=temperature,
                stop="</Reasoning>",
            )
            return res.split("</Reasoning>")[0].split("<Reasoning>")[-1].strip()
        except Exception as e:
            print(f"Error in crerate_reasoning: {e}")
            return None


def create_user_profile(
    data: str | Path | UploadedFile,
    model: ModelName = MODEL,
    attempts: int = ATTEMPTS,
    max_tokens: int = MAX_TOKENS,
    temperature: float = TEMPERATURE,
) -> UserProfile | str | None:
    system = """
You are a world class recruiter.
From the given resume, extract:
- Name
- Email
- Current/Preferred Job Title
- Experiences
- Skills
- Certifications
- Education
- Interested Job Titles
- Years of Experience
Also give a brief summary of the candidate. Include technical proficiencies and education.
Then, create a user profile with the extracted information.
"""
    data = extract_text(data)
    if not data:
        return None
    data_message = user_message(f"<Resume>\n{data[:GPT_MAX_TEXT_LEN]}\n</Resume>")
    try:
        if "gpt" not in model.lower():
            data_message = user_message(
                f"<Resume>\n{data[:CLAUDE_MAX_TEXT_LEN]}\n</Resume>"
            )
        return ask_cld_or_oai(
            messages=[data_message],
            system=system,
            model=model,
            response_model=UserProfile,
            attempts=attempts,
            max_tokens=max_tokens,
            temperature=temperature,
        )
    except Exception as e:
        print(f"Error when asking claude in create_user_profile: {e}")
        try:
            return ask_cld_or_oai(
                messages=[data_message],
                system=system,
                model=GPT_MODEL,
                response_model=UserProfile,
                attempts=attempts,
                max_tokens=max_tokens,
                temperature=temperature,
            )
        except Exception as e:
            print(f"Error when asking openai in create_user_profile: {e}")
            return None


def create_job_post(
    data: str | Path | UploadedFile,
    model: ModelName = ModelName.HAIKU,
    attempts: int = ATTEMPTS,
    max_tokens: int = MAX_TOKENS,
) -> JobPost | str | None:
    system = """
You are a world class recruiter.
From the given job description, extract:
- Job Title
- Company
- Skills
- Education
- Years of Experience Required
Also give a brief description of the job. Include the main responsibilities and technical skills required.
Then, create a job post with the extracted information.
"""
    data = extract_text(data)
    if not data:
        return None
    data_message = user_message(
        f"<Job Description>\n{data[:GPT_MAX_TEXT_LEN]}\n</Job Description>"
    )

    try:
        if "gpt" not in model.lower():
            data_message = user_message(
                f"<Job Description>\n{data[:CLAUDE_MAX_TEXT_LEN]}\n</Job Description>"
            )
        return ask_cld_or_oai(
            messages=[data_message],
            system=system,
            model=model,
            response_model=JobPost,
            attempts=attempts,
            max_tokens=max_tokens,
        )
    except Exception as e:
        print(f"Error when asking claude in create_job_post: {e}")
        try:
            return ask_cld_or_oai(
                messages=[data_message],
                system=system,
                model=GPT_MODEL,
                response_model=JobPost,
                attempts=attempts,
                max_tokens=max_tokens,
            )
        except Exception as e:
            print(f"Error when asking openai in create_job_post: {e}")
            return None


def ask_cld_then_oai(
    messages: list[dict[str, str]],
    system: str = "",
    model: ModelName = MODEL,
    response_model: Optional[type] = None,
    attempts: int = ATTEMPTS,
    max_tokens: int = MAX_TOKENS,
    temperature: float = TEMPERATURE,
):
    ask_kwargs = {
        "model": model,
        "response_model": response_model,
        "max_retries": attempts,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    try:
        return ask_cld.create(
            system=system,
            messages=merge_same_role_messages(messages),  # type: ignore
            **ask_kwargs,
        )
    except Exception as e:
        print(f"Error in ask_cld_then_oai. User messages: {messages}")
        print(e)
        try:
            return ask_oai.create(
                messages=messages,  # type: ignore
                **ask_kwargs,
            )
        except Exception as e:
            print(f"Error in ask_oai in ask_cld_then_oai: {e}")
            return None


def create_models_and_collection(
    data: Sequence[UploadedFile | str | Path | UploadedFile | UserProfile | JobPost],
    creator_fn: Creator = create_user_profile,
    model: ModelName = MODEL,
    attempts: int = ATTEMPTS,
    max_tokens: int = MAX_TOKENS,
    models_dir: Path | str = PROFILES_DIR,
    collection: ChromaCollection | None = None,
    collection_name: str = PROFILES_COLLECTION_NAME,
    delete_existing: bool = False,
):
    os.makedirs(models_dir, exist_ok=True)
    models_dir = Path(models_dir)
    model_docs = {"ids": [], "documents": []}
    for item in data:
        print(f"\n\nITEM:\n{item}\n\n")
        if isinstance(item, (UserProfile, JobPost)):
            model_instance = item
        else:
            model_instance = creator_fn(
                data=item,  # type: ignore
                model=model,
                attempts=attempts,
                max_tokens=max_tokens,
            )
        if model_instance is not None:
            model_id = str(uuid4())
            try:
                model_docs["ids"].append(model_id)
                model_docs["documents"].append(model_instance.to_doc())  # type: ignore
            except Exception as e:
                print(e)
                continue
            model_file = models_dir / f"{model_id}.json"
            with open(model_file, "w") as f:
                json.dump(model_instance.model_dump(), f, indent=2)  # type: ignore
    if len(model_docs["documents"]) == 0:
        return
    collection = collection or chroma_collection(
        name=collection_name, delete_existing=delete_existing
    )
    collection.add(**model_docs)
