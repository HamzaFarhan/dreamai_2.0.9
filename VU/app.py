import json

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Math 102")

st.title("VU 🎓🏫")
topics = json.load(open("math_102_app_topics.json"))
# topics = OrderedDict(
#     {
#         topic["name"]: OrderedDict(
#             {
#                 subtopic["name"]: OrderedDict(
#                     {
#                         concept["concept"]: concept["question_ids"]
#                         for concept in subtopic["concepts"]
#                     }
#                 )
#                 for subtopic in topic["subtopics"]
#             }
#         )
#         for topic in json.load(open("math_102_final_topics.json"))
#     }
# )
# concepts_dict = {}
selected_topic_name = st.sidebar.selectbox("Select a Topic", options=topics.keys())
selected_subtopic_name = st.sidebar.selectbox(
    "Select a Subtopic", options=topics[selected_topic_name].keys()
)
subtopic_concepts = topics[selected_topic_name][selected_subtopic_name]
selected_concept_name = st.sidebar.selectbox(
    "Select a Concept",
    options=subtopic_concepts.keys(),
)
questions = json.load(open("math_102_app_questions.json"))
# questions = {
#     str(q["id"]): q
#     for q in [
#         json.loads(f.read_text())
#         for f in Path("math_102_final_questions").glob("*.json")
#     ]
# }
if subtopic_concepts:
    st.session_state["show"] = True
else:
    st.session_state["show"] = False
print(f"SUBTOPIC: {selected_subtopic_name}, CONCEPT: {selected_concept_name}")

if st.session_state.get("show", False):
    selected_questions = [
        questions[id]
        for id in topics[selected_topic_name][selected_subtopic_name][
            selected_concept_name
        ]
    ]
    for i, question in enumerate(selected_questions, start=1):
        if st.button(f"Question {i}❔"):
            st.subheader("Question:")
            st.write(question["problem"])
            st.subheader("Solution:")
            st.write(question["solution"])
            with st.expander("Show Steps 📝"):
                for j, step in enumerate(question["subquestions"], start=1):
                    st.subheader(f"Step {j}:")
                    st.write(step["problem"])
                    st.subheader("Solution:")
                    st.write(step["solution"])
            prereq_questions = set()
            prereq_concepts = []
            for subquestion in question["subquestions"]:
                try:
                    prereq_qs = [
                        questions[id]["problem"]
                        for id in topics[subquestion["topic"]][subquestion["subtopic"]][
                            subquestion["concept"]
                        ]
                        if questions[id]["problem"] != prereq_questions
                    ]
                    prereq_questions |= set(prereq_qs)
                    prereq_concepts += [subquestion["concept"]] * len(prereq_qs)
                except KeyError:
                    pass
            if len(prereq_questions) > 0:
                with st.expander("Show Prerequisites 📚"):
                    st.dataframe(
                        pd.DataFrame(
                            {
                                "Prerequisite Questions": list(prereq_questions),
                                # "Prerequisite Concepts": prereq_concepts,
                            }
                        ),
                    )
