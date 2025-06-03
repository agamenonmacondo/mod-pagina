from flask import Blueprint, render_template, session, jsonify
from utils.decorators import login_required, admin_required
from database.db_manager import get_db_connection
import logging
import sqlite3
from pathlib import Path

logger = logging.getLogger(__name__)
dashboard_bp = Blueprint('dashboard', __name__)

# ✅ FUNCIÓN PARA CONECTAR A MEMORY.DB
def get_memory_connection():
    """Conecta a la base de datos de memoria de Ava"""
    try:
        # Buscar memory.db en ubicaciones comunes
        possible_paths = [
            Path("llmpagina/ava_bot/tools/adapters/memory.db"),
            Path("llmpagina/ava_bot/memory.db"),
            Path("memory.db")
        ]
        
        db_path = None
        for path in possible_paths:
            if path.exists():
                db_path = path
                break
        
        if not db_path:
            # Buscar recursivamente
            for root, dirs, files in Path(".").rglob("memory.db"):
                db_path = root / "memory.db"
                break
        
        if db_path:
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            return conn
        
        return None
    except Exception as e:
        logger.error(f"Error conectando a memory.db: {e}")
        return None

@dashboard_bp.route('/dashboard')
@login_required
def dashboard():
    """Dashboard principal - Incluye estadísticas de conversaciones"""
    try:
        conn = get_db_connection()
        
        # Estadísticas de usuarios
        stats = {}
        stats['total_users'] = conn.execute('SELECT COUNT(*) FROM users').fetchone()[0] or 0
        stats['active_users'] = conn.execute('SELECT COUNT(*) FROM users WHERE is_active = 1').fetchone()[0] or 0
        stats['admin_users'] = conn.execute('SELECT COUNT(*) FROM users WHERE is_admin = 1').fetchone()[0] or 0
        stats['today_logins'] = conn.execute(
            'SELECT COUNT(*) FROM login_attempts WHERE DATE(attempted_at) = DATE("now") AND success = 1'
        ).fetchone()[0] or 0
        
        # ✅ ESTADÍSTICAS DE CONVERSACIONES AVA (AJUSTADO)
        memory_conn = get_memory_connection()
        if memory_conn:
            try:
                # Total conversaciones
                stats['total_conversations'] = memory_conn.execute(
                    'SELECT COUNT(*) FROM memory_entries WHERE entry_type = "message"'
                ).fetchone()[0] or 0
                
                # Usuarios únicos que han conversado - CAMBIAR NOMBRE
                stats['unique_users'] = memory_conn.execute(
                    'SELECT COUNT(DISTINCT user_id) FROM memory_entries'
                ).fetchone()[0] or 0
                
                # Conversaciones hoy
                stats['today_conversations'] = memory_conn.execute(
                    'SELECT COUNT(*) FROM memory_entries WHERE DATE(timestamp) = DATE("now")'
                ).fetchone()[0] or 0
                
                # ✅ AGREGAR TIEMPO PROMEDIO DE RESPUESTA (simulado por ahora)
                stats['avg_response_time'] = 2.3  # Tiempo promedio en segundos
                
                memory_conn.close()
            except:
                stats['total_conversations'] = 0
                stats['unique_users'] = 0
                stats['today_conversations'] = 0
                stats['avg_response_time'] = 0
        else:
            stats['total_conversations'] = 0
            stats['unique_users'] = 0
            stats['today_conversations'] = 0
            stats['avg_response_time'] = 0
        
        # Usuarios recientes
        recent_users = conn.execute('''
            SELECT username, email, first_name, last_name, created_at, last_login, is_admin, is_active
            FROM users
            ORDER BY created_at DESC
            LIMIT 10
        ''').fetchall()
        
        # Intentos de login recientes
        recent_logins = conn.execute('''
            SELECT username, ip_address, success, attempted_at
            FROM login_attempts
            ORDER BY attempted_at DESC
            LIMIT 10
        ''').fetchall()
        
        conn.close()
        
        return render_template('dashboard.html', 
                             stats=stats,
                             recent_users=recent_users,
                             recent_logins=recent_logins,
                             user=session)
    except Exception as e:
        logger.error(f"Error en dashboard: {e}")
        return render_template('dashboard.html', 
                             stats={'total_users': 0, 'active_users': 0, 'admin_users': 0, 'today_logins': 0,
                                   'total_conversations': 0, 'conversation_users': 0, 'today_conversations': 0}, 
                             recent_users=[],
                             recent_logins=[],
                             user=session,
                             error=str(e))

