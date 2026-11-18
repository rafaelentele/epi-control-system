import os, shutil, subprocess, sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
from app.term_config import (
    carregar_configuracoes, salvar_configuracoes, data_dir,
    modelos_ativos, obter_modelo, novo_id_modelo,
)
from app.modelos_importacao import baixar_modelo_importacao
from gui.importacao_dialog import importar_planilha_dialog
from app.config.database import DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME


class ConfiguracoesSistemaFrame(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent, padding=12)
        self.cfg = carregar_configuracoes()
        self.logo_var = tk.StringVar(value=self.cfg.get('logo_empresa', ''))
        self.empresa_var = tk.StringVar(value=self.cfg.get('nome_empresa', 'PRORURAL'))
        self.modelo_id_var = tk.StringVar()
        self.nome_modelo_var = tk.StringVar()
        self.titulo_modelo_var = tk.StringVar()
        self.padrao_var = tk.BooleanVar(value=False)
        self.modelos = []
        self._montar_tela()
        self._recarregar_modelos()

    def _montar_tela(self):
        ttk.Label(self, text='Configurações do sistema', font=('Segoe UI', 14, 'bold')).pack(anchor='w', pady=(0, 10))
        termo = ttk.LabelFrame(self, text='Termos de Responsabilidade', padding=10)
        termo.pack(fill='x', pady=5)

        topo = ttk.Frame(termo)
        topo.grid(row=0, column=0, columnspan=3, sticky='ew', pady=(0, 8))
        ttk.Label(topo, text='Modelo:').pack(side='left')
        self.combo_modelo = ttk.Combobox(topo, textvariable=self.modelo_id_var, state='readonly', width=42)
        self.combo_modelo.pack(side='left', padx=(6, 8))
        self.combo_modelo.bind('<<ComboboxSelected>>', lambda _e: self._carregar_modelo_selecionado())
        ttk.Button(topo, text='+ Novo', command=self.novo_modelo).pack(side='left', padx=2)
        ttk.Button(topo, text='Duplicar', command=self.duplicar_modelo).pack(side='left', padx=2)
        ttk.Button(topo, text='Excluir', command=self.excluir_modelo).pack(side='left', padx=2)

        ttk.Label(termo, text='Nome do modelo:').grid(row=1, column=0, sticky='w', pady=4)
        self.nome_modelo = ttk.Entry(termo, textvariable=self.nome_modelo_var, width=55)
        self.nome_modelo.grid(row=1, column=1, columnspan=2, sticky='ew', pady=4)

        ttk.Label(termo, text='Título que aparecerá no PDF:').grid(row=2, column=0, sticky='w', pady=4)
        self.titulo_modelo = ttk.Entry(termo, textvariable=self.titulo_modelo_var, width=55)
        self.titulo_modelo.grid(row=2, column=1, columnspan=2, sticky='ew', pady=4)

        self.chk_padrao = ttk.Checkbutton(termo, text='Usar este modelo como padrão', variable=self.padrao_var)
        self.chk_padrao.grid(row=3, column=1, sticky='w', pady=(2, 8))

        ttk.Label(termo, text='Nome da empresa:').grid(row=4, column=0, sticky='w', pady=4)
        ttk.Entry(termo, textvariable=self.empresa_var, width=55).grid(row=4, column=1, columnspan=2, sticky='ew', pady=4)

        ttk.Label(termo, text='Texto de abertura (use {empresa}, {funcionario}, {setor}, {pedido} ou {data}):').grid(row=5, column=0, columnspan=3, sticky='w', pady=(8, 2))
        self.abertura = tk.Text(termo, height=4, width=90, wrap='word')
        self.abertura.grid(row=6, column=0, columnspan=3, sticky='ew')

        ttk.Label(termo, text='Texto antes das cláusulas:').grid(row=7, column=0, columnspan=3, sticky='w', pady=(8, 2))
        self.compromisso = tk.Text(termo, height=3, width=90, wrap='word')
        self.compromisso.grid(row=8, column=0, columnspan=3, sticky='ew')

        ttk.Label(termo, text='Cláusulas (uma por linha):').grid(row=9, column=0, columnspan=3, sticky='w', pady=(8, 2))
        self.clausulas = tk.Text(termo, height=7, width=90, wrap='word')
        self.clausulas.grid(row=10, column=0, columnspan=3, sticky='ew')

        ttk.Label(termo, text='Logo da empresa:').grid(row=11, column=0, sticky='w', pady=5)
        ttk.Entry(termo, textvariable=self.logo_var, width=65).grid(row=11, column=1, sticky='ew')
        ttk.Button(termo, text='Importar logo...', command=self.escolher_logo).grid(row=11, column=2, padx=5)

        ttk.Button(termo, text='Salvar modelo', command=self.salvar_termo).grid(row=12, column=1, sticky='e', pady=8)
        ttk.Label(termo, text='O modelo padrão será usado automaticamente quando nenhum outro for escolhido.', foreground='#666').grid(row=13, column=0, columnspan=3, sticky='w')
        termo.columnconfigure(1, weight=1)

        backup = ttk.LabelFrame(self, text='Backup do banco de dados Aiven', padding=10); backup.pack(fill='x', pady=5)
        ttk.Label(backup, text='Gera um arquivo SQL completo do banco remoto.').pack(side='left'); ttk.Button(backup, text='Fazer backup agora', command=self.backup).pack(side='right')
        imp = ttk.LabelFrame(self, text='Importação de dados', padding=10); imp.pack(fill='x', pady=5)
        ttk.Label(imp, text='Planilhas: categorias, funcionários e fornecedores. SQL: restauração do banco completo.').pack(anchor='w'); botoes_imp = ttk.Frame(imp); botoes_imp.pack(fill='x', pady=(6, 0)); ttk.Button(botoes_imp, text='Importar planilha...', command=self.importar).pack(side='left'); ttk.Button(botoes_imp, text='Baixar modelo', command=lambda: baixar_modelo_importacao(self)).pack(side='left', padx=6); ttk.Button(botoes_imp, text='Importar banco SQL...', command=self.importar_sql).pack(side='left', padx=6)
        ttk.Label(self, text='Segurança: faça backup antes de importar. A importação adiciona dados; não apaga registros existentes.', foreground='#8a4b08').pack(anchor='w', pady=5)

    def _recarregar_modelos(self, selecionar_id=None):
        self.modelos = modelos_ativos(self.cfg)
        if not self.modelos:
            self.cfg['modelos_termo'] = []
            self.novo_modelo()
            return
        nomes = [m.get('nome', 'Modelo') for m in self.modelos]
        self.combo_modelo['values'] = nomes
        alvo = selecionar_id or self.cfg.get('modelo_padrao_id') or self.modelos[0].get('id')
        indice = next((i for i, m in enumerate(self.modelos) if m.get('id') == alvo), 0)
        self.combo_modelo.current(indice)
        self._carregar_modelo_selecionado()

    def _modelo_atual(self):
        indice = self.combo_modelo.current()
        if 0 <= indice < len(self.modelos):
            return self.modelos[indice]
        return None

    def _carregar_modelo_selecionado(self):
        modelo = self._modelo_atual()
        if not modelo:
            return
        self.nome_modelo_var.set(modelo.get('nome', ''))
        self.empresa_var.set(modelo.get('nome_empresa') or self.cfg.get('nome_empresa') or 'PRORURAL')
        self.titulo_modelo_var.set(modelo.get('titulo', 'TERMO DE RESPONSABILIDADE'))
        self.padrao_var.set(modelo.get('id') == self.cfg.get('modelo_padrao_id'))
        self.abertura.delete('1.0', tk.END); self.abertura.insert('1.0', modelo.get('texto_abertura', ''))
        self.compromisso.delete('1.0', tk.END); self.compromisso.insert('1.0', modelo.get('texto_compromisso', ''))
        self.clausulas.delete('1.0', tk.END); self.clausulas.insert('1.0', '\n'.join(modelo.get('clausulas', [])))

    def novo_modelo(self):
        novo_id = novo_id_modelo(self.cfg.get('modelos_termo', []))
        modelo = {
            'id': novo_id,
            'nome': 'Novo modelo',
            'nome_empresa': self.empresa_var.get().strip() or 'PRORURAL',
            'titulo': 'TERMO DE RESPONSABILIDADE',
            'texto_abertura': 'Recebi da empresa {empresa}, gratuitamente, para uso exclusivo no desempenho de minhas atividades na empresa, conforme determinado em lei, os equipamentos relacionados neste termo de responsabilidade.',
            'texto_compromisso': 'Comprometo-me a usar e mantê-lo em perfeito estado de conservação, ficando ainda ciente de:',
            'clausulas': [],
            'ativo': True,
        }
        self.cfg.setdefault('modelos_termo', []).append(modelo)
        self.cfg['modelo_padrao_id'] = self.cfg.get('modelo_padrao_id') or novo_id
        self.salvar_configuracoes_silencioso()
        self._recarregar_modelos(novo_id)
        self.nome_modelo.focus_set()
        self.nome_modelo.selection_range(0, tk.END)

    def duplicar_modelo(self):
        atual = self._modelo_atual()
        if not atual:
            return
        copia = dict(atual)
        copia['id'] = novo_id_modelo(self.cfg.get('modelos_termo', []))
        copia['nome'] = f"Cópia - {atual.get('nome', 'Modelo')}"
        copia['ativo'] = True
        self.cfg.setdefault('modelos_termo', []).append(copia)
        self.salvar_configuracoes_silencioso()
        self._recarregar_modelos(copia['id'])

    def excluir_modelo(self):
        atual = self._modelo_atual()
        if not atual:
            return
        if len(self.modelos) <= 1:
            messagebox.showwarning('Modelo obrigatório', 'Mantenha pelo menos um modelo de termo cadastrado.')
            return
        if atual.get('id') == self.cfg.get('modelo_padrao_id'):
            messagebox.showwarning('Modelo padrão', 'Defina outro modelo como padrão antes de excluir este modelo.')
            return
        if not messagebox.askyesno('Excluir modelo', f"Deseja excluir o modelo '{atual.get('nome')}'?", parent=self):
            return
        self.cfg['modelos_termo'] = [m for m in self.cfg.get('modelos_termo', []) if m.get('id') != atual.get('id')]
        self.salvar_configuracoes_silencioso()
        self._recarregar_modelos()

    def salvar_configuracoes_silencioso(self):
        salvar_configuracoes(self.cfg)

    def escolher_logo(self):
        p = filedialog.askopenfilename(title='Selecionar logo da empresa', filetypes=[('Imagens', '*.png *.jpg *.jpeg'), ('Todos os arquivos', '*.*')])
        if p: self.logo_var.set(p)

    def salvar_termo(self):
        modelo = self._modelo_atual()
        if not modelo:
            messagebox.showwarning('Modelo', 'Selecione ou crie um modelo antes de salvar.')
            return
        nome = self.nome_modelo_var.get().strip()
        titulo = self.titulo_modelo_var.get().strip()
        if not nome:
            messagebox.showwarning('Modelo', 'Informe o nome do modelo.')
            self.nome_modelo.focus_set(); return
        if not titulo:
            messagebox.showwarning('Modelo', 'Informe o título que aparecerá no PDF.')
            self.titulo_modelo.focus_set(); return

        self.cfg['nome_empresa'] = self.empresa_var.get().strip() or 'Empresa'
        modelo.update({
            'nome': nome,
            'nome_empresa': self.empresa_var.get().strip() or 'Empresa',
            'titulo': titulo,
            'texto_abertura': self.abertura.get('1.0', 'end').strip(),
            'texto_compromisso': self.compromisso.get('1.0', 'end').strip(),
            'clausulas': [x.strip() for x in self.clausulas.get('1.0', 'end').splitlines() if x.strip()],
            'ativo': True,
        })
        if self.padrao_var.get():
            self.cfg['modelo_padrao_id'] = modelo['id']
        elif self.cfg.get('modelo_padrao_id') == modelo['id']:
            # O padrão não pode ficar sem substituto; mantém este como padrão.
            self.padrao_var.set(True)
            messagebox.showinfo('Modelo padrão', 'Este modelo continua como padrão. Para trocar, selecione outro modelo, marque como padrão e salve.')

        logo = self.logo_var.get().strip()
        if logo and os.path.isfile(logo):
            dest = data_dir() / ('logo_empresa_termo' + Path(logo).suffix.lower())
            try:
                shutil.copy2(logo, dest); self.cfg['logo_empresa'] = str(dest)
            except Exception as e:
                messagebox.showerror('Logo', str(e)); return

        self.cfg['texto_abertura'] = modelo['texto_abertura']
        self.cfg['texto_compromisso'] = modelo['texto_compromisso']
        self.cfg['clausulas'] = modelo['clausulas']
        self.cfg['titulo_termo'] = modelo['titulo']
        salvar_configuracoes(self.cfg)
        self._recarregar_modelos(modelo['id'])
        messagebox.showinfo('Configurações', 'Modelo de termo salvo com sucesso. Os próximos termos usarão o modelo escolhido ou o modelo padrão.')

    def backup(self):
        destino = filedialog.asksaveasfilename(title='Salvar backup Aiven', defaultextension='.sql', initialfile='backup_fardamento.sql', filetypes=[('Backup SQL', '*.sql')])
        if not destino: return
        candidatos = [shutil.which('mysqldump'), r'C:\Program Files\MySQL\MySQL Server 8.0\bin\mysqldump.exe', r'C:\Program Files\MySQL\MySQL Server 8.4\bin\mysqldump.exe']
        exe = next((x for x in candidatos if x and os.path.isfile(x)), None)
        if not exe:
            messagebox.showerror('Backup', 'Não encontrei o mysqldump. Instale MySQL Client ou coloque mysqldump.exe no PATH.'); return
        env = os.environ.copy(); env['MYSQL_PWD'] = DB_PASSWORD
        cmd = [exe, '--host='+DB_HOST, '--port='+str(DB_PORT), '--user='+DB_USER, '--default-character-set=utf8mb4', '--single-transaction', '--ssl-mode=REQUIRED', '--result-file='+destino, DB_NAME]
        try:
            r = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=300)
            if r.returncode == 0 and os.path.exists(destino) and os.path.getsize(destino) > 0: messagebox.showinfo('Backup concluído', 'Backup salvo em:\n'+destino)
            else: messagebox.showerror('Falha no backup', (r.stderr or r.stdout or 'mysqldump retornou erro'))
        except Exception as e: messagebox.showerror('Falha no backup', str(e))

    def importar_sql(self):
        origem = filedialog.askopenfilename(title='Selecionar backup SQL para importar', filetypes=[('Arquivos SQL', '*.sql'), ('Todos os arquivos', '*.*')])
        if not origem: return
        ok = messagebox.askyesno('Atenção: importar banco SQL', 'Esta operação executa os comandos do arquivo SQL no banco atualmente configurado. Pode substituir ou apagar dados existentes.\n\nFaça um backup recente do Aiven antes de continuar. Deseja prosseguir?', icon='warning', parent=self)
        if not ok: return
        candidatos = [shutil.which('mysql'), r'C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe', r'C:\Program Files\MySQL\MySQL Server 8.4\bin\mysql.exe']
        exe = next((x for x in candidatos if x and os.path.isfile(x)), None)
        if not exe:
            messagebox.showerror('Importar SQL', 'Não encontrei mysql.exe. Instale MySQL Client ou adicione mysql.exe ao PATH.', parent=self); return
        env = os.environ.copy(); env['MYSQL_PWD'] = DB_PASSWORD
        cmd = [exe, '--host='+DB_HOST, '--port='+str(DB_PORT), '--user='+DB_USER, '--default-character-set=utf8mb4']
        if os.getenv('DB_SSL', 'false').lower() == 'true': cmd.append('--ssl-mode=REQUIRED')
        cmd.append(DB_NAME)
        try:
            with open(origem, 'rb') as sql:
                r = subprocess.run(cmd, stdin=sql, env=env, capture_output=True, timeout=900)
            if r.returncode == 0:
                messagebox.showinfo('Importação SQL concluída', 'O arquivo SQL foi executado no banco configurado.', parent=self)
            else:
                erro = (r.stderr or r.stdout or b'Erro sem detalhes').decode('utf-8', 'replace')
                messagebox.showerror('Falha na importação SQL', erro[-4000:], parent=self)
        except Exception as e: messagebox.showerror('Falha na importação SQL', str(e), parent=self)

    def importar(self):
        importar_planilha_dialog(self)
