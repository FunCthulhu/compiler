# ir_generator.py
from ast_nodes import *
from intermediate_rep import *
from lexer import *

class IRGeneratorError(Exception):
    pass

class IRGenerator:
    def __init__(self):
        self.code = []
        self.temp_count = 0
        self.label_count = 0
        self.global_constants = {}

    def new_temp(self):
        name = f"t{self.temp_count}"
        self.temp_count += 1
        return name

    def new_label(self, hint="L"):
        name = f"{hint}{self.label_count}"
        self.label_count += 1
        return name

    def add_instruction(self, instruction):
        self.code.append(instruction)
        print(f"DEBUG_IR_ADD: {instruction}")

    def generate(self, node):
        self.visit(node)
        return self.code

    def visit(self, node):
        method_name = 'visit_' + type(node).__name__
        visitor = getattr(self, method_name, self.generic_visit)
        result = visitor(node)
        return result

    def generic_visit(self, node):
        raise IRGeneratorError(f"No visit_{type(node).__name__} method defined for node {type(node)} {node}")

    def visit_Program(self, node):
        if node.block.declarations:
            for declaration in node.block.declarations:
                self.visit(declaration)
        main_label = "__main_start"
        self.add_instruction(Label(main_label))
        self.add_instruction(EnterProc(node.name, []))
        if node.block.compound_statement:
            self.visit(node.block.compound_statement)
        self.add_instruction(ExitProc(node.name))
        self.add_instruction(Return())

    def visit_Block(self, node):
        pass

    def visit_VarDecl(self, node):
        pass

    def visit_ConstDecl(self, node):
        const_name = node.const_node.value
        const_value = node.value_node.value
        self.global_constants[const_name] = const_value

    def visit_ProcedureDecl(self, node):
        proc_label = node.proc_name
        self.add_instruction(Label(proc_label))
        param_names = [p.var_node.value for p in node.params]
        self.add_instruction(EnterProc(node.proc_name, param_names))
        if node.block_node.declarations:
            for declaration in node.block_node.declarations:
                self.visit(declaration)
        if node.block_node.compound_statement:
            self.visit(node.block_node.compound_statement)
        self.add_instruction(ExitProc(node.proc_name))
        self.add_instruction(Return())

    def visit_Param(self, node):
        pass

    def visit_Type(self, node):
        pass

    def visit_CompoundStatement(self, node):
        for child in node.children:
            self.visit(child)

    def visit_Assign(self, node):
        source_temp_name = self.visit(node.right)
        target_var_name = node.left.value
        self.add_instruction(StoreVar(target=target_var_name, source=source_temp_name))

    def visit_Variable(self, node):
        var_name = node.value
        target_temp_name = self.new_temp()
        if var_name in self.global_constants:
            const_value = self.global_constants[var_name]
            self.add_instruction(LoadConst(target=target_temp_name, value=const_value))
        else:
            self.add_instruction(LoadVar(target=target_temp_name, source=var_name))
        return target_temp_name

    def visit_Num(self, node):
        target_temp_name = self.new_temp()
        self.add_instruction(LoadConst(target=target_temp_name, value=node.value))
        return target_temp_name

    def visit_StringLiteral(self, node):
        target_temp_name = self.new_temp()
        self.add_instruction(LoadConst(target=target_temp_name, value=node.value))
        return target_temp_name

    def visit_BinOp(self, node):
        print(f"\nDEBUG_BINOP_ENTER: Op='{node.op.value}', Left Node Type: {type(node.left).__name__}, Right Node Type: {type(node.right).__name__}")

        left_operand_temp_name = self.visit(node.left)
        print(f"DEBUG_BINOP_LEFT_RESULT: Op='{node.op.value}', Left Temp Name = '{left_operand_temp_name}' (Type: {type(left_operand_temp_name)})")

        right_operand_temp_name = self.visit(node.right)
        print(f"DEBUG_BINOP_RIGHT_RESULT: Op='{node.op.value}', Right Temp Name = '{right_operand_temp_name}' (Type: {type(right_operand_temp_name)})")

        result_temp_name = self.new_temp()
        print(f"DEBUG_BINOP_TARGET_TEMP: Op='{node.op.value}', Target Temp Name = '{result_temp_name}'")

        op_str_map = {
            T_PLUS: '+', T_MINUS: '-', T_MUL: '*', T_REAL_DIV: '/', T_DIV: 'DIV',
            T_EQUAL: '==', T_NOT_EQUAL: '!=', T_LESS_THAN: '<', T_LESS_EQUAL: '<=',
            T_GREATER_THAN: '>', T_GREATER_EQUAL: '>=',
            T_AND: 'AND', T_OR: 'OR'
        }
        op_symbol_for_ir = op_str_map.get(node.op.type)

        if not op_symbol_for_ir:
            print(f"DEBUG_BINOP_ERROR: Unsupported operator token: {node.op.token} for node {node}")
            raise IRGeneratorError(f"Unsupported binary operator token: {node.op.token}")

        generated_instruction = BinOpIR(target=result_temp_name,
                                        op=op_symbol_for_ir,
                                        left=left_operand_temp_name,
                                        right=right_operand_temp_name)

        print(f"DEBUG_BINOP_GENERATED_INSTR: Op='{node.op.value}', Instruction = {generated_instruction}")

        self.add_instruction(generated_instruction)

        print(f"DEBUG_BINOP_RETURN: Op='{node.op.value}', Returning Temp Name = '{result_temp_name}'\n")
        return result_temp_name

    def visit_UnaryOp(self, node):
        operand_temp_name = self.visit(node.expr)
        result_temp_name = self.new_temp()
        op_str_map = { T_PLUS: '+', T_MINUS: '-', T_NOT: 'NOT' }
        op_symbol_for_ir = op_str_map.get(node.op.type)
        if not op_symbol_for_ir:
            raise IRGeneratorError(f"Unsupported unary operator token: {node.op.token}")
        self.add_instruction(UnaryOpIR(target=result_temp_name, op=op_symbol_for_ir, operand=operand_temp_name))
        return result_temp_name

    def visit_If(self, node):
        condition_temp_name = self.visit(node.condition)
        else_label = self.new_label("IF_ELSE")
        end_if_label = self.new_label("IF_END")
        jump_target_on_false = else_label if node.else_statement else end_if_label
        self.add_instruction(CondJump(condition_temp_name, jump_target_on_false))
        self.visit(node.then_statement)
        if node.else_statement:
            self.add_instruction(Jump(end_if_label))
            self.add_instruction(Label(else_label))
            self.visit(node.else_statement)
        self.add_instruction(Label(end_if_label))

    def visit_While(self, node):
        loop_start_label = self.new_label("WHILE_START")
        loop_end_label = self.new_label("WHILE_END")
        self.add_instruction(Label(loop_start_label))
        condition_temp_name = self.visit(node.condition)
        self.add_instruction(CondJump(condition_temp_name, loop_end_label))
        self.visit(node.body_statement)
        self.add_instruction(Jump(loop_start_label))
        self.add_instruction(Label(loop_end_label))

    def visit_ProcedureCall(self, node):
        arg_temp_names = []
        for param_node in node.actual_params:
            arg_temp_names.append(self.visit(param_node))
        self.add_instruction(Call(node.proc_name, arg_temp_names))

    def visit_Read(self, node):
        for var_node in node.variables:
            var_name_to_read_into = var_node.value
            self.add_instruction(ReadIR(target_var=var_name_to_read_into))

    def visit_Write(self, node):
        for expr_node in node.expressions:
            value_temp_name = self.visit(expr_node)
            self.add_instruction(WriteIR(source_var=value_temp_name))

    def visit_NoOp(self, node):
        pass