# ✅ NUEVA RUTA PARA VER CONVERSACIONES
@dashboard_bp.route('/conversations')
@login_required
def conversations():
    """Panel de conversaciones de Ava"""
    try:
        memory_conn = get_memory_connection()
        if not memory_conn:
            return render_template('conversations.html', 
                                 conversations=[], 
                                 stats={},
                                 error="No se pudo conectar a la base de datos de conversaciones",
                                 active_menu='conversations')
        
        # Estadísticas
        stats = {}
        stats['total'] = memory_conn.execute('SELECT COUNT(*) FROM memory_entries WHERE entry_type = "message"').fetchone()[0] or 0
        stats['users'] = memory_conn.execute('SELECT COUNT(DISTINCT user_id) FROM memory_entries').fetchone()[0] or 0
        stats['today'] = memory_conn.execute('SELECT COUNT(*) FROM memory_entries WHERE DATE(timestamp) = DATE("now")').fetchone()[0] or 0
        
        # Conversaciones recientes (últimas 50)
        conversations = memory_conn.execute('''
            SELECT user_id, content, response, timestamp, entry_type
            FROM memory_entries 
            WHERE entry_type = "message"
            ORDER BY timestamp DESC 
            LIMIT 50
        ''').fetchall()
        
        # Usuarios más activos
        active_users = memory_conn.execute('''
            SELECT user_id, COUNT(*) as conversation_count
            FROM memory_entries 
            WHERE entry_type = "message"
            GROUP BY user_id
            ORDER BY conversation_count DESC
            LIMIT 10
        ''').fetchall()
        
        memory_conn.close()
        
        return render_template('conversations.html', 
                             conversations=conversations,
                             active_users=active_users,
                             stats=stats,
                             active_menu='conversations')
    except Exception as e:
        logger.error(f"Error en conversations: {e}")
        return render_template('conversations.html', 
                             conversations=[], 
                             stats={},
                             error=str(e),
                             active_menu='conversations')

# ✅ API PARA BUSCAR CONVERSACIONES
@dashboard_bp.route('/api/conversations/search')
@login_required
def search_conversations_detailed():
    """API para buscar conversaciones con filtros avanzados"""
    from flask import request
    
    try:
        query = request.args.get('q', '').strip()
        user_id = request.args.get('user', '').strip()
        
        memory_conn = get_memory_connection()
        if not memory_conn:
            return jsonify({'error': 'No se pudo conectar a la base de datos'})
        
        sql = '''
            SELECT user_id, content, response, timestamp
            FROM memory_entries 
            WHERE entry_type = "message"
        '''
        params = []
        
        if query:
            sql += ' AND (content LIKE ? OR response LIKE ?)'
            params.extend([f'%{query}%', f'%{query}%'])
        
        if user_id:
            sql += ' AND user_id LIKE ?'
            params.append(f'%{user_id}%')
        
        sql += ' ORDER BY timestamp DESC LIMIT 100'
        
        results = memory_conn.execute(sql, params).fetchall()
        memory_conn.close()
        
        return jsonify({
            'success': True,
            'conversations': [dict(row) for row in results],
            'count': len(results)
        })
        
    except Exception as e:
        logger.error(f"Error buscando conversaciones: {e}")
        return jsonify({'error': str(e)})

@dashboard_bp.route('/chat', methods=['GET', 'POST'])
@login_required
def chat():
    """Página de chat"""
    from flask import request, flash
    
    if request.method == 'POST':
        message = request.form.get('message')
        if message:
            response_message = f"Echo: {message}"
            flash(f'Mensaje enviado: {message}', 'info')
            return render_template('chat.html', 
                                 user=session, 
                                 last_message=message,
                                 last_response=response_message)
    
    try:
        return render_template('chat.html', user=session)
    except Exception as e:
        logger.error(f"Error cargando chat.html: {str(e)}")
        return f"Error cargando template chat.html: {str(e)}"

