<script setup lang="ts">
  import {ref, watch} from 'vue'
  import {useI18n} from 'vue-i18n'

  import type {LearningType} from '@/types.ts'

  import {useLearningTypesStore} from '@/stores/learningTypes.ts'

  const learningTypesStore = useLearningTypesStore()
  const {locale} = useI18n()

  const showSnackbar = ref(false)

  watch(() => learningTypesStore.selectedLearningTypeId, () => {
    showSnackbar.value = true
  })
</script>

<template>
  <v-btn :aria-label="$t('changeLearningType')" icon variant="text">
    <v-icon icon="fas fa-graduation-cap" />
    <v-tooltip activator="parent" :text="$t('changeLearningType')" />
    <v-menu activator="parent" open-on-click>
      <v-list mandatory
              :selected="[learningTypesStore.selectedLearningTypeId]"
              slim
              @update:selected="learningTypesStore.selectedLearningTypeId = $event[0]">
        <v-list-item v-for="learningType in learningTypesStore.learningTypes"
                     :key="learningType.id"
                     :title="learningType.title[locale as keyof LearningType['title']]"
                     :value="learningType.id" />
        <v-divider />
        <v-list-item prepend-icon="fas fa-circle-question"
                     :title="$t('moreAboutLearningTypes')"
                     :to="{name: 'learningStyles'}" />
      </v-list>
    </v-menu>
  </v-btn>
  <v-snackbar v-model="showSnackbar"
              min-width="0"
              rounded="pill"
              :text="$t('selectedLearningType', {learningType: learningTypesStore.selectedLearningType?.title[locale as keyof LearningType['title']]})" />
</template>

<style scoped>

</style>
