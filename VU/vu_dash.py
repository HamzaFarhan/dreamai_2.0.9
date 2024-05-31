import re
import json
from collections import OrderedDict
import dash_bootstrap_components as dbc
import dash_cytoscape as cyto
from dash import Dash, Input, Output, callback, html, dcc
from vu_panel import Topics

cyto.load_extra_layouts()

topics = Topics(**json.load(open("math_102_latest_topics_may_30.json", "r")))

NUM_TOPICS = 15


def remove_asy(text: str) -> str:
    return re.sub(r"\[asy\].*?\[/asy\]", "", text, flags=re.DOTALL)


def generate_elements(
    topics: Topics, clicked_subtopic_ids: list[str] | None = None
) -> dict:
    clicked_subtopic_ids = clicked_subtopic_ids or []
    topics_list = list(topics.topics.values())[:NUM_TOPICS]
    elements = OrderedDict()
    elements["root"] = {
        "data": {"id": "root", "label": "MATH 102"},
        "classes": "course",
    }
    # elements = OrderedDict(
    #     {
    #         topic.id: {
    #             "data": {"id": topic.id, "label": topic.topic},
    #             "classes": "topic",
    #         }
    #         for topic in topics_list
    #     }
    # )
    # for i in range(len(elements) - 1):
    #     source_id = list(elements.keys())[i]
    #     target_id = list(elements.keys())[i + 1]
    #     edge_id = f"{source_id}->{target_id}"
    #     elements[edge_id] = {"data": {"source": source_id, "target": target_id}}
    for topic_idx, topic in enumerate(topics_list):
        elements[topic.id] = {
            "data": {"id": topic.id, "label": f"{topic_idx+1}: {topic.topic.title()}"},
            "classes": "topic",
        }
        elements[f"root->{topic.id}"] = {
            "data": {"source": "root", "target": topic.id},
            "classes": "course_edge",
        }
        for subtopic_idx, subtopic in enumerate(topic.subtopics.values()):
            elements[subtopic.id] = {
                "data": {
                    "id": subtopic.id,
                    "label": "",
                    # "parent": subtopic.topic,
                },
                "classes": "subtopic",
            }
            elements[f"{topic.id}->{subtopic.id}"] = {
                "data": {"source": topic.id, "target": subtopic.id}
            }
            if subtopic.id in clicked_subtopic_ids:
                elements[subtopic.id]["data"]["label"] = (
                    f"{subtopic_idx+1}: {subtopic.subtopic}"
                )
                for concept_idx, concept in enumerate(subtopic.concepts.values()):
                    elements[concept.id] = {
                        "data": {
                            "id": concept.id,
                            "label": f"{concept_idx+1}: {concept.concept}",
                            # "parent": f"{subtopic.topic}_{subtopic.subtopic}",
                        },
                        "classes": "concept",
                    }
                    elements[f"{subtopic.id}->{concept.id}"] = {
                        "data": {"source": subtopic.id, "target": concept.id}
                    }
                    for question in concept.questions.values():
                        elements[question.id] = {
                            "data": {
                                "id": question.id,
                                "label": str(question.question_number),
                                # "parent": f"{question.topic}_{question.subtopic}_{question.concept}",
                            },
                            "classes": "question",
                        }
                        elements[f"{concept.id}->{question.id}"] = {
                            "data": {"source": concept.id, "target": question.id}
                        }
    return elements


