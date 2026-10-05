FROM nginx:1.27-alpine

# apache2-utils provides htpasswd for the optional access password (PLT-003). The default
# access.conf keeps the gateway open; 40-access-password.sh replaces it when a password is set.
RUN apk add --no-cache apache2-utils \
    && echo 'auth_basic off;' > /etc/nginx/access.conf

COPY nginx.conf /etc/nginx/nginx.conf
COPY 40-access-password.sh /docker-entrypoint.d/40-access-password.sh
RUN chmod +x /docker-entrypoint.d/40-access-password.sh

EXPOSE 80
