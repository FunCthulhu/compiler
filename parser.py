from lexer import *
from ast_nodes import *

class ParserError(Exception):
    pass

class Parser:
    def __init__(self, lexer):
        self.lexer = lexer
        self.current_token = self.lexer.get_next_token()

    def error(self, message=""):
        token = self.current_token
        raise ParserError(
            f"Parser error at token {token}. L{token.line}:C{token.column}. {message}"
        )

    def eat(self, token_type):
        if self.current_token.type == token_type:
            self.current_token = self.lexer.get_next_token()
        else:
            self.error(f"Expected token {token_type}, but got {self.current_token.type}")

    def program(self):
        prog_name = "DefaultProgram"
        if self.current_token.type == T_PROGRAM:
            self.eat(T_PROGRAM)
            prog_name_token = self.current_token
            self.eat(T_ID)
            prog_name = prog_name_token.value
            self.eat(T_SEMI)
        block_node = self.block()
        program_node = Program(prog_name, block_node)
        self.eat(T_DOT)
        if self.current_token.type != T_EOF:
            self.error("Expected EOF after program DOT")
        return program_node

    def block(self):
        declaration_nodes = self.declarations()
        compound_statement_node = self.compound_statement()
        node = Block(declaration_nodes, compound_statement_node)
        return node

    def declarations(self):
        declarations = []
        while self.current_token.type in (T_VAR, T_CONST, T_PROCEDURE):
            if self.current_token.type == T_VAR:
                declarations.extend(self.var_declaration_part())
            elif self.current_token.type == T_CONST:
                declarations.extend(self.const_declaration_part())
            elif self.current_token.type == T_PROCEDURE:
                declarations.append(self.procedure_declaration_part())
        return declarations

    def var_declaration_part(self):
        self.eat(T_VAR)
        decls = []
        if self.current_token.type == T_ID:
            decls.extend(self.var_declaration())
            while self.current_token.type == T_SEMI:
                self.eat(T_SEMI)
                if self.current_token.type != T_ID:
                    break
                decls.extend(self.var_declaration())
        return decls

    def var_declaration(self):
        var_nodes = [Variable(self.current_token)]
        self.eat(T_ID)
        while self.current_token.type == T_COMMA:
            self.eat(T_COMMA)
            var_nodes.append(Variable(self.current_token))
            self.eat(T_ID)
        self.eat(T_COLON)
        type_node = self.type_spec()
        var_declarations = [VarDecl(var_node, type_node) for var_node in var_nodes]
        return var_declarations

    def const_declaration_part(self):
        self.eat(T_CONST)
        decls = []
        if self.current_token.type == T_ID:
            decls.append(self.const_declaration())
            while self.current_token.type == T_SEMI:
                self.eat(T_SEMI)
                if self.current_token.type != T_ID:
                    break
                decls.append(self.const_declaration())
        return decls

    def const_declaration(self):
        const_node = Variable(self.current_token)
        self.eat(T_ID)
        self.eat(T_EQUAL)
        value_node = self.constant()
        return ConstDecl(const_node, value_node)

    def procedure_declaration_part(self):
        self.eat(T_PROCEDURE)
        proc_name = self.current_token.value
        self.eat(T_ID)
        params = []
        if self.current_token.type == T_LPAREN:
            self.eat(T_LPAREN)
            if self.current_token.type == T_ID:
                params = self.formal_parameter_list()
            self.eat(T_RPAREN)
        self.eat(T_SEMI)
        block_node = self.block()
        self.eat(T_SEMI)
        proc_decl = ProcedureDecl(proc_name, params, block_node)
        return proc_decl

    def formal_parameter_list(self):
        params = self.formal_parameters()
        while self.current_token.type == T_SEMI:
            self.eat(T_SEMI)
            params.extend(self.formal_parameters())
        return params

    def formal_parameters(self):
        param_nodes = [Variable(self.current_token)]
        self.eat(T_ID)
        while self.current_token.type == T_COMMA:
            self.eat(T_COMMA)
            param_nodes.append(Variable(self.current_token))
            self.eat(T_ID)
        self.eat(T_COLON)
        type_node = self.type_spec()
        params = [Param(param_node, type_node) for param_node in param_nodes]
        return params

    def type_spec(self):
        token = self.current_token
        if token.type == T_INTEGER:
            self.eat(T_INTEGER)
        elif token.type == T_REAL:
            self.eat(T_REAL)
        else:
            self.error(f"Expected type specifier (INTEGER or REAL), got {token.type}")
        return Type(token)

    def compound_statement(self):
        self.eat(T_BEGIN)
        nodes = self.statement_list()
        self.eat(T_END)
        root = CompoundStatement()
        for node in nodes:
            root.children.append(node)
        return root

    def statement_list(self):
        nodes = []
        if self.current_token.type not in (T_END, T_ELSE):
            nodes.append(self.statement())

        while self.current_token.type == T_SEMI:
            self.eat(T_SEMI)
            if self.current_token.type in (T_END, T_ELSE):
                break
            if self.current_token.type == T_EOF:
                self.error("Unexpected EOF after SEMI in statement list")
            if self.current_token.type not in (T_END, T_ELSE):
                nodes.append(self.statement())
            else:
                break
        return nodes

    def statement(self):
        token_type = self.current_token.type
        node = None

        if token_type == T_BEGIN:
            node = self.compound_statement()
        elif token_type == T_ID:
            id_token = self.current_token
            next_token_after_id = self.lexer.peek_token()

            if next_token_after_id.type == T_ASSIGN:
                node = self.assignment_statement()
            elif next_token_after_id.type == T_LPAREN or \
                    next_token_after_id.type in (T_SEMI, T_END, T_ELSE, T_DOT):
                node = self.procedure_call_statement()
            else:
                self.error(f"After ID '{id_token.value}', expected ASSIGN (:=), LPAREN ((), or a statement terminator (like ';') for parameterless procedure call, but got {next_token_after_id.type} ('{next_token_after_id.value}')")
        elif token_type == T_IF:
            node = self.if_statement()
        elif token_type == T_WHILE:
            node = self.while_statement()
        elif token_type == T_READ:
            node = self.read_statement()
        elif token_type == T_WRITE:
            node = self.write_statement()
        elif token_type in (T_END, T_ELSE, T_EOF):
            node = self.empty()
        elif token_type == T_SEMI:
            node = self.empty()
        else:
            self.error(f"Unexpected token at start of statement: {self.current_token}")

        if node is None:
            self.error(f"Failed to parse statement near token: {self.current_token}")
        return node

    def assignment_statement(self):
        left = self.variable()
        token_op = self.current_token
        self.eat(T_ASSIGN)
        right = self.expr() # Используем expr для правой части присваивания
        node = Assign(left, token_op, right)
        return node

    def procedure_call_statement(self):
        proc_token = self.current_token
        proc_name = proc_token.value
        self.eat(T_ID)

        actual_params = []
        if self.current_token.type == T_LPAREN:
            self.eat(T_LPAREN)
            if self.current_token.type != T_RPAREN:
                actual_params.append(self.expr())
                while self.current_token.type == T_COMMA:
                    self.eat(T_COMMA)
                    actual_params.append(self.expr())
            self.eat(T_RPAREN)

        node = ProcedureCall(proc_name, actual_params, proc_token)
        return node

    def if_statement(self):
        self.eat(T_IF)
        condition_node = self.condition()
        self.eat(T_THEN)
        then_statement_node = self.statement()
        else_statement_node = None
        if self.current_token.type == T_ELSE:
            self.eat(T_ELSE)
            else_statement_node = self.statement()
        return If(condition_node, then_statement_node, else_statement_node)

    def while_statement(self):
        self.eat(T_WHILE)
        condition_node = self.condition()
        self.eat(T_DO)
        body_node = self.statement()
        return While(condition_node, body_node)

    def read_statement(self):
        self.eat(T_READ)
        self.eat(T_LPAREN)
        variables = [self.variable()]
        while self.current_token.type == T_COMMA:
            self.eat(T_COMMA)
            variables.append(self.variable())
        self.eat(T_RPAREN)
        return Read(variables)

    def write_statement(self):
        self.eat(T_WRITE)
        self.eat(T_LPAREN)
        expressions = []
        if self.current_token.type != T_RPAREN:
            expressions.append(self.expr())
            while self.current_token.type == T_COMMA:
                self.eat(T_COMMA)
                expressions.append(self.expr())
        self.eat(T_RPAREN)
        return Write(expressions)

    def expr(self):
        return self.condition()

    def condition(self):
        node = self.and_expr()
        while self.current_token.type == T_OR:
            token = self.current_token
            self.eat(T_OR)
            node = BinOp(left=node, op=token, right=self.and_expr())
        return node

    def and_expr(self):
        node = self.not_expr()
        while self.current_token.type == T_AND:
            token = self.current_token
            self.eat(T_AND)
            node = BinOp(left=node, op=token, right=self.not_expr())
        return node

    def not_expr(self):
        if self.current_token.type == T_NOT:
            token = self.current_token
            self.eat(T_NOT)
            node = UnaryOp(op=token, expr=self.not_expr())
            return node
        else:
            return self.comparison_expr()

    def comparison_expr(self):
        node = self.additive_expr()

        rel_ops = (T_EQUAL, T_NOT_EQUAL, T_LESS_THAN, T_LESS_EQUAL, T_GREATER_THAN, T_GREATER_EQUAL)
        if self.current_token.type in rel_ops:
            op_token = self.current_token
            self.eat(op_token.type)
            right_node = self.additive_expr()
            node = BinOp(left=node, op=op_token, right=right_node)
        return node

    def additive_expr(self):
        node = self.multiplicative_expr()
        while self.current_token.type in (T_PLUS, T_MINUS):
            token = self.current_token
            self.eat(token.type)
            node = BinOp(left=node, op=token, right=self.multiplicative_expr())
        return node

    def multiplicative_expr(self):
        node = self.primary()
        while self.current_token.type in (T_MUL, T_REAL_DIV, T_DIV):
            token = self.current_token
            self.eat(token.type)
            node = BinOp(left=node, op=token, right=self.primary())
        return node

    def primary(self):
        token = self.current_token
        node = None

        if token.type == T_PLUS:
            op_token = token
            self.eat(T_PLUS)
            node = UnaryOp(op=op_token, expr=self.primary())
        elif token.type == T_MINUS:
            op_token = token
            self.eat(T_MINUS)
            node = UnaryOp(op=op_token, expr=self.primary())
        elif token.type == T_INTEGER_CONST:
            self.eat(T_INTEGER_CONST)
            node = Num(token)
        elif token.type == T_REAL_CONST:
            self.eat(T_REAL_CONST)
            node = Num(token)
        elif token.type == T_STRING_LITERAL:
            self.eat(T_STRING_LITERAL)
            node = StringLiteral(token)
        elif token.type == T_LPAREN:
            self.eat(T_LPAREN)
            node = self.condition()
            self.eat(T_RPAREN)
        elif token.type == T_ID:
            node = self.variable()
        else:
            self.error(f"Unexpected token in primary (factor): {token}")

        if node is None:
            self.error(f"Primary (factor) parsing failed unexpectedly near token {self.current_token}")
        return node

    def variable(self):
        node = Variable(self.current_token)
        self.eat(T_ID)
        return node

    def constant(self):
        token = self.current_token
        if token.type == T_INTEGER_CONST:
            self.eat(T_INTEGER_CONST)
            return Num(token)
        elif token.type == T_REAL_CONST:
            self.eat(T_REAL_CONST)
            return Num(token)
        elif token.type == T_STRING_LITERAL:
            self.eat(T_STRING_LITERAL)
            return StringLiteral(token)
        else:
            self.error(f"Expected INTEGER_CONST, REAL_CONST, or STRING_LITERAL for constant value, got {token.type}")

    def empty(self):
        return NoOp()

    def parse(self):
        node = self.program()
        if self.current_token.type != T_EOF:
            self.error("Expected EOF token at the end of parsing.")
        return node