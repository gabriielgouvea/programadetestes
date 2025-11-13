# -*- coding: utf-8 -*-

"""
Arquivo: view_achados.py
Descrição: Contém a classe AchadosView, que constrói e gerencia
a nova tela de Achados e Perdidos.
(v5.3.7 - Corrigido o AttributeError 'btn_cancelar')
"""

import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from ttkbootstrap.widgets import DateEntry
from tkinter import messagebox, Toplevel, StringVar, scrolledtext, PhotoImage
from datetime import date
import os

# --- Importa o gerenciador do Firebase ---
import firebase_manager as fm

# --- Tenta importar o OpenCV (para a webcam) ---
try:
    import cv2
    from PIL import Image, ImageTk, ImageDraw, ImageFont
    OPENCV_DISPONIVEL = True
except ImportError:
    OPENCV_DISPONIVEL = False
    print("AVISO: opencv-python não instalado. A funcionalidade da webcam estará desabilitada.")
    print("Para instalar, rode: pip install opencv-python")


# --- O POPUP DE CADASTRO (NOVA JANELA) ---

class CadastroItemPopup(Toplevel):
    def __init__(self, app, view_achados):
        super().__init__(app)
        self.app = app
        self.view_achados = view_achados # Referência à tela principal de Achados

        self.title("Cadastrar Novo Item Perdido")
        self.app._center_popup(self, 750, 800) # (popup, largura, altura)
        self.resizable(False, False) # Trava o tamanho

        # --- Variáveis ---
        self.webcam_feed = None
        self.foto_capturada_pil = None # Guarda a imagem PIL (para salvar)
        self.foto_capturada_tk = None # Guarda a imagem TK (para exibir)
        self.camera_index = 0 # Qual câmera usar
        
        # --- Variáveis para os novos campos ---
        self.data_cadastro_var = StringVar(value=date.today().strftime("%d/%m/%Y"))
        self.consultor_var = StringVar(value=self.app.consultor_logado_data.get('nome', 'N/A'))


        # --- Layout ---
        # Frame principal que segura o formulário
        main_frame = ttk.Frame(self, padding=15)
        main_frame.pack(fill='both', expand=True) # Ocupa todo o espaço (menos o rodapé)
        main_frame.grid_columnconfigure(1, weight=1) # Coluna do formulário expande
        main_frame.grid_rowconfigure(3, weight=1)    # Linha da descrição expande

        # --- Lado Esquerdo: Câmera ---
        frame_camera = ttk.Frame(main_frame, padding=10)
        frame_camera.grid(row=0, column=0, rowspan=14, sticky='n', padx=(0, 15)) # Alinhado ao Topo

        # --- Placeholder inicial para a câmera ---
        self.camera_placeholder_img = Image.new('RGB', (320, 240), (230, 230, 230)) # Cinza claro
        draw = ImageDraw.Draw(self.camera_placeholder_img)
        
        try:
            pil_font = ImageFont.load_default(size=14)
        except:
            pil_font = ImageFont.load_default()

        text = "Ligar Câmera"
        text_bbox = draw.textbbox((0, 0), text, font=pil_font) 
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]
        draw.text(
            ((320 - text_width) / 2, (240 - text_height) / 2), 
            text, 
            fill=(50, 50, 50), 
            font=pil_font
        )
        self.camera_placeholder_tk = ImageTk.PhotoImage(self.camera_placeholder_img)


        self.camera_label = ttk.Label(frame_camera, image=self.camera_placeholder_tk, bootstyle='secondary', cursor="hand2")
        self.camera_label.image = self.camera_placeholder_tk # Manter ref
        self.camera_label.pack(side='top', pady=(0, 10))
        self.camera_label.bind("<Button-1>", lambda e: self.open_camera())
        
        # Botões de controle da câmera
        self.btn_ligar_camera = ttk.Button(frame_camera, text="Ligar/Trocar Câmera", command=self.open_camera, style='primary.TButton')
        self.btn_ligar_camera.pack(fill='x', ipady=5)
        
        self.btn_tirar_foto = ttk.Button(frame_camera, text="Capturar Foto", command=self.take_picture, style='secondary.TButton', state='disabled')
        self.btn_tirar_foto.pack(fill='x', pady=5)
        
        if not OPENCV_DISPONIVEL:
            img_err = Image.new('RGB', (320, 240), (230, 230, 230))
            draw = ImageDraw.Draw(img_err)
            err_text = "OpenCV não instalado.\nImpossível usar a câmera."
            text_bbox = draw.textbbox((0, 0), err_text, font=pil_font)
            text_width = text_bbox[2] - text_bbox[0]
            text_height = text_bbox[3] - text_bbox[1]
            draw.text(
                ((320 - text_width) / 2, (240 - text_height) / 2),
                err_text, 
                fill=(200, 0, 0), 
                font=pil_font
            )
            self.img_err_tk = ImageTk.PhotoImage(img_err)
            self.camera_label.config(image=self.img_err_tk, cursor="")
            self.camera_label.unbind("<Button-1>")
            self.btn_tirar_foto.config(state='disabled')
            self.btn_ligar_camera.config(state='disabled')

        # --- Lado Direito: Formulário ---
        
        # Título
        ttk.Label(main_frame, text="Título do Item (Ex: Coqueteleira preta):", font=self.app.FONT_BOLD).grid(row=0, column=1, sticky='w', pady=(0, 5))
        self.entry_titulo = ttk.Entry(main_frame, font=self.app.FONT_MAIN, width=50)
        self.entry_titulo.grid(row=1, column=1, sticky='ew', pady=(0, 10))

        # Descrição
        ttk.Label(main_frame, text="Descrição (Opcional):", font=self.app.FONT_BOLD).grid(row=2, column=1, sticky='w', pady=(0, 5))
        self.entry_descricao = scrolledtext.ScrolledText(main_frame, height=5, font=self.app.FONT_MAIN)
        self.entry_descricao.grid(row=3, column=1, sticky='nsew', pady=(0, 10))

        # Nº de Controle
        ttk.Label(main_frame, text="Nº de Controle (Adesivo):", font=self.app.FONT_BOLD).grid(row=4, column=1, sticky='w', pady=(0, 5))
        self.entry_controle = ttk.Entry(main_frame, font=self.app.FONT_MAIN, width=20)
        self.entry_controle.grid(row=5, column=1, sticky='w', pady=(0, 10))
        
        # --- NOVOS CAMPOS ---
        
        # Data que Achou
        ttk.Label(main_frame, text="Data que Achou:", font=self.app.FONT_BOLD).grid(row=6, column=1, sticky='w', pady=(0, 5))
        self.entry_data_achado = DateEntry(main_frame, dateformat="%d/%m/%Y", bootstyle='primary')
        self.entry_data_achado.grid(row=7, column=1, sticky='w', pady=(0, 10))
        
        # Data de Cadastro
        ttk.Label(main_frame, text="Data de Cadastro:", font=self.app.FONT_BOLD).grid(row=8, column=1, sticky='w', pady=(0, 5))
        self.entry_data_cadastro = ttk.Entry(main_frame, textvariable=self.data_cadastro_var, state='disabled', font=self.app.FONT_MAIN, width=20)
        self.entry_data_cadastro.grid(row=9, column=1, sticky='w', pady=(0, 10))
        
        # Consultor
        ttk.Label(main_frame, text="Consultor:", font=self.app.FONT_BOLD).grid(row=10, column=1, sticky='w', pady=(0, 5))
        self.entry_consultor = ttk.Entry(main_frame, textvariable=self.consultor_var, state='disabled', font=self.app.FONT_MAIN, width=30)
        self.entry_consultor.grid(row=11, column=1, sticky='w', pady=(0, 10))
        
        # Preview da Foto
        ttk.Label(main_frame, text="Preview da Foto:", font=self.app.FONT_BOLD).grid(row=12, column=1, sticky='w', pady=(0, 5))
        self.foto_preview_label = ttk.Label(main_frame, text="Nenhuma foto", bootstyle='secondary', anchor='center')
        self.foto_preview_label.grid(row=13, column=1, sticky='w', pady=(0, 10))
        
        
        # --- Rodapé: Botões de Ação ---
        frame_botoes = ttk.Frame(self, padding=10, bootstyle='secondary')
        frame_botoes.pack(fill='x', side='bottom') # Fica fixo no rodapé
        frame_botoes.grid_columnconfigure(0, weight=1) # Espaço
        
        self.btn_salvar = ttk.Button(frame_botoes, text="Salvar Item", style='success.TButton', command=self.save_item, state='disabled')
        self.btn_salvar.grid(row=0, column=1, padx=10, ipady=5)
        
        # --- ESTA É A CORREÇÃO ---
        # Adicionado 'self.' ao 'btn_cancelar'
        self.btn_cancelar = ttk.Button(frame_botoes, text="Cancelar", style='light.TButton', command=self.on_close)
        self.btn_cancelar.grid(row=0, column=2, ipady=5)
        # --- FIM DA CORREÇÃO ---
        
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def open_camera(self):
        if not OPENCV_DISPONIVEL:
            messagebox.showerror("Erro", "OpenCV não está instalado. Não é possível usar a câmera.", parent=self)
            return

        # Libera a câmera antiga, se estiver ligada
        if self.webcam_feed and self.webcam_feed.isOpened():
            self.webcam_feed.release()
            self.webcam_feed = None # Garante que está fechado
            # Volta para o placeholder visual
            self.camera_label.config(image=self.camera_placeholder_tk)
            self.camera_label.image = self.camera_placeholder_tk
            self.btn_ligar_camera.config(text="Ligar Câmera")
            self.btn_tirar_foto.config(state='disabled')
            return # Se clicou para desligar, para aqui

        # Tenta abrir a câmera (0 é a padrão, 1 seria uma segunda, etc.)
        self.webcam_feed = cv2.VideoCapture(self.camera_index)
        
        if not self.webcam_feed.isOpened():
            # Se falhou, tenta a próxima câmera (looping de 0 a 2)
            self.camera_index = (self.camera_index + 1) % 3
            self.webcam_feed = cv2.VideoCapture(self.camera_index)
            
            if not self.webcam_feed.isOpened():
                messagebox.showerror("Erro de Câmera", "Não foi possível encontrar uma webcam.", parent=self)
                return
        
        # Define a resolução (baixa) para ser rápido
        self.webcam_feed.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
        self.webcam_feed.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)
        
        # Atualiza o texto do botão para "Desligar/Trocar Câmera"
        self.btn_ligar_camera.config(text="Desligar/Trocar Câmera")
        self.btn_tirar_foto.config(state='normal') # Habilita o botão de tirar foto
        
        # Inicia o loop de atualização do vídeo
        self.update_webcam_feed()

    def update_webcam_feed(self):
        if not (self.webcam_feed and self.webcam_feed.isOpened()):
            return # Para o loop se a câmera foi desligada ou nunca ligou
            
        ret, frame = self.webcam_feed.read()
        if ret:
            # Converte a imagem do OpenCV (BGR) para PIL (RGB)
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img_pil = Image.fromarray(frame_rgb)
            img_tk = ImageTk.PhotoImage(image=img_pil)
            
            # Atualiza o label da câmera
            self.camera_label.config(image=img_tk, text="")
            self.camera_label.image = img_tk
        
        # Repete a função a cada 15ms
        self.after(15, self.update_webcam_feed)

    def take_picture(self):
        if not (self.webcam_feed and self.webcam_feed.isOpened()):
            messagebox.showwarning("Sem Câmera", "A câmera não está ligada. Clique em 'Ligar Câmera' primeiro.", parent=self)
            return
            
        ret, frame = self.webcam_feed.read()
        if ret:
            # Converte BGR -> RGB e salva a imagem PIL
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            self.foto_capturada_pil = Image.fromarray(frame_rgb)
            
            # Cria uma versão menor (thumbnail) para exibir no formulário
            foto_preview = self.foto_capturada_pil.copy()
            foto_preview.thumbnail((150, 150))
            self.foto_capturada_tk = ImageTk.PhotoImage(image=foto_preview)

            # Atualiza o label da foto no local correto
            self.foto_preview_label.config(image=self.foto_capturada_tk, text="")
            self.foto_preview_label.image = self.foto_capturada_tk # Guarda a referência

            # Habilita o botão de salvar
            self.btn_salvar.config(state='normal')
            self.entry_titulo.focus_set()

    def save_item(self):
        # --- ESTA É A FUNÇÃO ATUALIZADA ---
        
        # 1. Pega os dados
        titulo = self.entry_titulo.get().strip()
        descricao = self.entry_descricao.get("1.0", "end-1c").strip()
        n_controle = self.entry_controle.get().strip()
        data_achado = self.entry_data_achado.entry.get()
        data_cadastro = self.data_cadastro_var.get()
        consultor_cadastro = self.consultor_var.get()
        
        if not titulo or not n_controle:
            messagebox.showwarning("Campos Vazios", "O 'Título do Item' e o 'Nº de Controle' são obrigatórios.", parent=self)
            return
            
        if self.foto_capturada_pil is None:
            messagebox.showwarning("Sem Foto", "Você deve tirar uma foto do item antes de salvar.", parent=self)
            return
            
        # 2. Desabilita botões e mostra cursor de espera
        self.btn_salvar.config(text="Salvando...", state='disabled')
        self.btn_cancelar.config(state='disabled') # <-- AGORA FUNCIONA
        self.app.config(cursor="watch")
        self.update_idletasks() # Força a atualização da UI

        try:
            # 3. Faz o upload da foto para o ImageKit
            foto_url = fm.upload_foto_item_imagekit(self.foto_capturada_pil, n_controle)
            
            if not foto_url:
                # Erro já foi mostrado pelo firebase_manager
                raise Exception("Falha no upload da foto.")

            # 4. Prepara os dados para o RTDB
            item_data = {
                "id_controle": n_controle,
                "titulo": titulo,
                "descricao": descricao,
                "foto_url": foto_url, # <-- USA A URL REAL DO IMAGEKIT
                "status": "Pendente",
                "data_achado": data_achado,
                "data_cadastro": data_cadastro,
                "consultor_cadastro_nome": consultor_cadastro,
                "data_entrega": "",
                "consultor_entrega_nome": "",
                "cliente_nome": "",
                "cliente_cpf": "",
                "cliente_tipo": "",
                "assinatura_url": ""
            }
            
            # 5. Salva os dados no RTDB
            if not fm.salvar_novo_item_achado(item_data):
                # Erro já foi mostrado pelo firebase_manager
                raise Exception("Falha ao salvar dados no RTDB.")
            
            # 6. Sucesso!
            self.app.show_toast("Sucesso!", f"Item '{titulo}' cadastrado no Firebase.")
            self.on_close() # Fecha o popup

        except Exception as e:
            print(f"Erro em save_item: {e}")
            # Habilita os botões novamente se der erro
            self.btn_salvar.config(text="Salvar Item", state='normal')
            self.btn_cancelar.config(state='normal')
            self.app.config(cursor="")

        finally:
            # Garante que os botões e cursor voltem ao normal
            # (Mesmo que o código acima falhe, isso garante que o popup não trave)
            self.btn_salvar.config(text="Salvar Item", state='normal')
            self.btn_cancelar.config(state='normal')
            self.app.config(cursor="")


    def on_close(self):
        # Desliga a câmera antes de fechar a janela
        if self.webcam_feed and self.webcam_feed.isOpened():
            self.webcam_feed.release()
            self.webcam_feed = None # Garante que está fechado
        self.destroy()


