# semantic_analyzer.py
from ast_nodes import *
from symbol_table import SymbolTable, VarSymbol, ConstSymbol, ProcedureSymbol, BuiltinTypeSymbol, SymbolError
from lexer import *

class SemanticError(Exception):
    pass

class SemanticAnalyzer:
    def __init__(self):
        self.symtab = SymbolTable()
        self._init_builtins()

    def _init_builtins(self):
        self.symtab.define(BuiltinTypeSymbol('INTEGER'))
        self.symtab.define(BuiltinTypeSymbol('REAL'))

    def error(self, message, token):
        if token and hasattr(token, 'line') and hasattr(token, 'column'):
            location = f"[at L{token.line}:C{token.column}]"
        else:
            location = "[location unavailable]"
        raise SemanticError(
            f"Semantic Error: {message} {location}"
        )

    def visit(self, node):
        method_name = 'visit_' + type(node).__name__
        visitor = getattr(self, method_name, self.generic_visit)
        return visitor(node)

    def generic_visit(self, node):
        if node is None: return
        if isinstance(node, list):
            for item in node:
                if isinstance(item, AST): self.visit(item)
        else:
            for attr_name in dir(node):
                if not attr_name.startswith('_'):
                    attr_value = getattr(node, attr_name)
                    if isinstance(attr_value, AST): self.visit(attr_value)
                    elif isinstance(attr_value, list):
                        for item in attr_value:
                            if isinstance(item, AST): self.visit(item)

    def visit_Program(self, node):
        self.visit(node.block)

    def visit_Block(self, node):
        for declaration in node.declarations:
            self.visit(declaration)
        self.visit(node.compound_statement)

    def visit_VarDecl(self, node):
        type_name = node.type_node.value
        type_symbol = self.symtab.lookup(type_name)
        if type_symbol is None: self.error(f"Type '{type_name}' not defined", node.type_node.token); return
        var_name = node.var_node.value
        if self.symtab.lookup(var_name, current_scope_only=True): self.error(f"Duplicate identifier '{var_name}' found", node.var_node.token); return
        var_symbol = VarSymbol(var_name, type_symbol)
        self.symtab.define(var_symbol)
        node.var_node.symbol = var_symbol
        node.var_node.var_type = type_symbol

    def visit_ConstDecl(self, node):
        const_name = node.const_node.value
        if self.symtab.lookup(const_name, current_scope_only=True): self.error(f"Duplicate identifier '{const_name}' found", node.const_node.token); return
        self.visit(node.value_node)
        const_type_symbol = getattr(node.value_node, 'node_type', None)
        if const_type_symbol is None:
            value_token = getattr(node.value_node, 'token', node.const_node.token)
            self.error(f"Could not determine type of constant value for '{const_name}'", value_token); return
        const_symbol = ConstSymbol(const_name, const_type_symbol, node.value_node.value)
        self.symtab.define(const_symbol)
        node.const_node.symbol = const_symbol
        node.const_node.var_type = const_type_symbol

    def visit_ProcedureDecl(self, node):
        proc_name = node.proc_name
        proc_token = getattr(node, 'token', None)
        if not proc_token and node.params: proc_token = node.params[0].var_node.token
        elif not proc_token: proc_token = node.block_node
        if self.symtab.lookup(proc_name, current_scope_only=True):
            err_token = proc_token if proc_token else node
            self.error(f"Duplicate identifier '{proc_name}' found", err_token)
        proc_symbol = ProcedureSymbol(proc_name)
        self.symtab.define(proc_symbol)
        node.symbol = proc_symbol
        param_symbols = []
        if node.params:
            for param in node.params:
                self.visit(param)
                param_symbol = getattr(param.var_node, 'symbol', None)
                if param_symbol: param_symbols.append(param_symbol)
        proc_symbol.params = param_symbols
        self.visit(node.block_node)

    def visit_Param(self, node):
        type_name = node.type_node.value
        type_symbol = self.symtab.lookup(type_name)
        if type_symbol is None: self.error(f"Type '{type_name}' not defined", node.type_node.token); return
        var_name = node.var_node.value
        if self.symtab.lookup(var_name, current_scope_only=True): self.error(f"Duplicate identifier (parameter) '{var_name}' found", node.var_node.token); return
        var_symbol = VarSymbol(var_name, type_symbol)
        self.symtab.define(var_symbol)
        node.var_node.symbol = var_symbol
        node.var_node.var_type = type_symbol

    def visit_CompoundStatement(self, node):
        for child in node.children: self.visit(child)

    def visit_Assign(self, node):
        self.visit(node.right); right_type = getattr(node.right, 'node_type', None)
        self.visit(node.left); var_symbol = getattr(node.left, 'symbol', None)
        left_token = getattr(node.left, 'token', node.op)
        if var_symbol is None: self.error(f"Assignment target '{getattr(node.left,'value','<unknown>')}' not resolved", left_token); return
        if isinstance(var_symbol, ConstSymbol): self.error(f"Cannot assign to constant '{var_symbol.name}'", left_token); return
        if not isinstance(var_symbol, VarSymbol): self.error(f"Cannot assign to '{type(var_symbol).__name__}' identifier '{var_symbol.name}'", left_token); return
        var_type = getattr(var_symbol, 'type', None)
        if var_type is None: self.error(f"Cannot determine type of assignment target '{var_symbol.name}'", left_token); return
        if right_type is None: self.error(f"Cannot determine type of assigned expression", getattr(node.right, 'token', node.op)); return
        integer_type = self.symtab.lookup('INTEGER'); real_type = self.symtab.lookup('REAL')
        if var_type == right_type: pass
        elif var_type == real_type and right_type == integer_type: pass
        elif var_type == integer_type and right_type == real_type:
            # *** ИСПРАВЛЕНИЕ ПРИМЕНЕНО ЗДЕСЬ ***
            self.error(f"Type mismatch: Cannot assign REAL expression to INTEGER variable '{var_symbol.name}'", node.op)
        else: self.error(f"Type mismatch: Cannot assign type '{getattr(right_type, 'name', '?')}' to variable '{var_symbol.name}' of type '{getattr(var_type, 'name', '?')}'", node.op)
        node.node_type = var_type

    def visit_Variable(self, node):
        var_name = node.value; symbol = self.symtab.lookup(var_name)
        node.symbol = symbol
        if symbol is None: self.error(f"Identifier not found: '{var_name}'", node.token); node.node_type = None
        else: node.node_type = symbol.type if isinstance(symbol, (VarSymbol, ConstSymbol)) else None

    def visit_Num(self, node):
        if isinstance(node.value, int): node.node_type = self.symtab.lookup('INTEGER')
        elif isinstance(node.value, float): node.node_type = self.symtab.lookup('REAL')
        else: self.error("Internal error: Num node has non-numeric value", node.token); node.node_type = None

    def visit_StringLiteral(self, node):
        string_type = self.symtab.lookup('STRING')
        if string_type is None: string_type = BuiltinTypeSymbol('STRING'); self.symtab.define(string_type)
        node.node_type = string_type

    def visit_BinOp(self, node):
        self.visit(node.left); self.visit(node.right)
        left_type = getattr(node.left, 'node_type', None)
        right_type = getattr(node.right, 'node_type', None)
        op_type = node.op.type
        if left_type is None: self.error(f"Could not determine type of left operand for '{node.op.value}'", getattr(node.left, 'token', node.op)); node.node_type = None; return
        if right_type is None: self.error(f"Could not determine type of right operand for '{node.op.value}'", getattr(node.right, 'token', node.op)); node.node_type = None; return
        integer_type = self.symtab.lookup('INTEGER'); real_type = self.symtab.lookup('REAL'); string_type = self.symtab.lookup('STRING')
        result_type = None
        arithmetic_ops = (T_PLUS, T_MINUS, T_MUL, T_REAL_DIV)
        relational_ops = (T_LESS_THAN, T_GREATER_THAN, T_LESS_EQUAL, T_GREATER_EQUAL, T_EQUAL, T_NOT_EQUAL)
        logical_ops = (T_AND, T_OR)
        if op_type in arithmetic_ops:
            if left_type in (integer_type, real_type) and right_type in (integer_type, real_type): result_type = real_type if (left_type == real_type or right_type == real_type or op_type == T_REAL_DIV) else integer_type
            elif op_type == T_PLUS and left_type == string_type and right_type == string_type: result_type = string_type
            else: self.error(f"Operator '{node.op.value}' requires compatible numeric (or string for +) operands, got '{left_type.name}' and '{right_type.name}'", node.op)
        elif op_type == T_DIV:
            if left_type == integer_type and right_type == integer_type: result_type = integer_type
            else: self.error(f"Operator 'DIV' requires INTEGER operands, got '{left_type.name}' and '{right_type.name}'", node.op)
        elif op_type in relational_ops:
            if (left_type in (integer_type, real_type) and right_type in (integer_type, real_type)): result_type = integer_type
            elif left_type == string_type and right_type == string_type and op_type in (T_EQUAL, T_NOT_EQUAL): result_type = integer_type
            else: self.error(f"Cannot compare types '{left_type.name}' and '{right_type.name}' with '{node.op.value}'", node.op)
        elif op_type in logical_ops:
            if left_type == integer_type and right_type == integer_type: result_type = integer_type
            else: self.error(f"Logical operator '{node.op.value}' requires boolean (integer) operands, got '{left_type.name}' and '{right_type.name}'", node.op)
        else: self.error(f"Unsupported binary operator '{node.op.value}'", node.op)
        node.node_type = result_type

    def visit_UnaryOp(self, node):
        self.visit(node.expr)
        expr_type = getattr(node.expr, 'node_type', None)
        op_type = node.op.type
        if expr_type is None: self.error(f"Could not determine type of operand for unary '{node.op.value}'", getattr(node.expr, 'token', node.op)); node.node_type = None; return
        integer_type = self.symtab.lookup('INTEGER'); real_type = self.symtab.lookup('REAL')
        result_type = None
        if op_type in (T_PLUS, T_MINUS):
            if expr_type in (integer_type, real_type): result_type = expr_type
            else: self.error(f"Unary '{node.op.value}' requires numeric operand, got '{expr_type.name}'", node.op)
        elif op_type == T_NOT:
            if expr_type == integer_type: result_type = integer_type
            else: self.error(f"Operator 'NOT' requires boolean (integer) operand, got '{expr_type.name}'", node.op)
        else: self.error(f"Unsupported unary operator '{node.op.value}'", node.op)
        node.node_type = result_type

    def visit_ProcedureCall(self, node):
        proc_name = node.proc_name; proc_symbol = self.symtab.lookup(proc_name); proc_call_token = node.token
        if proc_symbol is None: self.error(f"Procedure '{proc_name}' not defined", proc_call_token); return
        if not isinstance(proc_symbol, ProcedureSymbol): self.error(f"Identifier '{proc_name}' is not a procedure", proc_call_token); return
        if len(node.actual_params) != len(proc_symbol.params): self.error(f"Procedure '{proc_name}': Expected {len(proc_symbol.params)} arguments, got {len(node.actual_params)}", proc_call_token); return
        integer_type = self.symtab.lookup('INTEGER'); real_type = self.symtab.lookup('REAL')
        for i, actual_param_node in enumerate(node.actual_params):
            self.visit(actual_param_node)
            actual_type = getattr(actual_param_node, 'node_type', None)
            param_error_token = getattr(actual_param_node, 'token', proc_call_token)
            if i < len(proc_symbol.params): formal_param_symbol = proc_symbol.params[i]; formal_type = getattr(formal_param_symbol, 'type', None)
            else: self.error(f"Internal error: Missing formal parameter info for arg {i+1} of '{proc_name}'", proc_call_token); continue
            if actual_type is None: self.error(f"Procedure '{proc_name}', argument {i+1}: Could not determine type of actual parameter", param_error_token); continue
            if formal_type is None: self.error(f"Internal error: Could not determine type of formal parameter '{formal_param_symbol.name}' for procedure '{proc_name}'", proc_call_token); continue
            if formal_type == actual_type: pass
            elif formal_type == real_type and actual_type == integer_type: pass
            else: self.error(f"Procedure '{proc_name}', argument {i+1}: Type mismatch. Expected '{getattr(formal_type,'name','?')}', got '{getattr(actual_type,'name','?')}'", param_error_token)
        node.node_type = None

    def visit_If(self, node):
        self.visit(node.condition); self.visit(node.then_statement)
        if node.else_statement: self.visit(node.else_statement)

    def visit_While(self, node):
        self.visit(node.condition); self.visit(node.body_statement)

    def visit_Read(self, node):
        for var_node in node.variables:
            self.visit(var_node)
            var_symbol = getattr(var_node, 'symbol', None)
            if isinstance(var_symbol, ConstSymbol): self.error(f"Cannot READ into constant '{var_node.value}'", var_node.token)

    def visit_Write(self, node):
        for expr_node in node.expressions: self.visit(expr_node)

    def visit_NoOp(self, node): pass
    def visit_Type(self, node): pass

    def analyze(self, tree):
        self.visit(tree)