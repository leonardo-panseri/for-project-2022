import json


def load_data_from_files(input_only=False):
    """
    Load data from JSON files and returns it
    :return: the input and results data from the JSON files in out/ directory
    """
    keys = {"locations_num", "max_dist_from_market", "min_dist_between_markets", "max_stores_per_route", "coords",
            "usable", "direct_build_cost", "dist"}
    with open("out/input.json") as f_input:
        input_data = json.loads(f_input.read())
        locations_num: int = input_data["locations_num"]
        max_dist_from_market = input_data["maxdist"]
        min_dist_between_markets = input_data["mindist"]
        max_stores_per_route = input_data["maxstores"]
        coords = {int(k): v for k, v in input_data["coords"].items()}
        usable = input_data["usable"]
        direct_build_cost = input_data["cost"]
        dist = input_data["dist"]

        data = [locations_num, max_dist_from_market, min_dist_between_markets, max_stores_per_route, coords, usable,
                direct_build_cost, dist]

        if not input_only:

            with open("out/location_results.json") as f_location, open("out/maintenance_results.json") as f_maintenance:
                location_data = json.loads(f_location.read())
                market_locations = location_data["market_locations"]
                installation_cost = location_data["cost"]
                adj_matrix = location_data["adj_matrix"]

                maintenance_data = json.loads(f_maintenance.read())
                maintenance_paths = maintenance_data["paths"]
                maintenance_cost = maintenance_data["cost"]

                keys = keys.union({"market_locations", "installation_cost", "adj_matrix", "maintenance_paths",
                                   "maintenance_cost"})
                data.extend([market_locations, installation_cost, adj_matrix, maintenance_paths, maintenance_cost])

    return dict.fromkeys(keys, data)


def build_base_graph(n, radius):
    """
    Constructs a base PyVis network graph with fixed positioning and a legend
    :param n: the number of nodes
    :param radius: the maximum radius for the problem
    :return: a PyVis Network
    """
    from pyvis.network import Network
    import networkx as nx

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


def visualize_installation_solution(scale=20):
    """
    Constructs a network graph to visualize the solution and shows it
    :param scale: multiplicative factor for coordinates to show nodes more distanced (default: 20)
    """
    data = load_data_from_files()
    market_locations = data["market_locations"]
    adj_matrix = data["adj_matrix"]
    locations_num = data["locations_num"]
    coords = data["coords"]
    max_dist_from_market = data["max_dist_from_market"]
    usable = data["usable"]
    direct_build_cost = data["direct_build_cost"]
    dist = data["dist"]

    print(locations_num)

    net = build_base_graph(locations_num, max_dist_from_market)

    locations = range(locations_num)

    for i in locations:
        # Add all n nodes to the graph with the colour: green if selected in the optimal solution,
        # black if not selected but usable, red if not usable
        color = "green" if i in market_locations else "red" if not usable[i] else "black"
        net.add_node(i, x=coords[i][0] * scale, y=-coords[i][1] * scale, size=4,
                     label=f"N{i}", color=color,
                     title=f"Usable: {usable[i]}<br/>Cost: {direct_build_cost[i]}")

    for i in locations:
        for j in locations:
            if adj_matrix[i][j] == 1:
                # Add all selected edges to the graph
                color = "green"
                net.add_edge(i, j, label=str(round(dist[i][j], 1)), color=color)

    net.show("installation_result.html")


def visualize_maintenance_solution():
    pass


def visualize_input(scale=20):
    """
    Constructs a network graph to visualize the input data and shows it
    :param scale: multiplicative factor for coordinates to show nodes more distanced (default: 20)
    """
    data = load_data_from_files(True)
    locations_num = data["locations_num"]
    usable = data["usable"]
    coords = data["coords"]
    max_dist_from_market = data["max_dist_from_market"]
    direct_build_costs = data["direct_build_costs"]
    dist = data["dist"]

    net = build_base_graph(locations_num, max_dist_from_market)

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

    net.show("input.html")
