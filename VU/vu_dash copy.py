import json
from collections import OrderedDict
import dash_bootstrap_components as dbc
import dash_cytoscape as cyto
from dash import Dash, Input, Output, callback, html, dcc
from vu_panel import Topics

cyto.load_extra_layouts()

topics = Topics(**json.load(open("panel_topics.json", "r")))

NUM_TOPICS = 3


def generate_elements(topics: Topics) -> dict:
    topics_list = list(topics.topics.values())[:NUM_TOPICS]
    elements = OrderedDict(
        {
            topic.id: {
                "data": {"id": topic.id, "label": topic.topic},
                "classes": "topic",
            }
            for topic in topics_list
        }
    )
    for i in range(len(elements) - 1):
        source_id = list(elements.keys())[i]
        target_id = list(elements.keys())[i + 1]
        edge_id = f"{source_id}->{target_id}"
        elements[edge_id] = {"data": {"source": source_id, "target": target_id}}
    for topic in topics_list:
        for subtopic in topic.subtopics.values():
            elements[subtopic.id] = {
                "data": {
                    "id": subtopic.id,
                    "label": subtopic.subtopic,
                    # "parent": subtopic.topic,
                }
            }
            elements[f"{topic.id}->{subtopic.id}"] = {
                "data": {"source": topic.id, "target": subtopic.id}
            }
            for concept in subtopic.concepts.values():
                elements[concept.id] = {
                    "data": {
                        "id": concept.id,
                        "label": concept.concept,
                        # "parent": f"{subtopic.topic}_{subtopic.subtopic}",
                    }
                }
                elements[f"{subtopic.id}->{concept.id}"] = {
                    "data": {"source": subtopic.id, "target": concept.id}
                }
                # for question in concept.questions.values():
                #     elements[question.id] = {
                #         "data": {
                #             "id": question.id,
                #             "label": str(question.question_number),
                #             # "parent": f"{question.topic}_{question.subtopic}_{question.concept}",
                #         }
                #     }
                #     elements[f"{concept.id}->{question.id}"] = {
                #         "data": {"source": concept.id, "target": question.id}
                #     }
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
    minZoom=1,
    id="cytoscape-compound",
    # layout={"name": "breadthfirst"},
    # layout={"name": "dagre"},
    # layout={"name": "cose"},
    layout={"name": "cola"},
    stylesheet=[
        {"selector": "node", "style": {"content": "data(label)"}},
        {
            "selector": "edge",
            "style": {
                "curve-style": "bezier",
                "target-arrow-shape": "vee",
                "target-arrow-color": "red",
                "line-color": "blue",
            },
        },
    ],
    elements=list(generate_elements(topics=topics).values()),
)

layout = html.Div(
    id="big-div",
    style=styles["container"],
    children=[graph],
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


@callback(Output(layout, "children"), Input(graph, "tapNodeData"))
def add_edges(data):
    children = []
    elements = generate_elements(topics=topics)
    if data:
        node_id = data["id"]
        node = topics.get(node_id)
        if node is not None:
            for prereq_id in node.prerequisite_ids:
                edge_id = f"{prereq_id}->{node_id}"
                elements[edge_id] = {"data": {"source": prereq_id, "target": node_id}}
        question = topics.questions.get(node_id)
        if question is not None:
            tabs = dcc.Tabs(
                value="",
                children=[
                    dcc.Tab(
                        label="QUESTION",
                        children=[
                            html.P(f"PROBLEM:\n{question.problem}"),
                            html.Br(),
                            html.P(f"SOLUTION:\n{question.solution}"),
                        ],
                    )
                ],
            )
            children.append(tabs)
    graph.elements = list(elements.values())  # type: ignore
    children.append(graph)
    return children


if __name__ == "__main__":
    app.run(debug=True, port="8000")
