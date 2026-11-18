# epi-control-system
# 🛡️ EpiControl - Sistema de Controle de Fardamentos e EPIs

> Sistema desenvolvido para otimizar o controle de estoque, compras, movimentações e conformidade de Equipamentos de Proteção Individual (EPIs) e fardamentos, garantindo rastreabilidade e segurança operacional.

---

## 💡 Sobre o Projeto
Este projeto nasceu da união entre a **experiência prática em Recursos Humanos (RH)** e o desenvolvimento de software. Na rotina corporativa, o controle manual de EPIs e fardamentos gera riscos trabalhistas, perda de prazos de Certificado de Aprovação (CA) e falhas de estoque. 

O **EpiControl** resolve essa dor real de negócio automatizando o fluxo completo: desde o pedido de compra e entrada de produtos por tamanho/setor até o ajuste de estoque e a auditoria de ações por usuário.

## 🚀 Tecnologias Utilizadas
* **Linguagem:** Python 3.x
* **Banco de Dados:** SQLite
* **Modelagem de Dados:** DBeaver (DER)
* **Controle de Versão:** Git & GitHub

## ⚙️ Funcionalidades Principais
- **Gestão de Produtos, Categorias e Setores:** Cadastro completo de fardamentos e EPIs com controle de estoque mínimo e Certificado de Aprovação (`CA`).
- **Controle de Compras e Entradas:** Registro de fornecedores, pedidos de compra e entrada de itens detalhados por tamanho.
- **Ajuste e Rastreabilidade de Estoque:** Controle de saldo anterior/posterior com registro de motivo para cada movimentação.
- **Segurança e Auditoria:** Controle de acesso por nível de usuário (`usuario_permissao`) e log completo de operações (`auditoria`) para rastrear quem realizou cada ação e quando.

## 🗄️ Modelagem do Banco de Dados (DER)
O sistema utiliza um banco de dados relacional **SQLite** estruturado com chaves estrangeiras para garantir a integridade referencial entre usuários, fornecedores, produtos e movimentações:

![Diagrama Entidade Relacionamento](./assets/der-fardamento.png)

