# Single-stage: nginx serving static files
FROM nginx:1.27-alpine

# Remove default nginx page
RUN rm -rf /usr/share/nginx/html/*

# Copy the SPA
COPY src/ /usr/share/nginx/html/

# Custom nginx config (proxies /ws and /flashcard to backend)
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
