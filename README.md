# Foundations of Operative Research Project @ PoliMi - Vehicle routing problem
Professor: Federico Malucelli

Project grade: 14/14  
Miniproject grade : 4/4

Model for a vehicle routing problem for a fictional company "RoboMarkt" that needs to keep shops stocked in large rural areas. The model has been implemented for Python modelling tool [MIP](https://www.python-mip.com/). 
Three solution strategy with different accuracies and computational cost have been implemented, including an heuristic for efficiently solving the VRP without deviating much from the optimal solution.

## Usage
- Change input data in [robomarkt_solver.py](https://github.com/leonardo-panseri/for-project-2022/blob/30a96135b40e3458e5acb1865d755aa7ca72a1e7/robomarkt_solver.py#L12) (it is imported from a Python file similar to the ones in *data/*)
- Install required packages
    pip install -r requirements.txt
- Run the script
    python robomarkt.py
