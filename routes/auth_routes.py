from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from database.db_manager import get_db_connection, log_login_attempt
from datetime import datetime, timedelta
import uuid
import logging

logger = logging.getLogger(__name__)
auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Página de login"""
    if request.method == 'POST':
        try:
            # ✅ OBTENER DATOS DEL FORMULARIO O JSON
            data = request.get_json() if request.is_json else request.form
            username = data.get('username', '').strip()
            password = data.get('password', '')
            
            if not username or not password:
                error_msg = 'Por favor ingresa usuario y contraseña'
                if request.is_json:
                    return jsonify({'success': False, 'message': error_msg}), 400
                flash(error_msg, 'error')
                return render_template('login.html')
            
            # Registrar intento de login
            ip_address = request.remote_addr
            user_agent = request.headers.get('User-Agent')
            
            conn = get_db_connection()
            
            # ✅ BUSCAR USUARIO POR USERNAME O EMAIL CON COLUMNA CORRECTA
            user = conn.execute('''
                SELECT id, username, email, password_hash, first_name, last_name, 
                       is_admin, is_active, created_at
                FROM users 
                WHERE (username = ? OR email = ?) AND is_active = 1
            ''', (username, username)).fetchone()
            
            # ✅ VERIFICAR CONTRASEÑA CON password_hash
            if user and user['password_hash'] and check_password_hash(user['password_hash'], password):
                # Login exitoso
                session.clear()  # Limpiar sesión anterior
                session['user_id'] = user['id']
                session['username'] = user['username']
                session['email'] = user['email']
                session['first_name'] = user['first_name'] or ''
                session['last_name'] = user['last_name'] or ''
                session['is_admin'] = bool(user['is_admin'])
                session['logged_in'] = True
                session.permanent = True  # Hacer sesión permanente
                
                # Actualizar último login
                conn.execute(
                    'UPDATE users SET last_login = ? WHERE id = ?',
                    (datetime.now().isoformat(), user['id'])
                )
                conn.commit()
                
                # Registrar login exitoso
                log_login_attempt(username, ip_address, True, user_agent)
                
                logger.info(f"✅ Login exitoso: {username} (ID: {user['id']})")
                
                success_msg = f"Bienvenido, {user['first_name'] or username}!"
                
                if request.is_json:
                    return jsonify({
                        'success': True,
                        'message': success_msg,
                        'redirect': '/dashboard',
                        'user': {
                            'id': user['id'],
                            'username': user['username'],
                            'email': user['email'],
                            'first_name': user['first_name'],
                            'last_name': user['last_name'],
                            'is_admin': bool(user['is_admin'])
                        }
                    }), 200
                
                flash(success_msg, 'success')
                conn.close()
                return redirect(url_for('dashboard.dashboard'))
                
            else:
                # Login fallido
                log_login_attempt(username, ip_address, False, user_agent)
                error_msg = 'Usuario o contraseña incorrectos'
                logger.warning(f"❌ Login fallido: {username}")
                
                if request.is_json:
                    return jsonify({'success': False, 'message': error_msg}), 401
                    
                flash(error_msg, 'error')
            
            conn.close()
            
        except Exception as e:
            logger.error(f"❌ Error en login: {e}")
            import traceback
            traceback.print_exc()
            
            error_msg = f'Error interno: {str(e)}'
            if request.is_json:
                return jsonify({'success': False, 'message': error_msg}), 500
            flash(error_msg, 'error')
    
    try:
        return render_template('login.html')
    except Exception as e:
        logger.error(f"Error cargando login.html: {str(e)}")
        return f"Error cargando template login.html: {str(e)}"

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Registro de usuarios"""
    if request.method == 'POST':
        try:
            # ✅ OBTENER DATOS DEL FORMULARIO O JSON
            data = request.get_json() if request.is_json else request.form
            
            username = data.get('username', '').strip()
            email = data.get('email', '').strip()
            password = data.get('password', '')
            confirm_password = data.get('confirm_password', password)  # Para JSON sin confirm
            first_name = data.get('first_name', '').strip()
            last_name = data.get('last_name', '').strip()
            
            # ✅ VALIDACIONES MEJORADAS
            if not all([username, password]):
                error_msg = 'Usuario y contraseña son obligatorios'
                if request.is_json:
                    return jsonify({'success': False, 'message': error_msg}), 400
                flash(error_msg, 'error')
                return render_template('register.html')
            
            if password != confirm_password:
                error_msg = 'Las contraseñas no coinciden'
                if request.is_json:
                    return jsonify({'success': False, 'message': error_msg}), 400
                flash(error_msg, 'error')
                return render_template('register.html')
            
            if len(password) < 6:
                error_msg = 'La contraseña debe tener al menos 6 caracteres'
                if request.is_json:
                    return jsonify({'success': False, 'message': error_msg}), 400
                flash(error_msg, 'error')
                return render_template('register.html')
            
            # ✅ VERIFICAR SI EL USUARIO YA EXISTE
            conn = get_db_connection()
            existing_user = conn.execute(
                'SELECT id FROM users WHERE username = ? OR email = ?', 
                (username, email or username)
            ).fetchone()
            
            if existing_user:
                conn.close()
                error_msg = 'El usuario o email ya existe'
                if request.is_json:
                    return jsonify({'success': False, 'message': error_msg}), 400
                flash(error_msg, 'error')
                return render_template('register.html')
            
            # ✅ CREAR USUARIO CON password_hash
            user_id = str(uuid.uuid4())
            password_hash = generate_password_hash(password)
            
            # ✅ USAR COLUMNA password_hash EN LUGAR DE password
            cursor = conn.execute('''
                INSERT INTO users (
                    id, username, email, password_hash, first_name, last_name, 
                    is_admin, is_active, created_at, role
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                user_id, username, email or f"{username}@ava.local", 
                password_hash, first_name, last_name, 0, 1, 
                datetime.now().isoformat(), 'user'
            ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"✅ Usuario registrado: {username} (ID: {user_id})")
            
            success_msg = 'Usuario registrado correctamente. Ahora puedes iniciar sesión.'
            
            if request.is_json:
                return jsonify({
                    'success': True,
                    'message': success_msg,
                    'user_id': user_id,
                    'redirect': '/login'
                }), 201
            
            flash(success_msg, 'success')
            return redirect(url_for('auth.login'))
            
        except Exception as e:
            logger.error(f"❌ Error en registro: {e}")
            import traceback
            traceback.print_exc()
            
            error_msg = f'Error interno: {str(e)}'
            if request.is_json:
                return jsonify({'success': False, 'message': error_msg}), 500
            flash(error_msg, 'error')
    
    try:
        return render_template('register.html')
    except Exception as e:
        logger.error(f"Error cargando register.html: {str(e)}")
        return f"Error cargando template register.html: {str(e)}"

@auth_bp.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    """Recuperar contraseña"""
    if request.method == 'POST':
        try:
            data = request.get_json() if request.is_json else request.form
            
            email = data.get('email', '').strip()
            password = data.get('password', '')
            confirm_password = data.get('confirm_password', '')
            
            if not all([email, password, confirm_password]):
                error_msg = 'Todos los campos son obligatorios'
                if request.is_json:
                    return jsonify({'success': False, 'message': error_msg}), 400
                flash(error_msg, 'error')
                return render_template('forgot_password.html')
            
            if password != confirm_password:
                error_msg = 'Las contraseñas no coinciden'
                if request.is_json:
                    return jsonify({'success': False, 'message': error_msg}), 400
                flash(error_msg, 'error')
                return render_template('forgot_password.html')
            
            # ✅ BUSCAR USUARIO POR EMAIL
            conn = get_db_connection()
            user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
            
            if user:
                # ✅ ACTUALIZAR password_hash NO password
                password_hash = generate_password_hash(password)
                conn.execute(
                    'UPDATE users SET password_hash = ? WHERE email = ?',
                    (password_hash, email)
                )
                conn.commit()
                
                success_msg = 'Contraseña actualizada correctamente'
                logger.info(f"✅ Contraseña actualizada para: {email}")
                
                if request.is_json:
                    return jsonify({
                        'success': True,
                        'message': success_msg,
                        'redirect': '/login'
                    }), 200
                
                flash(success_msg, 'success')
                conn.close()
                return redirect(url_for('auth.login'))
            else:
                error_msg = 'Email no encontrado'
                if request.is_json:
                    return jsonify({'success': False, 'message': error_msg}), 404
                flash(error_msg, 'error')
                
            conn.close()
            
        except Exception as e:
            logger.error(f"❌ Error en forgot_password: {e}")
            error_msg = f'Error interno: {str(e)}'
            if request.is_json:
                return jsonify({'success': False, 'message': error_msg}), 500
            flash(error_msg, 'error')
    
    try:
        return render_template('forgot_password.html')
    except Exception as e:
        logger.error(f"Error cargando forgot_password.html: {str(e)}")
        return f"Error cargando template forgot_password.html: {str(e)}"

@auth_bp.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """Restablecer contraseña con token"""
    if request.method == 'POST':
        try:
            data = request.get_json() if request.is_json else request.form
            
            password = data.get('password', '')
            confirm_password = data.get('confirm_password', '')
            
            if not all([password, confirm_password]):
                error_msg = 'Todos los campos son obligatorios'
                if request.is_json:
                    return jsonify({'success': False, 'message': error_msg}), 400
                flash(error_msg, 'error')
                return render_template('reset_password.html', token=token)
            
            if password != confirm_password:
                error_msg = 'Las contraseñas no coinciden'
                if request.is_json:
                    return jsonify({'success': False, 'message': error_msg}), 400
                flash(error_msg, 'error')
                return render_template('reset_password.html', token=token)
            
            # Por simplicidad, usar el token como user_id
            conn = get_db_connection()
            user = conn.execute('SELECT * FROM users WHERE id = ?', (token,)).fetchone()
            
            if user:
                # ✅ ACTUALIZAR password_hash NO password
                password_hash = generate_password_hash(password)
                conn.execute(
                    'UPDATE users SET password_hash = ? WHERE id = ?',
                    (password_hash, token)
                )
                conn.commit()
                
                success_msg = 'Contraseña restablecida correctamente'
                logger.info(f"✅ Contraseña restablecida para token: {token}")
                
                if request.is_json:
                    return jsonify({
                        'success': True,
                        'message': success_msg,
                        'redirect': '/login'
                    }), 200
                
                flash(success_msg, 'success')
                conn.close()
                return redirect(url_for('auth.login'))
            else:
                error_msg = 'Token inválido'
                if request.is_json:
                    return jsonify({'success': False, 'message': error_msg}), 404
                flash(error_msg, 'error')
                
            conn.close()
            
        except Exception as e:
            logger.error(f"❌ Error en reset_password: {e}")
            error_msg = f'Error interno: {str(e)}'
            if request.is_json:
                return jsonify({'success': False, 'message': error_msg}), 500
            flash(error_msg, 'error')
    
    try:
        return render_template('reset_password.html', token=token)
    except Exception as e:
        logger.error(f"Error cargando reset_password.html: {str(e)}")
        return f"Error cargando template reset_password.html: {str(e)}"

@auth_bp.route('/logout')
def logout():
    """Cerrar sesión"""
    username = session.get('username', 'Usuario desconocido')
    session.clear()
    
    logger.info(f"✅ Logout exitoso: {username}")
    flash('Has cerrado sesión correctamente', 'info')
    
    return redirect(url_for('index.index'))

# ✅ RUTA ADICIONAL PARA VERIFICAR AUTENTICACIÓN (API)
@auth_bp.route('/api/check_auth')
def check_auth():
    """API para verificar si el usuario está autenticado"""
    if 'user_id' in session and session.get('logged_in'):
        return jsonify({
            'authenticated': True,
            'user': {
                'id': session['user_id'],
                'username': session['username'],
                'email': session.get('email'),
                'first_name': session.get('first_name'),
                'last_name': session.get('last_name'),
                'is_admin': session.get('is_admin', False)
            }
        }), 200
    else:
        return jsonify({'authenticated': False}), 401