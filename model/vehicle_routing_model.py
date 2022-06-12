from enum import Enum, auto

import mip
import math
from model.utils import build_distance_matrix, calculate_path_total_length, write_json_file, find_shortest_subtour
from itertools import chain, combinations


class VRPSolutionStrategy(Enum):
    EXACT_ALL_CONSTR = auto()
    ITERATIVE_ADD_CONSTR = auto()
    SWEEP_CLUSTER_AND_ROUTE = auto()
    MODEL_CLUSTER_AND_ROUTE = auto()


# ###################################
# Cluster and route resolution method
# ###################################

def get_market_angles_with_depot_ordered(markets_num, x_coords, y_coords):
    """
    Calculates angle of each market respective to the x axis of the cartesian plane centered in the depot location and
    orders them in descending order
    :param markets_num: the number of open markets
    :param x_coords: an array containing the x coordinates of the markets
    :param y_coords: an array containing the y coordinates of the markets
    :return: an ordered array containing an object with the index of the market and its angle respect to the depot
    """
    # Translate all coordinates to have cartesian origin in the first location (depot)
    x_0 = x_coords[0]
    y_0 = y_coords[0]
    temp = [x_coords[i] - x_0 for i in range(markets_num)]
    x_coords = temp
    temp = [y_coords[i] - y_0 for i in range(markets_num)]
    y_coords = temp

    # Calculate the angle of each market respective of the x-axis
    angles = []
    for i in range(1, markets_num):
        angle_rad = math.atan2(y_coords[i], x_coords[i])
        if angle_rad < 0:
            angle_rad += 2 * math.pi
        angles.append({
            "index": i,
            "angle": angle_rad
        })

    # Sort the list in descending order
    angles.sort(key=lambda x: x["angle"], reverse=True)

    return angles


def sweep(markets_num, x_coords, y_coords, max_stores_per_route):
    """
    Clustering method that creates cluster based on the angle between the x-axis and each market location
    :param markets_num: the number of open markets
    :param x_coords: an array containing the x coordinates of the markets
    :param y_coords: an array containing the y coordinates of the markets
    :param max_stores_per_route: the maximum number of markets that can be served by a single truck
    :return: a list of clusters, each cluster is a list of market indexes
    """
    angles = get_market_angles_with_depot_ordered(markets_num, x_coords, y_coords)

    # Build the list of clusters, each of them can contain up to 'max_stores_per_route' elements
    clusters = [[]]
    i = len(angles) - 1
    curr_cluster = 0
    while len(angles) > 0:
        if len(clusters[curr_cluster]) == max_stores_per_route:
            curr_cluster += 1
            clusters.append([])

        clusters[curr_cluster].append(angles[i]["index"])

        del angles[i]
        i -= 1

    # Remove the last cluster if it is empty
    if len(clusters[curr_cluster]) == 0:
        del clusters[curr_cluster]

    for cluster in clusters:
        # Append node 0 to each cluster, as it is the depot and we need it in the path
        cluster.append(0)

    return clusters


def clustering_model(markets_num, x_coords, y_coords, max_stores_per_route):
    """
    Clustering method that creates cluster by solving a MIP model
    :param markets_num: the number of open markets
    :param x_coords: an array containing the x coordinates of the markets
    :param y_coords: an array containing the y coordinates of the markets
    :param max_stores_per_route: the maximum number of markets that can be served by a single truck
    :return: a list of clusters, each cluster is a list of market indexes
    """
    # Build distance matrix
    dist, _ = build_distance_matrix(markets_num, x_coords, y_coords)

    # Initialize model and disable verbose logging
    m = mip.Model()
    m.verbose = 0

    # ####
    # Sets
    # ####
    markets = range(markets_num)
    markets_wo_depot = range(1, markets_num)
    clusters = range(markets_num - 1)

    # #########
    # Variables
    # #########

    # cluster_c: 1 if cluster i is not empty, 0 otherwise
    cluster = {c: m.add_var(var_type=mip.BINARY, lb=0, ub=markets_num - 1) for c in clusters}
    # x_ic: 1 if market i is assigned to cluster c, 0 otherwise
    x = {(i, c): m.add_var(var_type=mip.BINARY) for i in markets for c in clusters}
    # y_ij: 1 if markets i and j belong to the same cluster
    y = {(i, j): m.add_var(var_type=mip.BINARY) for i in markets for j in markets}

    # ##################
    # Objective function
    # ##################
    cluster_weight = 100000
    # Minimizes the number of clusters and the distance between markets in each cluster
    m.objective = mip.minimize(mip.xsum(cluster_weight * cluster[c] for c in clusters) +
                               mip.xsum(dist[i, j] * y[i, j] for i in markets for j in markets if i < j))

    # ###########
    # Constraints
    # ###########

    # Ensures that every market is assigned to exactly 1 cluster
    for i in markets_wo_depot:
        m.add_constr(mip.xsum(x[i, c] for c in clusters) == 1)

    for c in range(markets_num - 2):
        m.add_constr(cluster[c] >= cluster[c + 1])

    for c in clusters:
        m.add_constr(mip.xsum(x[i, c] for i in markets) <= (max_stores_per_route + 1) * cluster[c])

    for c in clusters:
        m.add_constr(x[0, c] == cluster[c])

    for c in clusters:
        for i in markets:
            for j in markets:
                if i < j:
                    m.add_constr(y[i, j] >= (x[i, c] + x[j, c] - 1))

    m.optimize()

    result = []
    for c in clusters:
        if cluster[c].x == 1:
            result.append([])
            for i in markets:
                if x[i, c].x == 1:
                    result[-1].append(i)

    return result


