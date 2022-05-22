# Authors:
# Viola Renne
# Leonardo Panseri

import math
import mip
import json

# Import data, change the name of the file to change dataset
# from minimart_data import Cx, Cy, usable, Dc, r
from data.robomarkt_0 import Cx, Cy, usable, Dc, maxdist, mindist


# #################
# Utility functions
# #################

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


def get_input_length():
    """
    Get the length of the input, if arrays are of different size terminates the program
    :return: the number of items in input
    """
    n = len(Cx)
    if n != len(Cy) or n != len(usable) or n != len(Dc):
        print(f"Malformed input: length do not match")
        exit(1)
    return n


def build_distance_matrix(n):
    """
    Builds a nxn matrix containing the distance between each point
    :param n: the number of items
    :return:
    """
    return [[distance(Cx[i], Cy[i], Cx[j], Cy[j]) for j in range(n)] for i in range(n)]


# ###################################
# Model construction and optimization
# ###################################

def build_model_and_optimize(n, dist):
    """
    Constructs the linear model for the mini market construction problem and finds the optimal solution
    :param n: the size of the input
    :param dist: a matrix containing distances between all points
    :return: the objective value and optimal values for all variables and optimization status
    """
    # Initialize model and disable verbose logging
    m = mip.Model()
    m.verbose = 0

    # #########
    # Variables
    # #########

    # x_i: 1 if a market will be opened on the land of house i, 0 otherwise
    x = [m.add_var(var_type=mip.BINARY) for i in range(n)]

    # y_ij: 1 if market opened on the land of house j is the closest to house i, 0 otherwise
    y = [[m.add_var(var_type=mip.BINARY) for j in range(n)] for i in range(n)]

    # ###########
    # Constraints
    # ###########

    # Ensures that the main location of the company is always selected
    m.add_constr(x[0] == 1)

    # Ensures that a market can be placed only on land of homeowners that have given their permission
    for i in range(n):
        m.add_constr(x[i] <= usable[i])

    # Ensures that y_ij can be 1 only if j is the market closest to house i
    z = 1000000000000
    for i in range(n):
        for j in range(n):
            for t in range(n):
                m.add_constr(y[i][j] * dist[i][j] <= dist[i][t] + z * (1 - x[t]))

    # Ensures that the closest market to house i is at a distance smaller than maxdist
    for i in range(n):
        for j in range(n):
            if dist[i][j] != 0:
                m.add_constr(y[i][j] * dist[i][j] <= maxdist)

    # Ensures that y_ij can be 1 only if a market is placed on land of house j
    for i in range(n):
        for j in range(n):
            m.add_constr(y[i][j] <= x[j])

    # Ensures that every house i is served by at least one market j
    for i in range(n):
        m.add_constr(mip.xsum(y[i][j] for j in range(n)) == 1 - 1 * x[i])

    # Ensures that the distance between every two markets is grater than mindist
    for i in range(n):
        for j in range(n):
            if i != j:
                m.add_constr(distance(Cx[i], Cx[j], Cy[i], Cy[j]) >= mindist - z * (2 - x[i] - x[j]))

    # ##################
    # Objective function
    # ##################

    # Minimizes the cost of installation of the markets
    m.objective = mip.minimize(mip.xsum(Dc[i] * x[i] for i in range(n)))

    # Perform optimization of the model
    status = m.optimize()

    return m.objective_value, x, y, status


def print_optimal_solution(save=False):
    """
    Prints the optimal solution
    :param save: if True writes the results to a json file
    """
    n = get_input_length()
    dist = build_distance_matrix(n)

    obj_value, x, y, status = build_model_and_optimize(n, dist)

    if status != mip.OptimizationStatus.OPTIMAL:
        print(f"Problem has no optimal solution: {status}")
        exit()

    # Calculate the number of markets that are open
    num_of_markets = 0
    for i in range(n):
        num_of_markets += x[i].x

    print(f"RESULT: {obj_value} {num_of_markets}")

    installed_markets = ""
    for i in range(n):
        if x[i].x == 1:
            installed_markets += f"{i} "
    installed_markets = installed_markets.strip()
    print(installed_markets)

    if save:
        coords = {i: (Cx[i], Cy[i]) for i in range(n)}
        x_values = [x[i].x for i in range(n)]
        y_values = [[y[i][j].x for j in range(n)] for i in range(n)]
        result = {"n": n, "maxdist": maxdist, "mindist": mindist, "coords": coords, "usable": usable, "cost": Dc, "dist": dist, "obj_value": obj_value,
                  "x": x_values, "y": y_values,
                  "built": num_of_markets}

        f = open("result.json", "w")
        f.write(json.dumps(result))
        f.close()


# ##############################
# Input and output visualization
# ##############################

