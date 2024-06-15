import json
import random
import time
import typing as _t
from pathlib import Path
from collections import OrderedDict
import pandas as pd

import anthropic
import instructor
import openai
from dotenv import load_dotenv

from dreamai.ai import ModelName, ask_cld_or_oai, user_message, assistant_message

from vu_models import (
    MAX_CONCEPTS,
    MAX_SUBTOPICS,
    MIN_CONCEPTS,
    MIN_SUBTOPICS,
    BaseQuestion,
    CreatedTopic,
    Question,
    Subtopic,
    Topic,
    Topics,
    Concept,
)

random.seed(42)

load_dotenv()

ask_oai = instructor.from_openai(openai.OpenAI())
ask_cld = instructor.from_anthropic(anthropic.Anthropic())

SYSTEM_PREFIX = "You are a world class math course instructor."
MIN_WORDS = 3
MAX_WORDS = 5
QUESTIONS_PER_FOLDER = 80


def topics_to_df(topics: Topics, df_file: str | Path = "") -> pd.DataFrame:
    def append_data(
        topic: Topic,
        subtopic: Subtopic | None = None,
        concept: Concept | None = None,
        question: Question | None = None,
    ):
        df_data["Topic"].append(topic.topic)
        df_data["Subtopic"].append(subtopic.subtopic if subtopic else "")
        df_data["Concept"].append(concept.concept if concept else "")
        df_data["Problem"].append(question.problem if question else "")
        df_data["Solution"].append(question.solution if question else "")
        df_data["Difficulty"].append(question.difficulty if question else "")

    df_data = OrderedDict(
        {
            "Topic": [],
            "Subtopic": [],
            "Concept": [],
            "Problem": [],
            "Solution": [],
            "Difficulty": [],
        }
    )
    for topic in topics.topics.values():
        if not topic.subtopics:
            append_data(topic=topic)
        for subtopic in topic.subtopics.values():
            if not subtopic.concepts:
                append_data(topic=topic, subtopic=subtopic)
            for concept in subtopic.concepts.values():
                if not concept.questions:
                    append_data(topic=topic, subtopic=subtopic, concept=concept)
                for question in concept.questions.values():
                    append_data(
                        topic=topic,
                        subtopic=subtopic,
                        concept=concept,
                        question=question,
                    )

    topics_df = pd.DataFrame(df_data)
    if df_file:
        topics_df.to_csv(df_file, index=False)
    return topics_df


def df_to_topics(df: pd.DataFrame | None = None, df_file: str | Path = "") -> Topics:
    df = pd.read_csv(df_file) if df_file else df
    assert df is not None, "Dataframe is required"
    topics_from_df = Topics()
    for _, row in df.iterrows():
        topic = row["Topic"]
        subtopic = row["Subtopic"]
        concept = row["Concept"]
        problem = row["Problem"]
        solution = row["Solution"]
        difficulty = row["Difficulty"]
        if not subtopic or not isinstance(subtopic, str):
            topics_from_df.add_topics(topic)
        elif not concept or not isinstance(concept, str):
            topics_from_df.add_subtopics(Subtopic(topic=topic, subtopic=subtopic))
        elif not problem or not isinstance(problem, str):
            topics_from_df.add_concepts(
                Concept(topic=topic, subtopic=subtopic, concept=concept)
            )
        else:
            topics_from_df.add_questions(
                Question(
                    topic=topic,
                    subtopic=subtopic,
                    concept=concept,
                    problem=problem,
                    solution=solution,
                    difficulty=difficulty,
                )
            )
    return topics_from_df


def create_topics(
    outline: list[str] | str,
    model: ModelName = ModelName.GPT_4O,
    topics_file: str | Path = "",
) -> Topics:
    topic_system = f"""\
    {SYSTEM_PREFIX}
    You'll be given a topic description from a course outline and you have to generate a {MIN_WORDS}-{MAX_WORDS} word topic name that encapsulates the description.
    Then, generate {MIN_SUBTOPICS}-{MAX_SUBTOPICS} subtopics for the topic. Also {MIN_WORDS}-{MAX_WORDS} words each.
    Then for each subtopic, generate {MIN_CONCEPTS}-{MAX_CONCEPTS} concepts. Also {MIN_WORDS}-{MAX_WORDS} words each. The concepts should be related to the subtopic.
    Think of concepts as the smallest unit of knowledge that can be taught from the subtopic. And add a verb to the concept to make it actionable.
    For example:
    "Calculate Derivatives" instead of "Derivatives".
    "Identify Finite Sets" instead of "Finite Sets".
    "Find the y-intercept" instead of "y-intercept".
    The subtopics and concepts should be in the correct order.
    """
    topics = Topics()
    if isinstance(outline, str):
        outline = outline.split("\n")
    for line in outline:
        topic: CreatedTopic | None = ask_cld_or_oai(
            ask_cld=ask_cld,
            ask_oai=ask_oai,
            model=model,
            response_model=CreatedTopic,
            system=topic_system,
            messages=[
                user_message(
                    f"<topic_description>\n{line.strip()}\n</topic_description>"
                )
            ],
        )  # type: ignore
        if topic is None:
            continue
        topic2 = Topic(topic=topic.name)
        for subtopic in topic.subtopics:
            subtopic2 = Subtopic(topic=topic.name, subtopic=subtopic.name)
            subtopic2.add_concepts(subtopic.concepts)
            topic2.add_subtopics(subtopic2)
        topics.add_topics(topic2)
        if topics_file:
            with open(Path(topics_file).with_suffix(".json"), "w") as f:
                json.dump(topics.model_dump(), f, indent=2)
    return topics


