<script setup lang="ts">
import { ref } from 'vue'
import { errorMessage } from '../api/client'
import { usePolling } from '../composables/usePolling'
import { formatDateTime } from '../labels'
import { useDriverStore } from '../stores/driver'

const driver = useDriverStore()
const error = ref('')
const busyId = ref<number | null>(null)

async function load(clearError = true) {
  try {
    await driver.loadRequests()
    if (clearError) error.value = ''
  } catch (e) {
    error.value = errorMessage(e)
  }
}
usePolling(() => load())

const isInterested = (status: string | null) => status === 'INTERESTED' || status === 'CONTACTED'

async function toggle(id: number, status: string | null) {
  busyId.value = id
  try {
    await driver.setInterest(id, !isInterested(status))
    error.value = ''
  } catch (e) {
    error.value = errorMessage(e)
    await load(false) // the request may have closed meanwhile
  } finally {
    busyId.value = null
  }
}
</script>

<template>
  <main class="stack">
    <h1>الطلبات المناسبة</h1>
    <p class="hint">المطابقة تقديرية حسب المنطقة، وإبداء الاهتمام لا يعني تأكيد المشوار.</p>
    <p v-if="error" class="error" role="alert">{{ error }}</p>

    <p v-if="!driver.requests.length" class="card">
      لا توجد طلبات مناسبة الآن. تأكد من تفعيل الاستقبال وتحديد وجهتك وحداثة موقعك.
    </p>

    <section v-for="r in driver.requests" :key="r.id" class="card stack" data-testid="matched-request">
      <strong>{{ r.pickup_area.name }} ← {{ r.destination_area.name }}</strong>
      <span v-if="r.notes">ملاحظات: {{ r.notes }}</span>
      <span v-if="r.preferred_pickup_at">الوقت المفضل: {{ formatDateTime(r.preferred_pickup_at) }}</span>
      <span class="hint">ينتهي: {{ formatDateTime(r.expires_at) }}</span>
      <button
        type="button"
        :class="{ secondary: isInterested(r.my_interest) }"
        :disabled="busyId === r.id"
        @click="toggle(r.id, r.my_interest)"
      >
        {{ isInterested(r.my_interest) ? 'سحب الاهتمام' : 'مهتم' }}
      </button>
    </section>

    <router-link :to="{ name: 'driver-interests' }">اهتماماتي ومشاويري</router-link>
    <router-link :to="{ name: 'driver' }">وضع السائق</router-link>
  </main>
</template>

<style scoped>
.hint {
  margin: 0;
  color: var(--muted);
  font-size: 0.85rem;
}
</style>