# --- A TELA PRINCIPAL DE "ACHADOS E PERDIDOS" ---

class AchadosView:
    
    def __init__(self, app, main_frame):
        """
        Constrói a tela de Achados e Perdidos.
        'app' é a referência à classe principal (App)
        'main_frame' é o frame onde esta tela será desenhada
        """
        self.app = app
        self.main_frame = main_frame

        # --- Frame Superior: Título e Botão ---
        frame_header = ttk.Frame(self.main_frame)
        frame_header.pack(fill='x', pady=(0, 15), anchor='w')

        ttk.Label(frame_header, text="Controle de Achados e Perdidos", font=self.app.FONT_TITLE).pack(side='left')
        
        # --- NOVO BOTÃO DE CADASTRO ---
        btn_novo_item = ttk.Button(
            frame_header, 
            text="Cadastrar Novo Item", 
            style='success.TButton',
            command=self.abrir_popup_cadastro
        )
        btn_novo_item.pack(side='right')

        # --- TODO: Adicionar o resto (Busca, Filtros, Lista) ---
        ttk.Label(self.main_frame, text="Em construção... (A lista de itens aparecerá aqui)").pack(pady=20)
        
    
    def abrir_popup_cadastro(self):
        """Abre a nova janela (Toplevel) para cadastrar um item."""
        popup = CadastroItemPopup(self.app, self)