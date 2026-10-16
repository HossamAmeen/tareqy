<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { errorMessage } from '../api/client'
import type { RequestPayload } from '../api/requests'
import RequestForm from '../components/RequestForm.vue'
import { useRequestsStore } from '../stores/requests'

const store = useRequestsStore()
const router = useRouter()
const id = Number(useRoute().params.id)
const busy = ref(false)
const error = ref('')
const request = computed(() => store.items.find((r) => r.id === id))

onMounted(async () => {
  try {
    await Promise.all([store.loadAreas(), store.refresh(id)])
  } catch (e) {
    error.value = errorMessage(e)
  }
})

async function submit(payload: RequestPayload) {
  busy.value = true
  error.value = ''
  try {
    await store.update(id, payload)
    await router.replace({ name: 'request-detail', params: { id } })
  } catch (e) {
    error.value = errorMessage(e)
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <main class="stack">
    <h1>تعديل الطلب</h1>
    <p>تغيير مكان الركوب أو الوجهة يلغي اهتمام السائقين السابقين ويُبلغهم بالتغيير.</p>
    <RequestForm
      v-if="request"
      :areas="store.areas"
      :initial="request"
      submit-label="حفظ التعديلات"
      :busy="busy"
      :error="error"
      @submit="submit"
    />
    <p v-else-if="error" class="error" role="alert">{{ error }}</p>
    <router-link :to="{ name: 'request-detail', params: { id } }">رجوع</router-link>
  </main>
</template>
