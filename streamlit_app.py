import os
import streamlit as st
from pydub import AudioSegment, silence
from ibm_watson import SpeechToTextV1
from ibm_cloud_sdk_core.authenticators import IAMAuthenticator

APP_NAME = 'Clean Speech'
APP_ICON = '💬'
APP_DESCRIPTION = '<i>Powered by <a href="https://cloud.ibm.com/catalog/services/speech-to-text" target="_blank">IBM Speech to Text</a></i>'

SUPPORTED_AUDIO_FORMATS = ['flv', 'mp3', 'ogg', 'raw', 'wav']

SETTINGS_KEY_API_KEY = 'IBM_STT_API_KEY'
SETTINGS_KEY_API_URL = 'IBM_STT_API_URL'

LABEL_SETTINGS = 'Settings'
LABEL_SETTINGS_GROUP_IBM = 'IBM Speech To Text'
LABEL_UPLOAD_FILE = 'Upload Audio File'
LABEL_MAX_SILENCE = 'Max Silence Between Words (Milliseconds)'
LABEL_CLEANUP_TRANSCRIBED_WORDS = 'Transcribed Words'
LABEL_TRANSCRIBED_WORDS = 'Reorder/Delete'
LABEL_SETTINGS_IBM_SPEECH_TO_TEXT_API_KEY = 'API Key'
LABEL_SETTINGS_IBM_SPEECH_TO_TEXT_API_URL = 'API URL'
LABEL_SPEECH_HESITATION = '%HESITATION'
LABEL_SPEECH_PAUSE = '%PAUSE'

WARNING_SET_IBM_API_VARIABLES = f'Set IBM Speech to Text API key and URL in the sidebar or as environment variables {SETTINGS_KEY_API_KEY} and {SETTINGS_KEY_API_URL} respectively.'

ERROR_INVALID_AUDIO_FILE = 'Invalid audio file'
ERROR_UNABLE_TO_CONVERT_SPEECH_TO_TEXT = 'Unable to convert speech to text'

def get_env_variable(key):
    return os.environ.get(key, '')

def get_settings():
    settings = {}
    st.sidebar.header(LABEL_SETTINGS)

    api_key = get_env_variable(SETTINGS_KEY_API_KEY)
    api_url = get_env_variable(SETTINGS_KEY_API_URL)
    with st.sidebar.expander(LABEL_SETTINGS_GROUP_IBM, len(api_key) == 0 or len(api_url) == 0):
        settings[SETTINGS_KEY_API_KEY] = st.text_input(LABEL_SETTINGS_IBM_SPEECH_TO_TEXT_API_KEY, value=api_key, help=f'Set Environment Variable = {SETTINGS_KEY_API_KEY}')
        settings[SETTINGS_KEY_API_URL] = st.text_input(LABEL_SETTINGS_IBM_SPEECH_TO_TEXT_API_URL, value=api_url, help=f'Set Environment Variable = {SETTINGS_KEY_API_URL}')
    return settings

def upload_audio_file():
    audio_file = st.file_uploader(LABEL_UPLOAD_FILE, SUPPORTED_AUDIO_FORMATS, accept_multiple_files=False)
    if audio_file is not None:
        return audio_file, audio_file.type.split('/')[1]
    return None, None

def convert_audio_file_to_segment(uploaded_file):
    if uploaded_file is not None:
        try:
            if uploaded_file.type == 'audio/flv':
                return AudioSegment.from_flv(uploaded_file)
            elif uploaded_file.type == 'audio/mp3':
                return AudioSegment.from_mp3(uploaded_file)
            elif uploaded_file.type == 'audio/ogg':
                return AudioSegment.from_ogg(uploaded_file)
            elif uploaded_file.type == 'audio/raw':
                return AudioSegment.from_raw(uploaded_file)
            elif uploaded_file.type == 'audio/wav':
                return AudioSegment.from_wav(uploaded_file)
        except:
            st.error(ERROR_INVALID_AUDIO_FILE)
    return None

def audio_file_player(audio_file):
    st.audio(audio_file)

def audio_segment_player(audio_segment, audio_format):
    st.audio(audio_segment.export(format=audio_format).read())

@st.cache(show_spinner=True)
def convert_speech_to_text(audio_file, api_key, api_url):
    if audio_file:
        authenticator = IAMAuthenticator(f'{api_key}')
        speech_to_text = SpeechToTextV1(
            authenticator=authenticator
        )
        speech_to_text.set_service_url(f'{api_url}')
        return speech_to_text.recognize(
            audio=audio_file,
            content_type=audio_file.type,
            timestamps=True,
            smart_formatting=True
        ).get_result()
    return None

def get_transcript_json_to_text(transcript_json):
    words = []
    for results in transcript_json['results']:
        if len(results['alternatives']):
            for timestamp in results['alternatives'][0]['timestamps']:
                words.append(timestamp)
            words.append([LABEL_SPEECH_PAUSE, 0, 0])
    return words

def get_transcription_text(transcript_words):
    return " ".join([w[0] for w in transcript_words])

def cleanup_speech(audio_segment, transcription_words, max_silence=500):
    output_segment = audio_segment[0:0]
    output_transcription_words = []
    t = 0
    for w in transcription_words:
        if w[0] != LABEL_SPEECH_HESITATION and w[0] != LABEL_SPEECH_PAUSE:
            s = int(w[1]*1000)
            output_segment += audio_segment[t:t+min(s-t, max_silence)]
            t = int(w[2]*1000)
            output_segment += audio_segment[s:t]
            output_transcription_words.append(w)
    return output_segment, output_transcription_words

def main():
    st.set_page_config(page_title=APP_NAME, page_icon=APP_ICON, initial_sidebar_state='collapsed')
    st.title(APP_ICON + ' ' + APP_NAME)
    st.markdown(APP_DESCRIPTION, True)
    settings = get_settings()

    audio_file, audio_format = upload_audio_file()
    if audio_file is not None:
        st.subheader('Original Audio')
        audio_file_player(audio_file)
        
        if len(settings[SETTINGS_KEY_API_KEY]) and len(settings[SETTINGS_KEY_API_URL]):
            transcript_json = convert_speech_to_text(audio_file, settings[SETTINGS_KEY_API_KEY], settings[SETTINGS_KEY_API_URL])
            if transcript_json:
                transcript_words = get_transcript_json_to_text(transcript_json)
                st.info(get_transcription_text(transcript_words))
                
                st.subheader('Clean Audio')
                max_silence = st.slider(LABEL_MAX_SILENCE, 0, 1000, 500, 10)
                
                original_sound = convert_audio_file_to_segment(audio_file)
                
                transcript_words = [w for w in transcript_words if w[0] != LABEL_SPEECH_HESITATION and w[0] != LABEL_SPEECH_PAUSE]
                
                with st.expander(LABEL_CLEANUP_TRANSCRIBED_WORDS, False):
                    transcript_words = st.multiselect(LABEL_TRANSCRIBED_WORDS, transcript_words, transcript_words)

                clean_sound, clean_transcription_words = cleanup_speech(original_sound, transcript_words, max_silence)
                
                audio_segment_player(clean_sound, audio_format)
                st.warning(get_transcription_text(clean_transcription_words))
            else:
                st.error(ERROR_UNABLE_TO_CONVERT_SPEECH_TO_TEXT)
        else:
            st.warning(WARNING_SET_IBM_API_VARIABLES)

if __name__ == "__main__":
    main()
