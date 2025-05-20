# main_logic.py
import sys
import traceback
import io
import os

from lexer import Lexer, LexerError
from parser import Parser, ParserError
from semantic_analyzer import SemanticAnalyzer, SemanticError
from ir_generator import IRGenerator, IRGeneratorError
from optimizer import Optimizer
from interpreter import Interpreter, InterpreterError
from ast_printer import ASTPrinter
from nasm_generator import NASMGenerator, NASMGeneratorError
from nasm_compiler_linker import compile_nasm_and_link_exe, CompilationError

COMPILER_STAGES_OUTPUT = io.StringIO()

def print_to_compiler_output(*args, **kwargs):
    print(*args, **kwargs, file=COMPILER_STAGES_OUTPUT)

def compile_and_run_pascal(source_code_str,
                           interpreter_output_target_file,
                           exe_output_target_file,
                           gui_input_provider=None):
    global COMPILER_STAGES_OUTPUT
    COMPILER_STAGES_OUTPUT = io.StringIO()

    lexer = None
    ast = None
    # sem_analyzer = None
    ir_code = None
    optimized_ir_code = None
    interpreter = None
    nasm_generator = None
    nasm_code_output_str = None

    original_stdout = sys.stdout
    interpreter_output_handle = None

    interpreter_successful = False
    exe_generation_successful = False

    try:
        print_to_compiler_output("--- Запуск компилятора ---")
        print_to_compiler_output("--- Исходный код ---")
        print_to_compiler_output(source_code_str)
        print_to_compiler_output("--------------------")

        print_to_compiler_output("\n[Этап 1] Лексический анализ...")
        lexer = Lexer(source_code_str)
        print_to_compiler_output("Лексический анализ завершен.")

        print_to_compiler_output("\n[Этап 2] Синтаксический анализ (Парсинг)...")
        parser = Parser(lexer)
        ast = parser.parse()
        print_to_compiler_output("Парсинг успешно завершен.")

        print_to_compiler_output("\n--- Абстрактное Синтаксическое Дерево (AST) ---")
        ast_printer = ASTPrinter()
        ast_representation = ast_printer.get_representation(ast)
        print_to_compiler_output(ast_representation)
        print_to_compiler_output("---------------------------------------------")

        print_to_compiler_output("\n[Этап X] Семантический анализ...")
        sem_analyzer = SemanticAnalyzer()
        sem_analyzer.analyze(ast)
        print_to_compiler_output("Семантический анализ успешно завершен.")
        symtab_for_nasm = sem_analyzer.symtab

        print_to_compiler_output("\n[Этап 3] Генерация промежуточного представления (IR)...")
        ir_gen = IRGenerator()
        ir_code = ir_gen.generate(ast)
        print_to_compiler_output("Генерация IR успешно завершена.")

        print_to_compiler_output("\n--- Промежуточное представление (IR) ---")
        if ir_code:
            for i, instr in enumerate(ir_code):
                print_to_compiler_output(f"{i:03d}: {instr}")
        else:
            print_to_compiler_output("<IR не сгенерирован>")
        print_to_compiler_output("--------------------------------------")

        print_to_compiler_output("\n[Этап 4] Оптимизация IR...")
        optimizer = Optimizer(list(ir_code) if ir_code else [])
        optimized_ir_code = optimizer.optimize()
        initial_ir_len = len(ir_code) if ir_code else 0
        optimized_ir_len = len(optimized_ir_code) if optimized_ir_code else 0

        if optimized_ir_len < initial_ir_len and optimized_ir_code is not None:
            print_to_compiler_output(f"Оптимизация применена. IR сокращен с {initial_ir_len} до {optimized_ir_len} инструкций.")
            print_to_compiler_output("\n--- Оптимизированный IR ---")
            for i, instr in enumerate(optimized_ir_code):
                print_to_compiler_output(f"{i:03d}: {instr}")
            print_to_compiler_output("---------------------------")
        else:
            print_to_compiler_output("Эффективных оптимизаций не выполнено или оптимизатор вернул исходный список.")
            if optimized_ir_code is None and ir_code is not None:
                optimized_ir_code = list(ir_code)
            elif optimized_ir_code is None and ir_code is None:
                optimized_ir_code = []

        if optimized_ir_code:
            print_to_compiler_output("\n[Этап 5a] Интерпретация...")
            print_to_compiler_output(f"Вывод интерпретатора (операторы WRITE) будет направлен в: {interpreter_output_target_file}")
            try:
                interpreter_output_handle = open(interpreter_output_target_file, 'w', encoding='utf-8')
                sys.stdout = interpreter_output_handle
                interpreter = Interpreter(list(optimized_ir_code))
                interpreter.run(original_stdout_ref=original_stdout, input_provider_func=gui_input_provider)
                interpreter_successful = True
                print_to_compiler_output(f"\nВыполнение интерпретатором завершено. Вывод в {interpreter_output_target_file}")
            except InterpreterError as ie:
                sys.stdout = original_stdout
                print_to_compiler_output(f"\n--- Ошибка времени выполнения интерпретатора ---")
                print_to_compiler_output(f"Ошибка: {str(ie)}")
                interpreter_successful = False
            except Exception as e_interp:
                sys.stdout = original_stdout
                print_to_compiler_output(f"\n--- Непредвиденная ошибка во время интерпретации ---")
                print_to_compiler_output(f"Ошибка: {str(e_interp)}")
                traceback.print_exc(file=COMPILER_STAGES_OUTPUT)
                interpreter_successful = False
            finally:
                if interpreter_output_handle:
                    interpreter_output_handle.close()
                sys.stdout = original_stdout
        else:
            print_to_compiler_output("Нет IR-кода для интерпретации.")
            interpreter_successful = False

        if optimized_ir_code:
            print_to_compiler_output("\n[Этап 5b] Генерация NASM-кода...")
            try:
                # symtab_ref = symtab_for_nasm if 'symtab_for_nasm' in locals() else None
                nasm_generator = NASMGenerator(optimized_ir_code, symbol_table=None)
                nasm_code_output_str = nasm_generator.generate()
                print_to_compiler_output("Генерация NASM-кода успешно завершена.")

                print_to_compiler_output("\n--- Сгенерированный NASM-код (фрагмент) ---")
                nasm_lines_for_log = nasm_code_output_str.splitlines()
                if len(nasm_lines_for_log) > 40:
                    for line in nasm_lines_for_log[:20]: print_to_compiler_output(line)
                    print_to_compiler_output("...")
                    for line in nasm_lines_for_log[-20:]: print_to_compiler_output(line)
                else:
                    print_to_compiler_output(nasm_code_output_str)
                print_to_compiler_output("-----------------------------------------")

                print_to_compiler_output(f"\n[Этап 6] Ассемблирование NASM и компоновка EXE в: {exe_output_target_file}")
                exe_dir = os.path.dirname(exe_output_target_file)
                if exe_dir and not os.path.exists(exe_dir):
                    os.makedirs(exe_dir, exist_ok=True)
                    print_to_compiler_output(f"Создана директория для EXE: {exe_dir}")

                compile_nasm_and_link_exe(nasm_code_output_str, exe_output_target_file)
                print_to_compiler_output(f"Генерация EXE успешно завершена: {exe_output_target_file}")
                exe_generation_successful = True
            except (NASMGeneratorError, CompilationError) as nge_ce:
                print_to_compiler_output(f"\n--- Ошибка генерации EXE ---")
                print_to_compiler_output(f"Ошибка: {str(nge_ce)}")
                exe_generation_successful = False
            except Exception as e_nasm_link:
                print_to_compiler_output(f"\n--- Непредвиденная ошибка во время генерации EXE ---")
                print_to_compiler_output(f"Ошибка: {str(e_nasm_link)}")
                traceback.print_exc(file=COMPILER_STAGES_OUTPUT)
                exe_generation_successful = False
        else:
            print_to_compiler_output("Нет IR-кода для генерации NASM.")
            exe_generation_successful = False

    except (LexerError, ParserError, IRGeneratorError, NASMGeneratorError, CompilationError) as e_compile: # SemanticError
        if sys.stdout != original_stdout: sys.stdout = original_stdout
        if interpreter_output_handle and not interpreter_output_handle.closed: interpreter_output_handle.close()
        error_message_str = f"\n--- Ошибка компиляции/генерации ---"
        error_message_str += f"\nТип ошибки: {type(e_compile).__name__}"
        error_message_str += f"\nСообщение: {str(e_compile)}"
        token_info = getattr(e_compile, 'token', None)
        line_info = getattr(e_compile, 'line', None)
        column_info = getattr(e_compile, 'column', None)
        if token_info: error_message_str += f"\nРядом с токеном: {token_info}"
        elif line_info is not None and column_info is not None: error_message_str += f"\nМестоположение: L{line_info}:C{column_info}"
        print_to_compiler_output(error_message_str)
        print(error_message_str, file=sys.stderr)
        if not isinstance(e_compile, (LexerError, ParserError, IRGeneratorError, NASMGeneratorError, CompilationError)): # SemanticError
            traceback.print_exc(file=COMPILER_STAGES_OUTPUT)
            traceback.print_exc(file=sys.stderr)
        interpreter_successful = False
        exe_generation_successful = False
    except Exception as e_unexpected:
        if sys.stdout != original_stdout: sys.stdout = original_stdout
        if interpreter_output_handle and not interpreter_output_handle.closed: interpreter_output_handle.close()
        error_message_str = "\n--- Произошла непредвиденная критическая ошибка ---"
        error_message_str += f"\nТип ошибки: {type(e_unexpected).__name__}"
        error_message_str += f"\nСообщение: {str(e_unexpected)}"
        print_to_compiler_output(error_message_str)
        print_to_compiler_output("\n--- Трассировка стека ---")
        traceback.print_exc(file=COMPILER_STAGES_OUTPUT)
        print(error_message_str, file=sys.stderr)
        print("\n--- Трассировка стека ---", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        interpreter_successful = False
        exe_generation_successful = False
    finally:
        if sys.stdout != original_stdout: sys.stdout = original_stdout
        if interpreter_output_handle and not interpreter_output_handle.closed:
            interpreter_output_handle.close()
    log_output = COMPILER_STAGES_OUTPUT.getvalue()
    return log_output, interpreter_successful, exe_generation_successful

if __name__ == '__main__':
    if len(sys.argv) not in [3, 4]:
        print(f"Использование: python {sys.argv[0]} <входной_pas_файл> <выходной_файл_интерпретатора> [<выходной_exe_файл>]")
        sys.exit(1)

    source_file_path = sys.argv[1]
    interpreter_output_file_path = sys.argv[2]
    exe_file_path_target = ""
    if len(sys.argv) == 4:
        exe_file_path_target = sys.argv[3]
    else:
        base, _ = os.path.splitext(source_file_path)
        exe_file_path_target = base + ".exe"
        print(f"Примечание: Путь для EXE не указан, используется по умолчанию '{exe_file_path_target}'")

    try:
        with open(source_file_path, 'r', encoding='utf-8') as f:
            pascal_source_code = f.read()
        logs, interp_ok, exe_ok = compile_and_run_pascal(
            pascal_source_code,
            interpreter_output_file_path,
            exe_file_path_target,
            gui_input_provider=None
        )
        print("\n=== Подробный лог компилятора (из main_logic.py) ===")
        print(logs)
        print("=====================================================")
        if interp_ok:
            print(f"Выполнение интерпретатором завершено. Вывод (если есть) в {interpreter_output_file_path}")
        else:
            print(f"Выполнение интерпретатором не удалось или было пропущено. См. логи.")
        if exe_ok:
            print(f"Генерация EXE успешна: {exe_file_path_target}")
        else:
            print(f"Генерация EXE не удалась. См. логи.")
        if not interp_ok and not exe_ok:
            print(f"Не удалось ни выполнение интерпретатором, ни генерация EXE.")
    except FileNotFoundError:
        print(f"Ошибка: Входной файл не найден: {source_file_path}", file=sys.stderr)
        sys.exit(1)
    except Exception as e_main:
        print(f"Произошла ошибка во время выполнения из командной строки: {e_main}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)