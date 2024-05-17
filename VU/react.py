import json

import panel as pn
from vu_models import Question, Topics

pn.extension("floatpanel", "gridstack")  # type: ignore

DAY = 16
NCOLS = 3

questions_file = f"math_102_created_questions_may_{DAY}.json"
questions = {
    id: Question(**q) for id, q in json.load(open(questions_file, "r")).items()
}
topics = Topics(**json.load(open(f"math_102_final_topics_may_{DAY}.json", "r")))

button_args = pn.rx({})


def update_button_args(event):
    args_dict = {}
    group_id = event.obj.id
    button_type = button_args.rx.value.get(group_id, {}).get(  # type: ignore
        "button_type", "primary"
    )
    if button_type != "success":
        args_dict[group_id] = {
            "button_style": "solid",
            "button_type": "success",
        }
        for prereq_id in topics.groups[group_id].prerequisite_ids:
            args_dict[prereq_id] = {
                "button_style": "solid",
                "button_type": "primary",
            }
        for prererq_of_id in topics.groups[group_id].prerequisite_of_ids:
            args_dict[prererq_of_id] = {
                "button_style": "solid",
                "button_type": "danger",
            }

    button_args.rx.value = args_dict


topic_names = list(topics.topics.keys())
topic_chunks = [topic_names[i : i + NCOLS] for i in range(0, len(topic_names), NCOLS)]


def make_boxes(button_args):
    boxes = {}
    for group in topics.groups.values():
        box = boxes.get(
            group.topic,
            pn.WidgetBox(f"## <span style='color:lightgreen'>{group.topic}</span>"),
        )
        if group.subtopic in [b.name for b in box]:
            continue
        kwargs = button_args.get(
            group.id, {"button_style": "outline", "button_type": "primary"}
        )
        # name = f"<span style='color:blue'>{group.subtopic}</span>"
        name = group.subtopic
        button = pn.widgets.Button(
            name=name, icon="book", **kwargs, on_click=update_button_args
        )
        button.id = group.id  # type: ignore
        box.append(button)
        boxes[group.topic] = box
    return pn.FlexBox(*boxes.values())


template = pn.template.MaterialTemplate(
    site="VU",
    title="MATH 102",
    main=[pn.bind(make_boxes, button_args)],
    theme="dark",
).servable()
