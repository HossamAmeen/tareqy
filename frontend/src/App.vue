<script setup lang="ts">
import { useInstallPrompt } from './composables/useInstallPrompt'
import { useOnline } from './composables/useOnline'

const online = useOnline()
const { canInstall, install } = useInstallPrompt()
</script>

<template>
  <div v-if="!online" class="banner" role="status">
    لا يوجد اتصال بالإنترنت. ستظهر آخر حالة محفوظة عند عودة الاتصال.
  </div>
  <div v-if="canInstall" class="banner stack" role="region" aria-label="تثبيت التطبيق">
    <span>ثبّت «في طريقي» على شاشتك الرئيسية</span>
    <button type="button" @click="install">تثبيت</button>
  </div>
  <router-view />
</template>
