<script setup lang="ts">
import { ref } from 'vue'
import { errorMessage } from '../api/client'
import * as api from '../api/requests'
import { usePolling } from '../composables/usePolling'
import { phoneHref, whatsappHref } from '../labels'

const props = defineProps<{ requestId: number }>()
const emit = defineEmits<{ confirmed: [trip: api.Trip] }>()

const interests = ref<api.Interest[]>([])
const error = ref('')
const busy = ref(false)
const selected = ref<api.Interest | null>(null)
const price = ref<string | number>('')
const details = ref('')
// One key per confirmation attempt: a double tap or network retry returns the same trip.
let key = ''

async function load() {
  try {
    interests.value = await api.fetchInterests(props.requestId)
  } catch (e) {
    error.value = errorMessage(e)
  }
}
usePolling(load)

async function contacted(interest: api.Interest) {
  try {
    await api.markContacted(props.requestId, interest.id)
    error.value = ''
  } catch (e) {
    error.value = errorMessage(e)
  }
  await load()
}

function choose(interest: api.Interest) {
  selected.value = interest
  key = crypto.randomUUID()
  error.value = ''
}

async function confirm() {
  if (!selected.value || busy.value) return
  busy.value = true
  try {
    const trip = await api.confirmTrip(
      props.requestId,
      {
        interest: selected.value.id,
        agreed_price: String(price.value),
        pickup_details: details.value.trim(),
      },
      key,
    )
    emit('confirmed', trip)
  } catch (e) {
    error.value = errorMessage(e)
    selected.value = null
    await load() // the driver may have withdrawn, or the request changed
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <section class="stack">
    <h2>السائقون المهتمون</h2>
    <p v-if="error" class="error" role="alert">{{ error }}</p>
    <p v-if="!interests.length" class="card">لم يبدِ أي سائق اهتمامه بعد.</p>

    <article v-for="i in interests" :key="i.id" class="card stack" data-testid="interest">
      <strong>{{ i.driver.name || 'سائق' }}</strong>
      <span class="actions">
        <a :href="phoneHref(i.driver.phone)">اتصال</a>
        <a :href="whatsappHref(i.driver.phone)" target="_blank" rel="noopener">واتساب</a>
      </span>
      <button v-if="i.status === 'INTERESTED'" type="button" class="secondary" @click="contacted(i)">
        تم التواصل
      </button>
      <button type="button" @click="choose(i)">اتفقنا، أريد تأكيد هذا السائق</button>
    </article>

    <form v-if="selected" class="card stack" @submit.prevent="confirm">
      <strong>تفاصيل الاتفاق مع {{ selected.driver.name || 'السائق' }}</strong>
      <label>
        السعر المتفق عليه
        <input v-model="price" type="number" min="0" step="0.5" inputmode="decimal" required />
      </label>
      <label>
        مكان الركوب بدقة (اختياري)
        <input v-model="details" maxlength="300" />
      </label>
      <p class="hint">بعد التأكيد يُغلق الطلب أمام باقي السائقين.</p>
      <button type="submit" :disabled="busy || price === ''">تأكيد المشوار</button>
      <button type="button" class="secondary" :disabled="busy" @click="selected = null">رجوع</button>
    </form>
  </section>
</template>

<style scoped>
.actions {
  display: flex;
  gap: 16px;
}
.hint {
  margin: 0;
  color: var(--muted);
  font-size: 0.85rem;
}
</style>
