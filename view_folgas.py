# -*- coding: utf-8 -*-

"""
Arquivo: view_folgas.py
Descrição: Contém a classe FolgasView, que constrói e gerencia
a tela de consulta de Folgas.
(v5.3.1 - Corrigido 'messagebox' não definido)
"""

import ttkbootstrap as ttk
from ttkbootstrap.widgets.scrolled import ScrolledFrame
from tkinter import END, messagebox # <-- CORREÇÃO AQUI
# --- NOVA IMPORTAÇÃO ---
from tkinter import ttk as standard_ttk
from datetime import date, datetime
from dateutil.relativedelta import relativedelta

# --- Importa o gerenciador do Firebase ---
import firebase_manager as fm

# --- Importa as funções de utilidade ---
from app_utils import formatar_data

class FolgasView:

    def __init__(self, app, main_frame):
        """
        Constrói a tela de Folgas.
        'app' é a referência à classe principal (App)
        'main_frame' é o frame onde esta tela será desenhada
        """
        self.app = app
        self.main_frame = main_frame
        
        # Carrega os dados de folga
        self.dados_folgas = fm.carregar_folgas()

        # --- Início: Código de create_folgas_view ---
        
        # Configurar o grid do self.main_frame
        self.main_frame.grid_rowconfigure(1, weight=1) # Faz a linha 1 (resultados) expandir
        self.main_frame.grid_columnconfigure(0, weight=1) # Faz a coluna 0 expandir

        ttk.Label(self.main_frame, text="Controle de Folgas", font=self.app.FONT_TITLE).grid(row=0, column=0, pady=(0, 10), sticky='w')

        # --- Frame de Cima: Consultas ---
        frame_consulta = ttk.Frame(self.main_frame, padding=10)
        frame_consulta.grid(row=0, column=0, sticky='new')
        
        if not self.dados_folgas:
            msg = "Nenhum dado de folga cadastrado na nuvem.\n\nVá para a Área do Desenvolvedor para adicionar as folgas."
            ttk.Label(frame_consulta, text=msg, style='secondary.TLabel', font=self.app.FONT_MAIN).pack(expand=True)
            # Cria um frame de resultado vazio
            self.frame_resultado_folgas_scrolled = ttk.Frame(self.main_frame) 
            self.frame_resultado_folgas_scrolled.grid(row=1, column=0, sticky='nsew')
            return

        hoje_obj = date.today()
        hoje_formatado = hoje_obj.strftime("%d/%m/%Y")

        # 2. Folgas de Hoje
        frame_hoje = standard_ttk.LabelFrame(frame_consulta, text=" Folgas de Hoje ", padding=(15, 10))
        frame_hoje.pack(fill='x', expand=True, side='top', pady=(0, 5))

        folgas_hoje_lista = self.get_folgas_por_data(hoje_obj)
        folgas_hoje_str = ", ".join(folgas_hoje_lista) if folgas_hoje_lista else "Ninguém de folga hoje."

        ttk.Label(frame_hoje, text=f"Data: {hoje_formatado}", font=self.app.FONT_BOLD).pack(anchor='w')
        ttk.Label(frame_hoje, text=f"Consultores: {folgas_hoje_str}", font=self.app.FONT_MAIN).pack(anchor='w', pady=(5,0))

        # 3. Folgas de Amanhã
        frame_amanha = standard_ttk.LabelFrame(frame_consulta, text=" Folgas de Amanhã ", padding=(15, 10))
        frame_amanha.pack(fill='x', expand=True, side='top', pady=5)

        amanha_obj = hoje_obj + relativedelta(days=1)
        amanha_formatado = amanha_obj.strftime("%d/%m/%Y")
        folgas_amanha_lista = self.get_folgas_por_data(amanha_obj)
        folgas_amanha_str = ", ".join(folgas_amanha_lista) if folgas_amanha_lista else "Ninguém de folga amanhã."

        ttk.Label(frame_amanha, text=f"Data: {amanha_formatado}", font=self.app.FONT_BOLD).pack(anchor='w')
        ttk.Label(frame_amanha, text=f"Consultores: {folgas_amanha_str}", font=self.app.FONT_MAIN).pack(anchor='w', pady=(5,0))

        # 4. Consultar por Consultor
        frame_buscar = standard_ttk.LabelFrame(frame_consulta, text=" Consultar por Consultor ", padding=(15, 10))
        frame_buscar.pack(fill='x', expand=True, pady=5, side='top')

        ttk.Label(frame_buscar, text="Selecione o Consultor:").pack(anchor='w', side='left', padx=(0, 10))

        nomes_com_folga = sorted(list(self.dados_folgas.keys()))

        self.combo_consultor_folga = ttk.Combobox(frame_buscar, values=nomes_com_folga, state="readonly", width=30)
        self.combo_consultor_folga.pack(side='left', padx=10)

        btn_consultar = ttk.Button(frame_buscar, text="Consultar", command=self.mostrar_folgas_consultor, style='primary.TButton')
        btn_consultar.pack(side='left', padx=10)

        btn_limpar = ttk.Button(frame_buscar, text="Limpar", command=self.limpar_consulta_folgas, style='secondary.Outline.TButton')
        btn_limpar.pack(side='left', padx=10)

        btn_ver_tabela = ttk.Button(frame_buscar, text="Ver Tabela Completa", command=self.mostrar_tabela_completa_folgas, style='info.Outline.TButton')
        btn_ver_tabela.pack(side='right', padx=10)

        # 5. Consultar por Data
        frame_buscar_data = standard_ttk.LabelFrame(frame_consulta, text=" Consultar por Data ", padding=(15, 10))
        frame_buscar_data.pack(fill='x', expand=True, pady=5, side='top')

        ttk.Label(frame_buscar_data, text="Digite a Data (dd/mm/aaaa):").pack(anchor='w', side='left', padx=(0, 10))

        self.entry_data_folga = ttk.Entry(frame_buscar_data, width=20)
        self.entry_data_folga.pack(side='left', padx=10)
        self.entry_data_folga.bind("<KeyRelease>", lambda e: formatar_data(e, self.entry_data_folga))
        self.entry_data_folga.insert(0, hoje_formatado)

        btn_consultar_data = ttk.Button(frame_buscar_data, text="Consultar Data", command=self.mostrar_folgas_por_data, style='primary.TButton')
        btn_consultar_data.pack(side='left', padx=10)

        # --- Parte de Baixo: Resultado ---
        self.frame_resultado_folgas_scrolled = ScrolledFrame(self.main_frame, padding=10, autohide=False)
        
        # --- Rastreia o ScrolledFrame ---
        self.app.tracked_scrolled_frames.append(self.frame_resultado_folgas_scrolled)
        
        self.frame_resultado_folgas_scrolled.grid(row=1, column=0, sticky='nsew', pady=(10, 0))

        # O container é o frame interno onde os widgets vão
        self.frame_resultado_folgas = self.frame_resultado_folgas_scrolled.container

        ttk.Label(self.frame_resultado_folgas, text="Selecione um consultor ou data para consultar.").pack()

        # --- Fim: Código de create_folgas_view ---

    def get_folgas_por_data(self, data_obj):
        """Função HElPER. Retorna uma lista de nomes em folga para uma data específica."""
        folgas_lista = []
        for consultor_nome, lista_de_datas in self.dados_folgas.items():
            for data_str in lista_de_datas:
                try:
                    data_folga = datetime.strptime(data_str.strip(), "%d/%m/%Y").date()
                    if data_folga == data_obj:
                        folgas_lista.append(consultor_nome.upper())
                        break # Para de procurar nas datas desta pessoa
                except ValueError:
                    print(f"Aviso: Data mal formatada '{data_str}' para {consultor_nome}")
                    pass
        return folgas_lista

    def limpar_consulta_folgas(self):
        """Limpa os campos de consulta e o frame de resultado."""
        self.combo_consultor_folga.set("")
        self.entry_data_folga.delete(0, END)
        self.entry_data_folga.insert(0, date.today().strftime("%d/%m/%Y"))

        # Limpa o frame de resultado
        for widget in self.frame_resultado_folgas.winfo_children():
            widget.destroy()
        ttk.Label(self.frame_resultado_folgas, text="Selecione um consultor ou data para consultar.").pack()

    def mostrar_folgas_consultor(self):
        """Mostra a lista de folgas do consultor selecionado."""
        for widget in self.frame_resultado_folgas.winfo_children():
            widget.destroy()

        nome_consultor = self.combo_consultor_folga.get()
        if not nome_consultor:
            messagebox.showwarning("Atenção", "Selecione um consultor para consultar.")
            return

        datas_folga = self.dados_folgas.get(nome_consultor, [])

        container = self.frame_resultado_folgas
        ttk.Label(container, text=f"Folgas Cadastradas - {nome_consultor.upper()}:", font=self.app.FONT_BOLD).pack(anchor='w', pady=(0, 10))

        if not datas_folga:
            ttk.Label(container, text="Nenhuma folga cadastrada para este consultor.").pack(anchor='w')
            return

        try:
            datas_folga_sorted = sorted(datas_folga, key=lambda d: datetime.strptime(d.strip(), "%d/%m/%Y"))
        except ValueError:
            datas_folga_sorted = datas_folga

        for dia in datas_folga_sorted:
            ttk.Label(container, text=f"• {dia}").pack(anchor='w')

    def mostrar_folgas_por_data(self):
        """Mostra a lista de consultores em folga na data selecionada."""
        for widget in self.frame_resultado_folgas.winfo_children():
            widget.destroy()

        data_str = self.entry_data_folga.get()
        if not data_str or len(data_str) != 10:
            messagebox.showwarning("Data Inválida", "Digite uma data válida (dd/mm/aaaa).")
            return

        try:
            data_obj = datetime.strptime(data_str, "%d/%m/%Y").date()
        except ValueError:
            messagebox.showwarning("Data Inválida", "A data digitada não é válida (dd/mm/aaaa).")
            return

        folgas_lista = self.get_folgas_por_data(data_obj)

        container = self.frame_resultado_folgas
        ttk.Label(container, text=f"Consultores em Folga - {data_str}:", font=self.app.FONT_BOLD).pack(anchor='w', pady=(0, 10))

        if not folgas_lista:
            ttk.Label(container, text="Ninguém cadastrado para folga nesta data.").pack(anchor='w')
            return

        for nome in folgas_lista:
            ttk.Label(container, text=f"• {nome}").pack(anchor='w')

    def mostrar_tabela_completa_folgas(self):
        """Mostra a tabela completa de folgas do JSON."""
        for widget in self.frame_resultado_folgas.winfo_children():
            widget.destroy()

        container = self.frame_resultado_folgas

        colunas = ('consultor', 'datas')
        tree_folgas = ttk.Treeview(container, columns=colunas, show='headings', height=15)

        tree_folgas.heading('consultor', text='Consultor')
        tree_folgas.heading('datas', text='Datas de Folga')

        tree_folgas.column('consultor', width=200, anchor='w', stretch=False)
        tree_folgas.column('datas', width=500, anchor='w')

        for nome, lista_de_datas in sorted(self.dados_folgas.items()):
            try:
                datas_folga_sorted = sorted(lista_de_datas, key=lambda d: datetime.strptime(d.strip(), "%d/%m/%Y"))
            except ValueError:
                datas_folga_sorted = lista_de_datas

            datas_str = ", ".join(datas_folga_sorted)
            tree_folgas.insert('', 'end', values=(nome.upper(), datas_str))

        tree_folgas.pack(fill='both', expand=True)