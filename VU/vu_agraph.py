import streamlit as st
import json
from streamlit_agraph import agraph, Node, Edge, Config
from vu_models import Question, Topics
import networkx as nx


DAY = 8

questions_file = f"math_102_created_questions_may_{DAY}.json"
questions = {
    id: Question(**q) for id, q in json.load(open(questions_file, "r")).items()
}

topics = Topics(**json.load(open(f"math_102_final_topics_may_{DAY}.json", "r")))
topic_names = list(topics.topics.keys())

G = nx.DiGraph()

for topic_name in topics.topics:
    G.add_node(topic_name)
    for question in topics.groups.values():
        topic = question.topic
        for prereq_id in question.prerequisite_ids:
            prereq_topic = topics.groups[prereq_id].topic
            if topic != prereq_topic and topic:
                G.add_edge(prereq_topic, topic)

try:
    nx.find_cycle(G)
    G.remove_edges_from(nx.find_cycle(G))
except nx.exception.NetworkXNoCycle:
    pass

dependencies = {"Spiderman": ["Captain_Marvel"], "Captain_Marvel": []}

nodes = [
    Node(id=i, label=str(i), size=25, shape="dot", font={"color": "white"})
    for i in G.nodes
]
edges = [Edge(source=j, target=i) for i, j in G.edges if i in G.nodes and j in G.nodes]


def draw_edges(node: str = ""):
    node = node or st.session_state.get("selected_node", "")
    for friend in dependencies.get(node, []):
        edges.append(
            Edge(
                source=node,
                label="friend_of",
                target=friend,
                # **kwargs
            )
        )
        draw_edges(node=friend)


with st.sidebar:
    st.session_state.selected_node = st.selectbox(
        "Select a node", dependencies.keys(), index=None
    )
# draw_edges()
config = Config(
    width=1000,
    height=1000,
    directed=True,
    physics=True,
    hierarchical=True,
    staticGraph=True,
    # **kwargs
)

return_value = agraph(nodes=nodes, edges=edges, config=config)
