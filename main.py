"""
Aplicação GUI para capturar números de uma imagem copiada (clipboard),
exibir a imagem, mostrar apenas os dígitos extraídos em um campo copiável
e permitir nova busca com confirmação.

Dependências:
    pip install pillow pytesseract
Também é necessário o Tesseract‑OCR instalado no sistema.
"""

import os
import sys
import re
import logging
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk, ImageGrab, ImageOps, ImageFilter
import pytesseract

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ----------------------------------------------------------------------
# Configuração do Tesseract
# ----------------------------------------------------------------------
def setup_tesseract_path():
    """Configura o caminho do Tesseract automaticamente"""
    # Determinar diretório base
    if getattr(sys, 'frozen', False):
        app_path = os.path.dirname(sys.executable)
    else:
        app_path = os.path.dirname(os.path.abspath(__file__))
    
    parent_path = os.path.dirname(app_path)
    
    # Caminhos possíveis (ordem de prioridade)
    paths = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        os.path.join(app_path, "Tesseract-OCR", "tesseract.exe"),
        os.path.join(parent_path, "Tesseract-OCR", "tesseract.exe"),
        os.path.join(app_path, "_internal", "Tesseract-OCR", "tesseract.exe"),
        os.path.join(getattr(sys, "_MEIPASS", ""), "Tesseract-OCR", "tesseract.exe"),
    ]
    
    for path in paths:
        if path and os.path.isfile(path):
            pytesseract.pytesseract.tesseract_cmd = path
            logger.info(f"Tesseract encontrado: {path}")
            return True
    
    logger.error("Tesseract não encontrado")
    return False


tesseract_configured = setup_tesseract_path()


