import math


def distance(x1, y1, x2, y2):
    """
    Calculates the distance between two points
    :param x1: x coordinate of first point
    :param y1: y coordinate of first point
    :param x2: x coordinate of second point
    :param y2: y coordinate of second point
    :return: the distance between the two points
    """
    return math.sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2)


def get_input_length(x_coords, y_coords, usable, direct_build_costs):
    """
    Get the length of the input, if arrays are of different size terminates the program
    :param x_coords: the array containing the x coordinates for each location
    :param y_coords: the array containing the y coordinates for each location
    :param usable: the array containing booleans that represent if a location is suitable for market construction
    :param direct_build_costs: the array containing costs to build a market in a location
    :return: the number of items in input
    """
    n = len(x_coords)
    if n != len(y_coords) or n != len(usable) or n != len(direct_build_costs):
        print(f"Malformed input: length do not match")
        exit(1)
    return n


def build_distance_matrix(n, x_coords, y_coords):
    """
    Builds a nxn matrix containing the distance between each point
    :param n: the number of items
    :param x_coords: the array containing the x coordinates for each location
    :param y_coords: the array containing the y coordinates for each location
    :return: a nxn matrix containing distances between every location and the maximum distance between any two locations
    """
    dist = {}
    max_dist = 0
    for i in range(n):
        for j in range(n):
            new_dist = distance(x_coords[i], y_coords[i], x_coords[j], y_coords[j])

            if new_dist == 0 and i != j:
                print(f"WARNING: dist[{i}, {j}] is 0")

            dist[i, j] = new_dist

            if new_dist > max_dist:
                max_dist = new_dist

    return dist, max_dist


def pretty_print_path(edges):
    """
    Get a space-separated list of nodes that represent a path
    :param edges: a list of tuples representing the edges that form the path
    :return: a string representing the path
    """
    edges = edges.copy()

    nodes = []
    next_node = 0
    # Starting from node 0 follow the path until reaching node 0 again
    while len(edges) > 0:
        found = False

        for edge in edges:
            if edge[0] == next_node:
                nodes.append(edge[0])
                next_node = edge[1]
                edges.remove(edge)
                found = True
                continue

        if not found:
            raise Exception(f"Node {next_node} not found")

    nodes.append(0)
    return " ".join([str(el) for el in nodes])


def calculate_path_total_length(edges, dist):
    """
    Calculate the total length of the given path
    :param edges: a list of tuples representing the edges that form the path
    :param dist: a matrix containing the distances between the vertices references in the tuples
    :return: the total length of the given path
    """
    tot_dist = 0
    for (i, j) in edges:
        tot_dist += dist[i, j]
    return tot_dist
