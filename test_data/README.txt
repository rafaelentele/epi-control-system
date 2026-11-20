BANCO FICTICIO DE TESTE — EPI CONTROL

Conteúdo: 3 empresas de teste, 15 funcionários fictícios (5 por empresa),
5 fornecedores, 5 produtos, 5 pedidos de compra, 18 entradas distribuídas
por tamanho e 1 pedido de saída fictício com 1 bota (36) e 1 capacete (M).
Os CPFs são sintéticos e os CAs começam com CA-TESTE; não são identificadores
ou certificados oficiais.

Pedidos e distribuição de tamanhos:
  1. Bota de Segurança Teste — 30: 36 (3), 37 (5), 38 (7), 39 (6), 40 (5), 41 (4).
  2. Camisa UV Teste — 20: P (2), M (4), G (7), GG (5), XG (2).
  3. Capacete de Segurança Teste — 10: M (4), G (6), CA-TESTE-001.
  4. Luva de Proteção Teste — 16: 7 (3), 8 (5), 9 (5), 10 (3), CA-TESTE-002.
  5. Óculos de Proteção Teste — 12: UNICO (12), CA-TESTE-003.

A bota também recebe CA-TESTE-BOTAS para validar campos de EPI.

O banco está em epicontrol_teste.db e é independente do banco local do usuário.
O PDF termo_teste_ficticio_pedido_1.pdf foi gerado para validar o conteúdo e a
formatação do termo com os dois itens acima. Ele também valida a exibição da
empresa vinculada ao funcionário mesmo quando o modelo não usa {empresa}. O
script recria o pedido de saída no banco, mas não gera o PDF automaticamente.
O script seed_fake_data.py cria o banco uma vez e recusa substituir um arquivo
que já exista.

Para abrir o aplicativo pelo código-fonte usando esse banco, no PowerShell na
raiz do projeto:

  $env:EPICONTROL_TEST_DB_PATH = (Resolve-Path .\test_data\epicontrol_teste.db).Path
  python .\app\app_gui.py

O executável empacotado ignora esse override de teste e continua usando o banco
normal em %LOCALAPPDATA%\EPIControl\data\epicontrol.db.

Credenciais de teste: login admin_teste / senha Teste123.
Essas credenciais existem somente neste banco fictício.
