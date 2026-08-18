FROM node:22-bookworm-slim
WORKDIR /app
COPY package*.json ./
RUN npm install --omit=dev
COPY . .
ENV PORT=3000
ENV SOCKS_PORT=1080
EXPOSE 3000
EXPOSE 1080
CMD ["npm","start"]
