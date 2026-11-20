"""Importador histórico seguro da planilha de fardamento.

Importa somente movimentações das abas:
- REGISTRO DE ENTRADA
- REGISTRO DE SAIDA

Regras especiais:
- AJUSTE/AJSUTE na entrada => ajuste positivo.
- AJUSTE/AJSUTE na saída => ajuste negativo.
- Devoluções/retornos identificados na coluna FORNECEDOR da entrada continuam sendo entradas normais; não criam fornecedor fictício.
- datas Excel seriais (ex.: 46001) são convertidas corretamente.

Somente as abas REGISTRO DE ENTRADA e REGISTRO DE SAIDA movimentam o banco.
STATUS ESTOQUE é apenas uma aba de referência e não é importada como estoque.
Qualquer outra aba é ignorada.
Não apaga dados existentes. A operação é transacional e idempotente por arquivo/aba/linha.
"""
from __future__ import annotations

import hashlib
import re
import unicodedata
from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from tkinter import Tk, filedialog, messagebox

from openpyxl import load_workbook
from openpyxl.utils.datetime import from_excel
from sqlalchemy import text

from app.auth import abrir_login, garantir_estrutura_autenticacao
from app.config.database import engine, get_session
from app.models.models import (
    AjusteEstoque,
    Auditoria,
    Categoria,
    Entrada,
    Fornecedor,
    Funcionario,
    PedidoDeCompra,
    PedidoSaida,
    Produto,
    Saida,
    SetorLoja,
    Tamanho,
)

SHEET_ENTRADA = "REGISTRO DE ENTRADA"
SHEET_SAIDA = "REGISTRO DE SAIDA"
CATEGORIA_PADRAO = "Fardamento"
FORNECEDOR_NAO_INFORMADO = "NÃO INFORMADO"
SETOR_NAO_INFORMADO = "NÃO INFORMADO"
FUNC_AJUSTE = "AJUSTE HISTÓRICO"
FUNC_MOVIMENTO = "MOVIMENTO HISTÓRICO"


def normalizar_texto(valor) -> str:
    if valor is None:
        return ""
    return " ".join(str(valor).strip().split())


def chave_texto(valor) -> str:
    texto = normalizar_texto(valor).upper()
    texto = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in texto if not unicodedata.combining(c))


def normalizar_tamanho(valor) -> str:
    if valor is None or str(valor).strip() == "":
        return ""
    if isinstance(valor, float) and valor.is_integer():
        return str(int(valor))
    if isinstance(valor, int):
        return str(valor)
    s = normalizar_texto(valor)
    if re.fullmatch(r"\d+\.0+", s):
        s = s.split(".", 1)[0]
    return s.upper()


def data_excel(valor) -> date | None:
    if valor is None or valor == "":
        return None
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    if isinstance(valor, (int, float)) and not isinstance(valor, bool):
        try:
            convertido = from_excel(valor)
            if isinstance(convertido, datetime):
                return convertido.date()
            if isinstance(convertido, date):
                return convertido
        except Exception:
            pass
    s = normalizar_texto(valor)
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    raise ValueError(f"Data não reconhecida: {valor!r}")


def inteiro(valor) -> int | None:
    if valor is None or valor == "":
        return None
    if isinstance(valor, bool):
        return int(valor)
    if isinstance(valor, Decimal):
        if valor != int(valor):
            raise ValueError(f"Quantidade não inteira: {valor}")
        return int(valor)
    if isinstance(valor, float):
        if not valor.is_integer():
            raise ValueError(f"Quantidade não inteira: {valor}")
        return int(valor)
    return int(str(valor).strip())


def decimal(valor) -> Decimal:
    if valor is None or valor == "":
        return Decimal("0")
    if isinstance(valor, Decimal):
        return valor
    if isinstance(valor, (int, float)):
        return Decimal(str(valor))
    s = normalizar_texto(valor).replace("R$", "").replace(".", "").replace(",", ".")
    return Decimal(s)


def eh_ajuste(texto) -> bool:
    return chave_texto(texto) in {"AJUSTE", "AJSUTE", "AJUSTE DE ESTOQUE"}


def eh_ajuste_entrada(texto) -> bool:
    """Identifica somente AJUSTE/AJSUTE na coluna FORNECEDOR.

    Devoluções e retornos registrados nessa coluna continuam sendo entradas
    normais; apenas deixam de ser tratados como fornecedores reais.
    """
    return eh_ajuste(texto)


