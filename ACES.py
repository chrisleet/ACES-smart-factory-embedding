import json
import lib.scenario      as scenario
import sys

from lib.factory         import Factory
from lib.layout          import Layout
from lib.plan_generator  import Plan_Generator
from time                import time

config_path = sys.argv[1]
output_path = sys.argv[2]

with open(config_path) as file:
  config = json.loads(file.read())

procedure     = scenario.ManufacturingProcedure(config['procedure_path'])
blueprints    = scenario.Blueprints(config['blueprints_path'], procedure.process_types)

initial_layout  = Layout.from_layout_file(config['layout_path'], blueprints)

factory = Factory.from_layout(initial_layout)
factory.export_factory(config['vis_map'])

# (3) Generate plan
max_time      = 60*30 #seconds
max_timesteps = 30

start_time    = time()
timesteps     = 4

timesteps_to_objective = {}
timesteps_to_runtime   = {}

while (time() - start_time) < max_time and timesteps <= max_timesteps:

  iteration_start_time = time()

  factory.timesteps = timesteps 
  wdp = Plan_Generator(procedure, factory)
  print(procedure.output_process)
  wdp.model.optimize()
  # wdp.print_model()
  # wdp.print_objective()

  timesteps_to_objective[timesteps] = float(wdp.get_objective())
  timesteps_to_runtime[timesteps]   = time() - iteration_start_time

  print(f"timesteps:{timesteps} objective:{timesteps_to_objective[timesteps]} runtime:{timesteps_to_runtime[timesteps]}")

  # (4) Export plan
  if timesteps_to_objective[timesteps] == max(timesteps_to_objective.values()):
    print(f"timesteps:{timesteps} exporting...")
    wdp.export_plan(config, procedure, factory)

  timesteps += 1

with open(output_path, 'w') as outfile:
  json.dump({
    "timesteps_to_objective": timesteps_to_objective,
    "timesteps_to_runtime": timesteps_to_runtime
  }, outfile)

print(f"timesteps_to_objective:{timesteps_to_objective}")
print(f"timesteps_to_runtime:{timesteps_to_runtime}")

