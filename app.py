import os
import uuid
from PIL import Image, UnidentifiedImageError
from flask import Flask, redirect, render_template, request, send_from_directory, jsonify, url_for
from flask_login import LoginManager, UserMixin, login_user, current_user, login_required, logout_user
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'llave-ultra-secreta-xdxd'  # simula una sk de prueba

# ==================== CONFIGURACIÓN ====================
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024      # 5 MB total por petición
app.config['UPLOAD_EXTENSIONS'] = {'.jpg', '.jpeg', '.png', '.gif'}
app.config['UPLOAD_PATH'] = 'uploads'
app.config['MAX_FILE_SIZE'] = 5 * 1024 * 1024           # 5 MB por archivo

# MEJORA 1 - Límite de píxeles para evitar bombas de descompresión
# Un atacante podría subir una imagen de 10KB con dimensiones 100.000x100.000 píxeles,
# lo que agotaría la memoria RAM al intentar abrirla. Con este límite (50 millones de píxeles)
# Pillow lanzará una excepción DecompressionBombError y rechazará la imagen.
Image.MAX_IMAGE_PIXELS = 50_000_000

os.makedirs(app.config['UPLOAD_PATH'], exist_ok=True)

# ==================== LOGIN SIMULADO ====================
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

# ==================== FUNCIONES DE VALIDACIÓN ====================
def allowed_image_extension(filename: str) -> bool:
    """Valida la extensión del archivo."""
    ext = os.path.splitext(filename)[1].lower()
    return ext in app.config['UPLOAD_EXTENSIONS']

# MEJORA 2 - Validación profunda de contenido + coherencia formato/extensión
def validate_image(file_stream, original_filename: str) -> bool:
    """
    Verifica que el archivo sea una imagen real Y que su formato interno
    coincida con la extensión declarada. Esto evita, por ejemplo, que alguien
    renombre un .exe a .png o que suba un JPEG con extensión .gif.
    """
    try:
        # Primera apertura: verifica integridad básica
        file_stream.seek(0)
        with Image.open(file_stream) as img:
            img.verify()
        
        # Segunda apertura: obtenemos el formato real (verify() cierra el stream)
        file_stream.seek(0)
        with Image.open(file_stream) as img:
            real_format = img.format  # 'JPEG', 'PNG', 'GIF'
        
        # Mapeo de extensiones a formatos Pillow
        ext = os.path.splitext(original_filename)[1].lower()
        format_map = {'.jpg': 'JPEG', '.jpeg': 'JPEG', '.png': 'PNG', '.gif': 'GIF'}
        expected_format = format_map.get(ext)
        
        # Si no coincide, rechazamos
        if expected_format and real_format != expected_format:
            return False
        
        # MEJORA 1 (aplicada aquí automáticamente): Si la imagen supera MAX_IMAGE_PIXELS,
        # Pillow lanzará DecompressionBombError y será capturado abajo.
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

    # 2. Validar tamaño real (por seguridad, aunque el cliente ya lo limite)
    if request.content_length and request.content_length > app.config['MAX_FILE_SIZE']:
        return jsonify({"error": "El archivo excede el límite de tamaño permitido."}), 413

    # 3. Validación de contenido real (MEJORAS 1 y 2)
    if not validate_image(uploaded_file.stream, filename):
        return jsonify({"error": "El archivo no es una imagen válida o su formato no coincide con la extensión."}), 400

    # 4. Guardado en carpeta del usuario
    user_dir = os.path.join(app.config['UPLOAD_PATH'], current_user.get_id())
    os.makedirs(user_dir, exist_ok=True)

    try:
        uploaded_file.save(os.path.join(user_dir, filename))
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