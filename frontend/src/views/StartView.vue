<script setup lang="ts">
  import {ref} from 'vue'
  import {useI18n} from 'vue-i18n'
  import VueMarkdown from 'vue-markdown-render'

  import metis from '@/assets/metis.svg'
  import moreAboutDeMd from '@/locales/de_about.md?raw'
  import moreAboutEnMd from '@/locales/en_about.md?raw'

  const {locale} = useI18n()

  const shownExpansion = ref<number | undefined>()
</script>

<template>
  <v-main>
    <v-container class="fill-height flex-column justify-center">
      <v-card max-width="800" variant="elevated">
        <v-card-item>
          <v-card-title class="text-center text-display-sm text-sm-display-md"
                        :class="{'mt-6': $route.name === 'start'}"
                        tag="h1">
            <span>{{ $t('startTitle') }}</span>
            <img :alt="$t('logoChatBot')"
                 class="mx-auto mt-6 mb-12 px-2"
                 :src="metis"
                 style="max-height: 6rem; filter: drop-shadow(3px 3px 3px #999);">
          </v-card-title>
        </v-card-item>
        <v-card-text class="mx-auto px-sm-16 text-headline-sm text-sm-headline-md text-center"
                     style="text-wrap: balance">
          <I18nT keypath="startIntro" scope="global" tag="p">
            <strong style="font-weight: 800">{{ $t('chatBot') }}</strong>
          </I18nT>
        </v-card-text>
        <v-card-actions class="my-6 justify-center">
          <v-btn append-icon="fas fa-arrow-right"
                 size="large"
                 :text="$t('start')"
                 :to="{name: 'chatbots'}"
                 variant="flat" />
        </v-card-actions>
        <v-divider />
        <v-expansion-panels v-model="shownExpansion"
                            flat
                            tile
                            variant="accordion">
          <v-expansion-panel>
            <v-expansion-panel-title class="text-title-sm" height="4rem">
              {{ $t('startMoreAbout') }}
            </v-expansion-panel-title>
            <v-expansion-panel-text class="markdown">
              <VueMarkdown :source="locale === 'de' ? moreAboutDeMd : moreAboutEnMd" />
              <div class="mt-6 text-center">
                <v-btn :text="$t('startClose')" variant="text" @click="shownExpansion = undefined" />
              </div>
            </v-expansion-panel-text>
          </v-expansion-panel>
        </v-expansion-panels>
      </v-card>
    </v-container>
  </v-main>
</template>

<style scoped lang="scss">

</style>