@dashboard_bp.route('/clients')
@login_required
def clients():
    """Gestión de clientes"""
    try:
        # ✅ OBTENER USUARIOS DE LA BASE DE DATOS PRINCIPAL
        conn = get_db_connection()
        users = conn.execute('''
            SELECT id, username, email, first_name, last_name, 
                   created_at, last_login, is_admin, is_active
            FROM users 
            ORDER BY created_at DESC
        ''').fetchall()
        conn.close()
        
        # ✅ OBTENER DATOS DE CONVERSACIONES DE MEMORY.DB
        memory_conn = get_memory_connection()
        conversation_clients = []
        
        if memory_conn:
            try:
                # Obtener clientes únicos con estadísticas
                conversation_data = memory_conn.execute('''
                    SELECT 
                        user_id,
                        COUNT(*) as conversations,
                        MAX(timestamp) as last_activity,
                        MIN(timestamp) as first_activity
                    FROM memory_entries 
                    WHERE entry_type = "message" AND user_id IS NOT NULL
                    GROUP BY user_id
                    ORDER BY last_activity DESC
                ''').fetchall()
                
                # Convertir a lista de diccionarios con nombres amigables
                for row in conversation_data:
                    user_id = row['user_id']
                    
                    # Generar nombre amigable
                    if '@' in user_id:
                        name = user_id.split('@')[0].title()
                    elif user_id.lower() == 'unknown_user':
                        name = 'Usuario Anónimo'
                    else:
                        name = user_id.title()
                    
                    conversation_clients.append({
                        'user_id': user_id,
                        'name': name,
                        'conversations': row['conversations'],
                        'last_activity': row['last_activity'],
                        'first_activity': row['first_activity']
                    })
                
                memory_conn.close()
            except Exception as e:
                logger.error(f"Error obteniendo datos de conversaciones: {e}")
                conversation_clients = []
        
        # ✅ COMBINAR USUARIOS REGISTRADOS CON CLIENTES DE CONVERSACIONES
        all_clients = []
        
        # Agregar usuarios registrados
        for user in users:
            client_data = {
                'user_id': user['username'],
                'name': f"{user['first_name']} {user['last_name']}".strip() or user['username'],
                'email': user['email'],
                'conversations': 0,  # Se actualizará si tiene conversaciones
                'last_activity': user['last_login'],
                'is_registered': True,
                'is_admin': user['is_admin'],
                'is_active': user['is_active'],
                'created_at': user['created_at']
            }
            
            # Buscar si tiene conversaciones
            for conv_client in conversation_clients:
                if conv_client['user_id'] == user['username'] or conv_client['user_id'] == user['email']:
                    client_data['conversations'] = conv_client['conversations']
                    if conv_client['last_activity']:
                        client_data['last_activity'] = conv_client['last_activity']
                    break
            
            all_clients.append(client_data)
        
        # Agregar clientes solo de conversaciones (no registrados)
        registered_users = {user['username'] for user in users} | {user['email'] for user in users}
        
        for conv_client in conversation_clients:
            if conv_client['user_id'] not in registered_users:
                all_clients.append({
                    'user_id': conv_client['user_id'],
                    'name': conv_client['name'],
                    'email': None,
                    'conversations': conv_client['conversations'],
                    'last_activity': conv_client['last_activity'],
                    'is_registered': False,
                    'is_admin': False,
                    'is_active': True,
                    'created_at': conv_client['first_activity']
                })
        
        # ✅ CALCULAR ESTADÍSTICAS
        from datetime import datetime, timedelta
        now = datetime.now()
        week_ago = now - timedelta(days=7)
        
        stats = {
            'total_clients': len(all_clients),
            'recent_clients': len([c for c in all_clients if c.get('created_at') and 
                                 datetime.fromisoformat(c['created_at'].replace('Z', '+00:00')) > week_ago]),
            'total_conversations': sum(c['conversations'] for c in all_clients),
            'active_clients': len([c for c in all_clients if c['conversations'] > 0])
        }
        
        return render_template('clients.html', 
                             clients=all_clients,  # ✅ Cambiar de 'users' a 'clients'
                             stats=stats,
                             active_menu='clients')
        
    except Exception as e:
        logger.error(f"Error en clients: {e}")
        import traceback
        traceback.print_exc()
        
        return render_template('clients.html', 
                             clients=[],  # ✅ Cambiar de 'users' a 'clients'
                             stats={
                                 'total_clients': 0,
                                 'recent_clients': 0,
                                 'total_conversations': 0,
                                 'active_clients': 0
                             },
                             error=str(e),
                             active_menu='clients')

