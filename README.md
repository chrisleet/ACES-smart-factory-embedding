# ACES-smart-factory-embedding
This is the code associated with the ACES Smart Factory Embedding (SFE) problem solver. This code takes a smart factory and a manufacturing procedure and finds an optimized embedding of that manufacturing procedure into that smart factory. An embedding assigns the manufacturing procedure's processes to the smart factory's machines and determines how the smart factory's agents (e.g., mobile robots) should carry components between machines. Please find a link to the ArViX paper here: ```https://arxiv.org/abs/2502.21101``` This paper was accepted at ICRA 2025. All questions about the code should be directed to the corresponding author ([appellation][at][university]) where [appellation]:cjleet and [university]:usc.edu - I'll get back to you as soon as I can.

## QUICKSTART
To run our code, you will need to install Python 3 (we used version 3.11), Gurobipy 11.0.3, NetworkX 3.3, Numpy 1.26.4 and Filelock 3.16.0. Later version of the code should work but are untested. On Ubuntu, once you have installed Python 3.11, you can install these packages using the commands:

```
python3.11 -m pip install gurobipy==11.0.3
python3.11 -m pip install networkx==3.3
python3.11 -m pip install numpy==1.26.4
python3.11 -m pip install filelock==3.16.0
```

To run any one of the experiments from our paper, run:

```
python3.11 ACES.py <config_file> <file_for_results>
```

For example, to run our small beer brewing experiment, try running:

```
p ACES.py config/beer_from_malt_small.json data/beer_from_malt_small.json
```

You can find config files associated with each of the 6 experiments in the paper in the folder ```config```.

## VISUALIZING RESULTS
Our ACES writes the best plan that it has found to the file ```visualizer/tmp/plan.json```. (Details on how to change this below). You can visualize this plan using our simple HTML based visualizer as follows. First, start up the visualizer server pointed at the test's config file. For our small beer brewing experiment, you can do this as:

```
python3.11 visualizer/visualizer_server.py config/beer_from_malt_small.json
```

This server should display the base factory at ```http://localhost:8080/```

Next, run the plan! In a separate terminal, run the command:

```
python3.11 visualizer/visualizer.py config/beer_from_malt_small.json
```

again, pointing the visualizer code at the plan you want to visualize. The terminal should display the message:

```
> Show factory at timestep 0?
```

Push enter repeatedly to step through the timesteps in the plan one by one.
