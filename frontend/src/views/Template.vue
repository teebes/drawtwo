<template>
  <div class="template-page">
    <AppHeader />

    <main class="flex-1">
      <!-- Content goes here -->
      <section class="py-16">
        <div class="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div class="text-center">
            <h1 class="font-display text-3xl font-bold text-gray-900 dark:text-white">
              Page Title
            </h1>
            <p class="mt-4 text-lg text-gray-600 dark:text-gray-300">
              Page description or content goes here.
            </p>
          </div>
        </div>
      </section>
    </main>
  </div>
</template>

<script setup>
import AppHeader from '../components/AppHeader.vue'
</script>

<style scoped>
.template-page {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}
</style>