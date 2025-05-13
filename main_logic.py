import sys
import traceback
import io

from lexer import Lexer, LexerError
from parser import Parser, ParserError
from ir_generator import IRGenerator, IRGeneratorError
from optimizer import Optimizer
from interpreter import Interpreter, InterpreterError
from ast_printer import ASTPrinter

COMPILER_STAGES_OUTPUT = io.StringIO()

def print_to_compiler_output(*args, **kwargs):
    print(*args, **kwargs, file=COMPILER_STAGES_OUTPUT)

def compile_and_run_pascal(source_code_str, output_file_name_target, gui_input_provider=None):
    global COMPILER_STAGES_OUTPUT
    COMPILER_STAGES_OUTPUT = io.StringIO()

    lexer = None
    ast = None
    ir_code = None
    optimized_ir_code = None
    interpreter = None
    original_stdout = sys.stdout
    output_file_handle = None
    success = True

    try:
        print_to_compiler_output("--- Compiler Startup ---")
        print_to_compiler_output("--- Source Code ---")
        print_to_compiler_output(source_code_str)
        print_to_compiler_output("-------------------")

        print_to_compiler_output("\n[Phase 1] Lexing...")
        lexer = Lexer(source_code_str)
        print_to_compiler_output("Lexing completed.")

        print_to_compiler_output("\n[Phase 2] Parsing...")
        parser = Parser(lexer)
        ast = parser.parse()
        print_to_compiler_output("Parsing successful.")

        print_to_compiler_output("\n--- Abstract Syntax Tree (AST) ---")
        ast_printer = ASTPrinter()
        ast_representation = ast_printer.get_representation(ast)
        print_to_compiler_output(ast_representation)
        print_to_compiler_output("---------------------------------")

        print_to_compiler_output("\n[Phase 3] IR Generation...")
        ir_gen = IRGenerator()
        ir_code = ir_gen.generate(ast)
        print_to_compiler_output("IR generation successful.")

        print_to_compiler_output("\n--- Intermediate Representation (IR) ---")
        if ir_code:
            for i, instr in enumerate(ir_code):
                print_to_compiler_output(f"{i:03d}: {instr}")
        else:
            print_to_compiler_output("<No IR generated>")
        print_to_compiler_output("--------------------------------------")

        print_to_compiler_output("\n[Phase 4] Optimization...")
        optimizer = Optimizer(ir_code if ir_code else [])
        optimized_ir_code = optimizer.optimize()

        initial_ir_str = "\n".join(map(str, ir_code if ir_code else []))
        final_optimized_ir_str = "\n".join(map(str, optimized_ir_code if optimized_ir_code else []))

        if initial_ir_str != final_optimized_ir_str and optimized_ir_code is not None :
            print_to_compiler_output("Optimization applied.")
            print_to_compiler_output("--- Optimized IR Code ---")
            for i, instr in enumerate(optimized_ir_code):
                print_to_compiler_output(f"{i:03d}: {instr}")
            print_to_compiler_output("-------------------------")
        else:
            print_to_compiler_output("No effective optimizations performed or optimizer returned original list.")
            if optimized_ir_code is None and ir_code is not None:
                optimized_ir_code = ir_code
            elif optimized_ir_code is None and ir_code is None:
                optimized_ir_code = []

        print_to_compiler_output("\n[Phase 5] Interpretation...")
        print_to_compiler_output(f"Interpreter output (WRITE statements) will be redirected to: {output_file_name_target}")

        if not optimized_ir_code:
            print_to_compiler_output("No IR code to interpret.")
            success = False

        if success:
            try:
                output_file_handle = open(output_file_name_target, 'w', encoding='utf-8')
                sys.stdout = output_file_handle

                interpreter = Interpreter(optimized_ir_code)
                interpreter.run(original_stdout_ref=original_stdout, input_provider_func=gui_input_provider)

            finally:
                if output_file_handle:
                    output_file_handle.close()
                sys.stdout = original_stdout
                print_to_compiler_output(f"\nInterpreter output (WRITE statements) written to {output_file_name_target}")

        if success:
            print_to_compiler_output("\n--- Compilation and Execution Successful ---")

    except (LexerError, ParserError, IRGeneratorError, InterpreterError, RuntimeError) as e:
        sys.stdout = original_stdout
        if output_file_handle and not output_file_handle.closed: output_file_handle.close()
        error_message_str = f"\n--- Compilation/Runtime Error ---"; error_message_str += f"\nError: {str(e)}"
        token_info = getattr(e, 'token', None); line_info = getattr(e, 'line', None); column_info = getattr(e, 'column', None)
        if token_info: error_message_str += f"\nNear token: {token_info}"
        elif line_info is not None and column_info is not None: error_message_str += f"\nLocation: L{line_info}:C{column_info}"
        print_to_compiler_output(error_message_str); print(error_message_str, file=sys.stderr)
        if not isinstance(e, (LexerError, ParserError, IRGeneratorError, InterpreterError)):
            traceback.print_exc(file=COMPILER_STAGES_OUTPUT); traceback.print_exc(file=sys.stderr)
        success = False
    except Exception as e:
        sys.stdout = original_stdout
        if output_file_handle and not output_file_handle.closed: output_file_handle.close()
        error_message_str = "\n--- An Unexpected Error Occurred ---"; error_message_str += f"\nError: {str(e)}"
        print_to_compiler_output(error_message_str); print_to_compiler_output("\n--- Traceback ---")
        traceback.print_exc(file=COMPILER_STAGES_OUTPUT)
        print(error_message_str, file=sys.stderr); print("\n--- Traceback ---", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        success = False
    finally:
        if sys.stdout != original_stdout: sys.stdout = original_stdout
        if output_file_handle and not output_file_handle.closed: output_file_handle.close()

    log_output = COMPILER_STAGES_OUTPUT.getvalue()
    COMPILER_STAGES_OUTPUT.close()
    return log_output, success

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print(f"Usage (for command line): python {sys.argv[0]} <input_source_file> <output_target_file>")
        sys.exit(1)

    source_file_path = sys.argv[1]
    output_file_path_target = sys.argv[2]

    try:
        with open(source_file_path, 'r', encoding='utf-8') as f:
            source_code = f.read()

        logs, result_success = compile_and_run_pascal(source_code, output_file_path_target, gui_input_provider=None)

        print("\n=== Detailed Compiler Log (from main_logic.py) ===")
        print(logs)
        print("====================================================")

        if result_success:
            print(f"Compilation and execution finished. Output in {output_file_path_target}")
        else:
            print(f"Compilation/Execution failed. See logs above for details.")

    except FileNotFoundError:
        print(f"Error: Input file not found: {source_file_path}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"An error occurred during command-line execution: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)