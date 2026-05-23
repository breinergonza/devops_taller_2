// =============================================================================
// Script de pruebas de stress con k6 para la Entrega 4 (Monitoreo Continuo).
// -----------------------------------------------------------------------------
// Lo apunto al endpoint público de Fargate (o a localhost para validación local)
// para generar tráfico real y poder ver en New Relic:
//   - Tiempo de respuesta de los servicios (Web transactions time, p95/p99)
//   - Tiempo de respuesta de la DB (PostgreSQL segments en APM > Databases)
//   - Evolución del Apdex
//   - Errores agrupados
//   - Disparo de las condiciones de alerta configuradas
//
// Uso:
//   BASE_URL=https://<alb-dns>  TOKEN=uniandes-devops-2026  k6 run scripts/stress_test.js
//   BASE_URL=http://localhost:5002  TOKEN=uniandes-devops-2026  k6 run scripts/stress_test.js
// =============================================================================

import http from 'k6/http';
import { check, sleep } from 'k6';

// Defino una rampa que cubre warmup, sostenido y pico.
// Quiero que sea suficiente para hacer caer el Apdex por debajo del threshold
// y disparar al menos una alerta en New Relic durante la corrida.
export const options = {
  stages: [
    { duration: '2m', target: 20 },   // warm-up
    { duration: '5m', target: 100 },  // carga sostenida
    { duration: '2m', target: 200 },  // pico para estresar la DB
    { duration: '2m', target: 0 },    // ramp-down
  ],
  thresholds: {
    // Hago que k6 falle si el p95 supera 1s (mismo umbral que la alerta NR).
    http_req_duration: ['p(95)<1000'],
    http_req_failed: ['rate<0.05'],
  },
};

const BASE_URL = __ENV.BASE_URL || 'http://localhost:5002';
const TOKEN = __ENV.TOKEN || 'uniandes-devops-2026';

const authHeaders = {
  'Content-Type': 'application/json',
  Authorization: `Bearer ${TOKEN}`,
};

export default function () {
  // 1) Health check: barato, sirve para medir baseline.
  const pingRes = http.get(`${BASE_URL}/ping`);
  check(pingRes, { 'ping 200': (r) => r.status === 200 });

  // 2) POST a /blacklists: ejercita escritura en PostgreSQL.
  //    Genero un email único por iteración para evitar duplicados que
  //    cortarían la transacción antes de tiempo.
  const uniqueEmail = `stress+${__VU}-${__ITER}-${Date.now()}@test.local`;
  const postPayload = JSON.stringify({
    email: uniqueEmail,
    app_uuid: '11111111-1111-1111-1111-111111111111',
    blocked_reason: 'k6-stress',
  });
  const postRes = http.post(`${BASE_URL}/blacklists`, postPayload, {
    headers: authHeaders,
  });
  check(postRes, { 'post 201|200': (r) => r.status === 201 || r.status === 200 });

  // 3) GET por email: ejercita lectura indexada en PostgreSQL.
  const getRes = http.get(`${BASE_URL}/blacklists/${uniqueEmail}`, {
    headers: authHeaders,
  });
  check(getRes, { 'get 200': (r) => r.status === 200 });

  // Pequeña pausa para no saturar artificialmente y simular un usuario real.
  sleep(1);
}
