# symbol_table.py

class SymbolError(Exception):
    pass

class Symbol:
    def __init__(self, name, type=None):
        self.name = name
        self.type = type

    def __str__(self):
        type_name = getattr(self.type, 'name', None)
        return f"<{self.__class__.__name__}(name='{self.name}', type='{type_name}')>"

    __repr__ = __str__

class BuiltinTypeSymbol(Symbol):
    def __init__(self, name):
        super().__init__(name)

    def __str__(self):
        return f"<{self.__class__.__name__}(name='{self.name}')>"

class VarSymbol(Symbol):
    def __init__(self, name, type):
        super().__init__(name, type)

class ConstSymbol(Symbol):
    def __init__(self, name, type, value):
        super().__init__(name, type)
        self.value = value

    def __str__(self):
        type_name = getattr(self.type, 'name', None)
        return f"<{self.__class__.__name__}(name='{self.name}', type='{type_name}', value={repr(self.value)})>"

class ProcedureSymbol(Symbol):
    def __init__(self, name, params=None):
        super().__init__(name)
        self.params = params if params is not None else []

    def __str__(self):
        param_info = ', '.join(repr(p) for p in self.params)
        return f"<{self.__class__.__name__}(name='{self.name}', params=[{param_info}])>"

class SymbolTable:
    def __init__(self):
        self._symbols = {}

    def __str__(self):
        lines = [f"Symbols:"]
        for k,v in self._symbols.items():
            lines.append(f"  {k}: {v}")
        return '\n'.join(lines)

    __repr__ = __str__

    def define(self, symbol):
        if not isinstance(symbol, Symbol):
            raise TypeError("Can only define objects of type Symbol or its subclasses")
        self._symbols[symbol.name] = symbol

    def lookup(self, name, current_scope_only=False):
        symbol = self._symbols.get(name)
        return symbol