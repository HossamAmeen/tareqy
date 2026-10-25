<script setup lang="ts">
import { ref } from 'vue'
import { errorMessage } from '../api/client'
import { usePolling } from '../composables/usePolling'
import { formatDateTime, INTEREST_LABELS, phoneHref, whatsappHref } from '../labels'
import { useDriverStore } from '../stores/driver'

const driver = useDriverStore()
const error = ref('')

usePolling(async () => {
  try {
    await driver.loadInterests()
    error.value = ''
  } catch (e) {
    error.value = errorMessage(e)
  }
})
</script>

<template>
  <main class="stack">
    <h1>اهتماماتي ومشاويري</h1>
    <p v-if="error" class="error" role="alert">{{ error }}</p>
    <p v-if="!driver.interests.length" class="card">لم تبدِ اهتمامًا بأي طلب بعد.</p>

    <section v-for="i in driver.interests" :key="i.id" class="card stack" data-testid="driver-interest">
      <strong>{{ i.request.pickup_area.name }} ← {{ i.request.destination_area.name }}</strong>
      <span :class="`state-${i.status.toLowerCase()}`">{{ INTEREST_LABELS[i.status] }}</span>

      <p v-if="i.status === 'DECLINED'" class="hint">
        اختار العميل سائقًا آخر أو تغيّر الطلب أو أُغلق. ستظهر لك طلبات أخرى مناسبة.
      </p>

      <template v-if="i.customer_phone">
        <span class="actions">
          <a :href="phoneHref(i.customer_phone)">اتصال بالعميل</a>
          <a :href="whatsappHref(i.customer_phone)" target="_blank" rel="noopener">واتساب</a>
        </span>
      </template>

      <template v-if="i.trip">
        <strong>تفاصيل الاتفاق</strong>
        <span>السعر: {{ i.trip.agreed_price }}</span>
        <span v-if="i.trip.pickup_details">مكان الركوب: {{ i.trip.pickup_details }}</span>
        <span v-if="i.trip.scheduled_pickup_at">الوقت: {{ formatDateTime(i.trip.scheduled_pickup_at) }}</span>
        <router-link :to="{ name: 'trip', params: { id: i.trip.id } }">تفاصيل المشوار</router-link>
      </template>
    </section>

    <router-link :to="{ name: 'driver-requests' }">الطلبات المناسبة</router-link>
    <router-link :to="{ name: 'driver' }">وضع السائق</router-link>
  </main>
</template>

<style scoped>
.actions {
  display: flex;
  gap: 16px;
}
.hint {
  margin: 0;
  color: var(--muted);
  font-size: 0.85rem;
}
.state-selected {
  color: #15803d;
  font-weight: 600;
}
.state-declined {
  color: var(--muted);
}
</style>
