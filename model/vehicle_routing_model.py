import mip
import math


def sweep():
    pass


def cluster_first_route_second(markets_num, dist, x_coords, y_coords, max_stores_per_route, truck_fixed_fee, truck_fee_per_km):
    # Translate all coordinates to have cartesian origin in the first location (depot)
    x_0 = x_coords[0]
    y_0 = y_coords[0]
    temp = [x_coords[i] - x_0 for i in range(markets_num)]
    x_coords = temp
    temp = [y_coords[i] - y_0 for i in range(markets_num)]
    y_coords = temp

    # Calculate the angle of each market respective of the x axis
    angles = []
    for i in range(1, markets_num):
        angle_rad = math.atan2(y_coords[i], x_coords[i])
        if angle_rad < 0:
            angle_rad += 2 * math.pi
        angles.append({
            "index": i,
            "angle": angle_rad
        })

    # Sort the list in ascending order
    angles.sort(key=lambda x: x["angle"], reverse=True)

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
    print(clusters)

    return "ERR"


def linear_relaxation(installed_markets, dist, x_coords, y_coords, max_stores_per_route, truck_fixed_fee, truck_fee_per_km):

    for h in range(installed_markets):
        # Initialize model and disable verbose logging
        m = mip.Model()
        m.verbose = 0

        # #########
        # Variables
        # #########

        # u_h: 1 if truck h is used, 0 otherwise
        u = [m.add_var(var_type=mip.BINARY) for h in range(installed_markets)]

        # a_ijh: 1 if truck h path contains edge (i,j), 0 otherwise
        a = [[[m.add_var(var_type=mip.BINARY) for h in range(installed_markets)] for j in range(installed_markets)] for i in range(installed_markets)]

        # ###########
        # Constraints
        # ###########
        for i in range(installed_markets):
            for h in range(installed_markets):
                m.add_constr(a[i][i][h] == 0)

        for h in range(installed_markets - 1):
            m.add_constr(u[h] >= u[h + 1])

        for h in range(installed_markets):
            m.add_constr(mip.xsum(a[0][j][h] for j in range(installed_markets)) == u[h])

        for h in range(installed_markets):
            m.add_constr(mip.xsum(a[j][0][h] for j in range(installed_markets)) == u[h])

        for h in range(installed_markets):
            for i in range(installed_markets):
                for j in range(installed_markets):
                    m.add_constr(a[i][j][h] <= u[h])

        for h in range(installed_markets):
            for i in range(installed_markets):
                m.add_constr(mip.xsum(a[i][j][h] for j in range(installed_markets)) == mip.xsum(a[k][i][h] for k in range(installed_markets)))

        for i in range(1, installed_markets):
            m.add_constr(mip.xsum(mip.xsum(a[i][j][h] for h in range(installed_markets)) for j in range(installed_markets)) == 1)

        for j in range(1, installed_markets):
            m.add_constr(mip.xsum(mip.xsum(a[i][j][h] for h in range(installed_markets)) for i in range(installed_markets)) == 1)

        for h in range(installed_markets):
            m.add_constr(mip.xsum(mip.xsum(a[i][j][h] for j in range(installed_markets)) for i in range(installed_markets)) <= max_stores_per_route + 1)

        # ##################
        # Objective function
        # ##################

        # Minimizes the cost of the paths
        m.objective = mip.minimize(
            mip.xsum(truck_fixed_fee * u[h] +
                     mip.xsum(mip.xsum(truck_fee_per_km * dist[i, j] * a[i][j][h] for j in range(installed_markets)) for i in range(installed_markets))
                     for h in range(installed_markets)))

        # Perform optimization of the model
        status = m.optimize()

        if u[h].x == 1:
            edges = []
            for i in range(installed_markets):
                for j in range(installed_markets):
                    if a[i][j][h].x == 1:
                        edges.append((installed_markets[i], installed_markets[j]))
            print(f"Path {h}: {edges}")


def find_vehicle_paths(installed_markets, dist, x_coords, y_coords, max_stores_per_route, truck_fixed_fee, truck_fee_per_km):
    model = cluster_first_route_second

    n = len(installed_markets)
    result = model(n, dist, x_coords, y_coords, max_stores_per_route, truck_fixed_fee, truck_fee_per_km)

    return result
