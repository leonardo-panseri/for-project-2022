import mip
import math
from model.utils import build_distance_matrix, calculate_path_total_length, write_json_file
from itertools import chain, combinations


def powerset(iterable):
    """
       Find all the subsets of the given set
       :param iterable: the starting set
       """
    s = list(iterable)
    return chain.from_iterable(combinations(s, r) for r in range(len(s)+1))


def sweep(markets_num, x_coords, y_coords, max_stores_per_route):
    """
    Clustering method that creates cluster based on the angle between the x-axis and each market location
    :param markets_num: the number of open markets
    :param x_coords: an array containing the x coordinates of the markets
    :param y_coords: an array containing the y coordinates of the markets
    :param max_stores_per_route: the maximum number of markets that can be served by a single truck
    :return: a list of clusters, each cluster is a list of market indexes
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

    return clusters


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


def cluster_first_route_second(markets_num, dist, x_coords, y_coords, max_stores_per_route, truck_fixed_fee,
                               truck_fee_per_km):
    """
    Solution method that is based on clustering the locations together and then connect each cluster solving the
    traveling salesmen problem with an exact model, as we have only small clusters
    :param markets_num: the number of open markets
    :param dist: the matrix containing the distances between each market
    :param x_coords: an array containing the x coordinates of the markets
    :param y_coords: an array containing the y coordinates of the markets
    :param max_stores_per_route: the maximum number of markets that can be served by a single truck
    :param truck_fixed_fee: the fixed fee to pay for each truck + driver that will be used
    :param truck_fee_per_km: the fee per km to pay for the routes of the trucks
    :return: an array containing the paths, each path is an array containing tuples that represent edges in the graph
             and the total maintenance cost (NB: the paths are relative to the index from 0 to market_num)
    """
    clustering_method = sweep

    # Create the clusters
    clusters = clustering_method(markets_num, x_coords, y_coords, max_stores_per_route)

    cost = 0

    paths = []
    for cluster in clusters:
        # Append node 0 to each cluster, as it is the depot and we need it in the path
        cluster.append(0)

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


def exact_model_single_iteration(markets_num, dist, x_coords, y_coords, max_stores_per_route, truck_fixed_fee, truck_fee_per_km):
    """
    Solution method that is based on mip resolution
    :param markets_num: the number of open markets
    :param dist: the matrix containing the distances between each market
    :param x_coords: an array containing the x coordinates of the markets
    :param y_coords: an array containing the y coordinates of the markets
    :param max_stores_per_route: the maximum number of markets that can be served by a single truck
    :param truck_fixed_fee: the fixed fee to pay for each truck + driver that will be used
    :param truck_fee_per_km: the fee per km to pay for the routes of the trucks
    :return: an array containing the paths, each path is an array containing tuples that represent edges in the graph
             and the total maintenance cost (NB: the paths are relative to the index from 0 to market_num)
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

    # Subtours elimination
    for s in powerset(markets):
        if len(s) <= max_stores_per_route + 1:
            for h in trucks:
                m.add_constr(mip.xsum(a[i, j, h] for i in s for j in s) <= len(s) - 1)

    # ##################
    # Objective function
    # ##################

    # Minimizes the cost of the paths
    m.objective = mip.minimize(
        mip.xsum(truck_fixed_fee * u[h] +
                 mip.xsum(mip.xsum(truck_fee_per_km * dist[i, j] * a[i, j, h] for j in markets_0) for i in markets_0)
                 for h in trucks))

    # Perform optimization of the model
    status = m.optimize()

    if status != mip.OptimizationStatus.OPTIMAL:
        print(f"Problem has no optimal solution: {status}")
        exit()

    paths = []
    for h in trucks:
        if u[h].x > 1e-5:
            edges = []
            for i in range(markets_num):
                for j in range(markets_num):
                    if a[i, j, h].x > 1e-5:
                        edges.append((i, j))
            print(f"Path {h}: {edges}")
            paths.append(edges)

    return paths, m.objective_value


def exact_model_multiple_iteration(markets_num, dist, x_coords, y_coords, max_stores_per_route, truck_fixed_fee, truck_fee_per_km):
    """
    Solution method that is based on mip resolution. At each iteration, if the solution is not feasible, a constrain is
    for the smallest subtours in the paths.
    :param markets_num: the number of open markets
    :param dist: the matrix containing the distances between each market
    :param x_coords: an array containing the x coordinates of the markets
    :param y_coords: an array containing the y coordinates of the markets
    :param max_stores_per_route: the maximum number of markets that can be served by a single truck
    :param truck_fixed_fee: the fixed fee to pay for each truck + driver that will be used
    :param truck_fee_per_km: the fee per km to pay for the routes of the trucks
    :return: an array containing the paths, each path is an array containing tuples that represent edges in the graph
             and the total maintenance cost (NB: the paths are relative to the index from 0 to market_num)
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

    # Perform optimization of the model
    status = m.optimize()

    if status != mip.OptimizationStatus.OPTIMAL:
        print(f"Problem has no optimal solution: {status}")
        exit()

    paths = []
    for h in trucks:
        if u[h].x > 1e-5:
            edges = []
            for i in range(markets_num):
                for j in range(markets_num):
                    if a[i, j, h].x > 1e-5:
                        edges.append((i, j))
            print(f"Path {h}: {edges}")
            paths.append(edges)

    subtour = find_shortest_subtour(paths)
    print(subtour)

    while(subtour is not None):
        # Subtour elimination
        for h in trucks:
            m.add_constr(mip.xsum(a[i, j, h] for (i, j) in subtour) <= len(subtour) - 1)


        status = m.optimize()
        if status != mip.OptimizationStatus.OPTIMAL:
            print(f"Problem has no optimal solution: {status}")
            exit()

        paths = []
        for h in trucks:
            if u[h].x > 1e-5:
                edges = []
                for i in range(markets_num):
                    for j in range(markets_num):
                        if a[i, j, h].x > 1e-5:
                            edges.append((i, j))
                print(f"Path {h}: {edges}")
                paths.append(edges)

        subtour = find_shortest_subtour(paths)
        print(subtour)

    return paths, m.objective_value


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


def find_vehicle_paths(installed_markets, dist, x_coords, y_coords, max_stores_per_route, truck_fixed_fee,
                       truck_fee_per_km, save=False):
    """
    Finds a viable solution for the vehicle routing problem, various solution strategies can be utilized
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
    model = exact_model_single_iteration

    n = len(installed_markets)
    paths, cost = model(n, dist, x_coords, y_coords, max_stores_per_route, truck_fixed_fee, truck_fee_per_km)

    # Since the problem is solved for locations 0 to n the paths returned need to be adjusted to the real location index
    effective_paths = [[(installed_markets[i], installed_markets[j]) for i, j in path] for path in paths]

    if save:
        data = {"maintenance_paths": effective_paths, "maintenance_cost": cost}
        write_json_file("maintenance_results.json", data)

    return effective_paths, cost
