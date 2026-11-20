# Manual de Instruções — Epi Control

## 1. Entrar no sistema
1. Abra `EpiControl.exe`.
2. No primeiro início, crie o administrador informando nome, login, senha e confirmação. Use ao menos 8 caracteres com letras e números; não há credenciais padrão.
3. Nos próximos acessos, informe seu login e senha.
4. O acesso e os menus disponíveis dependem das permissões atribuídas pelo administrador.
5. Para rever este manual, clique em **Ajuda / Manual**, na barra inferior, ao lado de **Sair**.

## Como navegar
A barra de menus no topo agrupa as telas pelo fluxo de trabalho. O menu da tela em uso fica em **negrito** e o caminho atual aparece logo abaixo da barra (ex.: *Saídas › Pedido de Saída*).

| Menu | Telas |
|---|---|
| **Início** | Tela inicial, com atalhos para as tarefas mais usadas |
| **Estoque** | Status do Estoque, Ajuste de Estoque |
| **Compras** | Pedidos de Compra, Entrada de Estoque |
| **Saídas** | Pedido de Saída, Termo de Responsabilidade |
| **Cadastros** | Produtos, Categorias, Fornecedores, Tamanhos, Funcionários, Setores/Lojas |
| **Relatórios** | Status do Estoque, Entradas por Tamanho, Histórico por Funcionário, Histórico por Produto, Pesquisa de Registro de Compra, Listagem Geral, Histórico de Operações |
| **Configuração** | Usuários e Permissões, Termo/Backup/Importação |

- Itens em cinza são telas que o seu usuário não tem permissão para abrir. Menus sem nenhuma tela liberada não aparecem.
- **Teclas de atalho:** F2 Status do Estoque · F3 Pedidos de Compra · F4 Entrada de Estoque · F6 Pedido de Saída · F7 Termo de Responsabilidade · **F5** atualiza os dados da tela atual.
- Ao abrir uma tela pelo menu, os dados dela são recarregados do banco (por exemplo, um produto recém-cadastrado já aparece na Entrada).

## 2. Cadastros (menu Cadastros)
- **Categorias:** cadastre grupos como Fardamento, Calçados e EPI. Para exigir CA, o nome da categoria deve conter “EPI”.
- **Fornecedores:** cadastre nome e contato.
- **Tamanhos:** cadastre os tamanhos usados nos itens.
- **Funcionários:** cadastre os colaboradores que receberão materiais.
- **Setores/Lojas:** cadastre os locais de armazenamento/entrega.
- **Produtos:** informe nome, categoria, CA quando for EPI, setor padrão, descrição e estoque mínimo. O campo “Cadastrado por” é preenchido pelo usuário conectado.
- **Usuários:** somente o perfil Administrador abre **Configuração → Usuários e Permissões**. Novos Operadores recebem permissões usuais pré-selecionadas, que podem ser ampliadas no cadastro. O Administrador pode alterar nome, login e senha.
- **Termo, Backup e Importação** (menu Configuração): personalize o texto e a logo do Termo de Responsabilidade, faça backup do banco e importe cadastros de planilha.

## 3. Pedido de Compra
Cadastre os pedidos de compra com produto, quantidade, fornecedor e demais informações solicitadas. Acompanhe os pedidos na própria tela (menu **Compras → Pedidos de Compra**).

## 4. Entrada de estoque
Registre o recebimento dos itens e associe ao pedido de compra quando aplicável. Confira produto, tamanho, quantidade, fornecedor e data antes de salvar. O usuário da operação deve ser o usuário conectado.

## 5. Saída de estoque
Selecione o funcionário, setor e itens a entregar. Confira quantidades e saldo disponível antes de gravar. Os pedidos salvos devem ser conferidos antes da emissão do termo.

## 6. Ajuste de estoque
Use esta função para alinhar o saldo do sistema à contagem física. Informe produto, tamanho, quantidade física e motivo. Ajustes ficam registrados no histórico.

## 7. Termo de Responsabilidade
Selecione o pedido de saída e a data do documento, escolha onde salvar o PDF. O CA de EPI aparece na tabela. Para personalizar, abra **Configuração → Termo, Backup e Importação**, altere nome/textos/cláusulas e importe a logo da empresa, então salve. A personalização vale para os próximos termos.

## 8. Relatórios e auditoria
Consulte relatórios de estoque e o histórico de operações. O histórico ajuda a verificar usuário, data, operação e registro.

## 9. Banco local e backup
O banco SQLite local fica em `%LOCALAPPDATA%\EPIControl\data\epicontrol.db`. As tabelas são criadas automaticamente no primeiro início.
1. Abra **Configuração → Termo, Backup e Importação**.
2. Clique **Fazer backup agora**.
3. Escolha uma pasta segura para salvar a cópia SQLite.
4. Aguarde a confirmação.
5. Guarde outra cópia em local seguro. Não use bancos de outras instalações.

## 10. Importar cadastros por planilha
1. Abra **Configuração → Termo, Backup e Importação**.
2. Clique em **Baixar modelo de planilha**, escolha Categorias, Funcionários ou Fornecedores e salve o arquivo.
3. Preencha a aba **Dados** a partir da linha 2, sem alterar os cabeçalhos. A aba **Instruções** é ignorada.
4. Clique em **Importar planilha...**, escolha o tipo de cadastro e o arquivo (.xlsx ou .csv).
5. O sistema mostra uma prévia: registros novos, duplicados e rejeitados (com o número da linha). Confirme para importar.

Cada campo aceita no máximo 45 caracteres. Nomes que já existem, ou repetidos na planilha, são ignorados. Nada é apagado nem alterado, e a importação fica registrada no histórico de operações.

Faça um backup antes de importar. A importação serve para categorias, funcionários e fornecedores; não importe planilhas históricas de movimentação por esta função.

## 11. Boas práticas
- Faça backup antes de alterações em lote ou atualizações do sistema.
- Não compartilhe sua senha.
- O aplicativo usa SQLite local e não precisa de `.env`, certificados ou serviço externo de banco.
- Ao atualizar, preserve o banco local do usuário e valide a nova versão antes de substituir o executável em uso.
- Se uma operação falhar, anote a mensagem de erro e não repita várias vezes sem conferir se foi gravada.
