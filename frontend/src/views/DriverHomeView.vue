<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { errorMessage } from '../api/client'
import { useGeolocation } from '../composables/useGeolocation'
import { usePolling } from '../composables/usePolling'
import { formatDateTime, LOCATION_STATUS_LABELS } from '../labels'
import { useDriverStore } from '../stores/driver'
import { useRequestsStore } from '../stores/requests'

const driver = useDriverStore()
const requestsStore = useRequestsStore()
const error = ref('')
const busy = ref(false)
const destination = ref<number | ''>('')
const ttl = ref(120)

const geo = useGeolocation((lat, lng) => driver.reportLocation(lat, lng))
const available = computed(() => driver.profile?.availability_status === 'AVAILABLE')

async function run(action: () => Promise<void>) {
  busy.value = true
  try {
    await action()
    error.value = ''
  } catch (e) {
    error.value = errorMessage(e)
  } finally {
    busy.value = false
  }
}

async function refresh() {
  try {
    await driver.loadProfile()
  } catch (e) {
    error.value = errorMessage(e)
  }
}
usePolling(refresh)

onMounted(async () => {
  await requestsStore.loadAreas().catch(() => undefined)
  await refresh()
  // Resume reporting when the driver left the app in receive mode.
  if (available.value) geo.start()
})

const toggle = () =>
  run(async () => {
    const next = available.value ? 'OFFLINE' : 'AVAILABLE'
    await driver.update({ availability_status: next })
    if (next === 'AVAILABLE') geo.start()
    else geo.stop()
  })

const setDestination = () =>
  run(() =>
    driver.update({ destination_area: Number(destination.value), destination_ttl_minutes: ttl.value }),
  )
const clearDestination = () => run(() => driver.update({ destination_area: null }))
</script>

<template>
  <main class="stack">
    <h1>وضع السائق</h1>
    <p v-if="error" class="error" role="alert">{{ error }}</p>

    <section v-if="driver.profile" class="card stack">
      <strong>{{ available ? 'استقبال الطلبات: مفعّل' : 'استقبال الطلبات: متوقف' }}</strong>
      <p class="hint">
        نستخدم موقعك أثناء فتح التطبيق فقط، لعرض الطلبات القريبة منك على الأشخاص المناسبين. لا نتتبعك في
        الخلفية، ويمكنك الإيقاف في أي وقت.
      </p>
      <button type="button" :class="{ secondary: available }" :disabled="busy" @click="toggle">
        {{ available ? 'إيقاف استقبال الطلبات' : 'ابدأ استقبال الطلبات' }}
      </button>
      <p v-if="geo.permission.value === 'denied'" class="error">
        تم رفض إذن الموقع. فعّله من إعدادات المتصفح لتصلك الطلبات.
      </p>
      <p v-else-if="geo.permission.value === 'unsupported'" class="error">جهازك لا يدعم تحديد الموقع.</p>
      <p v-if="geo.error.value" class="error">{{ geo.error.value }}</p>
      <p data-testid="freshness" :class="`fresh-${driver.profile.location_status}`">
        الموقع: {{ LOCATION_STATUS_LABELS[driver.profile.location_status] }}
        <template v-if="driver.profile.current_area">({{ driver.profile.current_area.name }})</template>
      </p>
    </section>

    <section v-if="driver.profile" class="card stack">
      <strong>وجهتك الحالية</strong>
      <template v-if="driver.profile.destination_area">
        <span>{{ driver.profile.destination_area.name }}</span>
        <span v-if="driver.profile.destination_expires_at" class="hint">
          تنتهي {{ formatDateTime(driver.profile.destination_expires_at) }}
        </span>
        <button type="button" class="secondary" :disabled="busy" @click="clearDestination">
          إلغاء الوجهة
        </button>
      </template>
      <p v-else class="hint">
        حدّد وجهتك لتظهر لك الطلبات المناسبة. تُلغى الوجهة تلقائيًا بعد المدة المختارة.
      </p>

      <label>
        الوجهة
        <select v-model="destination">
          <option value="" disabled>اختر المنطقة</option>
          <option v-for="a in requestsStore.areas" :key="a.id" :value="a.id">{{ a.name }}</option>
        </select>
      </label>
      <label>
        صالحة لمدة
        <select v-model.number="ttl">
          <option :value="30">30 دقيقة</option>
          <option :value="60">ساعة</option>
          <option :value="120">ساعتان</option>
          <option :value="240">4 ساعات</option>
        </select>
      </label>
      <button type="button" :disabled="busy || destination === ''" @click="setDestination">
        تحديد الوجهة
      </button>
    </section>

    <router-link class="card" :to="{ name: 'driver-requests' }">الطلبات المناسبة</router-link>
    <router-link class="card" :to="{ name: 'driver-interests' }">اهتماماتي ومشاويري</router-link>
    <router-link to="/">رجوع</router-link>
  </main>
</template>

<style scoped>
select {
  font: inherit;
  padding: 12px;
  border-radius: 10px;
  border: 1px solid var(--border);
  background: var(--surface);
  color: var(--text);
  min-height: 48px;
}
.hint {
  margin: 0;
  color: var(--muted);
  font-size: 0.85rem;
}
.fresh-fresh {
  color: #15803d;
}
.fresh-stale {
  color: var(--danger);
}
</style>
