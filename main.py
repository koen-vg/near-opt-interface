# SPDX-FileCopyrightText: 2024 Koen van Greevenbroek
# SPDX-FileContributor: Aleksander Grochowicz
# SPDX-FileContributor: Maximilian Roithner
# SPDX-FileContributor: Oskar Vågerö
#
# SPDX-License-Identifier: GPL-3.0-or-later

from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from flask import Flask, jsonify, redirect, render_template, request, session
from scipy.spatial import ConvexHull
from sklearn.neighbors import NearestNeighbors

from geometry import linearly_interpolate, min_max_rays, min_metric

app = Flask(__name__)
app.secret_key = "secret"

# Load sample points
sample_points = pd.read_csv("data/samples.csv", index_col=0) / 1e6
point_metrics = pd.read_csv("data/metrics.csv", index_col=0)

# Clip metrics to positive
point_metrics = point_metrics.clip(lower=0)

slider_names = ["wind", "solar", "green-imports", "heat-storage", "h2"]

assert set(slider_names) == set(sample_points.columns.tolist())

sample_points = sample_points[slider_names]

slider_ranges = {
    name: {"min": 0, "max": sample_points[name].max()} for name in slider_names
}

# Hard-coded from optimum for now
SLIDER_DEFAULTS = {
    "wind": 15,
    "solar": 15,
    "h2": 15,
    "green-imports": 15,
    "heat-storage": 2.35,
}

SLIDER_OPT_VALUES = {
    "wind": 19.3,
    "solar": 0.0,
    "h2": 0.0,
    "green-imports": 27.0,
    "heat-storage": 1.4,
}

slider_names_pretty = {
    "wind": "Wind power",
    "solar": "Solar power",
    "h2": "Hydrogen storage",
    "green-imports": "Green fuel imports",
    "heat-storage": "Heat infrastructure",
}

slider_info = {
    "wind": "Investment in onshore wind turbines",
    "solar": "Investment in solar panels",
    "h2": "Investment in hydrogen tanks, electrolysers and fuel cells",
    "green-imports": "Imports of green ammonia and bioenergy (biogas or pellets)",
    "heat-storage": "Investment in geothermal storage or pit heat storage",
}

slider_context_text = {
    "wind": "Approx. number of 90m wind turbines",
}

slider_context_scale = {
    "wind": (1 / 1.151) / 4.2,  # 1 turbine = 4.2 MW, capital cost 1.151 MNOK/MW
}


# Custom order of output names:
output_names = [
    "slack",
    "electricity_price",
    "heat_price",
    "emissions",
    "vulnerability",
    "visual_impact",
    "land_use",
]

# Assert that they are equal to columns of point_metrics as set
assert set(output_names) == set(point_metrics.columns)

point_metrics = point_metrics[output_names]

output_names_pretty = {
    "slack": "Total cost",
    "electricity_price": "Elec. price",
    "heat_price": "Heat price",
    "emissions": "CO2 emissions",
    "vulnerability": "Vulnerability",
    "visual_impact": "Visual impact",
    "land_use": "Land use",
}

output_info = {
    "slack": "Additional cost compared to the cost-minimal system",
    "electricity_price": "Electricity price",
    "heat_price": "Heat price",
    "emissions": "CO2 emissions (comparison: diesel-powered system 14 tCO2/capita, coal-powered system 28 tCO2/capita)",
    "vulnerability": "Vulnerability to weather variability, import dependency, system complexity, heat storage",
    "visual_impact": "Visual impact of wind turbines",
    "land_use": "Land use (direct through infrastructure and indirect through imported fuels)",
}

output_scaling_factors = {
    "slack": 100,  # To percent
    "electricity_price": 0.1,  # To øre/kWh
    "heat_price": 0.1,  # To øre/kWh
    "emissions": 1 / 2417,  # tCO2 per capita
    "vulnerability": 1,
    "visual_impact": 1,
    "land_use": 1 / 1e6,  # Square kilometers
}

output_units = {
    "slack": "more expensive",
    "electricity_price": "øre/kWh",
    "heat_price": "øre/kWh",
    "emissions": "tCO2 per person",
    "land_use": "km²",
}

output_max_values = point_metrics.max().to_dict()

# As an exception, so the max value of both electricity and heat price
# to their common maximum
max_elec_heat_price = min(
    max(output_max_values["electricity_price"], output_max_values["heat_price"]), 3000
)
output_max_values["electricity_price"] = max_elec_heat_price
output_max_values["heat_price"] = max_elec_heat_price


# Compute nearest neighbor data structure
X = sample_points.to_numpy()
y = point_metrics.to_numpy()

nn_model = NearestNeighbors(n_neighbors=10 * len(slider_names) + 1)
nn_model.fit(X)

# Also compute the convex hull of all sample points
C = ConvexHull(X)

# Approximate centre as average of convex hull vertices.
centre = C.points[C.vertices].sum(axis=0) / len(C.vertices)


# Function to compute outputs from slider values
def compute_outputs(slider_values):
    # Interpolate the metrics for the given slider values
    interpolated_metrics = linearly_interpolate(
        slider_values, slider_names, output_names, X, y, nn_model, C
    )

    return interpolated_metrics


