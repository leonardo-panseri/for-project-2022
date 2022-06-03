# Authors:
# Viola Renne
# Leonardo Panseri
from model.utils import get_input_length, build_distance_matrix, pretty_print_path
from model.facility_location_model import find_optimal_locations
from model.vehicle_routing_model import find_vehicle_paths
from model.visualization import visualize_input, visualize_solution

# Import data, change the name of the file to change dataset
from data.robomarkt_0 import Cx as x_coords, Cy as y_coords, usable, Dc as direct_build_costs, \
    maxdist as max_dist_from_market, mindist as min_dist_between_markets, maxstores as max_stores_per_route, \
    Fc as truck_fixed_fee, Vc as truck_fee_per_km

# Find the number of locations of the input data and build the distance matrix
locations_num = get_input_length(x_coords, y_coords, usable, direct_build_costs)
distance_matrix, max_dist_between_locations = build_distance_matrix(locations_num, x_coords, y_coords)


def solve(save=False, visualize=False):
    installed_markets, installation_cost = find_optimal_locations(locations_num, distance_matrix, x_coords, y_coords,
                                                                  usable, direct_build_costs, max_dist_from_market,
                                                                  min_dist_between_markets, save)
    print("Shops: " + " ".join([str(el) for el in installed_markets]))

    markets_x_coords = [x_coords[i] for i in range(locations_num) if i in installed_markets]
    markets_y_coords = [y_coords[i] for i in range(locations_num) if i in installed_markets]
    markets_dist, max_dist_between_markets = build_distance_matrix(len(installed_markets), markets_x_coords,
                                                                   markets_y_coords)
    paths, maintenance_cost = find_vehicle_paths(installed_markets, markets_dist, markets_x_coords, markets_y_coords,
                                                 max_stores_per_route, truck_fixed_fee, truck_fee_per_km)

    for i in range(len(paths)):
        print(f"Path {i + 1}: {pretty_print_path(paths[i])}")

    print("\n==== Costs ====")
    print(f"Installation cost: {round(installation_cost, 2)}")
    print(f"Maintenance cost: {round(maintenance_cost, 2)}")
    print(f"Total cost: {round(installation_cost + maintenance_cost, 2)}")

    if visualize:
        visualize_solution()


if __name__ == '__main__':
    # If module is executed as a script check command line arguments
    from sys import argv

    if len(argv) >= 2:
        if argv[1] == "save":  # Find optimal solution, save it to file and visualize it
            solve(True, True)
            exit()
        elif argv[1] == "visualize":  # Visualize solution previously saved to file
            visualize_solution()
            exit()
        elif argv[1] == "visualizeinput":  # Visualize input data
            visualize_input(locations_num, distance_matrix, x_coords, y_coords, usable, direct_build_costs,
                            max_dist_from_market)
            exit()

# In any case (import of the module or execution as a script) optimize the model and print the result
solve()
