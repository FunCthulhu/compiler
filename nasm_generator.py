# nasm_generator.py
from intermediate_rep import *
import struct

class NASMGeneratorError(Exception):
    pass

class NASMGenerator:
    def __init__(self, ir_code, symbol_table=None):
        self.ir_code = ir_code
        self.symbol_table = symbol_table
        self._reset_state()

    def _reset_state(self):
        self.data_section_lines = []
        self.bss_section_lines = []
        self.text_section_lines = []
        self._string_literals_map = {}
        self._float_literals_map = {}
        self._next_str_lit_id = 0
        self._next_float_lit_id = 0
        self._global_vars = set()
        self._proc_stack_info = {}
        self._variable_type_hints = {}

    def _add_string_literal(self, value_str):
        if value_str not in self._string_literals_map:
            label = f"SL{self._next_str_lit_id}"
            self._next_str_lit_id += 1
            self._string_literals_map[value_str] = label
            escaped_bytes = [str(char_code) for char_code in value_str.encode('utf-8', errors='replace')]
            escaped_bytes.append("0")
            self.data_section_lines.append(f'  {label} db {", ".join(escaped_bytes)}')
        return self._string_literals_map[value_str]

    def _add_float_literal(self, value_float):
        hex_repr = struct.pack('>f', float(value_float)).hex()
        if value_float not in self._float_literals_map:
            label = f"FL{self._next_float_lit_id}"
            self._next_float_lit_id += 1
            self._float_literals_map[value_float] = label
            self.data_section_lines.append(f'  {label} dd 0x{hex_repr}')
        return self._float_literals_map[value_float]

    def _get_scope_for_var(self, var_name, current_proc_name):
        if not isinstance(var_name, str): return "__literal__"
        if var_name.startswith('t') and current_proc_name: return current_proc_name
        if current_proc_name:
            proc_info = self._proc_stack_info.get(current_proc_name)
            if proc_info and (var_name in proc_info['params'] or var_name in proc_info['locals_temps']):
                return current_proc_name
        if var_name in self._global_vars: return "__global__"
        if var_name in self._string_literals_map.values() or var_name in self._float_literals_map.values():
            return "__literal_label__"
        if var_name.startswith('t') and not current_proc_name: return "__global_temp__"
        return "__unknown__"

    def _update_type_hint(self, var_name, type_str, current_proc_name_context):
        scope_key = self._get_scope_for_var(var_name, current_proc_name_context)
        if scope_key == "__unknown__" and var_name.startswith('t') and current_proc_name_context:
            scope_key = current_proc_name_context
        if scope_key not in ["__literal__", "__literal_label__", "__unknown__"]:
            if scope_key not in self._variable_type_hints:
                self._variable_type_hints[scope_key] = {}
            self._variable_type_hints[scope_key][var_name] = type_str

    def _get_type_hint(self, var_name, current_proc_name_context):
        scope_key = self._get_scope_for_var(var_name, current_proc_name_context)
        return self._variable_type_hints.get(scope_key, {}).get(var_name)

    def _determine_operand_type(self, operand_name, current_proc_context, ir_instruction_index):
        hint = self._get_type_hint(operand_name, current_proc_context)
        if hint: return hint
        if isinstance(operand_name, str) and operand_name.startswith('t'):
            for k in range(ir_instruction_index - 1, -1, -1):
                prev_instr = self.ir_code[k]
                if hasattr(prev_instr, 'target') and prev_instr.target == operand_name:
                    if isinstance(prev_instr, LoadConst):
                        if isinstance(prev_instr.value, float): return 'REAL'
                        if isinstance(prev_instr.value, int): return 'INTEGER'
                        if isinstance(prev_instr.value, str): return 'STRING'
                    if isinstance(prev_instr, BinOpIR):
                        left_type = self._determine_operand_type(prev_instr.left, current_proc_context, k)
                        right_type = self._determine_operand_type(prev_instr.right, current_proc_context, k)
                        if prev_instr.op == '/' or left_type == 'REAL' or right_type == 'REAL': return 'REAL'
                        return 'INTEGER'
                    if isinstance(prev_instr, UnaryOpIR):
                        op_type = self._determine_operand_type(prev_instr.operand, current_proc_context, k)
                        if op_type == 'REAL' and prev_instr.op in ['+','-']: return 'REAL'
                        return 'INTEGER'
                    if isinstance(prev_instr, LoadVar):
                        return self._determine_operand_type(prev_instr.source, current_proc_context, k)
                    if isinstance(prev_instr, Call) and prev_instr.result_target == operand_name:
                        return self._get_type_hint(operand_name, current_proc_context) or 'INTEGER'
                    return None
            return None
        if isinstance(operand_name, str) and operand_name in self._float_literals_map.values(): return 'REAL'
        if isinstance(operand_name, str) and operand_name in self._string_literals_map.values(): return 'STRING'
        return 'INTEGER'

    def _is_float_operand_by_determined_type(self, operand_name, current_proc_context, ir_instruction_index):
        determined_type = self._determine_operand_type(operand_name, current_proc_context, ir_instruction_index)
        return determined_type == 'REAL'

    def _infer_and_store_type_hint_for_target(self, target_var, source_instr, current_proc_context, ir_instruction_index):
        inferred_type = None
        if isinstance(source_instr, LoadConst):
            if isinstance(source_instr.value, float): inferred_type = 'REAL'
            elif isinstance(source_instr.value, int): inferred_type = 'INTEGER'
            elif isinstance(source_instr.value, str): inferred_type = 'STRING'
        elif isinstance(source_instr, BinOpIR):
            left_type = self._determine_operand_type(source_instr.left, current_proc_context, ir_instruction_index -1)
            right_type = self._determine_operand_type(source_instr.right, current_proc_context, ir_instruction_index -1)
            if source_instr.op == '/' or left_type == 'REAL' or right_type == 'REAL':
                inferred_type = 'REAL'
            elif left_type == 'INTEGER' and right_type == 'INTEGER':
                inferred_type = 'INTEGER'
        elif isinstance(source_instr, UnaryOpIR):
            op_type = self._determine_operand_type(source_instr.operand, current_proc_context, ir_instruction_index -1)
            if op_type == 'REAL' and source_instr.op in ['+','-']: inferred_type = 'REAL'
            elif op_type == 'INTEGER': inferred_type = 'INTEGER'
        elif isinstance(source_instr, LoadVar):
            inferred_type = self._determine_operand_type(source_instr.source, current_proc_context, ir_instruction_index -1)
        elif isinstance(source_instr, Call) and source_instr.result_target == target_var :
            pass

        if inferred_type:
            self._update_type_hint(target_var, inferred_type, current_proc_context)

    def _get_operand_address_syntax(self, operand_name, current_proc_name):
        proc_info = self._proc_stack_info.get(current_proc_name)
        if proc_info:
            if operand_name in proc_info['locals_temps']:
                return f"ebp{proc_info['locals_temps'][operand_name]:+d}"
            if operand_name in proc_info['params']:
                param_index = proc_info['params'].index(operand_name)
                return f"ebp+{8 + param_index * 4}"
        if operand_name in self._global_vars:
            return operand_name
        if operand_name in self._string_literals_map.values() or \
                operand_name in self._float_literals_map.values():
            return operand_name
        raise NASMGeneratorError(f"_get_operand_address_syntax: No address for '{operand_name}' in '{current_proc_name}'.")

    def _get_operand_value_syntax(self, operand_name, current_proc_name):
        try:
            return str(int(operand_name))
        except ValueError:
            try:
                float(operand_name)
                if operand_name in self._float_literals_map.values():
                    return operand_name
            except ValueError:
                pass
        try:
            addr_syntax = self._get_operand_address_syntax(operand_name, current_proc_name)
            if addr_syntax.startswith("SL") or addr_syntax.startswith("FL"):
                return addr_syntax
            return f"[{addr_syntax}]"
        except NASMGeneratorError:
            raise NASMGeneratorError(f"_get_operand_value_syntax: Unknown operand '{operand_name}' in '{current_proc_name}'.")

    def _pre_scan_ir(self):
        current_proc_name_scan = None
        defined_in_any_proc_scope = set()
        proc_labels = {info.proc_name for info in self.ir_code if isinstance(info, EnterProc)}
        self._variable_type_hints.clear()
        for ir_idx_scan, instr_scan in enumerate(self.ir_code):
            if isinstance(instr_scan, EnterProc):
                current_proc_name_scan = instr_scan.proc_name
                self._proc_stack_info[current_proc_name_scan] = {
                    'params': list(instr_scan.param_names), 'locals_temps': {},
                    'frame_size': 0, 'next_local_offset': -4
                }
                defined_in_any_proc_scope.update(instr_scan.param_names)
            current_context_for_infer = current_proc_name_scan if current_proc_name_scan else "__global__"
            if hasattr(instr_scan, 'target') and isinstance(instr_scan.target, str):
                self._infer_and_store_type_hint_for_target(instr_scan.target, instr_scan, current_context_for_infer, ir_idx_scan)
            if hasattr(instr_scan, 'result_target') and isinstance(instr_scan.result_target, str) and isinstance(instr_scan, Call):
                self._infer_and_store_type_hint_for_target(instr_scan.result_target, instr_scan, current_context_for_infer, ir_idx_scan)
            if isinstance(instr_scan, StoreVar):
                source_type_for_store = self._determine_operand_type(instr_scan.source, current_context_for_infer, ir_idx_scan)
                if source_type_for_store:
                    self._update_type_hint(instr_scan.target, source_type_for_store, current_context_for_infer)
            if isinstance(instr_scan, ReadIR):
                if not self._get_type_hint(instr_scan.target_var, current_context_for_infer):
                    self._update_type_hint(instr_scan.target_var, 'INTEGER', current_context_for_infer)
            if current_proc_name_scan:
                proc_info = self._proc_stack_info[current_proc_name_scan]
                target_name_to_check = None
                if hasattr(instr_scan, 'target') and isinstance(instr_scan.target, str):
                    target_name_to_check = instr_scan.target
                elif hasattr(instr_scan, 'result_target') and isinstance(instr_scan.result_target, str):
                    target_name_to_check = instr_scan.result_target
                elif isinstance(instr_scan, ReadIR) and isinstance(instr_scan.target_var, str):
                    target_name_to_check = instr_scan.target_var
                if target_name_to_check and \
                        target_name_to_check not in proc_info['params'] and \
                        target_name_to_check not in proc_info['locals_temps']:
                    proc_info['locals_temps'][target_name_to_check] = proc_info['next_local_offset']
                    proc_info['next_local_offset'] -= 4
                    proc_info['frame_size'] += 4
                    if not target_name_to_check.startswith('t'):
                        defined_in_any_proc_scope.add(target_name_to_check)
            if isinstance(instr_scan, LoadConst):
                if isinstance(instr_scan.value, str): self._add_string_literal(instr_scan.value)
                elif isinstance(instr_scan.value, float): self._add_float_literal(instr_scan.value)
            if isinstance(instr_scan, ExitProc): current_proc_name_scan = None
        potential_globals = set()
        fmt_strings = {"fmt_int_write", "fmt_str_write", "fmt_newline", "fmt_int_read", "fmt_float_write", "fmt_float_read"}
        for instr in self.ir_code:
            operands_to_check = []
            if isinstance(instr, LoadVar): operands_to_check.append(instr.source)
            if isinstance(instr, StoreVar): operands_to_check.extend([instr.source, instr.target])
            if isinstance(instr, ReadIR): operands_to_check.append(instr.target_var)
            if isinstance(instr, BinOpIR): operands_to_check.extend([instr.left, instr.right])
            if isinstance(instr, UnaryOpIR): operands_to_check.append(instr.operand)
            if isinstance(instr, CondJump): operands_to_check.append(instr.condition_var)
            if isinstance(instr, WriteIR): operands_to_check.append(instr.source_var)
            if isinstance(instr, Call): operands_to_check.extend(instr.args)
            if hasattr(instr, 'result_target') and instr.result_target: operands_to_check.append(instr.result_target)
            for op_name in operands_to_check:
                if isinstance(op_name, str) and \
                        not op_name.startswith('t') and \
                        op_name not in defined_in_any_proc_scope and \
                        op_name not in proc_labels and \
                        op_name not in self._string_literals_map.values() and \
                        op_name not in self._float_literals_map.values() and \
                        op_name not in fmt_strings:
                    try: int(op_name); continue
                    except ValueError:
                        try: float(op_name); continue
                        except ValueError: potential_globals.add(op_name)
        self._global_vars = potential_globals

    def generate(self):
        self._reset_state()
        self._pre_scan_ir()

        self.data_section_lines.insert(0, '  fmt_float_read db "%lf", 0')
        self.data_section_lines.insert(0, '  fmt_float_write db "%.6g", 0')
        self.data_section_lines.insert(0, '  fmt_int_read db "%d", 0')
        self.data_section_lines.insert(0, '  fmt_newline db 10, 0')
        self.data_section_lines.insert(0, '  fmt_str_write db "%s", 0')
        self.data_section_lines.insert(0, '  fmt_int_write db "%d", 0')
        self.data_section_lines.insert(0, "SECTION .data")

        self.bss_section_lines.append("SECTION .bss")
        for g_var in self._global_vars:
            self.bss_section_lines.append(f'  {g_var} resd 1')

        self.text_section_lines.append("SECTION .text")
        self.text_section_lines.append("  global _main")
        self.text_section_lines.append("  extern _printf, _scanf, _exit")

        current_proc_name = None

        for ir_idx, instr in enumerate(self.ir_code):
            if isinstance(instr, Label):
                self.text_section_lines.append(f"{instr.name}:")
            elif isinstance(instr, EnterProc):
                current_proc_name = instr.proc_name
                proc_label = "_main" if instr.proc_name == "__main_start" else instr.proc_name
                self.text_section_lines.append(f"{proc_label}:")
                self.text_section_lines.append("    push ebp")
                self.text_section_lines.append("    mov ebp, esp")
                frame_size = self._proc_stack_info.get(current_proc_name, {}).get('frame_size', 0)
                if frame_size > 0:
                    self.text_section_lines.append(f"    sub esp, {frame_size}")
            elif isinstance(instr, ExitProc):
                proc_name_for_epilogue = instr.proc_name
                self.text_section_lines.append(f"  _{proc_name_for_epilogue}_epilogue:")
                self.text_section_lines.append("    mov esp, ebp")
                self.text_section_lines.append("    pop ebp")
                if proc_name_for_epilogue != "__main_start":
                    self.text_section_lines.append("    ret")
            elif isinstance(instr, LoadConst):
                target_val_syn = self._get_operand_value_syntax(instr.target, current_proc_name)
                if isinstance(instr.value, (int, bool)):
                    self.text_section_lines.append(f"    mov dword {target_val_syn}, {int(instr.value)}")
                elif isinstance(instr.value, str):
                    str_label = self._string_literals_map[instr.value]
                    self.text_section_lines.append(f"    mov dword {target_val_syn}, {str_label}")
                elif isinstance(instr.value, float):
                    float_label = self._float_literals_map[instr.value]
                    self.text_section_lines.append(f"    fld dword [{float_label}]")
                    self.text_section_lines.append(f"    fstp dword {target_val_syn}")
            elif isinstance(instr, (LoadVar, StoreVar)):
                source_op_name = instr.source
                target_op_name = instr.target
                src_val_syn = self._get_operand_value_syntax(source_op_name, current_proc_name)
                trg_val_syn = self._get_operand_value_syntax(target_op_name, current_proc_name)
                is_float_op = self._is_float_operand_by_determined_type(source_op_name, current_proc_name, ir_idx)
                if is_float_op:
                    self.text_section_lines.append(f"    fld dword {src_val_syn}")
                    self.text_section_lines.append(f"    fstp dword {trg_val_syn}")
                else:
                    self.text_section_lines.append(f"    mov eax, {src_val_syn}")
                    self.text_section_lines.append(f"    mov {trg_val_syn}, eax")
            elif isinstance(instr, BinOpIR):
                res_val_syn = self._get_operand_value_syntax(instr.target, current_proc_name)
                left_op_name = instr.left
                right_op_name = instr.right
                left_val_syn = self._get_operand_value_syntax(left_op_name, current_proc_name)
                right_val_syn = self._get_operand_value_syntax(right_op_name, current_proc_name)
                left_type = self._determine_operand_type(left_op_name, current_proc_name, ir_idx)
                right_type = self._determine_operand_type(right_op_name, current_proc_name, ir_idx)
                op_produces_float = (instr.op == '/') or (left_type == 'REAL') or (right_type == 'REAL')
                if instr.op in ['+', '-', '*', '/'] and op_produces_float:
                    if left_type == 'REAL':
                        self.text_section_lines.append(f"    fld dword {left_val_syn}")
                    elif left_type == 'INTEGER':
                        self.text_section_lines.append(f"    fild dword {left_val_syn}")
                    else:
                        self.text_section_lines.append(f"    fldz")
                    if right_type == 'REAL':
                        self.text_section_lines.append(f"    fld dword {right_val_syn}")
                    elif right_type == 'INTEGER':
                        self.text_section_lines.append(f"    fild dword {right_val_syn}")
                    else:
                        self.text_section_lines.append(f"    fldz")
                    if instr.op == '+': self.text_section_lines.append("    faddp st1, st0")
                    elif instr.op == '-': self.text_section_lines.append("    fsubp st1, st0")
                    elif instr.op == '*': self.text_section_lines.append("    fmulp st1, st0")
                    elif instr.op == '/':
                        self.text_section_lines.append(f"    ftst")
                        self.text_section_lines.append(f"    fstsw ax")
                        self.text_section_lines.append(f"    sahf")
                        zero_label = f"DIV_BY_ZERO_ERR_{ir_idx}"
                        ok_label = f"DIV_OK_{ir_idx}"
                        self.text_section_lines.append(f"    jz {zero_label}")
                        self.text_section_lines.append(f"    fdivp st1, st0")
                        self.text_section_lines.append(f"    jmp {ok_label}")
                        self.text_section_lines.append(f"{zero_label}:")
                        self.text_section_lines.append(f"    fstp st0")
                        self.text_section_lines.append(f"    fstp st0")
                        self.text_section_lines.append(f"    fldz")
                        self.text_section_lines.append(f"{ok_label}:")
                    self.text_section_lines.append(f"    fstp dword {res_val_syn}")
                else:
                    if left_type == 'REAL' or right_type == 'REAL':
                        self.text_section_lines.append(f"    mov dword {res_val_syn}, 0")
                    else:
                        self.text_section_lines.append(f"    mov eax, {left_val_syn}")
                        self.text_section_lines.append(f"    mov ebx, {right_val_syn}")
                        op_map_int = {
                            '+': "add eax, ebx", '-': "sub eax, ebx", '*': "imul eax, ebx",
                            'DIV': "cdq\n    idiv ebx",
                            '==': "cmp eax, ebx\n    sete al\n    movzx eax, al",
                            '!=': "cmp eax, ebx\n    setne al\n    movzx eax, al",
                            '<': "cmp eax, ebx\n    setl al\n    movzx eax, al",
                            '<=': "cmp eax, ebx\n    setle al\n    movzx eax, al",
                            '>': "cmp eax, ebx\n    setg al\n    movzx eax, al",
                            '>=': "cmp eax, ebx\n    setge al\n    movzx eax, al",
                            'AND': "and eax, ebx", 'OR': "or eax, ebx",
                        }
                        if instr.op in op_map_int:
                            self.text_section_lines.append(f"    {op_map_int[instr.op]}")
                            if instr.op in ['AND', 'OR']:
                                self.text_section_lines.append(f"    test eax, eax\n    setne al\n    movzx eax, al")
                        else: self.text_section_lines.append(f"    ; ERR: Unsupported BinOp for INTEGER: {instr.op}")
                        self.text_section_lines.append(f"    mov {res_val_syn}, eax")
            elif isinstance(instr, UnaryOpIR):
                operand_val_syn = self._get_operand_value_syntax(instr.operand, current_proc_name)
                target_val_syn = self._get_operand_value_syntax(instr.target, current_proc_name)
                op_is_float = self._is_float_operand_by_determined_type(instr.operand, current_proc_name, ir_idx)
                if instr.op == '-' and op_is_float:
                    self.text_section_lines.append(f"    fld dword {operand_val_syn}")
                    self.text_section_lines.append(f"    fchs")
                    self.text_section_lines.append(f"    fstp dword {target_val_syn}")
                else:
                    self.text_section_lines.append(f"    mov eax, {operand_val_syn}")
                    if instr.op == '-': self.text_section_lines.append("    neg eax")
                    elif instr.op == '+': pass
                    elif instr.op == 'NOT':
                        self.text_section_lines.append("    test eax, eax\n    sete al\n    movzx eax, al")
                    else: self.text_section_lines.append(f"    ; ERR: Unsupported UnaryOp: {instr.op}")
                    self.text_section_lines.append(f"    mov {target_val_syn}, eax")
            elif isinstance(instr, Jump):
                self.text_section_lines.append(f"    jmp {instr.label_name}")
            elif isinstance(instr, CondJump):
                cond_val_syn = self._get_operand_value_syntax(instr.condition_var, current_proc_name)
                self.text_section_lines.append(f"    mov eax, {cond_val_syn}")
                self.text_section_lines.append(f"    test eax, eax")
                self.text_section_lines.append(f"    jz {instr.false_label_name}")
            elif isinstance(instr, Call):
                num_args_pushed_bytes = 0
                if instr.args:
                    for arg_temp_name in reversed(instr.args):
                        arg_val_syn = self._get_operand_value_syntax(arg_temp_name, current_proc_name)
                        is_float_arg = self._is_float_operand_by_determined_type(arg_temp_name, current_proc_name, ir_idx)
                        if is_float_arg:
                            self.text_section_lines.append(f"    fld dword {arg_val_syn}")
                            self.text_section_lines.append(f"    sub esp, 8")
                            self.text_section_lines.append(f"    fstp qword [esp]")
                            num_args_pushed_bytes += 8
                        else:
                            self.text_section_lines.append(f"    push dword {arg_val_syn}")
                            num_args_pushed_bytes += 4
                proc_to_call_label = "_main" if instr.proc_name == "__main_start" else instr.proc_name
                self.text_section_lines.append(f"    call {proc_to_call_label}")
                if num_args_pushed_bytes > 0:
                    self.text_section_lines.append(f"    add esp, {num_args_pushed_bytes}")
                if instr.result_target:
                    res_target_val_syn = self._get_operand_value_syntax(instr.result_target, current_proc_name)
                    is_float_return = self._get_type_hint(instr.result_target, current_proc_name) == 'REAL'
                    if is_float_return:
                        self.text_section_lines.append(f"    fstp dword {res_target_val_syn}")
                    else:
                        self.text_section_lines.append(f"    mov {res_target_val_syn}, eax")
                    self._update_type_hint(instr.result_target, 'REAL' if is_float_return else 'INTEGER', current_proc_name)
            elif isinstance(instr, Return):
                if current_proc_name == "__main_start":
                    self.text_section_lines.append("    push 0")
                    self.text_section_lines.append("    call _exit")
                elif current_proc_name:
                    if instr.value_source_operand:
                        ret_val_syn = self._get_operand_value_syntax(instr.value_source_operand, current_proc_name)
                        is_float_ret = self._is_float_operand_by_determined_type(instr.value_source_operand, current_proc_name, ir_idx)
                        if is_float_ret:
                            self.text_section_lines.append(f"    fld dword {ret_val_syn}")
                        else:
                            self.text_section_lines.append(f"    mov eax, {ret_val_syn}")
                    self.text_section_lines.append(f"    jmp _{current_proc_name}_epilogue")
                else: self.text_section_lines.append("    ; ERR: Return outside procedure context")
            elif isinstance(instr, ReadIR):
                var_addr_syn_no_brackets = self._get_operand_address_syntax(instr.target_var, current_proc_name)
                is_reading_float = self._get_type_hint(instr.target_var, current_proc_name) == 'REAL'
                self.text_section_lines.append(f"    lea eax, [{var_addr_syn_no_brackets}]")
                self.text_section_lines.append(f"    push eax")
                format_str_label = "fmt_float_read" if is_reading_float else "fmt_int_read"
                self.text_section_lines.append(f"    push {format_str_label}")
                self.text_section_lines.append(f"    call _scanf")
                self.text_section_lines.append(f"    add esp, 8")
                self._update_type_hint(instr.target_var, 'REAL' if is_reading_float else 'INTEGER', current_proc_name)
            elif isinstance(instr, WriteIR):
                source_val_syn = self._get_operand_value_syntax(instr.source_var, current_proc_name)
                is_float_val = self._is_float_operand_by_determined_type(instr.source_var, current_proc_name, ir_idx)
                is_string_val = False
                if not is_float_val:
                    if (isinstance(instr.source_var, str) and instr.source_var.startswith("SL") and instr.source_var in self._string_literals_map.values()) or \
                            self._get_type_hint(instr.source_var, current_proc_name) == 'STRING':
                        is_string_val = True
                stack_cleanup_size = 8
                if is_string_val:
                    self.text_section_lines.append(f"    push dword {source_val_syn}")
                    self.text_section_lines.append(f"    push fmt_str_write")
                elif is_float_val:
                    self.text_section_lines.append(f"    fld dword {source_val_syn}")
                    self.text_section_lines.append(f"    sub esp, 8")
                    self.text_section_lines.append(f"    fstp qword [esp]")
                    self.text_section_lines.append(f"    push fmt_float_write")
                    stack_cleanup_size = 12
                else:
                    self.text_section_lines.append(f"    push dword {source_val_syn}")
                    self.text_section_lines.append(f"    push fmt_int_write")
                self.text_section_lines.append(f"    call _printf")
                self.text_section_lines.append(f"    add esp, {stack_cleanup_size}")
            elif isinstance(instr, NoOp):
                self.text_section_lines.append("    nop")
            else:
                self.text_section_lines.append(f"    ; ERR: Unknown IR: {type(instr).__name__}")

        full_nasm_code = []
        full_nasm_code.extend(self.data_section_lines)
        full_nasm_code.append("")
        full_nasm_code.extend(self.bss_section_lines)
        full_nasm_code.append("")
        full_nasm_code.extend(self.text_section_lines)
        return "\n".join(full_nasm_code)