# ClauDinhos Chat

## Visao Geral

Sistema web de chatbot desenvolvido em Python 3.13.9 com Django, integrando um modelo local executado via Ollama e utilizando PostgreSQL 17 como banco de dados principal.

O sistema tera uma interface web simples para conversas com IA, sem autenticacao de usuarios, com armazenamento persistente das conversas e mensagens. Cada conversa mantera um contexto ativo limitado, para evitar excesso de tokens e degradacao de desempenho durante as chamadas ao modelo. O sistema tambem devera suportar multiplos modelos configurados no Ollama, permitindo que o usuario escolha qual modelo deseja usar em cada conversa.

## Objetivos

- Disponibilizar uma interface web de chat responsiva e simples.
- Persistir conversas e mensagens no banco de dados.
- Integrar com Ollama local para execucao de modelos como Gemma 3, Gemma 4, Qwen 3.5 ou outros modelos compativeis.
- Limitar o contexto enviado ao modelo por conversa.
- Permitir ao usuario escolher o modelo da conversa entre os modelos habilitados.
- Seguir boas praticas de programacao, separacao de responsabilidades e organizacao em padrao MVC.
- Nao possuir tela de login, cadastro ou qualquer mecanismo de autenticacao.

## Stack Tecnologica

- Python 3.13.9
- Django 5.x compativel com Python 3.13
- PostgreSQL 17
- Ollama rodando localmente
- HTML, CSS e JavaScript para a interface web
- Docker opcional para padronizacao do ambiente local e de deploy

## Modelos de IA

O sistema deve permitir a configuracao dos modelos disponiveis via variavel de ambiente ou configuracao administrativa interna, mantendo um modelo padrao como fallback.

Modelos inicialmente previstos:

- Gemma 3
- Gemma 4
- Qwen 3.5
- Outros modelos suportados pelo Ollama

Recomendacao tecnica:

- Abstrair o provedor de inferencia em uma camada de servico, para que a troca de modelo ou ajuste de parametros nao impacte a camada web.
- Centralizar configuracoes como lista de modelos habilitados, modelo padrao, temperatura, limite de contexto e timeout em arquivo de configuracao do projeto.
- Validar se o modelo escolhido pelo usuario pertence a lista de modelos permitidos antes de iniciar ou atualizar uma conversa.

## Arquitetura

Embora o Django use naturalmente o padrao MVT, este projeto sera organizado com leitura arquitetural em MVC:

- Model: models do Django e regras de persistencia.
- View: templates HTML, componentes visuais e respostas JSON.
- Controller: views do Django, services e orquestracao dos fluxos.

Para manter o codigo limpo, a regra de negocio nao deve ficar concentrada apenas nas views. A recomendacao e usar uma camada de services para integracao com Ollama, montagem de contexto e controle transacional.

## Modulos Principais

### 1. Modulo de Chat

Responsabilidades:

- Criar conversas.
- Listar conversas.
- Exibir historico de mensagens.
- Permitir selecionar o modelo ao criar a conversa e, se desejado pela regra de negocio, alterar o modelo para mensagens futuras.
- Receber mensagens do usuario.
- Acionar o modelo local.
- Persistir respostas do assistente.

### 2. Modulo de Contexto

Responsabilidades:

- Definir o limite de contexto por conversa.
- Selecionar quais mensagens entram na janela ativa.
- Descartar ou resumir mensagens antigas quando necessario.
- Garantir que o prompt enviado ao modelo nao ultrapasse o limite configurado.

### 3. Modulo de Integracao com LLM

Responsabilidades:

- Comunicar com o Ollama local.
- Expor a lista de modelos disponiveis para a camada de aplicacao.
- Padronizar payloads de requisicao e resposta.
- Tratar timeout, indisponibilidade e erros do modelo.
- Permitir troca de modelo sem alterar o fluxo do chat.

### 4. Modulo Web

Responsabilidades:

