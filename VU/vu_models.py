import json
import random
from collections import OrderedDict
from pathlib import Path
from typing import Annotated, Literal, Optional

import anthropic
import instructor
import openai
from dotenv import load_dotenv
from langsmith import traceable
from langsmith.wrappers import wrap_openai
from pydantic import (
    AfterValidator,
    BaseModel,
    Field,
    field_validator,
    model_validator,
)

from dreamai.ai import ModelName, merge_same_role_messages, system_message, user_message
from dreamai.utils import deindent

load_dotenv()

ask_oai = instructor.from_openai(wrap_openai(openai.OpenAI()))
ask_cld = instructor.from_anthropic(anthropic.Anthropic())

MODEL = ModelName.HAIKU
MAX_TOKENS = 2048
TEMPERATURE = 0.15
ATTEMPTS = 3

QUESTIONS_PER_FOLDER = 20
CONCEPT_WORD_COUNT = 3
MIN_SUBQUESTIONS = 2
MAX_SUBQUESTIONS = 3
MIN_TOPICS = 10
MAX_TOPICS = 15
MIN_SUBTOPICS = 3
MAX_SUBTOPICS = 5
MIN_CONCEPTS = 2
MAX_CONCEPTS = 5
MIN_QUESTIONS_PER_CONCEPT = 2
MAX_QUESTIONS_PER_CONCEPT = 3
MIN_PREREQUISITES = 2
MAX_PREREQUISITES = 3
CONFIDENCE_THRESHOLD = 0.4
NUM_PREVIOUS_GROUPS = 10
RANDOM_SEED = 42

random.seed(RANDOM_SEED)


@traceable(name="ask_cld_or_oai")
def ask_cld_or_oai(
    user_messages: list[dict[str, str]],
    system: str = "",
    model: ModelName = MODEL,
    response_model: Optional[type] = None,
    attempts: int = ATTEMPTS,
    max_tokens: int = MAX_TOKENS,
    temperature: float = TEMPERATURE,
    validation_context: dict = {},
    ask_kwargs: dict = {},
):
    ask_kwargs["model"] = model
    ask_kwargs["max_retries"] = attempts
    ask_kwargs["max_tokens"] = max_tokens
    ask_kwargs["temperature"] = temperature
    ask_kwargs["response_model"] = response_model
    ask_kwargs["validation_context"] = validation_context
    # print(f"ASK_KWARGS:\n{ask_kwargs}")
    try:
        if "gpt" in ask_kwargs["model"].lower():
            if system:
                user_messages.insert(0, system_message(system))
            return ask_oai.create(
                messages=user_messages,  # type: ignore
                **ask_kwargs,
            )
        else:
            return ask_cld.create(
                system=system,
                messages=merge_same_role_messages(user_messages),  # type: ignore
                **ask_kwargs,
            )
    except Exception as e:
        print(f"Error in ask_cld_or_oai. User messages: {user_messages}")
        print(e)
        return None


class CreatedID(BaseModel):
    id: str
    confidence: float = Field(
        description="Confidence in the ID. Must be between 0 and 1.", ge=0.0, le=1.0
    )

    @model_validator(mode="after")  # type: ignore
    def validate_id(self) -> "CreatedID":
        if self.confidence < CONFIDENCE_THRESHOLD:
            self.id = ""
        return self


def create_prerequisite_group_ids(
    group: "Group",
    previous_groups: dict[str, "Group"],
    model: ModelName = MODEL,
    attempts: int = ATTEMPTS,
    max_tokens: int = MAX_TOKENS,
) -> list[str]:
    groups_str = "\n".join([str(g) for g in previous_groups.values()])
    sys_message = deindent(
        f"""
You are a world class math course instructor. You will be given a group with a topic, subtopic, and concept.
You will also be given a list of previously created groups which may or may not be prerequisites to the group.
Your job is to assign up to {MAX_PREREQUISITES} prerequisite group IDs to the group.
For each ID you assign, also give a confidence score between 0. and 1.

<groups>
{groups_str}
</groups>
"""
    )
    group_message = deindent(
        f"""
<group>

{str(group)}

</group>
"""
    )
    group_ids = ask_cld_or_oai(
        user_messages=[user_message(group_message)],
        system=sys_message,
        model=model,
        response_model=list[CreatedID],
        attempts=attempts,
        max_tokens=max_tokens,
    )
    return [g.id for g in group_ids if g.id] if group_ids else []


