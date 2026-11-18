"""Autenticacao, sessao e permissoes do sistema."""
import hashlib
import hmac
import secrets
import tkinter as tk
from tkinter import ttk, messagebox
from sqlalchemy import inspect, text

from app.config.database import IS_SQLITE, engine, get_session, iniciar_esquema
from app.models.models import Usuario, UsuarioPermissao
from app.branding import asset_path

PERMISSOES = {
    "consultar_produtos": "Consultar produtos",
    "cadastrar_produtos": "Cadastrar produtos",
    "editar_produtos": "Editar produtos",
    "excluir_produtos": "Excluir produtos",
    "alterar_estoque_minimo": "Alterar estoque mínimo",
    "consultar_estoque": "Consultar estoque",
    "cadastrar_funcionarios": "Cadastrar funcionários",
    "editar_funcionarios": "Editar funcionários",
    "excluir_funcionarios": "Excluir funcionários",
    "consultar_funcionarios": "Consultar funcionários",
    "cadastrar_fornecedores": "Cadastrar fornecedores",
    "editar_fornecedores": "Editar fornecedores",
    "excluir_fornecedores": "Excluir fornecedores",
    "consultar_fornecedores": "Consultar fornecedores",
    "criar_pedido_compra": "Criar pedido de compra",
    "editar_pedido_compra": "Editar pedido de compra",
    "excluir_pedido_compra": "Excluir pedido de compra",
    "consultar_pedidos": "Consultar pedidos",
    "dar_entrada": "Dar entrada no estoque",
    "dar_baixa": "Dar baixa de fardamento",
    "ajustar_estoque": "Ajustar estoque",
    "acessar_relatorios": "Acessar relatórios",
    "gerenciar_usuarios": "Gerenciar usuários",
    "gerenciar_empresas": "Cadastrar e gerenciar empresas",
    "gerar_termo": "Gerar termo de responsabilidade",
}

PERMISSOES_OPERADOR_PADRAO = {
    "consultar_produtos", "consultar_estoque",
    "cadastrar_funcionarios", "consultar_funcionarios",
    "cadastrar_fornecedores", "consultar_fornecedores",
    "consultar_pedidos", "dar_entrada", "dar_baixa",
}

USUARIO_ATUAL = None


def _hash_senha(senha, salt=None):
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", senha.encode("utf-8"), salt.encode("utf-8"), 200_000
    ).hex()
    return f"pbkdf2_sha256$200000${salt}${digest}"


def verificar_senha(senha, armazenada):
    if not armazenada or "$" not in armazenada:
        return False
    try:
        algoritmo, it, salt, digest = armazenada.split("$", 3)
        if algoritmo != "pbkdf2_sha256":
            return False
        calculado = hashlib.pbkdf2_hmac(
            "sha256", senha.encode("utf-8"), salt.encode("utf-8"), int(it)
        ).hex()
        return hmac.compare_digest(calculado, digest)
    except Exception:
        return False


def garantir_estrutura_autenticacao():
    """Garante senha/permissoes no banco sem apagar dados existentes.

    Tambem inicializa usuarios antigos com a senha temporaria 123456 e
    permissao padrao de operador quando ainda nao houver permissoes salvas.
    No SQLite vazio, cria o administrador padrao (login admin / senha 123456).
    """
    iniciar_esquema()
    insp = inspect(engine)
    insert_permissao = (
        "INSERT OR IGNORE INTO usuario_permissao (id_usuario, permissao) VALUES (:id,:p)"
        if IS_SQLITE
        else "INSERT IGNORE INTO usuario_permissao (id_usuario, permissao) VALUES (:id,:p)"
    )

    with engine.begin() as conn:
        colunas_produtos = {c["name"] for c in insp.get_columns("produtos")}
        if "ca" not in colunas_produtos:
            conn.execute(text("ALTER TABLE produtos ADD COLUMN ca VARCHAR(50) NULL"))

        colunas_usuario = {c["name"] for c in insp.get_columns("usuario")}
        if "password_hash" not in colunas_usuario:
            conn.execute(
                text("ALTER TABLE usuario ADD COLUMN password_hash VARCHAR(255) NULL")
            )

        usuarios = conn.execute(
            text("SELECT id_usuario, nivel_acesso, password_hash FROM usuario")
        ).mappings().all()

        if not usuarios:
            conn.execute(
                text(
                    "INSERT INTO usuario (nome, login, nivel_acesso, password_hash) "
                    "VALUES (:nome, :login, :nivel, :senha)"
                ),
                {
                    "nome": "Administrador",
                    "login": "admin",
                    "nivel": "Administrador",
                    "senha": _hash_senha("123456"),
                },
            )
            id_admin = conn.execute(
                text("SELECT id_usuario FROM usuario WHERE login = :login"),
                {"login": "admin"},
            ).scalar_one()
            for p in PERMISSOES:
                conn.execute(text(insert_permissao), {"id": id_admin, "p": p})
            return

        for u in usuarios:
            # Nova permissão: administradores existentes recebem acesso ao cadastro de empresas.
            # Operadores não recebem acesso automaticamente; o administrador pode habilitá-lo
            # individualmente na tela Usuários e Permissões.
            if u["nivel_acesso"] == "Administrador":
                conn.execute(
                    text(insert_permissao),
                    {"id": u["id_usuario"], "p": "gerenciar_empresas"},
                )

            if not u["password_hash"]:
                conn.execute(
                    text("UPDATE usuario SET password_hash=:senha WHERE id_usuario=:id"),
                    {"senha": _hash_senha("123456"), "id": u["id_usuario"]},
                )

            qtd = conn.execute(
                text("SELECT COUNT(*) FROM usuario_permissao WHERE id_usuario=:id"),
                {"id": u["id_usuario"]},
            ).scalar_one()
            if qtd == 0:
                permissoes = PERMISSOES if u["nivel_acesso"] == "Administrador" else PERMISSOES_OPERADOR_PADRAO
                for p in permissoes:
                    conn.execute(
                        text(insert_permissao),
                        {"id": u["id_usuario"], "p": p},
                    )


