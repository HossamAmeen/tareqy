<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute } from 'vue-router'
import { errorMessage } from '../api/client'
import InterestedDrivers from '../components/InterestedDrivers.vue'
import StatusBadge from '../components/StatusBadge.vue'
import { usePolling } from '../composables/usePolling'
import { formatDateTime, isEditable, phoneHref, whatsappHref } from '../labels'
import { useRequestsStore } from '../stores/requests'

const store = useRequestsStore()
const id = Number(useRoute().params.id)
const error = ref('')
const busy = ref(false)
const request = computed(() => store.items.find((r) => r.id === id))

async function refresh() {
  try {
    await store.refresh(id)
    error.value = ''
  } catch (e) {
    error.value = errorMessage(e)
  }
}
usePolling(refresh)

async function cancel() {
  if (!window.confirm('هل تريد إلغاء الطلب؟')) return
  busy.value = true
  try {
    await store.cancel(id)
    error.value = ''
  } catch (e) {
    error.value = errorMessage(e)
    await refresh() // the server state may have changed (e.g. expired)
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <main class="stack">
    <h1>تفاصيل الطلب</h1>
    <p v-if="error" class="error" role="alert">{{ error }}</p>

    <section v-if="request" class="card stack">
      <strong>{{ request.pickup_area.name }} ← {{ request.destination_area.name }}</strong>
      <span><StatusBadge :status="request.status" /></span>
      <span>الموقع: {{ request.pickup_location_is_precise ? 'دقيق' : 'تقريبي (حسب المنطقة)' }}</span>
      <span v-if="request.notes">ملاحظات: {{ request.notes }}</span>
      <span v-if="request.status === 'OPEN'">ينتهي: {{ formatDateTime(request.expires_at) }}</span>
      <p v-if="request.status === 'OPEN'">بانتظار سائق مهتم. سنعرض هنا السائقين عند اهتمامهم بطلبك.</p>
      <template v-else-if="request.status === 'CONFIRMED' && request.trip">
        <strong>{{
          request.trip.status === 'CANCELLED' ? 'أُلغي المشوار المؤكد' : 'تم تأكيد المشوار'
        }}</strong>
        <span>السائق: {{ request.trip.counterpart.name || 'سائق' }}</span>
        <span>السعر المتفق عليه: {{ request.trip.agreed_price }}</span>
        <span v-if="request.trip.pickup_details">مكان الركوب: {{ request.trip.pickup_details }}</span>
        <router-link :to="{ name: 'trip', params: { id: request.trip.id } }">تفاصيل المشوار</router-link>
        <span class="actions">
          <a :href="phoneHref(request.trip.counterpart.phone)">اتصال</a>
          <a :href="whatsappHref(request.trip.counterpart.phone)" target="_blank" rel="noopener">واتساب</a>
        </span>
      </template>
      <p v-else-if="request.status === 'EXPIRED'">انتهت صلاحية الطلب دون تأكيد. يمكنك إنشاء طلب جديد.</p>
    </section>

    <InterestedDrivers v-if="request?.status === 'OPEN'" :request-id="id" @confirmed="refresh" />

    <template v-if="request && isEditable(request.status)">
      <router-link class="card" :to="{ name: 'request-edit', params: { id } }">تعديل الطلب</router-link>
      <button type="button" class="secondary" :disabled="busy" @click="cancel">إلغاء الطلب</button>
    </template>
    <router-link :to="{ name: 'requests' }">كل طلباتي</router-link>
  </main>
</template>

<style scoped>
.actions {
  display: flex;
  gap: 16px;
}
</style>
