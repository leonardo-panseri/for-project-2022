import mip
import json


# ###################################
# Model construction and optimization
# ###################################

def build_new_location_model_and_optimize(all_locations, market_locations, dist, usable, direct_build_costs,
                                          max_dist_from_market, min_dist_between_markets):
    # Initialize model and disable verbose logging
    m = mip.Model()
    m.verbose = 0

    # #########
    # Variables
    # #########

    # y_j: 1 if market j will be opened, 0 otherwise
    y = {j: m.add_var(var_type=mip.BINARY) for j in market_locations}

    # x_ij: 1 if location i is assigned to market j, 0 otherwise
    x = {(i, j): m.add_var(var_type=mip.BINARY) for i in all_locations for j in market_locations}

    # ###########
    # Constraints
    # ###########

    # Ensures that every location is assigned to exactly 1 market
    for i in all_locations:
        m.add_constr(mip.xsum(x[i, j] for j in market_locations) == 1)

    # Ensures that if location i is assigned to market j, market j must be opened
    for i in all_locations:
        for j in market_locations:
            if dist[i, j] != 0:
                m.add_constr(x[i, j] <= y[j])
            else:
                m.add_constr(x[i, j] == y[j])

    # Ensures that market 0 is opened, as it is the main branch of the company
    m.add_constr(y[0] == 1)

    for i in all_locations:
        for j in market_locations:
            if dist[i, j] != 0:
                m.add_constr(x[i, j] * dist[i, j] <= max_dist_from_market)

    # Ensures that every location is assigned to the closest open market
    # for i in all_locations:
    #     for h in market_locations:
    #         m.add_constr(mip.xsum(x[i, j] for j in market_locations if dist[i, h] > dist[i, j]) <= 1 - y[h])
    for i in all_locations:
        for j in market_locations:
            for h in market_locations:
                if dist[i, j] != 0:
                    # m.add_constr(y[i, j] * dist[i, j] <= dist[i, t] + dist[i, j] * (1 - x[t]))
                    m.add_constr(dist[i, j] * x[i, j] <= dist[i, h] + dist[i, j] * (1 - y[h]))

    # ##################
    # Objective function
    # ##################

    # Minimizes the cost of installation of the markets
    m.objective = mip.minimize(mip.xsum(direct_build_costs[j] * y[j] for j in market_locations))

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
    all_locations = range(n)
    market_locations = [i for i in all_locations if usable[i]]

    obj_value, x, y, status = build_new_location_model_and_optimize(all_locations, market_locations, dist, usable,
                                                                    direct_build_costs, max_dist_from_market,
                                                                    min_dist_between_markets)

    if status != mip.OptimizationStatus.OPTIMAL:
        print(f"Problem has no optimal solution: {status}")
        exit()

    print(obj_value)

    installed_markets = []
    for i in market_locations:
        if y[i].x == 1:
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
        y_values = [y[i].x for i in market_locations]
        x_values = [[x[i, j].x for j in market_locations] for i in all_locations]
        dist_values = [[dist[i, j] for j in range(n)] for i in range(n)]
        result = {"n": n, "market_locations": market_locations, "maxdist": max_dist_from_market,
                  "mindist": min_dist_between_markets, "coords": coords, "usable": usable, "cost": direct_build_costs,
                  "dist": dist_values, "obj_value": obj_value, "x": x_values, "y": y_values}

        f = open("result.json", "w")
        f.write(json.dumps(result))
        f.close()
