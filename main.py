"""
Aplicação GUI para capturar números de uma imagem copiada (clipboard),
exibir a imagem, mostrar apenas os dígitos extraídos em um campo copiável
e permitir nova busca com confirmação.

Dependências:
    pip install pillow pytesseract
Também é necessário o Tesseract‑OCR instalado no sistema 
Se não tiver instalado, poderá instalar com o link: tesseract-ocr-w64-setup-5.5.0.20241111.exe 
ou empacotado junto usando PyInstaller (--add-data "Tesseract-OCR;Tesseract-OCR").
"""

import os
import sys
import re
import logging
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk, ImageGrab, ImageOps
import pytesseract

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ----------------------------------------------------------------------
# Configuração do caminho do Tesseract
# ----------------------------------------------------------------------
def setup_tesseract_path():
    """
    Configura o caminho do Tesseract automaticamente.
    Procura em múltiplos locais para suportar tanto desenvolvimento quanto distribuição.
    """
    # Determinar o diretório base do executável/script
    if getattr(sys, 'frozen', False):
        # Executável empacotado (PyInstaller)
        application_path = os.path.dirname(sys.executable)
    else:
        # Script Python normal
        application_path = os.path.dirname(os.path.abspath(__file__))
    
    logger.info(f"Diretório da aplicação: {application_path}")
    
    # Lista de caminhos possíveis (ordem de prioridade)
    possible_paths = [
        # 1. Junto com o executável (para distribuição ZIP)
        os.path.join(application_path, "Tesseract-OCR", "tesseract.exe"),
        
        # 2. Pasta _internal do PyInstaller (--onedir)
        os.path.join(application_path, "_internal", "Tesseract-OCR", "tesseract.exe"),
        
        # 3. Diretório temporário do PyInstaller (--onefile)
        os.path.join(getattr(sys, "_MEIPASS", ""), "Tesseract-OCR", "tesseract.exe"),
        
        # 4. Instalações padrão do sistema
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        r"C:\Tesseract-OCR\tesseract.exe",
    ]
    
    # Tentar cada caminho
    for path in possible_paths:
        if path and os.path.isfile(path):
            pytesseract.pytesseract.tesseract_cmd = path
            logger.info(f"✓ Tesseract encontrado: {path}")
            return True
        else:
            logger.debug(f"✗ Não encontrado: {path}")
    
    logger.error("Tesseract não foi encontrado em nenhum caminho!")
    return False


# Configurar Tesseract ao importar o módulo
tesseract_configured = setup_tesseract_path()