def eh_transferencia(texto) -> bool:
    k = chave_texto(texto).replace(" ", "")
    return "TRANSFERENCIAARQUIVO" in k or "TRANSFERENCIAARMARIO" in k


def eh_entrada_historica(texto) -> bool:
    return chave_texto(texto) in {"ENTRADA DE PRODUTO", "ENTRADA DE PRODUTOS"}


def eh_saida_historica(texto) -> bool:
    return chave_texto(texto) in {"SAIDA DE PRODUTO", "SAIDA DE PRODUTOS"}


def normalizar_fornecedor(valor) -> tuple[str, str | None]:
    original = normalizar_texto(valor)
    if not original:
        return FORNECEDOR_NAO_INFORMADO, None
    k = chave_texto(original)
    especiais = (
        eh_ajuste(original)
        or k.startswith("DEVOLUCAO")
        or k.startswith("FARDAMENTO DE ")
        or k == "CHEGOU DA LAVAGEM"
    )
    if especiais or len(original) > 45:
        return FORNECEDOR_NAO_INFORMADO, original
    return original, None


def sha256_arquivo(caminho: Path) -> str:
    h = hashlib.sha256()
    with caminho.open("rb") as f:
        for bloco in iter(lambda: f.read(1024 * 1024), b""):
            h.update(bloco)
    return h.hexdigest()


def fingerprint_linha(arquivo_hash, planilha, linha, valores) -> str:
    bruto = "|".join(normalizar_texto(v) for v in valores)
    return hashlib.sha256(f"{arquivo_hash}|{planilha}|{linha}|{bruto}".encode("utf-8")).hexdigest()


