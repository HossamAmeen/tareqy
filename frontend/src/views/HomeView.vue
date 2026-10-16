<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { errorMessage } from '../api/client'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const router = useRouter()
const error = ref('')
const loading = ref(false)

async function choose(role: 'customer' | 'driver') {
  error.value = ''
  loading.value = true
  try {
    const flag = role === 'driver' ? 'is_driver' : 'is_customer'
    if (!auth.user?.[flag]) await auth.updateRoles({ [flag]: true })
    await router.push({ name: role })
  } catch (e) {
    error.value = errorMessage(e)
  } finally {
    loading.value = false
  }
}

function logout() {
  auth.logout()
  router.replace({ name: 'login' })
}
</script>

<template>
  <main class="stack">
    <h1>أهلًا{{ auth.user?.name ? `، ${auth.user.name}` : '' }}</h1>
    <p>كيف تريد استخدام «في طريقي»؟</p>

    <div class="stack">
      <button type="button" :disabled="loading" @click="choose('customer')">اطلب توصيلة</button>
      <button type="button" :disabled="loading" @click="choose('driver')">أنا سائق</button>
    </div>
    <p v-if="error" class="error" role="alert">{{ error }}</p>

    <button type="button" class="secondary" @click="logout">تسجيل الخروج</button>
  </main>
</template>
