<script setup lang="ts">
  import { computed, onMounted } from 'vue'
  import { useI18n } from 'vue-i18n'
  import VueMarkdown from 'vue-markdown-render'
  import { useLearningTypesStore } from '@/stores/learningTypes'
  import { useStudyStore } from '@/stores/study'
  import moreAboutStudyDeMd from '@/locales/de_about_study.md?raw'
  import moreAboutStudyEnMd from '@/locales/en_about_study.md?raw'
  import moreAboutStudyDePostMd from '@/locales/de_about_study_post.md?raw'
  import moreAboutStudyEnPostMd from '@/locales/en_about_study_post.md?raw'

  const { locale, t } = useI18n()
  const learningTypesStore = useLearningTypesStore()
  const studyStore = useStudyStore()
  
  const markdownContent = computed(() => {
    if (studyStore.isDateAfterTarget()) {
      return locale.value === 'de' ? moreAboutStudyDePostMd : moreAboutStudyEnPostMd;
    }
    return locale.value === 'de' ? moreAboutStudyDeMd : moreAboutStudyEnMd;
  });

  function goToSurvey(survey: string) {
    window.open(studyStore.getQuestionnaireUrl(survey), '_blank');
  }

  onMounted(() => {
    if (!studyStore.hasUserId()) {
      studyStore.generateUserId();
    }
  });
</script>

<template>
  <v-main class="bg-brand">
    <v-container class="fill-height flex-column justify-center">
      <v-card max-width="800" variant="elevated">
        <v-card-title class="px-4 px-sm-6 px-md-10 pt-4 pt-sm-6 pt-md-8 text-center text-display-sm text-sm-display-md text-md-display-lg"
                      tag="h1">
          {{ $t('studyTitle') }}
        </v-card-title>

        <v-card-text class="px-4 px-sm-10 py-4">
          <VueMarkdown class="markdown text-body-1"
                       :html="true"
                       :source="markdownContent" />

          <div class="px-4 px-sm-10 d-flex justify-center" style="gap: 16px;">
            <v-btn :disabled="!studyStore.hasUserId()"
                   prepend-icon="fas fa-poll"
                   size="large"
                   variant="flat"
                   @click="goToSurvey('pre')">
              {{ $t('openPreSurvey') }}
            </v-btn>
            <v-btn :disabled="!studyStore.hasUserId() || !studyStore.hasUserSentMessage()"
                   prepend-icon="fas fa-poll"
                   size="large"
                   variant="flat"
                   @click="goToSurvey('post')">
              {{ $t('openPostSurvey') }}
            </v-btn>
          </div>
        </v-card-text>
        <v-divider />
        <v-card-actions class="my-6 justify-center">
          <v-btn append-icon="fas fa-arrow-right"
                 :disabled="!studyStore.hasUserId()"
                 size="large"
                 :text="$t('startChat')"
                 :to="{name: 'topics'}"
                 variant="flat" />
        </v-card-actions>
      </v-card>
    </v-container>
  </v-main>
</template>

<style scoped lang="scss">
.markdown {
  :deep(p) {
    margin-bottom: 1em;
  }
  :deep(a) {
    color: #007bff;
    text-decoration: underline;
  }

  :deep(a:hover) {
    color: #0056b3;
    text-decoration: underline;
  }
}
</style>
