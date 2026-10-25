<script setup lang="ts">
import { ref } from 'vue'
import AdminKpis from '../components/admin/AdminKpis.vue'
import AdminReports from '../components/admin/AdminReports.vue'
import AdminRequests from '../components/admin/AdminRequests.vue'
import AdminUsers from '../components/admin/AdminUsers.vue'

const tabs = [
  { id: 'kpis', label: 'المؤشرات', component: AdminKpis },
  { id: 'users', label: 'المستخدمون', component: AdminUsers },
  { id: 'requests', label: 'الطلبات', component: AdminRequests },
  { id: 'reports', label: 'البلاغات', component: AdminReports },
]
const active = ref('kpis')
</script>

<template>
  <main class="stack">
    <h1>لوحة الإدارة</h1>
    <nav class="tabs" role="tablist">
      <button
        v-for="t in tabs"
        :key="t.id"
        type="button"
        role="tab"
        :class="{ secondary: active !== t.id }"
        :aria-selected="active === t.id"
        @click="active = t.id"
      >
        {{ t.label }}
      </button>
    </nav>
    <template v-for="t in tabs" :key="t.id">
      <component :is="t.component" v-if="active === t.id" />
    </template>
    <router-link to="/">الرئيسية</router-link>
  </main>
</template>

<style scoped>
.tabs {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
</style>
