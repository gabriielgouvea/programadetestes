# -*- coding: utf-8 -*-

"""
Arquivo: view_achados.py
Descrição: Contém a classe AchadosView, que constrói e gerencia
a nova tela de Achados e Perdidos.
(v5.6.2 - Correção do layout dos botões 'Ver Detalhes' e 'X')
"""

import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from ttkbootstrap.widgets import DateEntry
from tkinter import messagebox, Toplevel, StringVar, scrolledtext, PhotoImage
from datetime import date, datetime
import os
import math # Para paginação

# --- Importa o gerenciador do Firebase ---
import firebase_manager as fm

# --- Imports para carregar imagens da URL ---
import io
import requests 
from PIL import Image, ImageTk, ImageDraw, ImageFont

# --- Tenta importar o OpenCV (para a webcam) ---
try:
    import cv2
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
        
        self.btn_cancelar = ttk.Button(frame_botoes, text="Cancelar", style='light.TButton', command=self.on_close)
        self.btn_cancelar.grid(row=0, column=2, ipady=5)
        
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
        self.btn_cancelar.config(state='disabled')
        self.app.config(cursor="watch")
        self.update_idletasks() # Força a atualização da UI

        try:
            # 3. Faz o upload da foto para o ImageKit
            foto_url, file_id_foto = fm.upload_foto_item_imagekit(self.foto_capturada_pil, n_controle)
            
            if not foto_url:
                raise Exception("Falha no upload da foto.")

            # 4. Prepara os dados para o RTDB
            item_data = {
                "id_controle": n_controle,
                "titulo": titulo,
                "descricao": descricao,
                "foto_url": foto_url,
                "file_id_foto": file_id_foto, # <-- NOVO: Salva o ID da foto
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
                raise Exception("Falha ao salvar dados no RTDB.")
            
            # 6. SUCESSO!
            self.app.show_toast("Sucesso!", f"Item '{titulo}' cadastrado no Firebase.")
            self.app.config(cursor="")
            self.on_close() # Fecha o popup
            
            # --- ATUALIZA A TELA PRINCIPAL ---
            self.view_achados.recarregar_lista_itens() # <-- Chama a função para recarregar

        except Exception as e:
            # 7. FALHA
            print(f"Erro em save_item: {e}")
            self.btn_salvar.config(text="Salvar Item", state='normal')
            self.btn_cancelar.config(state='normal')
            self.app.config(cursor="")


    def on_close(self):
        # Desliga a câmera antes de fechar a janela
        if self.webcam_feed and self.webcam_feed.isOpened():
            self.webcam_feed.release()
            self.webcam_feed = None # Garante que está fechado
        self.destroy()


# --- NOVO: POPUP DE DETALHES DO ITEM ---

class DetalhesItemPopup(Toplevel):
    def __init__(self, app, item_data, foto_tk):
        super().__init__(app)
        self.app = app
        self.item_data = item_data
        
        self.title(f"Detalhes do Item: {item_data.get('id_controle')}")
        self.app._center_popup(self, 500, 600)
        self.resizable(False, False)
        
        # Frame principal
        main_frame = ttk.Frame(self, padding=20)
        main_frame.pack(fill='both', expand=True)
        
        # Foto (grande)
        foto_label = ttk.Label(main_frame, text="Foto não carregada", bootstyle='secondary')
        if foto_tk:
            foto_label.config(image=foto_tk)
            foto_label.image = foto_tk # Mantém a referência
        foto_label.pack(pady=(0, 15))
        
        # --- Função Helper para criar linhas ---
        def criar_linha_info(label_bold, valor):
            frame_linha = ttk.Frame(main_frame)
            frame_linha.pack(fill='x', pady=2)
            ttk.Label(frame_linha, text=label_bold, font=self.app.FONT_BOLD, width=18, anchor='w').pack(side='left')
            ttk.Label(frame_linha, text=valor, wraplength=300, justify='left').pack(side='left')

        # --- Informações ---
        criar_linha_info("Nº de Controle:", item_data.get('id_controle'))
        criar_linha_info("Título:", item_data.get('titulo'))
        criar_linha_info("Status:", item_data.get('status'))
        
        if item_data.get('descricao'):
            criar_linha_info("Descrição:", item_data.get('descricao'))
            
        ttk.Separator(main_frame).pack(fill='x', pady=10)
        
        criar_linha_info("Data que Achou:", item_data.get('data_achado'))
        criar_linha_info("Data de Cadastro:", item_data.get('data_cadastro'))
        criar_linha_info("Cadastrado por:", item_data.get('consultor_cadastro_nome'))
        
        # Se foi entregue
        if item_data.get('status') == "Entregue":
            ttk.Separator(main_frame).pack(fill='x', pady=10)
            criar_linha_info("Data da Entrega:", item_data.get('data_entrega'))
            criar_linha_info("Entregue por:", item_data.get('consultor_entrega_nome'))
            criar_linha_info("Retirado por:", item_data.get('cliente_nome'))
            criar_linha_info("CPF do Cliente:", item_data.get('cliente_cpf'))
            
        # Se foi baixado
        elif item_data.get('status') == "Baixado":
            ttk.Separator(main_frame).pack(fill='x', pady=10)
            criar_linha_info("Data da Baixa:", item_data.get('data_baixa', 'N/A')) # (campo novo)
            criar_linha_info("Baixado por:", item_data.get('consultor_baixa_nome', 'N/A')) # (campo novo)
            criar_linha_info("Motivo:", item_data.get('motivo_baixa', 'N/A')) # (campo novo)

        # Botão de Fechar
        frame_botoes = ttk.Frame(self, padding=10, bootstyle='secondary')
        frame_botoes.pack(fill='x', side='bottom')
        frame_botoes.grid_columnconfigure(0, weight=1)
        
        btn_fechar = ttk.Button(frame_botoes, text="Fechar", style='light.TButton', command=self.destroy)
        btn_fechar.grid(row=0, column=1, padx=10)


# --- A TELA PRINCIPAL DE "ACHADOS E PERDIDOS" ---

class AchadosView:
    
    def __init__(self, app, main_frame):
        """
        Constrói a tela de Achados e Perdidos.
        """
        self.app = app
        self.main_frame = main_frame
        
        # --- Variáveis de Estado ---
        self.todos_os_itens = {} 
        self.lista_de_fotos_tk = [] # Guarda as miniaturas (thumbnails)
        self.fotos_originais_pil = {} # Guarda as fotos originais para o popup
        
        self.filtro_status_atual = StringVar(value="Pendente") # Filtro padrão
        self.search_var = StringVar()
        self.search_var.trace_add("write", self._on_search_change) # Chama a função ao digitar
        
        self.pagina_atual = 1
        # --- ***** MUDANÇA 1: Itens por página ***** ---
        self.ITENS_POR_PAGINA = 6 # 3 colunas x 2 linhas

        # --- Frame Superior: Título e Botão ---
        frame_header = ttk.Frame(self.main_frame)
        frame_header.pack(fill='x', pady=(0, 10), anchor='w')

        ttk.Label(frame_header, text="Controle de Achados e Perdidos", font=self.app.FONT_TITLE).pack(side='left')
        
        btn_novo_item = ttk.Button(
            frame_header, 
            text="Cadastrar Novo Item", 
            style='success.TButton',
            command=self.abrir_popup_cadastro
        )
        btn_novo_item.pack(side='right')

        # --- Frame de Filtros e Busca ---
        frame_filtros = ttk.Frame(self.main_frame, padding=(0, 10))
        frame_filtros.pack(fill='x')
        
        # Botões de Filtro
        btn_pendentes = ttk.Radiobutton(frame_filtros, text="Pendentes", variable=self.filtro_status_atual, value="Pendente", command=self.redesenhar_lista_filtrada, style='Outline.Toolbutton')
        btn_pendentes.pack(side='left', padx=(0, 5))
        
        btn_entregues = ttk.Radiobutton(frame_filtros, text="Entregues", variable=self.filtro_status_atual, value="Entregue", command=self.redesenhar_lista_filtrada, style='Outline.Toolbutton')
        btn_entregues.pack(side='left', padx=5)
        
        btn_baixados = ttk.Radiobutton(frame_filtros, text="Baixados", variable=self.filtro_status_atual, value="Baixado", command=self.redesenhar_lista_filtrada, style='Outline.Toolbutton')
        btn_baixados.pack(side='left', padx=5)
        
        # Campo de Busca
        self.entry_busca = ttk.Entry(frame_filtros, textvariable=self.search_var, width=40, font=self.app.FONT_SMALL, style='info')
        self.entry_busca.pack(side='right')
        ttk.Label(frame_filtros, text="Buscar:", style='secondary').pack(side='right', padx=(0, 5))

        # --- Linha Separadora ---
        ttk.Separator(self.main_frame, style='secondary').pack(fill='x', pady=10)

        # --- Frame Principal da Lista (NÃO mais ScrolledFrame) ---
        self.frame_conteudo_principal = ttk.Frame(self.main_frame)
        self.frame_conteudo_principal.pack(fill='both', expand=True)
        
        self.lista_container = self.frame_conteudo_principal 
        
        # --- Frame de Paginação (no rodapé) ---
        self.frame_paginacao = ttk.Frame(self.main_frame)
        self.frame_paginacao.pack(fill='x', pady=(10,0))
        
        # --- Carrega os dados ---
        self.recarregar_lista_itens()
        
    
    def abrir_popup_cadastro(self):
        """Abre a nova janela (Toplevel) para cadastrar um item."""
        popup = CadastroItemPopup(self.app, self) 
        
    def recarregar_lista_itens(self):
        """Busca todos os itens do Firebase e os armazena."""
        self.app.config(cursor="watch")
        self.app.update_idletasks()
        
        self.todos_os_itens = fm.carregar_itens_achados()
        
        self.app.config(cursor="")
        self.pagina_atual = 1 
        self.redesenhar_lista_filtrada()

    def redesenhar_lista_filtrada(self, event=None):
        """Limpa a lista e desenha os itens com base nos filtros."""
        
        if event is not None:
            self.pagina_atual = 1
            
        for widget in self.lista_container.winfo_children():
            widget.destroy()
        for widget in self.frame_paginacao.winfo_children():
            widget.destroy()
            
        self.lista_de_fotos_tk = []
        self.fotos_originais_pil = {} 
        
        status_filtro = self.filtro_status_atual.get() 
        termo_busca = self.search_var.get().lower()

        # Filtra os itens
        itens_filtrados = []
        for item_id, item_data in self.todos_os_itens.items():
            if item_data.get('status') == status_filtro:
                if (termo_busca in item_data.get('titulo', '').lower() or 
                    termo_busca in item_data.get('id_controle', '')):
                    itens_filtrados.append(item_data)
        
        try:
            itens_ordenados = sorted(
                itens_filtrados, 
                key=lambda item: datetime.strptime(item.get('data_cadastro', '01/01/1900'), "%d/%m/%Y"), 
                reverse=True
            )
        except:
            itens_ordenados = itens_filtrados
            
        # --- LÓGICA DE PAGINAÇÃO ---
        total_nomes = len(itens_ordenados)
        total_paginas = int(math.ceil(total_nomes / self.ITENS_POR_PAGINA))
        total_paginas = max(1, total_paginas) # Garante pelo menos 1 página
        self.pagina_atual = max(1, min(self.pagina_atual, total_paginas))

        inicio_index = (self.pagina_atual - 1) * self.ITENS_POR_PAGINA
        fim_index = inicio_index + self.ITENS_POR_PAGINA
        itens_para_exibir = itens_ordenados[inicio_index:fim_index]

        # --- Desenha os cards em grade ---
        if not itens_para_exibir:
            msg = "Nenhum item encontrado." if (termo_busca or status_filtro != "Pendente") else "Nenhum item pendente cadastrado."
            ttk.Label(self.lista_container, text=msg, style='secondary').pack(pady=20)
        else:
            # Configura o container da lista para ter 3 colunas
            self.lista_container.grid_columnconfigure((0, 1, 2), weight=1)
            
            for i, item in enumerate(itens_para_exibir):
                col = i % 3 # Coluna 0, 1, ou 2
                row = i // 3 # Linha 0, 1, 2...
                self.criar_card_item(self.lista_container, item, row, col)
        
        # --- Desenha os Botões de Paginação ---
        self.criar_paginacao(total_paginas)
    
    def _on_search_change(self, *args):
        """Chamado quando o usuário digita na busca."""
        self.pagina_atual = 1
        self.redesenhar_lista_filtrada()
        
    def _mudar_pagina(self, nova_pagina):
        """Chamado quando um botão de página é clicado."""
        self.pagina_atual = nova_pagina
        self.redesenhar_lista_filtrada() # Redesenha a lista para a nova página

    def criar_paginacao(self, total_paginas):
        """Cria os botões de navegação de página."""
        if total_paginas <= 1:
            return 

        # Container para centralizar os botões
        self.frame_paginacao.grid_columnconfigure(0, weight=1) 
        btn_container = ttk.Frame(self.frame_paginacao)
        btn_container.grid(row=0, column=0) # Centraliza
        
        # Botão "Anterior"
        if self.pagina_atual > 1:
            btn_prev = ttk.Button(btn_container, text="« Anterior", 
                                    command=lambda: self._mudar_pagina(self.pagina_atual - 1), 
                                    bootstyle="secondary-outline")
            btn_prev.pack(side='left', padx=2)

        # Botões de Número
        inicio_pagina = max(1, self.pagina_atual - 2)
        fim_pagina = min(total_paginas, self.pagina_atual + 2)

        if inicio_pagina > 1:
            btn_primeira = ttk.Button(btn_container, text="1", width=3, command=lambda: self._mudar_pagina(1), bootstyle="secondary-outline")
            btn_primeira.pack(side='left', padx=2)
            if inicio_pagina > 2:
                ttk.Label(btn_container, text="...").pack(side='left', padx=2)

        for i in range(inicio_pagina, fim_pagina + 1):
            style = "primary" if i == self.pagina_atual else "secondary-outline"
            btn_page = ttk.Button(btn_container, text=str(i),
                                    width=3,
                                    command=lambda p=i: self._mudar_pagina(p),
                                    bootstyle=style)
            btn_page.pack(side='left', padx=2)
        
        if fim_pagina < total_paginas:
            if fim_pagina < total_paginas - 1:
                ttk.Label(btn_container, text="...").pack(side='left', padx=2)
            btn_ultima = ttk.Button(btn_container, text=str(total_paginas), width=3, command=lambda: self._mudar_pagina(total_paginas), bootstyle="secondary-outline")
            btn_ultima.pack(side='left', padx=2)

        # Botão "Próximo"
        if self.pagina_atual < total_paginas:
            btn_next = ttk.Button(btn_container, text="Próximo »", 
                                    command=lambda: self._mudar_pagina(self.pagina_atual + 1), 
                                    bootstyle="secondary-outline")
            btn_next.pack(side='left', padx=2)

    def criar_card_item(self, parent, item_data, row, col):
        """Cria o widget (card) para um único item em um layout de grade."""
        
        card = ttk.Frame(parent, padding=10, relief='solid', borderwidth=1, bootstyle='secondary')
        card.grid(row=row, column=col, sticky='nsew', padx=10, pady=10)
        
        # --- Foto ---
        foto_url = item_data.get('foto_url')
        foto_label = ttk.Label(card, text="Sem foto", bootstyle='inverse-secondary', anchor='center')
        foto_label.pack(fill='x', pady=(0, 10))
        
        if foto_url:
            try:
                headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
                response = requests.get(foto_url, headers=headers, timeout=10)
                response.raise_for_status() 

                content_type = response.headers.get('content-type', '')
                if not content_type.startswith('image/'):
                    raise Exception(f"URL retornou um content-type de '{content_type}', não uma imagem.")
                
                img_data = response.content 
                
                img_pil_raw = Image.open(io.BytesIO(img_data))
                
                self.fotos_originais_pil[item_data.get('id_controle')] = img_pil_raw.copy() 
                
                img_pil_thumb = img_pil_raw.copy()
                img_pil_thumb.thumbnail((250, 250)) 
                
                img_tk = ImageTk.PhotoImage(img_pil_thumb)
                
                foto_label.config(image=img_tk, text="")
                foto_label.image = img_tk 
                self.lista_de_fotos_tk.append(img_tk) 
                
            except Exception as e:
                print(f"Erro ao carregar imagem URL ({foto_url}): {e}")
                foto_label.config(text="Erro foto")

        # --- Informações ---
        
        titulo = item_data.get('titulo', 'Sem Título')
        id_controle = item_data.get('id_controle')
        ttk.Label(card, text=f"Nº {id_controle}: {titulo}", font=self.app.FONT_BOLD, bootstyle='inverse-secondary', anchor='center').pack(fill='x')

        data_achado_str = item_data.get('data_achado', 'N/A')
        ttk.Label(card, text=f"Achado em: {data_achado_str}", font=self.app.FONT_SMALL, bootstyle='inverse-secondary', anchor='center').pack(fill='x', pady=(5,0))
        
        # --- Botões de Ação ---
        frame_acoes = ttk.Frame(card, bootstyle='secondary')
        frame_acoes.pack(fill='x', pady=10)
        frame_acoes.grid_columnconfigure((0,1), weight=1)
        
        item_status = item_data.get('status', 'Pendente')
        
        if item_status == "Pendente":
            btn_entregar = ttk.Button(frame_acoes, text="Entregar", style='success.TButton')
            btn_entregar.grid(row=0, column=0, padx=5, sticky='ew')
            btn_baixar = ttk.Button(frame_acoes, text="Dar Baixa", style='danger.Outline.TButton')
            btn_baixar.grid(row=0, column=1, padx=5, sticky='ew')
        
        elif item_status == "Entregue":
            ttk.Label(frame_acoes, text=f"Entregue: {item_data.get('cliente_nome', 'N/A')}", bootstyle='success-inverse').grid(row=0, column=0, columnspan=2)
        
        elif item_status == "Baixado":
             ttk.Label(frame_acoes, text="Item Baixado", bootstyle='danger-inverse').grid(row=0, column=0, columnspan=2)

        # --- ***** CORREÇÃO DO LAYOUT DO BOTÃO ***** ---
        
        # Frame para os botões de baixo
        frame_botoes_inferiores = ttk.Frame(card, bootstyle='secondary')
        frame_botoes_inferiores.pack(fill='x', side='bottom')
        # (Removemos a linha .column_configure que dava erro)

        # Botão de Detalhes
        btn_detalhes = ttk.Button(
            frame_botoes_inferiores, 
            text="Ver Detalhes", 
            style='info.Outline.TButton',
            command=lambda data=item_data: self.abrir_popup_detalhes(data)
        )
        # Usamos .pack() para ser compatível com o 'card'
        btn_detalhes.pack(side='left', fill='x', expand=True) 

        # Botão de Excluir (Lixeira)
        btn_excluir = ttk.Button(
            frame_botoes_inferiores,
            text="X",                             
            width=2,                              
            style='danger.Outline.TButton',
            command=lambda data=item_data: self._on_excluir_item(data)
        )
        # Usamos .pack()
        btn_excluir.pack(side='right', padx=(5,0))
        # --- ***** FIM DA CORREÇÃO ***** ---

    def abrir_popup_detalhes(self, item_data):
        """Abre o novo popup com todos os detalhes do item."""
        
        item_id = item_data.get('id_controle')
        foto_original_pil = self.fotos_originais_pil.get(item_id)
        
        foto_tk = None # Inicia como None
        if foto_original_pil:
            foto_popup_pil = foto_original_pil.copy()
            foto_popup_pil.thumbnail((400, 400))
            foto_tk = ImageTk.PhotoImage(foto_popup_pil)
        
        popup = DetalhesItemPopup(self.app, item_data, foto_tk)

    
    def _on_excluir_item(self, item_data):
        """Chamado pelo botão da lixeira, pede o PIN e exclui."""
        
        item_id = item_data.get('id_controle')
        titulo = item_data.get('titulo')
        file_id_foto = item_data.get('file_id_foto') # Pega o ID da foto
        
        # 1. Pede o PIN de admin
        pin_ok = self.app.show_developer_login(force_pin=True, pin_correto="8274")
        
        if not pin_ok:
            self.app.show_toast("Acesso Negado", "PIN incorreto.", bootstyle='danger')
            return
            
        # 2. Se o PIN estiver OK, pede confirmação
        if not messagebox.askyesno("Confirmar Exclusão", 
                                   f"Tem certeza que deseja excluir permanentemente o item:\n\n"
                                   f"Nº {item_id}: {titulo}\n\n"
                                   "Esta ação não pode ser desfeita.",
                                   parent=self.app):
            return

        # 3. Mostra o cursor de espera
        self.app.config(cursor="watch")
        self.app.update_idletasks()
        
        # 4. Exclui a foto do ImageKit (se tiver um file_id)
        if file_id_foto:
            fm.excluir_foto_item_imagekit(file_id_foto)
        else:
            print(f"Aviso: Item {item_id} não tinha 'file_id_foto' para excluir do ImageKit.")

        # 5. Exclui o item do Firebase (RTDB)
        if fm.excluir_item_achado(item_id):
            self.app.show_toast("Sucesso", f"Item '{titulo}' foi excluído.", bootstyle='success')
        else:
            self.app.show_toast("Erro", "Não foi possível excluir o item do banco de dados.", bootstyle='danger')

        # 6. Recarrega a lista
        self.app.config(cursor="")
        self.recarregar_lista_itens()