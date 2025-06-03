// Funcionalidad para la burbuja de chat del agente virtual
document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 Inicializando Chat Bubble...');
    
    class ChatBubble {
        constructor() {
            this.isOpen = false;
            this.isAvaOnline = false;
            this.conversationId = null;
            this.isTyping = false;
            this.agentStatus = 'checking';
            this.init();
            this.checkAvaStatus();
            
            // Verificar estado cada 30 segundos
            setInterval(() => this.checkAvaStatus(), 30000);
        }

        init() {
            this.createChatBubble();
            this.attachEventListeners();
        }

        createChatBubble() {
            console.log('🔧 Creando elementos de chat bubble...');
            
            // ✅ VERIFICAR SI YA EXISTE PARA EVITAR DUPLICADOS
            if (document.querySelector('.chat-assistant-container')) {
                console.log('⚠️ Chat bubble ya existe, no creando duplicado');
                return;
            }
            
            // ✅ CREAR EL HTML COMPLETO DE LA BURBUJA
            const chatContainer = document.createElement('div');
            chatContainer.className = 'chat-assistant-container';
            chatContainer.innerHTML = `
                <!-- Botón flotante -->
                <div class="chat-bubble-button" id="chatBubble">
                    <img src="/static/images/ava_agent_woman.png" alt="AVA" onerror="this.style.display='none'; this.parentElement.innerHTML='<div style=&quot;color: #1c1c1c; font-weight: bold; font-size: 16px;&quot;>AVA</div>';">
                </div>

                <!-- Ventana de chat -->
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
                        <input type="text" id="chatInput" placeholder="Escribe tu mensaje..." autocomplete="off">
                        <button id="sendButton" type="button">
                            <i class="fas fa-paper-plane"></i>
                        </button>
                    </div>
                </div>
            `;

            // Agregar al final del body
            document.body.appendChild(chatContainer);
            console.log('✅ Chat bubble HTML creado y agregado al DOM');
        }

        attachEventListeners() {
            console.log('🔧 Agregando event listeners...');
            
            const chatBubble = document.getElementById('chatBubble');
            const chatWindow = document.getElementById('chatWindow');
            const closeBtn = document.getElementById('closeBtn');
            const sendButton = document.getElementById('sendButton');
            const chatInput = document.getElementById('chatInput');

            if (!chatBubble || !chatWindow || !closeBtn || !sendButton || !chatInput) {
                console.error('❌ No se encontraron todos los elementos necesarios');
                return;
            }

            // ✅ TOGGLE CHAT
            chatBubble.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                console.log('📱 Click en bubble detectado');
                this.toggleChat();
            });

            // ✅ CERRAR CHAT
            closeBtn.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                console.log('❌ Click en cerrar detectado');
                this.closeChat();
            });

            // ✅ ENVIAR MENSAJE
            sendButton.addEventListener('click', (e) => {
                e.preventDefault();
                console.log('📤 Click en sendButton detectado');
                this.sendMessage();
            });

            chatInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    console.log('↩️ Enter presionado');
                    this.sendMessage();
                }
            });

            // ✅ CERRAR AL HACER CLIC FUERA
            document.addEventListener('click', (e) => {
                const chatContainer = document.querySelector('.chat-assistant-container');
                if (chatContainer && !chatContainer.contains(e.target) && this.isOpen) {
                    this.closeChat();
                }
            });

            console.log('✅ Event listeners agregados correctamente');
        }

        async checkAvaStatus() {
            try {
                console.log('🔍 Verificando estado de AVA...');
                const response = await fetch('/api/chat/status');
                const data = await response.json();
                this.isAvaOnline = data.ava_status === 'running';
                console.log('📊 Estado AVA:', this.isAvaOnline ? 'Online' : 'Offline', data);
            } catch (error) {
                console.error('❌ Error verificando estado de AVA:', error);
                this.isAvaOnline = false;
            }
        }

        toggleChat() {
            console.log('🔄 Toggling chat, estado actual:', this.isOpen);
            
            const chatWindow = document.getElementById('chatWindow');
            
            if (!chatWindow) {
                console.error('❌ chatWindow no encontrado');
                return;
            }

            if (this.isOpen) {
                this.closeChat();
            } else {
                console.log('📱 Abriendo chat...');
                chatWindow.style.display = 'flex';
                
                // Pequeño delay para que la transición se vea bien
                setTimeout(() => {
                    chatWindow.classList.add('active');
                }, 10);
                
                this.isOpen = true;
                
                // Enfocar input después de abrir
                setTimeout(() => {
                    const chatInput = document.getElementById('chatInput');
                    if (chatInput) {
                        chatInput.focus();
                    }
                }, 200);
                
                console.log('✅ Chat abierto');
            }
        }

        closeChat() {
            console.log('❌ Cerrando chat...');
            
            const chatWindow = document.getElementById('chatWindow');
            
            if (!chatWindow) {
                console.error('❌ chatWindow no encontrado');
                return;
            }

            chatWindow.classList.remove('active');
            
            // Delay para la animación antes de ocultar
            setTimeout(() => {
                chatWindow.style.display = 'none';
            }, 300);
            
            this.isOpen = false;
            console.log('✅ Chat cerrado');
        }

        // ✅ FUNCIÓN sendMessage COMPLETA
        async sendMessage() {
            console.log('🚀 sendMessage() iniciado');
            
            const chatInput = document.getElementById('chatInput');
            if (!chatInput) {
                console.error('❌ chatInput no encontrado');
                return;
            }
            
            const message = chatInput.value.trim();
            console.log('📝 Mensaje extraído:', message);
            
            if (!message) {
                console.log('⚠️ Mensaje vacío, abortando');
                return;
            }
            
            if (this.isTyping) {
                console.log('⚠️ Ya está enviando mensaje, abortando');
                return;
            }
            
            console.log('📤 Preparando envío de mensaje:', message);
            
            // Limpiar input INMEDIATAMENTE
            chatInput.value = '';
            console.log('🧹 Input limpiado');
            
            // Agregar mensaje del usuario al chat
            this.addMessage(message, 'user');
            console.log('✅ Mensaje de usuario agregado al chat');
            
            // Activar modo typing
            this.showTypingIndicator();
            this.isTyping = true;
            console.log('⏳ Indicador de typing activado');
            
            try {
                // ✅ PREPARAR DATOS DE LA PETICIÓN
                const requestData = {
                    message: message,
                    conversation_id: this.conversationId || null
                };
                
                console.log('📦 Datos preparados para envío:', requestData);
                console.log('🌐 URL destino: /api/chat/message');
                
                // ✅ REALIZAR PETICIÓN FETCH
                console.log('🔄 Iniciando fetch...');
                
                const response = await fetch('/api/chat/message', {
                    method: 'POST',
                    headers: { 
                        'Content-Type': 'application/json',
                        'Accept': 'application/json'
                    },
                    body: JSON.stringify(requestData)
                });
                
                console.log('📥 Fetch completado, analizando respuesta...');
                console.log('📊 Response status:', response.status);
                console.log('📊 Response statusText:', response.statusText);
                console.log('📊 Response headers:', Object.fromEntries(response.headers.entries()));
                
                // ✅ VERIFICAR STATUS DE RESPUESTA
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }
                
                // ✅ OBTENER TEXTO CRUDO PARA DEBUG
                const responseText = await response.text();
                console.log('📄 Response text crudo:', responseText);
                console.log('📏 Longitud de respuesta:', responseText.length);
                
                // ✅ PARSEAR JSON
                let data;
                try {
                    data = JSON.parse(responseText);
                    console.log('✅ JSON parseado exitosamente:', data);
                } catch (parseError) {
                    console.error('❌ Error parseando JSON:', parseError);
                    console.error('📄 Texto que falló:', responseText.substring(0, 500));
                    throw new Error('Respuesta del servidor no es JSON válido');
                }
                
                // ✅ OCULTAR TYPING INDICATOR
                this.hideTypingIndicator();
                this.isTyping = false;
                console.log('⏹️ Typing indicator ocultado');
                
                // ✅ PROCESAR RESPUESTA
                console.log('🔍 Procesando respuesta del servidor...');
                console.log('📊 data.success:', data.success);
                console.log('📊 data.response:', data.response);
                console.log('📊 data.image_generated:', data.image_generated);
                
                if (data.success === true) {
                    console.log('✅ Respuesta exitosa detectada');
                    
                    let responseText = '';
                    let hasImage = false;
                    let imageUrl = '';
                    
                    // Extraer texto de respuesta
                    if (data.response) {
                        responseText = String(data.response);
                        console.log('📝 Texto de respuesta extraído:', responseText);
                    } else {
                        responseText = 'Respuesta recibida sin contenido';
                        console.warn('⚠️ data.response está vacío');
                    }
                    
                    // Verificar imagen
                    if (data.image_generated === true && data.image_url) {
                        hasImage = true;
                        imageUrl = data.image_url;
                        console.log('🖼️ Imagen detectada:', imageUrl);
                    }
                    
                    // Agregar mensaje al chat
                    if (hasImage) {
                        console.log('🖼️ Agregando mensaje con imagen...');
                        this.addMessage({
                            text: responseText,
                            image_generated: true,
                            image_url: imageUrl,
                            image_filename: data.image_filename
                        }, 'assistant');
                    } else {
                        console.log('📝 Agregando mensaje de texto...');
                        this.addMessage(responseText, 'assistant');
                    }
                    
                    // Actualizar conversation_id si viene
                    if (data.conversation_id) {
                        this.conversationId = data.conversation_id;
                        console.log('🆔 Conversation ID actualizado:', this.conversationId);
                    }
                    
                    console.log('✅ Mensaje de respuesta agregado exitosamente');
                    
                } else {
                    console.error('❌ Respuesta no exitosa del servidor:', data);
                    const errorMsg = data.response || data.error || 'Error desconocido del servidor';
                    this.addMessage(`❌ ${errorMsg}`, 'assistant');
                }
                
            } catch (error) {
                // ✅ MANEJO DE ERRORES COMPLETO
                console.error('❌ Error en sendMessage:', error);
                console.error('❌ Error stack:', error.stack);
                
                this.hideTypingIndicator();
                this.isTyping = false;
                
                let errorMessage = '🔌 Error de conexión.';
                
                if (error.message.includes('Failed to fetch')) {
                    errorMessage = '🔌 No se pudo conectar con el servidor. Verifica tu conexión a internet.';
                } else if (error.message.includes('500')) {
                    errorMessage = '⚠️ Error interno del servidor. AVA puede estar reiniciándose.';
                } else if (error.message.includes('404')) {
                    errorMessage = '🔍 Servicio no encontrado. Contacta al administrador.';
                } else if (error.message.includes('JSON')) {
                    errorMessage = '📄 Error en formato de respuesta del servidor.';
                } else {
                    errorMessage = `❌ Error: ${error.message}`;
                }
                
                this.addMessage(errorMessage, 'assistant');
                console.error('💥 Error final mostrado al usuario:', errorMessage);
            }
            
            console.log('🏁 sendMessage() completado');
        }

        // ✅ FUNCIÓN addMessage COMPLETA
        addMessage(content, sender) {
            console.log('➕ Agregando mensaje:', { content, sender });
            
            const chatMessages = document.getElementById('chatMessages');
            if (!chatMessages) {
                console.error('❌ chatMessages no encontrado');
                return;
            }
            
            const messageDiv = document.createElement('div');
            messageDiv.className = `message ${sender}`;
            
            // ✅ VERIFICAR SI EL CONTENIDO ES UN OBJETO CON IMAGEN
            if (typeof content === 'object' && content.image_generated) {
                console.log('🖼️ Creando mensaje con imagen');
                messageDiv.innerHTML = `
                    <div class="message-content">
                        <p>${this.escapeHtml(content.text)}</p>
                        <div class="image-container">
                            <img src="${content.image_url}" 
                                 alt="Imagen generada por AVA" 
                                 class="generated-image"
                                 loading="lazy">
                            <div class="image-actions">
                                <button class="btn-download" title="Descargar imagen">
                                    <i class="fas fa-download"></i>
                                </button>
                                <button class="btn-expand" title="Ver en grande">
                                    <i class="fas fa-expand"></i>
                                </button>
                            </div>
                        </div>
                    </div>
                `;
                
                // ✅ AGREGAR EVENT LISTENERS DESPUÉS DE CREAR EL HTML
                setTimeout(() => {
                    const img = messageDiv.querySelector('.generated-image');
                    const downloadBtn = messageDiv.querySelector('.btn-download');
                    const expandBtn = messageDiv.querySelector('.btn-expand');
                    
                    if (img) {
                        img.addEventListener('click', () => this.openImageModal(content.image_url));
                        img.addEventListener('error', () => {
                            console.error('❌ Error cargando imagen:', content.image_url);
                            img.parentElement.innerHTML = '<p>❌ Error cargando imagen</p>';
                        });
                    }
                    if (downloadBtn) {
                        downloadBtn.addEventListener('click', () => this.downloadImage(content.image_url, content.image_filename));
                    }
                    if (expandBtn) {
                        expandBtn.addEventListener('click', () => this.openImageModal(content.image_url));
                    }
                }, 10);
                
            } else {
                console.log('📝 Creando mensaje de texto normal');
                const textContent = typeof content === 'string' ? content : 
                                   typeof content === 'object' ? (content.text || JSON.stringify(content)) : 
                                   String(content);
                                   
                messageDiv.innerHTML = `
                    <div class="message-content">${this.escapeHtml(textContent)}</div>
                `;
            }
            
            chatMessages.appendChild(messageDiv);
            chatMessages.scrollTop = chatMessages.scrollHeight;
            console.log('✅ Mensaje agregado al chat');
        }

        // ✅ FUNCIÓN showTypingIndicator
        showTypingIndicator() {
            const chatMessages = document.getElementById('chatMessages');
            
            // ✅ VERIFICAR SI YA EXISTE PARA EVITAR DUPLICADOS
            if (document.getElementById('typingIndicator')) {
                return;
            }
            
            const typingDiv = document.createElement('div');
            typingDiv.className = 'message assistant typing-indicator';
            typingDiv.id = 'typingIndicator';
            typingDiv.innerHTML = `
                <div class="message-content">
                    <div class="typing-dots">
                        <div class="typing-dot"></div>
                        <div class="typing-dot"></div>
                        <div class="typing-dot"></div>
                    </div>
                </div>
            `;
            
            chatMessages.appendChild(typingDiv);
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }

        // ✅ FUNCIÓN hideTypingIndicator
        hideTypingIndicator() {
            const typingIndicator = document.getElementById('typingIndicator');
            if (typingIndicator) {
                typingIndicator.remove();
            }
        }

        // ✅ FUNCIÓN escapeHtml
        escapeHtml(text) {
            if (!text) return '';
            const div = document.createElement('div');
            div.textContent = String(text);
            return div.innerHTML;
        }

        // ✅ FUNCIÓN openImageModal
        openImageModal(imageUrl) {
            console.log('🖼️ Abriendo modal para imagen:', imageUrl);
            
            const modal = document.createElement('div');
            modal.className = 'image-modal';
            modal.style.cssText = `
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0, 0, 0, 0.8);
                display: flex;
                justify-content: center;
                align-items: center;
                z-index: 9999;
            `;
            
            modal.innerHTML = `
                <div class="modal-content" style="position: relative; max-width: 90%; max-height: 90%;">
                    <span class="close" style="position: absolute; top: -40px; right: 0; color: white; font-size: 30px; cursor: pointer;">&times;</span>
                    <img src="${imageUrl}" alt="Imagen generada por AVA" style="max-width: 100%; max-height: 100%; border-radius: 8px;">
                    <div class="modal-actions" style="position: absolute; bottom: -50px; left: 50%; transform: translateX(-50%);">
                        <button class="btn-download-modal" style="background: #FFD700; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer;">
                            <i class="fas fa-download"></i> Descargar
                        </button>
                    </div>
                </div>
            `;
            
            const closeBtn = modal.querySelector('.close');
            const downloadBtn = modal.querySelector('.btn-download-modal');
            
            closeBtn.addEventListener('click', () => modal.remove());
            downloadBtn.addEventListener('click', () => {
                this.downloadImage(imageUrl);
                modal.remove();
            });
            
            modal.addEventListener('click', (e) => {
                if (e.target === modal) {
                    modal.remove();
                }
            });
            
            document.body.appendChild(modal);
        }

        // ✅ FUNCIÓN downloadImage
        downloadImage(imageUrl, filename = null) {
            console.log('📥 Descargando imagen:', imageUrl);
            
            const link = document.createElement('a');
            link.href = imageUrl;
            link.download = filename || `ava_image_${Date.now()}.png`;
            link.target = '_blank';
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        }
    }

    // ✅ FUNCIONES DE DEBUG
    window.debugAva = async function() {
        console.log('=== DEBUG AVA ===');
        
        const container = document.querySelector('.chat-assistant-container');
        const bubble = document.getElementById('chatBubble');
        const chatWindow = document.getElementById('chatWindow');
        
        console.log('Container existe:', !!container);
        console.log('Bubble existe:', !!bubble);
        console.log('Window existe:', !!chatWindow);
        console.log('ChatBubble instance:', window.chatBubble);
        
        try {
            console.log('🔍 Testeando conexión con backend...');
            const statusResponse = await fetch('/api/chat/status');
            const statusData = await statusResponse.json();
            console.log('Estado AVA:', statusData);
            
        } catch (error) {
            console.error('Error en debug:', error);
        }
        
        console.log('=== FIN DEBUG ===');
    };

    window.testAvaMessage = async function(msg = 'hola') {
        console.log(`🧪 Testeando mensaje: "${msg}"`);
        
        if (!window.chatBubble) {
            console.error('❌ ChatBubble no inicializado');
            return;
        }
        
        if (!window.chatBubble.isOpen) {
            console.log('📱 Abriendo chat para test...');
            window.chatBubble.toggleChat();
            await new Promise(resolve => setTimeout(resolve, 500));
        }
        
        const chatInput = document.getElementById('chatInput');
        if (chatInput) {
            chatInput.value = msg;
            console.log('📝 Input configurado, enviando...');
            await window.chatBubble.sendMessage();
        } else {
            console.error('❌ Input de chat no encontrado');
        }
    };

    // ✅ INICIALIZAR SOLO UNA VEZ
    if (!window.chatBubble) {
        window.chatBubble = new ChatBubble();
        console.log('✅ Chat Bubble inicializado correctamente');
    } else {
        console.log('⚠️ Chat Bubble ya estaba inicializado');
    }
    
    window.reinitChatBubble = function() {
        console.log('🔄 Reiniciando Chat Bubble...');
        
        const existing = document.querySelector('.chat-assistant-container');
        if (existing) {
            existing.remove();
        }
        
        window.chatBubble = new ChatBubble();
        console.log('✅ Chat Bubble reiniciado');
    };
});