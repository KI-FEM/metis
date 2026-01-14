<script setup lang="ts">
  import {useDisplay} from 'vuetify'
  import {useI18n} from 'vue-i18n'

  import {useThemeStore} from '@/stores/theme'

  import tuDresdenLogo from '@/assets/tu_dresden.svg'
  import tuDresdenLogoDe from '@/assets/tu_dresden_de.svg'
  import tuDresdenLogoEn from '@/assets/tu_dresden_en.svg'
  import euSachsenLogo from '@/assets/eu_sachsen.png'
  import scaDsAiLogo from '@/assets/scads_ai.png'
  import scsLogo from '@/assets/scs.svg'

  import ContrastChangeButton from '@/components/buttons/ContrastChangeButton.vue'
  import ThemeChangeButton from '@/components/buttons/ThemeChangeButton.vue'
  import LanguageChangeButton from '@/components/buttons/LanguageChangeButton.vue'

  const {locale} = useI18n()
  const {thresholds, xs} = useDisplay()
  const themeStore = useThemeStore()
</script>

<template>
  <v-app class="bg-brand">
    <header class="d-flex justify-space-between">
      <div class="pa-4 flex-shrink-0">
        <img :alt="$t('logoTuDresden')"
             height="60"
             :src="xs ? tuDresdenLogo : locale === 'de' ? tuDresdenLogoDe : tuDresdenLogoEn">
      </div>
      <div class="pa-4"
           style="--notch: 112px; padding-inline-start: calc(var(--notch) + 16px) !important; clip-path: polygon(0 0, 100% 0%, 100% 100%, var(--notch) 100%); background: white">
        <img :alt="$t('logoEuSachsen')"
             height="80"
             :src="euSachsenLogo">
      </div>
    </header>
    <RouterView />
    <v-footer v-if="!$route.meta.hideFooter"
              class="mt-auto flex-grow-0"
              :theme="themeStore.darkTheme">
      <v-container class="pa-8" :max-width="thresholds.lg">
        <v-row class="ga-12" no-gutters>
          <v-col class="d-flex justify-center justify-md-start flex-wrap ga-8">
            <span class="w-100 text-center text-md-start">{{ $t('logoPartnersIntro') }}</span>
            <img :alt="$t('logoScaDsAi')"
                 height="40"
                 :src="scaDsAiLogo">
            <img :alt="$t('logoSCS')"
                 height="40"
                 :src="scsLogo">
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
  img {
    object-fit: contain;
  }
</style>
