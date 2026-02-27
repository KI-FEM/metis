<script setup lang="ts">
  import {ref, watchEffect} from 'vue'
  import {useI18n} from 'vue-i18n'
  import DialogCloseButton from '@/components/buttons/DialogCloseButton.vue'
  import { useStudyStore } from '@/stores/study.ts' // Import the study store

  const studyStore = useStudyStore() // Initialize the study store

  const { t } = useI18n()
  const tickLabels: { [key: number]: string } = {
    1: '<<',
    2: '<',
    3: '=',
    4: '>',
    5: '>>'
  }

  const showDialog = defineModel<boolean>({default: false})
  const feedbackCorrectness = ref(3)
  const feedbackRelevance = ref(3)
  const feedbackComplexity = ref(3)
  const feedbackValue = ref('')
  const showForm = ref(true)
  const feedbackAnswer = ref('')
  const recommendationsReady = ref(false)
  const isLoading = ref(false)

  // Slider configurations
  const sliderConfigs = ref([
    {
      id: 'correctness-slider',
      model: feedbackCorrectness,
      leftLabel: 'feedbackCorrectnessLeft',
      rightLabel: 'feedbackCorrectnessRight',
      swap: false
    },
    {
      id: 'relevance-slider', 
      model: feedbackRelevance,
      leftLabel: 'feedbackRelevanceLeft',
      rightLabel: 'feedbackRelevanceRight',
      swap: false
    },
    {
      id: 'complexity-slider',
      model: feedbackComplexity, 
      leftLabel: 'feedbackComplexityLeft',
      rightLabel: 'feedbackComplexityRight',
      swap: false
    }
  ])

  // Shuffle helper function
  const shuffleArray = (array: { id: string; model: number; leftLabel: string; rightLabel: string; swap: boolean }[]) => {
    const shuffled = [...array]
    for (let i = shuffled.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]]
    }
    // Randomize the `swap` property for each slider
    shuffled.forEach(item => {
      item.swap = Math.random() < 0.5
    })
    return shuffled
  }

  // Function to reverse the (5-point) slider value, if it was swapped
  const reverseValue = (value: number) => {
    return 6 - value
  }

  watchEffect(() => {
    recommendationsReady.value = false
    isLoading.value = false
    // Reset feedback form when dialog is shown
    if (showDialog.value) {
      feedbackCorrectness.value = 3
      feedbackRelevance.value = 3
      feedbackComplexity.value = 3
      feedbackValue.value = ''
      showForm.value = true
      feedbackAnswer.value = ''
      // Randomize slider order
      sliderConfigs.value = shuffleArray(sliderConfigs.value)
    }
  })

  const submit = async () => {
    showForm.value = false;

    // Adjust each feedback value based on the `swap` property
    const adjustedCorrectness = sliderConfigs.value.find(config => config.id === 'correctness-slider')?.swap
      ? reverseValue(feedbackCorrectness.value)
      : feedbackCorrectness.value;

    const adjustedRelevance = sliderConfigs.value.find(config => config.id === 'relevance-slider')?.swap
      ? reverseValue(feedbackRelevance.value)
      : feedbackRelevance.value;

    const adjustedComplexity = sliderConfigs.value.find(config => config.id === 'complexity-slider')?.swap
      ? reverseValue(feedbackComplexity.value)
      : feedbackComplexity.value;

    // Save feedback to local storage using the study store
    studyStore.saveFeedback(
      adjustedCorrectness,
      adjustedRelevance,
      adjustedComplexity,
      feedbackValue.value
    );

    feedbackAnswer.value = t('feedbackThanks');
  }
</script>

<template>
  <v-dialog v-model="showDialog"
            max-width="700"
            scrollable>
    <v-card>
      <v-card-item>
        <v-card-title class="d-flex align-center">
          <v-icon icon="far fa-hand-point-up" start />
          <h1 class="text-headline-sm">
            {{ $t('feedbackTitle') }}
          </h1>
          <DialogCloseButton class="ms-auto" @click="showDialog = false" />
        </v-card-title>
      </v-card-item>
      <v-form v-if="showForm" class="pa-4" @submit.prevent="submit">
        <div class="mb-4">
          <h3 class="text-h6 mb-3">
            {{ $t('feedbackQuestion') }}
          </h3>
        </div>
        <div v-for="config in sliderConfigs" :key="config.id" class="mb-4">
          <div class="d-flex justify-space-between mb-2">
            <span v-if="!config.swap">{{ $t(config.leftLabel) }}</span>
            <span v-else>{{ $t(config.rightLabel) }}</span>
            <span v-if="!config.swap">{{ $t(config.rightLabel) }}</span>
            <span v-else>{{ $t(config.leftLabel) }}</span>
          </div>
          <v-slider :id="config.id"
                    v-model="config.model"
                    class="my-2 text-h5"
                    color="primary"
                    :max="5"
                    :min="1"
                    show-ticks="always"
                    :step="1"
                    :ticks="tickLabels" />
        </div>
        <div>
          <span class="text-body-1 mb-2" /> 
          <v-textarea id="feedback" 
                      v-model="feedbackValue"
                      counter
                      :label="$t('feedbackMessage')" 
                      maxlength="200"
                      variant="filled" />
        </div>
        <v-btn block
               class="mt-2"
               color="primary"
               type="submit"
               variant="flat">
          {{ $t('submitButton') }}
        </v-btn>
      </v-form>
      <v-card-text v-else>
        <div>
          {{ feedbackAnswer }}
        </div>
        <div v-if="isLoading" class="d-flex flex-column align-center text-primary ga-3">
          <v-progress-circular color="primary" indeterminate />
        </div>
      </v-card-text>
    </v-card>
  </v-dialog>
</template>

<style scoped lang="scss">

</style>
