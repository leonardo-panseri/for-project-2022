# Authors:
# Viola Renne
# Leonardo Panseri

from timeit import default_timer as timer
from model.utils import get_input_length, build_distance_matrix, pretty_print_path, write_json_file
from model.facility_location_model import find_optimal_locations
from model.vehicle_routing_model import find_vehicle_paths, VRPSolutionStrategy
from model.visualization import visualize_input, visualize_installation_solution, visualize_maintenance_solution

# Import data, change the name of the file to change dataset
from data.robomarkt_2 import Cx as x_coords, Cy as y_coords, usable, Dc as direct_build_costs, \
    maxdist as max_dist_from_market, mindist as min_dist_between_markets, maxstores as max_stores_per_route, \
    Fc as truck_fixed_fee, Vc as truck_fee_per_km

# Find the number of locations of the input data and build the distance matrix
locations_num = get_input_length(x_coords, y_coords, usable, direct_build_costs)
distance_matrix, max_dist_between_locations = build_distance_matrix(locations_num, x_coords, y_coords)

# ############################################################
# Strategy to use to solve the maintenance part of the problem
# ############################################################
# There are four possible solution strategies implemented, enumerated in the VRPSolutionStrategy enum:
#   - EXACT_ALL_CONSTR: a complete MIP formulation of the problem, very difficult to solve because of
#                       exponential constraint number.
#                       Optimal, but slowest.
#   - EXACT_ITERATIVE_ADD_CONSTR: a MIP formulation of the problem without sub-tours elimination constraints,
#                                 these constraints are added iteratively to eliminate the smallest sub-tour found
#                                 in the current solution until a feasible solution is found.
#                                 Very close to optimal, but still slow.
#   - SWEEP_CLUSTER_AND_ROUTE: heuristic approach that divides markets in clusters based on their position and then
#                              finds the optimal path in each cluster.
#                              Not optimal, but really fast.
# Since that in the data that has been given to us the fixed fee weights a lot more than the fee per km,
# the SWEEP_CLUSTER_AND_ROUTE approach is chosen as the default one.
# To obtain better solution in reasonable (but much longer) time, the EXACT_ITERATIVE_ADD_CONSTR approach can be
# used if the instances are not much bigger than those given for testing.

vehicle_routing_strategy = VRPSolutionStrategy.SWEEP_CLUSTER_AND_ROUTE

# Folders where the output files will be saved
json_folder = "out/"
html_folder = "out/html/"


def solve(save=False, visualize=False):
    """
    Solve the Robomarkt problem using the data imported from the input file
    :param save: if set to True saves the input and result to a JSON file, default is False
    :param visualize: if set to True builds and shows a graph representation of the solution, default is False
    :return:
    """
    if save:
        # Convert data to make it translatable to JSON
        coords = {i: (x_coords[i], y_coords[i]) for i in range(locations_num)}
        dist_values = [[distance_matrix[i, j] for j in range(locations_num)] for i in range(locations_num)]
        data = {"locations_num": locations_num, "max_dist_from_market": max_dist_from_market,
                "min_dist_between_markets": min_dist_between_markets, "max_stores_per_route": max_stores_per_route,
                "coords": coords, "usable": usable, "direct_build_costs": direct_build_costs, "dist": dist_values}
        write_json_file(json_folder, "input.json", data)

    # Solve the location facility part of the problem, finding where to install markets to minimize build cost
    # and to serve every customer
    time_start = timer()
    installed_markets, installation_cost = find_optimal_locations(locations_num, distance_matrix, x_coords, y_coords,
                                                                  usable, direct_build_costs, max_dist_from_market,
                                                                  min_dist_between_markets, save, json_folder)
    time_end = timer()
    print("Shops: " + " ".join([str(el) for el in installed_markets]))
    installation_exec_time = time_end - time_start

    # Build a new distance matrix for the vehicle routing part of the problem
    markets_x_coords = [x_coords[i] for i in installed_markets]
    markets_y_coords = [y_coords[i] for i in installed_markets]
    markets_dist, max_dist_between_markets = build_distance_matrix(len(installed_markets), markets_x_coords,
                                                                   markets_y_coords)
    # Solve the vehicle routing problem for the maintenance of the markets chosen in the previous step
    time_start = timer()
    paths, maintenance_cost = find_vehicle_paths(installed_markets, markets_dist, markets_x_coords, markets_y_coords,
                                                 max_stores_per_route, truck_fixed_fee, truck_fee_per_km, save,
                                                 vehicle_routing_strategy, json_folder)
    output_text = ""
    time_end = timer()
    for i in range(len(paths)):
        output_text += f"Path {i + 1}: {pretty_print_path(paths[i])}\n"
    maintenance_exec_time = time_end - time_start

    # Print the costs of the two solutions and the total cost
    output_text += "\n==== Costs ====\n"
    output_text += f"Installation cost: {round(installation_cost, 2)}\n"
    output_text += f"Maintenance cost: {round(maintenance_cost, 2)}\n"
    output_text += f"Total cost: {round(installation_cost + maintenance_cost, 2)}\n"

    # Print the time taken to solve both parts of the problem
    output_text += "\n==== Execution Time ====\n"
    output_text += f"Installation: {round(installation_exec_time, 2)} s\n"
    output_text += f"Maintenance: {round(maintenance_exec_time, 2)} s\n"
    output_text += f"Total execution time: {round(installation_exec_time + maintenance_exec_time, 2)} s\n"

    print(output_text)

    if visualize:
        visualize_installation_solution(html_folder, json_folder)
        visualize_maintenance_solution(html_folder, json_folder)

    return output_text


if __name__ == '__main__':
    # If module is executed as a script check command line arguments
    from sys import argv

    if len(argv) >= 2:
        if argv[1] == "save":  # Find optimal solution, save it to file and visualize it
            solve(True, True)
            exit()
        elif argv[1] == "visualizeinput":  # Visualize input data
            visualize_input(html_folder, json_folder)
            exit()
        elif argv[1] == "benchmark":  # Solve all instances of the problem with the given methods and save all results
            import importlib

            data_files = [str(i) for i in range(5)] + ["big_" + str(i) for i in range(4)]
            strategies = [VRPSolutionStrategy.SWEEP_CLUSTER_AND_ROUTE]

            for data_file in data_files:
                for strategy in strategies:
                    strategy_str = str(strategy).replace("VRPSolutionStrategy.", "")

                    print(f"====== Solving robomarkt_{data_file} - {strategy_str} ======")

                    data = importlib.import_module("data.robomarkt_" + data_file)
                    x_coords = data.Cx
                    y_coords = data.Cy
                    usable = data.usable
                    direct_build_costs = data.Dc
                    max_dist_from_market = data.maxdist
                    min_dist_between_markets = data.mindist
                    max_stores_per_route = data.maxstores
                    truck_fixed_fee = data.Fc
                    truck_fee_per_km = data.Vc

                    vehicle_routing_strategy = strategy

                    locations_num = get_input_length(x_coords, y_coords, usable, direct_build_costs)
                    distance_matrix, max_dist_between_locations = build_distance_matrix(locations_num, x_coords, y_coords)

                    json_folder = f"out/{data_file}/{strategy_str}/json/"
                    html_folder = f"out/{data_file}/{strategy_str}/html/"

                    output_text = solve(True, True)
                    with open(f"out/{data_file}/{strategy_str}/log.txt", "w") as f:
                        f.write(output_text)

                    print("\n")

            exit()


# In any case (import of the module or execution as a script) optimize the model and print the result
solve()
