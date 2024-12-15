from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import re
import secrets
from functools import wraps
from pymongo import MongoClient
from bson import ObjectId

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

# MongoDB Connection
client = MongoClient("mongodb://localhost:27017/")
db = client['PanamaAlert']
pings_collection = db['pings']
users_collection = db['users']

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Por favor inicie sesión', 'danger')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def validate_email(email):
    email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(email_regex, email) is not None

def validate_password(password):
    return (len(password) >= 8 and
            re.search(r'[A-Z]', password) and
            re.search(r'[a-z]', password) and
            re.search(r'\d', password))

@app.route('/')
@login_required
def home():
    return render_template('mapa.html')

@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        apellido = request.form.get('apellido')
        cedula = request.form.get('cedula')
        telefono = request.form.get('telefono')
        region = request.form.get('region')
        correo = request.form.get('correo')
        contrasena = request.form.get('contrasena')
        confirmar_contrasena = request.form.get('confirmar_contrasena')

        # Validations
        if not all([nombre, apellido, cedula, telefono, region, correo, contrasena, confirmar_contrasena]):
            flash('Todos los campos son obligatorios', 'danger')
            return redirect(url_for('registro'))

        if not validate_email(correo):
            flash('Correo electrónico inválido', 'danger')
            return redirect(url_for('registro'))

        if contrasena != confirmar_contrasena:
            flash('Las contraseñas no coinciden', 'danger')
            return redirect(url_for('registro'))

        if not validate_password(contrasena):
            flash('La contraseña debe tener al menos 8 caracteres, una mayúscula, una minúscula y un número', 'danger')
            return redirect(url_for('registro'))

        # Check if email already exists
        if users_collection.find_one({'correo': correo}):
            flash('El correo electrónico ya está registrado', 'danger')
            return redirect(url_for('registro'))

        # Create new user
        hashed_password = generate_password_hash(contrasena)
        new_user = {
            'nombre': nombre,
            'apellido': apellido,
            'cedula': cedula,
            'telefono': telefono,
            'region': region,
            'correo': correo,
            'contrasena': hashed_password
        }

        result = users_collection.insert_one(new_user)
        flash('Registro exitoso. Por favor inicie sesión.', 'success')
        return redirect(url_for('login'))

    return render_template('registro.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        correo = request.form.get('correo')
        contrasena = request.form.get('contrasena')

        if not correo or not contrasena:
            flash('Por favor ingrese correo y contraseña', 'danger')
            return redirect(url_for('login'))

        user = users_collection.find_one({'correo': correo})

        if user and check_password_hash(user['contrasena'], contrasena):
            session['user_id'] = str(user['_id'])
            session['nombre'] = user['nombre']
            flash('Inicio de sesión exitoso', 'success')
            return redirect(url_for('home'))
        else:
            flash('Correo o contraseña incorrectos', 'danger')
            return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Sesión cerrada exitosamente', 'success')
    return redirect(url_for('login'))

@app.route('/get_pings', methods=['GET'])
@login_required
def get_pings():
    user_pings = list(pings_collection.find({'user_id': session['user_id']}))
    for ping in user_pings:
        ping['_id'] = str(ping['_id'])
    return jsonify(user_pings)

@app.route('/add_ping', methods=['POST'])
@login_required
def add_ping():
    data = request.json
    lat = data.get('lat')
    lng = data.get('lng')
    info = data.get('info')

    if not all([lat, lng, info]):
        return jsonify({'success': False, 'error': 'Datos incompletos'}), 400

    new_ping = {
        'user_id': session['user_id'],
        'lat': lat,
        'lng': lng,
        'info': info
    }

    result = pings_collection.insert_one(new_ping)

    return jsonify({
        'success': True,
        'id': str(result.inserted_id)
    })

@app.route('/delete_ping/<ping_id>', methods=['DELETE'])
@login_required
def delete_ping(ping_id):
    try:
        result = pings_collection.delete_one({
            '_id': ObjectId(ping_id),
            'user_id': session['user_id']
        })

        return jsonify({'success': result.deleted_count > 0})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/update_ping/<ping_id>', methods=['PUT'])
@login_required
def update_ping(ping_id):
    try:
        data = request.json
        lat = data.get('lat')
        lng = data.get('lng')
        info = data.get('info')

        if not all([lat, lng, info]):
            return jsonify({'success': False, 'error': 'Datos incompletos'}), 400

        result = pings_collection.update_one(
            {'_id': ObjectId(ping_id), 'user_id': session['user_id']},
            {'$set': {'lat': lat, 'lng': lng, 'info': info}}
        )

        return jsonify({'success': result.modified_count > 0})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)