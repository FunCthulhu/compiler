# intermediate_rep.py

class IRInstruction:
    def __str__(self):
        raise NotImplementedError

class Label(IRInstruction):
    def __init__(self, name):
        self.name = name
    def __str__(self):
        return f"{self.name}:"

class LoadConst(IRInstruction):
    def __init__(self, target, value):
        self.target = target
        self.value = value
    def __str__(self):
        return f"{self.target} = {repr(self.value)}"

class LoadVar(IRInstruction):
    def __init__(self, target, source):
        self.target = target
        self.source = source
    def __str__(self):
        return f"{self.target} = {self.source}"

class StoreVar(IRInstruction):
    def __init__(self, target, source):
        self.target = target
        self.source = source
    def __str__(self):
        return f"{self.target} = {self.source}"

class BinOpIR(IRInstruction):
    def __init__(self, target, op, left, right):
        self.target = target
        self.op = op
        self.left = left
        self.right = right
    def __str__(self):
        return f"{self.target} = {self.left} {self.op} {self.right}"

class UnaryOpIR(IRInstruction):
    def __init__(self, target, op, operand):
        self.target = target
        self.op = op
        self.operand = operand
    def __str__(self):
        return f"{self.target} = {self.op} {self.operand}"

class Jump(IRInstruction):
    def __init__(self, label_name):
        self.label_name = label_name
    def __str__(self):
        return f"JUMP {self.label_name}"

class CondJump(IRInstruction):
    def __init__(self, condition_var, false_label_name):
        self.condition_var = condition_var
        self.false_label_name = false_label_name
    def __str__(self):
        return f"IF_FALSE {self.condition_var} JUMP {self.false_label_name}"

class Call(IRInstruction):
    def __init__(self, proc_name, args, result_target=None):
        self.proc_name = proc_name
        self.args = args
        self.result_target = result_target
    def __str__(self):
        args_str = ', '.join(map(str, self.args))
        if self.result_target:
            return f"{self.result_target} = CALL {self.proc_name}({args_str})"
        return f"CALL {self.proc_name}({args_str})"

class Return(IRInstruction):
    def __init__(self, value_source_operand=None):
        self.value_source_operand = value_source_operand
    def __str__(self):
        if self.value_source_operand:
            return f"RETURN {self.value_source_operand}"
        return f"RETURN"

class ReadIR(IRInstruction):
    def __init__(self, target_var):
        self.target_var = target_var
    def __str__(self):
        return f"READ {self.target_var}"

class WriteIR(IRInstruction):
    def __init__(self, source_var):
        self.source_var = source_var
    def __str__(self):
        return f"WRITE {self.source_var}"

class EnterProc(IRInstruction):
    def __init__(self, proc_name, param_names):
        self.proc_name = proc_name
        self.param_names = param_names
    def __str__(self):
        params_str = ', '.join(self.param_names)
        return f"ENTER_PROC {self.proc_name}({params_str})"

class ExitProc(IRInstruction):
    def __init__(self, proc_name):
        self.proc_name = proc_name
    def __str__(self):
        return f"EXIT_PROC {self.proc_name}"

class NoOp(IRInstruction):
    def __str__(self):
        return "NOOP"