def autenticar(login, senha):
    garantir_estrutura_autenticacao()
    session = get_session()
    try:
        usuario = session.query(Usuario).filter(Usuario.login == login).first()
        if usuario is None or not verificar_senha(senha, usuario.password_hash):
            return None
        permissoes = {
            p.permissao
            for p in session.query(UsuarioPermissao)
            .filter(UsuarioPermissao.id_usuario == usuario.id_usuario).all()
        }
        return {
            "id_usuario": usuario.id_usuario,
            "nome": usuario.nome,
            "login": usuario.login,
            "nivel_acesso": usuario.nivel_acesso,
            "permissoes": permissoes,
        }
    finally:
        session.close()


def definir_usuario_atual(usuario):
    global USUARIO_ATUAL
    USUARIO_ATUAL = usuario


def obter_usuario_atual():
    return USUARIO_ATUAL


def tem_permissao(permissao):
    if USUARIO_ATUAL is None:
        return False
    if USUARIO_ATUAL.get("nivel_acesso") == "Administrador":
        return True
    return permissao in USUARIO_ATUAL.get("permissoes", set())


def atualizar_sessao_permissoes():
    global USUARIO_ATUAL
    if USUARIO_ATUAL is None:
        return
    session = get_session()
    try:
        u = session.get(Usuario, USUARIO_ATUAL["id_usuario"])
        if u:
            perms = {
                p.permissao
                for p in session.query(UsuarioPermissao)
                .filter(UsuarioPermissao.id_usuario == u.id_usuario).all()
            }
            USUARIO_ATUAL.update(
                nivel_acesso=u.nivel_acesso,
                nome=u.nome,
                login=u.login,
                permissoes=perms,
            )
    finally:
        session.close()


class LoginApp(tk.Tk):
    """Janela principal de login. Usar Tk visivel evita o problema de Toplevel escondido."""
    def __init__(self):
        super().__init__()
        self.resultado = None
        self.title("Acesso - Sistema de Controle de Fardamento")
        try:
            self.iconbitmap(str(asset_path("icone_sistema.ico")))
        except Exception:
            pass
        self.resizable(False, False)
        self.protocol("WM_DELETE_WINDOW", self._cancelar)

        frame = ttk.Frame(self, padding=28)
        frame.pack(fill="both", expand=True)
        try:
            self._logo_login = tk.PhotoImage(file=str(asset_path("logo_login.png")))
            ttk.Label(frame, image=self._logo_login).grid(row=0, column=0, columnspan=2, pady=(0, 14))
            row = 1
        except Exception:
            row = 0
        ttk.Label(frame, text="Login:").grid(row=row, column=0, sticky="w", pady=6)
        self.login = ttk.Entry(frame, width=32)
        self.login.grid(row=row, column=1, pady=6)
        row += 1
        ttk.Label(frame, text="Senha:").grid(row=row, column=0, sticky="w", pady=6)
        self.senha = ttk.Entry(frame, width=32, show="*")
        self.senha.grid(row=row, column=1, pady=6)
        row += 1
        self.mensagem = ttk.Label(frame, text="")
        self.mensagem.grid(row=row, column=0, columnspan=2, pady=5)
        row += 1
        botoes = ttk.Frame(frame)
        botoes.grid(row=row, column=0, columnspan=2, pady=(12, 0))
        ttk.Button(botoes, text="Entrar", command=self._entrar).pack(side="left", padx=5)
        ttk.Button(botoes, text="Sair", command=self._cancelar).pack(side="left", padx=5)
        self._login_layout_rows = row
        self.bind("<Return>", lambda _e: self._entrar())
        self.login.focus_set()
        self.update_idletasks()
        largura = max(480, self.winfo_reqwidth())
        altura = self.winfo_reqheight()
        x = (self.winfo_screenwidth() - largura) // 2
        y = (self.winfo_screenheight() - altura) // 2
        self.geometry(f"{largura}x{altura}+{x}+{y}")

    def _entrar(self):
        login = self.login.get().strip()
        senha = self.senha.get()
        if not login or not senha:
            self.mensagem.configure(text="Informe login e senha.")
            return
        try:
            usuario = autenticar(login, senha)
        except Exception as exc:
            messagebox.showerror(
                "Erro de acesso",
                "Não foi possível acessar o banco de dados.\n\n" + str(exc),
                parent=self,
            )
            return
        if usuario is None:
            self.mensagem.configure(text="Login ou senha inválidos.")
            self.senha.delete(0, tk.END)
            self.senha.focus_set()
            return
        definir_usuario_atual(usuario)
        self.resultado = usuario
        self.destroy()

    def _cancelar(self):
        self.resultado = None
        self.destroy()


def abrir_login():
    janela = LoginApp()
    janela.mainloop()
    return janela.resultado
