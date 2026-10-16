<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { errorMessage } from '../api/client'
import type { RequestPayload } from '../api/requests'
import RequestForm from '../components/RequestForm.vue'
import { useRequestsStore } from '../stores/requests'

const store = useRequestsStore()
const router = useRouter()
const busy = ref(false)
const error = ref('')

onMounted(async () => {
  try {
    await store.loadAreas()
  } catch (e) {
    error.value = errorMessage(e)
  }
})

async function submit(payload: RequestPayload) {
  busy.value = true
  error.value = ''
  try {
    const created = await store.create(payload)
    await router.replace({ name: 'request-detail', params: { id: created.id } })
  } catch (e) {
    error.value = errorMessage(e)
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <main class="stack">
    <h1>طلب توصيلة</h1>
    <RequestForm :areas="store.areas" submit-label="نشر الطلب" :busy="busy" :error="error" @submit="submit" />
    <router-link :to="{ name: 'customer' }">رجوع</router-link>
  </main>
</template>
