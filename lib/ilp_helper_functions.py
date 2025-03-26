####################################
# Plan Generation Helper Functions #
####################################

# Converts a enum into a string
def convert_enum(enum):
  return str(enum).split(".")[1]

# True if process p to run on machine m
def assign_var(machine_id, pname):
  return f"run-m({machine_id})-p({convert_enum(pname)})"

# The rate that process p runs on machine m
def rate_var(machine_id, pname):
  assert type(machine_id) == int, 'Machine ID must be an int'
  return f"rate-m({machine_id})-p({convert_enum(pname)})"

def position_var(cell, time_step, token_type):
  return f"pos-({str(cell)}).t({time_step}).z({convert_enum(token_type)})"

def movement_var(cell1, cell2, time_step, token_type):
  return f"mov-({str(cell1)})-({str(cell2)}).t({time_step}).z({convert_enum(token_type)})"

def emission_var(cell, timestep, token_type):
  return f"em-({str(cell)}).t({timestep}).z({convert_enum(token_type)})"

def absorption_var(cell, timestep, token_type):
  return f"ab-({str(cell)}).t({timestep}).z({convert_enum(token_type)})"

def transport_var(token_id, m1_id, m2_id):
  """
  Represents the rate at which token_id is transported between m1 and m2
  """
  return f"m({m1_id})-transport-({convert_enum(token_id)})-to-m({m2_id}))"

# Ensures only one process assigned to machine m
def assign_constr(machine_id):
  return f"constr-assign-m({machine_id})"

# Ensures that the rate that machine m runs each of its processes is only non-zero if that process is assigned to 
# machine m
def bind_constr(mid, pname):
  return f"constr-bind-m({mid})-p-({convert_enum(pname)})"

# Limits the rate that machine m can run process p at
def rate_constr(mid, pname):
  return f"constr-rate-m({mid})-p-({convert_enum(pname)})"

# Absorb constraint
def absorb_constr(cell, machine_id, token_type):
  return f"constr-ab-({str(cell)})-m({machine_id}).z({convert_enum(token_type)})"

def emit_constr(cell, machine_id, token_type):
  return f"constr-em-{str(cell)}-m({machine_id}).z({convert_enum(token_type)})"

# For conveyor only
def consume_rate_constr(token_id, m1_id):
  return f"constr-consume-rate-m({m1_id})-t({token_id})"

# For conveyor only
def produce_rate_constr(token_id, m1_id):
  return f"constr-produce-rate-m({m1_id})-t({token_id})"

def from_constr(cell, timestep, token):
  return f"constr-from-{str(cell)}-t({timestep})-z({convert_enum(token)})"

def outgoing_constr(cell, time_step, token):
  return f"constr-to-({str(cell)})-t({time_step})-z({convert_enum(token)})"

def occupation_constr(cell, time_step):
  return f"constr-occupation-({str(cell)})-t({time_step})"

def move_constr(cell1, cell2, time_step):
  return f"constr-mv-({str(cell1)})-({str(cell2)})-t({time_step})"

def emit_empty_z_constr(cell, machine_id, time_step, token):
  return f"constr-emit-empty-z-{str(cell)}-m({machine_id})-t({time_step})-z({token})"

def absorb_empty_z_constr(cell, machine_id, time_step, token):
  return f"constr-absorb-empty-z-{str(cell)}-m({machine_id})-t({time_step})-z({token})"

def agent_limit_constr():
  return f"constr-agent-limit"

###########################
# Repair Helper Functions #
###########################
def displacement_x(machine):
  return f"dx-({machine.machine_id})"

def displacement_y(machine):
  return f"dy-({machine.machine_id})"

def indicator_var(m1, m2, cell1, cell2, indicator_type):
  return f"indicator-(m{m1.machine_id}-m{m2.machine_id})-({str(cell1)})-({str(cell2)})-({indicator_type})"

def indicator_constr(m1, m2, cell1, cell2, indicator_type):
  return f"constr-{indicator_var(m1, m2, cell1, cell2, indicator_type)}"

def adjacency_constr(m1, m2, cell1, cell2, indicator_type):
  return f"constr-adjacency-(m{m1.machine_id}-m{m2.machine_id})-({str(cell1)})-({str(cell2)})-({indicator_type})"

def boarder_constr(boarder_type, m, cell):
  return f"constr-boarder-{boarder_type}-m({m.machine_id})-c({str(cell)})"