external_stylesheets = [dbc.themes.CERULEAN]
app = Dash(external_stylesheets=external_stylesheets)
styles = {
    "container": {
        "position": "fixed",
        "display": "flex",
        # "flex-direction": "row",
        "height": "100%",
        "width": "100%",
    },
    # "cy-container": {"flex": "auto", "position": "relative", "flex-wrap": "wrap"},
    "cy-container": {"flex": "1", "position": "relative"},
    # "cy-container": {"flex-wrap": "wrap", "position": "relative"},
}
graph = cyto.Cytoscape(
    style=styles["cy-container"],
    clearOnUnhover=True,
    # responsive=True,
    maxZoom=4,
    minZoom=0.5,
    id="cytoscape-compound",
    layout={"name": "breadthfirst", "roots": "#root", "directed": True},
    # layout={"name": "dagre"},
    # layout={"name": "fcose"},
    # layout={"name": "grid", "cols": 3},
    # layout={"name": "klay"},
    stylesheet=[
        {"selector": "node", "style": {"content": "data(label)"}},
        {
            "selector": ".course",
            "style": {
                "background-color": "yellow",
                "font-size": "25px",
                "font-weight": "bold",
            },
        },
        {
            "selector": ".topic",
            "style": {
                "background-color": "red",
                # "font-size": "18px",
                # "font-weight": "bold",
            },
        },
        {
            "selector": ".subtopic",
            "style": {"background-color": "green"},
        },
        {
            "selector": ".concept",
            "style": {"background-color": "blue"},
        },
        {"selector": ".question", "style": {"background-color": "black"}},
        {
            "selector": ".selected",
            "style": {"background-color": "orange"},
        },
        {
            "selector": "edge",
            "style": {
                "curve-style": "unbundled-bezier",
                "target-arrow-shape": "vee",
                "target-arrow-color": "blue",
                "line-color": "blue",
            },
        },
        {
            "selector": ".prereqs",
            "style": {
                "curve-style": "unbundled-bezier",
                "target-arrow-shape": "vee",
                "target-arrow-color": "blue",
                "line-color": "red",
            },
        },
        {
            "selector": ".course_edge",
            "style": {
                "curve-style": "unbundled-bezier",
                "target-arrow-shape": "vee",
                "target-arrow-color": "white",
                "line-color": "white",
            },
        },
        {
            "selector": ".postreqs",
            "style": {
                "curve-style": "unbundled-bezier",
                "target-arrow-shape": "vee",
                "target-arrow-color": "green",
                "target-arrow-width": "100000px",
                "line-color": "green",
            },
        },
    ],
    elements=list(generate_elements(topics=topics).values()),
)
legend = html.Div(
    children=[
        dcc.Markdown(
            "**LEGEND:**",
            style={
                "display": "inline-block",
                "margin-right": "10px",
                "background": "linear-gradient(to right, green, blue, red)",
                "-webkit-background-clip": "text",
                "-webkit-text-fill-color": "transparent",
            },
        ),
        html.Div(
            html.P("Topic", style={"color": "red"}),
            style={"display": "inline-block", "margin-right": "10px"},
        ),
        html.Div(
            html.P("Subtopic", style={"color": "green"}),
            style={"display": "inline-block", "margin-right": "10px"},
        ),
        html.Div(
            html.P("Concept", style={"color": "blue"}),
            style={"display": "inline-block", "margin-right": "10px"},
        ),
        html.Div(
            html.P("Question", style={"color": "black"}),
            style={"display": "inline-block", "margin-right": "10px"},
        ),
        html.Div(
            html.P("Selected Node", style={"color": "orange"}),
            style={"display": "inline-block", "margin-right": "10px"},
        ),
        html.Div(
            html.P("Prerequisite Edge", style={"color": "red"}),
            style={"display": "inline-block", "margin-right": "10px"},
        ),
        html.Div(
            html.P("Postrequisite Edge", style={"color": "green"}),
            style={"display": "inline-block", "margin-right": "10px"},
        ),
    ],
    style={
        "position": "absolute",
        "top": "10px",
        "right": "10px",
        "background-color": "white",
        "padding": "10px",
    },
)
question_modals = OrderedDict(
    {
        f"modal-{question.id}": dbc.Modal(
            [
                dbc.ModalHeader(dbc.ModalTitle(f"Quesion: {i+1}")),
                dbc.ModalBody(
                    dcc.Markdown(
                        f"# Problem\n{remove_asy(question.problem)}", mathjax=True
                    )
                ),
                dbc.ModalFooter(
                    dcc.Markdown(
                        f"## Solution\n{remove_asy(question.solution)}", mathjax=True
                    )
                ),
            ],
            id=f"modal-{question.id}",
            is_open=False,
        )
        for i, question in enumerate(topics.questions.values())
    }
)

