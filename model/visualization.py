import json


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


def visualize_installation_solution(scale=20, show_all_edges=False):
    """
    Constructs a network graph to visualize the solution and shows it
    :param scale: multiplicative factor for coordinates to show nodes more distanced (default: 20)
    :param show_all_edges: if set to False (default) only edges that connect nodes in range and that have as destination
                           a node that is selected in the optimal solution are shown
    """
    # Load data from file
    f = open("result.json")
    data = json.loads(f.read())

    n = data["n"]
    market_locations = data["market_locations"]
    rn = data["maxdist"]
    coords = {int(k): v for k, v in data["coords"].items()}
    usbl = data["usable"]
    cost = data["cost"]
    dist = data["dist"]
    x = data["x"]
    y = data["y"]

    net = build_base_graph(n, rn)

    for i in range(len(x)):
        # Check if all selected nodes are usable
        # if y[i] == 1 and not usbl[i]:
        #     print(f"ERROR: node N{i} is selected in the optimal solution, but not usable")
        y_val = 0
        if i in market_locations:
            y_val = y[market_locations.index(i)]

        # Add all n nodes to the graph with the colour: green if selected in the optimal solution,
        # black if not selected but usable, red if not usable
        color = "green" if y_val == 1 else "red" if not usbl[i] else "black"
        net.add_node(i, x=coords[i][0] * scale, y=-coords[i][1] * scale, size=4,
                     label=f"N{i}", color=color,
                     title=f"Usable: {usbl[i]}<br/>Cost: {cost[i]}")

    for i in range(len(x)):
        for j in range(len(y)):
            location_index = market_locations[j]
            if show_all_edges or y[j] == 1:  # Show only edges to nodes that have been selected
                if show_all_edges or dist[i][location_index] <= rn:  # Show only edges in range
                    # Add all edges to the graph with colour: green if selected om the optimal solution,
                    # black if not selected but in range, red if not in range
                    color = "green" if x[i][j] == 1 else "black" if dist[i][location_index] <= rn else "red"
                    net.add_edge(i, location_index, label=str(round(dist[i][location_index], 1)), color=color)
                elif dist[i][location_index] > rn and x[i][j] == 1:  # Check if for all selected edges: distance <= max radius
                    print(f"ERROR: arc ({i},{j}) is selected but their distance is greater than max radius")
            elif x[j] == 0 and x[i][j] == 1:  # Check if all selected edges go to nodes that are selected
                print(f"ERROR: arc ({i},{j}) is selected but N{j} is not selected")

    net.show("installation_result.html")


def visualize_maintenance_solution():
    pass


def visualize_input(n, dist, x_coords, y_coords, usable, direct_build_costs, max_dist_from_market,
                    scale=20, show_all_edges=False):
    """
    Constructs a network graph to visualize the input data and shows it
    :param n: the number of locations in input
    :param dist: a nxn matrix containing distances between locations
    :param x_coords: the array containing the x coordinates for each location
    :param y_coords: the array containing the y coordinates for each location
    :param usable: the array containing booleans that represent if a location is suitable for market construction
    :param direct_build_costs: the array containing costs to build a market in a location
    :param max_dist_from_market: the maximum distance at which a location can be served by a market
    :param scale: multiplicative factor for coordinates to show nodes more distanced (default: 20)
    :param show_all_edges: if set to False (default) only edges that connect nodes in range are shown
    """
    net = build_base_graph(n, max_dist_from_market)

    market_locations = [i for i in range(n) if usable[i]]

    for i in range(n):
        # Add all n nodes to the graph with colour: black if usable, red if not
        color = "black" if usable[i] else "red"
        net.add_node(i, x=x_coords[i] * scale, y=-y_coords[i] * scale, size=4, label=f"N{i}", color=color,
                     title=f"Usable: {usable[i]}<br/>Cost: {direct_build_costs[i]}")

    for i in range(n):
        for j in market_locations:
            if i != j:  # Do not show self-loops
                if dist[i, j] <= max_dist_from_market:  # If node i is in range of node j
                    # Add all edges that connect nodes in range of each other colored black
                    net.add_edge(i, j, color="black", label=round(dist[i, j], 1))
                elif show_all_edges:
                    # Add all edges that connect nodes not in range of each other colored red
                    net.add_edge(i, j, color="red", label=round(dist[i, j], 1))

    net.show("input.html")
