from pydantic import BaseModel, Field


class ConceptWithQuestionIDs(BaseModel):
    concept: str
    question_ids: list[str] = Field(default_factory=list)


class Subtopic(BaseModel):
    name: str
    concepts: list[ConceptWithQuestionIDs] = Field(default_factory=list)


class Topic(BaseModel):
    name: str
    subtopics: list[Subtopic]


class QuestionWithConcept(BaseModel):
    id: str
    problem: str
    solution: str
    topic: str
    subtopic: str
    concept: str


class QuestionWithConceptAndSubquestions(QuestionWithConcept):
    subquestions: list[QuestionWithConcept]


"""
The ids in the question_ids list will be ids of QuestionWithConceptAndSubquestions objects.
It will not have ids of any subquestions. Only the main question ids will be present in the question_ids list.
The concept field in a QuestionWithConceptAndSubquestions object would be the same as the concept field in the ConceptWithQuestionIDs object.

So now if a QuestionWithConceptAndSubquestions object has some subquestions, for each subquestion we will:
    1. Go to the relevant Topic object using subquestion.topic.
    2. Go to the relevant Subtopic object using subquestion.subtopic.
    3. Go to the relevant ConceptWithQuestionIDs object using subquestion.concept.
    4. Find the relevant prerequisite question(s) using the question_ids list in the ConceptWithQuestionIDs object.

And if we start with a topic name, subtropic name, and concept name instead, we will:
    1. Go to the relevant Topic object using the topic name.
    2. Go to the relevant Subtopic object using the subtopic name.
    3. Go to the relevant ConceptWithQuestionIDs object using the concept name.
    4. Find the relevant prerequisite question(s) using the question_ids list in the ConceptWithQuestionIDs object.

This way, we can easily find the prerequisite questions for a question, or a subquestion, or a concept.
As I said, the question_ids list will only have the ids of the main questions, not the subquestions.
"""
