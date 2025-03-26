import json

import gurobipy                  as gp
import lib.ilp_helper_functions  as ilp
import lib.utilities             as util

from   collections          import defaultdict
from   gurobipy             import GRB
from   itertools            import product

from lib.scenario import ManufacturingProcedure
from lib.factory import Factory


class Plan_Generator():

  __slots__ = ('model', 'var')

  def __init__(self, procedure: ManufacturingProcedure, factory: Factory):

    # (A) Initialize ILP model
    env = gp.Env()
    env.setParam('OutputFlag', 0)
    self.model = gp.Model("plan_generation", env=env)
    self.model.setParam('TimeLimit', 2.5*60)

    # (B) Set up variables
    var          = {}                      # name -> gurobi variable

    #     If machine m can run process p, we create:
    #  a. An assignment variable which indicates if machine m has been assigned process p
    #  b. A  rate       variable which indicates the rate that machine m runs process p
    for m in factory.machines:
      for pname in m.blueprint.process_runtime_map:
        var_name      = ilp.assign_var(m.machine_id, pname)
        var[var_name] = self.model.addVar(vtype='B', name=var_name)

        var_name      = ilp.rate_var(m.machine_id, pname)
        var[var_name] = self.model.addVar(vtype='C', lb=0, ub=1, name=var_name)

    # Create position var for each cell on each time step for each token
    for c, t, z in product(factory.cell_graph.nodes, range(factory.timesteps), procedure.token_types):
      var_name = ilp.position_var(c, t, z)
      var[var_name] = self.model.addVar(vtype='B', name=var_name)

    # Create movement var for each edge on each time step for each token
    for (ck, cj), t, z in product(factory.cell_graph.edges, range(factory.timesteps), procedure.token_types):
      
      # Fwd movement
      var_name = ilp.movement_var(ck, cj, t, z)
      var[var_name] = self.model.addVar(vtype='B', name=var_name)
      # if ck == cj: continue
      # Bck movement 
      var_name = ilp.movement_var(cj, ck, t, z)
      var[var_name] = self.model.addVar(vtype='B', name=var_name)

    # Create emission var for each cell on each time step for relevant tokens
    for m in factory.machines:
      if m.get_output() is None: continue
      for z, t in product(m.blueprint.get_possible_output_tokens(procedure.processes.values()), range(factory.timesteps)):
        var_name = ilp.emission_var(m.get_output(), t, z)
        var[var_name] = self.model.addVar(vtype='B', name=var_name)

    # Create absorption var for null token for each output cell at each timestep
    for m in factory.machines:
      if m.get_output() is None: continue
      for t in range(factory.timesteps):
        var_name = ilp.absorption_var(m.get_output(), t, procedure.token_types.empty)
        var[var_name] = self.model.addVar(vtype='B', name=var_name)
    
    # Create absorption var for each cell on each time step for relevant tokens
    for m in factory.machines:
      if m.get_input() is None: continue
      for z, t in product(m.blueprint.get_possible_input_tokens(procedure.processes.values()), range(factory.timesteps)):
        var_name = ilp.absorption_var(m.get_input(), t, z)
        # print(f"Creating absorption var:{var_name}") # DEBUG
        var[var_name] = self.model.addVar(vtype='B', name=var_name)

    # Create emission var for null token for each input cell at each timestep
    for m in factory.machines:
      if m.get_input() is None: continue
      for t in range(factory.timesteps):
        var_name = ilp.emission_var(m.get_input(), t, procedure.token_types.empty)
        var[var_name] = self.model.addVar(vtype='B', name=var_name)


    # (C) Setup Constraints

    # (C) (1) at most one process is assigned to each machine
    for m in factory.machines:
      assign_sum  = gp.quicksum([var[ilp.assign_var(m.machine_id, pname)] for pname in m.blueprint.process_runtime_map])
      constr_name = ilp.assign_constr(m.machine_id)
      self.model.addConstr(assign_sum <= 1, name=constr_name) 

    # (C) (2) The rate that a machine runs a process is only non-zero if the process is assigned to the machine
    for m in factory.machines:
      for pname in m.blueprint.process_runtime_map:
        rate_var    = var[ilp.rate_var(m.machine_id, pname)]
        assign_var  = var[ilp.assign_var(m.machine_id, pname)]
        constr_name = ilp.bind_constr(m.machine_id, pname)
        self.model.addConstr(rate_var - assign_var <= 0, name=constr_name) 


    # (C) (3) The rate that each machine can run a process is limited by the machine's capabilities
    for m in factory.machines:
      for pname, runtime in m.blueprint.process_runtime_map.items():
        rate_var    = var[ilp.rate_var(m.machine_id, pname)]
        max_rate    = 1 / runtime
        constr_name = ilp.rate_constr(m.machine_id, pname) 
        self.model.addConstr(rate_var <= max_rate, name=constr_name)

    # (C) (4) Each cycle period, a machine must consume the same number of tokens the agents place in it's input buffer
    for m in factory.machines:
      if m.get_input() is None: continue
      cell = m.get_input()
      for z in m.blueprint.get_possible_input_tokens(procedure.processes.values()):
        
        num_agents_absorbed = gp.quicksum([var[ilp.absorption_var(cell, t, z)] for t in range(0, factory.timesteps)])
        constr_name         = ilp.absorb_constr(cell, m.machine_id, z)
        
        absorption_requirements = gp.quicksum(
          [var[ilp.rate_var(m.machine_id, pname)] * procedure.input_tokens(pname, z) * factory.timesteps
          for pname in m.blueprint.process_runtime_map])

        self.model.addConstr(num_agents_absorbed == absorption_requirements, name = constr_name)

    # (C) (5) Each cycle period, a machine must produce the same number of tokens that agents remove 
    #         from its output buffer
      for m in factory.machines:
        if m.get_output() is None: continue
        cell = m.get_output()
        for z in m.blueprint.get_possible_output_tokens(procedure.processes.values()):

          num_agents_emitted = gp.quicksum(var[ilp.emission_var(cell, t, z)] for t in range(0, factory.timesteps))
          constr_name = ilp.emit_constr(cell, m.machine_id, z)

          emision_requirements_sum = gp.quicksum(
            [var[ilp.rate_var(m.machine_id, pname)] * procedure.output_tokens(pname, z) * factory.timesteps 
            for pname in m.blueprint.process_runtime_map])

          self.model.addConstr(num_agents_emitted == emision_requirements_sum, name = constr_name)
          
    # (C) (6) At each time step an agent at a cell must either make a move action, a wait action (self-move), 
    #         or move into a machines input buffer
    for cell, t, z in product(factory.cell_graph.nodes, range(factory.timesteps), procedure.token_types):
      pos_var     = var[ilp.position_var(cell, t, z)]
      action_list = [var[ilp.movement_var(cell, ck, t, z)] for ck in factory.cell_graph.neighbors(cell)]
      constr_name = ilp.from_constr(cell, t, z)

      input_machine  = factory.cell_to_input_machine(cell) 
      processes      = procedure.processes.values()
      if input_machine is not None and z in input_machine.blueprint.get_possible_input_tokens(processes): 
        action_list.append(var[ilp.absorption_var(cell, t, z)])

      ### Negatokens
      if z == procedure.token_types.empty: 
        output_machine = factory.cell_to_output_machine(cell)
        if output_machine is not None: 
          action_list.append(var[ilp.absorption_var(cell, t, procedure.token_types.empty)])
      ### Negatokens 
        
      self.model.addConstr(pos_var == gp.quicksum(action_list), name=constr_name)

    # (C) (7) The number of tokens on c_i is equal to the number of tokens that moved there or were emitted 
    #         there the time step before
    for cell, t, z in product(factory.cell_graph.nodes, range(0, factory.timesteps), procedure.token_types):
      pos_var     = var[ilp.position_var(cell, (t + 1) % factory.timesteps, z)]
      action_list = [var[ilp.movement_var(ck, cell, t, z)] for ck in factory.cell_graph.neighbors(cell)]

      output_machine = factory.cell_to_output_machine(cell) 
      processes      = procedure.processes.values()
      if output_machine is not None and z in output_machine.blueprint.get_possible_output_tokens(processes): 
        action_list.append(var[ilp.emission_var(cell, t, z)])

      ### Negatokens
      if z == procedure.token_types.empty:
        input_machine  = factory.cell_to_input_machine(cell) 
        if input_machine is not None: 
          action_list.append(var[ilp.emission_var(cell, t, procedure.token_types.empty)])
      ### Negatokens
        
      self.model.addConstr(pos_var == gp.quicksum(action_list), name=constr_name)

    # (C) (8) At most one token can occupy a cell at a time
    for cell, t, in product(factory.cell_graph.nodes, range(0, factory.timesteps)):
      occupation_sum = gp.quicksum([var[ilp.position_var(cell, t, z)] for z in procedure.token_types])
      constr_name    = ilp.occupation_constr(cell, t)
      self.model.addConstr(occupation_sum <= 1, name=constr_name)

    # (C) (9) At most one token may traverse an edge at a time
    for (ci, cj), t in product(factory.cell_graph.edges, range(0, factory.timesteps)):

      move_sum = gp.quicksum([var[ilp.movement_var(ci, cj, t, z)] + var[ilp.movement_var(cj, ci, t, z)] 
                              for z in procedure.token_types])

      constr_name = ilp.move_constr(ci, cj, t)
      self.model.addConstr(move_sum <= 1, name=constr_name)

    # (C) (10) Whenever a machine emits a token, we must absorb a null token
    for (mi, t) in product(factory.machines, range(factory.timesteps)):
      if mi.get_output() is None: continue
      emit_sum = gp.quicksum(var[ilp.emission_var(mi.get_output(), t, z)]
                             for z in mi.blueprint.get_possible_output_tokens(procedure.processes.values()))

      absorb_null_var = var[ilp.absorption_var(mi.get_output(), t, procedure.token_types.empty)]

      constr_name = ilp.emit_empty_z_constr(mi.get_output(), mi.machine_id, t, z)
      self.model.addConstr(emit_sum == absorb_null_var, name=constr_name)

    # (C) (11) Whenever a machine absorbs a token, we must emit a null token
    for (mi, t) in product(factory.machines, range(factory.timesteps)):
      if mi.get_input() is None: continue
      absorb_sum = gp.quicksum(var[ilp.absorption_var(mi.get_input(), t, z)]
                               for z in mi.blueprint.get_possible_input_tokens(procedure.processes.values()))

      emit_null_var = var[ilp.emission_var(mi.get_input(),t, procedure.token_types.empty)]

      constr_name = ilp.absorb_empty_z_constr(mi.get_output(), mi.machine_id, t, z)
      self.model.addConstr(absorb_sum == emit_null_var, name=constr_name)

    # (C) (12) Constrain the number of cells that are equal to one at T = 0 to correspond to some limit
    constr_name = ilp.agent_limit_constr()
    agent_count = gp.quicksum([var[ilp.position_var(cell, 0, z)] for cell, z in product(factory.cell_graph.nodes, procedure.token_types)])
    self.model.addConstr(agent_count <= factory.agent_limit, name=constr_name)

    # (D) Set up objective
    utility = gp.quicksum([var[ilp.rate_var(m.machine_id, procedure.output_process.pname)] 
                           for m in factory.machines
                           if procedure.output_process.pname in m.blueprint.process_runtime_map])
    self.model.setObjective(utility, GRB.MAXIMIZE)
        
    self.model.update()
    self.var = var


  def get_objective(self):
    if self.model.getAttr(GRB.Attr.SolCount) > 0:
      return self.model.getObjective().getValue()
    return 0

  def print_objective(self):
    print(f"Running procedure with rate: {self.model.getObjective().getValue()}")


  def print_model(self, only_pos = False):
    print(self.model.getObjective())

    for constr in self.model.getConstrs():
      print(f"{constr.ConstrName}:  {self.constr_to_eq(constr, self.model)}")

    for v in self.model.getVars():
      if v.x == 0.0 and only_pos: continue
      print(f"{v.varName}: val:{v.x:.2f}")

  def export_plan(self, config, procedure, factory):

    plan = {"assignment": {},
            "rate":       {},
            "plan":       {t:[] for t in range(factory.timesteps)},
            # "emission":   {m.output_cell():[] for m in machines if m.output_cell() is not None}
            "timesteps":  factory.timesteps}

    for t in range(factory.timesteps):
      plan["plan"][t] = {ilp.convert_enum(z):[] for z in procedure.token_types}

    # Add assignments to plan
    for m in factory.machines:

      assigned_pnames = [pname for pname in m.blueprint.process_runtime_map 
                         if self.var[ilp.assign_var(m.machine_id, pname)].x > 1e-3]

      match len(assigned_pnames):
        case 0:
          plan["rate"][m.machine_id] = None
        case 1:
          plan["assignment"][m.machine_id] = ilp.convert_enum(assigned_pnames[0])
        case _:
          assert False, f"machine {m.machine_id} assigned multiple processes {assigned_pnames}"

    # Add rates to plan
    for m in factory.machines:

      run_pnames = [pname for pname in m.blueprint.process_runtime_map 
                    if self.var[ilp.rate_var(m.machine_id, pname)].x > 1e-3]

      match len(run_pnames):
        case 0:
          plan["rate"][m.machine_id] = None
        case 1:
          run_pname                = run_pnames[0]
          plan["rate"][m.machine_id] = self.var[ilp.rate_var(m.machine_id, run_pname)].x
        case _:
          assert False, f"run_pnames for machine {m.machine_id} neither 0 nor 1!"

    # Add token movement to plan
    for c, t, z in product(factory.cell_graph.nodes, range(factory.timesteps), procedure.token_types):
      var_name = ilp.position_var(c, t, z)
      z_name   = ilp.convert_enum(z)
      if self.var[var_name].x > 1e-3:
        plan["plan"][t][z_name].append([c.x, c.y])

    # Export plan
    with open(config["plan_path"], 'w', encoding='utf-8') as f:
      json.dump(plan, f, ensure_ascii=False, indent=4)