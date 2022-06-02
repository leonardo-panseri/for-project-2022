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


def find_vehicle_paths(installed_markets, dist, x_coords, y_coords, max_stores_per_route, truck_fixed_fee, truck_fee_per_km):
    model = cluster_first_route_second

    n = len(installed_markets)
    result = model(n, dist, x_coords, y_coords, max_stores_per_route, truck_fixed_fee, truck_fee_per_km)

    return result
