<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { PAGES } from '../pages'

const page = computed(() => PAGES[String(useRoute().meta.page)])
</script>

<template>
  <main v-if="page" class="stack">
    <h1>{{ page.title }}</h1>
    <p v-if="page.draft" class="banner">مسودة بانتظار المراجعة القانونية قبل الإطلاق.</p>
    <section v-for="s in page.sections" :key="s.heading" class="card stack">
      <strong>{{ s.heading }}</strong>
      <p>{{ s.text }}</p>
    </section>
    <router-link to="/">الرئيسية</router-link>
  </main>
</template>
