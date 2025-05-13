# optimizer.py

from intermediate_rep import *

class Optimizer:
    def __init__(self, ir_code):
        self.ir_code = ir_code
        self.optimized_code = []

    def optimize(self):
        if not self.ir_code:
            return []

        previous_code_str = ""
        optimized_pass_code = list(self.ir_code)
        current_code_str = self._code_to_str(optimized_pass_code)

        max_passes = 10
        passes = 0

        while passes < max_passes:
            passes += 1
            previous_code_str = current_code_str

            known_constants_this_pass = {}
            for instr_scan in optimized_pass_code:
                if isinstance(instr_scan, LoadConst):
                    known_constants_this_pass[instr_scan.target] = instr_scan.value

            temp_code_after_folding = []
            for instr in optimized_pass_code:
                folded_instr = self._try_fold_instruction(instr, known_constants_this_pass)
                temp_code_after_folding.append(folded_instr)
                if isinstance(folded_instr, LoadConst) and folded_instr is not instr:
                    known_constants_this_pass[folded_instr.target] = folded_instr.value

            optimized_pass_code = temp_code_after_folding
            optimized_pass_code = self._dead_code_elimination(optimized_pass_code)

            current_code_str = self._code_to_str(optimized_pass_code)
            if previous_code_str == current_code_str:
                break

        self.optimized_code = optimized_pass_code

        initial_ir_str = self._code_to_str(self.ir_code)
        final_optimized_ir_str = self._code_to_str(self.optimized_code)

        if initial_ir_str == final_optimized_ir_str:
            print("[Optimizer] No effective optimizations performed.")
        else:
            print("[Optimizer] Optimization complete.")

        return self.optimized_code

    def _code_to_str(self, code_list):
        return "\n".join(map(str, code_list))

    def _is_literal_value(self, val):
        return isinstance(val, (int, float, bool, str))

    def _get_value_if_const(self, operand_name_or_literal, constants_map):
        if isinstance(operand_name_or_literal, str) and operand_name_or_literal in constants_map:
            return constants_map[operand_name_or_literal]

        if self._is_literal_value(operand_name_or_literal):
            if isinstance(operand_name_or_literal, str) and \
                    operand_name_or_literal.startswith('t') and \
                    operand_name_or_literal[1:].isdigit():
                return None
            return operand_name_or_literal

        return None

    def _try_fold_instruction(self, instr, known_constants):
        if isinstance(instr, BinOpIR):
            left_value = self._get_value_if_const(instr.left, known_constants)
            right_value = self._get_value_if_const(instr.right, known_constants)

            if left_value is not None and right_value is not None:
                try:
                    result = None
                    op = instr.op
                    if op == '+':
                        if isinstance(left_value, (int, float)) and isinstance(right_value, (int, float)):
                            result = left_value + right_value
                        elif isinstance(left_value, str) and isinstance(right_value, str):
                            result = left_value + right_value
                    elif op == '-':
                        if isinstance(left_value, (int, float)) and isinstance(right_value, (int, float)):
                            result = left_value - right_value
                    elif op == '*':
                        if isinstance(left_value, (int, float)) and isinstance(right_value, (int, float)):
                            result = left_value * right_value
                        elif isinstance(left_value, str) and isinstance(right_value, int):
                            result = left_value * right_value
                        elif isinstance(left_value, int) and isinstance(right_value, str):
                            result = right_value * left_value
                    elif op == '/':
                        if isinstance(left_value, (int, float)) and isinstance(right_value, (int, float)):
                            if right_value == 0: raise ZeroDivisionError()
                            result = float(left_value) / float(right_value)
                    elif op == 'DIV':
                        if isinstance(left_value, int) and isinstance(right_value, int):
                            if right_value == 0: raise ZeroDivisionError()
                            result = left_value // right_value
                    elif op == '==': result = left_value == right_value
                    elif op == '!=': result = left_value != right_value
                    elif op == '<':
                        if type(left_value) == type(right_value) or \
                                (isinstance(left_value, (int,float)) and isinstance(right_value, (int,float))):
                            result = left_value < right_value
                    elif op == '<=':
                        if type(left_value) == type(right_value) or \
                                (isinstance(left_value, (int,float)) and isinstance(right_value, (int,float))):
                            result = left_value <= right_value
                    elif op == '>':
                        if type(left_value) == type(right_value) or \
                                (isinstance(left_value, (int,float)) and isinstance(right_value, (int,float))):
                            result = left_value > right_value
                    elif op == '>=':
                        if type(left_value) == type(right_value) or \
                                (isinstance(left_value, (int,float)) and isinstance(right_value, (int,float))):
                            result = left_value >= right_value
                    elif op == 'AND': result = bool(left_value) and bool(right_value)
                    elif op == 'OR': result = bool(left_value) or bool(right_value)

                    if result is not None:
                        return LoadConst(instr.target, result)
                except (TypeError, ZeroDivisionError):
                    return instr
        elif isinstance(instr, UnaryOpIR):
            operand_value = self._get_value_if_const(instr.operand, known_constants)
            if operand_value is not None:
                try:
                    result = None
                    op = instr.op
                    if op == '-':
                        if isinstance(operand_value, (int, float)): result = -operand_value
                    elif op == '+':
                        if isinstance(operand_value, (int, float)): result = +operand_value
                    elif op == 'NOT':
                        result = not bool(operand_value)
                    if result is not None:
                        return LoadConst(instr.target, result)
                except TypeError:
                    return instr
        elif isinstance(instr, CondJump):
            cond_value = self._get_value_if_const(instr.condition_var, known_constants)
            if cond_value is not None:
                if bool(cond_value):
                    return NoOp()
                else:
                    return Jump(instr.false_label_name)

        return instr

    def _dead_code_elimination(self, code):
        code_no_noop = [instr for instr in code if not isinstance(instr, NoOp)]
        active_labels = set()
        label_positions = {}
        for i, instr in enumerate(code_no_noop):
            if isinstance(instr, Label): label_positions[instr.name] = i
            elif isinstance(instr, Jump): active_labels.add(instr.label_name)
            elif isinstance(instr, CondJump): active_labels.add(instr.false_label_name)
            elif isinstance(instr, Call): active_labels.add(instr.proc_name)
        if "__main_start" in label_positions: active_labels.add("__main_start")
        new_code_pass1 = []
        i = 0
        while i < len(code_no_noop):
            instr = code_no_noop[i]; new_code_pass1.append(instr)
            if isinstance(instr, (Jump, Return)):
                i += 1
                while i < len(code_no_noop):
                    next_instr = code_no_noop[i]
                    if isinstance(next_instr, Label) and next_instr.name in active_labels: i -=1; break
                    i += 1
            i += 1
        final_code = []
        for instr in new_code_pass1:
            if isinstance(instr, Label) and instr.name not in active_labels: continue
            final_code.append(instr)
        return final_code