def dict_to_ordereddict(d: dict | OrderedDict) -> OrderedDict:
    return OrderedDict(d)


class CreatedSubtopic(BaseModel):
    name: str
    concepts: list[str] = Field(
        f"{MIN_CONCEPTS}-{MAX_CONCEPTS} concepts covered in the subtopic.",
        min_length=MIN_CONCEPTS,
        max_length=MAX_CONCEPTS,
    )


class CreatedTopic(BaseModel):
    name: str
    subtopics: list[CreatedSubtopic] = Field(
        f"{MIN_SUBTOPICS}-{MAX_SUBTOPICS} ordered subtopics with concepts.",
        min_length=MIN_SUBTOPICS,
        max_length=MAX_SUBTOPICS,
    )


class ConceptWithQuestionIDs(BaseModel):
    concept: str
    question_ids: list[str] = Field(default_factory=list)

    def add_question_id(self, question_id: str):
        if len(self.question_ids) == MAX_QUESTIONS_PER_CONCEPT:
            print(
                f"Concept {self.concept} already has {MAX_QUESTIONS_PER_CONCEPT} questions."
            )
            return
        if question_id in self.question_ids:
            print(f"Question {question_id} already exists for concept {self.concept}.")
            return
        self.question_ids.append(question_id)
        self.question_ids = sorted(self.question_ids, key=int)


class Subtopic(BaseModel):
    name: str
    concepts: Annotated[
        dict[str, ConceptWithQuestionIDs], AfterValidator(dict_to_ordereddict)
    ] = Field(
        description=f"{MIN_CONCEPTS}-{MAX_CONCEPTS} ordered concepts with question IDs.",
        min_length=MIN_CONCEPTS,
        max_length=MAX_CONCEPTS,
    )


class Topic(BaseModel):
    name: str
    subtopics: Annotated[dict[str, Subtopic], AfterValidator(dict_to_ordereddict)] = (
        Field(
            description=f"{MIN_SUBTOPICS}-{MAX_SUBTOPICS} ordered subtopics with concepts.",
            min_length=MIN_SUBTOPICS,
            max_length=MAX_SUBTOPICS,
        )
    )

    @classmethod
    def from_created_topic(cls, created_topic: CreatedTopic) -> "Topic":
        return cls(
            name=created_topic.name,
            subtopics={
                subtopic.name: Subtopic(
                    name=subtopic.name,
                    concepts={
                        concept: ConceptWithQuestionIDs(concept=concept)
                        for concept in subtopic.concepts
                    },
                )
                for subtopic in created_topic.subtopics
            },
        )


class Group(BaseModel):
    id: str
    topic: str
    subtopic: str
    concept: str
    prerequisite_ids: list[str] = Field(
        description="List of prerequisite group IDs.", default_factory=list
    )
    prerequisite_of_ids: list[str] = Field(
        description="List of group IDs that have this group as a prerequisite.",
        default_factory=list,
    )

    def __str__(self) -> str:
        return f"""
<id>
{self.id}
</id>

<topic>
{self.topic}
</topic>

<subtopic>
{self.subtopic}
</subtopic>

<concept>
{self.concept}
</concept>
"""

    def add_prequisite_ids(
        self,
        previous_groups: dict[str, "Group"],
        model: ModelName = MODEL,
        attempts: int = ATTEMPTS,
        max_tokens: int = MAX_TOKENS,
    ):
        if not previous_groups:
            return
        print(f"\nADDING PREREQUISITE IDS FOR GROUP: {self.id}\n")
        self.prerequisite_ids += create_prerequisite_group_ids(
            group=self,
            previous_groups=previous_groups,
            model=model,
            attempts=attempts,
            max_tokens=max_tokens,
        )
        self.prerequisite_ids = sorted(
            list(set(self.prerequisite_ids)), key=int, reverse=True
        )
        for prerequisite_id in self.prerequisite_ids:
            previous_groups[prerequisite_id].prerequisite_of_ids.append(self.id)


