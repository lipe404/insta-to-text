import os
import subprocess
import tempfile
import streamlit as st
from pydub import AudioSegment
from pydub.effects import normalize, compress_dynamic_range
import noisereduce as nr
import numpy as np
import re
from moviepy import VideoFileClip

# Import lazy do Whisper para evitar erros de inicialização
_whisper_loaded = False
_whisper_module = None


def load_whisper():
    """Carrega o módulo Whisper de forma lazy"""
    global _whisper_loaded, _whisper_module
    if not _whisper_loaded:
        try:
            import whisper
            _whisper_module = whisper
            _whisper_loaded = True
        except Exception as e:
            st.error(
                f"Erro ao carregar Whisper: {str(e)}\n\n"
                "Tente reinstalar: pip install --upgrade openai-whisper"
            )
            raise
    return _whisper_module


# Configuração da página
st.set_page_config(
    page_title="Insta to Text - Transcritor de Vídeos em Texto",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Mapeamento de idiomas para Whisper
IDIOMAS_WHISPER = {
    "Português (Brasil)": "pt",
    "Português (Portugal)": "pt",
    "Inglês (EUA)": "en",
    "Inglês (Reino Unido)": "en",
    "Espanhol": "es",
    "Espanhol (México)": "es",
    "Francês": "fr",
    "Italiano": "it",
    "Alemão": "de",
    "Japonês": "ja",
    "Chinês": "zh",
    "Russo": "ru",
    "Árabe": "ar",
    "Hindi": "hi",
}

# Modelos Whisper disponíveis (do menor/mais rápido ao maior/mais preciso)
MODELOS_WHISPER = {
    "tiny (Mais rápido, menor precisão)": "tiny",
    "base (Balanceado)": "base",
    "small (Boa precisão)": "small",
    "medium (Alta precisão)": "medium",
    "large (Máxima precisão, mais lento)": "large-v3",
}


def validar_url_instagram(url):
    """Valida se a URL é do Instagram"""
    if not url:
        return False
    padrao = r'instagram\.com/(reel|p|tv)/'
    return bool(re.search(padrao, url, re.IGNORECASE))


def limpar_arquivos_temporarios(*arquivos):
    """Remove arquivos temporários de forma segura"""
    for arquivo in arquivos:
        try:
            if arquivo and os.path.exists(arquivo):
                os.remove(arquivo)
        except Exception as e:
            st.warning(f"Erro ao remover {arquivo}: {e}")


def baixar_video_instagram(
        url, output_path, progress_bar=None, status_text=None):
    """
    Baixa um vídeo do Instagram usando yt-dlp
    """
    try:
        if status_text:
            status_text.text("Baixando vídeo do Instagram...")
        if progress_bar:
            progress_bar.progress(0.1)

        # Verifica se yt-dlp está instalado
        try:
            subprocess.run(
                ["yt-dlp", "--version"],
                check=True, capture_output=True, timeout=5
            )
        except (subprocess.CalledProcessError, FileNotFoundError,
                subprocess.TimeoutExpired):
            st.error(
                "yt-dlp não encontrado! "
                "Instale com: `pip install yt-dlp`"
            )
            return None

        comando = [
            "yt-dlp",
            "-f", "best",
            "-o", output_path,
            "--no-warnings",
            "--quiet",
            url
        ]

        subprocess.run(
            comando,
            check=True,
            capture_output=True,
            text=True,
            timeout=300  # 5 minutos de timeout
        )

        if progress_bar:
            progress_bar.progress(0.4)
        if status_text:
            status_text.text("Vídeo baixado com sucesso!")

        return output_path if os.path.exists(output_path) else None

    except subprocess.TimeoutExpired:
        st.error("⏱Tempo esgotado ao baixar o vídeo. Tente novamente.")
        return None
    except subprocess.CalledProcessError as e:
        st.error(f"Erro ao baixar vídeo: {e.stderr if e.stderr else str(e)}")
        return None
    except FileNotFoundError:
        st.error("yt-dlp não encontrado. Instale com: `pip install yt-dlp`")
        return None
    except Exception as e:
        st.error(f"Erro inesperado ao baixar vídeo: {str(e)}")
        return None


def processar_audio(
        audio_path, audio_processado_path,
        normalizar=True, reduzir_ruido=True,
        progress_bar=None, status_text=None):
    """
    Processa o áudio: normalização e redução de ruído
    """
    try:
        if status_text:
            status_text.text("Processando e melhorando qualidade do áudio...")
        if progress_bar:
            progress_bar.progress(0.5)

        # Carrega o áudio
        audio = AudioSegment.from_wav(audio_path)

        # Normalização de volume
        if normalizar:
            if status_text:
                status_text.text("Normalizando volume do áudio...")
            audio = normalize(audio)
            # Compressão de range dinâmico para melhorar clareza
            audio = compress_dynamic_range(audio)

        # Redução de ruído
        if reduzir_ruido:
            if status_text:
                status_text.text("Reduzindo ruído do áudio...")
            try:
                # Converte para numpy array
                audio_np = np.array(audio.get_array_of_samples())

                # Aplica redução de ruído estacionário
                audio_reduzido = nr.reduce_noise(
                    y=audio_np.astype(np.float32),
                    sr=audio.frame_rate,
                    stationary=True
                )

                # Converte de volta para AudioSegment
                audio_reduzido_int = (
                    audio_reduzido * 32767
                ).astype(np.int16)
                audio = AudioSegment(
                    audio_reduzido_int.tobytes(),
                    frame_rate=audio.frame_rate,
                    channels=audio.channels,
                    sample_width=audio.sample_width
                )
            except Exception as e:
                # Se falhar, continua sem redução de ruído
                st.warning(
                    f"Não foi possível reduzir ruído automaticamente: {e}. "
                    "Continuando sem redução de ruído."
                )

        # Garante mono e 16kHz (otimizado para Whisper)
        if audio.channels != 1:
            audio = audio.set_channels(1)
        if audio.frame_rate != 16000:
            audio = audio.set_frame_rate(16000)

        # Salva o áudio processado
        audio.export(audio_processado_path, format="wav")

        if progress_bar:
            progress_bar.progress(0.6)
        if status_text:
            status_text.text("Áudio processado com sucesso!")

        return audio_processado_path if os.path.exists(
            audio_processado_path
        ) else None

    except Exception as e:
        st.error(f"Erro ao processar áudio: {str(e)}")
        return None


def extrair_audio(video_path, audio_path, progress_bar=None, status_text=None):
    """
    Extrai o áudio do vídeo e converte para WAV usando MoviePy
    """
    try:
        if status_text:
            status_text.text("Extraindo áudio do vídeo...")
        if progress_bar:
            progress_bar.progress(0.45)

        # Verifica se o arquivo de vídeo existe
        if not os.path.exists(video_path):
            st.error(f"Arquivo de vídeo não encontrado: {video_path}")
            return None

        # Carrega o vídeo usando MoviePy
        try:
            video = VideoFileClip(video_path)
        except Exception as e:
            st.error(
                f"Erro ao carregar o vídeo: {str(e)}\n\n"
                "Certifique-se de que o arquivo é um vídeo válido."
            )
            return None

        try:
            audio = video.audio

            if audio is None:
                st.error("O vídeo não possui faixa de áudio.")
                video.close()
                return None

            # Salva o áudio em formato WAV
            audio.write_audiofile(
                audio_path,
                fps=16000,
                nbytes=2,
                codec='pcm_s16le',
                logger=None
            )

            # Fecha os objetos para liberar memória
            audio.close()
            video.close()

        except Exception as e:
            try:
                if 'audio' in locals():
                    audio.close()
                if 'video' in locals():
                    video.close()
            except Exception:
                pass

            st.error(f"Erro ao processar áudio: {str(e)}")
            return None

        if progress_bar:
            progress_bar.progress(0.5)
        if status_text:
            status_text.text("Áudio extraído com sucesso!")

        return audio_path if os.path.exists(audio_path) else None

    except Exception as e:
        st.error(f"Erro inesperado ao extrair áudio: {str(e)}")
        return None


def adicionar_pontuacao(texto):
    """
    Adiciona pontuação básica ao texto transcrito
    """
    if not texto:
        return texto

    # Remove espaços múltiplos
    texto = re.sub(r'\s+', ' ', texto).strip()

    # Adiciona ponto após maiúsculas seguidas de ponto e espaço
    # (para frases que já terminam)
    texto = re.sub(r'([.!?])\s*([A-ZÁÉÍÓÚÀÈÌÒÙÂÊÎÔÛÃÕÇ])', r'\1 \2', texto)

    # Adiciona ponto final se não terminar com pontuação
    if texto and texto[-1] not in '.!?':
        texto += '.'

    # Capitaliza primeira letra
    if texto:
        texto = texto[0].upper() + texto[1:]

    # Corrige espaços antes de pontuação
    texto = re.sub(r'\s+([,.!?;:])', r'\1', texto)

    # Adiciona espaço após pontuação se não houver
    texto = re.sub(r'([,.!?;:])([^\s])', r'\1 \2', texto)

    return texto


def transcrever_audio_whisper(
        audio_path, idioma="pt", modelo="base",
        adicionar_pontuacao_opcional=True,
        progress_bar=None, status_text=None):
    """
    Transcreve o áudio usando Whisper (OpenAI)
    """
    try:
        if status_text:
            status_text.text(f"Carregando modelo Whisper ({modelo})...")
        if progress_bar:
            progress_bar.progress(0.65)

        # Carrega o módulo Whisper (lazy loading)
        whisper = load_whisper()

        # Carrega o modelo Whisper
        modelo_whisper = whisper.load_model(modelo)

        if status_text:
            status_text.text("Transcrevendo áudio com Whisper...")
        if progress_bar:
            progress_bar.progress(0.7)

        # Transcreve o áudio
        resultado = modelo_whisper.transcribe(
            audio_path,
            language=idioma,
            task="transcribe",
            fp16=False,  # Usa float32 para compatibilidade
            verbose=False
        )

        texto_transcrito = resultado["text"].strip()

        if progress_bar:
            progress_bar.progress(0.9)

        # Aplica pós-processamento de pontuação se solicitado
        if adicionar_pontuacao_opcional and texto_transcrito:
            if status_text:
                status_text.text("Aplicando pontuação automática...")
            texto_transcrito = adicionar_pontuacao(texto_transcrito)

        if progress_bar:
            progress_bar.progress(1.0)
        if status_text:
            status_text.text("Transcrição concluída!")

        return texto_transcrito if texto_transcrito else None

    except Exception as e:
        st.error(f"Erro ao transcrever com Whisper: {str(e)}")
        return None


def main():
    # Cabeçalho
    st.title("🎬 Insta to Text")
    st.markdown("### Transcritor de Vídeos do Instagram com Whisper")
    st.markdown("---")

    # Sidebar com informações
    with st.sidebar:
        st.header("Informações")
        st.markdown("""
        **Como usar:**
        1. Cole a URL do vídeo do Instagram
        2. Configure as opções abaixo
        3. Clique em "Transcrever"
        4. Aguarde o processamento

        **Melhorias:**
        - 🎯 Whisper AI (alta precisão)
        - 🔊 Normalização automática de áudio
        - 🔇 Redução de ruído automática
        - 📝 Pontuação automática opcional
        """)

        st.markdown("---")
        st.header("Configurações de Transcrição")

        idioma_selecionado = st.selectbox(
            "Idioma do áudio:",
            options=list(IDIOMAS_WHISPER.keys()),
            index=0,
            help="Selecione o idioma falado no vídeo"
        )

        idioma_codigo = IDIOMAS_WHISPER[idioma_selecionado]

        modelo_selecionado = st.selectbox(
            "Modelo Whisper:",
            options=list(MODELOS_WHISPER.keys()),
            index=1,  # base como padrão
            help="Modelos maiores são mais precisos mas mais lentos"
        )

        modelo_codigo = MODELOS_WHISPER[modelo_selecionado]

        st.markdown("---")
        st.header("Processamento de Áudio")

        normalizar_audio = st.checkbox(
            "Normalizar áudio automaticamente",
            value=True,
            help="Ajusta volume e compressão dinâmica"
        )

        reduzir_ruido = st.checkbox(
            "Reduzir ruído automaticamente",
            value=True,
            help="Remove ruído de fundo do áudio"
        )

        st.markdown("---")
        st.header("Pós-processamento")

        adicionar_pontuacao_auto = st.checkbox(
            "Adicionar pontuação automaticamente",
            value=True,
            help="Aplica pontuação e formatação ao texto"
        )

        limpar_automatico = st.checkbox(
            "Limpar arquivos temporários automaticamente",
            value=True,
            help="Remove vídeo e áudio após a transcrição"
        )

    # Área principal
    st.markdown("### 📎 URL do Vídeo")
    url = st.text_input(
        "Cole a URL do vídeo do Instagram aqui:",
        placeholder="https://www.instagram.com/reel/...",
        label_visibility="collapsed"
    )

    # Validação da URL
    if url and not validar_url_instagram(url):
        st.warning(
            "URL inválida. Certifique-se de que é um link do Instagram "
            "(reel, post ou vídeo)."
        )

    col1, col2 = st.columns([1, 4])

    with col1:
        botao_transcrever = st.button(
            "Transcrever",
            type="primary",
            use_container_width=True,
            disabled=not url or not validar_url_instagram(url)
        )

    with col2:
        st.caption("Suporta reels, posts e vídeos do Instagram")

    # Processamento
    if botao_transcrever and url and validar_url_instagram(url):
        # Cria diretório temporário para arquivos
        with tempfile.TemporaryDirectory() as temp_dir:
            video_path = os.path.join(temp_dir, "video_instagram.mp4")
            audio_path = os.path.join(temp_dir, "audio.wav")
            audio_processado_path = os.path.join(
                temp_dir, "audio_processado.wav"
            )

            # Barra de progresso
            progress_bar = st.progress(0)
            status_text = st.empty()

            # Container para resultados
            resultado_container = st.container()

            try:
                # Passo 1: Baixar vídeo
                video_file = baixar_video_instagram(
                    url, video_path, progress_bar, status_text
                )
                if not video_file:
                    st.stop()

                # Passo 2: Extrair áudio
                audio_file = extrair_audio(
                    video_file, audio_path, progress_bar, status_text
                )
                if not audio_file:
                    limpar_arquivos_temporarios(video_file)
                    st.stop()

                # Passo 3: Processar áudio (normalização e redução de ruído)
                audio_processado = processar_audio(
                    audio_file,
                    audio_processado_path,
                    normalizar=normalizar_audio,
                    reduzir_ruido=reduzir_ruido,
                    progress_bar=progress_bar,
                    status_text=status_text
                )
                if not audio_processado:
                    # Usa áudio original se processamento falhar
                    audio_processado = audio_file

                # Passo 4: Transcrever com Whisper
                transcricao = transcrever_audio_whisper(
                    audio_processado,
                    idioma_codigo,
                    modelo_codigo,
                    adicionar_pontuacao_opcional=adicionar_pontuacao_auto,
                    progress_bar=progress_bar,
                    status_text=status_text
                )

                # Limpeza automática se solicitado
                if limpar_automatico:
                    limpar_arquivos_temporarios(
                        video_file, audio_file, audio_processado_path
                    )

                # Exibe resultado
                with resultado_container:
                    st.markdown("---")
                    if transcricao:
                        st.success("Transcrição concluída com sucesso!")
                        st.markdown("### Transcrição:")

                        # Área de texto editável
                        st.text_area(
                            "Texto transcrito:",
                            value=transcricao,
                            height=300,
                            label_visibility="collapsed",
                            key="transcricao_texto"
                        )

                        # Botão para download
                        st.download_button(
                            label="Baixar Transcrição (.txt)",
                            data=transcricao,
                            file_name="transcricao.txt",
                            mime="text/plain",
                            use_container_width=True
                        )

                        # Estatísticas
                        col_stat1, col_stat2, col_stat3, col_stat4 = (
                            st.columns(4)
                        )
                        with col_stat1:
                            st.metric("Palavras", len(transcricao.split()))
                        with col_stat2:
                            st.metric("Caracteres", len(transcricao))
                        with col_stat3:
                            st.metric("Idioma", idioma_selecionado)
                        with col_stat4:
                            modelo_nome = modelo_selecionado.split()[0]
                            st.metric("Modelo", modelo_nome)
                    else:
                        st.error("Não foi possível gerar a transcrição.")
                        st.info(
                            "Dicas:\n"
                            "- Verifique se o vídeo tem áudio\n"
                            "- Tente selecionar outro idioma\n"
                            "- Experimente um modelo maior (small/medium)\n"
                            "- Verifique se há espaço em disco suficiente"
                        )

            except Exception as e:
                st.error(f"Erro inesperado: {str(e)}")
                st.exception(e)

    elif botao_transcrever:
        st.warning("Por favor, insira uma URL válida do Instagram.")

    # Rodapé
    st.markdown("---")
    st.caption(
        "Desenvolvido com Streamlit por Felipe Toledo | "
        "Powered by OpenAI Whisper AI"
    )


if __name__ == "__main__":
    main()
