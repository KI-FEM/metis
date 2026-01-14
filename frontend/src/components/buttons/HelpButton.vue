<script setup lang="ts">
  import {useOnboardingStore} from '@/stores/onboarding.ts'

  const onboardingStore = useOnboardingStore()
</script>

<template>
  <v-btn :aria-label="$t('openHelp')" icon variant="text">
    <v-icon icon="fas fa-circle-question" />
    <v-tooltip activator="parent" :text="$t('openHelp')" />
    <v-menu activator="parent" open-on-click>
      <v-list slim>
        <v-list-item prepend-icon="fas fa-route"
                     :title="$t('resetOnboarding')"
                     @click="onboardingStore.reset()" />
<!--        <v-list-item prepend-icon="fas fa-question"-->
<!--                     :title="$t('faq')"-->
<!--                     :to="{name: 'faq'}" />-->
<!--        <v-list-item prepend-icon="fas fa-book-open"-->
<!--                     :title="$t('detailedHelp')"-->
<!--                     :to="{name: 'help'}" />-->
<!--        <v-list-item prepend-icon="fas fa-info"-->
<!--                     :title="$t('about')"-->
<!--                     :to="{name: 'about'}" />-->
      </v-list>
    </v-menu>
  </v-btn>
</template>

<style scoped>

</style>