- Renderizar a interface do chatbot.
- Exibir seletor de modelo na criacao da conversa e no cabecalho da conversa, conforme a experiencia definida.
- Atualizar a conversa em tempo quase real via requisicoes HTTP assicronas.
- Exibir estados de carregamento, erro e sucesso.

## Estrutura Inicial Sugerida

```text
src/
	config/
		settings/
		urls.py
		wsgi.py
		asgi.py
	apps/
		core/
		chat/
			models.py
			views.py
			urls.py
			forms.py
			services/
				conversation_service.py
				context_service.py
				ollama_service.py
			templates/chat/
			tests/
		common/
	static/
	templates/
```

## Requisitos Funcionais

- O usuario deve conseguir iniciar uma nova conversa.
- O usuario deve conseguir visualizar a lista de conversas existentes.
- O usuario deve conseguir abrir uma conversa e visualizar todo o historico persistido.
- O usuario deve conseguir escolher, entre os modelos habilitados, qual modelo sera usado em cada conversa.
- O usuario deve conseguir enviar uma mensagem para o assistente.
- O sistema deve enviar ao modelo apenas o contexto ativo dentro do limite configurado.
- O sistema deve armazenar a resposta gerada pelo modelo.
- O sistema deve persistir em cada conversa qual modelo foi escolhido pelo usuario.
- O sistema deve tratar falhas do modelo e informar erro amigavel na interface.

## Requisitos Nao Funcionais

- O sistema deve ser organizado de forma modular e testavel.
- O codigo deve seguir boas praticas do ecossistema Django.
- O banco deve garantir integridade referencial entre conversas e mensagens.
- O tempo de resposta deve ser aceitavel para uso local.
- O sistema deve permitir futura expansao para streaming de resposta.
- Configuracoes sensiveis devem ficar em variaveis de ambiente.

## Modelo de Dados

### Entidade Conversation

Campos sugeridos:

- id: UUID
- title: titulo resumido da conversa
- model_name: nome do modelo escolhido pelo usuario para a conversa
- system_prompt: instrucao base da conversa
- context_limit_tokens: limite de tokens do contexto ativo
- available_models_snapshot: lista opcional dos modelos apresentados ao usuario no momento da criacao
- created_at
- updated_at
- is_archived

### Entidade Message

Campos sugeridos:

- id: UUID
- conversation: chave estrangeira para Conversation
- role: user, assistant ou system
- content: texto da mensagem
- sequence_number: ordem da mensagem na conversa
- input_tokens_estimated
- output_tokens_estimated
- created_at
- metadata_json: dados auxiliares opcionais

## Regra de Contexto

O sistema deve diferenciar historico persistido de contexto ativo.

- O historico persistido pode armazenar todas as mensagens da conversa.
- O contexto ativo enviado ao modelo deve considerar apenas as mensagens mais relevantes dentro de um limite configurado, sempre respeitando o modelo selecionado para a conversa.
- O limite deve ser controlado preferencialmente por estimativa de tokens e, de forma secundaria, por quantidade maxima de mensagens.
- Mensagens antigas podem ser resumidas no futuro, mas a primeira versao pode apenas recortar a janela de contexto.

Fluxo sugerido:

1. Recuperar a conversa, o modelo selecionado e o historico ordenado.
2. Adicionar o system prompt, quando houver.
3. Incluir as mensagens mais recentes ate atingir o limite de contexto.
4. Enviar esse conjunto ao Ollama usando o modelo escolhido para a conversa.
5. Persistir a resposta do assistente.

## Fluxo Principal da Aplicacao

1. O usuario acessa a tela inicial do chat.
2. O usuario cria uma nova conversa escolhendo um modelo ou abre uma conversa existente.
3. O usuario envia uma mensagem.
4. O controller delega a montagem do contexto para a camada de servico.
5. O servico de integracao chama o Ollama local com o modelo selecionado para a conversa.
6. A resposta do modelo e persistida no PostgreSQL.
7. A interface atualiza o historico da conversa.

