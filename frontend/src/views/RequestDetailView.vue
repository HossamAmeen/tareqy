<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute } from 'vue-router'
import { errorMessage } from '../api/client'
import StatusBadge from '../components/StatusBadge.vue'
import { usePolling } from '../composables/usePolling'
import { formatDateTime, isEditable } from '../labels'
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
      <p v-else-if="request.status === 'EXPIRED'">انتهت صلاحية الطلب دون تأكيد. يمكنك إنشاء طلب جديد.</p>
    </section>

    <template v-if="request && isEditable(request.status)">
      <router-link class="card" :to="{ name: 'request-edit', params: { id } }">تعديل الطلب</router-link>
      <button type="button" class="secondary" :disabled="busy" @click="cancel">إلغاء الطلب</button>
    </template>
    <router-link :to="{ name: 'requests' }">كل طلباتي</router-link>
  </main>
</template>
