<script setup lang="ts">
  import {computed, ref} from 'vue'
  import {useRoute} from 'vue-router'
  import {useDisplay, useTheme, useLayout} from 'vuetify'
  import {useI18n} from 'vue-i18n'
  import VueMarkdown from 'vue-markdown-render'

  import type {Chat} from '@/types'
  import type {components} from '@/types_api'

  import {useTopicsStore} from '@/stores/topics'
  import {useChatStore} from '@/stores/chat'

  import OnboardingStep from '@/components/OnboardingStep.vue'
  import StorageInfoDialog from './dialogs/StorageInfoDialog.vue'

  defineOptions({
    inheritAttrs: false // needed to apply attributes from parent only to the main element (card)
  })

  const route = useRoute()
  const {xs} = useDisplay()
  const layout = useLayout()
  const {locale} = useI18n()
  const topicsStore = useTopicsStore()
  const chatStore = useChatStore()
  const theme = useTheme()

  const collapse = defineModel({default: false})

  // const collapse = ref(false)

  const isDev = import.meta.env.DEV

  const maxHeight = computed(() => `max-height: calc(100% - ${layout.mainRect.value.top}px - 16px)`)
  const selectedModule = computed(() => topicsStore.selectedTopic?.modules.find(module => module.code === route.params.chatId) as components['schemas']['Skill'])
  const selectedLevel = computed(() => selectedModule.value?.levels.find(level => level.id.toString() === topicsStore.storedModuleLevelId(selectedModule.value?.code)?.toString()))

  function getChatTitle(chat: Chat) {
    const title = chat.title || chatStore.getDefaultChatTitle()
    return title.length > 48 ? `${title.slice(0, 48)}...` : title // if longer than 48 chars, cut it off
  }


  const showStorageInfo = ref(false)

  function openStorageInfo() {
    showStorageInfo.value = true
  }

  function getImageUrl(imageURL: string) {
    if (!imageURL) return ''
    return import.meta.env.VITE_API_URL + imageURL.replace('{theme}', theme.current.value.dark ? 'dark' : 'light')
  }
</script>

<template>
  <v-card v-bind="$attrs" tag="header">
    <!-- TODO: Mobile layout? -->
    <div>
      <v-card-item>
        <v-card-title class="d-flex align-center ga-3 text-headline-sm text-sm-headline-md text-md-headline-lg">
          <v-icon icon="mdi mdi-book-open-variant" :style="{color: topicsStore.selectedTopic?.color || undefined}" />
          <v-skeleton-loader :loading="topicsStore.isFetching" type="heading" :width="xs ? '80%' : '60%'">
            <h2 style="font-size: inherit; font-weight: inherit;" class="d-flex flex-row align-center ga-2">
              <span>
                {{ topicsStore.selectedTopic?.title[locale] }}
              </span>
              <v-chip v-if="topicsStore.selectedTopic?.tag"
                      label
                      variant="outlined"
                      density="comfortable">
                {{ topicsStore.selectedTopic?.tag }}
              </v-chip>
            </h2>
          </v-skeleton-loader>
          <v-btn v-show="collapse"
                 v-tooltip="$t('topicCardMaximize')"
                 class="ms-auto"
                 icon="fas fa-chevron-down"
                 variant="text"
                 @click="collapse = false" />
        </v-card-title>
      </v-card-item>
      <v-expand-transition>
        <v-card-text v-show="!collapse" class="pb-0" :class="{'d-flex': !collapse}">
          <v-skeleton-loader :loading="topicsStore.isFetching" type="sentences">
            <VueMarkdown class="markdown" :source="topicsStore.selectedTopic?.long_description[locale] || ''" />
          </v-skeleton-loader>
          <img v-if="topicsStore.selectedTopic?.avatar"
               alt=""
               class="mt-sm-n16"
               :height="xs ? 100 : 200"
               :src="getImageUrl(topicsStore.selectedTopic?.avatar)"
               style="object-fit: contain">
        </v-card-text>
      </v-expand-transition>
      <v-expand-transition>
        <v-card-actions v-if="$route.name === 'chat'" v-show="!collapse">
          <v-skeleton-loader class="w-100 align-end ga-2" :loading="topicsStore.isFetching" type="button@2">
            <template v-if="selectedModule">
              <OnboardingStep storage-key="switchModuleLevel" :text="$t('onboardingSwitchModuleLevel')" />
              <v-chip class="bg-secondary"
                      prepend-icon="fas fa-graduation-cap"
                      :to="{name: 'modules'}">
                <span class="d-sr-only">{{ $t('actionModule') + ': ' }}</span>
                {{ selectedModule?.title[locale] }}
              </v-chip>
              <v-chip class="bg-tertiary"
                      prepend-icon="fas fa-flag-checkered"
                      :to="{name: 'modules'}">
                <span class="d-sr-only">{{ $t('actionLevel') + ': ' }}</span>
                {{ selectedLevel?.title[locale] }}
              </v-chip>
            </template>
            <template v-else-if="topicsStore.selectedTopic?.type === 'basic'">
              <OnboardingStep storage-key="switchChats" :text="$t('onboardingSwitchChats')" />
              <v-chip class="bg-secondary"
                      prepend-icon="fas fa-clock-rotate-left">
                {{ $t('actionChatHistory') }}
                <v-menu activator="parent" open-on-click>
                  <v-list>
                    <v-list-item v-for="chat in chatStore.topicChats"
                                 :key="chat.id"
                                 :subtitle="chat.id"
                                 :title="getChatTitle(chat)"
                                 :to="{name: 'chat', params: {chatId: chat.id}}" />
                  </v-list>
                </v-menu>
              </v-chip>
              <v-chip class="bg-tertiary"
                      prepend-icon="far fa-comment"
                      :text="$t('actionNewChat')"
                      :to="{name: 'chat', params: {chatId: 'new'}}" />
            </template>
            <v-spacer />
            <v-chip v-if="isDev"
                    class="bg-tertiary"
                    prepend-icon="fas fa-database"
                    text="Debug Storage"
                    @click="openStorageInfo" />
            <StorageInfoDialog v-model="showStorageInfo" />
            <v-btn v-if="topicsStore.selectedTopic?.optional"
                   v-tooltip="$t('topicUnsubscribe')"
                   icon="mdi mdi-minus-circle-outline"
                   @click="topicsStore.unsubscribeTopic(topicsStore.selectedTopic?.endpoint)" />
            <v-btn v-show="!collapse"
                   v-tooltip="$t('topicCardMinimize')"
                   class="ms-auto"
                   icon="fas fa-chevron-up"
                   variant="text"
                   @click="collapse = true" />
          </v-skeleton-loader>
        </v-card-actions>
      </v-expand-transition>
    </div>
  </v-card>
</template>

<style scoped lang="scss">
  .expand-transition-leave-to {
    min-height: 0;
    padding-top: 0;
    padding-bottom: 0;
  }
</style>
