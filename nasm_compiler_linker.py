# nasm_compiler_linker.py
import subprocess
import os
import tempfile
import shutil
import unicodedata
import re

class CompilationError(Exception):
    pass

def check_tool_in_path(tool_name):
    return shutil.which(tool_name) is not None

def sanitize_filename_for_temp(filename):
    nfkd_form = unicodedata.normalize('NFKD', filename)
    ascii_filename_parts = []
    for char_code in nfkd_form:
        if not unicodedata.combining(char_code) and ord(char_code) < 128:
            ascii_filename_parts.append(char_code)
    ascii_filename = "".join(ascii_filename_parts)
    ascii_filename = re.sub(r'[^\w-]', '_', ascii_filename)
    ascii_filename = re.sub(r'_+', '_', ascii_filename)
    ascii_filename = ascii_filename.strip('_')
    if not ascii_filename or len(ascii_filename) < 1:
        return "temp_asm_file"
    return ascii_filename

def compile_nasm_and_link_exe(nasm_code_str, exe_output_path, temp_dir_prefix="pasc_comp_"):
    exe_base_name_original = os.path.splitext(os.path.basename(exe_output_path))[0]
    temp_file_base_name = sanitize_filename_for_temp(exe_base_name_original)

    with tempfile.TemporaryDirectory(prefix=temp_dir_prefix) as tmpdir:
        asm_file_path = os.path.join(tmpdir, f"{temp_file_base_name}.asm")
        obj_file_path = os.path.join(tmpdir, f"{temp_file_base_name}.obj")

        try:
            with open(asm_file_path, 'w', encoding='utf-8') as f:
                f.write(nasm_code_str)
        except IOError as e:
            raise CompilationError(f"Не удалось записать временный ASM-файл '{asm_file_path}': {e}")
        except Exception as e_write:
            raise CompilationError(f"Непредвиденная ошибка при записи временного ASM-файла '{asm_file_path}': {e_write}")

        if not check_tool_in_path('nasm'):
            raise CompilationError("NASM не найден в PATH.")

        nasm_command = ['nasm', '-f', 'win32', asm_file_path, '-o', obj_file_path, '-g']
        try:

            result = subprocess.run(nasm_command, capture_output=True, text=True, check=True, encoding='utf-8', errors='replace')
        except FileNotFoundError:
            raise CompilationError("NASM не найден (FileNotFoundError).")
        except subprocess.CalledProcessError as e:
            error_output = f"NASM stdout:\n{e.stdout}\nNASM stderr:\n{e.stderr}"
            raise CompilationError(f"Ошибка компиляции NASM (код {e.returncode}) для '{asm_file_path}':\n{error_output}")

        if not check_tool_in_path('gcc'):
            raise CompilationError("GCC (компоновщик) не найден в PATH.")

        link_command = [
            'gcc', '-m32', obj_file_path, '-o', exe_output_path,
            '-Wl,-e,_main', '-nostdlib', '-lgcc', '-lkernel32', '-lmsvcrt'
        ]
        try:
            result = subprocess.run(link_command, capture_output=True, text=True, check=True, encoding='utf-8', errors='replace')

        except FileNotFoundError:
            raise CompilationError("GCC (компоновщик) не найден (FileNotFoundError).")
        except subprocess.CalledProcessError as e:
            error_output = f"Linker stdout:\n{e.stdout}\nLinker stderr:\n{e.stderr}"
            raise CompilationError(f"Ошибка компоновки (код {e.returncode}) для '{exe_output_path}':\n{error_output}")
    return True

if __name__ == '__main__':
    sample_nasm_code = """
section .data
    msg db "Привет из NASM EXE!", 0Ah, 0
    fmt_int db "%d", 0Ah, 0
section .text
    global _main
    extern _printf
    extern _exit
_main:
    push ebp
    mov ebp, esp
    push msg
    call _printf
    add esp, 4
    push dword 12345
    push fmt_int
    call _printf
    add esp, 8
    push 0
    call _exit
    """
    test_exe_name = "test_linker.exe"
    try:
        if compile_nasm_and_link_exe(sample_nasm_code, test_exe_name):
            print(f"Тестовый EXE '{test_exe_name}' создан.")

    except CompilationError as e_comp:
        print(f"Ошибка тестовой компиляции: {e_comp}")
