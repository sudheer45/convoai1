from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, send_file, send_from_directory, flash
from werkzeug.utils import secure_filename
from google.cloud import speech, texttospeech
import os

app = Flask(__name__)

# Configure upload folder
UPLOAD_FOLDER = 'uploads'
TTS_FOLDER = 'tts'
ALLOWED_EXTENSIONS = {'wav'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['TTS_FOLDER'] = TTS_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(TTS_FOLDER, exist_ok=True)

# Initialize Google Cloud clients
speech_client = speech.SpeechClient()
tts_client = texttospeech.TextToSpeechClient()

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_files(folder):
    files = []
    for filename in os.listdir(folder):
        if allowed_file(filename):
            files.append(filename)
    files.sort(reverse=True)
    return files

@app.route('/')
def index():
    audio_files = get_files(UPLOAD_FOLDER)
    tts_files = get_files(TTS_FOLDER)
    return render_template('index.html', audio_files=audio_files, tts_files=tts_files)

@app.route('/upload', methods=['POST'])
def upload_audio():
    if 'audio_data' not in request.files:
        flash('No audio data')
        return redirect(request.url)
    file = request.files['audio_data']
    if file.filename == '':
        flash('No selected file')
        return redirect(request.url)
    if file:
        filename = datetime.now().strftime("%Y%m%d-%I%M%S%p") + '.wav'
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)

        # Call Speech-to-Text API
        with open(file_path, 'rb') as audio_file:
            audio_content = audio_file.read()

        audio = speech.RecognitionAudio(content=audio_content)
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=16000,
            language_code='en-US'
        )

        response = speech_client.recognize(config=config, audio=audio)

        transcript = "".join([result.alternatives[0].transcript for result in response.results])

        # Save transcript to a text file
        transcript_file = file_path.replace('.wav', '.txt')
        with open(transcript_file, 'w') as f:
            f.write(transcript)

    return redirect('/')  # success

@app.route('/upload/<filename>')
def get_file(filename):
    return send_file(filename)

@app.route('/upload_text', methods=['POST'])
def upload_text():
    text = request.form['text']
    if not text:
        flash('No text provided')
        return redirect('/')

    # Call Text-to-Speech API
    synthesis_input = texttospeech.SynthesisInput(text=text)
    voice = texttospeech.VoiceSelectionParams(
        language_code='en-US',
        ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL
    )
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.LINEAR16
    )

    response = tts_client.synthesize_speech(
        input=synthesis_input, voice=voice, audio_config=audio_config
    )

    # Save the audio file
    filename = datetime.now().strftime("%Y%m%d-%I%M%S%p") + '.wav'
    file_path = os.path.join(app.config['TTS_FOLDER'], filename)
    with open(file_path, 'wb') as out:
        out.write(response.audio_content)

    return redirect('/')  # success

@app.route('/script.js', methods=['GET'])
def scripts_js():
    return send_file('./script.js')

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/tts/<filename>')
def tts_file(filename):
    return send_from_directory(app.config['TTS_FOLDER'], filename)

if __name__ == '__main__':
    app.run(debug=True)
