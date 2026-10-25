<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute } from 'vue-router'
import { errorMessage } from '../api/client'
import type { Trip } from '../api/requests'
import { reportTrip } from '../api/reports'
import * as api from '../api/trips'
import { usePolling } from '../composables/usePolling'
import { formatDateTime, phoneHref, TRIP_STATUS_LABELS, whatsappHref } from '../labels'

const id = Number(useRoute().params.id)
const trip = ref<Trip | null>(null)
const error = ref('')
const busy = ref(false)

const isDriver = computed(() => trip.value?.role === 'driver')

// Always show the server's state: polling and resume-from-offline replace anything cached here.
async function refresh(clearError = true) {
  try {
    trip.value = await api.fetchTrip(id)
    if (clearError) error.value = ''
  } catch (e) {
    error.value = errorMessage(e)
  }
}
usePolling(() => refresh())

const reporting = ref(false)
const reason = ref('')
const reported = ref(false)

async function sendReport() {
  busy.value = true
  try {
    await reportTrip(id, reason.value.trim())
    reported.value = true
    reporting.value = false
    reason.value = ''
    error.value = ''
  } catch (e) {
    error.value = errorMessage(e)
  } finally {
    busy.value = false
  }
}

async function act(action: (id: number) => Promise<Trip>, confirmText?: string) {
  if (confirmText && !window.confirm(confirmText)) return
  busy.value = true
  try {
    trip.value = await action(id)
    error.value = ''
  } catch (e) {
    error.value = errorMessage(e)
    await refresh(false) // the other side may have changed the trip meanwhile
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <main class="stack">
    <h1>تفاصيل المشوار</h1>
    <p v-if="error" class="error" role="alert">{{ error }}</p>

    <section v-if="trip" class="card stack">
      <strong>{{ trip.pickup_area.name }} ← {{ trip.destination_area.name }}</strong>
      <span data-testid="status">{{ TRIP_STATUS_LABELS[trip.status] }}</span>
      <span>{{ isDriver ? 'العميل' : 'السائق' }}: {{ trip.counterpart.name || '—' }}</span>
      <span>السعر المتفق عليه: {{ trip.agreed_price }}</span>
      <span v-if="trip.pickup_details">مكان الركوب: {{ trip.pickup_details }}</span>
      <span v-if="trip.scheduled_pickup_at">الوقت: {{ formatDateTime(trip.scheduled_pickup_at) }}</span>
      <span v-if="trip.started_at">بدأ: {{ formatDateTime(trip.started_at) }}</span>
      <span v-if="trip.completed_at">انتهى: {{ formatDateTime(trip.completed_at) }}</span>
      <span v-if="trip.cancelled_at">أُلغي: {{ formatDateTime(trip.cancelled_at) }}</span>
      <span v-if="trip.status === 'CONFIRMED' || trip.status === 'IN_PROGRESS'" class="actions">
        <a :href="phoneHref(trip.counterpart.phone)">اتصال</a>
        <a :href="whatsappHref(trip.counterpart.phone)" target="_blank" rel="noopener">واتساب</a>
      </span>
      <p v-if="trip.status === 'CANCELLED' && !isDriver">أُلغي المشوار. يمكنك إنشاء طلب جديد.</p>
    </section>

    <template v-if="trip">
      <button
        v-if="trip.status === 'CONFIRMED' && isDriver"
        type="button"
        :disabled="busy"
        @click="act(api.startTrip)"
      >
        بدء المشوار
      </button>
      <button
        v-if="trip.status === 'IN_PROGRESS'"
        type="button"
        :disabled="busy"
        @click="act(api.completeTrip, 'هل انتهى المشوار؟')"
      >
        إنهاء المشوار
      </button>
      <button
        v-if="trip.status === 'CONFIRMED'"
        type="button"
        class="secondary"
        :disabled="busy"
        @click="act(api.cancelTrip, 'هل تريد إلغاء المشوار المؤكد؟ سيُبلَّغ الطرف الآخر.')"
      >
        إلغاء المشوار
      </button>
      <p v-if="trip.status === 'IN_PROGRESS'" class="hint">
        لا يمكن إلغاء مشوار بدأ. إن واجهت مشكلة فاتصل بالدعم.
      </p>
    </template>

    <section v-if="trip" class="stack">
      <p v-if="reported" class="card" role="status">وصلنا بلاغك وسنراجعه. شكرًا لك.</p>
      <button v-else-if="!reporting" type="button" class="secondary" @click="reporting = true">
        الإبلاغ عن مشكلة
      </button>
      <form v-else class="card stack" @submit.prevent="sendReport">
        <label>
          ما المشكلة؟
          <textarea v-model="reason" rows="4" minlength="5" maxlength="1000" required />
        </label>
        <button type="submit" :disabled="busy || reason.trim().length < 5">إرسال البلاغ</button>
        <button type="button" class="secondary" @click="reporting = false">رجوع</button>
      </form>
      <router-link :to="{ name: 'safety' }">إرشادات السلامة</router-link>
    </section>

    <router-link to="/">الرئيسية</router-link>
  </main>
</template>

<style scoped>
textarea {
  font: inherit;
  padding: 12px;
  border-radius: 10px;
  border: 1px solid var(--border);
  background: var(--surface);
  color: var(--text);
}
.actions {
  display: flex;
  gap: 16px;
}
.hint {
  margin: 0;
  color: var(--muted);
  font-size: 0.85rem;
}
</style>
