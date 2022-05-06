import math
import mip
import json

# Import data, change the name of the file to change dataset
# from minimart_data import Cx, Cy, usable, Dc, r
from data.minimart_data0 import Cx, Cy, usable, Dc, r


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


def build_model_and_optimize(n, dist):
    """
    Constructs the linear model for the mini market construction problem and finds the optimal solution
    :param n: the size of the input
    :param dist: a matrix containing distances between all points
    :return: the objective value and optimal values for all variables
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

    # Ensures that a market can be placed only on land of homeowners that have given their permission
    for i in range(n):
        m.add_constr(x[i] <= usable[i])

    # Ensures that y_ij can be 1 only if j is the market closest to house i
    z = 1000000000000
    for i in range(n):
        for j in range(n):
            for t in range(n):
                m.add_constr(y[i][j] * dist[i][j] <= dist[i][t] + z * (1 - x[t]))

    # Ensures that the closest market to house i is at a distance smaller than r
    for i in range(n):
        for j in range(n):
            if dist[i][j] != 0:
                m.add_constr(y[i][j] * dist[i][j] <= r)

    # Ensures that y_ij can be 1 only if a market is placed on land of house j
    for i in range(n):
        for j in range(n):
            m.add_constr(y[i][j] <= x[j])

    # Ensures that every house i is served by at least one market j
    for i in range(n):
        m.add_constr(mip.xsum(y[i][j] for j in range(n)) == 1)

    # ##################
    # Objective function
    # ##################

    # Minimizes the cost of installation of the markets
    m.objective = mip.minimize(mip.xsum(Dc[i] * x[i] for i in range(n)))

    # Perform optimization of the model
    m.optimize()

    return m.objective_value, x, y


def print_optimal_solution(save=False):
    """
    Prints the optimal solution
    :param save: if True writes the results to a json file
    """
    n = get_input_length()
    dist = build_distance_matrix(n)

    obj_value, x, y = build_model_and_optimize(n, dist)

    # Calculate the number of markets that are open
    num_of_markets = 0
    for i in range(n):
        num_of_markets += x[i].x

    print(f"RESULT: {obj_value} {num_of_markets}")

    if save:
        coords = {i: (Cx[i], Cy[i]) for i in range(n)}
        x_values = [x[i].x for i in range(n)]
        y_values = [[y[i][j].x for j in range(n)] for i in range(n)]
        result = {"n": n, "r": r, "coords": coords, "dist": dist, "obj_value": obj_value, "x": x_values, "y": y_values,
                  "built": num_of_markets}

        f = open("result.json", "w")
        f.write(json.dumps(result))
        f.close()


def visualize_solution():
    """
    Constructs a network graph to visualize the solution and shows it
    """
    from pyvis.network import Network

    f = open("result.json")
    data = json.loads(f.read())

    n = data["n"]
    rn = data["r"]
    coords = {int(k): v for k, v in data["coords"].items()}
    dist = data["dist"]
    x = data["x"]
    y = data["y"]

    net = Network('100%', '100%')

    scale = 20
    for i in range(n):
        color = "red" if x[i] == 1 else "black"
        net.add_node(i, x=coords[i][0]*scale, y=-coords[i][1]*scale, label=f"N{i}", color=color)

    for i in range(n):
        for j in range(n):
            if x[j] == 1 and dist[i][j] <= rn:
                color = "red" if y[i][j] == 1 else "black"
                net.add_edge(i, j, label=round(dist[i][j], 1), color=color)

    net.toggle_physics(False)
    net.toggle_drag_nodes(False)
    net.toggle_stabilization(False)
    net.show("result_visualization.html")


if __name__ == '__main__':
    from sys import argv

    if len(argv) >= 2:
        if argv[1] == "save":
            print_optimal_solution(save=True)
            visualize_solution()
            exit()
        elif argv[1] == "visualize":
            visualize_solution()
            exit()

print_optimal_solution()
