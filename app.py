import imghdr
import os
from flask import Flask, render_template, request, send_from_directory
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Configuración
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024  # 2MB
app.config['UPLOAD_EXTENSIONS'] = ['.jpg', '.png', '.gif']
app.config['UPLOAD_PATH'] = 'uploads'


# Validación de contenido de imagen
def validate_image(stream):
    header = stream.read(512)
    stream.seek(0)

    format = imghdr.what(None, header)
    if not format:
        return None

    return '.' + (format if format != 'jpeg' else 'jpg')


# Manejo de error: archivo muy grande
@app.errorhandler(413)
def too_large(e):
    return "File is too large", 413


# Vista principal
@app.route('/')
def index():
    files = os.listdir(app.config['UPLOAD_PATH'])
    return render_template('index.html', files=files)


# Subida de archivos
@app.route('/', methods=['POST'])
def upload_files():
    uploaded_file = request.files['file']
    filename = secure_filename(uploaded_file.filename)

    if filename != '':
        file_ext = os.path.splitext(filename)[1]

        if file_ext not in app.config['UPLOAD_EXTENSIONS'] or \
           file_ext != validate_image(uploaded_file.stream):
            return "Invalid image", 400

        uploaded_file.save(os.path.join(app.config['UPLOAD_PATH'], filename))

    return '', 204


# Servir archivos subidos
@app.route('/uploads/<filename>')
def upload(filename):
    return send_from_directory(app.config['UPLOAD_PATH'], filename)


if __name__ == '__main__':
    app.run(debug=True)