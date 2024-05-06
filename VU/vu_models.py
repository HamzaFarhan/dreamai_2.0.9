import json
from collections import OrderedDict
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
    ValidationInfo,
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

QUESTIONS_PER_FOLDER = 30
CONCEPT_WORD_COUNT = 3
MIN_SUBQUESTIONS = 2
MAX_SUBQUESTIONS = 3
MIN_TOPICS = 10
MAX_TOPICS = 15
MIN_SUBTOPICS = 3
MAX_SUBTOPICS = 5
MIN_CONCEPTS = 2
MAX_CONCEPTS = 5


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


def dict_to_ordereddict(d: dict | OrderedDict) -> dict:
    return dict(d)


class CourseSubtopic(BaseModel):
    name: str
    concepts: list[str] = Field(
        f"{MIN_CONCEPTS}-{MAX_CONCEPTS} concepts covered in the subtopic.",
        min_length=MIN_CONCEPTS,
        max_length=MAX_CONCEPTS,
    )


class CourseTopic(BaseModel):
    name: str
    subtopics: list[CourseSubtopic] = Field(
        f"{MIN_SUBTOPICS}-{MAX_SUBTOPICS} ordered subtopics with concepts.",
        min_length=MIN_SUBTOPICS,
        max_length=MAX_SUBTOPICS,
    )


class ConceptQuestion(BaseModel):
    id: str
    problem: str
    solution: str


class ConceptWithQuestionIDs(BaseModel):
    concept: str
    # questions: Annotated[
    #     dict[str, ConceptQuestion], AfterValidator(dict_to_ordereddict)
    # ] = Field(default_factory=OrderedDict)
    question_ids: list[str] = Field(default_factory=list)


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
    def from_course_topic(cls, course_topic: CourseTopic) -> "Topic":
        return cls(
            name=course_topic.name,
            subtopics={
                subtopic.name: Subtopic(
                    name=subtopic.name,
                    concepts={
                        concept: ConceptWithQuestionIDs(concept=concept)
                        for concept in subtopic.concepts
                    },
                )
                for subtopic in course_topic.subtopics
            },
        )


class Topics(BaseModel):
    topics: Annotated[dict[str, Topic], AfterValidator(dict_to_ordereddict)]

    @model_validator(mode="after")  # type: ignore
    def create_groups(self) -> "Topics":
        self._groups = {}
        group_id = 0
        for topic_name, topic in self.topics.items():
            for subtopic_name, subtopic in topic.subtopics.items():
                for concept_name in subtopic.concepts.keys():
                    self._groups[str(group_id)] = {
                        "id": str(group_id),
                        "topic": topic_name,
                        "subtopic": subtopic_name,
                        "concept": concept_name,
                    }
                    group_id += 1
        return self


@traceable(name="102_topics")
def create_topic(
    text: str, model: ModelName = MODEL, attempts: int = ATTEMPTS
) -> Topic | None:
    sys_message = deindent(
        f"""
            You are a world class math course instructor. Extract the topic, subtopics, and concepts. Feel free to use your knowledge of the subject.
            {MIN_SUBTOPICS}-{MAX_SUBTOPICS} subtopics and {MIN_CONCEPTS}-{MAX_CONCEPTS} concepts each.
            """
    )
    course_topic = ask_cld_or_oai(
        user_messages=[user_message(text)],
        system=sys_message,
        model=model,
        response_model=CourseTopic,
        attempts=attempts,
        max_tokens=MAX_TOKENS,
    )
    return Topic.from_course_topic(course_topic) if course_topic else None


@traceable(name="102_question_group")
def create_question_group(
    groups: dict[str, dict[str, str]],
    problem: str,
    solution: str,
    model: ModelName = MODEL,
    attempts: int = ATTEMPTS,
    max_tokens: int = MAX_TOKENS,
) -> dict[str, str] | None:
    groups_str = "\n".join([json.dumps(g) for g in groups.values()])
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

<problem>
{problem}
</problem>

<solution>
{solution}
</solution>