class Topics(BaseModel):
    topics: Annotated[dict[str, Topic], AfterValidator(dict_to_ordereddict)]
    groups: Annotated[dict[str, Group], AfterValidator(dict_to_ordereddict)] = Field(
        default_factory=dict
    )

    def create_groups(
        self,
        model: ModelName = MODEL,
        attempts: int = ATTEMPTS,
        max_tokens: int = MAX_TOKENS,
    ):
        group_id = 0
        for topic_name, topic in self.topics.items():
            for subtopic_name, subtopic in topic.subtopics.items():
                for concept_name in subtopic.concepts.keys():
                    group = Group(
                        id=str(group_id),
                        topic=topic_name,
                        subtopic=subtopic_name,
                        concept=concept_name,
                    )
                    previous_groups = {
                        k: self.groups[k]
                        for k in list(self.groups.keys())[-NUM_PREVIOUS_GROUPS:]
                    }
                    group.add_prequisite_ids(
                        previous_groups=previous_groups,
                        model=model,
                        attempts=attempts,
                        max_tokens=max_tokens,
                    )
                    self.groups[str(group_id)] = group
                    group_id += 1

    def add_concept_question_id(
        self,
        question_id: str,
        topic_name: str,
        subtopic_name: str,
        concept_name: str,
    ):
        concept = (
            self.topics[topic_name].subtopics[subtopic_name].concepts[concept_name]
        )
        concept.add_question_id(question_id)
        return self


def create_topic(
    text: str, model: ModelName = MODEL, attempts: int = ATTEMPTS
) -> Topic | None:
    sys_message = deindent(
        f"""
            You are a world class math course instructor. Extract the topic, subtopics, and concepts. Feel free to use your knowledge of the subject.
            {MIN_SUBTOPICS}-{MAX_SUBTOPICS} subtopics and {MIN_CONCEPTS}-{MAX_CONCEPTS} concepts each.
            The topics, subtopics, and concepts should be ordered and no longer than 5 words each.
            """
    )
    created_topic = ask_cld_or_oai(
        user_messages=[user_message(text)],
        system=sys_message,
        model=model,
        response_model=CreatedTopic,
        attempts=attempts,
        max_tokens=MAX_TOKENS,
    )
    return Topic.from_created_topic(created_topic) if created_topic else None


def create_topics(
    outline_file: Path | str,
    topics_file: Path | str,
    model: ModelName = ModelName.GPT_4,
    attempts: int = ATTEMPTS,
    max_tokens: int = MAX_TOKENS,
) -> Topics:
    outline = Path(outline_file).read_text()
    created_topics = [
        create_topic(topic, model=model, attempts=attempts)
        for topic in outline.splitlines()
    ]
    topics = Topics(topics={topic.name: topic for topic in created_topics if topic})
    topics.create_groups(model=model, attempts=attempts, max_tokens=max_tokens)
    with open(str(topics_file), "w") as f:
        json.dump(topics.model_dump(), f, indent=2)
    return topics