## Integracao com Ollama

Configuracoes minimas esperadas:

- OLLAMA_BASE_URL
- OLLAMA_AVAILABLE_MODELS
- OLLAMA_DEFAULT_MODEL
- OLLAMA_TIMEOUT
- CHAT_CONTEXT_LIMIT_TOKENS

Boas praticas de integracao:

- Isolar chamadas HTTP ao Ollama em um servico dedicado.
- Definir timeout configuravel.
- Disponibilizar a lista de modelos permitidos ao frontend ou ao controller de criacao de conversa.
- Validar indisponibilidade do servidor Ollama antes de enviar requisicoes.
- Validar se o modelo informado pelo usuario esta habilitado antes de efetuar a chamada.
- Registrar logs tecnicos sem expor stack trace bruto na interface.
- Preparar a integracao para suportar respostas completas e streaming futuramente.

## Banco de Dados

O PostgreSQL 17 sera o banco oficial do projeto.

Diretrizes:

- Usar migrations do Django para versionamento do schema.
- Indexar campos usados em ordenacao e filtros frequentes, como created_at e conversation_id.
- Garantir cascade delete apenas quando fizer sentido para manter consistencia entre conversa e mensagens.
- Usar UUID como chave primaria para reduzir exposicao de sequencias previsiveis.

## Interface Web

Escopo inicial da interface:

- Pagina principal com lista de conversas na lateral.
- Area central com historico da conversa.
- Seletor de modelo ao iniciar uma nova conversa.
- Exibicao visivel do modelo atualmente em uso na conversa aberta.
- Campo de entrada para nova mensagem.
- Indicador visual de carregamento enquanto a IA responde.
- Exibicao clara de erros de comunicacao com o modelo.

Como nao havera autenticacao, a interface deve ser simples e direta, com foco na experiencia local de uso.

## Rotas Sugeridas

- GET / : tela principal do chat
- GET /conversations/ : lista de conversas
- POST /conversations/ : cria uma nova conversa com o modelo escolhido
- GET /conversations/<uuid>/ : detalha uma conversa
- POST /conversations/<uuid>/messages/ : envia uma nova mensagem
- GET /models/ : lista os modelos habilitados para selecao
- GET /health/ : verifica saude da aplicacao e da integracao com Ollama

## Padroes e Boas Praticas

- Separar regra de negocio, persistencia e camada de apresentacao.
- Evitar logica complexa diretamente em views ou templates.
- Concentrar a validacao de modelos permitidos na camada de servico ou configuracao, evitando duplicacao de regra.
- Escrever testes unitarios para services e testes de integracao para fluxos do chat.
- Utilizar classes, funcoes e nomes de arquivo claros e consistentes.
- Configurar ambientes por variaveis de ambiente.
- Padronizar formatacao, lint e validacoes automaticas.

## Seguranca e Escopo

- O sistema nao tera login nem autenticacao.
- O sistema sera pensado para uso controlado, local ou interno.
- Mesmo sem autenticacao, deve haver validacao de entrada, tratamento de erros e protecao contra falhas comuns.
- A aplicacao nao deve confiar cegamente no retorno do modelo.

## Possiveis Evolucoes Futuras

- Streaming de resposta do modelo.
- Resumo automatico de contexto antigo.
- Parametros ajustaveis por conversa, como temperatura.
- Exportacao de conversas.
- Interface com markdown renderizado nas respostas.

## Criterios de Aceite da Primeira Versao

- Criar e listar conversas.
- Permitir que o usuario escolha entre multiplos modelos habilitados.
- Persistir mensagens de usuario e assistente.
- Integrar com um modelo local via Ollama.
- Limitar o contexto enviado ao modelo.
- Usar PostgreSQL 17 como banco.
- Manter o projeto organizado em estrutura aderente ao MVC dentro do ecossistema Django.
- Operar sem autenticacao.
