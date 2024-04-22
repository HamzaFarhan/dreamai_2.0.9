import json
import random

import pandas as pd
import streamlit as st
import time
from pydantic import BaseModel

st.set_page_config(page_title="Math 102", initial_sidebar_state="collapsed")


class Subtopic(BaseModel):
    topic: str = ""
    name: str = ""
    concepts: list[str] = []
    prerequisites: list[str] = []


class Topic(BaseModel):
    name: str
    subtopics: list[Subtopic]


def ai_delay(message: str = "Processing...⏳", dur: int = 5):
    with st.spinner(message):
        time.sleep(dur)


st.title("VU 🎓🏫")
outline = st.text_input("Enter the course outline here 📋")
pdf_file = None
if outline:
    if "topics_extracted" not in st.session_state:
        ai_delay("Extracting Topics and Subtopics...⛓️")
    st.session_state.topics_extracted = True
    pdf_file = st.file_uploader("Upload a course material PDF file 📖", type=["pdf"])
    topics = json.load(open("math_102_topics_with_concepts_and_prerequisites.json"))
    topics = [Topic(**topic) for topic in topics]

    # Dropdown to select a topic
    topic_names = [topic.name for topic in topics]
    selected_topic_name = st.sidebar.selectbox("Select a Topic", options=topic_names)
    selected_topic = next(
        topic for topic in topics if topic.name == selected_topic_name
    )

    # Dropdown to select a subtopic based on the selected topic
    subtopic_names = [subtopic.name for subtopic in selected_topic.subtopics]
    selected_subtopic_name = st.sidebar.selectbox(
        "Select a Subtopic", options=subtopic_names
    )

    def find_subtopic_by_name(name: str) -> Subtopic | None:
        if not name:
            return Subtopic()
        for topic in topics:
            for subtopic in topic.subtopics:
                if subtopic.name == name:
                    return subtopic
        return Subtopic()

    def show_df():
        subtopic_name = st.session_state.selected_subtopic_name
        subtopic = find_subtopic_by_name(subtopic_name)
        prereq_topics = [
            find_subtopic_by_name(prereq).topic for prereq in subtopic.prerequisites
        ]
        df = pd.DataFrame(
            {
                "Concepts": subtopic.concepts,
                "Prerequisite Subtopics": subtopic.prerequisites,
                "Prerequisite Topics": prereq_topics,
            }
        )
        st.header(f"{subtopic_name.title()}")
        st.dataframe(df, use_container_width=True)

    if st.sidebar.button("Show Concepts 📊"):
        st.session_state.selected_subtopic_name = selected_subtopic_name

    if "selected_subtopic_name" in st.session_state:
        show_df()
        subtopic = find_subtopic_by_name(st.session_state.selected_subtopic_name)
        topic = subtopic.topic
        if st.button("Random Question 💭❔"):
            if topic == "Quadratic Equations":
                # ai_delay("Generating Question...🛠️")
                questions = json.load(open("math_102_quad_eqs_question_codes.json"))
                values = [value for value in questions.values() if value]
                code = random.choice(values)
                try:
                    func = code.split("def ")[1].split("(")[0]
                    exec(code)
                    func = locals()[func]
                    res = func()
                    st.header("Question:")
                    st.write(res["question"])
                    st.header("Answer:")
                    st.write(res["final_answer"])
                    with st.expander("Show Steps 📝"):
                        for i, subquestion in enumerate(res["sub_questions"]):
                            st.subheader(f"Subquestion {i+1}:")
                            st.write(subquestion["question"])
                            st.subheader("Answer:")
                            st.write(subquestion["answer"])
                            st.subheader("Explanation:")
                            st.write(subquestion["explanation"])
                except Exception as e:
                    # add red cross emoji
                    st.error(f"Failed to execute the code. ❌\n{e}")
                with st.expander("Show Code 🤖"):
                    st.code(code)
            else:
                st.error(
                    "Random questions are only available for Quadratic Equations. ⚠️"
                )
