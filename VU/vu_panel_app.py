import json
from collections import defaultdict

import panel as pn
from vu_panel import Topics

pn.extension("floatpanel", "gridstack", sizing_mode="stretch_both")  # type: ignore

DEFAULT_BUTTON_STYLE = "outline"
TOPIC_BUTTON_TYPE = "light"
SUBTOPIC_BUTTON_TYPE = "warning"
CONCEPT_BUTTON_TYPE = "primary"
QUESTION_BUTTON_TYPE = "success"
CLICKED_BUTTON_STYLE = "solid"
CLICKED_BUTTON_TYPE = "success"
PREREQ_BUTTON_STYLE = "solid"
PREREQ_BUTTON_TYPE = "primary"
POSTREQ_BUTTON_STYLE = "solid"
POSTREQ_BUTTON_TYPE = "warning"
MAX_QUESTION_BUTTONS = 3
MIN_BUTTON_HEIGHT = 35
MIN_BUTTON_WIDTH = 100
MARGIN = 5
NCOLS = 3
CARD_WIDTH_COLS = 4
CARD_HEIGHT_ROWS = 4

sidebar = pn.rx("")
collapsed_sidebar = pn.rx(False)

topics = Topics(**json.load(open("panel_topics.json", "r")))
buttons_dict = defaultdict(lambda: pn.rx({}))  # type: ignore


def reset_button_args():
    for button_id in buttons_dict:
        if button_id.count("_") == 0:
            buttons_dict[button_id].rx.value = {
                "button_style": DEFAULT_BUTTON_STYLE,
                "button_type": TOPIC_BUTTON_TYPE,
            }
        elif button_id.count("_") == 1:
            buttons_dict[button_id].rx.value = {
                "button_style": DEFAULT_BUTTON_STYLE,
                "button_type": SUBTOPIC_BUTTON_TYPE,
            }
        elif button_id.count("_") == 2:
            buttons_dict[button_id].rx.value = {
                "button_style": DEFAULT_BUTTON_STYLE,
                "button_type": CONCEPT_BUTTON_TYPE,
            }
        elif button_id.count("_") == 3:
            buttons_dict[button_id].rx.value = {
                "button_style": DEFAULT_BUTTON_STYLE,
                "button_type": QUESTION_BUTTON_TYPE,
            }


def clicked(button):
    button_id = button.obj.id
    node = topics.get(button_id)
    if node is None:
        return
    if (
        buttons_dict[button_id].rx.value["button_style"]  # type: ignore
        == CLICKED_BUTTON_STYLE
        and buttons_dict[button_id].rx.value["button_type"]  # type: ignore
        == CLICKED_BUTTON_TYPE
    ):
        reset_button_args()
        return
    reset_button_args()
    buttons_dict[button_id].rx.value = {
        "button_style": CLICKED_BUTTON_STYLE,
        "button_type": CLICKED_BUTTON_TYPE,
    }
    for prereq_id in node.prerequisite_ids:
        buttons_dict[prereq_id].rx.value = {
            "button_style": PREREQ_BUTTON_STYLE,
            "button_type": PREREQ_BUTTON_TYPE,
        }
    for postreq_id in node.postrequisite_ids:
        buttons_dict[postreq_id].rx.value = {
            "button_style": POSTREQ_BUTTON_STYLE,
            "button_type": POSTREQ_BUTTON_TYPE,
        }
    if button_id.count("_") == 3:
        problem = node.problem  # type: ignore
        solution = node.solution  # type: ignore
        sidebar.rx.value = f"""
# <span style='color:lightgreen'>QUESTION</span>
{problem}

## <span style='color:red'>Answer</span>
{solution}
"""
        collapsed_sidebar.rx.value = False
    else:
        sidebar.rx.value = ""
        collapsed_sidebar.rx.value = True