def tsp_optimize_and_get_paths(m, markets, x):
    """
    Utility method to optimize and parse the solution of the TSP model
    :param m: the model
    :param markets: the set of markets
    :param x: the array of variables
    :return: the array of edges representing the optimal path
    """
    status = m.optimize()

    if status != mip.OptimizationStatus.OPTIMAL:
        print(f"Problem has no optimal solution: {status}")
        exit()

    path = []
    for i in markets:
        for j in markets:
            if x[i, j].x == 1:
                path.append((i, j))
    return path


def build_tsp_model_and_optimize(markets_num, dist):
    """
    Constructs the linear model for the travelling salesmen problem and finds the optimal solution
    :param markets_num: the number of markets to solve the TSP on
    :param dist: the matrix of the distances between each market
    :return: an array of edges representing the optimal path (NB: the indexes in this array go from 0 to markets_num)
    """
    # Initialize model and disable verbose logging
    m = mip.Model()
    m.verbose = 0

    # ####
    # Sets
    # ####
    markets = range(markets_num)

    # #########
    # Variables
    # #########

    # x_ij: 1 if edge (i, j) is chosen, 0 otherwise
    x = {(i, j): m.add_var(var_type=mip.BINARY) for i in markets for j in markets}

    # ###########
    # Constraints
    # ###########

    # Ensures that there are no self-loops
    for i in markets:
        m.add_constr(x[i, i] == 0)

    # Ensures that from every market enters and exits only one edge
    for i in markets:
        m.add_constr(mip.xsum(x[i, j] for j in markets) == 1)
        m.add_constr(mip.xsum(x[j, i] for j in markets) == 1)

    # ##################
    # Objective function
    # ##################

    # Minimizes the total length of the path
    m.objective = mip.minimize(mip.xsum(x[i, j] * dist[i, j] for i in markets for j in markets))

    path = tsp_optimize_and_get_paths(m, markets, x)

    subtour = find_shortest_subtour([path])
    while subtour is not None:
        # While there are sub-tours in the solution, add a constraint to eliminate the smallest one
        m.add_constr(mip.xsum(x[i, j] for (i, j) in subtour) <= len(subtour) - 1)

        path = tsp_optimize_and_get_paths(m, markets, x)

        subtour = find_shortest_subtour([path])

    return path


def cluster_first_route_second(markets_num, x_coords, y_coords, max_stores_per_route, truck_fixed_fee,
                               truck_fee_per_km, cluster_strategy=sweep):
    """
    Solution method that is based on clustering the locations together and then connect each cluster solving the
    traveling salesmen problem with an exact model, as we have only small clusters
    :param cluster_strategy: the strategy to use to form clusters (sweep or clustering_model)
    :param markets_num: the number of open markets
    :param x_coords: an array containing the x coordinates of the markets
    :param y_coords: an array containing the y coordinates of the markets
    :param max_stores_per_route: the maximum number of markets that can be served by a single truck
    :param truck_fixed_fee: the fixed fee to pay for each truck + driver that will be used
    :param truck_fee_per_km: the fee per km to pay for the routes of the trucks
    :return: an array containing the paths, each path is an array containing tuples that represent edges in the graph
             and the total maintenance cost (NB: the paths are relative to the index from 0 to market_num)
    """
    # Create the clusters
    clusters = cluster_strategy(markets_num, x_coords, y_coords, max_stores_per_route)

    cost = 0

    paths = []
    for cluster in clusters:
        n = len(cluster)
        # Create arrays of coordinates for the cluster and the distance matrix
        cluster_x_coords = [x_coords[i] for i in cluster]
        cluster_y_coords = [y_coords[i] for i in cluster]
        cluster_dist, _ = build_distance_matrix(n, cluster_x_coords, cluster_y_coords)

        # Solve the TSP in the cluster
        path = build_tsp_model_and_optimize(n, cluster_dist)

        # Translate the edges indexes to be relative to the market indexes
        effective_path = [(cluster[i], cluster[j]) for i, j in path]

        paths.append(effective_path)

        # Calculate the cost of this path and add it to the total
        cost += calculate_path_total_length(path, cluster_dist) * truck_fee_per_km

    # Add the fixed cost to the total
    cost += truck_fixed_fee * len(paths)

    return paths, cost


