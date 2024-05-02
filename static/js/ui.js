// SPDX-FileCopyrightText: 2024 Koen van Greevenbroek
// SPDX-FileContributor: Aleksander Grochowicz
// SPDX-FileContributor: Maximilian Roithner
// SPDX-FileContributor: Oskar Vågerö
//
// SPDX-License-Identifier: GPL-3.0-or-later

var slider_mid_perc = 60;
var slider_mid_value = 30;

function slider_perc_from_value(value, slider_name) {
    // Given that each slider increases linearly from min to
    // `slider_min_value` in the first `slider_mid_perc`% of the
    // slider, and linearly to the max value after that, this function
    // returns the percentage of the way through the slider that the
    // given value is.
    var min = slider_ranges[slider_name]["min"];
    var max = slider_ranges[slider_name]["max"];

    if (slider_mid_value > max) {
        return (100 * (value - min)) / (max - min);
    }

    if (value <= slider_mid_value) {
        return ((value - min) / (slider_mid_value - min)) * slider_mid_perc;
    } else {
        return (
            slider_mid_perc +
            ((value - slider_mid_value) / (max - slider_mid_value)) *
                (100 - slider_mid_perc)
        );
    }
}

// Function to send an AJAX request to update the outputs
function onSliderChange() {
    // Collect the slider values
    var xhr = new XMLHttpRequest();
    var data = {};

    slider_names.forEach(function (slider_name) {
        data[slider_name] = parseFloat(
            document.getElementById(slider_name).noUiSlider.get(),
        );
    });

    xhr.open("POST", "/update", true);
    xhr.setRequestHeader("Content-Type", "application/json");
    xhr.onreadystatechange = function () {
        if (xhr.readyState === XMLHttpRequest.DONE && xhr.status === 200) {
            var responseData = JSON.parse(xhr.responseText);

            // Only update outputs when responseData.outputs is not None (from python)
            if (responseData.outputs === null) {
                // Log a warning
                console.warn("No metrics could be computed.");
            } else {
                // Update outputs dynamically based on 'output_names' passed from the server
                output_names.forEach(function (outputName) {
                    var value = responseData.outputs[outputName];
                    // Calculate normalised value
                    var value_norm = value / output_max_values[outputName];
                    value_norm = Math.min(value_norm, 1);
                    // Scale by scaling factor
                    value = value * output_scaling_factors[outputName];
                    // Round to 1 decimal place
                    value = Math.max(Math.round(value * 10) / 10, 0);

                    // If the outputName is slack, for format as "+<value>%"
                    if (outputName.includes("slack")) {
                        value = "+" + value + "%";
                    }

                    document.getElementById(outputName).innerText = value;

                    // Set bar height
                    document.getElementById(outputName + "_bar").style.height =
                        value_norm * 100 + "%";

                    // Update bar colour
                    var colorScale = chroma
                        .scale(["green", "yellow", "red"])
                        .mode("lch");
                    var color = colorScale(value_norm).hex();
                    document.getElementById(
                        outputName + "_bar",
                    ).style.backgroundColor = color;
                });
            }

            // Update the sliders' min and max if needed based on response
            slider_names.forEach(function (slider_name) {
                var slider = document.getElementById(slider_name);
                var min = slider_ranges[slider_name]["min"];
                var max = slider_ranges[slider_name]["max"];
                var soft_min = responseData.limits[slider_name]["min"];
                var soft_max = responseData.limits[slider_name]["max"];
                if (soft_min > soft_max) {
                    var avg = (soft_min + soft_max) / 2;
                    soft_min = avg;
                    soft_max = avg;
                }
                var left_pad = soft_min - min;
                var right_pad = max - soft_max;
                slider.noUiSlider.updateOptions({
                    padding: [left_pad, right_pad],
                });

                // Compute percentage of the way through the slider of soft_min and soft_max.
                var soft_min_percent = slider_perc_from_value(
                    soft_min,
                    slider_name,
                );
                var soft_max_percent = slider_perc_from_value(
                    soft_max,
                    slider_name,
                );

                // Update the color of the slider to reflect the soft_min and soft_max
                var feasible_colour = "#eeeeff";
                var infeasible_colour = "#ff6666";
                slider.querySelector(".noUi-base").style.background =
                    "linear-gradient(to right," +
                    infeasible_colour +
                    " " +
                    soft_min_percent +
                    "%, " +
                    feasible_colour +
                    " " +
                    soft_min_percent +
                    "%, " +
                    feasible_colour +
                    " " +
                    soft_max_percent +
                    "%, " +
                    infeasible_colour +
                    " " +
                    soft_max_percent +
                    "%)";
            });
        }
    };
    xhr.send(JSON.stringify(data));
}