def create_subquestions(question: Question, model: ModelName = ModelName.GPT_4O):
    system = """
    You are world class math instructor.
    You will be given a problem and its solution and your job is to break down the solution into steps and explain each step in detail.
    I will be using your steps as a transcript for text-to-speech. So, make sure the steps are in plain English and easy to understand.
    The text-to-speech model would get confused by back slashes and other symbols. So, make sure to remove them.
    For example, instead of writing $x^2$, write x squared. For fractions, write x over y. etc. No brackets or other symbols.
    For math operations, wrtie plus, minus, times, divided by, etc. instead of +, -, *, /, etc.
    If a number is -5, write negative 5. If a number is 2.5, write 2 point 5.
    But make sure to not lose the meaning of the math expression. A student should be able to understand the math expression from the text-to-speech.
    No more than 5 steps per problem.
    Make sure the final answer is included in the last step.
    """

    messages = [
        user_message(
            f"<problem>\n{question.problem}\n</problem>\n\n<solution>\n{question.solution}\n</solution>"
        )
    ]
    try:
        subquestions = ask_cld_or_oai(
            ask_cld=ask_cld,
            ask_oai=ask_oai,
            messages=messages,
            system=system,
            model=model,
            response_model=list[BaseQuestion],
        )
    except Exception as e:
        print(e)
        subquestions = []
    question.subquestions = subquestions  # type: ignore


def create_code(question: Question, model: ModelName = ModelName.GPT_4O):
    system = Path("code_prompt.txt").read_text()
    user = f"<problem>\n{question.problem}\n</problem>\n\n<solution>\n{question.solution}\n</solution>"
    if question.subquestions:
        user += "\n\n<subquestions>"
        for i, subquestion in enumerate(question.subquestions, start=1):
            user += f"\n<subquestion_{i}>\n{subquestion}\n</subquestion_{i}>"
        user += "\n</subquestions>"
    messages = [user_message(user), assistant_message("```python")]
    try:
        code = ask_cld_or_oai(
            ask_cld=ask_cld,
            ask_oai=ask_oai,
            messages=messages,
            system=system,
            model=model,
            response_model=str,
        )  # type: ignore
        question.code = code  # type: ignore
    except Exception as e:
        print(e)


