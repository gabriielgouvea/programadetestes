# -*- coding: utf-8 -*-

"""
Arquivo: view_comissao.py
Descrição: Contém a classe ComissaoView, que constrói e gerencia
a tela da Calculadora de Comissão e o novo Caixa Pessoal.
(v5.7.0 - Implementação do Caixa de Comissão e PINs)
"""

import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from ttkbootstrap.widgets import DateEntry
from ttkbootstrap.widgets.scrolled import ScrolledFrame
from tkinter import filedialog, messagebox, Toplevel, StringVar, END, ANCHOR
from tkinter import ttk as standard_ttk
import os
import traceback
from datetime import date, datetime
import calendar

# --- Importa as funções de utilidade ---
from app_utils import formatar_reais

# --- Importa o processador de PDF ---
try:
    from calculadora_core import processar_pdf
except ImportError:
    messagebox.showerror("Erro de Arquivo", "Arquivo 'calculadora_core.py' não encontrado.")
    processar_pdf = None

# --- Importa o gerenciador do Firebase ---
import firebase_manager as fm

class ComissaoView:
    
    def __init__(self, app, main_frame):
        """
        Constrói a tela de Comissão, agora com abas.
        """
        self.app = app
        self.main_frame = main_frame
        
        # Carrega dados essenciais
        self.dados_pins = fm.carregar_pins_consultores()
        self.dados_caixa_comissao = fm.carregar_caixa_comissao()
        
        # Variáveis de estado
        self.nome_consultor_logado = self.app.consultor_logado_data.get('nome', 'N/A')
        self.pin_verificado_nesta_sessao = False # Flag para não pedir o PIN toda hora
        self.saldo_acumulado_mes = 0.00
        self.saldo_esta_visivel = False

        # --- Carrega o ícone do "olho" ---
        try:
            self.icon_eye = ttk.PhotoImage(file=os.path.join(self.app.DATA_FOLDER_PATH, "eye.png"))
        except Exception as e:
            print(f"AVISO: Não foi possível carregar 'eye.png'. {e}")
            self.icon_eye = ttk.PhotoImage() # Imagem vazia

        if processar_pdf is None:
            ttk.Label(self.main_frame, text="Erro Crítico", font=self.app.FONT_TITLE).pack(pady=(0, 10), anchor='w')
            ttk.Label(self.main_frame, text="Não foi possível carregar 'calculadora_core.py'.\nA funcionalidade de comissão está desabilitada.", style="danger.TLabel").pack(pady=10)
            return

        # --- Título Principal ---
        ttk.Label(self.main_frame, text="Calculadora de Comissão", font=self.app.FONT_TITLE).pack(pady=(0, 10), anchor='w')

        # --- Abas (Notebook) ---
        notebook = ttk.Notebook(self.main_frame)
        notebook.pack(fill='both', expand=True)

        # 2. Cria os frames para cada aba
        tab_calcular = ttk.Frame(notebook, padding=10)
        tab_consultar = ttk.Frame(notebook, padding=10)
        
        notebook.add(tab_calcular, text=' Calcular e Registrar ')
        notebook.add(tab_consultar, text=' Consultar Meu Saldo ')

        # 3. Preenche cada aba
        self.criar_aba_calcular(tab_calcular)
        self.criar_aba_consultar(tab_consultar)

    # --- ABA 1: CALCULAR E REGISTRAR ---

    def criar_aba_calcular(self, parent_frame):
        """Cria o conteúdo da aba 'Calcular e Registrar'."""
        
        # Frame de Cima: Upload
        frame_upload = ttk.Frame(parent_frame)
        frame_upload.pack(side='top', fill='x', pady=(0, 10))

        btn_upload = ttk.Button(frame_upload, text="Fazer Upload do PDF de Fechamento",
                                command=self.processar_pdf_comissao,
                                style='primary.TButton',
                                width=40)
        btn_upload.pack(side='left', ipady=5, pady=5)

        self.lbl_pdf_selecionado = ttk.Label(frame_upload, text="Nenhum arquivo selecionado.", style='secondary.TLabel')
        self.lbl_pdf_selecionado.pack(side='left', padx=10)
        
        # --- NOVOS CAMPOS ---
        
        frame_novos_campos = standard_ttk.LabelFrame(parent_frame, text=" Opções de Lançamento ", padding=15)
        frame_novos_campos.pack(fill='x', pady=10)
        
        # 1. Planos Vendidos
        frame_planos = ttk.Frame(frame_novos_campos)
        frame_planos.pack(fill='x')
        
        ttk.Label(frame_planos, text="Planos Vendidos (R$ 40,00 cada):", font=self.app.FONT_BOLD).pack(side='left', padx=(0, 10))
        
        self.planos_var = StringVar(value="0")
        self.entry_planos = ttk.Entry(frame_planos, textvariable=self.planos_var, width=5)
        self.entry_planos.pack(side='left')
        
        # 2. Tipo de Operação
        frame_tipo = ttk.Frame(frame_novos_campos)
        frame_tipo.pack(fill='x', pady=(10,0))
        
        ttk.Label(frame_tipo, text="Tipo de Operação:", font=self.app.FONT_BOLD).pack(side='left', padx=(0, 10))
        
        self.tipo_operacao_var = StringVar(value="consulta") # Padrão é só consulta
        
        rb_consulta = ttk.Radiobutton(frame_tipo, text="Apenas Consultar", variable=self.tipo_operacao_var, value="consulta", style='Toolbutton')
        rb_consulta.pack(side='left', padx=5)
        
        rb_fechamento = ttk.Radiobutton(frame_tipo, text="Fazer Fechamento e Registrar Valor", variable=self.tipo_operacao_var, value="fechamento", style='Toolbutton')
        rb_fechamento.pack(side='left', padx=5)
        
        # --- FIM NOVOS CAMPOS ---

        # Frame de Baixo: Resultados
        frame_comissao = ScrolledFrame(parent_frame, autohide=False)
        self.app.tracked_scrolled_frames.append(frame_comissao) 
        frame_comissao.pack(side='top', fill='both', expand=True, pady=(10, 0))
        
        self.frame_resultado_comissao = frame_comissao.container 

        ttk.Label(self.frame_resultado_comissao,
                  text="Selecione um PDF para calcular a comissão.",
                  style='secondary.TLabel').pack(expand=True)

    def processar_pdf_comissao(self):
        """Função chamada pelo botão de upload."""
        filepath = filedialog.askopenfilename(
            title="Selecione o PDF de Fechamento de Caixa",
            filetypes=[("Arquivos PDF", "*.pdf")]
        )
        if not filepath:
            return

        self.lbl_pdf_selecionado.config(text=os.path.basename(filepath))

        for widget in self.frame_resultado_comissao.winfo_children():
            widget.destroy()

        self.app.config(cursor="watch")
        self.app.update_idletasks()

        try:
            # --- 1. Processa o PDF ---
            resultados_pdf = processar_pdf(filepath)
            
            # --- 2. Calcula os Planos ---
            try:
                qtd_planos = int(self.planos_var.get())
            except ValueError:
                qtd_planos = 0
            
            valor_comissao_planos = qtd_planos * 40.00
            valor_comissao_pdf = resultados_pdf.get('comissao_final', 0)
            valor_total_comissao = valor_comissao_planos + valor_comissao_pdf

            self.app.config(cursor="")
            self.app.update_idletasks()

            # --- 3. Exibe os resultados ---
            self.exibir_resultados_comissao_detalhado(
                resultados_pdf, 
                valor_comissao_pdf, 
                valor_comissao_planos, 
                qtd_planos, 
                valor_total_comissao
            )
            
            # --- 4. Tenta Registrar (se marcado) ---
            if self.tipo_operacao_var.get() == "fechamento":
                self.registrar_no_caixa(valor_comissao_pdf, valor_comissao_planos, qtd_planos)

        except Exception as e:
            self.app.config(cursor="")
            self.app.update_idletasks()
            messagebox.showerror("Erro ao Processar PDF",
                               f"Ocorreu um erro ao ler o arquivo:\n\n{e}\n\nTraceback:\n{traceback.format_exc()}")
            for widget in self.frame_resultado_comissao.winfo_children():
                widget.destroy()
            ttk.Label(self.frame_resultado_comissao,
                      text=f"Falha ao ler o PDF.\n{e}",
                      style='danger.TLabel').pack(expand=True)

    def exibir_resultados_comissao_detalhado(self, resultados, val_pdf, val_planos, qtd_planos, val_total):
        """Pega os resultados e exibe na tela de forma detalhada."""
        container = self.frame_resultado_comissao

        info_cabecalho = resultados.get("info_cabecalho", {})
        operador = info_cabecalho.get("operador", "Não identificado")
        periodo = info_cabecalho.get("periodo", "Não identificado")

        frame_info = ttk.Frame(container, bootstyle='info', padding=10)
        frame_info.pack(fill='x', pady=5)
        ttk.Label(frame_info, text=f"Fechamento: {operador}   |   Período: {periodo}",
                  font=self.app.FONT_BOLD, bootstyle='inverse-info').pack()

        # --- Seção 1: Resumo do Cálculo ---
        frame_resumo = standard_ttk.LabelFrame(container, text=" Resumo da Comissão do Dia ", padding=15)
        frame_resumo.pack(fill='x', pady=10)

        # Helper para criar as linhas
        def criar_linha_resumo(label, valor_str, style='default'):
            frame_linha = ttk.Frame(frame_resumo)
            frame_linha.pack(fill='x', pady=2)
            ttk.Label(frame_linha, text=label, font=self.app.FONT_BOLD, width=30).pack(side='left')
            bootstyle = style if style != 'default' else 'inverse-secondary'
            ttk.Label(frame_linha, text=valor_str, font=self.app.FONT_BOLD, bootstyle=bootstyle, padding=5).pack(side='left')

        # Cria as linhas do resumo
        criar_linha_resumo("Comissão de Produtos (PDF):", formatar_reais(val_pdf), 'primary')
        criar_linha_resumo(f"Comissão de Planos ({qtd_planos} x R$ 40,00):", formatar_reais(val_planos), 'primary')
        ttk.Separator(frame_resumo).pack(fill='x', pady=5)
        criar_linha_resumo("TOTAL DA COMISSÃO DO DIA:", formatar_reais(val_total), 'success')
        
        # --- Seção 2: Detalhes do PDF ---
        frame_detalhes_pdf = standard_ttk.LabelFrame(container, text=" Detalhes do PDF (Produtos) ", padding=15)
        frame_detalhes_pdf.pack(fill='x', pady=10)
        
        # ... (código para exibir os detalhes do PDF, como antes) ...
        # (Vou manter simples por enquanto para focar no caixa)
        ttk.Label(frame_detalhes_pdf, text=f"Valor Total (PDF): {formatar_reais(resultados.get('valor_total_bruto', 0))}").pack(anchor='w')
        ttk.Label(frame_detalhes_pdf, text=f"Total Deduções (PDF): {formatar_reais(resultados.get('total_deducoes', 0))}").pack(anchor='w')
        ttk.Label(frame_detalhes_pdf, text=f"Base Comissionável (PDF): {formatar_reais(resultados.get('base_comissionavel', 0))}").pack(anchor='w')
        
    def registrar_no_caixa(self, valor_pdf, valor_planos, qtd_planos):
        """Verifica o PIN e salva os valores no caixa do consultor."""
        
        # 1. Verificar o PIN
        if not self.pin_verificado_nesta_sessao:
            pin_ok = self._verificar_pin_consultor()
            if not pin_ok:
                self.app.show_toast("Registro Cancelado", "O PIN não foi validado.", bootstyle='warning')
                return
            # Se chegou aqui, o PIN está OK
            self.pin_verificado_nesta_sessao = True
        
        # 2. Preparar os dados para salvar
        hoje_str = date.today().strftime("%Y-%m-%d_%H%M%S") # ID único
        mes_ano_atual = date.today().strftime("%Y-%m") # Chave "2025-11"
        
        novo_registro = {
            "data": date.today().strftime("%d/%m/%Y"),
            "comissao_produtos": valor_pdf,
            "comissao_planos": valor_planos,
            "qtd_planos": qtd_planos,
            "total_dia": valor_pdf + valor_planos
        }
        
        # 3. Pegar os dados atuais e adicionar o novo
        # Garante que o consultor tenha uma entrada
        if self.nome_consultor_logado not in self.dados_caixa_comissao:
            self.dados_caixa_comissao[self.nome_consultor_logado] = {}
        
        # Garante que ele tenha uma entrada para o mês/ano
        if mes_ano_atual not in self.dados_caixa_comissao[self.nome_consultor_logado]:
            self.dados_caixa_comissao[self.nome_consultor_logado][mes_ano_atual] = {}
            
        # Adiciona o novo registro (com ID único de data/hora)
        self.dados_caixa_comissao[self.nome_consultor_logado][mes_ano_atual][hoje_str] = novo_registro
        
        # 4. Salvar no Firebase
        if fm.salvar_caixa_comissao(self.dados_caixa_comissao):
            self.app.show_toast("Sucesso!", "Valor registrado no seu caixa.", bootstyle='success')
        else:
            messagebox.showerror("Erro", "Não foi possível salvar o registro no Firebase.")
            # Se falhou, remove o item local para não dessincronizar
            self.dados_caixa_comissao[self.nome_consultor_logado][mes_ano_atual].pop(hoje_str)

    # --- LÓGICA DE PIN ---

    def _verificar_pin_consultor(self):
        """Verifica o PIN. Se for o padrão (0000), força a criação de um novo."""
        
        # Recarrega os PINs para garantir
        self.dados_pins = fm.carregar_pins_consultores()
        
        pin_atual = self.dados_pins.get(self.nome_consultor_logado, "0000") # Padrão é 0000
        
        # 1. Se for o PIN padrão, força a criação
        if pin_atual == "0000":
            if self._popup_criar_pin():
                return True # Criou com sucesso
            else:
                return False # Cancelou a criação
        
        # 2. Se já tem PIN, pede para digitar
        pin_digitado = self._popup_pedir_pin()
        
        if pin_digitado == pin_atual:
            return True
        elif pin_digitado is not None: # Digitou, mas errou
            messagebox.showerror("PIN Incorreto", "O PIN digitado está incorreto.")
            return False
        else: # Cancelou
            return False

    def _popup_criar_pin(self):
        """Popup para o usuário criar seu PIN de 4 dígitos."""
        popup = Toplevel(self.app)
        popup.title("Crie seu PIN de Segurança")
        self.app._center_popup(popup, 350, 220)
        
        container = ttk.Frame(popup, padding=20)
        container.pack(fill='both', expand=True)
        
        ttk.Label(container, text="Primeiro Acesso ao Caixa", font=self.app.FONT_BOLD).pack()
        ttk.Label(container, text="Seu PIN padrão é '0000'. Crie um novo PIN de 4 dígitos:", wraplength=300).pack(pady=10)
        
        ttk.Label(container, text="Novo PIN (4 dígitos):").pack(anchor='w')
        pin1_var = StringVar()
        entry_pin1 = ttk.Entry(container, textvariable=pin1_var, show="*", width=10)
        entry_pin1.pack(fill='x', pady=5)
        
        ttk.Label(container, text="Confirme o PIN:").pack(anchor='w')
        pin2_var = StringVar()
        entry_pin2 = ttk.Entry(container, textvariable=pin2_var, show="*", width=10)
        entry_pin2.pack(fill='x', pady=5)
        
        pin_criado_com_sucesso = False

        def on_salvar_pin():
            nonlocal pin_criado_com_sucesso
            pin1 = pin1_var.get()
            pin2 = pin2_var.get()
            
            if len(pin1) != 4 or not pin1.isdigit():
                messagebox.showerror("PIN Inválido", "O PIN deve conter exatamente 4 números.", parent=popup)
                return
            if pin1 != pin2:
                messagebox.showerror("Erro", "Os PINs não são iguais. Tente novamente.", parent=popup)
                return
            
            # Salva o novo PIN
            self.dados_pins[self.nome_consultor_logado] = pin1
            if fm.salvar_pins_consultores(self.dados_pins):
                self.app.show_toast("Sucesso!", "Seu novo PIN foi salvo.")
                pin_criado_com_sucesso = True
                popup.destroy()
            else:
                messagebox.showerror("Erro", "Não foi possível salvar seu PIN no Firebase.", parent=popup)

        ttk.Button(container, text="Salvar Novo PIN", style="success.TButton", command=on_salvar_pin).pack(pady=10)
        entry_pin1.focus_set()
        
        self.app.wait_window(popup)
        return pin_criado_com_sucesso
        
    def _popup_pedir_pin(self):
        """Popup que pede o PIN de 4 dígitos. Retorna o PIN ou None se cancelado."""
        popup = Toplevel(self.app)
        popup.title("Acesso ao Caixa")
        self.app._center_popup(popup, 350, 180)
        
        container = ttk.Frame(popup, padding=20)
        container.pack(fill='both', expand=True)
        
        ttk.Label(container, text=f"Consultor: {self.nome_consultor_logado}", font=self.app.FONT_BOLD).pack()
        ttk.Label(container, text="Digite seu PIN de 4 dígitos:").pack(pady=10)
        
        pin_var = StringVar()
        entry_pin = ttk.Entry(container, textvariable=pin_var, show="*", width=10, font=("Helvetica", 14))
        entry_pin.pack(pady=5)
        entry_pin.focus_set()

        resultado = None

        def on_confirmar():
            nonlocal resultado
            pin = pin_var.get()
            if len(pin) == 4 and pin.isdigit():
                resultado = pin
                popup.destroy()
            else:
                messagebox.showerror("PIN Inválido", "O PIN deve conter 4 números.", parent=popup)
                
        def on_cancelar():
            nonlocal resultado
            resultado = None
            popup.destroy()

        frame_botoes = ttk.Frame(container)
        frame_botoes.pack(pady=10)
        ttk.Button(frame_botoes, text="Confirmar", style="success.TButton", command=on_confirmar).pack(side='left', padx=5)
        ttk.Button(frame_botoes, text="Cancelar", style="light.TButton", command=on_cancelar).pack(side='left', padx=5)
        
        popup.bind("<Return>", lambda e: on_confirmar())
        self.app.wait_window(popup)
        return resultado


    # --- ABA 2: CONSULTAR SALDO ---

    def criar_aba_consultar(self, parent_frame):
        """Cria o conteúdo da aba 'Consultar Meu Saldo'."""
        
        parent_frame.grid_columnconfigure(0, weight=1)
        parent_frame.grid_rowconfigure(2, weight=1) # Faz a Treeview expandir
        
        # --- 1. Frame Saldo ---
        frame_saldo = standard_ttk.LabelFrame(parent_frame, text=" Saldo Acumulado no Mês Atual ", padding=15)
        frame_saldo.grid(row=0, column=0, sticky='ew', pady=(0, 10))
        frame_saldo.grid_columnconfigure(0, weight=1)
        
        self.saldo_label = ttk.Label(frame_saldo, text="R$ ****,**", font=self.app.FONT_TITLE, bootstyle='secondary')
        self.saldo_label.grid(row=0, column=0, sticky='w')
        
        self.olho_button = ttk.Button(frame_saldo, image=self.icon_eye, style='light.TButton', command=self.revelar_saldo)
        self.olho_button.grid(row=0, column=1, padx=10)
        
        # --- 2. Frame Filtros ---
        frame_filtros = standard_ttk.LabelFrame(parent_frame, text=" Consultar Registros ", padding=15)
        frame_filtros.grid(row=1, column=0, sticky='ew', pady=10)
        
        ttk.Label(frame_filtros, text="De:").grid(row=0, column=0, padx=(0,5))
        self.filtro_data_de = DateEntry(frame_filtros, dateformat="%d/%m/%Y", bootstyle='primary')
        self.filtro_data_de.grid(row=0, column=1, padx=(0, 10))
        
        ttk.Label(frame_filtros, text="Até:").grid(row=0, column=2, padx=(0,5))
        self.filtro_data_ate = DateEntry(frame_filtros, dateformat="%d/%m/%Y", bootstyle='primary')
        self.filtro_data_ate.grid(row=0, column=3, padx=(0, 20))

        # TODO: Adicionar filtro de Mês e Tipo
        
        btn_consultar = ttk.Button(frame_filtros, text="Consultar", style='primary.Outline.TButton', command=self.consultar_saldo)
        btn_consultar.grid(row=0, column=4, padx=10)
        
        # --- 3. Frame Resultados (Treeview) ---
        frame_resultados = ttk.Frame(parent_frame)
        frame_resultados.grid(row=2, column=0, sticky='nsew')
        
        cols = ('data', 'produtos', 'planos', 'total_dia')
        self.tree_saldo = ttk.Treeview(frame_resultados, columns=cols, show='headings', height=10)
        self.tree_saldo.heading('data', text='Data')
        self.tree_saldo.heading('produtos', text='Comissão Produtos')
        self.tree_saldo.heading('planos', text='Comissão Planos')
        self.tree_saldo.heading('total_dia', text='Total do Dia')
        
        self.tree_saldo.column('data', anchor='w', width=100)
        self.tree_saldo.column('produtos', anchor='e', width=150)
        self.tree_saldo.column('planos', anchor='e', width=150)
        self.tree_saldo.column('total_dia', anchor='e', width=150)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(frame_resultados, orient='vertical', command=self.tree_saldo.yview)
        self.tree_saldo.configure(yscrollcommand=scrollbar.set)
        
        scrollbar.pack(side='right', fill='y')
        self.tree_saldo.pack(side='left', fill='both', expand=True)
        
        # Carrega os dados iniciais
        self.consultar_saldo(primeira_carga=True)

    def revelar_saldo(self):
        """Pede o PIN e revela o saldo do mês."""
        
        # Se o saldo já está visível, oculta
        if self.saldo_esta_visivel:
            self.saldo_label.config(text="R$ ****,**", bootstyle='secondary')
            self.saldo_esta_visivel = False
            return
            
        # Pede o PIN
        if not self.pin_verificado_nesta_sessao:
            pin_ok = self._verificar_pin_consultor()
            if not pin_ok:
                self.app.show_toast("Acesso Negado", "O PIN não foi validado.", bootstyle='warning')
                return
            self.pin_verificado_nesta_sessao = True
        
        # Revela o saldo
        self.saldo_label.config(text=formatar_reais(self.saldo_acumulado_mes), bootstyle='success')
        self.saldo_esta_visivel = True

    def consultar_saldo(self, primeira_carga=False):
        """Busca no Firebase os registros do consultor e filtra."""
        
        # Limpa a árvore e o saldo
        for item in self.tree_saldo.get_children():
            self.tree_saldo.delete(item)
        self.saldo_acumulado_mes = 0.00
        
        # Recarrega os dados do Firebase (poderia ser otimizado, mas assim é mais seguro)
        if not primeira_carga:
            self.dados_caixa_comissao = fm.carregar_caixa_comissao()
        
        registros_consultor = self.dados_caixa_comissao.get(self.nome_consultor_logado, {})
        
        # Pega as datas do filtro
        try:
            data_filtro_de = self.filtro_data_de.entry.get_date()
            data_filtro_ate = self.filtro_data_ate.entry.get_date()
        except:
            # Pega o primeiro e último dia do mês atual
            hoje = date.today()
            data_filtro_de = hoje.replace(day=1)
            ultimo_dia = calendar.monthrange(hoje.year, hoje.month)[1]
            data_filtro_ate = hoje.replace(day=ultimo_dia)
            
            self.filtro_data_de.entry.set_date(data_filtro_de)
            self.filtro_data_ate.entry.set_date(data_filtro_ate)

        # Filtra e exibe
        total_acumulado = 0.0
        
        # Itera sobre os meses (ex: "2025-11")
        for mes_ano, registros_do_mes in registros_consultor.items():
            # Itera sobre os registros (ex: "2025-11-14_103050")
            for id_registro, dados in registros_do_mes.items():
                try:
                    data_registro = datetime.strptime(dados['data'], "%d/%m/%Y").date()
                    
                    # Filtra pela data
                    if data_filtro_de <= data_registro <= data_filtro_ate:
                        val_produtos = dados.get('comissao_produtos', 0)
                        val_planos = dados.get('comissao_planos', 0)
                        val_total = dados.get('total_dia', 0)
                        
                        total_acumulado += val_total
                        
                        self.tree_saldo.insert('', 'end', values=(
                            dados['data'],
                            formatar_reais(val_produtos),
                            formatar_reais(val_planos),
                            formatar_reais(val_total)
                        ))
                except Exception as e:
                    print(f"Erro ao processar registro {id_registro}: {e}")

        # Atualiza o saldo (mas mantém oculto)
        self.saldo_acumulado_mes = total_acumulado
        self.saldo_label.config(text="R$ ****,**", bootstyle='secondary')
        self.saldo_esta_visivel = False