def create_question_group_id(
    groups: dict[str, Group],
    question: "Question",
    model: ModelName = MODEL,
    attempts: int = ATTEMPTS,
    max_tokens: int = MAX_TOKENS,
) -> str:
    groups_str = "\n".join([str(g) for g in groups.values()])
    sys_message = deindent(
        f"""
You are a world class math course instructor. You will be given a question with a problem and solution.
Assign the question to a topic, subtopic, and concept group. Return the group ID.

<groups>
{groups_str}
</groups>
"""
    )
    question_message = deindent(
        f"""
<question>

{question.problem_solution()}

</question>
"""
    )
    group_id = ask_cld_or_oai(
        user_messages=[user_message(question_message)],
        system=sys_message,
        model=model,
        response_model=Literal[*groups.keys(), "OTHER"],  # type: ignore
        attempts=attempts,
        max_tokens=max_tokens,
    )
    return group_id if group_id else "OTHER"


def create_subquestions_decision(
    question: "Question",
    model: ModelName = MODEL,
    attempts: int = ATTEMPTS,
    max_tokens: int = MAX_TOKENS,
) -> bool:
    system = deindent("""
                You are a world class math course instructor. You will be given a question with a problem and solution.
                You must decide if the question should be broken down into subquestions.
                If a question is higher than high school level, it should be broken down into subquestions.
                Return True if the question should be broken down, otherwise return False.
                """)
    user_messages = [user_message(f"<question>\n{str(question)}\n</question>")]
    try:
        res = ask_cld_or_oai(
            user_messages=user_messages,
            system=system,
            model=model,
            response_model=bool,
            attempts=attempts,
            max_tokens=max_tokens,
        )
        return res if res is not None else False
    except Exception as e:
        print(f"Error in create_subquestions_decision. User messages: {user_messages}")
        print(e)
        return False


def create_subquestions(
    question: "Question",
    model: ModelName = MODEL,
    attempts: int = ATTEMPTS,
    max_tokens: int = MAX_TOKENS,
) -> "SubQuestions | None":
    system = deindent(
        f"""
You are a world class math course instructor.
You will be given a question with a 'problem', a 'solution', a 'topic', a 'subtopic', and a 'concept'.
Based on the main question's problem and solution, break the question down into {MIN_SUBQUESTIONS}-{MAX_SUBQUESTIONS} subquestions.
The subquestions are basically the steps to solving the main question.
So the solution of the last subquestion should be the solution of the main question.
We want the students to show their working. That's why we need the subquestions.
The subquestions will be contained in the main question's solution. So the ids can be 1, 2, 3...
For each subquestion:
    1. Give it an id.
    2. Don't repeat the main question's 'problem' or 'solution'.
    3. Define the 'problem'.
    4. Give a detailed 'solution'.
"""
    )
    user_messages = [user_message(f"<question>\n{str(question)}\n</question>")]
    return ask_cld_or_oai(
        user_messages=user_messages,
        system=system,
        response_model=SubQuestions,
        model=model,
        attempts=attempts,
        max_tokens=max_tokens,
    )


class BaseQuestion(BaseModel):
    id: str
    problem: str
    solution: str

    def problem_solution(self) -> str:
        return f"<problem>\n{self.problem}\n</problem>\n\n<solution>\n{self.solution}\n</solution>"

    def __str__(self) -> str:
        return f"""
<id>
{self.id}
</id>

{self.problem_solution()}
"""

    # @field_validator("id")
    # @classmethod
    # def validate_id(cls, id: str, info: ValidationInfo) -> str:
    #     print(f"\nVALIDATING ID for {id}\n")
    #     context: dict | None = info.context
    #     if context is None:
    #         return id
    #     questions: dict[str, "BaseQuestion"] | None = context.get("questions")
    #     if questions is None:
    #         return id
    #     counter = 1
    #     while id in questions:
    #         id = f"{id}_{counter}"
    #         counter += 1
    #     return id


class SubQuestions(BaseModel):
    subquestions: list[BaseQuestion] = Field(
        min_length=MIN_SUBQUESTIONS, max_length=MAX_SUBQUESTIONS
    )

    @field_validator("subquestions")
    @classmethod
    def print_number_of_subquestions(
        cls, subquestions: list[BaseQuestion]
    ) -> list[BaseQuestion]:
        print(f"\nNUMBER OF SUBQUESTIONS: {len(subquestions)}\n")
        return subquestions


