<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { fetchKpis, type Kpis } from '../../api/admin'
import { errorMessage } from '../../api/client'

const days = ref(30)
const kpis = ref<Kpis | null>(null)
const error = ref('')

const pct = (v: number | null) => (v === null ? '—' : `${Math.round(v * 100)}%`)
const minutes = (s: number | null) => (s === null ? '—' : `${Math.round(s / 60)} د`)

async function load() {
  try {
    kpis.value = await fetchKpis(days.value)
    error.value = ''
  } catch (e) {
    error.value = errorMessage(e)
  }
}
onMounted(load)
watch(days, load)
</script>

<template>
  <section class="stack">
    <label>
      الفترة
      <select v-model.number="days">
        <option :value="1">آخر يوم</option>
        <option :value="7">آخر 7 أيام</option>
        <option :value="30">آخر 30 يومًا</option>
      </select>
    </label>
    <p v-if="error" class="error" role="alert">{{ error }}</p>
    <div v-if="kpis" class="grid" data-testid="kpis">
      <div class="card">
        <small>الطلبات المنشورة</small><strong>{{ kpis.requests_published }}</strong>
      </div>
      <div class="card">
        <small>مفتوحة الآن</small><strong>{{ kpis.open_now }}</strong>
      </div>
      <div class="card">
        <small>وصل لها سائق مهتم</small><strong>{{ pct(kpis.interest_rate) }}</strong>
      </div>
      <div class="card">
        <small>معدل التأكيد</small><strong>{{ pct(kpis.confirmation_rate) }}</strong>
      </div>
      <div class="card">
        <small>انتهت دون تأكيد</small><strong>{{ pct(kpis.expired_rate) }}</strong>
      </div>
      <div class="card">
        <small>إلغاء قبل التأكيد</small><strong>{{ pct(kpis.cancelled_before_confirmation_rate) }}</strong>
      </div>
      <div class="card">
        <small>إلغاء بعد التأكيد</small><strong>{{ pct(kpis.cancelled_after_confirmation_rate) }}</strong>
      </div>
      <div class="card">
        <small>زمن أول اهتمام</small><strong>{{ minutes(kpis.avg_seconds_to_first_interest) }}</strong>
      </div>
      <div class="card">
        <small>زمن التأكيد</small><strong>{{ minutes(kpis.avg_seconds_to_confirmation) }}</strong>
      </div>
      <div class="card">
        <small>سائقون نشطون (24 ساعة)</small><strong>{{ kpis.active_drivers_24h }}</strong>
      </div>
      <div class="card">
        <small>عملاء عائدون</small><strong>{{ pct(kpis.returning_customer_rate) }}</strong>
      </div>
    </div>
    <p class="hint">الحسابات التجريبية مستبعدة. معدلات النتائج محسوبة على الطلبات المحسومة فقط.</p>
  </section>
</template>

<style scoped>
.grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}
.card {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
strong {
  font-size: 1.4rem;
}
small,
.hint {
  color: var(--muted);
  font-size: 0.8rem;
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