</question>
"""
    )
    group_id = ask_cld_or_oai(
        user_messages=[user_message(question_message)],
        system=sys_message,
        model=model,
        response_model=Literal[*groups.keys()],  # type: ignore
        attempts=attempts,
        max_tokens=max_tokens,
    )
    return groups.get(group_id) if group_id else None


@traceable(name="102_concept_question_ids")
def create_concept_questions_update_id(
    topics: Topics,
    questions: dict[str, "Question"],
    topic_name: str,
    subtopic_name: str,
    concept_name: str,
    question: "Question",
    model: ModelName = MODEL,
    attempts: int = ATTEMPTS,
    max_tokens: int = MAX_TOKENS,
) -> str:
    concept = topics.topics[topic_name].subtopics[subtopic_name].concepts[concept_name]
    # print(f"CONCEPT: {concept}")
    if not concept.question_ids or question.id in concept.question_ids:
        return question.id
    concept_questions = "\n---\n".join(
        [str(questions[id]) for id in concept.question_ids]
    )
    new_id = "NEW"
    response_model = Literal[*concept.question_ids, new_id]  # type: ignore
    # print(f"RESPONSE MODEL: {response_model}")
    questions_message = deindent(
        f"""
<existing_questions>
{concept_questions}
</existing_questions>
"""
    )
    sys_message = deindent(
        f"""
You are a world class validation model, your job is to check if a question is similar to any of the questions in the list.
If it's similar to any of the questions return the ID of that question.
If it's not similar to any of the questions return {new_id}.
By similar we mean that both questions are asking the same thing but in different ways.
So there would be no point in having both questions in the same set.
"""
    )
    question_message = deindent(
        f"""
<input question>

<problem>
{question.problem}
</problem>

<solution>
{question.solution}
</solution>

</input question>
"""
    )
    user_messages = [user_message(questions_message), user_message(question_message)]
    created_id = ask_cld_or_oai(
        user_messages=user_messages,
        system=sys_message,
        model=model,
        response_model=response_model,
        attempts=attempts,
        max_tokens=max_tokens,
    )
    if created_id is None or created_id == new_id:
        # concept.question_ids.append(question.id)
        return question.id
    return created_id


@traceable(name="102_subquestions_decision")
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
                Return "Yes" if the question should be broken down, otherwise return "No".
                """)
    user_messages = [user_message(f"<question>\n{str(question)}\n</question>")]
    try:
        res = ask_cld_or_oai(
            user_messages=user_messages,
            system=system,
            model=model,
            response_model=Literal["Yes", "No"],  # type: ignore
            attempts=attempts,
            max_tokens=max_tokens,
        )
        return res == "Yes"
    except Exception as e:
        print(f"Error in create_subquestions_decision. User messages: {user_messages}")
        print(e)
        return False


@traceable(name="102_subquestions")
def create_subquestions(
    question: "Question",
    context: dict,
    model: ModelName = MODEL,
    attempts: int = ATTEMPTS,
    max_tokens: int = MAX_TOKENS,
) -> "SubQuestions | None":
    ask_kwargs = context.get("ask_kwargs", {})
    ask_kwargs["model"] = model
    ask_kwargs["attempts"] = attempts
    ask_kwargs["max_tokens"] = max_tokens
    context["ask_kwargs"] = ask_kwargs  # type: ignore
    system = deindent(
        f"""
You are a world class math course instructor.
You will be given a question with a 'problem', a 'solution', a 'topic', a 'subtopic', and a 'concept'.
Based on the main question's problem and solution, break the question down into {MIN_SUBQUESTIONS}-{MAX_SUBQUESTIONS} subquestions.
The subquestions are basically prerequisites to the main question.
And if a student can solve the main question, we can assume that they have learned the underlying concepts of the subquestions.
No 2 subquestions can have the same concept.
The concepts don't have to be the same as the main question's concept.
Define the problem and solution and in a way that the subquestion could be considered a separate question even without the main question.
Don't make them vague, they should make sense even without the main question.
For each subquestion:
    1. The id should be <main_question_id>_<subquestion_number>.
    2. Don't repeat the main question's 'problem' or 'solution'.
    3. Define the 'problem'.
    4. Give a detailed 'solution'. This should be specifically for the subquestion and its variables. Not the main question.
"""
    )
    user_messages = [user_message(f"<question>\n{str(question)}\n</question>")]
    return ask_cld_or_oai(
        user_messages=user_messages,
        system=system,
        response_model=SubQuestions,
        validation_context=context,
        **ask_kwargs,
    )


