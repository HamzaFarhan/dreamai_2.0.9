import json
from collections import defaultdict

import panel as pn
from vu_models import Question, Topics

pn.extension("floatpanel", "gridstack")  # type: ignore

NCOLS = 3
DAY = 16

questions_file = f"math_102_created_questions_may_{DAY}.json"
questions = defaultdict(list)
for q in json.load(open(questions_file, "r")).values():
    questions[q["group_id"]].append(Question(**q))

topics = Topics(**json.load(open(f"math_102_final_topics_may_{DAY}.json", "r")))

flex_mode = pn.rx(False)
flex_mode_button_name = {False: "Full View", True: "Compact View"}
sidebar_toggle = pn.rx(True)
sidebar = pn.rx("")
buttons = {}
triggered_buttons = []


def toggle_flex_mode(event):
    flex_mode.rx.value = not flex_mode.rx.value  # type: ignore
    event.obj.name = flex_mode_button_name[flex_mode.rx.value]  # type: ignore


flex_mode_button = pn.widgets.Button(
    name=flex_mode_button_name[flex_mode.rx.value],  # type: ignore
    on_click=toggle_flex_mode,
)


def clear_triggered_buttons():
    for triggered_button in triggered_buttons:
        if triggered_button.count("_") == 1:
            buttons[triggered_button].button_style = "outline"
            buttons[triggered_button].button_type = "warning"
        elif triggered_button.count("_") == 2:
            buttons[triggered_button].button_style = "outline"
            buttons[triggered_button].button_type = "primary"
    triggered_buttons.clear()


def update_button_args(event):
    button_id = event.obj.id
    group_id = button_id.split("_")[0]
    button_type = buttons[button_id].button_type
    if button_type == "success":
        sidebar_toggle.rx.value = False  # type: ignore
        clear_triggered_buttons()
        return
    clear_triggered_buttons()
    buttons[button_id].button_style = "solid"
    buttons[button_id].button_type = "success"
    if button_id.count("_") == 2:
        sidebar_toggle.rx.value = False
        sidebar.rx.value = (
            "# <span style='color:lightgreen'>QUESTIONS</span>  \n\n\n"
            + (
                "\n\n------------\n\n".join(
                    [
                        f"### Q{i} - {question.problem}"
                        for i, question in enumerate(questions[group_id], start=1)
                    ]
                )
            )
        )
    else:
        sidebar_toggle.rx.value = True  # type: ignore
        sidebar.rx.value = ""
    triggered_buttons.append(button_id)
    for prereq_id in topics.groups[group_id].prerequisite_ids:
        group = topics.groups[prereq_id]
        if button_id.count("_") == 1:
            prereq_button_id = f"{prereq_id}_{group.subtopic}"
        elif button_id.count("_") == 2:
            prereq_button_id = f"{prereq_id}_{group.subtopic}_{group.concept}"
        buttons[prereq_button_id].button_style = "solid"
        buttons[prereq_button_id].button_type = "primary"
        triggered_buttons.append(prereq_button_id)
    for prererq_of_id in topics.groups[group_id].prerequisite_of_ids:
        group = topics.groups[prererq_of_id]
        if button_id.count("_") == 1:
            prererq_of_button_id = f"{prererq_of_id}_{group.subtopic}"
        elif button_id.count("_") == 2:
            prererq_of_button_id = f"{prererq_of_id}_{group.subtopic}_{group.concept}"
        buttons[prererq_of_button_id].button_style = "solid"
        buttons[prererq_of_button_id].button_type = "danger"
        triggered_buttons.append(prererq_of_button_id)


def make_button(
    id: str,
    name: str,
    icon: str = "",
    button_kwargs: dict | None = None,
):
    button_kwargs = button_kwargs or {
        "button_style": "outline",
        "button_type": "primary",
    }
    button = pn.widgets.Button(
        name=name, icon=icon, on_click=update_button_args, **button_kwargs
    )
    button.id = id  # type: ignore
    return button


def make_boxes(flex_mode):
    # print(f"\n\nflex_mode: {flex_mode}")
    gstack = pn.GridStack(sizing_mode="stretch_width", height=2000)
    topic_boxes = {}
    concepts_row = pn.Row()
    for group in topics.groups.values():
        topic_box = topic_boxes.get(
            group.topic,
            # pn.WidgetBox(f"## <span style='color:lightgreen'>{group.topic}</span>"),
            [],
            # pn.WidgetBox(),
        )
        topic_box_button_names = [button.name for button in topic_box]
        # subtopic_box = subtopic_boxes.get(group.subtopic, pn.WidgetBox())
        subtopic_button_id = f"{group.id}_{group.subtopic}"
        subtopic_button = make_button(
            id=subtopic_button_id,
            name=group.subtopic,
            icon="book",
            button_kwargs={"button_style": "outline", "button_type": "warning"},
        )
        buttons[subtopic_button_id] = subtopic_button
        if group.subtopic not in topic_box_button_names:
            if concepts_row:
                topic_box.append(concepts_row)
                concepts_row = pn.Row()
            if len(topic_box) == 1:
                topic_box.insert(0, subtopic_button)
            else:
                topic_box.append(subtopic_button)
        concept_button_id = f"{group.id}_{group.subtopic}_{group.concept}"
        concept_button = make_button(
            id=concept_button_id,
            name=group.concept,
            # icon="list-check",
        )
        if questions.get(group.id):
            concept_question_buttons_ncols = 2
            concept_question_buttons = [
                make_button(
                    id=f"{group.id}_{group.subtopic}_{group.concept}_{i}",
                    name=f"Q{i}",
                )
                for i in range(1, len(questions[group.id]) + 1)
            ]

            # concept_question_button_chunks = [
            #     concept_question_buttons[i : i + concept_question_buttons_ncols]
            #     for i in range(
            #         0, len(concept_question_buttons), concept_question_buttons_ncols
            #     )
            # ]
            # concept_question_buttons_stack = pn.GridStack(
            #     ncols=concept_question_buttons_ncols
            # )
            # for i, chunk in enumerate(concept_question_button_chunks):
            #     for j, button in enumerate(chunk):
            #         concept_question_buttons_stack[i, j] = button

            concepts_row.append(
                pn.Column(
                    concept_button,
                    # concept_question_buttons_stack,
                    *concept_question_buttons,
                    scroll=True,
                    min_height=50,
                    max_height=200,
                )
            )
        else:
            concepts_row.append(concept_button)
        buttons[concept_button_id] = concept_button
        # topic_box.append(concept_button)
        topic_boxes[group.topic] = topic_box
    if flex_mode:
        return pn.FlexBox(
            *[
                pn.WidgetBox(*topic_box, scroll=True)
                for topic_box in topic_boxes.values()
            ]
        )
    topic_boxes = list(topic_boxes.values())
    topic_box_chunks = [
        topic_boxes[i : i + NCOLS] for i in range(0, len(topic_boxes), NCOLS)
    ]
    for i, chunk in enumerate(topic_box_chunks):
        for j, topic_box in enumerate(chunk):
            gstack[i, j] = pn.WidgetBox(*topic_box, scroll=True)
    return gstack


# grid = make_boxes()
grid = pn.bind(make_boxes, flex_mode)
template_params = {
    "theme": "dark",
    "site": "VU",
    "title": "MATH 102",
    "main": [flex_mode_button, grid],
    "sidebar": pn.pane.Markdown(sidebar),
    "sidebar_width": 450,
    "collapsed_sidebar": True,
}
template = pn.template.MaterialTemplate(**template_params).servable()
