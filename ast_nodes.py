class AST:
    pass

class Program(AST):
    def __init__(self, name, block):
        self.name = name
        self.block = block

class Block(AST):
    def __init__(self, declarations, compound_statement):
        self.declarations = declarations
        self.compound_statement = compound_statement

class VarDecl(AST):
    def __init__(self, var_node, type_node):
        self.var_node = var_node
        self.type_node = type_node

class ConstDecl(AST):
    def __init__(self, const_node, value_node):
        self.const_node = const_node
        self.value_node = value_node

class ProcedureDecl(AST):
    def __init__(self, proc_name, params, block_node):
        self.proc_name = proc_name
        self.params = params
        self.block_node = block_node

class Param(AST):
    def __init__(self, var_node, type_node, is_var=False):
        self.var_node = var_node
        self.type_node = type_node
        self.is_var = is_var

class Type(AST):
    def __init__(self, token):
        self.token = token
        self.value = token.value

class Num(AST):
    def __init__(self, token):
        self.token = token
        self.value = token.value

class StringLiteral(AST):
    def __init__(self, token):
        self.token = token
        self.value = token.value

class BinOp(AST):
    def __init__(self, left, op, right):
        self.left = left
        self.op = op
        self.right = right
        self.eval_type = None

class UnaryOp(AST):
    def __init__(self, op, expr):
        self.op = op
        self.expr = expr
        self.eval_type = None

class Assign(AST):
    def __init__(self, left, op, right):
        self.left = left
        self.op = op
        self.right = right

class Variable(AST):
    def __init__(self, token):
        self.token = token
        self.value = token.value
        self.eval_type = None

class CompoundStatement(AST):
    def __init__(self):
        self.children = []

class If(AST):
    def __init__(self, condition, then_statement, else_statement=None):
        self.condition = condition
        self.then_statement = then_statement
        self.else_statement = else_statement

class While(AST):
    def __init__(self, condition, body_statement):
        self.condition = condition
        self.body_statement = body_statement

class ProcedureCall(AST):
    def __init__(self, proc_name, actual_params, token):
        self.proc_name = proc_name
        self.actual_params = actual_params
        self.token = token

class Read(AST):
    def __init__(self, variables):
        self.variables = variables

class Write(AST):
    def __init__(self, expressions):
        self.expressions = expressions

class NoOp(AST):
    pass