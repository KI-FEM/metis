<script setup lang="ts">
  import {computed} from 'vue'
  import {useI18n} from 'vue-i18n'
  import VueMarkdown from 'vue-markdown-render'

  import imprintDeMd from '@/locales/de_imprint.md?raw'
  import imprintEnMd from '@/locales/en_imprint.md?raw'

  const {locale, t} = useI18n()

  const privacyPolicy = computed(() => {
    const text = locale.value === 'de' ? imprintDeMd : imprintEnMd
    return text.replace(/{chatBot}/g, t('chatBot'))
  })
</script>

<template>
  <v-card max-width="800">
    <v-card-title class="d-flex align-center ga-3">
      <v-btn :aria-label="$t('imprintBack')"
             class="align-self-start"
             icon="fas fa-arrow-left"
             variant="text"
             @click="$router.back()" />
      <h1 class="text-headline-sm">
        {{ $t('imprint') }}
      </h1>
    </v-card-title>
    <v-divider />
    <v-card-text>
      <!-- TODO: add imprint and divider -->
      <VueMarkdown class="markdown"
                   :source="privacyPolicy" />
    </v-card-text>
    <v-card-actions class="justify-center">
      <v-btn :text="$t('imprintBack')" variant="text" @click="$router.back()" />
    </v-card-actions>
  </v-card>
</template>

<style scoped>

</style>
