<!--
SPDX-FileCopyrightText: 2024 Koen van Greevenbroek

SPDX-License-Identifier: CC-BY-4.0
-->

# Interface for exploring near-optimal energy system designs

This repository contains the source code for a simple web interface used to explore near-optimal energy system designs. The interface was first used during a [study](https://arxiv.org/abs/2501.05280) exploring Longyearbyen's residents' preferences and priorities regarding the local energy system:

Vågerö et al (2025). Exploring near-optimal energy systems with stakeholders: a novel approach for participatory modelling. [arXiv:2501.05280](https://arxiv.org/abs/2501.05280).

The interface presented here contains the same basic elements as the one used in the Longyearbyen study, but is stripped of explanatory information pertaining to Longyearbyen specifically, and presented only in English. However, we have included the same data on near-optimal designs used in Longyearbyen, so that it is possible to try out the interface in a meaningful way.

The data used in [arXiv:2501.05280](https://arxiv.org/abs/2501.05280) are as follows:
- We used Svalbard Energi's PyPSA-LYB model, developed by Haakon Duus and Jonas Blomberg Ghini at Multiconsult. (Link to repo coming soon.)
- We adapted and further developed the workflow developed in [Grochowicz et al., 2023. Intersecting near-optimal spaces: European power systems with more resilience to weather variability](https://doi.org/10.1016/j.eneco.2022.106496) and [van Greevenbroek et al., 2023](https://arxiv.org/abs/2312.11264) to approximate the near-optimal feasible spaces. (Link to repo based on [aleks-g/intersecting-near-opt-spaces](https://github.com/aleks-g/intersecting-near-opt-spaces/tree/main) and [koen-vg/enabling-agency](https://github.com/koen-vg/enabling-agency) coming soon.)
- We used the interface as presented in this repository, and added a questionnaire regarding demographics before the participants interacted with the interface, as well as a post-study questionnaire surveying the priorities of the participants. (Coming soon in the supplementary material.)


# Main elements of the interface

On the main page (when running locally, navigate to `http://localhost:5000/main`) consists of two main elements.
1. On the left, interactive sliders enabling the selection of near-optimal energy system designs.
2. On the right, the visualisation of 7 different metrics showing at any time the characteristics of the solution selected by the sliders.

In the case of the data included with the interface (as well as labels, descriptions, etc., specified in `main.py`), values are specific to Longyearbyen and units are in NOK/øre. Labels and units would have to be adapted to your particular needs when adapting this interface to other energy systems of interest.


# Data requirements

This interface is designed to allow the exploration of near-optimal energy system solutions while displaying a collection of metrics/indicators for each potential solution.

In order for this to work, the interface needs input data both on the extent of the near-optimal space as well as on the metrics. These are expected to be supplied in `data/samples.csv` and `data/metrics.csv`, respectively.

The two files must have the exact same index (i.e., first column); row `i` in `samples.csv` always corresponds to row `i` in `metrics.csv`. Both files describe the same set of points (assumed to be points in the near-optimal space of some energy system model), with `samples.csv` giving the coordinates of the points, and `metrics.csv` giving the values of a set of metrics for each point.

Near-optimal spaces are a-priori high-dimensional, and are usually projected down to a smaller number of dimensions for specific applications. Here, that smaller number of dimensions is taken to the be columns of `samples.csv`; also the elements of the `slider_names` list in `main.py`. Thus, each column of `samples.csv` represents coordinates in the respective dimension.

No assumptions are made on the metric values. Useful metrics may not necessarily depend only coordinates in the near-optimal space (e.g. the minimum state-of-charge of energy storage might be an interesting metric but can't necessarily be determined just from total install wind and solar capacity). This is the rationale for supplying pre-computed metrics to the interface: this allows metrics to be computed directly after solving the model instance associated to each point, while only providing final coordinates and metric values to the interface. It is important for performance reasons that the interface is supplied with only the minimal amount of information required, since the number of samples should ideally be large, and complete model-instances usually take significant disk-space and a significant amount of time to process.


# How to generate your own input data

If you want to use this interface to explore near-optimal solutions to your own energy system model, you will have to solve your model many times with different objectives and total system cost constraints. For an example methodology (though a bit more involved than what's strictly needed for the purposes of this interface), see [this](https://github.com/aleks-g/intersecting-near-opt-spaces) repository, and specifically the output of the `compute_near_opt` rule. The mentioned repository doesn't compute any metrics, only coordinates (i.e. for `samples.csv`).


# Interpolation

More data-points (coordinates and metrics) will results in more accurate results in the interface; the example dataset provided in this repository contains some 56000 points.

Even then, the interface allows for continuous changes in coordinates (slider values), meaning that most combinations of coordinates selected in the interface are not going to correspond exactly to a point in the dataset. Usually it's not even particularly close; the number of points needed to densely pack, say, a unit cube in d-dimensional space grows exponentially with d (the "curse of dimensionality").

That's all to say that some work is required from the interface to display sensible metric values when a point is selected that's not very close to one given in the input data.

The solution is to use some linear interpolation. When a slider value changes, the interface will find a small number of nearest neighbours in the input dataset to the point selected by the sliders. Then, metric values are computed for the selected point by linearly interpolating the metric values of the nearest points in the input dataset (see `linearly_interpolate` in `geometry.py`).


# Set-up

1. Install the conda environment from the `environment.yaml` file:

    ```bash
    mamba env create -f envs/environment.yaml
    ```
2. Activate the environment:

    ```bash
    conda activate near-opt-interface
    ```
3. Run the main python script to start the interface:

    ```bash
    python main.py
    ```
4. Open the interface in your browser at `http://localhost:5000/`


# Licenses

All originally produced code is distributed under the GPL v3.0 license. Data, documentation, and graphics are distributed under the CC-BY-4.0 license.

Two included Javascript libraries (noUiSlider and chroma.js) are redistributed with permission according to their respective licenses (see `static/lib`).
