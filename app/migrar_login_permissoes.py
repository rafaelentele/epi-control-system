"""Prepara a estrutura de login e permissões.

Pode ser executado manualmente, mas o próprio app_gui.py também garante
a estrutura automaticamente na inicialização.
"""
from app.auth import garantir_estrutura_autenticacao

garantir_estrutura_autenticacao()
print("Migração de login e permissões concluída com sucesso.")
print("Senha inicial dos usuários antigos: 123456")
