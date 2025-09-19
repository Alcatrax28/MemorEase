# spinner_widget.py
import customtkinter as ctk # pyright: ignore[reportMissingImports]

class SpinnerWidget:
    def __init__(self, parent, delay=150):
        self.parent = parent
        self.delay = delay
        self.spinner_state = 0
        self.spinner_running = False
        self.spinner_label = ctk.CTkLabel(parent, text="⠋", font=ctk.CTkFont(size=16))
        self.spinner_label.pack(pady=(0, 10))

    def start(self):
        self.spinner_running = True
        self._animate()

    def stop(self, final="✅"):
        self.spinner_running = False
        self.spinner_label.configure(text=final)

    def _animate(self):
        if not self.spinner_running:
            return
        spinner_chars = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        char = spinner_chars[self.spinner_state % len(spinner_chars)]
        self.spinner_state += 1
        self.spinner_label.configure(text=char)
        self.parent.after(self.delay, self._animate)