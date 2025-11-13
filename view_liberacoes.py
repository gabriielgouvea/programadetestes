# -*- coding: utf-8 -*-

"""
Arquivo: view_liberacoes.py
Descrição: Contém a classe LiberacoesView, que constrói e gerencia
a tela de Liberações. Inclui a correção para o bug 'TclError'.
"""

import ttkbootstrap as ttk
from ttkbootstrap.widgets.scrolled import ScrolledFrame
from tkinter import ttk as standard_ttk
from tkinter import messagebox

# --- Importa o gerenciador do Firebase ---
import firebase_manager as fm

class LiberacoesView:

    def __init__(self, app, main_frame):
        """
        Constrói a tela de Liberações.
        'app' é a referência à classe principal (App)
        'main_frame' é o frame onde esta tela será desenhada
        """
        self.app = app
        self.main_frame = main_frame

        # Carrega os dados das marcas
        self.dados_marcas = fm.carregar_marcas()
        nomes_marcas = sorted(list(self.dados_marcas.keys()))

        # --- Início: Código de create_liberacoes_view ---

        ttk.Label(self.main_frame, text="Controle de Liberações Gerais", font=self.app.FONT_TITLE).pack(pady=(0, 10), anchor='w')

        # --- Frame Superior: Seleção ---
        frame_selecao = ttk.Frame(self.main_frame)
        frame_selecao.pack(fill='x', pady=(0, 15), anchor='w')

        ttk.Label(frame_selecao, text="Selecione a Marca:", font=self.app.FONT_BOLD).pack(side='left', padx=(0, 10))

        self.combo_marcas = ttk.Combobox(frame_selecao, state="readonly", width=40, font=self.app.FONT_MAIN)
        self.combo_marcas.pack(side='left')
        
        # --- Frame de Conteúdo (Logo e Lista) ---
        frame_conteudo = ttk.Frame(self.main_frame)
        frame_conteudo.pack(fill='both', expand=True)
        frame_conteudo.grid_rowconfigure(0, weight=1)
        frame_conteudo.grid_columnconfigure(1, weight=1) # Coluna da lista expande

        # --- Sub-Frame Esquerda (Logo e Data) ---
        frame_logo = ttk.Frame(frame_conteudo, padding=(10, 0))
        frame_logo.grid(row=0, column=0, sticky='n', padx=(0, 20))
        
        # Placeholder da Logo
        self.marca_logo_tk = self.app.default_logo_photo # Inicia com o placeholder
        self.liberacoes_logo_label = ttk.Label(frame_logo, image=self.marca_logo_tk)
        self.liberacoes_logo_label.pack(pady=(10, 10))

        # Placeholder da Data
        self.liberacoes_data_label = ttk.Label(frame_logo, text="Selecione uma marca", style='secondary.TLabel', font=self.app.FONT_SMALL)
        self.liberacoes_data_label.pack(pady=10)

        # --- Sub-Frame Direita (Lista de Nomes) ---
        frame_lista = ttk.Frame(frame_conteudo)
        frame_lista.grid(row=0, column=1, sticky='nsew')
        
        ttk.Label(frame_lista, text="Pessoas Autorizadas:", font=self.app.FONT_BOLD).pack(anchor='w', pady=(0,5))
        
        # --- PONTO CRÍTICO DA CORREÇÃO ---
        # 1. O ScrolledFrame é criado UMA VEZ e nunca mais destruído.
        self.liberacoes_scrolled_frame = ScrolledFrame(frame_lista, autohide=False, bootstyle='secondary-rounded')
        
        # --- Rastreia o ScrolledFrame ---
        self.app.tracked_scrolled_frames.append(self.liberacoes_scrolled_frame)
        
        self.liberacoes_scrolled_frame.pack(fill='both', expand=True)
        
        # 2. Guardamos a referência ao 'container' interno dele.
        # É ESTE 'container_lista' QUE VAMOS LIMPAR.
        self.container_lista = self.liberacoes_scrolled_frame.container
        
        # --- Fim da Correção ---
        
        # --- Lógica de Seleção ---
        # O 'command' do combobox agora chama um método desta classe
        self.combo_marcas.bind("<<ComboboxSelected>>", self._on_marca_select)
        
        # Define o placeholder
        if nomes_marcas:
            self.combo_marcas['values'] = ["Selecione uma marca"] + nomes_marcas
            self.combo_marcas.set("Selecione uma marca")
        else:
            self.combo_marcas.set("Nenhuma marca cadastrada")
            self.combo_marcas.config(state='disabled')
        
        self._on_marca_select() # Chama uma vez para limpar a tela
        # --- Fim: Código de create_liberacoes_view ---


    def _on_marca_select(self, event=None):
        """
        Chamado quando uma marca é selecionada.
        Esta função aplica a CORREÇÃO DO BUG.
        """
        
        # --- INÍCIO DA CORREÇÃO TclError ---
        # 1. Verificamos se o container ainda existe (só por segurança)
        if not self.container_lista.winfo_exists():
            return
            
        # 2. Limpamos APENAS o *conteúdo* do container.
        # NÃO destruímos o self.liberacoes_scrolled_frame.
        for widget in self.container_lista.winfo_children():
            widget.destroy()
        # --- FIM DA CORREÇÃO ---

        marca_selecionada = self.combo_marcas.get()
        
        # Se "Selecione uma marca", limpa a tela
        if not marca_selecionada or marca_selecionada == "Selecione uma marca":
            # Chama a função de carregar imagem do App principal
            self.app.load_image_no_circular("", size=self.app.LOGO_MARCA_SIZE, is_marca_logo=True) 
            self.liberacoes_logo_label.config(image=self.app.marca_logo_tk) # <- CORREÇÃO: ATUALIZA A IMAGEM
            self.liberacoes_data_label.config(text="Selecione uma marca")
            
            label_vazia = ttk.Label(self.container_lista, text="Selecione uma marca para ver a lista.", style='secondary.TLabel')
            label_vazia.pack(padx=10, pady=10, anchor='nw')
            return

        # Pega os dados da marca
        dados_marca = self.dados_marcas.get(marca_selecionada)
        if not dados_marca:
            messagebox.showerror("Erro", "Dados da marca não encontrados.")
            return
        
        # 1. Atualiza a Logo
        logo_path = dados_marca.get("logo_path", "")
        self.app.load_image_no_circular(logo_path, size=self.app.LOGO_MARCA_SIZE, is_marca_logo=True)
        self.liberacoes_logo_label.config(image=self.app.marca_logo_tk) # <- CORREÇÃO: ATUALIZA A IMAGEM

        # 2. Atualiza a Data de Atualização
        data_att = dados_marca.get("ultima_atualizacao", "Sem data")
        self.liberacoes_data_label.config(text=f"Lista atualizada em: {data_att}")

        # 3. Atualiza a Lista de Nomes (no MESMO container)
        pessoas_sorted = sorted(dados_marca.get("pessoas", []), key=str.lower)
        
        if not pessoas_sorted:
            label_vazia = ttk.Label(self.container_lista, text="Nenhuma pessoa cadastrada para esta marca.")
            label_vazia.pack(padx=10, pady=10, anchor='nw')
        else:
            for i, nome in enumerate(pessoas_sorted, 1):
                linha_texto = f"{i}. {nome}"
                label_nome = ttk.Label(self.container_lista, text=linha_texto, font=self.app.FONT_MAIN)
                label_nome.pack(padx=10, pady=2, anchor='nw')