import json
import numpy as np

from collections import namedtuple
from enum import Enum

import lib.utilities as util

VALID_ORIENTATIONS = [0, 90, 180, 270]

# Manufacturing Procedure Representation
Process = namedtuple('Process', ('pname', 'inputs', 'outputs'))


class ManufacturingProcedure:
  __slots__ = ('token_types', 'process_types', 'processes', 'output_process')

  def __init__(self, path):
    with open(path) as file:
      info = json.loads(file.read())

    # Load procedure information
    info['tokens'].append('empty')
    self.token_types = Enum('Tokens', info['tokens'])
    self.process_types = Enum(
      'ProcessNames', [p['name'] for p in info['processes']])
    self.processes = {}

    for p in info['processes']:
      ptype = self.process_types[p['name']]
      inputs = [self.token_types[t] for t in p['inputs']]
      outputs = [self.token_types[t] for t in p['outputs']]
      self.processes[ptype] = Process(ptype, inputs, outputs)

    # Get the sink processes
    sink_processes = [p for p in self.processes.values() if len(p.outputs) == 0]

    # Make sure there is only one output process. Store it.
    output_processes = []

    if   len(sink_processes) > 1:
      output_processes = [p for p in sink_processes if self.token_types['waste'] in p.inputs]
    elif len(sink_processes) == 1:
      output_processes = sink_processes
      
    assert len(output_processes) == 1, "There is not 1 output process"

    self.output_process = output_processes[0]

  def output_tokens(self, process_type, token_type):
    return len([t for t in self.processes[process_type].outputs if t == token_type])

  def input_tokens(self, process_type, token_type):
    return len([t for t in self.processes[process_type].inputs if t == token_type])


# Blueprint Representation
class Blueprint:
  __slots__ = ('machine_type', 'process_runtime_map',
               'output', 'input', 'chassis')

  def __init__(self, blueprint_dict: dict, process_types: Enum, machine_types: Enum):

    # Get blueprint mtype
    self.machine_type = machine_types[blueprint_dict['mtype']]

    # Turn process runtimes into a Enum(pname) -> int dict
    self.process_runtime_map = {
      process_types[p]: t for p, t in blueprint_dict['pname_to_runtime'].items()}
    assert all(type(t) is int for t in self.process_runtime_map.values()
               ), 'All runtimes must be ints'

    # Check to see if the footprint is valid
    assert len(set(len(row)
               for row in blueprint_dict['footprint'])) == 1, 'Footprint rows must have same len'

    # Get the coordinates of the anchor point
    anchor = None
    for y, row in enumerate(reversed(blueprint_dict['footprint'])):
      if 'a' in row:
        anchor = util.Point(row.index('a'), y)

    self.input = None
    self.output = None
    self.chassis = []

    # Get the offset of the blueprint's tiles relative to the anchor point
    for y, row in enumerate(reversed(blueprint_dict['footprint'])):
      for x, tile in enumerate(row):
        # The offset of the current tile
        offset = util.Point(x - anchor.x, y - anchor.y)
        # Identify the current tile
        match tile:
          case '.':
            pass
          case 'i':
            self.input = offset
          case 'o':
            self.output = offset
          case 'a' | 'c':
            self.chassis.append(offset)

  def get_possible_input_tokens(self, processes: list[Process]) -> set[Enum]:
    """
    Return a set of possible input tokens a machine blueprinted by this blueprint may accept
    """
    return set([token for process in processes for token in process.inputs if process.pname in self.process_runtime_map])
  
  def get_possible_output_tokens(self, processes: list[Process]) -> set[Enum]:
    """
    Return a set of possible output tokens a machine blueprinted by this blueprint may produce
    """
    return set([token for process in processes for token in process.outputs if process.pname in self.process_runtime_map])


class Blueprints:
  __slots__ = ('machine_types', 'blueprints')

  def __init__(self, path: str, process_types: Enum):
    with open(path) as file:
      info = json.loads(file.read())

    self.machine_types = Enum(
      'MachineTypes', [b['mtype'] for b in info['blueprints']])
    self.blueprints = [Blueprint(
      b_info, process_types, self.machine_types) for b_info in info['blueprints']]

  # This is inefficient way to implement a list, but doesn't get run enough to be worth optimizing.
  # The idea of having mtype as a key for a dict AND a field in blueprint annoys me.
  def get_blueprint(self, mtype):
    return next(b for b in self.blueprints if b.machine_type == mtype)


# Layout Representation
class Machine:
  __slots__ = ('machine_id', 'blueprint', 'position', 'orientation')

  def __init__(self, machine_id: int, blueprint: Blueprint, position: list[int], orientation: int):
    assert all(
      type(num) is int for num in position), "Coordinates must be integers"
    assert orientation in VALID_ORIENTATIONS, "Orientation must be 0, 90, 180 or 270"

    self.machine_id = machine_id
    self.blueprint = blueprint
    self.position = util.Point(int(position[0]), int(position[1]))
    self.orientation = orientation

  def to_dict(self):
    return {
      "mtype": str(self.blueprint.machine_type).split('.')[1],
      "pos": [self.position.x, self.position.y],
      "orientation": self.orientation
    }

  def get_input(self) -> util.Point | None:
    """
    Return the coordinates of the input cell of the machine
    """
    # if self.blueprint.input != None:
    #   print(f"machine:{self.machine_id} blueprint input:{self._convert_point(self.blueprint.input)}") # DEBUG
    return None if self.blueprint.input is None else self._convert_point(self.blueprint.input) 

  def get_output(self) -> util.Point | None:
    """
    Return the coordinates of the input cell of the machine
    """
    # print(f"machine:{self.mid} blueprint output:{self.blueprint.output}") # DEBUG
    return None if self.blueprint.output is None else self._convert_point(self.blueprint.output)

  def get_chassis(self) -> list[util.Point]:
    """
    Return a list of chassis coordinates for the machine
    """
    # print(f"machine:{self.mid} blueprint chassis:{self.blueprint.chassis}") # DEBUG
    return [self._convert_point(pt) for pt in self.blueprint.chassis]

  def get_all_cells(self) -> list[util.Point]:
    """
    Returns the coordinates of every one of a machine's cells
    """
    cells       = self.get_chassis()
    input_cell  = self.get_input()
    output_cell = self.get_output()

    if input_cell is not None:
      cells.append(input_cell)

    if output_cell is not None:
      cells.append(output_cell)

    return cells

  def _convert_point(self, pt: util.Point) -> util.Point:
    """
    Convert a point from a blueprint-relative point to a machine relative point
    """
    return util.rotate_then_translate(pt=pt,
                                      angle=self.orientation,
                                      offset=self.position)
