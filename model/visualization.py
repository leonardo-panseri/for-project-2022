import json
import os


def load_data_from_files(json_folder, input_only=False):
    """
    Load data from JSON files and returns it
    :return: the input and results data from the JSON files in out/ directory
    """
    data = {}
    with open(json_folder + "input.json") as f_input:
        input_data = json.loads(f_input.read())
        input_data["coords"] = {int(k): v for k, v in input_data["coords"].items()}
        data.update(input_data)

        if not input_only:

            with open(json_folder + "location_results.json") as f_location, \
                    open(json_folder + "maintenance_results.json") as f_maintenance:
                location_data = json.loads(f_location.read())
                data.update(location_data)

                maintenance_data = json.loads(f_maintenance.read())
                data.update(maintenance_data)

    return data


def build_base_graph(n, radius, html_folder):
    """
    Constructs a base PyVis network graph with fixed positioning and a legend
    :param n: the number of nodes
    :param radius: the maximum radius for the problem
    :return: a PyVis Network
    :param html_folder: the folder where the graph HTML file will be saved
    """
    from pyvis.network import Network
    import networkx as nx

    if not os.path.exists(html_folder):
        os.makedirs(html_folder)

    net = Network('100%', '100%')

    # Turn off edges inheriting color from nodes
    net.options.edges.inherit_colors(False)

    # Set fixed positioning only
    net.toggle_physics(False)
    net.toggle_drag_nodes(False)
    net.toggle_stabilization(False)

    # Add legend
    g = nx.Graph()

    labels = [f"Max distance: {radius}", "Nodes legend (hover)", "Edges legend (hover)"]
    titles = ["",
              "<b>Nodes<b><br/><span style='color: green'>&bull;</span> : selected in optimal solution"
              "<br/><span style='color: black'>&bull;</span> : not selected but usable"
              "<br/><span style='color: red'>&bull;</span> : not usable",
              "<b>Edges<b><br/><span style='color: green'>&horbar;</span> : selected in optimal solution"
              "<br/><span style='color: black'>&horbar;</span> : not selected but in range"
              "<br/><span style='color: red'>&horbar;</span> : not in range"]

    step = 150
    x = -300
    y = -110
    legend_nodes = [
        (
            n + i,
            {
                'label': labels[i],
                'size': 40,
                'x': x,
                'y': f'{y + i * step}px',
                'shape': 'box',
                'widthConstraint': 150,
                'font': {'size': 30},
                'title': titles[i]
            }
        )
        for i in range(3)
    ]
    g.add_nodes_from(legend_nodes)
    net.from_nx(g)

    return net


def visualize_installation_solution(html_folder, json_folder, scale=20):
    """
    Constructs a network graph to visualize the market installation solution and shows it
    :param html_folder: the folder where the graph HTML file will be saved
    :param json_folder: the folder where the graph JSON file are saved
    :param scale: multiplicative factor for coordinates to show nodes more distanced (default: 20)
    """
    data = load_data_from_files(json_folder)
    installed_markets = data["installed_markets"]
    adj_matrix = data["adj_matrix"]
    locations_num = data["locations_num"]
    coords = data["coords"]
    max_dist_from_market = data["max_dist_from_market"]
    usable = data["usable"]
    direct_build_costs = data["direct_build_costs"]
    dist = data["dist"]

    net = build_base_graph(locations_num, max_dist_from_market, html_folder)

    locations = range(locations_num)

    for i in locations:
        # Add all n nodes to the graph with the colour: green if selected in the optimal solution,
        # black if not selected but usable, red if not usable
        color = "green" if i in installed_markets else "red" if not usable[i] else "black"
        net.add_node(i, x=coords[i][0] * scale, y=-coords[i][1] * scale, size=4, label=f"N{i}", color=color,
                     title=f"Usable: {usable[i]}<br/>Cost: {direct_build_costs[i]}")

    for i in locations:
        for j in locations:
            if adj_matrix[i][j] == 1:
                # Add all selected edges to the graph
                color = "green"
                net.add_edge(i, j, label=str(round(dist[i][j], 1)), color=color)

    net.show(html_folder + "installation_result.html")


def visualize_maintenance_solution(html_folder, json_folder, scale=20):
    """
    Constructs a network graph to visualize the market maintenance solution and shows it
    :param html_folder: the folder where the graph HTML file will be saved
    :param json_folder: the folder where the graph JSON file are saved
    :param scale: multiplicative factor for coordinates to show nodes more distanced (default: 20)
    """
    data = load_data_from_files(json_folder)
    installed_markets = data["installed_markets"]
    coords = data["coords"]
    max_dist_from_market = data["max_dist_from_market"]
    dist = data["dist"]
    maintenance_paths = data["maintenance_paths"]

    net = build_base_graph(max(installed_markets) + 1, max_dist_from_market, html_folder)

    for i in installed_markets:
        # Add all markets as nodes of the graph
        net.add_node(i, x=coords[i][0] * scale, y=-coords[i][1] * scale, size=4, label=f"N{i}")

    for path in maintenance_paths:
        for edge in path:
            # Add all edges forming the maintenance paths to the graph
            i, j = edge
            net.add_edge(i, j, label=str(round(dist[i][j], 1)))

    net.show(html_folder + "maintenance_result.html")


def visualize_input(html_folder, json_folder, scale=20):
    """
    Constructs a network graph to visualize the input data and shows it
    :param html_folder: the folder where the graph HTML file will be saved
    :param json_folder: the folder where the graph JSON file are saved
    :param scale: multiplicative factor for coordinates to show nodes more distanced (default: 20)
    """
    data = load_data_from_files(json_folder, True)
    locations_num = data["locations_num"]
    usable = data["usable"]
    coords = data["coords"]
    max_dist_from_market = data["max_dist_from_market"]
    direct_build_costs = data["direct_build_costs"]
    dist = data["dist"]

    net = build_base_graph(locations_num, max_dist_from_market, html_folder)

    locations = range(locations_num)
    market_locations = [i for i in locations if usable[i]]

    for i in locations:
        # Add all n nodes to the graph with colour: black if usable, red if not
        color = "black" if usable[i] else "red"
        net.add_node(i, x=coords[i][0] * scale, y=-coords[i][1] * scale, size=4, label=f"N{i}", color=color,
                     title=f"Usable: {usable[i]}<br/>Cost: {direct_build_costs[i]}")

    for i in locations:
        for j in market_locations:
            if i != j:  # Do not show self-loops
                if dist[i][j] <= max_dist_from_market:  # If node i is in range of node j
                    # Add all edges that connect nodes in range of each other colored black
                    net.add_edge(i, j, color="black", label=round(dist[i][j], 1))

    net.show(html_folder + "input.html")
