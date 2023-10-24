import tkinter as tk
import time
from vericota import Vericota

class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip = None
        self.widget.bind("<Enter>", self.show_tooltip)
        self.widget.bind("<Leave>", self.hide_tooltip)

    def show_tooltip(self, event):
        x = self.widget.winfo_rootx() + self.widget.winfo_width()
        y = self.widget.winfo_rooty()
        self.tooltip = tk.Toplevel(self.widget)
        self.tooltip.wm_overrideredirect(True)
        self.tooltip.wm_geometry(f"+{x}+{y}")
        label = tk.Label(self.tooltip, text=self.text,
                         background="lightyellow", relief="solid")
        label.pack()

    def hide_tooltip(self, event):
        if self.tooltip is not None:
            self.tooltip.destroy()
            self.tooltip = None


class VericotaApp:
    def __init__(self):
        self.vericota = Vericota()
        self.root = tk.Tk()
        self.root.title("Vericota")
        self.root.geometry("600x400")
        self.root.configure(bg="#333333")

        self.titulo = tk.Label(self.root, text="Vericota", bg="#333333",
                        fg="#CAFC3B", font=("Helvetica", 16, "bold"))
        self.titulo.pack(pady=10)

        self.botao_britech = tk.Button(self.root, text="E-mail Britech", bg="lightgreen", fg="black", command=self.atualiza_britech)
        self.botao_backoffice = tk.Button(self.root, text="E-mail Backoffice", bg="lightgreen", fg="black", command=self.atualiza_backoffice)
        self.botao_britech.pack(side=tk.LEFT, padx=10)
        self.botao_backoffice.pack(side=tk.LEFT, padx=10)

        self.status_text = tk.Text(self.root, bg="black", fg="white")
        self.status_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
    def adicionar_texto(self, texto):
        self.status_text.insert(tk.END, texto)
        self.status_text.see(tk.END)
        self.status_text.update_idletasks()

    def atualiza_backoffice(self):
        
        try:
            self.adicionar_texto("Preparando as bases...\n\n")
            time.sleep(2)
            self.adicionar_texto("Enviando email de \
                                    variação de cotas para \
                                    o Backoffice!\n\n")
            time.sleep(2)
            self.adicionar_texto("Aguarde...\n\n")
            self.vericota.atualicao_variacao_cota()
            self.adicionar_texto("E-mail enviado!\n")
            
        except Exception as e:
            self.adicionar_texto(
                f"\nErro {e}! Verifique o prompt para mais detalhes.")

    def atualiza_britech(self):
            
            try:
                self.adicionar_texto("Preparando as bases...\n\n")
                time.sleep(2)
                self.adicionar_texto("Enviando email - BPO Britech!\n")
                time.sleep(2)
                self.adicionar_texto("Aguarde...\n\n")
                self.vericota.atualizacao_britech()
                self.adicionar_texto("E-mail enviado!\n")
                
            except Exception as e:
                self.adicionar_texto(
                    f"\nErro {e}! Verifique o prompt para mais detalhes.")


if __name__ == "__main__":
    app = VericotaApp()
    app.root.mainloop()
