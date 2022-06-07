import json
import math
import os.path


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


def find_shortest_subtour(paths):
    """
    Given a list of paths, find the shortest sub-tour, if present
    :param paths: an array containing arrays of tuples representing edges in a graph
    :return: an array of edges representing the shortest sub-tour or None if not found
    """
    min_subtour = None

    for path in paths:
        # Paths with less than 3 edges cannot have sub tours
        if len(path) <= 2:
            return None

        # Copy to prevent array modification in caller of function
        path = path.copy()

        # The starting node of the current cycle
        start_node = None
        # The next node to explore
        next_node = None
        # A list of found cycles
        subtours = [[]]
        # Index of the cycle that we are currently exploring
        current_subtour = 0

        # Visit every edge in the path following the current cycle and remove it from the array
        while len(path) > 0:
            for edge in path:
                if start_node is None or next_node is None:
                    # Initialization of variables, the first cycle is the one that the first edge of the path is part of
                    start_node = edge[0]
                    next_node = edge[1]

                    path.remove(edge)
                    subtours[current_subtour].append(edge)
                if edge[0] == next_node:
                    # The next edge of the cycle has been found, proceed
                    next_node = edge[1]

                    subtours[current_subtour].append(edge)
                    path.remove(edge)

                    if next_node == start_node:
                        # The cycle has been explored, we are back to the first node
                        if len(subtours[current_subtour]) == 2:
                            # If the cycle found is of length 2 it is surely one of the smallest ones, we can return it
                            return subtours[current_subtour]

                        # Initialize a new cycle to explore
                        subtours.append([])
                        current_subtour += 1
                        start_node = None
                        next_node = None

        if len(subtours[current_subtour]) == 0:
            # Delete the last array if it is empty, to avoid problems
            del subtours[current_subtour]

        if len(subtours) > 1:
            # We have more than one cycle, let's find the smallest one
            for subtour in subtours:
                if min_subtour is None:
                    min_subtour = subtour
                elif 0 < len(subtour) < len(min_subtour):
                    min_subtour = subtour

    return min_subtour


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

    # Return a string containing nodes visited in order separated by spaces
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


def write_json_file(file_name, data):
    """
    Converts data to JSON and writes it to the file at the given path
    :param file_name: the name of the file to write
    :param data: any python object that can be converted to JSON
    """
    folder = "out/"
    if not os.path.exists("out/html/"):
        os.makedirs("out/html/")

    f = open(folder + file_name, "w")
    f.write(json.dumps(data))
    f.close()
