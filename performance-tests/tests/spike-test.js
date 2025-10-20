/**
 * ============================================================================
 * SPIKE TESTING
 * ============================================================================
 *
 * МЕТА:
 * Перевірити як система реагує на раптові різкі сплески навантаження.
 * Симулює ситуацію коли кількість користувачів миттєво зростає у 20 разів
 * (наприклад, після реклами, публікації у соцмережах, або виходу новини).
 *
 * ХІД ВИКОНАННЯ ТЕСТУ:
 * 1. Warm-up фаза (2 хвилини): Нормальна активність - 100 користувачів
 * 2. SPIKE фаза (30 секунд): РІЗКИЙ сплеск до 2000 користувачів
 * 3. Recovery фаза (1 хвилина): Швидке повернення до 100 користувачів
 * 4. Cool-down (1 хвилина): Зниження до 0
 *
 * КОЖНА ІТЕРАЦІЯ ТЕСТУ:
 * Під час сплеску користувачі виконують прості операції:
 * - Перегляд списку travel plans (GET /api/travel-plans)
 * - Читання деталей випадкового плану (GET /api/travel-plans/:id)
 * - Мінімальний запис (тільки 10% користувачів створюють плани)
 *
 * ЩО ПЕРЕВІРЯЄМО:
 * - Чи система витримує раптовий сплеск без падіння
 * - Скільки запитів втрачається (error rate)
 * - Як швидко response time повертається до норми
 * - Чи є queue overflow або connection timeouts
 * - Як швидко система відновлюється після сплеску
 *
 * ОЧІКУВАННЯ:
 * - Error rate під час сплеску може сягати 20-30% (це нормально)
 * - Response time може зрости до 5-10 секунд на піку
 * - Після сплеску система має відновитись за 30-60 секунд
 * - Критичні операції (health check) не повинні падати
 *
 * МЕТРИКИ:
 * - http_req_duration during spike (p95, p99, max)
 * - http_req_failed rate during spike
 * - Recovery time (час до нормалізації метрик)
 * - Requests dropped / timed out
 *
 * ============================================================================
 */

import { check, sleep, group } from 'k6';
import { Rate, Counter, Trend } from 'k6/metrics';
import { STRESS_THRESHOLDS } from '../config/endpoints.js';
import {
  checkHealth,
  createTravelPlan,
  getTravelPlan,
  listTravelPlans,
  addLocation,
  deleteTravelPlan,
  thinkTime,
} from '../utils/api-client.js';
import {
  generateTravelPlan,
  generateLocation,
} from '../utils/data-generator.js';

// ============================================================================
// КАСТОМНІ МЕТРИКИ
// ============================================================================

const spikePhaseErrors = new Rate('spike_phase_errors');
const normalPhaseErrors = new Rate('normal_phase_errors');
const requestsCompleted = new Counter('requests_completed');
const spikePhaseDuration = new Trend('spike_phase_response_time');

// Трекінг фаз тесту
let currentPhase = 'warmup';

// ============================================================================
// НАЛАШТУВАННЯ ТЕСТУ
// ============================================================================

export const options = {
  // Профіль навантаження: нормально → СПЛЕСК → відновлення → зниження
  stages: [
    { duration: '2m', target: 100 },    // Warm-up: нормальна активність
    { duration: '30s', target: 2000 },  // SPIKE: різкий сплеск у 20 разів!
    { duration: '1m', target: 100 },    // Recovery: швидке повернення
    { duration: '1m', target: 0 },      // Cool-down: зниження
  ],

  // М'які пороги - під час spike очікуємо погіршення
  thresholds: {
    // Під час spike response time може бути дуже високим
    'http_req_duration': [
      'p(95)<10000',  // 95% запитів < 10 секунд (дуже м'яко)
      'max<30000',    // Максимум 30 секунд
    ],

    // Під час spike допускаємо до 30% помилок
    'http_req_failed': ['rate<0.30'],

    // Специфічні метрики для spike фази
    'spike_phase_errors': ['rate<0.40'], // До 40% помилок у spike - ОК

    // У нормальній фазі має бути краще
    'normal_phase_errors': ['rate<0.05'], // <5% помилок у нормальній фазі

    // Загальні checks
    'checks': ['rate>0.70'], // 70% перевірок мають проходити

    // API помилки (500, не 429 або timeouts)
    'api_errors': ['rate<0.10'],
  },

  // Налаштування для обробки високого навантаження
  noConnectionReuse: false,
  userAgent: 'K6-SpikeTest/1.0',

  // Збільшуємо batch для кращої продуктивності k6
  batch: 20,
  batchPerHost: 10,
};

// ============================================================================
// ОСНОВНИЙ СЦЕНАРІЙ ТЕСТУ
// ============================================================================

