<script setup lang="ts">
  import {watchEffect} from 'vue'
  import {useI18n} from 'vue-i18n'
  import {useTheme} from 'vuetify'
  import {suggestAAColorVariant} from 'accessible-colors'

  import {useTopicsStore} from '@/stores/topics'
  import {useOnboardingStore} from '@/stores/onboarding'

  const {locale} = useI18n()
  const theme = useTheme()
  const topicsStore = useTopicsStore()
  const onboardingStore = useOnboardingStore()

  watchEffect(async () => {
    if (!onboardingStore.onboardingCompleted)
      onboardingStore.showOnboarding = true
  })

  function getTopicColor(color: string, isActive: boolean) {
    // TODO: suboptimal for middle contrast > change to whole topic theme instead?
    if (!color) return undefined
    const contrastColor = suggestAAColorVariant(color, isActive ? theme.current.value.colors['secondary-container'] : theme.current.value.colors['surface'], true)
    return contrastColor + ' !important'
  }
</script>

<template>
  <v-skeleton-loader :loading="topicsStore.isFetching" type="list-item-avatar-two-line@5">
    <v-list open-strategy="single">
      <v-list-item v-for="topic in topicsStore.topics"
                   :key="topic.endpoint"
                   :disabled="!topic.enabled"
                   :to="{name: topic.type === 'skills' ? 'modules' : 'chat', params: {endpoint: topic.endpoint}}">
        <template #prepend="{isActive}">
          <v-icon :icon="isActive ? 'mdi mdi-book-open-variant' : 'fas fa-book'"
                  :style="{color: getTopicColor(topic.color || '', isActive)}" />
        </template>
        <v-list-item-title class="font-weight-bold" tag="h3">
          {{ topic.title[locale] }}
        </v-list-item-title>
        <v-list-item-subtitle>
          {{ topic.short_description[locale] }}
        </v-list-item-subtitle>
      </v-list-item>
    </v-list>
  </v-skeleton-loader>
</template>

<style scoped>

</style>