# ----------------------------------------------------------------------
# Aplicação Principal
# ----------------------------------------------------------------------
class OCRApp(tk.Tk):
    """Aplicação de captura e OCR de números"""
    
    def __init__(self):
        super().__init__()
        self._img_tk = None
        self._original_image = None
        self.history = []
        
        # Configuração da janela
        self.title("Coletor de Números via OCR")
        self.geometry("850x750")
        self.minsize(800, 700)
        self.configure(bg="#ecf0f1")
        
        self._setup_styles()
        self._build_ui()
        
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        
        if not tesseract_configured:
            self.after(100, self._show_tesseract_error)
        
        logger.info("Aplicação inicializada")
    
    def _setup_styles(self):
        """Configura estilos visuais"""
        style = ttk.Style(self)
        style.theme_use('clam')
        
        style.configure('Toolbar.TButton', font=('Segoe UI', 10, 'bold'), padding=(15, 8))
        style.map('Toolbar.TButton', background=[('active', '#2980b9'), ('pressed', '#2472a4')])
        
        style.configure('Clear.TButton', font=('Segoe UI', 10, 'bold'), padding=(15, 8))
        style.map('Clear.TButton', background=[('active', '#c0392b'), ('pressed', '#a93226')])

    def _build_ui(self):
        """Constrói interface"""
        self._build_toolbar()
        self._build_main_content()
        self.bind_all("<Control-v>", lambda e: self.paste_image())
        self.bind_all("<Control-V>", lambda e: self.paste_image())

    def _build_toolbar(self):
        """Constrói barra de ferramentas"""
        toolbar = tk.Frame(self, bg="#34495e", height=60)
        toolbar.pack(fill="x", side="top")
        toolbar.pack_propagate(False)
        
        btn_container = tk.Frame(toolbar, bg="#34495e")
        btn_container.place(relx=0.5, rely=0.5, anchor="center")
        
        ttk.Button(btn_container, text="📋 Colar", style='Toolbar.TButton', 
                   command=self.paste_image).pack(side="left", padx=5)
        ttk.Button(btn_container, text="📄 Copiar", style='Toolbar.TButton', 
                   command=self.copy_text).pack(side="left", padx=5)
        ttk.Button(btn_container, text="🗑 Limpar", style='Clear.TButton', 
                   command=self.confirm_clear).pack(side="left", padx=5)
        
        tk.Frame(btn_container, bg="#7f8c8d", width=2).pack(side="left", padx=15, fill="y", pady=8)
        
        ttk.Button(btn_container, text="📜 Histórico", style='Toolbar.TButton', 
                   command=self.show_history).pack(side="left", padx=5)

    def _build_main_content(self):
        """Constrói conteúdo principal"""
        main = tk.Frame(self, bg="#ecf0f1")
        main.pack(fill="both", expand=True, padx=20, pady=20)
        
        self._build_image_area(main)
        self._build_text_area(main)

    def _build_image_area(self, parent):
        """Área de exibição de imagem"""
        frame = tk.LabelFrame(parent, text=" 🖼️  Imagem Capturada ", 
                             font=("Segoe UI", 11, "bold"), bg="#ffffff", 
                             fg="#2c3e50", relief="solid", borderwidth=1)
        frame.pack(fill="both", expand=True, pady=(0, 15))
        
        container = tk.Frame(frame, bg="#ffffff")
        container.pack(fill="both", expand=True, padx=5, pady=5)
        
        v_scroll = ttk.Scrollbar(container, orient="vertical")
        v_scroll.pack(side="right", fill="y")
        
        h_scroll = ttk.Scrollbar(container, orient="horizontal")
        h_scroll.pack(side="bottom", fill="x")
        
        self.image_canvas = tk.Canvas(container, bg="#f8f9fa", 
                                     yscrollcommand=v_scroll.set,
                                     xscrollcommand=h_scroll.set,
                                     highlightthickness=0)
        self.image_canvas.pack(side="left", fill="both", expand=True)
        
        v_scroll.config(command=self.image_canvas.yview)
        h_scroll.config(command=self.image_canvas.xview)
        
        self.placeholder = tk.Label(self.image_canvas,
                                   text="📋 Cole uma imagem para começar\n(Ctrl+V ou botão Colar)",
                                   font=("Segoe UI", 13, "italic"),
                                   bg="#f8f9fa", fg="#95a5a6")
        self.image_canvas.create_window(0, 0, anchor="nw", window=self.placeholder)

    def _build_text_area(self, parent):
        """Área de texto com números extraídos"""
        frame = tk.LabelFrame(parent, text=" 🔢  Números Extraídos ",
                             font=("Segoe UI", 11, "bold"), bg="#ffffff",
                             fg="#2c3e50", relief="solid", borderwidth=1)
        frame.pack(fill="x")
        
        container = tk.Frame(frame, bg="#ffffff")
        container.pack(fill="both", expand=True, padx=5, pady=5)
        
        scroll = ttk.Scrollbar(container, orient="vertical")
        scroll.pack(side="right", fill="y")
        
        self.text_box = tk.Text(container, height=4, font=("Consolas", 11),
                               bg="#f8f9fa", fg="#2c3e50", relief="flat",
                               yscrollcommand=scroll.set, wrap="word", state="disabled")
        self.text_box.pack(side="left", fill="both", expand=True)
        scroll.config(command=self.text_box.yview)

    def _show_tesseract_error(self):
        """Exibe erro de Tesseract não encontrado"""
        app_dir = os.path.dirname(sys.executable if getattr(sys, 'frozen', False) 
                                  else os.path.abspath(__file__))
        
        messagebox.showerror(
            "Tesseract não encontrado",
            f"O Tesseract-OCR não foi localizado!\n\n"
            f"Certifique-se de ter:\n"
            f"1. Tesseract instalado em C:\\Program Files\\Tesseract-OCR\\\n"
            f"   OU\n"
            f"2. Pasta Tesseract-OCR junto com o executável:\n"
            f"   {app_dir}\\Tesseract-OCR\\tesseract.exe"
        )

    def _process_image(self, img: Image.Image) -> Image.Image:
        """Processa imagem para OCR"""
        # Converter para escala de cinza
        gray = img.convert("L")
        
        # Detectar se fundo é escuro
        avg_brightness = sum(gray.getdata()) / (gray.size[0] * gray.size[1])
        if avg_brightness < 127:
            gray = ImageOps.invert(gray)
        
        # Aumentar contraste agressivamente
        gray = ImageOps.autocontrast(gray, cutoff=10)
        
        # Ampliar MUITO (quanto maior, melhor para OCR)
        w, h = gray.size
        gray = gray.resize((w * 6, h * 6), Image.Resampling.LANCZOS)
        
        # Aplicar filtro de desfoque leve para suavizar bordas
        gray = gray.filter(ImageFilter.GaussianBlur(radius=0.5))
        
        # Sharpen para deixar texto mais definido
        gray = gray.filter(ImageFilter.UnsharpMask(radius=1, percent=150, threshold=3))
        
        # Binarização Otsu-like (threshold automático baseado no histograma)
        # Calcular threshold ideal
        hist = gray.histogram()
        total = sum(hist)
        sum_total = sum(i * hist[i] for i in range(256))
        
        sum_b = 0
        w_b = 0
        maximum = 0.0
        threshold = 0
        
        for i in range(256):
            w_b += hist[i]
            if w_b == 0:
                continue
            w_f = total - w_b
            if w_f == 0:
                break
            sum_b += i * hist[i]
            m_b = sum_b / w_b
            m_f = (sum_total - sum_b) / w_f
            between = w_b * w_f * (m_b - m_f) ** 2
            if between > maximum:
                maximum = between
                threshold = i
        
        # Aplicar threshold calculado
        bw = gray.point(lambda x: 255 if x > threshold else 0, mode="1")
        
        return bw.convert("RGB")

    def _extract_numbers(self, img: Image.Image) -> list:
        """Extrai números usando OCR"""
        try:
            # Usar apenas PSM 6 com configuração otimizada
            # digits_only para forçar reconhecimento de números
            custom_config = r'--oem 3 --psm 6 -c tessedit_char_whitelist=0123456789 -c classify_bln_numeric_mode=1'
            
            text = pytesseract.image_to_string(img, lang="eng", config=custom_config)
            
            logger.info(f"OCR texto bruto: '{text}'")
            
            # Limpar texto - remover espaços extras e quebras de linha
            text = ' '.join(text.split())
            
            # Separar números por espaços
            parts = text.split()
            
            numbers = []
            for part in parts:
                # Extrair apenas dígitos de cada parte
                digits = ''.join(filter(str.isdigit, part))
                if digits and 1 <= len(digits) <= 15:
                    numbers.append(digits)
            
            # Remover duplicatas mantendo ordem
            seen = set()
            unique = []
            for num in numbers:
                if num not in seen:
                    seen.add(num)
                    unique.append(num)
            
            logger.info(f"Números extraídos finais: {unique}")
            return unique
            
        except pytesseract.TesseractNotFoundError:
            messagebox.showerror("Erro", "Tesseract não encontrado durante OCR")
            return []
        except Exception as e:
            logger.error(f"Erro no OCR: {e}")
            messagebox.showerror("Erro no OCR", str(e))
            return []

    def paste_image(self):
        """Cola e processa imagem"""
        try:
            img = ImageGrab.grabclipboard()
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao acessar clipboard:\n{e}")
            return

        if img is None:
            messagebox.showwarning("Nenhuma imagem", "Não há imagem na área de transferência.")
            return

        try:
            processed = self._process_image(img)
            self._original_image = processed
            
            self.image_canvas.delete("all")
            self._img_tk = ImageTk.PhotoImage(processed)
            self.image_canvas.create_image(0, 0, anchor="nw", image=self._img_tk)
            self.image_canvas.config(scrollregion=self.image_canvas.bbox("all"))
            
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao processar imagem:\n{e}")
            return

        # Extrair números
        nums = self._extract_numbers(processed)
        
        self.text_box.config(state="normal")
        self.text_box.delete("1.0", tk.END)

        if nums:
            extracted = " ".join(nums)
            self.text_box.insert(tk.END, extracted)
            self.history.append(extracted)
            logger.info(f"Coletado: {extracted}")
        else:
            messagebox.showinfo("Nenhum número", "OCR não encontrou dígitos na imagem.")
        
        self.text_box.config(state="disabled")

    def copy_text(self):
        """Copia texto para clipboard"""
        text = self.text_box.get("1.0", tk.END).strip()
        if not text:
            messagebox.showinfo("Vazio", "Não há texto para copiar.")
            return
        
        self.clipboard_clear()
        self.clipboard_append(text)
        messagebox.showinfo("✓ Copiado", "Texto copiado!")

    def confirm_clear(self):
        """Confirma limpeza"""
        if messagebox.askyesno("Nova consulta", "Limpar imagem e texto?"):
            self.clear_all()

    def clear_all(self):
        """Limpa interface"""
        self.image_canvas.delete("all")
        
        self.placeholder = tk.Label(self.image_canvas,
                                   text="📋 Cole uma imagem para começar\n(Ctrl+V ou botão Colar)",
                                   font=("Segoe UI", 13, "italic"),
                                   bg="#f8f9fa", fg="#95a5a6")
        self.image_canvas.create_window(0, 0, anchor="nw", window=self.placeholder)
        
        self.text_box.config(state="normal")
        self.text_box.delete("1.0", tk.END)
        self.text_box.config(state="disabled")
        
        self._img_tk = None
        self._original_image = None

    def show_history(self):
        """Exibe histórico"""
        win = tk.Toplevel(self)
        win.title("Histórico de Coletas")
        win.geometry("500x400")
        win.configure(bg="#f5f5f5")
        win.transient(self)
        win.grab_set()
        
        frame = tk.Frame(win, bg="#f5f5f5")
        frame.pack(fill="both", expand=True, padx=15, pady=15)
        
        tk.Label(frame, text="📋 Histórico de Extrações",
                font=("Segoe UI", 13, "bold"), bg="#f5f5f5",
                fg="#2c3e50").pack(pady=(0, 10))
        
        text_frame = tk.Frame(frame, bg="#ffffff", relief="solid", borderwidth=1)
        text_frame.pack(fill="both", expand=True)
        
        scroll = ttk.Scrollbar(text_frame, orient="vertical")
        scroll.pack(side="right", fill="y")
        
        text = tk.Text(text_frame, wrap="word", font=("Consolas", 10),
                      bg="#ffffff", fg="#2c3e50", yscrollcommand=scroll.set,
                      relief="flat", padx=10, pady=10)
        text.pack(side="left", fill="both", expand=True)
        scroll.configure(command=text.yview)
        
        if self.history:
            for i, item in enumerate(self.history, 1):
                text.insert(tk.END, f"{i}. {item}\n\n")
        else:
            text.insert(tk.END, "Nenhum dado coletado ainda.")
        
        text.configure(state="disabled")
        ttk.Button(frame, text="Fechar", command=win.destroy).pack(pady=(10, 0))

    def on_close(self):
        """Confirma saída"""
        if messagebox.askokcancel("Sair", "Deseja realmente sair?"):
            self.destroy()


if __name__ == "__main__":
    app = OCRApp()
    app.mainloop()