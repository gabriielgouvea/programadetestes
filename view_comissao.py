# -*- coding: utf-8 -*-

"""
Arquivo: view_comissao.py
Descrição: Contém a classe ComissaoView, que constrói e gerencia
a tela da Calculadora de Comissão.
"""

import ttkbootstrap as ttk
from ttkbootstrap.widgets.scrolled import ScrolledFrame
from tkinter import filedialog, messagebox
# --- NOVA IMPORTAÇÃO ---
from tkinter import ttk as standard_ttk
import os
import traceback

# --- Importa as funções de utilidade ---
from app_utils import formatar_reais

# --- Importa o processador de PDF ---
try:
    from calculadora_core import processar_pdf
except ImportError:
    messagebox.showerror("Erro de Arquivo", "Arquivo 'calculadora_core.py' não encontrado.")
    # A tela simplesmente não funcionará se o core não for encontrado
    processar_pdf = None

class ComissaoView:
    
    def __init__(self, app, main_frame):
        """
        Constrói a tela de Comissão.
        'app' é a referência à classe principal (App)
        'main_frame' é o frame onde esta tela será desenhada
        """
        self.app = app
        self.main_frame = main_frame

        if processar_pdf is None:
            ttk.Label(self.main_frame, text="Erro Crítico", font=self.app.FONT_TITLE).pack(pady=(0, 10), anchor='w')
            ttk.Label(self.main_frame, text="Não foi possível carregar 'calculadora_core.py'.\nA funcionalidade de comissão está desabilitada.", style="danger.TLabel").pack(pady=10)
            return

        # --- Início: Código de create_comissao_view ---
        
        ttk.Label(self.main_frame, text="Calculadora de Comissão", font=self.app.FONT_TITLE).pack(pady=(0, 10), anchor='w')

        # Frame de Cima: Upload
        frame_upload = ttk.Frame(self.main_frame)
        frame_upload.pack(side='top', fill='x', pady=(0, 10))

        btn_upload = ttk.Button(frame_upload, text="Fazer Upload do PDF de Fechamento",
                                command=self.processar_pdf_comissao,
                                style='primary.TButton',
                                width=40)
        btn_upload.pack(side='left', ipady=5, pady=5)

        self.lbl_pdf_selecionado = ttk.Label(frame_upload, text="Nenhum arquivo selecionado.", style='secondary.TLabel')
        self.lbl_pdf_selecionado.pack(side='left', padx=10)

        # Frame de Baixo: Resultados
        frame_comissao = ScrolledFrame(self.main_frame, autohide=False)
        
        # --- Rastreia o ScrolledFrame ---
        self.app.tracked_scrolled_frames.append(frame_comissao) 
        
        frame_comissao.pack(side='top', fill='both', expand=True, pady=(10, 0))
        
        # O container é o frame interno onde os widgets vão
        self.frame_resultado_comissao = frame_comissao.container 

        ttk.Label(self.frame_resultado_comissao,
                  text="Selecione um PDF para calcular a comissão.",
                  style='secondary.TLabel').pack(expand=True)
        
        # --- Fim: Código de create_comissao_view ---

    def processar_pdf_comissao(self):
        """Função chamada pelo botão de upload."""
        filepath = filedialog.askopenfilename(
            title="Selecione o PDF de Fechamento de Caixa",
            filetypes=[("Arquivos PDF", "*.pdf")]
        )
        if not filepath:
            return

        self.lbl_pdf_selecionado.config(text=os.path.basename(filepath))

        # Limpa resultados antigos
        for widget in self.frame_resultado_comissao.winfo_children():
            widget.destroy()

        # Mostra o cursor de "carregando"
        self.app.config(cursor="watch")
        self.app.update_idletasks()

        try:
            # Chama a lógica do calculadora_core.py
            resultados = processar_pdf(filepath)

            # Devolve o cursor ao normal
            self.app.config(cursor="")
            self.app.update_idletasks()

            # Exibe os resultados
            self.exibir_resultados_comissao(resultados)

        except Exception as e:
            # Devolve o cursor ao normal
            self.app.config(cursor="")
            self.app.update_idletasks()
            # Mostra o erro
            messagebox.showerror("Erro ao Processar PDF",
                               f"Ocorreu um erro ao ler o arquivo:\n\n{e}\n\nTraceback:\n{traceback.format_exc()}")
            # Limpa o frame de resultados
            for widget in self.frame_resultado_comissao.winfo_children():
                widget.destroy()
            ttk.Label(self.frame_resultado_comissao,
                      text=f"Falha ao ler o PDF.\n{e}",
                      style='danger.TLabel').pack(expand=True)

    def _create_metric_widget(self, parent, label_text, value_text, bootstyle):
        """Função helper para criar um card de métrica."""
        frame = ttk.Frame(parent, bootstyle=bootstyle, padding=10, borderwidth=1, relief="raised")

        lbl_title = ttk.Label(frame, text=label_text,
                              font=(self.app.FONT_MAIN[0], 9, 'bold'),
                              bootstyle=f'inverse-{bootstyle}')
        lbl_title.pack(side='top', anchor='nw')

        lbl_value = ttk.Label(frame, text=value_text,
                              font=(self.app.FONT_MAIN[0], 16, 'bold'),
                              bootstyle=f'inverse-{bootstyle}')
        lbl_value.pack(side='bottom', anchor='se', pady=(5,0))
        return frame

    def exibir_resultados_comissao(self, resultados):
        """Pega o dicionário de resultados e exibe na tela."""
        container = self.frame_resultado_comissao # Usa o container do ScrolledFrame

        # --- Seção 0: Info Cabeçalho ---
        info_cabecalho = resultados.get("info_cabecalho", {})
        operador = info_cabecalho.get("operador", "Não identificado")
        periodo = info_cabecalho.get("periodo", "Não identificado")

        frame_info = ttk.Frame(container, bootstyle='info', padding=10)
        frame_info.pack(fill='x', pady=5)
        ttk.Label(frame_info, text=f"Fechamento: {operador}    |    Período: {periodo}",
                  font=self.app.FONT_BOLD, bootstyle='inverse-info').pack()

        # --- Seção 1: Resumo do Cálculo ---
        frame_resumo = standard_ttk.LabelFrame(container, text=" Resumo do Cálculo de Comissão ", padding=15)
        frame_resumo.pack(fill='x', pady=10)

        frame_metrics = ttk.Frame(frame_resumo)
        frame_metrics.pack(fill='x')
        frame_metrics.grid_columnconfigure((0,1,2,3), weight=1)

        m1 = self._create_metric_widget(frame_metrics, "Valor Total",
                                        formatar_reais(resultados.get('valor_total_bruto', 0)),
                                        'secondary')
        m1.grid(row=0, column=0, padx=5, sticky='ew')

        m2 = self._create_metric_widget(frame_metrics, "Descontos",
                                        formatar_reais(resultados.get('total_deducoes', 0)),
                                        'warning')
        m2.grid(row=0, column=1, padx=5, sticky='ew')

        m3 = self._create_metric_widget(frame_metrics, "Valor Comissionável",
                                        formatar_reais(resultados.get('base_comissionavel', 0)),
                                        'primary')
        m3.grid(row=0, column=2, padx=5, sticky='ew')

        m4 = self._create_metric_widget(frame_metrics, "SUA COMISSÃO (3%)",
                                        formatar_reais(resultados.get('comissao_final', 0)),
                                        'success')
        m4.grid(row=0, column=3, padx=5, sticky='ew')

        # --- Seção 2: Resumo de Vendas ---
        frame_vendas = standard_ttk.LabelFrame(container, text=" Resumo de Vendas e Atendimentos ", padding=15)
        frame_vendas.pack(fill='x', expand=True, pady=10)

        resumo = resultados.get("resumo_vendas", {})
        total_atendimentos = resumo.get("total_atendimentos", 0)

        ttk.Label(frame_vendas, text=f"Total de Atendimentos: {total_atendimentos} transações").pack(anchor='w')
        ttk.Separator(frame_vendas).pack(fill='x', pady=10)

        cols = ('metodo', 'qtd', 'valor')
        tree_vendas = ttk.Treeview(frame_vendas, columns=cols, show='headings', height=7)
        tree_vendas.heading('metodo', text='Forma de Pagamento')
        tree_vendas.heading('qtd', text='Qtd.')
        tree_vendas.heading('valor', text='Valor Total')
        tree_vendas.column('metodo', anchor='w', width=250)
        tree_vendas.column('qtd', anchor='center', width=50)
        tree_vendas.column('valor', anchor='e', width=120)

        for metodo, dados in resumo.items():
            if isinstance(dados, dict) and dados.get('qtd', 0) > 0:
                nome_metodo = metodo.replace("_", " ").title().replace('(Ccc)', '(CCC)')
                tree_vendas.insert('', 'end', values=(nome_metodo, dados.get('qtd'), formatar_reais(dados.get('valor'))))
        tree_vendas.pack(fill='x', expand=True)

        # --- Seção 3: Detalhes das Deduções ---
        frame_deducoes = standard_ttk.LabelFrame(container, text=" Detalhamento das Deduções Encontradas ", padding=15)
        frame_deducoes.pack(fill='x', expand=True, pady=10)

        detalhes = resultados.get('detalhes', {})
        deducoes_encontradas = {k: v for k, v in detalhes.items() if v > 0}

        if not deducoes_encontradas:
            ttk.Label(frame_deducoes, text="Nenhuma dedução aplicável foi encontrada.").pack()
        else:
            cols_deduc = ('motivo', 'valor')
            tree_deduc = ttk.Treeview(frame_deducoes, columns=cols_deduc, show='headings', height=len(deducoes_encontradas))
            tree_deduc.heading('motivo', text='Motivo da Dedução')
            tree_deduc.heading('valor', text='Valor Deduzido')
            tree_deduc.column('motivo', anchor='w', width=300)
            tree_deduc.column('valor', anchor='e', width=120)

            for nome, valor in deducoes_encontradas.items():
                tree_deduc.insert('', 'end', values=(nome, formatar_reais(valor)))
            tree_deduc.pack(fill='x', expand=True)