function minMetric(event) {
    // Figure out from the event which button was pressed
    var button_id = event.target.id;
    var metric = button_id.replace("min_", "");

    // Make a request to the backend for the coordinates minimising a given metric
    var xhr = new XMLHttpRequest();
    var data = { metric: metric };

    xhr.open("POST", "/minmetric", true);
    xhr.setRequestHeader("Content-Type", "application/json");
    xhr.onreadystatechange = function () {
        if (xhr.readyState === XMLHttpRequest.DONE && xhr.status === 200) {
            var responseData = JSON.parse(xhr.responseText);
            var coords = responseData.coords;

            slider_names.forEach(function (slider_name) {
                var slider = document.getElementById(slider_name).noUiSlider;
                // Temporarily reset padding so it's possible to set the
                // slider to the default value
                slider.updateOptions({
                    padding: [0, 0],
                });
                slider.set(coords[slider_name]);
            });
            // This will set the outputs and paddings back to the correct values
            onSliderChange();
        }
    };
    xhr.send(JSON.stringify(data));
}

document.addEventListener("DOMContentLoaded", function () {
    slider_names.forEach(function (slider_name) {
        var sliderElement = document.getElementById(slider_name);
        var range = {
            min: slider_ranges[slider_name]["min"],
            [slider_mid_perc + "%"]: slider_mid_value,
            max: slider_ranges[slider_name]["max"],
        };
        noUiSlider.create(sliderElement, {
            start: slider_defaults[slider_name],
            range: range,
            padding: [0, 0],
            pips: {
                mode: "values",
                // For the values, generate a list of multiples of 5 between min and max, plus the rounded max value
                values: Array.from(
                    {
                        length:
                            (slider_ranges[slider_name]["max"] -
                                slider_ranges[slider_name]["min"]) /
                                10 +
                            1,
                    },
                    (_, i) => i * 10,
                ),
                density: -1,
            },
        });

        sliderElement.noUiSlider.on("update", function (values, handle) {
            var value = values[handle];
            var context_value = value * slider_context_scale[slider_name];

            // Round to one decimal place
            value = Math.max(Math.round(value * 10) / 10, 0);
            context_value = Math.max(Math.round(context_value * 10) / 10, 0);

            // Format to one decimal place
            context_value = context_value.toFixed(1);
            value = value.toFixed(1);

            var valueLabel = document.getElementById(
                slider_name + "_value_label",
            );
            if (valueLabel) {
                valueLabel.innerText = value;
            }

            var contextValueLabel = document.getElementById(
                slider_name + "_context_value_label",
            );
            if (contextValueLabel) {
                contextValueLabel.innerText = context_value;
            }
        });

        sliderElement.noUiSlider.on("change", function (values, handle) {
            onSliderChange();
        });

        // Mark the default value
        var perc_of_default_value = slider_perc_from_value(
            slider_opt_values[slider_name],
            slider_name,
        );

        // Create a new CSS rule for the pseudo-element
        var style = document.createElement("style");
        style.innerHTML = `
            #${slider_name} .noUi-base::before {
                content: "";
                position: absolute;
                height: 100%;
                border-left: 3px solid #000;
                left: ${perc_of_default_value}%;
            }
        `;

        // Add the rule to the slider element
        sliderElement.appendChild(style);

        // Set the text for the slider max value label; round to one decimal place
        var max_value_label = document.getElementById(
            slider_name + "_max_value_label",
        );
        var max_value = slider_ranges[slider_name]["max"];
        if (max_value_label) {
            max_value_label.innerText = Math.round(max_value * 10) / 10;
        }
    });

    // Call onSliderChange() to update the outputs on page load
    onSliderChange();

    document
        .getElementById("sliderForm")
        .addEventListener("submit", function (e) {
            e.preventDefault();

            var xhr = new XMLHttpRequest();
            var data = {};

            slider_names.forEach(function (slider_name) {
                data[slider_name] = parseFloat(
                    document.getElementById(slider_name).noUiSlider.get(),
                );
            });

            fetch("/save", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify(data),
            }).then((response) => {
                if (response.status === 200) {
                    window.location.href = "/finalquestions";
                } else {
                    alert("Error saving data");
                }
            });
        });
});

function resetSliders() {
    slider_names.forEach(function (slider_name) {
        var slider = document.getElementById(slider_name).noUiSlider;
        // Temporarily reset padding so it's possible to set the
        // slider to the default value
        slider.updateOptions({
            padding: [0, 0],
        });
        slider.set(slider_defaults[slider_name]);
    });
    // This will set the outputs and paddings back to the correct values
    onSliderChange();
}

document.getElementById("reset").addEventListener("click", resetSliders);

output_names.forEach(function (outputName) {
    document
        .getElementById("min_" + outputName)
        .addEventListener("click", minMetric);
});