# ----------------------------------------------------------------------
# Aplicação principal
# ----------------------------------------------------------------------
class OCRApp(tk.Tk):
    """Aplicação principal de captura e OCR de números"""
    
    # Constantes de configuração
    DEFAULT_WINDOW_WIDTH = 850
    DEFAULT_WINDOW_HEIGHT = 750
    MIN_WINDOW_WIDTH = 800
    MIN_WINDOW_HEIGHT = 700
    
    def __init__(self):
        super().__init__()
        self._setup_initial_state()
        self._setup_styles()
        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        
        # Verificar se Tesseract foi configurado
        if not tesseract_configured:
            self.after(500, self._show_tesseract_error)
        
        logger.info("Aplicação inicializada com sucesso")
    
    def _show_tesseract_error(self):
        """Exibe erro se Tesseract não foi encontrado"""
        if getattr(sys, 'frozen', False):
            app_dir = os.path.dirname(sys.executable)
        else:
            app_dir = os.path.dirname(os.path.abspath(__file__))
            
        messagebox.showerror(
            "Tesseract não encontrado",
            f"O Tesseract-OCR não foi localizado!\n\n"
            f"Certifique-se de que a pasta 'Tesseract-OCR' está no mesmo diretório do programa:\n"
            f"{app_dir}\n\n"
            f"Estrutura necessária:\n"
            f"  • {os.path.basename(sys.executable if getattr(sys, 'frozen', False) else 'programa.exe')}\n"
            f"  • Tesseract-OCR\\\n"
            f"      └── tesseract.exe\n"
            f"      └── tessdata\\"
        )
    
    def _setup_initial_state(self):
        """Inicializa o estado da aplicação"""
        self._img_tk = None
        self._original_image = None
        self.history = []
        
        # Configurações da janela
        self.title("CNEC - Coletor de Números via OCR")
        self.geometry(f"{self.DEFAULT_WINDOW_WIDTH}x{self.DEFAULT_WINDOW_HEIGHT}")
        self.minsize(self.MIN_WINDOW_WIDTH, self.MIN_WINDOW_HEIGHT)
        self.configure(bg="#ecf0f1")

    def _setup_styles(self):
        """Configura os estilos visuais da aplicação"""
        style = ttk.Style(self)
        style.theme_use('clam')
        
        # Estilo dos botões de toolbar
        style.configure(
            'Toolbar.TButton',
            font=('Segoe UI', 10, 'bold'),
            padding=(15, 8)
        )
        style.map(
            'Toolbar.TButton',
            background=[('active', '#2980b9'), ('pressed', '#2472a4')]
        )
        
        # Estilo do botão de limpeza
        style.configure(
            'Clear.TButton',
            font=('Segoe UI', 10, 'bold'),
            padding=(15, 8)
        )
        style.map(
            'Clear.TButton',
            background=[('active', '#c0392b'), ('pressed', '#a93226')]
        )

    def _build_ui(self):
        """Constrói a interface do usuário"""
        self._build_toolbar()
        self._build_main_content()
        self.bind("<Control-v>", lambda e: self.paste_image())

    def _build_toolbar(self):
        """Constrói a barra de ferramentas"""
        toolbar = tk.Frame(self, bg="#34495e", height=60)
        toolbar.pack(fill="x", side="top")
        toolbar.pack_propagate(False)
        
        btn_container = tk.Frame(toolbar, bg="#34495e")
        btn_container.place(relx=0.5, rely=0.5, anchor="center")
        
        # Botões principais
        buttons_config = [
            ("📋 Colar", 'Toolbar.TButton', self.paste_image),
            ("📄 Copiar", 'Toolbar.TButton', self.copy_text),
            ("🗑 Limpar", 'Clear.TButton', self.confirm_clear),
        ]
        
        for text, style, command in buttons_config:
            ttk.Button(
                btn_container,
                text=text,
                style=style,
                command=command
            ).pack(side="left", padx=5)
        
        # Separador
        tk.Frame(btn_container, bg="#7f8c8d", width=2).pack(
            side="left", padx=15, fill="y", pady=8
        )
        
        # Botão de histórico
        ttk.Button(
            btn_container,
            text="📜 Histórico",
            style='Toolbar.TButton',
            command=self.show_history
        ).pack(side="left", padx=5)

    def _build_main_content(self):
        """Constrói o conteúdo principal"""
        main_container = tk.Frame(self, bg="#ecf0f1")
        main_container.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Área da imagem
        self._build_image_area(main_container)
        
        # Área de números extraídos
        self._build_text_area(main_container)

    def _build_image_area(self, parent):
        """Constrói a área de exibição de imagem"""
        img_frame = tk.LabelFrame(
            parent,
            text=" 🖼️  Imagem Capturada ",
            font=("Segoe UI", 11, "bold"),
            bg="#ffffff",
            fg="#2c3e50",
            relief="solid",
            borderwidth=1
        )
        img_frame.pack(fill="both", expand=True, pady=(0, 15))
        
        canvas_container = tk.Frame(img_frame, bg="#ffffff")
        canvas_container.pack(fill="both", expand=True, padx=5, pady=5)
        
        v_scrollbar = ttk.Scrollbar(canvas_container, orient="vertical")
        v_scrollbar.pack(side="right", fill="y")
        
        h_scrollbar = ttk.Scrollbar(canvas_container, orient="horizontal")
        h_scrollbar.pack(side="bottom", fill="x")
        
        self.image_canvas = tk.Canvas(
            canvas_container,
            bg="#f8f9fa",
            yscrollcommand=v_scrollbar.set,
            xscrollcommand=h_scrollbar.set,
            highlightthickness=0
        )
        self.image_canvas.pack(side="left", fill="both", expand=True)
        
        v_scrollbar.config(command=self.image_canvas.yview)
        h_scrollbar.config(command=self.image_canvas.xview)
        
        self.placeholder_label = tk.Label(
            self.image_canvas,
            text="📋 Cole uma imagem para começar\n(Ctrl+V ou botão Colar)",
            font=("Segoe UI", 13, "italic"),
            bg="#f8f9fa",
            fg="#95a5a6"
        )
        self.image_canvas.create_window(0, 0, anchor="nw", window=self.placeholder_label)

    def _build_text_area(self, parent):
        """Constrói a área de texto com números extraídos"""
        text_frame = tk.LabelFrame(
            parent,
            text=" 🔢  Números Extraídos ",
            font=("Segoe UI", 11, "bold"),
            bg="#ffffff",
            fg="#2c3e50",
            relief="solid",
            borderwidth=1
        )
        text_frame.pack(fill="x")
        
        text_container = tk.Frame(text_frame, bg="#ffffff")
        text_container.pack(fill="both", expand=True, padx=5, pady=5)
        
        text_scroll = ttk.Scrollbar(text_container, orient="vertical")
        text_scroll.pack(side="right", fill="y")
        
        self.text_box = tk.Text(
            text_container,
            height=4,
            font=("Consolas", 11),
            bg="#f8f9fa",
            fg="#2c3e50",
            relief="flat",
            yscrollcommand=text_scroll.set,
            wrap="word",
            state="disabled"
        )
        self.text_box.pack(side="left", fill="both", expand=True)
        text_scroll.config(command=self.text_box.yview)

    def display_image_on_canvas(self, image):
        """Exibe a imagem no canvas com scroll"""
        self.image_canvas.delete("all")
        self._img_tk = ImageTk.PhotoImage(image)
        self.image_canvas.create_image(0, 0, anchor="nw", image=self._img_tk)
        self.image_canvas.config(scrollregion=self.image_canvas.bbox("all"))

    def _process_image(self, img: Image.Image) -> Image.Image:
        """Processa a imagem para melhorar OCR"""
        try:
            # Converter para escala de cinza
            gray = img.convert("L")
            
            # Aumentar contraste
            gray = ImageOps.autocontrast(gray, cutoff=1)
            
            # Ampliar MUITO a imagem (OCR funciona melhor com imagens grandes)
            w, h = gray.size
            scale = 4  # 4x maior
            gray = gray.resize((w * scale, h * scale), Image.Resampling.LANCZOS)
            
            # Aplicar sharpening (nitidez)
            from PIL import ImageFilter
            gray = gray.filter(ImageFilter.SHARPEN)
            
            # Binarização com threshold adaptativo
            # Teste diferentes thresholds para ver qual funciona melhor
            threshold = 170
            bw = gray.point(lambda x: 255 if x > threshold else 0, mode="1")
            
            return bw.convert("RGB")
            
        except Exception as e:
            logger.error(f"Erro ao processar imagem: {e}")
            raise

    def _extract_numbers_from_image(self, img: Image.Image) -> list:
        """Extrai números da imagem usando OCR com múltiplas estratégias"""
        try:
            all_numbers = []
            
            # Estratégia 1: PSM 6 (bloco de texto uniforme)
            config1 = "--oem 3 --psm 6 -c tessedit_char_whitelist=0123456789/"
            raw1 = pytesseract.image_to_string(img, lang="eng", config=config1)
            logger.debug(f"OCR PSM 6: {raw1}")
            
            # Estratégia 2: PSM 11 (texto esparso - melhor para números isolados)
            config2 = "--oem 3 --psm 11 -c tessedit_char_whitelist=0123456789/"
            raw2 = pytesseract.image_to_string(img, lang="eng", config=config2)
            logger.debug(f"OCR PSM 11: {raw2}")
            
            # Estratégia 3: PSM 7 (linha única)
            config3 = "--oem 3 --psm 7 -c tessedit_char_whitelist=0123456789/"
            raw3 = pytesseract.image_to_string(img, lang="eng", config=config3)
            logger.debug(f"OCR PSM 7: {raw3}")
            
            # Combinar resultados de todas estratégias
            combined = raw1 + "\n" + raw2 + "\n" + raw3
            
            # Separar por quebras de linha e espaços
            lines = combined.replace("/", "\n").split("\n")
            
            for line in lines:
                # Extrair números de cada linha
                # Aceita números com 1+ dígitos
                nums_in_line = re.findall(r"\d+", line.strip())
                all_numbers.extend(nums_in_line)
            
            # Remover duplicatas mantendo a ordem
            seen = set()
            unique_numbers = []
            for num in all_numbers:
                if num not in seen and len(num) >= 1:
                    seen.add(num)
                    unique_numbers.append(num)
            
            # Filtrar números muito grandes
            unique_numbers = [n for n in unique_numbers if len(n) <= 15]
            
            logger.info(f"OCR encontrou {len(unique_numbers)} números únicos")
            logger.debug(f"Números extraídos: {unique_numbers}")
            
            return unique_numbers
            
        except pytesseract.TesseractNotFoundError:
            logger.error("Tesseract não encontrado durante OCR")
            
            if getattr(sys, 'frozen', False):
                app_dir = os.path.dirname(sys.executable)
            else:
                app_dir = os.path.dirname(os.path.abspath(__file__))
            
            messagebox.showerror(
                "Tesseract não encontrado",
                f"O executável do Tesseract não foi localizado.\n\n"
                f"Certifique-se de que existe a pasta:\n"
                f"{os.path.join(app_dir, 'Tesseract-OCR')}\n\n"
                f"E que dentro dela está o arquivo:\n"
                f"tesseract.exe"
            )
            return []
        except Exception as e:
            logger.error(f"Erro no OCR: {e}")
            messagebox.showerror("Falha no OCR", str(e))
            return []

    def paste_image(self):
        """Cola e processa imagem da área de transferência"""
        try:
            img = ImageGrab.grabclipboard()
        except Exception as e:
            logger.error(f"Erro ao acessar clipboard: {e}")
            messagebox.showerror("Erro", f"Falha ao acessar clipboard:\n{e}")
            return

        if img is None:
            messagebox.showwarning("Nenhuma imagem", "Não há imagem na área de transferência.")
            logger.warning("Nenhuma imagem na clipboard")
            return

        try:
            # Processar imagem
            processed_img = self._process_image(img)
            self._original_image = processed_img
            self.display_image_on_canvas(processed_img)
            logger.info("Imagem exibida no canvas")
            
        except Exception as e:
            logger.error(f"Erro ao processar imagem: {e}")
            messagebox.showerror("Erro ao processar imagem", str(e))
            return

        # Extrair números
        nums = self._extract_numbers_from_image(processed_img)
        
        # Atualizar texto box
        self.text_box.config(state="normal")
        self.text_box.delete("1.0", tk.END)

        if nums:
            extracted = " ".join(nums)
            self.text_box.insert(tk.END, extracted)
            self.add_to_history(extracted)
            logger.info(f"Números extraídos: {extracted}")
        else:
            messagebox.showinfo("Nenhum número detectado", 
                              "O OCR não encontrou dígitos na imagem.")
            logger.warning("Nenhum número detectado na imagem")
        
        self.text_box.config(state="disabled")

    def copy_text(self):
        """Copia o texto extraído para a área de transferência"""
        text = self.text_box.get("1.0", tk.END).strip()
        if not text:
            messagebox.showinfo("Vazio", "Não há texto para copiar.")
            logger.warning("Tentativa de copiar texto vazio")
            return
        
        try:
            self.clipboard_clear()
            self.clipboard_append(text)
            messagebox.showinfo("✓ Copiado", "Texto copiado para a área de transferência.")
            logger.info(f"Texto copiado para clipboard: {text}")
        except Exception as e:
            logger.error(f"Erro ao copiar para clipboard: {e}")
            messagebox.showerror("Erro", f"Erro ao copiar: {e}")

    def confirm_clear(self):
        """Confirma antes de limpar a interface"""
        if messagebox.askyesno("Nova consulta", "Deseja limpar imagem e texto?"):
            self.clear_all()
            logger.info("Interface limpa pelo usuário")

    def clear_all(self):
        """Limpa toda a interface"""
        self.image_canvas.delete("all")
        
        self.placeholder_label = tk.Label(
            self.image_canvas,
            text="📋 Cole uma imagem para começar\n(Ctrl+V ou botão Colar)",
            font=("Segoe UI", 13, "italic"),
            bg="#f8f9fa",
            fg="#95a5a6"
        )
        self.image_canvas.create_window(0, 0, anchor="nw", window=self.placeholder_label)
        
        self.text_box.config(state="normal")
        self.text_box.delete("1.0", tk.END)
        self.text_box.config(state="disabled")
        
        self._img_tk = None
        self._original_image = None

    def show_history(self):
        """Exibe o histórico de números extraídos"""
        win = tk.Toplevel(self)
        win.title("Histórico de Coletas")
        win.geometry("500x400")
        win.configure(bg="#f5f5f5")
        win.transient(self)
        win.grab_set()
        
        main_frame = tk.Frame(win, bg="#f5f5f5")
        main_frame.pack(fill="both", expand=True, padx=15, pady=15)
        
        title_label = tk.Label(
            main_frame,
            text="📋 Histórico de Extrações",
            font=("Segoe UI", 13, "bold"),
            bg="#f5f5f5",
            fg="#2c3e50"
        )
        title_label.pack(pady=(0, 10))
        
        text_frame = tk.Frame(main_frame, bg="#ffffff", relief="solid", borderwidth=1)
        text_frame.pack(fill="both", expand=True)
        
        scrollbar = ttk.Scrollbar(text_frame, orient="vertical")
        scrollbar.pack(side="right", fill="y")
        
        text = tk.Text(
            text_frame,
            wrap="word",
            font=("Consolas", 10),
            bg="#ffffff",
            fg="#2c3e50",
            yscrollcommand=scrollbar.set,
            relief="flat",
            padx=10,
            pady=10
        )
        text.pack(side="left", fill="both", expand=True)
        scrollbar.configure(command=text.yview)
        
        if self.history:
            for i, item in enumerate(self.history, 1):
                text.insert(tk.END, f"{i}. {item}\n\n")
            logger.info(f"Histórico exibido: {len(self.history)} itens")
        else:
            text.insert(tk.END, "Nenhum dado coletado ainda.\n\nCole uma imagem e extraia números para começar.")
        
        text.configure(state="disabled")
        
        ttk.Button(main_frame, text="Fechar", command=win.destroy).pack(pady=(10, 0))

    def add_to_history(self, numbers: str):
        """Adiciona números ao histórico"""
        self.history.append(numbers)
        logger.debug(f"Item adicionado ao histórico. Total: {len(self.history)}")

    def on_close(self):
        """Confirma antes de fechar a aplicação"""
        if messagebox.askokcancel("Sair", "Deseja realmente sair?"):
            logger.info("Aplicação fechada pelo usuário")
            self.destroy()


# ----------------------------------------------------------------------
# Ponto de entrada
# ----------------------------------------------------------------------
if __name__ == "__main__":
    app = OCRApp()
    app.mainloop()