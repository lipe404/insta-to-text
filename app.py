import os
import subprocess
import tempfile
import streamlit as st
import speech_recognition as sr
from pydub import AudioSegment
from pydub.silence import split_on_silence
from moviepy import VideoFileClip
import re

# Configuração da página
st.set_page_config(
    page_title="Insta to Text - Transcritor de Vídeos em Texto",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Dicionário de idiomas suportados
IDIOMAS = {
    "Português (Brasil)": "pt-BR",
    "Português (Portugal)": "pt-PT",
    "Inglês (EUA)": "en-US",
    "Inglês (Reino Unido)": "en-GB",
    "Espanhol": "es-ES",
    "Espanhol (México)": "es-MX",
    "Francês": "fr-FR",
    "Italiano": "it-IT",
    "Alemão": "de-DE",
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


def extrair_audio(video_path, audio_path, progress_bar=None, status_text=None):
    """
    Extrai o áudio do vídeo e converte para WAV usando MoviePy
    """
    try:
        if status_text:
            status_text.text("Extraindo áudio do vídeo...")
        if progress_bar:
            progress_bar.progress(0.5)

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
            # Extrai o áudio e salva como WAV
            # Configurações otimizadas para reconhecimento de fala:
            # - 16kHz sample rate (padrão para reconhecimento)
            # - Mono channel
            # - FPS ajustado automaticamente pelo MoviePy

            audio = video.audio

            if audio is None:
                st.error("O vídeo não possui faixa de áudio.")
                video.close()
                return None

            # Salva o áudio em formato WAV
            # Na versão 2.x do moviepy, verbose foi removido
            audio.write_audiofile(
                audio_path,
                fps=16000,  # Taxa de amostragem otimizada para reconhecimento
                nbytes=2,   # 16-bit (2 bytes)
                codec='pcm_s16le',  # Codec PCM 16-bit little-endian
                logger=None  # Suprime logs e barra de progresso
            )

            # Fecha os objetos para liberar memória
            audio.close()
            video.close()

        except Exception as e:
            # Garante que os recursos são liberados mesmo em caso de erro
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
            progress_bar.progress(0.6)
        if status_text:
            status_text.text("Áudio extraído com sucesso!")

        # Verifica se o arquivo foi criado corretamente
        if os.path.exists(audio_path) and os.path.getsize(audio_path) > 0:
            return audio_path
        else:
            st.error("Erro: Arquivo de áudio não foi criado corretamente.")
            return None

    except Exception as e:
        st.error(f"Erro inesperado ao extrair áudio: {str(e)}")
        return None


def transcrever_audio(
        audio_path, idioma="pt-BR", progress_bar=None, status_text=None):
    """
    Transcreve o áudio usando Google Speech Recognition
    """
    recognizer = sr.Recognizer()

    try:
        if status_text:
            status_text.text("Carregando e processando áudio...")

        audio = AudioSegment.from_wav(audio_path)

        # Divide o áudio em chunks baseado no silêncio
        if status_text:
            status_text.text("Dividindo áudio em segmentos...")

        chunks = split_on_silence(
            audio,
            min_silence_len=500,  # Mínimo de 500ms de silêncio
            silence_thresh=audio.dBFS - 14,
            keep_silence=500  # Mantém 500ms de silêncio nas bordas
        )

        # Se não houver chunks, tenta transcrever o áudio completo
        if not chunks:
            chunks = [audio]

        transcricao_completa = []
        total_chunks = len(chunks)

        if status_text:
            status_text.text(f"Transcrevendo {total_chunks} segmentos...")

        for i, chunk in enumerate(chunks):
            # Atualiza progresso
            if progress_bar:
                progresso = 0.6 + (0.3 * (i + 1) / total_chunks)
                progress_bar.progress(progresso)

            # Exporta chunk temporário
            chunk_path = f"temp_chunk_{i}.wav"
            try:
                chunk.export(chunk_path, format="wav")

                # Transcreve o chunk
                with sr.AudioFile(chunk_path) as source:
                    # Ajusta para ruído ambiente
                    recognizer.adjust_for_ambient_noise(source, duration=0.5)
                    audio_data = recognizer.record(source)

                    try:
                        texto = recognizer.recognize_google(
                            audio_data, language=idioma)
                        transcricao_completa.append(texto)
                    except sr.UnknownValueError:
                        # Silenciosamente ignora segmentos não reconhecidos
                        pass
                    except sr.RequestError as e:
                        msg = (
                            f"Erro na API do Google para segmento "
                            f"{i+1}: {e}"
                        )
                        st.warning(msg)
            finally:
                # Remove chunk temporário
                limpar_arquivos_temporarios(chunk_path)

        if progress_bar:
            progress_bar.progress(0.95)

        resultado = " ".join(transcricao_completa)

        if progress_bar:
            progress_bar.progress(1.0)
        if status_text:
            status_text.text("Transcrição concluída!")

        return resultado if resultado.strip() else None

    except Exception as e:
        st.error(f"Erro ao transcrever áudio: {str(e)}")
        return None


def main():
    # Cabeçalho
    st.title("🎬 Insta to Text")
    st.markdown("### Transcritor de Vídeos do Instagram")
    st.markdown("---")

    # Sidebar com informações
    with st.sidebar:
        st.header("Informações")
        st.markdown("""
        **Como usar:**
        1. Cole a URL do vídeo do Instagram
        2. Selecione o idioma do áudio
        3. Clique em "Transcrever"
        4. Aguarde o processamento

        **Requisitos:**
        - yt-dlp instalado
        - Conexão com internet
        - Bibliotecas Python instaladas (requirements.txt)
        """)

        st.markdown("---")
        st.header("Configurações")

        idioma_selecionado = st.selectbox(
            "Idioma do áudio:",
            options=list(IDIOMAS.keys()),
            index=0,
            help="Selecione o idioma falado no vídeo para melhor precisão"
        )

        idioma_codigo = IDIOMAS[idioma_selecionado]

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

                # Passo 3: Transcrever áudio
                transcricao = transcrever_audio(
                    audio_file, idioma_codigo, progress_bar, status_text
                )

                # Limpeza automática se solicitado
                if limpar_automatico:
                    limpar_arquivos_temporarios(video_file, audio_file)

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
                        col_stat1, col_stat2, col_stat3 = st.columns(3)
                        with col_stat1:
                            st.metric("Palavras", len(transcricao.split()))
                        with col_stat2:
                            st.metric("Caracteres", len(transcricao))
                        with col_stat3:
                            st.metric("Idioma", idioma_selecionado)
                    else:
                        st.error("Não foi possível gerar a transcrição.")
                        st.info(
                            "Dicas:\n"
                            "- Verifique se o vídeo tem áudio\n"
                            "- Tente selecionar outro idioma\n"
                            "- Verifique sua conexão com a internet\n"
                            "- Alguns vídeos podem estar com áudio muito baixo"
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
        "Powered by Google Speech Recognition API"
    )


if __name__ == "__main__":
    main()
