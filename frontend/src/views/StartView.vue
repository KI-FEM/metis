<script setup lang="ts">
  import {ref} from 'vue'
  import {useI18n} from 'vue-i18n'
  import VueMarkdown from 'vue-markdown-render'

  import type {LearningType} from '@/types'

  import {useLearningTypesStore} from '@/stores/learningTypes'
  import {useStudyStore} from '@/stores/study'

  import metis from '@/assets/metis.svg'
  import moreAboutDeMd from '@/locales/de_about.md?raw'
  import moreAboutEnMd from '@/locales/en_about.md?raw'

  import PersonalityTypeConverter from '@/components/PersonalityTypeConverter.vue'

  const {locale} = useI18n()
  const learningTypesStore = useLearningTypesStore()
  const studyStore = useStudyStore()

  const shownExpansion = ref<undefined | string>(undefined)

  learningTypesStore.fetchLearningTypes()
</script>

<template>
  <v-main class="bg-brand">
    <v-container class="fill-height flex-column justify-center">
      <v-card max-width="800" variant="elevated">
        <v-card-item>
          <v-banner bg-color="success" class="text-center text-title-lg text-white" lines="one">
            {{ $t('evaluationBanner') }}
          </v-banner>
          <v-card-title class="text-center text-display-sm text-sm-display-md"
                        :class="{'mt-6': $route.name === 'start'}"
                        tag="h1">
            <span v-if="$route.name === 'start'">{{ $t('startTitle') }}</span>
            <img :alt="$t('logoChatBot')"
                 class="mx-auto mt-6 mb-12 px-2"
                 :src="metis"
                 style="max-height: 6rem; filter: drop-shadow(3px 3px 3px #999);">
          </v-card-title>
        </v-card-item>
        <v-card-text class="mx-auto px-sm-16 text-headline-sm text-sm-headline-md text-center"
                     style="text-wrap: balance">
          <I18nT :keypath="'startIntro'" scope="global" tag="p">
            <strong style="font-weight: 800">{{ $t('chatBot') }}</strong>
          </I18nT>
        </v-card-text>
        <v-card-actions class="my-6 justify-center">
          <v-btn v-if="$route.name === 'start'"
                 append-icon="fas fa-graduation-cap"
                 class="me-4"
                 color="success"
                 size="large"
                 :slim="false"
                 :text="$t('startStudy')"
                 :to="{name: 'study'}" 
                 variant="flat" />
          <v-btn v-if="$route.name === 'start'"
                 append-icon="fas fa-arrow-right"
                 :disabled="!studyStore.hasUserId()"
                 size="large"
                 :text="$t('startChat')"
                 :to="{name: 'topics'}"
                 variant="flat" />
        </v-card-actions>
        <v-divider />
        <v-expansion-panels v-model="shownExpansion"
                            flat
                            tile
                            variant="accordion">
          <v-expansion-panel value="'moreAboutChatbot'">
            <v-expansion-panel-title class="text-title-sm" height="4rem">
              {{ $t('startMoreAbout') }}
            </v-expansion-panel-title>
            <v-expansion-panel-text class="markdown">
              <VueMarkdown v-if="$route.name === 'start'"
                           :source="locale === 'de' ? moreAboutDeMd : moreAboutEnMd" />
              <template v-else>
                <v-skeleton-loader v-if="learningTypesStore.isFetching" boilerplate type="paragraph@4" />
                <template v-for="learningType in learningTypesStore.learningTypes" v-else :key="learningType.id">
                  <h2>
                    {{ learningType.title[locale as keyof LearningType['title']] }}
                  </h2>
                  <VueMarkdown :source="learningType.long_description[locale]" />
                </template>
              </template>
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
  .learningTypeCard {
    background: rgb(var(--v-theme-tertiary-container)) !important;
    color: rgb(var(--v-theme-on-tertiary-container)) !important;

    .v-icon {
      position: absolute;
      right: 16px;
    }
  }

  .learningTypeCardSelected {
    background: rgb(var(--v-theme-tertiary)) !important;
    color: rgb(var(--v-theme-on-tertiary)) !important;
  }
</style>
