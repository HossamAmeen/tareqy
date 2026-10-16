<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { errorMessage } from '../api/client'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const router = useRouter()

const step = ref<'phone' | 'code'>('phone')
const phone = ref('')
const code = ref('')
const error = ref('')
const loading = ref(false)

async function run(action: () => Promise<void>) {
  error.value = ''
  loading.value = true
  try {
    await action()
  } catch (e) {
    error.value = errorMessage(e)
  } finally {
    loading.value = false
  }
}

const sendCode = () =>
  run(async () => {
    await auth.requestOtp(phone.value.trim())
    step.value = 'code'
  })

const verify = () =>
  run(async () => {
    await auth.verifyOtp(phone.value.trim(), code.value.trim())
    await router.replace({ name: 'home' })
  })
</script>

<template>
  <main class="stack">
    <h1>في طريقي</h1>
    <p>سجّل دخولك برقم الهاتف للمتابعة.</p>

    <form v-if="step === 'phone'" class="card stack" @submit.prevent="sendCode">
      <label>
        رقم الهاتف
        <input
          v-model="phone"
          type="tel"
          inputmode="tel"
          autocomplete="tel"
          dir="ltr"
          placeholder="+20…"
          required
        />
      </label>
      <p v-if="error" class="error" role="alert">{{ error }}</p>
      <button type="submit" :disabled="loading">إرسال رمز التحقق</button>
    </form>

    <form v-else class="card stack" @submit.prevent="verify">
      <label>
        رمز التحقق المرسل إلى {{ phone }}
        <input
          v-model="code"
          type="text"
          inputmode="numeric"
          autocomplete="one-time-code"
          dir="ltr"
          maxlength="10"
          required
        />
      </label>
      <p v-if="error" class="error" role="alert">{{ error }}</p>
      <button type="submit" :disabled="loading">دخول</button>
      <button type="button" class="secondary" :disabled="loading" @click="step = 'phone'">تغيير الرقم</button>
    </form>
  </main>
</template>
