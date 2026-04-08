import imghdr
import os
from flask import Flask, redirect, render_template, request, send_from_directory, url_for
from flask_login import LoginManager, UserMixin, login_user, current_user, login_required, logout_user
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'llave-ultra-secreta-xdxd' # simula una sk de prueba

# Configuración
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 2MB (modificado para pruebas)
app.config['UPLOAD_EXTENSIONS'] = ['.jpg', '.png', '.gif']
app.config['UPLOAD_PATH'] = 'uploads'

# Fake login para pruebas
login_manager = LoginManager(app)
class User(UserMixin):
    def __init__(self, id):
        self.id = id
    def get_id(self):
        return super().get_id()
    
@login_manager.user_loader
def load_user(user_id):
    return User(user_id)

@app.route('/login/<int:user_id>')
def login_test(user_id):
    # simula el login de un usuario
    user = User(user_id)
    login_user(user)
    return redirect(url_for('index'))

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))

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
    files = []
    if current_user.is_authenticated:
        user_dir = os.path.join(app.config['UPLOAD_PATH'], current_user.get_id())
        if os.path.exists(user_dir):
            files = os.listdir(user_dir)
    return render_template('index.html', files=files)


# Subida de archivos
@app.route('/', methods=['POST'])
def upload_files():
    uploaded_file = request.files['file']
    filename = secure_filename(uploaded_file.filename)

    if filename != '':
        # sube archivos solo a una carpeta privada
        user_dir = os.path.join(app.config['UPLOAD_PATH'], current_user.get_id())
        os.makedirs(user_dir, exist_ok=True) # crea carpeta si no existe
        file_ext = os.path.splitext(filename)[1]

        if file_ext not in app.config['UPLOAD_EXTENSIONS'] or \
           file_ext != validate_image(uploaded_file.stream):
            return "Invalid image", 400

        uploaded_file.save(os.path.join(user_dir, filename))

    return '', 204


# Servir archivos subidos
@app.route('/uploads/<filename>')
@login_required
def upload(filename):
    return send_from_directory(os.path.join(
        app.config['UPLOAD_PATH'], current_user.get_id()), filename)


if __name__ == '__main__':
    app.run(debug=True)