<script setup lang="ts">
  import {useTheme} from 'vuetify'
  import {useI18n} from 'vue-i18n'

  import germanFlag from '@/assets/german.svg'
  import englishFlag from '@/assets/english.svg'

  const theme = useTheme()
  const {availableLocales, fallbackLocale, locale} = useI18n()

  // get and assign the default browser language if supported or fallback language otherwise
  locale.value = (navigator.languages.find(language => availableLocales.includes(language.split('-')[0])) || fallbackLocale.value as string).split('-')[0]
</script>

<template>
  <v-btn :aria-label="$t('changeLanguage')" icon variant="text">
    <v-icon icon="fas fa-earth-europe" />
    <v-tooltip activator="parent" :text="$t('changeLanguage')" />
    <v-menu activator="parent" open-on-click :theme="theme.global.name.value">
      <v-list mandatory
              :selected="[locale]"
              slim
              @update:selected="locale = $event[0]">
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
