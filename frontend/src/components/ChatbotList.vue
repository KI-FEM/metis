<script setup lang="ts">
  import {useI18n} from 'vue-i18n'
  import {useTheme} from 'vuetify'
  import {suggestAAColorVariant} from 'accessible-colors'

  import OnboardingStep from '@/components/OnboardingStep.vue'
  import {useTopicsStore} from '@/stores/topics'
  import {useOnboardingStore} from '@/stores/onboarding'
  import { computed, ref } from 'vue'

  const {locale} = useI18n()
  const theme = useTheme()
  const topicsStore = useTopicsStore()
  const onboardingStore = useOnboardingStore()

  function getTopicColor(color: string, isActive: boolean) {
    // TODO: suboptimal for middle contrast > change to whole topic theme instead?
    if (!color) return undefined
    const contrastColor = suggestAAColorVariant(color, isActive ? theme.current.value.colors['secondary-container']! : theme.current.value.colors['surface'], true)
    return contrastColor + ' !important'
  }
  const appliedTagFilter = ref(null as string | null)

  const filteredTopics = computed(() => {
    if (appliedTagFilter.value) {
      return topicsStore.unsubscribedTopics.filter(topic => topic.tag === appliedTagFilter.value)
    }
    return topicsStore.unsubscribedTopics
  })

  const allTags = computed(() => Array.from(new Set(topicsStore.unsubscribedTopics.map(t => t.tag))) as string[])

  function filterByTag(tag: string) {
    if (appliedTagFilter.value === tag) {
      appliedTagFilter.value = null
      return
    }
    appliedTagFilter.value = tag
  }
</script>

<template>
  <v-skeleton-loader :loading="topicsStore.isFetching" type="list-item-avatar-two-line@5">
    <v-list class="flex-shrink-0" open-strategy="single">
      <v-list-item v-for="topic in topicsStore.subscribedTopics"
                   :key="topic.endpoint"
                   :to="{name: topic.type === 'skills' ? 'modules' : 'chat', params: {endpoint: topic.endpoint}}">
        <template #prepend="{isActive}">
          <v-icon :icon="isActive ? 'mdi mdi-book-open-variant' : 'fas fa-book'"
                  :style="{color: getTopicColor(topic.color || '', isActive)}" />
        </template>
        <v-list-item-title class="font-weight-bold d-flex flex-row align-center ga-2" tag="h3">
          <span>
            {{ topic.title[locale] }}
          </span>
          <v-chip v-if="topic.tag"
                  density="comfortable"
                  label
                  size="small"
                  variant="outlined">
            {{ topic.tag }}
          </v-chip>
        </v-list-item-title>
        <v-list-item-subtitle>
          {{ topic.short_description[locale] }}
        </v-list-item-subtitle>
      </v-list-item>
    </v-list>
    <v-spacer />
    <v-divider v-if="topicsStore.unsubscribedTopics.length" />
    <v-list v-if="topicsStore.unsubscribedTopics.length" class="flex-shrink-0" open-strategy="single">
      <OnboardingStep v-if="onboardingStore.isRead('topicSelection')"
                      location="top"
                      storage-key="topicAddition"
                      :text="$t('onboardingTopicAddition')" />
      <v-list-subheader>
        <div class="text-body-1 text-primary">
          {{ $t('chatbotsSubscribe') }}:
        </div>
        <div class="d-flex flex-row align-center justify-start flex-wrap">
          <span v-if="appliedTagFilter == null" class="me-2">
            {{ $t('chatbotsFilter') }}:
          </span>
          <span v-else class="me-2 d-flex flex-row align-center">
            {{ $t('chatbotsFilterActive') }}:
          </span>
          <v-chip v-for="tag in allTags"
                  :key="tag"
                  class="ma-1"
                  density="comfortable"
                  label
                  size="small"
                  :variant="tag == appliedTagFilter ? 'tonal' : 'outlined'"
                  @click="filterByTag(tag)">
            {{ tag }}
          </v-chip>
        </div>
      </v-list-subheader>
      <v-list-item v-for="topic in filteredTopics"
                   :key="topic.endpoint"
                   @click="topicsStore.subscribeTopic(topic.endpoint)">
        <template #prepend="{isActive}">
          <v-icon :icon="isActive ? 'mdi mdi-book-open-variant' : 'fas fa-book'"
                  :style="{color: getTopicColor(topic.color || '', isActive)}" />
        </template>
        <v-list-item-title class="font-weight-bold d-flex flex-row align-center ga-2" tag="h3">
          <span>
            {{ topic.title[locale] }}
          </span>
          <v-chip v-if="topic.tag"
                  class="py-0"
                  density="comfortable"
                  label
                  size="small"
                  variant="outlined">
            {{ topic.tag }}
          </v-chip>
        </v-list-item-title>
        <v-list-item-subtitle>
          {{ topic.short_description[locale] }}
        </v-list-item-subtitle>
        <template #append>
          <v-icon icon="mdi mdi-plus-circle-outline" />
        </template>
      </v-list-item>
    </v-list>
  </v-skeleton-loader>
</template>

<style scoped>
  .v-chip {
    /* reduce horizontal padding of chips for better fit */
    padding: 0 10px !important;
  }
</style>
