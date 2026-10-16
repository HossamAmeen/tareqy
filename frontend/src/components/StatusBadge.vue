<script setup lang="ts">
import type { RequestStatus } from '../api/requests'
import { STATUS_LABELS } from '../labels'

defineProps<{ status: RequestStatus }>()
</script>

<template>
  <span class="badge" :class="`badge-${status.toLowerCase()}`">{{ STATUS_LABELS[status] }}</span>
</template>

<style scoped>
.badge {
  display: inline-block;
  padding: 2px 10px;
  border-radius: 999px;
  font-size: 0.8rem;
  font-weight: 600;
  border: 1px solid currentColor;
}
.badge-open {
  color: var(--primary);
}
.badge-confirmed {
  color: #15803d;
}
.badge-cancelled,
.badge-expired {
  color: var(--muted);
}
</style>