def build_base_graph(n, radius):
    """
    Constructs a base PyVis network graph with fixed positioning and a legend
    :param n: the number of nodes
    :param radius: the maximum radius for the problem
    :return: a PyVis Network
    """
    from pyvis.network import Network
    import networkx as nx

    net = Network('100%', '100%')

    # Turn off edges inheriting color from nodes
    net.options.edges.inherit_colors(False)

    # Set fixed positioning only
    net.toggle_physics(False)
    net.toggle_drag_nodes(False)
    net.toggle_stabilization(False)

    # Add legend
    g = nx.Graph()

    labels = [f"Max distance: {radius}", "Nodes legend (hover)", "Edges legend (hover)"]
    titles = ["",
              "<b>Nodes<b><br/><span style='color: green'>&bull;</span> : selected in optimal solution"
              "<br/><span style='color: black'>&bull;</span> : not selected but usable"
              "<br/><span style='color: red'>&bull;</span> : not usable",
              "<b>Edges<b><br/><span style='color: green'>&horbar;</span> : selected in optimal solution"
              "<br/><span style='color: black'>&horbar;</span> : not selected but in range"
              "<br/><span style='color: red'>&horbar;</span> : not in range"]

    step = 150
    x = -300
    y = -110
    legend_nodes = [
        (
            n + i,
            {
                'label': labels[i],
                'size': 40,
                'x': x,
                'y': f'{y + i * step}px',
                'shape': 'box',
                'widthConstraint': 150,
                'font': {'size': 30},
                'title': titles[i]
            }
        )
        for i in range(3)
    ]
    g.add_nodes_from(legend_nodes)
    net.from_nx(g)

    return net


def visualize_solution(scale=20, show_all_edges=False):
    """
    Constructs a network graph to visualize the solution and shows it
    :param scale: multiplicative factor for coordinates to show nodes more distanced (default: 20)
    :param show_all_edges: if set to False (default) only edges that connect nodes in range and that have as destination a node that is selected in the optimal solution are shown
    """
    # Load data from file
    f = open("result.json")
    data = json.loads(f.read())

    n = data["n"]
    rn = data["maxdist"]
    coords = {int(k): v for k, v in data["coords"].items()}
    usbl = data["usable"]
    cost = data["cost"]
    dist = data["dist"]
    x = data["x"]
    y = data["y"]

    net = build_base_graph(n, rn)

    for i in range(n):
        # Check if all selected nodes are usable
        if x[i] == 1 and not usbl[i]:
            print(f"ERROR: node N{i} is selected in the optimal solution, but not usable")

        # Add all n nodes to the graph with the colour: green if selected in the optimal solution,
        # black if not selected but usable, red if not usable
        color = "green" if x[i] == 1 else "red" if not usbl[i] else "black"
        net.add_node(i, x=coords[i][0] * scale, y=-coords[i][1] * scale, size=4, label=f"N{i}", color=color,
                     title=f"Usable: {usbl[i]}<br/>Cost: {cost[i]}")

    for i in range(n):
        for j in range(n):
            if i != j:  # Do not show self-loops
                if show_all_edges or x[j] == 1:  # Show only edges to nodes that have been selected
                    if show_all_edges or dist[i][j] <= rn:  # Show only edges in range
                        # Add all edges to the graph with colour: green if selected om the optimal solution,
                        # black if not selected but in range, red if not in range
                        color = "green" if y[i][j] == 1 else "black" if dist[i][j] <= rn else "red"
                        net.add_edge(i, j, label=str(round(dist[i][j], 1)), color=color)
                    elif dist[i][j] > rn and y[i][j] == 1:  # Check if all selected edges have distance less or equal than max radius
                        print(f"ERROR: arc ({i},{j}) is selected but their distance is greater than max radius")
                elif x[j] == 0 and y[i][j] == 1:  # Check if all selected edges go to nodes that are selected
                    print(f"ERROR: arc ({i},{j}) is selected but N{j} is not selected")
            elif y[i][j] == 1:  # Check if all self-loops are not selected
                print(f"ERROR: arc ({i},{j}) is selected but it is a self loop")

    net.show("result_visualization.html")


def visualize_input(scale=20, show_all_edges=False):
    """
    Constructs a network graph to visualize the input data and shows it
    :param scale: multiplicative factor for coordinates to show nodes more distanced (default: 20)
    :param show_all_edges: if set to False (default) only edges that connect nodes in range are shown
    """
    # Retrieve info about the input data
    n = get_input_length()
    dist = build_distance_matrix(n)

    net = build_base_graph(n, maxdist)

    for i in range(n):
        # Add all n nodes to the graph with colour: black if usable, red if not
        color = "black" if usable[i] else "red"
        net.add_node(i, x=Cx[i] * scale, y=-Cy[i] * scale, size=4, label=f"N{i}", color=color,
                     title=f"Usable: {usable[i]}<br/>Cost: {Dc[i]}")

    for i in range(n):
        for j in range(n):
            if i != j:  # Do not show self-loops
                if dist[i][j] <= maxdist:  # If node i is in range of node j
                    # Add all edges that connect nodes in range of each other colored black
                    net.add_edge(i, j, color="black", label=round(dist[i][j], 1))
                elif show_all_edges:
                    # Add all edges that connect nodes not in range of each other colored red
                    net.add_edge(i, j, color="red", label=round(dist[i][j], 1))

    net.show("input_visualization.html")


# ###########
# Entry point
# ###########

if __name__ == '__main__':
    # If module is executed as a script check command line arguments
    from sys import argv

    if len(argv) >= 2:
        if argv[1] == "save":  # Find optimal solution, save it to file and visualize it
            print_optimal_solution(save=True)
            visualize_solution()
            exit()
        elif argv[1] == "visualize":  # Visualize solution previously saved to file
            visualize_solution()
            exit()
        elif argv[1] == "visualizeinput":  # Visualize input data
            visualize_input()
            exit()

# In any case (import of the module or execution as a script) optimize the model and print the result
print_optimal_solution()