class Question(BaseQuestion):
    topic: str = ""
    subtopic: str = ""
    concept: str = ""
    group_id: str = ""
    subquestions: list[BaseQuestion] = Field(default_factory=list)

    def __str__(self) -> str:
        question_str = super().__str__()
        if self.topic:
            question_str += f"\n<topic>\n{self.topic}\n</topic>\n\n<subtopic>\n{self.subtopic}\n</subtopic>\n\n<concept>\n{self.concept}\n</concept>\n"
        return question_str

    def assign_group(
        self,
        topics: Topics,
        model: ModelName = MODEL,
        attempts: int = ATTEMPTS,
        max_tokens: int = MAX_TOKENS,
    ):
        if (not self.topic) and len(topics.groups) > 0:
            print(f"\nASSIGNING GROUP FOR QUESTION: {self.id}\n")
            group_id = create_question_group_id(
                groups=topics.groups,
                question=self,
                model=model,
                attempts=attempts,
                max_tokens=max_tokens,
            )
            print(f"GROUP ID: {group_id}")
            group = topics.groups.get(group_id)
            if not group:
                self.group_id = "OTHER"
                return
            self.topic = group.topic
            self.subtopic = group.subtopic
            self.concept = group.concept
            self.group_id = group_id
            topics.add_concept_question_id(
                question_id=self.id,
                topic_name=self.topic,
                subtopic_name=self.subtopic,
                concept_name=self.concept,
            )

    def get_prerequisite_question_ids(self, topics: Topics) -> list[str]:
        if self.group_id in ["OTHER", ""]:
            return []
        prerequisite_ids = set()
        group = topics.groups[self.group_id]
        for prerequisite_group_id in group.prerequisite_ids:
            prerequisite_group = topics.groups.get(prerequisite_group_id)
            if not prerequisite_group:
                continue
            prerequisite_group_questions = (
                topics.topics[prerequisite_group.topic]
                .subtopics[prerequisite_group.subtopic]
                .concepts[prerequisite_group.concept]
                .question_ids
            )
            if not prerequisite_group_questions:
                continue
            prerequisite_ids.add(random.choice(prerequisite_group_questions))
            if len(prerequisite_ids) == MAX_PREREQUISITES:
                break
        return sorted(prerequisite_ids, key=int)[:MAX_PREREQUISITES]

    def add_subquestions(
        self,
        model: ModelName = MODEL,
        attempts: int = ATTEMPTS,
        max_tokens: int = MAX_TOKENS,
    ):
        if self.group_id in ["OTHER", ""]:
            return
        print(f"\nADDING SUBQUESTIONS FOR QUESTION: {self.id}\n")
        if create_subquestions_decision(
            question=self, model=model, attempts=attempts, max_tokens=max_tokens
        ):
            subquestions = create_subquestions(
                question=self, model=model, attempts=attempts, max_tokens=max_tokens
            )
            if subquestions:
                self.subquestions = subquestions.subquestions


# data_dir = Path("/media/hamza/data2/MATH/train/")
# questions_dir = Path("math_102_questions")
# question_id = 0
# for folder in data_dir.iterdir():
#     if folder.is_dir() and folder.name != "counting_and_probability":
#         folder_questions = []
#         for question_file in folder.glob("*.json"):
#             question = json.loads(question_file.read_text())
#             if "5" in question["level"]:
#                 dest = questions_dir / f"{folder.name}/{question_id}.json"
#                 os.makedirs(dest.parent, exist_ok=True)
#                 with open(dest, "w") as f:
#                     json.dump(
#                         {
#                             "id": str(question_id),
#                             "problem": question["problem"],
#                             "solution": question["solution"],
#                         },
#                         f,
#                         indent=2,
#                     )
#                 question_id += 1
