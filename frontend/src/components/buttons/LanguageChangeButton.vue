<script setup lang="ts">
  import {useTheme} from 'vuetify'
  import {useI18n} from 'vue-i18n'

  import germanFlag from '@/assets/german.svg'
  import englishFlag from '@/assets/english.svg'

  const theme = useTheme()
  const {availableLocales, locale} = useI18n()

  const storedLanguage = localStorage.getItem('language')
  const browserLanguage = (navigator.languages || []).map(language => language.split('-')[0]!).find(language => availableLocales.includes(language))
  if (storedLanguage && availableLocales.includes(storedLanguage))
    locale.value = storedLanguage
  else if (browserLanguage)
    locale.value = browserLanguage

  function setLanguage(language: string) {
    locale.value = language
    localStorage.setItem('language', language)
  }
</script>

<template>
  <v-btn :aria-label="$t('changeLanguage')" icon variant="text">
    <v-icon icon="fas fa-earth-europe" />
    <v-tooltip activator="parent" :text="$t('changeLanguage')" />
    <v-menu activator="parent" open-on-click :theme="theme.global.name.value">
      <v-list mandatory
              :selected="[locale]"
              slim
              @update:selected="setLanguage($event[0] ?? locale)">
        <v-list-item :title="$t('languageGerman')" value="de">
          <template #prepend>
            <v-avatar :image="germanFlag" tile />
          </template>
        </v-list-item>
        <v-list-item :title="$t('languageEnglish')" value="en">
          <template #prepend>
            <v-avatar :image="englishFlag" tile />
          </template>
        </v-list-item>
      </v-list>
    </v-menu>
  </v-btn>
</template>

<style scoped>

</style>