# #############################
# Exact model resolution method
# #############################

def powerset(iterable):
    """
       Find all the subsets of the given set
       :param iterable: the starting set
       """
    s = list(iterable)
    return chain.from_iterable(combinations(s, r) for r in range(len(s) + 1))


def build_base_model(markets_num, dist, max_stores_per_route, truck_fixed_fee, truck_fee_per_km):
    """
    Builds the base exact model for the VRP
    :param markets_num: the number of markets
    :param dist: the distance matrix containing the distance between each market
    :param max_stores_per_route: the max number of stores in a path
    :param truck_fixed_fee: the fixed fee to pay for each truck + driver that will be used
    :param truck_fee_per_km: the fee per km to pay for the routes of the trucks
    :return:
    """
    # Initialize model and disable verbose logging
    m = mip.Model()
    m.verbose = 0

    # #########
    # Sets
    # #########

    markets_0 = range(markets_num)
    markets = range(1, markets_num)
    trucks = range(markets_num - 1)

    # #########
    # Variables
    # #########

    # u_h: 1 if truck h is used, 0 otherwise
    u = {h: m.add_var(var_type=mip.BINARY) for h in trucks}

    # a_ijh: 1 if truck h path contains edge (i,j), 0 otherwise
    a = {(i, j, h): m.add_var(var_type=mip.BINARY) for i in markets_0 for j in markets_0 for h in trucks}

    # ###########
    # Constraints
    # ###########

    # Every path must start from market 0
    for h in trucks:
        m.add_constr(mip.xsum(a[0, j, h] for j in markets) == u[h])

    # Take the trucks in index order
    for h in range(markets_num - 2):
        m.add_constr(u[h] >= u[h + 1])

    # Self loops are not allowed
    for i in markets_0:
        m.add_constr(mip.xsum(a[i, i, h] for h in trucks) == 0)

    # The number of arcs in the backward star must be equal to the number of the forward star
    for i in markets_0:
        for h in trucks:
            m.add_constr(mip.xsum(a[i, j, h] for j in markets_0) == mip.xsum(a[j, i, h] for j in markets_0))

    # If the truck is chosen, the maximum number of arcs in each path must be max_stores_per_route + 1
    for h in trucks:
        m.add_constr(mip.xsum(a[i, j, h] for i in markets_0 for j in markets_0) <= u[h] * (max_stores_per_route + 1))

    # Every node must be reached
    for i in markets:
        m.add_constr(mip.xsum(a[j, i, h] for j in markets_0 for h in trucks) == 1)

    # ##################
    # Objective function
    # ##################

    # Minimizes the cost of the paths
    m.objective = mip.minimize(
        mip.xsum(truck_fixed_fee * u[h] +
                 mip.xsum(mip.xsum(truck_fee_per_km * dist[i, j] * a[i, j, h] for j in markets_0) for i in markets_0)
                 for h in trucks))

    return m, u, a, markets, trucks


def model_optimize_and_get_paths(m, trucks, u, markets_num, a):
    """
    Utility method to optimize and parse the solution of the model
    :param m: the model
    :param trucks: the trucks
    :param u: the u variables
    :param markets_num: the number of markets
    :param a: the a variables
    :return: an array of paths, each path is an array of edges
    """
    status = m.optimize()

    if status != mip.OptimizationStatus.OPTIMAL:
        print(f"Problem has no optimal solution: {status}")
        exit()

    paths = []
    for h in trucks:
        if u[h].x == 1:
            edges = []
            for i in range(markets_num):
                for j in range(markets_num):
                    if a[i, j, h].x == 1:
                        edges.append((i, j))
            print(f"Path {h}: {edges}")
            paths.append(edges)

    return paths


