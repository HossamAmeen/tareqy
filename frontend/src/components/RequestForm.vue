<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { Area, RequestPayload, TripRequest } from '../api/requests'

const props = defineProps<{
  areas: Area[]
  initial?: TripRequest
  submitLabel: string
  busy?: boolean
  error?: string
}>()
const emit = defineEmits<{ submit: [payload: RequestPayload] }>()

const pickup = ref<number | ''>(props.initial?.pickup_area.id ?? '')
const destination = ref<number | ''>(props.initial?.destination_area.id ?? '')
const notes = ref(props.initial?.notes ?? '')
const coords = ref<{ lat: string; lng: string } | null>(null)
const locating = ref(false)
const locationError = ref('')

watch(
  () => props.initial,
  (req) => {
    if (!req) return
    pickup.value = req.pickup_area.id
    destination.value = req.destination_area.id
    notes.value = req.notes
  },
)

const sameArea = computed(() => pickup.value !== '' && pickup.value === destination.value)
const valid = computed(() => pickup.value !== '' && destination.value !== '' && !sameArea.value)
const precise = computed(() => !!coords.value || !!props.initial?.pickup_location_is_precise)

function useMyLocation() {
  locationError.value = ''
  if (!navigator.geolocation) {
    locationError.value = 'المتصفح لا يدعم تحديد الموقع'
    return
  }
  locating.value = true
  navigator.geolocation.getCurrentPosition(
    (pos) => {
      coords.value = { lat: pos.coords.latitude.toFixed(6), lng: pos.coords.longitude.toFixed(6) }
      locating.value = false
    },
    () => {
      locationError.value = 'تعذر تحديد موقعك، سنستخدم المنطقة فقط'
      locating.value = false
    },
    { enableHighAccuracy: true, timeout: 10000 },
  )
}

function onSubmit() {
  if (!valid.value) return
  const payload: RequestPayload = {
    pickup_area: Number(pickup.value),
    destination_area: Number(destination.value),
    notes: notes.value.trim(),
  }
  if (coords.value) {
    payload.pickup_latitude = coords.value.lat
    payload.pickup_longitude = coords.value.lng
  }
  emit('submit', payload)
}
</script>

<template>
  <form class="card stack" @submit.prevent="onSubmit">
    <label>
      مكان الركوب
      <select v-model="pickup" required>
        <option value="" disabled>اختر المنطقة</option>
        <option v-for="a in areas" :key="a.id" :value="a.id">{{ a.name }}</option>
      </select>
    </label>

    <label>
      الوجهة
      <select v-model="destination" required>
        <option value="" disabled>اختر المنطقة</option>
        <option v-for="a in areas" :key="a.id" :value="a.id">{{ a.name }}</option>
      </select>
    </label>
    <p v-if="sameArea" class="error" role="alert">مكان الركوب والوجهة يجب أن يكونا مختلفين</p>

    <div class="stack">
      <p class="location-state" data-testid="precision">
        {{ precise ? 'موقع الركوب: دقيق' : 'موقع الركوب: تقريبي (حسب المنطقة)' }}
      </p>
      <button type="button" class="secondary" :disabled="locating" @click="useMyLocation">
        استخدم موقعي الدقيق
      </button>
      <p v-if="locationError" class="error">{{ locationError }}</p>
    </div>

    <label>
      ملاحظات للالتقاء (اختياري)
      <input v-model="notes" maxlength="300" placeholder="مثال: عند البوابة الرئيسية" />
    </label>

    <p v-if="error" class="error" role="alert">{{ error }}</p>
    <button type="submit" :disabled="!valid || busy">{{ submitLabel }}</button>
  </form>
</template>

<style scoped>
select {
  font: inherit;
  padding: 12px;
  min-height: 48px;
  border-radius: 10px;
  border: 1px solid var(--border);
  background: var(--surface);
  color: var(--text);
}
.location-state {
  margin: 0;
}
</style>
