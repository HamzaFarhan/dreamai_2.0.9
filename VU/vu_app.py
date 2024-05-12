import json

import streamlit as st
from vu_models import Question, Topics

DAY = 8

st.set_page_config(page_title="🎓🏫")
st.title("Math 102 ➗✖️➕➖")

questions_file = f"math_102_created_questions_may_{DAY}.json"
questions = {
    id: Question(**q) for id, q in json.load(open(questions_file, "r")).items()
}

topics = Topics(**json.load(open(f"math_102_final_topics_may_{DAY}.json", "r")))
topic_names = list(topics.topics.keys())
print(f"\n\nSESSION STATE\n{st.session_state}\n\n")


def set_previous():
    st.session_state["previous_topic"] = st.session_state["selected_topic"]
    st.session_state["previous_subtopic"] = st.session_state["selected_subtopic"]
    st.session_state["previous_concept"] = st.session_state["selected_concept"]


def go_back():
    st.session_state["selected_topic"] = st.session_state["previous_topic"]
    st.session_state["selected_subtopic"] = st.session_state["previous_subtopic"]
    st.session_state["selected_concept"] = st.session_state["previous_concept"]


def get_idx(key: str, names: list[str]) -> int | None:
    idx = None
    value = st.session_state.get(key, None)
    if value is not None and value in names:
        idx = names.index(value)
    return idx


with st.sidebar:
    st.title("Topics")
    topic_idx = get_idx(key="selected_topic", names=topic_names)
    st.session_state["selected_topic"] = st.radio(
        label="Select a topic", options=topic_names, index=topic_idx
    )

if st.session_state.get("selected_topic", None) is not None:
    selected_topic = st.session_state["selected_topic"]
    subtopic_names = list(topics.topics[selected_topic].subtopics.keys())
    subtopic_idx = get_idx(key="selected_subtopic", names=subtopic_names)
    col1, col2 = st.columns(2)
    with col1:
        st.title("Subtopics")
        st.session_state["selected_subtopic"] = st.radio(
            label="Select a subtopic", options=subtopic_names, index=subtopic_idx
        )
    if st.session_state.get("selected_subtopic", None) is not None:
        selected_subtopic = st.session_state["selected_subtopic"]
        concept_names = list(
            topics.topics[selected_topic].subtopics[selected_subtopic].concepts.keys()
        )
        concept_idx = get_idx(key="selected_concept", names=concept_names)
        with col2:
            st.title("Concepts")
            st.session_state["selected_concept"] = st.radio(
                label="Select a concept", options=concept_names, index=concept_idx
            )
        if st.session_state.get("selected_concept", None) is not None:
            selected_concept = st.session_state["selected_concept"]
            print(
                f"\n\nSELECTED TOPIC and SUBTOPIC and CONCEPT: {selected_topic}, {selected_subtopic}, {selected_concept}"
            )
            concept = (
                topics.topics[selected_topic]
                .subtopics[selected_subtopic]
                .concepts[selected_concept]
            )

            if concept.question_ids:
                st.markdown(
                    "<h1 style='text-align: center'>Questions</h1>",
                    unsafe_allow_html=True,
                )
                for i, id in enumerate(concept.question_ids, start=1):
                    question = questions[id]
                    st.subheader(f"{i}: {question.problem}")
                    prerequisite_question_ids = question.get_prerequisite_question_ids(
                        topics=topics
                    )
                    if prerequisite_question_ids:
                        with st.expander("Prerequisites 📝"):
                            pre_col1, pre_col2 = st.columns(2)
                            with pre_col1:
                                st.subheader("Questions")
                            with pre_col2:
                                st.subheader("Concepts")
                            for j, preq_id in enumerate(
                                prerequisite_question_ids, start=1
                            ):
                                prerequisite_question = questions[preq_id]
                                with pre_col1:
                                    st.write(f"{j}: {prerequisite_question.problem}")
                                with pre_col2:
                                    if st.button(
                                        f"{prerequisite_question.concept}",
                                        key=f"prereq_{i}_{j}",
                                    ):
                                        set_previous()
                                        st.session_state["selected_topic"] = (
                                            prerequisite_question.topic
                                        )
                                        st.session_state["selected_subtopic"] = (
                                            prerequisite_question.subtopic
                                        )
                                        st.session_state["selected_concept"] = (
                                            prerequisite_question.concept
                                        )
                                        st.rerun()
                    if question.subquestions:
                        with st.expander("Subquestions 📝"):
                            for k, subquestion in enumerate(
                                question.subquestions, start=1
                            ):
                                st.write(f"Step {k}: {subquestion.problem}")
                                # st.write(f"Solution: {subquestion.solution}")


if (
    st.session_state.get("previous_topic", None)
    and st.session_state.get("previous_subtopic", None)
    and st.session_state.get("previous_concept", None)
):
    if st.button("Back"):
        go_back()
        st.session_state["previous_topic"] = None
        st.session_state["previous_subtopic"] = None
        st.session_state["previous_concept"] = None
        st.rerun()
