from collections import OrderedDict
from typing import Literal, Union

from pydantic import BaseModel, Field

STR_ATTRS = ["topic", "subtopic", "concept", "question_number"]


class Node(BaseModel):
    topic: str
    prerequisite_ids: list[str] = Field(default_factory=list)
    postrequisite_ids: list[str] = Field(default_factory=list)

    @property
    def id(self) -> str:
        id = ""
        for i, attr in enumerate(STR_ATTRS):
            if hasattr(self, attr):
                if i == 0:
                    id += getattr(self, attr)
                else:
                    id += f"_{getattr(self, attr)}"
        return id

    def __str__(self) -> str:
        node_str = f"<id>\n{self.id}\n</id>"
        for attr in STR_ATTRS:
            if hasattr(self, attr):
                node_str += f"\n\n<{attr}>\n{getattr(self, attr).title()}\n</{attr}>"
        return node_str.strip()

    def add_prerequisite_id(self, id: str):
        if id == self.id:
            return
        prerequisite_ids = set(self.prerequisite_ids)
        prerequisite_ids.add(id)
        self.prerequisite_ids = list(prerequisite_ids)

    def add_postrequisite_id(self, id: str):
        if id == self.id:
            return
        postrequisite_ids = set(self.postrequisite_ids)
        postrequisite_ids.add(id)
        self.postrequisite_ids = list(postrequisite_ids)


class Topic(Node):
    subtopics: dict[str, "Subtopic"] = Field(default_factory=OrderedDict)

    def get(self, id: str) -> Node | None:
        split_id = id.split("_")
        if len(split_id) == 1:
            return self
        elif len(split_id) == 2:
            return self.subtopics[id]
        elif len(split_id) == 3:
            return self.subtopics["_".join(split_id[:2])].concepts[id]
        elif len(split_id) == 4:
            return (
                self.subtopics["_".join(split_id[:2])]
                .concepts["_".join(split_id[:3])]
                .questions[id]
            )
        print(f"ID {id} not found")
        return None

    def add_subtopics(
        self,
        subtopics: Union[list[Union["Subtopic", str]], "Subtopic", str] | None = None,
    ):
        if subtopics is None or subtopics == [] or subtopics == "":
            return
        if not isinstance(subtopics, list):
            subtopics = [subtopics]
        for subtopic in subtopics:
            if isinstance(subtopic, str):
                subtopic = Subtopic(topic=self.topic, subtopic=subtopic)
            subtopic.topic = self.topic
            self.subtopics[subtopic.id] = subtopic

    def add_dependancies(
        self,
        id: str,
        dependancies: list[Node | str] | Node | str,
        mode: Literal["pre", "post"] = "pre",
    ):
        if dependancies is None or dependancies == [] or dependancies == "":
            return
        split_id = id.split("_")
        if split_id[0] != self.id:
            print(f"ID {id} does not match topic {self.id}")
            return
        if not isinstance(dependancies, list):
            dependancies = [dependancies]
        for dependancy in dependancies:
            if isinstance(dependancy, str):
                dependancy_id = dependancy
            else:
                dependancy_id = dependancy.id
            if dependancy_id == id:
                continue
            split_dependancy_id = dependancy_id.split("_")
            for i, splits in enumerate(zip(split_id, split_dependancy_id)):
                _, s2 = splits
                if i == 0:
                    if mode == "pre":
                        self.add_prerequisite_id(s2)
                    elif mode == "post":
                        self.add_postrequisite_id(s2)
                elif i == 1:
                    subtopic_id = "_".join(split_id[:2])
                    subtopic_dependancy_id = "_".join(split_dependancy_id[:2])
                    if mode == "pre":
                        self.subtopics[subtopic_id].add_prerequisite_id(
                            subtopic_dependancy_id
                        )
                    elif mode == "post":
                        self.subtopics[subtopic_id].add_postrequisite_id(
                            subtopic_dependancy_id
                        )
                elif i == 2:
                    subtopic_id = "_".join(split_id[:2])
                    concept_id = "_".join(split_id[:3])
                    concept_dependancy_id = "_".join(split_dependancy_id[:3])
                    if mode == "pre":
                        self.subtopics[subtopic_id].concepts[
                            concept_id
                        ].add_prerequisite_id(concept_dependancy_id)
                    elif mode == "post":
                        self.subtopics[subtopic_id].concepts[
                            concept_id
                        ].add_postrequisite_id(concept_dependancy_id)
                elif i == 3:
                    subtopic_id = "_".join(split_id[:2])
                    concept_id = "_".join(split_id[:3])
                    question_id = "_".join(split_id[:4])
                    question_dependancy_id = "_".join(split_dependancy_id[:4])
                    if mode == "pre":
                        self.subtopics[subtopic_id].concepts[concept_id].questions[
                            question_id
                        ].add_prerequisite_id(question_dependancy_id)
                    elif mode == "post":
                        self.subtopics[subtopic_id].concepts[concept_id].questions[
                            question_id
                        ].add_postrequisite_id(question_dependancy_id)


