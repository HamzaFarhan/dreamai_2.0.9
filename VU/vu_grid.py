import json

import panel as pn
from vu_models import Question, Topics

DAY = 8
NCOLS = 4

questions_file = f"math_102_created_questions_may_{DAY}.json"
questions = {
    id: Question(**q) for id, q in json.load(open(questions_file, "r")).items()
}

topics = Topics(**json.load(open(f"math_102_final_topics_may_{DAY}.json", "r")))
topic_names = list(topics.topics.keys())

active_topics = []


def get_active_topics(
    event,
    topics: Topics = topics,
):
    global active_topics
    active_topics = []
    selected_topic = event.obj.name
    print(f"Selected topic: {selected_topic}")
    for question in topics.groups.values():
        topic = question.topic
        if topic == selected_topic:
            active_topics.append(topic)
        else:
            continue
        for prereq_id in question.prerequisite_ids:
            prereq_topic = topics.groups[prereq_id].topic
            if topic != prereq_topic:
                active_topics.append(prereq_topic)


def create_grid(
    active_topics: list[str] = [],
    ncols: int = NCOLS,
    topic_names: list[str] = topic_names,
):
    print(f"Active topics: {active_topics}")
    topic_chunks = [
        topic_names[i : i + ncols] for i in range(0, len(topic_names), ncols)
    ]
    grid = pn.GridStack(ncols=ncols, nrows=len(topic_names), sizing_mode="stretch_both")
    for i, topics in enumerate(topic_chunks):
        for j, topic_name in enumerate(topics):
            if topic_name in active_topics:
                grid[i, j] = pn.widgets.Button(
                    name=topic_name,
                    button_style="solid",
                    button_type="success",
                    on_click=get_active_topics,
                )
            else:
                grid[i, j] = pn.widgets.Button(
                    name=topic_name,
                    button_style="outline",
                    button_type="default",
                    on_click=get_active_topics,
                )

    return grid


pn.Column("# HELLOOOO", create_grid(active_topics=active_topics.param.value)).servable()