def garantir_tabela_importacao():
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS importacao_historica (
                id_importacao INT AUTO_INCREMENT PRIMARY KEY,
                arquivo_hash CHAR(64) NOT NULL,
                nome_arquivo VARCHAR(255) NOT NULL,
                planilha VARCHAR(100) NOT NULL,
                linha_excel INT NOT NULL,
                fingerprint CHAR(64) NOT NULL,
                entidade VARCHAR(50) NOT NULL,
                id_registro INT NULL,
                importado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE KEY uq_importacao_fingerprint (fingerprint),
                INDEX idx_importacao_arquivo (arquivo_hash),
                INDEX idx_importacao_origem (planilha, linha_excel)
            ) ENGINE=InnoDB
        """))


def ler_planilha(caminho: Path):
    wb = load_workbook(caminho, read_only=True, data_only=True)
    obrigatorias = {SHEET_ENTRADA, SHEET_SAIDA}
    faltantes = obrigatorias.difference(wb.sheetnames)
    if faltantes:
        raise ValueError("A planilha não possui as abas obrigatórias: " + ", ".join(sorted(faltantes)))

    movimentos = []
    ignorados = []

    # Entradas atuais
    ws = wb[SHEET_ENTRADA]
    for linha, row in enumerate(ws.iter_rows(min_row=2, values_only=True), 2):
        if not any(v is not None and str(v).strip() for v in row[:5]):
            continue
        item, tamanho, qtd, data_mov, fornecedor_raw = row[:5]
        item = normalizar_texto(item); tamanho = normalizar_tamanho(tamanho)
        qtd = inteiro(qtd); data_mov = data_excel(data_mov)
        fornecedor_raw = normalizar_texto(fornecedor_raw)
        if qtd is None or qtd == 0:
            ignorados.append((SHEET_ENTRADA, linha, "quantidade zero/vazia")); continue
        if eh_ajuste_entrada(fornecedor_raw):
            # Somente AJUSTE/AJSUTE na coluna FORNECEDOR vira ajuste histórico positivo.
            delta = abs(qtd)
            movimentos.append({"tipo":"ajuste","planilha":SHEET_ENTRADA,"linha":linha,"item":item,"tamanho":tamanho,"quantidade":delta,"data":data_mov,"motivo":f"Importação histórica - {fornecedor_raw}","observacao":"Origem: REGISTRO DE ENTRADA"})
        else:
            # Devoluções/retornos continuam sendo ENTRADAS normais.
            # Se o texto não for fornecedor real, normalizar_fornecedor o coloca
            # como NÃO INFORMADO e preserva o texto original em nota_fornecedor.
            fornecedor, nota = normalizar_fornecedor(fornecedor_raw)
            movimentos.append({"tipo":"entrada","planilha":SHEET_ENTRADA,"linha":linha,"item":item,"tamanho":tamanho,"quantidade":qtd,"data":data_mov,"fornecedor":fornecedor,"nota_fornecedor":nota})

    # Saídas atuais
    ws = wb[SHEET_SAIDA]
    for linha, row in enumerate(ws.iter_rows(min_row=2, values_only=True), 2):
        if not any(v is not None and str(v).strip() for v in row[:6]):
            continue
        funcionario, setor, item, tamanho, qtd, data_mov = row[:6]
        funcionario = normalizar_texto(funcionario); setor = normalizar_texto(setor)
        item = normalizar_texto(item); tamanho = normalizar_tamanho(tamanho)
        qtd = inteiro(qtd); data_mov = data_excel(data_mov)
        if eh_ajuste(funcionario):
            if qtd is None or qtd == 0:
                ignorados.append((SHEET_SAIDA, linha, "ajuste com quantidade zero/vazia")); continue
            movimentos.append({"tipo":"ajuste","planilha":SHEET_SAIDA,"linha":linha,"item":item,"tamanho":tamanho,"quantidade":-abs(qtd),"data":data_mov,"motivo":"Importação histórica - AJUSTE na saída","observacao":"Origem: REGISTRO DE SAIDA"})
        else:
            if not setor: setor = SETOR_NAO_INFORMADO
            movimentos.append({"tipo":"saida","planilha":SHEET_SAIDA,"linha":linha,"funcionario":funcionario,"setor":setor,"item":item,"tamanho":tamanho,"quantidade":qtd,"data":data_mov,"observacao":"Origem: REGISTRO DE SAIDA"})



    wb.close()
    return movimentos, ignorados


def validar_movimentos(movimentos):
    erros=[]
    for r in movimentos:
        campos_obrigatorios = ("item", "data") if r["tipo"] == "compra" else ("item", "tamanho", "data")
        for campo in campos_obrigatorios:
            if not r.get(campo): erros.append(f"{r['planilha']} linha {r['linha']}: campo '{campo}' vazio.")
        q=r.get("quantidade")
        if q is None or q == 0: erros.append(f"{r['planilha']} linha {r['linha']}: quantidade inválida.")
        if len(r.get("item", "")) > 45: erros.append(f"{r['planilha']} linha {r['linha']}: item excede 45 caracteres: {r['item']}")
        if len(r.get("tamanho", "")) > 10: erros.append(f"{r['planilha']} linha {r['linha']}: tamanho excede 10 caracteres: {r['tamanho']}")
        if r["tipo"] == "compra":
            if not r.get("fornecedor"):
                erros.append(f"{r['planilha']} linha {r['linha']}: fornecedor vazio.")
            if r.get("quantidade", 0) <= 0:
                erros.append(f"{r['planilha']} linha {r['linha']}: quantidade de compra inválida.")
        elif r["tipo"] == "saida":
            for campo in ("funcionario","setor"):
                if not r.get(campo): erros.append(f"{r['planilha']} linha {r['linha']}: campo '{campo}' vazio.")
                elif len(r[campo]) > 45: erros.append(f"{r['planilha']} linha {r['linha']}: {campo} excede 45 caracteres.")
    return erros


def resumo_previa(movimentos, ignorados, erros):
    ent=[r for r in movimentos if r['tipo']=='entrada']; sai=[r for r in movimentos if r['tipo']=='saida']; aj=[r for r in movimentos if r['tipo']=='ajuste']
    produtos={chave_texto(r['item']) for r in movimentos if r['item']}
    funcs={chave_texto(r.get('funcionario')) for r in sai if r.get('funcionario')}
    forn={chave_texto(r.get('fornecedor')) for r in movimentos if r.get('fornecedor')}
    pos=sum(max(0,r['quantidade']) for r in aj); neg=sum(-min(0,r['quantidade']) for r in aj)
    return (
        f"ENTRADAS válidas: {len(ent)} | quantidade: {sum(r['quantidade'] for r in ent)}\n"
        f"SAÍDAS válidas: {len(sai)} | quantidade: {sum(r['quantidade'] for r in sai)}\n"
        f"AJUSTES históricos: {len(aj)} | positivos: {pos} | negativos: {neg}\n"
        f"Produtos envolvidos: {len(produtos)}\n"
        f"Funcionários/movimentos: {len(funcs)}\n"
        f"Fornecedores: {len(forn)}\n"
        f"Linhas ignoradas: {len(ignorados)}\n"
        f"Erros bloqueadores: {len(erros)}"
    )


def chave_produto(nome): return chave_texto(nome)


def montar_cache(session):
    return {
        "produtos": {chave_produto(x.nome): x for x in session.query(Produto).all()},
        "fornecedores": {chave_texto(x.nome): x for x in session.query(Fornecedor).all()},
        "funcionarios": {chave_texto(x.nome): x for x in session.query(Funcionario).all()},
        "setores": {chave_texto(x.nome): x for x in session.query(SetorLoja).all()},
        "tamanhos": {chave_texto(x.nome): x for x in session.query(Tamanho).all()},
        "categorias": {chave_texto(x.nome): x for x in session.query(Categoria).all()},
    }


def garantir_cadastros(session, cache, item, tamanho, fornecedor=None, funcionario=None, setor=None, id_usuario=None):
    criados=defaultdict(int)
    categoria=cache['categorias'].get(chave_texto(CATEGORIA_PADRAO))
    if categoria is None:
        categoria=Categoria(nome=CATEGORIA_PADRAO); session.add(categoria); session.flush(); cache['categorias'][chave_texto(CATEGORIA_PADRAO)]=categoria; criados['categorias']+=1
    pkey=chave_produto(item); produto=cache['produtos'].get(pkey)
    if produto is None:
        produto=Produto(nome=item,id_categoria=categoria.id_categoria,id_usuario=id_usuario,estoque_minimo=0); session.add(produto); session.flush(); cache['produtos'][pkey]=produto; criados['produtos']+=1
    forn=None
    if fornecedor is not None:
        fkey=chave_texto(fornecedor); forn=cache['fornecedores'].get(fkey)
        if forn is None:
            forn=Fornecedor(nome=fornecedor); session.add(forn); session.flush(); cache['fornecedores'][fkey]=forn; criados['fornecedores']+=1
    tam=None
    if tamanho is not None and normalizar_texto(tamanho):
        tkey=chave_texto(tamanho); tam=cache['tamanhos'].get(tkey)
        if tam is None:
            tam=Tamanho(nome=tamanho); session.add(tam); session.flush(); cache['tamanhos'][tkey]=tam; criados['tamanhos']+=1
    func=None
    if funcionario is not None:
        fkey=chave_texto(funcionario); func=cache['funcionarios'].get(fkey)
        if func is None:
            func=Funcionario(nome=funcionario); session.add(func); session.flush(); cache['funcionarios'][fkey]=func; criados['funcionarios']+=1
    setor_obj=None
    if setor is not None:
        skey=chave_texto(setor); setor_obj=cache['setores'].get(skey)
        if setor_obj is None:
            setor_obj=SetorLoja(nome=setor); session.add(setor_obj); session.flush(); cache['setores'][skey]=setor_obj; criados['setores']+=1
    return produto,forn,tam,func,setor_obj,criados


def preflight(caminho):
    movimentos, ignorados=ler_planilha(caminho); erros=validar_movimentos(movimentos); return movimentos,ignorados,erros


def importar(caminho,movimentos,usuario):
    garantir_tabela_importacao(); arquivo_hash=sha256_arquivo(caminho); nome_arquivo=caminho.name
    session=get_session(); id_usuario=int(usuario['id_usuario']); criados=defaultdict(int); importados=duplicados=0
    try:
        cache=montar_cache(session)
        ja=set(session.execute(text('SELECT fingerprint FROM importacao_historica')).scalars().all())
        # Movimentos que alteram o estoque.
        movimentos_estoque=movimentos
        ordem={SHEET_ENTRADA:0,SHEET_SAIDA:1}
        eventos=sorted(movimentos_estoque,key=lambda r:(r['data'], ordem.get(r['planilha'],9), r['linha']))
        saldo_historico=defaultdict(int)
        pedidos_saida={}
        pedidos_compra_cache={}
        for r in eventos:
            fpvals=[r.get(k) for k in ('tipo','item','tamanho','quantidade','data','fornecedor','funcionario','setor','motivo')]
            fp=fingerprint_linha(arquivo_hash,r['planilha'],r['linha'],fpvals)
            if fp in ja:
                duplicados+=1; continue
            produto,forn,tam,func,setor,novos=garantir_cadastros(session,cache,r['item'],r['tamanho'],r.get('fornecedor'),r.get('funcionario'),r.get('setor'),id_usuario)
            for k,v in novos.items(): criados[k]+=v
            chave=(produto.id_produto,tam.id_tamanho)
            if r['tipo']=='entrada':
                if forn is None:
                    forn=cache['fornecedores'].get(chave_texto(FORNECEDOR_NAO_INFORMADO))
                    if forn is None:
                        forn=Fornecedor(nome=FORNECEDOR_NAO_INFORMADO); session.add(forn); session.flush(); cache['fornecedores'][chave_texto(FORNECEDOR_NAO_INFORMADO)]=forn; criados['fornecedores']+=1
                pkey=(produto.id_produto,forn.id_fornecedor)
                pedido=pedidos_compra_cache.get(pkey)
                if pedido is None:
                    pedido=session.query(PedidoDeCompra).filter(PedidoDeCompra.id_produto==produto.id_produto,PedidoDeCompra.id_fornecedor==forn.id_fornecedor,PedidoDeCompra.observacao.like('IMPORTAÇÃO HISTÓRICA%')).order_by(PedidoDeCompra.id_pedido_compra.asc()).first()
                    if pedido is None:
                        pedido=PedidoDeCompra(id_produto=produto.id_produto,quantidade=0,preco=0,data_compra=r['data'],id_fornecedor=forn.id_fornecedor,observacao='IMPORTAÇÃO HISTÓRICA - pedido gerado para vincular entrada sem correspondente na aba Registro de Compra.')
                        session.add(pedido); session.flush(); criados['pedidos_compra']+=1
                    pedidos_compra_cache[pkey]=pedido
                nova=Entrada(id_produto=produto.id_produto,id_pedido_compra=pedido.id_pedido_compra,quantidade=abs(r['quantidade']),id_tamanho=tam.id_tamanho,data_entrada=r['data'],id_fornecedor=forn.id_fornecedor,id_usuario=id_usuario,observacao=('IMPORTAÇÃO HISTÓRICA' + (f" | Origem fornecedor: {r['nota_fornecedor']}" if r.get('nota_fornecedor') else ''))[:100])
                session.add(nova); session.flush(); saldo_historico[chave]+=abs(r['quantidade'])
                session.add(Auditoria(id_usuario=id_usuario,operacao='IMPORTAÇÃO',entidade='entrada',id_registro=nova.id_entrada,descricao=f"IMPORTAÇÃO HISTÓRICA: {r['planilha']} linha {r['linha']}; {produto.nome}; tamanho={tam.nome}; quantidade={r['quantidade']}; data={r['data']}.") )
                entidade='entrada'; rid=nova.id_entrada
            elif r['tipo']=='saida':
                pkey=(func.id_funcionario,setor.id_setor_loja,r['data'])
                pedido=pedidos_saida.get(pkey)
                if pedido is None:
                    pedido=PedidoSaida(id_funcionario=func.id_funcionario,id_setor_loja=setor.id_setor_loja,id_usuario=id_usuario,data_saida=r['data'],observacao='IMPORTAÇÃO HISTÓRICA - registros originados da planilha.')
                    session.add(pedido); session.flush(); pedidos_saida[pkey]=pedido; criados['pedidos_saida']+=1
                nova=Saida(id_pedido_saida=pedido.id_pedido_saida,id_produto=produto.id_produto,id_tamanho=tam.id_tamanho,quantidade=abs(r['quantidade']))
                session.add(nova); session.flush(); saldo_historico[chave]-=abs(r['quantidade'])
                session.add(Auditoria(id_usuario=id_usuario,operacao='IMPORTAÇÃO',entidade='saida',id_registro=nova.id_saida,descricao=f"IMPORTAÇÃO HISTÓRICA: {r['planilha']} linha {r['linha']}; funcionário={func.nome}; setor={setor.nome}; {produto.nome}; tamanho={tam.nome}; quantidade={r['quantidade']}; data={r['data']}.") )
                entidade='saida'; rid=nova.id_saida
            else:
                anterior=saldo_historico[chave]; posterior=anterior+int(r['quantidade'])
                ajuste=AjusteEstoque(id_produto=produto.id_produto,id_tamanho=tam.id_tamanho,quantidade_ajuste=int(r['quantidade']),estoque_anterior=anterior,estoque_posterior=posterior,motivo=r['motivo'][:60],observacao=(r.get('observacao') or '')[:1000],id_usuario=id_usuario,data_ajuste=datetime.combine(r['data'],datetime.min.time()))
                session.add(ajuste); session.flush(); saldo_historico[chave]=posterior
                session.add(Auditoria(id_usuario=id_usuario,operacao='IMPORTAÇÃO',entidade='ajuste_estoque',id_registro=ajuste.id_ajuste,descricao=f"IMPORTAÇÃO HISTÓRICA: ajuste {r['planilha']} linha {r['linha']}; {produto.nome}; tamanho={tam.nome}; diferença={r['quantidade']:+d}; estoque histórico {anterior}->{posterior}; data={r['data']}.") )
                entidade='ajuste_estoque'; rid=ajuste.id_ajuste
            session.execute(text('INSERT INTO importacao_historica (arquivo_hash,nome_arquivo,planilha,linha_excel,fingerprint,entidade,id_registro) VALUES (:ah,:nf,:pl,:ln,:fp,:ent,:rid)'),{'ah':arquivo_hash,'nf':nome_arquivo,'pl':r['planilha'],'ln':r['linha'],'fp':fp,'ent':entidade,'rid':rid})
            importados+=1
        session.add(Auditoria(id_usuario=id_usuario,operacao='IMPORTAÇÃO',entidade='planilha_historica',descricao=f'IMPORTAÇÃO HISTÓRICA concluída: arquivo={nome_arquivo}; registros importados={importados}; duplicados ignorados={duplicados}.'))
        session.commit()
        return {'importados':importados,'duplicados':duplicados,'criados':dict(criados)}
    except Exception:
        session.rollback(); raise
    finally: session.close()


def escolher_planilha():
    root=Tk(); root.withdraw(); root.attributes('-topmost',True)
    caminho=filedialog.askopenfilename(title='Selecione a planilha histórica',filetypes=[('Planilhas Excel','*.xlsx'),('Todos os arquivos','*.*')]); root.destroy()
    return Path(caminho) if caminho else None


def main():
    try: garantir_estrutura_autenticacao(); garantir_tabela_importacao()
    except Exception as exc:
        root=Tk(); root.withdraw(); messagebox.showerror('Importação histórica','Não foi possível preparar o banco.\n\n'+str(exc)); root.destroy(); return
    usuario=abrir_login()
    if not usuario: return
    if usuario.get('nivel_acesso')!='Administrador':
        root=Tk(); root.withdraw(); messagebox.showerror('Permissão','A importação histórica exige usuário Administrador.'); root.destroy(); return
    caminho=escolher_planilha()
    if not caminho: return
    try:
        movimentos,ignorados,erros=preflight(caminho)
    except Exception as exc:
        root=Tk(); root.withdraw(); messagebox.showerror('Planilha inválida',str(exc)); root.destroy(); return
    resumo=resumo_previa(movimentos,ignorados,erros)
    if erros:
        detalhe='\n\n'.join(erros[:20]); detalhe += f"\n\n... e mais {len(erros)-20} erro(s)." if len(erros)>20 else ''
        root=Tk(); root.withdraw(); messagebox.showerror('Importação bloqueada',resumo+'\n\n'+detalhe); root.destroy(); return
    root=Tk(); root.withdraw()
    ok=messagebox.askyesno('Prévia da importação',f'Arquivo: {caminho.name}\n\n{resumo}\n\nNenhum dado foi gravado ainda.\nSomente REGISTRO DE ENTRADA e REGISTRO DE SAIDA serão processados. STATUS ESTOQUE será usado apenas como referência e não será importado como estoque. As demais abas serão ignoradas.\n\nDeseja IMPORTAR agora?')
    root.destroy()
    if not ok: return
    try: resultado=importar(caminho,movimentos,usuario)
    except Exception as exc:
        root=Tk(); root.withdraw(); messagebox.showerror('Importação cancelada','Nenhum registro desta execução foi confirmado no banco.\n\n'+str(exc)); root.destroy(); return
    criados='\n'.join(f'- {k}: {v}' for k,v in resultado['criados'].items() if v) or 'Nenhum cadastro novo.'
    root=Tk(); root.withdraw(); messagebox.showinfo('Importação concluída',f"Movimentos importados: {resultado['importados']}\nDuplicados ignorados: {resultado['duplicados']}\n\nCadastros criados:\n{criados}"); root.destroy()

if __name__=='__main__': main()