layout = html.Div(
    id="big-div",
    style=styles["container"],
    children=[*list(question_modals.values()), legend, graph],
)
app.layout = layout

# @callback(Output(layout, "children"), Input(graph, "tapNodeData"))
# def clicked(tap):
#     # layout_elements = layout.children[0].elements  # type: ignore
#     # print(
#     #     f"\n\nLAYOUT: {[e for e in layout_elements if e['data'].get('label','Hmm')=='Clicked']}\n\n"
#     # )
#     children = []
#     elements = generate_elements(topics=topics)
#     if tap:
#         node_id = tap["id"]
#         node = topics.get(node_id)
#         if node is not None:
#             for prereq_id in node.prerequisite_ids:
#                 edge_id = f"{prereq_id}->{node_id}"
#                 elements[edge_id] = {"data": {"source": prereq_id, "target": node_id}}
#     # elif hover:
#     #     element_data = elements[hover["id"]]["data"]
#     #     label = element_data.get("label", "")
#     #     print(f"\n\nHovered: <{label}>\n\n")
#     #     if label == "Hovered":
#     #         label = ""
#     #     elif label == "":
#     #         label = "Hovered"
#     #     element_data["label"] = label
#     graph.elements = list(elements.values())  # type: ignore
#     children.append(graph)
#     return children


# @callback(Output("big-div", "children"), Input(graph, "mouseoverNodeData"))
# def hover(data):
#     children = []
#     elements = generate_elements(topics=topics)
#     if data:
#         element_data = elements[data["id"]]["data"]
#         if element_data.get("label", False):
#             element_data["label"] = topics.concepts[data["id"]].concept
#     graph.elements = list(elements.values())  # type: ignore
#     children.append(graph)
#     return children

callable_args = [Output(layout, "children")] + [Input(graph, "tapNodeData")]


@callback(*callable_args, supress_callback_exceptions=True)
def add_edges(data):
    children = []
    elements = generate_elements(topics=topics)
    for modal in question_modals.values():
        modal.is_open = False  # type: ignore
    if data:
        node_id = data["id"]
        node = topics.get(node_id)
        if node is not None:
            # print(f"Clicked on {node_id}")
            if node_id.count("_") == 3:
                # print(f"Opening modal for {node_id}")
                question_modals[f"modal-{node_id}"].is_open = True  # type: ignore
            subtopic_ids = []
            if node_id.count("_") >= 1:
                subtopic_ids.append("_".join(node_id.split("_")[:2]))
                elements = generate_elements(
                    topics=topics, clicked_subtopic_ids=subtopic_ids
                )
            # if node_id.count("_") > 1:
            for prereq_id in node.prerequisite_ids:
                prereq_subtoic = "_".join(prereq_id.split("_")[:2])
                if prereq_subtoic not in subtopic_ids:
                    subtopic_ids.append(prereq_subtoic)
                    elements = generate_elements(
                        topics=topics, clicked_subtopic_ids=subtopic_ids
                    )
                edge_id = f"{prereq_id}->{node_id}"
                # print(f"\n\nEDGE ID: {edge_id}\n\n")
                elements[edge_id] = {
                    "data": {"source": prereq_id, "target": node_id},
                    "classes": "prereqs",
                }
            for postreq_id in node.postrequisite_ids:
                postreq_subtopic = "_".join(postreq_id.split("_")[:2])
                if postreq_subtopic not in subtopic_ids:
                    subtopic_ids.append(postreq_subtopic)
                    elements = generate_elements(
                        topics=topics, clicked_subtopic_ids=subtopic_ids
                    )
                edge_id = f"{node_id}->{postreq_id}"
                elements[edge_id] = {
                    "data": {"source": node_id, "target": postreq_id},
                    "classes": "postreqs",
                }
            elements[node_id]["classes"] = "selected"

    graph.elements = list(elements.values())  # type: ignore
    children += list(question_modals.values())
    children.append(legend)
    children.append(graph)
    return children


if __name__ == "__main__":
    app.run(debug=True, port="8000")