# topic_buttons = pn.Row()
topic_buttons = []
for i, (topic_name, topic) in enumerate(topics.topics.items()):
    # topic_col = pn.Column(margin=(0, 20, 0, 20), scroll=True)
    topic_col = pn.Card(
        title=f"Topic: {i+1}",
        # margin=(0, 20, 20, 20),
        # scroll=True,
        collapsible=False,
        sizing_mode="stretch_both",
        # height=1000,
        # width=500,
    )
    style_args = buttons_dict.get(
        topic.id,
        pn.rx({"button_style": DEFAULT_BUTTON_STYLE, "button_type": TOPIC_BUTTON_TYPE}),
    )
    buttons_dict[topic.id] = style_args
    topic_button = pn.widgets.Button(
        name=topic.topic,
        align="start",
        sizing_mode="fixed",
        min_height=MIN_BUTTON_HEIGHT,
        min_width=MIN_BUTTON_WIDTH,
        margin=MARGIN,
        on_click=clicked,
        button_style=style_args["button_style"],
        button_type=style_args["button_type"],
    )
    topic_button.id = topic.id  # type: ignore
    topic_col.append(topic_button)
    for j, (subtopic_name, subtopic) in enumerate(topic.subtopics.items()):
        subtopic_card = pn.Card(
            title=f"Subtopic: {j+1}",
            collapsible=False,
            scroll=True,
            sizing_mode="stretch_both",
            scroll_button_threshold=0,
            # margin=(20, 0, 0, 0),
        )
        style_args = buttons_dict.get(
            subtopic.id,
            pn.rx(
                {
                    "button_style": DEFAULT_BUTTON_STYLE,
                    "button_type": SUBTOPIC_BUTTON_TYPE,
                }
            ),
        )
        buttons_dict[subtopic.id] = style_args
        subtopic_button = pn.widgets.Button(
            name=subtopic.subtopic,
            align="start",
            sizing_mode="fixed",
            min_height=MIN_BUTTON_HEIGHT,
            min_width=MIN_BUTTON_WIDTH,
            margin=MARGIN,
            on_click=clicked,
            button_style=style_args["button_style"],
            button_type=style_args["button_type"],
        )
        subtopic_button.id = subtopic.id  # type: ignore
        subtopic_card.append(subtopic_button)
        # topic_col.append(subtopic_button)
        for k, (concept_name, concept) in enumerate(subtopic.concepts.items()):
            # concept_card = pn.Card(title=f"Concept: {k+1}", collapsible=False)
            style_args = buttons_dict.get(
                concept.id,
                pn.rx(
                    {
                        "button_style": DEFAULT_BUTTON_STYLE,
                        "button_type": CONCEPT_BUTTON_TYPE,
                    }
                ),
            )
            buttons_dict[concept.id] = style_args
            concept_button = pn.widgets.Button(
                name=f"Concept: {concept.concept}",
                align="start",
                sizing_mode="fixed",
                min_height=MIN_BUTTON_HEIGHT,
                min_width=MIN_BUTTON_WIDTH,
                margin=MARGIN,
                on_click=clicked,
                button_style=style_args["button_style"],
                button_type=style_args["button_type"],
            )
            concept_button.id = concept.id  # type: ignore
            # topic_col.append(concept_button)
            subtopic_card.append(concept_button)
            # concept_card.append(concept_button)
            questions_row = pn.Row(align="start", margin=(MARGIN, MARGIN, MARGIN, 20))
            for question_name, question in concept.questions.items():
                if question.question_number > MAX_QUESTION_BUTTONS:
                    break
                style_args = buttons_dict.get(
                    question.id,
                    pn.rx(
                        {
                            "button_style": DEFAULT_BUTTON_STYLE,
                            "button_type": QUESTION_BUTTON_TYPE,
                        }
                    ),
                )
                buttons_dict[question.id] = style_args
                question_button = pn.widgets.Button(
                    name=f"Question {question.question_number}",
                    align="start",
                    sizing_mode="fixed",
                    min_height=MIN_BUTTON_HEIGHT,
                    min_width=MIN_BUTTON_WIDTH,
                    margin=MARGIN,
                    on_click=clicked,
                    button_style=style_args["button_style"],
                    button_type=style_args["button_type"],
                )
                question_button.id = question.id  # type: ignore
                questions_row.append(question_button)
            # concept_card.append(questions_row)
            # subtopic_card.append(questions_row)
            # topic_col.append(questions_row)
            # subtopic_card.append(concept_card)
            # subtopic_card.append(concept_button)
            subtopic_card.append(questions_row)
            # subtopic_card.append(pn.Spacer(sizing_mode="stretch_width"))
        topic_col.append(subtopic_card)
    topic_buttons.append(topic_col)
    # topic_buttons.append(pn.Spacer(sizing_mode="stretch_width"))

grid = pn.GridSpec(sizing_mode="stretch_both")
card_groups = [
    topic_buttons[i : i + NCOLS] for i in range(0, len(topic_buttons), NCOLS)
]
template = pn.template.FastGridTemplate(
    title="VU",
    # main_layout=None,
    # main=[grid],
    sidebar=sidebar,
    collapsed_sidebar=False,
)
row = 0
for i, card_group in enumerate(card_groups):
    col = 0
    for j, card in enumerate(card_group):
        template.main[row : row + CARD_HEIGHT_ROWS, col : col + CARD_WIDTH_COLS] = card  # type: ignore
        # grid[row + CARD_HEIGHT_ROWS, :] = pn.Spacer(
        #     sizing_mode="stretch_width", height=30
        # )
        col += CARD_WIDTH_COLS
    row += CARD_HEIGHT_ROWS
template.servable()
# flex = pn.FlexBox(*topic_buttons, align_content="space-evenly")
# cards = pn.Column()
# for card_group in card_groups:
#     cards.append(pn.Row(*card_group))
#     cards.append(pn.Spacer(sizing_mode="stretch_width"))
# template = pn.template.MaterialTemplate(
#     title="VU",
#     main=[cards],
#     sidebar=sidebar,
#     collapsed_sidebar=True,
# ).servable()
