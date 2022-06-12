import mip

from model.utils import write_json_file


def build_location_model_and_optimize(all_locations, market_locations, dist, direct_build_costs,
                                      max_dist_from_market, min_dist_between_markets):
    """
        Constructs the linear model for the mini market construction problem and finds the optimal solution
        :param all_locations: the list of all locations
        :param market_locations: the list of possible market locations
        :param dist: a matrix containing distances between all locations
        :param direct_build_costs: the array containing costs to build a market in a location
        :param max_dist_from_market: the maximum distance at which a location can be served by a market
        :param min_dist_between_markets: the minimum distance of two markets
        :return: the objective value and optimal values for all variables and optimization status
        """
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

    # Ensures that a location can be assigned to an open market only if the market is closer than a threshold
    for i in all_locations:
        for j in market_locations:
            if dist[i, j] != 0:
                m.add_constr(x[i, j] * dist[i, j] <= max_dist_from_market)

    # Ensures that two markets cannot be opened if the distance between each other is lower than a threshold
    for j in market_locations:
        for h in market_locations:
            if h != j:
                m.add_constr(dist[j, h] + (min_dist_between_markets + 1) * (2 - y[h] - y[j]) >= min_dist_between_markets)

    # ##################
    # Objective function
    # ##################

    # Minimizes the cost of installation of the markets
    m.objective = mip.minimize(mip.xsum(direct_build_costs[j] * y[j] for j in market_locations))

    # Perform optimization of the model
    status = m.optimize()

    for i in market_locations:
        for j in market_locations:
            if y[i].x == 1 and y[j].x == 1 and i != j:
                if dist[i, j] < min_dist_between_markets:
                    print(dist[i, j])

    return m.objective_value, x, y, status


def find_optimal_locations(n, dist, x_coords, y_coords, usable, direct_build_costs,
                           max_dist_from_market, min_dist_between_markets, save=False, json_folder="out/"):
    """
    Finds the optimal solution for the location problem
    :param json_folder: the folder where JSON results will be saved
    :param n: the number of locations in input
    :param dist: a nxn matrix containing distances between every location
    :param x_coords: the array containing the x coordinates for each location
    :param y_coords: the array containing the y coordinates for each location
    :param usable: the array containing booleans that represent if a location is suitable for market construction
    :param direct_build_costs: the array containing costs to build a market in a location
    :param max_dist_from_market: the maximum distance at which a location can be served by a market
    :param min_dist_between_markets: the minimum distance of two markets
    :param save: if True writes the results to a json file
    :return a list of locations where to install markets and the cost of doing so
    """
    all_locations = range(n)
    market_locations = [i for i in all_locations if usable[i]]

    obj_value, x, y, status = build_location_model_and_optimize(all_locations, market_locations, dist,
                                                                direct_build_costs, max_dist_from_market,
                                                                min_dist_between_markets)

    if status != mip.OptimizationStatus.OPTIMAL:
        print(f"Problem has no optimal solution: {status}")
        exit()

    installed_markets = []
    for i in market_locations:
        if y[i].x == 1:
            installed_markets.append(i)

    if save:
        # Save input of model and optimal solution to a JSON file
        x_values = [[x[i, j].x if j in market_locations else 0 for j in all_locations] for i in all_locations]
        data = {"installed_markets": installed_markets, "installation_cost": obj_value, "adj_matrix": x_values}
        write_json_file(json_folder, "location_results.json", data)

    return installed_markets, obj_value
