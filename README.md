# 🎬 Insta to Text - Transcritor de Vídeos do Instagram

Aplicação web interativa desenvolvida com Streamlit para baixar vídeos do Instagram e transcrever o conteúdo de áudio para texto.

## ✨ Funcionalidades

- 📥 Download automático de vídeos do Instagram (reels, posts, vídeos)
- 🎵 Extração de áudio dos vídeos
- 🎤 Transcrição de áudio para texto usando Google Speech Recognition API
- 🌐 Suporte para múltiplos idiomas
- 📊 Estatísticas da transcrição (palavras, caracteres)
- 💾 Download da transcrição em formato .txt
- 🗑️ Limpeza automática de arquivos temporários
- 📈 Barra de progresso e feedback visual em tempo real

## 🚀 Como Usar

### Pré-requisitos

1. **Python 3.7+** instalado
2. **Nenhuma instalação externa necessária!** 
   - Todas as dependências são instaladas via pip
   - O ffmpeg está incluído automaticamente via `imageio-ffmpeg`

### Instalação

1. Clone ou baixe este repositório
2. Instale as dependências:

```bash
pip install -r requirements.txt
```

### Executar a Aplicação

```bash
streamlit run app.py
```

A aplicação abrirá automaticamente no navegador em `http://localhost:8501`

## 📋 Como Usar a Interface

1. **Cole a URL do vídeo**: Cole a URL de um reel, post ou vídeo do Instagram
2. **Selecione o idioma**: Escolha o idioma do áudio na barra lateral
3. **Clique em "Transcrever"**: Aguarde o processamento
4. **Visualize e baixe**: Veja a transcrição e baixe em formato .txt

## 🌐 Idiomas Suportados

- Português (Brasil)
- Português (Portugal)
- Inglês (EUA)
- Inglês (Reino Unido)
- Espanhol
- Espanhol (México)
- Francês
- Italiano
- Alemão

## 🛠️ Tecnologias Utilizadas

- **Streamlit**: Interface web interativa
- **yt-dlp**: Download de vídeos do Instagram
- **MoviePy**: Extração de áudio dos vídeos (usa ffmpeg embutido via imageio-ffmpeg)
- **imageio-ffmpeg**: Binário do ffmpeg incluído (não requer instalação separada)
- **SpeechRecognition**: Reconhecimento de fala
- **pydub**: Processamento de áudio
- **Google Speech Recognition API**: Transcrição de áudio

## 📝 Requisitos do Sistema

- Conexão com internet (necessária para download e transcrição)
- Python 3.7 ou superior
- Todas as dependências são instaladas automaticamente via pip

## ⚙️ Melhorias Implementadas

### Código Original vs. Versão Melhorada

**Melhorias de Código:**
- ✅ Interface gráfica intuitiva com Streamlit
- ✅ Validação de URLs do Instagram
- ✅ Tratamento robusto de erros
- ✅ Indicadores de progresso em tempo real
- ✅ Limpeza automática de arquivos temporários
- ✅ Suporte a múltiplos idiomas
- ✅ Estatísticas da transcrição
- ✅ Feedback visual para o usuário
- ✅ Uso de diretórios temporários seguros
- ✅ Timeouts para operações longas
- ✅ Verificação prévia de dependências

**Análise do Código:**
- Código modularizado com funções bem definidas
- Tratamento de exceções abrangente
- Mensagens de erro claras e informativas
- Documentação inline com docstrings
- Separação de responsabilidades
- Uso eficiente de recursos (limpeza automática)

## 🐛 Solução de Problemas

### Erro: "yt-dlp não encontrado"
```bash
pip install yt-dlp
```

### Erro ao extrair áudio
- Certifique-se de que todas as dependências estão instaladas: `pip install -r requirements.txt`
- Verifique se o vídeo possui faixa de áudio

### Transcrição vazia
- Verifique se o vídeo tem áudio
- Tente selecionar outro idioma
- Verifique sua conexão com a internet
- Alguns vídeos podem ter áudio muito baixo

### Timeout ao baixar vídeo
- Verifique sua conexão com a internet
- O vídeo pode ser muito grande ou estar indisponível
- Tente novamente após alguns segundos

## 📄 Licença

Este projeto é livre para uso pessoal e educacional.

## 🤝 Contribuições

Contribuições são bem-vindas! Sinta-se à vontade para abrir issues ou pull requests.