def exact_model(markets_num, dist, max_stores_per_route, truck_fixed_fee, truck_fee_per_km):
    """
    Solution method that is based on mip resolution
    :param markets_num: the number of open markets
    :param dist: the matrix containing the distances between each market
    :param max_stores_per_route: the maximum number of markets that can be served by a single truck
    :param truck_fixed_fee: the fixed fee to pay for each truck + driver that will be used
    :param truck_fee_per_km: the fee per km to pay for the routes of the trucks
    :return: an array containing the paths, each path is an array containing tuples that represent edges in the graph
             and the total maintenance cost (NB: the paths are relative to the index from 0 to market_num)
    """
    m, u, a, markets, trucks = build_base_model(markets_num, dist, max_stores_per_route, truck_fixed_fee,
                                                truck_fee_per_km)

    # ###########
    # Constraints
    # ###########

    # Subtours elimination
    for s in powerset(markets):
        if len(s) <= max_stores_per_route + 1:
            for h in trucks:
                m.add_constr(mip.xsum(a[i, j, h] for i in s for j in s) <= len(s) - 1)

    paths = model_optimize_and_get_paths(m, trucks, u, markets_num, a)

    return paths, m.objective_value


def iterative_adding_constrains(markets_num, dist, max_stores_per_route, truck_fixed_fee, truck_fee_per_km):
    """
    Solution method that is based on mip resolution. At each iteration, if the solution is not feasible, a constrain is
    for the smallest subtours in the paths.
    :param markets_num: the number of open markets
    :param dist: the matrix containing the distances between each market
    :param max_stores_per_route: the maximum number of markets that can be served by a single truck
    :param truck_fixed_fee: the fixed fee to pay for each truck + driver that will be used
    :param truck_fee_per_km: the fee per km to pay for the routes of the trucks
    :return: an array containing the paths, each path is an array containing tuples that represent edges in the graph
             and the total maintenance cost (NB: the paths are relative to the index from 0 to market_num)
    """
    m, u, a, markets, trucks = build_base_model(markets_num, dist, max_stores_per_route, truck_fixed_fee,
                                                truck_fee_per_km)

    # Perform optimization of the model
    paths = model_optimize_and_get_paths(m, trucks, u, markets_num, a)

    subtour = find_shortest_subtour(paths)
    print(subtour)

    while subtour is not None:
        # Subtour elimination
        for h in trucks:
            m.add_constr(mip.xsum(a[i, j, h] for (i, j) in subtour) <= len(subtour) - 1)

        paths = model_optimize_and_get_paths(m, trucks, u, markets_num, a)

        subtour = find_shortest_subtour(paths)
        print(subtour)

    return paths, m.objective_value


# ###########
# Entry point
# ###########

def find_vehicle_paths(installed_markets, dist, x_coords, y_coords, max_stores_per_route, truck_fixed_fee,
                       truck_fee_per_km, save=False, strategy=VRPSolutionStrategy.SWEEP_CLUSTER_AND_ROUTE,
                       json_folder=""):
    """
    Finds a viable solution for the vehicle routing problem, various solution strategies can be utilized
    :param json_folder: the folder where JSON results will be saved
    :param strategy: the solution strategy to use
    :param installed_markets: the list of locations where markets are installed
    :param dist: a matrix containing the distances between each market
    :param x_coords: an array containing the x coordinates of the markets
    :param y_coords: an array containing the y coordinates of the markets
    :param max_stores_per_route: the maximum number of markets that can be served by a single truck
    :param truck_fixed_fee: the fixed fee to pay for each truck + driver that will be used
    :param truck_fee_per_km: the fee per km to pay for the routes of the trucks
    :param save: if True save the results to a JSON file (default: False)
    :return: an array containing the paths, each path is an array containing tuples that represent edges in the graph
             and the total maintenance cost
    """
    n = len(installed_markets)
    paths = []
    cost = 0
    if strategy is VRPSolutionStrategy.SWEEP_CLUSTER_AND_ROUTE:
        paths, cost = cluster_first_route_second(n, x_coords, y_coords, max_stores_per_route, truck_fixed_fee,
                                                 truck_fee_per_km, cluster_strategy=sweep)
    elif strategy is VRPSolutionStrategy.MODEL_CLUSTER_AND_ROUTE:
        paths, cost = cluster_first_route_second(n, x_coords, y_coords, max_stores_per_route, truck_fixed_fee,
                                                 truck_fee_per_km, cluster_strategy=clustering_model)
    elif strategy is VRPSolutionStrategy.ITERATIVE_ADD_CONSTR:
        paths, cost = iterative_adding_constrains(n, dist, max_stores_per_route, truck_fixed_fee, truck_fee_per_km)
    elif strategy is VRPSolutionStrategy.EXACT_ALL_CONSTR:
        paths, cost = exact_model(n, dist, max_stores_per_route, truck_fixed_fee, truck_fee_per_km)
    else:
        exit("Invalid solution strategy")

    # Since the problem is solved for locations 0 to n the paths returned need to be adjusted to the real location index
    effective_paths = [[(installed_markets[i], installed_markets[j]) for i, j in path] for path in paths]

    if save:
        data = {"maintenance_paths": effective_paths, "maintenance_cost": cost}
        write_json_file(json_folder, "maintenance_results.json", data)

    return effective_paths, cost
