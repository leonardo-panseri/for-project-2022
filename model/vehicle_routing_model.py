import mip
import math
from model.utils import build_distance_matrix, calculate_path_total_length, write_json_file


def sweep(markets_num, x_coords, y_coords, max_stores_per_route):
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


def build_tsp_model_and_optimize(markets_num, dist):
    m = mip.Model()
    m.verbose = 0

    markets = range(markets_num)

    x = {(i, j): m.add_var(var_type=mip.BINARY) for i in markets for j in markets}

    for i in markets:
        m.add_constr(x[i, i] == 0)

    for i in markets:
        m.add_constr(mip.xsum(x[i, j] for j in markets) == 1)
        m.add_constr(mip.xsum(x[j, i] for j in markets) == 1)

    m.objective = mip.minimize(mip.xsum(x[i, j] * dist[i, j] for i in markets for j in markets))

    status = m.optimize()

    if status != mip.OptimizationStatus.OPTIMAL:
        print(f"Problem has no optimal solution: {status}")
        exit()

    path = []
    for i in markets:
        for j in markets:
            if x[i, j].x == 1:
                path.append((i, j))

    subtour = find_shortest_subtour([path])
    while subtour is not None:
        m.add_constr(mip.xsum(x[i, j] for (i, j) in subtour) <= len(subtour) - 1)

        status = m.optimize()
        if status != mip.OptimizationStatus.OPTIMAL:
            print(f"Problem has no optimal solution: {status}")
            exit()

        path = []
        for i in markets:
            for j in markets:
                if x[i, j].x == 1:
                    path.append((i, j))

        subtour = find_shortest_subtour([path])

    return path


def cluster_first_route_second(markets_num, dist, x_coords, y_coords, max_stores_per_route, truck_fixed_fee,
                               truck_fee_per_km):
    clustering_method = sweep

    clusters = clustering_method(markets_num, x_coords, y_coords, max_stores_per_route)

    cost = 0

    paths = []
    for cluster in clusters:
        cluster.append(0)

        n = len(cluster)
        cluster_x_coords = [x_coords[i] for i in cluster]
        cluster_y_coords = [y_coords[i] for i in cluster]

        cluster_dist, _ = build_distance_matrix(n, cluster_x_coords, cluster_y_coords)
        path = build_tsp_model_and_optimize(n, cluster_dist)

        effective_path = [(cluster[i], cluster[j]) for (i, j) in path]
        paths.append(effective_path)

        cost += calculate_path_total_length(path, cluster_dist) * truck_fee_per_km

    cost += truck_fixed_fee * len(paths)

    return paths, cost


def linear_relaxation(markets_num, dist, x_coords, y_coords, max_stores_per_route, truck_fixed_fee, truck_fee_per_km):
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
    u = {h: m.add_var(lb=0, ub=1) for h in trucks}

    # a_ijh: 1 if truck h path contains edge (i,j), 0 otherwise
    a = {(i, j, h): m.add_var(lb=0, ub=1) for i in markets_0 for j in markets_0 for h in trucks}

    # ###########
    # Constraints
    # ###########

    # Every path must start from market 0
    for h in trucks:
        m.add_constr(mip.xsum(a[0, j, h] for j in markets) == u[h])

    for h in range(markets_num - 2):
        m.add_constr(u[h] >= u[h + 1])

    for i in markets_0:
        m.add_constr(mip.xsum(a[i, i, h] for h in trucks) == 0)

    #
    for i in markets_0:
        for h in trucks:
            m.add_constr(mip.xsum(a[i, j, h] for j in markets_0) == mip.xsum(a[j, i, h] for j in markets_0))

    for h in trucks:
        m.add_constr(mip.xsum(a[i, j, h] for i in markets_0 for j in markets_0) <= u[h] * (max_stores_per_route + 1))

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
        for h in trucks:
            m.add_constr(mip.xsum(a[i, j, h] for (i, j) in subtour) <= len(subtour) - 1)
            for (i, j) in subtour:
                a[i, j, h].var_type = mip.BINARY

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

    return "", 0


def find_shortest_subtour(paths):
    min_subtour = None

    for path in paths:
        if len(path) <= 2:
            return None

        path = path.copy()

        start = None
        next = None
        subtours = [[]]
        current_subtour = 0

        while len(path) > 0:
            for edge in path:
                if start is None or next is None:
                    start = edge[0]
                    next = edge[1]
                    path.remove(edge)
                    subtours[current_subtour].append(edge)
                if edge[0] == next:
                    next = edge[1]
                    subtours[current_subtour].append(edge)
                    path.remove(edge)
                    if next == start:
                        if len(subtours[current_subtour]) == 2:
                            return subtours[current_subtour]
                        subtours.append([])
                        current_subtour += 1
                        start = None
                        next = None

        if len(subtours[current_subtour]) == 0:
            del subtours[current_subtour]

        if len(subtours) > 1:
            for subtour in subtours:
                if min_subtour is None:
                    min_subtour = subtour
                elif 0 < len(subtour) < len(min_subtour):
                    min_subtour = subtour

    return min_subtour


def find_vehicle_paths(installed_markets, dist, x_coords, y_coords, max_stores_per_route, truck_fixed_fee,
                       truck_fee_per_km, save=False):
    model = cluster_first_route_second

    n = len(installed_markets)
    paths, cost = model(n, dist, x_coords, y_coords, max_stores_per_route, truck_fixed_fee, truck_fee_per_km)

    if save:
        data = {"paths": paths, "cost": cost}
        write_json_file("maintenance_results.json", data)

    return paths, cost
