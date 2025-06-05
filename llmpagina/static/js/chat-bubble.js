// ✅ CHAT BUBBLE SIMPLIFICADO Y FUNCIONAL
document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 Inicializando Chat Bubble...');
    
    class ChatBubble {
        constructor() {
            this.isOpen = false;
            this.isTyping = false;
            this.init();
        }

        init() {
            this.createChatBubble();
            this.attachEventListeners();
        }

        createChatBubble() {
            console.log('🔧 Creando elementos de chat bubble...');
            
            // ✅ VERIFICAR SI YA EXISTE
            if (document.querySelector('.chat-assistant-container')) {
                console.log('⚠️ Chat bubble ya existe');
                return;
            }
            
            // ✅ HTML CON BOTÓN DE SUBIR IMAGEN
            const chatContainer = document.createElement('div');
            chatContainer.className = 'chat-assistant-container';
            chatContainer.innerHTML = `
                <div class="chat-bubble-button" id="chatBubble">
                    <img src="/static/images/ava_agent_woman.png" alt="AVA" onerror="this.style.display='none'; this.parentElement.innerHTML='<div style=color:#1c1c1c;font-weight:bold;font-size:16px;>AVA</div>';">
                </div>

                <div class="chat-popup" id="chatWindow">
                    <div class="chat-header">
                        <h3>AVA Assistant</h3>
                        <button class="close-chat" id="closeBtn">×</button>
                    </div>

                    <div class="chat-messages" id="chatMessages">
                        <div class="message assistant">
                            <div class="message-content">
                                ¡Hola! Soy AVA, tu asistente virtual. ¿En qué puedo ayudarte?
                            </div>
                        </div>
                    </div>

                    <div class="chat-input">
                        <input type="file" id="imageInput" accept="image/*" style="display: none;">
                        <button class="upload-btn" id="uploadBtn" type="button" title="Subir imagen">
                            <i class="fas fa-image"></i>
                        </button>
                        <input type="text" id="chatInput" placeholder="Escribe tu mensaje..." autocomplete="off">
                        <button id="sendButton" type="button">
                            <i class="fas fa-paper-plane"></i>
                        </button>
                    </div>
                </div>
            `;

            document.body.appendChild(chatContainer);
            console.log('✅ Chat bubble creado');
        }

        attachEventListeners() {
            console.log('🔧 Agregando event listeners...');
            
            const chatBubble = document.getElementById('chatBubble');
            const closeBtn = document.getElementById('closeBtn');
            const sendButton = document.getElementById('sendButton');
            const chatInput = document.getElementById('chatInput');
            const uploadBtn = document.getElementById('uploadBtn');
            const imageInput = document.getElementById('imageInput');

            if (!chatBubble || !closeBtn || !sendButton || !chatInput || !uploadBtn || !imageInput) {
                console.error('❌ Algunos elementos no se encontraron');
                return;
            }

            // ✅ EVENTOS BÁSICOS
            chatBubble.addEventListener('click', () => this.toggleChat());
            closeBtn.addEventListener('click', () => this.closeChat());
            sendButton.addEventListener('click', () => this.sendMessage());
            chatInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    this.sendMessage();
                }
            });

            // ✅ EVENTOS PARA BOTÓN DE SUBIR IMAGEN
            uploadBtn.addEventListener('click', () => {
                imageInput.click();
            });

            imageInput.addEventListener('change', (e) => {
                if (e.target.files && e.target.files[0]) {
                    this.handleImageUpload(e.target.files[0]);
                }
            });

            console.log('✅ Event listeners agregados');
        }

        toggleChat() {
            const chatWindow = document.getElementById('chatWindow');
            if (!chatWindow) return;

            if (this.isOpen) {
                this.closeChat();
            } else {
                chatWindow.style.display = 'flex';
                setTimeout(() => chatWindow.classList.add('active'), 10);
                this.isOpen = true;
                
                setTimeout(() => {
                    const chatInput = document.getElementById('chatInput');
                    if (chatInput) chatInput.focus();
                }, 200);
            }
        }

        closeChat() {
            const chatWindow = document.getElementById('chatWindow');
            if (!chatWindow) return;

            chatWindow.classList.remove('active');
            setTimeout(() => {
                chatWindow.style.display = 'none';
            }, 300);
            this.isOpen = false;
        }

        // ✅ FUNCIÓN sendMessage CORREGIDA Y SIMPLIFICADA
        async sendMessage() {
            console.log('🚀 === ENVIANDO MENSAJE ===');
            
            const chatInput = document.getElementById('chatInput');
            if (!chatInput) {
                console.error('❌ chatInput no encontrado');
                return;
            }
            
            const message = chatInput.value.trim();
            console.log('📝 Mensaje:', message);
            
            if (!message || this.isTyping) {
                console.log('⚠️ Mensaje vacío o ya enviando');
                return;
            }
            
            // ✅ PREPARAR ENVÍO
            chatInput.value = '';
            this.addMessage(message, 'user');
            this.showTypingIndicator();
            this.isTyping = true;
            
            try {
                console.log('📤 Enviando al backend...');
                
                const response = await fetch('/api/chat/message', {
                    method: 'POST',
                    headers: { 
                        'Content-Type': 'application/json',
                        'Accept': 'application/json'
                    },
                    body: JSON.stringify({
                        message: message,
                        unlimited: false
                    })
                });
                
                console.log('📥 Fetch completado, status:', response.status);
                
                // ✅ OBTENER TEXTO RAW PRIMERO PARA DEBUG
                const rawText = await response.text();
                console.log('📄 RESPUESTA RAW DEL SERVIDOR:', rawText);
                
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }
                
                // ✅ PARSEAR JSON DESPUÉS DEL DEBUG
                let data;
                try {
                    data = JSON.parse(rawText);
                } catch (parseError) {
                    console.error('❌ Error parseando JSON:', parseError);
                    console.error('📄 Contenido que falló:', rawText);
                    throw new Error('Respuesta del servidor no es JSON válido');
                }
                
                console.log('✅ JSON parseado exitosamente:');
                console.log('📊 DATA COMPLETA:', JSON.stringify(data, null, 2));
                
                // ✅ DEBUG ESPECÍFICO DE CAMPOS DE IMAGEN
                console.log('🔍 DEBUG CAMPOS DE IMAGEN:');
                console.log('   success:', data.success, typeof data.success);
                console.log('   image_generated:', data.image_generated, typeof data.image_generated);
                console.log('   image_url:', data.image_url, typeof data.image_url);
                console.log('   image_filename:', data.image_filename, typeof data.image_filename);
                console.log('   response:', data.response ? data.response.substring(0, 100) + '...' : 'undefined');
                
                // Ocultar typing indicator
                this.hideTypingIndicator();
                this.isTyping = false;
                
                // ✅ PROCESAR RESPUESTA CON DEBUG DETALLADO
                if (data.success === true) {
                    console.log('✅ Respuesta exitosa detectada');
                    
                    let responseText = data.response || 'Respuesta recibida sin contenido';
                    console.log('📝 Texto de respuesta:', responseText);
                    
                    // ✅ VERIFICAR IMAGEN CON MÚLTIPLES CONDICIONES
                    const hasImageGenerated = data.image_generated === true;
                    const hasImageUrl = data.image_url && data.image_url.trim() !== '';
                    const hasImageFilename = data.image_filename && data.image_filename.trim() !== '';
                    
                    console.log('🔍 VERIFICACIÓN DE IMAGEN:');
                    console.log('   hasImageGenerated:', hasImageGenerated);
                    console.log('   hasImageUrl:', hasImageUrl);
                    console.log('   hasImageFilename:', hasImageFilename);
                    
                    if (hasImageGenerated && hasImageUrl && hasImageFilename) {
                        console.log('🖼️ ¡IMAGEN DETECTADA EN RESPUESTA!');
                        console.log('   📷 Filename:', data.image_filename);
                        console.log('   🔗 URL:', data.image_url);
                        console.log('   📝 Texto:', responseText);
                        
                        // ✅ AGREGAR MENSAJE CON IMAGEN
                        console.log('🎯 Llamando a addMessageWithImage...');
                        this.addMessageWithImage(responseText, data.image_url, data.image_filename);
                        console.log('✅ addMessageWithImage completado');
                        
                    } else {
                        console.log('📝 No hay imagen válida, agregando mensaje de texto normal');
                        console.log('📊 Razones:');
                        if (!hasImageGenerated) console.log('   - image_generated no es true');
                        if (!hasImageUrl) console.log('   - image_url vacío o inválido');
                        if (!hasImageFilename) console.log('   - image_filename vacío o inválido');
                        
                        this.addMessage(responseText, 'assistant');
                    }
                    
                    // Actualizar conversation_id si viene
                    if (data.conversation_id) {
                        this.conversationId = data.conversation_id;
                    }
                    
                } else {
                    console.error('❌ Respuesta no exitosa del servidor:', data);
                    const errorMsg = data.response || data.error || 'Error desconocido del servidor';
                    this.addMessage(`❌ ${errorMsg}`, 'assistant');
                }
                
            } catch (error) {
                console.error('❌ Error en sendMessage:', error);
                console.error('📋 Stack trace:', error.stack);
                
                this.hideTypingIndicator();
                this.isTyping = false;
                
                let errorMessage = '🔌 Error de conexión.';
                if (error.message) {
                    errorMessage += ` Detalle: ${error.message}`;
                }
                this.addMessage(errorMessage, 'assistant');
            }
        }

        // 🔥 ACTUALIZAR FUNCIÓN handleImageUpload
        async handleImageUpload(file) {
            console.log('📸 Imagen seleccionada:', file.name);
            
            // Validar tipo de archivo
            if (!file.type.startsWith('image/')) {
                this.addMessage('❌ Por favor selecciona solo archivos de imagen.', 'assistant');
                return;
            }
            
            // Validar tamaño (max 5MB)
            if (file.size > 5 * 1024 * 1024) {
                this.addMessage('❌ La imagen es muy grande. Máximo 5MB.', 'assistant');
                return;
            }
            
            try {
                // 🔥 MOSTRAR PLACEHOLDER MIENTRAS SE SUBE
                this.addMessage(`📷 Enviando imagen: ${file.name}...`, 'user');
                
                // Mostrar indicador de procesamiento
                this.showTypingIndicator();
                this.isTyping = true;
                
                // 🔥 ENVIAR DIRECTAMENTE AL BACKEND SIN PREVIEW
                await this.sendImageToBackend(file);
                
            } catch (error) {
                console.error('❌ Error procesando imagen:', error);
                this.addMessage('❌ Error procesando la imagen.', 'assistant');
            }
        }

        // 🔥 ACTUALIZAR sendImageToBackend PARA USAR NOMBRE CORRECTO
        async sendImageToBackend(file) {
            console.log('📤 Enviando imagen al backend para análisis...');

            try {
                // Convertir archivo a FormData
                const formData = new FormData();
                formData.append('image', file);
                // 🔥 CAMBIAR: Enviar mensaje genérico, no el nombre original
                formData.append('message', 'Analiza esta imagen que acabo de subir');
                formData.append('unlimited', 'false');
                
                console.log('📋 FormData preparado:', {
                    original_filename: file.name,
                    size: file.size,
                    type: file.type
                });
                
                // Enviar al endpoint
                const response = await fetch('/api/chat/image-analysis', {
                    method: 'POST',
                    body: formData
                });
                
                console.log('📥 Respuesta del backend:', response.status);
                
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }
                
                const rawText = await response.text();
                console.log('📄 Respuesta RAW del backend:', rawText);
                
                const data = JSON.parse(rawText);
                console.log('📊 Datos parseados:', data);
                
                // Ocultar typing indicator
                this.hideTypingIndicator();
                this.isTyping = false;
                
                // Procesar respuesta del análisis
                if (data.success) {
                    // 🔥 USAR EL NOMBRE ÚNICO GENERADO POR EL BACKEND
                    if (data.user_image_filename && data.user_image_path) {
                        console.log('📸 Imagen guardada en servidor:');
                        console.log('   Nombre original:', file.name);
                        console.log('   Nombre único:', data.user_image_filename);
                        console.log('   Ruta servidor:', data.user_image_path);
                        
                        const userImageUrl = `/api/chat/image/${data.user_image_filename}`;
                        this.addUserImageFromServer(data.user_image_filename, userImageUrl, file.name);
                    }
                    
                    const responseText = data.response || 'Análisis completado';
                    
                    // Si AVA generó una nueva imagen como respuesta
                    if (data.image_generated && data.image_url && data.image_filename) {
                        this.addMessageWithImage(responseText, data.image_url, data.image_filename);
                    } else {
                        this.addMessage(responseText, 'assistant');
                    }
                } else {
                    this.addMessage(`❌ Error analizando imagen: ${data.response || data.error}`, 'assistant');
                }
                
            } catch (error) {
                console.error('❌ Error enviando imagen al backend:', error);
                
                this.hideTypingIndicator();
                this.isTyping = false;
                
                this.addMessage(`❌ Error procesando imagen: ${error.message}`, 'assistant');
            }
        }

        // 🔥 ACTUALIZAR FUNCIÓN addUserImageFromServer PARA MOSTRAR AMBOS NOMBRES
        addUserImageFromServer(uniqueFilename, serverImageUrl, originalFilename = null) {
            console.log('📷 Agregando imagen del usuario desde servidor:', serverImageUrl);
            
            const chatMessages = document.getElementById('chatMessages');
            if (!chatMessages) return;
            
            // 🔥 MOSTRAR TANTO EL NOMBRE ORIGINAL COMO EL ÚNICO
            const displayName = originalFilename ? `${originalFilename} (${uniqueFilename})` : uniqueFilename;
            
            const messageElement = document.createElement('div');
            messageElement.className = 'message user message-with-image';
            messageElement.innerHTML = `
                <div class="message-content">
                    📷 Imagen enviada: ${originalFilename || uniqueFilename}
                    ${originalFilename ? `<br><small style="opacity: 0.7;">Guardada como: ${uniqueFilename}</small>` : ''}
                </div>
                <div class="image-container">
                    <img src="${serverImageUrl}" 
                         alt="${this.escapeHtml(displayName)}" 
                         onload="console.log('✅ Imagen del usuario cargada desde servidor:', '${uniqueFilename}');"
                         onerror="this.onerror=null; this.style.display='none'; this.parentElement.innerHTML='<div style=&quot;color: #dc3545; padding: 10px; text-align: center; border: 1px dashed #dc3545; border-radius: 8px;&quot;>❌ Error cargando imagen<br><small>${uniqueFilename}</small></div>';"
                         onclick="window.chatBubble.openImageModal('${serverImageUrl}', '${this.escapeHtml(displayName)}')">
            
            <div class="image-controls">
                <button class="control-btn download" 
                        onclick="window.chatBubble.downloadImage('${serverImageUrl}', '${this.escapeHtml(originalFilename || uniqueFilename)}'); event.stopPropagation();" 
                        title="Descargar imagen">
                    <i class="fas fa-download"></i>
                </button>
                
                <button class="control-btn expand" 
                        onclick="window.chatBubble.openImageModal('${serverImageUrl}', '${this.escapeHtml(displayName)}'); event.stopPropagation();" 
                        title="Ver en pantalla completa">
                    <i class="fas fa-expand"></i>
                </button>
            </div>
            
            <div class="image-info">
                <i class="fas fa-image" style="margin-right: 4px;"></i>
                ${displayName.length > 30 ? displayName.substring(0, 30) + '...' : displayName}
            </div>
        </div>
    `;
    
    chatMessages.appendChild(messageElement);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    
    console.log('✅ Imagen del usuario agregada desde servidor con nombre único:', uniqueFilename);
}

        addMessage(message, sender) {
            console.log('💬 Agregando mensaje al chat:', { message, sender });
            
            const chatMessages = document.getElementById('chatMessages');
            if (!chatMessages) {
                console.error('❌ chatMessages no encontrado');
                return;
            }
            
            // Crear elemento de mensaje
            const messageElement = document.createElement('div');
            messageElement.className = `message ${sender}`;
            messageElement.innerHTML = `
                <div class="message-content">
                    ${this.escapeHtml(message)}
                </div>
            `;
            
            // Agregar al contenedor de mensajes
            chatMessages.appendChild(messageElement);
            chatMessages.scrollTop = chatMessages.scrollHeight;
            
            console.log('✅ Mensaje agregado:', message);
        }

        // ✅ FUNCIÓN addMessageWithImage ACTUALIZADA PARA MISMO ANCHO QUE TEXTO
        addMessageWithImage(message, imageUrl, filename) {
            console.log('🖼️ Agregando mensaje con imagen al chat:', { message, imageUrl, filename });
            
            const chatMessages = document.getElementById('chatMessages');
            if (!chatMessages) {
                console.error('❌ chatMessages no encontrado');
                return;
            }
            
            // ✅ CREAR ELEMENTO CON IMAGEN DEL MISMO ANCHO QUE EL TEXTO
            const messageElement = document.createElement('div');
            messageElement.className = 'message assistant message-with-image';
            messageElement.innerHTML = `
                <div class="message-content">
                    ${this.escapeHtml(message)}
                </div>
                <div class="image-container">
                    <img src="${this.escapeHtml(imageUrl)}" 
                         alt="${this.escapeHtml(filename)}" 
                         onload="console.log('✅ Imagen cargada:', '${filename}');"
                         onerror="this.onerror=null; this.style.display='none'; this.parentElement.innerHTML='<div style=&quot;color: #dc3545; padding: 10px; text-align: center; border: 1px dashed #dc3545; border-radius: 8px;&quot;>❌ Error cargando imagen<br><small>${filename}</small></div>';"
                         onclick="window.chatBubble.openImageModal('${this.escapeHtml(imageUrl)}', '${this.escapeHtml(filename)}')">
                    
                    <!-- ✅ CONTROLES CON CLASES CSS -->
                    <div class="image-controls">
                        <button class="control-btn download" 
                                onclick="window.chatBubble.downloadImage('${this.escapeHtml(imageUrl)}', '${this.escapeHtml(filename)}'); event.stopPropagation();" 
                                title="Descargar imagen">
                            <i class="fas fa-download"></i>
                        </button>
                        
                        <button class="control-btn expand" 
                                onclick="window.chatBubble.openImageModal('${this.escapeHtml(imageUrl)}', '${this.escapeHtml(filename)}'); event.stopPropagation();" 
                                title="Ver en pantalla completa">
                            <i class="fas fa-expand"></i>
                        </button>
                    </div>
                    
                    <!-- ✅ INFORMACIÓN DEL ARCHIVO -->
                    <div class="image-info">
                        <i class="fas fa-image" style="margin-right: 4px;"></i>
                        ${filename.length > 30 ? filename.substring(0, 30) + '...' : filename}
                    </div>
                </div>
            `;
            
            // Agregar al contenedor de mensajes
            chatMessages.appendChild(messageElement);
            chatMessages.scrollTop = chatMessages.scrollHeight;
            
            console.log('✅ Mensaje con imagen del mismo ancho que texto agregado');
        }

        // ✅ AGREGAR FUNCIÓN PARA MODAL DE IMAGEN COMPLETA
        openImageModal(imageUrl, filename) {
            console.log('🖼️ Abriendo imagen en modal:', imageUrl);
            
            // Eliminar modal existente si hay uno
            const existingModal = document.querySelector('.image-modal-overlay');
            if (existingModal) {
                existingModal.remove();
            }
            
            // Crear modal
            const modal = document.createElement('div');
            modal.className = 'image-modal-overlay';
            modal.style.cssText = `
                position: fixed;
                top: 0;
                left: 0;
                width: 100vw;
                height: 100vh;
                background: rgba(0, 0, 0, 0.9);
                display: flex;
                justify-content: center;
                align-items: center;
                z-index: 10000;
                backdrop-filter: blur(5px);
            `;
            
            modal.innerHTML = `
                <div style="position: relative; max-width: 90%; max-height: 90%; text-align: center;">
                    <button onclick="this.parentElement.parentElement.remove()" 
                            style="position: absolute; top: -40px; right: 0; background: #dc3545; color: white; border: none; width: 35px; height: 35px; border-radius: 50%; cursor: pointer; font-size: 18px; display: flex; align-items: center; justify-content: center;"
                            title="Cerrar">
                        ×
                    </button>
                    <img src="${imageUrl}" 
                         alt="${filename}"
                         style="max-width: 100%; max-height: 100%; border-radius: 12px; box-shadow: 0 8px 32px rgba(0,0,0,0.5);"
                         onload="console.log('✅ Imagen modal cargada');">
                    <div style="position: absolute; bottom: -60px; left: 50%; transform: translateX(-50%); color: white; background: rgba(0,0,0,0.8); padding: 10px 20px; border-radius: 8px; min-width: 200px;">
                        <div style="font-weight: bold; margin-bottom: 8px;">${filename}</div>
                        <button onclick="window.chatBubble.downloadImage('${imageUrl}', '${filename}')" 
                                style="background: #28a745; color: white; border: none; padding: 8px 16px; border-radius: 6px; cursor: pointer; margin-right: 10px;">
                            <i class="fas fa-download"></i> Descargar
                        </button>
                    </div>
                </div>
            `;
            
            // Cerrar al hacer clic fuera
            modal.addEventListener('click', (e) => {
                if (e.target === modal) {
                    modal.remove();
                }
            });
            
            // Cerrar con Escape
            const handleEscape = (e) => {
                if (e.key === 'Escape') {
                    modal.remove();
                    document.removeEventListener('keydown', handleEscape);
                }
            };
            document.addEventListener('keydown', handleEscape);
            
            document.body.appendChild(modal);
        }

        // ✅ AGREGAR FUNCIÓN PARA DESCARGAR IMAGEN
        downloadImage(imageUrl, filename) {
            console.log('📥 Descargando imagen:', imageUrl);
            
            try {
                const link = document.createElement('a');
                link.href = imageUrl;
                link.download = filename || `imagen_${Date.now()}.png`;
                link.target = '_blank';
                link.style.display = 'none';
                
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
                
                console.log('✅ Descarga iniciada');
            } catch (error) {
                console.error('❌ Error descargando:', error);
                alert('Error al descargar la imagen. Intenta clic derecho > Guardar imagen');
            }
        }
        
        showTypingIndicator() {
            console.log('⏳ Mostrando indicador de escritura...');
            
            const chatMessages = document.getElementById('chatMessages');
            if (!chatMessages) {
                console.error('❌ chatMessages no encontrado');
                return;
            }
            
            // Crear elemento de "escribiendo..."
            const typingElement = document.createElement('div');
            typingElement.className = 'message assistant typing-indicator';
            typingElement.innerHTML = `
                <div class="message-content">
                    <i class="fas fa-spinner fa-spin"></i> Escribiendo...
                </div>
            `;
            
            // Agregar al contenedor de mensajes
            chatMessages.appendChild(typingElement);
            chatMessages.scrollTop = chatMessages.scrollHeight;
            
            console.log('✅ Indicador de escritura mostrado');
        }

        hideTypingIndicator() {
            console.log('🚫 Ocultando indicador de escritura...');
            
            const typingElements = document.querySelectorAll('.typing-indicator');
            typingElements.forEach(el => el.remove());
            
            console.log('✅ Indicador de escritura ocultado');
        }

        escapeHtml(unsafe) {
            return unsafe
                .replace(/&/g, "&amp;")
                .replace(/</g, "&lt;")
                .replace(/>/g, "&gt;")
                .replace(/"/g, "&quot;")
                .replace(/'/g, "&#039;");
        }

    } // ✅ FIN DE LA CLASE ChatBubble

    // Iniciar la clase ChatBubble
    window.chatBubble = new ChatBubble();
});

