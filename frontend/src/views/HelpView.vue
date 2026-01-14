<script setup lang="ts">
  import {useI18n} from 'vue-i18n'
  import VueMarkdown from 'vue-markdown-render'

  import fawDeMd from '@/locales/de_faq.md?raw'
  import faqEnMd from '@/locales/en_faq.md?raw'

  const {locale} = useI18n()
</script>

<template>
  <v-card v-if="$route.name === 'faq'" class="pa-6">
    <VueMarkdown class="markdown"
                 :source="locale === 'de' ? fawDeMd : faqEnMd" />
  </v-card>
  <v-alert v-else
           class="ma-4"
           color="secondary-container"
           position="absolute"
           rounded="md"
           text="Bitte wähle in der Navigation links ein Hilfethema aus."
           type="info" />
</template>

<style scoped lang="scss">

</style>
