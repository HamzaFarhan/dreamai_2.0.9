import panel as pn
pn.extension()

parents = {"Farhan"}
# Declare state of application
is_stopped = pn.rx(True)

rx_name = is_stopped.rx.where("Start the wind turbine", "Stop the wind turbine")

submit = pn.widgets.Button(name=rx_name)

def toggle_wind_turbine(clicked):
    is_stopped.rx.value = not is_stopped.rx.value  # type: ignore


submit.rx.watch(toggle_wind_turbine)

pn.Column(submit).servable()
