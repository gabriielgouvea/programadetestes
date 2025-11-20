# -*- coding: utf-8 -*-

"""
Arquivo: view_developer.py
Descrição: Contém a classe DeveloperView.
(v5.16.0 - COMPLETO: Ficha Cadastral Completa + Marcas + Auditoria)
"""

import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from ttkbootstrap.widgets import DateEntry
from tkinter import messagebox, Toplevel, Entry, Button, StringVar, \
    PhotoImage, Listbox, filedialog, END, ANCHOR, IntVar, DoubleVar
import os
import shutil
from datetime import date, datetime

# --- Importa o gerenciador do Firebase ---
import firebase_manager as fm

# --- Importa as funções de utilidade ---
from app_utils import formatar_data, formatar_reais

class DeveloperView:

    def __init__(self, app, main_frame):
        """
        Constrói a tela da Área do Desenvolvedor.
        """
        self.app = app
        self.main_frame = main_frame

        # Carrega os dados mais recentes
        self.lista_completa_consultores = fm.carregar_consultores()
        self.dados_marcas = fm.carregar_marcas()
        self.dados_folgas = fm.carregar_folgas()
        self.dados_caixa = fm.carregar_caixa_comissao() 
        
        ttk.Label(self.main_frame, text="Área do Desenvolvedor & Admin", font=self.app.FONT_TITLE).pack(pady=(0, 10), anchor='w')

        # 1. Cria o Notebook
        notebook = ttk.Notebook(self.main_frame)
        notebook.pack(fill='both', expand=True)

        # 2. Cria os frames para cada aba
        tab_consultores = ttk.Frame(notebook, padding=10)
        tab_marcas = ttk.Frame(notebook, padding=10)
        tab_fechamentos = ttk.Frame(notebook, padding=10) 
        
        # Renomeado para refletir a nova funcionalidade
        notebook.add(tab_consultores, text=' 👤 Dados Cadastrais (Holerite) ')
        notebook.add(tab_marcas, text=' Gerenciar Marcas ')
        notebook.add(tab_fechamentos, text=' 🛡️ Gerenciar Fechamentos (Admin) ')

        # 3. Preenche cada aba
        self.create_dev_tab_consultores(tab_consultores)
        self.create_dev_tab_marcas(tab_marcas)
        self.create_dev_tab_fechamentos(tab_fechamentos)

    # --- ABA 1: GERENCIAR CONSULTORES (ATUALIZADA COM FICHA COMPLETA) ---

    def create_dev_tab_consultores(self, parent_frame):
        """Cria o conteúdo da aba 'Dados Cadastrais'."""
        pw = ttk.Panedwindow(parent_frame, orient='horizontal') 
        pw.pack(fill='both', expand=True)

        # --- Lado Esquerdo: Lista ---
        frame_lista = ttk.Frame(pw, padding=10)
        pw.add(frame_lista, weight=1)

        ttk.Label(frame_lista, text="Usuários (Login)", font=self.app.FONT_BOLD).pack(anchor='w')

        cols = ('nome', 'foto_path')
        self.dev_tree = ttk.Treeview(frame_lista, columns=cols, show='headings', height=15, selectmode='browse')
        self.dev_tree.heading('nome', text='Apelido / Login')
        self.dev_tree.heading('foto_path', text='Arquivo Foto')
        self.dev_tree.column('nome', width=150)
        self.dev_tree.column('foto_path', width=100)
        self.dev_tree.pack(fill='both', expand=True, pady=10)

        self.dev_tree.bind('<<TreeviewSelect>>', self.on_dev_tree_select)

        frame_lista_botoes = ttk.Frame(frame_lista)
        frame_lista_botoes.pack(fill='x', pady=5)
        ttk.Button(frame_lista_botoes, text="+ Novo", style="success.TButton", command=self.dev_adicionar_novo).pack(side='left', padx=5)
        ttk.Button(frame_lista_botoes, text="- Excluir", style="danger.Outline.TButton", command=self.dev_excluir_selecionado).pack(side='left', padx=5)

        # --- Lado Direito: Formulário Completo ---
        frame_form = ttk.Frame(pw, padding=10)
        pw.add(frame_form, weight=3) # Mais largo para caber os dados

        # Cabeçalho (Foto e Botões)
        frame_header = ttk.Frame(frame_form)
        frame_header.pack(fill='x', pady=(0,10))
        
        self.dev_foto_label = ttk.Label(frame_header, image=self.app.default_profile_photo, background=self.app.COLOR_SIDEBAR_LIGHT)
        self.dev_foto_label.pack(side='left', padx=(0,15))
        
        frame_header_btns = ttk.Frame(frame_header)
        frame_header_btns.pack(side='left', fill='both')
        
        ttk.Button(frame_header_btns, text="Carregar Foto...", command=self.dev_fazer_upload, style='secondary.Outline.TButton').pack(anchor='w', pady=2)
        self.dev_folgas_button = ttk.Button(frame_header_btns, text="📅 Escala de Folgas", command=self.show_folgas_popup, style="info.Outline.TButton", state='disabled')
        self.dev_folgas_button.pack(anchor='w', pady=2)

        # Campos de Texto (Grid Layout)
        frame_grid = ttk.Frame(frame_form)
        frame_grid.pack(fill='x', pady=10)
        
        # Variáveis
        self.dev_nome_var = StringVar() # Login/Apelido
        self.dev_foto_path_var = StringVar()
        
        # Novas Variáveis para o Holerite
        self.var_nome_completo = StringVar()
        self.var_cpf = StringVar()
        self.var_nascimento = StringVar()
        self.var_email = StringVar()
        self.var_telefone = StringVar()

        def criar_campo(lbl, var, row, col, width=30):
            ttk.Label(frame_grid, text=lbl, font=("Segoe UI", 9)).grid(row=row, column=col, sticky='w', padx=5, pady=(5,0))
            e = ttk.Entry(frame_grid, textvariable=var, width=width, font=self.app.FONT_MAIN)
            e.grid(row=row+1, column=col, sticky='w', padx=5, pady=(0,10))
            return e

        # Linha 0
        criar_campo("Usuário (Apelido de Login) *", self.dev_nome_var, 0, 0)
        criar_campo("Nome Completo (Para Holerite) *", self.var_nome_completo, 0, 1, width=45)
        
        # Linha 2
        criar_campo("CPF", self.var_cpf, 2, 0)
        criar_campo("Data de Nascimento", self.var_nascimento, 2, 1)
        
        # Linha 4
        criar_campo("Email", self.var_email, 4, 0, width=35)
        criar_campo("Telefone", self.var_telefone, 4, 1)
        
        # Linha 6 (Foto Path - Readonly)
        ttk.Label(frame_grid, text="Arquivo da Foto (Sistema)", font=("Segoe UI", 8)).grid(row=6, column=0, columnspan=2, sticky='w', padx=5)
        ttk.Entry(frame_grid, textvariable=self.dev_foto_path_var, state='readonly', width=80).grid(row=7, column=0, columnspan=2, sticky='w', padx=5)

        # Botão Salvar
        ttk.Separator(frame_form).pack(fill='x', pady=15)
        ttk.Button(frame_form, text="💾 Salvar Dados Cadastrais", style="primary.TButton", command=self.dev_salvar_alteracoes, width=30).pack(pady=5)
        
        self.populate_consultor_tree()

    def populate_consultor_tree(self):
        """Limpa e preenche a Treeview de Consultores."""
        if not hasattr(self, 'dev_tree'): return 
        for item in self.dev_tree.get_children():
            self.dev_tree.delete(item)

        self.app.nomes_consultores = [c['nome'] for c in self.lista_completa_consultores]
        
        for consultor in self.lista_completa_consultores:
            self.dev_tree.insert('', 'end', values=(consultor['nome'], consultor['foto_path']))

        # Limpa o formulário
        for v in [self.dev_nome_var, self.dev_foto_path_var, self.var_nome_completo, self.var_cpf, self.var_nascimento, self.var_email, self.var_telefone]:
            v.set("")
        
        self.app.load_profile_picture("", size=self.app.PROFILE_PIC_SIZE, is_dev_preview=True)
        if hasattr(self, 'dev_foto_label'):
             self.dev_foto_label.config(image=self.app.dev_preview_photo_tk)
        
        if hasattr(self, 'dev_folgas_button'):
            self.dev_folgas_button.config(state='disabled')

    def on_dev_tree_select(self, event=None):
        """Chamado quando um item é selecionado na Treeview."""
        selected_iid = self.dev_tree.focus()
        if not selected_iid:
            self.dev_folgas_button.config(state='disabled') 
            return

        values = self.dev_tree.item(selected_iid, 'values')
        nome_login, foto_path = values[0], values[1]

        # Recupera dados completos do objeto na lista
        dados = next((c for c in self.lista_completa_consultores if c['nome'] == nome_login), {})

        self.dev_nome_var.set(nome_login)
        self.dev_foto_path_var.set(foto_path)
        
        # Preenche novos campos (se existirem, senão usa string vazia ou fallback)
        # Se 'nome_completo' não existir, usa o login como placeholder
        self.var_nome_completo.set(dados.get('nome_completo', dados.get('nome', ''))) 
        self.var_cpf.set(dados.get('cpf', ''))
        self.var_nascimento.set(dados.get('nascimento', ''))
        self.var_email.set(dados.get('email', ''))
        self.var_telefone.set(dados.get('telefone', ''))

        self.app.load_profile_picture(foto_path, size=self.app.PROFILE_PIC_SIZE, is_dev_preview=True)
        self.dev_foto_label.config(image=self.app.dev_preview_photo_tk)
        self.dev_folgas_button.config(state='normal')

    def dev_fazer_upload(self, is_marca_upload=False, parent_popup=None):
        """Abre a janela de diálogo para o upload de uma nova foto."""
        parent = parent_popup if parent_popup else self.app
        
        filepath = filedialog.askopenfilename(
            parent=parent,
            title="Selecionar foto",
            filetypes=[("Imagens", "*.png *.jpg *.jpeg *.bmp"), ("Todos os arquivos", "*.*")]
        )
        if not filepath: return

        filename = os.path.basename(filepath)
        dest_path = os.path.join(self.app.DATA_FOLDER_PATH, filename)
        
        try:
            if os.path.abspath(filepath) == os.path.abspath(dest_path):
                self.app.show_toast("Foto Selecionada", f"A imagem {filename} já estava na pasta 'data'.")
            else:
                shutil.copy(filepath, dest_path)
                self.app.show_toast("Upload Concluído", f"Arquivo {filename} salvo em 'data'.")
        except Exception as e:
            messagebox.showerror("Erro no Upload", f"Não foi possível copiar o arquivo: {e}", parent=parent)
            return 

        # Atualiza o formulário correto
        if is_marca_upload:
            self.dev_marca_logo_path_var.set(filename)
            self.app.load_image_no_circular(filename, size=self.app.LOGO_MARCA_SIZE, is_dev_preview=True)
            self.dev_marca_logo_label.config(image=self.app.dev_preview_logo_tk)
        else:
            self.dev_foto_path_var.set(filename)
            self.app.load_profile_picture(filename, size=self.app.PROFILE_PIC_SIZE, is_dev_preview=True)
            self.dev_foto_label.config(image=self.app.dev_preview_photo_tk) 

    def dev_salvar_alteracoes(self):
        """Salva as mudanças feitas no formulário no consultor selecionado."""
        selected_iid = self.dev_tree.focus()
        if not selected_iid:
            messagebox.showwarning("Nenhum Consultor", "Selecione um consultor na lista para salvar.")
            return

        original_nome = self.dev_tree.item(selected_iid, 'values')[0]
        novo_nome = self.dev_nome_var.get().strip()
        nova_foto = self.dev_foto_path_var.get()

        if not novo_nome:
            messagebox.showwarning("Campo Vazio", "O Usuário (Login) não pode estar vazio.")
            return

        # Recarrega a lista do DB
        lista_atual_db = fm.carregar_consultores()
        
        consultor = next((c for c in lista_atual_db if c['nome'] == original_nome), None)
        
        if not consultor:
            messagebox.showerror("Erro de Sincronia", f"O consultor '{original_nome}' não foi encontrado no DB.")
            self.lista_completa_consultores = lista_atual_db
            self.populate_consultor_tree()
            return

        # Atualiza Campos Básicos
        consultor['nome'] = novo_nome
        consultor['foto_path'] = nova_foto
        
        # Atualiza Novos Campos
        consultor['nome_completo'] = self.var_nome_completo.get().strip().upper()
        consultor['cpf'] = self.var_cpf.get().strip()
        consultor['nascimento'] = self.var_nascimento.get().strip()
        consultor['email'] = self.var_email.get().strip()
        consultor['telefone'] = self.var_telefone.get().strip()

        if fm.salvar_consultores(lista_atual_db):
            self.lista_completa_consultores = lista_atual_db
            self.populate_consultor_tree()
            self.app.show_toast("Sucesso!", "Ficha cadastral atualizada.")

            # Verifica se precisa atualizar o nome nas folgas (Se mudou o login)
            if original_nome != novo_nome:
                self.dados_folgas = fm.carregar_folgas()
                if original_nome in self.dados_folgas:
                    self.dados_folgas[novo_nome] = self.dados_folgas.pop(original_nome)
                    fm.salvar_folgas(self.dados_folgas)
        else:
            messagebox.showerror("Erro de Firebase", "Não foi possível salvar as alterações.")

    def dev_adicionar_novo(self):
        """Adiciona um novo consultor à lista."""
        novo_nome = "NOVO_USUARIO"
        nova_foto = "default_profile.png"

        lista_atual_db = fm.carregar_consultores() 
        
        if any(c['nome'] == novo_nome for c in lista_atual_db):
            messagebox.showwarning("Erro", "Já existe um 'NOVO_USUARIO'. Renomeie-o antes de adicionar outro.")
            return

        lista_atual_db.append({
            "nome": novo_nome, 
            "foto_path": nova_foto,
            "nome_completo": "NOVO CONSULTOR",
            "cpf": "",
            "email": ""
        })

        if fm.salvar_consultores(lista_atual_db):
            self.lista_completa_consultores = lista_atual_db
            self.populate_consultor_tree() 
            try:
                last_item = self.dev_tree.get_children()[-1]
                self.dev_tree.selection_set(last_item)
                self.dev_tree.focus(last_item)
                self.on_dev_tree_select() 
            except: pass
            self.app.show_toast("Adicionado", "Novo consultor criado. Edite a ficha ao lado.")
        else:
             messagebox.showerror("Erro de Firebase", "Não foi possível salvar o novo consultor.")

    def dev_excluir_selecionado(self):
        """Exclui o consultor selecionado da lista."""
        selected_iid = self.dev_tree.focus()
        if not selected_iid:
            messagebox.showwarning("Nenhum Consultor", "Selecione um consultor na lista para excluir.")
            return

        original_nome = self.dev_tree.item(selected_iid, 'values')[0]

        if not messagebox.askyesno("Confirmar Exclusão", f"Tem certeza que deseja excluir:\n\n{original_nome}\n\nEsta ação apaga todos os dados cadastrais."):
            return

        lista_atual_db = fm.carregar_consultores()
        nova_lista_db = [c for c in lista_atual_db if c['nome'] != original_nome]
        
        if len(nova_lista_db) == len(lista_atual_db):
            messagebox.showerror("Erro", "Consultor não encontrado no DB.")
            return

        if fm.salvar_consultores(nova_lista_db):
            self.lista_completa_consultores = nova_lista_db
            self.populate_consultor_tree()
            self.app.show_toast("Excluído", f"{original_nome} foi removido.")

            self.dados_folgas = fm.carregar_folgas()
            if original_nome in self.dados_folgas:
                if messagebox.askyesno("Remover Folgas", f"Deseja também remover as folgas cadastradas para '{original_nome}'?"):
                    self.dados_folgas.pop(original_nome)
                    fm.salvar_folgas(self.dados_folgas)
        else:
            messagebox.showerror("Erro de Firebase", "Não foi possível excluir o consultor.")


    # --- ABA 2: GERENCIAR MARCAS (MANTIDO INTEGRALMENTE) ---

    def create_dev_tab_marcas(self, parent_frame):
        """Cria o conteúdo da aba 'Gerenciar Marcas'."""
        pw = ttk.Panedwindow(parent_frame, orient='horizontal')
        pw.pack(fill='both', expand=True)

        # --- Lado Esquerdo: Lista de Marcas ---
        frame_lista = ttk.Frame(pw, padding=10)
        pw.add(frame_lista, weight=1)

        ttk.Label(frame_lista, text="Marcas Cadastradas", font=self.app.FONT_BOLD).pack(anchor='w')

        cols = ('nome_marca', 'data_att', 'qtd_pessoas')
        self.dev_tree_marcas = ttk.Treeview(frame_lista, columns=cols, show='headings', height=15, selectmode='browse')
        self.dev_tree_marcas.heading('nome_marca', text='Nome da Marca')
        self.dev_tree_marcas.heading('data_att', text='Última Atualização')
        self.dev_tree_marcas.heading('qtd_pessoas', text='Qtd. Pessoas')
        self.dev_tree_marcas.column('nome_marca', width=200)
        self.dev_tree_marcas.column('data_att', width=120, anchor='center')
        self.dev_tree_marcas.column('qtd_pessoas', width=80, anchor='center')
        self.dev_tree_marcas.pack(fill='both', expand=True, pady=10)
        
        frame_lista_botoes = ttk.Frame(frame_lista)
        frame_lista_botoes.pack(fill='x', pady=5)
        
        ttk.Button(frame_lista_botoes, text="Adicionar Nova", style="success.TButton", 
                   command=self.dev_adicionar_marca).pack(side='left', padx=5)
                   
        self.dev_btn_editar_marca = ttk.Button(frame_lista_botoes, text="Editar/Ver Pessoas", style="primary.Outline.TButton", 
                                               command=self.show_marca_popup, state='disabled')
        self.dev_btn_editar_marca.pack(side='left', padx=5)

        self.dev_btn_excluir_marca = ttk.Button(frame_lista_botoes, text="Excluir", style="danger.Outline.TButton",
                                                command=self.dev_excluir_marca, state='disabled')
        self.dev_btn_excluir_marca.pack(side='left', padx=5)

        self.dev_tree_marcas.bind('<<TreeviewSelect>>', self.on_dev_tree_marcas_select)
        
        self.populate_marcas_tree() # Preenche a lista

    def populate_marcas_tree(self):
        """Carrega dados do Firebase e preenche a Treeview de Marcas."""
        if not hasattr(self, 'dev_tree_marcas'): return 
        for item in self.dev_tree_marcas.get_children():
            self.dev_tree_marcas.delete(item)
            
        self.dados_marcas = fm.carregar_marcas()
        
        for nome_marca, dados in sorted(self.dados_marcas.items()):
            data_att = dados.get('ultima_atualizacao', 'N/A')
            qtd_pessoas = len(dados.get('pessoas', []))
            self.dev_tree_marcas.insert('', 'end', values=(nome_marca, data_att, qtd_pessoas))
            
        self.on_dev_tree_marcas_select()

    def on_dev_tree_marcas_select(self, event=None):
        """Habilita/desabilita botões de marca ao selecionar."""
        if not hasattr(self, 'dev_tree_marcas'): return
        
        if not self.dev_tree_marcas.focus():
            self.dev_btn_editar_marca.config(state='disabled')
            self.dev_btn_excluir_marca.config(state='disabled')
        else:
            self.dev_btn_editar_marca.config(state='normal')
            self.dev_btn_excluir_marca.config(state='normal')
            
    def dev_adicionar_marca(self):
        """Adiciona uma nova marca padrão ao Firebase."""
        novo_nome = "NOVA MARCA"
        
        self.dados_marcas = fm.carregar_marcas()
        
        if novo_nome in self.dados_marcas:
            messagebox.showwarning("Erro", "Já existe um 'NOVA MARCA'. Renomeie-a antes de adicionar outra.")
            return
            
        self.dados_marcas[novo_nome] = {
            "logo_path": "default_profile.png", 
            "ultima_atualizacao": date.today().strftime("%d/%m/%Y"),
            "pessoas": []
        }
        
        if fm.salvar_marcas(self.dados_marcas):
            self.app.show_toast("Sucesso", "Nova marca criada.")
            self.populate_marcas_tree()
            try:
                for item in self.dev_tree_marcas.get_children():
                    if self.dev_tree_marcas.item(item, 'values')[0] == novo_nome:
                        self.dev_tree_marcas.selection_set(item)
                        self.dev_tree_marcas.focus(item)
                        break
            except:
                pass
        else:
            messagebox.showerror("Erro de Firebase", "Não foi possível salvar a nova marca.")

    def dev_excluir_marca(self):
        """Exclui a marca selecionada."""
        selected_iid = self.dev_tree_marcas.focus()
        if not selected_iid:
            return
            
        nome_marca = self.dev_tree_marcas.item(selected_iid, 'values')[0]
        
        if not messagebox.askyesno("Confirmar Exclusão", f"Tem certeza que deseja excluir a marca:\n\n{nome_marca}\n\nTodas as pessoas cadastradas nela serão perdidas."):
            return
            
        self.dados_marcas = fm.carregar_marcas()
        
        if nome_marca in self.dados_marcas:
            self.dados_marcas.pop(nome_marca)
        
        if fm.salvar_marcas(self.dados_marcas):
            self.app.show_toast("Excluído", f"Marca '{nome_marca}' removida.")
            self.populate_marcas_tree()
        else:
            messagebox.showerror("Erro de Firebase", "Não foi possível excluir a marca.")

    # --- ABA 3: GERENCIAR FECHAMENTOS (ADMIN - NOVO) ---

    def create_dev_tab_fechamentos(self, parent_frame):
        """Cria a aba de auditoria e edição de fechamentos."""
        
        # Topo: Filtros
        frame_filtros = ttk.Frame(parent_frame)
        frame_filtros.pack(fill='x', pady=5)
        
        ttk.Label(frame_filtros, text="Filtrar por Consultor:", font=("Segoe UI", 10, "bold")).pack(side='left', padx=5)
        
        self.cb_filtro_caixa = ttk.Combobox(frame_filtros, values=["Todos"] + self.app.nomes_consultores, state="readonly", width=25)
        self.cb_filtro_caixa.set("Todos")
        self.cb_filtro_caixa.pack(side='left', padx=5)
        self.cb_filtro_caixa.bind("<<ComboboxSelected>>", lambda e: self.populate_fechamentos_tree())
        
        ttk.Button(frame_filtros, text="🔄 Atualizar Lista", command=self.populate_fechamentos_tree, style="secondary.Outline.TButton").pack(side='left', padx=15)
        
        # Tabela Principal
        cols = ('data', 'consultor', 'v_pdf', 'v_planos', 'total', 'id_oculto', 'mes_oculto')
        self.tree_caixa = ttk.Treeview(parent_frame, columns=cols, show='headings', selectmode='browse', height=15)
        
        self.tree_caixa.heading('data', text='Data do Registro')
        self.tree_caixa.heading('consultor', text='Consultor')
        self.tree_caixa.heading('v_pdf', text='Comissão (PDF)')
        self.tree_caixa.heading('v_planos', text='Comissão Planos')
        self.tree_caixa.heading('total', text='Total do Dia')
        
        self.tree_caixa.column('data', width=100, anchor='center')
        self.tree_caixa.column('consultor', width=200, anchor='w')
        self.tree_caixa.column('v_pdf', width=120, anchor='e')
        self.tree_caixa.column('v_planos', width=120, anchor='e')
        self.tree_caixa.column('total', width=120, anchor='e')
        # Colunas ocultas para controle
        self.tree_caixa.column('id_oculto', width=0, stretch=False)
        self.tree_caixa.column('mes_oculto', width=0, stretch=False)
        
        # Scrollbar
        scroll = ttk.Scrollbar(parent_frame, orient="vertical", command=self.tree_caixa.yview)
        self.tree_caixa.configure(yscrollcommand=scroll.set)
        
        self.tree_caixa.pack(side='left', fill='both', expand=True, pady=10)
        scroll.pack(side='right', fill='y', pady=10)
        
        # Botões de Ação (Rodapé)
        frame_actions = ttk.Frame(parent_frame)
        frame_actions.pack(side='bottom', fill='x', pady=10)
        
        ttk.Label(frame_actions, text="Ações Administrativas:", font=("Segoe UI", 10, "bold")).pack(side='left')
        
        ttk.Button(frame_actions, text="✏️ Editar Valores", style="primary.TButton", 
                   command=self.dev_editar_fechamento).pack(side='left', padx=10)
                   
        ttk.Button(frame_actions, text="🗑️ Excluir Registro", style="danger.TButton", 
                   command=self.dev_excluir_fechamento).pack(side='left', padx=0)

        self.populate_fechamentos_tree()

    def populate_fechamentos_tree(self):
        """Preenche a lista de fechamentos (Auditoria)."""
        for i in self.tree_caixa.get_children(): self.tree_caixa.delete(i)
        
        self.dados_caixa = fm.carregar_caixa_comissao() # Atualiza
        filtro = self.cb_filtro_caixa.get()
        
        items_para_exibir = []
        
        # Itera sobre tudo para achatar a estrutura
        for consultor, meses in self.dados_caixa.items():
            if filtro != "Todos" and consultor != filtro:
                continue
                
            for mes_ano, registros in meses.items():
                for id_reg, dados in registros.items():
                    try:
                        # Tenta criar objeto data para ordenar
                        dt_obj = datetime.strptime(dados.get('data'), "%d/%m/%Y")
                        items_para_exibir.append({
                            'dt_obj': dt_obj,
                            'data_str': dados.get('data'),
                            'consultor': consultor,
                            'v_pdf': dados.get('comissao_produtos', 0),
                            'v_planos': dados.get('comissao_planos', 0),
                            'total': dados.get('total_dia', 0),
                            'id': id_reg,
                            'mes': mes_ano
                        })
                    except: pass
        
        # Ordena do mais recente para o mais antigo
        items_para_exibir.sort(key=lambda x: x['dt_obj'], reverse=True)
        
        for it in items_para_exibir:
            self.tree_caixa.insert('', 'end', values=(
                it['data_str'],
                it['consultor'],
                formatar_reais(it['v_pdf']),
                formatar_reais(it['v_planos']),
                formatar_reais(it['total']),
                it['id'],
                it['mes']
            ))

    def dev_excluir_fechamento(self):
        """Remove um registro de fechamento."""
        sel = self.tree_caixa.focus()
        if not sel:
            messagebox.showwarning("Seleção", "Selecione um registro para excluir."); return
            
        vals = self.tree_caixa.item(sel, 'values')
        data_reg, consultor, v_total, id_reg, mes_ano = vals[0], vals[1], vals[4], vals[5], vals[6]
        
        msg = f"ATENÇÃO: Você está prestes a excluir o fechamento de {consultor} do dia {data_reg}.\nValor: {v_total}\n\nEssa ação é irreversível. Confirma?"
        if not messagebox.askyesno("Confirmar Exclusão", msg): return
        
        try:
            self.dados_caixa[consultor][mes_ano].pop(id_reg)
            if fm.salvar_caixa_comissao(self.dados_caixa):
                self.app.show_toast("Sucesso", "Registro excluído.")
                self.populate_fechamentos_tree()
            else:
                messagebox.showerror("Erro", "Falha ao salvar no banco de dados.")
        except Exception as e:
            messagebox.showerror("Erro", f"Erro técnico ao excluir: {e}")

    def dev_editar_fechamento(self):
        """Abre popup para editar os valores de um fechamento."""
        sel = self.tree_caixa.focus()
        if not sel:
            messagebox.showwarning("Seleção", "Selecione um registro para editar."); return

        vals = self.tree_caixa.item(sel, 'values')
        # Recupera dados originais do dict para ter precisão (não usar string formatada)
        consultor, id_reg, mes_ano = vals[1], vals[5], vals[6]
        dados_originais = self.dados_caixa[consultor][mes_ano][id_reg]
        
        # Popup
        popup = Toplevel(self.app)
        popup.title(f"Editar: {consultor}")
        self.app._center_popup(popup, 400, 450)
        
        container = ttk.Frame(popup, padding=20)
        container.pack(fill='both', expand=True)
        
        ttk.Label(container, text=f"Editando registro de {consultor}", font=("Segoe UI", 10, "bold")).pack(pady=(0,15))
        
        # Campos
        ttk.Label(container, text="Data do Registro:").pack(anchor='w')
        ent_data = DateEntry(container, dateformat="%d/%m/%Y", bootstyle='primary')
        ent_data.entry.delete(0, END)
        ent_data.entry.insert(0, dados_originais.get('data'))
        ent_data.pack(fill='x', pady=5)
        
        ttk.Label(container, text="Valor Comissão PDF (R$):").pack(anchor='w')
        var_pdf = DoubleVar(value=dados_originais.get('comissao_produtos', 0.0))
        ent_pdf = ttk.Entry(container, textvariable=var_pdf)
        ent_pdf.pack(fill='x', pady=5)
        
        ttk.Label(container, text="Qtd. Planos:").pack(anchor='w')
        var_qtd = IntVar(value=dados_originais.get('qtd_planos', 0))
        ent_qtd = ttk.Entry(container, textvariable=var_qtd)
        ent_qtd.pack(fill='x', pady=5)
        
        # Atualiza valor total de planos automaticamente
        lbl_total_planos = ttk.Label(container, text=f"Total Planos: {formatar_reais(var_qtd.get()*40)}", bootstyle='info')
        lbl_total_planos.pack(anchor='w')
        
        def update_lbl(*args):
            try: lbl_total_planos.config(text=f"Total Planos: {formatar_reais(var_qtd.get()*40)}")
            except: pass
        var_qtd.trace_add('write', update_lbl)

        def salvar_edicao():
            try:
                nova_data = ent_data.entry.get()
                novo_v_pdf = float(ent_pdf.get())
                # CORREÇÃO DE INDENTAÇÃO AQUI (AGORA CORRETA):
                nova_qtd = int(ent_qtd.get()) 
                novo_v_planos = nova_qtd * 40.0
                novo_total = novo_v_pdf + novo_v_planos
                
                # Verifica se mudou o mês (precisa mover de chave)
                dt_obj = datetime.strptime(nova_data, "%d/%m/%Y")
                novo_mes_ano = dt_obj.strftime("%Y-%m")
                
                registro_atualizado = dados_originais.copy()
                registro_atualizado.update({
                    "data": nova_data,
                    "comissao_produtos": novo_v_pdf,
                    "comissao_planos": novo_v_planos,
                    "qtd_planos": nova_qtd,
                    "total_dia": novo_total
                })
                
                # Se mudou o mês, remove do antigo e põe no novo
                if novo_mes_ano != mes_ano:
                    self.dados_caixa[consultor][mes_ano].pop(id_reg)
                    if novo_mes_ano not in self.dados_caixa[consultor]:
                        self.dados_caixa[consultor][novo_mes_ano] = {}
                    self.dados_caixa[consultor][novo_mes_ano][id_reg] = registro_atualizado
                else:
                    # Mesmo mês, só atualiza
                    self.dados_caixa[consultor][mes_ano][id_reg] = registro_atualizado
                
                if fm.salvar_caixa_comissao(self.dados_caixa):
                    self.app.show_toast("Sucesso", "Registro atualizado.")
                    self.populate_fechamentos_tree()
                    popup.destroy()
                else:
                    messagebox.showerror("Erro", "Falha ao salvar edição.")
                    
            except ValueError:
                messagebox.showerror("Erro", "Valores inválidos. Use ponto para decimais (ex: 45.50).")

        ttk.Button(container, text="Salvar Alterações", style="success.TButton", command=salvar_edicao).pack(side='bottom', fill='x', pady=15)


    # --- POPUPS DE FOLGAS E MARCAS (Código Original) ---

    def show_folgas_popup(self):
        """Mostra um popup para gerenciar a lista de folgas de um consultor."""
        selected_iid = self.dev_tree.focus()
        if not selected_iid:
            return 

        consultor_nome = self.dev_tree.item(selected_iid, 'values')[0]
        self.dados_folgas = fm.carregar_folgas() # Pega dados frescos
        lista_de_datas = self.dados_folgas.get(consultor_nome, [])

        popup = Toplevel(self.app)
        popup.title(f"Ajustar Folgas: {consultor_nome}")
        self.app._center_popup(popup, 500, 400) 

        container = ttk.Frame(popup, padding=15)
        container.pack(fill='both', expand=True)
        container.grid_rowconfigure(1, weight=1)
        container.grid_columnconfigure(0, weight=1)

        frame_add = ttk.Frame(container)
        frame_add.grid(row=0, column=0, columnspan=2, sticky='ew', pady=(0, 10))

        ttk.Label(frame_add, text="Nova Data (dd/mm/aaaa):").pack(side='left')

        entry_data = ttk.Entry(frame_add, width=15)
        entry_data.pack(side='left', padx=10)
        entry_data.bind("<KeyRelease>", lambda e: formatar_data(e, entry_data))

        def on_add_data():
            data_str = entry_data.get()
            if len(data_str) != 10:
                messagebox.showwarning("Data Inválida", "Digite a data completa (dd/mm/aaaa).", parent=popup)
                return
            try:
                datetime.strptime(data_str, "%d/%m/%Y")
            except ValueError:
                messagebox.showwarning("Data Inválida", "A data digitada não é válida.", parent=popup)
                return
            if data_str in listbox_folgas.get(0, END):
                messagebox.showwarning("Data Duplicada", "Esta data já está na lista.", parent=popup)
                return
            listbox_folgas.insert(END, data_str)
            entry_data.delete(0, END)

        btn_add = ttk.Button(frame_add, text="Adicionar", style="success.Outline.TButton", command=on_add_data)
        btn_add.pack(side='left')

        listbox_folgas = Listbox(container, height=10, font=self.app.FONT_MAIN, width=30)
        listbox_folgas.grid(row=1, column=0, sticky='nsew', pady=5)

        scrollbar = ttk.Scrollbar(container, orient='vertical', command=listbox_folgas.yview)
        scrollbar.grid(row=1, column=1, sticky='ns', pady=5)
        listbox_folgas.config(yscrollcommand=scrollbar.set)

        try:
            datas_ordenadas = sorted(lista_de_datas, key=lambda d: datetime.strptime(d.strip(), "%d/%m/%Y"))
        except ValueError:
            datas_ordenadas = lista_de_datas 

        for data in datas_ordenadas:
            listbox_folgas.insert(END, data)

        frame_botoes = ttk.Frame(container)
        frame_botoes.grid(row=2, column=0, columnspan=2, sticky='ew', pady=(10, 0))

        def on_remove_data():
            try:
                listbox_folgas.delete(ANCHOR) 
            except Exception as e:
                print(f"Erro ao remover: {e}")

        btn_remove = ttk.Button(frame_botoes, text="Remover Data Selecionada",
                                style="danger.Outline.TButton", command=on_remove_data)
        btn_remove.pack(side='left')

        def on_save_folgas():
            nova_lista_de_datas = list(listbox_folgas.get(0, END))
            self.dados_folgas[consultor_nome] = nova_lista_de_datas
            if fm.salvar_folgas(self.dados_folgas):
                self.app.show_toast("Sucesso!", f"Folgas de {consultor_nome} salvas na nuvem.")
                popup.destroy()
            else:
                messagebox.showerror("Erro", "Não foi possível salvar as folgas.", parent=popup)

        btn_save = ttk.Button(frame_botoes, text="Salvar e Fechar",
                                style="success.TButton", command=on_save_folgas)
        btn_save.pack(side='right')

    def show_marca_popup(self):
        """Mostra um popup para gerenciar pessoas, logo e data de uma Marca."""
        selected_iid = self.dev_tree_marcas.focus()
        if not selected_iid:
            return
            
        nome_marca_original = self.dev_tree_marcas.item(selected_iid, 'values')[0]
        
        self.dados_marcas = fm.carregar_marcas() # Pega dados frescos
        dados_marca = self.dados_marcas.get(nome_marca_original)
        
        if not dados_marca:
            messagebox.showerror("Erro", "Não foi possível encontrar os dados desta marca. A lista pode estar desatualizada.")
            self.populate_marcas_tree()
            return
            
        lista_de_pessoas = dados_marca.get("pessoas", [])
        logo_path_atual = dados_marca.get("logo_path", "default_profile.png")
        data_att_atual = dados_marca.get("ultima_atualizacao", date.today().strftime("%d/%m/%Y"))

        popup = Toplevel(self.app)
        popup.title(f"Editar Marca: {nome_marca_original}")
        self.app._center_popup(popup, 700, 650)
        
        pw = ttk.Panedwindow(popup, orient='horizontal')
        pw.pack(fill='both', expand=True)

        # --- Painel Esquerdo: Detalhes da Marca ---
        frame_detalhes = ttk.Frame(pw, padding=15)
        pw.add(frame_detalhes, weight=1)

        ttk.Label(frame_detalhes, text="Detalhes da Marca", font=self.app.FONT_BOLD).pack(anchor='w', pady=(0,10))
        ttk.Label(frame_detalhes, text="Logo:").pack(anchor='w', pady=(5, 2))
        self.dev_marca_logo_label = ttk.Label(frame_detalhes, image=self.app.default_logo_photo)
        self.dev_marca_logo_label.pack(anchor='w', pady=5)
        
        btn_upload_logo = ttk.Button(frame_detalhes, text="Fazer Upload de Nova Logo...", 
                                     command=lambda: self.dev_fazer_upload(is_marca_upload=True, parent_popup=popup))
        btn_upload_logo.pack(anchor='w', pady=5)

        ttk.Label(frame_detalhes, text="Caminho da Logo:").pack(anchor='w', pady=(10, 2))
        self.dev_marca_logo_path_var = StringVar(value=logo_path_atual)
        entry_logo_path = ttk.Entry(frame_detalhes, width=40, font=self.app.FONT_MAIN, 
                                    textvariable=self.dev_marca_logo_path_var, state='readonly')
        entry_logo_path.pack(anchor='w', fill='x', pady=5)
        
        ttk.Label(frame_detalhes, text="Nome da Marca:").pack(anchor='w', pady=(10, 2))
        dev_marca_nome_var = StringVar(value=nome_marca_original)
        entry_marca_nome = ttk.Entry(frame_detalhes, width=40, font=self.app.FONT_MAIN, 
                                     textvariable=dev_marca_nome_var)
        entry_marca_nome.pack(anchor='w', fill='x', pady=5)

        ttk.Label(frame_detalhes, text="Data da Lista (enviada pela gerência):").pack(anchor='w', pady=(10, 2))
        try:
            data_obj_atual = datetime.strptime(data_att_atual, "%d/%m/%Y").date()
        except:
            data_obj_atual = date.today()
            
        entry_data_att = DateEntry(frame_detalhes, dateformat="%d/%m/%Y", startdate=data_obj_atual, bootstyle='primary')
        entry_data_att.pack(anchor='w', fill='x', pady=5)
        
        self.app.load_image_no_circular(logo_path_atual, size=self.app.LOGO_MARCA_SIZE, is_dev_preview=True)
        self.dev_marca_logo_label.config(image=self.app.dev_preview_logo_tk) # Atualiza o label

        # --- Painel Direito: Lista de Pessoas ---
        frame_pessoas = ttk.Frame(pw, padding=15)
        pw.add(frame_pessoas, weight=1)
        
        frame_pessoas.grid_rowconfigure(2, weight=1) 
        frame_pessoas.grid_columnconfigure(0, weight=1)

        ttk.Label(frame_pessoas, text="Pessoas Autorizadas", font=self.app.FONT_BOLD).grid(row=0, column=0, columnspan=2, sticky='w', pady=(0,10))

        frame_add = ttk.Frame(frame_pessoas)
        frame_add.grid(row=1, column=0, columnspan=2, sticky='ew', pady=(0, 10))
        
        entry_pessoa = ttk.Entry(frame_add, width=30, font=self.app.FONT_MAIN)
        entry_pessoa.pack(side='left', fill='x', expand=True, padx=(0,10))

        def on_add_pessoa():
            nome_str = entry_pessoa.get().strip().upper()
            if not nome_str: return
            if nome_str in listbox_pessoas.get(0, END):
                messagebox.showwarning("Nome Duplicado", "Este nome já está na lista.", parent=popup)
                return
            listbox_pessoas.insert(END, nome_str)
            entry_pessoa.delete(0, END)
            entry_pessoa.focus_set()
            
        entry_pessoa.bind("<Return>", lambda e: on_add_pessoa())
        btn_add_pessoa = ttk.Button(frame_add, text="Adicionar", style="success.Outline.TButton", command=on_add_pessoa)
        btn_add_pessoa.pack(side='left')

        listbox_pessoas = Listbox(frame_pessoas, height=15, font=self.app.FONT_MAIN, width=40)
        listbox_pessoas.grid(row=2, column=0, sticky='nsew', pady=5)
        scrollbar = ttk.Scrollbar(frame_pessoas, orient='vertical', command=listbox_pessoas.yview)
        scrollbar.grid(row=2, column=1, sticky='ns', pady=5)
        listbox_pessoas.config(yscrollcommand=scrollbar.set)
        
        for nome in sorted(lista_de_pessoas):
            listbox_pessoas.insert(END, nome)
        
        frame_botoes_lista = ttk.Frame(frame_pessoas)
        frame_botoes_lista.grid(row=3, column=0, columnspan=2, sticky='ew', pady=(10,0))

        btn_remove_pessoa = ttk.Button(frame_botoes_lista, text="Remover Selecionado", 
                                      style="danger.Outline.TButton", 
                                      command=lambda: listbox_pessoas.delete(ANCHOR))
        btn_remove_pessoa.pack(side='left')
        
        btn_importar_lista = ttk.Button(frame_botoes_lista, text="Importar Lista (.txt)", 
                                        style="info.Outline.TButton", 
                                        command=lambda: self.dev_importar_lista_pessoas(listbox_pessoas, popup))
        btn_importar_lista.pack(side='left', padx=10)
        
        # --- Botão de Salvar (no rodapé do popup) ---
        frame_salvar = ttk.Frame(popup, padding=(15,10))
        frame_salvar.pack(fill='x', side='bottom')
        
        def on_save_marca():
            novo_nome_marca = dev_marca_nome_var.get().strip()
            novo_logo_path = self.dev_marca_logo_path_var.get()
            nova_data_att = entry_data_att.entry.get()
            nova_lista_pessoas = list(listbox_pessoas.get(0, END))
            
            if not novo_nome_marca:
                messagebox.showerror("Nome Vazio", "O nome da marca não pode estar vazio.", parent=popup)
                return
                
            dados_marcas_db = fm.carregar_marcas()
            
            if nome_marca_original != novo_nome_marca and nome_marca_original in dados_marcas_db:
                dados_marcas_db.pop(nome_marca_original)
                
            dados_marcas_db[novo_nome_marca] = {
                "logo_path": novo_logo_path,
                "ultima_atualizacao": nova_data_att,
                "pessoas": nova_lista_pessoas
            }
            
            if fm.salvar_marcas(dados_marcas_db):
                self.app.show_toast("Sucesso!", f"Marca '{novo_nome_marca}' salva na nuvem.")
                self.populate_marcas_tree() 
                popup.destroy()
            else:
                messagebox.showerror("Erro de Firebase", "Não foi possível salvar os dados da marca.", parent=popup)

        btn_save_marca = ttk.Button(frame_salvar, text="Salvar Alterações e Fechar",
                                    style="success.TButton", command=on_save_marca)
        btn_save_marca.pack(side='right')

    def dev_importar_lista_pessoas(self, listbox_pessoas, parent_popup):
        """Abre um seletor de arquivos para importar uma lista de nomes .txt."""
        filepath = filedialog.askopenfilename(
            parent=parent_popup,
            title="Selecionar arquivo .txt com nomes (um nome por linha)",
            filetypes=[("Arquivos de Texto", "*.txt"), ("Todos os arquivos", "*.*")]
        )
        if not filepath:
            return

        try:
            current_names = set(listbox_pessoas.get(0, END))
            novos_nomes_adicionados = 0
            
            with open(filepath, 'r', encoding='utf-8') as f:
                for line in f:
                    nome_limpo = line.strip().upper()
                    if nome_limpo and nome_limpo not in current_names:
                        listbox_pessoas.insert(END, nome_limpo)
                        current_names.add(nome_limpo) 
                        novos_nomes_adicionados += 1
            
            messagebox.showinfo("Importação Concluída", 
                                f"{novos_nomes_adicionados} novos nomes foram adicionados à lista.",
                                parent=parent_popup)

        except Exception as e:
            messagebox.showerror("Erro ao Importar",
                                 f"Não foi possível ler o arquivo.\nVerifique se é um .txt válido.\n\nErro: {e}",
                                 parent=parent_popup)