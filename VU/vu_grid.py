import json
from collections import defaultdict

import panel as pn
from vu_models import Question, Topics

pn.extension("floatpanel", "gridstack", sizing_mode="stretch_both")  # type: ignore

DAY = 16

NCOLS = 3
CARD_WIDTH_COLS = 4
CARD_HEIGHT_ROWS = 4
MIN_BUTTON_HEIGHT = 35
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

topics_file = f"math_102_final_topics_may_{DAY}.json"
questions_file = f"math_102_created_questions_may_{DAY}.json"

group_to_questions = defaultdict(list)
with open(questions_file, "r") as f:
    for q in json.load(f).values():
        question = Question(**q)
        group_to_questions[question.group_id].append(question)

topics = Topics(**json.load(open(topics_file, "r")))
buttons_dict = defaultdict(dict)
for group in topics.groups.values():
    buttons_dict[group.topic]["group_id"] = group.id
    buttons_dict[group.topic]["button_args"] = pn.rx(
        {"button_style": DEFAULT_BUTTON_STYLE, "button_type": TOPIC_BUTTON_TYPE}
    )

    buttons_dict[f"{group.topic}_{group.subtopic}"]["group_id"] = group.id
    buttons_dict[f"{group.topic}_{group.subtopic}"]["button_args"] = pn.rx(
        {"button_style": DEFAULT_BUTTON_STYLE, "button_type": SUBTOPIC_BUTTON_TYPE}
    )

    buttons_dict[f"{group.topic}_{group.subtopic}_{group.concept}"]["group_id"] = (
        group.id
    )
    buttons_dict[f"{group.topic}_{group.subtopic}_{group.concept}"]["button_args"] = (
        pn.rx(
            {"button_style": DEFAULT_BUTTON_STYLE, "button_type": CONCEPT_BUTTON_TYPE}
        )
    )

    for i in range(len(group_to_questions[group.id])):
        buttons_dict[f"{group.topic}_{group.subtopic}_{group.concept}_{i}"][
            "group_id"
        ] = group.id
        buttons_dict[f"{group.topic}_{group.subtopic}_{group.concept}_{i}"][
            "button_args"
        ] = pn.rx(
            {"button_style": DEFAULT_BUTTON_STYLE, "button_type": QUESTION_BUTTON_TYPE}
        )


def reset_button_args():
    for button_id in buttons_dict:
        if button_id.count("_") == 0:
            buttons_dict[button_id]["button_args"].rx.value = {
                "button_style": DEFAULT_BUTTON_STYLE,
                "button_type": TOPIC_BUTTON_TYPE,
            }
        elif button_id.count("_") == 1:
            buttons_dict[button_id]["button_args"].rx.value = {
                "button_style": DEFAULT_BUTTON_STYLE,
                "button_type": SUBTOPIC_BUTTON_TYPE,
            }
        elif button_id.count("_") == 2:
            buttons_dict[button_id]["button_args"].rx.value = {
                "button_style": DEFAULT_BUTTON_STYLE,
                "button_type": CONCEPT_BUTTON_TYPE,
            }
        elif button_id.count("_") == 3:
            buttons_dict[button_id]["button_args"].rx.value = {
                "button_style": DEFAULT_BUTTON_STYLE,
                "button_type": QUESTION_BUTTON_TYPE,
            }


def update_button_args(
    button_id: str,
    group_ids: list[str],
    button_style: str = DEFAULT_BUTTON_STYLE,
    button_type: str = TOPIC_BUTTON_TYPE,
):
    for group_id in group_ids:
        group = topics.groups[group_id]
        if button_id.count("_") == 0:
            update_id = group.topic
            print(f"update_id: {update_id}")
            if update_id != button_id:
                buttons_dict[update_id]["button_args"].rx.value = {
                    "button_style": button_style,
                    "button_type": button_type,
                }
        elif button_id.count("_") == 1:
            update_id = f"{group.topic}_{group.subtopic}"
            if update_id != button_id:
                buttons_dict[update_id]["button_args"].rx.value = {
                    "button_style": button_style,
                    "button_type": button_type,
                }
        elif button_id.count("_") == 2:
            update_id = f"{group.topic}_{group.subtopic}_{group.concept}"
            if update_id != button_id:
                buttons_dict[update_id]["button_args"].rx.value = {
                    "button_style": button_style,
                    "button_type": button_type,
                }
        elif button_id.count("_") == 3:
            for i in range(len(group_to_questions[group_id])):
                update_id = f"{group.topic}_{group.subtopic}_{group.concept}_{i}"
                if update_id != button_id:
                    buttons_dict[update_id]["button_args"].rx.value = {
                        "button_style": button_style,
                        "button_type": button_type,
                    }


