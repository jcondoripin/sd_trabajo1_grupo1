import os
import uuid
from PIL import Image, UnidentifiedImageError
from flask import Flask, redirect, render_template, request, send_from_directory, jsonify, url_for
from flask_login import LoginManager, UserMixin, login_user, current_user, login_required, logout_user
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'llave-ultra-secreta-xdxd' # simula una sk de prueba

# ==================== CONFIGURACIÓN ====================
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024      # 5 MB (recomendado para imágenes)
app.config['UPLOAD_EXTENSIONS'] = {'.jpg', '.jpeg', '.png', '.gif'}
app.config['UPLOAD_PATH'] = 'uploads'
app.config['MAX_FILE_SIZE'] = 5 * 1024 * 1024           # Límite por archivo (en bytes)

# Crear carpeta de uploads si no existe
os.makedirs(app.config['UPLOAD_PATH'], exist_ok=True)

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

def allowed_image_extension(filename: str) -> bool:
    """Valida la extensión del archivo."""
    ext = os.path.splitext(filename)[1].lower()
    return ext in app.config['UPLOAD_EXTENSIONS']


def validate_image(file_stream) -> bool:
    """Valida que el contenido sea realmente una imagen usando Pillow (más seguro que imghdr)."""
    try:
        # Rewind el stream
        file_stream.seek(0)
        # Intentamos abrir la imagen (Pillow lanza excepción si no es válida)
        with Image.open(file_stream) as img:
            img.verify()  # Verifica que sea una imagen válida
        file_stream.seek(0)  # Volvemos al inicio para guardarlo después
        return True
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
        return False


# ==================== MANEJO DE ERRORES ====================
@app.errorhandler(413)
def too_large(e):
    return jsonify({"error": "El archivo es demasiado grande. El límite es 5 MB."}), 413


# ==================== RUTAS ====================
@app.route('/')
def index():
    files = []
    if current_user.is_authenticated:
        user_dir = os.path.join(app.config['UPLOAD_PATH'], current_user.get_id())
        if os.path.exists(user_dir):
            files = os.listdir(user_dir)
    return render_template('index.html', files=files)


@app.route('/', methods=['POST'])
def upload_files():
    if 'file' not in request.files:
        return jsonify({"error": "No se envió ningún archivo"}), 400

    uploaded_file = request.files['file']
    filename = secure_filename(uploaded_file.filename)

    if filename == '':
        return jsonify({"error": "Nombre de archivo vacío"}), 400

    # 1. Validar extensión
    if not allowed_image_extension(filename):
        return jsonify({"error": "Tipo de archivo no permitido. Solo JPG, PNG y GIF."}), 400

    # 2. Validar tamaño real (por si el cliente lo burla)
    if request.content_length and request.content_length > app.config['MAX_FILE_SIZE']:
        return jsonify({"error": "El archivo excede el límite de tamaño permitido."}), 413

    # 3. Validar que sea realmente una imagen (contenido)
    if not validate_image(uploaded_file.stream):
        return jsonify({"error": "El archivo no es una imagen válida."}), 400

    # 4. Generar nombre seguro + único (evita sobrescrituras y ataques)
    # secure_name = secure_filename(filename)
    # unique_name = f"{uuid.uuid4().hex}_{secure_name}"
    # save_path = os.path.join(app.config['UPLOAD_PATH'], unique_name)
    user_dir = os.path.join(app.config['UPLOAD_PATH'], current_user.get_id())
    os.makedirs(user_dir, exist_ok=True) # crea carpeta si no existe

    # 5. Guardar de forma eficiente (streaming)
    try:
        uploaded_file.save(os.path.join(user_dir, filename))
        # Alternativa más controlada con streaming (útil para archivos grandes):
        # with open(save_path, 'wb') as f:
        #     while chunk := uploaded_file.stream.read(8192):
        #         f.write(chunk)
    except Exception as e:
        return jsonify({"error": "Error al guardar el archivo"}), 500

    return jsonify({
        "message": "Archivo subido correctamente",
        "filename": filename
    }), 201


@app.route('/uploads/<filename>')
@login_required
def upload(filename):
    return send_from_directory(os.path.join(
        app.config['UPLOAD_PATH'], current_user.get_id()), filename)


if __name__ == '__main__':
    app.run(debug=True)