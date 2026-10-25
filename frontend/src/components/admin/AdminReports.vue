<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { fetchReports, reviewReport, type AdminReport } from '../../api/admin'
import { errorMessage } from '../../api/client'
import { formatDateTime } from '../../labels'

const reports = ref<AdminReport[]>([])
const error = ref('')
const notes = ref<Record<number, string>>({})
const busyId = ref<number | null>(null)

const isOpen = (r: AdminReport) => r.status === 'OPEN' || r.status === 'REVIEWING'

async function load(clearError = true) {
  try {
    reports.value = await fetchReports()
    if (clearError) error.value = ''
  } catch (e) {
    error.value = errorMessage(e)
  }
}
onMounted(() => load())

async function review(r: AdminReport, status: 'REVIEWING' | 'RESOLVED' | 'DISMISSED') {
  busyId.value = r.id
  try {
    const updated = await reviewReport(r.id, status, notes.value[r.id] ?? '')
    reports.value = reports.value.map((x) => (x.id === updated.id ? updated : x))
    error.value = ''
  } catch (e) {
    error.value = errorMessage(e)
    await load(false)
  } finally {
    busyId.value = null
  }
}
</script>

<template>
  <section class="stack">
    <p v-if="error" class="error" role="alert">{{ error }}</p>
    <p v-if="!reports.length" class="card">لا توجد بلاغات.</p>
    <article v-for="r in reports" :key="r.id" class="card stack" data-testid="admin-report">
      <strong>{{ r.status }} · من {{ r.reporter }}</strong>
      <span v-if="r.related_user">بخصوص: {{ r.related_user.phone }}</span>
      <p>{{ r.reason }}</p>
      <small>{{ formatDateTime(r.created_at) }}</small>
      <p v-if="r.resolution_note">ملاحظة: {{ r.resolution_note }}</p>
      <template v-if="isOpen(r)">
        <input v-model="notes[r.id]" maxlength="500" placeholder="ملاحظة المراجعة" />
        <div class="row">
          <button
            v-if="r.status === 'OPEN'"
            type="button"
            class="secondary"
            :disabled="busyId === r.id"
            @click="review(r, 'REVIEWING')"
          >
            قيد المراجعة
          </button>
          <button type="button" :disabled="busyId === r.id" @click="review(r, 'RESOLVED')">
            تمت المعالجة
          </button>
          <button type="button" class="secondary" :disabled="busyId === r.id" @click="review(r, 'DISMISSED')">
            رفض
          </button>
        </div>
      </template>
    </article>
  </section>
</template>

<style scoped>
.row {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
small {
  color: var(--muted);
}
</style>
