"""Corrige o horário dos registros ANTIGOS da tabela auditoria (UTC -> Salvador, UTC-3).

Segurança:
- Só altera registros com data_hora ANTERIOR à data/hora de corte que você informar
  (o momento em que o código novo, que já grava em horário local, entrou em uso).
- Cria antes uma cópia de segurança (auditoria_bkp_utc).
- Se a cópia já existir, o script se recusa a rodar (evita descontar 3h duas vezes).
- Faz tudo numa única transação.

Para desfazer: veja o final deste arquivo.
"""
from datetime import datetime
from sqlalchemy import text
from app.config.database import engine

BKP = "auditoria_bkp_utc"

print("Este script converte registros antigos da auditoria de UTC para UTC-3 (Salvador).")
with engine.connect() as conn:
    existe = conn.execute(text("SHOW TABLES LIKE :t"), {"t": BKP}).first()
if existe:
    print(f"A tabela {BKP} já existe: a correção parece já ter sido feita. Nada foi alterado.")
    raise SystemExit

txt = input("Data/hora em que o código novo passou a gravar horário local (dd/mm/aaaa hh:mm): ").strip()
try:
    corte = datetime.strptime(txt, "%d/%m/%Y %H:%M")
except ValueError:
    print("Formato inválido. Operação cancelada.")
    raise SystemExit

with engine.connect() as conn:
    total = conn.execute(text("SELECT COUNT(*) FROM auditoria")).scalar()
    alvo = conn.execute(text("SELECT COUNT(*) FROM auditoria WHERE data_hora < :c"), {"c": corte}).scalar()
    amostra = conn.execute(text("SELECT id_auditoria, data_hora FROM auditoria WHERE data_hora < :c ORDER BY data_hora DESC LIMIT 3"), {"c": corte}).all()

print(f"\nTotal de registros: {total}. Serão alterados (anteriores a {corte:%d/%m/%Y %H:%M}): {alvo}.")
for r in amostra:
    print(f"  ex.: #{r[0]}  {r[1]}  ->  {r[1].replace(microsecond=0) - __import__('datetime').timedelta(hours=3)}")
if alvo == 0:
    print("Nada a alterar.")
    raise SystemExit

if input("Digite CONVERTER para continuar: ").strip().upper() != "CONVERTER":
    print("Operação cancelada.")
    raise SystemExit

with engine.begin() as conn:
    conn.execute(text(f"CREATE TABLE {BKP} AS SELECT * FROM auditoria"))
    conn.execute(text("UPDATE auditoria SET data_hora = DATE_SUB(data_hora, INTERVAL 3 HOUR) WHERE data_hora < :c"), {"c": corte})
print(f"Pronto. {alvo} registro(s) corrigido(s). Cópia original guardada em {BKP}.")

# Para DESFAZER (rode no MySQL):
#   UPDATE auditoria a JOIN auditoria_bkp_utc b USING (id_auditoria) SET a.data_hora = b.data_hora;
#   DROP TABLE auditoria_bkp_utc;