def clicked(button):
    button_id = button.obj.id
    # print(button_name)
    if (
        buttons_dict[button_id]["button_args"].rx.value["button_style"]
        == CLICKED_BUTTON_STYLE
        and buttons_dict[button_id]["button_args"].rx.value["button_type"]
        == CLICKED_BUTTON_TYPE
    ):
        reset_button_args()
        return
    reset_button_args()
    buttons_dict[button_id]["button_args"].rx.value = {
        "button_style": CLICKED_BUTTON_STYLE,
        "button_type": CLICKED_BUTTON_TYPE,
    }
    group = topics.groups[buttons_dict[button_id]["group_id"]]
    print(
        f"\n\n{button_id}\n{group.id}\n{group.topic}\n{group.subtopic}\n{group.concept}\n{group.prerequisite_ids}\n"
    )
    update_button_args(
        button_id=button_id,
        group_ids=group.prerequisite_ids,
        button_style=PREREQ_BUTTON_STYLE,
        button_type=PREREQ_BUTTON_TYPE,
    )
    update_button_args(
        button_id=button_id,
        group_ids=group.prerequisite_of_ids,
        button_style=POSTREQ_BUTTON_STYLE,
        button_type=POSTREQ_BUTTON_TYPE,
    )


def make_button(
    button_id: str, button_name: str, button_args: dict
) -> pn.widgets.Button:
    button = pn.widgets.Button(
        name=button_name,
        button_style=button_args["button_style"],
        button_type=button_args["button_type"],
        sizing_mode="stretch_both",
        on_click=clicked,
        min_height=MIN_BUTTON_HEIGHT,
    )
    button.id = button_id  # type: ignore
    return button


topic_cards = {}
subtopic_cards = {}
buttons = {}
for group in topics.groups.values():
    topic_card = topic_cards.get(
        group.topic,
        pn.Card(
            title=f"Topic: {len(topic_cards)+1}",
            collapsible=True,
            collapsed=False,
            sizing_mode="stretch_both",
            scroll=True,
        ),
    )
    button_id = group.topic
    if button_id not in buttons:
        button_args = buttons_dict[group.topic]["button_args"]
        button = make_button(
            button_id=button_id, button_name=group.topic, button_args=button_args
        )
        buttons[button_id] = button
        topic_card.append(button)

    button_id = f"{group.topic}_{group.subtopic}"
    if button_id not in buttons:
        button_args = buttons_dict[f"{group.topic}_{group.subtopic}"]["button_args"]
        button = make_button(
            button_id=button_id, button_name=group.subtopic, button_args=button_args
        )
        buttons[button_id] = button
        topic_card.append(button)

    button_id = f"{group.topic}_{group.subtopic}_{group.concept}"
    if button_id not in buttons:
        button_args = buttons_dict[f"{group.topic}_{group.subtopic}_{group.concept}"][
            "button_args"
        ]
        button = make_button(
            button_id=button_id, button_name=group.concept, button_args=button_args
        )
        buttons[button_id] = button
        topic_card.append(button)

    for i, _ in enumerate(group_to_questions[group.id]):
        button_id = f"{group.topic}_{group.subtopic}_{group.concept}_{i}"
        if button_id not in buttons:
            button_args = buttons_dict[
                f"{group.topic}_{group.subtopic}_{group.concept}_{i}"
            ]["button_args"]
            button = make_button(
                button_id=button_id, button_name=f"Q{i+1}", button_args=button_args
            )
            buttons[button_id] = button
            topic_card.append(button)

    topic_cards[group.topic] = topic_card

grid = pn.GridSpec(sizing_mode="stretch_both")
cards = list(topic_cards.values())
card_groups = [cards[i : i + NCOLS] for i in range(0, len(cards), NCOLS)]
row = 0
for i, card_group in enumerate(card_groups):
    col = 0
    for j, card in enumerate(card_group):
        grid[row : row + CARD_HEIGHT_ROWS, col : col + CARD_WIDTH_COLS] = card
        col += CARD_WIDTH_COLS
    row += CARD_HEIGHT_ROWS

template = pn.template.FastGridTemplate(
    title="VU", main_layout=None, main=grid
).servable()
