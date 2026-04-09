import os
import uuid  # <--- IMPORTANTE: Asegúrate de que esta línea esté
from PIL import Image, UnidentifiedImageError
from flask import Flask, redirect, render_template, request, send_from_directory, jsonify, url_for
from flask_login import LoginManager, UserMixin, login_user, current_user, login_required, logout_user
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'llave-ultra-secreta-xdxd' 

# ==================== CONFIGURACIÓN ====================
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024
app.config['UPLOAD_EXTENSIONS'] = {'.jpg', '.jpeg', '.png', '.gif'}
app.config['UPLOAD_PATH'] = 'uploads'
app.config['MAX_FILE_SIZE'] = 5 * 1024 * 1024

os.makedirs(app.config['UPLOAD_PATH'], exist_ok=True)

# Fake login para pruebas
login_manager = LoginManager(app)
class User(UserMixin):
    def __init__(self, id):
        self.id = id
    def get_id(self):
        return str(self.id)
    
@login_manager.user_loader
def load_user(user_id):
    return User(user_id)

@app.route('/login/<int:user_id>')
def login_test(user_id):
    user = User(user_id)
    login_user(user)
    return redirect(url_for('index'))

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))

def allowed_image_extension(filename: str) -> bool:
    ext = os.path.splitext(filename)[1].lower()
    return ext in app.config['UPLOAD_EXTENSIONS']

def validate_image(file_stream) -> bool:
    try:
        file_stream.seek(0)
        with Image.open(file_stream) as img:
            img.verify()
        file_stream.seek(0)
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
@login_required # Añadido para asegurar que hay un usuario
def upload_files():
    if 'file' not in request.files:
        return jsonify({"error": "No se envió ningún archivo"}), 400

    uploaded_file = request.files['file']
    
    # --- CAMBIO 1: Obtener extensión de forma segura ---
    original_filename = secure_filename(uploaded_file.filename)
    if original_filename == '':
        return jsonify({"error": "Nombre de archivo vacío"}), 400
    
    file_ext = os.path.splitext(original_filename)[1].lower()

    # 1. Validar extensión
    if not allowed_image_extension(original_filename):
        return jsonify({"error": "Tipo de archivo no permitido."}), 400

    # 2. Validar tamaño real
    if request.content_length and request.content_length > app.config['MAX_FILE_SIZE']:
        return jsonify({"error": "El archivo excede el límite permitido."}), 413

    # 3. Validar que sea realmente una imagen
    if not validate_image(uploaded_file.stream):
        return jsonify({"error": "El archivo no es una imagen válida."}), 400

    # --- CAMBIO 2: MEJORA UUID (Tu parte) ---
    # Generamos un nombre único para evitar sobrescrituras y ataques de nombre
    unique_name = f"{uuid.uuid4().hex}{file_ext}"
    # ----------------------------------------

    user_dir = os.path.join(app.config['UPLOAD_PATH'], current_user.get_id())
    os.makedirs(user_dir, exist_ok=True)

    try:
        # --- CAMBIO 3: Guardar con el nombre UNICO ---
        uploaded_file.save(os.path.join(user_dir, unique_name))
    except Exception as e:
        return jsonify({"error": "Error al guardar el archivo"}), 500

    return jsonify({
        "message": "Archivo subido correctamente",
        "filename": unique_name # Devolvemos el nombre único generado
    }), 201

@app.route('/uploads/<filename>')
@login_required
def upload(filename):
    return send_from_directory(os.path.join(
        app.config['UPLOAD_PATH'], current_user.get_id()), filename)

if __name__ == '__main__':
    app.run(debug=True)