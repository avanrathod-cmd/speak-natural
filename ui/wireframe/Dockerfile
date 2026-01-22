# SpeakRight Frontend Dockerfile

# Build stage
FROM --platform=linux/amd64 node:20-alpine AS build

WORKDIR /app

# Build arguments for React environment variables
ARG REACT_APP_API_URL=http://localhost:8000
ARG REACT_APP_SUPABASE_URL
ARG REACT_APP_SUPABASE_ANON_KEY

# Set as environment variables for build
ENV REACT_APP_API_URL=$REACT_APP_API_URL
ENV REACT_APP_SUPABASE_URL=$REACT_APP_SUPABASE_URL
ENV REACT_APP_SUPABASE_ANON_KEY=$REACT_APP_SUPABASE_ANON_KEY

# Copy package files
COPY package.json package-lock.json ./

# Install dependencies (use --legacy-peer-deps for TypeScript compatibility)
RUN npm ci --legacy-peer-deps

# Copy source code
COPY . .

# Build the app
RUN npm run build

# Production stage - serve with nginx
FROM --platform=linux/amd64 nginx:alpine

# Copy built app
COPY --from=build /app/build /usr/share/nginx/html

# Create nginx config template
RUN echo 'server { \
    listen ${PORT}; \
    location / { \
        root /usr/share/nginx/html; \
        index index.html; \
        try_files $uri $uri/ /index.html; \
    } \
}' > /etc/nginx/conf.d/default.conf.template

# Create startup script that substitutes PORT and starts nginx
RUN echo '#!/bin/sh' > /start.sh && \
    echo 'export PORT=${PORT:-8080}' >> /start.sh && \
    echo 'envsubst "\$PORT" < /etc/nginx/conf.d/default.conf.template > /etc/nginx/conf.d/default.conf' >> /start.sh && \
    echo 'nginx -g "daemon off;"' >> /start.sh && \
    chmod +x /start.sh

EXPOSE 8080

CMD ["/start.sh"]
