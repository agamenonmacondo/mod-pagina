console.log('🔍 Verificando estado de autenticación...');

// Verificar si estamos autenticados
fetch('/api/chat/status')
    .then(response => {
        console.log('📊 Auth status:', response.status);
        if (response.status === 302) {
            console.log('❌ No autenticado - redirigiendo al login');
            window.location.href = '/login';
            return;
        }
        return response.json();
    })
    .then(data => {
        console.log('✅ Autenticado:', data);
        // Solo aquí cargar conversaciones
        loadConversations();
    })
    .catch(error => {
        console.error('❌ Error verificando auth:', error);
    });

// ✅ PREVENIR EJECUCIÓN MÚLTIPLE
if (window.dashboardInitialized) {
    console.log('🔄 Dashboard ya inicializado, evitando duplicación');
} else {
    window.dashboardInitialized = true;
    
    console.log('🚀 Inicializando Dashboard...');

    // ✅ VARIABLES GLOBALES PARA CONTROL
    let currentPage = 1;
    let isLoading = false;
    let authChecked = false;

    // ✅ FUNCIÓN PRINCIPAL PARA CARGAR CONVERSACIONES
    function loadConversations(page = 1, filter = 'all', search = '') {
        if (isLoading) {
            console.log('⏳ Ya hay una carga en proceso, evitando duplicación');
            return;
        }
        
        isLoading = true;
        currentPage = page;
        
        console.log(`📥 Cargando conversaciones - Página: ${page}, Filtro: ${filter}, Búsqueda: "${search}"`);
        
        const url = `/api/conversations?page=${page}&filter=${filter}&search=${encodeURIComponent(search)}`;
        
        // Mostrar indicador de carga solo si hay tabla
        const tbody = document.querySelector('.conversation-table tbody');
        if (tbody) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="6" class="loading-indicator" style="text-align: center; padding: 40px;">
                        <div class="spinner" style="border: 4px solid #f3f3f3; border-top: 4px solid #3498db; border-radius: 50%; width: 30px; height: 30px; animation: spin 1s linear infinite; margin: 0 auto;"></div>
                        <p style="margin-top: 15px;">Cargando conversaciones...</p>
                    </td>
                </tr>
            `;
        }
        
        // Realizar la solicitud AJAX
        fetch(url)
            .then(response => {
                console.log(`📊 Response status: ${response.status}`);
                
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                console.log('✅ Datos recibidos:', {
                    success: data.success,
                    conversationsCount: data.conversations ? data.conversations.length : 0,
                    total: data.total
                });
                
                if (data.success && data.conversations) {
                    displayConversations(data.conversations, data.total, page);
                } else {
                    showEmptyState(data.error || 'No hay conversaciones disponibles');
                }
            })
            .catch(error => {
                console.error('❌ Error cargando conversaciones:', error);
                showEmptyState('Error de conexión. Verifique su conexión e intente nuevamente.');
            })
            .finally(() => {
                isLoading = false;
            });
    }

    // ✅ FUNCIÓN PARA MOSTRAR CONVERSACIONES
    function displayConversations(conversations, total, page) {
        const tbody = document.querySelector('.conversation-table tbody');
        if (!tbody) {
            console.log('⚠️ No se encontró tabla de conversaciones en esta página');
            return;
        }
        
        tbody.innerHTML = '';
        
        if (conversations && conversations.length > 0) {
            conversations.forEach((conv, index) => {
                const row = document.createElement('tr');
                
                const conversationId = conv.rowid;
                const displayId = `conv-${page}-${index + 1}`;
                const userId = conv.user_id || 'Usuario Anónimo';
                const lastMessage = (conv.content || '').substring(0, 50) + '...';
                const timestamp = formatDate(conv.timestamp);
                const responsePreview = (conv.response || '').substring(0, 30) + '...';
                
                row.innerHTML = `
                    <td>${displayId}</td>
                    <td>
                        <div class="user-info">
                            <strong>${userId}</strong>
                            <br>
                            <small style="opacity: 0.7;">${lastMessage}</small>
                        </div>
                    </td>
                    <td>${timestamp}</td>
                    <td>
                        <div class="message-preview">
                            <small style="opacity: 0.8;">${responsePreview}</small>
                        </div>
                    </td>
                    <td>
                        <span class="status-badge status-completed">Completada</span>
                    </td>
                    <td class="actions">
                        <!-- 👁️ BOTÓN DEL OJO PARA MODAL -->
                        <button class="action-btn view-btn" 
                                data-user="${userId}" 
                                data-content="${encodeURIComponent(conv.content)}"
                                data-response="${encodeURIComponent(conv.response)}"
                                data-timestamp="${conv.timestamp}"
                                data-id="${conversationId}"
                                title="Ver conversación en modal">
                            <i class="fas fa-eye"></i>
                        </button>
                        
                        <!-- ℹ️ BOTÓN DE DETALLES PARA PÁGINA COMPLETA -->
                        <a href="/conversation/${conversationId}" 
                           class="action-btn details-btn" 
                           title="Ver detalles completos"
                           style="display: inline-flex; align-items: center; justify-content: center; text-decoration: none; color: inherit;">
                            <i class="fas fa-info-circle"></i>
                        </a>
                        
                        <!-- 💾 BOTÓN DE EXPORTACIÓN -->
                        <button class="action-btn export-btn" 
                                data-user="${userId}"
                                data-id="${conversationId}"
                                title="Exportar conversación">
                            <i class="fas fa-download"></i>
                        </button>
                    </td>
                `;
                tbody.appendChild(row);
            });
            
            updatePaginationInfo(total, page);
            console.log(`✅ Mostradas ${conversations.length} conversaciones de ${total} totales`);
            
        } else {
            showEmptyState('No se encontraron conversaciones');
        }
    }

    // ✅ FUNCIÓN PARA MOSTRAR ESTADO VACÍO
    function showEmptyState(message) {
        const tbody = document.querySelector('.conversation-table tbody');
        if (tbody) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="6" class="empty-state" style="text-align: center; padding: 40px;">
                        <i class="fas fa-comments" style="font-size: 48px; opacity: 0.3; margin-bottom: 15px; display: block;"></i>
                        <p style="margin: 0; opacity: 0.7;">${message}</p>
                    </td>
                </tr>
            `;
        }
    }

    // ✅ FUNCIÓN PARA ACTUALIZAR PAGINACIÓN
    function updatePaginationInfo(total, page) {
        const pageInfo = document.querySelector('.page-info');
        const prevBtn = document.getElementById('prevPage');
        const nextBtn = document.getElementById('nextPage');
        
        if (pageInfo) {
            const totalPages = Math.ceil(total / 20);
            pageInfo.textContent = `Página ${page} de ${totalPages} (${total} conversaciones)`;
        }
        
        if (prevBtn) prevBtn.disabled = page <= 1;
        if (nextBtn) nextBtn.disabled = page >= Math.ceil(total / 20);
    }

    // ✅ FUNCIÓN PARA FORMATEAR FECHAS
    function formatDate(dateString) {
        if (!dateString) return 'N/A';
        
        try {
            const date = new Date(dateString);
            return date.toLocaleString('es-ES', {
                year: 'numeric',
                month: '2-digit',
                day: '2-digit',
                hour: '2-digit',
                minute: '2-digit'
            });
        } catch (e) {
            return dateString;
        }
    }

    // ✅ VERIFICACIÓN DE AUTENTICACIÓN SIMPLIFICADA
    function checkAuthAndLoad() {
        if (authChecked) {
            console.log('🔄 Auth ya verificado, cargando conversaciones directamente');
            if (document.querySelector('.conversation-table')) {
                loadConversations();
            }
            return;
        }
        
        console.log('🔍 Verificando autenticación...');
        
        fetch('/api/chat/status')
            .then(response => {
                console.log(`📊 Auth status: ${response.status}`);
                
                if (response.status === 302) {
                    console.log('❌ No autenticado - redirigiendo al login');
                    window.location.href = '/login';
                    return;
                }
                
                if (response.ok) {
                    authChecked = true;
                    console.log('✅ Autenticado correctamente');
                    
                    // Solo cargar conversaciones si hay tabla
                    if (document.querySelector('.conversation-table')) {
                        loadConversations();
                    }
                } else {
                    throw new Error(`Auth failed: ${response.status}`);
                }
            })
            .catch(error => {
                console.error('❌ Error verificando auth:', error);
                authChecked = false;
            });
    }

    // ✅ INICIALIZACIÓN CONTROLADA
    document.addEventListener('DOMContentLoaded', function() {
        console.log('📋 DOM cargado, configurando eventos...');
        
        // Event listeners para búsqueda
        const searchInput = document.getElementById('searchInput');
        const searchBtn = document.getElementById('searchBtn');
        const timeFilter = document.getElementById('timeFilter');
        
        if (searchBtn) {
            searchBtn.addEventListener('click', function() {
                const searchTerm = searchInput ? searchInput.value.trim() : '';
                const filter = timeFilter ? timeFilter.value : 'all';
                loadConversations(1, filter, searchTerm);
            });
        }
        
        if (searchInput) {
            searchInput.addEventListener('keypress', function(e) {
                if (e.key === 'Enter') {
                    const searchTerm = searchInput.value.trim();
                    const filter = timeFilter ? timeFilter.value : 'all';
                    loadConversations(1, filter, searchTerm);
                }
            });
        }
        
        // Event listeners para paginación
        const prevPageBtn = document.getElementById('prevPage');
        const nextPageBtn = document.getElementById('nextPage');
        
        if (prevPageBtn) {
            prevPageBtn.addEventListener('click', function() {
                if (!this.disabled && !isLoading) {
                    const searchTerm = searchInput ? searchInput.value.trim() : '';
                    const filter = timeFilter ? timeFilter.value : 'all';
                    loadConversations(currentPage - 1, filter, searchTerm);
                }
            });
        }
        
        if (nextPageBtn) {
            nextPageBtn.addEventListener('click', function() {
                if (!this.disabled && !isLoading) {
                    const searchTerm = searchInput ? searchInput.value.trim() : '';
                    const filter = timeFilter ? timeFilter.value : 'all';
                    loadConversations(currentPage + 1, filter, searchTerm);
                }
            });
        }
        
        // Event delegation para botones de acción
        document.addEventListener('click', function(e) {
            if (e.target.closest('.view-btn')) {
                e.preventDefault();
                const btn = e.target.closest('.view-btn');
                const userData = btn.dataset.user;
                const content = decodeURIComponent(btn.dataset.content);
                const response = decodeURIComponent(btn.dataset.response);
                const timestamp = btn.dataset.timestamp;
                
                openConversationModal(userData, content, response, timestamp);
            }
            
            if (e.target.closest('.export-btn')) {
                e.preventDefault();
                const btn = e.target.closest('.export-btn');
                const userData = btn.dataset.user;
                exportConversation(userData);
            }
            
            // ✅ NUEVO: Evento para botón de configuración
            if (e.target.closest('.config-btn') || e.target.closest('[data-action="config"]')) {
                e.preventDefault();
                console.log('🔧 Clic en botón de configuración detectado');
                openConfigModal();
            }
            
            // ✅ NUEVO: Cerrar modal al hacer clic fuera
            if (e.target.id === 'configModal') {
                closeConfigModal();
            }
        });
        
        // ✅ VERIFICAR AUTH Y CARGAR DESPUÉS DE UN DELAY
        setTimeout(() => {
            checkAuthAndLoad();
        }, 1000);
    });

    // ✅ FUNCIONES DE MODAL Y EXPORTACIÓN
    function openConversationModal(userData, content, response, timestamp) {
        console.log('👁️ Abriendo modal de conversación para:', userData);
        
        // Buscar el modal correcto del HTML
        const modal = document.getElementById('conversationModal');
        if (!modal) {
            console.error('❌ Modal conversationModal no encontrado');
            // Crear modal dinámicamente si no existe
            createConversationModal();
            return;
        }
        
        // Llenar datos del modal
        const modalUserId = document.getElementById('modal-user-id');
        const modalCreatedAt = document.getElementById('modal-created-at');
        const modalMessages = document.getElementById('modal-messages');
        
        // ✅ MEJORAR EL CONTENIDO DEL MODAL
        if (modalUserId) modalUserId.textContent = userData;
        if (modalCreatedAt) modalCreatedAt.textContent = formatDate(timestamp);
        
        // ✅ MOSTRAR CONVERSACIÓN COMPLETA CON MEJOR FORMATO
        if (modalMessages) {
            modalMessages.innerHTML = `
                <div class="conversation-thread">
                    <!-- MENSAJE DEL USUARIO -->
                    <div class="message user-message" style="margin-bottom: 20px; padding: 15px; background: linear-gradient(135deg, #f0f8ff 0%, #e6f3ff 100%); border-radius: 10px; border-left: 4px solid #007bff; box-shadow: 0 2px 5px rgba(0,0,0,0.1);">
                        <div class="message-header" style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                            <strong style="color: #007bff; display: flex; align-items: center; gap: 8px;">
                                <i class="fas fa-user-circle"></i> ${userData}
                            </strong>
                            <span style="font-size: 0.8em; color: #666; background: rgba(255,255,255,0.7); padding: 2px 8px; border-radius: 10px;">
                                ${formatDate(timestamp)}
                            </span>
                        </div>
                        <div class="message-content" style="line-height: 1.6; color: #333;">
                            ${content}
                        </div>
                    </div>
                    
                    <!-- RESPUESTA DE AVA -->
                    <div class="message bot-message" style="margin-bottom: 20px; padding: 15px; background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%); border-radius: 10px; border-left: 4px solid #28a745; box-shadow: 0 2px 5px rgba(0,0,0,0.1);">
                        <div class="message-header" style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                            <strong style="color: #28a745; display: flex; align-items: center; gap: 8px;">
                                <i class="fas fa-robot"></i> AVA Bot
                            </strong>
                            <span style="font-size: 0.8em; color: #666; background: rgba(255,255,255,0.7); padding: 2px 8px; border-radius: 10px;">
                                ${formatDate(timestamp)}
                            </span>
                        </div>
                        <div class="message-content" style="line-height: 1.6; color: #333;">
                            ${response}
                        </div>
                    </div>
                </div>
                
                <!-- ACCIONES DEL MODAL -->
                <div class="modal-actions" style="margin-top: 25px; text-align: center; border-top: 1px solid #eee; padding-top: 20px;">
                    <button onclick="exportThisConversation('${userData}', '${encodeURIComponent(content)}', '${encodeURIComponent(response)}')" 
                            style="padding: 10px 20px; margin-right: 15px; background: linear-gradient(135deg, #007bff 0%, #0056b3 100%); color: white; border: none; border-radius: 25px; cursor: pointer; font-weight: 500; transition: all 0.3s ease; box-shadow: 0 2px 10px rgba(0,123,255,0.3);"
                            onmouseover="this.style.transform='translateY(-2px)'; this.style.boxShadow='0 4px 15px rgba(0,123,255,0.4)';"
                            onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 2px 10px rgba(0,123,255,0.3)';">
                        <i class="fas fa-download"></i> Exportar Conversación
                    </button>
                    
                    <button onclick="viewFullHistory('${userData}')" 
                            style="padding: 10px 20px; margin-right: 15px; background: linear-gradient(135deg, #6f42c1 0%, #5a2d91 100%); color: white; border: none; border-radius: 25px; cursor: pointer; font-weight: 500; transition: all 0.3s ease; box-shadow: 0 2px 10px rgba(111,66,193,0.3);"
                            onmouseover="this.style.transform='translateY(-2px)'; this.style.boxShadow='0 4px 15px rgba(111,66,193,0.4)';"
                            onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 2px 10px rgba(111,66,193,0.3)';">
                        <i class="fas fa-history"></i> Ver Historial Completo
                    </button>
                    
                    <button onclick="closeConversationModal()" 
                            style="padding: 10px 20px; background: linear-gradient(135deg, #6c757d 0%, #5a6268 100%); color: white; border: none; border-radius: 25px; cursor: pointer; font-weight: 500; transition: all 0.3s ease; box-shadow: 0 2px 10px rgba(108,117,125,0.3);"
                            onmouseover="this.style.transform='translateY(-2px)'; this.style.boxShadow='0 4px 15px rgba(108,117,125,0.4)';"
                            onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 2px 10px rgba(108,117,125,0.3)';">
                        <i class="fas fa-times"></i> Cerrar
                    </button>
                </div>
            `;
        }
        
        // ✅ MOSTRAR EL MODAL CON ANIMACIÓN
        modal.style.display = 'block';
        modal.style.opacity = '0';
        modal.style.transform = 'scale(0.8)';
        
        // Animación de entrada
        setTimeout(() => {
            modal.style.transition = 'all 0.3s ease';
            modal.style.opacity = '1';
            modal.style.transform = 'scale(1)';
        }, 10);
        
        // Prevenir scroll del body
        document.body.style.overflow = 'hidden';
    }

    // ✅ FUNCIÓN PARA CERRAR MODAL CON ANIMACIÓN
    function closeConversationModal() {
        const modal = document.getElementById('conversationModal');
        if (modal) {
            // Animación de salida
            modal.style.transition = 'all 0.3s ease';
            modal.style.opacity = '0';
            modal.style.transform = 'scale(0.8)';
            
            setTimeout(() => {
                modal.style.display = 'none';
                document.body.style.overflow = 'auto'; // Restaurar scroll
            }, 300);
        }
    }

    // ✅ FUNCIÓN PARA EXPORTAR CONVERSACIÓN DESDE MODAL
    function exportThisConversation(userData, encodedContent, encodedResponse) {
        const content = decodeURIComponent(encodedContent);
        const response = decodeURIComponent(encodedResponse);
        
        const conversationText = `
╔══════════════════════════════════════════════════════════════╗
║                    CONVERSACIÓN AVA BOT                      ║
╚══════════════════════════════════════════════════════════════╝

Usuario: ${userData}
Fecha de exportación: ${new Date().toLocaleString('es-ES')}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

👤 MENSAJE DEL USUARIO:
${content}

🤖 RESPUESTA DE AVA:
${response}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Exportado desde AVA Dashboard
Sistema de Gestión de Conversaciones
    `;
        
        const blob = new Blob([conversationText], { type: 'text/plain;charset=utf-8' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `AVA_Conversacion_${userData.replace('@', '_')}_${new Date().toISOString().slice(0,10)}.txt`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
        
        showNotification('✅ Conversación exportada exitosamente', 'success');
    }

    // ✅ FUNCIÓN PARA VER HISTORIAL COMPLETO
    function viewFullHistory(userData) {
        console.log('📚 Abriendo historial completo para:', userData);
        
        // Buscar el rowid de esta conversación para construir el enlace
        const conversations = window.dashboardDebug ? window.dashboardDebug.currentConversations : [];
        let conversationId = null;
        
        // Si tenemos acceso a las conversaciones actuales, buscar el ID
        if (conversations && conversations.length > 0) {
            const userConv = conversations.find(conv => conv.user_id === userData);
            conversationId = userConv ? userConv.rowid : 1;
        } else {
            conversationId = 1; // Fallback
        }
        
        // Cerrar modal actual
        closeConversationModal();
        
        // Navegar a página de detalles completos
        setTimeout(() => {
            window.location.href = `/conversation/${conversationId}`;
        }, 300);
    }

    // ✅ FUNCIÓN PARA CREAR MODAL SI NO EXISTE
    function createConversationModal() {
        console.log('🏗️ Creando modal de conversación dinámicamente...');
        
        const modalHtml = `
            <div id="conversationModal" class="modal" style="display: none; position: fixed; z-index: 1000; left: 0; top: 0; width: 100%; height: 100%; overflow: auto; background-color: rgba(0,0,0,0.5);">
                <div class="modal-content" style="background-color: #fefefe; margin: 3% auto; padding: 0; border: none; width: 90%; max-width: 800px; border-radius: 15px; box-shadow: 0 10px 30px rgba(0,0,0,0.3);">
                    <div class="modal-header" style="padding: 25px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border-radius: 15px 15px 0 0; position: relative;">
                        <h3 style="margin: 0; font-size: 1.5em; display: flex; align-items: center; gap: 10px;">
                            <i class="fas fa-comments"></i> Detalles de Conversación
                        </h3>
                        <span class="close-modal" onclick="closeConversationModal()" style="position: absolute; top: 15px; right: 20px; color: white; font-size: 24px; font-weight: bold; cursor: pointer; width: 30px; height: 30px; display: flex; align-items: center; justify-content: center; border-radius: 50%; transition: all 0.3s ease;"
                              onmouseover="this.style.backgroundColor='rgba(255,255,255,0.2)'"
                              onmouseout="this.style.backgroundColor='transparent'">&times;</span>
                        
                        <div style="margin-top: 15px; display: flex; gap: 20px; font-size: 0.9em; opacity: 0.9;">
                            <div><strong>Usuario:</strong> <span id="modal-user-id">-</span></div>
                            <div><strong>Fecha:</strong> <span id="modal-created-at">-</span></div>
                        </div>
                    </div>
                    
                    <div class="modal-body" style="padding: 30px; max-height: 60vh; overflow-y: auto;">
                        <div id="modal-messages">
                            <!-- Contenido dinámico aquí -->
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        // Agregar al body
        document.body.insertAdjacentHTML('beforeend', modalHtml);
        
        // Mostrar el modal
        setTimeout(() => {
            openConversationModal(arguments[0], arguments[1], arguments[2], arguments[3]);
        }, 100);
    }

    // ✅ FUNCIÓN PARA MOSTRAR NOTIFICACIONES
    function showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 15px 25px;
            border-radius: 10px;
            color: white;
            font-weight: 500;
            z-index: 10000;
            animation: slideInNotification 0.4s ease;
            box-shadow: 0 4px 15px rgba(0,0,0,0.2);
            max-width: 400px;
            background: ${type === 'success' ? 'linear-gradient(135deg, #28a745 0%, #20c997 100%)' : 
                         type === 'error' ? 'linear-gradient(135deg, #dc3545 0%, #e91e63 100%)' : 
                         'linear-gradient(135deg, #007bff 0%, #6610f2 100)'};
        `;
        notification.innerHTML = `
            <div style="display: flex; align-items: center; gap: 10px;">
                <i class="fas fa-${type === 'success' ? 'check-circle' : type === 'error' ? 'exclamation-circle' : 'info-circle'}"></i>
                <span>${message}</span>
            </div>
        `;
        
        document.body.appendChild(notification);
        
        // Auto-remover después de 4 segundos
        setTimeout(() => {
            notification.style.animation = 'slideOutNotification 0.4s ease';
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.remove();
                }
            }, 400);
        }, 4000);
    }

    // ✅ CSS PARA ANIMACIONES DE NOTIFICACIÓN
    const notificationStyle = document.createElement('style');
    notificationStyle.textContent = `
        @keyframes slideInNotification {
            from { transform: translateX(100%); opacity: 0; }
            to { transform: translateX(0); opacity: 1; }
        }
        
        @keyframes slideOutNotification {
            from { transform: translateX(0); opacity: 1; }
            to { transform: translateX(100%); opacity: 0; }
        }
    `;
    document.head.appendChild(notificationStyle);
}

// ✅ CSS PARA SPINNER
const style = document.createElement('style');
style.textContent = `
    @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }
    .spinner {
        border: 4px solid #f3f3f3;
        border-top: 4px solid #3498db;
        border-radius: 50%;
        width: 30px;
        height: 30px;
        animation: spin 1s linear infinite;
        margin: 0 auto;
    }
`;
document.head.appendChild(style);

// En el console del navegador:
document.addEventListener('click', function(e) {
    console.log('Clic detectado en:', e.target);
    console.log('Classes:', e.target.className);
    console.log('Data attributes:', e.target.dataset);
}, true);