@dashboard_bp.route('/statistics')
@login_required
def statistics():
    """Estadísticas detalladas - Incluye conversaciones"""
    try:
        conn = get_db_connection()
        
        # Estadísticas de usuarios
        daily_activity = conn.execute('''
            SELECT DATE(created_at) as date, COUNT(*) as count
            FROM users
            WHERE created_at >= DATE('now', '-30 days')
            GROUP BY DATE(created_at)
            ORDER BY date
        ''').fetchall()
        
        # Intentos de login por día
        login_stats = conn.execute('''
            SELECT DATE(attempted_at) as date, 
                   SUM(success) as successful_logins,
                   COUNT(*) as total_attempts
            FROM login_attempts
            WHERE attempted_at >= DATE('now', '-30 days')
            GROUP BY DATE(attempted_at)
            ORDER BY date
        ''').fetchall()
        
        conn.close()
        
        # ✅ ESTADÍSTICAS DE CONVERSACIONES
        memory_conn = get_memory_connection()
        conversation_stats = []
        if memory_conn:
            try:
                conversation_stats = memory_conn.execute('''
                    SELECT DATE(timestamp) as date, COUNT(*) as count
                    FROM memory_entries
                    WHERE timestamp >= DATE('now', '-30 days') AND entry_type = "message"
                    GROUP BY DATE(timestamp)
                    ORDER BY date
                ''').fetchall()
                memory_conn.close()
            except:
                pass
        
        stats = {
            'daily_activity': [dict(row) for row in daily_activity],
            'login_stats': [dict(row) for row in login_stats],
            'conversation_stats': [dict(row) for row in conversation_stats],
            'user_distribution': {'Activos': 5, 'Inactivos': 2, 'Admins': 1}
        }
        
        return render_template('statistics.html', stats=stats, active_menu='stats')
    except Exception as e:
        logger.error(f"Error en statistics: {e}")
        return render_template('statistics.html', stats={}, active_menu='stats', error=str(e))

@dashboard_bp.route('/configuration')
@admin_required
def configuration():
    """Configuración del sistema"""
    try:
        return render_template('configuration.html', active_menu='config')
    except Exception as e:
        logger.error(f"Error en configuration: {e}")
        return f"Error cargando configuración: {str(e)}"

# ✅ AGREGAR ESTA API QUE FALTA
@dashboard_bp.route('/api/conversations')
@login_required
def api_conversations():
    """API para el dashboard que busca conversaciones"""
    from flask import request
    
    try:
        page = int(request.args.get('page', 1))
        filter_type = request.args.get('filter', 'all')
        search_term = request.args.get('search', '')
        
        logger.info(f"🔍 API Conversations llamada: page={page}, filter={filter_type}, search='{search_term}'")
        
        memory_conn = get_memory_connection()
        if not memory_conn:
            logger.error("❌ No se pudo conectar a memory.db")
            return jsonify({
                'success': False,
                'conversations': [],
                'total': 0,
                'error': 'No se pudo conectar a memory.db'
            })
        
        try:
            # ✅ AGREGAR ROWID A LA CONSULTA
            sql = '''
                SELECT rowid, user_id, content, response, timestamp
                FROM memory_entries 
                WHERE entry_type = "message"
            '''
            params = []
            
            # Filtro de búsqueda
            if search_term:
                sql += ' AND (content LIKE ? OR response LIKE ? OR user_id LIKE ?)'
                search_param = f'%{search_term}%'
                params.extend([search_param, search_param, search_param])
            
            # Ordenar y paginar
            sql += ' ORDER BY timestamp DESC LIMIT 20 OFFSET ?'
            params.append((page - 1) * 20)
            
            logger.info(f"📝 Ejecutando SQL: {sql}")
            logger.info(f"📝 Parámetros: {params}")
            
            conversations = memory_conn.execute(sql, params).fetchall()
            
            # Contar total
            count_sql = 'SELECT COUNT(*) FROM memory_entries WHERE entry_type = "message"'
            if search_term:
                count_sql += ' AND (content LIKE ? OR response LIKE ? OR user_id LIKE ?)'
                total = memory_conn.execute(count_sql, [search_param, search_param, search_param]).fetchone()[0]
            else:
                total = memory_conn.execute(count_sql).fetchone()[0]
            
            memory_conn.close()
            
            result = {
                'success': True,
                'conversations': [dict(row) for row in conversations],
                'total': total,
                'page': page
            }
            
            logger.info(f"✅ API Conversations exitosa: {len(conversations)} conversaciones, total: {total}")
            return jsonify(result)
            
        except Exception as db_error:
            logger.error(f"❌ Error en consulta DB: {db_error}")
            memory_conn.close()
            return jsonify({
                'success': False,
                'conversations': [],
                'total': 0,
                'error': f'Error en base de datos: {str(db_error)}'
            })
        
    except Exception as e:
        logger.error(f"❌ Error en API conversations: {e}")
        return jsonify({
            'success': False,
            'conversations': [],
            'total': 0,
            'error': str(e)
        })

