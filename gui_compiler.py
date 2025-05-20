# gui_compiler.py
import tkinter as tk
from tkinter import filedialog, scrolledtext, messagebox, simpledialog
import threading
import traceback
import queue
import sys
import os
from main_logic import compile_and_run_pascal

class CompilerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Паскаль -> Интерпретатор + EXE")
        self.root.geometry("800x750")

        self.input_request_queue = queue.Queue()
        self.input_response_queue = queue.Queue()

        tk.Label(root, text="Файл с исходным кодом (.pas):").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.source_file_entry = tk.Entry(root, width=70)
        self.source_file_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        tk.Button(root, text="Выбрать...", command=self.select_source_file).grid(row=0, column=2, padx=5, pady=5)

        tk.Label(root, text="Выходной файл WRITE интерпретатора (.txt):").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.output_file_entry = tk.Entry(root, width=70)
        self.output_file_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        tk.Button(root, text="Выбрать как...", command=self.select_output_file).grid(row=1, column=2, padx=5, pady=5)

        tk.Label(root, text="Выходной файл EXE (.exe):").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.exe_output_file_entry = tk.Entry(root, width=70)
        self.exe_output_file_entry.grid(row=2, column=1, padx=5, pady=5, sticky="ew")
        tk.Button(root, text="Сохранить EXE как...", command=self.select_exe_output_file).grid(row=2, column=2, padx=5, pady=5)

        self.compile_button = tk.Button(root, text="Скомп. в EXE и Запустить (интерпретатор)", command=self.run_compilation_thread, width=40, height=2)
        self.compile_button.grid(row=3, column=0, columnspan=3, padx=5, pady=10)

        tk.Label(root, text="Логи компиляции и выполнения:").grid(row=4, column=0, columnspan=3, padx=5, pady=5, sticky="w")
        self.log_text_area = scrolledtext.ScrolledText(root, wrap=tk.WORD, width=90, height=18)
        self.log_text_area.grid(row=5, column=0, columnspan=3, padx=5, pady=5, sticky="nsew")
        self.log_text_area.config(state=tk.DISABLED)
        self.log_context_menu = tk.Menu(root, tearoff=0)
        self.log_context_menu.add_command(label="Копировать", command=self.copy_log_text)
        self.log_context_menu.add_command(label="Выделить всё", command=self.select_all_log_text)
        self.log_text_area.bind("<Button-3>", self.show_log_context_menu)

        tk.Label(root, text="Содержимое файла WRITE (интерпретатор):").grid(row=6, column=0, columnspan=3, padx=5, pady=5, sticky="w")
        self.result_text_area = scrolledtext.ScrolledText(root, wrap=tk.WORD, width=90, height=8)
        self.result_text_area.grid(row=7, column=0, columnspan=3, padx=5, pady=5, sticky="nsew")
        self.result_text_area.config(state=tk.DISABLED)
        self.result_context_menu = tk.Menu(root, tearoff=0)
        self.result_context_menu.add_command(label="Копировать", command=self.copy_result_text)
        self.result_context_menu.add_command(label="Выделить всё", command=self.select_all_result_text)
        self.result_text_area.bind("<Button-3>", self.show_result_context_menu)

        root.grid_columnconfigure(1, weight=1)
        root.grid_rowconfigure(5, weight=1)
        root.grid_rowconfigure(7, weight=1)
        self.check_input_queue()

    def show_log_context_menu(self, event):
        self.log_context_menu.tk_popup(event.x_root, event.y_root)

    def copy_log_text(self):
        try:
            selected_text = self.log_text_area.get(tk.SEL_FIRST, tk.SEL_LAST)
            self.root.clipboard_clear()
            self.root.clipboard_append(selected_text)
        except tk.TclError:
            pass

    def select_all_log_text(self):
        self.log_text_area.config(state=tk.NORMAL)
        self.log_text_area.tag_add(tk.SEL, "1.0", tk.END)
        self.log_text_area.mark_set(tk.INSERT, "1.0")
        self.log_text_area.see(tk.INSERT)
        self.log_text_area.config(state=tk.DISABLED)
        self.log_text_area.focus_set()

    def show_result_context_menu(self, event):
        self.result_context_menu.tk_popup(event.x_root, event.y_root)

    def copy_result_text(self):
        try:
            selected_text = self.result_text_area.get(tk.SEL_FIRST, tk.SEL_LAST)
            self.root.clipboard_clear()
            self.root.clipboard_append(selected_text)
        except tk.TclError:
            pass

    def select_all_result_text(self):
        self.result_text_area.config(state=tk.NORMAL)
        self.result_text_area.tag_add(tk.SEL, "1.0", tk.END)
        self.result_text_area.mark_set(tk.INSERT, "1.0")
        self.result_text_area.see(tk.INSERT)
        self.result_text_area.config(state=tk.DISABLED)
        self.result_text_area.focus_set()

    def select_source_file(self):
        filepath = filedialog.askopenfilename(
            title="Выберите файл с исходным кодом Паскаль",
            filetypes=(("Pascal files", "*.pas"), ("Text files", "*.txt"), ("All files", "*.*"))
        )
        if filepath:
            self.source_file_entry.delete(0, tk.END)
            self.source_file_entry.insert(0, filepath)

    def select_output_file(self):
        filepath = filedialog.asksaveasfilename(
            title="Сохранить результат WRITE интерпретатора как",
            defaultextension=".txt",
            filetypes=(("Text files", "*.txt"), ("All files", "*.*"))
        )
        if filepath:
            self.output_file_entry.delete(0, tk.END)
            self.output_file_entry.insert(0, filepath)

    def select_exe_output_file(self):
        filepath = filedialog.asksaveasfilename(
            title="Сохранить исполняемый файл EXE как",
            defaultextension=".exe",
            filetypes=(("Executable files", "*.exe"), ("All files", "*.*"))
        )
        if filepath:
            self.exe_output_file_entry.delete(0, tk.END)
            self.exe_output_file_entry.insert(0, filepath)

    def update_log(self, message):
        if not self.root.winfo_exists(): return
        self.log_text_area.config(state=tk.NORMAL)
        self.log_text_area.insert(tk.END, message + "\n")
        self.log_text_area.see(tk.END)
        self.log_text_area.config(state=tk.DISABLED)
        self.root.update_idletasks()

    def update_result_area(self, content):
        if not self.root.winfo_exists(): return
        self.result_text_area.config(state=tk.NORMAL)
        self.result_text_area.delete('1.0', tk.END)
        self.result_text_area.insert(tk.END, content)
        self.result_text_area.config(state=tk.DISABLED)
        self.root.update_idletasks()

    def gui_input_provider_threaded(self, prompt_from_interpreter):
        if not self.root.winfo_exists():
            print("GUI_INPUT_PROVIDER: Окно GUI не существует, отмена ввода.", file=sys.stderr)
            return None
        dialog_title = "Ввод данных (для интерпретатора)"
        self.input_request_queue.put({'title': dialog_title, 'prompt': prompt_from_interpreter})
        try:
            response = self.input_response_queue.get(block=True, timeout=120)
            self.input_response_queue.task_done()
            return response
        except queue.Empty:
            print("GUI_INPUT_PROVIDER: Таймаут ожидания ответа от пользователя.", file=sys.stderr)
            self._safe_gui_update(self.update_log, "ПРЕДУПРЕЖДЕНИЕ: Таймаут ожидания пользовательского ввода для интерпретатора.")
            return None

    def check_input_queue(self):
        if not self.root.winfo_exists(): return
        try:
            request = self.input_request_queue.get_nowait()
            title = request['title']
            prompt = request['prompt']
            user_input = simpledialog.askstring(title, prompt, parent=self.root)
            self.input_response_queue.put(user_input)
            self.input_request_queue.task_done()
        except queue.Empty:
            pass
        except Exception as e:
            print(f"Ошибка в check_input_queue: {e}", file=sys.stderr)
            try:
                self.input_response_queue.put(None)
                if not self.input_request_queue.empty():
                    self.input_request_queue.task_done()
            except Exception: pass
        finally:
            if self.root.winfo_exists():
                self.root.after(100, self.check_input_queue)

    def run_compilation_thread(self):
        source_path = self.source_file_entry.get()
        interpreter_output_path = self.output_file_entry.get()
        exe_output_path = self.exe_output_file_entry.get()

        if not source_path: messagebox.showerror("Ошибка", "Пожалуйста, выберите файл с исходным кодом."); return
        if not interpreter_output_path: messagebox.showerror("Ошибка", "Пожалуйста, укажите путь для выходного файла интерпретатора."); return
        if not exe_output_path: messagebox.showerror("Ошибка", "Пожалуйста, укажите путь для выходного EXE файла."); return

        self.log_text_area.config(state=tk.NORMAL); self.log_text_area.delete('1.0', tk.END); self.log_text_area.config(state=tk.DISABLED)
        self.update_result_area("")
        self.compile_button.config(text="Компиляция...", state=tk.DISABLED)

        thread = threading.Thread(
            target=self.compile_in_background,
            args=(source_path, interpreter_output_path, exe_output_path, self.gui_input_provider_threaded),
            daemon=True
        )
        thread.start()

    def _safe_gui_update(self, func, *args):
        if self.root.winfo_exists():
            self.root.after(0, func, *args)

    def compile_in_background(self, source_path, interpreter_output_path, exe_output_path, input_provider_func_ref):
        try:
            with open(source_path, 'r', encoding='utf-8') as f:
                source_code = f.read()

            compiler_logs, interpreter_success, exe_success = compile_and_run_pascal(
                source_code,
                interpreter_output_path,
                exe_output_path,
                gui_input_provider=input_provider_func_ref
            )

            self._safe_gui_update(self.update_log, "--- Лог компилятора, интерпретатора и генерации EXE ---")
            self._safe_gui_update(self.update_log, compiler_logs)
            self._safe_gui_update(self.update_log, "--- Конец лога ---")

            if interpreter_success:
                self._safe_gui_update(self.update_log, f"Интерпретация завершена. Результат WRITE (если были) в {interpreter_output_path}")
                try:
                    with open(interpreter_output_path, 'r', encoding='utf-8') as f_res:
                        result_content = f_res.read()
                    self._safe_gui_update(self.update_result_area, result_content)
                except Exception as e_read:
                    self._safe_gui_update(self.update_result_area, f"Не удалось прочитать выходной файл интерпретатора: {e_read}")
            else:
                self._safe_gui_update(self.update_log, "Интерпретация не была успешной или была прервана.")
                self._safe_gui_update(self.update_result_area, "Выполнение интерпретатором не было успешным или было прервано.")

            if exe_success:
                self._safe_gui_update(messagebox.showinfo, "Успех EXE", f"Генерация EXE файла завершена: {exe_output_path}")
            else:
                self._safe_gui_update(messagebox.showerror, "Ошибка EXE", "Ошибка при генерации EXE файла. Смотрите логи.")

            if not interpreter_success and not exe_success and compiler_logs:
                pass
            elif not compiler_logs and not source_path:
                pass

        except FileNotFoundError:
            self._safe_gui_update(messagebox.showerror, "Ошибка", f"Файл с исходным кодом не найден: {source_path}")
            self._safe_gui_update(self.update_log, f"Ошибка: Файл с исходным кодом не найден: {source_path}")
        except Exception as e:
            tb_str = traceback.format_exc()
            self._safe_gui_update(messagebox.showerror, "Критическая ошибка", f"Произошла непредвиденная ошибка в потоке компиляции: {e}")
            self._safe_gui_update(self.update_log, f"Критическая ошибка в потоке: {e}\n{tb_str}")
        finally:
            self._safe_gui_update(lambda: self.compile_button.config(text="Скомп. в EXE и Запустить (интерпретатор)", state=tk.NORMAL))

if __name__ == '__main__':
    main_window = tk.Tk()
    app = CompilerApp(main_window)
    main_window.mainloop()