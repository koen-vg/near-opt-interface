# SPDX-FileCopyrightText: : 2024 Koen van Greevenbroek
#
# SPDX-License-Identifier: GPL-3.0-or-later


import random
import time

import numpy as np
import pandas as pd
from scipy.spatial import ConvexHull, Delaunay
from sklearn.neighbors import NearestNeighbors


def linearly_interpolate(x_dict, dims, metrics, X, y, nn_model, C):
    # Convert x_dict to numpy array
    x = np.array([x_dict[dim] for dim in dims]).reshape(1, -1)

    # Retrieve the indices of the N+1 nearest neighbors
    distances, indices = nn_model.kneighbors(x)

    # Retrieve the corresponding points and their values for the metrics
    neighbor_points = X[indices[0]]
    neighbor_values = y[indices[0]]

    # Also include the vertices of the convex hull; this is useful for
    # points close to the boundary. In particular, when the selected
    # point x is close to the boundary, there is a good chance that
    # all nearest neighbours are "on one side" of x, whereas there
    # could be no points at all between x and the boundary. In that
    # case, "interpolation" turns into "extrapolation". By including
    # the vertices of C, we ensure that x in actually contained within
    # the convex hull of the points selected for interpolation.
    hull_points = C.points[C.vertices]
    hull_values = y[C.vertices]

    # Combine the neighbor and hull points and values
    points = np.concatenate((neighbor_points, hull_points))
    values = np.concatenate((neighbor_values, hull_values))

    # We use Delaunay triangulation to determine the weights for
    # linear interpolation. With a Delaunay triangulation, we find a
    # simplex containing x, which can be used for interpolation via a
    # conversion to barycentric coordinates with respect to the
    # simplex.
    dl = Delaunay(points)
    simplex_index = dl.find_simplex(x)
    barycentric_coords = dl.transform[simplex_index[0], :-1].dot(
        x[0] - dl.transform[simplex_index[0], -1]
    )
    weights = np.append(barycentric_coords, 1 - barycentric_coords.sum())

    if not all(weights > 0):
        print("Warning: outside simplex: ", weights)
        return None

    simplex_values = values[dl.simplices[simplex_index]]

    # Interpolating each metric for the point x using the weights
    interpolated_metrics = np.dot(weights, simplex_values)

    # Return the interpolated values as a dictionary
    return dict(zip(metrics, interpolated_metrics[0]))


def min_max_rays(C: ConvexHull, x: np.array, buffer: float = 0.04):
    """Intersections of rays from x with the given convex hull.

    Returns the intersection points of all rays starting from x
    parallel to the axes with the given convex hull.

    """

    results = []
    for i in range(len(x)):
        ray = [0] * len(x)
        ray[i] = 1

        # Use matrix operations to get the intersection points of the ray with
        # each of the facets of C
        ray = np.array(ray)
        normals = C.equations[:, :-1]
        distances = -C.equations[:, -1]
        mask = np.dot(normals, ray) != 0
        t = (distances - np.dot(normals, x))[mask] / np.dot(normals, ray)[mask]

        xi = x + t.reshape(len(t), 1) * ray
        xi = xi[:, i]
        results.append(
            {
                "min": max(xi[xi < x[i]]) + buffer,
                "max": min(xi[xi > x[i]]) - buffer,
            }
        )

    return results


def min_metric(
    sample_points: pd.DataFrame,
    point_metrics: pd.DataFrame,
    metric: str,
    centre: pd.Series,
):
    # Get the point minimising the given metric
    i = point_metrics.idxmin()[metric]
    p = sample_points.iloc[i]

    # Shift the point slightly towards the centre of the near-opt
    # space to avoid numerical issues on the boundary.
    tolerance = 0.002
    p = (1 - tolerance) * p + tolerance * centre

    # Return as dictionary
    return p.to_dict()