@dashboard_bp.route('/conversation/<conversation_id>')
@login_required
def conversation_details(conversation_id):
    """Página de detalles de conversación específica"""
    try:
        memory_conn = get_memory_connection()
        if not memory_conn:
            return render_template('conversation_details.html', 
                                 error="No se pudo conectar a la base de datos de conversaciones",
                                 conversation=None,
                                 active_menu='conversations')
        
        # Buscar conversación específica
        conversation = memory_conn.execute('''
            SELECT user_id, content, response, timestamp, entry_type
            FROM memory_entries 
            WHERE rowid = ? AND entry_type = "message"
        ''', (conversation_id,)).fetchone()
        
        if not conversation:
            return render_template('conversation_details.html',
                                 error="Conversación no encontrada",
                                 conversation=None,
                                 active_menu='conversations')
        
        # Buscar historial completo del usuario
        user_history = memory_conn.execute('''
            SELECT user_id, content, response, timestamp, entry_type
            FROM memory_entries 
            WHERE user_id = ? AND entry_type = "message"
            ORDER BY timestamp ASC
        ''', (conversation['user_id'],)).fetchall()
        
        # Estadísticas del usuario
        user_stats = {
            'total_messages': len(user_history),
            'first_interaction': user_history[0]['timestamp'] if user_history else None,
            'last_interaction': user_history[-1]['timestamp'] if user_history else None,
            'conversation_span': None
        }
        
        # Calcular duración de conversaciones
        if user_stats['first_interaction'] and user_stats['last_interaction']:
            from datetime import datetime
            first = datetime.fromisoformat(user_stats['first_interaction'].replace('Z', '+00:00'))
            last = datetime.fromisoformat(user_stats['last_interaction'].replace('Z', '+00:00'))
            span = last - first
            user_stats['conversation_span'] = f"{span.days} días, {span.seconds // 3600} horas"
        
        memory_conn.close()
        
        return render_template('conversation_details.html',
                             conversation=dict(conversation),
                             user_history=[dict(row) for row in user_history],
                             user_stats=user_stats,
                             conversation_id=conversation_id,
                             active_menu='conversations')
        
    except Exception as e:
        logger.error(f"Error en detalles de conversación: {e}")
        return render_template('conversation_details.html',
                             error=str(e),
                             conversation=None,
                             active_menu='conversations')

