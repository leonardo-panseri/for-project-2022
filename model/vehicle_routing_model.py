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

    #
    angles = []
    for i in range(1, markets_num):
        angle_rad = math.atan2(y_coords[i])

    return "ERR"


def find_vehicle_paths(installed_markets, dist, x_coords, y_coords, max_stores_per_route, truck_fixed_fee, truck_fee_per_km):
    model = cluster_first_route_second

    n = len(installed_markets)
    result = model(n, dist, x_coords, y_coords, max_stores_per_route, truck_fixed_fee, truck_fee_per_km)

    return result