class Topics(BaseModel):
    topics: dict[str, Topic] = Field(default_factory=OrderedDict)

    def get(self, id: str) -> Node | None:
        split_id = id.split("_")
        return self.topics[split_id[0]].get(id)

    def add_topics(
        self,
        topics: Union[list[Union["Topic", str]], "Topic", str] | None = None,
    ):
        if topics is None or topics == [] or topics == "":
            return
        if not isinstance(topics, list):
            topics = [topics]
        for topic in topics:
            if isinstance(topic, str):
                topic = Topic(topic=topic)
            self.topics[topic.id] = topic

    def add_prerequisites(
        self, id: str, prerequisites: list[Node | str] | Node | str | None = None
    ):
        if prerequisites is None or prerequisites == [] or prerequisites == "":
            return
        topic_key = id.split("_")[0]
        self.topics[topic_key].add_dependancies(
            id=id, dependancies=prerequisites, mode="pre"
        )
        if not isinstance(prerequisites, list):
            prerequisites = [prerequisites]
        for prereq in prerequisites:
            if isinstance(prereq, str):
                prereq_id = prereq
            else:
                prereq_id = prereq.id
            if prereq_id == id:
                continue
            topic_key = prereq_id.split("_")[0]
            self.topics[topic_key].add_dependancies(
                id=prereq_id, dependancies=id, mode="post"
            )


class Subtopic(Node):
    subtopic: str
    concepts: dict[str, "Concept"] = Field(default_factory=OrderedDict)

    def add_concepts(
        self,
        concepts: Union[list[Union["Concept", str]], "Concept", str] | None = None,
    ):
        if concepts is None or concepts == [] or concepts == "":
            return
        if not isinstance(concepts, list):
            concepts = [concepts]
        for concept in concepts:
            if isinstance(concept, str):
                concept = Concept(
                    topic=self.topic, subtopic=self.subtopic, concept=concept
                )
            concept.topic = self.topic
            concept.subtopic = self.subtopic
            self.concepts[concept.id] = concept


class Concept(Node):
    subtopic: str
    concept: str
    questions: dict[str, "Question"] = Field(default_factory=OrderedDict)

    def add_questions(
        self,
        questions: Union[list["Question"], "Question"] | None = None,
    ):
        if questions is None or questions == []:
            return
        if not isinstance(questions, list):
            questions = [questions]
        for question in questions:
            question.topic = self.topic
            question.subtopic = self.subtopic
            question.concept = self.concept
            question.question_number = len(self.questions) + 1
            self.questions[question.id] = question


class BaseQuestion(BaseModel):
    problem: str
    solution: str

    def problem_solution(self) -> str:
        return f"<problem>\n{self.problem}\n</problem>\n\n<solution>\n{self.solution}\n</solution>"


class Question(Node, BaseQuestion):
    subtopic: str
    concept: str
    question_number: int = 1
    subquestions: list[BaseQuestion] = Field(default_factory=list)

    def __str__(self) -> str:
        return f"""
<id>
{self.id}
</id>

{self.problem_solution()}
""".strip()
