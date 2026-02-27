<script setup lang="ts">
  import {useDisplay} from 'vuetify'

  import {useThemeStore} from '@/stores/theme'

  import kiFemLogo from '@/assets/ki_fem.png'
  import scaDsAiLogo from '@/assets/scads_ai.png'
  import tuDresdenLogo from '@/assets/tu_dresden.svg'

  import ThemeChangeButton from '@/components/buttons/ThemeChangeButton.vue'
  import ContrastChangeButton from '@/components/buttons/ContrastChangeButton.vue'
  import LanguageChangeButton from '@/components/buttons/LanguageChangeButton.vue'

  const {thresholds} = useDisplay()
  const themeStore = useThemeStore()
</script>

<template>
  <v-app>
    <RouterView />
    <v-footer v-if="!$route.meta.hideFooter"
              class="flex-grow-0"
              :theme="themeStore.darkTheme">
      <v-container class="pa-8" :max-width="thresholds.lg">
        <v-row class="ga-12" no-gutters>
          <v-col class="d-flex justify-center justify-md-start flex-wrap ga-8">
            <img :alt="$t('logoTuDresden')"
                 height="40"
                 :src="tuDresdenLogo">
            <img :alt="$t('logoScaDsAi')"
                 height="40"
                 :src="scaDsAiLogo">
            <img :alt="$t('logoKiFem')"
                 height="40"
                 :src="kiFemLogo">
          </v-col>
          <v-col class="d-flex justify-center align-center flex-wrap ga-12 d-print-none" cols="12" md="auto">
            <RouterLink :to="{name: 'imprint'}">{{ $t('imprint') }}</RouterLink>
            <div class="d-flex ga-12">
              <ContrastChangeButton is-on-dark-parent />
              <ThemeChangeButton />
              <LanguageChangeButton />
            </div>
          </v-col>
        </v-row>
      </v-container>
    </v-footer>
  </v-app>
</template>

<style scoped>

</style>
