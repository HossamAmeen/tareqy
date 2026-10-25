<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { errorMessage } from '../api/client'
import type { AppNotification } from '../api/notifications'
import { usePolling } from '../composables/usePolling'
import { usePush } from '../composables/usePush'
import { formatDateTime, notificationTarget } from '../labels'
import { useNotificationsStore } from '../stores/notifications'

const store = useNotificationsStore()
const router = useRouter()
const push = usePush()
const error = ref('')

usePolling(async () => {
  try {
    await store.load()
    error.value = ''
  } catch (e) {
    error.value = errorMessage(e)
  }
})
onMounted(() => push.refresh())

async function open(n: AppNotification) {
  try {
    if (!n.read_at) await store.markRead(n.id)
  } catch {
    /* reading is best effort; still navigate */
  }
  const target = notificationTarget(n.type, n.related_object_id)
  if (target) await router.push(target)
}
</script>

<template>
  <main class="stack">
    <h1>الإشعارات</h1>
    <p v-if="error" class="error" role="alert">{{ error }}</p>

    <section class="card stack" data-testid="push">
      <template v-if="push.state.value === 'on'">
        <span>التنبيهات على هذا الجهاز: مفعّلة</span>
        <button type="button" class="secondary" @click="push.disable()">إيقاف التنبيهات</button>
      </template>
      <template v-else-if="push.state.value === 'off'">
        <span>فعّل التنبيهات لتصلك الطلبات والتحديثات حتى لو كان التطبيق مغلقًا.</span>
        <button type="button" @click="push.enable()">تفعيل التنبيهات</button>
      </template>
      <span v-else-if="push.state.value === 'denied'">التنبيهات محظورة من إعدادات المتصفح.</span>
      <span v-else>التنبيهات غير متاحة على هذا الجهاز. ستظهر الإشعارات هنا داخل التطبيق.</span>
      <p v-if="push.error.value" class="error">{{ push.error.value }}</p>
    </section>

    <p v-if="!store.items.length" class="card">لا توجد إشعارات.</p>
    <button
      v-for="n in store.items"
      :key="n.id"
      type="button"
      class="card note"
      :class="{ unread: !n.read_at }"
      data-testid="notification"
      @click="open(n)"
    >
      <strong>{{ n.title }}</strong>
      <span>{{ n.body }}</span>
      <small>{{ formatDateTime(n.created_at) }}</small>
    </button>

    <router-link to="/">الرئيسية</router-link>
  </main>
</template>

<style scoped>
.note {
  display: flex;
  flex-direction: column;
  gap: 4px;
  align-items: flex-start;
  text-align: start;
  width: 100%;
  color: var(--text);
  font-weight: 400;
  background: var(--surface);
  border-color: var(--border);
}
.unread {
  border-color: var(--primary);
  border-width: 2px;
}
small {
  color: var(--muted);
}
</style>