# Function to compute new slider limits
def compute_new_limits(slider_values):
    # Convert the slider values to a point in the same space as C
    x = np.array([slider_values[c] for c in sample_points.columns])

    # Now compute min and max ranges geometrically
    return dict(zip(sample_points.columns, min_max_rays(C, x)))


# Helper function to get timestamped filename
def get_timestamped_filename():
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    return f"outputs_{timestamp}.csv"


# Redirect the index page to intro.html
@app.route("/")
def intro():
    session["intro_visited"] = True  # Set session flag to indicate intro page visit
    return render_template("intro.html")


@app.route("/questionnaire")
def questionnaire():
    if "intro_visited" not in session or not session["intro_visited"]:
        return redirect("/")  # Redirect to intro page if the user has not visited it
    return render_template("questionnaire.html")


@app.route("/main", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        session["age"] = request.form["age"]
        session["gender"] = request.form["gender"]
        session["education"] = request.form["education"]

    return render_template(
        "main.html",
        values=SLIDER_DEFAULTS,
        outputs=compute_outputs(SLIDER_DEFAULTS),
        slider_names=slider_names,
        slider_names_pretty=slider_names_pretty,
        slider_info=slider_info,
        slider_context_text=slider_context_text,
        slider_context_scale=slider_context_scale,
        slider_ranges=slider_ranges,
        slider_defaults=SLIDER_DEFAULTS,
        slider_opt_values=SLIDER_OPT_VALUES,
        output_names=output_names,
        output_names_pretty=output_names_pretty,
        output_info=output_info,
        output_max_values=output_max_values,
        output_scaling_factors=output_scaling_factors,
        output_units=output_units,
    )


@app.route("/update", methods=["POST"])
def update():
    values = request.get_json()
    outputs = compute_outputs(values)
    limits = compute_new_limits(values)
    return jsonify(outputs=outputs, limits=limits)


@app.route("/minmetric", methods=["POST"])
def minmetric():
    metric = request.get_json()["metric"]
    coords = min_metric(sample_points, point_metrics, metric, centre)
    return jsonify(coords=coords)


@app.route("/save", methods=["POST"])
def save():
    values = request.get_json()
    outputs = compute_outputs(values)

    # Retrieve session metadata
    metadata = {
        "age": session.get("age", ""),
        "gender": session.get("gender", ""),
        "education": session.get("education", ""),
    }

    data_to_save = {
        **metadata,
        **values,
        **outputs,
    }

    filename = get_timestamped_filename()
    df = pd.DataFrame([data_to_save])
    output_directory = "outputs"
    Path(output_directory).mkdir(parents=True, exist_ok=True)
    df.to_csv((Path(output_directory) / filename), index=False)

    session.clear()
    session["previous_file"] = filename

    # Return success
    return jsonify(success=True)


@app.route("/finalquestions", methods=["GET", "POST"])
def finalquestions():
    if request.method == "POST":
        previous_data_file = session.get("previous_file", "")

        feedback_data = {}
        if previous_data_file:
            df = pd.read_csv((Path("outputs") / previous_data_file))
            feedback_data = df.to_dict(orient="records")[0]

        # Get the additional questionnaire data
        questionnaire_data = {
            "additional_cost_prioritized": request.form.get("slack", "no"),
            "electricity_price_prioritized": request.form.get("elec", "no"),
            "heat_price_prioritized": request.form.get("heat", "no"),
            "emissions_prioritized": request.form.get("emissions", "no"),
            "vulnerability_prioritized": request.form.get("vulnerability", "no"),
            "visual_impact_prioritized": request.form.get("visual", "no"),
            "land_use_prioritized": request.form.get("landuse", "no"),
            "willingness_to_pay": request.form.get("willingness_to_pay", ""),
        }

        # Combine previous submission data and questionnaire data
        data_to_save = {**feedback_data, **questionnaire_data}

        # Set output directory and filename
        output_directory = "outputs"
        filename = previous_data_file  # This filename contains the timestamp

        # Save combined data to the same CSV file
        df_to_save = pd.DataFrame([data_to_save])
        df_to_save.to_csv((Path(output_directory) / filename), index=False)

        # Optionally, clear the session variable if necessary
        if "previous_file" in session:
            del session["previous_file"]

        # Return success
        return redirect("/feedback")
    else:
        # If the method is GET, just display the form
        return render_template("finalquestions.html")


@app.route("/feedback", methods=["GET", "POST"])
def feedback():
    return render_template("feedback.html")


@app.route("/final_page", methods=["POST"])
def final_page():
    previous_data_file = session.get("previous_file", "")
    feedback_data = {}
    if previous_data_file:
        df = pd.read_csv((Path("outputs") / previous_data_file))
        feedback_data = df.to_dict(orient="records")[0]

    # Retrieve session metadata
    metadata = {"feedback": request.form["text"]}

    data_to_save = {**feedback_data, **metadata}

    filename = "fb" + get_timestamped_filename()
    df = pd.DataFrame([data_to_save])
    output_directory = "outputs"
    Path(output_directory).mkdir(parents=True, exist_ok=True)
    df.to_csv((Path(output_directory) / filename), index=False)
    return render_template("final_page.html")


if __name__ == "__main__":
    app.run(debug=True)
