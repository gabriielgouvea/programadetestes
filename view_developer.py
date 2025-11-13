# -*- coding: utf-8 -*-

"""
Arquivo: view_developer.py
Descrição: Contém a classe DeveloperView, que constrói e gerencia
toda a Área do Desenvolvedor (Abas de Consultores e Marcas).
(v5.6.3 - Corrige o preview da logo da marca ao fazer upload)
"""

import ttkbootstrap as ttk
from ttkbootstrap.widgets import DateEntry
from tkinter import messagebox, Toplevel, Entry, Button, StringVar, \
    PhotoImage, Listbox, filedialog, END, ANCHOR
import os
import shutil
from datetime import date, datetime

# --- Importa o gerenciador do Firebase ---
import firebase_manager as fm

# --- Importa as funções de utilidade ---
from app_utils import formatar_data

class DeveloperView:

    def __init__(self, app, main_frame):
        """
        Constrói a tela da Área do Desenvolvedor.
        'app' é a referência à classe principal (App)
        'main_frame' é o frame onde esta tela será desenhada
        """
        self.app = app
        self.main_frame = main_frame

        # Carrega os dados mais recentes
        self.lista_completa_consultores = fm.carregar_consultores()
        self.dados_marcas = fm.carregar_marcas()
        self.dados_folgas = fm.carregar_folgas()
        
        # --- Início: Código de create_developer_area_view ---
        
        ttk.Label(self.main_frame, text="Área do Desenvolvedor", font=self.app.FONT_TITLE).pack(pady=(0, 10), anchor='w')

        # 1. Cria o Notebook (o gerenciador de abas)
        notebook = ttk.Notebook(self.main_frame)
        notebook.pack(fill='both', expand=True)

        # 2. Cria os frames para cada aba
        tab_consultores = ttk.Frame(notebook, padding=10)
        tab_marcas = ttk.Frame(notebook, padding=10)
        
        notebook.add(tab_consultores, text=' Gerenciar Consultores ')
        notebook.add(tab_marcas, text=' Gerenciar Marcas ')

        # 3. Preenche cada aba
        self.create_dev_tab_consultores(tab_consultores)
        self.create_dev_tab_marcas(tab_marcas)

        # --- Fim: Código de create_developer_area_view ---

    # --- ABA 1: GERENCIAR CONSULTORES ---

    def create_dev_tab_consultores(self, parent_frame):
        """Cria o conteúdo da aba 'Gerenciar Consultores'."""
        pw = ttk.Panedwindow(parent_frame, orient='horizontal') 
        pw.pack(fill='both', expand=True)

        # --- Lado Esquerdo: Lista de Consultores ---
        frame_lista = ttk.Frame(pw, padding=10)
        pw.add(frame_lista, weight=1)

        ttk.Label(frame_lista, text="Consultores", font=self.app.FONT_BOLD).pack(anchor='w')

        cols = ('nome', 'foto_path')
        self.dev_tree = ttk.Treeview(frame_lista, columns=cols, show='headings', height=15, selectmode='browse')
        self.dev_tree.heading('nome', text='Nome do Consultor')
        self.dev_tree.heading('foto_path', text='Caminho da Foto')
        self.dev_tree.column('nome', width=200)
        self.dev_tree.column('foto_path', width=150)
        self.dev_tree.pack(fill='both', expand=True, pady=10)

        self.dev_tree.bind('<<TreeviewSelect>>', self.on_dev_tree_select)

        frame_lista_botoes = ttk.Frame(frame_lista)
        frame_lista_botoes.pack(fill='x', pady=5)
        ttk.Button(frame_lista_botoes, text="Adicionar Novo", style="success.TButton", command=self.dev_adicionar_novo).pack(side='left', padx=5)
        ttk.Button(frame_lista_botoes, text="Excluir Selecionado", style="danger.Outline.TButton", command=self.dev_excluir_selecionado).pack(side='left', padx=5)

        # --- Lado Direito: Formulário de Edição ---
        frame_form = ttk.Frame(pw, padding=10)
        pw.add(frame_form, weight=2)

        ttk.Label(frame_form, text="Editar Consultor", font=self.app.FONT_BOLD).pack(anchor='w')

        ttk.Label(frame_form, text="Foto de Perfil:").pack(anchor='w', pady=(10, 2))
        
        self.dev_foto_label = ttk.Label(frame_form, image=self.app.default_profile_photo, background=self.app.COLOR_SIDEBAR_LIGHT)
        self.dev_foto_label.pack(anchor='w', pady=5)
        
        # O 'command' agora chama um método desta classe
        ttk.Button(frame_form, text="Fazer Upload de Nova Foto...", command=self.dev_fazer_upload).pack(anchor='w', pady=5)

        ttk.Label(frame_form, text="Nome:").pack(anchor='w', pady=(10, 2))
        self.dev_nome_var = StringVar()
        self.dev_nome_entry = ttk.Entry(frame_form, width=50, font=self.app.FONT_MAIN, textvariable=self.dev_nome_var)
        self.dev_nome_entry.pack(anchor='w', fill='x', pady=5)

        ttk.Label(frame_form, text="Caminho do Arquivo da Foto:").pack(anchor='w', pady=(10, 2))
        self.dev_foto_path_var = StringVar()
        self.dev_foto_path_entry = ttk.Entry(frame_form, width=50, font=self.app.FONT_MAIN, textvariable=self.dev_foto_path_var, state='readonly')
        self.dev_foto_path_entry.pack(anchor='w', fill='x', pady=5)

        ttk.Button(frame_form, text="Salvar Alterações na Nuvem", style="primary.TButton", command=self.dev_salvar_alteracoes).pack(anchor='w', pady=20)

        self.dev_folgas_button = ttk.Button(frame_form, text="Ajustar Folgas",
                                           command=self.show_folgas_popup,
                                           style="info.TButton",
                                           state='disabled')
        self.dev_folgas_button.pack(anchor='w', pady=5, ipady=4)
        
        self.populate_consultor_tree() # Preenche a lista

    def populate_consultor_tree(self):
        """Limpa e preenche a Treeview de Consultores."""
        if not hasattr(self, 'dev_tree'): return 
        for item in self.dev_tree.get_children():
            self.dev_tree.delete(item)

        # Atualiza a variável de nomes
        self.app.nomes_consultores = [c['nome'] for c in self.lista_completa_consultores]
        
        for consultor in self.lista_completa_consultores:
            self.dev_tree.insert('', 'end', values=(consultor['nome'], consultor['foto_path']))

        # Limpa o formulário da direita
        if hasattr(self, 'dev_nome_var'):
            self.dev_nome_var.set("")
        if hasattr(self, 'dev_foto_path_var'):
            self.dev_foto_path_var.set("")
        
        # Chama o 'load_profile_picture' do app principal
        self.app.load_profile_picture("", size=self.app.PROFILE_PIC_SIZE, is_dev_preview=True)
        # Atualiza o label da foto com a imagem carregada (default)
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
        nome, foto_path = values[0], values[1]

        self.dev_nome_var.set(nome)
        self.dev_foto_path_var.set(foto_path)
        self.app.load_profile_picture(foto_path, size=self.app.PROFILE_PIC_SIZE, is_dev_preview=True)
        self.dev_foto_label.config(image=self.app.dev_preview_photo_tk) # Atualiza o label
        self.dev_folgas_button.config(state='normal')

    def dev_fazer_upload(self, is_marca_upload=False, parent_popup=None):
        """Abre a janela de diálogo para o upload de uma nova foto."""
        parent = parent_popup if parent_popup else self.app
        
        filepath = filedialog.askopenfilename(
            parent=parent,
            title="Selecionar foto",
            filetypes=[("Imagens", "*.png *.jpg *.jpeg *.bmp"), ("Todos os arquivos", "*.*")]
        )
        if not filepath:
            return

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
            return # Sai da função se a cópia falhar

        # Atualiza o formulário correto
        if is_marca_upload:
            self.dev_marca_logo_path_var.set(filename)
            self.app.load_image_no_circular(filename, size=self.app.LOGO_MARCA_SIZE, is_dev_preview=True)
            # --- ***** AQUI ESTÁ A CORREÇÃO ***** ---
            self.dev_marca_logo_label.config(image=self.app.dev_preview_logo_tk)
            # --- ***** FIM DA CORREÇÃO ***** ---
        else:
            self.dev_foto_path_var.set(filename)
            self.app.load_profile_picture(filename, size=self.app.PROFILE_PIC_SIZE, is_dev_preview=True)
            self.dev_foto_label.config(image=self.app.dev_preview_photo_tk) # Atualiza o label

    def dev_salvar_alteracoes(self):
        """Salva as mudanças feitas no formulário no consultor selecionado."""
        selected_iid = self.dev_tree.focus()
        if not selected_iid:
            messagebox.showwarning("Nenhum Consultor", "Selecione um consultor na lista para salvar.")
            return

        original_nome = self.dev_tree.item(selected_iid, 'values')[0]
        novo_nome = self.dev_nome_var.get()
        nova_foto = self.dev_foto_path_var.get()

        if not novo_nome:
            messagebox.showwarning("Campo Vazio", "O nome do consultor não pode estar vazio.")
            return

        # Recarrega a lista do DB para evitar sobreposição
        lista_atual_db = fm.carregar_consultores()
        consultor_encontrado = False
        for consultor in lista_atual_db:
            if consultor['nome'] == original_nome:
                consultor['nome'] = novo_nome
                consultor['foto_path'] = nova_foto
                consultor_encontrado = True
                break

        if not consultor_encontrado:
            messagebox.showerror("Erro de Sincronia", f"O consultor '{original_nome}' não foi encontrado no DB.")
            self.lista_completa_consultores = lista_atual_db
            self.populate_consultor_tree()
            return

        if fm.salvar_consultores(lista_atual_db):
            self.lista_completa_consultores = lista_atual_db
            self.populate_consultor_tree()
            self.app.show_toast("Sucesso!", "Consultor atualizado na nuvem.")

            # Verifica se precisa atualizar o nome nas folgas
            self.dados_folgas = fm.carregar_folgas()
            if original_nome in self.dados_folgas and original_nome != novo_nome:
                if messagebox.askyesno("Atualizar Folgas", f"Deseja transferir os dados de folgas de '{original_nome}' para '{novo_nome}'?"):
                    self.dados_folgas[novo_nome] = self.dados_folgas.pop(original_nome)
                    fm.salvar_folgas(self.dados_folgas)
                    self.app.show_toast("Sucesso!", "Folgas transferidas para o novo nome.")
        else:
            messagebox.showerror("Erro de Firebase", "Não foi possível salvar as alterações.")

    def dev_adicionar_novo(self):
        """Adiciona um novo consultor à lista."""
        novo_nome = "NOVO CONSULTOR"
        nova_foto = "default_profile.png"

        lista_atual_db = fm.carregar_consultores() 
        
        if any(c['nome'] == novo_nome for c in lista_atual_db):
            messagebox.showwarning("Erro", "Já existe um 'NOVO CONSULTOR'. Renomeie-o antes de adicionar outro.")
            self.lista_completa_consultores = lista_atual_db
            self.populate_consultor_tree() 
            return

        lista_atual_db.append({"nome": novo_nome, "foto_path": nova_foto})

        if fm.salvar_consultores(lista_atual_db):
            self.lista_completa_consultores = lista_atual_db
            self.populate_consultor_tree() 
            try:
                last_item = self.dev_tree.get_children()[-1]
                self.dev_tree.selection_set(last_item)
                self.dev_tree.focus(last_item)
                self.on_dev_tree_select() 
            except:
                pass
            self.app.show_toast("Adicionado", "Novo consultor criado. Edite-o e salve.")
        else:
             messagebox.showerror("Erro de Firebase", "Não foi possível salvar o novo consultor.")

    def dev_excluir_selecionado(self):
        """Exclui o consultor selecionado da lista."""
        selected_iid = self.dev_tree.focus()
        if not selected_iid:
            messagebox.showwarning("Nenhum Consultor", "Selecione um consultor na lista para excluir.")
            return

        original_nome = self.dev_tree.item(selected_iid, 'values')[0]

        if not messagebox.askyesno("Confirmar Exclusão", f"Tem certeza que deseja excluir o consultor:\n\n{original_nome}\n\nEsta ação não pode ser desfeita."):
            return

        lista_atual_db = fm.carregar_consultores()
        nova_lista_db = [c for c in lista_atual_db if c['nome'] != original_nome]
        
        if len(nova_lista_db) == len(lista_atual_db):
            messagebox.showerror("Erro de Sincronia", f"O consultor '{original_nome}' não foi encontrado no DB.")
            self.lista_completa_consultores = lista_atual_db
            self.populate_consultor_tree()
            return

        if fm.salvar_consultores(nova_lista_db):
            self.lista_completa_consultores = nova_lista_db
            self.populate_consultor_tree()
            self.app.show_toast("Excluído", f"{original_nome} foi removido.")

            # Verifica se precisa remover as folgas
            self.dados_folgas = fm.carregar_folgas()
            if original_nome in self.dados_folgas:
                if messagebox.askyesno("Remover Folgas", f"Deseja também remover as folgas cadastradas para '{original_nome}'?"):
                    self.dados_folgas.pop(original_nome)
                    fm.salvar_folgas(self.dados_folgas)
                    self.app.show_toast("Sucesso!", "Folgas removidas.")
        else:
            messagebox.showerror("Erro de Firebase", "Não foi possível excluir o consultor.")


    # --- ABA 2: GERENCIAR MARCAS ---

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
            
        # Recarrega os dados
        self.dados_marcas = fm.carregar_marcas()
        
        for nome_marca, dados in sorted(self.dados_marcas.items()):
            data_att = dados.get('ultima_atualizacao', 'N/A')
            qtd_pessoas = len(dados.get('pessoas', []))
            self.dev_tree_marcas.insert('', 'end', values=(nome_marca, data_att, qtd_pessoas))
            
        self.on_dev_tree_marcas_select() # Desabilita os botões

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

    # --- POPUPS DE FOLGAS E MARCAS ---

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