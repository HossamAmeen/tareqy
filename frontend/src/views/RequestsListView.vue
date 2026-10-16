<script setup lang="ts">
import { ref } from 'vue'
import { errorMessage } from '../api/client'
import StatusBadge from '../components/StatusBadge.vue'
import { usePolling } from '../composables/usePolling'
import { formatDateTime } from '../labels'
import { useRequestsStore } from '../stores/requests'

const store = useRequestsStore()
const error = ref('')
const loaded = ref(false)

usePolling(async () => {
  try {
    await store.load()
    error.value = ''
  } catch (e) {
    error.value = errorMessage(e)
  } finally {
    loaded.value = true
  }
})
</script>

<template>
  <main class="stack">
    <h1>طلباتي</h1>
    <p v-if="error" class="error" role="alert">{{ error }}</p>
    <p v-else-if="loaded && !store.items.length">لا توجد طلبات بعد.</p>

    <router-link
      v-for="r in store.items"
      :key="r.id"
      class="card stack"
      :to="{ name: 'request-detail', params: { id: r.id } }"
    >
      <strong>{{ r.pickup_area.name }} ← {{ r.destination_area.name }}</strong>
      <span><StatusBadge :status="r.status" /> · {{ formatDateTime(r.created_at) }}</span>
    </router-link>

    <router-link class="card" :to="{ name: 'request-new' }">طلب جديد</router-link>
    <router-link :to="{ name: 'customer' }">رجوع</router-link>
  </main>
</template>