@dashboard_bp.route('/api/conversation/<conversation_id>/export')
@login_required  
def export_conversation_details(conversation_id):
    """API para exportar detalles completos de conversación"""
    try:
        memory_conn = get_memory_connection()
        if not memory_conn:
            return jsonify({'success': False, 'error': 'No se pudo conectar a la base de datos'})
        
        # Obtener conversación
        conversation = memory_conn.execute('''
            SELECT user_id, content, response, timestamp
            FROM memory_entries 
            WHERE rowid = ? AND entry_type = "message"
        ''', (conversation_id,)).fetchone()
        
        if not conversation:
            return jsonify({'success': False, 'error': 'Conversación no encontrada'})
        
        # Obtener historial completo
        user_history = memory_conn.execute('''
            SELECT content, response, timestamp
            FROM memory_entries 
            WHERE user_id = ? AND entry_type = "message"
            ORDER BY timestamp ASC
        ''', (conversation['user_id'],)).fetchall()
        
        memory_conn.close()
        
        # Generar contenido del archivo
        export_content = f"""DETALLES DE CONVERSACIÓN - AVA BOT
================================================

Usuario: {conversation['user_id']}
Fecha de exportación: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Total de intercambios: {len(user_history)}

HISTORIAL COMPLETO DE CONVERSACIONES:
================================================

"""
        
        for i, msg in enumerate(user_history, 1):
            timestamp = msg['timestamp']
            try:
                # Formatear timestamp
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                formatted_time = dt.strftime('%Y-%m-%d %H:%M:%S')
            except:
                formatted_time = timestamp
            
            export_content += f"""
--- Intercambio #{i} ---
Fecha: {formatted_time}

👤 USUARIO:
{msg['content']}

🤖 AVA:
{msg['response']}

{'='*50}
"""
        
        return jsonify({
            'success': True,
            'content': export_content,
            'filename': f"conversacion_detallada_{conversation['user_id'].replace('@', '_')}_{conversation_id}.txt"
        })
        
    except Exception as e:
        logger.error(f"Error exportando conversación: {e}")
        return jsonify({'success': False, 'error': str(e)})

# Agregar después de las rutas existentes

@dashboard_bp.route('/api/client/<client_id>/conversations')
@login_required
def get_client_conversations(client_id):
    """API para obtener conversaciones de un cliente específico"""
    try:
        memory_conn = get_memory_connection()
        if not memory_conn:
            return jsonify({'success': False, 'error': 'No se pudo conectar a la base de datos'})
        
        # Obtener todas las conversaciones del cliente
        conversations = memory_conn.execute('''
            SELECT content, response, timestamp
            FROM memory_entries 
            WHERE user_id = ? AND entry_type = "message"
            ORDER BY timestamp DESC
            LIMIT 50
        ''', (client_id,)).fetchall()
        
        memory_conn.close()
        
        return jsonify({
            'success': True,
            'conversations': [dict(row) for row in conversations],
            'total': len(conversations)
        })
        
    except Exception as e:
        logger.error(f"Error obteniendo conversaciones del cliente {client_id}: {e}")
        return jsonify({'success': False, 'error': str(e)})

@dashboard_bp.route('/api/client/<client_id>/export')
@login_required
def export_client_data(client_id):
    """API para exportar datos completos de un cliente"""
    try:
        memory_conn = get_memory_connection()
        if not memory_conn:
            return jsonify({'success': False, 'error': 'No se pudo conectar a la base de datos'})
        
        # Obtener todas las conversaciones
        conversations = memory_conn.execute('''
            SELECT content, response, timestamp
            FROM memory_entries 
            WHERE user_id = ? AND entry_type = "message"
            ORDER BY timestamp ASC
        ''', (client_id,)).fetchall()
        
        memory_conn.close()
        
        # Generar contenido del archivo
        from datetime import datetime
        
        export_content = f"""REPORTE COMPLETO DE CLIENTE - AVA BOT
================================================

Cliente: {client_id}
Fecha de exportación: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Total de conversaciones: {len(conversations)}

HISTORIAL COMPLETO:
================================================

"""
        
        for i, conv in enumerate(conversations, 1):
            timestamp = conv['timestamp']
            try:
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                formatted_time = dt.strftime('%Y-%m-%d %H:%M:%S')
            except:
                formatted_time = timestamp
            
            export_content += f"""
--- Conversación #{i} ---
Fecha: {formatted_time}

👤 CLIENTE:
{conv['content']}

🤖 AVA:
{conv['response']}

{'='*50}
"""
        
        return jsonify({
            'success': True,
            'content': export_content,
            'filename': f"cliente_{client_id.replace('@', '_')}_{datetime.now().strftime('%Y%m%d')}.txt"
        })
        
    except Exception as e:
        logger.error(f"Error exportando cliente {client_id}: {e}")
        return jsonify({'success': False, 'error': str(e)})