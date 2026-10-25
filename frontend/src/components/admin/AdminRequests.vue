<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { fetchAdminRequests, type AdminRequest } from '../../api/admin'
import { errorMessage } from '../../api/client'
import { formatDateTime } from '../../labels'

const rows = ref<AdminRequest[]>([])
const status = ref('')
const error = ref('')

async function load() {
  try {
    rows.value = await fetchAdminRequests(status.value || undefined)
    error.value = ''
  } catch (e) {
    error.value = errorMessage(e)
  }
}
onMounted(load)
watch(status, load)
</script>

<template>
  <section class="stack">
    <select v-model="status">
      <option value="">كل الحالات</option>
      <option value="OPEN">مفتوح</option>
      <option value="CONFIRMED">مؤكد</option>
      <option value="CANCELLED">ملغي</option>
      <option value="EXPIRED">منتهي</option>
    </select>
    <p v-if="error" class="error" role="alert">{{ error }}</p>
    <article v-for="r in rows" :key="r.id" class="card stack" data-testid="admin-request">
      <strong>{{ r.pickup_area }} ← {{ r.destination_area }}</strong>
      <span>{{ r.customer }} · {{ r.status }} · اهتمام: {{ r.interest_count }}</span>
      <small>{{ formatDateTime(r.created_at) }}</small>
    </article>
  </section>
</template>

<style scoped>
small {
  color: var(--muted);
}
select {
  font: inherit;
  padding: 12px;
  border-radius: 10px;
  border: 1px solid var(--border);
  background: var(--surface);
  color: var(--text);
}
</style>
