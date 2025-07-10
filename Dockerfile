# Dockerfile para Next.js App
FROM node:20-alpine

WORKDIR /app

# Verificar que existe el directorio firebase_pagina
COPY firebase_pagina/package*.json ./

# Instalar dependencias
RUN npm ci --only=production

# Copiar el resto del código de firebase_pagina
COPY firebase_pagina/ .

# Crear directorios para assets estáticos
RUN mkdir -p public/videos public/images

# Build de la aplicación
RUN npm run build

# Exponer puerto
EXPOSE 3000

# Variables de entorno
ENV NODE_ENV=production
ENV NEXT_PUBLIC_NEWS_API_URL=http://webhook-news:5000
ENV NEXT_PUBLIC_CHAT_API_URL=http://webhook-chat:5001

# Crear usuario no-root para seguridad
RUN addgroup -g 1001 -S nodejs
RUN adduser -S nextjs -u 1001

# Cambiar propietario de archivos
RUN chown -R nextjs:nodejs /app
USER nextjs

# Comando para iniciar
CMD ["npm", "start"]