// ✅ FUNCIONES DE PRUEBA FUERA DE LA CLASE
window.testBackendResponse = async function() {
    console.log('🧪 === PRUEBA DIRECTA DEL BACKEND ===');
    
    try {
        const response = await fetch('/api/chat/message', {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            body: JSON.stringify({
                message: 'genera una imagen de prueba',
                unlimited: false
            })
        });
        
        const rawText = await response.text();
        console.log('📄 Respuesta RAW:', rawText);
        
        const data = JSON.parse(rawText);
        console.log('📊 Datos parseados:', data);
        
        if (data.image_generated) {
            console.log('🖼️ Backend dice que hay imagen:');
            console.log('   URL:', data.image_url);
            console.log('   Filename:', data.image_filename);
            
            // Probar si la imagen existe
            const imgTest = new Image();
            imgTest.onload = () => console.log('✅ Imagen accesible desde:', data.image_url);
            imgTest.onerror = () => console.log('❌ Imagen NO accesible desde:', data.image_url);
            imgTest.src = data.image_url;
        }
        
    } catch (error) {
        console.error('❌ Error en prueba:', error);
    }
    
    console.log('🧪 === FIN PRUEBA ===');
};

window.testImageVisualization = function() {
    console.log('🧪 === PRUEBA DE VISUALIZACIÓN ===');
    
    if (!window.chatBubble) {
        console.error('❌ ChatBubble no disponible');
        return;
    }
    
    // Usar la imagen que sabemos que se generó
    const testImageUrl = '/api/chat/image/ava_generated_20250604_044243.png';
    const testFilename = 'ava_generated_20250604_044243.png';
    const testText = 'Esta es una imagen de prueba del retrato romántico que generé.';
    
    console.log('🎯 Probando visualización con:');
    console.log('   URL:', testImageUrl);
    console.log('   Filename:', testFilename);
    
    window.chatBubble.addMessageWithImage(testText, testImageUrl, testFilename);
    
    console.log('✅ Función de visualización ejecutada');
    console.log('🧪 === FIN PRUEBA VISUALIZACIÓN ===');
};