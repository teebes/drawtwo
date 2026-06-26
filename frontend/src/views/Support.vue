<template>
  <div class="support-page">
    <main class="px-6 py-24 sm:px-8 lg:px-12">
      <div class="mx-auto max-w-3xl">
        <h1 class="font-display text-4xl font-bold text-gray-900 dark:text-white sm:text-5xl">
          Support
        </h1>

        <div class="mt-12 space-y-8 text-gray-700 dark:text-gray-300">
          <section>
            <h2 class="text-2xl font-bold text-gray-900 dark:text-white">Help with Draw Two</h2>
            <p class="mt-4 leading-relaxed">
              For account, login, gameplay, or billing questions, contact Morel Software through the Draw Two support
              repository.
            </p>
            <a
              href="https://github.com/teebes/drawtwo/issues"
              target="_blank"
              rel="noreferrer"
              class="mt-6 inline-flex items-center text-lg font-semibold text-gray-900 underline decoration-2 underline-offset-4 transition-colors hover:text-gray-700 dark:text-white dark:hover:text-gray-300"
            >
              Open a support request
            </a>
          </section>
        </div>

        <div class="mt-16">
          <router-link
            to="/"
            class="inline-flex items-center text-lg font-semibold text-gray-900 underline decoration-2 underline-offset-4 transition-colors hover:text-gray-700 dark:text-white dark:hover:text-gray-300"
          >
            Back to Home
          </router-link>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup>
</script>

<style scoped>
.support-page {
  min-height: 100vh;
}
</style>
