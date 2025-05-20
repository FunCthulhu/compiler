from intermediate_rep import *
import sys

class InterpreterError(RuntimeError):
    pass

class Interpreter:
    def __init__(self, ir_code):
        self.ir_code = ir_code
        self.memory = {}
        self.labels = self._find_labels()
        entry_point = self.labels.get("__main_start")
        if entry_point is None:
            self.ip = 0
        else:
            self.ip = entry_point + 1
        self.call_stack = []

    def _find_labels(self):
        labels = {}
        for index, instruction in enumerate(self.ir_code):
            if isinstance(instruction, Label):
                if instruction.name in labels:
                    raise InterpreterError(f"Duplicate label found: {instruction.name}")
                labels[instruction.name] = index
        return labels

    def _get_value(self, operand_name):
        if self.call_stack:
            current_frame_locals = self.call_stack[-1]['locals']
            if operand_name in current_frame_locals:
                return current_frame_locals[operand_name]

        if operand_name in self.memory:
            return self.memory[operand_name]

        if operand_name in self.labels and \
                len(self.ir_code) > self.labels[operand_name]+1 and \
                isinstance(self.ir_code[self.labels[operand_name]+1], EnterProc):
            raise InterpreterError(f"Attempting to use procedure '{operand_name}' as a variable.")
        raise InterpreterError(f"Variable or temporary '{operand_name}' not found in current scope or global memory.")

    def _set_value(self, target_name, value):
        if self.call_stack:
            current_frame = self.call_stack[-1]
            current_frame_locals = current_frame['locals']

            current_frame_entry_ip = current_frame.get('entry_ip')
            is_param = False
            if current_frame_entry_ip is not None and \
                    current_frame_entry_ip < len(self.ir_code) and \
                    isinstance(self.ir_code[current_frame_entry_ip], EnterProc):
                proc_params = self.ir_code[current_frame_entry_ip].param_names
                if target_name in proc_params:
                    is_param = True

            if is_param or target_name in current_frame_locals:
                current_frame_locals[target_name] = value
                return
            else:
                current_frame_locals[target_name] = value
                return

        self.memory[target_name] = value

    def run(self, original_stdout_ref=sys.stdout, input_provider_func=None):
        while 0 <= self.ip < len(self.ir_code):
            instruction = self.ir_code[self.ip]
            jumped = False
            try:
                if isinstance(instruction, Label):
                    pass
                elif isinstance(instruction, EnterProc):
                    if self.call_stack:
                        pass
                elif isinstance(instruction, ExitProc):
                    pass
                elif isinstance(instruction, LoadConst):
                    self._set_value(instruction.target, instruction.value)
                elif isinstance(instruction, LoadVar):
                    value = self._get_value(instruction.source)
                    self._set_value(instruction.target, value)
                elif isinstance(instruction, StoreVar):
                    value_to_store = self._get_value(instruction.source)
                    self._set_value(instruction.target, value_to_store)
                elif isinstance(instruction, BinOpIR):
                    left_val = self._get_value(instruction.left)
                    right_val = self._get_value(instruction.right)
                    op = instruction.op
                    result = None
                    if op == '+':
                        if isinstance(left_val, (int, float)) and isinstance(right_val, (int, float)):
                            result = left_val + right_val
                        elif isinstance(left_val, str) and isinstance(right_val, str):
                            result = left_val + right_val
                        else:
                            raise InterpreterError(f"Type mismatch for operator '+': cannot add/concatenate {type(left_val).__name__} and {type(right_val).__name__}")
                    elif op == '-':
                        if not (isinstance(left_val, (int, float)) and isinstance(right_val, (int, float))):
                            raise InterpreterError(f"Type mismatch for operator '-': requires numeric operands, got {type(left_val).__name__} and {type(right_val).__name__}")
                        result = left_val - right_val
                    elif op == '*':
                        if isinstance(left_val, (int, float)) and isinstance(right_val, (int, float)):
                            result = left_val * right_val
                        elif isinstance(left_val, str) and isinstance(right_val, int):
                            result = left_val * right_val
                        elif isinstance(left_val, int) and isinstance(right_val, str):
                            result = right_val * left_val
                        else:
                            raise InterpreterError(f"Type mismatch for operator '*': cannot multiply {type(left_val).__name__} and {type(right_val).__name__}")
                    elif op == '/':
                        if not isinstance(left_val, (int, float)) or not isinstance(right_val, (int, float)):
                            raise InterpreterError(f"Real division requires numeric operands, got {type(left_val).__name__} for '{instruction.left}' and {type(right_val).__name__} for '{instruction.right}'")
                        if right_val == 0: raise InterpreterError("Division by zero")
                        result = float(left_val) / float(right_val)
                    elif op == 'DIV':
                        if not isinstance(left_val, int):
                            raise InterpreterError(f"Integer division requires integer dividend, got {type(left_val).__name__} for '{instruction.left}' ({left_val})")
                        if not isinstance(right_val, int):
                            raise InterpreterError(f"Integer division requires integer divisor, got {type(right_val).__name__} for '{instruction.right}' ({right_val})")
                        if right_val == 0: raise InterpreterError("Division by zero")
                        result = left_val // right_val
                    elif op == '==': result = left_val == right_val
                    elif op == '!=': result = left_val != right_val
                    elif op == '<': result = left_val < right_val
                    elif op == '<=': result = left_val <= right_val
                    elif op == '>': result = left_val > right_val
                    elif op == '>=': result = left_val >= right_val
                    elif op == 'AND': result = bool(left_val) and bool(right_val)
                    elif op == 'OR': result = bool(left_val) or bool(right_val)
                    else:
                        raise InterpreterError(f"Unknown binary operator: {op}")
                    self._set_value(instruction.target, result)
                elif isinstance(instruction, UnaryOpIR):
                    operand_val = self._get_value(instruction.operand)
                    op = instruction.op
                    result = None
                    if op == '-':
                        if not isinstance(operand_val, (int, float)):
                            raise InterpreterError(f"Unary minus requires numeric operand, got {type(operand_val).__name__}")
                        result = -operand_val
                    elif op == '+':
                        if not isinstance(operand_val, (int, float)):
                            raise InterpreterError(f"Unary plus requires numeric operand, got {type(operand_val).__name__}")
                        result = +operand_val
                    elif op == 'NOT': result = not bool(operand_val)
                    else:
                        raise InterpreterError(f"Unknown unary operator: {op}")
                    self._set_value(instruction.target, result)
                elif isinstance(instruction, Jump):
                    if instruction.label_name not in self.labels:
                        raise InterpreterError(f"Undefined label for JUMP: {instruction.label_name}")
                    self.ip = self.labels[instruction.label_name]
                    jumped = True
                elif isinstance(instruction, CondJump):
                    condition_val = self._get_value(instruction.condition_var)
                    if not bool(condition_val):
                        if instruction.false_label_name not in self.labels:
                            raise InterpreterError(f"Undefined label for CondJump: {instruction.false_label_name}")
                        self.ip = self.labels[instruction.false_label_name]
                        jumped = True
                elif isinstance(instruction, Call):
                    target_label = instruction.proc_name
                    target_ip = self.labels.get(target_label)
                    if target_ip is None:
                        raise InterpreterError(f"Undefined procedure called: {target_label}")

                    enter_proc_instr_index = target_ip + 1
                    if enter_proc_instr_index >= len(self.ir_code) or \
                            not isinstance(self.ir_code[enter_proc_instr_index], EnterProc):
                        raise InterpreterError(f"Label '{target_label}' does not point to a valid procedure entry (EnterProc).")

                    enter_proc_instr = self.ir_code[enter_proc_instr_index]

                    if len(instruction.args) != len(enter_proc_instr.param_names):
                        raise InterpreterError(f"Procedure '{target_label}': Argument count mismatch. Expected {len(enter_proc_instr.param_names)}, got {len(instruction.args)}.")

                    arg_values = [self._get_value(arg_temp) for arg_temp in instruction.args]

                    return_ip = self.ip + 1
                    new_frame = {
                        'name': target_label,
                        'return_ip': return_ip,
                        'entry_ip': enter_proc_instr_index,
                        'locals': {}
                    }
                    for name, value in zip(enter_proc_instr.param_names, arg_values):
                        new_frame['locals'][name] = value

                    self.call_stack.append(new_frame)
                    self.ip = enter_proc_instr_index
                    jumped = True
                elif isinstance(instruction, Return):
                    if not self.call_stack:
                        self.ip = len(self.ir_code)
                        jumped = True
                    else:
                        frame = self.call_stack.pop()
                        self.ip = frame['return_ip']
                        jumped = True
                elif isinstance(instruction, ReadIR):
                    current_stdout = sys.stdout
                    sys.stdout = original_stdout_ref

                    user_input_str = ""
                    value_read_for_set = None
                    prompt_message = f"Enter value for {instruction.target_var}: "

                    try:
                        if input_provider_func:
                            # ВЫЗОВ С АРГУМЕНТОМ prompt_message
                            user_input_str = input_provider_func(prompt_message)
                            if user_input_str is None:
                                raise EOFError("Input cancelled by user or GUI provider.")
                        else:
                            user_input_str = input(prompt_message)

                        try: value_read_for_set = int(user_input_str)
                        except ValueError:
                            try: value_read_for_set = float(user_input_str)
                            except ValueError: raise InterpreterError("Invalid input: Expected integer or real.")

                    except  EOFError as e:
                        raise InterpreterError(f"Input stream closed or cancelled: {e}")
                    finally:
                        sys.stdout = current_stdout

                    if value_read_for_set is not None:
                        self._set_value(instruction.target_var, value_read_for_set)

                elif isinstance(instruction, WriteIR):
                    value = self._get_value(instruction.source_var)
                    print(value, end='')
                else:
                    raise InterpreterError(f"Unknown IR instruction: {type(instruction).__name__}")
            except InterpreterError as e:
                if sys.stdout != original_stdout_ref:
                    sys.stdout = original_stdout_ref
                print(f"\nRuntime Error at IP={self.ip}, Instruction: {instruction}", file=sys.stderr)
                print(f"Error: {e}", file=sys.stderr)
                print("Memory:", self.memory, file=sys.stderr)
                print("Call Stack Frames (locals per frame):")
                for i, frame_data in enumerate(self.call_stack):
                    print(f"  Frame {i} ({frame_data.get('name', 'unknown')}): {frame_data.get('locals')}")
                if not self.call_stack: print("  <empty>")
                raise
            if not jumped:
                self.ip += 1