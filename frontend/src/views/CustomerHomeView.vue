<template>
  <main class="stack">
    <h1>العميل</h1>
    <router-link class="card" :to="{ name: 'request-new' }">اطلب توصيلة جديدة</router-link>
    <router-link class="card" :to="{ name: 'requests' }">طلباتي</router-link>
    <router-link to="/">رجوع</router-link>
  </main>
</template>
