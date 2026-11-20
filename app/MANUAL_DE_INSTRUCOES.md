# Manual de Instruções — Epi Control

## 1. Entrar no sistema
1. Abra `EpiControl.exe`.
2. No primeiro início, crie o administrador informando nome, login, senha e confirmação. Use ao menos 8 caracteres com letras e números; não há credenciais padrão.
3. Nos próximos acessos, informe seu login e senha.
4. O acesso e as abas disponíveis dependem das permissões atribuídas pelo administrador.

## 2. Cadastro e Configuração
- **Categorias:** cadastre grupos como Fardamento, Calçados e EPI. Para exigir CA, o nome da categoria deve conter “EPI”.
- **Fornecedores:** cadastre nome e contato.
- **Tamanhos:** cadastre os tamanhos usados nos itens.
- **Funcionários:** cadastre os colaboradores que receberão materiais.
- **Setores/Lojas:** cadastre os locais de armazenamento/entrega.
- **Produtos:** informe nome, categoria, CA quando for EPI, setor padrão, descrição e estoque mínimo. O campo “Cadastrado por” é preenchido pelo usuário conectado.
- **Usuários:** somente o perfil Administrador gerencia usuários. Ao cadastrar um Operador, as permissões usuais já vêm selecionadas e o administrador pode acrescentar outras. Administradores podem alterar nome, login e senha dos usuários.
- **Configurações do Sistema:** personalize o texto e a logo do Termo de Responsabilidade, faça backup do banco e importe cadastros de planilha.

## 3. Pedido de Compra
Cadastre os pedidos de compra com produto, quantidade, fornecedor e demais informações solicitadas. Acompanhe os pedidos na própria aba.

## 4. Entrada de estoque
Registre o recebimento dos itens e associe ao pedido de compra quando aplicável. Confira produto, tamanho, quantidade, fornecedor e data antes de salvar. O usuário da operação deve ser o usuário conectado.

## 5. Saída de estoque
Selecione o funcionário, setor e itens a entregar. Confira quantidades e saldo disponível antes de gravar. Os pedidos salvos devem ser conferidos antes da emissão do termo.

## 6. Ajuste de estoque
Use esta função para alinhar o saldo do sistema à contagem física. Informe produto, tamanho, quantidade física e motivo. Ajustes ficam registrados no histórico.

## 7. Termo de Responsabilidade
Selecione o pedido de saída e a data do documento, escolha onde salvar o PDF. O CA de EPI aparece na tabela. Para personalizar, abra **Cadastro e Configuração → Configurações do Sistema**, altere nome/textos/cláusulas e importe a logo da empresa, então salve. A personalização vale para os próximos termos.

## 8. Relatórios e auditoria
Consulte relatórios de estoque e o histórico de operações. O histórico ajuda a verificar usuário, data, operação e registro.

## 9. Banco local e backup
O banco SQLite local fica em `%LOCALAPPDATA%\EPIControl\data\epicontrol.db`. As tabelas são criadas automaticamente no primeiro início.
1. Abra **Cadastro e Configuração → Configurações do Sistema**.
2. Clique **Fazer backup agora**.
3. Escolha uma pasta segura para salvar a cópia SQLite.
4. Aguarde a confirmação.
5. Guarde outra cópia em local seguro. Não use bancos de outras instalações.

## 10. Importar cadastros por planilha
1. Prepare um arquivo Excel (.xlsx) ou CSV com cabeçalhos na primeira linha.
2. A coluna `nome` é obrigatória. Para fornecedores, inclua também `contato` (pode ficar vazio).
3. Abra **Cadastro e Configuração → Configurações do Sistema → Importar planilha**.
4. Escolha o arquivo e o tipo de cadastro solicitado.
5. O sistema adiciona novos registros e ignora nomes já existentes; não apaga registros.

Faça um backup antes de importar. A importação atual é destinada a categorias, funcionários e fornecedores; não importe planilhas históricas de movimentação por esta função.

## 11. Boas práticas
- Faça backup antes de alterações em lote ou atualizações do sistema.
- Não compartilhe sua senha.
- O aplicativo usa SQLite local e não precisa de `.env`, certificados ou serviço externo de banco.
- Ao atualizar, preserve o banco local do usuário e valide a nova versão antes de substituir o executável em uso.
- Se uma operação falhar, anote a mensagem de erro e não repita várias vezes sem conferir se foi gravada.
