"""Valida que a compilação independente não precisa de banco incluído.

O aplicativo cria o SQLite vazio no diretório de dados local do usuário no
primeiro início. Este script existe para compatibilidade com o fluxo de build;
intencionalmente não abre, copia, migra ou empacota qualquer banco existente.
"""

print("Build independente do Epi Control: nenhum banco SQLite será copiado ou incluído.")
print("O Epi Control criará %LOCALAPPDATA%\\EPIControl\\data\\epicontrol.db no primeiro início.")
