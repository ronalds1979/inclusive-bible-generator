# inclusive-bible-generator

Um aplicativo desktop para Windows que gera imagens acessíveis de versículos bíblicos para redes sociais, com suporte a múltiplos idiomas (Português, Inglês e Espanhol).

## Requisitos
- Python 3.10 ou superior
- Pip (gerenciador de pacotes do Python)

## Instalação

1. Clone o repositório ou baixe os arquivos.
2. Abra o terminal na pasta do projeto e instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```

## Como usar

1. Execute o arquivo `main.py`:
   ```bash
   python main.py
   ```
2. Na interface gráfica, selecione o idioma desejado (Português, English ou Español).
3. Selecione a versão da Bíblia, insira a referência (ex: Salmos 119:105) e busque o versículo.
4. Você pode personalizar a imagem utilizando as seguintes opções:
   - **Imagem de Fundo:** Selecione uma imagem padrão ou carregue uma imagem personalizada.
   - **Fonte:** Escolha o tipo de fonte, tamanho e cor (incluindo cores personalizadas com código Hex).
   - **Formato:** Altere a proporção da imagem (1:1, 3:4, 4:3) e ajuste a posição vertical do texto.
   - **Áudio (TTS):** Marque a opção para gerar um arquivo de áudio narrando o versículo e selecione a voz (Feminina ou Masculina).
5. Clique no botão "Gerar Conteúdo" (ou equivalente no idioma escolhido).
6. Você será solicitado a escolher o local no seu computador para salvar:
   - A imagem gerada.
   - O arquivo de áudio (se a opção foi selecionada).
7. O aplicativo também gerará:
   - O Texto Alternativo (Alt-Text) pronto para ser copiado.
   - A Legenda para redes sociais, com dicas de acessibilidade em vídeo.
8. Você pode copiar o Alt-Text ou a Legenda clicando nos respectivos botões.

## Estrutura do Projeto

- `main.py`: A interface gráfica do aplicativo.
- `generator.py`: Módulo responsável pela geração da imagem e textos localizados.
- `getbible_api.py`: Integração com a API getbible.net para buscar versículos bíblicos.
- `locales/`: Contém os arquivos JSON com os textos para cada idioma.
- `assets/`: Contém fontes e imagens de fundo.
- `output/`: Pasta onde imagens geradas eram salvas anteriormente por padrão.
