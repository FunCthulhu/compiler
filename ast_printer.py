# ast_printer.py
from ast_nodes import *
import io

class ASTPrinter:
    def __init__(self):
        self.output_buffer = io.StringIO()

    def _p(self, indent_level, text):
        self.output_buffer.write(f"{'  ' * indent_level}{text}\n")

    def get_representation(self, node):
        self.output_buffer = io.StringIO()
        self._visit(node, 0)
        return self.output_buffer.getvalue()

    def _visit(self, node, indent=0):
        if node is None:
            self._p(indent, "NoneNode")
            return
        method_name = '_visit_' + type(node).__name__
        visitor = getattr(self, method_name, self._generic_visit)
        visitor(node, indent)

    def _generic_visit(self, node, indent=0):
        self._p(indent, f"{type(node).__name__} (Generic - Add specific visitor)")
        for attr_name in dir(node):
            if not attr_name.startswith('_'):
                attr_value = getattr(node, attr_name)
                if isinstance(attr_value, AST):
                    self._visit(attr_value, indent + 1)
                elif isinstance(attr_value, list) and attr_value and isinstance(attr_value[0], AST):
                    self._p(indent + 1, f"{attr_name}: [List]")
                    for item in attr_value:
                        self._visit(item, indent + 2)

    def _visit_Program(self, node, indent=0):
        self._p(indent, f"Program(name='{node.name}')")
        self._visit(node.block, indent + 1)

    def _visit_Block(self, node, indent=0):
        self._p(indent, "Block")
        self._p(indent + 1, "Declarations:")
        if node.declarations:
            for decl in node.declarations:
                self._visit(decl, indent + 2)
        else:
            self._p(indent + 2, "<None>")
        self._p(indent + 1, "Compound Statement:")
        self._visit(node.compound_statement, indent + 2)

    def _visit_VarDecl(self, node, indent=0):
        self._p(indent, "VarDecl:")
        self._visit(node.var_node, indent + 1)
        self._visit(node.type_node, indent + 1)

    def _visit_ConstDecl(self, node, indent=0):
        self._p(indent, "ConstDecl:")
        self._visit(node.const_node, indent + 1)
        self._visit(node.value_node, indent + 1)

    def _visit_ProcedureDecl(self, node, indent=0):
        self._p(indent, f"ProcedureDecl(name='{node.proc_name}')")
        self._p(indent + 1, "Parameters:")
        if node.params:
            for param in node.params:
                self._visit(param, indent + 2)
        else:
            self._p(indent + 2, "<None>")
        self._p(indent + 1, "Block:")
        self._visit(node.block_node, indent + 2)

    def _visit_Param(self, node, indent=0):
        self._p(indent, "Param:")
        self._visit(node.var_node, indent + 1)
        self._visit(node.type_node, indent + 1)

    def _visit_Type(self, node, indent=0):
        self._p(indent, f"Type(value='{node.value}')")

    def _visit_Num(self, node, indent=0):
        self._p(indent, f"Num(value={node.value})")

    def _visit_StringLiteral(self, node, indent=0):
        self._p(indent, f"StringLiteral(value='{node.value}')")

    def _visit_BinOp(self, node, indent=0):
        self._p(indent, f"BinOp(op='{node.op.value}')")
        self._visit(node.left, indent + 1)
        self._visit(node.right, indent + 1)

    def _visit_UnaryOp(self, node, indent=0):
        self._p(indent, f"UnaryOp(op='{node.op.value}')")
        self._visit(node.expr, indent + 1)

    def _visit_Assign(self, node, indent=0):
        self._p(indent, f"Assign(op='{node.op.value}')")
        self._visit(node.left, indent + 1)
        self._visit(node.right, indent + 1)

    def _visit_Variable(self, node, indent=0):
        self._p(indent, f"Variable(name='{node.value}')")

    def _visit_CompoundStatement(self, node, indent=0):
        self._p(indent, "CompoundStatement")
        for child in node.children:
            self._visit(child, indent + 1)

    def _visit_If(self, node, indent=0):
        self._p(indent, "If")
        self._p(indent + 1, "Condition:")
        self._visit(node.condition, indent + 2)
        self._p(indent + 1, "Then:")
        self._visit(node.then_statement, indent + 2)
        self._p(indent + 1, "Else:")
        if node.else_statement:
            self._visit(node.else_statement, indent + 2)
        else:
            self._p(indent + 2, "<None>")

    def _visit_While(self, node, indent=0):
        self._p(indent, "While")
        self._p(indent + 1, "Condition:")
        self._visit(node.condition, indent + 2)
        self._p(indent + 1, "Body:")
        self._visit(node.body_statement, indent + 2)

    def _visit_ProcedureCall(self, node, indent=0):
        self._p(indent, f"ProcedureCall(name='{node.proc_name}')")
        self._p(indent + 1, "Actual Parameters:")
        if node.actual_params:
            for param in node.actual_params:
                self._visit(param, indent + 2)
        else:
            self._p(indent + 2, "<None>")

    def _visit_Read(self, node, indent=0):
        self._p(indent, "Read")
        self._p(indent + 1, "Variables:")
        for var in node.variables:
            self._visit(var, indent + 2)

    def _visit_Write(self, node, indent=0):
        self._p(indent, "Write")
        self._p(indent + 1, "Expressions:")
        for expr in node.expressions:
            self._visit(expr, indent + 2)

    def _visit_NoOp(self, node, indent=0):
        self._p(indent, "NoOp")