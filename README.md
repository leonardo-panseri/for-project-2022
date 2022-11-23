# Foundations of Operational Research Project @ PoliMi - Vehicle routing problem

![Python](https://img.shields.io/badge/python-3776AB?logo=python&logoColor=ffdd65&style=for-the-badge&logoWidth=)

Operational Research course final project  
Professor: Federico Malucelli  
Tutor: Ing. Belotti Pietro Luigi

<img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/python/python-original-wordmark.svg" width="40"/>

## Grades
Project grade: 14/14  
Miniproject grade: 4/4

## Team Members
* [Leonardo Panseri](https://github.com/leonardo-panseri)
* [Viola Renne](https://github.com/viols-code)

## Problem
### Miniproject
A company wants to plan the construction of mini-markets so that each house is at most r kilometers away (Euclidean distance) from a mini-market, and the total construction cost is minimized. The goal was to develop a MILP formulation of the problem and implement it in Python using the MIP module.  
For a detailed description: [Problem](https://github.com/leonardo-panseri/for-project-2022/blob/mini-project/project.pdf)  
More about this project in the mini-project branch

### Final Project
Model for a vehicle routing problem for a fictional company "RoboMarkt" that needs to keep shops stocked in large rural areas. The model has been implemented for Python modelling tool [MIP](https://www.python-mip.com/).  
For a detailed description: [Problem](https://github.com/leonardo-panseri/for-project-2022/blob/master/project.pdf)

## Solutions
Three solution strategies with different accuracies and computational costs have been implemented, including a heuristic for efficiently solving the VRP without deviating much from the optimal solution.

- EXACT_ALL_CONSTR: a complete MIP formulation of the problem, very difficult to solve because of exponential constraint number. Optimal, but slowest.
- ITERATIVE_ADD_CONSTR: a MIP formulation of the problem without sub-tours elimination constraints, these constraints are added iteratively to eliminate the smallest sub-tour found in the current solution until a feasible solution is found. Very close to optimal, but still slow.
- SWEEP_CLUSTER_AND_ROUTE: heuristic approach that divides markets in clusters based on their position and then finds the optimal path in each cluster. Not optimal, but really fast.

## Usage
- Change input data in [robomarkt_solver.py](https://github.com/leonardo-panseri/for-project-2022/blob/30a96135b40e3458e5acb1865d755aa7ca72a1e7/robomarkt_solver.py#L12) (it is imported from a Python file similar to the ones in *data/*)
- Install required packages
    pip install -r requirements.txt
- Run the script
    python robomarkt.py
