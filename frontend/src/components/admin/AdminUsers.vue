<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { fetchUsers, userAction, type AdminUser } from '../../api/admin'
import { errorMessage } from '../../api/client'

const users = ref<AdminUser[]>([])
const search = ref('')
const role = ref('')
const error = ref('')
const busyId = ref<number | null>(null)

async function load() {
  try {
    users.value = await fetchUsers({
      search: search.value.trim() || undefined,
      role: role.value || undefined,
    })
    error.value = ''
  } catch (e) {
    error.value = errorMessage(e)
  }
}
onMounted(load)

async function act(user: AdminUser, action: Parameters<typeof userAction>[1]) {
  if (action === 'suspend' && !window.confirm(`إيقاف حساب ${user.phone}؟`)) return
  busyId.value = user.id
  try {
    const updated = await userAction(user.id, action)
    users.value = users.value.map((u) => (u.id === updated.id ? updated : u))
    error.value = ''
  } catch (e) {
    error.value = errorMessage(e)
  } finally {
    busyId.value = null
  }
}
</script>

<template>
  <section class="stack">
    <form class="stack" @submit.prevent="load">
      <input v-model="search" placeholder="بحث بالهاتف أو الاسم" />
      <select v-model="role" @change="load">
        <option value="">كل الأدوار</option>
        <option value="driver">سائقون</option>
        <option value="customer">عملاء</option>
      </select>
      <button type="submit">بحث</button>
    </form>
    <p v-if="error" class="error" role="alert">{{ error }}</p>

    <article v-for="u in users" :key="u.id" class="card stack" data-testid="admin-user">
      <strong>{{ u.name || '—' }}</strong>
      <small>{{ u.phone }}</small>
      <span>
        {{ u.account_status === 'ACTIVE' ? 'نشط' : 'موقوف' }}
        <template v-if="u.is_driver"> · سائق {{ u.is_verified ? '(موثّق)' : '(غير موثّق)' }}</template>
        <template v-if="u.is_staff"> · إدارة</template>
      </span>
      <div class="row">
        <button
          v-if="u.account_status === 'ACTIVE'"
          type="button"
          class="secondary"
          :disabled="busyId === u.id"
          @click="act(u, 'suspend')"
        >
          إيقاف الحساب
        </button>
        <button v-else type="button" :disabled="busyId === u.id" @click="act(u, 'activate')">
          تفعيل الحساب
        </button>
        <template v-if="u.is_driver">
          <button
            v-if="!u.is_verified"
            type="button"
            :disabled="busyId === u.id"
            @click="act(u, 'verify-driver')"
          >
            توثيق السائق
          </button>
          <button
            v-else
            type="button"
            class="secondary"
            :disabled="busyId === u.id"
            @click="act(u, 'unverify-driver')"
          >
            إلغاء التوثيق
          </button>
        </template>
      </div>
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
select {
  font: inherit;
  padding: 12px;
  border-radius: 10px;
  border: 1px solid var(--border);
  background: var(--surface);
  color: var(--text);
}
</style>
