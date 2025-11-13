# -*- coding: utf-8 -*-

"""
Arquivo: view_liberacoes.py
Descrição: Contém a classe LiberacoesView, que constrói e gerencia
a tela de Liberações.
NOVA VERSÃO: Remove ScrolledFrame e adiciona Busca e Paginação.
"""

import ttkbootstrap as ttk
from tkinter import ttk as standard_ttk
from tkinter import messagebox, StringVar
import math # Importa a biblioteca de matemática

# --- Importa o gerenciador do Firebase ---
import firebase_manager as fm

class LiberacoesView:

    def __init__(self, app, main_frame):
        """
        Constrói a tela de Liberações com Busca e Paginação.
        'app' é a referência à classe principal (App)
        'main_frame' é o frame onde esta tela será desenhada
        """
        self.app = app
        self.main_frame = main_frame

        # --- Variáveis de Estado da Tela ---
        self.ITENS_POR_PAGINA = 25
        self.pagina_atual = 1
        self.pessoas_completas = [] # Lista completa da marca selecionada
        self.pessoas_filtradas = [] # Lista após aplicar a busca
        self.search_var = StringVar() # Variável para o campo de busca

        # Carrega os dados das marcas
        self.dados_marcas = fm.carregar_marcas()
        nomes_marcas = sorted(list(self.dados_marcas.keys()))

        # --- Frame Superior (Controles de Seleção e Busca) ---
        frame_controles = ttk.Frame(self.main_frame)
        frame_controles.pack(fill='x', pady=(0, 15), anchor='w')

        # Combobox de Marca
        ttk.Label(frame_controles, text="Selecione a Marca:", font=self.app.FONT_BOLD).pack(side='left', padx=(0, 10))
        self.combo_marcas = ttk.Combobox(frame_controles, state="readonly", width=30, font=self.app.FONT_MAIN)
        self.combo_marcas.pack(side='left', padx=(0, 20))
        
        # --- NOVO: Campo de Busca ---
        ttk.Label(frame_controles, text="Buscar Pessoa:", font=self.app.FONT_BOLD).pack(side='left', padx=(0, 10))
        self.search_entry = ttk.Entry(frame_controles, width=30, textvariable=self.search_var, font=self.app.FONT_MAIN)
        self.search_entry.pack(side='left', fill='x', expand=True)
        
        # --- Frame de Conteúdo (Logo e Lista) ---
        frame_conteudo = ttk.Frame(self.main_frame)
        frame_conteudo.pack(fill='both', expand=True)
        frame_conteudo.grid_rowconfigure(0, weight=1)
        frame_conteudo.grid_columnconfigure(1, weight=1) # Coluna da lista expande

        # --- Sub-Frame Esquerda (Logo e Data) ---
        frame_logo = ttk.Frame(frame_conteudo, padding=(10, 0))
        frame_logo.grid(row=0, column=0, sticky='n', padx=(0, 20))
        
        self.marca_logo_tk = self.app.default_logo_photo # Inicia com o placeholder
        self.liberacoes_logo_label = ttk.Label(frame_logo, image=self.marca_logo_tk)
        self.liberacoes_logo_label.pack(pady=(10, 10))
        self.liberacoes_data_label = ttk.Label(frame_logo, text="Selecione uma marca", style='secondary.TLabel', font=self.app.FONT_SMALL)
        self.liberacoes_data_label.pack(pady=10)

        # --- Sub-Frame Direita (Lista e Paginação) ---
        frame_direita = ttk.Frame(frame_conteudo)
        frame_direita.grid(row=0, column=1, sticky='nsew')
        frame_direita.grid_rowconfigure(1, weight=1) # Faz a área da lista expandir
        frame_direita.grid_columnconfigure(0, weight=1)
        
        ttk.Label(frame_direita, text="Pessoas Autorizadas:", font=self.app.FONT_BOLD).grid(row=0, column=0, sticky='w', pady=(0,5))
        
        # --- SUBSTITUIÇÃO DO ScrolledFrame ---
        # Este é um Frame simples apenas para guardar os nomes da página atual
        self.container_lista = ttk.Frame(frame_direita)
        self.container_lista.grid(row=1, column=0, sticky='nsew')
        
        # --- NOVO: Frame de Paginação ---
        self.frame_paginacao = ttk.Frame(frame_direita)
        self.frame_paginacao.grid(row=2, column=0, sticky='ew', pady=(10,0))
        
        # --- Bindings (Eventos) ---
        self.combo_marcas.bind("<<ComboboxSelected>>", self._on_marca_select)
        self.search_var.trace_add("write", self._on_search) # Chama a função _on_search toda vez que você digita
        
        # --- Carga Inicial ---
        if nomes_marcas:
            self.combo_marcas['values'] = ["Selecione uma marca"] + nomes_marcas
            self.combo_marcas.set("Selecione uma marca")
        else:
            self.combo_marcas.set("Nenhuma marca cadastrada")
            self.combo_marcas.config(state='disabled')
        
        self._atualizar_lista() # Chama a função para mostrar a tela em branco/placeholder


    def _on_marca_select(self, event=None):
        """Chamado quando uma nova marca é selecionada."""
        
        # 1. Pega os dados da marca
        marca_selecionada = self.combo_marcas.get()
        
        # Limpa a busca e reseta a página
        self.search_var.set("")
        self.pagina_atual = 1
        
        if not marca_selecionada or marca_selecionada == "Selecione uma marca":
            self.pessoas_completas = [] # Limpa a lista de nomes
            # Atualiza a logo para o placeholder
            self.app.load_image_no_circular("", size=self.app.LOGO_MARCA_SIZE, is_marca_logo=True) 
            self.liberacoes_logo_label.config(image=self.app.marca_logo_tk)
            self.liberacoes_data_label.config(text="Selecione uma marca")
        else:
            # Busca os dados da marca selecionada
            dados_marca = self.dados_marcas.get(marca_selecionada)
            if not dados_marca:
                messagebox.showerror("Erro", "Dados da marca não encontrados.")
                self.pessoas_completas = []
            else:
                # Guarda a lista completa de pessoas (já ordenada)
                self.pessoas_completas = sorted(dados_marca.get("pessoas", []), key=str.lower)
                
                # Atualiza a Logo
                logo_path = dados_marca.get("logo_path", "")
                self.app.load_image_no_circular(logo_path, size=self.app.LOGO_MARCA_SIZE, is_marca_logo=True)
                self.liberacoes_logo_label.config(image=self.app.marca_logo_tk)

                # Atualiza a Data
                data_att = dados_marca.get("ultima_atualizacao", "Sem data")
                self.liberacoes_data_label.config(text=f"Lista atualizada em: {data_att}")

        # 2. Chama a função principal para redesenhar a lista
        self._atualizar_lista()

    def _on_search(self, *args):
        """Chamado toda vez que o usuário digita no campo de busca."""
        # Reseta para a página 1 e redesenha a lista
        self.pagina_atual = 1
        self._atualizar_lista()

    def _mudar_pagina(self, nova_pagina):
        """Chamado quando um botão de página (ex: 1, 2, 3) é clicado."""
        self.pagina_atual = nova_pagina
        self._atualizar_lista()

    def _atualizar_lista(self):
        """
        Esta é a função principal.
        Ela filtra a lista (com base na busca) e mostra a página correta.
        """
        
        # --- 1. Filtrar (Busca) ---
        termo = self.search_var.get().lower()
        if not termo:
            # Se a busca está vazia, usa a lista completa da marca
            self.pessoas_filtradas = self.pessoas_completas[:] # Usa uma cópia
        else:
            # Se tem um termo, filtra a lista
            self.pessoas_filtradas = [p for p in self.pessoas_completas if p.lower().startswith(termo)]

        # --- 2. Limpar a Tela ---
        # Limpa a lista de nomes antiga
        for widget in self.container_lista.winfo_children():
            widget.destroy()
        # Limpa os botões de paginação antigos
        for widget in self.frame_paginacao.winfo_children():
            widget.destroy()

        # --- 3. Paginar (Calcular a página) ---
        total_nomes = len(self.pessoas_filtradas)
        if total_nomes == 0:
            total_paginas = 1 # Sempre tem pelo menos a página 1
        else:
            # Calcula o total de páginas (ex: 55 nomes / 25 por pág = 2.2 -> 3 páginas)
            total_paginas = int(math.ceil(total_nomes / self.ITENS_POR_PAGINA))

        # Garante que a página atual não seja inválida (ex: se a busca reduziu de 5 para 1 página)
        self.pagina_atual = max(1, min(self.pagina_atual, total_paginas))

        # Calcula quais nomes mostrar
        inicio_index = (self.pagina_atual - 1) * self.ITENS_POR_PAGINA
        fim_index = inicio_index + self.ITENS_POR_PAGINA
        nomes_para_exibir = self.pessoas_filtradas[inicio_index:fim_index]

        # --- 4. Exibir Nomes ---
        if not nomes_para_exibir:
            msg = "Nenhum resultado encontrado." if termo else "Selecione uma marca para ver a lista."
            ttk.Label(self.container_lista, text=msg, style='secondary.TLabel').pack(padx=10, pady=10, anchor='nw')
        else:
            # Adiciona os nomes da página atual
            for i, nome in enumerate(nomes_para_exibir, start=inicio_index + 1):
                linha_texto = f"{i}. {nome}"
                label_nome = ttk.Label(self.container_lista, text=linha_texto, font=self.app.FONT_MAIN)
                label_nome.pack(padx=10, pady=2, anchor='nw') # Usa .pack() pois o ScrolledFrame foi removido

        # --- 5. Exibir Botões de Paginação ---
        if total_paginas > 1:
            # Container para centralizar os botões
            self.frame_paginacao.grid_columnconfigure(0, weight=1) # Faz a coluna 0 (central) expandir
            btn_container = ttk.Frame(self.frame_paginacao)
            btn_container.grid(row=0, column=0) # Coloca o container no meio
            
            # Botão "Anterior"
            if self.pagina_atual > 1:
                btn_prev = ttk.Button(btn_container, text="« Anterior", 
                                      command=lambda: self._mudar_pagina(self.pagina_atual - 1), 
                                      bootstyle="secondary-outline")
                btn_prev.pack(side='left', padx=2)

            # Botões de Número (Ex: 1, 2, 3)
            # (Vamos fazer a versão simples do Google, com reticências)
            
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