class SubQuestions(BaseModel):
    subquestions: list["Question"] = Field(
        min_length=MIN_SUBQUESTIONS, max_length=MAX_SUBQUESTIONS
    )

    @field_validator("subquestions")
    @classmethod
    def print_number_of_subquestions(
        cls, subquestions: list["Question"]
    ) -> list["Question"]:
        print(f"\nNUMBER OF SUBQUESTIONS: {len(subquestions)}\n")
        return subquestions


class Question(BaseModel):
    id: str
    problem: str
    solution: str

    def all_dump(self) -> dict:
        d = self.model_dump()
        if hasattr(self, "_topic"):
            d["_topic"] = self._topic
            d["_subtopic"] = self._subtopic
            d["_concept"] = self._concept
        if hasattr(self, "_subquestion_ids"):
            d["_subquestion_ids"] = self._subquestion_ids
        return d

    def __str__(self) -> str:
        question_str = f"""
<id>
{self.id}
</id>

<problem>
{self.problem}
</problem>

<solution>
{self.solution}
</solution>
"""
        if hasattr(self, "_topic"):
            question_str += f"<topic>\n{self._topic}\n</topic>\n\n<subtopic>\n{self._subtopic}\n</subtopic>\n\n<concept>\n{self._concept}\n</concept>"
        return question_str

    @field_validator("id")
    @classmethod
    def validate_id(cls, id: str, info: ValidationInfo) -> str:
        print(f"\nVALIDATING ID for {id}\n")
        if not (context := info.context):
            return id
        questions: dict[str, "Question"] = context.get("questions")
        if questions is None:
            return id
        counter = 1
        while id in questions:
            id = f"{id}_{counter}"
            counter += 1
        return id

    @model_validator(mode="after")  # type: ignore
    def assign_group(self, info: ValidationInfo) -> "Question":
        print(f"\nASSIGNING GROUP for {self.id}\n")
        if not (context := info.context):
            return self
        topics: Topics = context.get("topics")
        if topics is None:
            return self
        if not hasattr(topics, "_groups"):
            return self
        group = create_question_group(
            groups=topics._groups,
            problem=self.problem,
            solution=self.solution,
            **context.get("ask_kwargs", {}),
        )
        if group:
            self._topic = group["topic"]
            self._subtopic = group["subtopic"]
            self._concept = group["concept"]
        return self

    @model_validator(mode="after")  # type: ignore
    def update_concept_questions(self, info: ValidationInfo) -> "Question":
        print(f"\nUPDATING CONCEPT QUESTIONS for {self.id}\n")
        if not (context := info.context):
            return self
        topics: Topics = context.get("topics")
        if topics is None:
            return self
        questions: dict[str, "Question"] = context.get("questions")
        if questions is None:
            return self
        if not hasattr(self, "_topic"):
            return self
        topic_name = self._topic
        subtopic_name = self._subtopic
        concept_name = self._concept
        question_id = create_concept_questions_update_id(
            topics=topics,
            questions=questions,
            topic_name=topic_name,
            subtopic_name=subtopic_name,
            concept_name=concept_name,
            question=self,
            **context.get("ask_kwargs", {}),
        )
        print(f"QUESTION ID: {question_id}")
        if question_id == self.id:
            topics.topics[topic_name].subtopics[subtopic_name].concepts[
                concept_name
            ].question_ids.append(question_id)
            questions[question_id] = self
        else:
            self = questions[question_id].model_copy()
        return self

    @model_validator(mode="after")  # type: ignore
    def vlidate_subquestions(self, info: ValidationInfo) -> "Question":
        print(f"\nCREATING SUBQUESTIONS for {self.id}\n")
        if hasattr(self, "_subquestion_ids"):
            print("Already has subquestions. Skipping.")
            return self
        self._subquestion_ids = []
        ask_kwargs = {}
        context = info.context
        if context is not None:
            ask_kwargs = context.get("ask_kwargs", {})
        if create_subquestions_decision(self, **ask_kwargs) and context is not None:
            # parent_ids = context.get("parent_ids", [])
            # parent_ids.append(self.id)
            # context["parent_ids"] = parent_ids
            subquestions = create_subquestions(
                question=self, context=context, **ask_kwargs
            )
            # self._subquestion_ids = []
            if subquestions:
                self._subquestion_ids = [
                    subquestion.id
                    for subquestion in subquestions.subquestions
                    if subquestion.id != self.id
                    and subquestion.id not in self._subquestion_ids
                ]
        return self