def assign_questions(
    questions_dir: str | Path,
    topics: Topics | None = None,
    topics_file: str | Path = "",
    assigner_model: ModelName = ModelName.HAIKU,
    subquestion_model: ModelName = ModelName.GPT_4O,
    code_model: ModelName = ModelName.GPT_4O,
    assigned_questions_file: str | Path = "assigned_questions.json",
    questions_per_folder: int = QUESTIONS_PER_FOLDER,
    num_questions: int | None = None,
) -> Topics:
    assert Path(questions_dir).exists(), f"{questions_dir} does not exist"
    assert topics or topics_file, "Either topics or topics_file must be provided."
    if topics_file:
        topics_file = Path(topics_file).with_suffix(".json")
        if topics_file.exists():
            print(f"Loading topics from {topics_file}")
            topics = Topics(**json.loads(topics_file.read_text()))
    assert topics, "Topics must be provided."
    questions_dir = Path(questions_dir)
    questions = [
        BaseQuestion(**json.loads(question_file.read_text()))
        for folder in questions_dir.iterdir()
        for question_file in list(folder.glob("*.json"))[:questions_per_folder]
    ]
    random.shuffle(questions)

    assigned_questions_file = Path(assigned_questions_file).with_suffix(".json")
    assigned_questions = (
        json.loads(assigned_questions_file.read_text())
        if assigned_questions_file.exists()
        else {}
    )
    assigned_questions["used"] = assigned_questions.get("used", 0)
    assigned_questions["questions"] = [
        Question(**question) for question in assigned_questions.get("questions", [])
    ]

    questions_system = f"""\
    {SYSTEM_PREFIX}
    You'll be given the problem and solution of a question and list of topic_subtopic_concept objects.
    Based on your knowledge of math, you have to decide which topic_subtopic_concept the question belongs to.
    """
    num_questions = num_questions or len(questions)
    used_index = assigned_questions["used"]
    for i, question in enumerate(
        questions[used_index:num_questions], start=used_index + 1
    ):
        print(f"Question {i}")
        concept_strs = [
            str(concept)
            for concept in topics.concepts.values()
            if len(concept.questions) < 3
        ]
        if not concept_strs:
            break

        objects_str = "\n\n".join(concept_strs)
        concept_ids = list(topics.concepts.keys())
        messages = [
            user_message(
                f"<question>\n{question}\n</question>\n\n<objects>\n{objects_str}\n</objects>"
            )
        ]
        try:
            belongs_to: str = ask_cld_or_oai(
                ask_cld=ask_cld,
                ask_oai=ask_oai,
                messages=messages,
                system=questions_system,
                model=assigner_model,
                response_model=_t.Literal[*concept_ids],  # type: ignore
            )
            split = belongs_to.split("_")
            assigned_question = Question(
                topic=split[0],
                subtopic=split[1],
                concept=split[2],
                problem=question.problem,
                solution=question.solution,
            )
            create_subquestions(question=assigned_question, model=subquestion_model)
            create_code(question=assigned_question, model=code_model)
            assigned_questions["questions"].append(assigned_question.model_dump())
            topics.add_questions(assigned_question)
            if topics_file:
                with open(Path(topics_file).with_suffix(".json"), "w") as f:
                    json.dump(topics.model_dump(), f, indent=2)
            with open(assigned_questions_file, "w") as f:
                json.dump(
                    {"used": i, "questions": assigned_questions["questions"]},
                    f,
                    indent=2,
                )
            time.sleep(0.3)
        except Exception as e:
            print(e)
            continue

    return topics


def add_dependencies(
    topics: Topics | None = None,
    topics_file: str | Path = "",
    model: ModelName = ModelName.HAIKU,
    prerequisities_file: str | Path = "prerequisites.json",
) -> Topics:
    assert topics or topics_file, "Either topics or topics_file must be provided."
    if topics_file:
        topics_file = Path(topics_file).with_suffix(".json")
        if topics_file.exists():
            print(f"Loading topics from {topics_file}")
            topics = Topics(**json.loads(topics_file.read_text()))
    assert topics, "Topics must be provided."

    prereq_system = f"""\
    {SYSTEM_PREFIX}
    You'll be given a question with a problem and solution and a list of other questions.
    Based on your knowledge of math, you have to decide which question form the list is a prerequisite to the given question.
    Just one question. If none are a prerequisite, or if the question is super easy for a highschooler, select 'None'.
    """
    prerequisites_file = Path(prerequisities_file).with_suffix(".json")
    prerequisites = (
        json.loads(prerequisites_file.read_text())
        if prerequisites_file.exists()
        else {}
    )
    question_values = list(topics.questions.values())

    for question_idx, question in enumerate(question_values):
        if question.id in prerequisites:
            continue
        prereq_qs = [
            prereq_q
            for prereq_q in question_values[:question_idx]
            if prereq_q.concept != question.concept
        ]
        prereq_strs = [
            f"<question>\n<id>\n{prereq_q.id}\n</id>\n{prereq_q.problem}\n{prereq_q.solution}\n</question>"
            for prereq_q in prereq_qs
        ]
        if not prereq_strs:
            continue
        candidate_questions = "\n\n".join(prereq_strs)
        messages = [
            user_message(
                f"<question>\n{question.problem}\n{question.solution}\n</question>\n\n<candidate_questions>\n{candidate_questions}\n</candidate_questions>"
            )
        ]
        try:
            prereq_id: str = ask_cld_or_oai(
                ask_cld=ask_cld,
                ask_oai=ask_oai,
                messages=messages,
                system=prereq_system,
                model=model,
                response_model=_t.Literal[
                    "None", *[question.id for question in prereq_qs]  # type: ignore
                ],
            )
            if prereq_id not in ["None", None]:
                topics.add_prerequisites(
                    id=question.id, prerequisites=topics.get(prereq_id)
                )
                if topics_file:
                    with open(Path(topics_file).with_suffix(".json"), "w") as f:
                        json.dump(topics.model_dump(), f, indent=2)
            prerequisites[question.id] = prereq_id
            with open(prerequisities_file, "w") as f:
                json.dump(prerequisites, f, indent=2)
            time.sleep(0.3)
        except Exception as e:
            print(e)
            continue
    return topics
