<script setup lang="ts">
  import {computed, ref} from 'vue'
  import {VueDraggable} from 'vue-draggable-plus'
  import VueMarkdown from 'vue-markdown-render'
  import {useI18n} from 'vue-i18n'

  import {useChatStore} from '@/stores/chat'

  import ChatBubble from '@/components/ChatBubble.vue'
  import OnboardingStep from './OnboardingStep.vue'

  import type {components} from '@/types_api'

  const {locale} = useI18n()
  const chatStore = useChatStore()

  const isEditMode = ref(false)

  const bookmarkedMessages = computed(() => {
    if (!chatStore.currentChat) return []
    return chatStore.bookmarksStorage[chatStore.currentChat?.id]?.map(index => chatStore.currentChat?.messages[index]).filter(message => !!message && !message.fragment) ?? []
  })

  function removeBookmark(index: number) {
    if (!chatStore.currentChat) return
    chatStore.bookmarksStorage[chatStore.currentChat.id]?.splice(index, 1)
  }

  const competences = computed(() => {
    const learnerModel = chatStore.currentChat?.storage['learner_model'] as components['schemas']['LearnerModel-Input']
    if (!(learnerModel && typeof learnerModel === 'object' && 'competences' in learnerModel))
      return []
    const competences: components['schemas']['LearnerModel-Input']['competences'] = learnerModel['competences']
    if (!competences || competences === undefined || Object.keys(competences).length === 0)
      return []
    return Object.values(competences).map(competence => ({
      title: competence.name[locale.value],
      score: (competence['competence_level'] || 0),
      children: Object.values(competence['concepts']).map(concept => ({
        title: concept.name[locale.value],
        completed: concept.completed,
        score: calculateConceptScore(concept),
        children: Object.values(concept.learning_units).length ? Object.values(concept.learning_units).map(unit => ({
          title: unit.name[locale.value],
          completed: unit.completed,
          score: calculateLearningUnitScore(unit)
        })) : undefined
      }))
    }))
  })

  function mean(arr: number[]): number {
    return arr.length ? arr.reduce((a, b) => a + b, 0) / arr.length : 0
  }

  function calculateLearningUnitScore(lu: components['schemas']['LearnerModelConcept-Input']['learning_units'][0]) {
    const PRIOR = 0.6
    const K = 3
    const EXPO_CAP = 5
    const W_COMP = 0.6, W_ACC = 0.3, W_EXPO = 0.1

    const comp = lu.completed ? 1 : 0
    const tq = lu.times_quizzed ?? 0
    const tc = lu.times_correct ?? 0
    const ts = lu.times_seen ?? 0
    const acc = (tc + K * PRIOR) / (tq + K)
    const expo = Math.min(ts, EXPO_CAP) / EXPO_CAP
    return 100 * (W_COMP * comp + W_ACC * comp * acc + W_EXPO * expo)
  }

  function calculateConceptScore(concept: components['schemas']['LearnerModelConcept-Input']) {
    if (concept.learning_units.length)
      return mean(Object.values(concept.learning_units).map(calculateLearningUnitScore))
    return concept.completed ? 100 : 0
  }
</script>

<template>
  <v-navigation-drawer v-model="chatStore.showDashboard" location="end" mobile-breakpoint="md">
    <template #prepend>
      <div class="mt-8 mb-11 pa-2 d-flex flex-column align-center gr-4">
        <h2 class="d-flex align-center text-headline-lg">
          <v-icon icon="mdi mdi-view-dashboard-outline" start />
          {{ $t('dashboard') }}
        </h2>
        <!--        <v-toolbar class="px-3" -->
        <!--                   floating -->
        <!--                   rounded="xl" -->
        <!--                   tag="div"> -->
        <!--          <v-btn v-tooltip="'Kacheln bearbeiten'" -->
        <!--                 icon="mdi mdi-view-dashboard-edit-outline" -->
        <!--                 @click="isEditMode = !isEditMode" /> -->
        <!--          <v-btn v-tooltip="'Dashboard schließen'" -->
        <!--                 icon="fas fa-close" -->
        <!--                 variant="text" -->
        <!--                 @click="chatStore.showDashboard = false" /> -->
        <!--        </v-toolbar> -->
      </div>
    </template>
    <OnboardingStep v-if="chatStore.showDashboard"
                    location="top"
                    storage-key="dashboard"
                    :text="$t('onboardingDashboard')" />
    <v-expansion-panels flat rounded="md">
      <v-expansion-panel :disabled="!competences.length">
        <v-expansion-panel-title>
          <v-icon icon="fas fa-table-list" />
          {{ $t('dashboardTopics') }}
        </v-expansion-panel-title>
        <v-expansion-panel-text>
          <v-treeview density="compact"
                      indent-lines
                      :items="competences"
                      open-on-click
                      separate-roots>
            <template #append="{item, depth}">
              <v-progress-circular v-if="depth" :model-value="item.score" size="20" />
            </template>
          </v-treeview>
        </v-expansion-panel-text>
      </v-expansion-panel>
      <v-expansion-panel>
        <v-expansion-panel-title>
          <v-icon icon="fas fa-lightbulb" />
          {{ $t('dashboardFindings') }}
        </v-expansion-panel-title>
        <v-expansion-panel-text>
          <VueMarkdown :source="chatStore.currentChat?.storage['user_memory'] as string || $t('dashboardNoUserMemory')" />
        </v-expansion-panel-text>
      </v-expansion-panel>
      <v-expansion-panel>
        <v-expansion-panel-title>
          <v-icon icon="fas fa-thumbtack" />
          {{ $t('dashboardBookmarks') }}
        </v-expansion-panel-title>
        <v-expansion-panel-text>
          <em v-if="!bookmarkedMessages.length">{{ $t('dashboardBookmarksEmpty') }}</em>
          <ChatBubble v-for="(message, index) in bookmarkedMessages"
                      :key="index"
                      bookmarked
                      :message="message"
                      @bookmark="removeBookmark(index)" />
        </v-expansion-panel-text>
      </v-expansion-panel>
      <v-expansion-panel>
        <v-expansion-panel-title>
          <v-icon icon="fas fa-comment-dots" />
          {{ $t('dashboardThoughts') }}
        </v-expansion-panel-title>
        <v-expansion-panel-text>
          <VueMarkdown :source="chatStore.currentChat?.storage['conversation_strategy'] as string || $t('dashboardNoConversationStrategy')" />
        </v-expansion-panel-text>
      </v-expansion-panel>
      <!--      <v-expansion-panel> -->
      <!--        <v-expansion-panel-title> -->
      <!--          <v-icon icon="fas fa-calendar-days" /> -->
      <!--          {{ $t('dashboardCalendar') }} -->
      <!--        </v-expansion-panel-title> -->
      <!--        <v-expansion-panel-text> -->
      <!--          Hier kannst du wichtige Termine wie Prüfungen, Abgabetermine usw. einrichten, damit Metis dich daran erinnern -->
      <!--          und passende Lernpläne erstellen kann. -->
      <!--          <v-date-picker class="mt-3" -->
      <!--                         elevation="0" -->
      <!--                         hide-header -->
      <!--                         width="100%" /> -->
      <!--        </v-expansion-panel-text> -->
      <!--      </v-expansion-panel> -->
    </v-expansion-panels>
    <template #append>
      <div class="mt-3 text-center">
        <v-btn variant="outlined" @click="chatStore.showDashboard = false" :text="$t('dashboardClose')" />
      </div>
    </template>
  </v-navigation-drawer>
</template>

<style scoped lang="scss">

</style>