export default function () {
  // Визначаємо поточну фазу на основі часу виконання
  const elapsed = __ITER * __VU; // Приблизна оцінка
  if (elapsed < 120) {
    currentPhase = 'warmup';
  } else if (elapsed < 150) {
    currentPhase = 'spike';
  } else if (elapsed < 210) {
    currentPhase = 'recovery';
  } else {
    currentPhase = 'cooldown';
  }

  // Під час spike робимо простіші операції
  if (currentPhase === 'spike') {
    spikeScenario();
  } else {
    normalScenario();
  }
}

// ============================================================================
// СЦЕНАРІЙ ПІД ЧАС SPIKE
// ============================================================================

function spikeScenario() {
  const startTime = Date.now();
  let hasError = false;

  group('Spike Scenario - Light Operations', function () {
    // --------------------------------------------------
    // 1. HEALTH CHECK (критично - має працювати завжди)
    // --------------------------------------------------
    const isHealthy = checkHealth();
    if (!isHealthy) {
      hasError = true;
    }

    // Мінімальна пауза
    sleep(0.1);

    // --------------------------------------------------
    // 2. ПЕРЕГЛЯД СПИСКУ (найпростіша операція)
    // --------------------------------------------------
    const plansList = listTravelPlans();

    if (!plansList) {
      hasError = true;
    } else {
      check(plansList, {
        'spike: can get plans list': (list) => Array.isArray(list),
      });
    }

    sleep(0.2);

    // --------------------------------------------------
    // 3. ЧИТАННЯ ОДНОГО ПЛАНУ (якщо список не порожній)
    // --------------------------------------------------
    if (plansList && plansList.length > 0) {
      const randomIndex = Math.floor(Math.random() * plansList.length);
      const randomPlanId = plansList[randomIndex].id;

      const plan = getTravelPlan(randomPlanId);

      if (!plan) {
        hasError = true;
      } else {
        check(plan, {
          'spike: can read plan details': (p) => p.id !== undefined,
        });
      }
    }

    sleep(0.2);

    // --------------------------------------------------
    // 4. МІНІМАЛЬНИЙ ЗАПИС (тільки 10% користувачів)
    // --------------------------------------------------
    if (Math.random() < 0.10) {
      const planData = generateTravelPlan();
      planData.title = `Spike Test Plan ${Date.now()}`;

      const plan = createTravelPlan(planData);

      if (plan) {
        // Додаємо одну локацію
        const locationData = generateLocation();
        addLocation(plan.id, locationData);

        // Швидке видалення (cleanup)
        deleteTravelPlan(plan.id);
      } else {
        hasError = true;
      }
    }
  });

  // Записуємо метрики spike фази
  const duration = Date.now() - startTime;
  spikePhaseDuration.add(duration);
  spikePhaseErrors.add(hasError ? 1 : 0);
  requestsCompleted.add(1);

  // Дуже коротка пауза під час spike
  sleep(0.1);
}

// ============================================================================
// НОРМАЛЬНИЙ СЦЕНАРІЙ (WARM-UP / RECOVERY / COOL-DOWN)
// ============================================================================

function normalScenario() {
  let hasError = false;

  group('Normal Scenario - Full Operations', function () {
    // --------------------------------------------------
    // 1. HEALTH CHECK
    // --------------------------------------------------
    const isHealthy = checkHealth();
    if (!isHealthy) {
      hasError = true;
    }

    thinkTime(0.5, 1);

    // --------------------------------------------------
    // 2. ПЕРЕГЛЯД СПИСКУ
    // --------------------------------------------------
    const plansList = listTravelPlans();

    if (!plansList) {
      hasError = true;
    }

    thinkTime(1, 2);

    // --------------------------------------------------
    // 3. ЧИТАННЯ ДЕКІЛЬКОХ ПЛАНІВ
    // --------------------------------------------------
    if (plansList && plansList.length > 0) {
      const readsCount = Math.min(2, plansList.length);

      for (let i = 0; i < readsCount; i++) {
        const randomIndex = Math.floor(Math.random() * plansList.length);
        const plan = getTravelPlan(plansList[randomIndex].id);

        if (!plan) {
          hasError = true;
        }

        thinkTime(1, 2);
      }
    }

    // --------------------------------------------------
    // 4. СТВОРЕННЯ НОВОГО ПЛАНУ (50% користувачів)
    // --------------------------------------------------
    if (Math.random() < 0.5) {
      const planData = generateTravelPlan();
      const plan = createTravelPlan(planData);

      if (!plan) {
        hasError = true;
      } else {
        // Додаємо 1-2 локації
        const locationCount = Math.random() < 0.5 ? 1 : 2;

        for (let i = 0; i < locationCount; i++) {
          const locationData = generateLocation();
          addLocation(plan.id, locationData);
          thinkTime(0.5, 1);
        }

        // Cleanup (30% шанс)
        if (Math.random() < 0.3) {
          deleteTravelPlan(plan.id);
        }
      }
    }
  });

  // Записуємо метрики нормальної фази
  normalPhaseErrors.add(hasError ? 1 : 0);
  requestsCompleted.add(1);

  sleep(1);
}

