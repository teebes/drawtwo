<template>
  <div class="legal-page">
    <main class="px-6 py-24 sm:px-8 lg:px-12">
      <div class="mx-auto max-w-3xl">
        <h1 class="font-display text-4xl font-bold text-gray-900 dark:text-white sm:text-5xl">
          Terms of Service
        </h1>
        <p class="mt-4 text-lg text-gray-600 dark:text-gray-400">
          Last updated: November 14, 2025
        </p>

        <div class="mt-12 space-y-8 text-gray-700 dark:text-gray-300">
          <section>
            <h2 class="text-2xl font-bold text-gray-900 dark:text-white">1. Acceptance of Terms</h2>
            <p class="mt-4 leading-relaxed">
              By accessing and using Draw Two, you accept and agree to be bound by the terms and provision of this
              agreement. If you do not agree to these Terms of Service, please do not use our service.
            </p>
          </section>

          <section>
            <h2 class="text-2xl font-bold text-gray-900 dark:text-white">2. Description of Service</h2>
            <p class="mt-4 leading-relaxed">
              Draw Two is an open-source engine for building and playing online trading card games. Morel Software, LLC
              provides you with access to this service subject to these Terms of Service.
            </p>
          </section>

          <section>
            <h2 class="text-2xl font-bold text-gray-900 dark:text-white">3. User Accounts</h2>
            <p class="mt-4 leading-relaxed">
              To access certain features of the service, you may be required to create an account. You agree to:
            </p>
            <ul class="mt-4 list-disc space-y-2 pl-6">
              <li>Provide accurate and complete information</li>
              <li>Maintain the security of your password</li>
              <li>Notify us immediately of any unauthorized use of your account</li>
              <li>Be responsible for all activities that occur under your account</li>
            </ul>
          </section>

          <section>
            <h2 class="text-2xl font-bold text-gray-900 dark:text-white">4. User Conduct</h2>
            <p class="mt-4 leading-relaxed">
              You agree not to use the service to:
            </p>
            <ul class="mt-4 list-disc space-y-2 pl-6">
              <li>Violate any laws or regulations</li>
              <li>Infringe on the rights of others</li>
              <li>Transmit any harmful or malicious code</li>
              <li>Interfere with or disrupt the service or servers</li>
              <li>Attempt to gain unauthorized access to any portion of the service</li>
              <li>Harass, abuse, or harm other users</li>
            </ul>
          </section>

          <section>
            <h2 class="text-2xl font-bold text-gray-900 dark:text-white">5. Intellectual Property</h2>
            <p class="mt-4 leading-relaxed">
              The Draw Two engine is open source and available under the license specified in the project repository.
              User-generated content remains the property of the user, but you grant us a license to use, display, and
              distribute such content as necessary to provide the service.
            </p>
          </section>

          <section>
            <h2 class="text-2xl font-bold text-gray-900 dark:text-white">6. Disclaimer of Warranties</h2>
            <p class="mt-4 leading-relaxed">
              THE SERVICE IS PROVIDED "AS IS" AND "AS AVAILABLE" WITHOUT WARRANTIES OF ANY KIND, EITHER EXPRESS OR IMPLIED.
              WE DO NOT WARRANT THAT THE SERVICE WILL BE UNINTERRUPTED, SECURE, OR ERROR-FREE.
            </p>
          </section>

          <section>
            <h2 class="text-2xl font-bold text-gray-900 dark:text-white">7. Limitation of Liability</h2>
            <p class="mt-4 leading-relaxed">
              TO THE MAXIMUM EXTENT PERMITTED BY LAW, MOREL SOFTWARE, LLC SHALL NOT BE LIABLE FOR ANY INDIRECT, INCIDENTAL,
              SPECIAL, CONSEQUENTIAL, OR PUNITIVE DAMAGES, OR ANY LOSS OF PROFITS OR REVENUES, WHETHER INCURRED DIRECTLY OR
              INDIRECTLY.
            </p>
          </section>

          <section>
            <h2 class="text-2xl font-bold text-gray-900 dark:text-white">8. Termination</h2>
            <p class="mt-4 leading-relaxed">
              We reserve the right to suspend or terminate your account and access to the service at our sole discretion,
              without notice, for conduct that we believe violates these Terms of Service or is harmful to other users,
              us, or third parties, or for any other reason.
            </p>
          </section>

          <section>
            <h2 class="text-2xl font-bold text-gray-900 dark:text-white">9. Changes to Terms</h2>
            <p class="mt-4 leading-relaxed">
              We reserve the right to modify these Terms of Service at any time. We will notify users of any material
              changes by posting the new Terms of Service on this page and updating the "Last updated" date.
            </p>
          </section>

          <section>
            <h2 class="text-2xl font-bold text-gray-900 dark:text-white">10. Governing Law</h2>
            <p class="mt-4 leading-relaxed">
              These Terms of Service shall be governed by and construed in accordance with the laws of the jurisdiction
              in which Morel Software, LLC is registered, without regard to its conflict of law provisions.
            </p>
          </section>

          <section>
            <h2 class="text-2xl font-bold text-gray-900 dark:text-white">11. Contact Information</h2>
            <p class="mt-4 leading-relaxed">
              If you have any questions about these Terms of Service, please contact us through our GitHub repository.
            </p>
          </section>
        </div>

        <div class="mt-16">
          <router-link
            to="/"
            class="inline-flex items-center text-lg font-semibold text-gray-900 underline decoration-2 underline-offset-4 transition-colors hover:text-gray-700 dark:text-white dark:hover:text-gray-300"
          >
            ← Back to Home
          </router-link>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup>
</script>

<style scoped>
.legal-page {
  min-height: 100vh;
}
</style>
