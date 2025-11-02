# 🎬 Insta to Text - Transcritor de Vídeos do Instagram

Aplicação web interativa desenvolvida com Streamlit para baixar vídeos do Instagram e transcrever o conteúdo de áudio para texto usando **OpenAI Whisper AI**.

## ✨ Funcionalidades

- 📥 Download automático de vídeos do Instagram (reels, posts, vídeos)
- 🎵 Extração de áudio dos vídeos
- 🎯 **Whisper AI integrado** - Transcrição de alta precisão
- 🔊 **Normalização automática de áudio** - Melhora qualidade do som
- 🔇 **Redução de ruído automática** - Remove ruído de fundo
- 📝 **Pontuação automática opcional** - Formata o texto automaticamente
- 🌐 Suporte para múltiplos idiomas (14+ idiomas)
- 🎚️ **Múltiplos modelos Whisper** - Do mais rápido ao mais preciso
- 📊 Estatísticas da transcrição (palavras, caracteres)
- 💾 Download da transcrição em formato .txt
- 🗑️ Limpeza automática de arquivos temporários
- 📈 Barra de progresso e feedback visual em tempo real

## 🚀 Como Usar

### Pré-requisitos

1. **Python 3.8+** instalado
2. **Nenhuma instalação externa necessária!** 
   - Todas as dependências são instaladas via pip
   - O ffmpeg está incluído automaticamente via `imageio-ffmpeg`
   - Os modelos Whisper são baixados automaticamente na primeira execução

### Instalação

1. Clone ou baixe este repositório
2. Instale as dependências:

```bash
pip install -r requirements.txt
```

**Nota:** A primeira instalação pode demorar alguns minutos para baixar o PyTorch e outras dependências pesadas.

### Executar a Aplicação

```bash
streamlit run app.py
```

A aplicação abrirá automaticamente no navegador em `http://localhost:8501`

## 📋 Como Usar a Interface

1. **Cole a URL do vídeo**: Cole a URL de um reel, post ou vídeo do Instagram
2. **Configure as opções** na barra lateral:
   - Selecione o idioma do áudio
   - Escolha o modelo Whisper (base recomendado)
   - Configure processamento de áudio (normalização/redução de ruído)
   - Ative/desative pontuação automática
3. **Clique em "Transcrever"**: Aguarde o processamento
4. **Visualize e baixe**: Veja a transcrição e baixe em formato .txt

## 🌐 Idiomas Suportados

- Português (Brasil/Portugal)
- Inglês (EUA/Reino Unido)
- Espanhol (Espanha/México)
- Francês
- Italiano
- Alemão
- Japonês
- Chinês
- Russo
- Árabe
- Hindi
- E mais (Whisper suporta 99 idiomas)

## 🎚️ Modelos Whisper Disponíveis

- **tiny**: Mais rápido, menor precisão (~1GB RAM)
- **base**: Balanceado, boa qualidade (recomendado) (~1GB RAM)
- **small**: Boa precisão, um pouco mais lento (~2GB RAM)
- **medium**: Alta precisão, mais lento (~5GB RAM)
- **large-v3**: Máxima precisão, mais lento (~10GB RAM)

**Recomendação:** Use `base` para a maioria dos casos. Use `small` ou `medium` para maior precisão quando necessário.

## 🛠️ Tecnologias Utilizadas

- **Streamlit**: Interface web interativa
- **yt-dlp**: Download de vídeos do Instagram
- **OpenAI Whisper**: Transcrição de áudio de alta precisão
- **MoviePy**: Extração de áudio dos vídeos (usa ffmpeg embutido via imageio-ffmpeg)
- **imageio-ffmpeg**: Binário do ffmpeg incluído (não requer instalação separada)
- **pydub**: Processamento e normalização de áudio
- **noisereduce**: Redução automática de ruído
- **PyTorch**: Framework de deep learning (requerido pelo Whisper)

## 📝 Requisitos do Sistema

- Conexão com internet (necessária para download e primeira instalação dos modelos)
- Python 3.8 ou superior
- **RAM recomendada:**
  - Mínimo: 4GB (para modelos tiny/base)
  - Recomendado: 8GB+ (para modelos small/medium)
  - Ideal: 16GB+ (para modelo large)
- Espaço em disco: ~3-5GB (para modelos Whisper)

## ⚙️ Melhorias Implementadas

### Novas Funcionalidades:

✅ **Whisper AI como motor principal**
   - Substituiu Google Speech Recognition
   - Maior precisão e melhor suporte a múltiplos idiomas
   - Funciona offline após download do modelo

✅ **Processamento de áudio avançado**
   - Normalização automática de volume
   - Compressão dinâmica para melhor clareza
   - Redução automática de ruído de fundo

✅ **Pós-processamento inteligente**
   - Pontuação automática opcional
   - Formatação e correção básica de texto
   - Capitalização automática

✅ **Interface melhorada**
   - Controles granulares para cada funcionalidade
   - Seleção de modelo Whisper
   - Estatísticas detalhadas

### Melhorias de Código:

- Código modularizado com funções bem definidas
- Tratamento robusto de erros
- Mensagens de erro claras e informativas
- Documentação inline com docstrings
- Separação de responsabilidades
- Uso eficiente de recursos (limpeza automática)

## 🐛 Solução de Problemas

### Erro: "yt-dlp não encontrado"
```bash
pip install yt-dlp
```

### Erro ao instalar Whisper/PyTorch
- Certifique-se de ter Python 3.8+
- Se tiver problemas, instale PyTorch separadamente: `pip install torch torchvision torchaudio`

### Transcrição muito lenta
- Use um modelo menor (tiny ou base)
- Desative processamento de áudio se não for necessário
- Verifique se tem RAM suficiente

### Transcrição vazia ou com erros
- Verifique se o vídeo tem áudio
- Tente selecionar outro idioma
- Experimente um modelo maior (small ou medium)
- Ative normalização e redução de ruído

### Sem espaço em disco
- Os modelos Whisper ocupam espaço (3-5GB total)
- Remova modelos não usados manualmente se necessário
- Modelos ficam em: `~/.cache/whisper/` (Linux/Mac) ou `C:\Users\{user}\.cache\whisper\` (Windows)

### Timeout ao baixar vídeo
- Verifique sua conexão com a internet
- O vídeo pode ser muito grande ou estar indisponível
- Tente novamente após alguns segundos

## 📄 Licença

Este projeto é livre para uso pessoal e educacional.

## 🤝 Contribuições

Contribuições são bem-vindas! Sinta-se à vontade para abrir issues ou pull requests.

## 🙏 Agradecimentos

- **OpenAI** pelo modelo Whisper
- **yt-dlp** pela capacidade de download
- **Streamlit** pela excelente framework web