// ============================================================================
// SETUP & TEARDOWN
// ============================================================================

export function setup() {
  console.log('='.repeat(80));
  console.log('🔥 SPIKE TEST - Sudden Traffic Burst');
  console.log('='.repeat(80));
  console.log('');
  console.log('Test Profile:');
  console.log('  Phase 1 (2m):   Warm-up     → 100 users   (normal activity)');
  console.log('  Phase 2 (30s):  SPIKE! 🚀   → 2000 users  (20x increase!)');
  console.log('  Phase 3 (1m):   Recovery    → 100 users   (back to normal)');
  console.log('  Phase 4 (1m):   Cool-down   → 0 users');
  console.log('');
  console.log('Total Duration: 4.5 minutes');
  console.log('');
  console.log('What to expect:');
  console.log('  ⚠️  High error rate during spike (20-30%) is NORMAL');
  console.log('  ⚠️  Response time will spike to 5-10 seconds');
  console.log('  ✅  System should recover within 30-60 seconds');
  console.log('  ✅  No complete outages (health check still works)');
  console.log('');
  console.log('Key Metrics:');
  console.log('  - spike_phase_errors (errors during spike)');
  console.log('  - normal_phase_errors (errors before/after)');
  console.log('  - spike_phase_response_time (latency during spike)');
  console.log('  - Recovery time (visual from graph)');
  console.log('='.repeat(80));
  console.log('');

  // Створюємо декілька тестових планів для читання під час spike
  console.log('Creating 10 sample plans for spike testing...');
  const samplePlans = [];

  for (let i = 0; i < 10; i++) {
    const planData = generateTravelPlan();
    planData.title = `Sample Plan ${i + 1} for Spike Test`;
    planData.is_public = true;

    const plan = createTravelPlan(planData);

    if (plan) {
      samplePlans.push(plan.id);

      // Додаємо 2 локації
      for (let j = 0; j < 2; j++) {
        const locationData = generateLocation();
        addLocation(plan.id, locationData);
      }
    }

    sleep(0.2);
  }

  console.log(`✓ Created ${samplePlans.length} sample plans`);
  console.log('');
  console.log('Starting spike test in 3 seconds...');
  sleep(3);
  console.log('='.repeat(80));

  return { samplePlanIds: samplePlans };
}

export function teardown(data) {
  console.log('');
  console.log('='.repeat(80));
  console.log('🔥 SPIKE TEST COMPLETED');
  console.log('='.repeat(80));
  console.log('');

  // Cleanup тестових планів
  if (data && data.samplePlanIds && data.samplePlanIds.length > 0) {
    console.log('Cleaning up sample plans...');
    let deleted = 0;

    for (const planId of data.samplePlanIds) {
      if (deleteTravelPlan(planId)) {
        deleted++;
      }
      sleep(0.1);
    }

    console.log(`✓ Cleaned up ${deleted}/${data.samplePlanIds.length} plans`);
    console.log('');
  }

  console.log('Results Analysis:');
  console.log('');
  console.log('1. Compare metrics:');
  console.log('   - spike_phase_errors vs normal_phase_errors');
  console.log('   - Look for difference in error rates');
  console.log('');
  console.log('2. Check response times:');
  console.log('   - http_req_duration p95/p99 during spike');
  console.log('   - spike_phase_response_time trend');
  console.log('');
  console.log('3. Recovery analysis:');
  console.log('   - How quickly did errors drop after spike?');
  console.log('   - Did response times return to normal?');
  console.log('   - Were there any timeouts or connection errors?');
  console.log('');
  console.log('4. System behavior:');
  console.log('   - Did health checks remain stable?');
  console.log('   - Were requests queued or dropped?');
  console.log('   - Any database connection pool exhaustion?');
  console.log('');
  console.log('Good results:');
  console.log('  ✅ Error rate <30% during spike');
  console.log('  ✅ Recovery within 60 seconds');
  console.log('  ✅ No complete system failure');
  console.log('  ✅ Health checks always respond');
  console.log('');
  console.log('Warning signs:');
  console.log('  ⚠️  Error rate >50% during spike');
  console.log('  ⚠️  Recovery takes >2 minutes');
  console.log('  ⚠️  Health checks fail');
  console.log('  ⚠️  System crashes or becomes unresponsive');
  console.log('='.repeat(80));
}