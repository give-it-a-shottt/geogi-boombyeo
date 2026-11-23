# 빌드 단계: 의존성 설치 → next build (standalone 출력)
FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
# 빌드 때는 백엔드가 없어도 된다. 장소 페이지는 실행 뒤 첫 요청에서 데이터를 채운다.
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build

# 실행 단계: 필요한 파일만 담는다.
FROM node:22-alpine
WORKDIR /app
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    HOSTNAME=0.0.0.0 \
    PORT=3000
COPY --from=build --chown=node:node /app/.next/standalone ./
COPY --from=build --chown=node:node /app/.next/static ./.next/static
COPY --from=build --chown=node:node /app/public ./public
USER node
EXPOSE 3000
CMD ["node", "server.js"]
