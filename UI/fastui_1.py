from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastui import AnyComponent, FastUI, prebuilt_html
from fastui import components as c
from fastui import events as e
from fastui.forms import fastui_form
from pydantic import BaseModel, Field
from typing_extensions import Annotated

app = FastAPI()


class BMIForm(BaseModel):
    weight: float = Field(56, title="Weight (kg)")
    height: float = Field(178, title="Height (cm)")

    def calculate_bmi(self) -> float:
        return (self.weight / (self.height**2)) * 10_000


@app.get("/api/", response_model=FastUI, response_model_exclude_none=True)
def page() -> list[AnyComponent]:
    return [
        c.PageTitle(text="BMI Calculator"),
        c.Page(
            components=[c.ServerLoad(path="/form")],
        ),
    ]


def bmi_results(bmi: float) -> list[AnyComponent]:
    return [
        c.Heading(text="BMI Result", level=2),
        c.Paragraph(text=f"Your BMI is {bmi:.2f}"),
        c.Button(text="Calculate Again", on_click=e.GoToEvent(url="/api/form")),
    ]


def input_form() -> list[AnyComponent]:
    return [
        c.Heading(text="BMI Calculator", level=2),
        c.Paragraph(text="Enter your weight and height to calculate your BMI."),
        c.ModelForm(model=BMIForm, submit_url="/api/calculate"),
    ]


@app.get("/api/form", response_model=FastUI, response_model_exclude_none=True)
def form(bmi: float | None = None) -> list[AnyComponent]:
    return bmi_results(bmi=bmi) if bmi else input_form()


@app.post("/api/calculate", response_model=FastUI, response_model_exclude_none=True)
def calculate(
    bmi_form: Annotated[BMIForm, fastui_form(BMIForm)],
) -> list[AnyComponent]:
    return form(bmi=bmi_form.calculate_bmi())


@app.get("/{path:path}")
def root() -> HTMLResponse:
    """Simple HTML page which serves the React app, comes last as it matches all paths."""
    return HTMLResponse(prebuilt_html(title="BMI Calculator"))
