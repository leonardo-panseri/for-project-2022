import mip
import json


# ###################################
# Model construction and optimization
# ###################################

def build_location_model_and_optimize(locations_num, dist, usable, direct_build_costs,
                                      max_dist_from_market, min_dist_between_markets):
    """
    Constructs the linear model for the mini market construction problem and finds the optimal solution
    :param locations_num: the number of locations in input
    :param dist: a matrix containing distances between all locations
    :param usable: the array containing booleans that represent if a location is suitable for market construction
    :param direct_build_costs: the array containing costs to build a market in a location
    :param max_dist_from_market: the maximum distance at which a location can be served by a market
    :param min_dist_between_markets: the minimum distance of two markets
    :return: the objective value and optimal values for all variables and optimization status
    """
    # Initialize the set of all locations
    n = range(locations_num)
    # Initialize large constant to use in constraints
    z = 1e12
    
    # Initialize model and disable verbose logging
    m = mip.Model()
    m.verbose = 0

    # #########
    # Variables
    # #########

    # x_i: 1 if a market will be opened on the land of house i, 0 otherwise
    x = {i: m.add_var(var_type=mip.BINARY) for i in n}

    # y_ij: 1 if market opened on the land of house j is the closest to house i, 0 otherwise
    y = {(i, j): m.add_var(var_type=mip.BINARY) for j in n for i in n}

    # ###########
    # Constraints
    # ###########

    # Ensures that the main location of the company is always selected
    m.add_constr(x[0] * 1 == 1)

    # Ensures that a market can be placed only on land of homeowners that have given their permission
    for i in n:
        m.add_constr(x[i] * 1 <= usable[i])

    # Ensures that y_ij can be 1 only if j is the market closest to house i
    for i in n:
        for j in n:
            for t in n:
                m.add_constr(y[i, j] * dist[i, j] <= dist[i, t] + z * (1 - x[t]))

    # Ensures that the closest market to house i is at a distance smaller than a threshold
    for i in n:
        for j in n:
            if dist[i, j] != 0:  # Check if distance is not 0 to avoid problems in mip linear expression
                m.add_constr(y[i, j] * dist[i, j] * 1 <= max_dist_from_market)

    # Ensures that y_ij can be 1 only if a market is placed on land of house j
    for i in n:
        for j in n:
            m.add_constr(y[i, j] * 1 <= x[j])

    # Ensures that every house i is served by at least one market j
    for i in n:
        m.add_constr(mip.xsum(y[i, j] for j in n) == 1 - 1 * x[i])

    # Ensures that the distance between every two markets is greater than a threshold
    for i in n:
        for j in n:
            if i != j:
                m.add_constr(dist[i, j] >= min_dist_between_markets - z * (2 - x[i] - x[j]))

    # ##################
    # Objective function
    # ##################

    # Minimizes the cost of installation of the markets
    m.objective = mip.minimize(mip.xsum(direct_build_costs[i] * x[i] for i in n))

    # Perform optimization of the model
    status = m.optimize()

    return m.objective_value, x, y, status


def find_optimal_locations(n, dist, x_coords, y_coords, usable, direct_build_costs,
                           max_dist_from_market, min_dist_between_markets, save=False):
    """
    Finds the optimal solution for the location problem and prints it
    :param n: the number of locations in input
    :param dist: a nxn matrix containing distances between every location
    :param x_coords: the array containing the x coordinates for each location
    :param y_coords: the array containing the y coordinates for each location
    :param usable: the array containing booleans that represent if a location is suitable for market construction
    :param direct_build_costs: the array containing costs to build a market in a location
    :param max_dist_from_market: the maximum distance at which a location can be served by a market
    :param min_dist_between_markets: the minimum distance of two markets
    :param save: if True writes the results to a json file
    """

    obj_value, x, y, status = build_location_model_and_optimize(n, dist, usable,
                                                                direct_build_costs, max_dist_from_market,
                                                                min_dist_between_markets)

    if status != mip.OptimizationStatus.OPTIMAL:
        print(f"Problem has no optimal solution: {status}")
        exit()

    installed_markets = []
    for i in range(n):
        if x[i].x == 1:
            installed_markets.append(i)
    print("Shops: " + " ".join([str(el) for el in installed_markets]))

    # s = len(installed_markets)
    #
    # installed_dist = [[
    #   distance(Cx[installed_markets[i]], Cy[installed_markets[i]],
    #           Cx[installed_markets[j]], Cy[installed_markets[j]]) for j in range(s)] for i in range(s)]
    #
    # obj_value, u, a, status = build_path_model_and_optimize(n, s, installed_dist)
    #
    # if status != mip.OptimizationStatus.OPTIMAL:
    #     print(f"Problem has no optimal solution: {status}")
    #     exit()
    #
    # for h in range(s):
    #     if u[h].x == 1:
    #         edges = []
    #         for i in range(s):
    #             for j in range(s):
    #                 if a[i][j][h].x == 1:
    #                     edges.append((installed_markets[i], installed_markets[j]))
    #         print(f"Path {h}: {edges}")

    if save:
        coords = {i: (x_coords[i], y_coords[i]) for i in range(n)}
        x_values = [x[i].x for i in range(n)]
        y_values = [[y[i][j].x for j in range(n)] for i in range(n)]
        result = {"n": n, "maxdist": max_dist_from_market, "mindist": min_dist_between_markets,
                  "coords": coords, "usable": usable, "cost": direct_build_costs, "dist": dist, "obj_value": obj_value,
                  "x": x_values, "y": y_values}

        f = open("result.json", "w")
        f.write(json.dumps(result))
        f.close()
