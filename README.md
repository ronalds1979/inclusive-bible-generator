# Luz Inclusiva (Inclusive Light)

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
3. Insira o versículo bíblico e a sua referência.
4. Clique no botão "Gerar Conteúdo" (ou equivalente no idioma escolhido).
5. O aplicativo gerará:
   - Uma imagem com o texto formatado na pasta `output/`.
   - O Texto Alternativo (Alt-Text) pronto para ser copiado.
   - A Legenda para redes sociais, com dicas de acessibilidade em vídeo.
6. Você pode copiar o Alt-Text ou a Legenda clicando nos respectivos botões.

## Estrutura do Projeto

- `main.py`: A interface gráfica do aplicativo.
- `generator.py`: Módulo responsável pela geração da imagem e textos localizados.
- `locales/`: Contém os arquivos JSON com os textos para cada idioma.
- `assets/`: Contém fontes e imagens de fundo.
- `output/`: Pasta onde as imagens geradas são salvas.
