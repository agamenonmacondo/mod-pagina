# Dockerfile para Next.js App
FROM node:20-alpine

WORKDIR /app

# Copiar package.json desde firebase_pagina
COPY firebase_pagina/package*.json ./

# Instalar dependencias
RUN npm install

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

# Comando para iniciar
CMD ["npm", "start"]
