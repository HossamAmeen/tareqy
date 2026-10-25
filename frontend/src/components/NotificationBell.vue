<script setup lang="ts">
import { usePolling } from '../composables/usePolling'
import { useNotificationsStore } from '../stores/notifications'

const store = useNotificationsStore()
// Unread count also refreshes when the app regains focus or connectivity.
usePolling(() => store.load().catch(() => undefined), 30000)
</script>

<template>
  <router-link class="bell" :to="{ name: 'notifications' }" aria-label="الإشعارات">
    الإشعارات
    <span v-if="store.unread" class="count" data-testid="unread">{{ store.unread }}</span>
  </router-link>
</template>

<style scoped>
.bell {
  display: inline-flex;
  gap: 6px;
  align-items: center;
  margin-bottom: 8px;
}
.count {
  background: var(--danger);
  color: #fff;
  border-radius: 999px;
  padding: 0 8px;
  font-size: 0.8rem;
}
</style>
